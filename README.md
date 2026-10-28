# OA Skills

泛微 E10 / E-Builder 的技能与配套资源，包含 MAX 公司流程规范。仓库按用户要求公开。

## 直接交给你的 AI 安装

将下面这段话发给接收者的 AI。也可以转发本仓库的 [AGENTS.md](AGENTS.md) 链接，并明确要求“按 README 安装”：

```text
请安装 https://github.com/breezeFur/oa-skills 中已发布的 OA 技能。
先读取仓库 README.md 和 AGENTS.md，确认你所用 AI 的真实技能目录和规则文件，保留完整技能及配套资源。
安装完成后，把 docs/oa-agents.md 中的 OA 规则片段合并到我实际生效的 AGENTS.md；将 __OA_SKILLS_DIR__ 换成本机技能目录的绝对路径。
保留我已有的规则，先备份；已有 OA 标记块就更新同一块，不要重复追加，也不要用仓库 AGENTS.md 覆盖整个文件。
之后处理 OA 相关任务时，先检查并读取已安装的对应 OA 技能，再按技能要求检查工具、版本和认证环境。
验证 5 个技能定义、规则中的真实路径及新会话加载情况，最后报告安装路径、规则文件路径和仍需准备的外部依赖。
```

安装包含三个步骤：**安装技能目录 → 合并 OA 规则到接收者的规则文件 → 验证新会话识别**。只克隆仓库或只阅读本仓库的 AGENTS.md 不会替接收者的其他项目配置规则。

## 当前收录的技能

| 技能 | 仓库中的 SKILL.md | 用途 |
| --- | --- | --- |
| weaver-e10-builder | [应用搭建](skills/oa-skill/weaver-e10-builder/SKILL.md) | 应用、表单、原生流程、权限、编号等 |
| generating-actionflows | [动作流](skills/oa-skill/weaver-e10-builder/actionflows/SKILL.md) | ESB 动作流生成与保留原 ID 的修改 |
| weaver-e10-edcreport | [报表搭建](skills/oa-skill/weaver-e10-edcreport/SKILL.md) | 数据源、布局、查询条件及点名修改 |
| weaver-e10-components | [组件搭建](skills/oa-skill/weaver-e10-components/SKILL.md) | 可复用指标卡、图表、表格、筛选器及设计器配置 |
| max-workflow-standard | [MAX 规范](skills/max-workflow-standard/SKILL.md) | MAX 公司流程、泳道、表单及验收规范 |

`oa-skill` 是前三个技能所在的集合目录。保留它的原有嵌套结构与全部 references、assets、scripts；报表 CLI 会引用同一技能内的相邻 scripts，不能只复制 CLI 子目录。

## 安装前确认位置

- 先确认目标 AI 和版本实际读取哪个技能目录。当前 Codex 官方文档的用户技能目录为 `~/.agents/skills`；项目技能目录为 `.agents/skills`。旧环境可能使用 `~/.codex/skills`，已有安装应按实际配置确认，不在多个目录重复安装同名技能。
- Codex 全局规则文件位于 `CODEX_HOME` 指定的目录，未设置时为 `~/.codex/AGENTS.md`。同级存在非空 `AGENTS.override.md` 时它优先生效，应合并到实际生效的文件。项目范围还需检查项目的 AGENTS.md / AGENTS.override.md 是否影响 OA 规则。
- 其他 AI 使用其真实支持的技能目录及规则文件。若工具不自动读取 AGENTS.md，安装 AI 应将同一 OA 规则合并到该工具实际使用的规则文件，并报告位置。
- 已有仓库先检查 remote、工作区和分支，确认来源一致后复用；已有技能目录先核对内容及链接目标，保留用户修改。缺少写入权限时报告受影响步骤。

### Windows / PowerShell

下面示例使用当前 Codex 默认技能目录。安装 AI 应按实际配置调整 `$oaRepoPath` 和 `$oaSkillsPath`；先确认 Git 已安装。

```powershell
$oaRepoPath = Join-Path $env:USERPROFILE 'oa-skills'
git clone https://github.com/breezeFur/oa-skills.git $oaRepoPath
$oaSkillsPath = Join-Path $env:USERPROFILE '.agents\skills'
New-Item -ItemType Directory -Force -Path $oaSkillsPath | Out-Null
foreach ($oaSkillName in @('oa-skill', 'max-workflow-standard')) {
    $oaLinkPath = Join-Path $oaSkillsPath $oaSkillName
    $oaTargetPath = Join-Path (Join-Path $oaRepoPath 'skills') $oaSkillName
    $oaExisting = Get-Item -LiteralPath $oaLinkPath -Force -ErrorAction SilentlyContinue
    if ($null -ne $oaExisting) {
        Write-Host "已有安装，先核对再处理：$oaLinkPath"
        continue
    }
    New-Item -ItemType Junction -Path $oaLinkPath -Target $oaTargetPath
}
```

目录符号链接也可使用。环境不支持链接时，可把上述两个目录完整复制到实际技能目录，并在以后更新时比较副本。示例中的“已有安装”跳过提示不代表已验证该副本可用。

### Linux / macOS

```bash
git clone https://github.com/breezeFur/oa-skills.git "$HOME/oa-skills"
oa_repo_path="$HOME/oa-skills"
oa_skills_path="$HOME/.agents/skills"
mkdir -p "$oa_skills_path"
for oa_skill_name in oa-skill max-workflow-standard; do
  oa_link_path="$oa_skills_path/$oa_skill_name"
  if [ -e "$oa_link_path" ] || [ -L "$oa_link_path" ]; then
    printf '已有安装，先核对再处理：%s\n' "$oa_link_path"
    continue
  fi
  ln -s "$oa_repo_path/skills/$oa_skill_name" "$oa_link_path"
done
```

## 安装后合并 AGENTS.md（必做）

可复制的规则见 **[docs/oa-agents.md](docs/oa-agents.md)**。安装 AI 按以下顺序处理：

1. 找到接收者实际生效的全局规则文件；用户要求仅作用于某项目时使用该项目规则文件。Codex 优先检查 CODEX_HOME 下的非空 AGENTS.override.md，否则使用 AGENTS.md。文件不存在时创建；先读取已有文件及项目覆盖规则。
2. 对已有文件保存带时间戳的备份，保留原有 UTF-8、BOM 和换行格式。不要用仓库根 AGENTS.md 替换接收者整个文件，也不要把仓库维护约定整段导入个人规则。
3. 读取 docs/oa-agents.md，将 `__OA_SKILLS_DIR__` 的所有出现替换为实际技能根目录的绝对路径。Windows 可用正斜杠，例如 `C:/Users/用户名/.agents/skills`；Linux/macOS 例如 `/home/用户名/.agents/skills`。
4. 将 `<!-- OA_SKILLS_START -->` 至 `<!-- OA_SKILLS_END -->` 的整块规则合并进去。没有该块时追加一次；已有完整块时只更新该块。标记不成对或已有多块时先读清内容并合并，保留用户自定义要求，避免重复和误覆盖。
5. 回读核对原规则被保留、OA 标记块仅一份、真实路径可读，并确认没有遗留 `__OA_SKILLS_DIR__`。Codex 规则有加载长度限制，若规则被截断或被项目覆盖，应报告并在用户指定范围内调整位置；不能只凭写盘成功宣称规则生效。

该规则让 AI 在 OA 任务前先检查、读取对应技能，然后按任务检查 CLI、版本和认证。规范问答只读相关资料；不会因为问一个流程规范问题就登录 OA 或扫描整个技能库。

## 外部工具与认证

- Builder 声明对应 e10-cli 1.5.4；动作流使用该 CLI 的 actionflow 命令组。e10-cli 发行包需按技能安装说明单独准备，本仓库没有提供它。
- 报表 CLI 源码位于 `skills/oa-skill/weaver-e10-edcreport/edc-report`，Node.js 要求 >=18。按需在完整仓库的该目录执行 `npm link` 注册 `edc-report`，再以 `edc-report --help` 检查启动；这会改变本机 npm 命令安装。
- `weaver-e10-components` 已收录，依赖同集合中相邻的 Builder 指令。`weaver-e10-login` 认证技能未收录；若本机已有可按认证任务读取，缺失时明确说明，不把它算作本次已安装。
- e10-login 是外部认证 CLI，需要单独准备并在本机登录。克隆技能不会迁移登录态。安装时检查命令可用性即可；实际平台操作前才检查相应目标环境的认证状态。
- 密码、Token、Cookie、私钥及认证缓存留在本机，输出和提交物中不得包含实际凭证。公司资料保留来源和适用范围；后续新增公司资料须确认公开范围。

## 安装完成如何验证

安装 AI 必须分别报告：

| 检查项 | 完成依据 |
| --- | --- |
| 技能文件 | 实际技能目录中的 5 个 SKILL.md 都可读取，链接目标正确，配套文件完整 |
| OA 规则合并 | 接收者实际规则文件已回读；OA 标记块唯一、路径真实、原规则保留 |
| AI 已识别 | 新会话或重新加载后，AI 能列出 5 个技能并说明 OA 操作前读取对应技能；尚未执行新会话验证时标为待验证 |
| 工具依赖 | 报告 e10-cli、edc-report、e10-login 的可用性及匹配情况，缺少什么就列出什么 |
| 平台认证 | 作为独立准备项报告，缺少登录态不伪装成工具或技能安装失败 |

可在接收者 AI 的新会话发送：

```text
请先不要操作 OA 平台。列出你读取到的 OA 操作前检查规则、规则文件路径和已安装的 5 个 OA 技能路径，并说明创建表单、修改动作流、搭建报表、创建自定义组件、审阅 MAX 流程分别应先读哪个技能。
```

若新会话不能识别，检查真实技能目录、嵌套技能发现、规则覆盖及加载长度。目标工具若只识别直接子目录，按其支持方式登记这些已有 SKILL.md 路径，或为尚未发现的技能创建目录链接；保留源目录结构和相对引用，并确认没有重复同名技能。按目标 AI 的方式重新加载，Codex 未检测到更新时可重启；不要把未验证状态报告为完成。

## 更新技能与规则

使用链接安装时，更新仓库后技能文件随链接更新；复制安装则需比较并更新实际副本。**接收者 AGENTS.md 中的规则片段是合并的副本**，仓库更新后还应按同一标记块更新规则，并复查实际路径与新会话识别。

先检查工作区和远端，有本地修改时妥善保存后再拉取：

```text
git status --short --branch
git fetch origin
git rev-list --left-right --count origin/main...main
git pull --rebase
```

向本仓库推送时，明确列出本次相关路径，例如：

```text
git add -- README.md AGENTS.md docs/oa-agents.md
git diff --cached --stat
git diff --cached
git commit -m "Update OA installation guidance"
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

只维护拉取后远端已有的技能。新增顶层或嵌套 SKILL.md 默认留在本机，只有用户直接调用 skill-manage-github 并明确要求上传后才收录。原 agent-skills 与本仓库是独立 Git 历史，不会自动互相同步。

## 离线资料校验

```text
python -X utf8 skills/max-workflow-standard/scripts/verify_bundle.py
node --check skills/oa-skill/weaver-e10-edcreport/edc-report/edc-report.js
node skills/oa-skill/weaver-e10-edcreport/edc-report/edc-report.js --help
```

MAX 校验涵盖原件、媒体、OLE 附件、历史数据行、资料链接和清单，是离线完整性校验；平台配置回读、界面效果、实例流转按实际 OA 任务分别验证。

.gitignore 排除本机配置、数据库、运行缓存及 vibecodingdoc。初始内容来自 breezeFur/agent-skills 的 c7f156ce52ed313fe02c1e4408ec16ec87097e11 提交；资料原件保留来源，仓库未赋予额外开源许可。

## 官方配置参考

安装位置和规则发现方式于 2026-10-28 核对：

- [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI 官方 AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
