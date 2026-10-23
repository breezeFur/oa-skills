# 设计器布局层指南

> 本文件为 `SKILL.md` 的子模块，在用户于 Ebuilder 设计器中读/改/存页面布局时加载。覆盖：页面元信息（info）、布局树（layout）、保存（save）、锁定/解锁（lock）、主题（theme）、栅格位置（position）、加组件（comp-add，factory 模板自带打包）。
>
> **契约来源**：本指南全部字段、参数、取值枚举来自 ebuilder-designer 的 7 个 HTTP 接口规约（layout/page-info、layout/list、layout/save、layout/lock、layout/refTheme、page/version/list、page/version/revert）。凡接口未给出、须运行时 inspect 真实页面才能确定的具体取值（组件 config 子字段集、取值枚举、header 样本集等），一律标 **「需 inspect 真实页面查原始值」**，不凭空构造——盲造组件 config 会触发 ERR-007/008 崩页。
>
> 本 skill 自包含分发，不依赖任何本机文件；"inspect 真实页面"指用户对自己的页面运行 `designer layout <pageId> --json` 查看实际数据，是运行时操作。

---

## 命令总览

| 命令 | 说明 | 对应接口 |
|------|------|----------|
| `e10-cli designer info <pageId>` | 获取页面元信息（权限/变量/数据集/主题/锁定态） | GET `/layout/page/info` |
| `e10-cli designer layout <pageId> [--no-cuscomp]` | 获取 PC/MOBILE 两端完整组件树（默认 `returnCusComp=true`；`--no-cuscomp` 切 false 需 READONLY 权限） | GET `/layout/list` |
| `e10-cli designer layout <pageId> --json` | 导出布局 JSON 文件，供 save/comp-add 复用（`--json` 是全局选项，非 layout 专属隐藏） | GET `/layout/list`（落地为文件） |
| `e10-cli designer save <pageId> --layouts <json\|@file> [--page-name] [--sync-outdate]` | 保存布局（CLI 内部 LZ 压缩后 POST）。`--layouts` 必填（**不是位置参数**） | POST `/layout/save` |
| `e10-cli designer lock <pageId>` / `designer unlock <pageId>` | 锁定/解锁页面 | POST `/layout/lock` |
| `e10-cli designer css read <pageId> <compId> [--terminal <pc\|mobile\|both>]` | 读组件自定义 CSS（默认双端；`<compId>` 给任一端都行） | GET `/layout/list` |
| `e10-cli designer css write <pageId> <compId> (--css <文本> \| --css-file <路径>) [--append\|--clear] [--terminal] [--yes]` | 写组件自定义 CSS（默认**双端同写**、默认整段替换）。写后回读比对，对不上报错 | POST `/layout/save` |
| `e10-cli designer dom-list` / `designer dom <type> [--keys] [--section <path>] [--refs]` | 查写 CSS 要用的**组件 DOM 结构索引**（27 个组件；先 `--keys` 看骨架，再 `--section` 取子树） | 读随包资产 |
| `e10-cli designer position <pageId> <compId> --x --y --w --h` | 调组件栅格位置（PC，封装 `/layout/save`：改 `config.layout.x/y/w/h` 后 save） | POST `/layout/save` |
| `e10-cli designer comp-add <pageId> --type <Type> [--template @<file>] [--from <srcPage> --comp <id>] [--x --y --w --h]` | 加组件（封装 `/layout/save`）。**`--type` 是选项不是位置参数**。两种取源：`--type --template @<file>`（factory 模板，见 `guide-designer-factory.md`）/ `--from <srcPage> --comp <id>`（从活页克隆）。`--h` 按该指南「组件高度判断」自行算 | POST `/layout/save` |
| `e10-cli designer comp-remove <pageId> <compId>` | 移除组件（含 PC/MOBILE refCompId 两端） | POST `/layout/save` |

> **页面主题（`/layout/refTheme`）、页面可用组件库（`/api/ebuilder/coms/component/list`）这两类接口目前没有 CLI 命令封装**，故不列在此表 —— 上表只列**实际可执行**的命令。

> 组件 config 字段名与配置机制见 `guide-designer-components.md`；自定义 CSS 与 DOM 结构索引见 `guide-designer-css.md`；版本 list/revert 见 `guide-designer-version.md`。

---

## designer info — 获取页面布局信息

**接口契约**：GET `/api/bs/ebuilder/designer/layout/page/info`，Query `pageId`（Long，必填），请求头 `ETEAMSID`。

**返回字段**（`Map<String,Object>`，随 `BelongModule` 不同字段集不同）：

| 字段 | 类型 | 说明 |
|------|------|------|
| id / pageId | String | 页面 ID |
| module | Enum | 所属模块，如 `EB_PAGE` / `EB_FORM_VIEW` / `PORTAL_PAGE` |
| moduleName | String | 模块中文名 |
| layoutType | Enum | `GRID` / `ABSOLUTE` / `FLEX` |
| isLock | Integer | `0` 未锁 / `1` 已锁 |
| allowEdit | Boolean | 当前用户是否可编辑（仅 EB 页面模块返回） |
| terminalScopes | String | 终端范围，如 `"PC,MOBILE"` |
| appid / appName / appLabelId | - | 所属应用信息（仅 EB 页面模块） |
| dataset | Array | 页面数据集 |
| pageVar / appVar / pageModel | Array | 页面变量 / 全局变量 / 变量模型 |
| refTheme | String | 关联主题 ID |
| isIntro | Boolean | 是否需新手引导 |
| pageAnonymousEnable | Boolean | 是否免登录访问 |
| compPermit / compStylePermit | Boolean | 组件库/样式库创建权限（仅 `PORTAL_PAGE`） |

> **坑**：
> - 本接口**无 `@Permission` 注解**，只校验登录态；可编辑性通过 `allowEdit` 字段返回，前端据此控制——`allowEdit=false` 不要调 save。
> - `isLock=1` 须先 `designer unlock` 再 save。
> - `isIntro=true` 首次使用需引导，完成后调 `/finishIntro`（本 skill 未封装，需界面）。

---

## designer layout — 获取页面布局列表

**接口契约**：GET `/api/bs/ebuilder/designer/layout/list`，Query `pageId`（必填）、`returnCusComp`（Boolean，默认 `true`），请求头 `ETEAMSID`。

**权限分层**：`returnCusComp=true` 校验 `ObjType.PAGE`+`OptType.VIEW`，返回完整组件（含权限过滤）；`returnCusComp=false` 校验 `READONLY`，不返回自定义组件（`/api/bs` 路径下自动置 `false`）。

**返回**：`Array<PageLayoutEntity>`，通常 2 元素（PC + MOBILE），按 `terminalType` 区分。

**PageLayoutEntity 核心字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 布局唯一标识 |
| pageId | Long | 所属页面 ID |
| layoutType | Enum | `GRID` / `ABSOLUTE` / `FLEX` |
| terminalType | Enum | `PC` / `MOBILE` |
| module | Enum | `EB_PAGE` / `PORTAL_PAGE` 等 |
| config | Map | 布局配置（页面样式/背景/缩放等） |
| comps | Array<LayoutComponentEntity> | 组件列表 |
| sourceCode | Map | 页面源码 |
| ecodeVersion | Integer | ecode 版本标识 `1`~`4` |
| rightCompIds | Array<String> | 当前用户有权限查看的组件 ID |
| appId | Long | 所属应用 ID |
| thumbnail | String | 缩略图文件 ID |
| sysVariable / cssCache* | - | 组件变量 / 样式缓存相关 |

**LayoutComponentEntity 核心字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 组件唯一标识（32 位无连字符 UUID） |
| type | String | 组件类型名，如 `Slide` / `NList` / `NText` |
| package | String | 组件 npm 包路径 |
| category | String | 组件分类编号 |
| pid | String | 父组件 ID |
| refCompId | String | 关联组件 ID（PC/MOBILE 同名组件互指） |
| config | Map | 组件配置（含 `layout`、样式、属性、事件等） |
| isCustom / isLock | Boolean | 是否自定义 / 是否锁定 |
| applyStyle | String | 应用样式 ID 列表（逗号分隔） |
| prop | String | 组件属性标识 |
| styleCategoryCompKey / styleCategoryPackage | String | 样式分类 key / 包路径 |

> **坑**：
> - `returnCusComp=true` 时 comps 经权限过滤，只返有权查看的组件；`rightCompIds` 列出有权组件 ID。
> - PC 与 MOBILE 同名组件经 `refCompId` 互连——改一端时注意另一端是否需同步。
> - 跨租户页面走 `/api/{module}/designer/layout/list` 路径会额外查 `isNoTenantPage`。

---

## designer save — 保存页面布局（核心）

**接口契约**：POST `/api/bs/ebuilder/designer/layout/save`，Query `pageId`（必填）、`pageName`（可选，1-200）、`isSyncOutDateComps`（可选，默认 `false`）；**Body = `layouts` 字符串，是 LZ 压缩后的 JSON**。请求头 `ETEAMSID`。需 `ObjType.PAGE`+`OptType.EDIT` 权限。

### 入参数据来源铁律

> **layouts 直接取自 `/layout/list` 返回值作为基础，调用方只需完整构造 `comps` 属性**——`pageId`、`terminalType`、`module`、`layoutType`、`ecodeVersion`、`appId`、`config`、`sourceCode`、`rightCompIds` 等元数据保持 `/list` 原值不动。CLI 的 `designer save` 也遵循此模式：先 `layout --json` 导出，改 `comps`，再 save。

### PageLayoutEntity 入参字段（解密后 JSON 数组每元素）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | Long | 是 | 布局 ID |
| pageId | Long | 是 | 所属页面 ID |
| terminalType | Enum | 是 | `PC` / `MOBILE` |
| module | Enum | 是 | `EB_PAGE` / `PORTAL_PAGE` 等 |
| comps | Array<LayoutComponentEntity> | 是 | 组件列表（**唯一需完整构造**） |
| layoutType | Enum | 否 | `GRID` / `ABSOLUTE` / `FLEX` |
| config | Map | 否 | 布局配置 |
| compStyles / dataset / pageVar / pageModel / appVar | Array | 否 | 样式/数据集/变量/模型 |
| sourceCode | Map | 否 | 页面源码 |
| ecodeId / ecodeVersion / appId | - | 否 | ecode/应用标识 |
| thumbnail / refTheme / themeData | - | 否 | 缩略图/主题 |
| sysVariable | Map<String,String> | 否 | 组件变量 |

### LayoutComponentEntity 入参字段（comps 子元素）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | String | 是 | 32 位无连字符 UUID（前端生成） |
| type | String | 是 | 组件类型名 |
| config | Map | 是 | 组件配置（含 `layout`/样式/属性/事件等） |
| package | String | 否 | npm 包路径（序列化时映射为 `compPackage`） |
| category / pid / refCompId | String | 否 | 分类 / 父组件 / 关联组件 |
| refPluginPackageId / refPluginPackage | - | 否 | 插件包 |
| refModule / refBusinessId | - | 否 | 关联模块/业务 |
| prop / applyStyle | String | 否 | 属性标识 / 样式 ID 列表 |
| styleCategoryCompKey / styleCategoryPackage | String | 否 | 样式分类 |
| styles / customConfig | - | 否 | 自定义样式/配置 |
| ecodeId / ecodeVersion | - | 否 | ecode 标识 |
| isCustom / isLock | Boolean | 否 | 是否自定义/锁定 |
| masterComponent / master | - | 否 | 母版 |
| visibleScope | Enum | 否 | `ALL` / `OWNER` / `CUSTOM` |
| isCover | int | 否 | `0`/`1` 是否覆盖母版 |
| formComponent | Object | 否 | 表单组件 DTO（表单页才用） |

### config 内部结构（以 Slide 为例——接口文档唯一给出的完整样例）

| 子字段 | 类型 | 说明 |
|------|------|------|
| name | String | 组件显示名 |
| title / titleEnabled | String / Boolean | 标题文本 / 是否启用 |
| footerEnabled | Boolean | 是否启用页脚 |
| pics | Array | 图片列表 |
| imageMode | String | 图片填充模式 |
| switchEffect | String | 切换效果 |
| intervalTime | Object | 轮播间隔 `{type, value}` |
| speed | Integer | 切换速度（ms） |
| lazyLoad | Boolean | 是否懒加载 |
| imgSourceType | String | 图片来源类型 |
| eventGroup | Array | 事件配置列表 |
| **filter** | **Object** | **数据过滤条件（HTTP 契约：filter 类型为 Object，传 `[]` 与契约不符）** |
| showNum | Integer | 展示数量 |
| layout | Object | 栅格布局 `{i, x, y, w, h, scope, moved, selected, offsetTop, hidden}` |
| flow / disabled | Object | 流程 / 禁用配置 |

> **⚠️ 需 inspect 真实页面查原始值**：上表是 Slide 一例。**其他组件类型（NList / NText / NButton / Calendar / Pie / Bar / Line / NavPanel / DigitalPanel 等）的 config 子字段集，接口文档未给出**——必须 `designer layout <pageId> --json` 导出真实已配置页面，查 `comps[].config` 字段名与取值，**勿凭空构造**（盲造触发 ERR-007/008）。具体 setter 取值枚举见 `guide-designer-components.md`。

### LZ 压缩算法（CLI 内部使用，直接调 `designer save` 无需手压）

`layouts` Body 是 LZW（Lempel-Ziv-Welch）压缩后的**逗号分隔数字串**，服务端 `EbuilderCommonUtil.decryptByLZ()` 解密。算法要点：
1. 字典初始大小 **65536**（`2^16`，Unicode 字符最大值 +1）。
2. 字典**不预初始化**单字符映射，运行时按需添加。
3. `w` 为单字符且不在字典时，将其 Unicode 码点加入字典作为 code。
4. 输出逗号分隔数字序列，每个数字为字典 code 或 Unicode 码点。

> CLI `designer save` 内置该算法（JS/Java/Python 三语言实现见 layout-save 接口文档 §4.4），调用方传 `@layouts.json` 文件即可，**不要自己压**。
>
> **坑**：Body 直接传压缩后的数字串（`Content-Type: application/json`），**不要**再用 `JSON.stringify()` 包裹；保存前若 `isLock=1` 须先 unlock。
>
> **⚠️ 需 inspect 真实页面**：接口文档 §4.4 仅明示 `ebbusinessid` 请求头（=pageId）+ Cookie（`ETEAMSID`/`LOGIN_TYPE`/`langType`）。真实浏览器调用还带 `referer`、`timezoneoffset` 等头——**完整 header 集需样本确认，本骨架只列文档明示项**。CLI 已封装常用头，手调原始接口时按需补。

### 返回与内部流程

**返回**：`data.refreshComps`（Map<layoutId, Array<comp>>，仅 NList + 插件包 `933846626099339271` 时返，需前端刷新的组件）、`data.ecodeIds`（Map<layoutId, {ecodeId, ecodeVersion}>；`ecodeVersion` 为 2/3 时 `ecodeId` 取应用的而非布局自身的）。

**保存内部流程**：解密 → updateLayouts → saveSourceCode → updatePageVersion →（异步）createPageVersionBySavingLayout →（异步）syncMultilingual。历史记录与多语言同步不阻塞保存成功。

---

## designer lock / unlock — 锁定/解锁

**接口契约**：POST `/api/bs/ebuilder/designer/layout/lock`，Query `pageId`（必填）、`isLock`（Boolean 必填，`true` 锁 / `false` 解锁），请求头 `ETEAMSID`，需 EDIT 权限。返回 `data: true`。

> **坑**：
> - 锁是**软约束**——`/save` 本身**不校验** `isLock`；实际编辑权由 `@Permission` 强制。锁主要用于多人协作防并发。
> - 每次 lock/unlock 都触发 `updatePageVersion`，**版本号会递增**（即使幂等调用）。
> - `isLock` 存储为 int（`lockType` 1/0）。

---

## designer theme — 设置主题

**接口契约**：POST `/api/bs/ebuilder/designer/layout/refTheme`，**Query 参数** `themeId`（Long 必填）、`pageId`（Long 必填）、`terminalType`（`PC`/`MOBILE`，默认 `PC`；契约只列 themeId+pageId，CLI 样本发现带 terminalType），请求头 `ETEAMSID`，需 EDIT 权限。

**返回**：`{ themeCss, styleConfig, themeId, themeVersion, refTheme, defTheme, refStyles[] }`。

> **坑**：
> - `themeId` 与当前一致且版本缓存一致时 `themeCss` 可为 `null` → 用缓存，不再注入 CSS。
> - 主题已删除时不报错但 CSS 空，回落默认。
> - 设置主题后**须再调 `designer save` 持久化** `refTheme` 到布局。
> - 异步同步到发布端（`asyncTheme`）。
>
> **⚠️ 需 inspect 真实页面**：`themeId` 取值（可用主题清单）接口文档未给获取主题列表的接口——先用 `designer theme-list <pageId>` 查可选 themeId 清单，再 inspect 设计器主题面板核对；当前主题详情用 `designer theme-info <pageId>`。

---

## designer position — 调整栅格位置（PC）

`designer position <pageId> <compId> --x --y --w --h` 是 save 的封装：`designer layout <pageId> --json` → 改目标 comp 的 `config.layout.x/y/w/h` → `designer save`。

PC 端 12 列栅格（`config.style.layout.column=12`）；`--x` 列起点、`--y` 行起点、`--w` 宽（≤12）、`--h` 高（栅格行数）。

> **⚠️ 需 inspect 真实页面**：Mobile 端 `config.layout` 字段（`adaptive`/`h` 等，见 layout-list 示例）与 PC 差异——接口文档示例可见但不完整，**需 inspect 两端真实布局对比**。`designer position` 默认只改 PC 端栅格。

---

## designer comp-add — 加组件

加组件 = 读 `/layout/list` → 向对应 `terminalType` 的 `comps[]` push 一个新 `LayoutComponentEntity` → `designer save`。

- **comp id**：前端生成的 32 位无连字符 UUID（接口文档 §4.3 comps id 字段约束）。
- **config 完整性**：`config` 字段必须完整，缺失字段会崩页（ERR-007/008）。
- **factory 模式（首选）**：`designer comp-add <pageId> --type <Type> --template @<file>`（**`--type` 是选项不是位置参数**）从本 skill 自带的 `assets/factory/factory-<name>.json`（28 组件均有，原8源 2ganjing/新增20源 0805yuanshi 平台初始态，见 `guide-designer-factory.md`）复制完整 comp（仅换 id/refCompId）。模板是平台拖拽初始态、绑定空——**greenfield 用户无任何已配页面也能开箱即用**，克隆后用组件子命令把数据绑到自己的表单（图表/列表/日历/导航/幻灯/数字面板有 setter；其余组件见 factory 指南"克隆后必做"节）。
- **活页克隆模式**：`designer comp-add <pageId> --from <srcPage> --comp <srcCompId>` 从一个已配好的真实页面逐字克隆某 comp（连配置一起搬）。用于搬运已配好的复杂数据；会带入源页表单绑定，须逐个 remove+add 重指到自己的表单，不如 factory 干净。
- **无模板凭空构造**：除 Slide 外的组件 config 字段集接口未给，**勿凭空拼装**（盲造 ERR-007/008）；始终走 factory 模式。

> **新建 comp 对 PC/MOBILE `refCompId` 互连**：接口示例可见互指，factory 模板已内置两端互连规则，`comp-add --template` 自动生成新对并重连，无需手动处理。

---

## 版本与还原（速查）

版本列表 / 版本还原见 `guide-designer-version.md`（GET `/page/version/list` + POST `/page/version/revert`）。

---

## 典型工作流

```bash
# 1. 拿 pageId（应用已建、页面已建；见 ref-cli-commands.md 页面管理节）
e10-cli app list                       # 拿 appId
e10-cli page list --app-id <appId>     # 拿 pageId
e10-cli page create <页面名> <appId> --scope PC,MOBILE --layout-type GRID   # 建空页（参数顺序：名称在前、appId 在后）

# 2. 进设计器前先看元信息
e10-cli designer info <pageId>         # 看 allowEdit / isLock / module

# 3. 读布局（作为编辑基础）—— --json 输出完整 PC+MOBILE 两端（save 必须两端，否则覆盖丢 MOBILE；CLI save 强校验）
e10-cli designer layout <pageId> --json > layouts.json   # 导出 PC+MOBILE 组件树

# 4. 锁定（多人协作防并发）
e10-cli designer lock <pageId>

# 5. 改 comps（加组件/改 config/调位置）→ 保存
e10-cli designer comp-add <pageId> --template slide --x 0 --y 0 --w 12 --h 25   # 模板名直传（28 个内置），--h 按组件高度判断自行算，见 guide-designer-factory.md
e10-cli designer position <pageId> <compId> --x 0 --y 0 --w 12 --h 25
e10-cli designer auto-height <pageId>                    # 单列纵堆模式：按内容定高+重排 y（多列栅格勿用，手调 position）
e10-cli designer save <pageId> --layouts @layouts.json   # 收尾显式保存

# 6. 解锁
e10-cli designer unlock <pageId>
```

> **关键**：save 入参直接取自 `/list` 导出值，只改 `comps`；元数据不动。组件具体 config 取值需 inspect 真实页面，不凭空造。

> **⚠️ 收尾必做显式 save + unlock（否则"布局未保存"）**：`comp-add`/`position`/各组件 setter（chart dataset-set/measure-add 等）虽各自**封装 `/layout/save` 自动存盘**，但全部改完后**必须再跑一次显式 `designer save <pageId> --layouts @<fresh-layout.json>` + `designer unlock <pageId>`**（fresh layout 用 `designer layout <pageId> --terminal all --json` 现导）。否则页面留 `isLock=true`（浏览器开了设计器会自动上锁）或 draft 标志未清，**设计器/预览打开会弹"布局未保存"提示**（验证：未 unlock 的页 `isLock=true`，预览必弹）。`designer unlock` 是软锁释放，多人协作场景防并发；单人编辑也必须收尾 unlock 清态。`publish-menu` 前务必先 save+unlock。
