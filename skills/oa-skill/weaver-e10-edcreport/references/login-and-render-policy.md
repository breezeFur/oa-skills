# 登录凭证 与 渲染 策略（强制）

> 针对两个高频痛点：①「登录自动获取不了，还一直等待/反复调用」②「为了看效果反复全量渲染，白等几分钟」。
> 实现：`scripts/eb_auth.js`（JS）/ `scripts/weaver_auth_headers.py`（Python）/ `scripts/auth_ready.js`（门禁）/ `scripts/eb_render.js`（渲染守卫）。

---

## 一、登录：只接受「用户提供的 ETEAMSID」，禁止自动登录

### 1.1 需要用户提供什么（缺凭证时**照此原样告诉用户**）

| 需要的东西 | 说明 |
|---|---|
| **ETEAMSID cookie 值** | 浏览器登录平台后，F12 → Application / 应用程序 → Storage → Cookies → 选中该站点 → 复制 `ETEAMSID` 的 Value，形如 `PCACCOUNT_EXAMPLE_SESSION_VALUE` |
| **平台地址 baseUrl** | 例如 `https://itsm.hongjing-wh.com:5001` |

拿到后**二选一**：

```bash
# A) 只对当前终端生效（最快，零等待）
export EB_ETEAMSID="<粘贴 cookie>"
export EB_HOST="<平台地址>"

# B) 持久写入（之后所有脚本免配置）
e10-login set --eteamsid "<粘贴 cookie>" --base-url "<平台地址>"
```

### 1.2 禁止事项（硬约束）

1. **禁止用 `e10-login oidc` 兜底。** 部分环境的 SSO `authorize` 端点不发放授权码（`302 → /sp/intauthportal/logintip?code=80015`），本地回调 `127.0.0.1:19800` 永远等不到 → 命令一直卡住。缺凭证时应当**立即向用户索要 ETEAMSID**，而不是尝试 oidc。
2. **禁止循环校验**：`auth ready` / `e10-login status` 一次即结论，不要 repeatedly 重试、不要 whoami 二次确认。
3. **禁止为登录去 Glob/Grep 乱扫仓库**，也不要通读 `weaver-e10-login` 全文。
4. 禁止把 cookie 写进代码、写进仓库或写进任何提交物。

### 1.3 解析顺序（`eb_auth.js` 实现）

| 顺序 | 来源 | 成本 |
|---|---|---|
| ① | 环境变量 `EB_ETEAMSID` + `EB_HOST` | **0 spawn、0 网络**（推荐） |
| ② | `~/.e10-cli/profiles/<profile>/auth` **不存在** → 立即抛错并给出获取指引 | **不 spawn、不等待** |
| ③ | 本地 `config.json`（明文）取 `baseUrl` | 0 spawn |
| ④ | **一次** `e10-login status`（硬超时 `EB_AUTH_TIMEOUT_MS`，默认 8000ms） | ~1s，每进程最多一次 |
| ⑤ | 仍失败 → 抛 `EbAuthError`（`.help` 含完整获取步骤） | 立即 |

> 实测：纯 env 路径 **0ms**；无凭证路径 **不 spawn**，直接给出指引；同一进程内重复调用 **0ms**（进程级缓存）。
> 对比修复前：每次请求 `execSync('e10-login status')` 2~4 次，单次冷启动 ≈2.4s。

### 1.4 相关环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `EB_ETEAMSID` / `EB_HOST` | — | 首选凭证 |
| `E10_BASE_URL` / `E10_HOST` | — | 兼容旧名 |
| `EB_AUTH_TIMEOUT_MS` | `8000` | CLI 硬超时，超时即失败，不重试 |
| `EB_AUTH_NO_CLI` | — | `1` = 禁止 spawn CLI（纯 env 模式，测试用） |
| `E10_PROFILE` | — | 指定 profile（否则读 `~/.e10-cli/profile`） |

### 1.5 脚本用法

```js
// JS
const A = require('./eb_auth.js');
const sid = A.eteamsId();          // 缺凭证时抛 EbAuthError（含 .help 指引）
const host = A.baseUrl();
const cookie = A.cookieHeader();
const st = A.authStatus();         // {ok, source, host, eteamsIdMasked} 或 {ok:false, need, how_to}
```

```python
# Python
from weaver_auth_headers import resolve_auth, auth_status, build_auth_headers
r = resolve_auth()                 # {"eteams_id", "host", "source"}；缺失抛 EbAuthError
```

命令行门禁：

```bash
edc-report auth ready      # 或 node scripts/auth_ready.js
# ok:true  → exit 0，直接搭建
# ok:false → exit 1，输出 need / how_to / forbid
```

---

## 二、渲染：默认不渲染全量数据

### 2.1 为什么必须默认关闭

本平台交叉表渲染**先算完再拒绝**：数据集不带过滤约 **24,200 行**，完整展开 87 列 ≈ **210 万格**，平台硬上限 **50,000 格**（≈ 574 行 × 87 列）→ 必然 `code:555`，且**每次都要白烧 15~80 秒**才拿到这个结论。

> 实测：已上线「考勤汇总报表(全量)」本体 80,659ms → 555；计提 77,575ms → 555。

**搭报表只需要落库成功，不需要渲染全量数据。**

### 2.2 验证优先用「结构回读」，不用渲染

| 验证目标 | 用什么 | 不用什么 |
|---|---|---|
| 报表已落库 | `getReportDevInfo` 返回 200 且 `fields` 非空 | ❌ analysis+getJsonStr |
| 单元格/字段绑定正确 | `getReportDevInfo.fields`（`name` / `fieldKey` / `x` / `y` / `cellType`） | ❌ 渲染 |
| Field 绑定合法 | `node scripts/verify_field_bind.js <reportId> [appId]` | ❌ 渲染 |
| 数据集注册形态 | `dataset/list?hasField=true`、`fieldsAndOriginFields` | ❌ 渲染 |
| 查询条件 | `getQueryItemNew` 回读 | ❌ 渲染 |
| 交付 | 直接给设计器地址，人眼确认 | ❌ 反复渲染截图 |

### 2.3 确实要渲染时的守卫规则（`eb_render.js`）

| 规则 | 值 |
|---|---|
| 默认放行？ | **否**，需 `EB_ALLOW_RENDER=1` |
| 硬超时 | `EB_RENDER_TIMEOUT_MS`，默认 **30000ms**，超时立即放弃 |
| 重试 | **绝不重试**；命中 555 直接返回结论，不换参数再试 |
| `pageRowCount` 封顶 | `EB_MAX_PAGE_ROW_COUNT`，默认 **574**（= 50000/87） |

```bash
# 默认：直接跳过，0 渲染
node scripts/eb_render.js <reportId> <appId>

# 放行（诊断用），并把硬超时压到 3s
EB_ALLOW_RENDER=1 EB_RENDER_TIMEOUT_MS=3000 node scripts/eb_render.js <reportId> <appId> 200
```

```js
const R = require('./eb_render.js');
const r = await R.render(reportId, appId, { pageRowCount: 200 });
if (r.skipped) console.log(r.hint);          // 默认不渲染
if (r.code === 555) console.log(r.hint);     // 超限：用查询条件收敛行数
```

### 2.4 结论

- **搭建流程里不出现渲染调用**；渲染只作为「显式放行的诊断」存在。
- 若必须让报表可看：用**查询条件（年月/部门/人员）**或**行级权限**把行数收敛到 ≤574，而不是调 `pageRowCount` 硬凑（同结构下 700 挂、1000 过的边界不稳定）。
