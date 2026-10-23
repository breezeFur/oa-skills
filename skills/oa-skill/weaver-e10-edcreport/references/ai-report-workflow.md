# AI 报表生成工作流程

> **冷启动禁止通读**：见 `cold-start-scan-guide.md`。纯搭表走 `api-report-build-fast-path.md`，勿开场读本文。

## 一、整体流程概览

```
用户输入（文本描述 / 图片效果 / 需求文件）
        |
        v
  1. 需求解析：理解报表类型、数据维度、指标、样式需求
        |
        v
  2. 字段分类：将需求中的字段映射为三类
     - groupFields（分组/维度字段）
     - listFields（列表/展示字段）
     - targetFields（指标/度量字段）
        |
        v
  3. 报表类型判定：根据字段组合判断报表类型
     - 简单列表（LIST）
     - 分组表（GROUP）
     - 交叉表/统计表（COUNT）
        |
        v
  4. 布局规划：确定单元格位置、扩展方向、父格关系
        |
        v
  5. 样式配置：主题选择、条件格式、字体样式
        |
        v
  6. 高级配置：查询条件、分页、打印、解析优化
        |
        v
  7. 输出配置：生成完整的 ReportProps JSON 配置
```

## 二、需求解析规则

### 2.1 从文本描述解析

识别以下关键信息：
- **报表名称**：用户提到的报表名称，如"客户信息报表"、"销售统计表"
- **数据源**：用户提到的数据表/表单名称，如"客户信息表"、"销售合同表"
- **分组维度**：用户提到"按...分组"、"按...统计"中的字段
- **指标度量**：用户提到"统计...数量"、"求和...金额"中的字段和聚合方式
- **列表字段**：用户提到"显示...信息"、"展示...详情"中的字段
- **查询条件**：用户提到"按...筛选"、"按...查询"中的字段
- **排序要求**：用户提到"按...排序"中的字段和方向
- **样式要求**：用户提到的主题颜色、条件格式等

### 2.2 从图片效果解析

分析报表截图中的以下要素：
- **报表布局**：表头结构、数据排列方式（分组/交叉/列表）
- **字段位置**：行维度字段、列维度字段、指标字段的位置
- **样式特征**：背景色、字体样式、交替行颜色
- **条件格式**：数据条、图标集、高亮规则
- **功能区域**：查询条件区域、工具栏按钮

### 2.3 从需求文件解析

支持的需求文件格式：
- **Word/Excel**：提取表格结构、字段列表、统计要求
- **JSON/YAML**：直接映射为报表配置
- **Markdown**：提取结构化的报表需求描述
- **图片**：同图片效果解析流程

## 三、字段分类规则

### 3.1 groupFields（分组/维度字段）

判定条件：
- 用户提到"按...分组"、"按...分类"、"按...维度"
- 日期类字段且用户提到时间粒度（年/月/日）
- 报表中需要横向或纵向展开的分类字段

配置示例：
```json
{
    "fieldName": "创建日期",
    "groupType": "yearmonth"    // 按年月分组
}
```

groupType 中文到系统值映射：
- "年份" → `year`
- "年月" → `yearmonth`
- "月份" → `month`
- "年月日" → `yearmonthday`
- 无时间分组 → `none`

### 3.2 listFields（列表/展示字段）

判定条件：
- 用户提到"显示...信息"、"展示...字段"
- 不需要分组、不需要聚合的普通展示字段
- 报表中的明细数据列

配置示例：
```json
{
    "fieldName": "客户名称",
    "groupType": "none"
}
```

### 3.3 targetFields（指标/度量字段）

判定条件：
- 用户提到"统计...数量"、"求和...金额"、"平均...值"
- 需要聚合计算的数字类型字段
- 报表中的数据值区域

配置示例：
```json
{
    "fieldName": "合同金额",
    "countType": "sum"     // 求和
}
```

countType 中文到系统值映射：
- "求和" → `sum`
- "最大值" → `max`
- "最小值" → `min`
- "平均值" → `avg`
- "计数" → `count`
- "去重计数" → `distinctcount`
- 默认 → `sum`

## 四、报表类型判定与布局规则

### 4.1 简单列表（LIST）

**触发条件**：只有 listFields 和/或 targetFields，没有 groupFields

**布局规则**：
- 所有字段纵向扩展（expandType = Vertical）
- 显示方式为排列（displayType = List）
- 左父格均为默认（leftParent = ["default", 0, 0]）
- 无上父格（topParent = ["empty", 0, 0]）

**单元格布局示例**：
```
A1: 标题行（常量）
A2: 字段1(纵向扩展,排列)  B2: 字段2(纵向扩展,排列)  C2: 字段3(纵向扩展,排列)
```

### 4.2 分组表（GROUP）

**触发条件**：有 groupFields 但数量 < 2，或没有 targetFields

**布局规则**：
- 分组字段纵向扩展（expandType = Vertical），显示方式为分组（displayType = Group）
- 指标字段纵向扩展（expandType = Vertical），显示方式为汇总（displayType = Count）
- 左父格关系：指标字段的左父格默认依赖相邻的分组字段
- 无上父格

**单元格布局示例**：
```
A1: 标题行（常量）
A2: 分组字段(纵向扩展,分组)  B2: 指标字段(纵向扩展,汇总,求和)
```

### 4.3 交叉表/统计表（COUNT）

**触发条件**：groupFields >= 2 且有 targetFields

**布局规则**：
- 行维度 = groupFields 的最后一个（纵向扩展，分组）
- 列维度 = groupFields 的前 N-1 个（横向扩展，分组）
- 指标字段在交叉位置（纵向扩展，汇总）
- 指标字段的左父格自定义指向行维度单元格
- 指标字段的上父格自定义指向列维度单元格
- 必须设置父格筛选关联多数据集

**单元格布局示例**（2个分组字段+1个指标）：
```
A1: 标题行（常量）
A2: 行维度字段(纵向扩展,分组)  B2: 列维度字段(横向扩展,分组)
                              B3: 指标字段(纵向扩展,汇总,求和)
                                  左父格=自定义(A2), 上父格=自定义(B2)
```

### 4.4 交叉表父格筛选配置

当使用多个数据集时，必须同时配置 **subordination**（从属关系）和 **leftFilterField**（左父格筛选）。  
字段引用必须使用 **fieldKey**：`{dataSetId}.{sourceId}.{fieldName}`，且 `id` 等于 `currentField`。

> 完整说明、自定义筛选、双保存与排查见 `cross-dataset-filter-guide.md`。

```json
{
    "subordination": [
        "1304979556231593994.1299763447342276611.field_1299763447342276617",
        "1304979560546713602.1299789221321891842.field_1299789221321891843"
    ],
    "leftFilterField": [{
        "parentField": "1304979556231593994.1299763447342276611.field_1299763447342276617",
        "currentField": "1304979560546713602.1299789221321891842.field_1299789221321891843",
        "type": "Equals",
        "id": "1304979560546713602.1299789221321891842.field_1299789221321891843"
    }],
    "customFilterField": [{
        "currentField": "1304979560546713602.1299789221321891842.field_1299789221321891844",
        "type": "NotContain",
        "value": "排除机构",
        "id": "1304979560546713602.1299789221321891842.field_1299789221321891844"
    }]
}
```

**常见错误**：使用显示名「团队」「销售经理」或裸 `field_xxx` → 设计器筛选下拉空白。

## 五、单元格坐标规划规则

### 5.1 基本布局原则

- 第1行（y=0）：报表标题行，使用常量字段（cellType=Const）
- 第2行（y=1）：表头/字段名称行
- 第3行及以后（y>=2）：数据区域

### 5.2 坐标系

- x = 行号（从0开始，向下递增）
- y = 列号（从0开始，向右递增）
- 父格坐标：[type, x, y]
  - `["default", 0, 0]` = 默认（依赖相邻单元格）
  - `["custom", x, y]` = 自定义（指向坐标 x,y 的单元格）
  - `["empty", 0, 0]` = 无父格

### 5.3 多数据集布局

当报表使用多个数据集时：
1. 维度字段通常来自主数据集
2. 指标字段可能来自不同数据集
3. 跨数据集字段必须设置父格筛选关联

## 六、公式配置规则

> **API / 脚本保存含 Formula 时，完整规范见 `formula-cell-api-guide.md`。** 本节为工作流摘要。

### 6.1 公式类型

| 分类 | 常用公式 |
|------|----------|
| 数学 | SUM, AVERAGE, COUNT, MAX, MIN, ABS, ROUND, CEILING, FLOOR |
| 文本 | LEFT, RIGHT, MID, LEN, CONCAT, UPPER, LOWER |
| 日期 | YEAR, MONTH, DAY, DATE, DATEDIF, NOW, TODAY |
| 逻辑 | IF, IFERROR, AND, OR, NOT |
| 信息 | ISERROR, ISBLANK, ISNUMBER |

### 6.2 公式配置方式（ReportProps / getReportDevInfo）

公式单元格 `cellType` 为 `Formula`，**cellText 为公式表达式且不带前导 `=`**：

```json
{
    "cellType": "Formula",
    "cellText": "IF(J3=0,0,L3/J3)",
    "displayType": "Group",
    "countType": "count",
    "groupType": null,
    "expandType": "NoExpand"
}
```

**错误示例（会导致设计器空白）**：

```json
{
    "cellType": "Formula",
    "cellText": "=IF(J3=0,0,L3/J3)",
    "displayType": "List",
    "countType": "none"
}
```

### 6.3 workbook 写入（saveReportWithCacheConfig）

workbook `dataTable` 中 Formula 格需同时设置：

- 顶层 `"formula": "IF(...)"`（无前导 `=`）
- `style.cellType.cellText` 与顶层 `formula` 内容一致
- `style.formatter` 为空字符串

参考 `make_formula()` 见 `formula-cell-api-guide.md` §四。

### 6.4 公式与父格关系

若公式需要按特定分组计算，公式单元格也需设置自定义左父格或上父格（`leftX`/`leftY` 指向根格）。

公式格通常 `subordination: ["", ""]`，引用同表内 Field 汇总格而非数据集字段名。

### 6.5 占比 / 除法推荐写法

| 场景 | 设计器输入 | API 存储 |
|------|-----------|----------|
| 达成率 | `=IF(J3=0,0,L3/J3)` | `IF(J3=0,0,L3/J3)` |
| 占比 | `=IF(L3=0,0,M3/L3)` | `IF(L3=0,0,M3/L3)` |
| 安全除法 | `=IFERROR(G5/F5,"--")` | `IFERROR(G5/F5,"--")` |

### 6.6 保存与验证

1. 双保存：`saveReportWithCacheConfig` + `saveReportDevInfo`
2. `getReportDevInfo` 回读：确认 `cellText` 不以 `=` 开头
3. 运行 `validate_report_config.py` 预检 Formula 格式

## 七、高级功能配置

### 7.1 查询条件配置

> **API/脚本写入完整规范**见 `query-condition-api-guide.md`（条件字段形态、asNameIndex、21 项日期选项、系统参数默认值）。以下为 ReportProps 摘要，**不可直接等同于 saveQueryItem  payload**。

```json
{
    "queryFields": [{
        "uuid": "query-1",
        "id": "field-001",
        "text": "日期范围",
        "displayType": "date",
        "conditions": [{
            "dataSetId": "ds-001",
            "fieldId": "createdate",
            "relation": "between"
        }],
        "showOrder": 1
    }]
}
```

### 7.2 分页配置

```json
{
    "pageNum": 1,
    "pageRowCount": 200,        // 每页行数
    "dynamicField": "",        // 动态Sheet页字段
    "scrollPage": false        // 滚动分页
}
```

### 7.3 解析优化配置

```json
{
    "rowMode": false,          // 行式加载（仅单数据集简单列表）
    "preAggregate": true       // 数据预聚合（默认开启）
}
```

### 7.4 打印配置

```json
{
    "printInfo": {
        "area": { "startRow": -1, "endRow": -1, "startCol": -1, "endCol": -1 },
        "repeatArea": { "startRow": -1, "endRow": -1, "startCol": -1, "endCol": -1 },
        "printGridLine": false,
        "printOuterBorder": false,
        "allRowsInOnePage": false,
        "allColsInOnePage": false,
        "printOrder": "auto"
    },
    "pageMargin": { "top": -1, "bottom": -1, "left": -1, "right": -1, "header": -1, "footer": -1 },
    "paperSize": "A4",
    "paperOrientation": "portrait"
}
```

## 八、确认信息生成规则

生成报表配置后，应向用户展示确认信息：

```
报表创建确认：

名称：{reportName}
数据源：{formName}
报表类型：{列表|分组表|交叉表}

行维度字段：{字段名}（{分组类型}）
列维度字段：{字段名}（{分组类型}）
列表字段：{字段名}
指标字段：{字段名}（{聚合方式}）

查询条件：{条件名}（{条件类型}）
主题样式：主题{编号}

请确认是否创建此报表。
```

## 九、错误处理与校验

### 9.1 必须校验项

1. **报表名称**：不能为空，不能与已有报表重名
2. **数据源**：必须指定有效的数据源
3. **字段配置**：至少需要一个字段
4. **字段有效性**：指定的字段名必须在数据集可用字段中
5. **父格一致性**：多数据集时必须设置父格筛选

### 9.2 常见错误及处理

| 错误 | 原因 | 处理方式 |
|------|------|----------|
| 字段不存在 | AI 指定的字段名不在数据集中 | 列出可用字段，提示用户修正 |
| 数据源未找到 | formId 无效 | 提示用户选择有效数据源 |
| 名称重复 | 报表名已存在 | 提示用户更换名称 |
| 父格循环引用 | 父格设置形成环 | 检查并修正父格关系 |
| 聚合字段非数字 | 对文本字段使用求和 | 检查字段类型，使用计数替代 |
