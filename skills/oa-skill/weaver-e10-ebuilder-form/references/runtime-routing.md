# List/NList 列表运行时路由

本文件是菜单解析完成后的内部入口。详细契约与可复用脚本都在本 skill 内：

- [table-config.md](table-config.md)：传统 List 初始化与配置。
- [nlist-config.md](nlist-config.md)：NList 页面与组件配置。
- [list-pagination.md](list-pagination.md)：List 分页与总数。
- [nlist-pagination.md](nlist-pagination.md)：NList 分页与总数。

本文件中的接口都位于 `/api/ebuilder/form/**`，因此使用主流程已经确定的 `apiPrefix`；独立部署时替换为 `/api/ebuilder{appId}`。该规则只适用于 `/form/**`。使用本 skill 的脚本时通过 `--api-prefix` 或当前进程的 `EBUILDER_API_PREFIX` 传入该值。

## 从 listId 获取 objId 与页面上下文

### pageType=SEARCH

调用：

```text
POST {origin}{apiPrefix}/form/list/listInit
Content-Type: application/json

{"listId":"{listId}"}
```

从成功响应 `data` 中读取字符串 `objid`/`objId`、`appId`、`name`、`conditionId` 以及列表配置所需的其他运行时上下文。`objId` 缺失时不得从其他 ID 推算。菜单 `pageType=SEARCH` 已确定此流程按 List 路由，不再调用其他视图接口二次确认。

### pageType=VIEWPORT

调用：

```text
GET {origin}{apiPrefix}/form/viewdesigner/viewPageInfo?pageId={menuPageId}&terminalType=PC&entranceType=RUN&runType=
```

菜单 `pageId` 在 VIEWPORT 场景中是请求 `viewPageInfo` 使用的 `menuPageId`，不作为后续数据列表的 `listId`。接口成功后直接读取 `data.page.comps[1].config`（`config` 可以是对象或 JSON 字符串）：

- 后续数据列表 `listId` 以 `config.ebListId` 为准。
- 表单对象 `objId` 以 `config.objId` 为准。

任一节点或 ID 缺失、格式无效时立即报告响应结构问题并停止。不扫描其他组件、不调用其他接口，也不通过 `dataset.id` 等字段猜测或回退。

取得唯一匹配组件及其 `objId` 后，保留组件配置作为 NList 分页和总数的运行时上下文。菜单 `pageType=VIEWPORT` 已确定此流程按 NList 路由，不再调用其他视图接口二次确认。

## 页面路由

- 菜单 `pageType=SEARCH`：读取 List 配置并调用 List 分页/总数接口。
- 菜单 `pageType=VIEWPORT`：读取 NList 配置并调用 NList 分页/总数接口。
- 常规 CRUD 和详情只使用已解析的 `objId`，不需要额外确认页面类型。
- 页面分页与 count 必须复用相同的 `tableuid`、过滤条件和运行时上下文；明细展开产生的重复行按原顺序保留。

## 按需枚举表单视图

只有用户明确询问“某个表单有哪些表格或数据列表视图”时，才使用已知 `objId` 调用：

```text
GET {origin}{apiPrefix}/form/viewlist/getViewlist/{objId}?objId={objId}
```

从响应中枚举该表单的视图，并只保留 `List` 和大小写不敏感的 `NList`。不要把该接口作为菜单解析、`objId` 获取、CRUD、详情、页面分页或总数的常规前置步骤。

禁止调用任何 `/api/bs/` 接口。
