# 流程分支条件指南

> 流程基础（建流程、节点、连线、审批人）见 `workflow/guide-workflow.md`。本指南专讲**分支/出口条件**：金额>1万走高级审批、合同类型=采购走快速通道这类路由。

## 添加分支条件（简化语法，推荐）

**一行命令搞定**，自动校验字段类型、自动生成 API payload、自动绑定到连线：

命令中的 `<sourceId>` 是要绑定条件的**连线 ID（linkId）**，`<nodeId>` 是该连线的**来源节点 ID（srcNodeId）**，不是目标节点 ID。可先执行 `workflow nodes <wf> --json` 或 `workflow link-list <wf>`，从同一条连线中取得这两个值。

> **AND / OR 规则写在「同一次调用」里**：要组合多条规则，一次 `add` 传多个 `--rule` + `--relation AND|OR`，例如
> `--rule "form:金额:大于:1000" --rule "system:流程标题:包含:合同" --relation AND`。
>
> **对同一连线重复 `add` 是「替换」，不是叠加**：第二次 `add` 会先删掉该连线旧条件再重建。这是刻意的——若允许跨调用叠加，极易产生 `(金额≥100万) AND (金额<100万)` 这类永远不成立的矛盾条件。因此**想给已有条件补一条规则，必须在新的 `add` 里把旧规则连同新规则一起写全**，不能靠再跑一次叠上去。
>
> **同源节点多分支**：一条连线只绑一个条件。要分多个分支，先给每个分支各建一条连线（`add-link`），再分别对每条连线 `add`。

### 基础示例

```bash
# 系统字段条件
e10-cli workflow condition add <wf> <sourceId> <nodeId> "条件名称" \
  --rule "system:流程标题:包含:关键词"

# 数值范围条件
e10-cli workflow condition add <wf> <sourceId> <nodeId> "金额过万" \
  --rule "system:流程超时(时):范围:1:72"

# 日期范围条件
e10-cli workflow condition add <wf> <sourceId> <nodeId> "今年发起" \
  --rule "system:发起时间:范围:2026-01-01:2026-12-31"

# 为空/不为空
e10-cli workflow condition add <wf> <sourceId> <nodeId> "无部门" \
  --rule "system:发起人部门:为空"

# 多规则 AND/OR 组合
e10-cli workflow condition add <wf> <sourceId> <nodeId> "复合条件" \
  --rule "system:流程标题:包含:报销" \
  --rule "system:流程超时(时):大于:24" \
  --relation AND

# 表单字段条件（字段ID / 名称 / dataKey 均可匹配）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "表单字段" \
  --rule "form:<字段ID>:大于:1000"          # 按 fieldId
  --rule "form:申请金额:大于:1000"          # 按字段名
  --rule "form:je_2831:大于:1000"           # 按 dataKey（原生流程表单 fieldId 会变，用 dataKey 最稳）
```

### 选项类字段（Select/CheckBox/RadioBox）：用"属于"或"包含"

选项类字段归 Browser 族，用 `属于`（= `包含`，code 9）匹配任一选项：

```bash
# 合同类型=采购类（单个选项）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "采购类合同" \
  --rule "form:合同类型:属于:采购类"

# 报销类型∈{差旅费,住宿费}（多个选项，逗号分隔）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "差旅住宿报销" \
  --rule "form:报销类型:属于:差旅费,住宿费"

# 也可以直接用"包含"（等价）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "招待费报销" \
  --rule "form:报销类型:包含:招待费"

# 不包含/不属于
e10-cli workflow condition add <wf> <sourceId> <nodeId> "非采购类" \
  --rule "form:合同类型:不属于:采购类"
```

> `属于` 和 `包含` 是**别名**，底层都是 code 9（"包含或属于"），由平台显示语义。对 Select/CheckBox/RadioBox 选项字段，建议用 `属于`；对文本/人员字段用 `包含`。

### 人员/部门字段

人员/部门字段值走浏览器解析，用逗号分隔多值：

```bash
# 报销人=闫宇或吴鹏（人员多选）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "闫宇或吴鹏报销" \
  --rule "form:报销人:等于:闫宇,吴鹏"

# 所属部门=财务部
e10-cli workflow condition add <wf> <sourceId> <nodeId> "财务部报销" \
  --rule "form:所属部门:等于:财务部"

# 部门不含子部门
e10-cli workflow condition add <wf> <sourceId> <nodeId> "本部门" \
  --rule "form:所属部门:等于:财务部:不包含子部门"
```

### 字段 vs 字段比较（变量模式）

用 `field` 关键字表示值来自另一个字段，而非字面值：

```bash
# 发起时间 ≥ 报销日期（系统字段 vs 表单字段）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "先报销后发起" \
  --rule "system:发起时间:大于等于:field:报销日期"

# 发票日期 < 报销日期（表单字段 vs 表单字段）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "发票早于报销日期" \
  --rule "form:发票日期:小于:field:报销日期"

# 数值字段 vs 字段
e10-cli workflow condition add <wf> <sourceId> <nodeId> "超标" \
  --rule "form:实际金额:大于:field:预算金额"
```

> **语法**：`来源:左字段:操作:field:右字段`。`field` 是固定关键字，表示右边是字段引用不是字面值。支持 `system` 和 `form` 两种来源，适用范围：`大于`/`小于`/`等于`/`不等于`/`大于等于`/`小于等于`。

### 明细字段条件

末尾量词 `:任一`(任一行满足，**缺省**) / `:所有`(所有行满足)：

> **量词只对明细字段生效**：它决定"明细任一行 / 所有行"的语义，只有左字段属于明细表时才会写入配置。**写在主表字段上会被忽略且不报错**——主表字段直接省略量词。明细字段省略量词时按"任一行"处理。

```bash
# 明细任一行金额>1万
e10-cli workflow condition add <wf> <sourceId> <nodeId> "明细金额过万" \
  --rule "form:明细金额:大于:10000:任一"

# 明细所有行数量都在 1~100
e10-cli workflow condition add <wf> <sourceId> <nodeId> "明细数量范围" \
  --rule "form:明细数量:范围:1:100:所有"

# 明细字段 vs 字段（发票日期 < 报销日期）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "明细发票日期" \
  --rule "form:发票日期:小于:field:报销日期:任一"
```

明细量与主表条件组合（同一次调用内，多条 `--rule` 默认 AND）：

```bash
# 所属部门=财务部 AND 明细任一行金额>1万
e10-cli workflow condition add <wf> <sourceId> <nodeId> "财务部大额明细" \
  --rule "form:所属部门:等于:财务部" \
  --rule "form:明细金额:大于:10000:任一"

# 明细所有行数量都在 1~100 AND （发起时间≥报销日期）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "明细数量且时间" \
  --rule "form:明细数量:范围:1:100:所有" \
  --rule "system:发起时间:大于等于:field:报销日期"
```

> 需要"明细任一行满足 A **或** 任一行满足 B"时，用 `|` 把两条明细规则串在同一条 `--rule` 里（见下方 OR 分组），两条各带各的量词。

### OR 分组：用 `|` 分隔子规则

同一条 `--rule` 内用 `|` 分隔表示 OR 关系：

```bash
# 报销类型∈{差旅费,住宿费} OR 发票编号含 FP（两个都是主表字段，不带量词）
e10-cli workflow condition add <wf> <sourceId> <nodeId> "差旅住宿或含FP发票" \
  --rule "form:报销类型:属于:差旅费,住宿费|form:发票编号:包含:FP"

# 报销金额>10000 OR 紧急程度=紧急
e10-cli workflow condition add <wf> <sourceId> <nodeId> "大额或紧急" \
  --rule "form:报销金额:大于:10000" \
  --rule "system:紧急程度:等于:紧急"
```

> 单条 `--rule` 内用 `|` 分隔的子规则是 OR 关系；多条 `--rule` 之间默认 AND 关系（`--relation OR` 可改）。

### 完整复杂条件示例

```bash
# 报销初审→财务部专项复核：
# AND条件：所属部门=财务部, 报销金额5k~10k, 发起时间≥报销日期,
# OR条件：报销类型∈{差旅费,住宿费} OR 发票编号含 FP
e10-cli workflow condition add <wf> <sourceId> <nodeId> "财务部复核" \
  --rule "form:所属部门:等于:财务部" \
  --rule "form:报销金额:范围:5000:10000" \
  --rule "system:发起时间:大于等于:field:报销日期" \
  --rule "form:报销类型:属于:差旅费,住宿费|form:发票编号:包含:FP"
```

### 平台边界：不支持"前缀匹配"

出口条件**没有「以…开头 / 开头包含」运算符**。文本字段可用的比较符就是：等于、不等于、包含、不包含、为空、不为空——其中 **「包含」是全串包含**，`FP` 出现在编号任意位置都算命中，不限定开头。

写前缀操作会被当场拒绝，不会静默存错：

```bash
e10-cli workflow condition add <wf> <sourceId> <nodeId> "FP发票" --rule "form:发票编号:开头包含:FP"
# ❌ 字段 "发票编号" (类型=String) 不支持操作 "开头包含"，可选: 等于, 不等于, 包含, 不包含, 为空, 不为空
```

要表达"编号以 FP 开头"，按下列顺序选，**不要**把「包含」当「开头」用：

1. **编号规则本身前缀唯一**——同前缀不会出现在其他类别里，直接用「包含」，语义等价；
2. **取值有限**——用「属于」逐项枚举，如 `属于:FP001,FP002,FP003`；
3. **确实要严格前缀语义**——不在出口条件解决：改用节点提交校验（`workflow node validate`）或表单/编号规则层约束；
4. **都不行**——走平台需求，不要在方案里承诺出口条件支持前缀。

> **判据以协议为准**：可用关系符的唯一权威来源是 `POST /api/workflow/pathdef/rule/condition/getRuleDesignCondition` 的当次响应（`otherItems` / `browserCompareOptions`），历史编码矩阵只作参考。协议里没有的语义，**直接判定不支持，不要用相近编码替代**——这条是平台接口文档的明确要求（"关系符不含目标语义 → 不生成该叶子，不用相近编码替代"）。
>
> 同理，`结尾包含`、正则匹配在这个域也不存在。

## 添加分支条件（原始 JSON，完整控制）

需要 4 步操作：
```bash
# 1. 生成新连线 ID
e10-cli workflow generate-link-id <workflowId>               # → newLinkId

# 2. 获取当前流程图 XML，在 XML 中添加新的 <mxCell edge="1"> 后保存
e10-cli workflow save-layout <workflowId> @修改后的xml文件

# 3. 保存条件规则（CLI 自动生成节点 ID，只需写条件逻辑）
e10-cli workflow save-condition @条件.json --app-id <appId>  # → conditionKey

# 4. 绑定条件到连线
e10-cli workflow set-link-condition-key <wf> <linkId> <key> <nodeId>
```

> `--app-id` 用于自动生成唯一 ID。省略时透传原始 JSON（需自己填好所有 ID）。

## 条件 JSON 格式

`childrens` 是**递归树结构**，叶子条件用 `selectType` 判断，分组条件用 `relation` + `childrens` 组合。**CLI 只自动生成 ID**（`expressionId`/`expressionBaseId`/`dataValueId`/`elementValue*Id`），其余字段必须按以下格式手写。

**完整结构**：
```json
{
  "source": 2,
  "sourceId": "连线ID",
  "workflowId": "流程ID",
  "conditionName": "条件名称",
  "linkName": "连线名称",
  "needFormfield": true,
  "readOnly": false,
  "mapBaseId": "表单ID",
  "isEdit": false,
  "isFromRuleListPage": true,
  "relation": 1,
  "childrens": [/* 叶子或分组 */]
}
```

---

### 两种节点类型

**叶子条件** — 有 `selectType`，无 `childrens`：

**分组条件** — 有 `relation` + `childrens`，无 `selectType`：

```json
{ "relation": 1, "childrens": [/* 嵌套的叶子或分组 */] }
```

> `selectType` 是数字 3 或 4。`relation`: 1=AND, 2=OR。

---

### 叶子条件：字段前缀由 fieldType 决定

> **关键**：每组字段有 `{前缀}CompareOptionLeft`、`{前缀}ValueOptionLeft`、`{前缀}TextValueLeft1` 三件套。

**Text / Textarea → `String*` 前缀**：

```json
{
  "selectType": 4,
  "formField": [{ "supportContainType": false, "total": false, "name": "字段名", "id": "fieldId", "fieldType": "Text", "groupKey": "Text" }],
  "StringValueOptionLeft": 1,
  "StringCompareOptionLeft": 5,
  "StringTextValueLeft1": "要匹配的值",
  "valueType": "0"
}
```

**Number / Money / Int → `Number*` 前缀**：

```json
{
  "selectType": 4,
  "formField": [{ "supportContainType": false, "total": false, "name": "金额", "id": "fieldId", "fieldType": "Money", "groupKey": "Money" }],
  "NumberValueOptionLeft": 1,
  "NumberCompareOptionLeft": 1,
  "NumberTextValueLeft1": "50000",
  "valueType": "1"
}
```

**Select / RadioBox / CheckBox → `Browser*` 前缀**：

```json
{
  "selectType": 4,
  "formField": [{ "supportContainType": false, "total": false, "name": "字段名", "id": "fieldId", "fieldType": "Select", "groupKey": "Select" }],
  "BrowserCompareOptionLeft": "9",
  "BrowserValueOptionLeft": "1",
  "BrowserTextValueLeft1": [{ "id": "选项valueKey", "content": "选项名" }],
  "valueType": "0"
}
```

**Date / DateTime → `Date*` 前缀**：

```json
{
  "selectType": 4,
  "formField": [{ "supportContainType": false, "total": false, "name": "日期", "id": "fieldId", "fieldType": "Date", "groupKey": "Date" }],
  "DateValueOptionLeft": 1,
  "DateCompareOptionLeft": 1,
  "DateTextValueLeft1": "2026-07-23",
  "valueType": "0"
}
```

**系统变量-字符串**（selectType=3, systemVariable="-1" 等）：

```json
{
  "selectType": 3,
  "systemVariable": "-1",
  "StringValueOptionLeft": 1,
  "StringCompareOptionLeft": 5,
  "StringTextValueLeft1": "值",
  "valueType": "0"
}
```

**系统变量-日期**（selectType=3, systemVariable="-3" 等）：

```json
{
  "selectType": 3,
  "systemVariable": "-3",
  "DateValueOptionLeft": 1,
  "DateCompareOptionLeft": 1,
  "DateTextValueLeft1": "2026-07-23",
  "valueType": "0"
}
```

---

### formField 字段映射

`formField` 需要**完整字段元数据**（不是精简格式）。直接从 `form read --app-id <appId> --out fields.json` 输出的字段对象中取，保留所有字段。

`formField` 至少包含：`id`（fieldId）、`name`（fieldName）、`fieldType`、`detail`、`detailName`、`total`、`formId`、`sourceModule`、`layoutDetail`、`selectDataSource`、`groupKey`、`supportContainType`、`newFormDesigner`、`variable`、`valueCount`、`dataTemplateId`、`detailTableId`。

> **不要精简**：碰到 `selectType: "4"` 就把 `form read` 返回的字段对象全量塞进 `formField` 数组。紧凑格式在 mulinquan 碰巧能过但不完整，eteams 直接拒绝。

---

## 查看已有条件

```bash
# 列出工作流下所有连线绑定的条件（连线名 + 条件名 + 表达式 + mapId）
e10-cli workflow condition list <workflowId> [--name <关键词>]
# 查看单个条件详情（含中文表达式），id 可用 conditionKey / mapId / conditionId
e10-cli workflow condition get <workflowId> <id>
# 删除条件（自动解绑连线），id 同 get
e10-cli workflow condition delete <workflowId> <id> [--link-id <linkId>]
```

> **getConditionList 是「按连线」查询**：请求体需回传 getConditionSet 的完整上下文
> （`sourceId`=连线 + `conditionName`=sourceName + `linkName` + `mapBaseId`/`conditionKey`
> + `exitConditionMapBrowserInfo`/`conditionMapBrowserBean`），只传简化参数会返回空列表。
> 删除时 `deleteConditions.mapIds` 需传 **mapId**（getConditionList 记录里的 mapId），不是 conditionKey。

---

### 前缀速查表

| 字段类型 | selectType | 前缀 | CompareOption 类型 | valueType |
|---------|-----------|------|--------------------|-----------|
| Text / Textarea | 4 | `String` | number | `"0"` |
| Number / Money / Int | 4 | `Number` | number | `"1"` |
| Select / RadioBox / CheckBox | 4 | `Browser` | **string** | `"0"` |
| Date / DateTime | 4 | `Date` | number | `"0"` |
| 系统变量-字符串 | 3 | `String` | number | `"0"` |
| 系统变量-日期 | 3 | `Date` | number | `"0"` |
| 系统变量-下拉 | 3 | `SysBrowser` | — | `"0"` |

---

### 比较符（CompareOption）

| 值 | 含义 |
|---|------|
| 1 | 大于 |
| 2 | 大于等于 |
| 3 | 小于 |
| 4 | 小于等于 |
| 5 | 等于 |
| 6 | 不等于 |
| 9 | 包含（文本/人员/部门）/ 属于（发起人/下拉） |
| 10 | 不包含 / 不属于 |
| 13 | 为空 |
| 14 | 不为空 |

> **易错**：`1` 是「大于」**不是**「大于等于」——`≥` 要用 `2`，`<` 用 `3`，`≤` 用 `4`。
> Number/Date 字段用 1/2/3/4/5/6（数值、日期比较）；Text 用 5/6/9/10（等于/不等于/包含/不包含）；Select/Browser 用 9/10（属于/不属于）。完整矩阵见 operator-matrix.md。

---

### 树结构示例

`合同子类型=采购类 AND 合同总金额≤50000`：

```json
{
  "source": 2,
  "sourceId": "1294902940272197632",
  "workflowId": "1294602764921430016",
  "conditionName": "采购类5w快速通道",
  "linkName": "采购类5w快速通道",
  "needFormfield": true,
  "readOnly": false,
  "mapBaseId": "1294601519433310236",
  "isEdit": false,
  "isFromRuleListPage": true,
  "relation": 1,
  "childrens": [
    {
      "selectType": 4,
      "formField": [{"supportContainType":false,"total":false,"name":"合同子类型","id":"1294601519433310217","fieldType":"Select","groupKey":"Select"}],
      "BrowserCompareOptionLeft": "9",
      "BrowserValueOptionLeft": "1",
      "BrowserTextValueLeft1": [{"id":"1294601523677945864","content":"采购类"}],
      "valueType": "0"
    },
    {
      "selectType": 4,
      "formField": [{"supportContainType":false,"total":false,"name":"合同总金额","id":"1294601519433310221","fieldType":"Money","groupKey":"Money"}],
      "NumberCompareOptionLeft": 4,
      "NumberValueOptionLeft": 1,
      "NumberTextValueLeft1": "50000",
      "valueType": "1"
    }
  ]
}
```

> `expressionId`/`expressionBaseId`/`dataValueId`/`elementValue*Id` 省略，CLI 自动生成。

---

## 参考

- [字段类型与关系符编码矩阵](operator-matrix.md) — 数字编码、字段类型矩阵、系统字段清单
