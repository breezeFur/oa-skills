# 会话搭建性能与禁令（强制）

> **适用**：新开会话做报表搭建 / 改已有报表。  
> **冷启动一页（开场必读）**：`cold-start-scan-guide.md` — 本文件为展开细则，**禁止**开场与 cold-start 重复通读两遍。  
> **目标**：已登录不重登；找表只扫当前应用；**只扫登录+报表必要 CLI**；禁止下 SpreadJS 黑盒；落库后先交地址；编辑只改点名项。  
> **CLI**：`edc-report auth ready` · `edc-report policy build` · `edc-report policy login` · `edc-report find form` · `edc-report policy scope`

---

## 一、登录：只走 e10-login（强制 · 禁扫文件）

| 步骤 | 动作 | 禁止 |
|------|------|------|
| **1** | **仅** `e10-login status` 或 `edc-report auth ready`（秒级） | — |
| **2a** | 输出含「已登录」且有 ETEAMSID → **立刻进入搭建** | 再跑 `oidc` / `whoami` / 二次确认 |
| **2b** | 未登录 + CLI ≥1.5 → **一次** `oidc`（或 `set`）后再 `auth ready` | 循环登录校验、固定 sleep |
| **2c** | 未登录 + CLI &lt;1.5（`login_required_legacy_set`）→ **AskUserQuestion**：① 建议升级 1.5+ 再 oidc；② 请用户提供 **ETEAMSID + base-url** 后 `set`（见 `policy login` / `auth ready` 的 `askUser`） | 「必须先升级才能搭表」；未索要就编造 token |

**登录扫描禁令（强制）**：

- 登录**只执行** `e10-login` / `edc-report auth ready` CLI  
- **禁止**为登录去 `Glob`/`Grep`/`Read` 乱扫仓库、`e10-cli*`、profile 明文、无关 md  
- **禁止**开场通读完整 `weaver-e10-login`（仅 `auth ready` 失败需登录时再读最短段落 / `policy login`）  
- 已登录 → **0 文件扫描**，直接搭表  
- **低版本**：建议升级，或提示用户提供 ETEAMSID 等必要信息；**禁止因版本阻断搭表**

细则：`e10-login-integration.md` §「快速路径」· `edc-report policy login`。

---

## 一补充、冷启动 / 首响（强制 · 防 502 与超时）

> **权威一页**：`cold-start-scan-guide.md`（开场只读该页）。以下为摘要，避免与 SKILL 全文重复加载。

首次加载本 Skill 时，**禁止**一口气通读 `SKILL.md` 全文 + 全部 `references/` + 知识库。  
过载会导致首包过大、网关 **502**/超时、体感极慢。

| 阶段 | 允许加载 | 禁止 |
|------|----------|------|
| **首响 ≤ 开场** | `cold-start-scan-guide.md` + `auth ready`；用户点名的 1～2 篇 guide | 通读 SKILL 全文、knowledge-base、help、分析模板、全部 references |
| **搭表进行中** | 按任务点名再加载单篇（找表/落库/条件格式…） | 「先把文档目录扫一遍再干活」；扫 `.workbuddy/` |
| **API 建表** | `api-report-build-fast-path.md` 轻量清单 | 开场需求分析模板 + 知识库第九节 |

**冷启动顺序（强制）**：`auth ready` →（缺凭证则立即向用户索要 ETEAMSID；禁 oidc）→ `find form` / 定点 patch → 仅那时再读对应 guide。

---

## 二、找表：当前应用绝对优先（强制）

用户已给 **appId / appName / 应用上下文** 时：

| 优先级 | 允许 | 禁止（首轮） |
|--------|------|----------------|
| **P0** | `GET /api/bs/ebuilder/form/obj/getList/{appId}` 或 `edc-report find form <appId> <表单名>` | `GET /ds/group` 拉全部分组 |
| **P1** | 应用内 `listByPage` **带 appId + 表名关键字** 分页 | 无关键字翻页扫全库 |
| **P2** | 仅 P0/P1 未命中后，才允许别处有限次检索 | 一上来全系统多 module 轮询 |

**硬禁令**：已指定应用时，**禁止**首轮加载「整个系统」的分组树 / 全库分页。  
分页也必须 **先带 appId 限域**，不得先拉系统级再本地过滤。

细则：`app-datasource-lookup-guide.md`。

---

## 三、SpreadJS：禁止每次下载（强制）

| 规则 | 说明 |
|------|------|
| **禁止** | 为「摸条件格式 / 对齐枚举」去下载 `gc.spread*.js`、`route_ReportDesigner.js`、设计器 main chunk |
| **禁止** | 循环黑盒逆向、反复保存试探未知枚举 |
| **允许** | 使用本 Skill 已沉淀文档与 CLI 白名单（`condition-format-guide.md`、`cell-config-echo-guide.md`） |
| **若确需本地库** | 一次性落到固定缓存目录（如 `.workbuddy/cache/spreadjs/`），**之后只读缓存**；不得每任务重下 |

报表搭建本身 **不需要** SpreadJS 运行时；workbook JSON 按指南拼即可。

---

## 四、条件格式：禁黑盒返工；落库先交地址（强制）

1. 突出显示 / 数据条 / 图标集 → **只走** `condition-format-guide.md` + `edc-report validate condition`  
2. **禁止**下载前端包、禁止多轮试错保存探结构  
3. `saveReportDevInfo` 成功拿到 `reportId` 后 → **立刻**给出设计器地址并 **结束本轮**（`report-delivery-contract.md`）  
4. 条件格式校验失败 → 提示用户；**不得**阻塞首轮地址  
5. **默认不**生成 HTML、不跑 verify→再 save；**禁止**交链后继续空转；全局修复 ≤1  
6. **已移除**测试用例/原型能力 —— 禁止查找相关脚本


---

## 五、最小扫描面：只扫登录 + 报表必要 CLI（强制）

> 搭建报表时：**只加载登录门禁 + 本报表必要的 `edc-report` CLI / 点名指南**。  
> **本包不含 `e10-cli/` / `e10-cli-bundle/`** — 禁止查找、通读、遍历（白费首轮时间）。

| 允许 | 禁止 |
|------|------|
| `edc-report auth ready` / `e10-login status` | 完整通读 `weaver-e10-login`（仅未登录时） |
| `edc-report find/verify/query/snapshot/validate…` | 扫描 **`e10-cli*`** / `actionflows`（本包无此目录） |
| 本任务点名的 `references/*-guide.md` | 其它无关 skill；开场通读全部 references |

**硬禁令**：禁止为搭表去 Glob/Grep `e10-cli`；对应 Skill **§A0.2**。

---

## 六、编辑已有报表：只改点名项（强制）

见 `user-request-scope-only-guide.md` + `targeted-fix-guide.md`。

- 「改滑动分页 / 快照 / 某一格」→ **禁止**整表重识别、重扫 fields、重跑需求分析  
- 只 patch 点名能力；其余原样写回

---

## 六补充、API 落库耗时实测与提速（2026-09-09 基准 · 强制参考）

> 结论先说：**搭表真正慢的不是 API**。本轮从零搭 11 列报表，落库 API 段合计 **≈7.7s**，而用户体感 20 分钟里 ≥80% 是「读文档 + 多轮工具往返 + 推理」。改 API 只能省 5s，改流程能省 10 分钟。

### 1) 单次接口墙钟（Python `http.client`，每条新建连接）

| 步骤 | 实测 |
|------|------|
| `baseInfo` 建壳 | **1.5s（冷）／0.33s（热连接）** ← 首个请求含 TLS+DNS 预热，后续骤降 |
| `addDataset` | 0.5s |
| `dataset/list`（1 次命中） | 0.5～1.5s |
| `fieldsAndOriginFields` | 0.65～1.0s |
| `saveReportDevInfo` | 0.5s |
| `baseInfo` 改名 | 0.16～1.4s |
| `getReportDevInfo` 回读 | 0.17～1.0s |
| `fillDatasetConfig` | 0.43s |
| `deleteReport` | 0.34s |
| CLI：`e10-login status` | **0.9s** |
| CLI：`edc-report auth ready` | 1.8s |
| CLI：`edc-report app search --name` | **2.8s**（返回全量 998 条，未服务端过滤） |
| CLI：`edc-report find form` | 1.7s（含一次 `e10-login status`） |
| CLI：`edc-report verify bind` | 2.4s |

### 2) 三个确定有效的提速项（实测 7.9s → 3.2s）

| 项 | 做法 | 收益 |
|----|------|------|
| **复用 HTTPS 连接** | 全程一条 `HTTPSConnection`（或 `http.client` keep-alive），不要每请求 new | 5 次请求 1355ms → **573ms**（≈2.4x） |
| **凭证缓存** | `e10-login status` 结果写本地缓存（≤1h 复用）；**禁止**每个脚本/每次请求 subprocess 拉一次 | 每次 0.9s × N 次 → 0 |
| **少调可选接口** | 新空壳可省 `designKey` 预读、`fillDatasetConfig`；`dataset/list` 通常第 1 次即命中，不要预 sleep | 省 1～1.5s |

热连接下限：建壳后 addDataset→回读整段 **≈1.7s**，整表 **≈2s** 可完成落库。

### 3) 体感耗时的真正大头（必须这样改）

| 大头 | 优化 |
|------|------|
| 开场读 4～6 篇 guide | 冷启动 **只读** `cold-start-scan-guide.md` + 点名 **≤2** 篇；条件格式/单元格格式/布局三篇能合并成 **一次 `validate` 批量校验** |
| 多轮工具往返（本轮 30+ 次） | **一个脚本跑完** 登录→定源→落库→回读；禁止 stage1/stage2 分文件、禁止 debug 脚本 |
| `app search` 拉 998 条 | 已知 appId 就直接 `find form`；不要为了「确认应用存在」先 search |
| 找源后仍反复回读 | fieldsKey 拿一次即可，字段门禁走本地断言 |

---

## 七、Agent 开场检查清单（≤30s）

```
[ ] edc-report auth ready  → 已登录？是 → 0 文件扫描直接搭
[ ] 未为登录乱扫文件？未通读 SKILL/references 全文？（防 502）
[ ] 未查找 e10-cli*？只加载点名 guide？
[ ] 有 appId？ → edc-report find form（禁 ds/group）
[ ] 同款样式只验一次？
[ ] 临时壳 ≤1；失败/终止必 cleanup shells？
[ ] 落库成功 → 先交设计器 URL
[ ] 用户是「改已有」？ → policy scope + 定点 patch
```

---

## 耗时基线（2026-09-09 实测 · chl测试0909-005）

**平台 API 侧（全部实测）**

| 环节 | 耗时 |
|------|------|
| `find form` | 809ms |
| `build spec` 全链路 | **1029ms**（定源 157 → 建壳 402 → dataset 148 → fieldsKey 146 → 组 workbook 2 → save 127 → 改名 88 → 回读 114）|
| 复用 datasetId 原位重落 | 1729ms |

**Agent 侧（同一次需求）**：**48 次工具调用 / 10.8 分钟**，平均 **13.5s/轮**。
锚点：需求 17:32:43 → 落库 17:38:22（5m39s）→ 首次回复 ~17:43:30（收尾又花 5 分钟）。
→ **API 只占 0.3%，99.7% 是工具往返 + 生成开销。优化 = 减少轮次。**

### 最小调用路径（目标 6 次 ≈ 1.5 分钟）

1. `auth ready`（已登录可省） 2. `find form`（已知 appId+sourceId 可省）
3. Write `spec.json` 4. `build spec --spec` 5. 一次回读校验 6. 交设计器地址

### 砍掉这五类耗时

1. **开场通读文档**（6 轮）：SKILL.md 全文 + 冷启动页 + spec schema + CLI 源码。冷启动页已明令「禁通读 SKILL.md 全文」—— 只加载点名的 1 篇就动手
2. **搭表前先探字段**（建临时壳 → fieldsKey → 删壳，3~4 轮纯浪费）：字段由 spec `field` 匹配 + `matchField` 校验，错了退出码 2 并报 `bindErrors`，不必预读
3. **为平台不支持的样式改 CLI**（5 次 Edit + 1 次失败重跑 = 6 轮，最后还回滚白做）：目录外样式一律回退内置值 + 提示用户，不改脚本
4. **回读校验猜结构**（4 轮）：`getReportDevInfo` 的 **workbook 不在 `data.workbook`**（返回体顶层只有 `groupId / fields / sheetProps / workbookProps / designKey`）。校验只看 `data.fields[]` 一层：`style`(font/backColor/hAlign/formatter) + `conditionRule` + `fixed` —— 1 轮搞定
5. **多处小改动用 N 次 Edit**：技能文档 / CLI / 记忆的多处修改合并成单条 Bash 脚本一次写完
