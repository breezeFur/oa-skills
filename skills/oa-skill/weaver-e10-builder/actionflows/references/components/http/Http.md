# 执行 HTTP（`Http`）

执行已经在当前租户连接器中配置好的 HTTP/HTTPS 接口。平台前端组件类型是 `Http`；HTTPS 不是另一个组件类型，而是资源接口地址的协议。

先运行：

```bash
e10-cli actionflow component-describe Http
```

按以下顺序发现真实对象，并把接口详情完整保存下来，避免终端摘要或截断输出造成误判：

```bash
e10-cli actionflow http-connectors --out http-connectors.json
e10-cli actionflow http-resources '{"systemId":"<连接器ID>"}' --out http-resources.json
e10-cli actionflow http-interfaces '{"systemId":"<连接器ID>","resourceId":"<资源ID>"}' --out http-interfaces.json
e10-cli actionflow http-interface-detail '{"interfaceId":"<接口ID>"}' --out http-interface-detail.json
```

`http-interface-detail` 的 `request`、`response`、`address`、`requestMethod` 和 `type` 是生成计划的真实来源。正式 `generate` 还会在保存前再次按三个 ID 实时读取并校验这条链路：连接器名称/图标来自当前租户的 connector 列表，资源名称来自当前连接信息列表，接口名称和原生映射来自当前接口详情；找不到或归属不一致就停止，不会用旧环境的名称、图标或 DTO 继续生成。计划可以省略 `request`/`response`，但必须提供当前租户的三个 ID，CLI 会从接口详情补齐；如果显式传入原生映射，其 mapping ID 必须与当前接口详情一致。`type=http` 时地址可以是 `http://` 或 `https://`；`type=webservice` 时才考虑 `selectMethod`/`soapVersion`。

## 必填对象

- `systemId`：HTTP 连接器 ID。
- `resourceId`：连接信息/资源 ID，必须属于 `systemId`。
- `interfaceId`：执行接口 ID，必须属于 `resourceId`。
- `request`：当前租户接口详情返回的原生 `ParamGroupMappingBean`。它是保存 HTTP 动作时的请求参数映射，不能用空数组或自行猜测的 `tables`/`tableData` 代替。

这四项必须来自同一租户、同一条“连接器 → 资源 → 接口”链路。CLI 不根据名称猜 ID，也不把 HTTPS 地址改写成 HTTP。

## 可选对象

- `response`：接口详情返回的原生响应参数映射。传入后保留在节点数据中，供上下文字段和回读使用。
- `address`：接口详情的回显地址；如果是 `https://`，必须原样保留。它不是替代 `resourceId/interfaceId` 的连接配置。
- `requestMethod`：`GET`、`POST`、`PUT`、`PATCH` 或 `DELETE`。通常直接采用接口详情返回值。
- `selectMethod`、`soapVersion`：只用于 WebService 兼容回显，普通 HTTP/HTTPS 接口不要填写。
- `basisValue`：当请求 Body 是明细参数时传 `{ "paramKey": "<明细上下文paramKey>", "label": "<明细名>" }`，编译器写入平台 `basisValue` 和 `basisValueFormula`。
- `inputParams`：请求参数赋值列表。每项必须指定真实的参数分组、参数名和赋值表达式；CLI 会把它写入对应请求参数行的 `formulaData`，保留接口详情原有的 `request.tables` 及参数元数据。

输入参数格式是固定的：

```json
{
  "inputParams": [
    { "table": "Header", "paramKey": "Authorization", "value": { "kind": "fixed", "value": "Bearer xxx" } },
    { "table": "Params", "paramKey": "requestId", "value": { "kind": "context", "paramKey": "requestId", "label": "流程ID" } },
    { "table": "Header", "paramKey": "userid", "value": { "kind": "system_variable", "key": "{userid}" } }
  ]
}
```

`table` 只能是接口详情实际返回的 `Params`、`Header`、`Body`、`Url` 或 `Cookie`；`paramKey` 必须精确匹配该分组的真实参数（包括 JSON/明细字段的完整路径）。`value` 使用统一赋值类型，除上例外还可使用已支持的 `function`、`formula`、`variable`、`constant`、`transform` 和 `query_result`；变量/常量必须先按 `references/dynamic_resources.md` 解析，函数参数仍按函数目录的真实参数名和数量填写。CLI 会在保存前校验分组和参数是否存在，不能猜参数或静默新增参数。

## 示例

以下只展示结构，ID 和 `request` 必须替换为当前租户真实接口详情回读值：

```json
{
  "type": "Http",
  "params": {
    "systemId": "<当前租户HTTP连接器ID>",
    "resourceId": "<该连接器的资源ID>",
    "interfaceId": "<该资源的接口ID>",
    "address": "https://api.example.com/project",
    "requestMethod": "POST",
    "request": {
      "<接口详情返回的原生字段>": "<按平台参数设计器保存的原值>"
    },
    "response": {
      "<接口详情返回的原生响应字段>": "<按平台参数设计器保存的原值>"
    }
  }
}
```

`response` 仍必须使用接口详情返回的原生对象。`request` 的结构和参数元数据不能用通用对象替换；但请求字段的赋值可以通过 `inputParams` 使用统一的固定值、上下文、系统变量或函数/公式语义，CLI 会转换成前端真实的 `formulaData` 协议。没有真实原生对象或参数不在接口详情中时，停止生成并先补齐接口上下文。
