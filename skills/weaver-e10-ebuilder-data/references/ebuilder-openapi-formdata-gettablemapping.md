# OpenAPI 获取表单标识映射关系

> 获取 `mainTable`、`detail1`、`detail2` 等请求节点与表单主表、明细表标识的对应关系。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/dataset/v1/getTableMapping` |
| **请求方式** | `GET` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

请求路径只有一套，请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

## 请求参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| objId | Query | String/Long | 是 | eBuilder 表单对象 ID。 |
| reverse | Query | Boolean | 否 | 是否反转键值关系；默认 `false`。 |

## 请求头

```http
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

```http
GET /api/ebuilder/form/dataset/v1/getTableMapping?objId={{objId}}&reverse=false
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 返回结果

### 默认方向：请求节点到表标识

`reverse=false` 或不传时，返回 `mainTable`、`detailN` 到主表/明细表标识的映射：

```json
{
  "data": {
    "mainTable": "{{mainTableId}}",
    "detail1": "{{subFormId1}}",
    "detail2": "{{subFormId2}}"
  },
  "message": {
    "code": "0",
    "msg": "success"
  }
}
```

其中，`mainTable` 对应主表标识，`detail1`、`detail2` 等按明细表顺序对应各自的 `subFormId`。明细表显示名称不参与接口请求键生成。

### 反向：表标识到请求节点

传 `reverse=true` 时，返回反向映射：

```json
{
  "data": {
    "{{subFormId2}}": "detail2",
    "{{mainTableId}}": "mainTable",
    "{{subFormId1}}": "detail1"
  },
  "message": {
    "code": "0",
    "msg": "success"
  }
}
```

当响应中的明细字段只带有 `subFormId` 时，可用反向结果确定应写入的 `detailN` 节点。

### 异常响应

```json
{
  "message": {
    "code": "100001",
    "msg": "表单不存在或已被删除"
  }
}
```

## 使用建议

1. `objId` 必须传表单对象 ID；不要传业务数据 ID、`formId` 或 `subFormId`。
2. 新增、修改、详情和分页请求中的明细节点统一使用映射返回的 `detail1`、`detail2` 等键。
3. `detailN` 的编号取决于表单明细顺序，不要根据显示名称或本地排序自行编号。
4. 建议缓存同一表单的映射结果；表单结构调整后重新获取并更新缓存。
