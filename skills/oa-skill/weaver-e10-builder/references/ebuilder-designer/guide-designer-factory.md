# 设计器工厂模板指南

> 本文件为 `SKILL.md` 的子模块，在用户用 `designer comp-add --template` 加组件、或需要参考"如何配置组件"时加载。
>
> 本 skill **自带打包**两类资产（`assets/factory/`），全部封装、自包含：
> - **factory 模板**（`factory-*.json`）：从【纯拖拽未配置】的初始态样本抽取——平台真实初始结构/默认值/字段类型，comp.config 原样保留（无业务数据、无配置期多余字段）。源页对个别组件若非纯初始态（Comment 已绑 `targetId`/`moduleValue`、Picture/CountDown 的 `styles[]` 携源页 `themeId`/样式记录 ID），打包时已把源页残留长 ID 剥掉 → 置空，对齐原 8「`styles:[]` 无长 ID 无绑定」的干净初始态。**greenfield 用户开箱即用 `comp-add --template`**，不依赖已有页面。
> - **example-configured(-N).json**：从【已配置】的真实页面 genericize——**领域无关**：含 CJK 字符的串视为业务值 → `<value>`（平台结构/枚举/CSS/图标路径均为 ASCII，业务内容必含中文，故对任何业务域通用，无需维护业务词表）；`fieldId`/`objId/业务值`→`<id>`/`<value>`、`field_<n>`→`<field_name>`、`ft_<n>`→`<form_table>`、UUID→`<uid>`，留结构与枚举——一份"配置范例页"，**供学习完整配置方式**（tableField 列项、measures/dimensions 度量维度、menuConfig 菜单项、panels 指标卡、pics 图片等的填充结构），以后遇到用户需求不至于配置错误。

---

## 工厂模板概念

factory 模板 = 平台纯拖拽初始态的 comp（PC+MOBILE 对，config 字段完整、绑定全空）。`designer comp-add <type> --template @<file>` 时作为新 comp 的**复制源**：替换 `id`（生成新 32 位 UUID）+ 重连 `refCompId`（PC/MOBILE 互指）→ push 进对应 `terminalType` 的 `comps[]` → `designer save`。

**为什么用 factory（初始态）而不是凭空构造**：
- 接口（layout-save §4.3/§6.1）要求 comps 的 `config` 字段**完整**，缺字段崩页（ERR-007/008）。
- 接口只给 Slide 一例完整 config；其余组件 config 字段集未给，无法凭契约拼装。
- factory 取自平台真实拖拽初始态（字段名/类型/默认值都是平台原样），克隆即得干净可用的 comp，再按 `example-configured.json` 的范例填数据绑定。

**filter 形态跟平台真实**：factory 的 filter 是平台拖拽初始值（Slide=`[]` 数组、Calendar=`{commonFilters:[]}`、NList/图表无 filter 键）——跟 `/layout/list` 返回一致，往返 save 不冲突。（注：layout-save.md 契约表写 filter=Object，与平台 Slide 实际返回的 `[]` 不一致，以平台真实为准。）

> **机制依据**：`designer save` 入参铁律——layouts 取自 `/layout/list`、只构造 `comps`（见 `guide-designer.md`）。comp-add 的 factory 模式即"提供一份完整 comps 元素供复制"。

---

## 打包的资产清单

路径前缀 = 本 skill 的 `assets/factory/`。

**克隆起点（factory 模板，平台初始态，绑定空）**：

原有 8 组件（源 2ganjing）：

| 文件 | 组件 type | 用途 |
|---|---|---|
| `factory-slide.json` | `Slide` | 幻灯片轮播 |
| `factory-digital-panel.json` | `DigitalPanel` | 数字面板（指标卡） |
| `factory-nav-panel.json` | `NavPanel` | 导航面板 |
| `factory-pie.json` | `Pie` | 饼图 |
| `factory-bar.json` | `Bar` | 柱状图 |
| `factory-line.json` | `Line` | 折线图 |
| `factory-nlist.json` | `NList` | 数据列表 |
| `factory-calendar.json` | `Calendar` | 日历 |

新增 20 组件（源 0805yuanshi）：

| 文件 | 组件 type | 用途 | h(算出) |
|---|---|---|---|
| `factory-circular.json` | `Circular` | 环形图 | 34 |
| `factory-bar-stack.json` | `BarStack` | 堆叠柱图 | 34 |
| `factory-h-bar.json` | `HBar` | 横向柱图 | 34 |
| `factory-h-bar-stack.json` | `HBarStack` | 横向堆叠柱图 | 34 |
| `factory-nightingale.json` | `Nightingale` | 南丁格尔玫瑰图 | 34 |
| `factory-gauge.json` | `Gauge` | 仪表盘 | 34 |
| `factory-treemap.json` | `Treemap` | 矩形树图 | 34 |
| `factory-bubble.json` | `Bubble` | 气泡图 | 34 |
| `factory-picture.json` | `Picture` | 图片 | 24 |
| `factory-progress-chart.json` | `ProgressChart` | 进度条 | 15 |
| `factory-collapse-panel.json` | `CollapsePanel` | 折叠面板 | 21 |
| `factory-new-tab.json` | `NewTab` | 标签页 | 24 |
| `factory-nav-bar.json` | `NavBar` | 导航栏 | 6 |
| `factory-nav-menu.json` | `NavMenu` | 导航菜单 | 6 |
| `factory-page-header.json` | `PageHeader` | 页头 | 8 |
| `factory-count-down.json` | `CountDown` | 倒计时 | 15 |
| `factory-search-global.json` | `SearchGlobal` | 搜索框 | 8 |
| `factory-eb-button.json` | `EbButton` | 按钮 | 5 |
| `factory-fast-create.json` | `FastCreate` | 快速新建 | 13 |
| `factory-comment.json` | `Comment` | 评论 | 29 |
| `chart-dimensions.json` | — | 图表维度样本（Employee/Date/Select/String，`chart dimension-add --template` 用） | — |

**配置范例（学习如何填数据绑定）**：

| 文件 | 用途 |
|---|---|
| `example-configured.json` | 原 8 组件【已配置】整页（源 0804111），genericize 占位，留结构与枚举。学习 tableField/measures/dimensions/menuConfig/panels/pics 等填充结构 |
| `example-configured-2.json` | 新增 20 组件【已配置】整页（源 0805peizhi），同 genericize。学习 Circular/BarStack/HBar/HBarStack/Nightingale/Gauge/Treemap/Bubble/Picture/NewTab/CollapsePanel/NavBar/NavMenu/CountDown/SearchGlobal/EbButton/FastCreate/PageHeader/Comment 的配置结构。 |
| `example-btn-progress-collapse-configured.json` | **按钮/进度条/折叠面板【已配置】范例**（源 333anniu4，genericize：19 位 ID→`<id>`、中文→`<value>`、保留 `{username}/{userid}` 平台变量）。学习：EbButton 两种 btnKind（`levelBtnGroup`/`tileBtnGroup`）+ btnGroup[].eventGroup NewPage 跳页 + children 子菜单；ProgressChart 数据驱动（dataset/denominator `80{pay.field_<id>}`/`100{all.field_<id>}` + rangeColor + molecularName/denominatorName.nameAlias）；CollapsePanel 2 panel + flow.linkedNodes 映射 InternalContainer 子件 + panel content `{username}{userid}` 变量。**填补 example-2 缺 ProgressChart 的空缺**。 |

---

## comp-add --template 命令

| 命令 | 说明 |
|------|------|
| `e10-cli designer comp-add <pageId> --template <名\|@file> [--type <Type>] [--x --y --w --h]` | 从 factory 模板读 comp（**模板名直传**：`pie`/`bar`/`nlist`/`slide`… 28 个内置；也可 `@<文件路径>` 或 `designer layout --json` 导出的布局），生成新 32 位 UUID + refCompId 互连，push 到对应 terminalType comps，save。`--type` 与模板 type 不一致会拒绝；`--h` 按下方「组件高度判断」自行算 |

> **坑**：
> - factory 模板名直接传：`comp-add --template pie`（CLI 内置发现，28 组件全有）；也可传 `@<文件路径>` 或任意布局 JSON 路径。`designer factory-list` 列出全部内置模板名↔type 对照。
> - `designer layout <pageId> --json` 输出完整布局 JSON，可作 `comp-add` 的 `--template`。`--json` 是**全局选项**（`--help` 在全局有列），普通 `designer layout` 输出是格式化摘要，不能当模板。
> - **免登录页（EB_ANONYMOUS_PAGE）不支持需登录态的组件**——`Comment`/`SearchGlobal`/`FastCreate` 在 EB_ANONYMOUS_PAGE 报错（要当前用户上下文）。须建普通 `EB_PAGE` 页承载（`page create <name> <appId> --module EB_PAGE`，默认即 EB_PAGE；参数顺序：名称在前）。
> - factory 模板的 `measures`/`dimensions` 已清空成 `[]`（初始态，绑定全空）。克隆后用 `chart measure-add`/`dimension-add` 加。

---

## 组件高度判断（自行算，不预设）

`comp-add`/`designer position` 的 `--h` 是**栅格行数**，**实际像素 = h × 行高(px)**。高度过低 → 内容被裁切显示不完全。**不要套预设值，按组件内容 + 页行高自行算 h**：

**铁律**：组件内容高度 ≤ h × 行高，否则裁切。拿不准就**慷慨给 h**（多留白别裁切），加完浏览器打开页面核对，裁切就 `designer position <pageId> <compId> --h <更大值> --yes` 往上调。

> **配置完字段后必回核高度宽度（2026-08-06 验证）**：comp-add 时给的 h 是初始值，**配置完字段（绑数据/嵌套子组件/事件/添加内容项）后要按内容项数 + 宽度回核 `layout.h/w`**——**高度是内容驱动 + 宽度感知的**：NavBar/NavMenu 有 N 个导航项→`h = 8 + ceil(N / floor(w/3)) × 8`（**w6→4项2行≈h24-25，w12→1行≈h16**，半宽时项换行要更高）；DigitalPanel N 张卡→`h = 8 + ceil(N/floor(w/3))×8`（w6 2×2≈h24）；CollapsePanel N 面板+1 展开→`4N+12`（4面板≈h28-30）；NavPanel N 菜单同公式；NList 按 pageSize；图表按 config.height÷行高（≈34）；FastCreate/SearchGlobal≈h15（1.5×初始h10）。尤其 NewTab/CollapsePanel：`autoHeight:true` 在嵌套内容未注册时缩到仅壳（如 4.8）→ 设计页不显示嵌套。

> **美观布局：多列栅格（别全 w12 纵堆）**——28 组件全 w12 纵堆成超长列不美观。推荐多列栅格分组：
> ```
> [PageHeader w12]
> [NavBar w6][NavMenu w6]
> [SearchGlobal w4][EbButton w4][FastCreate w4]
> [DigitalPanel w12][Slide w12]
> [Pie w4][Bar w4][Line w4]     ← 图表3列网格(w4 h34)
> [Circular w4][HBar w4][Nightingale w4]
> [BarStack w4][HBarStack w4][Treemap w4]
> [Gauge w4][Bubble w4][ProgressChart w4]
> [CountDown w6][Picture w6]
> [NewTab w12][CollapsePanel w12]
> [NList w8][NavPanel w4]
> [Calendar w12][Comment w12]
> ```
> 多列栅格用 `designer position` 手设 x/y/w/h（按分组），**不跑 `designer auto-height`**（auto-height 是单列 w12 纵堆模式，会覆盖多列 w）。两种模式：① 单列快速定高→`designer auto-height <pageId>`（w12，按内容算 h+纵堆 y，改后自动保存）；② 多列美观栅格→手设 x/y/w/h（按上面分组，同行同高，y 按 max(行内高) 累加）。**w6 的 NavBar 4 项要 h24-25**（半宽换行），不是单列的 h16。
>
> **自动化：跑 `designer auto-height <pageId>` 一键按内容定高 + 重排 y**（不用手算，改后自动保存）：
> ```bash
> e10-cli designer auto-height <pageId>   # 按 navMenus/panels/pageSize/newButtons/config.height 等内容算 h + 重排 y + autoHeight=false，保存
> e10-cli designer unlock <pageId>        # 收尾解锁
> ```
> 规则：顶层组件（无 flow.parent）按原 y 顺序重排 y=累加 h、`autoHeight=false` 防缩；嵌套子组件（IC/子按钮 flow.parent 有值）不动（IC 内相对坐标，IC autoHeight 自撑高）。公式（CLI 内置）：PageHeader=8+按钮行、NavBar/NavMenu=8+ceil(项数/floor(w/3))×8、NavPanel/DigitalPanel=8+ceil(项数/column)×8、CollapsePanel=4×面板数+12、NList=8+ceil(pageSize×1.5)、图表=ceil(height/10.7)。**配完所有组件字段后必跑一次**，省手算且不漏。

**行高怎么取**（每页不同，必须查）：
- `designer layout <pageId> --json`，看页面 `config.style.layout.rowHeight`（若有直接用）。
- 没标 rowHeight 的，按经验区间 **10.7~16.4px/行**估算；**未知时取安全下界 10.7px/行**算（保证最坏情况不裁切）。

**按组件内容算 h**（内容高度 ÷ 行高，向上取整）：

| 组件 | 内容高度依据 | 算法 |
|---|---|---|
| 图表（Pie/Bar/Line + 新增 Circular/BarStack/HBar/HBarStack/Nightingale/Gauge/Treemap/Bubble） | `config.height`（px，默认 360） | `h = ceil(config.height / 行高)`；360px ÷10.7 ≈ 34 |
| 图片 Picture | 图片显示高度（height=100% 填满 comp） | `h = ceil(250 / 行高)` ≈ 24（按图高调） |
| 进度条 ProgressChart | 进度条 ~150px | `h = ceil(150 / 行高)` ≈ 15 |
| 折叠面板 CollapsePanel | 面板内容 ~220px | `h = ceil(220 / 行高)` ≈ 21 |
| 标签页 NewTab | 标签栏+内容区 ~250px | `h = ceil(250 / 行高)` ≈ 24 |
| 导航栏 NavBar / 导航菜单 NavMenu | ~60px | `h = ceil(60 / 行高)` ≈ 6 |
| 页头 PageHeader | ~80px | `h = ceil(80 / 行高)` ≈ 8 |
| 倒计时 CountDown | ~150px | `h = ceil(150 / 行高)` ≈ 15 |
| 搜索框 SearchGlobal | ~80px | `h = ceil(80 / 行高)` ≈ 8 |
| 按钮 EbButton | ~50px | `h = ceil(50 / 行高)` ≈ 5 |
| 快速新建 FastCreate | ~130px | `h = ceil(130 / 行高)` ≈ 13 |
| 评论 Comment | 评论列表 ~300px（可滚轮） | `h = ceil(300 / 行高)` ≈ 29 |
| 数字面板 DigitalPanel | 卡片高（单行约 100-130px）× 卡片行数（`panels` 数 ÷ `columns`） | `h = ceil(卡片行数 × 单卡高 / 行高)` |
| 列表 NList | `pageSize` × 列表行高（约 32-40px/行） | `h = ceil(pageSize × 列表行高 / 行高)`；**列表可滚轮控制上下**，h 不必塞下全部行——给能显示 pageSize 行的值即可，更小也行（滚轮补） |
| 幻灯片 Slide | banner 内容，约 250-410px | `h = ceil(内容高度 / 行高)` |
| 导航面板 NavPanel | 菜单项数 ÷ 每行列数(`column`) = 菜单行数 × 单行高 | `h = ceil(菜单行数 × 单行高 / 行高)`；菜单可分页，h 适中 |
| 日历 Calendar | 月视图约 6 行 day-cell，约 360-400px | `h = ceil(月视图高度 / 行高)` |

> **堆叠**：多个组件上下排时 `--y` = 上一个 y + 上一个 h。列表可滚轮所以 h 适中；其余组件**一开始就给够高度**，别裁切。
>
> factory 模板里的 `layout.h` 已按各组件内容 + 安全行高 10.7px/行**自行算好**（图表/日历 h=34、列表 h=30、幻灯片 h=29、数字面板 h=13、导航 h=15）——是合适默认，克隆即不裁切（按最坏行高 10.7 算，实际页行高更高则更宽裕）。**但若该页行高 < 10.7 仍可能裁切**：comp-add 后浏览器打开核对，裁切就 `designer position <pageId> <compId> --h <更大值> --yes` 往上调。仍按上方方法自行判断，别死套 factory 的 h。

---

## 克隆后必做：重绑数据到自己的表单

factory 模板是平台初始态（绑定全空），克隆后须把数据绑到**你自己的表单**。**下列 6 类组件有 setter 子命令，全部 CLI 直配**（2026-09-07 验证全通；绑定条目由 CLI 从 `/api/ebuilder/common/ds/fields` 取平台原样字段对象自动构造，physicalField/browserParams/formInfo 填齐，**不会出现维度错填/幽灵空槽**；`--field-id` 传字段名或 fieldId 均可）：

- **数字面板（DigitalPanel）**：`designer digital-panel panel-add <pageId> <compId> --obj-id --app-id --field-id <数字字段id|名> --aggregator <SUM|COUNT|AVG|MAX|MIN> --label "<标题>"`。每项聚合一个字段。
- **图表（全 11 种）**：`designer chart dataset-set <pageId> <compId> --obj-id --app-id --text "<表单名>"` → `chart measure-add`（SUM/AVG/MAX/MIN 用 `--field-id`；COUNT 用 `--count-records`）→ `chart dimension-add --field-id <id|名> --text`（**不再需要 --type/--template**）→ `chart title --text`。Date 维度自动按月。像素高度 `chart height --px <n>`。

> **组件标题用业务名（必做）**：comp-add 出来的 title 是 factory 默认占位（"标题"/"饼图"/"折线图"/"柱状图"/"图片"/"按钮"/"导航面板"等），**配完每个组件必须设业务标题**——图表 `designer chart title <pageId> <compId> --text "<业务名>" --enabled on --yes`（标题=维度+度量描述：饼图→分布占比如"订单状态分布"、柱图→对比如"客户等级消费对比"、折线→趋势如"月度销售趋势"、堆积→构成分解如"各月订单金额与运费"）；非图表脚本改 `config.title/titleEnabled`（NavPanel→"业务导航"、DigitalPanel→"销售KPI指标"、NList→"销售订单明细"、CollapsePanel→"业务模块"等）。**别留 factory 默认占位名**，不美观也不专业。

- **数字面板（DigitalPanel）**：`designer digital-panel panel-add <pageId> <compId> --obj-id --app-id --field-id <Number字段fieldId> --aggregator <SUM|COUNT|AVG|MAX|MIN> --label "<标题>"`。每项聚合一个 Number 字段；fieldId 一次写对并核对（手误少几位会取数错）。
- **图表（Pie/Bar/Line + 新增 Circular/BarStack/HBar/HBarStack/Nightingale/Gauge/Treemap/Bubble）**：同用 `designer chart dataset-set <pageId> <compId> --obj-id --app-id --text "<表单名>"` 绑顶层 dataset；`designer chart measure-add` 加度量（COUNT 用 `--count-records` 按数据id；SUM/AVG/MAX/MIN 用 `--field-id` 指 Number 字段）；`designer chart dimension-add <pageId> <compId> --type <Employee|Date|Select> --template @<skill>/assets/factory/chart-dimensions.json --obj-id --app-id --field-id --text`（`--type` + `--template` 都必填，template 是含该 type 维度的图表布局文件）。factory 模板的 `measures`/`dimensions` 已清空（初始态），必须用上面 setter 加。

> **factory 图表模板字段完整性（2026-08-05 已修）**：8 个新增图表（Circular/BarStack/HBar/HBarStack/Nightingale/Gauge/Treemap/Bubble）的 factory 模板曾**缺 22 个 config 字段**（`xAxis`/`yAxis`/`scatterColor`/`scatterSize`/`dataset`/`filter`/`markLine`/`dataListDisplay`/`eventGroup`/`nodesShowRange`/`measureName`/`yoyDimensions` 等）→ 平台崩页「设计页/预览页不显示」（尤以 Bubble 明显，旧记 Circular/Nightingale/Gauge 预览不显示同因）+ `measure-add` 后出现幽灵空 measure 槽 `{format:NONEFORMAT}`（须运行时 node 删）。**已修**：factory 模板按 `example-configured-2.json` 同类型 comp 补全这 22 字段（绑定类 `dataset.id/text/appId`、`eventGroup`、`dataListDisplay.fieldList` 留空，结构类 `xAxis`/`markLine` 等照范例默认值），comp-add 出来即结构完整、`measure-add` 不再产生空槽。**维护者换样本时务必保留这 22 字段**（别在清洗时剥掉它们），否则回归崩页+空槽。

> **各图表类型的度量/维度配方**（源自 `example-configured-2.json` 验证，照此配不踩坑）：
>
> | 图表 | 度量 measures | 维度 dimensions |
> |---|---|---|
> | Pie / Bar / Line / Circular / Nightingale / HBar / Treemap / Bubble | 1×SUM（`--field-id` 指 Number 字段） | 1（`--type` 按字段类型 Employee/Date/Select） |
> | **BarStack / HBarStack（堆叠）** | **2×SUM**（两个 Number 字段，各 `measure-add` 一次） | 1（堆叠按此维度分组） |
> | **Gauge（仪表盘）** | 1×**COUNT**（`--count-records` 按数据id，记记录数） | 0（**不配维度**） |
>
> ⚠️ 堆叠图是 **2 度量 + 1 维度**，不是「1 度量 + 2 维度」；Gauge 用 COUNT 不用 SUM 且不配维度。具体每个 measure/dimension 的字段绑定结构对照 `example-configured-2.json` 里同类型 comp 的 `config.measures`/`config.dimensions` 填。
- **列表（NList）**：`designer list dataset-set <pageId> <compId> --obj-id --app-id --text` 绑 dataset（factory 初始态无 dataset 也直配，无需模板克隆）；`list field-add <pageId> <compId> --field-id <id|名> --obj-id --text --type <类型> --comp-type <类型>`（两处同值：Text/Select/DateComponent/Money/NumberComponent/Employee 等）；`list order-add --field-id --obj-id [--desc]`。
- **导航面板（NavPanel）**：`designer nav-panel menu-add <pageId> <compId> --name "<菜单名>" --to-page <目标pageId>` 加跳页菜单项（双层 eventGroup 自动构造）。factory 克隆出的 NavPanel `menuSourceType=DEFAULT`（取应用默认菜单树）——**DEFAULT 下自定义菜单项正常渲染**。若要切自定义菜单来源用 `designer nav-panel menu-source-type <pageId> <compId> CUSTOM`。`groupBrowser`/`menuBrowser` 须界面配（样本为空）。
- **幻灯片（Slide）**：`designer slide pic-add <pageId> <compId> --url "<imgUrl>"`。**坑**：`imgUrl` 须**平台资源路径**（如 `/build/ebdcoms/images/cover/cover_1.png`），本地路径（`D:/...`）浏览器不可达显示破图；e10-cli 无图片上传命令，本地图须设计器界面上传或用平台内置 cover 资源。**Git Bash MSYS 路径转换已内置防护**（`/build/...` 被转成 `C:/Program Files/Git/...` 会自动还原）。
- **日历（Calendar）**：`designer calendar dataset-bind <pageId> <compId> --obj-id --app-id --text --start <开始Date字段> --end <结束Date字段> --title-field <标题字段>` 绑数据源（**内置 dataShowType 全视图数组** `["2","4","3","5"]` + baseInfo，事件直接渲染，无需再脚本补字段）；`designer calendar field-map <pageId> <compId> [--start] [--end|clear] [--title-field]` 调映射（`--end clear` 做全天单日事件）；`calendar title`。**坑**：日历开始/结束 Date 字段**建表单时一次建全**更稳。

> 组件标题用业务名：图表/日历/幻灯/导航面板用各自 `title` 子命令；DigitalPanel/NList 配置时传 `--label`/`--text` 即业务名。改完收尾 `designer save` + `designer unlock`。

- **新增非图表组件（Picture/ProgressChart/CollapsePanel/NewTab/NavBar/NavMenu/CountDown/SearchGlobal/EbButton/FastCreate/PageHeader/Comment）**：**这 12 个组件 CLI 无专属 setter 子命令**（`designer <comp>` 会报 unknown command，勿试）。factory 模板已自带平台初始态，克隆后配置方式 = `designer layout <pageId> --json > layouts.json` 导出 → 用脚本（node/python）改目标 comp 的 `config`（参照 `assets/factory/example-configured-2.json` 或 `example-btn-progress-collapse-configured.json` 里同类型 comp 的 `config` 结构填）→ `designer save <pageId> --layouts @layouts.json`。**图表类（全 11 种）有 setter**，统一走 `designer chart`。

> **非图表组件配置方法（2026-08-05，含范例 `example-btn-progress-collapse-configured.json`）**：
> - **Picture**：factory 模板 `config.path.url` 已填**平台内置 cover 图** `/build/ebdcoms/images/cover/cover_1.png`（greenfield-safe，跨租户可用），comp-add 即显示；**用户自行替换为自己的图片资源**（e10-cli 无图片上传命令，自换须设计器界面上传或用平台素材路径，见 Slide 条同款坑）。
> - **EbButton 事件/按钮组**：CLI 无 setter，但**可脚本配**。参照范例 EbButton（2 个，两种 btnKind）：`btnKind` = `btn`（单按钮）/ `levelBtnGroup`（下拉按钮组）/ `tileBtnGroup`（平铺按钮组）；`btnGroup[]` 每项可挂 `eventGroup`（NewPage 跳页：`linkInfo.page.{pageId,pageName,pageType:"PAGE",parentId:"pages",appid,openMode:"4"}`）+ `children`（子菜单，每项又可挂 eventGroup，`isSplit:true` 做分割线）。配按钮组样式另有 10 字段（`display/icon/defaultStyle/hoverStyle/groupBtnDefaultStyle/groupBtnHoverStyle/groupBtnPosition/subGroupBtnDefaultStyle/subGroupBtnHoverStyle/subGroupBtnPosition`，btnKind 非 `btn` 时出现）。配法：导出 layout → 改 comp.config.btnGroup/btnKind/eventGroup → save。
> - **ProgressChart 数据驱动（无需页面级数据集，CLI 可解）**：参照范例 + 收款页实践——`dataset`/`denominator` 用**直接 objId 表达式** `"{<formObjId>.field_<fieldId>}"`（如 `"{1300163811369664522.field_1300163811369664515}"`，验证收款页 `数据集:0` 照样数据驱动）。`rangeColor` 分段色（0-20 红/20-60 黄/60-100 蓝），`molecularName.nameAlias`/`denominatorName.nameAlias` 设分子/分母显示名，`valueType:"resultValue"`。factory 初始态 `dataset="80"`/`denominator="100"`（静态 80%），改成 objId 表达式即数据驱动。详见下方「深度配置踩坑」§5。
> - **CollapsePanel / NewTab 嵌套机制（已破解）**：容器通过 `config.flow.linkedNodes` 把每个 `panels[].id`/`tabs[].id` 映射到一个 **InternalContainer** 子件（canvas 容器），IC 的 `config.flow.parent` 反指父容器 id；`panels[].children`/`tabs[].children` 保持空 `[]`（嵌套不走 children）。**factory-collapse-panel.json / factory-new-tab.json 已把 `flow.linkedNodes`/`flow.nodes` 清空 `{}`/`[]`**——原模板带源页 IC id，comp-add 只克隆容器不克隆 IC，留悬空引用致 panel/tab 内容画板坏。清空后：comp-add 出来的容器不带悬空引用。**纯 CLI 可建嵌套**（见下方「非图表组件深度配置踩坑」§4：手加 InternalContainer comp + 双向连 `flow.linkedNodes`/`flow.parent`/`flow.nodes`，**不须开设计器 UI**）；用户在浏览器开设计器时 UI 也会为缺 IC 的 panel/tab 自动建一个。panel/tab `content` 支持 `{username}`/`{userid}` 等平台变量（范例：`{username}{userid}<value>`）。
> - **Chart Date 维度默认按月**：`dimension-add --type Date` 后维度即 `dateGroupType=month`/`format=yyyy-MM`（已确认），`chart dimension-date-group ... month` 会报"无实际改动"——GAP-002「Date 维度默认按天需手改月」**实际不触发**，Date 维度 add 后即按月。
> - **脏数据/greenfield**：factory 模板与范例文件均已 genericize（19 位业务 ID→`<id>`、中文→`<value>`、保留 `{username}`/`{userid}` 平台变量与图标/颜色结构），跨租户/跨用户机器开箱即用。维护者加新样本须跑 genericize（按本节规则：19 位 ID→`<id>`、CJK→`<value>`、`field_<n>`→`field_<id>`、保留平台变量），**别把源页 pageId/appid/fieldId/中文业务名带进封装**。

> **脚本改 config 坑**：用 python/node 脚本改 `layouts.json` 时，bash 变量别直接嵌进 heredoc（`python3 <<EOF ... $VAR ... EOF` 里 $VAR 展开易出错/丢空格）——把 pageId/fieldId 等作**命令行参数或环境变量**传给脚本（`python3 edit.py "$pageId" "$fieldId"` 或 `os.environ`），脚本内 `sys.argv`/`process.argv` 取。改完 `designer save --layouts @layouts.json`。

> **能力判断铁律**：配组件前先 `e10-cli designer <comp> --help` 查全部 setter 子命令再判断能力，不能凭印象说"CLI 配不了"。**仅 6 类注册组件有子命令**（calendar/slide/digital-panel/chart/nav-panel/list，均有 setter）；Picture/ProgressChart/CollapsePanel/NewTab/NavBar/NavMenu/CountDown/SearchGlobal/EbButton/FastCreate/PageHeader/Comment 等 **12 类无 setter，`designer <comp> --help` 会报 unknown command**，配置走 factory 模板 + 脚本改 `comp.config` + `designer save`。

---

## 组件业务用途与数据选取（先理解用户想看什么数据）

> 配组件前先想清楚"这块要回答什么业务问题"，再选组件类型 + 选度量/维度。**别机械地"有 Money 字段就绑 SUM"**——进度条的分子分母、堆积图的各层都要业务上说得通（同量纲、能相加/相比）。用户需求模糊就反问，别上来就 comp-add。

### 图表类（数据驱动，度量/维度选取是关键）

| 组件 | 业务用途 | 度量 measures | 维度 dimensions | 举例 |
|---|---|---|---|---|
| **ProgressChart 进度条** | **完成进度** = 已完成量/总量 | 分子=已完成量(SUM)、分母=总量(SUM)（**同量纲**） | —（无维度） | 收款进度=已收款金额/合同总额；付款进度=已付/应付；采购完成率=已采购/计划 |
| Pie/Circular/Nightingale 饼/环/玫瑰 | **占比构成** | 1×SUM（各类的量） | 1（分类） | 采购状态分布、付款方式占比 |
| Bar/HBar 柱/条形 | **对比排名** | 1×SUM | 1（分类） | 各供应商采购额对比、各月销售额 |
| Line 折线 | **趋势** | 1×SUM | 1（时间/类别，Date 按月） | 月度采购金额趋势 |
| **BarStack/HBarStack 堆积柱/条** | **总量的构成分解**（看总量+各部分占比） | 2+ SUM（**各构成部分**，业务上要能相加/同量纲） | 1（主分组） | 各月采购额按付款状态(已付/未付)堆积；各供应商采购额按品类堆积 |
| Gauge 仪表盘 | **单一关键指标/KPI** | 1×COUNT(记录数)或 SUM | —（无维度） | 本月采购总额、订单总数、达成率 |
| Treemap 矩形树图 | **层级占比**（面积=大小） | 1×SUM | 1（分类，**Select 或 String 均可**——验证 Select 客户等级 + String 客户名称都能正常显示） | 各供应商采购额占比（面积大=采购多） |
| Bubble 气泡 | **三维关系** | **1×SUM（只能选1个指标）** | 1（Date/分类） | 订单总额 by 月（X=维度，Y=度量值，气泡大小=值） |

> **堆积图要点**：2 个度量必须是"同一总量的构成部分"（如 已付+未付=应付总额，或 各品类金额=总采购额），不是任意两个 Number 字段。若用户要"看各月采购额+按状态分解"用堆积；只要"看各月采购额对比"用普通柱图。

### 容器/导航/展示类（非数据驱动，看用途配内容）

| 组件 | 业务用途 | 配什么 |
|---|---|---|
| NewTab/CollapsePanel 标签页/折叠面板 | 信息分区/导航 | tab/panel content 用 `{username}`/`{userid}` 变量或静态文本；内嵌子组件(图表/列表)放 InternalContainer（见深度配置 §4） |
| NavBar/NavMenu 导航 | 跳转入口 | navMenus 挂 eventGroup NewPage 跳真实页 |
| PageHeader 页头 | 页面标题+新建按钮 | newButtons 挂 NewPage |
| EbButton 按钮 | 操作动作(新建/导出/跳转) | btnGroup 挂事件；levelBtnGroup 做下拉菜单 |
| DigitalPanel 数字面板 | 多 KPI 指标卡(一眼看关键指标) | 每张卡聚合一个 Number 字段(SUM/COUNT/AVG) |
| NList 列表 | 看每条记录(明细) | 绑表单 dataset + tableField 列 |
| Calendar 日历 | 事件/日程(付款日历/交付日历) | 绑 Date(start/end)+title 字段 |
| SearchGlobal 全局搜索 | 跨表搜索入口 | 绑一个表单的搜索字段 |
| CountDown 倒计时 | 截止提醒(采购年度截止/合同到期) | deadline 设目标日期 |
| Comment 评论 | 协作讨论 | targetId 绑业务对象(表单) |
| Picture 图片 | 展示图 | path 用平台素材 |
| FastCreate 快速新建 | 快速创建业务记录(任务/目标/日程) | moduleType 选 task/goal/schedule |

### 数据选取原则
1. **先问业务问题**：用户说"做个采购看板"，先问想看哪些指标（总额/占比/趋势/明细/进度），别上来就 comp-add。
2. **度量同量纲可比较**：进度条分子分母、堆积图各层都要业务上能相加/相比（都 Money 或都 Number）——**别用 金额/数量 做比值**（无意义，本轮踩过）。
3. **维度选分类/时间**：饼/柱维度=分类(状态/类型)，折线/气泡维度=时间(Date 按月)。
4. **没合适字段就先建表单**：如要做"收款进度"，表单要有"已收款金额"+"合同总额"两个字段；没有就先 `form create/add-field` 补，再配图表。

---

## 非图表组件深度配置踩坑（2026-08-05 实操，必读）

> 以下坑来自「分期付款管理收款页面」38 comps 实操（全 28 组件 + 5 InternalContainer + 5 内嵌子按钮）。**脚本改 config 后必须回读校验**（见 §7）——壳字段/双层结构会骗脚本"以为配了实际没生效"。

### 1. eventGroup 必须双层 `[[obj]]`

平台结构是 `Array<Array<ClickEvent>>`——外层=事件组，内层=组内 click 事件。**单层 `[{CLICK}]` 预览点击不触发 = 没配**（本轮最深的坑：PageHeader newButtons / NavBar·NavMenu navMenus / EbButton btnGroup[].eventGroup 全失效，看起来像"没配"，实际是被平台吞了）。

正确结构（所有挂 eventGroup 的地方统一）：
```json
"eventGroup": [[
  { "type":"CLICK", "name":"单击", "id":"<uid>", "disableDelete":true,
    "events":[ { "id":"<uid>", "type":"NewPage", "linkInfo":{...} } ],
    "actionDesc":"<描述>" }
]]
```

**NewPage 跳页 `linkInfo.page` 两种形态**（别混）：
- **跳表单台账**：`pageType:"VIEWPORT"` / `pageId=<viewId>`（**viewId 非 objId**，从 `e10-cli form list-view <objId> <appId>` 取）/ `parentId:"Form_<objId>"` / `pageViewType:"NList"` / `appid` / `openMode:"4"`
- **跳自定义 EB 页**：`pageType:"PAGE"` / `pageId=<pageId>` / `parentId:"pages"` / `terminalScopes:"PC,MOBILE"` / `appid` / `openMode:"4"`

`linkInfo` 另含 `openMode`/`params:[]`/`name`/`flatToBottom:false`/`icon:{path:"#icon-eBuilder-o",style:{color:"#5d9cec",fillType:"borderColor",borderColor:"#5d9cec"}}`。

### 2. EbButton 下级按钮 children 子菜单

`btnKind` 三种（**均已验证可用**）：`btn`（单按钮）/ `levelBtnGroup`（下拉按钮组，点开下拉）/ `tileBtnGroup`（平铺，直接触发——按钮平铺展示，点击直接执行事件，非下拉）。

> **children 规则（2026-08-06 已确认，必读）**：
> - **btnGroup 必须 ≥2 项**；children **只能挂在 `btnGroup[1]`+（第2个及以后）**，`btnGroup[0]` 是叶子（无 children）。只有一个按钮时设 children 无效。
> - **带 children 的 btn 必须含 `actions:[]` + `isSplit:false` 两字段**（叶子 btn 不需要这俩）。**缺这俩会被平台 mangle**：children 被剥掉、该 btn 退化成 factory 默认"按钮"、children 错挪到 btn[0]。
> - 照 `0806jindutiao.json` 结构才不坏：`btn[0]={id,text,onlyIcon,hoverTip,btnGroupDisabled,eventGroup}`（叶子，无 children/无 actions）；`btn[1]={id,text,actions:[],onlyIcon,isSplit:false,hoverTip,btnGroupDisabled,children:[...],eventGroup}`（带 children + actions + isSplit）。
> - children 项也须含 `actions:[]`+`isSplit:false`（分割线项 `isSplit:true` 无 eventGroup）；`children[].parentId` 指向所属 `btnGroup[]` 项 id。

正确结构（≥2 按钮，children 在第2个）：
```json
"btnGroup":[
  { "id":"<b0>", "text":"新建订单", "onlyIcon":false, "hoverTip":"", "btnGroupDisabled":false,
    "eventGroup":[[ <click> ]] },   // btn[0] 叶子，无 children
  { "id":"<b1>", "text":"更多操作", "actions":[], "onlyIcon":false, "isSplit":false, "hoverTip":"", "btnGroupDisabled":false,
    "children":[
      { "id":"<uid>", "text":"<子项>", "actions":[], "onlyIcon":false, "isSplit":false, "hoverTip":"", "btnGroupDisabled":false, "parentId":"<b1>", "eventGroup":[[ <click> ]] },
      { "id":"<uid>", "text":"分割线", "actions":[], "isSplit":true },
      ...
    ],
    "eventGroup":[[ <click> ]] }   // btn[1] 带 children + actions + isSplit
  }
]

### 3. CountDown 截止时间在 `countDownSettings[].deadline`，不是顶层 deadline

顶层 `deadline` 是**壳字段**（默认值 `"default"`）。只改顶层 → 倒计时不倒数（停在建组件时的默认时刻，一直"已到期"）。真正生效在 `countDownSettings` 数组（支持多个倒计时）：
```json
"timingType":"day-hour-minute-second", "endType":"specifiedTime",
"countDownSettings":[
  { "id":"<uid>", "name":"<倒计时名>", "timingType":"day-hour-minute-second",
    "endType":"specifiedTime", "deadline":"2026-09-25T00:00:00", "paramName":"" }
]
```
`deadline` 用 **ISO** `YYYY-MM-DDTHH:mm:ss`。

### 4. NewTab / CollapsePanel 嵌套子组件（纯 CLI 可建，不须开 UI）

> **2026-08-06 从 `0806jindutiao.json` 验证**。**纠正旧说**：「CLI `designer save` 不自动建 IC，须开设计器 UI 触发」**不准确**——纯 CLI 可建嵌套，手动加 InternalContainer + 双向连 `flow`。**完全不用 `pid`**（所有 comp pid=null/""，嵌套全走 `flow.parent`/`flow.nodes`/`flow.linkedNodes`）。

**完整嵌套链（2026-08-06 从 000.json 验证，全部字段必配）**：
```
容器 (NewTab/CollapsePanel)
  ├─ flow.isCanvas = true                             ← 容器也要 isCanvas!
  ├─ flow.linkedNodes { <panelId/tabId>: <IC.id> }   ← panel/tab → IC
  ├─ flow.nodes [ <IC.id>, ... ]                    ← 直接子级 IC 列表
  └─ panels/tabs.children = []                      ← 不走 children（保持空）
InternalContainer (IC，每个 panel/tab 一个，是 canvas)
  ├─ flow.parent = <容器.id>                         ← IC → 容器（反向）
  ├─ flow.nodes [ <子组件.id>, ... ]                ← IC 里的子组件
  ├─ flow.isCanvas = true                            ← IC 必须有（画布渲染面）
  ├─ package = "" / category = ""                   ← 空字符串（不是 null）
  ├─ titleEnabled = false / hasCssCache = false
  └─ layout {i,x:0,y:0,w:12,h:10,hidden:false,scope:"",selected:false}  无 autoHeight/moved
子组件 (factory comp-add 的图表/列表/按钮，在 IC 里)
  └─ flow.parent = <IC.id>                          ← 子 → IC
  └─ pid = ""                                       ← 空字符串（不是 null）
```

**容器必配字段（照搬 000.json，缺一不显示）**：
- **NewTab**: `rerender:"on"` + `addChildAfterSelect:"notAllow"` + `topOperatBtns:{enabled:true,alignType:"CENTER",btns:[设置按钮]}` + **`autoHeight:true`**（不是 false！）+ `titleEnabled:false` + `flow.isCanvas:true` + tab ID 用 UUID
- **CollapsePanel**: `spreadType:"mutex"` + `expandAll:false` + **`autoHeight:true`** + `titleEnabled:false` + `flow.isCanvas:true` + panel ID 用 UUID
- **IC**: `flow.isCanvas:true` + `package:""` + `category:""` + `titleEnabled:false` + `hasCssCache:false` + layout 无 autoHeight/moved
- **子组件**: 用 **factory comp-add**（非脚本构造）——有完整 comp-level 字段（package/category/refCompId/applyStyle/prop/pid:""），脚本只改 `flow.parent=IC.id`

> **最大坑（2026-08-06 验证）**：之前设 `autoHeight:false`（防缩）是**错的**——容器要 `autoHeight:true` 才能撑开画布显示 IC 嵌套内容（false 把容器定死，设计页不渲染画布）。`autoHeight:true` + `flow.isCanvas:true`(IC+容器) + `rerender:"on"`(NewTab) + `spreadType:"mutex"`(CollapsePanel) 组合才能在设计页正常显示嵌套。

factory-collapse-panel.json / factory-new-tab.json 已清空 `flow.linkedNodes`/`flow.nodes`（去悬空源页 IC 引用）。建嵌套步骤：
1. comp-add NewTab/CollapsePanel（容器，flow 已空）
2. **InternalContainer 无 factory 模板**——用脚本在 `layouts.json` 里手加 InternalContainer comp（`type:"InternalContainer"`，`config` 含 `type/name/layout/flow:{parent:<容器id>}/displayName/titleEnabled/hasCssCache`）
3. 容器 `flow.linkedNodes[panelId] = IC.id` + 容器 `flow.nodes.push(IC.id)`
4. IC `flow.parent = 容器.id` + IC `flow.nodes` 设为子组件列表
5. 子组件 `flow.parent = IC.id`（**不用 pid**）+ `IC.flow.nodes.push(子组件id)` + 子组件 layout 用 IC 内坐标（如 `x:0,y:0,w:12,h:5`）
6. **双向校验**：`IC.flow.parent == 容器.id` 且 `容器.flow.linkedNodes[panelId] == IC.id` 且 `容器.flow.nodes 含 IC.id` 且 `IC.flow.nodes 含子组件.id` 且 `子组件.flow.parent == IC.id`
7. `designer save` + 回读校验（§7）

`panels[].children`/`tabs[].children` 保持空 `[]`。panel/tab `content` 支持 `{username}`/`{userid}` 平台变量。

### 5. ProgressChart 绑字段（要往 `pc.config.dataset` 加 calcFields 条目，CLI 可解）

> **2026-08-06 已确认 + 用户解答**（参照 `0806jindutiao.json` 样本 + 用户反馈）。
>
> **formId 推测**：`formId = formObjId + 1`（平台 ID 顺序约定——form 对象 objId + 1 = 表单数据表 ID；验过 3 个表单均为+1，`curl ds/fields` response 的 field.browserParams.formId 可验）。
>
> **valueType**：`"resultValue"` = **聚合计算**（SUM 把列所有值加一起，**一般场景用这个**，验证进度条正确显示百分比如 44.42%=SUM收款/SUM合同）；`"originValue"` = **原始列**（原始值，也验证可用但不常用）。

**步骤**（脚本改 layouts.json 后 `designer save`）：

1. 往页面 `config.dataset` 数组 push 一个 dataset 条目（分子、分母各一个独立条目，参照 0806 的 yfkje/zje）：
```json
{ "id":"<gen 19位>", "name":"<别名如 cg1>", "dataType":"calc", "calcFields":[...], "fields":[],
  "datasource":{ "id":"<formObjId>", "text":"<formName>(ft_<formId>)", "type":"LOGIC",
    "groupId":"weaver-ebuilder-form-service", "isPhysical":true, "usage":"all", "detailTable":false,
    "objType":"physical", "module":"ebuilder", "appId":"<appId>", "isFormModuleSelected":true },
  "filter":[], "calcFields":[ <见下> ] }
```
2. `calcFields` 项结构（`aggregator` 是聚合方式）：
```json
{ "id":"<calcFieldId,32hex uid>", "type":"Number", "compType":"<Money|NumberComponent>",
  "text":"<显示名>", "mainPrimaryKey":false,
  "browserParams":{ "formId":"<objId+1>", "formInfo":{"fieldId":"<fieldId>"}, "layoutId":"",
    "serviceModule":"ebuilderform", "fieldId":"<fieldId>" },
  "objId":"<formObjId>", "name":"field_<fieldId>", "aggregator":"SUM" }
```
3. ProgressChart comp.config：
```json
{ "dataset":"{<分子别名>.<分子calcFieldId>}", "denominator":"{<分母别名>.<分母calcFieldId>}",
  "molecularName":{"nameAlias":"<分子名>"}, "denominatorName":{"nameAlias":"<分母名>}",
  "valueType":"originValue", "showText":true, "showName":true, "title":"<标题>", "titleEnabled":true,
  "rangeColor":[{"min":{"disable":false,"value":0},"max":20,"color":"#ff4d4f"},...] }
```

**要点**：
- `formId = formObjId + 1`（采购单 objId ...854 → formId ...855；可 `curl ds/fields` 或 `form read` 验）。
- 表达式 `{alias.<calcFieldId>}` 的 `<calcFieldId>` = 步骤2 里 calcField 的 `id`（自己生成的 32hex uid），**不是 fieldId**。
- 分子、分母各用独立 dataset 条目（不同别名），即使都指向同一表单。
- `objId` 从 `form list <appId>`、`fieldId` 从 `form read <objId> --app-id <appId>` 取。**不需要 UI 的 6 步浏览接口**（`ds/group`/`ds/listByPage`/`ds/fields`/`generateId`/`ebAppTagIsOpen` 是设计器选字段流程，CLI 跳过）。
- factory 初始 `dataset="80"`/`denominator="100"`（静态 80%）；按上述改后即数据驱动。

> **业务用途**：进度条=**完成进度 = 已完成量/总量（同量纲）**。别用 金额/数量 做比值（无意义）；做"收款进度"要表单有"已收款金额"+"合同总额"两 Money 字段。详见上方「组件业务用途与数据选取」节。

> **系统参数**：`{username}`/`{userid}`/`{当前日期}`/`{当前部门}` 平台变量在渲染上下文解析，可用于 panel content/CountDown paramName/过滤条件。`ebAppTagIsOpen` 是查应用功能标签开关，CLI 不需要调。

**非数据组件清单**（无数据集概念，第一轮就讲清楚，别硬配数据源）：SearchGlobal、NewTab、NavBar/NavMenu、PageHeader、EbButton、Picture、CountDown、FastCreate、Comment。内容用 `{username}`/`{userid}` 变量或静态文本即可，无需数据集。

### 6. 日历事件不渲染 span / 只点天才显示 + title 单独配

- **症状**：日历事件不作为 span 渲染、只有点击某天才显示数据源。
- **根因（2026-08-06 验证，参照 555rilizhedie.json working 样本）**：缺**数据展示视图字段 `dataShowType`**（必须是数组 `["2","4","3","5"]`，不是字符串"0"）+ `titlefieldid` 用错值。`dataset-bind` 设的初始 dataSetNodes[0].dataShowType 可能是"0"（不渲染事件）。
- **修复（照 working 555 结构，555 用销售订单同 objId 可直接对照）**：
  - `config.dataSetNodes[0].dataShowType = ["2","4","3","5"]`（**数组**，视图模式集合=日/周/双周/月，**全上即可**，具体数字↔视图的映射不清楚，一般全包含）；同步设顶层 `config.dataShowType`）+ `config.dataSetNodes[0].baseInfo = {titlefieldid:<**表单字段相关值**，非固定"1"，表示标题取自表单的哪个字段；默认值非"1">, startTimeField:<开始Date fieldId>, endTimeField:<结束Date fieldId>, startTimeRange:9, endTimeRange:18, colorField:"", detailInfo:""}`（startTime/endTime 用 Date 字段 fieldId）。
  - `config.calendarType="1"`、`config.defaultView="3"`（month）、`config.viewModeSelectType="tile"`、`config.showViewModeChange=true`、`config.showLunar=true`。
  - `config.canCreateInterData=["calendar","task","contactRemind"]`、`config.canCreateDataset=true`、`config.baseInfo={use_viewModeChangeHideItem:true}`、`config.baseInfoForMulp={startTimeRange:9,endTimeRange:18}`、`config.historyData={}`、`config.notTransformField=["topOperatBtns","bottomOperatBtns"]`。
  - `config.dataSetNodes[0].dataset.text="<formName>(ft_<formId>)"`（带 ft_前缀）+ `dataSetNodes[0].dataAction={}`、`dataSetName:"日程"`、`show:true`、`datasetType:"dataset"`。
  - CLI 起步：`calendar dataset-bind <pageId> <compId> --obj-id --app-id --text --start --end --title-field --yes` + `calendar view <pageId> <compId] month --yes`；再脚本补上述全字段（`dataShowType` 数组 + titlefieldid:"1" + canCreateInterData 等），否则事件不渲染 span。
- 日历 `config.title`/`titleEnabled` **单独配**（`calendar title <pageId> <compId>` setter 或脚本改 comp.config.title/titleEnabled）。

### 7. save 后必回读校验（自检闭环，别把验证甩给用户）

`designer save` 返回 `✅ 已保存` **≠ 字段配对生效**——壳字段（如顶层 deadline）会骗脚本"以为配了"，双层结构（eventGroup `[[obj]]`、countDownSettings 数组、IC.flow.nodes）尤其易错。**每次脚本改 config + save 后，必跑 `e10-cli --json designer layout <pageId> --terminal pc 2>/dev/null` 回读，校验关键字段真进了**：
- eventGroup 是双层 `[[...]]` 不是单层 `[{...}]`
- countDownSettings[].deadline 是目标 ISO 时间（不是顶层壳）
- IC.flow.nodes 含子组件 id、子组件.flow.parent == IC.id、容器.flow.linkedNodes[panelId] == IC.id、**每个 tab/panel 都有 IC**（不只 tab1/panel1）
- 图表 measures 无幽灵空槽 `{format:NONEFORMAT}`（见上方图表坑）
- **图表 dimensions[0].id 是数字 fieldId**（不是维度名 text）——见下方 dimension-add 坑
- EbButton children 在 `btnGroup[1]+`（不是 btn[0]），带 children 的 btn 含 `actions:[]`+`isSplit:false`
- Bubble 气泡图 measures=1（不能多）
- **各组件 layout.h/w 合适**：配置完字段（绑数据/嵌套/事件）后**回核高度宽度**——容器 NewTab/CollapsePanel `h≥12`（建议 24）放嵌套子组件、`autoHeight:false` 避免缩到仅壳（验证 autoHeight 在内容未注册时缩到 4.8 致设计页不显示嵌套）；图表 `h≥34` 不裁切；列表 h 适中（可滚轮）；autoHeight:true 的组件确认没被缩到仅壳

> **dimension-add 可能错填所有 fieldId 槽（2026-08-06 已确认，必读）**：`chart dimension-add --type Select --field-id <fid> --text "<名>"` 有时把 **--text 的值填进 dimension 的所有 fieldId 槽**（不止 id），`text` 反而空 → 图解析不出维度 → 前端显示"缺维度"。验证 Pie+HBarStack 中招，其他图(Circular/Bar/HBar/Nightingale/Treemap)正常。
>
> **回读校验**：`layout --json` 查 `dimensions[0]`，比对"能正常显示的同类图"维度。**需全字段修正（不止 id/formInfo.fieldId）**：
> - `id` = 数字 fieldId
> - `text` = 维度名
> - `name` = `field_<fieldId>`
> - `formInfo.fieldId` = fieldId
> - `browserParams.formInfo.fieldId` = fieldId、`browserParams.fieldId` = fieldId、`browserParams.formId` = objId+1
> - `physicalField` = 字段物理名（从 `curl ds/fields` 取，形如 `f_<dataKey>`）
> - `config.fieldId` = fieldId、`config.title` = 维度名、`config.dataKey`/`config.columnName` = physicalField
> - `fieldGroup.id` = form objId
>
> 物理字段名（physicalField/dataKey/columnName）取法：`curl 'https://<base>/api/ebuilder/common/ds/fields' -F groupId=weaver-ebuilder-form-service -F sourceId=<objId> -F sourceType=LOGIC -F detailFieldsGroup=false -F enableMerge=true -F params=[]`，响应 `data[0].fields[].physicalField`（也即 config.dataKey/columnName）。**别只改 id 就以为修好了**——browserParams/config/name/physicalField 全要改，否则维度仍解析不出。

把验证责任留给自己，别甩给用户反馈才暴露。

---

### 命令/参数坑（速查）

- **Windows bash 反斜杠路径被吃**：`D:\dir\x.json` → `D:dirx.json`。正解用正斜杠 `D:/dir/x.json`（node 脚本内同理）。
- **`layout --json` 输出混 [AUTH] 行污染 JSON**：`> file` 会把 stderr 的 `[AUTH] 认证文件:...` 混进来致解析失败。必须 `2>/dev/null` 单独重定向 stdout：`e10-cli --json designer layout <pageId> --terminal all > layouts.json 2>/dev/null`。
- **`measure-add` 度量显示名用 `--text` 不是 `--name`**：`--name` 选项不存在，报 `required option --text`。
- **`calendar dataset-bind` 必填 `--text`**（表单显示名）。
- **`--yes` 支持不一致**：`comp-add` / `publish-menu` / 各 setter（chart/calendar/slide 等）**需 `--yes`**（非交互不加 → 静默"已取消"，compIds 一个都没加）；`designer save` **无 `--yes`** 选项。非交互环境一律加 `--yes`（save 除外）。

---

## 重新生成资产（维护者）

`assets/factory/` 的模板与范例是**打包好的数据资产**（源自平台真实页面解码样本的初始态/已配置态，已 genericize 去业务值）。skill 运行时只用打包好的资产（`designer comp-add --template` 内置发现，自包含分发），不读样本路径。维护者更换样本时：替换对应 `factory-*.json`（保持 PC+MOBILE 双端对、config 完整、绑定空、genericize 规则不变），skill 与 CLI 的模板发现逻辑无需改动。

---

## 相关指南

- 布局层（info/layout/save/comp-add）→ `guide-designer.md`
- 组件 config 字段名 → `guide-designer-components.md`
- 命令速查 → `../common/ref-cli-commands.md`「designer」节
