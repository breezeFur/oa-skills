# 条件业务规则

仅在需求包含条件、筛选或 if/else 时读取本文件。

- 用户没有说明条件成立或不成立后要做什么时，不擅自补写更新、删除、通知或其他业务动作。
- 条件的业务含义存在多个合理解释时，向用户确认比较含义与各结果分支的预期动作。
- 条件字段、操作符、值形态的**权威规范（前端 ConditionSet 源码逆向）**见下方「二、ESB filterInput / ConditionSet 右值规范」，来源：工作区 `condition-generator-skill/`（SKILL.md 第 6 章 + references/）。

---

## 一、筛选条件（filterCondition）plan 写法

- 单条件：`{"field": {"id": "<目标字段id>", "label": "<字段名>"}, "operator": "<操作符>", "right": {...}}`。`right` 是唯一对外计划字段；不要使用历史别名 `value`。
- 条件组（且/或）：`{"relationship": "and|or", "conditions": [ <条件1>, <条件2>, ... ]}`（编译器支持嵌套）。不接受平台输出 DTO 的 `datas` 或 `1/0`。
- `right` 值形态（type）：
  - `context`：`{"type":"context","paramKey":"<真实paramKey>","label":"<显示名>"}` —— 引用上游上下文（esbAssign.wId 自动指向当前节点）
  - `native` + `mode: "currentTime"|"currentDate"|"now"|"today"`：**当前时间/当前日期**。编译器自动改写为系统参数 `{time}`/`{date}`（见下节 6），`conditions.value` 非空、`type:""`，设计器点开筛选器右值区能正常回显，不会出现「右值未配置」（真机验证 2026-08-18）
  - `fixed`：普通固定值；字符串为 `{...}` 系统变量时自动识别为 system
  - `system`：系统参数 token，如 `{userid}`/`{date}`/`{time}`（由动作流编译器内置 system_params 处理）
- 操作符：`eq/neq/gt/lt/gte/lte/contains/uncontains/empty/nempty`（`empty/nempty` 无右值）
- 日期字段用系统值：直接 `right.value = "{date}"` 或 `{time}`（ESB 体系），无需 `{today}`（那是通用 ConditionSet 的占位符写法，ESB 编译器会归一为 system）

## 分支条件（`Condition`）

分支条件和 `filterCondition` 共用 AND/OR 业务语义，但保存协议不同，不能互相复制 DTO。

- **分支位置**：`branches` 写在节点顶层或 `params.branches` 都会被受理（`component-describe Condition` 声明的就是 `params.branches`）；归一化后草稿只保留顶层 `branches`。**同一节点不要两处各写一份**——读分支的实现统一走同一入口，两份写法只会让人误判哪份生效。
- 计划用 `condition: { relationship: "and|or", conditions: [...] }`；叶子为 `{left, operator, right}`。顶层 `relationship` 直接作为条件树根关系；编译器不会额外套同关系 AND/OR，只有条件中明确嵌套的规则组才保留子组。
- `left` 只能是当前上游组件的实时字段；`operator` 由字段类型限制，未知或不兼容时编译失败。
- `right` 只用 `fixed`、`system`、`context`，或 `formula` 完整回读对象。`context` 必须写真实 `paramKey`，由运行时生成 FormulaBean；禁止把字段名作为固定值。
- 保存采用 ESB `source=8`：预暂存注册来源节点 → `getConditionSet` → `saveCondition` → 以保存响应回填真实持久化 ID → 最终暂存。新建后 `getExpressionBean` 可能只返回分组骨架，不能覆盖完整 `childrens` 叶子树；`mapBaseId`、`conditionId`、`mapId` 和所有 Long ID 都保持字符串，新建条件不传本地 `conditionId`。

## 二、ESB filterInput / ConditionSet 右值规范（源自 condition-generator-skill）

ESB 动作流的 `filterInput`（TimeBatchTrigger/DateTrigger/数据动作筛选）与通用 ConditionSet 筛选器**结构同源**（`isNewFilter/isParent/datas/relationship/key` + 叶子 `conditions{func,type,value,text}`）。生成条件时遵循以下规范：

### 1. 叶子条件结构

```json
{
  "id": "<字段id>", "fieldName": "<字段英文名>",
  "conditions": { "func": "lt", "type": "", "value": "{time}", "text": "当前时间" }
}
```

`fieldType/text/objId/compType` 等元信息由编译器按真实字段补全（`buildFilterInput`），**plan 里不写**。对于关联字段，编译器必须保留平台所需的真实 `sformId`；`refObjId` 仅在该组件的正式 DTO 要求时保留，不能把它作为所有关联字段的统一必填项，也不能只写字段 ID或把表单版本 `formId` 当作关联对象身份，否则保存后设计器可能显示“字段已删除”。

其中 Workflow 字段要区分两种 ID：`formInfo.formId` 是当前目标表单的版本 ID；顶层 `sformId` 是该字段关联的流程表单对象 ID。正式回读的 Workflow DTO 使用原始数字 `fieldName`、`fieldType:"String"`、空 `module`/`originBrowserType`，`config` 只保留 `fieldId`；不能按普通 e-builder 业务字段加 `field_` 前缀，也不能把组件名 `Workflow` 当作存储类型。`refObjId` 对 Workflow 不是必填。若实时字段接口没有返回 Workflow 的关联对象，预检必须根据当前 `workflowPath.formIds` 在同一应用的表单列表中反查对象 ID，并把目标表 `getFormLayout` 返回的默认布局 ID写入 `formInfo.layoutId`。反查不到时应报错停止，不能用目标表单版本 ID兜底。

### 2. 值类型 `conditions.type` 枚举

| type | 含义 | 适用 |
|---|---|---|
| `""` | 手动输入 / 选选项 / **系统值** | 文本/数值直接输入、选择框选选项、**日期选系统占位符** |
| `"custom"` | 专用选择器 / 选择框手动输入 | 人员/部门/级联/地区/Select 手动输入；**日期 range 模式推荐**（渲染日期选择器） |
| `"custombyhander"` | 手动输入（浏览器类组件） | 人员/部门/关联字段/文档/附件 |
| `"formField"` | 引用本表/关联表字段值 | 所有类型（value 含 `compareFormField`，必须含 `objId`+`name` 否则回显空白） |
| `"varField"` | 引用系统/流程变量 | 所有类型（value 含 `compareVarField`，`id` 必须是真实变量 id 否则回显空白） |
| `"filterVal"` | 引用其他筛选组件搜索值 | 文本/数值/日期 |

### 3. 系统日期占位符（通用 ConditionSet 写法，type 为 `""`）

| 占位符 | 含义 |
|---|---|
| `{today}` | 当前日期 |
| `{yesterday}` / `{tomorrow}` | 昨天 / 明天 |
| `{currweek}` / `{lastweek}` / `{nextweek}` | 本周 / 上周 / 下周 |
| `{currmonth}` / `{lastmonth}` / `{nextmonth}` | 本月 / 上月 / 下月 |
| `{currseason}` / `{lastseason}` / `{nextseason}` | 本季 / 上季 / 下季 |
| `{curryear}` / `{lastyear}` / `{nextyear}` | 本年 / 去年 / 明年 |

自定义日期占位符（type `"custom"`，后端 `handleValue` 识别）：`{year}`（本年区间）、`{year}-{month}`（当月区间）、`{date:±N}`（今天±N 天）。

> **ESB 差异**：ESB 动作流的系统值 token 由编译器内置 system_params 处理（`{date}`=当前日期、`{time}`=当前时刻、`{userid}` 等）；通用 ConditionSet 的 `{today}` 等占位符在 ESB filterInput 中由编译器归一（native `currentTime/currentDate/now/today` → `{time}`/`{date}`），生成时两者皆可，编译器兜底。

### 4. func 操作符

| func | 含义 | 适用 |
|---|---|---|
| `eq`/`neq` | 等于/不等于 | 所有 |
| `gt`/`lt`/`gte`/`lte` | 大于/小于/大于等于/小于等于 | 数值、日期 |
| `range` | 区间（value 为 `[起始,结束]`） | 数值、日期 |
| `contains`/`uncontains` | 包含/不包含 | 文本 |
| `empty`/`nempty` | 为空/不为空（无右值） | 所有 |

### 5. 字段类型 × 值类型速查

- 文本（String/Text/TextArea）：type `""`、`formField`、`varField`、`filterVal`；无 `custombyhander`
- 数值（Number/NumberComponent）：type `""`（含 range）、`formField`、`varField`、`filterVal`；**无 `custombyhander`**
- 日期（Date/DateComponent/DateInterval）：type `""`（手动输入/系统日期）、`"custom"`（手动输入，range 推荐）、`"customDate"`（仅宿主注入回调时可用，**默认不用**）、`formField`、`varField`、`filterVal`
- 选择框（Select/RadioBox/CheckBox）：type `""`（选选项，value 逗号分隔）、`"custom"`（手动输入）、`formField`、`varField`
- 人员（Employee）/部门（Department）：type `""`（系统选项）、`"custom"`（选人/选部门）、`"custombyhander"`、`formField`、`varField`

### 6. 「当前时间」筛选的正确表达（真机验证 2026-08-18）

ESB TimeBatchTrigger/DateTrigger 等定时器的 `filterCondition` 用「字段 < 当前时间」时：

- plan 写：`{"field": {"id": "<日期字段id>", "label": "<字段名>"}, "operator": "lt", "right": {"type": "native", "mode": "currentTime", "label": "当前时间"}}`
- 编译器把 `native currentTime/now/current_time` 改写为系统参数 `{time}`（`currentDate/today/current_date` → `{date}`），落到 system 路径
- 读回后 `conditions = {"func":"lt","text":"当前时间","value":"{time}","type":"","isEsb":false}` —— value 非空，设计器点开筛选器右值区正常回显「当前时间」，**不会空**（此前直接透传 `type:"currentTime"` + `value:""` 导致点进去右值区空白，外部摘要正常）
