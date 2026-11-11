# 数据列表配置字段

仅在查询数据列表配置详情时读取本文件。以接口当前返回值为准；不同版本可能缺少字段或改变布尔开关的表示类型，解释时保留原值。

## 响应定位

- 列表名称：逐层展开嵌套 `data` 后取得的 `page.name`。
- 列表配置：固定读取 `data.page.comps[1].config`。
- `listId` 以该配置的 `ebListId` 为准，`objId` 以该配置的 `objId` 为准。菜单 `pageId` 仅用于请求 `viewPageInfo`，不拿它和 `ebListId` 反复匹配。
- `comps[1]`、`config`、`ebListId` 或 `objId` 缺失时停止并报告结构问题；不扫描其他组件或使用其他字段回退。
- `config.name` 是组件名称，不能替代页面中的列表名称。

## 基础设置

| 字段 | 含义 |
| --- | --- |
| `ebListId` | 数据列表视图 ID。 |
| `objId` | 数据源表单对象 ID。 |
| `mode` | 当前显示模式；它是有效字段，`modeType` 已废弃。 |
| `pageSize` / `detailPageSize` | 主列表或明细列表分页大小。 |
| `hideTableHeader` | 是否隐藏表头。 |
| `hideCheckbox` | 是否隐藏或禁用勾选框；保留接口返回的布尔或 `0/1` 类型。 |
| `operatColumnFixation` | 是否固定操作列。 |
| `enableSpreadTop` | 是否显示“展开至顶部”。 |
| `isShowFollow` | 是否启用关注。 |
| `readState` | 是否启用已读/未读状态。 |
| `batchAdd` / `batchEdit` / `batchEditValue` | 批量新增、批量修改、批量更改字段值开关。 |
| `setTop` / `setTopType` / `setTopRule` | 数据置顶开关、类型和规则；类型通常为规则置顶 `1`、手动置顶 `2`。 |
| `enableGroup` | 老版本分组配置；后端已废弃但老数据继续使用。 |
| `tableMergeMainData` | 明细数据中是否合并主表数据。 |
| `subFormMain` | 是否按子表主配置处理。 |
| `filterWithMainId` | 是否使用主数据 ID 做宽松过滤。 |

`mode` 的已知值：

| 值 | 显示模式 |
| --- | --- |
| `1` | 表格式 |
| `2` | 列表式 |
| `3` | 左图式 |
| `4` | 横向列表式 |
| `5` | 上图式 |
| `6` | 左定位表格 |
| `7` | 网格列表 |
| `8` | 可编辑表格（数据） |
| `9` | 可编辑表格（只读） |
| `11` | 可编辑表格（编辑） |
| `12` | 极简列表 |
| `13` | 极简左对齐图片 |
| `14` | 极简横向列表 |
| `15` | 极简顶部图片 |
| `17` | 极简网格列表 |

不要猜测未列出的模式值。

## 显示列

| 字段 | 含义 |
| --- | --- |
| `tableField` | 表格式显示列。 |
| `listField` | 列表式显示字段。 |
| `logicField` | 逻辑流使用字段。 |
| `picField` | 图片字段。 |
| `tableMergeFields` | 合并列配置。 |
| `personalFields` | 个性化列配置。 |
| `excelDisabledFieldIds` | Excel 中禁用的字段 ID。 |
| `cardLayout` | 卡片布局及字段事件信息。 |
| `fieldUsage` | 当前列表使用到的完整字段集合。 |
| `extendArea` | 扩展区域及其字段配置。 |

展示字段时优先列出 `id`、`name`、`text`、`objId`、`type`、`compType`、`mainField`、`mainPrimaryKey`。不要根据名称猜测缺失的字段元数据。

## 排序

- `order`：排序字段数组，`orderType` 通常为 `ASC` 或 `DESC`。
- `refEbuilderDataset`：关联其他 eBuilder 数据源时的排序数据集信息。
- `order` 缺失或为空表示没有显式排序配置，不能据此断言数据库没有默认顺序。

## 搜索

`searchConditions` 是可搜索项配置，不是当前用户提交的查询值。常见字段：

- `commonFilters`：常用搜索字段。
- `quickFilters`：快速搜索字段。
- `groupFilters`：分组搜索字段。
- `commonFilterGroups`：搜索字段分组。
- `commonSearchType`：常用搜索展示方式。
- `needCondition`、`manualFilter`、`searchRelationEnable`：搜索面板及组合关系开关。

常见 `conditionTypeValue`：`eq` 等于、`neq` 不等于、`like` 包含、`notLike` 不包含、`isNull` 为空。

## 统计

`listStatistics` 保存列表统计设置：

- `statisticsPosition`：统计展示位置。
- `statisticsManualLoad`：是否手动加载统计。
- `enableStatisticsFilterData`：是否让统计跟随筛选数据。
- `statisticsList`：统计项；若接口返回该数组，按统计项 ID 或字段映射解释，不默认取第一项。

常见 `statisticsType`：`sum`、`count`、`avg`、`max`、`min`。

## 条件

- `filter`：列表固定条件树。
- `filterIsNull`：固定条件是否为空的兼容标记。
- `isFilterSub`：是否过滤明细子表。
- `checkboxDisabledSet`：勾选框禁用条件。

条件树中的字段对象和数据源元数据必须保持完整。SQL 条件中的 `condition` 可能是数据集 ID，不应当作原始 SQL 文本解释。

## 兼容性

`EbListConfig` 在通用 `NListConfig` 上扩展 `ebListId`、`objId`、`readState`、`subFormMain`、`filterWithMainId`。运行接口还可能追加实体类未声明的配置，如 `listStatistics`。处理结果时把未归类字段放入 `otherConfig`，查询结果中不要静默丢弃它们。
