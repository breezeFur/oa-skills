# 内置 MQ 监听（`InnerMQListener`）

## 何时使用

需求明确要求监听平台内置 MQ 广播 Topic 时使用。它不同于外部 RabbitMQ/Kafka 等 `MqConsumer`。

## 参数

```json
{
  "event": {
    "type": "InnerMQListener",
    "params": {
      "queueName": "真实Topic名称",
      "sendModel": "1",
      "receiveParams": {
        "tableId": "<平台参数表 ID>",
        "tableData": [{
          "id": "<平台字段 ID>",
          "paramKey": "payload",
          "paramName": "payload",
          "showName": "消息体",
          "paramType": "string",
          "dataType": "attribute",
          "required": true,
          "arrs": false
        }]
      }
    }
  }
}
```

- `queueName` 必填，使用平台真实 Topic/队列名称。
- `sendModel` 当前只支持 `1`（广播模式），省略时 CLI 默认填入 `1`。
- `receiveParams` 可选；有业务接收字段时传平台原生 `ParamSettingBean`，在当前设计器回读结构中表现为 `tableId + tableData`，没有时省略。不能传 `{type:'SETTING', tables:[]}` 期待它自动生成输入字段。
- 参数表中的“高级设置”（命名空间、默认值、敏感词等）目前没有独立的 CLI 参数或生成校验；如果已经取得平台完整的 `receiveParams` 原生对象，CLI 会随对象透传，但不会根据简化字段替你创建这些配置。

根触发器图标不是猜测的 `Icon-message-queue`，平台内置 MQ 监听实际使用 `Icon-built-in-mq-listening-mcolor`；不要把发送动作的图标当成监听触发器图标。

`InnerMQListener` 与动作 `InnerMQSend` 不能同时出现在一个动作流中，包括条件和循环内部；CLI 会在创建或更新前拒绝该计划。
