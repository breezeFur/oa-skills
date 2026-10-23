# 设计器 · 数据集侧栏菜单操作（强制）

> **入口**：报表设计器左侧数据集标题 `…` 菜单  
> **页面例**：`/sp/edc/report/designer/{reportId}`  
> **CLI**：`edc-report dataset rename|agg|sort|replace|delete|check-used|preview`  
> **鉴权**：e10-login 三项头（`api-auth-headers.md`）

---

## 〇、能力总表

| # | UI | API | 说明 |
|---|-----|-----|------|
| 1 | **自定义名称** | `GET /api/bs/edc/dataset/rename` | 改 `edc_dataset_dev.name` |
| 2 | **数据聚合** | `POST/GET …/dataset/aggregationSave\|Get` | 数据集级分组+度量；≠ 页面 `dataPreAgg` |
| 3 | **数据排序** | `POST/GET …/dataset/sortSave\|Get` | 数据集级多字段排序 |
| 4 | **替换数据集** | `POST /api/bs/edc/dataset/replaceDataset` | JSON：新源 + `fieldMap`；返回新 datasetId |
| 5 | **移除** | `POST /api/bs/edc/report/delDataset` | `sourceIds`=**datasetId**；被引用则禁删 |

同菜单已有完整指南：

| UI | 文档 |
|----|------|
| 筛选条件 | `dataset-query-filter-guide.md`（`queryInfoSave`） |
| 数据预览 | `GET /api/bs/edc/dataset/getPreviewData?dataSetId=`（本指南 §六） |

---

## 一、自定义名称

```http
GET /api/bs/edc/dataset/rename?datasetId={id}&name={显示名}&nameLabelId=-1
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `datasetId` | ✅ | 侧栏数据集实例 id |
| `name` | ✅ | 自定义显示名（空名前端拦截） |
| `nameLabelId` | 建议 | 无多语言传 `-1` |

```bash
edc-report dataset rename --dataset-id <id> --name "轻资产主表" [--name-label-id -1]
```

---

## 二、数据聚合（侧栏 · 勿与预聚合混淆）

### 2.1 接口

| 动作 | 方法 | 路径 |
|------|------|------|
| 读 | GET | `/api/bs/edc/dataset/aggregationGet?datasetId=` |
| 写 | POST | `/api/bs/edc/dataset/aggregationSave` form：`datasetId` + `aggreData`（JSON 数组字符串） |

写时服务端先删该 dataset 全部聚合行再插入（全量替换）。表：`edc_reportdsaggregate_dev`。

### 2.2 `aggreData` 结构

```json
[
  {
    "fieldId": "{datasetId}.{tableId}.{fieldName}",
    "countType": "sum",
    "showName": "库存合计",
    "fieldName": "s_sum_field_xxx"
  },
  { "groupBy": "{datasetId}.{tableId}.{fieldName}" }
]
```

| 行类型 | 关键字段 | 说明 |
|--------|----------|------|
| 度量 | `fieldId` + `countType` + `showName` | `countType`：`sum`/`max`/`min`/`avg`/`count` 等；`fieldName` 常为 `s_{countType}_{leaf}` |
| 维度 | `groupBy` | 完整 fieldKey；无 `countType` |

规则（对齐设计器）：

- 须同时有维度 + 度量，或两者皆空（清空聚合）  
- 保存后 `fieldsAndOriginFields` 可见字段变为「分组字段 + 度量别名」  

### 2.3 ≠ 页面「数据预聚合」

| | 侧栏「数据聚合」 | 页面「解析优化 · 数据预聚合」 |
|--|------------------|------------------------------|
| 存储 | `aggregationSave` / `edc_reportdsaggregate_dev` | `sheetConfig.dataPreAgg` |
| 指南 | **本文 §二** | `preaggregate-auto-disable-guide.md` |
| CLI | `edc-report dataset agg …` | `edc-report py preagg` |

有侧栏聚合时，引擎侧预聚合路径会被跳过/弱化。

```bash
edc-report dataset agg get --dataset-id <id>
edc-report dataset agg save --dataset-id <id> --file aggre.json
edc-report dataset agg clear --dataset-id <id>
```

---

## 三、数据排序

| 动作 | 方法 | 路径 |
|------|------|------|
| 读 | GET | `/api/bs/edc/dataset/sortGet?datasetId=` |
| 写 | POST | `/api/bs/edc/dataset/sortSave` form：`datasetId` + `sortData` |

全量替换；表 `edc_reportdsorderby_dev`。数组下标 = `priority`（越前越优先）。

```json
[
  { "fieldId": "{datasetId}.{tableId}.{name}", "orderType": "asc" },
  { "fieldId": "{datasetId}.{tableId}.{name2}", "orderType": "desc" }
]
```

`orderType`：`asc` / `desc`。清空：提交 `[]` 或无 `fieldId` 的占位被设计器清掉。

```bash
edc-report dataset sort get --dataset-id <id>
edc-report dataset sort save --dataset-id <id> --file sort.json
edc-report dataset sort clear --dataset-id <id>
```

---

## 四、替换数据集

```http
POST /api/bs/edc/dataset/replaceDataset
Content-Type: application/json
```

```json
{
  "reportId": 1313049481975267329,
  "builtinId": 旧datasetId,
  "name": "新数据源显示名",
  "sourceType": "LOGIC",
  "sourceId": "新表单sourceId",
  "sourceGroup": "weaver-ebuilder-form-service",
  "appid": "<appId>",
  "fieldMap": [
    {
      "builtinField": "旧字段leaf或度量别名",
      "replaceField": "新字段name",
      "replaceFieldName": "新显示名"
    }
  ]
}
```

- 返回 `data` = **新 datasetId**（字符串）  
- 服务端：新建数据集 → 映射字段/筛选/聚合/排序/查询引用 → 删除旧 `builtinId`  
- 影响分析（可选）：`POST /api/bs/edc/report/getReplaceFields`（`dataSetId`/`sheetId`/`fields`）  

```bash
edc-report dataset replace --file replace-body.json
```

替换后须用新 id 再 `fieldsAndOriginFields` / 必要时 remap 单元格 `dataSetId`/`fieldKey`。

---

## 五、移除（删除数据集）

### 5.1 引用检查

```http
GET /api/bs/edc/dataset/checkDataSetUsed?reportId=&datasetId=
```

`data=true` → 设计器禁止移除（字段等仍引用）。Agent 须先 check，为 true 时提示用户先清画布引用。

### 5.2 删除

```http
POST /api/bs/edc/report/delDataset
form: reportId=<报表ID>&sourceIds=<datasetId>
```

> **`sourceIds` 参数名历史遗留，实际传的是 datasetId**，不是表单 sourceId。

```bash
edc-report dataset check-used --report-id <rid> --dataset-id <did>
edc-report dataset delete --report-id <rid> --dataset-id <did> [--force]
```

无 `--force` 时若 `checkDataSetUsed=true` 则拒绝删除。

注册错误重建场景见 `add-dataset-registration-guide.md`（须带正确 `reportId`+`sourceIds=datasetId`）。

### 5.3 ⚠️ 侧栏出现「重复数据源分组」的根因与清理（2026-09-11 实证）

**症状**：设计器左侧「数据集」下出现 **两个同名分组**，例如 `党员发展` 与 `党员发展(业务模块)`，字段列表完全相同；或分组名缺失 `(业务模块)` 后缀。

**根因（两层，须分查）**：

| 层 | 现象 | 排查接口 |
|---|---|---|
| **① 报表挂载了重复数据集** | `dataset/list` 返回 **2 条同 `sourceId`、同 `name`** 的数据集记录 | `GET /api/bs/edc/dataset/list?hasField=true&reportId=` |
| **② 画布存在游离单元格** | 某单元格 `dataSetId` 指向第二个数据集，常在**另一张 sheet 或表格远端的孤立格** | 遍历 workbook 全部 sheet 的 `dataTable`，按 `cellType.dataSetId` 统计 |

> **关键陷阱**：游离单元格**不一定在 Sheet1**。本例游标藏在 **Sheet2 的 B3**（`sheetIndex:1, x:2, y:1`），只扫 Sheet1 会漏诊。**必须遍历全部 sheet**。

**左侧树显示名的权威来源**：`GET /api/bs/edc/dataset/listWithPageReport?hasField=true&reportId=` → 返回**源级**记录（`id` 是 **sourceId 而非 datasetId**），其 `name`/`tableText` 决定分组显示名。
- 正常：`name = '事项清单(uf_ydsxqd_1)'`（业务模块名 + 物理表名）
- 异常：`name = '党员发展'`（纯中文名，无后缀）→ 面板显示纯名

> **一键体检**：`edc-report verify bind <reportId> [appId]` 会直接列出
> `duplicate_dataset_mount`（同源重复挂载）、`dataset_name_mismatch`（回显名 vs 源级名）、
> `display_mismatch`（单元格文案 vs 字段真实显示名）三类待确认项。
>
> ⚠️ **非物理表表单**（`form/obj/getList` → `isPhysical:false`、`tableType:""`）本身就没有物理表名，
> 源级名只能是纯中文名（本例报表 `1313789294296735745` 的 14 张表全为此类）——
> 这**不是**报表脚本能改的，要带后缀需在 eBuilder 侧给表单配置物理表/业务模块。

**清理步骤（顺序不可颠倒）**：

```python
# 1) 先摘除游标：遍历 workbook 全 sheet，删除/改绑指向重复数据集的单元格
for sheet_name, sh in wb["sheets"].items():
    dt = (sh.get("data") or {}).get("dataTable") or {}
    for ri in list(dt):
        for ci in list(dt[ri]):
            ct = ((dt[ri][ci].get("style") or {}).get("cellType")) or {}
            if ct.get("dataSetId") == DUP_DS:
                del dt[ri][ci]            # 或改绑 KEEP_DS

# 2) saveReportDevInfo 落库（提交 workbook，gzip+base64，带 designKey）

# 3) 再调用 delDataset 删除重复数据集
POST /api/bs/edc/report/delDataset   form: reportId=<rid>&sourceIds=<dupDatasetId>

# 4) 校验
dataset/list            → 只剩 1 条同源数据集
getReportDevInfo.fields → 无任何字段引用 DUP_DS（注意看 sheetIndex 分布）
列表/面板               → 顶层分组只剩 1 个
```

> **顺序原因**：被引用时 `delDataset` 会被服务端拒绝（引用检查）。必须先清画布再删数据集。
>
> **验证要点**：`getReportDevInfo.fields` 按 `(sheetIndex, dataSetId)` 分组统计，确认 `DUP_DS` 计数为 0 —— 只看 Sheet1 会假阳性通过。
>
> **`delDataset` 返回 `code:200` 但 `data` 为空是正常的**；探针传 `sourceIds=0` 同样返回 200 且不删任何东西，**不可用返回码判断是否真的删掉了**，必须回读 `dataset/list` 核对。

---

## 六、数据预览（同菜单）

```http
GET /api/bs/edc/dataset/getPreviewData?dataSetId={id}&isFront=true
```

```bash
edc-report dataset preview --dataset-id <id>
```

---

## 七、Agent 检查清单

- [ ] 自定义名称走 `rename`，未误改 `sourceName` 当永久显示名唯一手段  
- [ ] 「数据聚合」未写成改 `sheetConfig.dataPreAgg`  
- [ ] 聚合/排序 JSON 用完整 fieldKey；保存后回读 Get  
- [ ] 替换带 `fieldMap`；拿到新 datasetId 再继续  
- [ ] 删除前 `checkDataSetUsed`；`sourceIds`=datasetId  
- [ ] **重复分组排查：先 `dataset/list` 查重复数据集，再遍历「全部 sheet」找游离单元格**（勿只看 Sheet1）  
- [ ] 清理顺序：**先摘游标 → saveReportDevInfo → 再 delDataset**  
- [ ] 删除成功以 **回读 `dataset/list`** 为准，不以返回码为准

---

## 关联

- `dataset-query-filter-guide.md` — 筛选条件  
- `add-dataset-registration-guide.md` — 添加/重建  
- `preaggregate-auto-disable-guide.md` — 页面预聚合  
- `dataset-table-field-contract-guide.md` — 字段落库契约（`tableName` 等）  
- `report-designer-feature-map.md` §六  
- `field-bind-exact-match-guide.md` — 字段绑定  
