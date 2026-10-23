# 干预流程（`ApproveIntervention`）

## 何时使用

将流程干预流转到指定节点并指定处理人。

## 先查询

查询真实流程、节点、实例、操作人和节点处理人。

## 不可猜测

`workflowId`、`submitToNodeId`、处理人均必须是当前租户 Browser 对象。

## 最小计划

`workflowId`、`submitToNodeId`、`requestId`、`employeeId`、`interventionReceiverIds`。
