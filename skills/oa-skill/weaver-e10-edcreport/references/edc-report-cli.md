# edc-report · CLI 优先（强制）

> 包：`edc-report/`（npm `edc-report`）。安装见 `edc-report/README.md`。  
> **原则**：历史会话沉淀到 Skill 的**可执行**调整点，一律走 CLI；规则判断仍读 `references/*`，禁止再写一次性 debug 脚本。  
> **最高优先级**：`user-request-scope-only-guide.md` — **仅改用户点名项**；未点名禁止改删；`edc-report policy scope`。

---

## 〇、执行优先级（强制）

| 优先级 | 入口 |
|--------|------|
| **0（政策）** | **仅改用户点名项** — 未点名不执行破坏性/改写类命令（见 §一 §A0） |
| **1** | `e10-login` |
| **2** | `edc-report …`（本表全部能力） |
| **3** | 裸 `node`/`python` scripts（**仅 CLI 未安装时**） |

---

## 一、历史会话沉淀 → CLI 映射（强制对照）

| Skill 硬规则 / 指南 | 可执行动作 | **优先 CLI** |
|---------------------|------------|--------------|
| **§A0 仅改用户点名项（最高）** | 改配置前自检范围；禁止擅自删改 | **`edc-report policy scope`**；破坏性命令须用户点名：`lifecycle delete` / `cleanup shells` / `restore` |
| **§A0.1 / 冷启动扫描** | 开场只读 cold-start 一页；禁通读知识库；交链即停 | **`policy build`** / `auth ready`；`cold-start-scan-guide.md` |
| **登录低版本兼容** | &lt;1.5 未登录：建议升级或索要 ETEAMSID+base-url 后 set | **`edc-report auth ready`**（`askUser`）/ **`policy login`** |
| **新建报表三模式** | 空白 / 模版创建 / 快速构建-列表式 | **`edc-report create models|blank|template|quick`**；指南 `report-create-modes-guide.md` |
| **默认表头样式** | 未指定样式且无效果图 → 蓝标题+灰列头；用户指定/效果图优先 | `validate style`；`build spec`；`default-header-style-guide.md` |
| **找表 / 未给表名** | **仅当前应用** getList；未给准确表名或模糊命中 → 候选 + **二次确认**；禁静默 addDataset | `find form` / `--list` / `--suggest`（exit 3=须确认） |
| **★ 声明式一次搭表（模式 A 首选）** | **字段预检**（不精确命中 exit 4 不建表）→ **目标名**一次创建 → 本表取字段（同源只挂一次）→ 落库；禁空壳/rename；exact 直建 / fuzzy 须确认 | **`edc-report build spec`**；`--form-confirmed --source-id`；`--field-confirmed`；`spec-build-schema.md` |
| **规则 A · 字段找不到 → 让用户指定** | 需求字段在当前数据集表单无精确命中 → exit 4 · 不建表 · 输出 `unmatched`/`candidates`/`allFields` | `edc-report policy ask`；`spec-build-schema.md §2.1` |
| **规则 B · 表没指明/非精确匹配 → 让用户指定** | 未指出具体表 或 模糊/多命中/未命中 → exit 3 · 不建表 · 输出 `candidates` | `edc-report policy ask`；`spec-build-schema.md §1.1` |
| **字段精确绑定（2026-09-11 强制）** | 仅精确匹配；无命中/文案≠字段显示名 → **让用户指定字段**；禁模糊兜底、禁回退系统字段 | `build spec`（exit 4 带 `candidates`/`allFields`）；`field-bind-exact-match-guide.md §2.0` |
| **同源只挂一次** | 本表已有同 sourceId 数据集必须复用；否则左侧出现重复数据源分组 | `build spec`（`datasetReused`/`datasetDuplicates`）；`add-dataset-registration-guide.md §2.1` |
| **列表页操作** | 分组增删；视图/排序说明；矩阵；移动；转移 | **`policy list-page`** / `group` / `scope matrix` / `lifecycle move\|transfer` / `app search` |
| **数据集侧栏** | 自定义名/聚合/排序/替换/移除 | **`edc-report dataset …`**；指南 `dataset-sidebar-ops-guide.md` |
| §A 定点修改 | 仍由 Agent 裁剪改动面；落库后自检 | `edc-report verify self` / `verify all` |
| §B 查询条件 saveQueryItem | multipart 单对象；**条件级 `queryType` 写 JSON 数组短码 `'["advance"]'`**（`showWhere` 置空）；save 后 **updateQueryType（同数组形态，它会批量覆盖所有条件）**；人员/部门自动补 `browserType`/`browserTypeStr`；**默认值三件套 `defaultValueType`/`defaultValue` 必写** | `edc-report query save` / `query type` / `query list` / `query check-echo` / `query fix-echo` / **`verify query`** / `validate query` |
| **事件超链接传参** | 查询串 `参数名=坐标`；路径 `{坐标}`；禁全角？；Field 须写 pcHreflink | **`validate href [--fix]`**；`event-hreflink-guide.md` |
| §C / §D 父格 + 落库自检 | 伪 `(0,0)`、超链接父格、Field 绑定 | `edc-report verify self` + `verify bind` 或 `verify all` |
| **§L 设计区空白防护** | 禁 Number(雪花 sheetId)；showLocation≠0；滑动分页完整；快照默认 `{报表名}-{date}-{time}` | `edc-report validate blank` / `verify blank`；`snapshot set`；`verify all` 含 blank |
| **§4.6.1 网格线** | **默认关**；**workbook 禁含 `gridline` 键（存在即 500）**；只写 page `gridLine:0\|1` | **`edc-report validate gridline`** / `verify gridline`；`safe_report_save` strip |
| **报表内部错误门禁** | name/nameLabelId/groupId + 条件格式 + 自检 | `verify meta` + `verify condition` + `verify all`；指南 `report-internal-error-guide.md` |
| **★ 环境体检（工具链坑）** | 凭证/host+port/host 变量名/CLI 版本/连通性探针；脚本 require 解析、漏 port 扫描、python 依赖、语法；全局 shim 悬空、入口行尾；三树一致性；渲染守卫 | **`edc-report doctor [env\|scripts\|install\|trees\|perf\|all] [--json] [--fix] [--full]`** |
| **★ 踩坑知识库（动手前先扫）** | 历史会话全部坑：症状/根因/对策/对应 CLI，按领域检索 | **`edc-report pitfalls [关键词] [--area auth\|perf\|env\|build\|layout\|field\|query\|excel] [--json] [--list-areas]`** |
| **渲染守卫** | 默认**拒绝**全量渲染（必然 555 且白烧 15~80s）；需 `EB_ALLOW_RENDER=1` 放行；pageRowCount 自动封顶 574 | **`edc-report render <reportId> [appId] [pageRowCount]`**；`eb_render.js` |
| **★ 渲染规模预检** | 不渲染，只做算术：设计列数 × 数据集行数 vs 50000，给出超限倍数、安全行数、收敛建议 | **`edc-report verify limit <reportId> [appId] [--rows N] [--cols N] [--date-values N]`** |
| **★ tableName 回显修复** | 单元格不回显数据集名 → 从 `fields[]` 反向重建 workbook 重写 `cellType.tableName`（默认 dry-run，`--apply` 落库；`--restore-from` 补回被覆盖的手绑单元格） | **`edc-report fix table-name --report-id <id> [--app-id <id>] [--apply]`**；`dataset-table-field-contract-guide.md §四点六` |
| **★ 查询条件合规体检** | 一次跑完 Q1~Q10：queryType 数组短码 / advancedSearchType 必须为空 / 默认值三件套 / id+asNameIndex 唯一 / browser 富对象 / filterParam / showOrder / 报表级是否混杂 | **`edc-report verify query <reportId> <appId> [--json] [--fix]`**（有 FAIL → exit 1；`--fix` 幂等修安全项，绝不新增删条件） |
| **tableName 契约体检（只读）** | 报告 tableName 缺失数 / 规范取值 / 重建保真度，不落库 | **`edc-report verify contract <reportId> [appId]`** |
| **查询条件回显修复** | 长码/空值 `queryType` → 数组短码，恢复设计器勾选 | **`edc-report fix echo --report-id <id> --app-id <appId>`**（同 `query fix-echo`） |
| **查询条件「样式」清理** | 条件被静默写过 `advancedSearchType='openCondition'` → 报表页查询区从「默认样式」变成「展开条件」；同时可显式删除误插入的重复条件行 | **`edc-report fix query-style --report-id <id> --app-id <appId> [--id <itemId>...] [--delete-id <itemId>...] [--apply]`**（默认 dry-run）；`query-condition-api-guide.md §2.1.9` |
| **查询条件默认值补齐** | 缺 `defaultValueType`/`defaultValue` → 设计器弹窗「默认值类型」= 请选择、默认值区炸开、日期类型/显示位置/条件必填被顶出可视区 | **`edc-report fix query-default --report-id <id> --app-id <appId> [--set "<文本>=<default\|custom>:<JSON值>"]... [--all] [--show-order <n>] [--apply]`**（默认 dry-run）；`query-condition-api-guide.md §2.1.10` |
| **冻结单元格 / 锁定列** | 锚点格写 `tag.fixed`（唯一持久化标记）→ 冻结其上方行 + 左侧列；锚点不必是空格；落库前清旧 `fixed`；重复坐标自动拦截 | **`edc-report fix freeze --report-id <id> [--app-id <id>] --anchor <x,y> [--apply]`**（默认 dry-run）；`layout-showlocation-freeze-guide.md §2.6` |
| 跨源 leftFilter fieldKey | 组装筛选 JSON | `edc-report py left-filter` |
| 配置 / 公式校验 | validate | `edc-report py validate` |
| 预聚合 | 关闭建议 | `edc-report py preagg` |
| 字段绑定门禁 | fieldsKey 精确匹配 + 文案/显示名一致性 + 重复数据集体检 | `edc-report verify bind`（`--strict`） |
| 版本 / 快照 / 权限范围 | 生命周期附属；快照默认名 `{报表名}-{date}-{time}` | `version` / `snapshot set\|list` / `scope` |
| 安全局部保存 | 库：`scripts/safe_report_save.js`（模块，供建表脚本 require） | 建表脚本内 `require`；交付前仍 `verify all` |

**禁止**：上述能力已有 CLI 时，再在 `.workbuddy/` 堆 `debug_*.js` / 手写 saveQueryItem multipart。  
**禁止**：用户未点名时执行 `lifecycle delete` / `cleanup shells` / 整表覆盖 save / 擅自 `restore`。

---

## 二、命令速查

```bash
# 环境体检 + 踩坑知识库（动手前先跑）
edc-report doctor                       # 全量体检；有 FAIL → exit 1
edc-report doctor env|scripts|install|trees|perf
edc-report doctor --json                # Agent 消费
edc-report doctor --fix                 # 自动修：入口 CRLF→LF、shim 路径改指
edc-report doctor --full                # 追加全量 JS 语法检查（慢）
edc-report pitfalls                     # 全部坑（41 条，按领域分组）
edc-report pitfalls 500                 # 关键词全文匹配
edc-report pitfalls --area field        # 按领域：auth|perf|env|build|layout|field|query|excel
edc-report pitfalls --list-areas
edc-report pitfalls --json

# 渲染（默认被守卫拦截）
edc-report render <reportId> [appId] [pageRowCount]
EB_ALLOW_RENDER=1 edc-report render <reportId> [appId] 100

# 渲染规模预检（不渲染）
edc-report verify limit <reportId> [appId] [--rows N] [--cols N] [--date-values N]

# tableName 回显：体检 → 修复
edc-report verify contract <reportId> [appId]                       # 只读
edc-report fix table-name --report-id <id> --app-id <aid>            # dry-run
edc-report fix table-name --report-id <id> --app-id <aid> --apply    # 落库
edc-report fix table-name --report-id <id> --restore-from wb.json --apply
edc-report fix echo --report-id <id> --app-id <appId>                # 同 query fix-echo
edc-report fix freeze --report-id <id> --app-id <aid> --anchor 4,3   # dry-run（冻结上方4行+左侧3列）
edc-report fix freeze --report-id <id> --app-id <aid> --anchor 4,3 --apply
edc-report fix freeze --report-id <id>                                # 缺省锚点=首个数据行,第0列（仅冻结表头）
edc-report fix query-style --report-id <id> --app-id <aid>            # dry-run：列出被注入 advancedSearchType 的条件
edc-report fix query-style --report-id <id> --app-id <aid> --apply    # 清掉（保留 id/顺序/queryType）
edc-report fix query-style --report-id <id> --app-id <aid> --delete-id <itemId> --apply  # 顺带删误插入的重复行
edc-report fix query-default --report-id <id> --app-id <aid>          # dry-run：列出缺「默认值三件套」的条件
edc-report fix query-default --report-id <id> --app-id <aid> --apply  # 补齐（default 模式、空默认值）
edc-report fix query-default --report-id <id> --app-id <aid> \
     --set '年月=custom:["{yearmonth:-0}",""]' --set '部门=default:[[],""]' --apply   # 点名默认值
edc-report fix query-default --report-id <id> --app-id <aid> --all --show-order 0 --apply  # 顺带对齐「排序」=0

edc-report auth ready
edc-report policy scope
edc-report policy build
edc-report policy ask         # 规则 A/B：字段找不到 / 表没指明或非精确匹配 → 停下问用户

edc-report build spec --spec <spec.json>
edc-report build spec --spec <spec.json> --form-confirmed --source-id <id>  # 模糊确认后
edc-report build spec --spec <spec.json> --field-confirmed "党组织,姓名"     # 文案≠字段显示名，已确认
edc-report build spec --spec <spec.json> --dry-run                          # 打印列→字段绑定映射
edc-report find form <appId> <表单名>
edc-report find form <appId> --list
edc-report find form <appId> --suggest "资产,台账"   # 未给准确表名：候选 + needConfirm
edc-report join suggest --app-id <appId> --parent-form "主表" --child-form "子表"

edc-report query list --report-id <id> --app-id <appId>
# 查询条件：体检 → 修复
edc-report verify query <reportId> <appId>                          # 只读体检（Q1~Q10）
edc-report verify query <reportId> <appId> --json                   # 结构化输出
edc-report verify query <reportId> <appId> --fix                    # 幂等修安全项（清样式字段/补三件套/短码化）
edc-report fix query-style --report-id <id> --app-id <aid> --apply  # 清 advancedSearchType（另可 --delete-id 删重复行）
edc-report fix query-default ... --set '年月=custom:["{yearmonth:-0}",""]' --apply

edc-report query save --report-id <id> --app-id <appId> --item queryItem.json
edc-report query save ... --show-where "高级搜索"   # 默认；用户要筛选时传「筛选」
edc-report query type --report-id <id> --app-id <appId> [--show-where 高级搜索|筛选]
  # ⚠️ 不传 --show-where = 未点名 → **只回读不改**（updateQueryType 是批量覆盖接口）
edc-report validate query --map-show-where "筛选"
edc-report validate query --validate-show-where --file item.json

edc-report verify bind <reportId> [appId] [--strict]
edc-report verify self <reportId> [appId]
edc-report verify all <reportId> [appId]
edc-report verify meta <reportId> [appId]
edc-report verify condition <reportId> [appId]
edc-report validate base --name "报表名" --name-label-id -1 --group-id 0
edc-report validate condition --file rule.json
edc-report validate condition --map "介于 1 5"
edc-report validate condition --map "数据条"
edc-report validate condition --map "图标集"
edc-report validate format --map "货币"
edc-report validate format --map "年份"
edc-report validate transform --map "人员"
edc-report validate transform --list
edc-report validate href --map "弹出页"
edc-report validate href --file cell.json
edc-report validate href --list
edc-report validate href --file cell.json --fix   # 全角？→ASCII ?
edc-report verify format <reportId> [appId]
edc-report validate blank --inline '{"snapshot":{"enableSnapshot":true,"sheetId":"..."}}'
edc-report validate gridline --inline '{"sheetProps":[{"gridLine":0}],"sheets":{"Sheet1":{"name":"Sheet1"}}}'
edc-report validate gridline --file patch.json   # sheets.* 含 gridline → exit 1
edc-report validate gridline --fix --file patch.json
edc-report validate style --list
edc-report validate style --inline "{}"
edc-report verify blank <reportId> [appId]

# 破坏性：仅用户明确要求
edc-report cleanup shells --app-id <appId> --report-id <id>
edc-report cleanup shells --app-id <appId> --prefix __build_
edc-report lifecycle delete --host ... --app-id ... --report-id ...

edc-report version save --report-id <id>
edc-report snapshot set --report-id <id> [--cron "0 0/1 * * * ?"] [--snapshot-name "..."]
edc-report snapshot list --report-id <id>
edc-report scope set --report-id <id> --app-id <appId> --scope all

edc-report py validate <config.json>
edc-report py left-filter ...
edc-report py preagg ...
```

---

## 三、与 Skill 的关系

| | Skill（Agent） | CLI |
|--|----------------|-----|
| 职责 | 规则、需求分析、布局、关联确认话术、**改动范围闸门** | 确定性 API / 校验 / 清理 |
| 规则文档 | `SKILL.md` + `references/`（含 **user-request-scope-only-guide.md**） | 行为对齐 `scripts/`；`policy scope` 打印政策 |
| 脚本源 | `../scripts/` | 唯一来源：CLI 直接解析同仓 `scripts/` |

**新增沉淀规则时的整合清单（强制）**

1. 写入 `references/*.md` + `SKILL.md` 硬规则  
2. 能脚本化 → 加 `scripts/*` + `edc-report/cli.js` 子命令  
3. 本文件 §一 映射表补一行  
4. **把「新踩的坑」补成 `scripts/pitfalls.js` 的一条**（id/area/symptom/cause/fix/cli），能自动检查的再补进 `scripts/doctor.js`  
5. bump `edc-report/package.json` version  
6. 同步 extract / 分发包；**改完必须 `edc-report doctor trees` 确认三树一致**

---

## 二点五、doctor / pitfalls 用法（Agent）

```bash
# ① 会话开场或环境报错时：一次体检定位（不要逐个脚本手工试）
edc-report doctor --json

# ② 动手前查有没有同类历史坑（避免重复踩）
edc-report pitfalls --area build --json

# ③ 周期回归（改动 Skill 后必跑）
edc-report doctor trees scripts
```

**doctor 检查项 ↔ pitfalls id 对照**

| doctor 项 | pitfalls | 说明 |
|-----------|----------|------|
| `env.auth` | AUTH-1~3 | 凭证可用性与快速失败 |
| `env.host-var` | AUTH-4 | EB_HOST / E10_HOST 变量名不一致 |
| `env.probe` | ENV-1 | 连通性探针（含 port） |
| `scripts.require` | ENV-2 / ENV-4 | require 不可解析（MODULE_NOT_FOUND） |
| `scripts.port` | ENV-1 | 漏 port / 把 host:port 当 hostname |
| `scripts.py-dep` | ENV-5 | python 本地模块缺失（ImportError） |
| `scripts.query-guard` | QUERY-2 / QUERY-5 | 查询条件守卫是否被回退（静默注入 advancedSearchType / 硬编码批量覆盖 / query type 未点名仍改） |
| `scripts.query-verify` | QUERY-1~7 | verify_query_items.js 在位 |
| `install.shim` | ENV-3 | 全局 shim 悬空 |
| `install.eol` | ENV-7 | 入口 CRLF（npm link 会重新分叉） |
| `trees.diff` | ENV-6 | 安装树与开发树分叉 |
| `perf.render-guard` | PERF-1~3 | 渲染守卫与 5 万格上限 |
| `verify limit` | PERF-1 / PERF-5 | 渲染规模预检（超限倍数） |
| `verify contract` | FIELD-1 | tableName 契约回读 |

---

## 四、Agent 检查清单

- [ ] **命令报错 / 环境异常 / 会话开场 → 先 `edc-report doctor`（一次定位），不要逐个脚本手工试**（§二点五）
- [ ] **动手前扫 `edc-report pitfalls --area <域>`，确认没有同类历史坑**
- [ ] **改过 Skill → `edc-report doctor trees scripts` 确认三树一致 + require 全解析**
- [ ] **本轮用户点名改动列表是否已写下？是否未越界？**（§A0）
- [ ] **开场是否只读 `cold-start-scan-guide.md` + ≤2 篇点名 guide？**（禁通读 SKILL/知识库）
- [ ] **未扫 `.workbuddy/` / `e10-cli*` / 嵌套 `weaver-e10-login`？**
- [ ] **临时壳 ≤1；失败/会话终止已 cleanup？**（§F）
- [ ] **同款样式未逐格 validate format？**（§K）
- [ ] **未查找 e10-cli*（本包无）？只加载点名 guide？**（§A0.2）
- [ ] **未建 `__build_*` 空壳？** 目标名一次落库；模糊表 exit 3 确认前不建表
- [ ] 找表：exact 才可 autoBind；**模糊 / 未命中 → 确认**（禁静默绑表、禁跨报表 datasetId）
- [ ] **低版本未登录：已建议升级或 AskUser 索要 ETEAMSID+base-url？未因版本阻断？**（`policy login`）
- [ ] 本任务确定性步骤是否都能对应到 §一 CLI？
- [ ] 多表未写关联 → `join suggest` + 用户确认话术
- [ ] 查询 → `query save`（默认高级搜索 + updateQueryType；失败提示后继续）；用户点名筛选才 `--show-where 筛选`
- [ ] 查询 → 回读 `queryType` 为**JSON 数组短码字符串** `'["advance"]'`/`'["filter"]'`（以 `[` 开头；长码 `"advancedSearch"` 会导致设计器不勾选）；**`updateQueryType` 会批量覆盖所有条件的 `queryType`，其入参也必须是数组短码**；保存后跑 `edc-report query check-echo`，异常用 `query fix-echo`；人员/部门条件 `browserTypeStr` 非空且与 `originFieldType` 一致
- [ ] `getQueryConfig` 本环境恒为 `data:null`，**不可作判据**（已废弃该门禁）
- [ ] 事件超链接 → `validate href`（ASCII ?；`参数名=坐标`；禁全角？）
- [ ] 删除/cleanup/restore → **仅用户明确要求**
- [ ] 交付前 → 先交设计器 URL；`verify all` 可后置（定点场景可裁剪）
- [ ] 开快照 → `snapshot set`（默认名 `{报表名}-{date}-{time}`；禁 Number sheetId）
- [ ] 网格线 → workbook **无** `gridline` 键；page `gridLine=0`；`validate gridline`
- [ ] 条件格式 → `validate condition`（含数据条/图标集）；禁 SpreadJS 黑盒
