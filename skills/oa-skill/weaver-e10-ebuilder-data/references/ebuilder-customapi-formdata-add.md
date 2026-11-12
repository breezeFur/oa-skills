# 自定义接口新增表单数据

> 通过已发布的自定义接口向关联表单新增一条或多条数据。请求字段必须与该接口配置中允许输入的主表、明细表字段一致。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/formdata/v2/saveFormData/{interfacePk}` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |
| **前置条件** | 自定义接口配置的 `interfaceType` 为 `addData` |

## 动态参数说明

| 占位符 | 来源与说明 |
|---|---|
| `{{interfacePk}}` | 保存自定义接口配置后返回的 `data.interfacePk`。它不是配置记录 `id`。 |
| `{{operator}}` | 当前操作人 ID。 |
| `{{fieldDataKey}}` | 关联表单布局或字段元数据中的实际数据键；必须已在接口配置中启用为输入字段。 |
| `{{fieldValue}}` | 要写入的业务字段值，类型必须与表单字段类型一致。 |

## 认证方式

所有请求均使用内部会话认证，必须在请求头中携带 `Cookie: ETEAMSID={{ETEAMSID}}`。

## 请求头

```http
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

## 请求参数

### Path 与 Query 参数

| 参数名 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| interfacePk | Path | String | 是 | 对外运行接口标识。 |

### Body 参数（JSON）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| datajson | Object | 是 | 运行时请求根对象。 |
| datajson.operationinfo | Object | 是 | 执行选项。 |
| datajson.operationinfo.printCost | Boolean | 否 | 是否记录接口执行耗时，默认 `false`。 |
| datajson.operationinfo.asyncPostProcess | Boolean | 否 | 是否异步执行后置处理，默认 `false`。 |
| datajson.operationinfo.asyncMark | Boolean | 否 | 是否异步生成编码，默认 `false`。 |
| datajson.datas | Array | 是 | 待新增的数据集合。 |
| datajson.datas[].mainTable | Object | 是 | 主表字段键值对，键为真实 `dataKey`。 |
| datajson.datas[].detailTable | Object/Array | 否 | 明细字段数据；具体结构由 `detailFields` 配置决定。 |
| datajson.header | Object | 是 | 请求上下文。 |
| datajson.header.operator | String/Long | 是 | 当前操作人 ID。 |

## 请求示例

### 新增一条主表数据

```http
POST /api/ebuilder/form/formdata/v2/saveFormData/{{interfacePk}}
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
          "{{fieldDataKey}}": "{{fieldValue}}"
        }
      }
    ],
    "header": {
      "operator": "{{operator}}"
    }
  }
}
```

### 批量新增数据

```json
{
  "datajson": {
    "operationinfo": {
      "printCost": false,
      "asyncPostProcess": true,
      "asyncMark": false
    },
    "datas": [
      { "mainTable": { "{{fieldDataKey}}": "第一条数据" } },
      { "mainTable": { "{{fieldDataKey}}": "第二条数据" } }
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
      "{{newDataId}}"
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| datajson | Object | 响应业务数据根节点。 |
| datajson.dataIds | Array | 新增成功的数据 ID 列表，与请求数据顺序对应。 |

## 注意事项

1. 不要自行猜测 `{{fieldDataKey}}`。应从表单布局或字段元数据获取，并确认该字段已配置为接口输入字段。
2. 单次传入的数据数量不能超过配置的 `datasNumber` 限制；明细行数量还受明细表配置限制。
3. 调用时必须携带有效的 `Cookie: ETEAMSID={{ETEAMSID}}`，并确保会话账号具有目标表单的数据权限。
4. 创建成功后应保存 `datajson.dataIds`，后续修改、删除和详情查询均需要该数据 ID。
