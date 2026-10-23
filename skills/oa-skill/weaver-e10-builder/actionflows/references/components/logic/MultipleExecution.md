# 循环（MultipleExecution）

循环体通过 `actions` 提供，至少包含一个非 `Output` 动作，当前不支持循环嵌套。

## 循环方式

| `cycleMode` | 场景 | 必填参数 |
| --- | --- | --- |
| `1` | 按指定次数 | `cycleTimes` |
| `2` | 满足条件时继续 | `condition` |
| `3` | 按列表逐条遍历 | `detailData` |
| `4` | 按列表分批遍历 | `batchDetailData`、`batchSizeData` |
| `5` | 存在下一页时继续 | `pageCycleData`（平台已有变量 FormulaBean） |

## 参数规则

- `cycleTimes`：固定整数 `1-1000`，或实时上下文的 `context/reference`。动态引用必须使用 `getComponentContext` 返回的完整 `paramKey`；预检会保留来源字段的真实类型、所属组件和参数路径。
- `detailData` / `batchDetailData`：只能引用真实 List/数组字段（表单明细、多选浏览框或上游动态列表）。不可用普通文本字段伪装为列表。
- `batchSizeData`：固定整数 `2-1000`。
- `condition`：使用 ESB `ConditionRule`，与动作流分支复用同一类规则树和 `saveCondition` 持久化；它不是 e-builder 表单动作的 `filterInput/ConditionSet`。左值可使用完整 `paramKey`、字段显示名、`paramName` 或真实字段 ID；编译器会按当前流程实时上下文回填真实 DTO。
- `pageCycleData`：设计器会创建布尔变量并在循环体首节点写入“是否存在下一页”。当前只接受已存在的原始 `type: "7"` 变量 FormulaBean；尚未自动创建变量及赋值节点时，不生成该模式。

## 示例

```json
{
  "type": "MultipleExecution",
  "params": {
    "cycleMode": "3",
    "detailData": {
      "kind": "context",
      "source": "event",
      "paramKey": "<workflowId>.<arrayField>[]"
    }
  },
  "actions": [{ "type": "SendMessage", "params": { "receiver": { "type": "all" }, "msgTitlev": "逐条处理", "msgContentv": "..." } }]
}
```
