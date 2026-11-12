# OpenAPI 删除表单数据

> 使用 eBuilder 表单数据 OpenAPI 按主键或字段条件删除表单数据。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/dataset/v2/deleteData` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

请求体结构只有一套，请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

## 请求参数

### 顶层参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| datajson | Object | 是 | 删除条件和操作选项。 |

### `datajson` 参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| header.objId | String/Long | 是 | eBuilder 表单对象 ID。 |
| mainTable | Object | 否 | 删除条件，多个字段之间为 AND 关系；按主键删除时传 `id`。 |
| operationinfo | Object | 否 | 操作选项。 |
| operationinfo.fieldNoFindIgnore | String/Boolean | 否 | 字段不存在是否忽略；默认忽略。 |
| operationinfo.doAction | String/Boolean | 否 | 是否执行删除 action；默认不执行。 |

## 请求头

```http
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

按数据 ID 删除：

```http
POST /api/ebuilder/form/dataset/v2/deleteData
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
      "fieldNoFindIgnore": "false",
      "doAction": "false"
    }
  }
}
```

按条件删除时，在同一 `mainTable` 中传入多个字段，多个条件同时满足才会进入删除范围：

```json
{
  "datajson": {
    "header": {
      "objId": "{{objId}}"
    },
    "mainTable": {
      "{{fieldDataKey}}": "{{fieldValue}}"
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
      "dataIds": "{{deletedDataId1}},{{deletedDataId2}}",
      "status": true
    }
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| data.datajson.dataIds | String | 成功删除的数据 ID，多个 ID 以逗号分隔。 |
| data.datajson.status | Boolean | 数据操作状态。 |
| data.datajson.message | String | 失败时的异常信息，例如无权限或数据不存在。 |

## 注意事项

1. 删除范围受当前操作人的数据权限影响；请求条件命中的数据不一定全部可删除。
2. 单次删除数量按接口限制处理，超过限制请拆分请求。
3. 删除不可逆，调用前确认 `objId`、条件和操作人。
4. 业务成功应同时检查 `message`、`data.datajson.status` 和返回的 `dataIds`。
