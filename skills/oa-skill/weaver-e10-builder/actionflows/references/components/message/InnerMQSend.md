# 内置 MQ 发送（`InnerMQSend`）

## 何时使用

向平台内置 MQ 的 Topic/队列发送消息时使用。它不是外部 MQ 连接器的生产者动作。

## 参数

```json
{
  "actions": [
    {
      "type": "InnerMQSend",
      "params": {
        "queueName": "真实Topic名称",
        "sendModel": "1",
        "sendParams": "<平台 InnerMqComponentDTO.sendParams 原生 ParamMappingBean>",
        "inputParams": [
          { "paramKey": "payload", "value": { "kind": "context", "paramKey": "<真实字段paramKey>", "label": "消息体" } }
        ]
      }
    }
  ]
}
```

- `queueName` 和 `sendParams` 必填；固定 Topic 直接传字符串，CLI 会转换为平台所需的 `FormulaBean`。
- `queueName` 也可以传统一动态赋值或平台原生 `FormulaBean`，包括上下文、系统变量、变量、常量和函数。
- `sendModel` 为 `1` 广播模式或 `2` 集群模式，省略时默认 `1`。
- `sendParams` 必须来自平台发送参数设计器的原生 `ParamMappingBean`，不要用 `receiveParams` 或普通字符串替代。
- 需要给发送参数赋值时使用 `inputParams`。`paramKey` 必须命中 `sendParams.tableData` 的真实参数；`value` 支持固定值、上下文、系统变量、变量、常量、查询结果和函数/公式，CLI 会写入该行的 `formulaData`，不会重建参数定义。

### 参数类型与数据类型联动

`tableData` 中每一行的 `paramType` 决定 `dataType` 的合法候选和是否允许继续加下级，不能只把 `dataType` 当成一个任意字符串填写：

- 普通标量（如 `string`、`int`、`boolean` 等）且 `arrs:false` 时，合法数据类型只有“属性”；平台因此不会显示数据类型下拉，这是正常行为。
- `arrs:true` 时，平台允许在该参数类型对应的多个数据类型中选择；数组参数的 `paramKey` 回读时可能规范化为带 `[]` 的形式。
- `json`、`xml`、`xml_string` 是结构化参数，可以通过 `parentId` 组织下级参数；下级参数仍需按自身 `paramType` 和父节点限制填写，不能把结构化参数拍平成普通标量。
- 数据类型下拉是否显示是设计器根据参数类型、数组标志、父节点和固定类型限制计算出来的 UI 状态，不由服务端仅凭 `dataType` 字段强行打开。

因此，需求只要求一个数据类型时不要伪造下拉；需求需要多种数据类型或下级节点时，必须按真实参数类型构造 `tableData` 层级。

`InnerMQSend` 与触发器 `InnerMQListener` 不能同时出现在一个动作流中，包括条件和循环内部；CLI 会在创建或更新前拒绝该计划。
