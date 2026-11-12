# 按任务自动准备 CLI

用户要求安装、更新这些技能，或执行需要 CLI 的 OA 任务时，Agent 直接代为安装缺少的工具、更新不匹配的版本并继续原任务。简短说明正在准备什么即可，不另外设置“是否安装 CLI”的确认步骤，也不把命令交给用户手动运行。用户已明确要求只检查、不安装时遵从。纯规范问答、文件比对和阅读文档只准备实际需要的本地工具。

## 先确定本轮依赖

| 任务 | 工具与来源 | 验证 |
| --- | --- | --- |
| 应用、表单、流程设计、动作流、自定义组件 | npm 包 `weaver-e10-builder@1.5.4`，命令 `e10-cli` | `e10-cli --version`、`e10-cli --help`；动作流另查 `e10-cli actionflow --help` |
| E10 登录、租户基础操作、eBuilder 数据/表单接口、报表鉴权 | npm 包 `e10-login@1.5.0` | `e10-login --version`、`e10-login --help` |
| 报表 | 当前完整技能中的 `weaver-e10-edcreport/edc-report` | `edc-report --version`、`edc-report --help`、`edc-report scripts-path` |
| 流程待办、发起、处理与查询 | npm 包 `weaver-work-cli`，已核对基线 `0.1.49`；配套 `weaver-e10-shared` | `weaver-work-cli --version`、`weaver-work-cli workflow --help`、读取共享技能 |
| 页面生成 | 页面技能自己的 `scripts/bootstrap.mjs`、`product.json` 和 `runtime-lock.json` | `status --json`，按需 `ensure --json`，成功后 `protocol --json` |
| 离线迁出包比对、MAX 本地资料查询 | Python 3.10+ 和技能自带标准库脚本 | Python 版本及对应脚本 `--help`；不安装在线 OA CLI |

## 运行时

优先使用宿主已提供的可用 Node.js/npm 或 Python，检查真实路径和版本；不要把 Windows Store 的 `python.exe` 启动别名当作已安装的解释器。Node.js 缺少或版本不足时，直接通过当前系统可用的官方安装方式准备受支持的 LTS，页面生成需要 Node.js >=22.5，其他 CLI 至少需要 Node.js 18。Python 脚本需要 Python 3.10+。

Windows 缺少满足本轮要求的 Node 时，优先使用同级 [node-write](../node-write/SKILL.md) 提供的 `scripts/ensure-node.ps1`。先读取该技能，再由 Agent 运行实际绝对路径：

```powershell
$oaNodeJson = & '<技能根目录>/node-write/scripts/ensure-node.ps1' -MinimumVersion 22.5.0
if ($LASTEXITCODE -ne 0) { throw $oaNodeJson }
$oaNodeSetup = $oaNodeJson | ConvertFrom-Json
$oaNodeExecutable = $oaNodeSetup.nodePath
$env:PATH = (Split-Path -Parent $oaNodeExecutable) + [IO.Path]::PathSeparator + $env:PATH
& $oaNodeExecutable --version
& (Join-Path (Split-Path -Parent $oaNodeExecutable) 'npm.cmd') --version
```

示例满足页面 Node >=22.5 要求；只需普通文本工具时可省略 MinimumVersion，默认 >=22。已有满足当前 CLI 契约的运行时直接复用，不因提供该脚本强制升级。脚本从 nodejs.org 下载最新适用 LTS ZIP，核对官方 SHA-256，安装在用户目录，返回绝对路径；不修改永久 PATH。以上 PATH 仅供本次进程及其子进程使用。新 Node 的 DGS 能力仍须按 node-write 单独验证；OA CLI 使用其他运行时不构成 DGS 验证。

其他平台或需要系统安装时，按实际操作系统选择已有包管理器，例如 Windows 的 `winget install --exact --id OpenJS.NodeJS.LTS` / `winget upgrade --exact --id OpenJS.NodeJS.LTS`、macOS 的 `brew install node` / `brew upgrade node`；Linux 先确认发行版和官方包源是否提供满足版本的包。不要把 Windows 命令用在其他系统，不执行来历不明的下载脚本。安装后刷新当前进程 PATH 或使用确认过的绝对路径，再核对 `node --version`、`npm --version`。Python 可使用 Windows 的 `winget install --exact --id Python.Python.3.13` / `winget upgrade --exact --id Python.Python.3.13` 或 macOS 的 `brew install python` / `brew upgrade python`；Linux 确认官方包源版本后安装 python3。已有满足要求的其他 Python 版本直接复用，安装后验证解释器能启动。

若宿主已有可用包管理器，Agent 自行执行所需安装与更新；真实的系统权限阻断或浏览器授权由宿主工具处理。没有可用安装来源时，说明具体缺项，继续独立工作；不能把失败状态称为安装完成。

## npm CLI

先查命令实际路径和版本。版本与当前技能契约匹配时直接复用；缺少、低于技能要求、启动失败或用户明确要求更新时，从官方 npm registry 安装已匹配的版本。包名与命令名不同：`e10-cli` 来自 `weaver-e10-builder`，不要安装猜测的同名 npm 包。

```text
npm install -g weaver-e10-builder@1.5.4 --registry=https://registry.npmjs.org
npm install -g e10-login@1.5.0 --registry=https://registry.npmjs.org
npm install -g weaver-work-cli@latest --registry=https://registry.npmjs.org
```

只执行本轮需要的行。Builder 和登录 CLI 按技能匹配版本安装；不要直接把它们升级到未经核对契约的 `latest`。流程 CLI 可按官方最新版本更新，并以 `workflow schema` / `workflow --help` 的实际契约为准。已安装版本仍匹配时，普通业务任务不重复联网查新版本。

安装/更新采用 npm 原位管理，不先递归删除旧包目录，不删认证配置，也不清空整个 npm 缓存。只有出现具体 bin 冲突时才检查冲突所属包，处理该包并重新安装。全局目录无权限时可改用用户可写的 npm prefix，并用绝对路径验证和调用；不要仅因权限问题把安装工作退回给用户。Windows 根据宿主执行方式选择 `npm.cmd` 或 Node 调用已确认的 npm CLI，避免 PowerShell shim 的执行策略问题。

安装命令成功后必须验证实际命令路径、版本和 `--help`；失败时只针对明确原因修复，不反复执行同一安装命令。依赖准备完成后继续原业务任务，保留已有业务写入的确认与失败重放边界。

## 报表 CLI 使用当前完整技能

`edc-report` 依赖相邻 `../scripts/`，使用当前已安装的完整报表技能注册命令，不能只把 CLI 子目录打包到别处。缺少命令、版本不符或 `scripts-path` 指向旧副本时，Agent 在当前技能的 `edc-report/` 目录直接执行：

```text
npm link
edc-report --version
edc-report --help
edc-report scripts-path
```

核对版本与该目录的 `package.json` 一致、脚本路径指向本技能的 `scripts/`。全局注册无权限时直接用 `node "<当前报表技能>/edc-report/edc-report.js" <参数>` 运行同一份完整 CLI；不要安装来源或版本不明的 npm `edc-report`。

## 流程共享依赖

XiaoE 客户端托管的流程 CLI 按共享技能由客户端自动准备；其他宿主使用上面的官方 npm 方式，不额外要求用户确认安装。先准备 `weaver-work-cli`，再检查与流程技能同级的 `weaver-e10-shared/SKILL.md`。缺少时直接执行：

```text
weaver-work-cli skills install shared --target-dir "<本流程技能的上一级绝对目录>"
```

共享技能已存在时先比较版本和用户改动。需要更新时先备份当前共享技能到技能目录之外，核对 `weaver-work-cli skills install --help` 后更新同一目标；保留用户自定义规则，不创建重复同名技能。随后回读共享规则再执行流程命令。

## 页面 runtime 和认证

页面环境只通过页面技能自己的 bootstrap 准备；其锁文件管理精确版本、更新、并发锁和原子就绪检查，不用全局 `npm install ui-code-agent` 替代。版本随页面技能的正式产品清单与锁文件一起更新；执行 `ensure` 自动准备相匹配的 runtime。

CLI 安装验证不调用平台业务接口、不切换租户，也不触发登录。实际在线任务前才按对应认证技能检查环境；有效登录态直接复用，需要 OAuth 时由 Agent 发起官方授权流程并让用户完成浏览器授权。密码、Cookie、Token、私钥和认证缓存留在本机，不能迁移到仓库或安装日志。
