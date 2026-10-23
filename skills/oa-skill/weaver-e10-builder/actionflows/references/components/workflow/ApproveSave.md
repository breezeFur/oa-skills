# 保存流程（`ApproveSave`）

## 何时使用

保存已有流程及其表单数据，不执行审批提交。

## 先查询

查询流程定义、实例上下文和操作人。

## 不可猜测

实例 ID 与流程定义不可互换；表单赋值的目标字段必须来自真实流程表单。

## 最小计划

`workflowPath`、`requestId`、`operator`；按需求补充赋值。`requestId`、`requestName`、`remark`、`odocId`、`dataId` 和 `onlySaveForm` 都支持统一动态赋值。
