# 抄送批注流程（`ApproveManualCC`）

## 何时使用

向指定人员抄送流程并允许批注意见。

## 先查询

查询实例和人员。

## 不可猜测

当前仅支持人员接收方，不把部门或角色伪装为人员。

## 最小计划

`requestId`、`receiveTypes: "user"`、`receiveIds`、`initiator`。
