# 自定义接口根据主键查询表单数据

> 根据表单数据 ID 获取一条数据详情。返回字段由自定义接口配置中标记为返回字段的 `mainFields` 决定。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/formdata/v2/getFormDataByPk/{interfacePk}` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |
| **前置条件** | 自定义接口配置的 `interfaceType` 为 `getDataDetail` |

## 动态参数说明

| 占位符 | 来源与说明 |
|---|---|
| `{{interfacePk}}` | 已保存的详情查询接口返回的 `data.interfacePk`。 |
| `{{operator}}` | 当前操作人 ID。 |
| `{{dataId}}` | 目标表单数据 ID。 |
| `{{fieldDataKey}}` | 配置为返回字段的表单真实数据键。 |

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
| datajson.mainTable.id | String/Long | 是 | 要查询的表单数据 ID。 |
| datajson.header.operator | String/Long | 是 | 当前操作人 ID。 |

## 请求示例

```http
POST /api/ebuilder/form/formdata/v2/getFormDataByPk/{{interfacePk}}
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "datajson": {
    "mainTable": {
      "id": "{{dataId}}"
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
          "{{fieldDataKey}}": "{{fieldValue}}"
        }
      }
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| datajson.datas | Array | 数据详情集合。根据主键查询时通常包含一条记录。 |
| datajson.datas[].mainTable | Object | 配置为返回字段的主表字段键值对。 |

## 注意事项

1. 必须在配置中为业务字段设置返回属性，否则响应中不会包含该字段。
2. 响应字段键是实际 `dataKey`，不是字段显示名称；调用方需按配置或字段元数据解析。
3. 不要将 `datajson.datas` 假设为固定字段集合，返回结构随接口配置变化。
4. 调用时必须携带有效的 `Cookie: ETEAMSID={{ETEAMSID}}`，并确保会话账号具有目标表单的数据权限。
