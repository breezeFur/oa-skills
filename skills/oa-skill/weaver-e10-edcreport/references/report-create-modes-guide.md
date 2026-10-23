# 新建报表 · 三种创建模式（强制）

> **页面**：`/sp/ebdapp/detail/{appId}/report` → **新建报表** 对话框  
> **UI 三卡片**：从空白创建 · **模版创建** · **快速构建-列表式**  
> **源码**：`EdcReportDevBaseController.saveReportBaseInfo` + `EdcReportDevBaseServiceImpl.addReportBaseInfo`  
> **CLI**：`edc-report create blank|template|quick` · `edc-report create models`

---

## 〇、结论（Agent 必读）

| UI 卡片 | 是否支持 | 怎么走 |
|---------|----------|--------|
| **从空白创建** | ✅ 已支持 | `POST baseInfo`，`reportModel=0`，不传 `quicklyParam` |
| **模版创建** | ✅ **本指南 / CLI 已支持** | `GET getReportModels` 选模板 → `POST baseInfo` 且 **`reportModel={模板报表ID}`** |
| **快速构建-列表式** | ✅ **本指南 / CLI 已支持** | `POST baseInfo` 且 **`quicklyParam={QuicklyParam JSON 串}`**（`reportModel=0`） |

服务端分支（**互斥，模板优先**）：

```text
modelId > 0           → 模版创建（copySheet）
else quicklyParam 非空 → 快速构建-列表式
else                  → 从空白创建（空 workbook + sheet）
```

**禁止混淆**：Skill 自带的 `assets/template-*-report.json` 是 **Agent 布局脚手架**，**不是**平台「模版创建」的 `getReportModels` 模板池。

---

## 一、共享入口

`POST /api/bs/edc/report/baseInfo`（`multipart/form-data`，`id=0` 新建）

| 参数 | 空白 | 模版创建 | 快速构建-列表式 |
|------|------|----------|-----------------|
| `appId` | 必填 | 必填 | 必填 |
| `id` | `0` | `0` | `0` |
| `name` | 必填 | 必填 | 必填 |
| `nameLabelId` | `-1` | `-1` | `-1` |
| `groupId` | `0` | `0` | `0` |
| `showOrder` | `1` | `1` | `1` |
| `permission` | `[]` | `[]` | `[]` |
| **`reportModel`** | **`0`** | **模板报表 ID（>0）** | **`0`** |
| **`quicklyParam`** | **省略** | **省略** | **QuicklyParam JSON 字符串** |

返回 `data` = 新报表 ID（雪花字符串）。

设计器地址：

```text
{host}/sp/edc/report/design/{reportId}?appId={appId}&type=1&from=management
```

---

## 二、模版创建

### 2.1 列模板

```http
GET /api/bs/edc/report/getReportModels
```

系统模板池（`getReportList(-999, -1, user)`）。Agent 须把列表展示给用户或按名称精确匹配后再创建。

### 2.2 创建

```bash
edc-report create models
edc-report create template --app-id <appId> --name "新报表" --model-id <模板ID>
```

Python：

```python
models = client.get_report_models()
rid, obj = client.create_report_shell(name, report_model=str(model_id))
# 或
rid, obj = client.create_from_model(name, model_id)
```

服务端：`addReportByModel` → `copySheet(modelId)`，布局/字段随模板复制。

---

## 三、快速构建-列表式

### 3.1 QuicklyParam 结构（源码 `quicklycreate.bean.QuicklyParam`）

```json
{
  "dataSetList": [
    {
      "id": "<临时UUID，与 showField[].dataSetId 一致>",
      "sourceType": "1",
      "sourceId": "<表单/数据源 ID>",
      "sourceName": "表单名",
      "sourceGroup": ""
    }
  ],
  "showField": [
    {
      "dataSetId": "<同上临时UUID>",
      "tableId": "...",
      "name": "fieldKey",
      "text": "显示名"
    }
  ],
  "fieldConfig": {
    "<dataSetId>.<tableId>.<name>": {
      "colName": "列标题",
      "colWidth": "170",
      "vAlign": "1",
      "hAlign": "1",
      "group": "0",
      "hideCol": "0",
      "lockCell": "0",
      "textWrap": "0"
    }
  },
  "theme": "-1",
  "sheetIndex": 0,
  "startRow": 0,
  "startCol": 0
}
```

要点：

- `showField[].dataSetId` 必须与 `dataSetList[].id` **同一临时 ID**（同数据源多选时靠临时 id 区分）。
- `fieldConfig` 的 key = `{dataSetId}.{tableId}.{name}`。
- 任一字段 `group=1` → 服务端 **关闭** `simpleList`；否则默认 **开启** `simpleList:true`（列表加速）。
- `theme` 默认 `"-1"`（无主题样式）。

示例文件：`assets/quickly-param.example.json`

### 3.2 CLI

```bash
edc-report create quick --app-id <appId> --name "列表报表" --quickly-file assets/quickly-param.example.json
# 或
edc-report create quick --app-id <appId> --name "列表报表" --quickly-json "{...}"
```

Python：`client.create_from_quickly_param(name, quickly_param_dict_or_str)`

### 3.3 与设计器内「快速构建」的区别

| | 列表页「快速构建-列表式」 | 设计器「更多 → 快速构建」 |
|--|--------------------------|---------------------------|
| 时机 | **新建** `baseInfo` + `quicklyParam` | **已有报表** 设计保存 `quicklyParamList` |
| 本指南 | §三 | 见 `report-help-guide.md` §13.2；不走 create CLI |

---

## 四、Agent 选型

| 用户意图 | 模式 |
|----------|------|
| 从零搭布局 / API 细粒度单元格 | **从空白创建** + `api-report-build-fast-path.md` |
| 「用某某模板」「系统模板」 | **模版创建** |
| 「选表选字段一键列表」「快速构建」 | **快速构建-列表式** |
| 未说明 | 默认空白；或 AskUserQuestion 三选一 |

---

## 五、禁令

- 禁止同时依赖 `reportModel>0` 与 `quicklyParam` 指望「都生效」——服务端 **模板优先**，快速构建被跳过。
- 禁止把 `assets/template-list-report.json` 当成平台 `getReportModels` 模板去传 `reportModel`。
- 禁止未登录乱扫前端 bundle 猜参数；以本指南 + 源码 bean 为准。

---

## 六、相关文档

| 文档 | 用途 |
|------|------|
| `report-lifecycle-api-guide.md` | 列表页生命周期；含新建三模式入口 |
| `report-baseinfo-defaults-guide.md` | baseInfo 默认值 + `reportModel` / `quicklyParam` |
| `api-report-build-fast-path.md` | 空白创建后的细粒度搭建 |
| `report-help-guide.md` §十三 | 产品 UX 说明 |
