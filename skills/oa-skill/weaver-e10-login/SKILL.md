---
name: weaver-e10-login
display_name: 泛微E10登录工具
display_name_en: E10 Login
description: E10 平台独立登录认证 —— OAuth2.0 浏览器授权 / ETEAMSID 手动设置 / 状态查询 / 多环境切换
description_zh: E10 平台的登录认证工具，支持 OAuth2.0 浏览器授权登录、ETEAMSID 手动写入、登录状态查询与多环境（Profile）切换。
description_en: E10 login & auth tool — OAuth2.0 browser authorization, manual ETEAMSID set, status check and multi-environment profile switching.
category: coding
version: 1.5.1
author: 泛微网络科技股份有限公司
---

# e10-login 登录 Skill

e10-login 是 e10-cli 的配套登录工具，只做认证管理。两者共享 `~/.e10-cli/profiles/` 下的认证文件，格式完全兼容。

## 安装

Agent 按 [CLI 自动准备](../cli-setup.md) 检查运行时和命令。缺少或版本与本技能匹配要求不符时，直接代用户安装/更新；有效版本复用，不另外发起安装确认，也不要求用户开终端。CLI 安装和启动验证不执行登录。

```bash
# 全局安装
npm i -g e10-login@1.5.0 --registry=https://registry.npmjs.org

# 验证
e10-login --version   # → 1.5.0
e10-login --help
```

> Node.js ≥ 18（用到原生 fetch、ESM）。安装后 `e10-login` 命令全局可用。

> ⚠️ **使用前务必确认版本号**：跑 `e10-login --version` 看实际装的版本，确保是预期版本（旧版本可能缺新字段/新协议支持）。淘宝镜像约 10 分钟同步官方源，急用最新版加 `--registry https://registry.npmjs.org`。
>
> 本 Skill 配套 **e10-login@1.5.0** 使用；按匹配版本安装，安装成功后核对真实路径、版本和 `--help`，再继续当前认证任务。

## 首次登录

触发登陆之前，必须使用你的 AskUserQuestion 工具询问用户“请确认：数据会经过大模型，敏感数据请谨慎操作使用 Yes / No ”

OAuth2.0 浏览器授权登录（推荐）：

```bash
e10-login oidc --base-url https://weapp.xxx.cn
```

端口冲突时换端口：

```bash
e10-login oidc --base-url https://weapp.xxx.cn --port 19801
```

指定代理类型（随 `access_type=agent&agent_type=<type>` 发给 authorize，并用于登录后请求的 UA 与 cookie。UA 形如 `AgentType=<type>,IsAgent=true`，cookie 形如 `agentType=<type>; isAgent=true`。可选值如 WorkBuddy / ClaudeCode / Codex / Xiao.E ：

```bash
e10-login oidc --base-url https://weapp.xxx.cn --agent_type WorkBuddy
```

## 无法走 localhost 回调时（手动设置）

```bash
e10-login set --eteamsid "PCACCOUNT_xxx" --base-url https://weapp.xxx.cn
```

从浏览器 DevTools → Application → Cookies 复制 ETEAMSID 值，跳过浏览器登录直接写入。

## 命令

| 命令 | 用途 |
|------|------|
| `e10-login oidc --base-url <url> [--agent_type <type>]` | OAuth2.0 浏览器授权登录（首次登录用这个；--agent_type 指定代理类型，默认 workbuddy） |
| `e10-login set --eteamsid <id> --base-url <url>` | 手动写入 ETEAMSID |
| `e10-login status` | 查看当前登录状态（含 cookie 是否过期） |
| `e10-login whoami` | 获取当前登录用户信息（调后端 teamsCheck，发完整 cookie） |
| `e10-login whoami --json` | 输出后端原始 JSON |
| `e10-login profile list` | 列出所有环境 |
| `e10-login profile use <name>` | 切换环境 |
| `e10-login profile current` | 查看当前激活环境 |

## 用法示例

```bash
# 首次登录
e10-login oidc --base-url https://weapp.xxx.cn

# 查看登录状态
e10-login status

# 查看当前用户信息（含完整 cookie 串）
e10-login whoami

# 切换环境
e10-login profile use yunteams
e10-login profile list
```

## 认证文件

- 目录：`~/.e10-cli/profiles/<profile>/auth`（AES-256-GCM 加密；密钥存 OS keychain，每机一把，源码不含密钥）
- 结构：`{ cookies: { ETEAMSID, raw }, userId, tenantKey, agentType, version, baseUrl, passportUrl }`
  - `cookies.ETEAMSID`：单值，e10-cli 兼容读取
  - `cookies.raw`：后端 profile 接口返回的完整 cookie 串，发请求时优先用它（带 langType / LOGIN_TYPE 等），没有则回退 `ETEAMSID=...`
  - `agentType`：代理类型（默认 workbuddy，可用 `oidc --agent_type` 指定）；发请求时拼进 cookie（`agentType=<值>; isAgent=true`）**并**作为 `User-Agent` 头（格式 `AgentType=<值>,IsAgent=true`）—— cookie 与 UA 双携带
  - `version`：基线版本（用户信息接口返回），`status`/`whoami` 会展示；`whoami` 还会显示当前发送的 `User-Agent`
- 配置：`~/.e10-cli/profiles/<profile>/config.json`（baseUrl / passportUrl / tenantKey）
- 当前激活 profile：`~/.e10-cli/profile`
