# 设计器组件层指南（骨架）

> 本文件为 `SKILL.md` 的子模块，在用户配置具体组件时加载。
>
> **重要**：组件层**不是原生后端接口**——平台没有按组件类型分的 HTTP 端点。所有组件配置最终落地经 `designer save`（POST `/layout/save`，见 `guide-designer.md`）：读布局 → 改 `comps[].config` → 保存。本骨架只给机制与接口能确定的 Slide 字段；**其余组件 config 字段集与取值枚举接口未给，须运行时 inspect 真实页面查 `comp.config`，不凭空构造**（盲造触发 ERR-007/008 崩页）。
>
> 本 skill 自包含分发，不依赖任何本机样本文件；"inspect 真实页面"指用户对自己的页面运行 `designer layout <pageId> --json` 查看实际 comp.config，是运行时操作。

---

## 机制说明

所有组件配置的工作流一致：

```bash
# 1. 导出布局（作为 save 入参基础，取自 /layout/list）。--json 走 stdout，日志走 stderr，故 `>` 只收 JSON 干净；勿 `2>&1` 混入日志
e10-cli designer layout <pageId> --terminal all --json > layouts.json
# 2. 定位目标 comp，改 comp.config.<字段>
# 3. 保存（comps 整体重传）
e10-cli designer save <pageId> --layouts @layouts.json
```

> **保真规则**：save 是浅合并，入参取自 `/layout/list`、**只构造 `comps`**（见 `guide-designer.md`「入参数据来源铁律」）。改 comp.config 子字段后，整个 comps 数组随 save 重传；`pageId`/`terminalType`/`module`/`ecodeVersion`/`appId` 等元数据保持原值不动。
>
> **save 必须含两端**：`layouts.json` 要含 **PC + MOBILE 两端**（用 `--terminal all` 导出）。只传 PC 端 save 会**覆盖丢失 MOBILE 端布局**（save 是整页覆盖，不是按端 merge）。
>
> **PC/MOBILE 同名组件**经 `refCompId` 互连——改一端 config 时注意另一端是否需同步。

### 自定义 CSS

组件的外观有两层：`comp.config.styles[N].customStyle` 下的**图形化样式块**（`title`/`content`/`footer`/`container` 的字号、背景、边框等），以及其中的 **`base.codeSource` 自由文本 CSS**。后者就是需求里说的「自定义 CSS」。

- 干净组件的 `styles` 是**空数组**；Picture/CountDown 之类自带**主题绑定记录**（`useComStyle:true`），与自由 CSS 记录是两回事，**不要碰**。
- 不要绕开命令直接改布局 JSON，也不要去动 `sourceCode.cssCache`（平台的编译产物）。
- 用 `e10-cli designer css read/write` 读写，用 `e10-cli designer dom <type>` 查该组件的 DOM 结构来写选择器。

完整契约、选择器作用域速查、27 个组件的 DOM 文档对照表与各条坑 → `guide-designer-css.md`。

---

## 接口给出的组件字段（Slide 一例）

接口文档（layout-save §4.3 config 内部结构 + §6.1 完整 Slide 入参）只给 Slide 一个完整 config 示例。**只有 Slide 的字段名是接口确定的**，可照此修改：

| config 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String | 组件显示名 |
| `title` / `titleEnabled` | String / Boolean | 标题文本 / 是否启用 |
| `footerEnabled` | Boolean | 是否启用页脚 |
| `pics` | Array | 图片列表 |
| `imageMode` | String | 图片填充模式 |
| `switchEffect` | String | 切换效果 |
| `intervalTime` | Object | 轮播间隔 `{type, value}` |
| `speed` | Integer | 切换速度（ms） |
| `lazyLoad` | Boolean | 是否懒加载 |
| `imgSourceType` | String | 图片来源类型 |
| `eventGroup` | Array | 事件配置列表 |
| `filter` | **Object** | 数据过滤条件（HTTP 契约：filter 类型为 Object，传 `[]` 与契约不符） |
| `showNum` | Integer | 展示数量 |
| `layout` | Object | 栅格布局 `{i, x, y, w, h, ...}` |
| `flow` / `disabled` | Object | 流程 / 禁用配置 |

> **需 inspect 真实页面查原始值**：上表**字段名**来自接口 Slide 示例；但 `imageMode`/`switchEffect`/`imgSourceType` 等字段的**完整取值枚举接口未给**（示例仅各一例）——须 inspect 自己已配好的 Slide 组件查可选值，勿凭枚举造。

---

## 其余组件（Calendar / DigitalPanel / Chart / NavPanel / List 等）

> 除 Slide 外，各组件 config 字段集与取值枚举**接口文档均未给出**。下表**字段名**来自示例页面结构（非穷尽、非权威，以 inspect 真实页面为准）；**取值**一律须运行时 inspect 自己的页面 `comp.config` 查，不赋空值（`字段=''`/`[]`/`{}` 凭空造值会触发 ERR-007/008）。

| 组件 type | config 顶层字段（结构示例，取值须 inspect） |
|---|---|
| `DigitalPanel` | name/type/title/titleEnabled/footerEnabled/panels/showmode/columns/timedRefresh/layout/flow/disabled/styles |
| `NavPanel` | name/type/title/titleEnabled/column/pageColumn/enableGroup/menuConfig/menuSourceType/showSearch/commonMenu*/groupMode/openType/userSource/groupBrowser/menuBrowser/menuDisplayRange/externalDataInterfaceSetting/actionTemplateStr/layout/flow/disabled/styles |
| `Pie` / `Bar` / `Line`（图表） | name/type/title/titleEnabled/topOperatBtns/measures/dimensions/height/barType(Bar)/label(Bar)/filterVersion/dataset/filter/searchConditions/dataListDisplay/xAxis/yAxis/showTotal/showLimit/hideForNoData/tools/layout/flow/disabled/styles |
| `NList`（列表） | name/type/mode/pageMode/title/titleEnabled/footerEnabled/pageSize/headMerge/listVersion/dataset/order/filter/tableField/personalFields/searchConditions/enableGroup/filterIsNull/isFilterSub/version/rootStr/fieldUsage/layout/flow/disabled/styles |
| `Calendar`（日历） | name/type/title/titleEnabled/footerEnabled/calendarType/condition/defaultView/weekStart/filter/showViewModeChange/viewModeSelectType/showLunar/useAttendanceHoliday/monthChangeAutoSelectFirstDate/dataSetNodes/baseInfo/historyData/topOperatBtns/bottomOperatBtns/commonConditionSetting/layout/flow/disabled/styles |
| `Circular`/`BarStack`/`HBar`/`HBarStack`/`Nightingale`/`Gauge`/`Treemap`/`Bubble`（新增图表） | name/type/title/titleEnabled/topOperatBtns/showTopOperatBtnConfig/measures/dimensions/height/[label/chartType/totalTitle 因类型而异]/layout/flow/disabled/styles/filterVersion/hasCssCache |
| `Picture`（图片） | name/type/title/titleEnabled/footerEnabled/width/height/path/position/imageMode/imgFormat/textTitle/textDescribe/styles/layout/flow/disabled |
| `NewTab`（标签页） | name/type/title/titleEnabled/footerEnabled/rerender/tabs/addChildAfterSelect/topOperatBtns/layout/flow/disabled/styles/displayName |
| `CollapsePanel`（折叠面板） | name/type/title/titleEnabled/footerEnabled/panels/spreadType/expandAll/layout/flow/disabled/styles/displayName |
| `ProgressChart`（进度条） | name/type/title/titleEnabled/rangeColor/dataset/denominator/showText/showName/valueType/layout/flow/disabled/styles |
| `NavBar`（导航栏） | name/type/title/titleEnabled/navMenus/rightArrow/separator/splitBgColor/layout/flow/disabled/styles |
| `NavMenu`（导航菜单） | name/type/fixedArea/dataSource/showType/showMore/hideSelf/showPortal/showWorkMessage/navMenus/remember/leftSider/layout/flow/disabled/styles |
| `CountDown`（倒计时） | name/type/title/titleEnabled/topOperatBtns/timingType/endType/deadline/paramName/countDownSettings/layout/flow/disabled |
| `SearchGlobal`（搜索框） | name/type/title/titleEnabled/footerEnabled/fixedArea/layout/flow/disabled/styles |
| `EbButton`（按钮） | name/type/titleEnabled/footerEnabled/btnText/btnType/size/btnKind/groupSize/showExpandIcon/btnGroup/showBtnNum/layout/flow/disabled/styles |
| `FastCreate`（快速新建） | name/type/title/labelPosition/moduleType/setPersonnel/showTimeField/relatedPersonnel/enterAdd/layout/flow/disabled/styles |
| `PageHeader`（页头） | name/type/title/titleEnabled/icon/newButtons/underTheTitle/layout/flow/disabled/styles/displayName |
| `Comment`（评论） | name/type/commentTitle/title/showEmpty/hasEdit/showEditAvatar/showListAvatar/pageSize/showSource/showTime/moduleValue/componentShowType/displaySetting/targetId/layout/flow/disabled/styles |

> 配置流程（**数据绑定的条目结构怎么填，参考 `assets/factory/example-configured.json`（原8组件）/ `example-configured-2.json`（新增20组件）**——已配置好的整页范例，业务值替占位，照 `comps[].config` 里各绑定的真实填充结构填）：
> 1. `designer comp-add <pageId> --type <Type> --template @<file>` 用 factory 模板（平台初始态）克隆出干净 comp；
> 2. 参考 `example-configured.json`/`example-configured-2.json` 里同类型 comp 的 `config`，把数据绑定（tableField/measures/dimensions/menuConfig/panels/pics 等）用你自己表单的真实 fieldId/objId 填进去；
> 3. `designer save`。
>
> 组件 `type`/`package`/`category`/`applyStyle`/`styleCategoryCompKey`/`styleCategoryPackage` 同样从真实 comp 复制真实值，不编造、不赋空。
>
> **机器随机 id 硬规则**：页面/组件配置里**所有由工具生成的随机 hex 机器 id 首位都不能是数字**（后端校验，浏览器样本首位恒为 a-f 字母）：`comp.id`(32 位)、图表 `axisId`(32 位)/`shortKey`(7 位，平台数据行/分组键)、NavPanel 菜单项/事件组/事件 id、DigitalPanel panel id 等。CLI `designer chart`/`digital-panel`/`nav-panel` 已统一用 `genLetterHex()`（首位强制 a-f）自动生成；agent 手工改 config 时须遵守同规则。真实数字标识（objId/pageId/formId/字段 id）照常可数字开头，勿动。

---

## 加/删组件

加组件 = 向对应 `terminalType` 的 `comps[]` push 一个 config**完整**的新 `LayoutComponentEntity` → `designer save`。删组件 = 从 `comps[]` 移除 → save。

- **comp id**：前端生成的 32 位无连字符 UUID（接口 §4.3 comps id 字段约束）。
- **config 完整性**：config 字段必须完整，缺字段崩页（ERR-007/008）。
- **加组件首选 factory 模式**：`designer comp-add <pageId> --type <Type> --template @<file>` 用本 skill 自带的 `assets/factory/factory-<name>.json`（28 组件均有，原8源 2ganjing/新增20源 0805yuanshi 平台初始态、绑定空），克隆后参考 `example-configured.json`/`example-configured-2.json` 填数据绑定。详见 `guide-designer-factory.md`。勿凭空拼装 config（除 Slide 外字段集接口未给，盲造 ERR-007/008）。

> 删组件 = 从 `comps[]` 移除目标 comp 后 `designer save`。

---

## 相关指南

- 布局层（info/layout/save/lock/position）→ `guide-designer.md`
- 自定义 CSS 与组件 DOM 结构索引（`designer css` / `designer dom`）→ `guide-designer-css.md`
- 工厂模板（comp-add 复制机制）→ `guide-designer-factory.md`
- 版本层（list/revert）→ `guide-designer-version.md`
- 命令速查 → `../common/ref-cli-commands.md`「designer」节
