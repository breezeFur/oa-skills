# OpenAPI 修改表单数据

> 使用 eBuilder 表单数据 OpenAPI 按数据 ID 或条件修改主表、明细表数据。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/dataset/v2/updateFormData` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |

请求体结构只有一套，请求头必须携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

## 请求参数

### 顶层参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| datajson | Object | 是 | 表单数据和更新策略。 |

### `datajson` 参数

| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| header.objId | String/Long | 是 | eBuilder 表单对象 ID。 |
| datas | Array | 是 | 待修改数据集合。 |
| datas[].mainTable.id | String/Long | 按 ID 修改时是 | 目标数据 ID。 |
| datas[].mainTable | Object | 是 | 修改字段或条件字段，键使用实际数据键。 |
| datas[].detail1、detail2... | Array | 否 | 按明细表顺序提交明细行。 |
| operationinfo | Object | 否 | 更新策略。 |
| operationinfo.updateType | String | 否 | `ids`（默认，按 ID 更新）或 `updatePolicy`（按条件更新）。 |
| operationinfo.needAdd | String/Boolean | 否 | 按 ID/条件找不到数据时是否新增；默认不新增。 |
| operationinfo.updateField | Object | 条件更新时是 | 指定实际更新字段，如 `{"mainTable":["{{fieldDataKey}}"]}`。 |
| operationinfo.operateType | Object | 否 | 明细表操作策略；传 `{"detail1":"cover"}` 表示覆盖明细行。 |
| operationinfo.fieldNoFindIgnore | String/Boolean | 否 | 字段不存在是否忽略；默认忽略。 |
| operationinfo.doAction | String/Boolean | 否 | 是否执行数据 action；默认不执行。 |

## 请求头

```http
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求示例

### 按 ID 修改

```http
POST /api/ebuilder/form/dataset/v2/updateFormData
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "datajson": {
    "datas": [
      {
        "mainTable": {
          "id": "{{dataId}}",
          "{{fieldDataKey}}": "{{newValue}}"
        }
      }
    ],
    "header": {
      "objId": "{{objId}}"
    },
    "operationinfo": {
      "updateType": "ids",
      "fieldNoFindIgnore": "true",
      "needAdd": "false",
      "doAction": "false"
    }
  }
}
```

### 条件更新

将 `updateType` 设置为 `updatePolicy`，在 `mainTable` 中传入筛选字段，并通过 `updateField` 指定真正要更新的字段：

```json
{
  "datajson": {
    "datas": [
      {
        "mainTable": {
          "{{conditionFieldDataKey}}": "{{conditionValue}}",
          "{{fieldDataKey}}": "{{newValue}}"
        }
      }
    ],
    "header": {
      "objId": "{{objId}}"
    },
    "operationinfo": {
      "updateType": "updatePolicy",
      "updateField": {
        "mainTable": ["{{fieldDataKey}}"]
      }
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
        "{{dataId}}"
      ],
      "status": true
    }
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| data.datajson.dataIds | Array | 实际更新（或按 `needAdd` 新增）的数据 ID。 |
| data.datajson.status | Boolean | 数据操作状态。 |

## 注意事项

1. `updateType=ids` 时必须在每条 `mainTable` 中传 `id`；没有匹配数据时只有 `needAdd=true/y` 才会新增。
2. `updateType=updatePolicy` 时必须传 `updateField`，否则无法确定实际更新字段。
3. 明细表使用映射接口返回的 `detail1`、`detail2` 等顺序名称；需要覆盖明细行时配置对应的 `operateType`。
4. 修改成功后用 `dataIds` 与目标数据 ID 对照，不要仅依据 HTTP 状态码判断业务成功。
