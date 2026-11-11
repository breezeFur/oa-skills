# 自定义接口修改表单数据

> 根据数据 ID 修改已存在的表单数据。可修改字段必须在自定义接口配置中启用为输入字段。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/formdata/v2/updateFormData/{interfacePk}` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |
| **前置条件** | 自定义接口配置的 `interfaceType` 为 `editData` |

## 动态参数说明

| 占位符 | 来源与说明 |
|---|---|
| `{{interfacePk}}` | 已保存的修改数据接口返回的 `data.interfacePk`。 |
| `{{operator}}` | 当前操作人 ID。 |
| `{{dataId}}` | 目标表单数据 ID，来自新增接口返回或表单数据查询结果。 |
| `{{fieldDataKey}}` | 关联表单字段的真实数据键。 |
| `{{newValue}}` | 修改后的字段值。 |

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
| datajson.operationinfo | Object | 是 | 执行选项，字段与新增接口相同。 |
| datajson.datas | Array | 是 | 待修改的数据集合。 |
| datajson.datas[].mainTable.id | String/Long | 是 | 待修改的数据 ID。 |
| datajson.datas[].mainTable.{{fieldDataKey}} | Any | 否 | 要更新的业务字段。每个字段必须已在接口配置中允许输入。 |
| datajson.header.operator | String/Long | 是 | 当前操作人 ID。 |

## 请求示例

```http
POST /api/ebuilder/form/formdata/v2/updateFormData/{{interfacePk}}
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "datajson": {
    "operationinfo": {
      "printCost": false,
      "asyncPostProcess": false,
      "asyncMark": false
    },
    "datas": [
      {
        "mainTable": {
          "id": "{{dataId}}",
          "{{fieldDataKey}}": "{{newValue}}"
        }
      }
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
    "dataIds": [
      "{{dataId}}"
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| datajson.dataIds | Array | 实际修改成功的数据 ID 列表。 |

## 注意事项

1. `mainTable.id` 必须是目标数据 ID，不是接口配置 `id` 或 `interfacePk`。
2. 修改请求只提交需要变更的业务字段，避免以空值覆盖未修改字段。
3. 后置处理、编码等需要异步执行时，可在 `operationinfo` 中将对应开关设为 `true`。
4. 返回的 `dataIds` 应包含请求的 `{{dataId}}`；否则不得将本次调用视为修改完成。
5. 调用时必须携带有效的 `Cookie: ETEAMSID={{ETEAMSID}}`，并确保会话账号具有目标表单的数据权限。
