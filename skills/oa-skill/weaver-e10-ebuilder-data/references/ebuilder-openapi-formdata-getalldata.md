# OpenAPI 获取分页数据

> 使用 eBuilder 表单数据 OpenAPI 分页查询表单数据，可按主表字段条件过滤，并按需返回明细表。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/dataset/v2/getAllData` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

请求体结构只有一套，请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

## 请求参数

### 顶层参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| datajson | Object | 是 | 查询条件、分页和返回选项。 |

### `datajson` 参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| header.objId | String/Long | 是 | eBuilder 表单对象 ID。 |
| mainTable | Object | 否 | 主表过滤条件；多个字段之间为 AND 关系。 |
| mainTable.{{fieldDataKey}} | Any | 否 | 按实际字段数据键传入过滤值。 |
| pageInfo | Object | 否 | 分页参数。 |
| pageInfo.pageNo | Integer/String | 否 | 页码，从 1 开始，默认 1。 |
| pageInfo.pageSize | Integer/String | 否 | 每页条数，默认 10，最大 1000。 |
| operationinfo.isReturnDetail | String/Boolean | 否 | 是否返回明细表；默认不返回，传 `y` 或 `true` 返回。 |
| operationinfo.fieldNoFindIgnore | String/Boolean | 否 | 字段不存在是否忽略；默认忽略。 |

## 请求头

```http
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

```http
POST /api/ebuilder/form/dataset/v2/getAllData
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "datajson": {
    "header": {
      "objId": "{{objId}}"
    },
    "mainTable": {
      "{{fieldDataKey}}": "{{fieldValue}}"
    },
    "pageInfo": {
      "pageNo": 1,
      "pageSize": 10
    },
    "operationinfo": {
      "isReturnDetail": "y",
      "fieldNoFindIgnore": "false"
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
      "datas": [
        {
          "mainTable": {
            "{{fieldDataKey}}": {
              "fieldId": "{{fieldId}}",
              "fieldType": "Text",
              "fieldValue": "{{fieldValue}}"
            }
          },
          "detail1": []
        }
      ],
      "status": true
    }
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| data.datajson.datas | Array | 当前页数据。 |
| data.datajson.datas[].mainTable | Object | 主表字段及字段值对象。 |
| data.datajson.datas[].detail1、detail2... | Array | 开启 `isReturnDetail` 后返回的明细行。 |
| data.datajson.status | Boolean | 查询状态。 |

## 注意事项

1. `pageNo` 从 1 开始；`pageSize` 最大支持 1000，建议根据业务分页处理。
2. 未传 `mainTable` 时查询当前账号有权限查看的全部数据；传入字段必须是实际数据键。
3. `isReturnDetail` 默认不返回明细表；开启后响应中会出现映射对应的 `detail1`、`detail2` 等明细节点。
4. 若需要总条数，请在相同的 `objId` 和过滤条件下调用[获取数据总数](./ebuilder-openapi-formdata-getalldatacount.md)。
