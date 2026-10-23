# 人员入职

组件类型：`PersonnelOnboarding`。先运行 `component-describe PersonnelOnboarding`。

## 何时使用

用于新增人员到系统。它没有“目标人员”参数：人员由入职字段创建。若人员已经存在并只需改资料，改用 `HrmEmployeeUpdate`。

## 生成前查询

1. 使用 `recipient-search` 取得操作人的当前租户 Browser 原对象。
2. 使用 `hrm-onboarding-fields '{}'` 取得当前租户人员主表、明细、字段类型和必填项。

## 业务边界

- plan 传 `fieldAssignments`，CLI 根据实时字段定义生成平台 `setting`；不允许手写 `setting` / `EsbFormDataDto`。
- 字段可用显示名或字段 ID。当前租户出现同名字段时必须使用字段 ID。
- Browser 字段（部门、岗位、上级等）只接受其对应选择器返回的真实对象，不能把名称或 ID 当文本填入。
- 未提供当前租户必填字段、或字段/取值无法解析时，停止生成并报告缺项。

## 语义计划形状

```json
{
  "type": "PersonnelOnboarding",
  "params": {
    "operators": {"id": "<真实人员ID>", "name": "<真实姓名>"},
    "fieldAssignments": {
      "main": {"姓名": "张三", "部门": {"id": "<真实部门ID>", "name": "研发部"}},
      "detail": [{"table": "教育经历", "fields": {"学校名称": "某大学"}}]
    }
  }
}
```
