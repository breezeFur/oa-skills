# 表格分页查询

仅在查询传统表格视图（`List`）的分页数据时读取本文件。所有 ID 按字符串处理，响应行按接口顺序原样保留。

## 运行上下文

先调用：

```text
POST /api/ebuilder/form/list/listInit
{"listId":"{tableId}"}
```

从 `data` 动态取得 `objid`、`appId`、表格名称、`tableType` 和配置的 `pageSize`。通常不需要用户额外提供表单 ID 或应用 ID。

数据请求默认携带 `passid={objId}&cid={objId}`。只有页面运行上下文明确给出了其他值时才传 `--pass-id` 或 `--cid`。

## 数据与总数接口

分页数据：

```text
POST /api/ebuilder/form/list/getListDatas?passid={objId}&cid={objId}
Content-Type: application/json
```

默认请求体：

```json
{
  "current": 1,
  "pageSize": 20,
  "requiredMatch": 1,
  "tableuid": "每次查询生成的随机值",
  "listId": "表格ID",
  "searchParamData": {
    "searchType": "2",
    "type": "and",
    "groupFields": {}
  },
  "isFollow": 0,
  "isShareToMe": 0,
  "filterCondition": {},
  "terminal": "PC"
}
```

`requiredMatch=1` 表示满足加载数据的前置条件；传 `0` 时后端会返回空数据。`pageSize` 最大为 200；命令行显式传入更大值时拒绝，列表配置值更大时按 200 执行。

查询全部页时，取得总数后按实际 `pageSize` 计算 `mainPageCount`。`mainPageCount >= 100` 时立即停止，不继续翻页，并请用户增加查询条件或缩小范围。不得通过重复查询单页绕过该限制。

真实总数必须另外调用：

```text
POST /api/ebuilder/form/list/getListDataCount?passid={objId}&cid={objId}
```

数据与总数请求必须复用完全相同的 `tableuid`、`listId` 和搜索条件。以 `getListDataCount.data.total` 为总数；不要使用 `getListDatas.data.total`，后者可能在已有当前页数据时仍返回 `0`。

## 搜索

后端会把 `searchParamData` 合并到顶层参数。常用结构为：

```json
{
  "searchType": "2",
  "type": "and",
  "groupFields": {},
  "commonSearchFields": {
    "field_{fieldId}": [
      {
        "field_{fieldId}": "AA",
        "field_{fieldId}_condition_type": "like"
      }
    ]
  }
}
```

简单字段应根据已保存搜索配置，把真实 `fieldId`、操作符和值写入上述 `commonSearchFields` 结构。

`eq`、`like`、`gt`、`between`、`inC`、`notInC`、`isNull`、`isNotNull` 等条件能否使用取决于字段组件。日期区间、浏览框、多选和组合关系不要猜测，只使用从真实配置或已确认规则构造的完整 `searchParamData`；结构化值保持其 JSON 类型。

`type` 控制多条件关系，通常为 `and` 或 `or`。`groupFields` 是分类搜索条件，不等同于普通高级搜索字段。

## 排序与其他参数

显式排序结构：

```json
[
  {"orderKey":"字段列的 orderKey 或 dataIndex","orderType":"desc"}
]
```

显式排序时传完整排序数组；未传排序时使用表格保存的排序配置。

`filterCondition` 使用完整条件对象。关注、共享给我、批量编辑、上下级列表、个性化视图等特殊场景只能传入已从真实页面上下文确认的额外请求体字段；调用时仍必须使用目标 `tableId`、本次分页参数、`requiredMatch=1` 和新生成的 `tableuid`。

## 分页输出口径

输出使用 `getListDatas.data.displayData` 作为视图行，并返回首个响应的 `columns`。关键字段：

| 字段 | 含义 |
| --- | --- |
| `pagination.mainRecordTotal` | `getListDataCount.data.total`。 |
| `pagination.mainPageCount` | 按总数和 `pageSize` 计算的页数。 |
| `pagination.returnedRowCount` | 本次各页返回的视图行数。 |
| `pagination.groupedEntryCount` | 分组表格对象的顶层项数；普通表格为 0。 |
| `pagination.distinctStableIdCount` | 不同 `id`、`form_data_id`、`ebrecord_rowkey` 或 `rowKey` 数量，仅供观察。 |
| `pages[].rows` | 每页 `displayData` 行。 |
| `rows` | 所有已查询页面按页码拼接后的行。 |

明细字段展开可能产生重复主记录 ID；必须保留接口顺序和重复行，不去重。分组表格的 `displayData` 可能是对象，处理时将其原样保留在 `pages[].groupedDisplayData`。

查询全部页必须从第 1 页开始，并按真实总数请求后续页。

## 安全与响应

- 域名只使用主流程已确认的 origin，没有默认域名。
- 登录态只使用当前同源浏览器会话或当前进程注入的 Cookie/ETEAMSID，不写入文件、命令输出或回答。
- 401/403 时请求新登录态，不回显旧值。
- HTTP、业务码或必要响应结构无效时可以报告接口失败；不要把合法的空页或重复明细行误判为分页失败。
