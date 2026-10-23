# 单元格「转换」面板（强制）

> **UI**：设计器右侧 **单元格 → 转换**（选中 Field 格时）  
> **源码**：`AnalysisFieldCellType` · `Trans.getTransInstance` · 设计器 `route_ReportDesigner`  
> **CLI**：`edc-report validate transform --map "人员"` / `--file cell.json`  
> **落库**：须同时写入 `fields[]` 与 workbook `style.cellType`（`fieldToCell` 已透传）

---

## 〇、结论（扫描结果）

| UI 能力 | 落库键 | Skill 此前 | 现状 |
|---------|--------|------------|------|
| 字段转换（人员/部门/…） | `transType` + `browserType` / `transSelectOptions` | 帮助文案不全；`report-data-model` 枚举**错误** | **本文 + validate + fieldToCell** |
| HTML转换 | **`isHtml`** `"0"|"1"`（不是 transType） | 未正确文档化 | ✅ |
| 前缀/后缀 | **`prefixAndSuffix`** `["前","后"]` | 仅一笔带过 | ✅ |
| 条码 | **`qrcodeType`** `no|barcode|qrcode`（± `qrcodelink`） | 误写成 FieldType | ✅ |
| 隐藏内容 | **`hiddenContext`** `"0"|"1"`（拼写 Context） | 易与显示方式混淆 | ✅ |
| 文字方向 | **`textDirection`** 枚举 | 知识库有枚举、无面板映射 | ✅ |

**禁止**再用 `person` / `department` / `image` / `html` / `barcode` 当作单一 `transType`。

---

## 一、字段转换 `transType`

### 1.1 UI → 落库（设计器当前）

| UI 文案 | `transType` | 附加字段 |
|---------|-------------|---------|
| 无 | `default` | — |
| **人员** | **`browser`** | `browserType:[{id:"HrmEmployeeComInfo"}]` |
| **部门** | **`browser`** | `browserType:[{id:"HrmDepartmentComInfo"}]` |
| **部门全路径** | **`browser`** | `browserType:[{id:"HrmDepartmentAllPathComInfo"}]` |
| Checkbox | `checkbox` | — |
| 选择框 | `select` | `transSelectOptions:[{selectValue,selectName},…]` |
| 颜色选择框 | `colorSelect` | `transSelectOptions`（`selectName` 常为颜色值） |
| 分值图标 | `scoreIcon` | `transSelectOptions:[{id:"scoreIconId",selectValue:"1",selectName:"<最大分>"}]` |
| 斜线文字 | `slashWord` | `transSelectOptions:[{id:"slashWordId",selectValue:"slashWord",selectName:"TopLeftDownRight"|"DownLeftTopRight"}]`；文案最多 3 段，半角 `;` 分隔 |
| 关联类型 | `browser` | 弹窗写入 `browserType`（如 `{module,type}` / ComInfo id，**以抓包为准**） |
| 图片 | `picture` | — |

> Java 仍兼容遗留 `hrm` / `dept` / `subcom` / `fill`，**新写禁止**用遗留值；人员/部门一律走 `browser`+ComInfo。

### 1.2 双写示例（人员）

```json
{
  "transType": "browser",
  "browserType": [{ "id": "HrmEmployeeComInfo" }],
  "isHtml": "0",
  "qrcodeType": "no",
  "prefixAndSuffix": ["", ""],
  "hiddenContext": "0",
  "textDirection": "FromLeftToRight"
}
```

`fields[].browserType` / `transSelectOptions` / `prefixAndSuffix` 在 DB 侧常为 **JSON 字符串**；workbook `cellType` 侧为数组。

---

## 二、HTML转换 · `isHtml`

| UI | 值 |
|----|-----|
| 否 | `"0"` |
| 是 | `"1"` |

为 `"1"` 时运行时按 HTML 处理/剥离（见 `AnalysisParams`）。**不是** `transType=html`。

---

## 三、前缀 / 后缀 · `prefixAndSuffix`

```json
"prefixAndSuffix": ["前缀文本", "后缀文本"]
```

默认 `["",""]`。重建 workbook 时禁止丢掉该键。

---

## 四、条码 · `qrcodeType`

| UI | 值 |
|----|-----|
| 无 | `no` |
| 条码 | `barcode` |
| 二维码 | `qrcode` |

二维码可选：`qrcodelink` = `"1"` / `"0"`（是否包含移动端地址）。**不是** `transType`。

---

## 五、隐藏内容 · `hiddenContext`

| UI | 值 |
|----|-----|
| 否 | `"0"` |
| 是 | `"1"` |

键名是 **`hiddenContext`**（Context，不是 Content）。与「显示方式」`displayType` **无关**。

---

## 六、文字方向 · `textDirection`

| UI | 值 |
|----|-----|
| 从左向右 | `FromLeftToRight`（默认） |
| 从右向左 | `FromRightToLeft` |
| 竖排 | `VerticalArrangement` |
| 顺时针旋转 90° | `CW` |
| 逆时针旋转 90° | `CCW` |

---

## 七、Agent / CLI

```bash
edc-report validate transform --map "人员"
edc-report validate transform --map "部门全路径"
edc-report validate transform --map "二维码"
edc-report validate transform --file cell-transform.json
edc-report validate transform --list
```

定点改转换时：改 `fields[]` 对应键 → `safe_report_save` / `fieldToCell` 透传到 workbook → 回读核对。

---

## 八、禁令

- 禁止 `transType=person|department|image|html|barcode|hidden`
- 禁止人员/部门只写 `transType=hrm|dept`（遗留）
- 禁止重建 workbook 时丢掉转换键
- 禁止把「隐藏内容」当成「显示方式=不显示」

---

## 关联

- `cell-config-echo-guide.md` — 数字格式 / 日期分组 / 字体  
- `report-designer-feature-map.md` — 右侧面板总览  
- `report-data-model.md` §八 — 已废弃错误表，以本文为准  
- `safe_report_save.js` — `fieldToCell` 透传  
