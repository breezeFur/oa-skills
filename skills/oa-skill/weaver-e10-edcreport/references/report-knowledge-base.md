# e-Builder 报表功能知识库

> **冷启动禁止通读**：见 `cold-start-scan-guide.md`。仅文档与引擎冲突、或用户要源码级对齐时再读相关节（优先第九节）。

## 一、报表设计器布局

报表设计器采用左中右三栏布局：
- **左侧栏**：数据集添加展示区，支持添加多个数据集，支持快捷搜索字段
- **中间区域**：报表设计展示区，即单元格编辑区域
- **右侧栏**：单元格基本信息设置区（父格、扩展方向、显示方式、分组排序、字段转换、父格筛选等）

### 顶部 Ribbon（开始 / 页面 / 公式）

设计器 URL：`/sp/edc/report/designer/{reportId}`。**完整功能清单与 API 对照见 `report-designer-feature-map.md`**。

**Tab「开始」**：保存 / 存为新版本 / 预览 / 历史版本 / 数据分析 / 代码块；字体与对齐；数字格式；条件格式（突出显示、数据条、图标集）；查询条件快捷入口。

**Tab「页面」**：查询设置与添加条件；单元格冻结；样式（主题模板、配色交替）；打印与分页；报表展示（列排序、子格合并、行式加载、数据预聚合、分栏、按钮控制）；页面布局（网格线、树形展开、显示位置）；快照设置；填报与二维组件。

**Tab「公式」**：插入函数（数学/逻辑/文本/日期/信息）；单元格内 `=` 联想；API 写入规则见 `formula-cell-api-guide.md`。

**右上角**：保存、预览、历史版本（与开始 Tab 重复入口）。

### 高级设置（页面 Tab 汇总，旧称）
- 报表展示设置：冻结单元格、背景图片、行号列头网格线
- 报表显示位置：居中或居左
- 解析优化：行式加载（优化列表解析速度）、数据预聚合（默认开启，按分组聚合逻辑解析）
- 分页设置
- 打印设置
- 列排序筛选

## 二、核心配置概念

### 2.1 父格（关键概念）
父格是报表中最核心的配置，决定了单元格数据的扩展参照关系。

- **左父格**：控制单元格纵向扩展时的分组参照。默认情况下同行的左侧相邻单元格为左父格。
- **上父格**：控制单元格横向扩展时的分组参照。默认情况下同列的上方相邻单元格为上父格。
- **自定义父格**：手动指定参照的单元格，用于跨数据集关联或特殊分组需求。
- **父格筛选**：当多个数据集字段需要关联时，通过父格筛选配置关联关系。跨数据集时必须同时配置 **subordination** + **leftFilterField**，字段引用使用 **fieldKey**（`{dataSetId}.{sourceId}.{fieldName}`）。详见 `cross-dataset-filter-guide.md`。

**父格配置原则：**
1. 分组字段通常作为其右侧/下方字段的父格
2. 交叉区域的字段左父格通常不能默认，需自定义
3. 交叉区域后的字段（公式或字段值）左父格也不建议默认
4. 多行配置不同科目数据时，需要给所有行第一列字段设置统一父格
5. 当字段左父格自定义为某分组字段但未正常合并时，可开启"子格合并"或添加辅助列

### 2.2 扩展方向
- **纵向扩展**：数据向下展开，一行一条记录（最常用）
- **横向扩展**：数据向右展开，一列一条记录（用于交叉报表的列头）
- **不扩展**：固定单元格，不随数据变化（用于标题、合计行等）

### 2.3 显示方式
- **分组**：相同值合并显示为一条
- **排列**：所有数据一一展示，不合并
- **汇总**：按父格分组进行聚合计算
  - 汇总方式：求和、计数、计数(去重)、最大值、最小值、平均值
- **树形**：按字段上下级关系分层级展示
- **隐藏内容**：分组后可隐藏明细，仅显示分组汇总

### 2.4 日期分组
日期类型字段设置分组时支持：
- 不设置（保持原值）
- 按年份分组（如2025-03-28 → 2025）
- 按年月分组（如2025-03-28 → 2025-03）

### 2.5 自定义筛选
用于在单元格级别过滤数据。**API/脚本配置时** `currentField` 和 `id` 必须使用 fieldKey，type 使用平台枚举（`Equals`、`NotContain`、`Null` 等，不用 `eq`/`uncontains`）。详见 `cross-dataset-filter-guide.md`。

示例（设计器 UI 或需求描述）：
- `年度={year}`（筛选当年数据）
- `年度={year:-1}`（筛选去年数据）
- `年度 开头是 {year}`（年度字段存储的是日期格式时）
- `一级预算科目 包含于 41,42`
- 多个条件用 or 连接

### 2.6 字段转换设置
支持给字段设置不同的转换规则实现展示多样化：
- 突出显示（条件背景色、字体色）
- 条码转换
- 等等多种规则叠加

### 2.7 单元格格式
- 数字格式：支持设置小数位数、数据单位、单位后缀、千分位转换
- 百分比格式：当前数据/数据合计的占比
- 货币格式
- 自定义日期格式

## 三、数据集配置

### 3.1 数据集类型
- e-builder表单
- 数据加工（SQL视图）
- 外部数据源
- 业务模块
- ESB中心

### 3.2 数据集操作
- **添加数据集**：左上角"+"，支持多选
- **数据预览**：展示10条数据确认数据源
- **筛选条件**：支持or和and组合，当前报表所有sheet页引用此数据集均为过滤后数据
- **数据聚合**：提前分组汇总，简化报表配置
- **排序**：支持多字段排序，最前面的优先级最高
- **替换数据集**：快速替换原有报表中的数据集字段
- **移除数据集**：被引用时无法删除

## 四、报表类型与配置模式

### 4.1 简单列表报表
**适用场景**：逐条展示数据，无分组汇总
**配置要点**：
- 所有数据字段：左父格默认，上父格无，纵向扩展，显示方式：排列
- 标题行：左父格无，上父格无，不扩展
- 可开启行式加载优化解析速度
- 快速构建入口：新建报表 → 快速构建-列表式（API：`quicklyParam`，见 `report-create-modes-guide.md` / `edc-report create quick`）
- 模版创建入口：新建报表 → 模版创建（`getReportModels` + `reportModel`，见同指南）

### 4.2 分组报表
**适用场景**：按维度分类汇总展示
**配置要点**：
- 分组字段：左父格默认，上父格无，纵向扩展，显示方式：分组
- 汇总字段：纵向汇总求和（或其他汇总方式），左父格默认
- 合计行：合并单元格，设置左父格为分组字段，不扩展
- 总计行：左父格无，上父格无，不扩展
- 公式计算：可用Excel公式进行分组计算

**示例配置**：
```
C4~G4（分组字段）: 左父格默认, 上父格无, 纵向扩展, 显示方式:分组
H4（金额字段）: 纵向汇总求和, 左父格默认
合计行 D5~G5合并: 左父格自定义C4, 上父格无, 不扩展
总计行 C6~G6合并: 左父格无, 上父格无, 不扩展
```

### 4.3 交叉报表
**适用场景**：多维度交叉展示数据（如按人员×月份展示金额）
**配置要点**：
- 纵向维度字段：左父格默认，上父格无，纵向扩展，显示方式：分组
- 横向维度字段：左父格无，上父格无，横向扩展，显示方式：分组（日期可设置按年月分组）
- 交叉区域字段：左父格自定义（纵向最后一列），上父格自定义（横向字段），纵向扩展，显示方式：汇总求和
- 交叉区域下方自定义文本：左父格无，上父格自定义（横向字段），不扩展
- 交叉区域后的字段：左父格需自定义，不能默认

**示例配置**：
```
B5~E5（纵向维度）: 左父格默认, 上父格无, 纵向扩展, 显示方式:分组
F3（横向维度）: 左父格无, 上父格无, 横向扩展, 显示方式:分组(按年月), 降序
F4~H4（横向表头文本）: 左父格无, 上父格自定义F3, 不扩展
F5~H5（交叉数据）: 左父格自定义E5, 上父格自定义F3, 纵向扩展, 显示方式:汇总求和
I5~J5（交叉后字段）: 左父格自定义E5, 上父格默认, 纵向扩展
```

**数据合计配置**：
```
大区合计行: 左父格自定义B5, 上父格无, 不扩展
合计行的交叉区域: 左父格自定义B8, 上父格自定义F3, 不扩展
总计行: 左父格无, 上父格无, 不扩展
```

### 4.4 自由布局报表
**适用场景**：记录分块或分页显示，非标准行列展示
**配置要点**：
- 确定主字段（如E3）：左父格无，上父格无，纵向扩展，排列展示
- 其他所有字段：左父格自定义E3，上父格无，纵向扩展，排列展示
- 自定义文本内容：左父格自定义E3，上父格无，不扩展
- 条码字段：开启条码转换

### 4.5 填报报表
**适用场景**：多级填报，支持数据录入
**配置要点**：
- 主表字段：支持单行文本、多行文本、整数、浮点数、日期、人力资源、部门、关联浏览、下拉框、check框
- 明细表字段：选中区域 → 添加明细，可设置包含标题
- 字段属性：只读、编辑、必填（默认编辑）
- 明细表字段额外属性：新增行、删除行开关
- 选择框联动：父级选择框限定子级选择框可选内容
- 封存选项：填报时不展示

### 4.6 树形报表
**适用场景**：按字段上下级关系分层级展示
**配置要点**：
- 树形字段：左父格无，上父格无，纵向扩展，显示方式：树形
- 从属关系：人员字段=上级字段（通过id值匹配）
- 其他字段：左父格默认，上父格无
- 默认收起，可设置默认展开：页面 → 页面布局 → 数据展开 → 树形

### 4.7 分栏报表
**适用场景**：数据量大的报表分栏展示
**分栏方式**：
1. **横向分栏**（纵向扩展数据）：按行/列数分栏，复制标题行（如2-3），触发分栏行数
2. **纵向分栏**（横向扩展数据）：按行/列数分栏，复制表头列（如B-E），触发分栏列数
3. **垂直分栏**（纵向扩展数据）：按栏数分栏，设置栏数，复制标题行
4. **水平分栏**（横向扩展数据）：按栏数分栏，设置栏数，复制表头列
5. **卡片分栏**（纵向扩展数据）：按栏数分栏，设置栏数+复制单元（整体扩展单元首尾单元格）

### 4.8 多横向维度交叉报表
**适用场景**：两层横向维度交叉
**配置要点**：
- 纵向维度：左父格默认，上父格无，纵向扩展，分组
- 第二层横向维度：左父格自定义（纵向最后一列），上父格自定义（第一层横向），纵向扩展，分组
- 第二层横向表头：左父格无，上父格自定义（第一层横向），不扩展
- 第一层横向维度：上父格默认，左父格无，横向扩展
- 顶层横向维度：上父格无，左父格无，横向扩展

### 4.9 一个sheet页多报表展示
**配置要点**：
- 使用A1单元格放自定义文本作为统一父格
- 每个报表区域的第一列字段左父格自定义A1
- 避免样式错乱

### 4.10 预算科目统计报表
**适用场景**：多行不同科目分类数据展示
**配置要点**：
- 年度字段结合自定义筛选展示今年/去年数据
- 每行第一列字段左父格自定义A1（统一父格）
- 自定义筛选按科目类型过滤
- 百分比格式设置
- 父格沿用自定义筛选结果

## 五、查询条件配置

### 5.1 查询条件设置
- 入口：报表设计器 → 查询条件设置
- 支持条件类型：文本、日期、日期区间、下拉框等
- 查询条件标识：{searchfield001}、{searchfield002}等
- 可在单元格中引用查询条件值作为表头
- 日期区间可设置默认选取（如本周）
- 可开启必填避免无数据

### 5.2 系统参数（查询条件默认值）

设计器「默认值类型 = 自定义」时，在 `defaultValue` JSON 数组中使用：

| 参数 | 含义 | 典型 defaultValue |
|------|------|-------------------|
| `{thismonth}` | 本月区间 | `["{thismonth}",""]` |
| `{date}` | 今天 | `["{date}","{date}"]` |
| `{thisweek}` | 本周 | `["{thisweek}",""]` |
| `{thisyear}` | 今年 | `["{thisyear}",""]` |
| `{year}` | 当前年份 | 用于文本/等于类条件 |

完整说明见 `query-condition-api-guide.md` §5。`{today}` 无效，请用 `{date}`。

### 5.3 查询条件传参（事件链接）

> 权威写法见 **`event-hreflink-guide.md`**。

- 报表 **事件** 动作支持传递 **单元格值**（当前格、父格、父格的父格）
- 支持传递 **查询条件值**：`{searchfield001}` 等（对应条件 `asNameIndex`）
- 单元格坐标写法：`{L4}` / `{A1}`，或手册示例 `?ry=B5&kssj=E3`
- 打开方式：`blank`（弹出页）/ `self`（当前页）/ `jsscript`（执行 JS）

## 六、常见配置场景

### 6.1 序号字段
- **场景一**（末列递增）：序号字段左父格默认，纵向扩展
- **场景二**（首列递增）：序号字段上父格必须设置，左父格自定义（参照字段）
- **场景三**（分组合并自增）：添加辅助列（分组字段），序号和辅助列左父格均默认
- **场景四**（分类重新递增）：上父格默认，左父格自定义（参照字段），参照格自定义（分组字段）

### 6.2 字段分组合并
- 方案一：开启子格合并
- 方案二：添加辅助列字段（必须为分组字段的子集），辅助列左父格默认

### 6.3 空值显示为0
- 方案一：设置字段显示方式为汇总
- 方案二：使用Excel的if公式判断

### 6.4 冻结表头
- 冻结单元格冻结当前字段的左侧及上方区域
- 去除延长线代码：`excel.workbook.getActiveSheet().options.frozenlineColor = 'Transparent';`

### 6.5 隐藏预览页面按钮
- 链接拼接hidetop=1隐藏顶部按钮
- 代码块隐藏sheet页签：`<style>.ant-col-sm-9{display: none}</style>`

### 6.6 跳转数据列表页

- 单元格配置 **事件** 动作，填写 PC/H5 链接地址（`pcHreflink` / `h5Hreflink`）
- 拼接参数示例：`/sp/ebdfpage/list/xxx?ry=B5&kssj=E3`（取单元格展开值）
- 亦可：`/sp/ebdfpage/card/0/{sourceId}/{L4}?q={searchfield001}`
- 支持传当前字段值及父格值；细则见 `event-hreflink-guide.md`

## 七、二维图表组件

- 位置：页面 → 二维报表组件
- 无需配置父格和扩展方向，直接选取维度项和指标项
- 横向维度/纵向维度：支持多字段，支持分组/排列、排序
- 指标：仅支持数值类型和数据id字段，支持求和/计数/计数(去重)/最大值/最小值/平均值
- 合计：行合计、列合计、行分组合计、列分组合计
- 链接跳转：携带维度项和系统参数传值

## 八、报表组件（页面嵌入）

- 选取当前应用下的后端报表展示
- 支持选择sheet页
- 可设置网格线、行号列头、打印辅助线、子格合并
- 报表筛选需结合页面筛选组件使用

---

## 九、源码级隐性规则（基于 weaver-common-edc 源码，文档冲突以代码为准）

> 以下规则来自对 `D:\edc_source\weaver-common-edc` 四个模块（base / dataset / report / report-analysis，共约 8.8 万行 Java）的逐文件核查。**当本知识库其它章节的描述与源码不一致时，一律以源码为准。**

### 9.1 引擎选择与报表类型映射（代码事实）
- 渲染引擎工厂 `Engine.getInstance(sheet.getQuickType())`（`SplitUtilThread.java:70` / `Engine.java:18-26`）：
  - `QuickType.Custom` → `CustomEngine`（自由布局，手动指定左/上父格坐标）
  - `QuickType.SimpleList` → `SimpleListEngine`（行式列表，无分组聚合）
  - 其它（默认）→ `GroupCrossEngine`（分组 + 交叉，x 列维 / y 行维 / z 度量）
- **结论**：报表类型不是用户随意选的"展示形态"，而是由底层 `QuickType` 决定走哪套引擎；分组/交叉/树形/合计均运行在 `GroupCrossEngine` 之上。

### 9.2 父格解析与循环依赖（代码事实）
- 父格以坐标表达：`leftX/leftY`、`topX/topY`（`AnalysisField.java:82-93`）。
- `CustomEngine` 用 `fieldMap.get(sheetIndex, leftX, leftY)` 反查父格并 `setLeftParent/setTopParent`；`left==field` 时跳过（防自引用）；无父→`rootFields`，双父→`crossFields`。
- `GroupCrossEngine` 把 xFields 串成 `topParent` 链、yFields 串成 `leftParent` 链；zFields（度量）同时挂 `topParent=最后一个xField`、`leftParent=最后一个yField` → 交叉字段。
- **循环依赖是保存必校验项**：`ReportBiz.checkCyclicDependence(fields)` 为 true 时抛 `ReportException("存在父格循环依赖或者左、上父格设置相同单元格的情况，请检查！")`（label 213247）；当 `leftX==topX && leftY==topY`（左、上父格为同一格）直接判为循环。
- **注意**：引擎内部并无实时环检测，仅保存时校验；配置坐标成环会导致布局错乱而非抛异常。

### 9.3 扩展方向与聚合计算（代码事实）
- 枚举 `AnalysisExpandType` = `NoExpand / Horizontal / Vertical`；标题格默认 `Horizontal`。
- 真实扩展由 `AnalysisUtil.expandCell` + `OffSet` 偏移实现：子格被推到父格扩展末端；交叉区在 `BaseEngine.analysisCrossField` 按 `leftParent×topParent` 坐标分组，取首个可扩展子格类型决定整体方向。
- **聚合算法**（`DataSetEngine.getListLikeMap`）：
  - `sum`：`BigDecimal` 累加，初值 `ZERO`；`min/max`：流比较；`avg`：`sum/size`，`divide(scale=10, ROUND_HALF_UP)`，`size==0` 返回 `ZERO`；`count`：分组数据集取 `s_*_*` 整数字段求和，否则计非空 map 数；`distinctcount`：按 `dataSetKey` 去重。
  - **Null 处理**：`sum/min/max` 用 `getBigDecimalValue(v, ZERO)`（null→0）；`avg` 先过滤 null 再除；聚合 key 用 `NumberFormat` 最多 10 位小数。
  - **预聚合（SQL 下推）**：当"全部分组字段可分组、无自定义/结果筛选、排序仅含分组字段"时，`BaseEngine.initDataSetByGroup` 构造 `EdcDatasetAggregateDto(groupBy+countType)` 走 `queryForListGroupByFields`，打 `QuickTypeTag=GroupQuery`。
- **合计/小计不自动插入**：引擎不会自动加合计行。合计由设计器在分组旁放置一个 `AnalysisDisplayType.Count` 单元格实现（其聚合值即渲染值）；树形字段组内合计通过 `groupCountConfig`（location first/last）插入；总计 `COMB_GRAND_TOTAL` → 转 `SUM(...)`。
- **占比/同环比是公式，不在 Java 端计算**：`AnalysisField.initFormula` 中 `COMB_GROWTH_RATE/COMB_DYNAMIC_RATE/COMB_DIFF` 仅生成 `IFERROR+原串`，`COMB_GRAND_TOTAL` 生成 `SUM+原串`；同比增长率/环比/差值的具体算术在 **SpreadJS 前端计算引擎**执行，Java 端无对应算式。

### 9.4 时区转换（代码事实 —— 帮助文档未覆盖）
- **全仓库无任何时区配置字段**：grep `timeZone/zoneId/时区` 仅命中 `DateUtil.java`，且写死 `GMT+8`（北京时间），不存在 `timeZoneId`/`timeZone` 等数据集或报表配置项，也无默认值逻辑。
- **应用位置**：仅在结果集映射阶段、且只对 `field.isDate()` 字段触发（`YunConnect/LocalViewConnect/DataSetConnect` 的 `switchDate`）。
- **唯一转换**：`DateUtil.timeZoneTransfer` 写死 `source="0"、target="+8"`，即"假定源是 GMT+0，转成 GMT+8"；server→DB 方向无任何转换。
- `switchDate` 分支条件（`YunConnect` 为例）：
  - `length==13`（epoch 毫秒）→ 用 JVM 默认时区 `format "yyyy-MM-dd HH:mm:ss"`
  - `length==21` → `substring(0,19)`，无转换
  - `length==29 && contains("T")` → 触发 `timeZoneTransfer`（**唯一时区转换分支**）
  - 其它 → 原样返回
- **隐式规则（极易踩坑）**：
  1. 源时区被忽略：即使 ISO 串自带偏移（如 `+09:00`），代码先 `substring(0,19)` 丢弃偏移再硬按 `GMT+0` 解析，非 UTC 源会算错。
  2. 设计预览 ≠ 运行预览：`EdcReportDevDesignServiceImpl.switchDate`（设计态）只有 13/21 两个分支，**没有 `T` 的时区转换分支**——设计预览不做 +8，运行态做。
  3. 13 位毫秒分支依赖 JVM 默认时区（无显式 setTimeZone），仅因服务器通常在国内才"恰巧"+8；非 +8 服务器此处结果偏移。
  4. 只对 `isDate()` 字段生效；基础类型、Map/List、select/browser 字段一律跳过。
  5. 多数据库（mysql/oracle/sqlserver/pg/dm）**无差异**：无 `convert_tz/FROM_TZ/AT TIME ZONE`，时区逻辑纯 Java 层。

### 9.5 参数校验与静默改值（代码事实）
- **报表名校验不在保存事务内**：`checkReportName`（`EdcReportDevBaseServiceImpl:2758-2784`）在新增时校验许可数量（`count>aliveCount && aliveCount!=-1 → OUT_OF_NUMBER`）与重名（`SAME_NAME`）；但 `saveReportDevInfo/doAddReportBaseInfo` 自身不调用该检查，仅前端先调 `checkReportName` 防御——**保存事务内无二次校验**。
- **乐观锁**：`designKey` 与缓存不符 → "您当前的数据不是最新的，请重新打开获取最新的数据！"（label 284414）。
- **查询参数解析**（`QueryParamsBuilder`）：
  - 字段名按固定格式 `name.split('.')[2]` 解析；名称不含 2 个 `.` 会 `ArrayIndexOutOfBoundsException`，无格式校验。
  - 别名 `length>25` 时生成 `f_<uuid>` 别名。
  - **缺失必填参数不报错**，仅跳过该 filter（`filterList.isEmpty → new ArrayList`），查询照常执行。
  - `SELECT` 非数字值兜底：有 `selectId` 用 `selectId`，否则非数字 value 置 `"-1"`。
  - **SQL 注入防护**：`sql_where` 类型经 `LZString.decompress → buildOnlySearchField`（占位符 `searchfield00x`）→ `QueryFilterBiz.buildSqlWhereParams` 参数化，未见原始拼接。
  - 范围值拆分：日期/数字 EQ/RANGE 拆 GTE+LTE；数字 NEQ 拆 LT+GT 并生成新 groupId；其它 func 不合法时"不做处理"。
- **静默改值（不抛异常）**（`ReportConfigConverter.applyDefaultFieldValues`）：
  - `xCount<=0→1`、`yCount<=0→1`；空 JSON 数组默认 `[]`；`orderType` 空→`"no"`、`openType` 空→`"blank"`、`thumbnail` 空→`"NoDisplay"`、`subordination` 空→`"[\"\",\"\"]"`、`valueCompletion`→`"{}"`；`colVisible/rowVisible` 空→`"1"`；`cellType=="Field" && transType` 空→`"default"`；`refX==0&&refY==0 → refX=refY=-1`。
  - 设计服务中字段 `cellType` 为 null/空串时**静默跳过该单元格**（不入库）。
- **AI 配置保存**（`ReportConfigSaveServiceImpl`）：`@Transactional(rollbackFor=Exception.class)`；`validateParams` 仅做循环依赖检查；`user==null → ReportException("user is required")`；更新路径只补齐缺失 sheet 不删已有；按 `uniqKey` 增量增/改/删，重复 `uniqKey` 跳过。

### 9.6 多端差异化（代码事实）
- **归属类型** `BelongAttr`：`PC("0")`、`MOBILE("1")`、`PCMOBILE("2")`；**默认均为 PC**（`SearchConditionItem`/`SplitTableColBean` 构造时 `belong=PC`）。即查询条件/列默认只给 PC，需显式改为 MOBILE/PCMOBILE 才在移动端出现。
- **移动端视图/展示类型**：`MobileViewTypeAttr`：`HIGHLIGHT("1")`、`DETAIL("2")`；`MobileShowTypeAttr`：`ListView("listview",0)`、`Table("table",1)`；`SplitTableBean` 默认 `mobileshowtype=ListView`（移动端默认走列表/卡片，而非 PC 网格表）。
- **不做 UA 嗅探**：`ParamUtil` 仅透传 `user-agent` 头；真正分支来自请求参数 `isMobile`：`AnalysisParams.isMobile = "true".equals(params.getString("isMobile"))`，由上游门户（PC Web / eMobile / 企微 / 小程序）决定。
- 引擎内唯一使用点（移动端超链接替换）：`CustomEngine`/`SimpleListEngine` 中 `if(isMobile && mbhreflink 非空) 用 mbhreflink 覆盖 PC 链接`；`GroupCrossEngine.getFields(...,isMobile)` 未对移动端特殊处理——**交叉表在后端不禁用**，由前端按终端决定呈现。
- **隐式规则**：`belong=PC` 的列与查询条件在移动端不渲染；字段有 `mbhreflink`（移动端链接）、浏览按钮 `BrowserBean` 区分 `linkUrl`(PC) 与 `mobileLinkUrl`(移动)、`ddUrl`(钉钉)；企微/小程序统一归入 `isMobile=true` 路径。浏览按钮单/多选由 `MULT_BROWSER_TYPE` 列表判断（注意 `BrowserConstant`/`BrowserBean`/`Util.isMultiBrowser` 三处列表略有出入，属潜在不一致）。

### 9.7 合法枚举值清单（构建/原型必须以这些值为准）
- 单元格类型 `AnalysisCellType`：`Const, Field, Formula, DateTime, AllCheck, SequenceNumber, SystemField, Control, TreeField, DateField`
- 扩展方向 `AnalysisExpandType`：`NoExpand, Horizontal, Vertical`
- 显示方式 `AnalysisDisplayType`：`Group, List, Count, Tree`（默认 `Group`）
- 缩略图 `AnalysisThumbnail`：`Display, NoDisplay`（默认 `NoDisplay`）
- 文字方向 `AnalysisTextDirection`：`FromLeftToRight, FromRightToLeft, VerticalArrangement, CW, CCW`（默认 `FromLeftToRight`）
- 字段类型 `EtFieldType`：`String, Date, Number, Select, BusinessData`
- 条件函数 `FuncType`：`eq, neq, gt, lt, gte, lte, startWith, endWith, contains, uncontains, aggregate, unaggregate, empty, nempty, range`
- 聚合方式（SQL/Java）：`SUM, MAX, MIN, AVG, COUNT`（含 `COUNT DISTINCT`）
- **写入 DB 的默认枚举字符串**：`expandType→"NoExpand"`、`cellType→"Const"`、`thumbnail→"NoDisplay"`、`displayType→"Group"`、`textDirection→"FromLeftToRight"`

### 9.8 文档与代码冲突速查（以代码为准）
| 帮助文档/直觉说法 | 源码事实 | 正确结论 |
|---|---|---|
| 合计行由报表自动生成 | 引擎不自动插入合计，需手动放 `Count` 单元格 | 合计/小计均为手动放置 |
| 同环比在后端计算 | `COMB_*` 仅生成 `IFERROR/SUM` 公式串，算术在 SpreadJS 前端 | 占比/同环比是前端公式 |
| API 写入公式与手动相同（带 `=`） | `EdcReportDevDesignServiceImpl` 原样持久化 `cell.getFormula()`；设计器保存去 `=` | API 存储 `cellText` **无前导 `=`**，见 `formula-cell-api-guide.md` |
| IF 公式 API 不可用 | 实测为 `=` 前缀 + 错误 countType/displayType 导致空白 | IF/IFERROR 可用，须 `countType=count`、`displayType=Group` |
| 报表支持配置时区 | 全仓库无时区配置字段，写死 GMT+8 且仅 isDate 字段、运行态才转换 | 时区不可配置、仅运行态+8 |
| 保存时会校验报表名/重名 | `checkReportName` 不在保存事务内，仅前端防御 | 后端保存事务不二次校验重名 |
| 移动端自动适配 | 无 UA 嗅探，靠 `isMobile` 参数 + `belong`/`mbhreflink` 元数据 | 必须显式配置 belong=MOBILE |
| 查询参数缺失会报错 | 缺失必填参数静默跳过 filter | 不报错、照常查询 |
