# E-Builder 报表数据模型参考

> **冷启动禁止通读**：见 `cold-start-scan-guide.md`。仅生成整包 ReportProps / 深分析时再读。

## 一、核心枚举类型

### 1.1 单元格类型 (CellTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `Const` | 常量字段（自定义文本内容） |
| `Field` | 数据字段（数据集选取的字段） |
| `Formula` | 公式字段（公式计算） |
| `DateTime` | 日期时间 |
| `DateField` | 日期字段 |
| `SequenceNumber` | 序号字段（自动生成序号） |
| `AllCheck` | 全选字段（全选框） |
| `SlashWord` | 斜线文字（多维交叉表头） |
| `SystemField` | 系统字段 |
| `Control` | 控件字段（多级填报） |
| `TreeField` | 树形字段 |

### 1.2 显示方式 (DisplayTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `List` | 排列（数据逐条展示） |
| `Group` | 分组（相同数据合并为一组） |
| `Count` | 汇总（求和/最大值/最小值/平均数/个数） |
| `Tree` | 树形（上下级层级展示） |

### 1.3 扩展方向 (ExpandTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `Vertical` | 纵向扩展（从上至下，不同单元格展示） |
| `Horizontal` | 横向扩展（从左至右，不同单元格展示） |
| `NoExpand` | 不扩展（所有数据在一个单元格） |

### 1.4 分组类型 (GroupTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `year` | 按年份分组 |
| `yearmonth` | 按年月分组 |
| `month` | 按月份分组 |
| `yearmonthday` | 按年月日分组 |
| `yearweekday` | 按年周分组 |
| `monthweekday` | 按月周分组 |
| `none` | 不进行时间分组 |

### 1.5 统计类型 (CountTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `sum` | 求和 |
| `max` | 最大值 |
| `min` | 最小值 |
| `avg` | 平均值 |
| `count` | 计数 |
| `distinctcount` | 去重计数 |
| `none` | 无统计 |

### 1.6 排序方式 (OrderTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `no` | 不排序 |
| `asc` | 升序 |
| `desc` | 降序 |

### 1.7 父格类型 (CellParentType)

| 枚举值 | 说明 |
|--------|------|
| `empty` | 无父格 |
| `default` | 默认父格（相邻左/上单元格） |
| `custom` | 自定义父格（指定具体单元格坐标） |

父格值格式: `[CellParentType, x坐标, y坐标]`

### 1.8 数据源类型 (SourceTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `local` | 本地 |
| `form` | e-builder 表单 |
| `eteams` | eTeams |
| `logic` | 逻辑（数据加工） |
| `external` | 外部数据源 |
| `externaldataset` | 外部数据集 |
| `localds` | 本地数据集 |
| `systemField` | 系统字段 |
| `localView` | 本地视图 |
| `integration` | 集成 |

## 二、报表配置数据模型

### 2.1 报表配置 (ReportProps)

```typescript
interface ReportProps {
    config: {
        fields: CellProps[];           // 字段列表
        ds: SourceTableResult[];       // 数据源列表
        sheetProps?: {                 // 工作表属性
            rowHeights: Record<number, number>;
            colWidths: Record<number, number>;
        };
    };
    name: string;                       // 报表名称
    appId: string;                     // 应用ID
}
```

### 2.2 单元格配置 (CellProps)

```typescript
interface CellProps {
    cellType: CellTypeEnum;             // 字段类型
    displayType: DisplayTypeEnum;       // 显示方式
    expandType: ExpandTypeEnum;         // 扩展方向
    dataSet: string;                    // 数据集主键
    field: string;                     // 字段主键
    leftParent: CellParentValueType;    // 左父格 [类型, x, y]
    topParent: CellParentValueType;     // 上父格 [类型, x, y]
    groupType: GroupTypeEnum;           // 分组类型
    countType: CountTypeEnum;           // 统计类型
    orderType: OrderTypeEnum;           // 排序方式
    cellText: string;                   // 内容/显示文本
    x: number;                          // 行号
    y: number;                          // 列号
    rowCount: number;                   // 所占行数
    colCount: number;                   // 所占列数
    style?: SpreadJSCellStyle;           // 单元格样式
    leftFilterField?: FilterFieldItem[];  // 左父格过滤
    topFilterField?: FilterFieldItem[];   // 上父格过滤
}
```

### 2.3 单元格样式 (SpreadJSCellStyle)

```typescript
interface SpreadJSCellStyle {
    backColor?: string;       // 背景颜色
    foreColor?: string;       // 字体颜色
    hAlign?: number;          // 水平对齐 (0=左, 1=居中, 2=右)
    vAlign?: number;          // 垂直对齐 (0=上, 1=居中, 2=下)
    font?: string;            // 字体 (如 "12px Arial")
    formatter?: string;       // 数字格式
    borderLeft?: { color: string; style: number };
    borderTop?: { color: string; style: number };
    borderRight?: { color: string; style: number };
    borderBottom?: { color: string; style: number };
    textIndent?: number;      // 缩进
    wordWrap?: boolean;       // 自动换行
    textDecoration?: number; // 文本装饰 (0=无, 1=下划线, 2=删除线)
}
```

### 2.4 过滤配置

```typescript
// fieldKey 格式：{dataSetId}.{sourceId}.{fieldName}
// 设计器筛选下拉按 fieldKey 匹配，不可用显示名或裸 field_xxx

// 父格过滤（跨数据源关联）
type ParentFilter = {
    parentField?: string;      // 父格字段 fieldKey
    currentField?: string;     // 当前字段 fieldKey
    type?: FilterOptionEnum;   // 匹配关系（如 Equals）
    id?: string;               // 必须等于 currentField（设计器回显）
}

// 自定义过滤（单元格级）
type CustomFilter = {
    currentField?: string;     // fieldKey
    type?: FilterOptionEnum;   // 平台枚举，禁止 eq/uncontains/empty/nempty
    value?: string;
    id?: string;               // 必须等于 currentField
}

// 从属关系（VLOOKUP 映射，与 leftFilterField 配套）
type Subordination = [string, string];  // [父格fieldKey, 当前fieldKey]
```

// 数据行过滤
type DataFilter = {
    currentField?: DataRowFilterType;  // Before|Last|Odd|Even|Designates
    value?: string;
}
```

### 2.5 过滤操作符 (FilterOptionEnum)

| 枚举值 | 说明 |
|--------|------|
| `Equals` | 等于 |
| `NotEquals` | 不等于 |
| `Greater` | 大于 |
| `GreaterOrEquals` | 大于等于 |
| `Less` | 小于 |
| `LessOrEquals` | 小于等于 |
| `StartsWith` | 开始于 |
| `NotStartsWith` | 不开始于 |
| `EndsWith` | 结束于 |
| `NotEndsWith` | 不结束于 |
| `Contain` | 包含 |
| `NotContain` | 不包含 |
| `Include` | 属于 |
| `NotInclude` | 不属于 |
| `Null` | 为空 |
| `NotNull` | 不为空 |

## 三、AI 报表配置 DTO

### 3.1 ReportAIDto

```java
class ReportAIDto {
    Long appId;               // 所属应用ID
    Long reportId;            // 报表ID（更新时使用）
    String reportName;        // 报表名称
    String formId;            // 数据源表单ID
    String formName;          // 数据源表单名称
    List<FieldAIDto> groupFields;   // 分组字段（维度字段）
    List<FieldAIDto> listFields;    // 列表字段（不分组只展示）
    List<FieldAIDto> targetFields;   // 指标/度量字段（要聚合计算的字段）
    String theme;             // 报表主题/样式
    List<FieldAIDto> queryFields;    // 查询筛选字段
    String version;           // 版本标识（"v2"表示直接创建）
}
```

### 3.2 FieldAIDto

```java
class FieldAIDto {
    String fieldName;   // 字段显示名称（中文业务名）
    String groupType;   // 分组时间粒度（仅分组字段使用）
    String countType;   // 聚合计算类型（仅指标字段使用）
}
```

### 3.3 字段类型映射

| AI 字段类型 | fieldType | 含义 | groupType | countType |
|-------------|-----------|------|-----------|-----------|
| groupFields | GROUP | 分组/维度字段 | year/yearmonth/month/none | - |
| listFields | LIST | 列表/展示字段 | none | - |
| targetFields | COUNT | 指标/度量字段 | - | sum/max/min/avg/count/distinctcount |

## 四、报表类型判断规则

### 4.1 三种报表类型的字段组织方式

**类型一：简单列表**（只有 listFields + targetFields）
- dimensionFields = groupFields + listFields（全部作为行维度）
- yDimensionFields = [] （无列维度）
- targetFields = 指标字段

**类型二：分组表**（只有 groupFields < 2 或无 targetFields）
- dimensionFields = groupFields（全部分组字段作为行维度）
- yDimensionFields = [] （无列维度）
- targetFields = 指标字段

**类型三：交叉表/统计表**（groupFields >= 2 且有 targetFields）
- 行维度 (yDimensionFields) = groupFields 的最后一个
- 列维度 (dimensionFields) = groupFields 的前 N-1 个 + listFields
- 指标 (targetFields) = 指标字段

## 五、主题配置

### 5.1 预置主题模板（10 个）

| 主题编号 | 标题背景 | 交替色1 | 交替色2 | 风格 |
|----------|----------|---------|---------|------|
| 1 | #B6D6FF | #FFFFFF | #FFEDB8 | 蓝+黄 |
| 2 | #CAF5BF | #FFFFFF | #FFEDED | 绿+粉 |
| 3 | #C6C0FF | #FFFFFF | #ECECEC | 紫+灰 |
| 4 | #FFC0C0 | #FFFFFF | #DBEBFF | 红粉+蓝 |
| 5 | #FFDD7A | #FFFFFF | #FFEFDD | 金+橙 |
| 6 | #33B617 | #FFFFFF | #FFEDB8 | 深绿 |
| 7 | #15A8FB | #FFFFFF | #F0F0F0 | 蓝 |
| 8 | #F38114 | #FFFFFF | #E4E4E4 | 橙 |
| 9 | #F03112 | #FFFFFF | #FFF5D6 | 红 |
| 10 | #B035F4 | #FFFFFF | #FFF2CD | 紫 |

### 5.2 自定义主题结构

```typescript
interface StyleConfig {
    custom: boolean;              // 是否自定义
    theme: number | null;         // 主题编号 (1-10)
    alternateMode: 'row' | 'col'; // 交替方式
    titleBg: string;              // 标题背景色
    alternateBg1: string;         // 交替背景色1
    alternateBg2: string;         // 交替背景色2
    titleStyle: {
        fontSize: number;
        color: string;
        bold: boolean;
        italic: boolean;
    };
    bodyStyle: {
        fontSize: number;
        color: string;
        bold: boolean;
        italic: boolean;
    };
    area: { row: number; col: number; rowCount: number; colCount: number } | null;
}
```

## 六、条件格式配置

### 6.1 条件规则类型

```typescript
interface ConditionRuleType {
    highlightDatas?: HightlightRuleType[];  // 高亮规则
    lineDatas?: DataLineRuleType[];         // 数据条规则
    iconDatas?: DataIconRuleType[];         // 图标集规则
}
```

### 6.2 高亮规则

```typescript
interface HightlightRuleType {
    index: number;
    conditionType?: 'currCell' | 'otherCell';
    relation?: HighlightRelationEnum;  // equals/greater/less/interval/include/happenDate/sameValue 等
    value1?: any;
    value2?: any;
    fontFamily?: string;
    fontSize?: string;
    bold?: boolean;
    italic?: boolean;
    underline?: boolean;
    backColor?: string;
    foreColor?: string;
}
```

### 6.3 数据条规则

```typescript
interface DataLineRuleType {
    index: number;
    leftType: 'min' | 'custom';
    leftValue?: number;
    rightType: 'max' | 'custom';
    rightValue?: number;
    gradient?: 'gradient' | 'solid';
    color?: string;
    negativeFillColor?: string;
}
```

## 七、查询条件配置

```typescript
interface IReportConditionItemType {
    uuid: string;
    id: string;
    text: string;                           // 条件名称
    displayType: ReportConditionDisplayTypeEnum;  // 显示类型
    selectOptions: any[];
    filterOptions: any[];
    defaultValue: [string, string];
    param: string;
    filterType: 'default' | 'sql';
    conditions: IReportConditionRel[];      // 条件关联
    showOrder: number;
    queryType?: 'filter' | 'advance';
}

// 查询条件显示类型
enum ReportConditionDisplayTypeEnum {
    text = 'text',         // 文本
    number = 'number',     // 数字
    select = 'select',     // 下拉选择
    cascader = 'cascader', // 级联
    date = 'date',         // 日期范围
    singleDate = 'singleDate', // 单日期
    eBuilder = 'eBuilder', // e-builder组件
    browser = 'browser',   // 浏览框
    custom = 'custom',     // 自定义
    time = 'time'          // 时间
}
```

## 八、字段转换类型（已更正 · 以「转换」面板为准）

> **权威**：`references/cell-transform-guide.md`。下列旧表 **作废**，勿再使用 `person`/`department`/`image`/`html`/`barcode` 作为单一 `transType`。

### 8.1 `transType`（字段转换）

| UI | `transType` | 附加 |
|----|-------------|------|
| 无 | `default` | — |
| 人员 / 部门 / 部门全路径 / 关联类型 | `browser` | `browserType`（ComInfo id 等） |
| Checkbox | `checkbox` | — |
| 选择框 | `select` | `transSelectOptions` |
| 颜色选择框 | `colorSelect` | `transSelectOptions` |
| 分值图标 | `scoreIcon` | `transSelectOptions` |
| 斜线文字 | `slashWord` | `transSelectOptions` |
| 图片 | `picture` | — |

### 8.2 同面板其它键（独立字段，不是 transType）

| UI | 键 | 值 |
|----|-----|-----|
| HTML转换 | `isHtml` | `"0"` / `"1"` |
| 前缀后缀 | `prefixAndSuffix` | `["前","后"]` |
| 条码 | `qrcodeType` | `no` / `barcode` / `qrcode`（另 `qrcodelink`） |
| 隐藏内容 | `hiddenContext` | `"0"` / `"1"` |
| 文字方向 | `textDirection` | `FromLeftToRight` / `FromRightToLeft` / `VerticalArrangement` / `CW` / `CCW` |

## 九、填报字段配置

### 9.1 填报数据类型 (FillingDataTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `Text` | 单行文本 |
| `TextArea` | 多行文本 |
| `Number` | 整数 |
| `Float` | 浮点数 |
| `Date` | 日期 |
| `Employee` | 人力资源 |
| `Department` | 部门 |
| `Subcompany` | 分部 |
| `Browser` | 浏览框 |
| `FileComponent` | 文件 |
| `ImageComponent` | 图片 |

### 9.2 填报显示方式 (FillingShowTypeEnum)

| 枚举值 | 说明 |
|--------|------|
| `Input` | 输入框 |
| `Browser` | 浏览按钮 |
| `CheckBox` | check 框 |
| `Select` | 选择框 |
| `FileUpload` | 文件上传 |
