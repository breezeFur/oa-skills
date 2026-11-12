# OpenAPI 获取表单字段信息

> 使用 eBuilder 字段接口获取表单主表和明细表的字段定义。该接口返回字段组件类型、字段 ID、显示文本、字段名和组件参数，可用于组装数据接口请求和判断是否需要继续读取选项。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/common/ds/fields` |
| **请求方式** | `POST` |
| **Content-Type** | `multipart/form-data` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。`multipart/form-data` 的 boundary 由 HTTP 客户端自动生成，不要手工固定示例中的 boundary。

## 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| groupId | FormData | String/Long | 是 | eBuilder 应用或分组标识。 |
| sourceId | FormData | String/Long | 是 | 表单对象 ID，通常与 `objId` 相同。 |
| sourceType | FormData | String | 是 | 数据来源类型，表单场景传 `FORM`。 |
| detailFieldsGroup | FormData | Boolean | 否 | 是否按明细表分组返回，建议传 `true`。 |
| enableMerge | FormData | Boolean | 否 | 是否合并字段配置，建议传 `true`。 |
| customParam | FormData | JSON String | 否 | 终端等扩展参数；无特殊要求时传 `{"terminal":""}`。 |
| params | FormData | JSON String | 否 | 扩展查询参数；无特殊要求时传 `[]`。 |

## 请求头

```http
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

```http
POST /api/ebuilder/common/ds/fields
Content-Type: multipart/form-data; boundary={{boundary}}
Cookie: ETEAMSID={{ETEAMSID}}

--{{boundary}}
Content-Disposition: form-data; name="groupId"

{{groupId}}
--{{boundary}}
Content-Disposition: form-data; name="sourceId"

{{objId}}
--{{boundary}}
Content-Disposition: form-data; name="sourceType"

FORM
--{{boundary}}
Content-Disposition: form-data; name="detailFieldsGroup"

true
--{{boundary}}
Content-Disposition: form-data; name="enableMerge"

true
--{{boundary}}
Content-Disposition: form-data; name="customParam"

{"terminal":""}
--{{boundary}}
Content-Disposition: form-data; name="params"

[]
--{{boundary}}--
```

也可以使用 HTTP 客户端的 multipart 参数 API 发送上述字段，避免手工拼接 boundary。

## 响应数据结构

```json
{
  "code": 200,
  "msg": "接口返回成功",
  "status": true,
  "data": [
    {
      "name": "{{formName}}",
      "id": "{{objId}}",
      "fields": [
        {
          "compType": "Select",
          "type": "Select",
          "id": "{{fieldId}}",
          "text": "{{fieldText}}",
          "name": "{{fieldName}}",
          "objId": "{{objId}}",
          "subFormId": "",
          "mainField": true,
          "optionType": "",
          "multiSelect": "false",
          "browserParams": {
            "formId": "{{formId}}",
            "fieldId": "{{fieldId}}",
            "layoutId": "",
            "serviceModule": "ebuilderform"
          },
          "config": {
            "dataKey": "{{dataKey}}",
            "componentKey": "Select",
            "fieldId": "{{fieldId}}",
            "subFormId": "",
            "options": []
          }
        }
      ]
    }
  ],
  "fail": false
}
```

## 返回参数说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data | Array | 字段分组列表；主表和每个明细表各占一个分组。 |
| data[].id | String/Long | 分组所属表单或明细表标识。 |
| data[].name | String | 分组显示名称。 |
| data[].fields | Array | 分组下的字段对象。 |
| fields[].compType | String | 字段组件类型，例如 `Text`、`Select`、`RadioBox`、`NumberComponent`。用于判断控件行为。 |
| fields[].type | String | 字段逻辑类型，例如 `String`、`Number`、`Date`、`Select`。 |
| fields[].id | String/Long | 字段元数据 ID；获取选项时作为 `fieldName` Query 参数。 |
| fields[].text | String | 字段显示文本，用于展示或人工确认，不能直接作为请求字段键。 |
| fields[].name | String | 字段名，数据接口组装字段时优先使用该值。 |
| fields[].objId | String/Long | 字段所属主表对象 ID。 |
| fields[].subFormId | String/Long | 明细字段所属明细表 ID；主表字段通常为空。 |
| fields[].mainField | Boolean | 是否为主表字段。 |
| fields[].optionType | String | 选项配置类型；为空时仍应结合 `compType`、`type` 和 `config` 判断。 |
| fields[].multiSelect | String/Boolean | 是否支持多选。 |
| fields[].browserParams | Object | 浏览/关联组件参数，至少保留 `formId`、`fieldId`、`layoutId` 和 `serviceModule`。 |
| fields[].config | Object | 组件配置；可能包含 `dataKey`、`componentKey`、`subFormId`、`options` 等。 |
| fields[].config.dataKey | String | 组件层数据键；当具体数据接口要求组件数据键时使用，不要与 `id` 或 `text` 混淆。 |
| fields[].conditionType | Array | 可用筛选操作，例如 `eq`、`in`、`between`。 |

## 字段键和选项处理

1. 数据操作请求不要使用 `text` 作为字段键。通常使用字段对象的 `name`；若目标接口明确要求组件数据键，则使用 `config.dataKey`。
2. `id` 是字段元数据标识，不等于显示文本；它也是[获取字段选项](ebuilder-openapi-formdata-getoptions.md)接口的 `fieldName` 参数来源。
3. 当字段的 `compType` 或 `type` 表示选择类组件（例如 `Select`、`RadioBox`），且后续逻辑需要把选项 ID 转换为选项名称时，再调用选项接口。
4. `subFormId` 用于和[表单标识映射关系](ebuilder-openapi-formdata-gettablemapping.md)中的 `detail1`、`detail2` 等节点对应；不要按显示名称自行编号。
5. `Employee`、`Department`、`SubCompany`、`Workflow`、`Document` 或 `RelateBrowser` 等浏览字段不能使用普通选项接口代替。按名称填写时读取[浏览字段查询](browser-fields.md)，优先使用 `config.browserType.module/type` 或已验证的组件路由查询真实可选项。

## 注意事项

1. `sourceId` 必须是表单对象 ID；不要传业务数据 ID 或表单引擎内部 `formId`。
2. 主表和明细表字段都可能出现在 `data[].fields` 中，调用方应根据 `mainField`、`subFormId` 和分组 `id` 区分归属。
3. 字段响应中的 `config.options` 可能只包含部分配置或为空，完整选项名称应以选项接口返回结果为准。
4. 真实 Cookie、表单 ID 和业务字段值只在运行时传入，不要写入文档或日志。
