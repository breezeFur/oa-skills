# 标准函数规则

`custom`（自定义 JS）和 `code`（编码函数）不支持跨环境生成。其余标准函数内置名称、类别和参数约束。

需要计算、转换或拼接时，函数树可用于组件明确支持的公式属性：e-builder 的 `formula` 字段、流程/文档的 `formula_or_reference` 字段，以及 `ApproveCreate.requestName`。写法统一为：

```json
{"kind":"function","name":"CONCAT","args":[{"kind":"fixed","value":"项目-"},{"kind":"context","paramKey":"<真实字段paramKey>","label":"项目名称"}]}
```

函数参数可为 `fixed`、`context`、`variable`、`constant`、`system_variable` 或嵌套 `function`。其中 `variable`/`constant` 必须先按 `references/dynamic_resources.md` 解析为当前租户的真实资源 ID；不能把名称或默认值当作引用。

生成时仅对实际使用的函数调用当前租户接口，校验可用性并获取当次函数 ID。

消息标题/内容、循环和条件各有专用 DTO；只有对应组件说明明确支持函数树时才使用，不能因为它们也显示“动态赋值”就套用通用函数结构。
