# 自定义事件触发（`CustomTrigger`）

## 何时使用

需求明确要求由平台自定义事件主动触发动作流时使用。它不是 e-builder 表单数据变化触发，也不是按钮触发。

## 参数

唯一必填参数是 `customData`，新建时必须按后端 `CustSetFormDto` 组装。顶层字段为 `customId`、`formType`、`businessModule`、`tableList`、`deleteTableIds` 和 `appId`：`customId` 必须传空字符串，由 `CustSetFormService#saveCustSetForm` 生成组件关联 ID；`formType` 为 `input`；`deleteTableIds` 新建传空数组；`appId` 由编译器注入当前动作流应用 ID。不要使用旧的 `tables`/`SETTING` 结构。

`tableList` 的主表需要 `id`、`formId`、`showName`、`isMain: true`、`orderNum` 和 `fields`；明细表需要 `id`、`showName`、`isMain: false`、`orderNum` 和 `fields`，不设置 `formId`。字段需要 `id`、`paramName`、`showName`、`paramType`、`isRequired`、`fieldComments`。缺少 ID 时由编译器生成；字段 `paramName` 不能为空。

```json
{
  "event": {
    "type": "CustomTrigger",
    "params": {
      "customData": {
        "customId": "",
        "formType": "input",
        "businessModule": "",
        "tableList": [{
          "id": "<可选，缺失时生成>",
          "formId": "<主表可选，缺失时生成>",
          "showName": "",
          "isMain": true,
          "orderNum": 0,
          "fields": [{
            "id": "<可选，缺失时生成>",
            "paramName": "payload",
            "showName": "",
            "paramType": "string",
            "isRequired": false,
            "fieldComments": ""
          }]
        }],
        "deleteTableIds": []
      }
    }
  }
}
```

自定义参数的字段定义是业务特定的。根据需求新建时可以直接提供 `tableList` 和字段；`tableList` 或其中的 `fields` 为空时，设计器“输入参数设置”就是空白。已有组件的更新场景如需保留平台生成的 `customId`，应使用平台回读 DTO，不要把更新 DTO 当作新建 DTO。

根触发器图标不是 `Icon-custom-trigger`，编译器统一保存为 `Icon-N-Triggerrul`。

## 上下文

触发后业务字段上下文根为 `SelectParams`，可引用 `SelectParams.<主表/明细表路径>`；同时可使用平台提供的 `FormField`、`SettingInfo`、`accessId` 和 `monitorId`。不要将自定义触发字段编译为 `FormData`。

动态赋值的 `paramKey` 只写业务路径，不写 `FormData.`、`ApprovalData.` 或 `SelectParams.` 前缀。主表和明细表必须沿用同一个主表 key：主表字段写成 `主表key.字段key`，明细字段写成 `主表key.明细表key[].字段key`；只有最终公式的 `value`、`currentParamKey` 和 `allParamKey` 使用 `SelectParams.` 前缀。不能把明细字段写成 `FormData.明细表key[].字段key`，也不能省略前面的主表 key。

## 自定义参数来源的 `frontId` 规则

动态赋值来源于当前触发组件的 `customData` 时，必须把 `event.params.customData`（后端类型 `CustSetFormDto`）作为唯一 ID 来源。不要从目标字段、FormulaBean 自身的 `id` 或 `paramKey` 尾段推导 `frontId`。

按以下顺序生成：

1. 先按动态引用的表路径，在 `customData.tableList[]` 中找到对应的表对象（后端类型 `CustFormTableDto`）。
2. 如果引用选择的是表维度（例如 `主表key.明细表key[]`），生成的 FormulaBean 写 `frontId = tableList[].id`。
3. 如果引用选择的是字段维度（例如 `主表key.字段key` 或 `主表key.明细表key[].字段key`），先在匹配表的 `fields[]` 中找到对应字段对象（后端类型 `CustFormDetailDto`），再写 `frontId = fields[].id`。
4. 这个 `frontId` 要写到关联映射生成的 FormulaBean 上，包括普通动作映射和终止组件 `customParamSetting.tableList[].fields[].formulaValue`；不能写目标字段 ID、表名、字段名、临时公式 ID 或 `paramKey` 尾段。
5. 对应表/字段没有真实 ID 时，`frontId` 写空串 `""`；有值时必须是纯数字字符串。`field_<数字>` 只能在生成时转成 `<数字>`。

例如：

```json
{
  "customData": {
    "tableList": [{
      "id": "1001",
      "fields": [{"id": "2001", "paramName": "name"}]
    }]
  },
  "mapping": {
    "targetFieldId": {"kind": "context", "paramKey": "main.name"}
  }
}
```

上例生成的关联 FormulaBean 必须是 `frontId: "2001"`；如果引用的是 `main[]` 表节点，则必须是 `frontId: "1001"`。
