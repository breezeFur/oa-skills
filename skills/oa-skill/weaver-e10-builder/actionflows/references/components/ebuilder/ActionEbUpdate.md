# 更新表单数据（`ActionEbUpdate`）

## 何时使用

更新已有 e-builder 数据；新增数据使用 `ActionEbAdd`，删除数据使用 `ActionEbDelete`。

## 先查询

查询目标表单及字段；按条件更新还要确认条件左字段和本次触发器上下文。

## 不可猜测

`id`、`updateData`、`fieldUpdate` 三种定位方式互不替代。`basisValue` 只用于真实上游明细依据值。

更新赋值可以使用固定值、上下文、动作流变量、租户常量或函数/公式；变量必须属于当前动作流场景，常量必须是当前租户真实常量 ID。新建资源和名称引用见 `references/dynamic_resources.md`。

## 最小计划

`targetForm`、`person`、更新赋值，以及与 `opType` 对应的定位参数。

## 三种更新模式

- `opType:"updateData"`：必须配置 `filterCondition`，仅按条件更新；不支持 `basisValue`，也不能同时配置 `updateId` 或 `updateFieldCondition`。
- `opType:"id"`：必须配置 `updateId`。不填写 `basisValue` 时按数据 ID 更新单条数据；填写真实上游明细依据值后，按依据值批量更新。
- `opType:"fieldUpdate"`：必须配置 `updateFieldCondition` 和 `updatePolicy`。不填写 `basisValue` 时按字段匹配更新单条数据；填写真实上游明细依据值后，按依据值批量更新。

`basisValue` 只是 `id` 和 `fieldUpdate` 的批量开关，不能用于条件筛选更新。CLI 会在编译前校验这些组合，避免把一个模式的定位参数静默带入另一个模式。

### 明细表策略

更新组件的 `ActionEbDlg` 会为每张明细表单独保存策略。`detail` 每项至少包含 `detailTableId`，可使用以下结构：

```json
{
  "detailTableId": "<目标明细表ID>",
  "operateType": "update",
  "basisValue": {"paramKey": "<来源明细paramKey>[]", "label": "<来源明细表>"},
  "updateType": "fields",
  "updateFieldCondition": {
    "updateField": [
      {"fieldKey": "<匹配字段ID>", "assign": {"kind": "context", "paramKey": "<来源字段>"}}
    ]
  },
  "updatePolicy": "ALL",
  "mapping": {"<来源字段>": "<目标明细字段ID>"},
  "constants": {"<目标明细字段ID>": "<固定值>"},
  "formula": {},
  "deleteFields": []
}
```

`operateType` 与前端枚举一致：`default`、`add`、`update`、`updateAdd`、`cover`、`delete`。

- `add`/`cover`：用于按依据值新增或覆盖明细；有字段赋值时需要 `basisValue`。
- `update`/`updateAdd`：必须有 `basisValue` 和至少一个字段赋值；`updateType` 只能是 `fields` 或 `rowId`。`fields` 必须提供 `updateFieldCondition.updateField`，`rowId` 必须提供 `rowId`。
- `delete`：`updateType` 可为 `fields`、`rowId` 或 `deleteAll`。前两者需要 `basisValue` 和对应条件，`deleteAll` 不需要依据值且不配置字段赋值。
- `updatePolicy` 仅用于 `update`/`updateAdd`，可选 `ALL`、`FIRST`、`LAST`、`ZERO`、`EXCEPTION`。

当 `operateType` 为 `update` 或 `updateAdd` 且 `updateType` 为 `fields` 时，`updateFieldCondition.updateField[].fieldKey` 是专门用于匹配的条件字段，不能同时出现在 `mapping`、`constants` 或 `formula` 的目标字段中。编译后的 `EsbDetailForm.data` 与 `EsbDetailForm.updateFieldCondition` 对同一字段只能保留一份；主表的 `updateFieldCondition` 与 `setting.main` 也遵循同样规则。按 `rowId` 更新时不能再配置 `updateFieldCondition`。

`rowId` 使用动态赋值对象，例如 `{"kind":"context","paramKey":"<来源明细ID>","label":"明细数据ID"}`；CLI 会将它包装为后端 `EsbDetailForm.rowId` 的 `FieldValue`。`deleteFields` 仍表示清除字段配置，不表示删除明细行；删除明细行必须使用 `operateType:"delete"`。

## filterCondition 格式（opType=updateData 定位条件）

**以 `references/condition_rules.md` 为准**：`{"field":{"id":"<目标字段id>","label":"<字段名>"},"operator":"eq","right":{...}}`。`field` 是 `{id,label}` 对象、`operator` 用英文操作符（`eq/neq/gt/lt/gte/lte/contains/uncontains/empty/nempty`）、右值键用 `right`。**勿用**废弃的 `value` 别名 / `=` / 裸字符串 `field`，否则编译报「左侧字段 id 不在目标表单实时字段列表中」。

当条件左字段是「关联流程」Workflow 时，必须由 Skill 根据实时字段元数据和 `workflowPath.formIds` 反查真实流程表单对象；编译后的左值使用原始数字 `fieldName`、`fieldType:"String"`、顶层 `sformId` 和 `formInfo.formId/layoutId`，不得套用普通业务字段的 `field_` 前缀或把目标表单版本 ID写成 `sformId`。
