# 表单数据触发（`EventFormData`）

## 何时使用

在 e-builder 表单新增、更新或删除数据后触发动作流。

## 先查询

查询触发表单及允许作为触发字段的真实字段。

## 不可猜测

触发时机、表单和字段以当前租户返回为准；不要把流程表单误当 e-builder 独立表单。

多条数据变动的后续触发方式通过 `triggerType` 支持：`sequence`（依次）、`merge`（合并）、`parallel`（并行）。

## 最小计划

`dataSource` 与 `triggerTimes`；按需求补充触发字段。
