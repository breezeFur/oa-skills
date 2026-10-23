# e-builder 按钮触发（`EventButton`）

## 何时使用

需求明确为点击 e-builder 表单上的某个按钮时触发。它与 `EventFormData` 不同：后者只监听数据变动，不能识别是由哪个按钮触发。

## 先查询

1. 用 `form-search '{"keyword":"<表名>"}'` 按表名直接拿到表单 `objId` 与所属业务应用 `appId`（同名表多于一条时按 `appName` 收窄，应用名同名多命中或查无会直接报错并给候选，改用 `appId`）；只知道应用时用 `form-applications` → `form-list`。返回体 `truncated: true` 表示还有命中未返回，**据此判定表单不存在是错的**，应按 `appName` 收窄或传 `{"max":0}`。
2. 用 `e10-cli actionflow form-buttons '{"tableId":"<表单ID>","appId":"<应用ID>"}'` 读取真实按钮 ID、名称与启用状态。

不要按按钮名称猜测 ID，也不要创建按钮作为生成动作流的隐含步骤。

## 最小计划

```json
{
  "event": {
    "type": "EventButton",
    "params": {
      "targetForm": {"groupId":"<应用ID>","id":"<表单ID>"},
      "buttonType": [{"id":"<按钮ID>","name":"<按钮名称>","buttonLocation":"after"}],
      "triggerType": "sequence"
    }
  }
}
```

`buttonLocation` 只能是 `before`（按钮默认动作前）或 `after`（默认动作后）。多选记录场景的 `triggerType` 为 `sequence`、`merge` 或 `parallel`。需要异步时在对应按钮项写 `asyncExecution:true`。

## 上下文

触发后可引用 `FormData`、`FormField`、`FormButton`、`SettingInfo`、`accessId` 和 `monitorId`。先通过组件上下文预检获取当前租户的字段，禁止猜测字段路径。
