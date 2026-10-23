# edc-report CLI

独立 Node CLI，与 **weaver-e10-edcreport** Skill 同仓。鉴权复用 **e10-login**（`~/.e10-cli/profiles/`）。

## 和 Skill 的关系（重要）

| | Skill（Agent） | edc-report（CLI） |
|--|----------------|-------------------|
| 职责 | 读规则、需求分析、布局判断、少挂源、关联确认话术、**改动范围闸门** | 执行确定性 API（找表、关联推断、校验、版本、权限、生命周期…） |
| 规则文档 | `SKILL.md` + `references/`（含 **user-request-scope-only-guide.md**） | 不替代；`edc-report policy scope` 打印最高优先级政策 |
| 脚本源 | `../scripts/` | 唯一来源：CLI 直接解析同仓 Skill 的 `scripts/` |
| **执行优先级** | 判断走 Skill | **有 CLI 时优先 `edc-report`**，见 `references/edc-report-cli.md` |
| **改删约束** | 仅用户点名项 | 破坏性命令须用户明确要求才可跑 |

**不会影响 Skill 使用**：Agent 仍加载本目录上级的 `SKILL.md`；不装 CLI 也能按原方式跑 `node scripts/...`。

**脚本来源**：

- **CLI 解析到的是同仓 Skill 的 `../scripts/`**：你改 Skill 脚本后**立刻生效**（无需重装、无需同步）。
- **若把 `edc-report/` 单独拷走安装**：必须保持它与 `scripts/` 同级，否则用 `EDC_REPORT_SCRIPTS` 显式指定脚本目录。
- **只改 `references/*.md` 规则**：CLI 不会“自动学会”；若规则要落到可执行默认值，需改 `scripts/` 并在同一轮更新里同步（Skill 整合时请一并改脚本 + 必要时 bump CLI 版本）。

## 安装

```bash
# 依赖
npm i -g e10-login          # 若尚未安装
e10-login status

# 从 Skill 目录安装（推荐）
cd weaver-e10-edcreport/edc-report
npm i -g .

# 或开发态 link（始终跟 Skill scripts）
npm link
```

```bash
edc-report --help
edc-report --version
edc-report policy scope     # 最高优先级：仅改用户点名项
edc-report scripts-path     # 确认解析到的脚本目录（应为 Skill 的 scripts/）
```

## 命令速查

```bash
edc-report auth status
edc-report policy scope
edc-report policy build
edc-report policy login     # 低版本：建议升级或索要 ETEAMSID
edc-report auth ready
# 环境体检 / 踩坑知识库（动手前先跑）
edc-report doctor                     # 全量体检（env/scripts/install/trees/perf），FAIL → exit 1
edc-report doctor --fix               # 自动修：入口 CRLF→LF、shim 路径改指
edc-report doctor --json
edc-report pitfalls                   # 历史踩坑知识库（41 条）
edc-report pitfalls --area field
# 渲染守卫 / 规模预检（搭表不需要渲染）
edc-report render <reportId> [appId] [pageRowCount]        # 默认被守卫拦截
edc-report verify limit <reportId> [appId] [--date-values N]
# tableName 回显：体检 → 修复（默认 dry-run，--apply 落库）
edc-report verify contract <reportId> [appId]
edc-report fix table-name --report-id <id> --app-id <aid> --apply
edc-report fix echo --report-id <id> --app-id <appId>
edc-report create models
edc-report create blank --app-id <appId> --name "报表名"
edc-report create template --app-id <appId> --name "报表名" --model-id <模板ID>
edc-report create quick --app-id <appId> --name "报表名" --quickly-file quickly.json
edc-report policy list-page
edc-report group list --app-id <appId>
edc-report group add --app-id <appId> --name "分组名"
edc-report lifecycle move --app-id <appId> --report-id <id> --group-id <gid>
edc-report app search --name "应用名"
edc-report lifecycle transfer --report-id <id> --app-name "应用名"
edc-report scope matrix list --app-id <appId> --report-id <id>
edc-report dataset rename --dataset-id <id> --name "显示名"
edc-report dataset agg get --dataset-id <id>
edc-report dataset sort save --dataset-id <id> --file sort.json
edc-report dataset replace --file replace.json
edc-report dataset delete --report-id <rid> --dataset-id <did>
edc-report find form <appId> <表单名>
edc-report join suggest --app-id <appId> --parent-form "主表" --child-form "子表"
edc-report query list --report-id <id> --app-id <appId>
edc-report query save --report-id <id> --app-id <appId> --item queryItem.json
edc-report verify all <reportId> [appId]
edc-report verify meta <reportId> [appId]
edc-report verify condition <reportId> [appId]
edc-report validate base --name "报表名" --name-label-id -1 --group-id 0
edc-report validate condition --file rule.json
edc-report validate condition --map "介于 1 5"
edc-report validate condition --map "数据条"
edc-report validate format --map "货币"
edc-report verify format <reportId> [appId]
edc-report verify blank <reportId> [appId]
edc-report cleanup shells --app-id <appId> --report-id <id>
edc-report version save --report-id <id>
edc-report snapshot set --report-id <id>
edc-report lifecycle delete --host ... --app-id ... --report-id ...
edc-report scope set --report-id <id> --app-id <appId> --scope all
```

历史沉淀 → CLI 映射：`../references/edc-report-cli.md` §一（含 **§A0** / **§A0.1 性能** / **§L 空白防护**）。

## Skill 整合时怎么更新 CLI

1. 改 Skill 规则文档（必做）。
2. 若影响可执行行为 → 改 `scripts/`（必做）。
3. bump `edc-report/package.json` version（建议）。
4. `npm i -g .`（或 `npm link`；给本机全局 CLI）。
5. 同步 extract / 分发包时把整个 `edc-report/` 目录一并带上。
