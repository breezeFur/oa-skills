# 存为版本（`ActionEbSaveVersion`）

## 何时使用

为已启用版本能力的 e-builder 数据创建大版本或小版本。

## 先查询

查询目标表单、操作人及待版本化的数据 ID 来源。

## 不可猜测

不确认目标表已启用版本时不生成；不可用表单 ID 替代数据 ID。

## 最小计划

`targetForm`、`person`、`updateId`；版本策略按需求指定。
