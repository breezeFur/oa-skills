# 流程触发（`ApproveTrigger`）

## 同一流程的多条触发规则

平台的“动作执行节点/出口”窗口可为同一个流程添加多行规则；不要把它误拆成多个动作流。计划用 `triggerRules` 表达：

```json
{
  "workflowPath": {"id":"<流程id>","name":"<流程名>"},
  "triggerRules": [
    {"triggerTiming":"leave","approveNode":{"id":"<发起节点id>","name":"发起节点"}},
    {"triggerTiming":"arrive","nodeTime":"2","approveNode":{"id":"<发起节点id>","name":"发起节点"}},
    {"triggerTiming":"workflow_completed","approveNode":{"id":"<结束节点id>","name":"结束节点"}}
  ]
}
```

CLI 会逐条校验真实节点/出口及其允许的执行时间，并写入同一流程的 `singleApproveConfigs[workflowId]` 数组。未传 `triggerRules` 时，才使用原来的单条 `triggerTiming` 写法。

## 活动版本

动作执行节点/出口窗口里的“活动版本”对应触发规则中 `nodeOrLinkName[0].versionId`。可在计划中传 `workflowVersionId` 指定真实版本 ID：

```json
{
  "workflowPath": {"id":"<流程id>","name":"<流程名>"},
  "workflowVersionId": "<流程节点浏览接口返回的真实versionId>",
  "triggerTiming": "submitted",
  "approveNode": {"id":"<真实发起节点id>","name":"发起节点"}
}
```

`workflowVersionId` 只能使用流程节点浏览接口返回的真实 `versionId`，CLI 会按流程、节点和版本一起校验；不传时沿用真实 `approveNode` 携带的版本。不会猜测或生成版本 ID。出口规则同样把真实版本写入 `nodeOrLinkName[0]`。

## 多时机触发不同动作时，先按触发上下文分支

多条规则触发的仍是**同一张动作流画布**，因此不能把“新增 / 删除 / 更新”三个动作直接串在主链上。应在事件后的第一个节点放 `Condition`，用流程触发器实时输出的字段路由：

- `triggerType`：`pre`（节点前）、`after`（节点后）、`link`（出口）等；
- `executeTime`：例如 `2` 表示返回到达；
- `triggerNodeOrLinkId`：实际触发的节点或出口 ID。

例如“发起节点离开新增、返回到达删除、结束节点正向到达更新”写成三条互斥分支：

```text
triggerNodeOrLinkId = 发起节点 AND triggerType = after AND executeTime = 1  -> 新建
triggerNodeOrLinkId = 发起节点 AND triggerType = pre   AND executeTime = 2  -> 删除
triggerNodeOrLinkId = 结束节点 AND triggerType = pre   AND executeTime = 1  -> 更新
```

以上三个字段必须从当前流程触发器的 `getComponentContext` 返回结果取真实 `paramKey`，不要手写成业务表单字段。

## 何时使用

由流程提交、审批、结束等时机触发动作流。

## 先查询

查询真实流程、节点和当前时机的 `workflow-context-fields`。

## 不可猜测

后续动态引用只使用本次返回的 `paramKey`；多流程触发按组件契约提供真实列表。

## 最小计划

`workflowPath`、`triggerTiming`；节点型时机提供真实 `approveNode`，出口型时机提供真实 `approveLink`。

## 触发时机

plan 统一使用：`arrive`（节点前/到达）、`submitted`（流程提交）、`approve_passed`（审批通过）、`workflow_completed`（流程结束）、`leave`、`link`、`delete`、`save`、`revert`、`pause`、`cancel`。中文界面名称可输入，CLI 会归一为上述值后再查询并校验对应的真实流程节点；不能按“第一个节点”猜测时机。

## 类型联动：可选节点/出口与执行时间

| `triggerTiming` | 可选对象 | `nodeTime` |
|---|---|---|
| `submitted` | 仅发起节点（nodeType=0） | 仅正向到达（1） |
| `approve_passed` | 审批/中间节点（1/2/5） | 不使用 |
| `workflow_completed` | 仅结束节点（3） | 仅正向到达（1） |
| `arrive` | 当前流程真实节点（0/1/2/3/5） | 结束节点可选 1/2/3/4/5/6；其他节点 1/2/3/4/6 |
| `leave` | 当前流程真实节点（0/1/2/3/5） | 1/2/3/6 |
| `link` | 仅当前流程真实出口 `approveLink` | 不使用 |
| `pause` | 发起/审批/中间节点（0/1/2/5） | 1/2 |
| `cancel` | 当前流程真实节点（0/1/2/3/5） | 1/2 |
| `delete` / `save` / `revert` | 当前流程真实节点（0/1/2/3/5） | 不使用 |

出口不能使用 `approveNode`，也不自动选择“第一条出口”；需求未指定出口时必须先查并追问。

## 执行时间（节点前 / 节点后）

节点型触发可传 `nodeTime`，其值和设计器下拉框一致：`1` 正向流转到达、`2` 返回到达、`3` 强制收回到达、`4` 撤回到达、`5` 强制结束到达、`6` 干预到达。

例如，要在某节点**返回到达**时触发，使用真实节点和 `nodeTime:"2"`：

```json
{"workflowPath":{"id":"<流程ID>","name":"<流程名>"},"triggerTiming":"arrive","approveNode":{"id":"<真实节点ID>","nodeType":1},"nodeTime":"2"}
```

`revert` 是“流程还原时”，与节点执行时间中的“返回到达”不是同一事件。
