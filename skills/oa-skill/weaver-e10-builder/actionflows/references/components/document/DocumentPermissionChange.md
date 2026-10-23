# 文档权限变更（`DocumentPermissionChange`）

## 何时使用

对文档执行赋权或收权。

## 先查询

查询文档及平台返回的权限对象。

## 不可猜测

固定赋权只能传真实 `SharePermissionBean`；动态赋权传真实上下文公式。

## 最小计划

`docId`、`assignType`，以及对应的 `permissionList` 或 `permissionFormula`。
