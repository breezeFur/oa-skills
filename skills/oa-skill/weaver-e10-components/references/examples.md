# 已验证实例与可复用经验

来源：聊天“查找线下合同评审迁移记录”的组件导出记录，以及本项目 2026-10-22 可视化拖拽副本源码与 2026-10-26 编辑前快照。只提炼机制，不依赖该项目文件在其他机器存在，不复制业务数据、认证或固定资源 ID。

历史现用组件包括指标卡、图表、明细表、期间筛选、环形占比和比例条。`ContractEditable…_1022` 是该项目已有组件标识，不是新组件命名规则。后续修改需实时读取当前平台，历史源码不代表最新部署状态。

已在源码核实的面板字段：

| 类型 | 历史开放字段 |
|---|---|
| 通用 | title、cardWidth、cardHeight、accentColor、cardBackground、titleFontSize、valueFontSize、cornerRadius、height、note |
| 指标卡 | bindingCode、bindingField、bindingUnit、panelsJson、hint |
| 图表 | sources、labelField、valueField、secondaryField、unit、chartKind、topCount |
| 表格 | code、columnsJson、columnLabels、visibleColumnNames |

这些历史字段均使用 `TEXTAREA`；panelsJson/columnsJson 等有 JSON 语法和数组校验。新的技能应补齐具体结构和业务字段校验。历史图表标签列出的图形类型也需要检查渲染分支，不能仅凭标签宣称全部支持。

旧源码中的业务 API、主页面 ID、主题选择器和默认跳转应用等是项目定制痕迹；可复用组件需改为实例配置或运行上下文。某个配置字段适用于图表但不适用于指标卡时，不照搬整份通用面板，避免无效配置。

历史导出已取得 6 个原生包；尚未提供目标环境导入验收证据。此经验只支持“原生接口能够生成并下载包”，不支持“跨环境迁移已经验证”。
