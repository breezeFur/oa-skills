# 自定义接口查询表单数据总数

> 查询符合当前自定义接口配置条件的表单数据总数。结果会受到接口条件表达式、权限和关联表单范围影响。

---

## 接口信息

| 项目 | 值 |
|---|---|
| **接口 URL** | `/api/ebuilder/form/formdata/v2/getFormDataCount/{interfacePk}` |
| **请求方式** | `POST` |
| **Content-Type** | `application/json` |
| **认证方式** | `Cookie: ETEAMSID={{ETEAMSID}}` |
| **前置条件** | 自定义接口配置的 `interfaceType` 为 `getListCount` |

## 动态参数说明

| 占位符 | 来源与说明 |
|---|---|
| `{{interfacePk}}` | 已保存的总数查询接口返回的 `data.interfacePk`。 |
| `{{operator}}` | 当前操作人 ID。 |
| `{{queryFieldDataKey}}` | 已配置为输入字段的查询字段数据键；不需要额外筛选时可省略。 |
| `{{queryValue}}` | 查询字段值。 |

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
| datajson.mainTable | Object | 是 | 查询输入字段。无额外条件时传 `{}`。 |
| datajson.mainTable.{{queryFieldDataKey}} | Any | 否 | 配置为输入字段时，用于补充筛选值。 |
| datajson.header.operator | String/Long | 是 | 当前操作人 ID。 |

## 请求示例

### 查询当前配置范围内的总数

```http
POST /api/ebuilder/form/formdata/v2/getFormDataCount/{{interfacePk}}
Content-Type: application/json
Cookie: ETEAMSID={{ETEAMSID}}
```

```json
{
  "datajson": {
    "mainTable": {},
    "header": {
      "operator": "{{operator}}"
    }
  }
}
```

### 带输入字段的总数查询

```json
{
  "datajson": {
    "mainTable": {
      "{{queryFieldDataKey}}": "{{queryValue}}"
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
    "datas": 42
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| datajson.datas | Integer | 满足当前接口配置与请求筛选条件的数据总数。 |

## 注意事项

1. `datajson.datas` 是数值，不是数组。
2. 计数范围由保存接口中的 `conditions` 和当前接口配置共同决定；不能用总数接口替代无条件的全表统计。
3. 若配置没有输入字段，`mainTable` 应传空对象 `{}`，不要省略 `datajson` 或 `header`。
4. 调用时必须携带有效的 `Cookie: ETEAMSID={{ETEAMSID}}`，并确保会话账号具有目标表单的数据权限。
