# 条件分支（`Condition`）

## 何时使用

根据上游字段进入 if/else if/else 分支。

## 先查询

查询当前触发器的真实上下文字段及字段类型。

## 不可猜测

条件左值只能引用当前可见上下文；右值、操作符和字段类型必须匹配。未知操作符或类型不兼容必须报错，不能静默改成“等于”。无法通过条件编辑器实际回显时，不伪称已验证。

右值使用 `fixed`、`system`、`context` 之一；动态右值传 `type:"context"` 和真实 `paramKey`，或传平台回读的完整 `formula`。不要把动态字段名当作固定字符串。

## 保存与回读

分支条件由运行时在预暂存注册来源节点后保存：取得真实 `mapBaseId`，保存完整 `childrens` 树，并以保存响应的真实 `conditionId/mapBaseId/mapId` 回填设计。顶层 `relationship` 直接作为根关系，不能再包一层相同关系的子组；只有 plan 明确写出的嵌套 AND/OR 才保留嵌套。新建后 `getExpressionBean` 可能只返回分组骨架，不能以它覆盖完整叶子树。所有平台 Long ID 都按字符串处理；最终以动作流暂存回读和设计器弹窗确认。

## 最小计划

`branches`，每个 if/else if 有真实 `condition`，每个分支有动作列表。
