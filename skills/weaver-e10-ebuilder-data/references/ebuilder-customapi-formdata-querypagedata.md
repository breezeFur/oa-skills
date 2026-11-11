# 自定义接口分页查询表单数据

> 按页查询符合当前自定义接口配置条件的表单数据。返回字段、排序和过滤能力由接口配置中的字段设置与条件表达式决定。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/formdata/v2/getFormDataList/{interfacePk}` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |
| **前置条件** | 自定义接口配置的 `interfaceType` 为 `getListData` |

## 动态参数说明

| 占位符 | 来源与说明 |
|---|---|
| `{{interfacePk}}` | 已保存的分页查询接口返回的 `data.interfacePk`。 |
| `{{operator}}` | 当前操作人 ID。 |
| `{{pageNo}}` | 当前页码，从 `1` 开始。 |
| `{{pageSize}}` | 每页数据量。 |
| `{{queryFieldDataKey}}` | 配置为输入字段的查询字段真实数据键。 |
| `{{queryValue}}` | 查询字段值。 |
| `{{returnFieldDataKey}}` | 配置为返回字段的真实数据键。 |

## 请求参数

## 认证方式

所有请求均使用内部会话认证，必须在请求头中携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

### Path 与 Query 参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| interfacePk | Path | String | 是 | 对外运行接口标识。 |

### Body 参数（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| datajson.mainTable | Object | 是 | 查询输入字段；无额外筛选时传 `{}`。 |
| datajson.mainTable.{{queryFieldDataKey}} | Any | 否 | 已配置为输入字段的筛选值。 |
| datajson.pageInfo | Object | 是 | 分页信息。 |
| datajson.pageInfo.pageNo | String/Integer | 是 | 页码，从 `1` 开始。 |
| datajson.pageInfo.pageSize | String/Integer | 是 | 每页条数。 |
| datajson.header.operator | String/Long | 是 | 当前操作人 ID。 |

## 请求示例

### 查询第一页

```http
POST /api/ebuilder/form/formdata/v2/getFormDataList/{{interfacePk}}
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "datajson": {
    "mainTable": {},
    "pageInfo": {
      "pageNo": "1",
      "pageSize": "10"
    },
    "header": {
      "operator": "{{operator}}"
    }
  }
}
```

### 带字段筛选的分页查询

```json
{
  "datajson": {
    "mainTable": {
      "{{queryFieldDataKey}}": "{{queryValue}}"
    },
    "pageInfo": {
      "pageNo": "{{pageNo}}",
      "pageSize": "{{pageSize}}"
    },
    "header": {
      "operator": "{{operator}}"
    }
  }
}
```

## 响应数据结构

```json
{
  "datajson": {
    "datas": [
      {
        "mainTable": {
          "{{returnFieldDataKey}}": "{{fieldValue}}"
        }
      }
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| datajson.datas | Array | 当前页数据集合。 |
| datajson.datas[].mainTable | Object | 当前记录的返回字段。键和值由接口配置决定。 |

## 注意事项

1. `pageNo` 与 `pageSize` 支持字符串或整数；为保持调用一致性，建议统一传字符串。
2. `mainTable` 只能传配置为输入字段的真实 `dataKey`，其他字段不会成为有效查询条件。
3. 响应字段由 `isreturn`、`returntype` 等配置决定。未配置为返回字段的列不应在调用方中假设存在。
4. 分页结果的总数应使用[自定义接口查询表单数据总数](./ebuilder-customapi-formdata-count.md)获取，并在相同的配置条件和筛选参数下比对。
5. 调用时必须携带有效的 `Cookie: ETEAMSID={{ETEAMSID}}`，并确保会话账号具有目标表单的数据权限。
