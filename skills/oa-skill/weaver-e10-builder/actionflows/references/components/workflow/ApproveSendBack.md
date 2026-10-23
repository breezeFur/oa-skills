# 退回流程（`ApproveSendBack`）

## 何时使用

将流程退回至一个指定节点。

## 先查询

查询流程定义、实例、真实退回节点和操作人。

## 不可猜测

退回节点必须属于该流程；不能以节点名称或猜测 ID 代替。

## 最小计划

`workflowPath`、`requestId`、`rejectToNodeId`、`operator`。
