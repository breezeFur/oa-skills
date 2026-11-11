# 自定义接口删除表单数据

> 根据数据 ID 删除一条或多条表单数据。删除范围会受自定义接口配置的条件表达式和权限设置限制。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/formdata/v2/deleteFormData/{interfacePk}` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |
| **前置条件** | 自定义接口配置的 `interfaceType` 为 `delData` |

## 动态参数说明

| 占位符 | 来源与说明 |
|---|---|
| `{{interfacePk}}` | 已保存的删除数据接口返回的 `data.interfacePk`。 |
| `{{operator}}` | 当前操作人 ID。 |
| `{{dataId}}` | 目标表单数据 ID。 |

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
| datajson.datas | Array | 是 | 待删除的数据集合。 |
| datajson.datas[].mainTable.id | String/Long | 是 | 要删除的表单数据 ID。 |
| datajson.header.operator | String/Long | 是 | 当前操作人 ID。 |

## 请求示例

### 删除一条数据

```http
POST /api/ebuilder/form/formdata/v2/deleteFormData/{{interfacePk}}
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "datajson": {
    "datas": [
      {
        "mainTable": {
          "id": "{{dataId}}"
        }
      }
    ],
    "header": {
      "operator": "{{operator}}"
    }
  }
}
```

### 删除多条数据

```json
{
  "datajson": {
    "datas": [
      { "mainTable": { "id": "{{dataId1}}" } },
      { "mainTable": { "id": "{{dataId2}}" } }
    ],
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
    "dataIds": "{{deletedDataId}}"
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| datajson.dataIds | String | 已删除的数据 ID。批量删除时可能为逗号分隔字符串。 |

## 注意事项

1. 接口仅删除满足当前接口配置条件的数据。即使请求中传入多个 ID，也只会返回实际被删除的数据 ID。
2. `dataIds` 在单条删除时是字符串；批量调用时应按逗号拆分并与请求 ID 集合比对。
3. 删除操作不可逆。调用前应确认 `interfacePk`、操作人和目标数据范围。
4. 条件表达式支持相等、不等于、包含、不包含、以指定值结尾、不以指定值结尾等操作，最终删除范围以配置条件为准。
5. 调用时必须携带有效的 `Cookie: ETEAMSID={{ETEAMSID}}`，并确保会话账号具有目标表单的数据权限。
