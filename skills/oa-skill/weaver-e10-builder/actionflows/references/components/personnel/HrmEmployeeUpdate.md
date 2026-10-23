# 更新人员

组件类型：`HrmEmployeeUpdate`。先运行 `component-describe HrmEmployeeUpdate`。

## 何时使用

用于更新一个已有人员的资料。它不创建人员；需要新增人员时使用 `PersonnelOnboarding`。只变更在职/离职状态时使用 `AlterPersonStatus`。

## 生成前查询

1. 固定人员时使用 `recipient-search` 分别取得操作人和待更新人员的当前租户 Browser 原对象；动态人员时改用真实人员字段上下文或当前用户系统变量。
2. 使用 `hrm-onboarding-fields '{}'` 取得当前租户人员字段定义。

## 业务边界

- `operators`、`person` 支持固定人员 Browser 原对象、当前用户、上游人员上下文以及已解析的变量/常量/函数公式。固定人员仍必须是真实 Browser 对象，动态引用不能手输人员 ID。
- plan 只传 `fieldAssignments`，CLI 基于实时定义生成平台 `setting`；不允许手写 DTO。
- Browser 字段必须匹配字段的真实选择器对象；字段名重名时必须传字段 ID。
- 至少提供一个待更新字段；字段、对象或必填约束无法解析时，停止生成。

## 语义计划形状

```json
{
  "type": "HrmEmployeeUpdate",
  "params": {
    "operators": {"id": "<真实人员ID>", "name": "<真实姓名>"},
    "person": {"id": "<真实人员ID>", "name": "<真实姓名>"},
    "fieldAssignments": {"main": {"邮箱": "zhangsan@example.com"}}
  }
}
```
