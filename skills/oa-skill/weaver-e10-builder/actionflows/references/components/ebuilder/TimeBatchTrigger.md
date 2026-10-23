# 定时批量触发（`TimeBatchTrigger`）

## 何时使用

按一次、按小时、按日、按周、按月或 Quartz Cron 表达式扫描 e-builder 表单中满足条件的数据，并逐条触发后续动作。

## 先查询

查询数据源、查询/筛选字段与操作人。

## 不可猜测

批量筛选只能使用数据源真实字段；操作人不能使用文本或不存在的系统别名。

`rate` 使用平台原生频率编码：`1` 一次、`2` 按小时、`3` 按日、`4` 按周、`5` 按月、`6` Cron。图形化频率需要 `startTime`；按小时/日/周用 `cycle` 或指定列表，按月用 `day`、`atWeek` 或 `lastWeek`。`orderFields` 支持查询排序；`endTime` 支持定时窗口；`openRetryFlag` 支持失败补偿。

## 最小计划

`dataSource`、`rate`、`startTime`、`operator`；按需求补充频率子项、查询字段、筛选条件、`orderFields`、`endTime` 和 `openRetryFlag`。未明确限制 `queryFields` 时不要传它（或传空数组），CLI 会默认全选主表和系统字段，包含后续链接/赋值需要的“数据ID”。Cron 模式使用 `rate=6` + `cornString`，例如每天 10:00：`0 0 10 * * ?`。
