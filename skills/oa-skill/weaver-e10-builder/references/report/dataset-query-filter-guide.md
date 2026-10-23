# 数据集筛选（queryInfoSave）API 写入规范

> **适用场景**：设计器左侧「数据集 → 筛选条件」、行级数据权限、整表预过滤。 
> **参考报表**：`1304979556231593985`（EBU 经营数据统计） 
> **代码实现**：`本地工作目录` → `build_*_dataset_query_filter()` / `ensure_*_dataset_filter()` 
> **执行**：`python 本地工作目录`

---

## 一、三种「筛选」机制（必区分）

| 机制 | 设计器入口 | API | 持久化形态 | 典型用途 |
|------|-----------|-----|-----------|----------|
| **高级搜索** | 页面 → 查询设置 | `saveQueryItem` / `getQueryItem` | QueryItem JSON | 用户运行时输入筛选 |
| **数据集筛选** | 左侧数据集 → 筛选条件 | **`queryInfoSave` / `queryInfoGet`** | `conditionData` + `otherData` | 行级权限、整表预过滤 |
| **单元格/实例筛选** | 单元格自定义筛选 / 多数据集副本 | `saveReportWithCacheConfig` → `datasetFilter` / `customFilterField` | filterList + fieldKey | 列级差异化汇总 |

**Agent 硬约束**

- 用户说「左侧数据集筛选」「行级权限」「数据集过滤条件」→ **只用 `queryInfoSave`**，禁止写 `saveQueryItem`。
- 用户说「高级搜索」「查询条件」→ **`saveQueryItem`**，禁止写 `queryInfoSave`。
- 用户说「自定义筛选」「核算机构不包含」且针对**某一列/某一数据集实例**→ `datasetFilter` / `customFilterField`（见 `cross-dataset-filter-guide.md`）。

---

## 二、API

| 操作 | 方法 | 参数 |
|------|------|------|
| 保存 | `POST /api/bs/edc/dataset/queryInfoSave` | `datasetId`, `filterData`（conditionData JSON 字符串）, `otherData`（JSON 字符串） |
| 读取 | `GET /api/bs/edc/dataset/queryInfoGet` | `datasetId` |

回读路径：`data.conditionData`、`data.otherData`（均为 JSON 字符串，需二次 `json.loads`）。

---

## 三、conditionData 顶层结构

```json
{
 "key": "<毫秒时间戳>",
 "relationship": "1",
 "isParent": true,
 "isNewFilter": true,
 "parentNode": "",
 "datas": [ /* 条件节点数组 */ ],
 "version": 1
}
```

| 字段 | 值 | 说明 |
|------|-----|------|
| `relationship` | **`"1"`** | 且（AND） |
| `relationship` | **`"0"`** | 或（OR） |
| `otherData.rootStr` | 人类可读表达式 | 设计器展示用，须与 datas 语义一致 |
| `otherData.filterIsNull` | **`true`** | **变量值为空时不参与条件过滤**（平台 `QueryFilterBiz.analysisConfigFilter`）；与设计器「空值不筛」对齐，写入变量条件时**必须**为 `true` |
| `otherData.rootStr` | 人类可读表达式 | 设计器展示用，须与 datas 语义一致 |
| `otherData.version` | `1` | 与手动 save 对齐 |

### 5.4 自定义变量（如 `{cs}`）

| 场景 | func | value | otherData |
|------|------|-------|-----------|
| 创建者等于自定义变量 cs | `eq` | `{cs}` | **`filterIsNull: true`** |
| 固定字面量（如资产名称=办公用品） | `eq` | `办公用品` | 同上（整组筛选共用 otherData） |

> 变量名写在花括号内，与运行时请求参数 / 页面入参键一致。`filterIsNull=true` 时，`{cs}` 解析为空则**整条条件跳过**，不会误筛成「等于空」。

---

## 四、单条条件节点（datas[]）

```json
{
 "type": "condition",
 "fieldName": "field_1299789221321891852",
 "fieldType": "String",
 "compType": "Text",
 "text": "产品类型",
 "objId": "<sourceId>",
 "conditions": {
 "func": "nempty",
 "value": "",
 "type": "",
 "text": "",
 "isEsb": false
 },
 "formInfo": { "fieldId": "<字段 id>" },
 "config": { "fieldId": "<字段 id>" }
}
```

`conditions` 三要素：**func** + **value** + **type**（字段对比时为 `"formField"`）。

---

## 五、需求语义 → func / value 对照表

### 5.1 字面量条件（type 为空）

| 设计器 / 需求描述 | func | value 示例 | 备注 |
|------------------|------|-----------|------|
| 不为空 | **`nempty`** | `""` | 保存用 `nempty`，勿写 `isNotNull` |
| 为空 | **`empty`** | `""` | |
| 等于 | **`eq`** | 固定值或 `{lastname}` | 人员当前登录见 §5.3 |
| 不等于（固定文本） | **`notEq`** | `"新签合同"` | 与字段对比的 `neq` 不同 |
| 包含 | `like` / `contains` | 文本 | |
| 不包含 | `uncontains` | 文本 | datasetFilter 常用 |
| 开头包含 | **`startWith`** | `{thisyear}` | 按年份前缀筛 datetime / yyyy-MM |
| 结尾包含 | `endWith` | 文本 | |
| 介于 | **`between`** | `["{thisyear}",""]` | 完整日期区间；**不**适用于 yyyy-MM 等于当前月 |

### 5.2 字段对比（type = `"formField"`）

左字段为当前节点 `fieldName`；右字段写在 `value.compareFormField`（目标字段完整 `originField` + `showName` + `changeTrigger`）。

| 设计器 / 需求描述 | func | value 结构 |
|------------------|------|-----------|
| **不属于**（字段 A 不属于字段 B） | **`unaggregate`** | `{ "compareFormField": <字段B originField> }` |
| **不等于**（字段 A ≠ 字段 B） | **`neq`** | `{ "compareFormField": <字段B originField> }` |

```python
def _build_compare_form_field(origin_field):
 field = dict(origin_field or {})
 field["showName"] = field.get("name") or field.get("showName") or ""
 field["changeTrigger"] = field.get("changeTrigger") or "1"
 return field
```

**常见错误**

| 错误写法 | 正确理解 |
|----------|----------|
| `notEq` + 字符串 `"核算机构"` | 排除产品类型**枚举值**为「核算机构」，不是字段对比 |
| `unaggregate` 用于「不等于」 | 「不等于」用 **`neq`**；「不属于」用 **`unaggregate`** |
| `isNotNull` 写入 queryInfoSave | 平台归一化为 **`nempty`** |

### 5.3 系统参数（dataset 筛选已验证）

| 场景 | func | value |
|------|------|-------|
| 当前用户姓名 | `eq` | `{lastname}` |
| 当前登录人员 ID | **`eq`** | `{userid}`（设计器显示「等于」，勿用 `in`） |
| 当前年月（format=`yyyy-MM`） | `eq` | **`{year}-{month}`** |
| 今年（yyyy-MM / datetime 前缀） | `startWith` | **`{thisyear}`** |
| 今年（高级搜索日期区间） | `between` | `["{thisyear}",""]` | 仅 saveQueryItem，非左侧 dataset |

**无效占位符**：`{username}`、`{today}`、`{currmonth}`。

---

## 六、日期字段 format 与写法

| 字段 format | 需求 | 推荐写法 | 勿用 |
|-------------|------|----------|------|
| `yyyy-MM` | 当前年月 | `eq` + `{year}-{month}` | `between` + `{thismonth}` |
| `yyyy-MM` | 今年 | `startWith` + `{thisyear}` | `between`（完整日期语义） |
| `yyyy-MM-dd` / `yyyy-MM-dd HH:mm:ss` | 今年 | `startWith` + `{thisyear}` | — |
| 高级搜索日期区间 | 本月 | — | 见 `query-condition-api-guide.md` §五 |

---

## 七、EBU 参考示例

报表 `1304979556231593985`

### 7.1 EBU团队 · AND（`relationship: "1"`）

数据集 `1304979556231593994`

| 字段 | func | value |
|------|------|-------|
| 负责人姓名 | `eq` | `{lastname}` |
| 创建者 | **`eq`** | `{userid}` |

rootStr：`( 负责人姓名 等于 '{lastname}' ) AND ( 创建者 等于 '{userid}' )`

### 7.2 直销合同业绩表 · OR（`relationship: "0"`）

数据集 `1304979560546713602`

| 字段 | func | type | value |
|------|------|------|-------|
| 核算机构 | **`neq`** | **`formField`** | compareFormField → 合同种类 |
| 创建时间 | **`startWith`** | — | `{thisyear}` |

rootStr：`(( 核算机构 不等于合同种类 ) 或 ( 创建时间 开头包含 '{thisyear}' ))`

### 7.3 其他可用写法（按需）

| 场景 | func | value |
|------|------|-------|
| 产品类型 不属于 核算机构 | `unaggregate` + formField | compareFormField → 核算机构 |
| 合同业绩年月 = 当前年月 | `eq` | `{year}-{month}` |

---

## 八、写入与验证流程

1. `fieldsAndOriginFields` / `get_fields` 取字段 **originField**（字段对比右侧必填）。
2. 组装 `conditionData` + `otherData`（含 `rootStr`）。
3. `POST queryInfoSave`。
4. **`GET queryInfoGet` 回读**，核对：
 - [ ] `relationship` 与 AND/OR 一致
 - [ ] 每条 `conditions.func` / `conditions.type` / `conditions.value`
 - [ ] 字段对比：`value.compareFormField.name` 为右字段 fieldName
 - [ ] `otherData.rootStr` 与设计器一致
5. 设计器刷新左侧数据集 → 筛选条件，确认操作项与默认值回显。

**禁止**：未回读 `queryInfoGet` 即声称配置正确（手动 save 与脚本形态可能不同）。

---

## 九、与 queryInfoSave 无关的筛选

以下场景**不要**使用本章 API：

| 需求 | 文档 |
|------|------|
| 报表顶部高级搜索 | `query-condition-api-guide.md` §二–§六 |
| 单元格 customFilterField | `cross-dataset-filter-guide.md` §三 |
| 多数据集实例 datasetFilter | `cross-dataset-filter-guide.md` §3.4 |
| 左父格 subordination / leftFilterField | `cross-dataset-filter-guide.md` §二 |

---

## 十、相关文件

| 文件 | 用途 |
|------|------|
| `本地工作目录` | `_dataset_filter_condition_node`、`_dataset_filter_form_field_compare_node`、`build_*_dataset_query_filter` |
| `本地工作目录` | 一键写入高级搜索 + 数据集筛选 |
| `query-condition-api-guide.md` | saveQueryItem 高级搜索（与本文互补） |
| `cross-dataset-filter-guide.md` | datasetFilter / customFilterField / fieldKey |
| `report-knowledge-base.md` | FuncType 枚举摘要 |
