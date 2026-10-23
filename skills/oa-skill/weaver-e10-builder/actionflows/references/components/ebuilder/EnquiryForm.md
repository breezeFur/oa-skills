# 查询表单数据（`EnquiryForm`）

## 何时使用

查询 e-builder 表单列表或分组统计；按单条 ID 读取使用 `EbGetDataById`。

## 先查询

查询数据源、全部字段、筛选字段、输出字段和查询操作人。

## 不可猜测

筛选、排序、分组和输出字段都必须来自当前数据源；统计结果应作为后续节点上下文使用。

## 最小计划

`dataSource`、`person`；按 `opType` 补充查询字段和筛选条件。未明确限制 `queryFields` 时不要传它（或传空数组），CLI 会默认全选主表和系统字段，包含“数据ID”。未指定 `filter` 时，CLI 会生成平台必填的中性条件“数据ID不为空”，不改变业务筛选范围；只有明确指定 `filter` 时才使用业务条件。

## 动态分页和条件

- `formPageNo`、`formPageSize` 支持固定值、上下文、系统变量、变量、常量和函数/公式。
- 需要由上游计算整段查询条件时使用 `conditionFormula`；它会写为 `conditionType:"assign"`，此时不得同时传 `filter`。
- 普通业务筛选继续使用 `filter`，两种条件模式不能混用。

## 分组/汇总查询

`opType:"groupFields"` 是原生“分组/汇总”能力，不需要规则集或外部计算组件：

- `groupFields` 是分组维度：`[{"field":"<真实字段id>"}]`；没有分组维度时传空数组。
- `groupMessage` 是汇总值：`[{"field":"<真实字段id>","aggregator":"SUM"}]`。
- 可用聚合方式：`SUM`、`MIN`、`AVG`、`MAX`、`COUNT`、`DISTINCTCOUNT`。其中 `SUM`/`AVG` 只用于数值字段。
- 汇总输出字段名由平台固定为 `s_sum_<字段id>`、`s_min_<字段id>`、`s_avg_<字段id>`、`s_max_<字段id>`、`s_count_<字段id>`、`s_distinctcount_<字段id>`；后续节点引用它时使用 `kind:"query_result"`、`fieldId:"s_sum_<字段id>"`、`source:"<查询动作ref>"`、`index:0`。

示例：汇总“收款金额”并让后续节点取第一条汇总结果：

```json
{
  "type": "EnquiryForm",
  "ref": "收款汇总",
  "params": {
    "dataSource": {"groupId":"<应用id>","id":"<合同收款表id>","text":"合同收款表"},
    "person": {"type":"role"},
    "opType": "groupFields",
    "filter": {"field":{"id":"<关联项目字段id>","label":"关联项目"},"operator":"eq","right":{"kind":"context","paramKey":"<当前表单>.关联项目"}},
    "groupFields": [],
    "groupMessage": [{"field":"<收款金额字段id>","aggregator":"SUM"}]
  }
}
```

## 批量新增主表字段引用查询结果（2026-08-27 真机钉死）

**结论：当需求确实需要反查时，EnquiryForm 查询结果可以赋给 `batchInsert` 主表字段（标量），但只限"单值反查"场景**。它不是任何表单新增动作的默认前置节点。手动创建成功样本：`references/examples/enquiry-form-batch-insert-scene2.json`（ApproveTrigger → EnquiryForm → ActionEbAdd(batchInsert) → Output）。样例中的 `opText` 是历史平台序列化快照，不是生成模板；生成时只依据语义 plan 和实时字段元数据，尤其不要复制其中 Workflow 左值的旧 `field_`/`Workflow` 组合。

关键结构（与旧结论不同，已修正）：

1. **EnquiryForm 节点（首动作）**：
   - `dataSource.type = "LOGIC"`、`dataSource.groupId = "weaver-ebuilder-form-service"`（不是表单所属应用 id！）
   - `queryFields[].id = "id"`（简写，不是 `{表id}[].id`）；`fieldGroup = { name: 表名, id: 表id }`
   - 筛选：`filterInput.datas[].conditions.value` 用流程上下文 type=3（`ApprovalData.{wfId}.requestId`）
   - 首动作 **不需要 sources**（undefined），ActionEbAdd 的 sources 指向 EnquiryForm 节点 wId

2. **主表字段引用查询结果（项目名称 5453）**：
   - assign：`type=3`，`value = "FormData.{查询表id}[{positionId}].id"`（**数组下标用 positionId 而非 `[]`**）
   - `config.comType = "EnquiryForm"`、`config.comId = EnquiryForm 节点 id`、`config.paramKey = "{查询表id}[].id"`（paramKey 保持 `[]` 数组标记）
   - **childs 必须带固定值取下标**：`[{ type: "1", value: "0", position: "{positionId}" }]`（value=0 取第一条）
   - `frontId` = 查询结果字段的真实 `fieldId`（不能使用公式对象临时 id）；前端用它定位查询节点输出字段，否则会回显为“数据源查询（已删除）”并标红。

3. 其余明细字段仍用依据值下级 type=10 直连（paramKey `{wfId}.{明细表id}[].{子字段id}`，source=event 节点 id）。

4. 挂接注意：EnquiryForm 作为**流程首动作**保存成功；此前「两个起始执行组件」报错疑与给首动作补 sources 或 dataSource.type 用 FORM 有关，**勿给首动作补 sources**。

计划中引用该结果时，必须显式写 `kind:"query_result"`，不能把它写成普通流程字段。例如：

```json
{
  "mapping": {
    "<查询表单id>[].id": {
      "target": "<目标字段id>",
      "kind": "query_result",
      "source": "<EnquiryForm动作ref>",
      "formId": "<查询表单id>",
      "fieldId": "id",
      "label": "数据ID",
      "index": 0
    }
  }
}
```

其中查询动作需显式声明例如 `{"type":"EnquiryForm","ref":"项目查询","params":{...}}`，后续写 `source:"项目查询"`。编译器会将该语义 `ref` 替换为实际节点 ID，并生成保存所需的 `childs` 下标公式；禁止使用或猜测平台节点 ID。

## 关键边界：只支持"单值反查"，不支持"逐行明细反查"（2026-08-27 用户确认）

**适用条件（场景2 成立的唯一前提）**：EnquiryForm 的筛选条件用的是**流程级唯一值**（如 `关联流程 eq requestId`），业务上一个流程只对应一条查询结果 → 取第一条（childs value=0）就是唯一那条，赋值主表字段正确。

**禁止场景（多条结果）**：如果筛选条件用的是**明细行 id/明细字段**（如"按任务编号反查"），查询结果会有多条，且**数据源返回结果的顺序与流程明细表的行顺序不保证一致**（第 1 行明细对应的结果可能排在返回结果第 5 行）。此时：
- 无法用"取第一条"对应到正确的明细行；
- 无法把查询结果作为依据值（basisValue）传给下方组件——明细字段值仍需以**流程明细表本身作为依据值**（type=10 直连）；
- **转化规则必须逐行做明细字段转化，多条结果做不到 → 该场景明确拒绝，不硬凑 EnquiryForm**。

一句话决策：**EnquiryForm 反查只能给"与明细行无关的全局单值"（主表字段，按流程级唯一条件查）；凡需"按每行明细反查对应值"的，直接拒绝并告知用户**。

## 曾经的错误结论（已推翻，勿沿用）

- ~~EnquiryForm 输出是列表数组不能赋主表标量~~ → 实际通过 childs 固定值取下标（value=0 第一条）实现（仅限单值反查）。
- ~~批量新增场景不要用 EnquiryForm 反查~~ → 单值反查是标准做法，见上；逐行反查仍不可行。
