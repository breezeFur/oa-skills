# E10 API 鉴权请求头规范（硬约束）

> **适用范围**：本 Skill 内所有 EDC 报表 API、DataSetAction、Python 脚本 HTTP 请求。  
> **与登录 Skill 关系**：鉴权参数**必须**来自 `e10-login` 登录 Skill 的会话结果，禁止绕过登录 Skill 自行拼 token。

---

## 一、登录必须走 e10-login Skill

| 允许 | 禁止 |
|------|------|
| `export EB_ETEAMSID=... EB_HOST=...` / `e10-login set --eteamsid ...` | 在脚本/对话中硬编码 ETEAMSID；`e10-login oidc` 兜底（部分环境 SSO 不返回授权码会一直卡住） |
| `e10-login set --eteamsid "PCACCOUNT_xxx" --base-url <url>` | 仅把裸 token 当 Cookie 发请求 |
| `e10-login status` / `whoami --json` 确认会话 | 跳过 e10-login，直接 curl 拼 Cookie |
| `scripts/e10_auth.py` 从 profile 读取 | 裁剪/去重/改写 cookies.raw |

**Agent 执行顺序**：

1. 加载 `weaver-e10-login`
2. 执行 `edc-report auth ready`（一次即结论）；缺凭证 → **立即向用户索要 ETEAMSID cookie**（禁 oidc 兜底）
3. 通过 `e10-login whoami --json` 或 `scripts/e10_auth.py creds` 取得完整鉴权三元组
4. 再调用报表 API / 运行搭建脚本

---

## 二、API 请求必须携带三项（缺一不可）

每次 HTTP 请求**必须同时**包含以下三项，且均来自 e10-login 返回的用户会话信息：

| # | 请求头 | 取值来源 | 硬约束 |
|---|--------|----------|--------|
| ① | `Cookie` | `auth.cookies.raw`（e10-login profile） | **完整原始串**；禁止裁剪、去重、改写、重拼（如禁止自行拼 `ETEAMSID=xxx`） |
| ② | `eteamsid` | 与 Cookie 中 `ETEAMSID` 值一致 | 独立请求头，不可省略 |
| ③ | `User-Agent` | `auth.agentType` | 末尾必须为 `AgentType=<agentType>,IsAgent=true`（如 `AgentType=WorkBuddy,IsAgent=true`） |

### 正确示例

```http
Cookie: <完整 Cookie 原始串来自 e10-login cookies.raw> ; ETEAMSID=<ETEAMSID 值>
eteamsid: <ETEAMSID 值>
User-Agent: Mozilla/5.0 ... Chrome/<browser-version> Safari/537.36 Edg/<browser-version> AgentType=WorkBuddy,IsAgent=true
```

### 错误示例（禁止）

```http
# ❌ 仅裸 ETEAMSID，丢失 cookies.raw 其它键
Cookie: ETEAMSID=<不应手动拼写>

# ❌ 自行重拼 Cookie，非 e10-login 原始串
Cookie: <不应手动拼写>; ETEAMSID=<不应手动拼写>

# ❌ User-Agent 占位符或未带 IsAgent
User-Agent: ... AgentType=<agentType>,IsAgent=true

# ❌ 缺少 eteamsid 请求头
```

---

## 三、Python 脚本实现

本 Skill 统一通过 `scripts/weaver_auth_headers.py` 构造请求头：

```python
from weaver_auth_headers import build_auth_headers

headers = build_auth_headers(
    host=creds["host"],
    eteamsid=creds["eteamsid"],
    cookie=creds["cookie"],          # cookies.raw 完整串
    agent_type=creds["agent_type"],  # 来自 e10-login
    ebbusinessid=creds["ebbusinessid"],
)
```

凭证解析：`scripts/e10_auth.py ensure_creds()` → 写入 `outputs/eub_creds.json`：

```json
{
  "host": "weapp.xxx.cn",
  "eteamsid": "PCACCOUNT_...",
  "cookie": "<cookies.raw 完整原始串>",
  "agent_type": "WorkBuddy",
  "ebbusinessid": "...",
  "app_id": "..."
}
```

---

## 四、与脚本环境变量

- 推荐：`eval "$(python scripts/e10_auth.py env)"` 或 `edc-report auth ready` 后由脚本读 profile。
- 报表 API **仍须满足上述三项**；可从 `e10-login whoami --json` 或 profile `auth` 取 `cookies.raw` / `agentType`。
- 本报表包 **不依赖、不扫描** e10-cli。

---

## 五、常见错误

| 现象 | 原因 | 处理 |
|------|------|------|
| `token为空或失效` | Cookie 被改写或只有裸 token | 请用户重新提供 ETEAMSID，再用 `cookies.raw` |
| 401 / 403 | 缺少 `eteamsid` 头或 User-Agent 无 IsAgent | 检查 `weaver_auth_headers.build_auth_headers` |
| Agent 环境被拒 | `agentType` 与登录时不一致 | 用 `e10-login set` 重新写入（`agentType` 由 eb_auth 统一生成） |

---

## 相关文档

- `weaver-e10-login` — 登录命令与 profile 结构
- `references/e10-login-integration.md` — 报表任务步骤 0 登录流程
