# 多数据源报表（跨数据集）· spec 写法与落地

> **命令**：`e10-cli report build --spec <spec.json>`
> **校验**：`e10-cli report verify parents <reportId> --app-id <id>`
> **证明跑得通**：`e10-cli report render <reportId> --app-id <id>`
> 配套规则见 `cross-dataset-filter-guide.md`（fieldKey 写法）、
> `datasource-selection-and-parent-filter-guide.md`（区域与入口格）。

---

## 一、什么时候需要多数据源

**先问能不能不加。** 主表上已有可展示字段时，不要为了"好看/完整"再挂一张表回显名称
（`datasource-selection-and-parent-filter-guide.md` §一）。只有主表确实取不到该字段、
且业务必须跨表关联时才加第二源。

典型：主从明细（客户 × 该客户的订单）、维度下钻（合同 × 供应商主数据）。

---

## 二、spec 写法

```json
{
  "appId": "1316387504760741888",
  "name": "客户订单综合分析",
  "formConfirmed": true,
  "sources": [
    { "key": "customer", "form": "客户信息表" },
    { "key": "order", "form": "销售订单表",
      "link": { "parent": "customer", "parentField": "客户名称", "childField": "客户名称",
                "type": "Equals" } }
  ],
  "layout": { "title": "客户订单综合分析", "freezeRows": 1, "showLocation": "left" },
  "columns": [
    { "source": "customer", "title": "客户名称", "field": "客户名称", "width": 170 },
    { "source": "customer", "title": "客户等级", "field": "客户等级", "width": 120 },
    { "source": "order", "title": "订单编号", "field": "订单编号", "width": 150 },
    { "source": "order", "title": "销售金额", "field": "销售金额", "width": 150, "format": "huobi" }
  ]
}
```

| 键 | 说明 |
|---|---|
| `sources[0]` | **父源**。它的列区域是报表的根，不写 `link` |
| `sources[].key` | spec 内引用名，`columns[].source` 用它；必须唯一 |
| `sources[].form` / `sourceId` | 与单源 spec 同义；`sourceId` 是已确认的表单 ID |
| `sources[].sourceType/Group/Name` | 数据集注册契约，普通应用留空即可（默认 `LOGIC` + `weaver-ebuilder-form-service`） |
| `sources[].link.parent` | 挂在哪个源上；**必须是左边紧邻的那个源** |
| `link.parentField` / `childField` | 关联字段，写**显示名或 `field_xxx`**，各自在**本方**表里解析 |
| `link.type` | 比较方式，TitleCase 枚举，默认 `Equals` |
| `columns[].source` | 该列属于哪个源；**缺省 = 父源** |

**不写 `sources` 时行为与单源报表完全一致** —— 老 spec 不需要改。

---

## 三、布局是怎么排的

平台侧"多数据集"的机制是：字段按来源排成**连续区域**，区域入口格挂到左边区域的父格上。

```
┌─ 父源区域 ────────┐┌─ 子源区域（连续） ──────────┐
│ 客户名称 客户等级 ││ 订单编号  销售金额  订单状态 │
│   ↑               ││   ↑ 入口格（挂父格筛选）     │
│   └── 默认父格     ││     其余格：普通链式父格     │
└───────────────────┘└─────────────────────────────┘
```

CLI 按 `columns[]` 的顺序自动切区域：

- **父源区域**：整行首列默认父格，其余逐列链式；
- **子源区域**：**只有入口格**（该区域第一列）写 `subordination` + `leftFilterField` 并指向父区域，
  其余格一律普通链式父格 —— **不逐格重复配**（逐格重复会让预览异常）。

### 关键：关联键不必是入口格自己的字段

文档示例里入口格指向「联系方式」，而关联字段是「供应商名称」。**锚点看位置，关联键看字段引用**，
两者互不相干。所以 `link.parentField`/`childField` 只要能在那张表里唯一定位到字段即可，
**不需要**把关联字段单独排成一列。

### 当前限制

每个**子源只能占一段**连续区域（父源可以多段）。平台允许一段以上（每段各配一次入口筛选），
CLI 暂不支持——需要时请在设计器里手工补，或把该源的列排到一起。

---

## 四、落库时 CLI 自动做的事

1. 逐个源走**规则 B**（定源）与**规则 A**（字段精确绑定），任一不通过都不建表；
2. 逐个源挂数据集，并断言 N 个 datasetId 互不相同（两个源指向同一张表会退化成自引用，直接报错）；
3. 按 `link` 解析关联字段（显示名歧义时报错，不取首条）；
4. 组表时把 `subordination` / `leftFilterField` 写到入口格；
5. **双保存**：先 `saveReportDevInfo`，再 `saveReportWithCacheConfig`；
6. 跨源报表**自动关预聚合**（`dataPreAgg=false`）—— 父格筛选参与取数，预聚合结果不成立，
   这是必然代价不是配置错误。设计器「预聚合」开关会显示为关闭。

> `saveReportWithCacheConfig` 并非所有站点都有。缺该路由时 CLI 降级为警告，
> 报表本身仍然建成；此时跨源缓存的生效情况需在设计器里手工保存一次确认。

---

## 五、验证

```bash
e10-cli report verify parents <reportId> --app-id <appId>   # 结构合规
e10-cli report render <reportId> --app-id <appId>           # 真跑一遍看行数
```

`verify parents` 检查：入口格唯一、同区域其余格留空、`subordination[1] === leftFilterField[0].currentField`、
`id === currentField`、`type` 在白名单内、fieldKey 三段式且指向正确的数据集、锚点落在真实的父区域单元格上。

**`render` 是唯一能证明关联真的生效的手段** —— 结构对不代表数据对。判读方式：

- 父源 N 行、子表 M 条明细 → 展开后数据行数应 = 子表匹配到的明细数；
- 用 `--dump <file>` 把 workbook 写出来，逐行看父源字段是否只在该组第一行出现、后续行留空。

---

## 六、常见报错与处置

| 报错 | 含义 | 处置 |
|---|---|---|
| `源「b」的列排在源「a」后面，但没写 link` | 子源没声明怎么关联 | 补 `link` |
| `link.parent=「a」，但它左边紧邻的区域来自「b」` | 关联只能指向左边紧邻区域 | 调整列顺序或改 `link.parent` |
| `源「b」被拆成了 N 段连续区域` | 子源列没排在一起 | 把该源的列排到一起 |
| `源「x」与「y」解析到同一张表单` | 两个源指同一张表 | 改为单源布局 |
| `源「x」的父格关联字段「…」匹配到 N 个字段` | 显示名歧义 | 改用 `field_xxx` 精确指定 |
| `带缓存保存未成功` | 站点缺 `saveReportWithCacheConfig` 路由 | 见 §四 说明；在设计器里手工保存一次 |

---

## 七、相关文档

| 文档 | 关系 |
|---|---|
| `cross-dataset-filter-guide.md` | fieldKey 三段式、`id=currentField`、filter 结构权威说明 |
| `datasource-selection-and-parent-filter-guide.md` | 区域/入口格规则、少挂源的判定顺序 |
| `spec-build-schema.md` | spec 全量字段 |
| `preaggregate-auto-disable-guide.md` | 为什么跨源必须关预聚合 |
| `api-report-build-fast-path.md` | 双保存顺序与禁忌 |
