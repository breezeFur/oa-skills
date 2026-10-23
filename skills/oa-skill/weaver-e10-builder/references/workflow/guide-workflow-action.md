# 流程动作流指南

> 流程基础（建流程、节点、连线、审批人）见 `workflow/guide-workflow.md`，分支条件见 `workflow/guide-workflow-condition.md`。本指南专讲**节点提交事件**和**跨表单动作流**（本表数据 → 目标表 新增/更新/删除 记录）。
>
> **动作流新建走 `e10-cli actionflow generate`，已有动作流修改走 `e10-cli actionflow update`**。新建是语义 plan → 编译 → preflight → 保存并启用 → 正式回读；修改是精确 appId → 读取正式设计 → 备份 → 按原 ID 保留式修改 → `saveDesign` → 正式回读。`ApproveTrigger` 自带流程节点触发绑定，不走 pathdef/addaction。详见 `actionflows/SKILL.md` + `e10-cli actionflow component-describe <type>`。`e10-cli workflow action` 仅作动作流**管理**（`list-node`/`clear-node` 查清节点绑定、`delete`/`disable`/`batch-delete` 禁用删除动作流 app）。

## 节点提交事件（字段更新）

节点提交/到达时自动更新本表单字段值（actionType=0），如「审批状态置为审批中」。

> CLI 接受简化 JSON，内部自动构造 `saveAddActionList` 正确 payload（`targetValue`/`firstValue:"custom"`/`customValue`/`actionType:0`/`triggerType:"pre"` 等）。也支持直接传完整 `data:[]` 结构（高级用法）——**传入的 `data:[]` 行会自动归一化**，把 `action list-node` 的读回结果原样回传是安全的。
>
> **合并语义**：写入前先读回节点已有动作并归一化，再追加新动作写回——不覆盖已有动作。可与节点上的 type2 动作流安全混用同一节点。若节点已被写坏（读动作恒 500），CLI 会明确提示用 `delete-node` 删节点重建（API 无法修复）。
>
> **fieldId 会校验**：简化 JSON 的 `fieldId` 必须是流程表单里真实存在的字段，CLI 写入前反查表单字段校验，无效会报错并列出可用字段。**切勿用占位 fieldId**（如 `"1"`）——无效 fieldId 会被服务端存成空字段映射，之后任何合并写回都会把节点写坏（读恒 500，只能 delete-node 重建）。

**命令**：
```bash
e10-cli workflow save-action @action.json
```
> **只接 JSON 一个参数**：`workflowId` / `nodeId` 写在 JSON 内部，不是位置参数。写成 `save-action <wf> <node> @file` 会报错。

### action.json 格式（常量赋值）

```json
{
  "workflowId": "1296243932023734272",
  "nodeId":     "1296243932023734278",
  "nodeName":   "上级审批",
  "fieldId":    "1296243579896791071",
  "fieldName":  "审批状态",
  "value":      "1296243644242280449"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| workflowId | 是 | 流程 ID |
| nodeId | 是 | 节点 ID（即 `objId`） |
| nodeName | 否 | 节点显示名（默认"节点"） |
| fieldId | 是 | 要更新的目标字段 fieldId |
| fieldName | 否 | 字段显示名（用于 `actionName` 展示） |
| value | 是 | 常量值。Text/Number 字段用实际值；Select 用 option 的 valueKey |
| trigger | 否 | 触发时机，默认 `"pre"`（到达节点时）；`leave` 离开 / `back-arrive` 退回到达 |

---

## 跨表单动作流（本表数据 → 目标表 新增/更新/删除 记录）

跨表单动作流的**生成**统一走 `e10-cli actionflow generate`：写一份语义 plan（`event` + `actions`），CLI 编译、preflight、保存并启用、正式回读，返回设计器链接。组件参数、映射、条件的权威是 `e10-cli actionflow component-describe <type>`，参考 `actionflows/references/components/` 下对应组件 md。下面是平台机制要点，写 plan 时按此组织。

除 e-builder/流程数据动作外，动作流还支持 HTTP/HTTPS 接口调用、DML 数仓 SQL/存储过程、自定义事件、内置 MQ 监听/发送、消息、文档、人员、会议和日程等组件。HTTP 必须先按“连接器 → 连接信息 → 接口 → 接口详情”读取当前环境对象；请求参数通过接口详情真实 `table`/`paramKey` 配置 `inputParams`，不要猜测或重建 `request.tables`。DML 的数据源连接必须先用 `e10-cli actionflow datasource-list` 查询，SQL 占位符与 `fieldSet` 必须一致；详细约束分别见 `actionflows/references/components/http/Http.md` 和 `actionflows/references/components/database/DMLExecute.md`。

已有动作流的局部变更不要重新生成新应用；先用 `read-design --out` 保存正式设计，再按 `actionflows/SKILL.md` 的 `update` 计划格式提交显式 `operations`。更新器会自动备份原设计并保留未声明内容，不能按名称选择目标，也不会在保存/回读失败时自动回滚或删除目标。更新计划中的节点 ID 必须来自这次正式回读；保存新版时平台可能重分配动作/出口节点 ID，CLI 会按新版版本列表定位新场景并按动作树结构回读校验，不能把新 ID 变化误判为失败。更新时触发器 `event` 必须保持原样，不能修改触发类型、触发表单、触发时机或其他触发器参数；如果需求要变更触发器，必须改为新建动作流，CLI 会在检查/保存前明确拒绝。正常更新通过后调用 `saveDesign` 时固定使用 `saveNewVersion:true`，保存为该动作流的新版本。

### 平台机制要点

**目标表字段映射**：plan 的 `mapping` 是 `{源字段 paramKey: 目标字段 ID}`。目标字段 ID 支持 `+`/`-` 前缀做加减运算（赋值不加前缀、`+`累加、`-`扣减）。源字段用本次 `actionflow workflow-context-fields` 返回的原始 `paramKey`，不写死 `FormData.*`/`ApprovalData.*` 路径（编译器自动判定）。

**明细表映射（明细→明细）**：`ActionEbAdd` 的 `insert`/`batchInsert` 支持源明细表逐行写入目标明细表。同一目标明细表的映射须来自同一张源明细表（作为该表「依据值」basisValue）。明细目标字段不支持 `+`/`-` 前缀。**明细 update/delete**（含 basisValue/rowId 行匹配/updateAdd、requestId 定位）走 `ActionEbUpdate`/`ActionEbDelete` 契约的 `filterCondition`（动态右值引用 requestId），`component-describe ActionEbUpdate` 看 detail + requestId 定位参数。

**更新定位方式**：`ActionEbUpdate` 的 `opType`：`id`（按数据ID更新，配 EBuilder 关联字段其值=目标记录数据ID）/ `updateData`+`filterInput`（按「目标字段=源字段值」匹配，推荐）/ `fieldUpdate`（按字段匹配，保存后右侧条件会被清空，不可用）。匹配字段不要选 `*_name`/「名称」显示字段（标签文本非真值）。

**常量值**：plan 里目标字段可用固定值（constants）而非映射字段；公式计算（加减乘除多字段）用 `formula`。mapping/constants/formula 可混合。详见 `component-describe ActionEbAdd/ActionEbUpdate`。

---

## 流程数据写入台账（数据来源落点）

**场景**：流程发起时写入目标台账、归档/退回时更新/删除台账记录（如"流程数据写入项目台账"，发起写入、归档更新、退回删除）。

**核心前提：目标台账必须建「数据来源」Flow 字段**（浏览-流程，`--sform-id` 指向流程绑定的表单 objId）。它存的是**流程实例 ID（requestId）**——add 时写入它，update/delete 靠它定位是哪次流程创建的记录，点击还能跳回流程。

```bash
# 台账建「数据来源」Flow 字段（只读，来源=项目立项流程）
e10-cli form add-field <台账objId> <appId> "数据来源" Flow --sform-id <流程表单objId>
```

**① add（发起写入）**：plan 里把流程实例 ID（requestId 系统变量）写进台账「数据来源」字段，其余字段按 mapping 映射。

**② update/delete（归档更新/退回删除）**：定位条件"**台账.数据来源 = 当前流程 requestId**"。`filterCondition` 动态右值引用 requestId，编译器自动判定为 `ApprovalData` 流程数据——`paramKey` 必须用本次 `actionflow workflow-context-fields` 返回的原始键，不要写死路径。示例 plan 结构：

```json
{
  "event": {"type":"ApproveTrigger","params":{"workflowPath":{"id":"<流程id>"},"triggerTiming":"workflow_completed"}},
  "actions":[
    {"type":"ActionEbUpdate","params":{
      "targetForm":{"groupId":"<appId>","id":"<台账objId>"},
      "person":{"id":"<人员id>","name":"<姓名>"},
      "opType":"updateData",
      "filterCondition":{"field":{"id":"<台账数据来源字段ID>","label":"<数据来源字段名>"},"operator":"eq","right":{"type":"context","paramKey":"<workflow-context-fields 返回的流程ID paramKey>","label":"流程ID"}},
      "mapping":{"<源paramKey>":"<目标字段ID>"}
    }}
  ]
}
```

> `filterCondition` 格式**以 `actionflows/references/condition_rules.md` 为准**：`field` 必须为 `{id,label}` 对象、`operator` 用英文操作符（`eq/neq/gt/lt/gte/lte/contains/uncontains/empty/nempty`，`empty/nempty` 无右值）、右值键必须为 `right`。`value` 别名、`=`、裸字符串 `field`、数组根节点和 `relationship:"1|0"` 都会在编译前被拒绝。需求含条件/筛选时先翻 condition_rules.md 再下笔。

> **关联流程左值特别注意**：不要因为字段 ID 是数字就套用普通 e-builder 的 `field_<id>`。`Workflow` 必须使用原始数字 `fieldName`、`fieldType:"String"`、空 `module`/`originBrowserType`，`formInfo.formId/layoutId`，顶层 `sformId` 和仅含 `fieldId` 的 `config`；`sformId` 从 `workflowPath.formIds` 反查流程表单对象，不能用目标表单版本 ID代替。

> 也可直接给 `actionflow generate` 下自然语言 plan（"流程归档时按数据来源更新台账，项目状态置为立项"），由组件契约承载。`generate` 默认保存并启用设计（saveDesign saveAndStart=true，正式生效），返回 appId + 设计器链接，event 节点已含流程节点触发绑定。仅 `mode:"stash"` 时走暂存（需设计器手动发布）。

**③ add 回写 dataId（源表存台账记录 ID）**：若后续 update/delete 想用"源表字段 = 台账 dataId"定位，`actionflow workflow-context-fields` 提供"回写数据ID对应字段"候选查询。

---

## 关联 EBuilder 更新目标表数据（跨表更新）

**场景**：表A（带流程）通过 EBuilder 关联字段指向表B，流程到节点时动作流更新表B的目标记录字段。

**机制**：表A 的 EBuilder 关联字段的值 = 表B 记录的数据ID。plan 里 `ActionEbUpdate` 的 `opType=id`（按数据ID更新）+ `filterCondition` 用表A的 EBuilder 关联字段 → 直接用关联值定位表B记录，无需字段值匹配。

### 建两张表

表B「客户台账表」（被更新）：客户名称(Text)、最后拜访日期(Date)、累计拜访金额(Money)
```json
[
  {"componentKey":"Text","fieldName":"客户名称"},
  {"componentKey":"Date","fieldName":"最后拜访日期"},
  {"componentKey":"Money","fieldName":"累计拜访金额"}
]
```

表A「拜访登记表」（带流程）：拜访日期(Date)、拜访金额(Money)、客户关联(EBuilder→表B)
```json
[
  {"componentKey":"Date","fieldName":"拜访日期"},
  {"componentKey":"Money","fieldName":"拜访金额"},
  {"componentKey":"EBuilder","fieldName":"客户关联","sformId":"<表B objId>","dataTitle":"客户名称"}
]
```
> EBuilder 字段：`sformId`=目标表 objId，`dataTitle`=目标表显示字段（填字段名或 fieldId，CLI 自动解析）。

写 plan 时 mapping 目标ID 不加前缀=**直接赋值**（源值原样写入）；加 `+`=累加，`-`=扣减。直接赋值时按目标字段类型（日期/金额/文本等）自动匹配。

---

## 条件性动作流（同一节点按条件走不同动作）

一个节点可挂**多个动作流，各自带触发条件**——提交时只有条件命中的动作才执行。典型场景「合同变更」：变更类型=续期 → 插入台账；变更/终止 → 更新+插入。

在 plan 里用 `Condition` 组件（逻辑分支）表达条件，或多个 `ActionEb*` 配 `filterCondition`。条件规则语法见 `actionflows/references/condition_rules.md`。`actionflow component-describe Condition` 看条件组件契约。

> **验证**：`e10-cli workflow action list-node <wf> <node>` 会标注 `⚠️条件` 的动作为带规则动作。条件内容在流程设计器节点 → 提交事件 → 动作的规则图标里查看。

---

## 动作流管理

生成（`actionflow generate`）之后的查/清/删/禁用：

```bash
e10-cli workflow action list-node <wf> <node>    # 列节点绑定的动作（type0 常量赋值 + type2 动作流）
e10-cli workflow action clear-node <wf> <node>  # 清空节点动作绑定（deleteAddAction，不删动作流实体）
e10-cli workflow action disable <appId> <name>  # 禁用动作流（禁用后可删除）
e10-cli workflow action delete <appId> <name>   # 删除动作流（自动先禁用再 batchAddRecycle）
e10-cli workflow action batch-delete @list.json  # 批量删除（每项 {id,name}）
```

> **clear-node vs delete**：`clear-node` 只解绑节点（动作流实体仍在）；`delete` 删动作流 app（节点残留悬空引用，前端显示「被删除」，平台无按动作流反查节点接口，逐个 `clear-node` 清理）。
>
> **list-node 显示**：`type0 常量赋值`（本表字段赋值，`save-action` 写的）/ `type2 动作流`（`actionflow generate` 生成的，带 appId）。

---

## 角色管理

```bash
e10-cli role list                              # 查看角色树
e10-cli role create <name> --parent <id> --code <code> --remark <text>
e10-cli role delete <ids...>                   # 删除角色（可多个）
e10-cli role add-member <roleId> <keyword>     # 搜索人员添加到角色
```
