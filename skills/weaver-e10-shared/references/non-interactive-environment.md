# 非交互环境处置（容器 / 沙箱 / CI / 无 GUI）

## 什么时候读取

满足以下任一条件时，在执行登录或认证相关命令**之前**读取本文件：

- 运行在容器、沙箱、CI、远程执行器或任何无 GUI / 无本地浏览器的环境
- 无法向用户弹出输入框、选择框或确认框（无人值守）
- `auth login` 输出中出现浏览器 OAuth 相关字样（见下方「浏览器 OAuth 信号」）
- 登录类命令执行时间超过 180 秒仍未结束（300 秒为硬上限，见 SKILL.md「超时与重试预算」）

## 环境判定：可交互 vs 非交互

| 判定项 | 可交互环境 | 非交互环境（按非交互处理） |
| --- | --- | --- |
| 浏览器 | CLI 与浏览器在同一台机器，可自动或手动打开授权页 | 无浏览器，或浏览器在宿主机而 CLI 在容器/沙箱内 |
| OAuth 回调 | 外部浏览器可访问 `127.0.0.1:19800` | 外部浏览器无法回调容器内 `127.0.0.1:19800`（结构性不可达） |
| 用户输入 | 可向用户提问并等待回答 | 无人值守，提问不会有人回答 |
| 安装/写入权限 | 可写、可提权 | 只读 HOME、只读配置目录、无 sudo |

判定不了时一律按**非交互**处理：非交互流程在可交互环境下同样安全，反之则会挂起或卡死。

## 登录失败信号判读

任意系统中 `auth xiaoe` 统一登录失败时都会直接返回结构化错误：

```text
error.type = authentication
error.subtype = xiaoe_credential_unavailable
error.stage = xiaoe_unified_login
```

收到该错误后，反馈宿主登录态或凭据注入不可用并停止。不要自动执行 `auth login`，也不要要求用户在本地终端重复执行登录。

`auth xiaoe` 不会自动降级到浏览器；当前任务已判定为 XiaoE 时不得另行执行 `auth login` 或调用其他登录 Skill。只有非 XiaoE 环境进入 `auth login` 流程时，才可能出现下列浏览器 OAuth 信号：

| 浏览器 OAuth 信号 | 含义 |
| --- | --- |
| `Open browser login: <url>` | 已生成浏览器授权 URL，准备跳转 OAuth |
| `Waiting for E10 authorization callback...` | 已在本地 `127.0.0.1:<port>` 监听回调并等待 |
| `Local callback server: http://127.0.0.1:19800/callback` | 回调监听地址；非交互环境下不可达 |
| `Could not open browser automatically. Copy the login URL manually.` | 无法自动打开浏览器，且无人可复制 URL 完成授权 |

在非交互环境中出现任一信号时的处置顺序：

1. **立即终止**该命令，不要等待本地回调。
2. 向用户反馈浏览器 OAuth 在当前环境无法完成本地回调的实际原因。
3. 不自动给出“去本地终端执行”的操作；仅非 XiaoE 环境可说明浏览器授权必须在 CLI 与浏览器同机的环境执行。
4. 仅非 XiaoE 环境且用户明确要求保底方式时，可说明 `auth set`，但 Agent 不得索取、展示、转述或记录 ETEAMSID：
   ```text
   weaver-work-cli auth set --eteamsid "<ETEAMSID>" --base-url "<用户确认的登录域名>" --agent_type "<当前智能体名称>"
   ```
   Agent 不得索取、展示、转述或记录该值。

## 显式传域名后仍失败

显式传入 E10 域名后仍返回统一登录错误：

```text
weaver-work-cli auth xiaoe --base-url "<用户确认的 E10 域名>"
# authentication/xiaoe_credential_unavailable
```

判定结论与处置：

- 域名与网络**不是**失败原因，不要再反复更换域名重试。
- 这属于宿主登录态、凭据注入或当前 CLI 消费凭证的异常；停止并反馈。XiaoE 环境不执行 `weaver-work-cli --version`，版本检查更新由客户端负责。
- 不要因为一次认证失败就断言 CLI 不可用；只读诊断命令（`auth status --no-check`、`doctor --e10`）仍可作为环境检查手段。

## 可写性相关说明

认证目录不可写（写入认证 profile 报 `EACCES: permission denied`）属于**环境侧**问题：凭证通常已在 1～2 秒内取到，失败发生在随后的落盘动作。技能侧只能识别与上报，无法在只读 HOME 中自行修复（禁止为绕过权限而改写其他目录或使用 sudo）。

出现该错误时：立即停止登录流程，原样反馈 `EACCES: permission denied` 与失败文件路径所在动作（不打印路径细节与凭证），并说明需由环境侧将认证目录改为可写或支持用环境变量指定配置目录。不建议反复重试登录命令。

## 收尾流程（每次登录尝试后必做）

1. 记录本次结果：成功 / 凭据不可用 / 权限失败 / 超时，以及耗时与退出码。
2. 非成功结果一律**不自动重试**登录类命令（见 SKILL.md「超时与重试预算」）。
3. 用只读命令确认真实登录态，再决定是否继续业务操作：
   ```text
   weaver-work-cli auth status --no-check
   weaver-work-cli doctor --e10
   ```
4. 登录未打通前，不执行任何依赖登录态的业务 operation。
