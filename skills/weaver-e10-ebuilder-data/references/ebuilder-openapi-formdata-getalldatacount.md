# OpenAPI 获取数据总数

> 使用 eBuilder 表单数据 OpenAPI 查询当前表单和过滤条件下的数据总数。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/dataset/v2/getAllDataCount` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

请求体结构只有一套，请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

## 请求参数

### 顶层参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| datajson | Object | 是 | 表单上下文和过滤条件。 |

### `datajson` 参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| header.objId | String/Long | 是 | eBuilder 表单对象 ID。 |
| mainTable | Object | 否 | 主表过滤条件；多个字段之间为 AND 关系。 |
| mainTable.{{fieldDataKey}} | Any | 否 | 按实际字段数据键传入过滤值。 |
| operationinfo.fieldNoFindIgnore | String/Boolean | 否 | 字段不存在是否忽略；默认忽略。 |

## 请求头

```http
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

```http
POST /api/ebuilder/form/dataset/v2/getAllDataCount
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
    "operationinfo": {
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
      "datas": 12,
      "status": true
    }
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| data.datajson.datas | Integer/Long | 满足权限和过滤条件的数据总数。 |
| data.datajson.status | Boolean | 查询状态。 |

## 注意事项

1. 总数统计使用与分页查询相同的 `objId`、过滤条件和认证账号，才能与分页结果对应。
2. `datas` 是数值，不是数组。
3. 业务成功应同时检查 `message.code` 和 `data.datajson.status`。
