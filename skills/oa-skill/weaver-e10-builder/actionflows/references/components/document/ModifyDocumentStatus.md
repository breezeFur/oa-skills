# 更新状态（`ModifyDocumentStatus`）

## 何时使用

更新文档状态。

## 先查询

查询当前租户文档状态与目标文档。

## 不可猜测

状态只能取 `document-statuses` 返回值；文档固定值必须是真实 Browser 对象。

## 最小计划

`documents`、`docStatus`。
