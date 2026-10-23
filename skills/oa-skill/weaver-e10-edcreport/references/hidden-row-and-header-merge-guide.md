# 空白行 与 表头合并（Excel → 报表 对齐）

> 触发场景：用户拿一份 Excel 效果图来搭表，之后反馈
> 「第 N 行多了一个空白行」「表头标题没有参考 Excel 合并」。
> 2026-09-14 事故实录：考勤汇总报表 `1314970921403138199`。

## 一、`rows[i].size = 0` **不会隐藏行**

workbook `sheets.Sheet1.rows` 是**行高数组**，不是可见性开关。

| 写法 | 服务端行为 | 结果 |
|------|-----------|------|
| `{ size: 0 }` | 规范化为 `null`（落回默认行高） | ❌ **照旧渲染成一条可见空行** |
| 不写这一行 | — | ✅ 该行不存在 |
| `rowVisible: 0`（field 层） | 仅影响字段格 | 不用于「整行不要」 |

**结论：要让某一行不存在，就在 `dataTable` + `rows` 里根本不放它，后续行整体上移。**

### Excel 的 `hidden=1` 行怎么处理

Excel 里 `ht="0" hidden="1"` 的行（常见用途：表头与数据之间的**垫行**），
在 Excel 中不可见 → 报表里也应**直接删掉**，让表头下一行就是数据行。

对齐判据（用户视角）：Excel 隐藏行=看不见 → 报表里也不该出现这一行。

## 二、合并单元格 = workbook `spans`

> 合并**只能**靠 `sheets.Sheet1.spans` 表达，`style.border`/`hAlign` 与合并无关。

```js
spans = [
  { row: 2, col: 0,  rowCount: 2, colCount: 1 },   // 固定列表头纵向合并（Excel B3:B4）
  { row: 2, col: 45, rowCount: 1, colCount: 3 },   // 日期区横向合并（Excel AU3:AW3）
]
```

| 字段 | 含义 | 对应 `fields` |
|------|------|---------------|
| `row` / `col` | 合并区左上角（**0-based**，row=行、col=列） | `x` = row、`y` = col |
| `rowCount` | **行**跨度 | `fields.xCount` |
| `colCount` | **列**跨度 | `fields.yCount` |

要点：

1. **`row`/`col` 是 0-based**，而 Excel 的 `mergeCells` 是 1-based → 换算 `row = excelRow - 1`、`col = excelColNum - 1`。
2. 日期/交叉维度区块本就必须 `colCount = 块宽`（本包默认日期块 3 列），**不要再叠加一次**，否则块宽翻倍。
3. 实测：**只写 `spans` 即可生效**，可不写 cell 级 `rowCount`/`colCount`（服务端统一按 spans 回写 `xCount`/`yCount`）。
4. 合并区内的非左上角单元格**不要放内容**（Excel 同理），否则合并语义混乱。

### 从 Excel 提取 mergeCells（本环境 xlsx 常被 openpyxl 拒读）

`openpyxl` 遇到非法 `styles.xml`（如非法 border `style`）会抛 `ValueError` → 改为**解 zip 直读 XML**：

```python
import zipfile, xml.etree.ElementTree as ET
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
sh = ET.fromstring(zipfile.ZipFile(path).read("xl/worksheets/sheet1.xml"))
mc = sh.find(f"{NS}mergeCells")
refs = [m.attrib["ref"] for m in mc.findall(f"{NS}mergeCell")]   # ["B3:B4", "AU3:AW3", ...]
```

映射规律（常见表头）：

| Excel merge | 报表 spans | 说明 |
|---|---|---|
| `B3:B4` … `AT3:AT4` | 每列 `{row:2, col:i, rowCount:2, colCount:1}` | 固定列表头纵向跨「列名 + 星期」两行 |
| `AU3:AW3` | `{row:2, col:45, rowCount:1, colCount:3}` | 日期表头横向跨 3 列 |
| `AU4:AW4` | `{row:3, col:45, rowCount:1, colCount:3}` | 星期行同理 |
| `AU1:CH1`（跨全部日期块） | 设计态只写**一个块宽**（`colCount:3`） | 设计态只摆 1 个日期块，展开由引擎做；照抄 42 列会把块宽搞错 |

## 三、验证：渲染回读（唯一可信证据）

设计态 `getReportDevInfo` **不返回 workbook**（`workbookProps.sheets` 恒为 `{}`），
只能看 `fields`（含 `xCount`/`yCount`）——**不能证明渲染效果**。要看用户到底看见什么，必须走渲染链：

```
POST /api/edc/report/view/analysis   (multipart；sheetId=reportId、pageFilter、pageNum…)
   → data.json[0] = sessionKey
GET  /api/edc/report/view/getJsonStr?sessionKey=<key>
   → gunzip → workbook（含展开后的 dataTable / rows / spans）
```

判据：

- **无多余空行**：下一行（0-based = `数据行 index`）应已是非空数据行。
  例：表头 r2、星期 r3 → r4 必须是数据（此前 r4 全空 = 事故）。
- **表头合并生效**：渲染 `spans` 中应存在 `{row:表头行, rowCount:2, colCount:1}` 共 N 条（N=固定列数）、
  以及 `{row:表头行, col:日期起始列, colCount:块宽}`。

⚠️ 渲染有 **50000 单元格上限**（超限 `code:555`）。估算：`渲染行数 × 列数`。
本例 `1004 × 48 ≈ 48192` 勉强过关；列维度一展开就会超，需靠默认查询条件收敛。

## 四、修复动线（保持同一 reportId）

1. `getReportDevInfo` 取当前 `designKey`；`baseInfo` 取当前 `name`。
2. 按新布局重建 workbook（`rows` 少一行、`spans` 补齐）。
3. `saveReportDevInfo`（multipart：`groupId/appId/reportId/name/nameLabelId/designKey/workbook`）。
4. 渲染回读复核 → 交设计器地址。

**不需要**重新建表，**不要**另建报表（一次任务只建 1 壳）。
