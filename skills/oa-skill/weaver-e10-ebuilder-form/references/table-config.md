# eBuilder 表格（List）配置说明

本说明只适用于传统表格视图（`List`），不适用于数据列表（`NList`）。所有 ID 均按字符串处理。

## 读取链路

本 skill 先只凭 `tableId` 调用：

```text
POST /api/ebuilder/form/list/listInit
{"listId":"{tableId}"}
```

从 `data` 动态取得 `appId`、`objid`、`name`、`conditionId` 和 `viewType`，随后读取六类配置：

这些配置统一通过前台登录态接口 `/api/ebuilder/form/...` 读取。

| 分类 | 接口 | 有效数据 |
| --- | --- | --- |
| 基础设置 | `GET /api/ebuilder/form/list/getBaseInfo/{tableId}` | `data` |
| 显示列 | `GET /api/ebuilder/form/list/getListFields/{tableId}` | `data.pc`、`data.mobile` 等 |
| 排序 | `GET /api/ebuilder/form/viewlist/getViewOrder` | `data[]` |
| 搜索 | `GET /api/ebuilder/form/listFilter/getSearchFilters/{tableId}` | `data` |
| 统计 | `GET /api/ebuilder/form/listStatistics/getStatisticsList/{tableId}` | `data` |
| 条件 | `GET /api/ebuilder/form/plugin/conditionEditor/getById` | `data.rootdata` |

配置接口的公共参数为 `apid={appId}`、`tpaid={tableId}`、`objId={objId}`。显示列还传 `clientType=PC`；显示列、排序、搜索、统计传 `isVirtualForm=false`；排序传 `viewType=tableView&viewId={tableId}`；搜索传 `viewType=tableView`；条件传 `id={conditionId}&type=search`。

`getMainFieldsByObjId`、`getDetailFieldsByObjId`、`getDetailFormByObjId`、`getOptionsForAdd` 是配置编辑器的候选项接口，不代表当前已保存配置，所以不并入结果。

## 基础设置

基础配置位于 `config.basicSettings`。常用字段：

| 字段 | 含义 |
| --- | --- |
| `id`、`name` | 表格 ID、名称 |
| `listModeType` | 展示样式；通常区分表格、卡片/小卡片、可编辑列表 |
| `pageSize`、`pageMode` | 每页条数、分页模式 |
| `showTitle`、`hideCheckbox` | 是否显示标题、是否隐藏复选框 |
| `operatColumnFixation` | 操作列固定方式 |
| `batchEdit`、`batchEditFields`、`batchEditValue` | 批量编辑开关、字段和取值设置 |
| `batchAdd`、`batchAddFields` | 批量新增开关和字段 |
| `setTop`、`setTopType` | 置顶开关和方式 |
| `readState`、`isShowFollow` | 已读状态、关注显示 |
| `openChildList`、`expandLevel`、`expandNumLimit` | 子表展开及层级/数量限制 |
| `gridRow`、`gridCol`、`gridWidthType`、`gridHeightType` | 卡片网格及宽高策略 |
| `dataRangeType`、`listDataRange` | 数据范围类型和配置 |
| `searchRelationEnable`、`manualFilter`、`quickSearchTextArea` | 搜索关系、手动筛选、快捷搜索多行文本能力 |

未列出的字段仍需原样返回；不要把兼容字段丢弃。

## 显示列

`config.displayColumns.pc` 是 PC 当前显示列，`mobile` 是移动端当前显示列。`groupFields`、`mergeColumnInfoList`、`subMergeColumnInfoList` 保存分组列及主/明细合并列信息。

列字段常见含义：

| 字段 | 含义 |
| --- | --- |
| `fieldId`、`showName`、`fieldType`、`componentKey` | 字段 ID、显示名、业务类型、组件类型 |
| `showOrder`、`width`、`widthUnit`、`alignment` | 顺序、宽度、单位、对齐 |
| `fixed`、`hiddenColumn`、`wrapSetting` | 固定列、隐藏列、换行设置 |
| `hrefLink`、`hrefType`、`openType`、`pageWidth` | 链接、链接类型、打开方式、页面宽度 |
| `formulaType`、`formulaRange` | 公式显示方式和范围 |
| `isSubForm`、`subFieldList` | 是否明细字段及明细字段配置 |
| `fieldConfig`、`conversionSet` | 扩展字段配置和转换设置 |

## 排序

`config.sorting` 是已保存排序数组。每项通常包含 `fieldId`、`fieldName`、`fieldType`、`componentKey`、`orderType`、`showOrder`；`orderType=asc` 为升序，`desc` 为降序。空数组表示未配置固定排序。

## 搜索

`config.search` 的核心结构：

- `commonFilters`：常用/高级搜索字段。
- `quickFilters`：快捷搜索字段。
- `groupFilters`：分类搜索字段。
- `commonSearchType`：搜索展示模式。
- `fixedCol`、`fixedColCount`：搜索区固定列设置。
- `commonFilterGroupsJson`：搜索分组关系。
- `searchRelationEnable`：是否允许搜索关系配置。
- `manualFilter`：是否启用手动筛选。
- `noneOfShow`、`hideFilterField`：空选项/字段显隐设置。
- `quickSearchTextArea`：快捷搜索是否支持多行文本场景。

过滤项中的 `fieldId`、`fieldShowName`、`fieldType`、`componentKey` 标识字段；比较符、默认值、显示顺序等以接口实际返回为准。

## 统计

`config.statistics` 常见字段：

| 字段 | 含义 |
| --- | --- |
| `statisticsPosition` | 统计显示位置，如 `top`、`topSimple`、`topRight` |
| `statisticsManualLoad` | 是否手动加载统计值 |
| `enableStatisticsFilterData` | 是否启用“统计过滤后的数据” |
| `statisticsList` | 已保存的统计项 |

统计项的常见计算类型为 `sum`、`count`、`avg`、`max`、`min`，具体字段、格式和关联表单信息以 `statisticsList` 返回为准。空数组表示未配置统计项。

## 条件

`listInit.data.conditionId` 是条件配置 ID；读取时使用 `type=search`。只有 `getById` 实际返回非空 `rootdata` 才算已配置：

- `config.conditions.configured=true`：`rootData` 是解析后的条件树。
- `config.conditions.configured=false`：未配置固定条件，即使 `conditionId` 本身非空也不要误判。

条件树保留服务端节点、逻辑关系、比较符和值，不擅自改写为搜索配置。
