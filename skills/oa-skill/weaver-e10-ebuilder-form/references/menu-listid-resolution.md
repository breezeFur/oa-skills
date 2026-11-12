# 菜单到 listId 解析

本步骤明确禁止调用任何 `/api/bs/` 接口。

## 解析规则

对已经过关键词匹配且准备选用的菜单候选执行以下规则：

1. 大小写不敏感地规范化 `pageType`。
2. `pageType=SEARCH`：菜单表示表格，记录页面类别 `List`。
3. `pageType=VIEWPORT`：菜单表示数据列表，记录页面类别 `NList`。
4. 其他类型、空值或未知值：过滤该候选，不能继续解析。
5. 对合适候选，把 `pageId` 无损转换为字符串。`SEARCH` 时它就是 `listId`；`VIEWPORT` 时它只是请求 `viewPageInfo` 的 `menuPageId`，真正的 `listId` 随后从 `data.page.comps[1].config.ebListId` 读取。`appId` 同样无损转换为字符串。任一菜单字段为空、不是十进制 Long 型 ID 或已发生数值精度丢失时，该候选无效。

如果所有候选都被过滤、关键词没有匹配候选或有效候选无法唯一确定，明确告诉用户没有找到合适的表格或数据列表菜单。没有唯一目标时不得调用独立部署检查、列表查询或 CRUD 接口。

## 输出交接

解析成功后向后续步骤交接：

```json
{
  "status": "resolved",
  "appId": "<selectedMenu.appId>",
  "apiPrefix": "<resolved /api/ebuilder prefix>",
  "menuPageId": "<VIEWPORT 时为 selectedMenu.pageId，否则为空>",
  "listId": "<SEARCH 时为 selectedMenu.pageId；VIEWPORT 时为 comps[1].config.ebListId>",
  "menuPageType": "<SEARCH 或 VIEWPORT>",
  "listKind": "<List 或 NList>"
}
```

`apiPrefix` 必须来自此前的 `isIndependentDeploy` 检查，并且只用于后续 `/form/**` 接口。随后按 [List/NList 运行时路由](runtime-routing.md) 获取 `objId` 和页面运行时上下文。

`listKind` 直接由菜单 `pageType` 确定，并用于选择 List/NList 列表信息、分页和总数契约。不得从 URL、名称、`menuId`、`combinationId`、`navId` 或其他 ID 改猜 `listId`，也不调用 `getViewlist` 二次确认页面类型。VIEWPORT 只调用一次 `viewPageInfo`，直接使用 `data.page.comps[1].config.ebListId` 和 `config.objId`，不扫描其他组件或尝试其他发现接口。
