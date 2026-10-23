---
name: weaver-e10-edcreport
display_name: 泛微E10e-builder报表
display_name_en: edcreport
description: "E-Builder 报表搭建技能。核心：用 edc-report CLI + weaver-e10-login 在应用下创建/修改报表（定源→落库→交设计器地址即停）。支持列表/分组/交叉等布局与查询/权限/快照等点名能力。可选需求分析指导。"
description_en: "E-Builder report builder skill. Use edc-report CLI with weaver-e10-login to create or modify reports under an app (define datasource -> persist -> return designer URL). Supports list/group/cross layouts, query conditions, permissions and snapshots."
version: 1.7.1
author: 泛微网络科技股份有限公司
requires: [weaver-e10-login]
agent_created: true
---

# 泛微E10e-builder报表

> Skill slug：`weaver-e10-edcreport` · 版本 **1.7.0**（+ **`verify query` 查询条件合规体检（Q1~Q10 判据总表，--fix 幂等修）+ doctor 守卫在位扫描**；+ **查询条件「默认值三件套」必须写**（漏写会让设计器弹窗默认值区炸开、后续整段行被顶出可视区；新增 `fix query-default` 补齐；`query save` 自动补缺失项）；+ **禁止静默注入查询条件样式字段 `advancedSearchType`**（新增 `fix query-style`：清「展开条件」回「默认样式」+ 删误插入重复行）；+ 冻结单元格 API 落库 `fix freeze`（`cell.tag.fixed` 是唯一持久化标记）；+ 关联浏览富对象改走 GET `browserBeanSearch`（旧 POST `getBrowserBean` 恒 500）；+ 重复坐标拦截；+ 空白行/表头合并指南；+ tableName 免浏览器重建；+ `doctor` 环境体检 / `pitfalls` 踩坑知识库 / `verify limit` 规模预检 / `render` 渲染守卫）

## 搭表完成即停（最高强制）

> **模式 A**：`saveReportDevInfo` 成功并已输出设计器地址后 → **本轮任务结束**。  
> **禁止**继续：verify / 预聚合 / HTML / 需求分析 / 配置检测 / 再 save / 通读知识库 / 扫描无关文件。  
> 细则：`references/report-delivery-contract.md` · CLI：`edc-report policy build`

---

## 冷启动（最高 · 防 502）

> **开场只读**：`references/cold-start-scan-guide.md`（一页）+ 本任务点名的 **≤2** 篇 guide。  
> **禁止**通读本 `SKILL.md` 全文、全部 `references/`、`report-knowledge-base.md`、`weaver-e10-login`、`.workbuddy/`。  
> **本包不含** `e10-cli*` — 禁止查找。CLI：`edc-report policy build` · `auth ready`

| 允许（默认） | 禁止（开场） |
|--------------|--------------|
| `edc-report auth ready` / `e10-login status`（0 文件扫描） | Glob/Grep 全 skill、扫 profile、通读登录 SKILL |
| `edc-report …` 命令 | 查找 `e10-cli*` / `actionflows` |
| 点名单篇 `*-guide.md` | knowledge-base / help / 分析模板 / data-model / config-schema / ai-workflow / datasource-metadata 全文 |

---

## 概述

e-Builder 报表模块能力包：依赖 **weaver-e10-login**（登录）与 **edc-report**（搭表执行 CLI）。  
**判断走本 Skill 索引 → 细则走 `references/` → 执行优先 `edc-report`。**

| 能力 | 说明 |
|------|------|
| 搭表落库 | 定源 → CLI/脚本落库 → 交设计器地址即停 |
| 点名改表 | 仅改用户点名项（`user-request-scope-only-guide.md`） |
| 需求分析 | **仅**用户要分析/指导时；纯搭表跳过 |
| 已移除 | 测试用例、原型图 — 勿再查找 |

---

## 触发条件（摘要）

用户提到：生成/创建/搭建报表、报表设计、edc-report、父格、查询条件、数据集、设计器、权限、快照、定点修改、高级搜索、超链接/事件、模版创建/快速构建、分组/移动/转移等。  
登录相关：只跑 `auth ready`，勿为登录扫仓库。

---

## 执行优先级（强制）

| 优先级 | 入口 |
|--------|------|
| **0** | `edc-report build spec --spec <spec.json>` — **声明式一次落库（模式 A 首选，见 `spec-build-schema.md`）** |
| **0.5** | `edc-report policy scope` — 仅改用户点名项 |
| **1** | `e10-login` / `edc-report auth ready` |
| **2** | `edc-report …`（find / query / verify / create / dataset / …） |
| **3** | 裸 `node`/`python` `scripts/`（**仅 CLI 不可用时**，且须连接复用） |

映射表：`references/edc-report-cli.md`。

---

## 会话硬规则（摘要 · 细则在 guide）

### A0 仅改用户点名项

**必加载**（改已有表时）：`user-request-scope-only-guide.md`。  
未点名：不删、不重建、不顺手改。破坏性命令须用户明确要求。

### A0.1 / A0.2 性能与扫描

**必加载**：`cold-start-scan-guide.md`（开场）。展开：`session-build-performance-guide.md`（进行中按需）。  
找表已给 app → 只 `find form` / `getList/{appId}`；禁首轮 `/ds/group`；禁 SpreadJS 黑盒；交链即停。

### A0.3 会话终止 = 未完成 → 强制回滚空壳

**会话中止 / 取消 / 超时 / 未交设计器链接** → 视为任务失败。  
**禁止**故意建 `__build_*` / `__probe_*`；正常路径用目标名一次落库（`build spec`）。  
仅 save 失败留下的未完成表须 `deleteReport`；历史残留壳用户点名再 `cleanup shells`。  
正式交付成功的报表保留。细则：`failure-cleanup-and-nonblocking-guide.md` §〇。

### A0.4 字段找不到 → **让用户指定字段**（规则 A · 强制 · 2026-09-11）

列字段只允许**精确**匹配（`fieldMap`/`fieldName` → 列标题 === `fieldsKey.text` → `field` === `text`/`name`）。  
**禁止**模糊自动绑定；**禁止**回退系统字段（`name`/`id`/`create_time`…）。无命中 → `build spec` **exit 4 且不建表**，
把 `candidates`/`allFields` **原样交用户挑字段**；列文案与字段真实显示名不一致 → 需用户确认（`--field-confirmed`）。  
事故：列「姓名」被静默绑到系统字段 `name`（真实显示名「标题」）。细则：`field-bind-exact-match-guide.md §2.0`。

### A0.4b 表没指明 / 非精确匹配 → **让用户指定表**（规则 B · 强制 · 2026-09-11）

需求**未指出具体表**，或应用内检索**非完全精准匹配**（模糊包含 / 多条近名 / 未命中）→ `build spec` / `find form` **exit 3 且不建表**，
输出 `candidates[]` 请用户自行选取指定。**禁止**按关键词猜表、用「最像的」顶上、先建壳试探。  
确认后 `--form-confirmed --source-id <id>` 复跑。  
**统一入口**：`edc-report policy ask`（两条规则一页）；`spec-build-schema.md §1.1/§2.1`。

### A0.5 同源只挂一次 + 回显名带后缀（强制 · 2026-09-11）

本报表已有同 `sourceId` 数据集 → **复用**，禁止二次 `addDataset`（否则左侧出现重复数据源分组）。  
`sourceName` 强制 `{表单名}(业务模块)`（共享表 `(表单)`）；裸表单名会使面板缺后缀。  
体检：`edc-report verify bind <reportId> [appId]`。细则：`add-dataset-registration-guide.md §2.1`。

### A0.6 字段接口返回格式（**以 `fieldsAndOriginFields` 为准** · 2026-09-11）

`fieldsBySource` → `data` 是**裸数组**、`dataSetId="0"`；`fieldsAndOriginFields` → `data` 是 `{fieldsKey, originFieldsKey}`、`dataSetId` 为真实值；
两者**字段元素同形**（30/30 仅 `dataSetId` 不同）。统一用 `spec_lib.normalizeFieldList(res,{datasetId})` 取「字段元素数组」，**务必注入本报表真实 datasetId**。
细则：`dataset-table-field-contract-guide.md §三点五`。

### 其它硬规则 → 点名再读（禁止开场全载）

| 主题 | Guide | CLI |
|------|-------|-----|
| 定点修改 | `targeted-fix-guide.md` | `verify self`（可裁剪） |
| 查询条件 | `query-condition-api-guide.md` | `query save\|type\|list\|check-echo\|fix-echo`；条件级 `queryType` 写**JSON 数组短码字符串** `'["advance"]'`（高级搜索）/ `'["filter"]'`（筛选）—— 长码 `"advancedSearch"` 会导致**设计器回显不勾选**；**`updateQueryType` 会把入参批量覆盖所有条件**（传长码=一键摧毁回显，真正根因）；保存后必须 `check-echo` 自检，异常用 `fix-echo` 修复；人员/部门 `browserType` 富对象**只能**从 `GET /api/bcw/relevanceBrowser/browserBeanSearch?searchValue=<中文名>` 取（旧 `POST getBrowserBean` 恒 500），CLI 已自动升级简写；🔴 **禁止静默注入 `advancedSearchType`**（写 `'openCondition'` = 把报表页查询区从「默认样式」改成「展开条件」，属擅改展示样式；入参没有该键就不写）→ 存量清理 `fix query-style`；🔴 **默认值三件套 `defaultValueType`/`defaultValue`/`type1`/`type2` 必写**（漏写→弹窗「默认值类型」=请选择、默认值区把所有控件变体炸开、日期类型/显示位置/条件必填被顶出可视区）→ `fix query-default --set ...` 补齐（`query save` 已自动补缺失项）；⚠️ `saveQueryItem` **必须带 `id` 才是原地更新**，不带 `id` 会新增出重复条件；★ 改完条件一律跑 `verify query <rid> <appId>` 自检（Q1~Q10）；`query type` **不传 `--show-where` = 未点名 → 只读回读**（updateQueryType 是批量覆盖接口） |
| 事件超链接 | `event-hreflink-guide.md` | `validate href [--fix]`；ASCII `?`；`参数名=坐标` |
| 父格 / 少挂源 | `datasource-selection-and-parent-filter-guide.md` | `join suggest` |
| 找表 | `app-datasource-lookup-guide.md`（§2.0 未给表名须确认） | `find form` / `--list` / `--suggest` |
| API 建表 | `api-report-build-fast-path.md` | `create …` |
| **声明式一次建表（首选）** | **`spec-build-schema.md`** | **`build spec --spec`** |
| 交付 | `report-delivery-contract.md` | `policy build` |
| 失败删壳 | `failure-cleanup-and-nonblocking-guide.md` | `cleanup shells` |
| 局部保存 | `safe-partial-save-guide.md` | `safe_report_save` |
| 设计区空白 | `designer-blank-prevention-guide.md` | `validate blank` |
| 网格线 | `report-designer-feature-map.md` §4.6.1；`report-internal-error-guide.md` | `validate gridline` |
| 条件格式 | `condition-format-guide.md` | `validate condition` |
| 转换面板 | `cell-transform-guide.md` | `validate transform` |
| 单元格格式 | `cell-config-echo-guide.md` | `validate format` |
| **默认表头样式** | `default-header-style-guide.md`（未指定/无效果图才套用） | `validate style`；`build spec` 自动分层 |
| 字段绑定 | `field-bind-exact-match-guide.md` + `add-dataset-registration-guide.md` | `verify bind` |
| **表名/字段映射契约** | **`dataset-table-field-contract-guide.md`**（tableName + 三件套，禁删；§四点六 = 免浏览器反向重建修 tableName） | `build spec` 自动门禁；`verify contract` / `fix table-name` |
| **冻结单元格 / 锁定列** | `layout-showlocation-freeze-guide.md` **§2.6 API 落库**（`cell.tag.fixed` 是**唯一**持久化标记；锚点格不必是空格；禁写 `cellText=fixed-cell-tag`；`fixed` 必须唯一；重复坐标拦截） | **`fix freeze --report-id <id> --anchor <x,y> [--apply]`** |
| **环境体检（工具链坑）** | 凭证/host+port/变量名/CLI 版本/连通性；require 解析、漏 port、python 依赖、语法；shim 悬空、入口行尾；三树一致性；渲染守卫 | **`doctor [env\|scripts\|install\|trees\|perf\|all] [--fix] [--json]`** |
| **踩坑知识库**（动手前先扫） | 历次会话全部坑：症状/根因/对策/对应 CLI，按领域检索 | **`pitfalls [关键词] [--area auth\|perf\|env\|build\|layout\|field\|query\|excel] [--json]`** |
| **渲染守卫 / 规模预检** | 默认拒绝全量渲染（必然 555 且白烧 15~80s）；pageRowCount 封顶 574；超限倍数可算 | `render`；**`verify limit <reportId>`** |
| 公式 | `formula-cell-api-guide.md` | — |
| 数据集筛选 | `dataset-query-filter-guide.md` | — |
| 跨源筛选 | `cross-dataset-filter-guide.md` | `py left-filter` |
| 新建三模式 | `report-create-modes-guide.md` | `create models\|blank\|template\|quick` |
| 列表页 | `report-list-page-ops-guide.md` | `group` / `lifecycle` / `app search` |
| 数据集侧栏 | `dataset-sidebar-ops-guide.md` | `dataset …` |
| 权限/生命周期 | `report-permission-guide.md` / `report-lifecycle-api-guide.md` | `scope` / `lifecycle` |
| 快照/版本 | `designer-blank-prevention-guide.md` 等 | `snapshot` / `version` |
| 基础默认值 | `report-baseinfo-defaults-guide.md` | `validate base` / `verify meta` |
| 居左/冻结 | `layout-showlocation-freeze-guide.md` | `fix freeze`（冻结）；居左 = `showLocation:1` |
| **空白行 / 表头合并**（Excel 对齐） | `hidden-row-and-header-merge-guide.md` | `verify all` + 渲染回读（`size:0` **不隐藏行**；合并只认 `spans`） |
| 落库自检 | `report-self-check-guide.md` | `verify all`（默认不在交链后跑） |
| 鉴权头 | `api-auth-headers.md` | — |
| 雪花 ID | `snowflake-id-precision-guide.md` | — |
| 预聚合 | `preaggregate-auto-disable-guide.md` | `py preagg` |
| 日期区间 catalog | `date-range-query-reference.md` | — |

**查询摘要**：multipart 单对象；条件级 `queryType='["advance"]'`（数组短码）+ save 后 `updateQueryType`（同数组形态）+ `check-echo` 自检；下拉 `selectKey`=ID / `selectValue`=名称。  
**事件摘要**：`?zclb=D7&zcmc=E7&cx={searchfield001}`；禁全角 `？`；Field 写 `pcHreflink`。  
**父格摘要**：新建单数据集左父格默认 `-1,-1`；超链接 Const 须指向数据格；`(0,0)`≠默认。

---

## 工作流（极简）

### 模式 A · 从零搭表

**首选（默认）**：`edc-report build spec --spec <spec.json>` —— 建表前字段预检（未命中 exit 4 **不建表**）→ 目标名一次创建 → 本表取字段（复校）→ 落库（禁空壳/rename）。模糊表名须确认（exit 3）。
结构见 `spec-build-schema.md`（样式/货币/条件格式/公式/标题冻结/`fieldMap` 全部声明式描述）。实测 **1.0s 落库 / 2.8s 含 CLI 启动**。

备用（手工分步）：

1. `edc-report auth ready`  
2. 读 `api-report-build-fast-path.md` + `app-datasource-lookup-guide.md`  
3. `find form` → 建壳/落库（CLI 或脚本 + `safe_report_save`）  
4. 输出设计器 URL → **停**（`report-delivery-contract.md`）

### 定点改

1. `auth ready` + `user-request-scope-only-guide.md` + `targeted-fix-guide.md`  
2. 只加载与改点相关的 **一篇** guide  
3. 只改点名项 → 交链或说明结果 → 停

### 仅需求分析

1. 加载 `report-requirement-analysis-template.md`（**勿**默认搭表）  
2. HTML 仅用户点名时再 `build_guide_html.py`

---

## 禁止冷启动加载（保留文件 · 勿开场读）

| 文件 | 何时才读 |
|------|----------|
| `report-knowledge-base.md` | 引擎冲突 / 源码对齐 |
| `report-building-guide.md` | 界面操作指导 |
| `report-help-guide.md` | 帮助问答 |
| `report-requirement-analysis-template.md` | 用户要分析 |
| `report-data-model.md` / `report-config-schema.md` / `ai-report-workflow.md` | 整包配置生成 |
| `datasource-metadata-guide.md` | DataSetAction 全手册 |
| `build_guide_html.py` | 用户要 HTML |
| `weaver-e10-login` | auth 失败需说明时 |
| `assets/template-*.json` | 布局脚手架（≠ 模版创建） |

源码核对路径（按需）：`D:\edc_source\weaver-common-edc` — **非开场扫描目标**。

---

## 包结构

| 路径 | 用途 |
|------|------|
| `references/` | 专题指南；**点名加载** |
| `scripts/` | 可执行源；CLI 开发态直用 |
| `edc-report/` | npm CLI（扁平结构：`edc-report.js` + `cli.js`）；脚本直接解析同仓 `scripts/` |
| `weaver-e10-login` | 外部依赖：登录 Skill；运行时用全局 `e10-login` CLI |
| `assets/` | 示例 JSON；非默认扫描 |

安装 CLI：`cd edc-report && npm i -g .`（或 `npm link`；需先安装 `weaver-e10-login` 提供的 `e10-login` CLI，建议固定版本并校验来源）。

---

## 综合注意事项（索引）

1. **登录**：Cookie.raw + eteamsid + User-Agent 三项；见 `api-auth-headers.md`  
2. **CLI 优先**：有命令禁止再堆 `.workbuddy` debug  
3. **网格线**：workbook **禁** `gridline` 键；page `gridLine=0`；`validate gridline`  
4. **交链即停**：见 delivery-contract；全局修复 ≤1 轮  
5. **禁止空壳**：先字段预检再落库；禁 `__build_*`/跨表复用 datasetId；模糊表须确认；同源只挂一次；仅失败删未完成表
5.1 **字段精确绑定**：无精确命中 → exit 4 让用户指定字段（禁模糊兜底/系统字段回退）
6. **同款样式**：只验一次再复用（`cell-config-echo-guide.md`）  
7. 完整 CLI 映射与检查清单：`edc-report-cli.md`

细则与历史硬规则全文已下沉到各 `references/*-guide.md`；**本 SKILL 为入口索引，禁止当作百科通读。**
