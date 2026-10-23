# 数据预聚合自动关闭指南

> **解析优化 · 数据预聚合**（设计器「页面 → 报表展示 · 解析优化」）对应 `sheetConfig.dataPreAgg`（默认 `true`）。  
> 当数据源字段或报表布局不满足引擎预聚合条件时，**必须自动关闭**，避免预览/解析异常或静默降级。  
> **勿混淆**：左侧数据集菜单「**数据聚合**」是 `aggregationSave`（见 `dataset-sidebar-ops-guide.md`），不是本指南的 `dataPreAgg`。

---

## 一、源码依据

| 来源 | 规则 |
|------|------|
| `SheetServiceImpl.existNotAllAllowAggregate` | 数据集字段 `gdBySelf=true` → 不支持预聚合 |
| 同上 | 字段 `usage == "list"` → 不支持（仅 `""`/`all`/`char`/`aggregate` 支持分组） |
| `BaseEngine.initDataSetByGroup` | `sheetConfig.dataPreAgg=false` → 全局跳过 |
| 同上 | 单元格存在 `customFilterField` 或 `dataFilterField` → 该 dataset 不参与预聚合 |
| 同上 | 存在 `displayType=List`（排列）字段 → 该 dataset 不参与 |
| `GCONST.NO_GROUP_COMP_TYPE` | 分组字段 `compType` 为 `TextArea` / `RichText` → 不可预分组 |

---

## 二、检测时机（Agent 必做）

在 **addDataset 后、saveReportWithCacheConfig 前**：

1. 调用 `GET /api/bs/edc/dataset/fieldsAndOriginFields?datasetId={id}&hasField=true&isFront=true`
2. 读取 `data.fieldsKey` 或 `data.originFields` 中每个字段的 `usage`、`originField.compType`、`gdBySelf`（若在 dataset 级）
3. 结合已规划的报表字段（displayType、customFilterField）运行检测脚本

```bash
python scripts/check_preaggregate_support.py --fields-json <fields.json> [--layout-json <report_fields.json>]
```

---

## 三、判定逻辑（摘要）

**以下任一成立 → `dataPreAgg: false`**

### 3.1 字段元数据（数据源）

- 任一绑定字段 `usage == "list"`
- 任一作为**分组**使用的字段 `originField.compType ∈ {TextArea, RichText}`
- 数据集级标记 `gdBySelf == true`

### 3.2 报表布局

- 任一字段 `displayType == "List"`（排列）
- 任一字段 `customFilterField` 或 `dataFilterField` 非空
- 多数据集且存在跨表 `leftFilterField`（父格筛选参与取数，引擎对涉及 dataset 跳过预聚合）

---

## 四、写入方式

### 4.1 pageSetting / sheetConfig

双保存时 `pageSetting` 或 sheet props 中写入：

```json
{
  "0": {
    "rowHeader": 0,
    "colHeader": 0,
    "gridLine": 0,
    "sheetConfig": "{\"dataPreAgg\":false,\"simpleList\":false}"
  }
}
```

> **注意**：`rowHeader` / `colHeader` / `gridLine` 保持 **0**（默认关闭）。勿为写 `sheetConfig` 而顺带把网格线/行号列头写成 `1`；见 `report-designer-feature-map.md` §4.6.1。

### 4.2 ReportProps JSON

```json
"sheetProps": {
  "sheetConfig": "{\"dataPreAgg\":false,\"simpleList\":false}"
}
```

### 4.3 脚本辅助

`check_preaggregate_support.py` 输出：

```json
{
  "dataPreAgg": false,
  "reasons": ["字段[备注] usage=list 不支持预聚合", "…"],
  "sheetConfig": "{\"dataPreAgg\":false,\"simpleList\":false}"
}
```

---

## 五、Agent 流程嵌入

1. 获取字段元数据 → 运行 `check_preaggregate_support.py`
2. 若 `dataPreAgg=false`，在 save 载荷中写入 `sheetConfig`，并在 HTML 手册 `tips` 中注明「已关闭数据预聚合：原因…」
3. 保存后 `getReportDevInfo` / 设计器「页面 → 解析优化」确认开关状态

---

## 六、相关文档

- `report-designer-feature-map.md` — 解析优化入口
- `report-knowledge-base.md` §1.2 — 预聚合概念
- `report-delivery-contract.md` — 交付自检含预聚合项
