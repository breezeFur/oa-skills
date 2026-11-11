---
name: weaver-e10-shared
display_name: 泛微CLI共享规则
display_name_en: Weaver CLI Shared Rules
description: weaver-work-cli 共享规则：安装检查、E10 认证、JSON 输出、高风险写入、安全边界和引用路由。
description_zh: weaver-work-cli 共享规则：安装检查、E10 认证、JSON 输出、高风险写入、安全边界和引用路由。
description_en: Shared rules for weaver-work-cli, including installation checks, E10 authentication, JSON output, high-risk writes, safety boundaries, and reference routing.
version: 1.2.5
author: 泛微网络科技股份有限公司
agent_created: true
requires:
  bins: ["weaver-work-cli"]
---

# weaver-work-cli 共享规则

本仓库中使用 `weaver-work-cli` 的业务 Skill 共享的底座；独立的 `e10-login` 和 Builder 技能仍按自身认证契约执行。共享内容包括：命令可用性、E10 认证、JSON 输出契约、大结果渲染与高风险操作。

## 连接器模式：--is-connector

同一条 `weaver-work-cli` 命令，认证来源由 `--is-connector true` 区分。**按下面的判据决定传不传，只判断一次，本任务内所有命令沿用同一写法：**

| 本次任务的情形 | 是否传 `--is-connector true` |
| --- | --- |
| 用户明确使用连接器，或上下文中要求使用连接器完成任务 | **传** |
| 本次任务或上下文中直接选择单独技能 | **不传** |
| 用户没有明确说明 | **按正在运行的这份 Skill 是哪一级定**：用户级 → **不传**；连接器级 → **传** |

- **怎么分辨级别**：技能条目标 `(user)`、从 `~/.workbuddy/skills/` 加载的就是**用户级**；标 `(connector)`、从连接器安装目录加载的就是**连接器级**。
- 同名 Skill 只会运行**用户级**那一份（WorkBuddy 按 Skill 名去重、用户级优先），所以这种情况一律按用户级处理。
- 用户级 → CLI 读取**本机活跃 profile**；连接器级 → CLI 读取**连接器托管的 eteams 认证与登录域名**。
- 连接器级**不要再写 `--profile` / `--base-url`**：认证与域名由连接器托管，手工指定会与它冲突。
- 漏传 `--is-connector` **不会报错**，但会退回本机活跃 profile，可能操作到与预期不同的租户。
- **本套 Skill 里的命令示例一律省略 `--is-connector`**（示例只示意参数形态，不代表最终命令）：执行前必须先按上表判定，命中「传」的要在 `weaver-work-cli` 之后补上 `--is-connector true`，且**本任务内每条命令都要带**——包括记忆读取、记忆保存这类无入参的命令。

## XiaoE 版本更新由客户端托管（全局覆盖）

本任务开始时一旦按下文规则判定当前智能体为 XiaoE，**不得执行 `weaver-work-cli --version` 或 `npm view weaver-work-cli version` 做可用性、版本或更新检查**。XiaoE 客户端已经负责检查并更新配套的 `weaver-work-cli`；Agent 直接进入登录态诊断或业务命令。本规则覆盖本 Skill、业务 Skill 及其 references 中所有通用的 `--version` 检查示例。

XiaoE 中如果后续命令直接返回 `command not found`、退出码 127 或明确的版本不兼容错误，停止并反馈 XiaoE 客户端运行时异常，不自行执行 npm 查询、安装或升级。仅非 XiaoE 环境继续使用下述版本检查与安装流程。

## 业务 Skill 安装前版本检查

非 XiaoE 环境按 [CLI 自动准备](../oa-skill/cli-setup.md) 由 Agent 直接准备 CLI。先确认真实命令路径与版本；缺少、版本低于已核对基线 0.1.49、明确不兼容或用户要求更新时，执行 `npm install -g weaver-work-cli@latest --registry=https://registry.npmjs.org`，随后验证 `--version` 和本轮业务命令 `--help`，再继续原任务。普通业务任务已有匹配版本时不重复联网查更新。无需让用户选择安装来源或再次确认更新；用户明确指定本地源码时才按其来源构建。XiaoE 客户端托管的工具由客户端自动准备，保留上节宿主边界。

## 最高优先级：XiaoE 统一登录

XiaoE 环境有两种识别入口：桌面客户端由 Agent 根据宿主或任务上下文明确识别，可接受标识包括“智能小 e 客户端”、“小 E”、`XiaoE` 或 `xiaoe-client`；传入 CLI 的环境中只要存在任意 `XIAOE_*` 变量，也直接识别为 XiaoE，包括 `XIAOE_DATA_ROOT` 等路径变量。本任务开始时只判断一次，后续命令沿用同一结论。没有 `XIAOE_*` 环境变量时，不得把以下任一情况单独当成 XiaoE 宿主证据：

- 本机存在 `xiaoeUserData/tokens.py` 或 XiaoE 客户端目录；
- 文件系统中存在客户端目录、配置文件或 Token 脚本，但这些路径没有通过 `XIAOE_*` 环境变量传入；
- 仅有 `WEAVER_XIAOE_*`、`WORKBUDDY_*`、`CODEX_*` 环境变量；
- 工作目录名含 `xiaoeUserData`、使用 XiaoE 内置 Node.js，或已安装相关 CLI；
- 过去在同一台机器上登录或安装过 XiaoE。

桌面客户端首次没有本地会话时，Agent 判定为 XiaoE 后可显式执行 `weaver-work-cli auth xiaoe`，或通过 `--runtime-agent xiaoe` 标识宿主，让业务命令在加载会话时自动获取登录信息，例如 `weaver-work-cli --runtime-agent xiaoe workflow ...`；网页端已有 `XIAOE_*` 标记时自动识别。已保存的 XiaoE 会话过期恢复不依赖这个参数，也不依赖 Skill 或 Agent：CLI 会根据会话内的 `agentType` / `loginSource` 在公共请求层自行处理。`--runtime-agent` 表示运行时身份，不携带凭据。

WorkBuddy、Codex 及其他智能体一律使用 `weaver-work-cli auth login --base-url "<用户确认的登录域名>" --agent_type "<当前智能体名称>"` 走浏览器 OAuth。`auth login` / `auth oidc` 不会读取或消费 XiaoE 凭据。

### XiaoE 凭据由 CLI 独占处理（顶层强规则）

Token、Cookie、ETEAMSID 和业务凭证**只能由 `weaver-work-cli` 内部读取和消费**。Agent 禁止：

- 自行执行宿主 `xiaoeUserData/tokens.py`（或任何取 Token 的脚本）并把 stdout 读进上下文——stdout 含 ETEAMSID/Cookie/Token，会进入对话、日志与缓存；
- 执行 `weaver-work-cli auth export-weaver-env` 并 `eval` / `Invoke-Expression` 到当前 shell，或把 `WEAVER_*` 值写进命令、日志、报告；
- 要求用户粘贴、或在回复中展示、转述任何凭证。

下述 `auth xiaoe` 流程仅适用于上述已确认的 XiaoE 智能体环境；其他智能体不执行宿主脚本检测，直接进入浏览器 OAuth 流程。`auth xiaoe` 命令本身就是认证方式的显式选择；`hasXiaoEEnv` 使用桌面的 `--runtime-agent xiaoe` 或任意 `XIAOE_*` 环境变量识别运行环境。

首次缺少本地会话时，已识别为 XiaoE 的业务命令会在 CLI 公共会话加载层自动获取登录信息；如需提前登录，只运行 `weaver-work-cli auth xiaoe`。CLI 内部按「平台凭证 Node 换票 → CLI 自带 `xiaoe_env.py` 兼容换票 → 宿主 `tokens.py` → 桌面 XiaoE 客户端会话 → `WEAVER_XIAOE_*` 环境映射」顺序取凭据；其中 `XIAOE_DOMAIN` 是 XiaoE/erpa 换票服务地址，不是 E10 地址。`xiaoe_env.py` 属于 CLI npm 包，不放入 shared Skill，且只能由 CLI 内部执行和解析。已有 XiaoE 会话达到换票结果的 `expiryTimes` 时，CLI 会在业务请求发出前静默换票；已有 XiaoE 会话被接口明确拒绝为失效时，CLI 根据会话元数据在公共请求层静默恢复并重放一次。这个流程绕开 shared Skill，Agent 不参与，也不得再补跑登录或原业务命令。失败时 CLI 返回最终结构化错误。

1. 首次无本地登录态、需要在业务命令之前显式建立 E10 会话时，可运行：
   ```text
   weaver-work-cli auth xiaoe
   ```
2. 不得因为本地存在旧 profile、`auth profile current` 指向旧环境，或 `auth profile list` 里只有旧环境，就跳过 XiaoE 统一登录；也不得先要求用户选择旧 profile 或输入域名。
3. XiaoE 统一登录由 CLI 按序取凭证：① 平台注入的 `XIAOE_USER_TOKEN` + `XIAOE_DOMAIN`，先走 Node 换票，再由 CLI npm 包自带的标准库 `xiaoe_env.py` 作兼容回退；② 宿主 `xiaoeUserData/tokens.py`（仅桌面宿主，CLI 在 macOS/Windows 都会先自动发现 XiaoE 客户端内置 Python，再回退到系统 Python）；③ 内置原生实现读取桌面 XiaoE 客户端会话换取 `eteamId`，依次查找 `XIAOE_USER_SETTINGS_PATH`、`XIAOE_ROBOT_DATA_ROOT` / `XIAOE_ROBOT_ROOT` 和默认 `XiaoE/Robots/<id>/user_settings.json`，因此会话有效时不要求存在 `tokens.py`；④ `WEAVER_XIAOE_*` 环境映射。宿主只注入 `XIAOE_DOMAIN`、`XIAOE_USER_TOKEN` 等平台变量，不会注入 ETEAMSID 环境变量，CLI 也不读取 `XIAOE_ETEAMSID`。Agent 不要打印、转述、索取或要求用户手动设置这些凭证，也不要直接执行任一脚本或因为脚本报缺依赖就让用户安装 Python 包——凭据链内部的兼容回退由 CLI 完成。
4. `auth xiaoe` 是 XiaoE 认证方式的显式入口：CLI 不再判断当前宿主，只检查并消费可用凭据源。E10 目标地址按「显式 `--base-url` → 专用 `WEAVER_XIAOE_*` E10 配置/映射 → 当前 profile → CLI 内置默认值」解析，绝不能把 `XIAOE_DOMAIN` 当作 E10 地址。Token、Cookie、ETEAMSID 仍属于凭证，禁止在回复中展示。
5. XiaoE 统一登录走不通时，无论 macOS、Windows、Linux 或 Web，CLI 都返回 `authentication/xiaoe_credential_unavailable`，绝不自动打开浏览器或降级到 `auth login`；本任务必须停止，不得另行调用其他登录 Skill 或登录命令。网页端若带 `details.reason=host_credential_not_injected`，只反馈「网页技能沙箱未获得宿主登录凭据」，该问题由宿主/沙箱启动层修复，不要让用户重新登录或手动提供凭据。若失败全程都是网络错误（连不上 E10，登录态根本没被验证过），子类型是 `authentication/xiaoe_network_unavailable`、`retryable: true`，文案为「暂时无法连接 E10，请稍后重试」——此时只反馈并建议稍后重试，不要引导用户重新登录。
6. `auth status --no-check` 不会触发 XiaoE 统一登录；业务命令加载到 `agentType=XiaoE` 或 `loginSource=xiaoe-unified` 的会话并被 E10 明确拒绝为失效时，即使没有 `XIAOE_*` 或 `--runtime-agent xiaoe`，也会静默触发一次统一登录并重放该请求一次。无可读取的本地会话时，则需要当前 `XIAOE_*` 或 `--runtime-agent xiaoe` 等宿主标记才能自动获取；显式 `--auth` 不触发自动替换。具体读取 [`e10-auth-and-session.md`](references/e10-auth-and-session.md)。

### 认证错误只报告状态，不指定登录命令

CLI 和业务 Skill 在返回 `authentication` / `session_expired` 时，只能说明未登录或会话已失效，不得在 `error.message` 或业务错误分支中写死 `auth login`、`auth xiaoe`、`--base-url`、`--agent_type` 等具体登录命令或参数。

业务 Skill 的提示词必须区分“CLI 已处理的过期恢复”和“首次认证缺失”，不能让 Agent 接管底层自动恢复：

1. 已有 XiaoE 会话出现 `session_expired` 时，CLI 已在公共请求层自动取凭据、校验同一环境/用户并重放一次；若该错误最终仍返回，Agent 只反馈错误并停止，不执行 `auth xiaoe`、其他登录 Skill 或原业务命令。
2. 仅首次无会话或明确的 `auth not found` 才由 Agent 重用任务开始时的宿主判定；明确为 XiaoE 时执行一次 `weaver-work-cli auth xiaoe`，不得改用 `auth login`。返回 `authentication/xiaoe_credential_unavailable` 时停止并反馈宿主凭据不可用。
3. 首次认证缺失且非 XiaoE 时，不得执行 `auth xiaoe`；取得用户确认的真实 E10 登录域名后，执行 `weaver-work-cli auth login --base-url "<用户确认的 E10 登录域名>" --agent_type "<当前智能体名称>"`。已有可用 profile 时也可按用户选择切换并验证。
4. 显式登录后读操作可以重新执行；写操作不得复用旧 continuation，必须重新 prepare 并重新确认。已返回 `partial` / `write_uncertain` 时先只读回查，禁止直接重放写入。

`auth xiaoe` 的 preflight 会输出不含凭证的 `authMode=xiaoe`、`credentialSourceDetected`、`attempted`、`platformCredentialDetected`、`tokenScriptDetected`、`clientSettingsDetected`、`environmentCredentialDetected` 和 `baseUrl`；命中脚本分支时会出现 `Trying XiaoE token script credential...`，命中内置 Node 会话分支时会出现 `Trying built-in XiaoE client session credential...`。成功后登录结果和 `auth status` 中的 `credentialSourceStep`、`credentialSourceType`、`credentialSourceLabel` 用于确认实际来源；`2 / token_script / xiaoeUserData/tokens.py` 表示宿主脚本换票成功，`3 / xiaoe_client / XiaoE client settings` 表示不依赖 `tokens.py`、由 Node 直接换票成功。

`auth login` / `auth oidc` 是严格的浏览器 OAuth 入口，即使同一台机器上存在 XiaoE 凭据或客户端文件，也不得先尝试 XiaoE 统一登录。

### 浏览器 OAuth 防挂起（顶层强规则）

`auth login` 会在本机 `127.0.0.1:19800` 监听浏览器回调，最长等待 5 分钟。在 Agent 沙箱/托管环境中，外部浏览器无法回调容器内 `127.0.0.1:19800`，因此：

1. 任意系统运行 `auth xiaoe` 时，收到 `xiaoe_credential_unavailable` 即反馈宿主登录态/凭据注入异常，不要自动切换 `auth login`，也不要要求用户去本地终端重复执行命令。
2. 仅非 XiaoE 环境在用户确认真实 E10 域名且确认 CLI 与浏览器同机后运行 `auth login`；仍须限时等待，超时未完成即终止并反馈。
3. 仅非 XiaoE 环境在用户无法完成浏览器登录、且明确要求并同意人工录入时，才可使用保底方式 `weaver-work-cli auth set --eteamsid "<ETEAMSID>" --base-url "<用户确认的登录域名>"`；它不是业务认证错误的默认恢复路径。ETEAMSID 由用户从已登录浏览器主动提供，Agent 不得索取、展示或转述该值。
4. 严禁不加限制地前台运行 `auth xiaoe` / `auth login` 并等待 OAuth 回调。

## 通用准则

1. 执行业务命令前先确认用法：优先读当前业务 Skill 和被路由到的 reference，必要时跑对应命令的 `--help` 或 `schema`，不要猜参数。

2. 首次使用先确认 CLI 可用。XiaoE 环境不检查版本，直接执行：

```text
weaver-work-cli doctor --e10
```

非 XiaoE 环境执行：

```text
weaver-work-cli --version
weaver-work-cli doctor --e10
```

如果命令不可用（尤其是 `command not found` 或退出码 127），XiaoE 环境按客户端托管规则处理；非 XiaoE 环境读取 [`weaver-e10-installation.md`](references/weaver-e10-installation.md)，先检查 PATH 和实际安装位置，再由 Agent 直接安装/更新官方 CLI，验证成功后继续原任务，不要求用户手动安装或重复确认安装。

3. 业务输入只描述业务对象和意图。认证、Cookie、ETEAMSID、业务 Token、接口地址和回查细节都由 CLI 托管。调用业务 operation 时，简单 JSON 优先使用 `--input-json '<json>'`；多步传递优先用 shell 变量，超大结果用 `--input-ref <refId>`，不要把上一步 stdout 写入临时文件再作为下一步输入。`--input <path>` 只用于用户提供的 JSON 文件或明确的文件业务输入；复杂 JSON 可在确有需要时使用，不能用它中转 CLI 上一步的输出。只有确认当前 shell 能稳定传管道时才使用 `--input -`。生成或改写 docs、reference、提示词和命令示例时，必须同时兼容 Windows 和 macOS/Linux；涉及 JSON 输入、用户目录、路径分隔符、Python 启动器、文件删除、目录查看或文件比对时，同时给 Windows PowerShell 与 macOS/Linux（bash/zsh）两套示例。Agent 先根据当前系统和 shell 选择对应示例，不确定时用 `node -p "process.platform"` 判断。Windows/PowerShell 下不要使用 `printf`、`$HOME/...`、`~/...`、bash 反斜杠续行、`rm/ls/diff/python3` 等 Unix-only 写法。

   CLI 对 `--input <path>` 默认只告警；需要拒绝文件 JSON 输入时使用 `--no-file-input`，或设置 `WEAVER_WORK_CLI_FILE_INPUT=deny` / config `io.fileInput=deny`。一次性允许时可用 `--allow-file-input`。`--input -` 和业务附件参数（如 `--file`）不受这条策略影响。

4. 认证诊断只能通过 `weaver-work-cli auth root/status/profile list/profile current`、`weaver-work-cli doctor --e10` 和业务命令 JSON 错误完成。禁止直接列目录、打印、复制或解析用户态认证目录和认证文件。

5. 涉及附件、图片、本地文件、远程 URL 文件或文件内容解析的操作，执行前必须先向用户说明：文件内容可能会被上传到业务系统、OCR/解析服务，并可能进入当前大模型上下文用于理解和处理。必须等待用户明确确认后，才继续上传、读取、解析、OCR、导入或复用已上传文件对象；用户未确认时只说明风险和所需确认，不执行相关命令。

6. **同名不同包不要混用**：环境中可能并存另一个独立的 E10 登录 CLI（例如 `e10-login`，版本号可能带 `xiaoe` 后缀），它提供登录与状态查询，但其登录态**不会**被 `weaver-work-cli` 复用。非 XiaoE 环境的 CLI 可用性以 `weaver-work-cli --version` 为凭；XiaoE 环境跳过版本检查，以 `doctor --e10` 或实际业务命令的结果为凭。登录态一律以 `weaver-work-cli auth status --no-check` / `doctor --e10` 为凭；不得因为另一个 CLI 显示已登录就判定本 CLI 可用，也不要用另一个 CLI 的输出替代本 CLI 的认证结论。

## 超时与重试预算

命令执行必须有界。默认按下表 timeout（超时）预算约束；超时即终止并反馈，不允许无界等待或无界重试。

| 命令类别 | 单次超时预算 | 重试策略 |
| --- | --- | --- |
| 登录类（`auth xiaoe` / `auth login` / `auth set`） | 300 秒（5 分钟，后台运行 + 限时观察） | Agent 不自动重跑登录命令；XiaoE 业务请求收到明确认证拒绝时，CLI 内部只静默恢复 1 次 |
| 只读业务查询（list / get / schema / preview） | 120 秒 | 最多 1 次；仅在网络类错误且未产生副作用时 |
| 写入类（prepare / apply / import / update / delete） | 600 秒（10 分钟） | **禁止自动重试**（存在重复入账/重复提交风险）；结果不确定时只补一次只读回查 |
| 安装与构建（`npm install` / `npm run build` / `npm link`） | 1800 秒（30 分钟） | 禁止自动重试；失败即停止并报告，不加 `sudo` |
| 诊断类（`--version` / `doctor` / `auth status --no-check` / `skills list`） | 60 秒 | 最多 1 次 |

预算是**上限**而不是必须等满：`auth login` 一旦出现浏览器 OAuth 等待信号（`Open browser login` / `Waiting for E10 authorization callback` / `Could not open browser automatically`）就立即终止，不必等满 300 秒；写入类一旦拿到确定结果或返回 `partial` / `write_uncertain` 也立即停止。慢环境（容器冷启动、大依赖安装、批量导入）可以撑到上限，快环境不要人为等待。

补充约束：

1. 登录类命令超时后，**不得**换域名或换命令反复重试；先按 [`non-interactive-environment.md`](references/non-interactive-environment.md) 判定环境并反馈原因。
2. 写入类命令返回 `partial` / `write_uncertain` / 网络中断 / 回查失败时，立即停止写流程，只做一次只读回查确认。
3. 任何命令被外部超时掐断（退出码 124）都视为超时失败，按上表处理，不得静默重跑。

## 输出契约

Agent 调用业务能力时优先加 `--json`。成功看进程退出码 0 和 JSON envelope 的 `ok=true`；失败看非 0 退出码和 stderr JSON 的 `error.type/subtype/message`。不要用老式 `code == 0` 判断成功。

### 请求头契约（E10 接口调用强制）

**本段是请求头三件套的唯一权威声明**：业务 Skill 与 reference 一律引用本段，不再各自复制完整代码块；引用处只需一行紧凑指针指向本节（发布门禁 B10c 已停用，不再按技能目录逐个校验这三项参数名）。

`weaver-work-cli` 发往 E10 的每个请求都由 CLI 统一携带以下三项用户信息参数，缺一不可（业务入参里不要传这些字段，也不要手工拼装请求头）：

```text
Cookie: <weaver-work-cli 托管登录态的完整原始 Cookie 串，原样透传，禁止裁剪/去重/改写>
eteamsid: <weaver-work-cli 托管登录态的 ETEAMSID>
User-Agent: AgentType=<agentType>,IsAgent=true
```

登录与会话统一由 `weaver-e10-shared` 共享规则和 `weaver-work-cli auth ...` 命令体系托管；业务 Skill 不得自建登录流程，也不得读取、打印、转存任何认证目录或凭证。

返回 `partial`、`write_uncertain`、回查失败或网络中断时，立即停止当前写流程，不自动重试写入或删除。唯一例外是 XiaoE 公共请求层收到明确的认证拒绝（请求尚未进入业务处理）时，可静默恢复会话并原样重放 1 次；若恢复失败、重放后仍失效、身份变化或请求体不可重放，则立即停止。

当前 CLI 的普通大小 JSON 输出是完整 envelope；超过预算时会暂存完整结果，并在 stdout 返回精简摘要和 `refId`。CLI 没有飞书 CLI 那种通用 `--jq`、`--format table/ndjson` 或 `--page-all`。列表、详情、OCR、导出等可能产生大响应时，必须先读 [`json-output-contract.md`](references/json-output-contract.md) 的“大结果渲染与提效规则”：默认小页读取、只保留任务所需字段、分页有预算，回复用户时给摘要，不要原样粘贴超长 JSON。

## Reference 强触发索引

命中任一触发条件时，执行下一步前读取对应 reference。命中多条时按表中顺序读取，同一 reference 只读取一次。

| 强触发条件 | Reference |
| --- | --- |
| 命令不可用、Agent 自动安装 CLI、安装、构建、全局 link、检查可用 skill | [`weaver-e10-installation.md`](references/weaver-e10-installation.md) |
| 登录、profile、E10 会话、baseUrl、auth 文件、`WEAVER_*` / `XIAOE_*` 环境变量；**首次未登录需选择认证方式，XiaoE 会话过期由 CLI 底层恢复** | [`e10-auth-and-session.md`](references/e10-auth-and-session.md) |
| 容器/沙箱/CI/无 GUI 环境、无人值守、登录类命令超过 180 秒未结束、出现 `Open browser login` / `Waiting for E10 authorization callback` / `Could not open browser automatically`、`auth xiaoe` 返回凭据不可用、认证目录 `EACCES` | [`non-interactive-environment.md`](references/non-interactive-environment.md) |
| 判断 stdout/stderr、JSON envelope、退出码、脚本封装、自动化调用、大结果渲染/分页控量 | [`json-output-contract.md`](references/json-output-contract.md) |
| 准备执行写入/删除/导入/更新、遇到 `confirmation.required`、`partial.write_uncertain`、网络中断或回查失败 | [`high-risk-write.md`](references/high-risk-write.md) |

## 安全规则

1. 禁止输出或索取 Cookie、ETEAMSID、业务 Token、access token、app key、app secret。

2. 禁止读取、列出、打印、复制或解析任何 `e10-login` / `e10-cli` 历史认证目录，例如用户主目录下的旧 `.e10-cli`；也禁止直接读取 `auth`、`config.json` 或 Keychain 项来推断登录态。

3. 禁止绕过 `weaver-work-cli` 直接 `curl`、`fetch`、浏览器自动化或访问 E10 业务接口。

4. 写入、删除、导入、更新等高风险操作必须使用 CLI 提供的确认流程；业务 Skill 要求 `prepare -> apply` 时，必须把 prepare 返回的 continuation 原样传给 apply，并在 apply 前取得用户明确确认。

5. 不能猜测 CLI 未暴露的内部字段、接口路径、ID 解析逻辑或回查语义。

6. 已有 XiaoE 会话的 `session_expired` 由 CLI 底层自动处理，Agent 不运行任何登录命令或重试业务命令；最终仍返回该错误时只反馈并停止。首次未登录或 `auth status` 未登录时，Agent 若已判定为 XiaoE，可运行一次 `weaver-work-cli auth xiaoe`；统一登录不可用时反馈 CLI 原因并停止。任意系统都不得把 `xiaoe_credential_unavailable` 改成浏览器 OAuth、本地终端操作或其他登录 Skill。仅首次认证缺失且非 XiaoE 环境在用户确认真实 E10 域名后运行 `auth login`，并传入 `--agent_type "<当前智能体名称>"`。具体流程读取 [`e10-auth-and-session.md`](references/e10-auth-and-session.md)。

7. 附件、图片上传或文件解析属于敏感数据处理。即便 operation 风险等级不是高风险写入，也必须先取得用户对“文件内容可能进入大模型/外部解析服务”的明确确认；不能把用户仅提供文件路径或文件名视为同意解析或上传。

8. Agent 明确选择 `auth xiaoe` 后，或业务命令在已识别的 XiaoE 运行时发现本地会话缺失时，CLI 按顺序从平台注入凭证（Node 换票后由 CLI npm 包自带 `xiaoe_env.py` 兼容回退）、宿主 `xiaoeUserData/tokens.py`、内置原生实现读取的桌面 XiaoE 客户端会话（宿主注入路径优先、默认 `XiaoE/Robots/<id>/user_settings.json` 回退）、`WEAVER_XIAOE_*` 环境映射读取支持统一登录的凭证。已有会话被接口明确拒绝时会根据持久化会话的 `agentType` / `loginSource` 静默恢复 1 次，不要求 Agent 添加 `--runtime-agent xiaoe`。不要要求用户提供、展示或手动设置这些凭证。任意系统失败时都反馈结构化错误，不自动降级浏览器。
