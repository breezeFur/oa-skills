# 声明式搭表 spec（一次性落库 · 推荐默认路径）

> **CLI**：`edc-report build spec --spec <spec.json> [--dry-run] [--form-confirmed] [--source-id <id>] [--field-confirmed "标题1,标题2"]`  
> **脚本**：`scripts/build_from_spec.js` · 公共库 `scripts/spec_lib.js`  
> **强制流程**：应用内定源 → **建表前字段预检**（`fieldsBySource`，**不建表**）→ **目标名** `baseInfo` → 本表 `addDataset`（同源只挂一次）→ `fieldsKey`（**再校验一次**）→ `saveReportDevInfo` → 回读。  
> **禁止**：`__build_*` / `__probe_*` 空壳、落库后再 rename、跨报表复用 datasetId、模糊表名未确认就搭表、**字段精确匹配失败时静默兜底（含回退系统字段）**。

> ### ⚠ 两条「停下来问用户」规则（强制 · 2026-09-11 · `edc-report policy ask`）
>
> | 规则 | 触发 | 行为 |
> |------|------|------|
> | **A · 字段找不到** | 需求字段在当前数据集表单（`fieldsKey`/`fieldsBySource`）中**无精确命中** | **exit 4 · 不建表**，输出 `unmatched[]` + `allFields[]`，**请用户指定字段** |
> | **B · 表没指明 / 非精确匹配** | 需求**未指出具体表**，或应用内检索**非完全精准匹配**（模糊/多命中/未命中） | **exit 3 · 不建表**，输出 `candidates[]`，**请用户指定表** |
>
> 核心：**不确定 → 停下问用户**；既不替用户猜，也不允许「先建表再回滚」。

---

## 一、顶层字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `appId` | ✅ | 应用 ID |
| `name` | ✅ | **目标报表名**（直接写入 baseInfo + saveReportDevInfo） |
| `form` | ＊ | 准确表单名；或与 `sourceId` 二选一 |
| `sourceId` | | 已确认表单 ID；有则跳过模糊确认 |
| `formConfirmed` | | `true` = 用户已确认当前 form/sourceId |
| `formKeywords` | | **未指明表**时用于出候选的关键词（仅用于列候选，不代表已选表） |
| `columns[]` | ✅ | 列定义，见 §二 |
| `fieldMap` | | **字段兜底指定**：`{ "列标题": "字段显示名 | field_雪花 | 系统字段名" }`（列标题精确匹配失败时由用户指定，见 §二.1） |
| `fieldConfirmed` | | 数组：**已确认「列文案 ≠ 字段真实显示名」**的列标题（用户认可自定义列名） |
| `confirmDisplayMismatch` | | `true` = 全部列允许文案与字段显示名不同（等价 CLI `--field-confirmed`） |
| `style` / `titleStyle` / `headerStyle` / `bodyStyle` | | 见 §三 / `default-header-style-guide.md` |
| `layout` | | `title` / `freezeRows` / `showLocation`，见 §四 |
| `datasetId` | | **仅本 report 已挂载的数据集**可复用；跨报表 ID 忽略并本表 addDataset |
| `sourceType` | | 默认 `LOGIC`；共享表应用用 `form` |
| `sourceGroup` | | 默认 `weaver-ebuilder-form-service`；共享表用 appId |
| `sourceName` | | 数据集回显名；**缺后缀时自动补** `(业务模块)`/`(表单)`（裸表单名 → 面板缺后缀） |

\* `form` 与 `sourceId` **均可省** → 走**规则 B**：exit **3**，列出应用内候选请用户指定表（**不会**按关键词猜、**不会**建表）。

### 1.1 定源规则 · 规则 B（表没指明 / 非精确匹配 → 让用户指定）

`resolveFormWithPrompt()` / `edc-report find form` 统一语义：

| 触发 | `reason` | 行为 |
|------|----------|------|
| **未指明具体表**（无 `form`/`sourceId`，或只给业务关键词） | `form_unspecified` | exit **3**，输出应用内候选 `candidates[]` |
| **非完全精准匹配**：模糊包含 / 多条同名近名 | `form_fuzzy_match` | exit **3**，输出 `candidates[]`（带 `score`/`hits`） |
| **未命中** | `form_not_found` | exit **3**，`action=need_exact_form_name` |
| **exact 唯一** 或 已带 `--form-confirmed`/`sourceId` | `exact`/`confirmed` | 放行（`autoBind=true`） |

确认后复跑（二选一）：

```bash
edc-report build spec --spec a.json --form-confirmed --source-id <id>
```
```json
{ "formConfirmed": true, "sourceId": "<id>", "form": "<准确表名>" }
```

浏览候选（**不建表**）：

```bash
edc-report find form <appId> --list
edc-report find form <appId> --suggest "关键词1,关键词2"
```

> **禁止**：按关键词自行挑一张「最像的」表；先建壳/试探表再判断对不对。
> 输出字段：`action=confirm_form` · `rule:"B"` · `needConfirm:true` · `reportCreated:false`。

### 1.2 数据集挂载规则（同源只挂一次）

| 场景 | 行为 |
|------|------|
| 本报表已有同 `sourceId` 数据集 | **复用**（`datasetReused=true`），**禁止**再次 `addDataset` |
| 同 `sourceId` 多于 1 条（存量脏数据） | 回传 `datasetDuplicates[]` 并 WARN → 按 `dataset-sidebar-ops-guide.md §5.3` 去重 |
| 传了**别的报表**的 `datasetId` | 忽略并 WARN（禁止跨报表复用，本表重新解析） |

---

## 二、columns[]

| 字段 | 说明 |
|------|------|
| `title` | 表头文案（**也是字段匹配依据**，见 §二.1） |
| `field` | 对应 fieldsKey 的 text/name（精确匹配） |
| `fieldName` | **显式指定** fieldsKey.name（优先于 `field`/`title`） |
| `confirmDisplayMismatch` | `true` = 该列允许「文案 ≠ 字段真实显示名」（用户认可自定义列名） |
| `width` | 列宽，默认 120 |
| `format` | 见下表；`huobi` 等 |
| `formula` | 公式表达式（无 `=` 前缀；公式列不参与字段匹配） |
| `groupType` | 日期分组等 |
| `rule` | 条件格式，见 §五 |

### 2.1 字段绑定门禁 · 规则 A（**字段找不到 → 让用户指定 · 禁止静默兜底 · 2026-09-11 强制**）

匹配顺序（命中即止）：① `fieldName` / `fieldMap[列标题]` 显式指定 → ② 列标题 **精确等于** `fieldsKey[].text` → ③ `column.field` 精确等于 `text`/`name`。

| `reason` | 情况 | 行为 |
|------|------|------|
| — | 精确命中 | 正常搭建 |
| `no_exact_match` | **需求字段在当前数据集表单中找不到** | **exit 4**，输出 `unmatched` + `candidates` + `allFields`；**不建表** |
| `explicit_not_found` | 显式指定的字段名不在该数据源 | **exit 4**，同上（禁止臆造字段） |
| `display_mismatch` | 能绑到，但字段**真实显示名 ≠ 列文案**且用户未确认 | **exit 4**，确认后加 `fieldConfirmed` / `--field-confirmed "列标题"` |
| — | 系统字段（`name`/`id`/`create_time`…） | **只能**通过列标题精确命中（如列标题就叫「标题」）或显式指定；**禁止**作为兜底 |

输出（**原样交用户挑，不要自己猜**）：

```json
{
  "action": "confirm_field", "rule": "A", "reportCreated": false,
  "unmatched": [
    { "column": "党组织", "reason": "no_exact_match",
      "prompt": "需求字段「党组织」在当前数据集表单中不存在：请用户从 allFields/candidates 中指定字段。",
      "candidates": [{ "name": "field_1475883017323040117", "text": "所属党委", "system": false }] }
  ],
  "allFields": [ { "name": "field_3505883017323279926", "text": "发展人", "system": false } ],
  "next": { "specFields": { "fieldMap": { "<列标题>": "<字段显示名 | field_雪花 | 系统字段名>" } } }
}
```

用户指定后复跑：

```bash
edc-report build spec --spec a.json --field-confirmed "党组织,姓名"
```
```json
{ "fieldMap": { "党组织": "field_1475883083739840137", "姓名": "发展人" },
  "fieldConfirmed": ["党组织", "姓名"] }
```

> 事故：列「姓名」在表单无对应字段时被静默绑到系统字段 `name`（真实显示名「标题」）→ 列语义被改写且属性面板回显不符。
> 详见 `field-bind-exact-match-guide.md §2.0`。

### format 别名

| 别名 | 说明 | formatter 示例 |
|------|------|----------------|
| `common` / 空 | 常规 | |
| `huobi` | 货币 | `¥` 类目录值 |
| `kuaiji` | 会计专用 | |
| `percent` | 百分比 | `0.00%` |
| `shortdate` / `longdate` / `time` / `text` / `fenshu` / `kexuejishu` | 见 `cell-config-echo-guide.md` §二 |

---

## 三、style（分层 · 默认表头）

> 细则：`default-header-style-guide.md`。  
> **未指定样式且无效果图** → 自动套默认标题/表头；**用户指定或有效果图** → 完全按用户。

```json
"style": { "font": "微软雅黑", "fontSize": 12, "foreColor": "#333", "backColor": "#fff", "hAlign": "left" },
"titleStyle": { },
"headerStyle": { },
"bodyStyle": { },
"styleFromMockup": false,
"applyDefaultHeader": true
```

| 场景 | 行为 |
|------|------|
| 无 style / *Style / 效果图 | 标题 `#B6D6FF`；列头 `#E6E6E6`；正文白底 |
| 有用户样式或 `styleFromMockup:true` | 用户优先 |
| `applyDefaultHeader:false` | 素色 |

字号目录：`[8,9,11,12,14,16,18,20,22,24,26,28,36,48,72]`（无 10）；平台字号≈px 1:1。

---

## 四、layout

```json
"layout": { "title": "轻资产信息统计表", "freezeRows": 1, "showLocation": "left" }
```

- `title`：第 0 行合并标题  
- `freezeRows: 1`：冻标题/表头首格锚点  
- `showLocation`：`left`=1；**禁止 0**

---

## 五、rule 条件格式

落点 `style.cellType.conditionRule`（`highlightDatas` / `lineDatas` / `iconDatas`）。  
**禁止** sheet 级 `conditionalFormats`。

---

## 六、完整示例

```json
{
  "appId": "770979194185342976",
  "name": "资产信息统计",
  "form": "轻资产信息",
  "layout": { "title": "轻资产信息统计表", "freezeRows": 1 },
  "columns": [
    { "title": "资产名称", "field": "资产名称", "width": 160 },
    { "title": "库存数量", "field": "库存数量", "width": 110 }
  ]
}
```

模糊表名确认后再搭：

```bash
edc-report build spec --spec a.json
# exit 3 → 用户确认 sourceId
edc-report build spec --spec a.json --form-confirmed --source-id 770981333078605824
```

---

## 七、输出与退出码

| code | 含义 |
|------|------|
| 0 | 成功；`noTempShell: true`（回读含 `fieldBindings` / `displayMismatch` / `datasetDuplicates`） |
| 2 | 落库成功但存在告警：Field 绑定不在 fieldsKey / 文案与字段显示名不一致 / 同源重复挂载 |
| 3 | **规则 B** 须确认表（`confirm_form` / `need_exact_form_name`）——**尚未建表** |
| 4 | **规则 A** 须确认字段（`confirm_field`）：**建表前预检**未精确命中 → **未建表**；落库前 `fieldsKey` 再校验失败 → **已删除本表** |
| 1 | 失败；已 `deleteReport` 删除未完成报表 |

> **两规则共同点**：都**不会**留下列表垃圾；exit 3/4 时 `reportCreated:false`（或 `reportDeleted:true`）。

成功输出含 `designerUrl`；按 `report-delivery-contract.md` **交链即停**。

### 7.1 exit 4 的处理（**规则 A** · 给用户看，不要自己猜字段）

```json
{
  "action": "confirm_field",
  "rule": "A",
  "reportCreated": false,
  "unmatched": [
    { "column": "姓名", "reason": "no_exact_match",
      "message": "列「姓名」在该数据源 fieldsKey 中没有精确匹配的显示名…",
      "prompt": "需求字段「姓名」在当前数据集表单中不存在：请用户从 allFields/candidates 中指定字段。",
      "candidates": [{ "name": "field_1475883001898540109", "text": "培养人" }] }
  ],
  "allFields": [ { "name": "field_3505883017323279926", "text": "发展人", "system": false } ]
}
```

1. 把 `candidates` / `allFields` **原样抛给用户**，请其指定字段（**不要**自己挑一个相近的顶上）；
2. 用户指定后写 `spec.fieldMap = { "姓名": "发展人" }`（或 `field_xxx`）复跑；
3. 若用户坚持「列名与字段显示名不同」（如列名写「党组织」绑字段「所属党委」）→ 加 `fieldConfirmed: ["党组织"]` 或 CLI `--field-confirmed "党组织"`。

---

## 八、相关文档

| 文档 | 关系 |
|------|------|
| `app-datasource-lookup-guide.md` §2.0 | 未给表名 / 模糊确认 |
| `default-header-style-guide.md` | 默认表头 |
| `add-dataset-registration-guide.md` | LOGIC 注册 |
| `failure-cleanup-and-nonblocking-guide.md` | 仅失败删未完成表，禁止故意建空壳 |
| `report-delivery-contract.md` | 交链即停 |
