# 人员状态变更

组件类型：`AlterPersonStatus`。先运行 `component-describe AlterPersonStatus`。

## 何时使用

用于把已有人员批量设为在职或离职。它只改变人员账号状态；不要用它修改人员资料、入职信息或人员类型。

## 生成前查询

固定人员时使用 `recipient-search` 取得每一位目标人员和操作人的当前租户 Browser 原对象；动态人员时使用真实人员字段上下文或当前用户系统变量。

## 业务边界

- `personList` 支持动态人员 FormulaBean 数组或固定人员 Browser 原对象数组；`operators` 支持动态人员 FormulaBean 或固定人员 Browser 原对象。不能把裸人员 ID 当作固定 Browser 对象。
- `userStatus` 仅为 `1`（在职）或 `2`（离职）。
- 变更离职状态会影响真实人员可用性；仅在用户明确要求时生成。

## 语义计划形状

```json
{
  "type": "AlterPersonStatus",
  "params": {
    "personList": [{"id": "<真实人员ID>", "name": "<真实姓名>"}],
    "userStatus": "2",
    "operators": {"id": "<真实人员ID>", "name": "<真实姓名>"}
  }
}
```
