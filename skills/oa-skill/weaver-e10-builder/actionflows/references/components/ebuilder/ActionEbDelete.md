# 删除表单数据（`ActionEbDelete`）

## 何时使用

按筛选条件删除 e-builder 表单数据；还原已删除数据使用 `ActionEbRecover`。

## 先查询

查询目标表单、条件字段和操作人。

## 不可猜测

筛选条件必须引用目标表真实字段；不能把名称或非本次上下文的字段键写入条件。

## 最小计划

`targetForm`、`person`、`filterCondition`。

## filterCondition 格式

**以 `references/condition_rules.md` 为准**：`{"field":{"id":"<目标字段id>","label":"<字段名>"},"operator":"eq","right":{...}}`。`field` 是 `{id,label}` 对象、`operator` 用英文操作符（`eq/neq/gt/lt/gte/lte/contains/uncontains/empty/nempty`）、右值键用 `right`。**勿用**废弃的 `value` 别名 / `=` / 裸字符串 `field`，否则编译报「左侧字段 id 不在目标表单实时字段列表中」。

当条件左字段是「关联流程」Workflow 时，必须由 Skill 根据实时字段元数据和 `workflowPath.formIds` 反查真实流程表单对象；编译后的左值使用原始数字 `fieldName`、`fieldType:"String"`、顶层 `sformId` 和 `formInfo.formId/layoutId`，不得套用普通业务字段的 `field_` 前缀或把目标表单版本 ID写成 `sformId`。
