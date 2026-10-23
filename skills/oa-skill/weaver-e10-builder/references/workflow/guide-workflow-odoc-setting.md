# 公文设置指南

## 使用范围

本指南用于配置原生公文流程的专属设置。先从 [公文流程指南](guide-workflow-odoc.md) 完成流程、表单、节点和出口，再按本指南配置正文、模板、痕迹、编号、附件区、归档和智能助手等内容。

所有环境读取与配置均使用 `e10-cli`：

```bash
e10-cli workflow odoc setting get <workflowId>
e10-cli workflow odoc setting set <workflowId> --config @odoc-setting.json
```

`setting get` 返回当前环境实际提供的设置分组、当前值、候选字段和候选控件。配置前先读取，按需求选择设置项；配置后再次读取核对。

## 已验证的通用规则

- `setting set` 先读取当前完整配置，只合并本次指定项，再整包保存；未指定的设置保持原值。
- 保存后自动回读比对，配置是否生效以回读结果为准。
- 字段选择值保存为字段 ID；显式字段参数支持字段名称或字段 ID。
- 节点参数支持节点名称或节点 ID。节点名称在同一流程内重复时，命令停止并返回候选节点 ID，不自动选择。
- `--open-text-select 2` 时使用 `--open-text-node` 指定一个或多个节点；`--edit-text-node` 同样支持多个节点。
- `--ai-abstract`、`--ai-format` 属于公文助手子能力，启用时同时配置 `--ai-odoc 1`。
- `odocNumber`、`odocAttachArea` 保持嵌套对象；`signNode` 以 `signNodeList` 保存；其他普通分组字段平铺到保存报文顶层。
- 已配置的节点清单读回为 `{name,id}` 数组，保存时转换为节点 ID 串；重复修改设置时同样按此形状保存。签章节点数组保持对象结构。

## 配置方式

公文设置有三种使用方式：

- **显式参数**：常用字段、节点和开关直接使用命令参数。
- **结构化配置**：其余已明确结构的设置写入 `--config @文件`。
- **专用配置**：目录、模板、字段映射等需要选择业务对象的设置，先查询候选资源，再按对应章节配置。

配置文件可使用业务分组包装，CLI 会将普通分组字段合并到完整保存报文：

当前可用的配置包装名称为 `basic`、`text`、`files`、`nodes`、`signature`、`archive`、`ai`；`number` 映射为 `odocNumber`，`attachmentArea` 映射为 `odocAttachArea`。也可以直接在配置对象顶层填写平台配置键。

```json
{
  "basic": {
    "officialType": "1",
    "requestTitleField": "字段ID",
    "documentTitleField": "-102",
    "openTextDefaultSelect": "2",
    "openTextDefaultNode": ["节点ID"],
    "editTextNode": ["节点ID"],
    "editorReadOnly": true,
    "previewDefault": true
  }
}
```

字段选择值使用字段 ID；节点选择可在显式参数中使用名称或 ID，在 JSON 中使用节点 ID。开关在 JSON 中使用布尔值或 `0/1`，CLI 保存时转换为平台要求的形状。

## 配置分组总览

| 平台分组 | settingKey | 包含内容 |
|---|---|---|
| 基础设置 | `base` | 公文类型、标题、正文字段、目录、正文节点和预览 |
| 常用功能 | `common` | 新建正文、上传格式、正文版本、流程草稿、签字意见分组 |
| 正文显示设置 | `textDisplay` | 表单内显示、分栏、位置、比例、应用节点和重新上传 |
| 痕迹设置 | `trace` | 留痕、审阅、隐藏痕迹、清稿节点 |
| 其他设置 | `other` | 附件转换、打印下载、标题同步、客户端插件和保存提醒 |
| 模板设置 | `template` | 套红模板、编辑模板、打印模板 |
| 排版设置 | `format` | 排版模板 |
| 签章节点设置 | `signNode` | 节点签章、启用与必填 |
| 正文动作设置 | `docAction` | 正文动作规则 |
| 公文字段设置 | `fieldSetting` | 公文字段配置 |
| 内部交换设置 | `innerExchangeSetting` | 内部交换配置 |
| 公文编号设置 | `odocNumber` | 文号字段、类型、出口和编辑节点 |
| 附件区设置 | `odocAttachArea` | 展开方式、字段、比例、节点和角标 |
| 文种变更设置 | `odocTypeChangeSettings` | 文种变更规则 |
| 公文环节映射设置 | `processRelativeSetting` | 公文环节映射 |
| 在线签批设置 | `wellSignSettings` | 在线签批配置 |
| 公文元数据设置 | `metaDataSettings` | 公文元数据 |
| 归档管理设置 | `Archive` | 预归档节点、触发方式、表单和字段映射 |
| 智能助手 | `OdocAi` | 公文助手、事务公文、智能排版和默认格式 |

## 基础设置

| 设置项 | 配置键 | 值与依赖 | 当前 CLI 配置方式 |
|---|---|---|---|
| 公文类型 | `officialType` | `1` 发文、`2` 收文、`3` 签报 | **CLI 已支持**：`--official-type 1|2|3` 或 JSON |
| 流程标题 | `requestTitleField` | 单行或多行文本字段 | **CLI 已支持**：`--request-title-field <字段名或ID>` |
| 正文字段 | `flowDocField` | 单选文档浏览框，候选项以 `setting get` 为准 | **CLI 部分支持**：JSON 写字段 ID，非空字段尚未验证 |
| 正文标题 | `documentTitleField` | 单行或多行文本字段；`-102` 表示流程名称（系统） | **CLI 已支持**：JSON 写字段 ID 或 `-102` |
| 默认存放目录 | `defaultCat` | 文档目录 | **CLI 未支持**：待补充目录查询和非空保存结构 |
| 目录区分字段 | `flowDocCatField` | 表单选择字段 | **CLI 已支持**：JSON 写字段 ID |
| 文档属性设置 | `docPropSettings` | 正文文档属性与流程表单字段的映射 | **CLI 未支持**：待补充映射结构 |
| 默认打开正文的节点 | `openTextDefaultSelect`、`openTextDefaultNode` | `1` 全部；`2` 选择节点 | **CLI 已支持**：`--open-text-select` 配合 `--open-text-node` |
| 可编辑正文的节点 | `editTextNode` | 一个或多个流程节点 | **CLI 已支持**：`--edit-text-node <节点名或ID...>` |
| 编辑时使用预览插件 | `editorReadOnly` | 开关 | **CLI 已支持**：JSON 写布尔值 |
| 默认预览正文 | `previewDefault` | 开关 | **CLI 已支持**：JSON 写布尔值 |

完整示例：

```json
{
  "basic": {
    "officialType": "1",
    "requestTitleField": "公文标题字段ID",
    "flowDocField": "正文浏览框字段ID",
    "documentTitleField": "-102",
    "flowDocCatField": "目录区分字段ID",
    "openTextDefaultSelect": "2",
    "openTextDefaultNode": ["发起节点ID", "审批节点ID"],
    "editTextNode": ["发起节点ID"],
    "editorReadOnly": true,
    "previewDefault": true
  }
}
```

## 常用功能

| 设置项 | 配置键 | CLI 支持情况 |
|---|---|---|
| 只能新建正文 | `newTextNodes` | **CLI 已支持**：JSON |
| 允许上传 WORD | `uploadWORD` | **CLI 已支持**：`--upload-word` |
| 允许上传 PDF | `uploadPDF` | **CLI 已支持**：`--upload-pdf` |
| 允许上传 OFD | `uploadOFD` | **CLI 已支持**：`--upload-ofd` |
| 保留正文版本 | `saveTempFile` | **CLI 已支持**：JSON |
| 存为流程草稿 | `isWorkflowDraft` | **CLI 已支持**：JSON |
| 签字意见分组 | `signGroupMould` | **CLI 部分支持**：可写分组 ID，未提供名称查询 |

上传格式可直接使用 `--upload-word`、`--upload-pdf`、`--upload-ofd`。其余普通开关写入 JSON；签字意见分组按候选分组 ID 配置。

## 正文显示设置

- `isTextInForm`：正文内容显示在流程表单。**CLI 已支持**：`--text-in-form`。
- `editTextInForm`：允许在表单中直接编辑正文。**CLI 已支持**：JSON。
- `showTextNewColumn`：正文分栏显示。**CLI 已支持**：JSON。
- `columnPosition`：正文位置，`1` 左侧、`2` 右侧。**CLI 已支持**：`--column-position`。
- `textColumnSize`：正文栏占比。**CLI 部分支持**：JSON 可写；启用附件区后可能保留原值，须以回读为准。
- `openTextInFormSelect`、`openTextInFormNode`：正文显示应用节点，`1` 全部、`2` 选择。**CLI 已支持**：JSON 写节点 ID。
- `showAttributeTab`：正文页面显示文档属性页签。**CLI 已支持**：JSON。
- `reupload`：发起节点允许重新上传。**CLI 未支持**：写入后仍为关闭。
- `reUploadSelect`、`reUploadNode`：允许重新上传正文的节点。**CLI 已支持**：JSON 写节点 ID。
- `canChangeEditMould`：发起节点允许更换编辑模板。**CLI 已支持**：JSON。

## 痕迹设置

- `isCompellentMark`：必须保留痕迹。**CLI 已支持**：JSON。
- `isCancelCheck`：取消审阅。**CLI 已支持**：JSON。
- `isHideTraces`：编辑正文时默认隐藏痕迹。**CLI 已支持**：JSON。
- `cleanCopyNodesSelect`、`cleanCopyNodes`：清稿节点，`1` 全部、`2` 选择。**CLI 已支持**：JSON 写节点 ID。
- `isAutoCleanCopy`：清稿节点保存正文时自动清稿。**CLI 已支持**：JSON。

## 其他设置

- `extFileToDoc`：流程附件转为正文附件。**CLI 已支持**：JSON。
- `extFileToDocSelect`：选择转为正文附件的字段。**CLI 部分支持**：可写字段 ID，字段选择结构待补。
- `keepExtFile`：保留流程附件。**CLI 已支持**：JSON。
- `defaultDocType`：默认文档类型。**CLI 部分支持**：可写类型值，待补充码表。
- `printNodeSelect`：打印正文节点。**CLI 部分支持**：可写节点 ID，待补充完整选择结构。
- `downloadSelect`：正文下载权限。**CLI 部分支持**：可写配置值，待补充完整码表。
- `syncTitleNodes`：同步正文标题的节点。**CLI 已支持**：JSON 写节点 ID。
- `useClientNodes`：使用客户端插件的节点。**CLI 已支持**：JSON 写节点 ID。
- `openSignatureSeal`：启用签名印章。**CLI 已支持**：JSON。
- `savedBackForm`：保存正文返回表单。**CLI 已支持**：JSON。
- `savedRemind`：离开正文提醒保存。**CLI 已支持**：JSON。
- `isTextInFormMobile`：移动端正文附件显示在表单。**CLI 已支持**：JSON。
- `openAfterSavingMerge`：手动合并文档时自动保存正文。**CLI 已支持**：JSON。

## 模板、排版与签章

- 模板设置：`officialTemplate` 套红模板、`editTemplate` 编辑模板、`printTemplate` 打印模板。**CLI 未支持**。
- 排版设置：`composingTemplate`。**CLI 未支持**。
- 签章节点设置：保存为 `signNodeList`，每项包含节点及启用、必填状态。**CLI 部分支持**：JSON 对象数组已实际保存并读回；命令的回读比较可能误报不一致。
- 正文动作设置：`textActionSetting`。**CLI 未支持**。

模板和排版配置先查询可用模板，再按模板 ID、适用节点及条件配置。签章节点对象数组中的开关由 CLI 转换为平台要求的 `"1"/`"0"`。

## 公文字段与交换

以下设置使用各自的结构化配置：

- `officialFieldSetting`：公文字段设置。**CLI 未支持**。
- `innerExchangeSetting`：内部交换设置。**CLI 未支持**。
- `odocTypeChangeSettings`：文种变更设置。**CLI 未支持**。
- `processRelativeSetting`：公文环节映射。**CLI 未支持**。
- `wellSignSettings`：在线签批。**CLI 未支持**。
- `metaDataSettings`：公文元数据。**CLI 未支持**。

逐项补充时记录选择资源的查询方式、保存结构、字段码表及回读结构。

## 公文编号

`odocNumber` 作为完整嵌套对象保存：

- `openOdocNumber`：启用公文文号。**CLI 已支持**：`number` JSON。
- `odocNumberField`：文号字段。**CLI 部分支持**：可写字段 ID。
- `numberTypeField`：文号类型字段。**CLI 部分支持**：可写字段 ID。
- `odocNumberSelect`：`1` 全部、`2` 选择。**CLI 已支持**：`number` JSON。
- `odocNumberType`：可用文号类型。**CLI 部分支持**：可写类型 ID，未提供名称查询。
- `odocNumberLink`：生成文号出口。**CLI 部分支持**：可写出口 ID，未提供名称查询。
- `editNumberNode`：文号可编辑节点。**CLI 已支持**：`number` JSON 写节点 ID。

## 附件区

`odocAttachArea` 作为完整嵌套对象保存。可使用 `--attach-area 1|0` 控制总开关，其余配置写入 `attachmentArea`：

- `attachDefaultOpen`：默认展开。**CLI 已支持**：`attachmentArea` JSON。
- `attachOpenDirection`：`1` 左侧、`2` 右侧。**CLI 已支持**：`attachmentArea` JSON。
- `attachOpenNodeSelect`、`attachOpenNode`：默认展开节点。**CLI 已支持**：JSON 写节点 ID。
- `attachProportion`：附件区占比。**CLI 已支持**：JSON 写百分比数值。
- `odocProportion`：正文栏占比。**CLI 部分支持**：JSON 可写；启用附件区后可能保留原值，须以回读为准。
- `allowAddFile`：允许上传新附件或添加新文档。**CLI 已支持**：JSON。
- `attachSelect`、`attachField`：附件区展示字段。**CLI 部分支持**：选择范围可写，字段结构待补充。
- `subscriptOpen`：启用角标。**CLI 已支持**：JSON。
- `subscriptStyle`：`1` 数字、`2` 红点。**CLI 已支持**：JSON。
- `subscriptScope`：`1` 附件数量、`2` 文档数量、`3` 正文数量。**CLI 已支持**：JSON。

## 归档管理

- `archivesNodeOpen`：启用预归档。**CLI 已支持**：JSON；使用 `--archive-node` 时自动开启。
- `archivesNode`：预归档节点。**CLI 已支持**：`--archive-node <节点名或ID>`。
- `archivesNodeSelect`：`1` 到达节点、`2` 离开节点。**CLI 已支持**：JSON。
- `archivesFormSettings`：归档表单设置。**CLI 未支持**。
- `archivesFormFieldSettings`：归档表单字段映射。**CLI 未支持**。

## 智能助手

- `showAiOdoc`：启用公文助手。**CLI 已支持**：`--ai-odoc`。
- `showOfficialDoc`：启用事务公文。**CLI 已支持**：JSON。
- `openAiAbstract`：智能摘要。**CLI 已支持**：`--ai-abstract`。
- `aiAbstractField`：摘要写入字段。**CLI 部分支持**：JSON 可写字段 ID；当前环境无可选字段，非空写入尚未验证。
- `openAiFormat`：智能排版。**CLI 已支持**：`--ai-format`。
- `autoAiFormat`：生成正文后自动排版。**CLI 已支持**：JSON。
- `defaultFormatTemplate`：默认排版格式。**CLI 部分支持**：可写模板 ID，未提供名称查询。

配置摘要或排版能力时同时开启 `showAiOdoc`。

## 保存形状

CLI 读取完整设置后合并指定修改，再按平台保存形状提交：

| 数据 | 配置输入 | 保存形状 |
|---|---|---|
| 开关 | 布尔或 `0/1` | `"1"/`"0"` |
| ID 清单 | 字符串数组 | 逗号分隔字符串 |
| 节点清单 | 节点 ID 数组 | 逗号分隔节点 ID |
| 签章节点 | 对象数组 | 对象数组，内部开关转换为字符串 |
| 公文编号 | `number` | `odocNumber` 嵌套对象 |
| 附件区 | `attachmentArea` | `odocAttachArea` 嵌套对象 |

`setting set` 保存后自动回读比对。配置结果以回读值为准。
