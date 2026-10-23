# e10-login 与报表 Skill 集成指南

> 登录统一由 **`weaver-e10-login`** 提供，本 Skill 不内置登录实现。凭证存 `~/.e10-cli/profiles/`（目录名历史兼容，**不是**要去扫 e10-cli 源码包）。

---

## 硬约束（必读）

1. **登录只走 e10-login CLI** — `auth ready` / `status`；禁止硬编码 token；**已登录禁止重跑 oidc**。  
   **禁止**为登录扫描仓库、md、profile 文件、e10-cli*（见快速路径）。
2. **API 请求必须携带三项（缺一不可）**，均来自 e10-login 会话：

| 请求头 | 来源 | 说明 |
|--------|------|------|
| `Cookie` | `cookies.raw` | 完整原始串，**禁止裁剪/去重/改写** |
| `eteamsid` | ETEAMSID 值 | 独立请求头 |
| `User-Agent` | `agentType` | `... AgentType=<agentType>,IsAgent=true` |

完整规范见 **`references/api-auth-headers.md`**；脚本实现见 `scripts/weaver_auth_headers.py`、`scripts/e10_auth.py`。

---

## 何时加载

| 场景 | 动作 |
|------|------|
| **新会话报表搭建（默认）** | **仅** `edc-report auth ready` 或 `e10-login status`；已登录 → **直接搭建** |
| 缺凭证 / 凭证过期 | **立即向用户索要 ETEAMSID cookie**（F12 → Application → Cookies）；**禁止 oidc 兜底**、禁止循环重试 |
| 用户说「登录」「鉴权」「ETEAMSID 失效」 | 同上 |
| 切换测试/生产环境 | `e10-login profile use <name>` |

### 快速路径（强制 · 反慢启动）

```
edc-report auth ready
  ├─ ok:true  → 立刻进入找表/建表（禁止再 whoami / 通读登录 SKILL / 扫任何文件）
  └─ ok:false → 立即按输出的 need/how_to 向用户索要 ETEAMSID → 注入 EB_ETEAMSID/EB_HOST 后继续
                ❌ 禁止 e10-login oidc 兜底；❌ 禁止循环重试 auth ready
```

**禁止**：登录阶段 `Glob`/`Grep`/`Read` 乱扫 Skill 树或其它文件。

详见 `session-build-performance-guide.md`。

---

## 报表任务标准流程（步骤 0）

```
┌─────────────────────────────────────────────────────────────┐
│ 0. 快速鉴权（默认）                                           │
│  edc-report auth ready  /  e10-login status                  │
│    ├─ ✅ 已登录 → 跳到找表/搭建                                │
│    └─ ❌ 缺凭证 → 向用户索要 ETEAMSID；禁 oidc、禁重试          │
├─────────────────────────────────────────────────────────────┤
│ （仅失败时）加载 weaver-e10-login · whoami --json           │
│  Cookie.raw + eteamsid + AgentType 三项请求头                │
└─────────────────────────────────────────────────────────────┘
```

### 推荐命令

```bash
# 每会话首选（秒级）
edc-report auth ready

# 仅未登录时
e10-login oidc --base-url https://<your-e10-host> --agent_type WorkBuddy
e10-login set --eteamsid "<粘贴 cookie>" --base-url https://<your-e10-host>

e10-login profile list
e10-login profile use yunteams
e10-login status
```

### Python 脚本鉴权

```bash
python scripts/e10_auth.py creds --appid <appId>
# 或
eval "$(python scripts/e10_auth.py env)"
```

`ensure_creds()` 写入的 creds 含：`cookie`（raw）、`eteamsid`、`agent_type`。

---

## 与其它能力的分工

| 能力 | 文档 |
|------|------|
| **登录 / OAuth / cookie 刷新** | 本文 + `weaver-e10-login` |
| **API 请求头三项规范** | `references/api-auth-headers.md` |
| **找表 / 字段 / 报表 API** | `edc-report` + 本 Skill `references/*-guide.md` |
| **为何不扫 e10-cli** | `e10-cli-integration.md`（本包不内置说明） |

**不要**在报表 Skill 中重复实现登录逻辑；统一走 e10-login CLI。  
**不要**为搭报表去查找/安装/扫描 e10-cli。

---

## 常见错误处理

| 现象 | 处理 |
|------|------|
| `token为空或失效` / `cookie 已过期` | 优先 `oidc`；失败则 `set` |
| **CLI 1.1.x oidc 无法获取 eteamsId** | **不要因版本阻断**。`auth ready` → `login_required_legacy_set` → **AskUserQuestion**：① 建议升到 1.5.0+ 再 oidc；② 请用户提供 **ETEAMSID（Cookie 单项 Value）+ base-url** 后 `set` → `auth ready`。详见 `edc-report policy login` |
| OIDC localhost 回调被拦 | 换 `--port` 或改用手动 `e10-login set` |
| 脚本环境与 profile 不一致 | `e10-login profile current` 对齐后 `e10_auth.py creds --refresh` |
| 硬编码 ETEAMSID 仍失败 | 删除脚本内写死的 ID，改用 `e10_auth.py` + cookies.raw |
| API 401 但 status 显示已登录 | 检查 Cookie 是否被重拼；须用 cookies.raw 完整串 |

---

## 安装与版本（兼容低版本）

```bash
# 推荐：固定版本、指定官方 registry，安装后校验版本
npm i -g e10-login@1.5.0 --registry https://registry.npmjs.org
e10-login --version

# 低版本（1.1.x 等）已装且无法立刻升级时：用 set 继续搭表
e10-login set --eteamsid "<粘贴 cookie>" --base-url https://<your-e10-host>
edc-report auth ready
```

| 版本 | 报表 | 说明 |
|------|------|------|
| ≥1.5.0 | 推荐 | oidc 新协议完整 |
| 1.3～1.4 | 可用 | status/set/oidc |
| **1.1.x** | **须兼容** | oidc 常失败 → **建议升级或索要 ETEAMSID+base-url 后 set**；`auth ready` 已登录即放行，**禁止**「必须先升到 1.5」挡搭表 |

### 低版本 Agent 流程（强制）

1. `edc-report auth ready`
2. 若 `ok:false` 且 `legacyCli` / `action=login_required_legacy_set`：
   - 向用户说明：**建议升级**，或**提供必要信息**继续搭表
   - AskUserQuestion 收集：`eteamsid` + `baseUrl`（及可选 `agentType`）
   - `e10-login set --eteamsid "<用户值>" --base-url "<用户值>"` → 再 `auth ready`
3. 未拿到用户提供的 ETEAMSID 前，**禁止**编造 token

本报表 Skill **不内置** e10-cli；搭表只用 e10-login + edc-report。
