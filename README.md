# OA Skills

泛微 E10 / E-Builder 的技能与配套资源。仓库按用户 2026-10-23 的明确要求公开，包含 MAX 公司规范原件及历史参考资料。

## 收录范围

| 技能 | 目录 | 用途 |
| --- | --- | --- |
| weaver-e10-builder | skills/oa-skill/weaver-e10-builder | E-Builder 应用、表单、流程、权限、编号等搭建 |
| generating-actionflows | skills/oa-skill/weaver-e10-builder/actionflows | ESB 动作流生成与保留原 ID 的修改 |
| weaver-e10-edcreport | skills/oa-skill/weaver-e10-edcreport | 报表数据源、布局、查询条件及点名修改 |
| max-workflow-standard | skills/max-workflow-standard | MAX 公司流程、表单、泳道及验收规范 |

初始版本从私有仓库 breezeFur/agent-skills 的提交 c7f156ce52ed313fe02c1e4408ec16ec87097e11 提取以上两个目录，共 441 个配套文件。原仓库继续保留这些内容；本仓库是独立的 OA 副本。

## 工具与认证依赖

- Builder 技能声明对应 e10-cli 1.5.4；动作流由该 CLI 的 actionflow 命令组执行。e10-cli 运行程序需按技能内安装说明单独获取，本仓库不提供其发行包。
- 报表 CLI 源码在 skills/oa-skill/weaver-e10-edcreport/edc-report，依赖相邻 scripts 目录。Node.js 要求 >=18；使用前按技能与 CLI 的说明准备外部依赖。
- weaver-e10-login 认证技能未包含在此次收录范围。e10-login 是外部认证 CLI，需要单独安装并在本机登录。克隆本仓库不会迁移登录态。
- Python 脚本按各技能的依赖说明使用；MAX 完整性校验只需 Python 标准库。
- 账号、密码、Token、Cookie、私钥及服务配置保留在本机。当前收录的公司原件与历史附件随本仓库公开；后续新增资料须确认其公开范围。

## 克隆与安装

### Windows / PowerShell

公开仓库可直接克隆：

```powershell
git clone https://github.com/breezeFur/oa-skills.git D:\develop\oa-skills
```

以下示例在默认 Codex 技能目录中创建目录联接。若设置了 CODEX_HOME，使用该目录。已有安装会被跳过；需要改用此副本时，先自行备份原目录并确认原链接目标。

```powershell
$oaRepoPath = 'D:\develop\oa-skills'
$oaCodexPath = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$oaSkillsPath = Join-Path $oaCodexPath 'skills'
New-Item -ItemType Directory -Force -Path $oaSkillsPath | Out-Null
foreach ($oaSkillName in @('oa-skill', 'max-workflow-standard')) {
    $oaLinkPath = Join-Path $oaSkillsPath $oaSkillName
    $oaTargetPath = Join-Path (Join-Path $oaRepoPath 'skills') $oaSkillName
    if (Test-Path -LiteralPath $oaLinkPath) {
        Write-Host "跳过已有目录：$oaLinkPath"
        continue
    }
    New-Item -ItemType Junction -Path $oaLinkPath -Target $oaTargetPath
}
```

保留 oa-skill 内嵌套技能的目录结构，避免丢失相对引用。目录符号链接也可使用；其权限要求取决于 Windows 配置。仓库根 AGENTS.md 约束本项目维护，无需覆盖个人全局 AGENTS.md。

### Linux / macOS

```bash
git clone https://github.com/breezeFur/oa-skills.git "$HOME/oa-skills"
oa_repo_path="$HOME/oa-skills"
oa_codex_path="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$oa_codex_path/skills"
for oa_skill_name in oa-skill max-workflow-standard; do
  oa_link_path="$oa_codex_path/skills/$oa_skill_name"
  if [ -e "$oa_link_path" ] || [ -L "$oa_link_path" ]; then
    printf '跳过已有目录：%s\n' "$oa_link_path"
    continue
  fi
  ln -s "$oa_repo_path/skills/$oa_skill_name" "$oa_link_path"
done
```

按需注册报表 CLI 时，在完整仓库内执行 npm link；CLI 会引用相邻 scripts，因此不要只复制 edc-report 子目录。此操作改变本机 npm 命令安装，不属于克隆步骤。

```text
cd skills/oa-skill/weaver-e10-edcreport/edc-report
npm link
edc-report --help
```

## 更新与推送

先查看工作区和远端；有本地修改时先妥善保存，再拉取：

```text
git status --short --branch
git fetch origin
git rev-list --left-right --count origin/main...main
git pull --rebase
```

提交时仅暂存本次已授权修改的文件。例如只修改 Builder 技能定义：

```text
git add -- skills/oa-skill/weaver-e10-builder/SKILL.md
git diff --cached --stat
git diff --cached
git commit -m "Update OA builder skill"
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

README、AGENTS.md 和配套资源有相关变化时，明确列出对应路径再暂存。只维护拉取后远端已有的 4 个技能；新建或新安装技能默认留在本机。新增顶层或嵌套 SKILL.md，均须用户直接调用 skill-manage-github 并明确要求上传后才能收录。

原 agent-skills 和本仓库是独立 Git 历史，不会自动互相同步。同一技能存在两份时，先比较内容与来源，再按明确的维护范围同步，避免用旧副本覆盖新改动。

## 本地校验

```text
python -X utf8 skills/max-workflow-standard/scripts/verify_bundle.py
node --check skills/oa-skill/weaver-e10-edcreport/edc-report/edc-report.js
node skills/oa-skill/weaver-e10-edcreport/edc-report/edc-report.js --help
rg -n -i "password|token|secret|api[_-]?key|apikey|密钥|密码|令牌" skills AGENTS.md README.md
```

逐条判断凭证关键词命中：安全说明、占位符、业务字段与实际凭证分别处理。MAX 校验涵盖原件、媒体、OLE 附件、历史数据行、资料链接和文件清单，属于离线资料校验，不能证明线上 OA 流程通过验收。

.gitignore 排除本机配置、数据库、运行缓存、临时生成数据及 vibecodingdoc。原始资料保留其来源及适用范围；未赋予额外的开源许可。
