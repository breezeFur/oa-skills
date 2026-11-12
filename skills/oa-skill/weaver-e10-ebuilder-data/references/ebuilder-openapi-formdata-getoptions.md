# OpenAPI 获取表单字段选项

> 对选择类表单字段获取选项 ID 和选项名称。当字段定义中的 `compType` 或 `type` 表示选择组件，且后续逻辑需要展示选项名称或将名称转换为选项 ID 时使用本接口。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/common/ds/options` |
| **请求方式** | `GET` |
| **Content-Type** | 无请求体；可使用 `application/json` 作为通用请求头 |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。调用前应先通过[获取表单字段信息](./ebuilder-openapi-formdata-getfields.md)确认目标字段的 `id`、`compType` 和所属表单。

## 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| fieldName | Query | String/Long | 是 | 目标字段的元数据 ID，取字段接口返回的 `fields[].id`；参数名沿用接口定义。 |
| objId | Query | String/Long | 是 | 表单对象 ID，取字段接口返回的 `fields[].objId` 或请求中的 `sourceId`。 |
| sourceType | Query | String | 是 | 数据来源类型，表单场景传 `FORM`。 |
| groupId | Query | String/Long | 是 | eBuilder 应用或分组标识，与字段接口请求的 `groupId` 保持一致。 |
| optionLevel | Query | Integer/String | 否 | 选项层级；常用值为 `1`。存在层级选项时按实际层级传入。 |

## 请求头

```http
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

```http
GET /api/ebuilder/common/ds/options?fieldName={{fieldId}}&objId={{objId}}&sourceType=FORM&groupId={{groupId}}&optionLevel=1
Cookie: ETEAMSID={{ETEAMSID}}
```

## 响应数据结构

```json
{
  "code": 200,
  "msg": "接口返回成功",
  "status": true,
  "data": [
    {
      "id": "{{optionId}}",
      "name": "{{optionName}}",
      "pid": "",
      "templateId": "",
      "styleConfig": "{\"optionBackground\":\"#FFFFFF\"}",
      "archive": "0"
    }
  ],
  "fail": false
}
```

## 返回参数说明

| 字段 | 类型 | 说明 |
|---|---|---|
| data | Array | 当前字段在请求层级下的选项列表。 |
| data[].id | String/Long | 选项 ID；写入或匹配字段值时使用。 |
| data[].name | String | 选项名称；展示或将名称转换为选项 ID 时使用。 |
| data[].pid | String/Long | 父选项 ID；空值表示根选项。 |
| data[].templateId | String | 选项所属模板 ID，没有模板时为空。 |
| data[].styleConfig | String | JSON 字符串形式的选项样式配置。只用于展示，不要当作业务值解析。 |
| data[].archive | String/Integer | 归档状态；通常 `0` 表示未归档，具体以接口返回值和业务约定为准。 |
| fail | Boolean | 是否失败；同时结合 `code`、`status` 和 `msg` 判断调用结果。 |

## 推荐使用方式

1. 调用[获取表单字段信息](./ebuilder-openapi-formdata-getfields.md)，遍历 `data[].fields[]`。
2. 找到 `compType` 或 `type` 为选择类组件的字段，并确认后续逻辑确实需要选项名称。
3. 使用该字段的 `id` 作为 `fieldName`，使用 `objId`、字段查询时的 `groupId` 和 `sourceType` 调用本接口。
4. 以选项 `id` 作为数据值，以选项 `name` 作为展示文本；层级选项按 `pid` 建立父子关系。

## 注意事项

1. `fieldName` 不是字段显示文本，也不是字段对象的 `name`；它在本接口中表示字段元数据 ID。
2. 选项列表可能受 `optionLevel`、归档状态和当前账号权限影响；不要在调用方硬编码生产选项 ID 或名称。
3. 当字段定义中的 `config.options` 已满足当前逻辑时可以直接使用，但需要完整名称或最新选项时应以本接口结果为准。
4. 真实 Cookie、表单 ID 和选项值只在运行时传入，不要写入文档或日志。
