# 页面组件自定义 CSS

需求里出现「给这个组件调样式」「自定义 CSS」「改选择器」「样式不生效」「DOM 结构」时读本篇。组件 config 字段见 `guide-designer-components.md`，布局读写机制见 `guide-designer.md`。

## 定位与职责边界

自定义 CSS 写在**组件**上，形如：

```
comp.config.styles[N].customStyle.base.codeSource   ← 自由文本 CSS
```

- **页面级没有自由 CSS 槽位**。`layout.config.style` 里只有结构化的 `page.margin/padding/background`。想整页统一风格，只能往组件上写。
- **CLI 只负责写**：写对、写稳、写后回读比对。样式在页面上如何渲染、样式缓存如何编译，是平台的事，命令不做判断也不承诺。
- **一个页面有 PC/MOBILE 两套布局，每个终端各有一份组件**，靠互指 `refCompId` 配对。设计器本身就是双端同写，所以 `css write` 默认也双端。

## `styles` 记录契约

`comp.config.styles` 是数组，里面有**两种互不相干的记录**，标志位正好相反：

| | 自由 CSS 记录 | 主题绑定记录 |
|---|---|---|
| 形态 | `{category, useCustom:true, useComStyle:false, styleVersion, customStyle:{…}}` | `{id, category, customType, useCustom:false, themeId, useComStyle:true}` |
| 来源 | 用户/CLI 写的自定义样式 | 组件自带的外观主题（Picture、CountDown 的模板就带） |
| CLI 行为 | 读它、写它 | **绝不碰**（写 CSS 时追加一条新记录，不动它） |

干净组件的 `styles` 是**空数组 `[]`**。三种输入状态及对应行为：

1. `styles` 为空 → 新建一条记录（只需 `category`/`useCustom`/`useComStyle`/`styleVersion` + `customStyle.base.codeSource` 四个键）。
2. 已有自由记录 → **外科式**只换 `customStyle.base.codeSource`，`customStyle` 下的 `title`/`content`/`footer`/`container` 等图形化样式块与记录的其它字段原样保留。
3. 只有主题绑定记录 → **追加**一条自由记录，第 0 条一字不动。

## 命令

```bash
# 读（默认双端；compId 给 PC 或 MOBILE 任一端的都可以）
e10-cli designer css read <pageId> <compId> [--terminal pc|mobile|both] [--json]

# 写（默认双端、默认整段替换）
e10-cli designer css write <pageId> <compId> --css "<CSS>"
e10-cli designer css write <pageId> <compId> --css-file <路径>
e10-cli designer css write <pageId> <compId> --css "<CSS>" --append
e10-cli designer css write <pageId> <compId> --clear
e10-cli designer css write <pageId> <compId> --css "<CSS>" --terminal pc
```

- **`--css` 与 `--css-file` 是两个选项，没有 `@file` 约定。** `@media` 开头的 CSS 是合法写法，用 `@文件` 会被当成路径。
- `--append` **非幂等**：重复跑会重复追加。想改内容用整段替换。
- `--clear` 清空内容但**保留记录**（不动 `customStyle` 其它块）。
- 两端现有 CSS **都非空且不一致**时，双端写会覆盖其中一端 —— 命令会拦下并点名两端字节数，确认覆盖加 `--yes`，只想改一端用 `--terminal`。
- 写完会**回读比对**；对不上直接报错（服务端可能没落库或改写了形状），用 `css read` 看实际值。

## 写选择器：**不要写组件 id**

**`customStyle.base.codeSource` 是组件级的** —— 每段 CSS 本来就只属于它所在的那个组件，平台在编译时会自己套上 `#<comId>` 限域。所以源码里**再写一遍 id 是错的**：

```css
/* ✅ 对：直接写类名 */
.ebcoms-navPanel-wrapper-square { border-radius: 12px; }
.content { background: #070d1a; }

/* ❌ 错：多写了组件 id */
#f3708b2387bd757a336ab0e176243801 .ebcoms-navPanel-wrapper-square { … }
```

写进去会怎样：轻则多余，重则**不生效** —— 一个页面 PC 与 MOBILE 是两份布局、两个不同的实例 id，同一段 CSS 双端同时写时（设计器自己就是双端同写、两端 `codeSource` 一模一样），写死哪一端的 id，另一端就必不匹配。

> 组件 DOM 文档里说的「官方样式生成器一律以 `#<comId>` 限域」，讲的是**编译产物**（`sourceCode.cssCache`）长什么样，**不是叫你写在源码里**。

组件 DOM 由三层拼出来，**类名前缀区分来源**：

| 前缀 | 来源 |
|---|---|
| `ebcom-` | 引擎/框架层（源码里搜不到，由引擎外壳生成） |
| `ebcoms-` | 组件自己写的 |
| `ui-` | `@weapp/ui` 第三方组件追加的 |

- 引擎外壳的 `id` 与挂在组件根上的 `data-id` 都是组件实例 id —— **它们是给平台编译用的，不要写进你的选择器**。
- 页面层外壳是 `#ebpage_<pageId>`，同样**别拿它定位组件**。
- 各组件的 `ebcom-*` 外壳类名不统一（如 NList → `ebcom-nlist`、CountDown → `ebcom-countdown`、CollapsePanel → `ebcom-collapsepanel`），以 DOM 结构文档为准，不要凭类型名拼。

写样式时：**只写类名，不写 id**；**不要杜撰类名**（拼错就是静默不生效）；尽量不用 `!important` 去压默认样式。

## 查 DOM 结构：`designer dom`

内置 **27 个组件**的 DOM 结构索引，随 skill 资产分发，用来把「用户说的部位」翻成选择器。

```bash
e10-cli designer dom-list                    # 全表：类型 / 体量 / 组件名
e10-cli designer dom NList --keys            # 先看骨架：usage / pickTree / legend / 各区块体量
e10-cli designer dom NList --section shared.title        # 只取需要的子树
e10-cli designer dom NList --section shared.title --refs # 就地展开 {"ref":"shared.x"}
```

**先 `--keys` 再 `--section`**：文档中位数 20 多 KB，整份打出来很占上下文，而 `usage`/`pickTree`/`legend` 三段散文才是找对树的关键。

文档里的记号（各文件自己的 `legend` 也有解释）：

| 记号 | 含义 |
|---|---|
| `[cls]` | 条件类名，满足业务条件才挂 |
| `{a\|b}` | 同一个位置按配置二选一 |
| `a > b` | 父子层级压缩写法 |
| `<comId>` | 组件实例 id。**只出现在文档对编译产物的描述里**，写源码选择器时不要用（见上） |
| `ref:shared.x` / `{"ref":"shared.x"}` | 引用同文件的复用片段，用 `--refs` 展开 |
| `uncontrolled` | 第三方（`@weapp/ui` 等）渲染，只给挂载点 |

覆盖的 27 个组件（命令按**平台组件 type** 取，也认下面的常见写法）：

| 平台 type | 也认 | 平台 type | 也认 |
|---|---|---|---|
| `NavPanel` | nav-panel | `NList` | nlist、n-list |
| `NavBar` | nav-bar | `DigitalPanel` | digitalpanel、digital-panel |
| `ProgressChart` | progress-bar、progressbar | `PageHeader` | pageheader、page-header |
| `EbButton` | eb-button | `CountDown` | count-down |
| `FastCreate` | fast-create | `SearchGlobal` | search-global |
| `CollapsePanel` | collapse-panel | `NewTab` | new-tab |
| `Comment` / `Picture` / `Slide` / `Calendar` | — | `Bar`/`BarStack`/`Line`/`HBar`/`HBarStack`/`Pie`/`Circular`/`Nightingale`/`Gauge`/`Treemap`/`Bubble` | — |

`NavMenu`、`InternalContainer` **暂无**文档，命令会直接说明并列出已覆盖清单。

## 坑

- **注释不会被编译进去**，但 CLI 写进去时**原样保存**，回读比对会按去掉注释后比 —— 所以带注释的原文是安全的。
- **MOBILE 端的布局不返回样式缓存**，双端写完之后想确认效果，看 PC 端更省事。
- **别手写 `sourceCode.cssCache`** —— 那是平台的编译产物，手写会和下次编译打架。
- 改完布局记得收尾 `designer unlock`（多人协作防并发；`/layout/save` 本身不校验锁）。
