# 简单定时器（`SimpleScheduler`）

## 何时使用

按一次、按小时、按日、按周、按月或 Quartz Cron 表达式定时触发。

## 先查询

无需外部对象；确认业务时间规则。

## 参数

`rate` 为定时频率：`1` 一次、`2` 按小时、`3` 按日、`4` 按周、`5` 按月、`6` Cron。图形化频率需要 `startTime`；按小时/日/周用 `cycle` 或指定列表，按月用 `day`、`atWeek` 或 `lastWeek`。选择 `rate=6` 时才需要 `cornString`，例如每天 10:00：`0 0 10 * * ?`。`endTime` 和 `openRetry` 可选。

图形化频率直接使用平台原生字段，不要自行换算成 Cron；只有明确选择 `rate=6` 时才传 Cron。

## 最小计划

`rate`、`startTime`；按需求补充 `cycle`、`hour`、`day`、`week`、`atWeek`、`atWeekDetail`、`lastWeek`、`endTime`、`openRetry`。Cron 模式使用 `rate=6` + `cornString`。
