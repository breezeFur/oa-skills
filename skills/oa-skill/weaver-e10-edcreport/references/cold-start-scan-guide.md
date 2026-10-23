# 冷启动 / 最小扫描面（强制 · 一页）

> **目标**：防首包过大 → 网关 **502**/超时。  
> **CLI**：`edc-report policy build` · `edc-report auth ready` · `edc-report policy scope`  
> **本文件 = 冷启动唯一必读性能页**；细则仍在各专题 guide，**禁止**开场把它们全读完。

---

## 〇、开场只做这 3 步

1. `edc-report auth ready`（或 `e10-login status`）— **0 文件扫描**  
2. 判断意图：模式 A 搭表 / 定点改 / 仅分析  
3. **只**再加载本任务点名的 **1～2 篇** `references/*-guide.md`，然后执行 CLI

**禁止**开场：通读 `SKILL.md` 全文、Glob 全目录、扫 `.workbuddy/`、通读 `weaver-e10-login`、扫 `e10-cli*`、通读全部 `references/`。

---

## 一、模式 A（默认搭表）允许加载

| 顺序 | 加载 | 用途 |
|------|------|------|
| 0 | 本页 + `user-request-scope-only-guide.md`（改已有表时） | 扫描面 + 改动闸门 |
| 1 | **`spec-build-schema.md`（首选）** 或 `api-report-build-fast-path.md`（需手工分步时） | 从零建表 |
| 2 | `app-datasource-lookup-guide.md` | 已给 app 找表 |
| 3 | `report-delivery-contract.md` | 交链即停 |
| 4 | 用户点名专题（查询/事件/父格…） | 单篇 |

落库成功并输出设计器地址后 → **本轮结束**（见 delivery-contract）。

---

## 二、禁止冷启动加载（按需点名才读）

下列文件 **开场禁止 Read/通读**；仅当用户明确要该能力、或排错必须时再读对应篇：

| 文件 | 何时才读 |
|------|----------|
| `report-knowledge-base.md` | 文档与引擎冲突 / 用户要源码级对齐 |
| `report-building-guide.md` | 界面逐步操作指导 |
| `report-help-guide.md` | 帮助手册问答 |
| `report-requirement-analysis-template.md` | 用户要「需求分析/搭建指导」 |
| `report-data-model.md` / `report-config-schema.md` / `ai-report-workflow.md` | 生成整包 ReportProps / 深分析 |
| `datasource-metadata-guide.md` | 需要 DataSetAction 全接口手册 |
| `report-designer-feature-map.md` | Ribbon/全景对照（非搭表默认） |
| `build_guide_html.py` / HTML 手册 | 用户点名要 HTML |
| `assets/template-*.json` | 仅作布局脚手架时；≠ 平台模版创建 |
| `weaver-e10-login` | `auth ready` 失败且需登录说明时 |
| `.workbuddy/**` | **禁止**；会话垃圾，勿扫 |

---

## 三、硬禁令（扫描）

1. 本包 **无** `e10-cli/` / `e10-cli-bundle/` — 禁止查找  
2. 登录只走 CLI — 禁止为登录 Grep/Glob 仓库或 profile  
3. 已给 app — 找表只用 `edc-report find form` / `getList/{appId}`；禁首轮 `/ds/group`  
4. 禁每次下载 SpreadJS / 设计器 chunk 做黑盒  
5. 禁「先扫目录再干活」  
6. 禁 `__build_*` / `__probe_*` 探测壳；字段/表名未确认前**不建表**（`build spec` exit 3/4 即停）

---

## 四、与其它文档关系

| 文档 | 关系 |
|------|------|
| `session-build-performance-guide.md` | 登录/找表/SpreadJS/同款样式等**展开**；冷启动先读本页即可 |
| `report-delivery-contract.md` | 交链即停；本页 §一 引用 |
| `api-report-build-fast-path.md` | 建表步骤；轻量清单与本页 §一一致 |
| `build-resilience-guide.md` | 失败韧性；非开场必读 |
| `edc-report-cli.md` | 命令映射；执行时再读 §一表 |

---

## 五、Agent 自检（开场 5 秒）

- [ ] 是否只跑了 `auth ready`，未扫登录目录？  
- [ ] 是否未 Glob 整个 skill / `.workbuddy`？  
- [ ] 是否未打开 knowledge-base / help / 分析模板？  
- [ ] 本轮是否只准备加载 ≤2 篇点名 guide？  
- [ ] 模式 A 是否准备交链后立刻停？
