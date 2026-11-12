# 数据列表分页查询

仅在查询数据列表视图的分页数据时读取本文件。所有 ID 按字符串处理，响应行按接口顺序原样保留。

## 运行上下文

先调用：

```text
GET /api/ebuilder/form/viewdesigner/viewPageInfo?pageId={hostPageId}&terminalType=PC&entranceType=RUN&runType=
```

从页面及目标 NList 组件动态取得：

| 参数 | 来源 |
| --- | --- |
| `pageAppId` | `data.page.appId`，不能由表单 ID 推算。 |
| `pageId` | 菜单返回并用于请求 `viewPageInfo` 的 `hostPageId/menuPageId`。 |
| `listId` | `data.page.comps[1].config.ebListId`。 |
| `compId` | `data.page.comps[1]` 的组件 ID。 |
| `formObjId` | `data.page.comps[1].config.objId`。 |
| `refPluginPackageId` | 组件或配置中的值；标准 NList 缺失时回退到 `933846626099339271`。 |
| `pageSize` | 命令行参数；未指定时使用 `config.pageSize`，再回退到 10；最大为 200。 |

一次 `viewPageInfo` 响应即可取得上述运行上下文。不要扫描其他组件、调用其他发现接口或要求菜单 `pageId` 等于内部 `ebListId`；`comps[1]` 的必要配置缺失时直接停止并报告。

## 数据与总数接口

分页数据：

```text
POST /api/ebuilder/form/eblist/getData
Content-Type: application/x-www-form-urlencoded
```

主要表单字段：`pageAppId`、`pageId`、`compId`、`pageNo`、`pageSize`、`tableuid`、`filter`、`fieldFilter`、`pageFilter`、`refPluginPackageId`、`customConfig`。

查询全部页时，取得总数后按实际 `pageSize` 计算 `mainPageCount`。`mainPageCount >= 100` 时立即停止，不继续翻页，并请用户增加查询条件或缩小范围。不得通过重复查询单页绕过该限制。命令行显式传入大于 200 的 `pageSize` 时拒绝；页面配置值更大时按 200 执行。

其中 `filter`、`fieldFilter`、`pageFilter` 是 JSON 序列化后的表单字符串。`customConfig` 是平台压缩算法生成的逗号分隔数字字符串，不是原始 JSON。编码时先把对象序列化为紧凑 ASCII JSON，再执行 LZW：单字符代码使用其 Unicode 码点，新增词条从 `65536` 递增；每次输出当前最长匹配词条代码，最后用逗号连接所有十进制代码。不得直接提交 JSON 文本。

总数：

```text
POST /api/ebuilder/form/eblist/getCount?passid={formObjId}
```

表单字段为 `tableuid`、`pageId`、`compId`、`refPluginPackageId`。`getData` 与 `getCount` 必须复用相同的 `tableuid`；改变账号、搜索条件或页面条件后生成新的 `tableuid`。

## 默认条件

没有显式过滤条件时，加入运行时配置条件：

```json
[
  {
    "conditionComId": "{compId}_filter_EXCLUDECACHE",
    "conditionType": "and",
    "dataType": "classification",
    "id": "{randomUuid}",
    "useConfig": true
  }
]
```

默认 `fieldFilter` 为 `{}`，默认 `pageFilter` 为：

```json
{"filter": {}, "filterIsNull": true, "esbFilter": []}
```

默认 `customConfig` 为 `{"superiorField":{"enable":false}}`，然后再编码。

## 搜索

自然语言搜索只能使用列表已经配置的 `commonFilters`、`quickFilters` 或 `groupFilters` 字段。根据该字段与 `config.dataset` 生成完整 `filterFields`，并追加 `{compId}_advance_EXCLUDECACHE` 条件。

文本搜索使用配置中的真实 `fieldId`、允许的操作符和值构造过滤项。日期区间、浏览框、多选、空值等复杂格式不要猜测，只能传入从真实运行请求或已确认规则构造的完整过滤数组。

## 分页输出口径

输出中的关键字段：

| 字段 | 含义 |
| --- | --- |
| `pagination.mainRecordTotal` | `getCount.data.total`，主表记录总数。 |
| `pagination.mainPageCount` | 按主记录总数和 `pageSize` 计算的页数。 |
| `pagination.returnedRowCount` | 本次查询返回的原始行数；明细展开后可大于主记录数。 |
| `pagination.distinctStableIdCount` | 当前结果中不同 `id`/`form_data_id` 的数量，仅供观察。 |
| `pages[].rows` | 每页原始行。 |
| `rows` | 所有已查询页面按页码拼接后的原始行。 |

同一主记录存在多条明细数据时，接口会返回多个相同 `id` 或 `form_data_id` 的扁平行。必须保留这些行，不去重，也不因 `mainRecordTotal`、`returnedRowCount`、`distinctStableIdCount` 不一致而主动报错。

查询全部页从第 1 页开始，按 `mainRecordTotal` 计算需要请求的主记录页数。只拼接原始行，不折叠明细数据。

## 安全与响应

- 域名只使用主流程已确认的 origin，没有默认域名。
- 登录态只使用当前同源浏览器会话或当前进程注入的 Cookie/ETEAMSID，不写入文件、命令输出或回答。
- 401/403 时请求新登录态，不回显旧值。
- HTTP、业务码或必要响应结构无效时可以报告接口失败；不要把合法的明细行重复误判为分页失败。
