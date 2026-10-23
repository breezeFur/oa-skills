# 共享流程（`ApproveShareEntry`）

## 何时使用

将流程实例共享给指定人员。

## 先查询

查询实例、共享对象和操作人。

## 不可猜测

当前仅支持人员共享；共享对象必须是 Browser 原对象。

## 最小计划

`requestIds`、`shareType: "user"`、`shareEntities`、`perator`。
