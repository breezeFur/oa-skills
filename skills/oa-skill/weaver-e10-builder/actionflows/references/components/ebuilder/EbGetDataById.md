# 获取表单数据详情（`EbGetDataById`）

## 何时使用

按数据 ID 获取指定 e-builder 表单的一条详情，供后续动作引用。

## 先查询

查询目标表单和读取操作人。

## 不可猜测

`dataId` 必须是实际数据 ID 或其真实上下文；`person` 只是 `operatorId` 的兼容别名。

## 最小计划

`targetForm`、`dataId`、`operatorId`（或 `person`）。`dataId` 和 `checkRight` 都支持固定值、上下文、系统变量、变量、常量和函数/公式；`operatorId` 支持固定人员 Browser 对象或动态人员公式。
