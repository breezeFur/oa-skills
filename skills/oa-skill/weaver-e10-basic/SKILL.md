---
name: weaver-e10-basic
display_name: "泛微E10基础能力"
display_name_en: "Weaver E10 Basic Capabilities"
description: "泛微E10基础能力助手，覆盖登录、租户、应用、主题等基础功能支持，包括获取租户列表，人员身份切换等对接场景。"
description_zh: "泛微E10基础能力助手，封装登录、租户、应用、主题等基础功能支持，包括获取租户列表，人员身份切换等对接场景。"
description_en: "Weaver E10 basic capabilities assistant. Covers login, tenant, application, theme and other basic function support, including getting tenant list and personnel identity switching scenarios."
version: 1.0.0
---

## 泛微E10基础能力助手

本 Skill 封装泛微E10基础能力，涵盖登录、租户、应用、主题等基础功能支持，用于 Agent 在对话中完成切换组织等基础操作。

### 前置依赖

Agent 按 [CLI 自动准备](../cli-setup.md) 直接准备匹配的 `e10-login@1.5.0`，检查命令路径、版本与启动；登录技能已随本仓库收录，读取同级 `../weaver-e10-login/SKILL.md`。需要的 CLI 缺少或不匹配时自行安装/更新，成功后继续任务，不要求用户手动安装。此技能无需另装一个 basic CLI。

本 Skill 依赖以下外部 skill，使用前需确保已安装并可用：

| 依赖 skill | 用途 | 何时需要 |
|---|---|---|
| `weaver-e10-login` | 认证（access_token、签名）、完整 URL 拼接、提供 `base_url`/`tenant_key`/`operator` | 所有操作 |

### 读取顺序

1. 本文件已包含能力概览和解析策略速览，大多数场景可直接据此操作
2. 如需了解完整接口列表，读取 `references/catalog.md`
3. 调用具体接口前，读取对应的单接口文档，确认参数结构和约束

### 认证与接口地址

- 单接口文档中的接口 URL 均为**去域名路径**
- 接口路径格式：
  - `/papi/passport/xxx` - Passport相关接口
  - `/api/app/basicserver/xxx` - BasicWeb相关接口
  - `/papi/baseserver/layout/xxx` - BaseServer相关接口（如checkTicket）
- **完整接口地址的拼接和认证（access_token、签名等）必须由 `weaver-e10-login` skill 完成**
- 生成请求参数时，不包含认证字段

### 可用能力

| 用户意图 | 对应接口 | 类型 |
|---|---|---|
| 查询当前用户所属组织/租户列表 | 查询用户所属组织列表 (siblingsTenantList) | 用户场景 |
| 选择要切换的租户/组织 | 查询用户所属组织列表 (siblingsTenantList) | 用户场景 |
| 切换租户/团队/组织 | App/客户端切换组织 (appChangeTenant) | 用户场景 |
| workbuddy等第三方系统对接切换组织 | App/客户端切换组织 (appChangeTenant) | 第三方对接 |

### 接口说明

#### 查询用户所属组织列表

- **路径**: `/api/app/basicserver/siblingstenant/list`
- **请求方法**: GET
- **必填参数**: 无（自动从登录态获取用户信息）
- **返回方式**: 直接返回JSON，包含用户所属的所有组织/租户列表
- **使用场景**: 切换租户前，获取当前登录人员的租户列表供选择
- **返回数据**: 包含 employeeId、tenantKey、tenantName、isCurrent 等信息

#### App/客户端切换组织（workbuddy等第三方系统对接）

- **路径**: `/papi/passport/login/appChangeTenant`
- **请求方法**: GET
- **必填参数**: employeeId（查询参数）
- **返回方式**: 直接返回JSON，包含新的ETEAMSID
- **ETEAMSID获取**: 从Cookie中自动获取
- **ETEAMSID回写**: 切换成功后接口自动回写新的ETEAMSID到Cookie
- **使用场景**: 第三方系统对接（如workbuddy），可直接获取最终的ETEAMSID

### 切换租户流程

```
1. 调用查询用户所属组织列表接口，获取当前用户的所有租户/组织
2. 展示租户列表供用户选择
3. 用户选择要切换的租户，获取对应的 employeeId
4. 调用切换组织接口，传入 employeeId
5. 接口回写新的ETEAMSID到Cookie
6. 切换完成
```

### 调用规则

- **写操作授权**：用户已明确要求切换到指定组织等操作时，核对真实目标后执行；候选不唯一或切换超出请求时才提问，不对相同请求重复确认。
- **同类型候选**：在同类型候选接口中只选择最符合用户意图和接口约束的一个；目标接口不明确时先询问或收窄，不盲猜。
- **失败边界**：同类型候选接口调用失败后立即停止并向用户说明失败原因，**不自动切换**到其他同类型接口、近义接口或兜底接口继续尝试。
