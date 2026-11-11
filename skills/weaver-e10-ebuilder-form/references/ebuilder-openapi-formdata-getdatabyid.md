# OpenAPI 获取数据详情

> 使用 eBuilder 表单数据 OpenAPI 根据主表数据 ID 获取一条数据详情。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/dataset/v2/getDataById` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

请求体结构只有一套，请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

## 请求参数

### 顶层参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| datajson | Object | 是 | 查询条件和返回选项。 |

### `datajson` 参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| header.objId | String/Long | 是 | eBuilder 表单对象 ID。 |
| mainTable.id | String/Long | 是 | 要查询的数据 ID。 |
| operationinfo.isReturnDetail | String/Boolean | 否 | 是否返回明细表；默认不返回，传 `y` 或 `true` 返回。 |
| operationinfo.fieldNoFindIgnore | String/Boolean | 否 | 字段不存在是否忽略；默认忽略。 |

## 请求头

```http
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

```http
POST /api/ebuilder/form/dataset/v2/getDataById
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
      "id": "{{dataId}}"
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

字段值对象可能包含 `fieldValue`、`fieldTextValue`、`fieldOptionId`、`fieldOptionName`、`dataIndex` 和 `subFormId`，具体取决于字段类型和是否为明细字段。

## 注意事项

1. `mainTable.id` 是业务数据 ID，不是表单对象 ID；表单对象 ID 放在 `header.objId`。
2. `isReturnDetail` 未开启时不返回明细表；需要明细数据时传 `y` 或 `true`。
3. 返回字段键和字段元数据一致，字段值通常是带类型信息的对象，不要直接按普通字符串解析所有字段。
4. 查询结果为空时应按 `datas` 为空数组处理，并结合 `status` 与 `message` 判断调用结果。
