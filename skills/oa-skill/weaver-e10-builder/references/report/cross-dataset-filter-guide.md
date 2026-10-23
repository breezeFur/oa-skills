# 跨数据集筛选配置指南（左父格筛选 & 自定义筛选）

> **适用场景**：单元格字段与左/上父格字段来自不同数据集；或单元格需按固定条件过滤（如核算机构排除、年度参数）。
>
> **已验证平台**：e-Builder EDC 报表设计器（2026-08，EBU 经营数据统计报表 `1304979556231593985`）。
>
> **与「左侧数据集筛选」区分**：整表/行级预过滤走 **`queryInfoSave`**（`conditionData`），见 **`dataset-query-filter-guide.md`**。本文档面向 **subordination / leftFilterField / customFilterField / datasetFilter**（单元格与多实例副本级）。

## 一、核心结论（必读）

设计器下拉框**按 `fieldKey` 匹配字段**，不是按显示名（`text`）或裸系统名（`field_xxx`）。

**fieldKey 格式**（三段式，用 `.` 连接）：

```
{dataSetId}.{sourceId}.{fieldName}
```

| 段 | 含义 | 示例 |
|----|------|------|
| dataSetId | 报表内数据集 ID（`ds[].id`） | `1304979556231593994` |
| sourceId | 数据源/逻辑表 ID（`ds[].sourceId`） | `1299763447342276611` |
| fieldName | 字段系统名（`fields[].name`） | `field_1299763447342276617` |

**症状对照**：

| 现象 | 常见原因 |
|------|----------|
| API 保存成功，设计器筛选区下拉为空白 | `parentField`/`currentField` 用了显示名或裸 `field_xxx` |
| 筛选条件不生效 | 未配置 `subordination` 或父格坐标错误 |
| 类型选了但无效 | `type` 用了 `eq`/`uncontains` 而非平台枚举 |

---

## 二、左父格筛选（leftFilterField）

### 2.1 何时需要

当前单元格 `dataSetId` ≠ 左父格单元格 `dataSetId` 时，必须同时配置：

1. **subordination** — VLOOKUP 式字段映射（设计器「从属关系」）
2. **leftFilterField** — 左父格筛选条件（设计器「左父格筛选」）

两者字段引用**都必须使用 fieldKey**。

### 2.1.1 连续同源区域：只配入口格（强制）

> 完整规则见 **`datasource-selection-and-parent-filter-guide.md` §二**（含 **§2.5 关联键：需求优先 · 推断须用户确认**）。

若连续一片单元格**全部来自同一数据源**，且整体挂在另一数据源父格下：

- **仅该区域第一个字段**：自定义父格指向异源父格 + 配置 `subordination` / `leftFilterField`
- **同区域其余字段**：父格用**默认**，**不要**逐格再指异源父格、**不要**重复配父格筛选
- **关联字段**：需求已写明则按需求；未写明则字段匹配推断后 **必须提示用户确认**（CLI：`e10-cli report join-suggest`）

禁止对连续同源列/行「每个字段都配一遍跨源父格筛选」。

### 2.2 数据结构

**workbook 内**（`style.cellType` 上）：

```json
{
 "subordination": [
 "1304979556231593994.1299763447342276611.field_1299763447342276617",
 "1304979560546713602.1299789221321891842.field_1299789221321891843"
 ],
 "leftFilterField": [
 {
 "parentField": "1304979556231593994.1299763447342276611.field_1299763447342276617",
 "currentField": "1304979560546713602.1299789221321891842.field_1299789221321891843",
 "type": "Equals",
 "id": "1304979560546713602.1299789221321891842.field_1299789221321891843"
 }
 ]
}
```

| 字段 | 说明 |
|------|------|
| subordination[0] | 父格（左父格）字段 fieldKey |
| subordination[1] | 当前单元格字段 fieldKey |
| parentField | 同 subordination[0] |
| currentField | 同 subordination[1] |
| type | 匹配关系，跨数据集关联通常用 `Equals` |
| id | **必须等于 currentField**（设计器回显关键） |

**save 后 fields 表**（`getReportDevInfo`）：`leftFilterField`、`subordination` 出现在字段记录顶层（JSON 字符串或数组），不在 `style` 内。

### 2.3 左父格筛选识别与写入（2026-09 eteams · 必遵）

设计器 F2「左父格筛选」下拉按 **fieldKey 注册表** 解析标签；下列写法会导致回显 **`undefined`** 或下拉空白：

| 错误写法 | 现象 | 正确写法 |
|----------|------|----------|
| `parentField: "...field_5"`（截断/臆造字段名） | 父格关联字段显示 undefined | 完整 `{dataSetId}.{sourceId}.field_4746632256695654785` |
| `id: "c43a895a664140dc"`（随机 UUID） | 筛选行无法匹配字段 | **`id` 必须等于 `currentField`（完整 fieldKey）** |
| `subordination: ["",""]` | 从属关系丢失 | `[parentField, currentField]` 与 leftFilter 同步 |
| 仅改 fields 表、workbook 内 `style.cellType` 未同步 | 保存后字段绑定丢失 | workbook + fields **双保存**（见 §4.1） |

**父格坐标（leftX / leftY）**：须指向布局上**真实的左父格单元格**（0-based 列 x、行 y），不能机械套用 `leftY = col - 1`。

**纵向堆叠多数据集示例**（进销存-供应商 + 采购进货单，同列 B）：

- 供应商字段：y=0~4（供应商等级 → 联系方式），根格 y=0 左父格无
- 采购字段：y=5~9，`leftX=1`, **`leftY=4`**（指向 E2「联系方式」所在行）
- 关联：`parentField` = 供应商.供应商名称；`currentField` = 进货单.供应商

**生成 helper**（Skill 内置）：

```python
from scripts.left_filter_builder import build_cross_dataset_filter

lf, sub = build_cross_dataset_filter(
 ds_supplier, src_supplier, "field_4746632256695654785",
 ds_purchase, src_purchase, "field_4746633026496455388",
)
# lf[0]["id"] == lf[0]["currentField"] # 必须
```

**保存后验证**（`getReportDevInfo` 抽检首个跨表格，如进货单编号 y=5）：

```bash
# parentField / currentField 各含两个 '.' 段；subordination 与 leftFilterField 一致
```

参考实现：`本地工作目录`、`restore_and_fix_left_filter.js`。

### 2.4 业务映射示例（EBU 报表）

| 子表类型 | 父格字段 | 当前字段 | 含义 |
|----------|----------|----------|------|
| 直销合同列 | EBU团队·责任人 | 直销合同业绩表·销售经理 | 按责任人关联合同 |
| 收款明细列 | EBU团队·责任人 | 收款明细表·销售经理 | 按责任人关联收款 |

根格（如 F3 责任人）设置 `leftX=-1, leftY=-1`；子格/公式格 `leftX=2, leftY=5` 指向根格列（0-based：行 2、列 5）。

### 2.5 Python 辅助函数

```python
def field_key_ref(ds_id, src_id, field):
 return f"{ds_id}.{src_id}.{field['name']}"

def make_subordination(p_ds_id, p_src_id, p_field, c_ds_id, c_src_id, c_field):
 return [
 field_key_ref(p_ds_id, p_src_id, p_field),
 field_key_ref(c_ds_id, c_src_id, c_field),
 ]

def make_left_filter(p_ds_id, p_src_id, p_field, c_ds_id, c_src_id, c_field):
 ck = field_key_ref(c_ds_id, c_src_id, c_field)
 pk = field_key_ref(p_ds_id, p_src_id, p_field)
 return [{"parentField": pk, "currentField": ck, "type": "Equals", "id": ck}]
```

参考实现：`本地工作目录`。

---

## 三、单元格自定义筛选（customFilterField）

### 3.1 与数据集级筛选的区别

| 层级 | 配置位置 | 用途 |
|------|----------|------|
| **单元格 customFilterField** | `style.cellType.customFilterField` | 该单元格取数时的行级条件 |
| **数据集 datasetFilter** | `saveReportWithCacheConfig` 的 `datasetFilter` 参数 | 整个数据集的基础过滤 |

单元格自定义筛选同样必须使用 **fieldKey** 作为 `currentField` 和 `id`。

### 3.2 数据结构

```json
{
 "customFilterField": [
 {
 "currentField": "1304979560546713602.1299789221321891842.field_1299789221321891843",
 "type": "NotContain",
 "value": "某核算机构",
 "id": "1304979560546713602.1299789221321891842.field_1299789221321891843"
 },
 {
 "currentField": "1304979560546713602.1299789221321891842.field_1299789221321891844",
 "type": "Null",
 "value": "",
 "id": "1304979560546713602.1299789221321891842.field_1299789221321891844"
 }
 ]
}
```

### 3.3 type 枚举（平台值）

**必须使用下列枚举**，不要用简写：

| 平台 type | 错误写法（无效） | 说明 |
|-----------|------------------|------|
| `Equals` | `eq` | 等于 |
| `NotContain` | `uncontains` | 不包含 |
| `Null` | `empty` | 为空 |
| `NotNull` | `nempty` | 不为空 |
| `Contain` | — | 包含 |
| `Include` | — | 属于（多值逗号分隔） |

完整枚举见 `report-data-model.md` §2.5。

### 3.4 需求文档到配置的映射

需求 Excel 中常见写法 → API 配置：

```
核算机构 不包含 机构A,机构B → type: NotContain, value: 机构A（多条则多个 filter 项）
核算机构 为空 → type: Null, value: ""
年度={year} → type: Equals, value: "{year}"（系统参数原样保留）
```

```python
FILTER_TYPE_MAP = {
 "eq": "Equals", "uncontains": "NotContain",
 "empty": "Null", "nempty": "NotNull",
}
```

---

## 四、保存与验证流程

### 4.1 双保存（API 脚本必做）

1. `POST /api/bs/edc/report/saveReportWithCacheConfig` — workbook + dataset + datasetFilter
2. `POST /api/bs/edc/report/saveReportDevInfo` — 同 workbook（需带 `designKey`）

仅保存其一可能导致设计器回显异常或筛选丢失。

### 4.2 验证清单

保存后调用 `getReportDevInfo`，检查 L3（或目标数据行）字段：

- [ ] `subordination` 为两段 fieldKey，非 `["",""]`
- [ ] `leftFilterField` 非空，且 `parentField`/`currentField` 含两个 `.`
- [ ] `customFilterField`（若有）的 `type` 为平台枚举
- [ ] 设计器打开后左父格筛选、自定义筛选下拉**有选中项**（非空白）

### 4.3 配置校验脚本

```bash
python e10-cli report validate <配置文件路径>
```

脚本会检查 fieldKey 格式、type 枚举、customFilterField 结构。

---

## 五、常见错误定位

### 5.1 设计器筛选下拉空白

1. 确认 `parentField`/`currentField`/`id` 均为 `{dataSetId}.{sourceId}.{fieldName}`
2. 确认 `dataSetId` 是报表内数据集 ID，不是 appId / reportId
3. 确认 `fieldName` 来自 `ds/fields` 接口的 `name` 字段
4. 双保存后刷新设计器

### 5.2 父格循环引用

子格 `leftY` 指向错误列会导致父格环（如根格在 F 列却设 `leftY=6` 指向 G）。根格用 `leftX=-1, leftY=-1`。

### 5.3 style 与 fields 表不一致

`getAllSheets` 的 `dtTable` 可能为空；**以 `getReportDevInfo.fields` 为准**。workbook 内筛选写在 `style.cellType`，平台解析后同步到 fields 表。

---

## 六、生成配置时的 Agent 检查项

生成或修改含跨数据集字段的报表时，Agent 必须：

1. 从 `ds/list` + `ds/fields` 获取真实 `dataSetId`、`sourceId`、`field.name`
2. 对每个跨数据集列生成 `subordination` + `leftFilterField`（fieldKey + `id`）
3. 对需求中的过滤条件生成 `customFilterField`（fieldKey + 平台 type）
4. 含 Formula 单元格时遵守 `formula-cell-api-guide.md`（cellText 无前导 `=`）
5. 运行 `validate_report_config.py` 预检
6. 若通过 API 保存，执行双保存并用 `getReportDevInfo` 验证

---

## 八、公式单元格（另见专篇）

含 Formula 单元格且通过 **API / 脚本保存** 时，必须遵守 `formula-cell-api-guide.md`：

- `cellText` / 顶层 `formula` **不带前导 `=`**
- `countType: count`、`displayType: Group`、`groupType: null`
- 双保存 + `getReportDevInfo` 回读验证

公式格本身通常 **不需要** subordination / leftFilterField；它引用同表内已配好筛选的 Field 汇总格。

---

## 九、相关文档

- `formula-cell-api-guide.md` — 公式单元格 API 写入规范（完整）
- `report-config-schema.md` §2.4–2.5 — 过滤与 Formula Schema
- `report-data-model.md` §2.4–2.5 — TypeScript 类型与枚举
- `ai-report-workflow.md` §4.4、§六 — 交叉表工作流与公式规则
- `report-knowledge-base.md` §2.1、§2.5 — 父格与自定义筛选概念
