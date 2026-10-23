# 动态赋值资源：变量与常量

动态赋值中的变量、常量不是普通文本，也不能直接把名称写进 `value`。CLI 会在生成阶段读取当前租户资源，必要时先创建资源，再把真实 ID 编译为平台 FormulaBean：变量是 `type:"7"`，常量是 `type:"5"`。

## 使用已有资源

```json
{"kind":"variable","id":"<当前动作流已有变量ID>","name":"批次号"}
{"kind":"constant","id":"<当前租户常量ID>","name":"接口地址"}
```

变量必须属于当前动作流的 `applicationId + sceneId`；常量按租户范围读取，可跨动作流使用。不能只传名称冒充 ID。生成时找不到真实资源会在保存前失败。

## 按计划新建资源

```json
{
  "variables": [{"ref":"批次变量","name":"批次变量","type":"string","value":""}],
  "constantDefinitions": [{"ref":"服务地址","name":"服务地址","groupName":"接口配置","contentType":"string","content":"https://example.test"}],
  "actions": [{"type":"ActionEbUpdate","params":{"constants":{"<目标字段>":{"kind":"variable","name":"批次变量"}}}}]
}
```

- `variables[]` 调用 `application/variable/addVariable`，变量绑定本次新建动作流场景；类型使用平台值 `string`、`int`、`double`、`boolean`、`date`、`time`、`datetime`。
- `constantDefinitions[]` 调用 `constant/save`；填写 `groupPk` 使用已有分组，填写 `groupName` 时按精确名称复用已有分组，不存在才调用 `constant/saveConstGroup` 新建分组。
- 新建定义用 `{kind:"variable",name:"..."}` 或 `{kind:"constant",name:"..."}` 引用；也可以直接传平台真实 `id`。
- `constants` 仍表示“目标字段 → 固定/动态赋值”的属性名，不与顶层 `constantDefinitions` 混用。固定值继续写 `{kind:"fixed",value:"..."}`。
- 同一个动作流只能用自身变量；更新已有动作流时使用当前版本的变量 ID，CLI 不会把另一个动作流的变量 ID 自动迁移。

## CLI 发现与创建

```bash
e10-cli actionflow variable-list '{"applicationId":"<应用ID>","sceneId":"<场景ID>"}'
e10-cli actionflow variable-create '{"applicationId":"<应用ID>","sceneId":"<场景ID>","name":"批次变量","type":"string","value":""}'
e10-cli actionflow constant-list
e10-cli actionflow constant-group-list
e10-cli actionflow constant-group-create '{"groupName":"接口配置"}'
e10-cli actionflow constant-create '{"groupPk":"<分组ID>","name":"服务地址","contentType":"string","content":"..."}'
```

完整平台响应可用 CLI 的 `--out` 保存，终端只看摘要；不要根据截断输出判断资源是否创建成功。凭据和敏感常量值不写入 Skill、计划或 Git。
