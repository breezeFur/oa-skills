# 本包不含 e10-cli（强制说明）

> **事实**：`weaver-e10-edcreport` 包内 **只有** `edc-report/` + `references/` + `scripts/`，**没有** `e10-cli/`、`e10-cli-bundle/`。登录由外部依赖 `weaver-e10-login` 提供。  
> **强制**：搭建/改报表时 **禁止** `Glob` / `Grep` / `Read` / 通读任何名为 `e10-cli*` 的路径——目录不存在，只会浪费首轮时间。

---

## 用什么代替

| 需求 | 本包入口 |
|------|----------|
| 登录 | `edc-report auth ready` → 未登录再 `e10-login` |
| 应用内找表 | `edc-report find form <appId> <表单名>` |
| 字段结构 | DataSetAction / `fieldsAndOriginFields` / `edc-report verify bind` |
| Word/需求文件 | 直接读文件提取需求（勿找 e10-cli docx） |
| 报表 API | `edc-report …` + 本 Skill `references/*` |

凭证目录仍为 `~/.e10-cli/profiles/`（e10-login 存储路径名，**不是**要去扫 e10-cli 源码包）。

---

## 若本机全局已装 e10-cli

那是 **外部环境**，与本 Skill 包无关。报表任务默认 **仍不加载、不扫描**；仅当用户在对话里明确点名「用 e10-cli 建表单/动作流」且与报表无关时，再按用户本机 skill 处理。
