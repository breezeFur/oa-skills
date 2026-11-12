---
name: weaver-e10-ebuilder-form
display_name: 泛微E10 eBuilder智能助手
display_name_en: Weaver E10 eBuilder Assistant
version: 1.0.4
author: 泛微网络科技股份有限公司
agent_created: true
description: "面向泛微 E10 OA 的 eBuilder 智能助手。通过自然语言查询业务列表和表单数据，按名称填写人员、部门及关联数据，并协助新增、修改或删除数据。"
description_zh: "面向泛微 E10 OA 的 eBuilder 智能助手。通过自然语言查询业务列表和表单数据，按名称填写人员、部门及关联数据，并协助新增、修改或删除数据。"
description_en: "AI assistant for Weaver E10 OA eBuilder forms. Query list/form data, fill relational fields by name, and assist data creation/modification/deletion."
license: "Proprietary"
compatibility: "WorkBuddy；需已安装并授权 weaver-e10-login，目标 E10 环境须开放对应 eBuilder 接口。"
dependencies:
  - "weaver-e10-login"
---
# 泛微E10-EB智能助手

面向 OA 使用人员，通过自然语言查找有权限访问的 eBuilder 业务菜单，查询列表和表单数据，并按权限协助新增、修改和删除数据。

把菜单定位、List/NList 页面查询和表单数据操作放在同一套已认证上下文中。除登录依赖外，只读取本目录中的 references 和 scripts。

## 适用场景与触发条件

当用户提出以下需求时触发本技能：
- **菜单与表单查询**：通过业务名称/菜单名称查找 E10 eBuilder 菜单，查看表格、数据列表或表单布局配置。
- **列表数据查看与分页**：查询 List / NList 表格的运行时配置、分页数据及数据总数。
- **表单数据操作**：根据表单id或自定义接口新增、修改、详情查询或删除 eBuilder 表单业务数据。
- **关联字段智能解析**：在新增或编辑表单时，按名称智能匹配人员、部门、分部、审批实例及关联浏览字段 ID。

## 登录依赖

本 Skill 不负责登录、环境切换或凭证管理。当前任务没有目标 E10 环境的有效认证会话时，使用 `weaver-e10-login` Skill 建立会话，并复用其确认的 `origin` 和当前运行时会话；已有有效会话时直接复用，不重复调用。

- 登录依赖仅为 `weaver-e10-login`，已随本仓库收录。按 [CLI 自动准备](../cli-setup.md) 由 Agent 直接准备 Python 3.10+、`e10-login@1.5.0` 并验证；登录 CLI 缺少或不匹配时自行安装/更新，随后继续原任务，不要求用户手动安装。宿主命名凭据能力缺少时如实说明，不把 CLI 安装等同于插件能力已可用。
- 目标环境不明确时，先由 `weaver-e10-login` 向用户确认；不得自行猜测域名、租户或账号。
- 不要求用户在对话中粘贴密码、Cookie 或 `ETEAMSID`，也不得把认证信息写入文件、命令示例、查询参数或回复。
- 同一任务、同一 `origin` 最近一次认证接口已经成功且尚未出现 `401/403` 时，直接复用现有会话；不要为了“确认是否登录”重复调用登录 Skill 或额外发送健康检查请求。
- 接口返回 `401` 或 `403` 时，停止当前操作，交由 `weaver-e10-login` 重新建立或确认会话；恢复后再从失败的只读步骤继续，写操作不得自动重放。

## 先建立共享上下文

每次执行先检查当前任务是否已有用户确认目标环境的有效认证会话；有则复用，没有则调用 `weaver-e10-login` 建立会话。然后读取 [references/session-and-routing.md](references/session-and-routing.md)，在任务上下文中维护字符串形式的 `origin`、`appId`、`apiPrefix`、`hostPageId`、`listId`、`listKind`、`objId` 和 `interfacePk`；未知值保持未知，不能用其他 ID 猜测。

### 快速复用与最少交互

- 新增、修改、详情和删除默认使用统一 CLI 的短期缓存：同一认证会话下，菜单/部署/表单上下文复用 30 分钟，字段结构复用 10 分钟。缓存只保存上下文和字段元数据，不保存 Cookie、`ETEAMSID`、浏览查询结果或业务记录。
- 缓存命中时不要再次搜索菜单、检查部署、解析 `objId` 或获取字段。用户要求最新配置、表单结构刚修改或缓存上下文与实际响应冲突时，才使用 `--refresh` 重建缓存。
- 菜单、字段和浏览数据均唯一匹配时直接继续，不额外询问用户，也不增加写前详情查询或权限探测。只有重名、目标/范围不明确、缺少必要业务值时才询问。
- `checkRight=true` 是写请求自身的权限校验，不是额外接口；新增和修改后的单次 `getDataById` 回查继续保留。

## 按用户提供的入口路由


| 已知信息或用户意图                           | 入口               |
| -------------------------------------------- | ------------------ |
| 业务名称、菜单名称或自然语言描述             | 菜单定位           |
| E10 表格或数据列表页面 URL                   | 直接链接解析       |
| `objId`，询问有哪些表格、数据列表或表单布局  | 表单视图枚举       |
| 已确认的 List/NList ID，查询配置、分页或总数 | 列表运行时         |
| `objId`，直接操作表单数据                    | OpenAPI 表单数据   |
| `interfacePk` 或明确要求已发布自定义接口     | 自定义接口表单数据 |
| 按名称填写人员、部门、分部、审批或关联字段   | 浏览字段查询       |

### 菜单定位

1. 读取 [references/menu-search.md](references/menu-search.md)，只搜索当前用户有权限的菜单并消歧；选中菜单后同时保留其 `menuUrl`。
2. 取得唯一菜单的 `appId` 后读取 [references/deployment-routing.md](references/deployment-routing.md)，确定 `/api/ebuilder/form/**` 接口使用的 `apiPrefix`；字段、选项等 `/api/ebuilder/common/**` 接口仍走公共路径。
3. 读取 [references/menu-listid-resolution.md](references/menu-listid-resolution.md)，把 `SEARCH` 路由为 List，把 `VIEWPORT` 路由为 NList。SEARCH 直接以菜单 `pageId` 作为 `listId`；VIEWPORT 以菜单 `pageId` 请求一次 `viewPageInfo`，再从 `data.page.comps[1].config` 取得真实 `listId` 和 `objId`。
4. 读取 [references/runtime-routing.md](references/runtime-routing.md)，取得 `objId` 与页面上下文，再执行页面查询或表单数据操作。

菜单未唯一匹配时停止，不得默认取第一条。用户提供可识别的列表页面 URL 时改走下面的直接链接解析；URL 结构不受支持时不得从名称或其他 ID 猜测目标。

### 直接链接解析

用户提供 E10 列表页面 URL 时，优先运行 `scripts/form_data.py resolve --url "<完整URL>"`，不再搜索菜单：

- URL 路径中的 `list`，或参数中的 `SEARCH`，按表格处理。
- URL 路径中的 `viewport`，或参数中的 `VIEWPORT`，按数据列表处理。
- `search` 路径视为表格；`nlist` 类型值视为数据列表。
- `/ebdapp/view/{appId}/{SEARCH|VIEWPORT}/{pageId}-{menuId}` 中拆出应用、页面和菜单 ID；`SEARCH` 的 `pageId` 就是 `listId`，`VIEWPORT` 的 `pageId` 是 `hostPageId`。
- `/sp/ebdfpage/{list|search|viewport}/{appId}_{pageId}` 中拆出 `appId` 和页面 ID；其中 `viewport` 的页面 ID 仍是 `hostPageId`。
- 路径与 `pageType/listKind/viewType` 参数冲突、路径 ID 与 `pageId/listId` 参数冲突时停止，不尝试两套接口。
- 表格只调用 List 上下文接口；数据列表只调用一次 `viewPageInfo`，并继续以 `data.page.comps[1].config.ebListId` 和 `config.objId` 为准。
- 用户消息包含 Markdown 链接时解析实际跳转地址；若显示文字与实际地址不同，不把两条地址的 ID 混用。
- 完整 URL 可直接确定 `origin`；相对 URL 必须复用已确认的 `origin`。解析出的原始同源链接作为返回给用户的优先列表地址。

### 表单视图枚举与列表运行时

- 已知 `objId` 并要枚举视图或布局：运行 `scripts/get_form_views.py`。
- List 配置：读取 [references/table-config.md](references/table-config.md)，运行 `scripts/get_table_config.py`。
- NList 配置：读取 [references/nlist-config.md](references/nlist-config.md)，运行 `scripts/get_nlist_config.py`。
- List 分页与总数：读取 [references/list-pagination.md](references/list-pagination.md)，运行 `scripts/query_list_data.py`。
- NList 分页与总数：读取 [references/nlist-pagination.md](references/nlist-pagination.md)，运行 `scripts/query_nlist_data.py`。
- 两类列表单页最多查询 200 条。查询全部页时先按总数计算页数；预计需要 100 页或更多时拒绝请求，请用户增加筛选条件或缩小范围，不得循环调用单页查询绕过限制。

只使用菜单 `pageType` 映射或接口实际返回的 `viewType` 路由。只有一个未分类的视图 ID 时，先取得父表单 `objId` 并枚举视图，或请用户确认页面类别；不要同时试跑两套接口来猜类型。

所有脚本都接受 `--origin` 与 `--api-prefix`，也可从当前进程的 `EBUILDER_ORIGIN`、`EBUILDER_API_PREFIX`、`EBUILDER_COOKIE` 或 `ETEAMSID` 读取运行时上下文。独立部署时必须把已经解析的 `/api/ebuilder{appId}` 传给脚本；脚本只把它用于 `/form/**`，不会改写 `/common/**` 或业务模块浏览接口。

### 表单数据操作

读取 [references/routing.md](references/routing.md)，再只读取本次操作对应的接口文档：

- 新增、修改、详情或删除优先读取[统一表单数据 CLI](references/cli.md)，运行 `scripts/form_data.py`。它在一次进程内复用菜单上下文和字段定义，并行解析互不依赖的浏览字段，输出逐阶段耗时。
- 新增和修改成功后必须由统一 CLI 使用返回的 `dataId` 调用 `getDataById` 回查；不得使用 `getAllData` 代替单条回查。
- 服务端返回 `status=false`、缺少 `dataIds` 或权限错误时视为业务失败，保留真实业务消息并停止；不得自动重试写请求，也不得关闭权限校验。

- 已知 `objId`：使用 OpenAPI。先读取字段定义，按需读取选项，并解析 `mainTable`/`detailN` 映射。
- 已知 `interfacePk`：使用与已发布配置类型一致的自定义接口；需要 `operator` 时只能使用当前已认证会话确认的操作人 ID。
- 同时存在 `objId` 和 `interfacePk` 而用户没有指定接口族时，先消歧，不能交叉拼接两套请求体。
- 页面分页/总数优先使用 List/NList 运行时契约；只有用户明确要求表单级数据时才使用 OpenAPI 或自定义接口分页/总数。

### 浏览字段查询

新增或修改数据时，如果人员、部门、分部、审批、文档或其他关联浏览字段只给了名称，不要反问用户索要 ID。读取 [按名称查询人员、部门和关联数据](references/browser-fields.md)，运行 `scripts/query_browser_field.py`，在当前账号权限范围内把名称解析为可写入的选项。

- 查到唯一结果后，使用返回的 `optionId` 和 `content` 继续组装字段值。
- 查到多条重名结果时，向用户展示可用于区分的业务信息并让用户选择，不能默认取第一条。
- 未查到时说明当前账号下没有可选结果，不能把显示名称直接当作 ID 写入。
- 关联浏览优先使用字段定义中实际返回的模块和浏览类型；人员、部门、分部、审批数据和文档使用文档中已验证的内置路由。不得根据字段标题猜接口。
- 审批字段查询的是审批实例；流程定义查询不能代替审批实例查询。
- 写操作包含多个浏览字段时优先交给 `scripts/form_data.py` 并行解析；`query_browser_field.py` 保留给单字段查询和诊断。两者都必须复用已取得的字段定义，不能为了每个字段重复请求字段接口。

## 接口失败止损

任一接口返回 HTTP 错误、业务失败、超时或响应结构异常时，立即按[接口失败止损规则](references/session-and-routing.md#接口失败止损)处理。同一接口或同一排查方向在条件未变化时最多尝试两次：首次失败后，仅在网络波动、临时服务异常或有明确修正依据时再试一次；第二次仍失败就停止，不再通过轮换接口、前缀或参数碰运气。写请求不得因超时或结果不明确而直接重放。

## 返回可直接打开的页面地址

新增、修改、删除、查询详情或查询列表数据后，回复中必须同时给出用户可直接打开的完整页面地址。每次执行前读取的 [会话、上下文与路径路由](references/session-and-routing.md#用户页面地址) 包含数据地址、删除后回收站地址及列表地址的选择规则。

- 面向用户统一称为“列表”，不要暴露 List/NList 等内部分类名称。
- 用户直接提供可识别的列表 URL 时优先原样返回；否则优先使用本次选中菜单实际返回的 `menuUrl`，没有可用的 `menuUrl` 时再按内部列表类型拼接预设地址。
- 链接使用当前任务已确认的 `origin`，不能使用 API 前缀，也不能写成未替换的地址模板。
- 批量新增、修改或删除时，每条已确认成功的数据都分别返回对应地址。
- 操作结果或上下文缺少生成地址所需的 `objId`、`dataId`、`listId` 或列表类型时，先按既有核验与消歧流程补齐；不能猜测 ID 或页面类型。

## 执行边界

- 菜单可见性不等于数据读写权限，以实际接口权限结果为准。
- 查询可以直接执行。新增和修改在目标、字段、条件或数量有歧义时先确认。用户当前请求已经明确指定删除目标和范围时，视为已确认，不再要求重复口头确认；否则先确认。CLI 的 `--confirm-delete` 仍必须由执行方传入相同 `dataId` 作为防误删校验。
- 写请求超时或响应不明确时先查询核验，不直接重试。
- 不调用任何 `/api/bs/` 接口，不创建菜单，不修改页面配置，不提升权限。
- 不输出或持久化 Cookie、ETEAMSID、敏感字段值或未经脱敏的完整响应。
