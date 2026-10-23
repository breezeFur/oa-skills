# 报表配置 JSON Schema

> **冷启动禁止通读**：见 `cold-start-scan-guide.md`。仅生成整包配置 / Schema 校验时再读。

## 一、完整配置结构

```json
{
    "name": "报表名称",
    "appId": "应用ID",
    "config": {
        "ds": [
            {
                "id": "数据集ID",
                "name": "数据集名称",
                "type": "form",
                "sourceId": "源表单ID",
                "sourceGroup": "源分组",
                "fields": [
                    {
                        "id": "字段ID",
                        "name": "字段名",
                        "text": "显示文本",
                        "fieldType": "字段类型",
                        "dataSetId": "数据集ID",
                        "datasetName": "数据集名称"
                    }
                ]
            }
        ],
        "fields": [
            {
                "cellType": "Field",
                "displayType": "Group",
                "expandType": "Vertical",
                "dataSet": "数据集ID",
                "field": "字段ID",
                "leftParent": ["default", 0, 0],
                "topParent": ["empty", 0, 0],
                "groupType": "none",
                "countType": "none",
                "orderType": "no",
                "cellText": "字段显示名",
                "x": 2,
                "y": 0,
                "rowCount": 1,
                "colCount": 1,
                "style": {
                    "backColor": "#B6D6FF",
                    "foreColor": "#000000",
                    "hAlign": 1,
                    "vAlign": 1,
                    "font": "12px Arial",
                    "wordWrap": true
                }
            }
        ],
        "sheetProps": {
            "rowHeights": { "0": 30, "1": 25 },
            "colWidths": { "0": 120, "1": 150 }
        }
    }
}
```

## 二、单元格配置 Schema

### 2.1 必填字段

| 字段 | 类型 | 说明 | 枚举值 |
|------|------|------|--------|
| cellType | string | 单元格类型 | Const, Field, Formula, DateTime, DateField, SequenceNumber, AllCheck, SlashWord, SystemField, Control, TreeField |
| displayType | string | 显示方式 | List, Group, Count, Tree |
| expandType | string | 扩展方向 | NoExpand, Horizontal, Vertical |
| dataSet | string | 数据集ID | - |
| field | string | 字段ID | - |
| leftParent | array | 左父格 [type, x, y] | type: empty/default/custom |
| topParent | array | 上父格 [type, x, y] | type: empty/default/custom |
| groupType | string | 分组类型 | year, yearmonth, month, yearmonthday, yearweekday, monthweekday, none |
| countType | string | 统计类型 | sum, max, min, avg, count, distinctcount, none |
| orderType | string | 排序方式 | no, asc, desc |
| cellText | string | 内容/文本 | - |
| x | number | 行坐标 | >= 0 |
| y | number | 列坐标 | >= 0 |
| rowCount | number | 占行数 | >= 1 |
| colCount | number | 占列数 | >= 1 |

### 2.2 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| style | object | SpreadJS 样式 |
| leftFilterField | array | 左父格过滤（跨数据集必填，字段引用用 fieldKey） |
| topFilterField | array | 上父格过滤（字段引用用 fieldKey） |
| customFilterField | array | 单元格自定义筛选（字段引用用 fieldKey） |
| subordination | string[2] | 从属关系/VLOOKUP 映射（两段 fieldKey） |

### 2.3 样式 Schema

```json
{
    "style": {
        "backColor": "#FFFFFF",
        "foreColor": "#000000",
        "hAlign": 1,
        "vAlign": 1,
        "font": "12px Microsoft YaHei",
        "formatter": "0.00",
        "borderLeft": { "color": "#000000", "style": 1 },
        "borderTop": { "color": "#000000", "style": 1 },
        "borderRight": { "color": "#000000", "style": 1 },
        "borderBottom": { "color": "#000000", "style": 1 },
        "textIndent": 0,
        "wordWrap": false,
        "textDecoration": 0
    }
}
```

对齐值映射：
- hAlign: 0=左对齐, 1=居中, 2=右对齐
- vAlign: 0=上对齐, 1=居中, 2=下对齐
- textDecoration: 0=无, 1=下划线, 2=删除线
- borderStyle: 0=无, 1=细线, 2=中粗线, 3=虚线

### 2.4 过滤 Schema

> **重要**：设计器按 **fieldKey** 回显筛选字段，格式 `{dataSetId}.{sourceId}.{fieldName}`。  
> 不可用显示名（如「销售经理」）或裸系统名（如 `field_xxx`）。详见 `cross-dataset-filter-guide.md`。

**fieldKey 示例**：`1304979556231593994.1299763447342276611.field_1299763447342276617`

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
    ],
    "topFilterField": [
        {
            "parentField": "{父格fieldKey}",
            "currentField": "{当前fieldKey}",
            "type": "Equals",
            "id": "{当前fieldKey}"
        }
    ],
    "customFilterField": [
        {
            "currentField": "{当前fieldKey}",
            "type": "NotContain",
            "value": "排除值",
            "id": "{当前fieldKey}"
        }
    ]
}
```

workbook 内上述字段写在 `style.cellType` 上；API 保存后同步到 `getReportDevInfo.fields[]` 顶层。

### 2.5 Formula Schema

> **完整规范见 `formula-cell-api-guide.md`。** 以下为 Schema 摘要。

Formula 单元格（ReportProps `fields[]` 或 workbook `dataTable`）必填约定：

| 字段 | 值 | 说明 |
|------|-----|------|
| cellType | `Formula` | 固定 |
| cellText | 无前导 `=` | 如 `IF(J3=0,0,L3/J3)`，**禁止** `=IF(...)` |
| displayType | `Group` | 勿用 `List` |
| countType | `count` | 勿用 `none` |
| groupType | `null` | 勿用 `"none"` |
| expandType | `NoExpand` | 公式格通常不扩展 |

workbook 额外要求：

```json
{
  "formula": "IF(J3=0,0,L3/J3)",
  "style": {
    "formatter": "",
    "cellType": {
      "typeName": "FormulaCellType",
      "cellType": "Formula",
      "cellText": "IF(J3=0,0,L3/J3)",
      "displayType": "Group",
      "countType": "count",
      "groupType": null,
      "expandType": "NoExpand",
      "subordination": ["", ""]
    }
  }
}
```

## 三、数据集配置 Schema

```json
{
    "ds": [
        {
            "id": "唯一标识",
            "name": "数据集显示名",
            "type": "form",
            "sourceId": "源ID",
            "sourceGroup": "源分组标识",
            "fields": [
                {
                    "id": "字段唯一标识",
                    "name": "字段系统名",
                    "text": "字段显示名",
                    "fieldType": "string|number|date|datetime",
                    "originFieldType": "原始类型",
                    "dataSetId": "所属数据集ID",
                    "datasetName": "所属数据集名",
                    "tableId": "表ID",
                    "tableName": "表名",
                    "tableText": "表显示名",
                    "nameIndex": "名称索引",
                    "fieldKey": "字段键",
                    "fieldTitle": "字段标题"
                }
            ]
        }
    ]
}
```

## 四、工作表属性 Schema

```json
{
    "sheetProps": {
        "rowHeights": { "0": 30, "1": 25, "2": 20 },
        "colWidths": { "0": 120, "1": 150, "2": 100 },
        "styleConfig": {
            "custom": false,
            "theme": 1,
            "alternateMode": "row",
            "titleBg": "#B6D6FF",
            "alternateBg1": "#FFFFFF",
            "alternateBg2": "#FFEDB8",
            "titleStyle": {
                "fontSize": 12,
                "color": "#000000",
                "bold": true,
                "italic": false
            },
            "bodyStyle": {
                "fontSize": 12,
                "color": "#000000",
                "bold": false,
                "italic": false
            }
        },
        "pageProps": {
            "pageNum": 1,
            "pageRowCount": 200,
            "dynamicField": "",
            "scrollPage": false,
            "rowMode": false,
            "preAggregate": true,
            "frozenCell": null,
            "showGridLine": false,
            "showRowColHeader": false,
            "showLocation": "center",
            "childMerge": false,
            "columnFilter": true
        }
    }
}
```

## 五、查询条件 Schema

> **API 写入完整规范见 `query-condition-api-guide.md`。**  
> **默认规则**：数据集合选取后，选择类型未特别指定 SQL 时，均为 **条件字段**（`filterType: "default"`；`conditions` 仅含 `dataSetId` + `fieldId` + `relation`，**勿写** `filterType: "field"`）。

### 5.1 saveQueryItem（条件字段，非 SQL）

> 完整字段说明与 EBU 示例见 `query-condition-api-guide.md`。  
> **调用**：`queryItems` 参数必须是**单个对象**的 JSON 字符串（`JSON.stringify(item)`），禁止传数组；见该指南 §二 / §二点五（防 500）。

```json
{
  "dataSetId": null,
  "nameIndex": "0",
  "name": null,
  "text": "集团军",
  "displayType": "text",
  "filterType": "default",
  "showWhere": "advancedSearch",
  "advancedSearchType": "openCondition",
  "showOrder": 1,
  "asNameIndex": 1,
  "defaultValueType": "default",
  "defaultValue": "[\"\",\"\"]",
  "conditions": [{
    "dataSetId": "1304979556231593994",
    "fieldId": "1304979556231593994.1299763447342276611.field_1299763447342276612",
    "relation": "Contain"
  }],
  "fieldOptions": {
    "selected": "1304979556231593994",
    "1304979556231593994": [{
      "id": "1305320275886522369",
      "dataSetField": "1304979556231593994.1299763447342276611.field_1299763447342276612",
      "relation": "Contain",
      "queryItemValue": "输入值"
    }]
  },
  "sqlOptions": {}
}
```

| 字段 | 条件字段（默认） | SQL（显式指定） |
|------|------------------|-----------------|
| 顶层 `filterType` | `"default"` | `"sql"` |
| `conditions[]` | 仅 `dataSetId` + `fieldId` + `relation` | 含 `filterType: "sql"` + `sql` |
| `fieldOptions` | 保存时必传（含 `id`）；读回可能为空 | 通常不用 |

### 5.2 ReportProps queryFields（AI 生成摘要）

```json
{
    "queryFields": [
        {
            "uuid": "唯一标识",
            "id": "关联字段ID",
            "text": "条件显示名",
            "displayType": "date",
            "selectOptions": [],
            "filterOptions": [],
            "defaultValue": ["", ""],
            "param": "参数名",
            "filterType": "default",
            "conditions": [
                {
                    "dataSetId": "数据集ID",
                    "fieldId": "字段ID",
                    "relation": "between",
                    "sql": ""
                }
            ],
            "showOrder": 1,
            "queryType": "filter"
        }
    ]
}
```

## 六、条件格式 Schema

> **完整算子白名单、区间映射、冲突确认**：见 `condition-format-guide.md`。  
> **忌**：`highlight:between`（引擎不识别 → 规则不生成）。区间用 **`highlight:interval`**。

```json
{
    "conditionRule": {
        "highlightDatas": [
            {
                "index": 0,
                "conditionType": "currCell",
                "relation": "highlight:interval",
                "value1": "1",
                "value2": "5",
                "fontFamily": "Calibri",
                "fontSize": "12",
                "bold": false,
                "italic": false,
                "underline": false,
                "backColor": "",
                "foreColor": "#FF0000"
            },
            {
                "index": 1,
                "conditionType": "currCell",
                "relation": "highlight:greater",
                "value1": "5",
                "value2": "",
                "fontFamily": "Calibri",
                "fontSize": "12",
                "bold": true,
                "italic": false,
                "underline": false,
                "backColor": "",
                "foreColor": "#0000FF"
            }
        ],
        "lineDatas": [
            {
                "index": 0,
                "leftType": "min",
                "rightType": "max",
                "gradient": "gradient",
                "color": "#6495ED",
                "negativeFillColor": "#FF0000"
            }
        ],
        "iconDatas": [
            {
                "index": 0,
                "iconSetType": "direction",
                "iconCriteria": [
                    {
                        "iconValue": "33",
                        "isGreaterThanOrEqualTo": true,
                        "iconValueType": 1
                    }
                ]
            }
        ]
    }
}
```

支持的 `relation`：`greater` / `greaterAndEquals` / `less` / `lessAndEquals` / `equals` / `noEquals` / **`interval`（介于）** / `include` / `happenDate` / `sameValue`（均带 `highlight:` 前缀）。

## 七、配置生成检查清单

生成报表配置时必须验证以下项目：

- [ ] 报表名称非空且不重复
- [ ] 至少配置一个数据集（ds）
- [ ] 至少配置一个字段（fields）
- [ ] 每个字段的 cellType/displayType/expandType 值合法
- [ ] groupType 仅对分组字段生效，其余为 none
- [ ] countType 仅对指标字段生效，其余为 none
- [ ] 父格坐标不形成循环引用
- [ ] 多数据集时配置了 subordination + leftFilterField（fieldKey 格式，含 id）
- [ ] customFilterField（若有）使用平台 type 枚举且 currentField/id 为 fieldKey
- [ ] 公式字段的 cellType 为 Formula
- [ ] 公式字段 cellText **不以 `=` 开头**（见 `formula-cell-api-guide.md`）
- [ ] 公式字段 countType 为 `count`、displayType 为 `Group`、groupType 为 `null`
- [ ] workbook Formula 格顶层 `formula` 与 cellText 一致且无前导 `=`
- [ ] 常量字段的 cellType 为 Const
- [ ] 样式配置的颜色值为有效 hex 或 rgb 格式
