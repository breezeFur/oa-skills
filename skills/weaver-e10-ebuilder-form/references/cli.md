# 统一表单数据 CLI

`scripts/form_data.py` 用一个进程完成菜单定位、部署检查、表单对象解析、字段获取、浏览字段转换、数据操作和结果回查。新增、修改、详情和删除优先使用该入口；列表分页仍使用对应的列表查询脚本。

## 运行时认证

CLI 只从当前进程读取认证信息，不接受把凭证放进 JSON、URL 或文件：

```powershell
$env:EBUILDER_ORIGIN = "https://oa.example.com"
$env:ETEAMSID = "<runtime token>"
```

也可以使用 `EBUILDER_COOKIE` 注入完整 Cookie header。命令结束后按任务的会话管理规则清理环境变量。

所有命令在 Windows 下强制使用 UTF-8 输出，不需要调用方额外修改控制台代码页。

## 从菜单直接操作

查询并输出可复用上下文：

```powershell
python scripts/form_data.py resolve --menu "专项考核竞赛"
```

菜单匹配规则：

- 只接受 `SEARCH` 和 `VIEWPORT` 类型，并要求实际返回 `pageId`、`appId`。
- 唯一清晰匹配才继续；同分候选会返回 `status=blocked`，此时使用接口输出的真实 `menuId` 再传 `--menu-id`，不能默认取第一条。
- 自动执行独立部署检查，并按列表类别取得 `objId`。独立部署前缀只应用于 `/form/**`；字段和选项继续使用公共 `/api/ebuilder/common/**`。
- VIEWPORT 菜单只用菜单 `pageId` 请求一次 `viewPageInfo`；随后直接采用 `data.page.comps[1].config.ebListId` 作为 `listId`、`config.objId` 作为 `objId`，不再探测其他组件或接口。
- 输出 `context` 中的 `appId`、`apiPrefix`、`hostPageId`、`listId`、`listKind`、`menuUrl` 和 `objId`，ID 始终保留为字符串。`hostPageId` 只用于 VIEWPORT 的页面请求，`listId` 才是后续列表业务 ID。

同一次新增或修改命令会在内存中复用这些上下文，不重复搜索菜单、检查部署或获取字段；后续独立命令还会使用下述短期缓存。

## 从页面 URL 直接操作

用户已经提供列表页面 URL 时使用 `--url`，跳过菜单搜索：

```powershell
python scripts/form_data.py resolve `
  --url "https://oa.example.com/sp/ebdfpage/list/123456789"

python scripts/form_data.py resolve `
  --url "https://oa.example.com/sp/ebdfpage/viewport/987654321"

python scripts/form_data.py resolve `
  --url "https://oa.example.com/ebdapp/view/123/VIEWPORT/456-789?cusMenuId=789"

python scripts/form_data.py resolve `
  --url "https://oa.example.com/sp/ebdfpage/viewport/123_456"
```

类型路由固定如下：

- 路径 `list` 或 `search`、参数值 `SEARCH`：表格，走 List 上下文与分页逻辑。
- 路径 `viewport`、参数值 `VIEWPORT` 或 `nlist`：数据列表，走 NList 页面与分页逻辑。
- `/ebdapp/view/{appId}/{SEARCH|VIEWPORT}/{pageId}-{menuId}`：拆出 `appId`、`pageId` 和 `menuId`。`SEARCH` 直接把 `pageId` 作为 `listId`；`VIEWPORT` 把它作为 `hostPageId`。
- `/sp/ebdfpage/{list|search|viewport}/{appId}_{pageId}`：下划线前是 `appId`，下划线后是页面 ID；`viewport` 的页面 ID 作为 `hostPageId` 请求 `viewPageInfo`。
- URL 路径没有直接类型时，也可使用同一 URL 中的 `pageType/listKind/viewType` 与 `pageId/listId`；类型和 ID 必须各自唯一且不冲突。
- 路径和查询参数中的 `appId`、`pageId/listId`、`menuId/cusMenuId` 必须一致；发现冲突立即停止。
- URL 没有 `appId` 时，只允许已识别类型对应的公共运行时接口做一次发现请求；取得 `appId` 后检查独立部署，不改跑另一类列表接口。
- 完整 URL 自动提供 `origin`；相对 URL 还需传 `--origin`。URL 必须与当前运行环境同源。

成功输出中的 `entryUrl` 保留用户提供的同源链接，并优先作为返回给用户的列表地址。`--url` 不能和 `--menu`、`--menu-id`、`--obj-id` 或 `--context-json` 同时使用。

## 快速复用

CLI 默认启用跨进程短期缓存：

- 菜单、部署和表单上下文缓存 30 分钟。
- 字段结构缓存 10 分钟。
- 缓存按站点和当前认证会话的单向摘要隔离；只保存上下文与字段元数据，不保存 Cookie、`ETEAMSID`、浏览查询结果或业务记录。
- 没有 `EBUILDER_COOKIE`/`ETEAMSID` 时缓存自动关闭；实际业务接口仍会正常校验认证和权限。

同一账号连续操作同一表单时，继续使用原来的 `--menu` 即可。缓存命中后会跳过菜单搜索、独立部署检查、表单对象解析和字段查询。需要获取最新配置时强制刷新：

```powershell
python scripts/form_data.py fields --menu "专项考核竞赛" --refresh
```

排查缓存问题时可对当前命令禁用缓存：

```powershell
python scripts/form_data.py detail `
  --menu "专项考核竞赛" `
  --data-id "{{dataId}}" `
  --no-cache
```

缓存目录默认位于系统临时目录。只有运行环境需要固定临时位置时才使用 `--cache-dir` 或 `EBUILDER_CACHE_DIR`，不要把缓存目录提交到 Skill 包中。

## 新增

`--values-json` 的键可以使用字段显示名称、字段数据键或字段 ID。普通文本和日期直接写入；选择字段按选项名称转换；人员、部门、分部、审批、文档和关联浏览字段按名称查询唯一 ID。

```powershell
python scripts/form_data.py add `
  --menu "专项考核竞赛" `
  --values-json '{"标题":"报名信息表-王泽慧","姓名":"王泽慧","报名流程":"自定义报表测试 20250310"}'
```

也可以从标准输入读取 JSON，避免复杂的命令行转义：

```powershell
'{"标题":"测试数据","姓名":"王泽慧"}' |
  python scripts/form_data.py add --menu "专项考核竞赛" --values-json -
```

行为约束：

- 字段定义只获取一次；浏览字段和选择字段复用同一份内存数据。
- 多个互不依赖的浏览字段并行查询，默认最多 4 个，可用 `--workers` 调整，最大 8 个。
- 浏览名称必须唯一；重名或未查到时返回 `status=blocked`，不执行写请求。
- 请求固定启用权限校验，CLI 不提供关闭权限校验的参数。
- 固定使用 `fieldNoFindIgnore=false`，防止字段名错误被静默忽略。
- 写请求业务状态失败时保留内层真实 `message`，退出且不重试。
- 新增成功必须取得 `dataIds`，随后逐条调用 `getDataById` 回查；不使用 `getAllData` 验证。

## 修改和详情

修改按唯一 `dataId` 执行，并用 `getDataById` 回查同一条数据：

```powershell
python scripts/form_data.py update `
  --obj-id "{{objId}}" `
  --app-id "{{appId}}" `
  --data-id "{{dataId}}" `
  --values-json '{"标题":"修改后的标题"}'
```

详情：

```powershell
python scripts/form_data.py detail `
  --obj-id "{{objId}}" `
  --app-id "{{appId}}" `
  --data-id "{{dataId}}"
```

如果已经有经核验的 `apiPrefix`，可用 `--api-prefix` 代替 `--app-id`；否则 CLI 会根据 `appId` 执行独立部署检查，不能猜测前缀。

`apiPrefix` 只控制 `/api/ebuilder/form/**` 路由。即使当前应用是独立部署，字段定义仍请求 `/api/ebuilder/common/ds/fields`，字段选项仍请求 `/api/ebuilder/common/ds/options`。

## 删除

删除要求 `--confirm-delete` 传入完全相同的 `dataId`：

```powershell
python scripts/form_data.py delete `
  --obj-id "{{objId}}" `
  --app-id "{{appId}}" `
  --data-id "{{dataId}}" `
  --confirm-delete "{{dataId}}"
```

用户当前请求已经明确指定删除目标和范围时，不需要再让用户重复确认；执行方直接把相同 `dataId` 传给 `--confirm-delete`。用户没有明确目标或范围时才先询问。确认值不一致时不会发送请求，成功结果返回带 `fromRecycle=1` 的回收站数据地址。

## 输出和退出码

CLI 只输出 UTF-8 JSON：

```json
{
  "status": "success",
  "operation": "add",
  "context": {},
  "result": {
    "status": true,
    "message": "success",
    "dataIds": ["{{dataId}}"],
    "records": [
      {
        "dataId": "{{dataId}}",
        "verified": true,
        "url": "{{dataUrl}}"
      }
    ]
  },
  "cache": {
    "enabled": true,
    "refresh": false,
    "contextTtlSeconds": 1800,
    "fieldsTtlSeconds": 600,
    "hits": 2,
    "misses": 0,
    "writes": 0
  },
  "performance": {
    "totalMs": 1234.5,
    "requestCount": 8,
    "stages": [],
    "requests": []
  }
}
```

退出码：

| 退出码 | 含义 |
|---|---|
| `0` | 操作和必要回查成功 |
| `1` | 网络、认证、响应格式或运行错误 |
| `2` | 菜单、字段、选项或浏览数据需要消歧 |
| `3` | 服务端明确返回业务失败，例如无创建权限 |

`performance.requests` 包含请求阶段、方法、同源路径、HTTP 状态和客户端耗时，不包含 Cookie、ETEAMSID、请求体或完整响应。写接口会请求服务端 `printCost`；服务端实际返回时保留在 `result.serverCost`。

## 旧脚本兼容

- 只查询一个浏览字段时仍可使用 `query_browser_field.py`。
- 查询列表分页继续使用 `query_list_data.py` 或 `query_nlist_data.py`。
- 查询表格或数据列表配置继续使用各自配置脚本。

这些脚本与统一 CLI 共用 `ebuilder_http.py` 的 origin、认证和 UTF-8 规则。统一 CLI 的连接复用和并行浏览查询在单次进程内生效；上下文与字段结构可通过短期缓存跨独立命令复用。旧脚本不会读取该缓存。
