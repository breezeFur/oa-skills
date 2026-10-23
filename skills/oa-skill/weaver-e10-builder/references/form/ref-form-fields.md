# 表单字段类型与配置

本文件维护 EB 表单字段的类型码表、选型规则和通用配置。表单结构、明细表和布局组件的创建方式见 `guide-create-form.md`。

## 通用结构

```json
{
  "componentKey": "Text",
  "fieldName": "项目名称",
  "dataKey": "xmmc",
  "columnName": "xmmc",
  "required": true,
  "readOnly": false,
  "hidden": false,
  "singleRow": false,
  "group": "基本信息",
  "defaultValue": ""
}
```

| 属性 | 说明 |
| --- | --- |
| `componentKey` | 字段类型标识 |
| `fieldName` | 字段名称 |
| `dataKey` / `columnName` | 字段编码 / 数据库列名。**两者是两个独立的东西**，可分别指定；都不写则同为字段名拼音首字母，只写 `dataKey` 时列名跟随。建后由 `add-field --data-key/--column-name`、`edit-field --column-name` 调整 |
| `required` / `readOnly` / `hidden` | 必填、只读、隐藏 |
| `singleRow` | 独占一行 |
| `group` | 所属分组 |
| `multiple` | 是否多选；`false` 为单选，`true` 为多选 |
| `defaultValue` | 默认值；人员、部门和日期写 `true` 表示动态当前值 |

## 字段类型分类

### 基本类型

| 用途 | `componentKey` | 主要配置 |
| --- | --- | --- |
| 单行文本 | `Text` | `maxLen`，缺省 100 |
| 多行文本 | `TextArea` | `maxLen`，缺省 4000 |
| 邮箱 / 电话 / 手机 / 身份证 | `Email` / `Phone` / `Mobile` / `IDCard` | `maxLen`、对应格式校验 |
| 数字 | `Number` | `precision`、`delimiter`、`percent`、`capital` |
| 金额 | `Money` | `precision`、`delimiter`、`capital` |
| 开关 | `Switch` | 开关值 |
| 附件 | `FileComponent` | 附件上传设置（**没有 `Attachment` 这个类型名**） |
| 图片 | `Image` | 图片上传设置 |
| 语音 | `AudioRecord` | 语音录制与上传 |
| 视频 | `VideoRecord` | 视频录制与上传 |

### 选项类型

| 用途 | `componentKey` | 主要配置 |
| --- | --- | --- |
| 下拉单选 | `Select` | `fieldOptions` 或 `optionTemplate` |
| 下拉多选 | `SelectMultiple` | `fieldOptions` 或 `optionTemplate` |
| 单选框 | `RadioBox` | `fieldOptions` 或 `optionTemplate` |
| 复选框 | `CheckBox` | `fieldOptions` 或 `optionTemplate` |
| 级联选择 | `Cascade` | 级联选项数据 |
| 树形选择 | `Tree` | 树形选项数据 |
| 矩阵选择 | `Matrix` | 矩阵配置 |

### 日期类型

| 用途 | `componentKey` | 主要配置 |
| --- | --- | --- |
| 日期 | `Date` | `format`、`minField`、`maxField`、`defaultValue` |
| 日期时间 | `DateTime` | `format`、`minField`、`maxField`、`defaultValue` |
| 日期区间 | `DateRange` / `DateInterval` | `format`、`startPlaceholder`、`endPlaceholder` |
| 时间 | `Time` | 格式 `HH:mm:ss`；平台组件是 `TimeComponent`（`componentKey` 与类型名不同） |

一个字段名称或业务含义同时包含开始、结束、起止、期间、周期等区间含义时，优先使用日期区间；两个独立字段分别表达起点和终点时，再使用两个日期字段并通过 `minField` / `maxField` 约束。

### 组织类型

| 用途 | `componentKey` | 主要配置 |
| --- | --- | --- |
| 人员选择 | `Employee` | `multiple` |
| 部门选择 | `Department` | `multiple` |
| 分部选择 | `SubCompany` | `multiple`（默认单选）；平台读回的组件名为 `Subcompany` |
| 共享人 | `Sharer` | 共享范围设置 |

创建“分部选择”字段使用原生组织类型 `SubCompany`，例如 `form add-field <objId> <appId> 所属分部 SubCompany`；多选时加 `--multiple`。它与“关联浏览”中选择分部数据源是两种字段配置。

### 关联类型

以下为原生关联对象码表。需求明确指向这些业务对象时，直接使用对应类型。

| 界面名称 | `componentKey` | 平台组件 | 主要配置或说明 |
| --- | --- | --- | --- |
| 关联 e-builder | `EBuilder` | `Ebuilder` | `sformId`、`dataTitle`、`displayColumns` |
| 关联项目 | `Project` | `Mainline` | 项目选择范围 |
| 关联任务 | `Task` | `Task` | 任务选择范围 |
| 关联文档 | `Document` | `Document` | 文档选择范围 |
| 关联流程 | `Flow` | `Workflow` | `target_workflow_form_name`、流程范围 |
| 关联日程 | `Agenda` | `AgendaComponent` | 日程选择范围 |
| 关联上报 | `FormData` | `FormComponent` | 上报表单、显示列、条件和数据标题 |
| 关联客户 | `Customer` | `CustomerComponent` | 客户选择范围 |
| 关联线索 | `Clue` | `ClueComponent` | 线索选择范围 |
| 关联联系人 | `Contact` | `ContactComponent` | 联系人选择范围 |
| 关联商机 | `Chance` | `ChanceComponent` | 商机选择范围 |
| 关联订单 | `Order` | `OrderComponent` | 订单选择范围；不执行客户编号未填校验 |
| 关联合同 | `Contract` | `ContractComponent` | 合同选择范围 |
| 关联产品 | `Product` | `ProductionComponent` | 产品选择范围 |
| 关联活动 | `Activity` | `ActivityComponent` | 活动选择范围 |
| 关联报价 | `Quote` | `QuoteComponent` | 报价选择范围 |
| 关联对手 | `Competitor` | `CompetitorComponent` | 竞争对手选择范围 |
| 关联绩效 | `Performance` | `KpiFlowComponent` | 绩效选择范围 |
| 关联报告 | `Report` | `WorkreportComponent` | 报告选择范围 |
| 关联考勤 | `Attend` | `AttendComponent` | `attendDateType` |
| 关联浏览 | `Browser` / `RelateBrowser` | `RelateBrowser` | 通过 `browserType` 选择浏览子类 |
| 电子发票 | `EInvoice` | `EinvoiceComponent` | 发票选择配置 |
| 行车记录 | `DrivingRecord` | `DrivingRecord` | `defaultRows` |
| 关联公文 | `RelateODoc` | `RelateODoc` | 公文选择范围 |
| 关联标签 | `RelateTag` | `RelateTag` | `range` |

#### 关联类型选型

| 需求语义 | 选择 |
| --- | --- |
| 关联电子发票 | `EInvoice` |
| 关联上报数据 | `FormData` |
| 关联合同业务对象 | `Contract` |
| 关联某张 EB 表单，如“合同信息表” | `EBuilder` |
| 关联人事合同 | `RelateBrowser`，`browserType: "hrcontract"` |
| 关联流程数据 | `Flow` |
| 浏览工作流定义 | `RelateBrowser`，`browserType: "workflow"` |
| 关联业务表单或 EB 表单数据 | `RelateBrowser`，`browserType: "form"` |

`FormData` 表示“关联上报”，与通用关联浏览中的表单浏览不是同一配置。`EBuilder` 用于关联明确的 EB 表单；`RelateBrowser + form` 用于通用表单浏览。

#### 关联 e-builder

```json
{
  "fieldName": "关联客户",
  "componentKey": "EBuilder",
  "target_form_name": "客户信息表",
  "dataTitle": "客户名称",
  "displayColumns": ["客户名称", "客户编号"],
  "multiple": false
}
```

- `sformId` 可直接指定目标表单 ID；按需求编排时也可使用 `target_form_name`，执行阶段解析为目标表单。
- `dataTitle` 指定已选数据的标题字段。
- `displayColumns` 指定选择窗口显示列；省略时使用目标表单的业务字段。
- `multiple: false` 对应单选，`multiple: true` 对应多选。

字段带出使用 `relateFrom`：

```json
{
  "fieldName": "客户名称",
  "componentKey": "Text",
  "relateFrom": {
    "ebuilderField": "关联客户",
    "sourceFieldId": "目标表单字段ID"
  }
}
```

`sourceFieldId` 使用目标表单字段的数字 ID。

#### 通用关联浏览子类

| `browserType` | 作用 | 主要配置 |
| --- | --- | --- |
| `workflow` | 浏览工作流定义 | 工作流范围 |
| `hrcontract` | 浏览人事合同 | 人事合同范围 |
| `form` | 浏览业务表单或 EB 表单数据 | `browserFormSource`、目标表单、标题和显示列 |
| `role` | 浏览角色 | 角色范围 |
| `archive` | 浏览档案 | 档案范围 |
| `hrm_sex` | 浏览人事「性别」 | — |
| `hrmJobcall` | 浏览人事「职称」 | — |

已明确的专属参数包括考勤 `attendDateType`、行车记录 `defaultRows`、标签 `range`。参数值按实际需求或接口返回配置。

业务表单浏览：

```json
{
  "fieldName": "关联业务数据",
  "componentKey": "RelateBrowser",
  "browserType": "form",
  "browserFormSource": "business",
  "target_form_name": "业务表单",
  "multiple": false
}
```

EB 表单浏览：

```json
{
  "fieldName": "关联EB数据",
  "componentKey": "RelateBrowser",
  "browserType": "form",
  "browserFormSource": "ebuilder",
  "target_form_name": "客户信息表",
  "multiple": true
}
```

### 行政区域

| 用途 | `componentKey` | 主要配置 |
| --- | --- | --- |
| 行政区域 / 城市选择 | `City` | 区域层级与选择范围 |

### 其他

| 用途 | `componentKey` | 主要配置 |
| --- | --- | --- |
| 进度 | `Progress` | 进度值范围 |
| 评分 | `Score` | 评分范围 |
| 签名 | `Signature` | 签名设置 |
| 定位 | `Location` | 位置信息；用于支持该组件的布局 |
| 颜色选择 | `ColorPicker` | 颜色值 |
| 富文本 | `RichText` | 富文本内容 |
| 文档目录 | `DocFolder` / `DocFloder` | 文档目录选择 |

## 文本、数字和日期配置

```json
[
  {"fieldName": "标题", "componentKey": "Text", "maxLen": 100},
  {"fieldName": "说明", "componentKey": "TextArea", "maxLen": 4000},
  {"fieldName": "数量", "componentKey": "Number", "precision": 0},
  {"fieldName": "金额", "componentKey": "Money", "precision": 2, "delimiter": true},
  {"fieldName": "完成比例", "componentKey": "Number", "precision": 2, "percent": true},
  {"fieldName": "开始日期", "componentKey": "Date"},
  {"fieldName": "结束日期", "componentKey": "Date", "minField": "开始日期"},
  {"fieldName": "创建日期", "componentKey": "Date", "defaultValue": true}
]
```

- 百分比字段按 0–100 的显示语义设计，公式按实际业务口径编写。
- `Number` 缺省精度为 0；`Money` 缺省精度为 2。
- `minField` / `maxField` 用于两个独立日期字段的先后约束。
- 日期字段的 `defaultValue: true` 表示默认当前日期。

## 选项、默认值与多选

```json
{
  "fieldName": "项目状态",
  "componentKey": "Select",
  "fieldOptions": [
    {"name": "审批"},
    {"name": "立项"},
    {"name": "执行"},
    {"name": "结案"}
  ]
}
```

- `valueKey` 可省略，由 CLI 生成；手工指定时使用稳定的数字字符串。
- 公共选项模板使用 `optionTemplate`；`fieldOptions` 与 `optionTemplate` 二选一。
- `multiple: false` 保存为单选（`isSingle: true`），`multiple: true` 保存为多选（`isSingle: false`）。
- `Select` 开启多选后使用 `SelectMultiple`。

```json
{
  "fieldName": "重要程度",
  "componentKey": "Select",
  "optionTemplate": "重要程度"
}
```

## 公式

```json
{
  "fieldName": "项目收益",
  "componentKey": "Number",
  "precision": 2,
  "readOnly": true,
  "formula": "{主表.项目已收款}-({主表.项目工时}*100+{主表.项目费用})"
}
```

- 公式字段通常设为只读。
- 主表字段使用 `{主表.字段名}`，明细字段按对应表和字段引用。
- 公式对象还可包含 `expression`、`returnType` 和 `name`。
- 公式、联动和校验在字段与布局初始化后使用各自命令配置。

## 相关文档

- 表单创建与主表、明细表结构：`guide-create-form.md`
- 布局：`guide-form-layout.md`
- 字段事件：`guide-field-event.md`
- 字段公式函数：`guide-form-formula-functions.md`
- CLI 命令：`../common/ref-cli-commands.md`
