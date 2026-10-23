# 日期区间查询条件选项参考（已验证样例）

> **来源**：报表 `1304979556231593985`（EBU 经营数据统计）· 查询条件「入职时间」 
> **完整规范**：`query-condition-api-guide.md`（条件字段形态、系统参数默认值、验证清单） 
> **filterParam 快照**：`outputs/join_date_filterparam.json`（运行 `本地工作目录` 可重新导出） 
> **代码实现**：`本地工作目录` → `_default_date_filter_param()`

---

## 一、快捷选项（filterParam.dataOptions · 21 项）

设计器 save 后的正确形态：

| 字段 | 正确值 |
|------|--------|
| `selectOptions` | **`[]`** |
| `filterParam.enableOption` | `true` |
| `filterParam.isTile` | `true` |
| `filterParam.dataOptions` | **21 行**（下表） |
| `filterParam.optionTile` | **`{}`** |
| `filterParam.dateSelectDefaultValue` | **`""`** |

**勿用旧格式**：15 项数字码（`"9"`、`"{yesterday}"`）+ 9 项 `selectOptions` + 填满 `optionTile` → 齿轮菜单常只剩「自定义」。

---

## 二、dataOptions catalog（id = selectValue）

| selectKey | selectValue / id |
|-----------|------------------|
| 近三天 | day3 |
| 近五天 | day5 |
| 近七天 | day7 |
| 今天 | today |
| 昨天 | yesterday |
| 明天 | tomorrow |
| 本周 | thisWeek |
| 上一周 | lastWeek |
| 下一周 | nextWeek |
| 本月 | thisMonth |
| 上一月 | lastMonth |
| 下一月 | nextMonth |
| 本季度 | thisSeason |
| 上一季 | lastSeason |
| 下一季 | nextSeason |
| 今年 | thisYear |
| 上半年 | firstHalfYear |
| 下半年 | nextHalfYear |
| 去年 | lastYear |
| 明年 | nextYear |
| 自定义 | custom |

---

## 三、系统参数默认值（与快捷选项独立）

默认值写在顶层 **`defaultValueType` + `defaultValue`**，不是 `dateSelectDefaultValue`。

| 场景 | defaultValueType | defaultValue | handleDefaultValue 示例 |
|------|------------------|--------------|-------------------------|
| 本月 | `custom` | `["{thismonth}",""]` | `["2026-08-01,2026-08-31",""]` |
| 今天 | `custom` | `["{date}","{date}"]` | `["2026-08-19","2026-08-19"]` |

`displayType`：`yyyy-MM-dd` 字段 → `date.ymd`；`yyyy-MM` 字段 → `date.ym`。

---

## 四、filterParam 完整示例

```json
{
 "isTile": true,
 "enableOption": true,
 "showType": "tile",
 "multiple": false,
 "dataOptions": [ { "selectKey": "本月", "selectValue": "thisMonth", "id": "thisMonth" } ],
 "optionTile": {},
 "dateSelectDefaultValue": ""
}
```

（`dataOptions` 须写满 21 项，此处省略。）

---

## 五、Agent checklist

1. 加载本文 + `query-condition-api-guide.md`
2. `_default_date_filter_param()` + `defaultValueType: custom` + 系统参数
3. 校验：21 项 dataOptions、`selectOptions=[]`、`handleDefaultValue` 非空
4. 设计器：齿轮 21 项 + 默认筛选项生效

---

## 六、相关文件

| 文件 | 用途 |
|------|------|
| `query-condition-api-guide.md` | 查询条件总规范 |
| `outputs/join_date_filterparam.json` | filterParam 参考样本 |
| `本地工作目录` | 生成/修复 |
| `本地工作目录` | 扫描导出 |
