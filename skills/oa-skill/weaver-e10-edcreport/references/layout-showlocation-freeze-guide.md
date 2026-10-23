# 报表显示位置（居左/居中）与冻结单元格 · 功能解析（强制）

> **适用**：用户要求「报表居左/居中」「冻结表头/冻结单元格」时 **必加载**。  
> **原则**：只改这两项（及用户同时点名的列宽等），**禁止**顺手重写单元格字体/颜色/行高。见 `targeted-fix-guide.md`。

---

## 一、报表显示位置 `showLocation`

### 1.1 UI → 存储枚举（前端实测）

设计器「页面 → 页面布局 → 报表显示位置」写入：

| 用户说法 | 写入值 | 说明 |
|----------|--------|------|
| **居左** | **`1`** | 前端：`showLocation = ("left" === t ? 1 : 2)` |
| **居中** | **`2`** | 缺省；`tag` 缺失时前端也回落为 `2` |

### 1.2 落点

| 层 | 字段 |
|----|------|
| workbook | `sheets.Sheet1.tag.showLocation` |
| 落库 | `sheetProps[0].showLocation`（由 save 从 sheet.tag 解析） |

服务端：`workSheet.getTag().getIntValue("showLocation")`；**tag 为 null** 时默认写 `2`。

### 1.3 致命错误：禁止写 `0` 当居左

| 错误写法 | 后果 |
|----------|------|
| `showLocation: 0` | 前端用 **truthy** 判断：`tag.showLocation ? tag.showLocation : 2` → **`0` 被当成缺省 → 回落成 `2`（居中）**，居左「设置了但不生效」 |
| 猜 `0`=空表默认=居左 | 空表 Java 侧曾写 `0`，**与 UI「居左」不是同一枚举** |

**正确**：居左写 **`1`**；居中写 **`2`**。回读断言 `sheetProps.showLocation === 1|2`。

### 1.4 视觉注意

宽表（列宽×列数 ≥ 视口）时居左/居中视觉差可能不明显；仍须按枚举正确落库，不得因「看起来一样」改回错误值。

---

## 二、冻结单元格 / 冻结表头

### 2.1 UI 语义

- 路径：页面 → 单元格 → **冻结单元格**
- 冻结区域 = 锚点单元格的**上方行 + 左侧列**，**不含**锚点格本身
- 「冻结表头」= 锚点放在**表头下一行、第 0 列**（或用户指定的首个数据格）

### 2.2 设计器真实落点（前端 `setFixedCellByTarget`）

仅写 `frozenRowCount` **不够**。完整落点：

| 项 | 值 | 作用 |
|----|-----|------|
| **锚点 Const** | `cellText = "fixed-cell-tag"`，坐标 `(freezeX, freezeY)` | 设计器标记；样式透明/`1px` 字 |
| **`cell.tag.fixed = true`** | 该锚点格 | 保存时回写 `field.fixed = 1` |
| **`field.fixed = 1`** | 同上 | 预览引擎识别 |
| **`sheet.tag.fixedCell`** | `{ x: freezeX, y: freezeY }` | 设计器记住锚点，取消冻结时清掉 |
| **`frozenRowCount` / `frozenColCount`** | 通常 = `freezeX` / `freezeY` | Spread 设计区冻结线（辅助） |

### 2.3 预览引擎（Custom / SimpleList）

`AnalysisParams.analysisFrozenCell()`：

1. 找 **第一个** `field.fixed == 1` 的字段  
2. `frozenRowCount = minCell.x`，`frozenColumnCount = minCell.y`  
3. 再应用到预览 workbook  

→ **没有 `fixed=1` 的锚点格，只改 sheet.`frozenRowCount`，预览不冻结。**

### 2.4 如何选锚点坐标

| 需求 | 锚点 `(x,y)` | 效果 |
|------|--------------|------|
| 冻结表头（仅行） | `(表头行+1, 0)` | 冻上方表头；不冻左侧数据列 |
| 冻结到某数据格左上 | `(该格.x, 该格.y)` | 冻其上方与左侧（含左侧字段列） |
| 快捷创建「锁定列」 | 给该 **Field** `fixed=1`（无 fixed-cell-tag） | 锚点=该 Field 的 minCell |

**识别步骤（强制）**

1. 从表布局找表头 Const 行 `headerX`、数据 Field 行 `dataX`（通常 `dataX = headerX + 1`）  
2. 「冻结表头」→ 锚点 **`(dataX, 0)`**，除非用户点名其它格  
3. 落库后回读：存在 `cellText===fixed-cell-tag` 且 `fixed===1`，坐标正确；`sheetProps`/`tag` 可核对 `fixedCell`

### 2.5 取消冻结

- 删除 `fixed-cell-tag` Const  
- 清所有 `field.fixed` / `tag.fixed`  
- 清 `sheet.tag.fixedCell`  
- `frozenRowCount`/`frozenColCount` → `0`

---

### 2.6 API 落库（源码级定案 · 2026-09-14）

> 用 `saveReportDevInfo` 整份落库时，**唯一真正持久化的冻结数据是 `cell.tag.fixed`**：

| 项 | 保存侧是否读取 | 结论 |
|---|---|---|
| `cell.tag.fixed = true` | **是** → `field.fixed = 1`（`EdcReportDevDesignServiceImpl` 读 `cell.getTag().isFixed()`） | **必须写**，唯一权威 |
| `sheet.frozenRowCount` / `frozenColCount` | **否**（保存侧无此读取） | 带上无害；预览/设计区由 `field.fixed` 推导 |
| `sheet.tag.fixedCell = {x,y}` | **否**（sheetProps 只落 showLocation/childMerge/filterSheet/tableNameSuffix/dtTable/columnConfig/sheetConfig） | 带上无害；设计器加载时**从锚点字段重建** |

**预览与设计区冻结线的唯一来源**（`AnalysisParams.analysisFrozenCell()`，仅 `Custom` / `SimpleList`）：

```java
Optional<AnalysisField> obj = this.fields.stream().filter(d -> d.getFixed() == 1).findFirst();
OffSet cell = obj.get().getMinCell();
setFrozenRowCount(cell.getX());      // 冻结锚点上方各行
setFrozenColumnCount(cell.getY());   // 冻结锚点左侧各列
```

**推论（三条）**

1. **锚点格不必是空格**。设计器 `setFixedCellByTarget` 只在锚点格 `cellType.typeName` 为假（空格）时才补写
   `cellText="fixed-cell-tag"` + 透明样式；**占用格（数据字段所在格）它什么都不写**，只更新内存里的 `tag.fixedCell`。
   所以「用 API 把锚点设在数据格上」是**唯一可行**的做法 —— 只置 `tag.fixed` 即可，预览照样冻结。
2. **禁止**顺手给锚点格写 `cellText="fixed-cell-tag"`：服务端会据此把该格**边框 4 边 + 底色清空**
   （`CustomEngine`/`SimpleListEngine` 的 `field.getFixed()==1 && "fixed-cell-tag".equals(cellText)` 分支），
   属于改动未点名格的样式。
3. **`fixed=1` 的字段必须唯一**。`findFirst()` 取的是字段列表里第一个 `fixed==1`，多个会以第一个为准（顺序 = x 升序、同 x 按 y）→ 落库前先清掉所有旧 `fixed`。

**锚点坐标怎么选**

| 目标 | 锚点 `(x, y)`（0 基） |
|---|---|
| 仅冻结表头（前 `h` 行） | `(h, 0)` |
| 表头 + 左侧 `c` 列 | `(h, c)` |

CLI：`edc-report fix freeze --report-id <id> --app-id <aid> --anchor 4,3 [--apply]`（默认 dry-run）。

**脚本会拒绝落库的两种情况**

1. **重建保真度不足**（除冻结点外与线上 `fields[]` 有差异）→ 拒绝，避免误伤；
2. **重复坐标**（同一 `(x,y)` 在 `fields[]` 里有 ≥2 条记录）→ 报 `exit 3` 并列出各条 `id/createTime`。
   典型成因：**在设计器里把字段拖到某个表头格上**，旧 Const 未被清掉 → 该格"表头 + 字段"两条记录并存。
   此时 workbook 一个坐标只能放一格，重建必然丢一条 → 必须先由用户确认取舍（或先去设计器清理）。

---

## 三、定点改 checklist（禁止伤样式）

用户只说「列宽 / 冻结 / 居左」时：

| 允许 | 禁止 |
|------|------|
| 改目标列 `width` + workbook `columns[]` 对应 `size` | 用默认 style 重建整表 cell |
| 增/改 `fixed-cell-tag` + `showLocation` + freeze 计数 | 改未点名格的 font/backColor/border/行高 |
| 其它格 **原样**写回（style JSON 原串） | 为「方便」从零 `fieldToCell` 丢 tag/合并/条件格式 |
| 保留并回写原 `spans` / `xCount`/`yCount` | **拆掉或漏写合并**（无任何规则授权「取消合并」） |

`columns` 必须是 **数组** `[{size:N}, …]`，不能是 `{ "3": {size:250} }` 对象。

**合并单元格**：`fields.xCount/yCount` ↔ workbook `spans`（`row/col/rowCount/colCount`）及 cell `rowCount/colCount`。重建 workbook 漏 spans = 表头/表尾合并消失。

---

## 四、与其它文档

| 文档 | 关系 |
|------|------|
| `targeted-fix-guide.md` | 定点范围；样式禁碰 |
| `report-designer-feature-map.md` §4.2 / §4.6 | UI 入口索引 |
| `safe-partial-save-guide.md` | 完整 workbook 写回 |
| `safe_report_save.js` → `fieldToCell` | 须把 `fixed` 写入 `cell.tag.fixed` |
