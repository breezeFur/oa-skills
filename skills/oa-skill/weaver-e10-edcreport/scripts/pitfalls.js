'use strict';
/**
 * pitfalls.js —— 历史会话踩坑知识库（可执行 · 可检索）
 *
 * 目的：把历次会话踩过的坑与优化点，从「散落在 references/*.md 的长文档」变成
 *       **一条条可检索、带 CLI 对策**的结构化条目，供 Agent 在动手前先扫一遍。
 *
 * 用法：
 *   node pitfalls.js                       # 全部条目（按 area 分组）
 *   node pitfalls.js <关键词>              # 标题/症状/根因/对策全文匹配
 *   node pitfalls.js --area auth           # 按领域过滤
 *   node pitfalls.js --list-areas          # 只列领域
 *   node pitfalls.js --json                # 结构化输出（供 Agent 消费）
 *
 * 领域（area）：auth 登录鉴权 · perf 性能渲染 · env 环境工具链 · build 建表落库
 *              layout 布局 · field 字段契约 · query 查询条件 · excel Excel 解析
 *
 * 约定：条目里的 `cli` 字段 = 该坑在 CLI 里的**对策命令**；`check` = 可自动体检时 doctor 的检查项 id。
 */

const AREA_LABEL = {
  auth: '登录 / 鉴权',
  perf: '性能 / 渲染',
  env: '环境 / 工具链',
  build: '建表 / 落库',
  layout: '布局（行 / 列 / 合并）',
  field: '字段绑定 / 契约回显',
  query: '查询条件',
  excel: 'Excel 解析',
};

const PITFALLS = [
  // ─────────────────────────── auth ───────────────────────────
  {
    id: 'AUTH-1',
    area: 'auth',
    title: '每请求 spawn e10-login，2.4s/次吃掉 78% 耗时',
    symptom: '搭建一次报表几十秒；计时发现每个 HTTP 请求前都在调 e10-login。',
    cause: '各脚本各自 spawn `e10-login status` 取凭证，没有缓存、没有 env 优先。',
    fix: '统一走 scripts/eb_auth.js：env(EB_ETEAMSID/EB_HOST) 优先 → 进程内缓存 → 最多一次 CLI。2400ms → 11ms。',
    cli: 'edc-report auth ready  (已就绪 0 次 spawn)',
  },
  {
    id: 'AUTH-2',
    area: 'auth',
    title: 'e10-login oidc 永远等不到授权码（会卡死）',
    symptom: '执行 oidc 登录后进程一直挂着；authorize 回调 127.0.0.1:19800 永远不返回。',
    cause: '本环境 SSO 的 authorize 端点不发放授权码：302 → /sp/intauthserver/logintip?code=80015。',
    fix: '禁 oidc 兜底；改为向用户索要浏览器 ETEAMSID cookie + baseUrl（AskUserQuestion）。',
    cli: 'edc-report policy login  /  edc-report auth ready（缺凭证时输出 need/how_to/askUser）',
  },
  {
    id: 'AUTH-3',
    area: 'auth',
    title: '凭证文件不存在时仍去 spawn CLI → 白等 8s',
    symptom: '未登录时命令卡住一段时间才报错，报错还不说清要什么。',
    cause: '先 spawn 再判断，且失败信息只有 "unknown"。',
    fix: '先判 `~/.e10-cli/profiles/<p>/auth` 是否存在 → 不存在立即抛带完整指引的 LOGIN_HELP，不 spawn 不等待。',
    cli: 'edc-report auth ready  (exit 1 + action:credential_required)',
  },
  {
    id: 'AUTH-4',
    area: 'auth',
    title: 'EB_HOST 与 E10_HOST 变量名不匹配',
    symptom: 'e10env.sh 里明明导出了 host，某些脚本仍报 host 缺失。',
    cause: 'e10env.sh 只导出 EB_HOST，而部分脚本读 E10_HOST / E10_BASE_URL。',
    fix: 'e10env.sh 同时导出 EB_HOST + E10_HOST + E10_BASE_URL；脚本侧统一由 eb_auth.fromEnv 兼容三者。',
    cli: 'edc-report doctor env',
    check: 'env.host-var',
  },

  // ─────────────────────────── perf ───────────────────────────
  {
    id: 'PERF-1',
    area: 'perf',
    title: '全量渲染交叉表 → 超 5 万格上限 code:555',
    symptom: '探测渲染时转很久，最后报 `code:555`。',
    cause: '数据集约 2.4 万行 × 展开 87 列 ≈ 210 万格，远超平台 50,000 格上限（≈574 行 × 87 列）。',
    fix: '**搭报表不要求渲染全量**：落库成功即可。验证用结构回读（fields / verify bind）。真要收敛数据就加查询条件（年月/部门/人员）。',
    cli: 'edc-report verify limit <reportId> [appId]   # 提前算格数',
  },
  {
    id: 'PERF-2',
    area: 'perf',
    title: '平台「先算完再拒绝」，每次超限探测白烧 15~80s',
    symptom: '明知会超限，仍每次渲染都等 15~80s 才拿到 555。',
    cause: '服务端先完成计算再校验上限，客户端无超时、无短路。',
    fix: '渲染守卫：默认直接拒绝渲染，需 EB_ALLOW_RENDER=1 显式放行；硬超时 EB_RENDER_TIMEOUT_MS（默认 30s）；命中 555 立即返回，**绝不换参数重试**。',
    cli: 'edc-report render <reportId> [appId]   # 默认被守卫拦截',
  },
  {
    id: 'PERF-3',
    area: 'perf',
    title: 'pageRowCount 未封顶 → 必然触 555',
    symptom: '设了很大的 pageRowCount 想"一次看全"，结果直接失败。',
    cause: 'pageRowCount 决定列维度（日期）是否在一页内展开，设太大就超格数上限。',
    fix: '自动封顶 574（= 50000 / 87 列），可用 EB_MAX_PAGE_ROW_COUNT 覆盖，并在结果里回报 `capped`。',
    cli: 'edc-report render <reportId> [appId] [pageRowCount]',
  },
  {
    id: 'PERF-4',
    area: 'perf',
    title: '把"渲染成功"当作搭建验收标准',
    symptom: '为了确认搭好了反复渲染，既慢又必然失败。',
    cause: '验收口径选错。',
    fix: '验收 = `saveReportDevInfo` 200 + `fields` 结构回读 + `verify bind` PASS。渲染只是诊断手段。',
    cli: 'edc-report verify all <reportId> [appId]',
  },
  {
    id: 'PERF-5',
    area: 'perf',
    title: '预览页面一直转圈（前端在等全量渲染）',
    symptom: '打开报表预览，页面长时间转圈不出结果。',
    cause: '同 PERF-1：默认无过滤条件时前端也在等全量交叉表。',
    fix: '给报表补「年月」等查询条件并设默认值，让用户打开时就自动收敛；或把 pageRowCount 收到安全值。',
    cli: 'edc-report query save / edc-report verify limit',
  },

  // ─────────────────────────── env ───────────────────────────
  {
    id: 'ENV-1',
    area: 'env',
    title: '脚本构造 https.request 漏了 port → 非 443 环境 ETIMEDOUT',
    symptom: '在 `https://host:5001` 环境所有请求超时；换 443 环境却正常。',
    cause: '写成 `{ hostname: u.hostname }`，没带 `port: u.port || 443`，于是永远连 443。',
    fix: '所有 https.request 一律 `port: u.port || 443`。（曾一次性修 36 文件 38 处）',
    cli: 'edc-report doctor scripts',
    check: 'scripts.port',
  },
  {
    id: 'ENV-2',
    area: 'env',
    title: 'resolve_e10_host.js 缺失 → 17 个脚本 MODULE_NOT_FOUND',
    symptom: '大量脚本一执行就 `Cannot find module ./resolve_e10_host`。',
    cause: '该模块在重构中被删，但多处 require 仍在。',
    fix: '恢复为 eb_auth.js 的薄封装（resolveE10Host({host}) → string），保持单一凭证来源。',
    cli: 'edc-report doctor scripts',
    check: 'scripts.require',
  },
  {
    id: 'ENV-3',
    area: 'env',
    title: '全局 edc-report 软链悬空（指向已改名的目录）',
    symptom: '`edc-report` 命令报模块找不到，或跑到老版本。',
    cause: '技能目录从 `edc-report-generator` 改名为 `weaver-e10-edcreport`，npm 全局软链仍指旧名。',
    fix: '重建软链（managed node 侧 `npm link`；AppData npm 侧无 npm.cmd，需改写 shim 三件套 sh/cmd/ps1）。',
    cli: 'edc-report doctor install  [--fix]',
    check: 'install.shim',
  },
  {
    id: 'ENV-4',
    area: 'env',
    title: '打包清单漏新依赖 → npm pack 后 MODULE_NOT_FOUND',
    symptom: '同仓开发时一切正常，`npm pack` 安装后脚本 require 失败。',
    cause: '同步脚本的 INCLUDE 清单没把新增的 eb_auth.js / resolve_e10_host.js / eb_render.js / weaver_auth_headers.py 纳入。',
    fix: '新增脚本必须同步进打包清单；并把「所有 require 可解析」做成体检项。',
    cli: 'edc-report doctor scripts',
    check: 'scripts.require',
  },
  {
    id: 'ENV-5',
    area: 'env',
    title: 'weaver_auth_headers.py 缺失 → ImportError',
    symptom: 'Python 侧 report_api_client.py 一执行就 ImportError。',
    cause: '`from weaver_auth_headers import build_auth_headers`，但该文件从未建。',
    fix: '补齐该模块（env 优先 + 一次 CLI + 浏览器一致请求头），并把 python 依赖存在性纳入体检。',
    cli: 'edc-report doctor scripts',
    check: 'scripts.py-dep',
  },
  {
    id: 'ENV-6',
    area: 'env',
    title: '安装树与开发树分叉（版本/布局/文档都不同）',
    symptom: 'C 盘跑的是 0.3.7 的老 CLI，`edc-report dataset` 报 Unknown command；D 盘开发树已是 0.3.26。',
    cause: '两棵树各自演进：布局 `bin/+lib/+vendor-scripts` vs 扁平，脚本 23 vs 45。',
    fix: '确立唯一权威 = D 盘开发树；用 `_tree_tools.py mirror` 镜像到 C 盘两处副本，`check` 做只读一致性自检。',
    cli: 'edc-report doctor trees',
    check: 'trees.diff',
  },
  {
    id: 'ENV-7',
    area: 'env',
    title: 'npm link 把入口 shebang 行 CRLF 规范成 LF → 每次都重新分叉',
    symptom: '镜像后两树永远差 1 字节；diff 显示入口文件首行不同。',
    cause: '`#!/usr/bin/env node\r\n` 被 npm link 写成 `\n`。',
    fix: '入口统一 LF（`env node\\r` 本身就会找不到解释器，是隐患）；doctor 把行尾作为体检项。',
    cli: 'edc-report doctor install  [--fix]',
    check: 'install.eol',
  },

  // ─────────────────────────── build ───────────────────────────
  {
    id: 'BUILD-1',
    area: 'build',
    title: '为了试探建一堆空壳报表',
    symptom: '应用里冒出一堆 `__build_*` / 无内容报表，需要事后清理。',
    cause: '用"建壳试探"代替字段预检；模糊匹配时先建表再改。',
    fix: '**单壳搭建**：一次任务只允许 1 个目标壳，命名即最终名；字段预检不通过就不建表（exit 4）；模糊表 exit 3 交用户确认。交付 reportId 恰好 1 个。',
    cli: 'edc-report build spec --spec <spec.json> [--dry-run]  /  edc-report cleanup shells --list',
  },
  {
    id: 'BUILD-2',
    area: 'build',
    title: 'saveReportWithCacheConfig 在本环境 404',
    symptom: '按参照脚本调双保存，第一步就 404。',
    cause: '该路由只在部分站点存在（weapp 有），`itsm.hongjing-wh.com:5001` 没有。',
    fix: '本环境**只调 `saveReportDevInfo`** 即可落库；不要因为参照脚本有就照抄。',
    cli: 'edc-report doctor env   # 环境能力探测',
  },
  {
    id: 'BUILD-3',
    area: 'build',
    title: '分页设置写接口报 400：字段名与 designKey',
    symptom: 'POST /api/bs/edc/report/allPageSetting 报 400 Bad Request。',
    cause: '① 字段名必须是 **`pageSetting`**（易误写成 `allPageSetting`）；② **必须带 `designKey`**。',
    fix: 'multipart 三件套：`sheetId` + `designKey` + `pageSetting`；值 `JSON.stringify([{split:{pageRowCount:N},sheetIndex:0,enableSplit:true}])`。回读确认 pageRowCount。',
    cli: 'edc-report verify meta / edc-report render',
  },
  {
    id: 'BUILD-4',
    area: 'build',
    title: '数据加工 SQL 视图当普通表单注册 → 挂不上',
    symptom: 'addDataset 后字段空、或数据集选项里找不到该视图。',
    cause: '「数据加工的 SQL 视图」不是 LOGIC 表单，注册形态不同。',
    fix: '注册形态 C：`sourceType:"ETEAMS"` + `sourceGroup:"sql"`（`sourceIds` = 视图 sourceId）。',
    cli: 'edc-report find form <appId> --list  /  edc-report verify contract',
  },
  {
    id: 'BUILD-5',
    area: 'build',
    title: '同一数据源被挂多次 → 左侧出现重复数据源分组',
    symptom: '数据集侧栏出现两个同名分组。',
    cause: '重复 addDataset 同一 sourceId，没有"本表已有则复用"。',
    fix: '同源只挂一次：先查本表 dataset 列表，命中同 sourceId 则复用，并在结果里回报 `datasetReused`/`datasetDuplicates`。',
    cli: 'edc-report build spec（内置去重回报）  /  edc-report dataset list',
  },
  {
    id: 'BUILD-6',
    area: 'build',
    title: '报表内残留无引用数据集 → 左侧多出空分组',
    symptom: '数据集侧栏有个 0 单元格引用的数据集，删不掉也看着乱。',
    cause: '早期试探留下的 LOGIC 数据集没清理。',
    fix: '`delDataset` 参数 `reportId` + `sourceIds`（值传 datasetId）；删前先 `check-used` 确认 0 引用。',
    cli: 'edc-report dataset check-used / edc-report dataset delete',
  },
  {
    id: 'BUILD-7',
    area: 'build',
    title: '报表列表接口返回 0 条',
    symptom: '查应用下报表列表恒为空。',
    cause: '`report/list` 只带 `appId` 不够。',
    fix: '必须带 `appid` + **`groupid=-1`** + **`objId=-1`**。',
    cli: 'edc-report cleanup shells --list  /  edc-report group list',
  },
  {
    id: 'BUILD-8',
    area: 'build',
    title: '字段引用写成本地 key → 落库后绑定丢失',
    symptom: 'saveReportDevInfo 成功，但字段格全是空的。',
    cause: 'fieldKey 拼错。',
    fix: '`fieldKey` = `{dataSetId}.{sourceId}.{fieldName}`；落库后必须 `verify bind`。',
    cli: 'edc-report verify bind <reportId> [appId]',
  },

  // ─────────────────────────── layout ───────────────────────────
  {
    id: 'LAYOUT-1',
    area: 'layout',
    title: 'Excel 隐藏行落成 rows[i]={size:0} → 变成一条可见空行',
    symptom: '报表比 Excel 多出一条空白行（用户一眼看出来）。',
    cause: 'Excel 的 `ht="0" hidden="1"` 垫行，落库时写成 `{size:0}`；**服务端会把它规范成 `null`**，于是没被隐藏。',
    fix: '不要写 `size:0` 试图隐藏行 —— **直接从布局里删掉这一行**，数据整体上移（本例 6 行 → 5 行）。',
    cli: 'edc-report verify self <reportId>  /  pitfalls --area layout',
  },
  {
    id: 'LAYOUT-2',
    area: 'layout',
    title: '表头没按 Excel 合并（固定列表头缺纵向合并）',
    symptom: 'Excel 里"列名跨两行"的表头，报表里没合并。',
    cause: '只写了日期区的横向合并，45 个固定列表头的纵向合并**一条都没写**；设计器只认 `workbook.spans`。',
    fix: '补 `spans`：固定列表头 45 条 `{row:2,col:i,rowCount:2,colCount:1}`；日期区 `{row:r,col:45,rowCount:1,colCount:3}`。',
    cli: 'edc-report verify self <reportId>',
  },
  {
    id: 'LAYOUT-3',
    area: 'layout',
    title: 'spans 语义写反 / 日期区照抄 Excel 合并宽度',
    symptom: '合并后列宽翻倍、或合并区域张冠李戴。',
    cause: '① 语义记错：`rowCount` = **行**跨度、`colCount` = **列**跨度，`row/col` 0-based（Excel mergeCells 是 1-based）。② Excel 的 `AU1:CH1` 是 42 列，但设计态每个日期块只占 3 列。',
    fix: '日期区顶部合并**只写一个块宽（3 列）**，不要照抄 Excel 的 42 列。',
    cli: 'edc-report verify self <reportId>',
  },
  {
    id: 'LAYOUT-4',
    area: 'layout',
    title: '交叉表行维度 / 交叉格 displayType 写错 → 不展开',
    symptom: '日期列不横向展开，或行不分组。',
    cause: '交叉表需明确 displayType=Group。',
    fix: '行维度与交叉格 `displayType` 必须 `Group`；列维度（日期）用 `Horizontal/Group`，其子格用 `NoExpand` + 上父格指向它。',
    cli: 'edc-report verify self <reportId>',
  },

  // ─────────────────────────── field ───────────────────────────
  {
    id: 'FIELD-1',
    area: 'field',
    title: '单元格不回显数据集名（tableName 为空）',
    symptom: '设计器里字段格不显示"数据集名.字段"，用户一眼发现只有个别格对。',
    cause: '落库时 `cellType.tableName` 全写成空串；只有用户在设计器手加的单元格才带正确值。',
    fix: '写入 workbook 的 `cellType.tableName`。后缀由注册形态决定：LOGIC → `(业务模块)`、共享表 form → `(表单)`、**ETEAMS/sql 数据加工视图 → 无后缀（裸数据集名）**。',
    cli: 'edc-report verify contract <reportId>  /  edc-report fix table-name --report-id <id> --app-id <id> --apply',
  },
  {
    id: 'FIELD-2',
    area: 'field',
    title: 'saveReportDevInfo 报 500「报表内部错误」的三大根因',
    symptom: '整份 workbook 提交后 500，且不告诉你哪里错。',
    cause: '① 照抄 `fields[]` 的键重建 → 缺 `typeName`（服务端**不回传但保存必须**）等 6 键；② 把服务端**派生键**（`dateTimeProps`/`highlightDatas`/`allNeedFields`/`fill*`）回写 → 必 500；③ `cellType.formatterType` 写成含 common 的数组（正确是**空数组**；common 属于 `tag.formatterType`）。',
    fix: '重建时：6 个必填键（typeName/allowOverflow/editorType/groupType/isActiveParent/arrowType）强制兜底；派生键**一律不写**（服务端自己生成）；formatterType 用空数组（写含 common 的数组是错的，common 属于 tag.formatterType）。',
    cli: 'edc-report fix table-name（内置重建保真自检）',
  },
  {
    id: 'FIELD-3',
    area: 'field',
    title: '拿不到线上 workbook（只能反向重建）',
    symptom: '想"只改一个字段"却发现找不到 dataTable。',
    cause: '`getReportDevInfo.workbookProps.sheets` 恒为 `{}`；`getWorkbook`/`getReportWorkbook`/`loadReport`/`devInfo` 等端点全 404；设计器页面是无数据的 SPA 壳。',
    fix: '用 **`fields[]` 反向重建 workbook**（它就是服务端对 workbook 的逐单元格回读），重建后做"保真度自检 + 保存前后快照 diff"。',
    cli: 'edc-report fix table-name --report-id <id> [--restore-from <wb.json>]',
  },
  {
    id: 'FIELD-4',
    area: 'field',
    title: 'designKey 被当成静态乐观锁复用',
    symptom: '保存偶发失败，重试有时又好了。',
    cause: '`designKey` **每次 GET 都返回新值**（即时令牌）。',
    fix: '每次保存前**紧邻**读一次 designKey，不要缓存复用。',
    cli: 'edc-report fix table-name（按此实现）',
  },
  {
    id: 'FIELD-5',
    area: 'field',
    title: 'fields[].width/height 用 || 兜底把 0 吞掉',
    symptom: 'Excel 里隐藏的列（列宽 0）在报表里变成正常宽度。',
    cause: '`Number(w) || 40` —— 0 是**合法值**（隐藏列）。',
    fix: '用 `w === undefined ? 默认 : Number(w)`，别用 `||`。合并区覆盖但无单元格的列，沿用左侧最近已知列宽。',
    cli: 'edc-report fix table-name',
  },
  {
    id: 'FIELD-6',
    area: 'field',
    title: '整份覆盖保存时冲掉了用户手加的单元格',
    symptom: '保存后用户在设计器里手动加的那一格不见了。',
    cause: '`saveReportDevInfo` 是**整份替换**；重建源（fields[]）里如果有丢失，覆盖后就没了。',
    fix: '保存前先 `--save-backup` 导出当前 workbook；发现缺格用 `--restore-from <备份>` 把"线上已不存在"的单元格补回。',
    cli: 'edc-report fix table-name --restore-from <backup.json> --apply',
  },

  // ─────────────────────────── query ───────────────────────────
  {
    id: 'QUERY-1',
    area: 'query',
    title: 'queryType 写成中文长码 → 设计器不勾选',
    symptom: '查询条件保存成功，但设计器里"显示方式"复选框是空的。',
    cause: '`queryType` 必须是 **JSON 数组短码字符串**；长码（如 "filter"/"advancedSearch"）回显不勾选。',
    fix: '写 JSON 数组短码字符串：只有 advance / 只有 filter / 两者都要；形如 `["advance"]`、`["filter"]`、`["advance","filter"]`，且 `showWhere` 置空。',
    cli: 'edc-report verify query <rid> <appId>（Q1）/ edc-report query check-echo --report-id <id> --app-id <id> / edc-report query fix-echo',
  },
  {
    id: 'QUERY-2',
    area: 'query',
    title: 'updateQueryType 批量覆盖所有条件的 queryType（含 save 后无条件调用）',
    symptom: '只改了其中一个条件，结果其它条件的 queryType 全被打回长码/全变成「高级搜索」。',
    cause:
      '`updateQueryType` 是**报表级批量**接口，会把该报表**所有**条件一起改写。两处放大器：' +
      '(1) 入参形态错了（长码）→ 全部条件一起丢回显；' +
      '(2) `query save` / `query fix-echo` 在保存后**无条件**调用它，且传入的 `showWhere` 已被置空 → ' +
      '映射成 `["advance"]` → 只要保存任意一条条件，整表显示方式被静默改成「高级搜索」。',
    fix:
      '入参必须是数组短码（或短名由 CLI 映射）；**未显式点名就不调用**——' +
      '`query save` 现在只在传了 `--show-where` 时才批量对齐；`fix-echo` 改为按修正后的条件实际值反推，' +
      '不一致则跳过；`query type` 不带 `--show-where` 同样视为未点名 → **改为只读回读**（旧实现默认 advancedSearch 直接覆盖整表）。改完立刻 `query check-echo` / `verify query` 回读全部条件自检。',
    cli: 'edc-report query type --show-where <高级搜索|筛选> / edc-report query check-echo',
  },
  {
    id: 'QUERY-3',
    area: 'query',
    title: '人员/部门条件缺 browserType → 条件不可用',
    symptom: '人员/部门筛选条件在设计器里点不开。',
    cause: '关联类型字段需要富对象描述。',
    fix: '人员/部门条件用 `GET /api/bcw/relevanceBrowser/browserBeanSearch?searchValue=<中文名>` 取 `browserType` 富对象（⚠️ 2026-09-14 修正：旧的 POST `getBrowserBean` 在本环境恒 500），并保证 `browserTypeStr` 非空且与 `originFieldType` 一致；富对象 `id` 是业务 id，校验类型要按 `name`。CLI 已自动升级简写为富对象。',
    cli: 'edc-report query save',
  },
  {
    id: 'QUERY-4',
    area: 'query',
    title: '拿 getQueryConfig 当判据（它恒为 data:null）',
    symptom: '用 getQueryConfig 判断条件是否保存成功，永远判为失败。',
    cause: '本环境该接口恒返回 `data:null`。',
    fix: '判据改为 `query list` 回读 + `query check-echo`；已废弃 getQueryConfig 门禁。',
    cli: 'edc-report query list / edc-report query check-echo',
  },
  {
    id: 'QUERY-5',
    area: 'query',
    title: 'CLI 静默注入 advancedSearchType=openCondition → 改掉报表页查询区样式',
    symptom: '用户质问「怎么又把查询条件的样式改了，不能动页面上原有展示格式」；报表页查询区从「默认样式（右上角搜索图标）」变成「展开条件」铺开。',
    cause: '`save_query_item.js` 曾在保存时**无条件注入** `advancedSearchType: \'openCondition\'`；后端 `SheetServiceImpl` 取第一条高级搜索条件的该值 → `isOpenCondition=true`。人工配的条件里**没有这个键**。',
    fix: '禁止静默注入：入参没有该键就不写该键；只有显式 `--advanced-search-type openCondition` 才写。存量数据用 `fix query-style` 清掉。注意它属**展示样式**，与「显示方式」`queryType` 是两回事，禁止绑一起写。',
    cli: 'edc-report verify query <rid> <appId>（Q2）/ edc-report fix query-style --report-id <id> --app-id <id> [--apply]',
  },
  {
    id: 'QUERY-6',
    area: 'query',
    title: 'saveQueryItem 不带 id → 变成新增，报表出现重复条件',
    symptom: '重存一条条件后，报表上同名字段出现两条（asNameIndex 自增）。',
    cause: '`saveQueryItem` 以 `id` 判更新；入参无 `id` 即 INSERT 新行。',
    fix: '更新存量条件时，payload 从线上回读对象派生并**保留 `id`**；派生键（`*_Str`/`handleDefaultValue`/`updateTime`）剥掉。误插入的行用显式 `--delete-id` 清理。',
    cli: 'edc-report fix query-style --report-id <id> --app-id <id> --delete-id <itemId> --apply',
  },
  {
    id: 'QUERY-7',
    area: 'query',
    title: '建条件只写 displayType/conditions，漏了「默认值三件套」→ 设计器弹窗坏掉',
    symptom:
      '打开「编辑查询条件」，默认值类型显示「请选择」、默认值区把**所有**控件变体同时铺开' +
      '（请输入/开始-结束日期/选择日期时间/请选择/选择日期/选择月份/选择年份…），' +
      '把其后的「日期类型 / 显示位置 / 条件必填 / 查询条件」整段顶出可视区 —— 看起来像"样式被改坏了"。',
    cause:
      '`defaultValueType` / `defaultValue`（+ `type1DefaultValue` / `type2DefaultValue` / ' +
      '`handleDefaultValue`）是弹窗渲染默认值区的**驱动字段**。三个都不写时，前端 switch 落空 → ' +
      '把每个变体都渲染一遍。设计器「新建条件」模板本身带 ' +
      '`defaultValueType:"default", defaultValue:["",""]`，所以人工配的条件永远不会缺。',
    fix:
      '建条件/改条件时**必须带上**：`defaultValueType`（`default`=常规 / `custom`=自定义）、' +
      '`defaultValue`（当前生效值）、对应模式的 `type1DefaultValue`(常规) / `type2DefaultValue`(自定义)；' +
      '值都是 **JSON 字符串**（`"[[],\\"\"]"` 这种，不是对象）。' +
      '日期占位符如 `{yearmonth:-0}` 由平台解析并回写 `handleDefaultValue`（实测 → `["2026-09",""]`），无需自己算。' +
      '另：`showOrder` 人工配置通常是 `0`（设计器模板值），API 建条件时自行填 1,2,3… 会在弹窗「排序」上留下可见差异 —— 对齐参照用 `--show-order 0`。',
    cli:
      'edc-report verify query <rid> <appId>（Q3~Q5，--fix 可自动补齐）/ edc-report fix query-default --report-id <id> --app-id <id> [--set "年月=custom:[\\"{yearmonth:-0}\\",\\"\\"]"] [--apply]',
  },

  // ─────────────────────────── excel ───────────────────────────
  {
    id: 'EXCEL-1',
    area: 'excel',
    title: 'openpyxl 读不了该 xlsx（styles.xml 非法 border）',
    symptom: '`load_workbook` 抛 `ValueError`，报表需求明明读不出来。',
    cause: '该文件的 `styles.xml` 有非法 border `style` 值，openpyxl 直接拒绝。',
    fix: '改为解 zip 直读 XML（sharedStrings + sheetN.xml），自行处理 `t="s"` / `inlineStr` / 数值。',
    cli: 'pitfalls --area excel（解析脚本 _read_xlsx.py）',
  },
  {
    id: 'EXCEL-2',
    area: 'excel',
    title: '解析单元格时用 enumerate 下标 → 整行错位一列',
    symptom: '表头整体偏移：本应是「部门」的首列读成了「人员姓名」。',
    cause: '`<c>` 元素**可以没有 `r` 属性**，此时列位必须**累加续位**（cur+1），用 enumerate 下标会在遇到跳列时整体错位。',
    fix: '解析时维护累积列号 `cur`：有 `r` 就取其列号，没有就 `cur += 1`。用列宽/填充色互证校验。',
    cli: 'pitfalls --area excel',
  },
  {
    id: 'EXCEL-3',
    area: 'excel',
    title: 'Excel 表头行号 / 数据行号想当然',
    symptom: '把星期行当数据行，或漏掉隐藏垫行。',
    cause: '典型表头是 2 行（列名 + 星期），中间还有 1 行隐藏垫行，数据从第 6 行开始。',
    fix: '先 dump 前 10 行的**原始 XML**（含 ht/hidden/spans）再定布局，不要只看"有值的行"。',
    cli: 'pitfalls --area excel',
  },
  // ─────────────────── layout · 冻结单元格（2026-09-14） ───────────────────
  {
    id: 'LAYOUT-F1',
    area: 'layout',
    title: '冻结单元格只写 sheet.frozenRowCount → 预览不冻结',
    symptom: '`frozenRowCount` / `sheet.tag.fixedCell` 都写了，保存也 200，但预览里表头照样跟着滚。',
    cause: '**唯一持久化**的冻结标记是 `cell.tag.fixed` → 服务端存成 `field.fixed = 1`；预览引擎 `AnalysisParams.analysisFrozenCell()` 只认它：取第一个 `fixed==1` 字段的 minCell，`frozenRowCount=cell.x`、`frozenColumnCount=cell.y`。`sheet.frozenRowCount` 与 `sheet.tag.fixedCell` 保存侧根本不读。',
    fix: '在锚点格写 `tag.fixed = true`（锚点 = 想冻结区域的「右下角+1」，其**上方行 + 左侧列**被冻结）；落库前先清掉所有旧的 `fixed`，保证只有一个。锚点格**不必是空格**——设计器只在锚点是空格时才补 `cellText="fixed-cell-tag"`，占用格它什么都不写，所以直接给数据格置 `fixed` 是唯一可行解。**别**顺手写 `cellText="fixed-cell-tag"`：服务端会据此把该格四边边框+底色清空（改了未点名样式）。',
    cli: 'edc-report fix freeze --report-id <id> --app-id <aid> --anchor 4,3 [--apply]',
  },
  {
    id: 'LAYOUT-F2',
    area: 'layout',
    title: '同一坐标出现两条记录（表头格被字段压住）→ 整份重建必丢一格',
    symptom: '`getReportDevInfo.fields` 里同一 `(x,y)` 返回 2 条（例：`Const 聘用类型 xCount=2` + 新拖入的 `Field name`）；重建 workbook 后该格只剩一条。',
    cause: '在设计器里把字段**拖到某个已有表头格上**，旧的 Const 记录未被清掉，服务端两条并存。workbook 的一个坐标只能放一个 cell，任何整份重建都只能保留一条。',
    fix: '落库前先做**重复坐标体检**：有重复 → 停手，列出各条 `id/createTime`，让用户确认取舍（或先在设计器里清理），**禁止自行择一**。',
    cli: 'edc-report fix freeze --report-id <id> （内置重复坐标拦截，exit 3）',
  },
];

// ---------------- args ----------------
function parseArgs(v) {
  const a = { areas: [], json: false, listAreas: false, words: [] };
  for (let i = 0; i < v.length; i++) {
    if (v[i] === '--area') a.areas.push(String(v[++i] || '').toLowerCase());
    else if (v[i] === '--json') a.json = true;
    else if (v[i] === '--list-areas') a.listAreas = true;
    else if (v[i] === '-h' || v[i] === '--help') a.help = true;
    else if (!v[i].startsWith('--')) a.words.push(v[i].toLowerCase());
  }
  return a;
}

function match(p, a) {
  if (a.areas.length && !a.areas.includes(p.area)) return false;
  if (!a.words.length) return true;
  const hay = [p.id, p.title, p.symptom, p.cause, p.fix, p.cli || '', AREA_LABEL[p.area] || '']
    .join(' ')
    .toLowerCase();
  return a.words.every((w) => hay.includes(w));
}

// ---------------- main ----------------
function main() {
  const a = parseArgs(process.argv.slice(2));

  if (a.help) {
    console.log(`Usage: node pitfalls.js [关键词...] [--area <area>] [--json] [--list-areas]

领域: ${Object.keys(AREA_LABEL).join(' | ')}

示例:
  node pitfalls.js                       # 全部条目
  node pitfalls.js 500                   # 全文匹配 "500"
  node pitfalls.js --area field --json   # 字段契约类，结构化输出
`);
    return;
  }

  if (a.listAreas) {
    if (a.json) {
      console.log(JSON.stringify(AREA_LABEL, null, 2));
    } else {
      for (const [k, v] of Object.entries(AREA_LABEL)) {
        const n = PITFALLS.filter((p) => p.area === k).length;
        console.log(`  ${k.padEnd(8)} ${v}  (${n} 条)`);
      }
    }
    return;
  }

  const hit = PITFALLS.filter((p) => match(p, a));

  if (a.json) {
    console.log(JSON.stringify({ total: PITFALLS.length, matched: hit.length, items: hit }, null, 2));
    return;
  }

  if (!hit.length) {
    console.log(`未命中条目（共 ${PITFALLS.length} 条）。用 --list-areas 看领域，或减少关键词。`);
    process.exitCode = 1;
    return;
  }

  console.log(`\nedc-report pitfalls —— 历史踩坑知识库（命中 ${hit.length} / ${PITFALLS.length}）\n`);
  const groups = {};
  for (const p of hit) (groups[p.area] = groups[p.area] || []).push(p);
  for (const [area, list] of Object.entries(groups)) {
    console.log(`━━━ ${area} · ${AREA_LABEL[area] || ''} `.padEnd(72, '━'));
    for (const p of list) {
      console.log(`\n  [${p.id}] ${p.title}`);
      console.log(`    症状: ${p.symptom}`);
      console.log(`    根因: ${p.cause}`);
      console.log(`    对策: ${p.fix}`);
      if (p.cli) console.log(`    CLI : ${p.cli}`);
    }
    console.log('');
  }
  console.log('体检: edc-report doctor   （把可自动化的检查项一次跑完）\n');
}

if (require.main === module) main();

module.exports = { PITFALLS, AREA_LABEL };
