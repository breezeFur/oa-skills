# 查询当前用户有权限的 eBuilder 菜单

仅在用户通过菜单名称或业务描述定位 eBuilder 页面时读取本文件。

## 接口来源

接口来自 `RuntimeViewListUsController#searchPermittedEbMenus`：

```text
POST {origin}/api/ebuilder/form/viewlist/searchPermittedEbMenus
Content-Type: application/json
```

菜单搜索固定使用无应用前缀的公共运行时路径，因为 `appId` 需要从搜索结果取得。选中菜单后再调用 `isIndependentDeploy` 确定该菜单后续请求的前缀；不要用应用前缀重复搜索菜单。

## 请求

Body 是关键词字符串数组，不是对象：

```json
[
  "客户档案",
  "华东"
]
```

约束：

- 传入 1 至 5 个去除操作词后的业务关键词。
- 不在请求中传 `employeeId`、`tenantKey` 或操作人；控制器从 `UserContext` 获取当前用户，并以其用户 ID 和租户调用菜单服务。
- 使用当前已认证会话。不要在 Query 或 Body 中追加凭证。

## 响应

Java 返回类型为：

```text
WeaResult<List<MenuSearchResultDto>>
```

已确认候选对象包含 `menuId`、`menuName`、`menuNameLabelId`、`refferName`、`pageType`、`pageId`、`combinationId`、`appId`、`navId` 和 `menuUrl`。处理响应时：

1. 先检查 HTTP 和外层 `WeaResult` 是否成功。
2. 把业务数据当作菜单候选数组。
3. `pageType` 大小写不敏感地只接受 `SEARCH` 和 `VIEWPORT`；其他类型、空值和未知值在匹配前过滤掉。
4. 候选必须具有非空 `pageId` 和 `appId`。SEARCH 的 `pageId` 是 `listId`；VIEWPORT 的 `pageId` 是请求 `viewPageInfo` 的 `menuPageId`，真实 `listId` 取该响应的 `data.page.comps[1].config.ebListId`。`appId` 是后续独立部署检查和表单上下文使用的应用 ID。
5. 保留每个候选的原始对象，使用 `menuName`、`refferName` 和其他实际返回的可读文本消歧。
6. `SEARCH` 表示表格候选并按 List 路由，`VIEWPORT` 表示数据列表候选并按 NList 路由；此映射用于候选过滤以及选择列表信息、分页和总数接口。
7. `menuId`、`pageId`、`combinationId`、`appId`、`navId` 等 Long 型值均须无损转换为字符串。若响应把 19 位 ID 输出为未加引号的 JSON 数字，读取原始响应文本并使用支持任意精度整数的解析器；不要先经过 JavaScript `Number` 或普通 `response.json()` 再转字符串。
8. 取得 SEARCH 的 `listId` 或 VIEWPORT 的 `menuPageId` 后，按本 skill 的 [List/NList 运行时路由](runtime-routing.md) 获取真实列表上下文和 `objId`。
9. 选中唯一菜单后保留该对象的 `menuUrl`，用于向用户返回列表入口；不得使用其他候选菜单的地址。
10. 整个流程不得调用任何 `/api/bs/` 接口。

## 匹配与重试

- 唯一清晰匹配：继续进入菜单目标解析。
- 多个合理匹配：向用户展示可区分的 `menuName`、`refferName`、`pageType`、`appId`、`pageId` 等实际返回信息，等待选择。
- 接口无结果、过滤后无候选或候选都不匹配：可依次去掉修饰词缩短查询，最多三次；不能扩展到用户未提及的业务对象。仍无匹配时明确告诉用户“没有找到合适的表格或数据列表菜单”，然后停止，不继续独立部署检查、列表查询或 CRUD。
- 401/403：当前会话失效或无权访问，改用同源已登录浏览器或请用户重新登录；不要输出失效凭证。
