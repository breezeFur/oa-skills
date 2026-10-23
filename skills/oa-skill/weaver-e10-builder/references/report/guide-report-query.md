# 报表查询条件（高级搜索 / 筛选）

> 细则与完整字段表见 `query-condition-api-guide.md`；本条是入口与最容易踩的几点。

---

## 一、先分清「显示方式」与「条件本身」

报表页顶部的查询区有两种形态：

| 显示方式 | 落库 `queryType` | 用户在页面上看到 |
|---|---|---|
| 高级搜索 | `'["advance"]'` | 点开才展开的高级搜索面板 |
| 筛选 | `'["filter"]'` | 顶部平铺的筛选条 |

**必须写成 JSON 数组短码**。写成 `"advancedSearch"` 这种长码，服务端照收，
但设计器「显示方式」不勾选 —— 用户会以为配置丢了。

```bash
e10-cli report query check-echo <reportId> --app-id <appId>   # 体检
e10-cli report query fix-echo   <reportId> --app-id <appId>   # 修复
```

---

## 二、两条不可逾越的线

### 2.1 `updateQueryType` 是**报表级**批量覆盖

它会把入参写到**所有**条件上，不是只改你这一条。

所以：**只有用户明确点名要改显示方式时才调用**。不点名时 `report query type` 只回读、不写。

混着筛选和高级搜索的报表，被它跑一次就全拉平了。

### 2.2 绝不注入 `advancedSearchType`

写 `'openCondition'` 会把报表页查询区从「默认样式」改成「展开条件」——
这是**擅改用户的展示样式**。入参里没有这个键就不要写。

存量误注入的清理：`e10-cli report fix query-style <reportId> --app-id <appId> --apply`

---

## 三、保存一条条件

```bash
e10-cli report query save <reportId> --app-id <appId> --item item.json
e10-cli report query save <reportId> --app-id <appId> --item item.json --show-where 高级搜索
```

CLI 会自动补齐：

- **默认值三件套** `defaultValueType` / `defaultValue` / `type1DefaultValue` / `type2DefaultValue`
  （漏写会让设计器弹窗「默认值类型」=请选择、默认值区炸开、后面整段字段被顶出可视区）
- `filterParam` 默认对象
- `displayType`（按字段元数据推断：人员/部门→关联浏览，日期→区间，下拉→等于，其余→包含）
- 关联浏览的**富对象**（简写 `[{id:'HrmEmployeeComInfo'}]` 不足以让设计器「关联类型」回显）

**必须带 `id`**，否则服务端会当成新增，产生重复条件。

---

## 四、改完必查

```bash
e10-cli report query verify <reportId> --app-id <appId>          # Q1~Q10
e10-cli report query verify <reportId> --app-id <appId> --fix    # 顺带做幂等修复
```

`--fix` 只做三件安全事：清 `advancedSearchType`、补三件套、`queryType` 短码化。
**绝不新增或删除条件** —— 增删条件是用户的决定。

Q1~Q10 判据速查：

| 码 | 判据 |
|---|---|
| Q1 | `queryType` 是数组短码 |
| Q2 | `advancedSearchType` 必须为空 |
| Q3~Q5 | 默认值三件套齐全 |
| Q6 | 有 `id`、`asNameIndex` 唯一 |
| Q7 | `displayType=browser` 时 `browserType` 富对象非空 |
| Q8 | `filterParam` 存在（`showType` 缺只作提示） |
| Q9 | `showOrder` 建议为 0（仅提示） |
| Q10 | 报表级 `queryType` 不混杂 |

---

## 五、常见需求对照

| 用户说 | 怎么做 |
|---|---|
| 「加个按客户名查」 | `query save`，`displayType=text`，`relation=Contain` |
| 「按年月筛选」 | `displayType=date.ym`，`relation=between`，默认值给 `["{yearmonth:-0}",""]` |
| 「按部门筛选，默认本部门」 | `displayType=browser`（自动取富对象）+ 默认值走 custom |
| 「这条件放筛选条不放高级搜索」 | `--show-where 筛选`（**只在这一条上**；会触发报表级覆盖，要确认用户是整表统一） |
| 「条件顺序调一下」 | `report fix query-default --show-order 0` |
| 「默认值不对」 | `report fix query-default --set "年月=custom:[\"{yearmonth:-0}\",\"\"]" --apply` |
