# 定点修改 · 禁止整表重扫（强制）

> **适用**：用户指出「某处不对 / 修某一格 / 改某条查询 / M4 父格」等**已定位**问题；以及「只改列宽 / 冻结 / 居左 / 分页 / 快照 / 打印」等**已列明范围**的调整；**改已有报表设计器内容**时一律适用。 
> **目标**：少读配置、少调 API、少改无关格，避免整表重扫浪费时间与额度。 
> **总闸（更高优先级）**：`user-request-scope-only-guide.md` — **仅改用户点名项**；未点名禁止改删、禁止额外命令。 
> **硬约束**：用户说「只对提出的要求做调整，其他不要动」时，**样式/行高/字体/颜色/边框/未点名格一律禁止改写**——即便为写 workbook 必须整表回传，语义上也只能 patch 点名项。 
> **禁止**：因编辑需求而重新走完整「需求分析 → 识别全部搭建配置 → 整表重建」。

---

## 一、硬原则

| 原则 | 说明 |
|------|------|
| **仅用户点名（总闸）** | 见 `user-request-scope-only-guide.md`；CLI `e10-cli report fix --help` |
| **听指定位置** | 用户点名单元格（如 M4）、查询条件名、字段名、dataset → **只处理该范围** |
| **禁止整表重扫** | 不得因修一格而：全量 dump 所有 fields、重拉全部数据集元数据、重跑整表 verify、从参考表整表 clone 覆盖 |
| **禁止顺手重构** | 未点名时禁止批量改其它 Field 父格、禁止重写全部查询条件、禁止「顺便」对齐整表样式 |
| **禁止顺手改样式（强制）** | 用户未点名「改样式/行高/主题/字体/颜色」时：**禁止**重建 cell `style`、禁止改 `rows[].size`（行高）、禁止用默认模板覆盖已有外观。列宽/冻结/居左 ≠ 许可重做报表样式 |
| **禁止拆合并（强制）** | **没有任何规则要求拆分合并单元格**。从 fields 重建 workbook 时必须带上原 `xCount`/`yCount` → `cell.rowCount`/`colCount` + `sheet.spans`；漏写 = 等价于取消合并。用户未要求「取消合并」时禁止丢 spans |
| **禁止擅自删除** | 未点名删除时禁止 `deleteReport` / `lifecycle delete` / `cleanup shells` |
| **最小读** | 只需 `getReportDevInfo` 时优先按坐标/条件 id **过滤后使用**；不要为定位一格打印全表 |
| **最小写** | 查询 → 只 `saveQueryItem` 改目标条；父格/超链接 → 在**完整 workbook 保护**前提下只 patch 目标 cellType（见下） |

---

## 二、问题类型 → 动作范围

| 用户说法（例） | 允许动作 | 禁止 |
|----------------|----------|------|
| 「M4 左/上父格不对」 | 只读 `(3,12)`（及占位依赖格如 `(3,11)`）；只改该 Const 的父格/`pcHreflink` | 重扫全部 Const/Field 父格；整表从兄弟报表覆盖 |
| 「供应商等级没选项」 | 只读/改该条 `getQueryItem`；按 §3.2 拉该字段 options | 重配全部查询条件；重扫布局 |
| 「查询显示方式不对」 | 只改目标条 `showWhere` | 新建一套条件 |
| 「某 Field 绑错」 | 只改该格 `name`/`fieldKey` + workbook 对应 cell | 全表 remap |
| 「整表父格都要默认」 | **仅当用户明确整表要求** 才批量；否则只更新 Skill 规则 | 把「规则说明」当成改线上表的许可 |
| 「列宽 N / 冻结表头 / 居左」 | 只改 `width`+`columns`、冻结锚点、`showLocation`（见 `layout-showlocation-freeze-guide.md`） | 重建整表 style/行高；猜 `showLocation=0`；只写 `frozenRowCount` 不写 `fixed-cell-tag`；**丢掉 spans/合并** |

---

## 二点五、合并单元格（spans）保护

服务端从 workbook **`spans`**（或 cell.`rowCount`/`colCount`>1）回写 `field.xCount`/`yCount`。 
`safe_report_save.js` 的 `fieldToCell` / `buildWorkbookFromFields` **必须**把 `xCount`/`yCount` 写回 cell + `spans`。

**反例（本次事故）**：只为改列宽/冻结，用无 `spans` 的 workbook 整表 `saveReportDevInfo` → 表头标题、表尾合计行合并被拆成 1×1。 
**正例**：有原 workbook 时优先 `mergeWorkbookSafe` 原地 patch；无 workbook 时从 fields 重建也必须带 spans。

---

## 三、布局类定点改（仍须保护设计区）

修**单格**父格/超链接时：

1. **仍须**按 `safe-partial-save-guide.md` 提交**完整** `fields` + 从 fields 重建的 workbook（禁止空/残 workbook）。
2. **语义上只改目标格**：其它格原样写回；禁止顺带改 Field 左父格链。
3. **Const**：`ConstCellType` 必须显式带 `leftX/leftY/topX/topY` 与（若有）`pcHreflink`——服务端从 workbook 回写；缺 `leftX` → `0` → 伪 A1。见 `report-self-check-guide.md` §2.2。
4. **保存后自检范围收窄**：只断言**被改格** + Field 总数不降；**不要**为修 M4 再跑全表字段遍历报告。

```
用户指 M4 →
 GET getReportDevInfo（内存过滤 x,y）
 patch fields 中该格 + 重建 workbook（全表 cell 保留，仅该格 ConstCellType 变）
 saveReportDevInfo
 回读：仅检查该格 left/top/href/text + Field.count
```

---

## 四、查询类定点改

1. `getQueryItem` → 按显示名 / `asNameIndex` / `id` **定位一条**。
2. 只改该条：`showWhere` / `displayType` / `selectOptions` / `relation` 等。
3. 下拉选项：`selectKey`=选项 ID，`selectValue`=显示名；`fieldName` 用裸雪花 ID。见 `query-condition-api-guide.md` §3.2。
4. 回读**只核对该条**，不必打印全部 queryItems。

---

## 五、列宽 / 冻结 / 居左（样式敏感）

1. **必加载** `layout-showlocation-freeze-guide.md`。 
2. 其它 cell 的 `style` JSON **原样**进入 workbook；禁止为省事用空白 style 重生。 
3. 居左 = `showLocation: 1`（**不是 0**）；冻结表头 = `fixed-cell-tag` 锚点 + `tag.fixed` + `tag.fixedCell`，不能只设 `frozenRowCount`。 
4. 回读只断言：目标列宽、`showLocation`、锚点 `(x,y)`/`fixed==1`；**不要**为调列宽去「优化」行高。

---

## 六、与其它文档关系

| 文档 | 关系 |
|------|------|
| `user-request-scope-only-guide.md` | **总闸**：仅改用户点名项；禁止擅自改删 |
| `safe-partial-save-guide.md` | 写布局时的 workbook 完整性（与「语义定点」不矛盾） |
| `layout-showlocation-freeze-guide.md` | 居左枚举 + 冻结锚点；禁止伤样式 |
| `report-self-check-guide.md` | 落库门禁；定点场景下**检查项可裁剪到改动面** |
| `datasource-selection-and-parent-filter-guide.md` §〇 | 父格规则；「默认」≠ 批量改已有表 |
| `query-condition-api-guide.md` | 查询/选项映射 |
| `report-delivery-contract.md` | 仍可先交设计器链接；后台只验证改动面 |
