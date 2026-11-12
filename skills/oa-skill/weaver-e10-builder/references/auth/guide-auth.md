# 鉴权与多环境管理

> e10-cli 支持多环境 Profile 切换，auth 文件和 config 按环境隔离存储。

## 目录结构

```
~/.e10-cli/
├── profile                    ← 当前激活的 profile 名
└── profiles/
    ├── yunteams/
    │   ├── auth               ← 加密的认证凭证
    │   └── config.json        ← baseUrl + passportUrl
    └── mulinquan/
        ├── auth
        └── config.json
```

## 命令参考

### 登录认证

| 命令 | 说明 |
|------|------|
| `e10-login oidc --base-url <url> --agent_type <实际宿主>` | 推荐的官方浏览器 OAuth；与 Builder 共享 profile |
| `e10-cli auth set --eteamsid <id> --base-url <url>` | 仅按用户主动提供的 ETEAMSID 写入；不用于账号密码 |
| `e10-cli auth status` | 查看当前登录状态（含 profile 名、cookie 有效性） |

Builder 1.5.4 的 `auth login --help` 已提供 OIDC 入口，但该入口带必填 tenant-key；默认使用配套 `e10-login oidc`，其 tenant-key 可选，不为登录额外索取租户 Key。以实际安装版本帮助为准。

用户已经提供的目标地址、账号密码和登录授权直接沿用，不再次询问是否允许登录或重复索取。已有匹配环境的有效会话直接复用；新会话由 Agent 发起官方 OAuth 登录。CLI 没有账号密码直登参数时，在可控的官方浏览器登录页使用用户提供的账号密码；不把密码作为 ETEAMSID，不猜测登录接口或参数。只有验证码、MFA、平台授权按钮或当前工具无法操作的页面需要用户参与时，说明具体阻碍并交接该步骤。CLI 与浏览器能否访问同一本地回调由 Agent 根据实际运行环境判断，无需用户口头确认同机。不要把凭证或带凭证的工具结果打印到对话、日志或提交中。

### Profile 管理

| 命令 | 说明 |
|------|------|
| `e10-cli auth profile list` | 列出本地所有 Profile |
| `e10-cli auth profile current` | 查看当前激活的 Profile |
| `e10-cli auth profile use <name>` | 切换到指定 Profile（不存在则自动创建） |

**单次覆盖**：所有命令支持 `--profile <name>` 临时用指定 profile（auth + config baseUrl），不切换全局激活态：
```bash
e10-cli --profile e-cology form list <appId>   # 只用这一次，不改变当前环境
```

## 典型用法

```bash
# 在 yunteams 环境登录
e10-login oidc --base-url "https://weapp.yunteams.cn"
# → 自动创建/切换到 profile: yunteams

# 切到 mulinquan
e10-login oidc --base-url "https://weapp.mulinquan.cn"
# → 自动创建/切换到 profile: mulinquan

# 查看所有环境
e10-cli auth profile list

# 切回 yunteams
e10-cli auth profile use yunteams

# 查看当前
e10-cli auth status
```

## 全局选项

| 选项 | 说明 |
|------|------|
| `--auth <path>` | 临时指定 auth 文件路径（覆盖 profile） |
| `--base-url <url>` | 临时指定平台地址 |
| `--json` | JSON 格式输出 |

## Profile 命名规则

`auth set` 时根据 `baseUrl` 域名自动生成 profile 名：
- `https://weapp.yunteams.cn` → `yunteams`
- `https://weapp.mulinquan.cn` → `mulinquan`

也可用 `auth profile use <自定义名>` 手动创建命名。

## 凭证加密

Auth 文件使用 AES-256-GCM 加密存储，密钥存于 **OS keychain**（每机一把动态密钥，源码不含密钥），headless 无 keychain 后端时回退到 `~/.e10-cli/.key`（0600）。详见 `core/crypto.ts`。格式：
```json
{ "enc": true, "v": 1, "data": "<base64>" }
```

> 与 `e10-login` 共用同一 keychain 条目（service=`e10-cli`/account=`auth-key`），auth 文件在 e10-cli 与 e10-login 间互通——用任一登录后另一个可直接用。
> ⚠️ 从硬编码密钥迁移到动态密钥后，旧版 auth 文件无法解密，需重新登录（`auth login` 或 `auth set --eteamsid`）。
