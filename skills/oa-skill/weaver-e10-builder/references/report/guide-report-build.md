# 新建报表（声明式一步落库）

> 命令：`e10-cli report build --spec <spec.json>` · 结构详解见 `spec-build-schema.md`
> 交付形态：给出设计器地址即完成，详见 `report-delivery-contract.md`

---

## 一、一句话说清

报表 = **一张表单当数据源** + **若干列绑定到该表单的字段** + 可选布局/查询条件/权限。

`report build` 一次调用跑完：定源 → 字段预检 → 建表 → 挂数据集 → 落库 → 回读，中途不留空壳。

```bash
e10-cli report build --spec spec.json           # 正式建表
e10-cli report build --spec spec.json --dry-run # 只看定源与字段绑定，不写任何数据
```

---

## 二、最小 spec

```json
{
  "appId": "1315401436173942786",
  "name": "销售明细报表",
  "form": "销售订单",
  "columns": [
    { "title": "客户名称", "width": 160 },
    { "title": "合同金额", "width": 120, "format": "货币" },
    { "title": "签订日期", "width": 140, "format": "短日期" }
  ]
}
```

| 键 | 说明 |
|---|---|
| `appId` | 应用 ID（必填） |
| `name` | 报表名。**写入即最终名**，不留 `__build_*`、不落库后改名 |
| `form` / `sourceId` | 表单名或表单 id。**两个都不给就是没指明表**，会停下让你选 |
| `columns[]` | 列定义。`title` 同时是**字段匹配键** |
| `layout` | `{ title, freezeRows, showLocation }` |
| `style` / `titleStyle` / `headerStyle` / `bodyStyle` | 分层样式；不给就是默认表头样式 |

列的可选项：`width`、`format`（`货币`/`短日期`/`百分比`…，见 `cell-config-echo-guide.md`）、`formula`（公式列不参与字段绑定）、`groupType`（日期分组）、`rule`（条件格式，见 `condition-format-guide.md`）、`field` / `fieldName`（显式指定字段）。

---

## 三、两处「必须问用户」的门禁

这是本能力最重要的两条规则。两处都**不建表、不回退、不猜**。

### 规则 B · 表没指明或不是完全精准匹配

触发：需求没写表名；或应用内检索是模糊命中 / 同名多条 / 未命中。

行为：退出码 **3**，列出 `candidates[]`，**不建任何报表**。

```bash
e10-cli report find <appId> --list             # 列应用内全部表单
e10-cli report find <appId> "销售订单"          # 精确/模糊查找
e10-cli report build --spec spec.json --form-confirmed --source-id <id>   # 用户确认后复跑
```

### 规则 A · 列字段没有精确匹配

触发：列标题与该表单字段的**显示名**对不上（归一化后仍不等），且没有显式指定。

行为：退出码 **4**，列出 `unmatched[]` + `allFields[]`（全量可选字段），**不建报表**（若已建到一半会删掉）。

**绝对禁止**用系统字段（`name`/`id`/`create_time`…）兜底。历史事故：需求写「姓名」，被静默绑到系统字段 `name`（真实显示名是「标题」），报表能用但数据全错，用户毫不知情。

三种收场方式：

```bash
# 1) 从候选里挑，写进 spec.fieldMap
"fieldMap": { "党组织": "所属党委" }

# 2) 文案与字段真实显示名不同但确实有意如此
e10-cli report build --spec spec.json --field-confirmed "列名A,列名B"
e10-cli report build --spec spec.json --field-confirmed        # 不带值 = 全部确认

# 3) 先看清楚再决定
e10-cli report build --spec spec.json --dry-run
```

---

## 四、退出码

| 码 | 含义 |
|---|---|
| 0 | 成功，已输出设计器地址 |
| 2 | 成功但有警告（显示名不一致 / tableName 缺失 / 重复数据集挂载） |
| 3 | 规则 B：需要用户指定表，**未建表** |
| 4 | 规则 A：需要用户指定字段，**未建表或已删掉未完成的报表** |
| 1 | 失败 |

---

## 五、建完之后

```bash
e10-cli report read <reportId> --fields        # 回读字段记录
e10-cli report verify bind <reportId> --app-id <appId>   # 字段绑定体检
e10-cli report verify all  <reportId> --app-id <appId>   # 综合自检
```

**搭表不要求渲染。** 落库成功、字段绑定正确就是交付完成。全量渲染超过 5 万格必然失败且空耗几十秒，
真要评估用 `e10-cli report verify limit <reportId>` 做算术预检（见 `report-designer-feature-map.md`）。

---

## 六、不要做的事

- ❌ 建 `__build_*` / `__probe_*` 空壳试探 —— 字段预检不需要报表就能做
- ❌ 落库后再改报表名 —— 直接用目标名建
- ❌ 跨报表复用 `datasetId` —— 数据集不能跨报表引用
- ❌ 同一张表挂两次 —— 左侧会出现重复数据源分组；`report dataset list` 可核对
- ❌ 一上来拉全系统表单分组树 —— 用户给了应用就在应用内找（`report find`）

---

## 相关文档

- `spec-build-schema.md` —— spec 全字段
- `add-dataset-registration-guide.md` —— 数据集注册契约
- `field-bind-exact-match-guide.md` —— 字段精确绑定细则
- `dataset-table-field-contract-guide.md` —— `tableName` 与字段三件套
- `api-report-build-fast-path.md` —— 接口层逐步流程
- `report-create-modes-guide.md` —— 空白 / 模板 / 快速构建三种建法
