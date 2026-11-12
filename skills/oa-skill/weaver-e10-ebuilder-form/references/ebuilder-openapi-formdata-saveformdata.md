# OpenAPI 新建表单数据

> 使用 eBuilder 表单数据 OpenAPI 新建一条或多条主表数据，可同时提交明细表数据。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/dataset/v2/saveFormData` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

调用地址使用本页相对路径，说明见 [OpenAPI 调用方式说明](ebuilder-openapi-common.md)。请求体结构只有一套，请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

## 请求参数

### 顶层参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| datajson | Object | 是 | 表单数据和操作配置。 |

### `datajson` 参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| header | Object | 是 | 表单上下文。 |
| header.objId | String/Long | 是 | eBuilder 表单对象 ID。 |
| datas | Array | 是 | 待新增数据集合。 |
| datas[].mainTable | Object | 是 | 主表字段，键使用实际数据键。 |
| datas[].detail1、detail2... | Array | 否 | 按明细表顺序提交明细行。 |
| operationinfo | Object | 否 | 操作选项。 |
| operationinfo.fieldNoFindIgnore | String/Boolean | 否 | 字段不存在是否忽略；默认忽略，传 `false` 或 `n` 时不忽略。 |
| operationinfo.doAction | String/Boolean | 否 | 是否执行当前数据对应的 action；默认不执行，传 `true` 或 `y` 执行。 |

## 请求头

```http
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

```http
POST /api/ebuilder/form/dataset/v2/saveFormData
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "datajson": {
    "datas": [
      {
        "mainTable": {
          "{{mainFieldDataKey}}": "{{mainFieldValue}}"
        },
        "detail1": [
          {
            "{{detailFieldDataKey}}": "{{detailFieldValue}}"
          }
        ]
      }
    ],
    "header": {
      "objId": "{{objId}}"
    },
    "operationinfo": {
      "fieldNoFindIgnore": "true",
      "doAction": "false"
    }
  }
}
```

## 响应数据结构

```json
{
  "message": {
    "code": "0",
    "msg": "success"
  },
  "data": {
    "datajson": {
      "dataIds": [
        "{{newDataId}}"
      ],
      "status": true
    }
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| data.datajson.dataIds | Array | 本次成功新增的数据 ID。 |
| data.datajson.status | Boolean | 数据操作状态。 |
| data.datajson.message | String | 失败时的异常信息（如果返回）。 |

## 注意事项

1. `mainTable` 中的字段键必须来自[获取表单字段信息](ebuilder-openapi-formdata-getfields.md)返回的字段对象 `name`；若具体接口要求组件数据键，则使用对应的 `config.dataKey`，字段值按字段类型传入。
2. **自定义字段键选择（实测关键）**：当字段为自定义字段时，其 `name` 通常与元数据 `id` 相同（如 `936482847057182721`），而真实数据键在 `config.dataKey`（如 `dxwb_jonh`）。保存/修改时**必须使用 `config.dataKey` 作为 `mainTable` 的字段键**，否则字段会被静默忽略（响应仍返回成功，但字段值为空）。系统字段（如 `name`、`data_status`）的 `name` 即等于数据键，可直接使用。判断方法：若字段 `name` 等于其 `id`，则改用该字段的 `config.dataKey`。
2. `detail1`、`detail2` 等名称按[表单标识映射关系](ebuilder-openapi-formdata-gettablemapping.md)中的明细顺序使用，不要使用明细表显示名称。
3. 单次数据量和明细行数量受接口限制；超过限制时请拆分请求。
4. 新增成功后保存 `dataIds`，后续详情、修改和删除需要使用返回的数据 ID。
