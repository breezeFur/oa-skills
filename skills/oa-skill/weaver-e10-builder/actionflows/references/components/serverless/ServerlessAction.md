# serverless/Action（`ServerlessAction`）

## 何时使用

用于执行平台的二开代码。`crossService=1` 时调用远程 serverless/Action 服务；`crossService=0` 时执行本地上传的 Java 类。

## 参数

```json
{
  "actions": [
    {
      "type": "ServerlessAction",
      "params": {
        "codeType": "customAction",
        "crossService": 1,
        "groupId": "ces",
        "serverVersion": "1.1",
        "request": {
          "primaryKey": "",
          "name": "",
          "tableId": "<ParamMappingBean.tableId>",
          "mappingTableId": "<ParamMappingBean.mappingTableId>",
          "tableData": []
        },
        "response": {
          "primaryKey": "",
          "name": "",
          "tableId": "<ParamSettingBean.tableId>",
          "tableData": []
        }
      }
    }
  ]
}
```

- `codeType` 当前仅支持 `customAction`。
- `crossService=1` 时必须提供 `groupId`，`serverVersion` 按 provider/consumer 约定填写，可为空；`crossService=0` 时必须提供本地代码完整类路径 `address`。
- `request` 必须使用前端输入参数配置生成的原生 `ParamMappingBean`；`response` 必须使用前端输出参数配置生成的原生 `ParamSettingBean`。
- 参数行的 `id`、`parentId`、`paramKey`、`paramType`、`dataType` 和前端高级配置会被保留；缺失的参数表/字段 ID 由 CLI 补齐，不能用语义字符串替代原生结构。
- 二开动作执行后，可以引用 `Response.entry.<字段>` 上下文；请求参数上下文使用 `Request.entry.<字段>`。
