# 触发器运行时注意事项（真机验证）

本文沉淀验收 1（11 场景）真机验证得到的、与平台接口客观行为相关的经验，宿主 agent 生成 `semantic_plan` 时必须遵守。这些事实与实现语言无关（Python/Node 版同源）。

## 1. 「数据ID」paramKey 格式因触发器而异（最关键）

「按数据ID更新/引用当前数据」场景中，数据ID 字段的 paramKey **不是统一的 `{formId}.id`**，三种触发器各不相同：

| 触发器 | 数据ID 的 paramKey | 说明 |
|---|---|---|
| `TimeBatchTrigger` | `{formId}.id` | 例：`1300502645411717121.id` |
| `DateTrigger` | `dataResponse.id` | 前缀是 `dataResponse.`，不是表单 id |
| `EventFormData` | `{formId}.5` | **数据ID 是数字 `5`，不是 `.id`！** 极易踩坑 |

生成 plan 时，`mapping` 源侧引用「数据ID」必须按上表写真实 paramKey，否则 preflight 的源字段校验会报「源字段 paramKey 未在真实上下文中找到」。

> 最稳妥的做法：先跑 `workflow-context-fields` 查该触发器在当前数据源下的真实上下文，从返回里确认「数据ID」的精确 paramKey，再写入 plan，不要凭记忆猜格式。

## 2. queryFields 需包含系统字段

定时/批量/日期触发器的 `queryFields` 全选时，除了业务字段，还必须包含**平台系统字段**（数据ID / 标题 / 创建者 / 创建时间 等 9 个）。否则 `getComponentContext` 返回的上下文中**缺少「数据ID」**，导致「按数据ID更新」引用失败。

系统字段的 `id` 是英文字符串（`id`/`name`/`creator`/`createTime`/`lastUpdateTime`/`lastUpdater`/`dataStatus`/`myTag`/`publicTag`），`content` 是中文名。宿主 agent 侧无需手动列全，但需知晓：**数据ID 属于系统字段，不随业务字段自动出现**。

## 3. 动态人员引用用 `context`，不要用 `{userid}`

触发器/新建流程等节点的 `operator`（操作人）需要动态引用某字段值时，用**上下文引用**而非系统变量：

```json
{"type": "context", "paramKey": "<formId>.<人员字段id>", "label": "<字段名>"}
```

`{userid}` 这类系统变量在 `resolveFixedPeople` 阶段会被当作「固定人员」去查浏览器解析，失败即拦截报错。动态人员一律走 context 引用。

## 4. filterCondition 的 `esbAssign.wId` 必须指向「当前节点」（真机验证 2026-08-18）

`ActionEbUpdate` 等数据动作的筛选条件（filterCondition）右值走上下文引用时，条件对象里的 `esbAssign.wId` 字段**必须指向「当前节点」**（filterInput 所属的数据动作节点 id），**不能指向上游 event 节点**。

- 设计器打开「动态赋值」对话框时，用 `esbAssign.wId` 在 `orginFlowDatas` 里定位当前组件；指向 event 节点 → 定位不到 → 右侧「暂无数据」（EmptyView，不可编辑/不可选）。
- `value.source` / `config.comId` 仍指向 event 节点（公式来源，不变）；只有 `esbAssign.wId` 单独用当前节点 id。
- 判断口径：读回后 `esbAssign.wId` 应等于该 ActionEbAdd/Update/Delete 节点的 `id`，不等于 `event.id`。

## 4b. 同类问题全量修复：mapping / updateId / basisValue / 明细依据值下级 / updateFieldCondition / requestName 的上下文公式也要 `esbAssign.wId`（真机验证 2026-08-18）

第 4 节最初只修了 `filterCondition`（`buildFilterInput` 路径）。验收 1 重跑时发现：**ActionEbAdd/Update 的字段映射（mapping）、按数据 ID 更新的 `updateId`、批量新增依据值 `basisValueFormula`/`setting.bassisValue`、明细映射的 type=10 依据值下级、`updateFieldCondition` 的 assign、ApproveCreate 的 `requestName`** —— 这些位置的上下文公式（type 3/8/10）**同样必须带 `esbAssign.wId` 指向当前数据动作节点**，否则设计器打开「动态赋值」会把该条显示为「【组件名（已删除）】」（组件未删除，只是 wId 缺失导致前端定位不到当前组件）。

- 修复（2026-08-18）：`formula_service.ts` 新增 `attachEsbAssign(bean, meta, fallbackSource)`，在 `buildSettingEntry` 的 context 分支（含提前 return 的 assignFlatEsbChild 子表路径）与统一 return 前、`workflow_compiler.ts` 的 `_updateId`/`_basisValueFormula`/`handleBasisValue`/`requestName`、`action_eb_update_compiler.ts` 的 `buildUpdateFieldCondition` 处统一调用。wId 取值顺序与 filterInput 一致：`meta._upstream_node_id`（convertNode 设的当前节点 id）→ 公式 `source` → `meta._upstream_w_id` → 时间戳前缀。
- 固定值（type=1）不加 esbAssign（设计器 fixvalue 不需要定位当前组件）。
- 真机回归：验收 1 全 12 场景 readBack 通过；抽查 S1（basisValue+主表映射+type10 下级）/S2（filterInput+主表映射+明细 type10）/S10（updateId）/S11（ApproveCreate formData）/S12（updateId+累加 mapping）—— 所有 esbAssign.wId == 当前数据动作节点 id，无一处指向 event。
- 新增/维护组件时，凡生成上下文公式的地方都要过一遍 `attachEsbAssign`；`references/components/` 下各组件契约 md 与 SKILL.md「esbAssign.wId」条目已同步。
- 关联字段的身份元数据是另一条独立约束：筛选字段必须保留真实 `sformId`；`refObjId` 只在对应平台 DTO 要求时保留，不能把它当作所有关联字段的统一必填项。`esbAssign.wId` 正确只能保证动态右值能定位当前动作节点；缺少 `sformId` 仍会让设计器把左侧仍存在的字段显示成“已删除”。
- Workflow 左值还必须带目标表默认布局 `formInfo.layoutId`。`formInfo.formId` 只能填目标表版本 ID，顶层 `sformId` 要填 `workflowPath.formIds` 对应的流程表单对象 ID；Workflow 使用原始数字 `fieldName`、`fieldType:"String"`、空 `module`/`originBrowserType`，不能加 `field_` 前缀或把 `Workflow` 当存储类型。不能把目标表版本 ID当作关联对象；反查不到真实对象时停止生成并报错。

