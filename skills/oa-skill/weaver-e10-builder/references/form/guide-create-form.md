# 新建 EBuilder 表单

通过 `e10-cli form create` 在 EBuilder 应用中创建表单。本指南说明从需求整理、`fields.json` 编写到建后配置的完整顺序；字段参数和布局样表的详细规则按需读取专题参考。

需求以已有 EB 表单、系统业务表或数据加工结果为实际数据源时，使用 [虚拟表创建与维护](guide-virtual-form.md) 的 `form virtual` 流程。

## 标准创建流程

1. 确认目标应用 `appId`。
2. 确认布局类型：流式 `FLOW` 或表格式 `EXCEL`。布局类型在建表时确定。
3. 从需求中整理字段、明细表、字段顺序和布局要求；遇到完整布局样表时，将空间结构写入 plan 的“表单布局蓝图”。
4. 将建表时可以完成的配置写入 `fields.json`。
5. 执行 `form create`，记录返回的 `objId` 和 `formId`。
6. 使用 `form list-view` 查询并记录默认台账 `listId`。
7. 按需求完成多语言、联动、校验、权限、视图和按钮等建后配置。
8. 使用读取命令轻量核对字段、布局和默认台账。

```bash
e10-cli form create <appId> "<表单名>" --fields @fields.json --layout FLOW|EXCEL
e10-cli form list-view <objId> <appId>
e10-cli form read <objId> --app-id <appId> --out fields-created.json
```

需要同时生成台账菜单入口时，在创建命令中增加 `--menu`；建成后也可使用 `menu add-table <appId> <objId>` 添加。默认台账视图与应用菜单入口是两个资源。

### 自定义数据库表名

不指定时表名按表单名拼音首字母加随机数生成（如 `uf_xsddb_4683`）。需要固定或对齐既有命名时用 `--table-name`：

```bash
e10-cli form create <appId> "客户信息表" --fields @fields.json --table-name cs_khxx
```

- **平台前缀由 CLI 自动补**：传 `cs_khxx` 与传 `uf_cs_khxx` 结果相同（`uf_cs_khxx`）。
- **格式约束**：字母开头，只含字母、数字、下划线。前缀之外的部分受平台长度上限约束 —— 前缀 `uf_`、总长上限 30 时，自定义部分最多 27 位。越界会直接报错，不会建成一半。
- **建成后回读校验**：实际表名与预期不一致会报错，不静默通过。
- 仅对**物理表**应用有效；应用未启用物理表时该选项不适用（CLI 会先查存储设置并拒绝）。

## 各阶段配置范围

| 阶段 | 配置内容 |
|---|---|
| 需求与 plan | 表单名称、字段类型、顺序、明细结构、FLOW/EXCEL、布局蓝图及外围配置 |
| `fields.json` | 字段、选项、默认值、精度、日期格式、关联、公式、明细、分组和显示属性 |
| `form create` | 表单主体、字段、明细、布局、基础查看权限、默认台账及可选菜单 |
| 建成后 | 字段多语言、联动、查重、进一步权限、视图名称与列、筛选、按钮及关联页签 |
| 完成核对 | `objId`、`formId`、`listId`、字段结构和布局结果 |

## 建表前整理需求

### 布局类型

```bash
e10-cli form create <appId> "<表单名>" --fields @fields.json --layout FLOW
e10-cli form create <appId> "<表单名>" --fields @fields.json --layout EXCEL
```

- `FLOW`：流式布局。
- `EXCEL`：表格式布局，也是 CLI 缺省值。
- 需求未明确且布局选择会影响结果时，建表前向用户确认。
- 需求提供完整表格、合并单元格、分组标题、标签与字段交替排布时，按布局样表处理，详见 [表单布局规划](guide-form-layout-planning.md)。

### 字段定义

字段按照需求顺序写入 `fields.json`。主表字段在前，`DetailTable` 明细表放在数组末尾。

```json
[
  {"componentKey":"Text","fieldName":"合同名称","required":true,"singleRow":true},
  {"componentKey":"DateRange","fieldName":"合同有效期","format":"yyyy-MM-dd"},
  {"componentKey":"Money","fieldName":"合同金额","precision":2},
  {"componentKey":"Select","fieldName":"合同状态","fieldOptions":[{"name":"草稿"},{"name":"履行中"}]},
  {"componentKey":"Employee","fieldName":"负责人"},
  {"componentKey":"DetailTable","fieldName":"付款明细","formFields":[
    {"componentKey":"Date","fieldName":"付款日期"},
    {"componentKey":"Number","fieldName":"付款金额","precision":2}
  ]}
]
```

常用字段类型包括文本、数字、选项、日期、组织、关联、行政区域和其他类型。完整类型、关联码表及各类型属性见 [表单字段定义参考](ref-form-fields.md)；明细表通过表单结构配置创建。

## 常用字段属性

| 属性 | 作用 |
|---|---|
| `required:true` | 字段必填 |
| `readOnly:true` | 禁止手工编辑 |
| `hidden:true` | 布局中隐藏，字段仍可参与计算 |
| `singleRow:true` | 独占一行 |
| `group:"基本信息"` | 放入指定字段分组 |
| `multiple:true` | 支持多选的字段设置为多选 |
| `maxLen:500` | 文本最大长度 |
| `precision:2` | 数字或金额小数位 |
| `defaultValue` | 字段默认值 |

### 字段分组

以需求为准：只有需求明确要求字段分组时，才在 `fields.json` 中设置 `group`；需求未要求时保持不分组。

```json
[
  {"componentKey":"Text","fieldName":"项目名称","group":"基本信息","required":true},
  {"componentKey":"Employee","fieldName":"负责人","group":"基本信息"},
  {"componentKey":"Number","fieldName":"项目金额","group":"财务信息","precision":2}
]
```

同名 `group` 的字段进入同一个分组。分组内字段按字段顺序排列，需要整行展示的字段增加 `singleRow:true`。已有表单补充分组时使用：

```bash
e10-cli form group <objId> <appId> --groups '{"基本信息":["项目名称","负责人"]}'
```

### 日期区间

字段本身包含开始与结束含义，如“项目周期、合同有效期、请假时间、活动时间”，优先使用 `DateRange`。明确要求两个独立字段，或开始、结束需要分别参与公式和联动时，再拆成两个日期字段。

```json
{"componentKey":"DateRange","fieldName":"项目周期","format":"yyyy-MM-dd"}
```

### 选项和多选

```json
{"componentKey":"Select","fieldName":"状态","fieldOptions":[{"name":"启用"},{"name":"停用"}]},
{"componentKey":"Employee","fieldName":"项目成员","multiple":true}
```

`Select`、`RadioBox`、`CheckBox` 可在 `fieldOptions` 中定义选项。人员、部门、EBuilder、Browser 和 Select 等支持按字段能力设置多选。共享选项可使用 `optionTemplate`；详细结构见 [表单字段定义参考](ref-form-fields.md)。

### 关联字段

EBuilder 关联字段在创建时指定目标表单 `objId` 和显示字段：

```json
{
  "componentKey":"EBuilder",
  "fieldName":"关联客户",
  "sformId":"<目标表单objId>",
  "dataTitle":"客户名称",
  "displayColumns":["客户名称","客户类型"]
}
```

`Flow` 的 `sformId` 同样指向目标流程绑定的表单 `objId`。原生关联对象和通用浏览类型的配置码表见 [表单字段定义参考](ref-form-fields.md)；关联数据过滤和范围分别见 [EBuilder 过滤](guide-ebuilder-filter.md) 与 [关联浏览数据范围](guide-ebuilder-scope.md)。

### 明细表与二级明细

明细字段写入 `DetailTable.formFields`。二级明细关系配置在父明细表上，父明细每一行分别拥有对应的子明细数据：

```json
[
  {"componentKey":"DetailTable","fieldName":"任务明细","enableSubDetail":true,
   "subDetailConfig":[{"subForm":"工时明细","subField":"父任务标识"}],"formFields":[
    {"componentKey":"Text","fieldName":"任务名称"}
  ]},
  {"componentKey":"DetailTable","fieldName":"工时明细","formFields":[
    {"componentKey":"Text","fieldName":"父任务标识"},
    {"componentKey":"Number","fieldName":"工时","precision":2}
  ]}
]
```

父级行标识缺省使用行 ID；子级行标识必须为单行文本。多父级复用、多子级和多级嵌套的规则，以及已有表单的查询、增加、删除、启停命令见 [二级明细表配置](guide-form-sub-detail.md)。

### 表单结构与布局组件

主表字段直接写在 `fields.json` 根数组中；明细表使用 `DetailTable` 配置，并通过 `formFields` 维护其字段。主表与明细表字段采用相同的字段类型和属性规则。

布局初始化会根据表单结构生成相应的内部组件：

| 组件 | 在创建流程中的作用 |
| --- | --- |
| `DetailTable` | 定义明细表及其字段 |
| `DataTable` | 在布局中承载和展示明细表 |
| `Fold` | 承载字段分组和折叠区域 |
| `Placeholder` | 维护布局中的占位位置 |
| `EbuilderAppTag` | 维护 EB 应用相关的布局标签 |

业务字段从字段类型码表中选择；以上结构与内部组件由明细表、分组和布局配置生成与维护。

### 字段公式

可在目标字段中写 `formula`，由创建流程完成公式创建和字段绑定：

```json
{"componentKey":"Number","fieldName":"项目收益","formula":"{主表.已收款}-{主表.项目费用}"}
```

公式表达式、明细汇总和函数格式见 [字段公式函数参考](guide-form-formula-functions.md)。复杂编号属于建后配置，见 [表单复杂编号](guide-form-serial-mark.md)。

## 执行创建

```bash
e10-cli form create <appId> "采购合同" --fields @fields.json --layout EXCEL
```

创建流程会依次完成表单主体、字段和明细、布局初始化、字段高级属性、关联关系、选项、公式、分组、基础查看权限及默认台账配置。传入 `--menu` 时同时添加台账菜单入口。

记录命令返回的：

- `objId`：EB 表单业务对象 ID，多数 `form` 命令使用它。
- `formId`：底层表单 ID，布局和部分底层接口使用它。
- `listId`：默认台账 ID，通过 `form list-view` 查询。

## 建成后配置

按需求执行，未提出的配置不额外增加：

| 需求 | 命令或指南 |
|---|---|
| 字段中英文名称 | `form field-lang set` |
| 字段显隐、只读、必填联动 | [表单联动](guide-form-linkage.md) |
| 字段查重 | `form validate` |
| 表单和数据权限 | `form permission` |
| 默认台账改名、列、筛选和分组 | [表单视图](guide-form-view.md) |
| 表单及视图按钮 | [表单按钮](guide-form-button.md) |
| 关联页签 | [表单关联页签](guide-form-association.md) |
| 复杂编号 | [表单复杂编号](guide-form-serial-mark.md) |

需求写成 `中文/English`（如 `项目/project`）时，先以中文名称创建字段，再设置多语言：

```bash
e10-cli form field-lang set <objId> <appId> <fieldId> --zh "项目" --en "project"
```

## 完成核对

使用与本次需求直接相关的读取命令核对即可：

```bash
e10-cli form read <objId> --app-id <appId> --out fields-created.json
e10-cli form list-view <objId> <appId>
e10-cli form layout read <objId>
```

重点确认字段数量与类型、明细结构、分组和显示属性、布局类型、默认台账名称与 `listId`。需要菜单时再确认菜单入口。

## 专题参考

- [表单字段定义参考](ref-form-fields.md)：完整字段类型、属性、关联类型和 JSON 结构。
- [表单布局规划](guide-form-layout-planning.md)：FLOW/EXCEL、布局样表、布局蓝图及建后调整。
- [表单复杂编号](guide-form-serial-mark.md)：编号段、流水和代字配置。
- [字段公式函数参考](guide-form-formula-functions.md)：公式表达式和函数。
- [表单视图](guide-form-view.md)：默认台账、视图名称和列表配置。
