# 报表落库自检（强制）

> **适用**：API/脚本保存布局后、交付设计器链接前（可后台跑，但**不得跳过**）。 
> **目标**：尽早发现字段丢失、伪父格、绑定失败、超链接被冲掉，避免「设计器看着有格、取数/父格全错」。

---

## 一、父格坐标语义（勿混）

| API `leftX/leftY` 或 `topX/topY` | 设计器含义 | 说明 |
|----------------------------------|------------|------|
| **`-1, -1`** | **默认** 或 **无** | 普通 Const / 单数据集 Field 的常见正确态 |
| **`0, 0`** | **自定义 → 原点 (0,0)** | **不是默认**；写成 0,0 会显示父格「不对」 |
| **其它 `x,y`** | **自定义** 指向该坐标 | 多数据集入口、交叉、**超链接占位依赖**等 |

---

## 二、按单元格类型的父格规则

### 2.1 普通 Const（表头 / 标题 / 无链接）

| 项 | 规则 |
|----|------|
| 左父格 | **`-1,-1`** |
| 上父格 | **`-1,-1`** |
| 禁止 | `(0,0)`；勿把「默认」误写成原点 |

### 2.2 超链接 Const（`pcHreflink` / `h5Hreflink`，URL 含 `{L4}` `{C4}` 等）

> **事故**：把「左父格默认」套到「点击查看」上 → 设计器左/上显示不对，且 `{L4}` 无法解析；或重建 workbook 时丢掉 `ConstCellType.cellText` → 保存后 `cellText` 变空、`pcHreflink` 丢失。

| 项 | 规则 | 例（供应商表 M4） |
|----|------|-------------------|
| **上父格** | 无横向扩展时必须 **`topX=topY=-1`**（不需要上父格） | `(-1,-1)` |
| **左父格** | **禁止**一律改成默认；须指向占位符依赖的数据格 | `{L4}` → 左父格 **`(3,11)`**（同行「数据ID」） |
| **链接元数据** | 须进 **workbook `ConstCellType`**（`pcHreflink`/`openType`/`cellText`/`left*`/`top*`）；仅写 `fields[]` **不够** | `/sp/ebdfpage/card/0/{sourceId}/{L4}` |
| **workbook** | `ConstCellType` 必须含：`cellText`、`leftX/leftY/topX/topY`、有链接时还要 `pcHreflink` | 服务端 `saveReportDevInfo` **从 cellType 回写 fields**；缺 `leftX` → Java int **0** → 伪 `(0,0)`；缺 `pcHreflink` → 链接丢失 |
| **禁止** | 只塞 `{typeName,cellText}` 的残 ConstCellType；禁止左=`(0,0)`；禁止有 `{Ln}` 却左=`-1,-1` |

**占位符 → 左父格**（自检算法）：

1. 从 `pcHreflink`/`h5Hreflink` 提取 `{L4}` / `{C4}` / `{Ln}` 等。
2. `{L4}`：同行纵向扩展语境下，左父格应指向同列（或约定列）上提供 ID 的 Field（本需求为 `(3,11)`）。
3. 若 URL 含占位而 `leftX/leftY === -1` → **FAIL**（不是「默认正确」）。
4. 若 `topX/topY !== -1` 且无横向交叉需求 → **FAIL**。

### 2.3 Field（单数据集、无指定计算）

| 场景 | 左父格 |
|------|--------|
| **新建**报表 | 优先 **`-1,-1`（默认）** |
| **已有**报表 | **禁止**用户未点名时批量改父格 |

---

## 三、保存门禁（每次 `saveReportDevInfo`）

### 保存前

1. `fields` 中 `cellType=Field` 数量 ≥ 保存前（或与预期列数一致）。
2. workbook `dataTable` 内 `FieldCellType` 数量 ≥ Field 数。
3. 每个 **Const**：workbook `ConstCellType` 须含 `cellText`（有文案时）以及显式 **`leftX/leftY/topX/topY`（常用 -1，禁止省略）**。
4. 每个 **超链接 Const**：`ConstCellType` 须含非空 `pcHreflink`、`openType`，且父格与 `fields` 一致（服务端以 workbook 为准回写）。
5. 每个 Field：`name` ∈ `fieldsAndOriginFields.fieldsKey[].name`（须带 `field_`；禁止裸雪花 ID）。 
 - 拉 fieldsKey 参数名用 **`datasetId`**（不是 `dataSetId`）。

### 保存后立刻回读

| 检查项 | 失败标准 |
|--------|----------|
| Field 数量 | 比保存前减少 → **立即失败**，禁止再改，优先恢复 |
| Field.`name` | 裸 ID 或不在 fieldsKey → FAIL（`e10-cli report verify bind`） |
| 普通 Const 父格 | `left=top=(0,0)` → FAIL（伪自定义 A1） |
| 超链接 Const | 缺 `pcHreflink` / `cellText` 空 / `top≠-1` / 含 `{L*}` 但 `left=-1` 或 `left=(0,0)` → FAIL |
| 同数据集 leftFilterField | Field 上仍有跨源 leftFilter → WARN/FAIL |

```bash
e10-cli report verify bind <reportId> [appId] # 字段绑定
e10-cli report verify self <reportId> [appId] # 父格/超链接自检
e10-cli report verify all <reportId> [appId] # 自检 + 绑定（推荐）
```

---

## 四、Agent 自检脚本逻辑（摘要）

```javascript
function assertParents(fields) {
 for (const f of fields) {
 if (f.cellType !== 'Const') continue;
 const origin =
 f.leftX === 0 && f.leftY === 0 && f.topX === 0 && f.topY === 0;
 const href = f.pcHreflink || f.h5Hreflink || '';
 if (origin && !href) {
 throw new Error(`Const(${f.x},${f.y}) 父格(0,0)=伪自定义A1，应为-1,-1`);
 }
 if (!href) continue;
 // 超链接：上父格默认无
 if (f.topX !== -1 || f.topY !== -1) {
 throw new Error(`链接格(${f.x},${f.y}) 不需要上父格，top 应为 -1,-1`);
 }
 if (!f.cellText) {
 throw new Error(`链接格(${f.x},${f.y}) cellText 为空（workbook 可能未写 ConstCellType）`);
 }
 // URL 占位依赖左父格，禁止「默认」
 if (/\{L\d+\}|\{C\d+\}/.test(href)) {
 if (f.leftX === -1 && f.leftY === -1) {
 throw new Error(`链接格(${f.x},${f.y}) 含占位符但左父格为默认，应指向依赖数据格`);
 }
 if (f.leftX === 0 && f.leftY === 0) {
 throw new Error(`链接格(${f.x},${f.y}) 左父格不能为(0,0)`);
 }
 }
 }
}

function assertWorkbookConstCellType(dataTable, fields) {
 for (const f of fields) {
 if (f.cellType !== 'Const') continue;
 const cell = dataTable?.[String(f.x)]?.[String(f.y)];
 const ct = cell?.style?.cellType;
 if (!ct || ct.typeName !== 'ConstCellType') {
 throw new Error(`workbook 缺 ConstCellType @(${f.x},${f.y})`);
 }
 if ((f.cellText || f.text) && !ct.cellText) {
 throw new Error(`workbook 缺 cellText @(${f.x},${f.y})，保存会冲掉文案`);
 }
 // 缺 leftX 时服务端写成 0 → 伪自定义 A1
 for (const k of ['leftX', 'leftY', 'topX', 'topY']) {
 if (ct[k] === undefined || ct[k] === null) {
 throw new Error(`workbook ConstCellType 缺 ${k} @(${f.x},${f.y})，会落成 0`);
 }
 }
 if (f.pcHreflink && ct.pcHreflink !== f.pcHreflink) {
 throw new Error(`workbook 缺/错 pcHreflink @(${f.x},${f.y})（服务端只认 cellType）`);
 }
 }
}

function assertFieldPreserved(before, after) {
 const n = (fs) => fs.filter((f) => f.cellType === 'Field').length;
 if (n(after) < n(before)) throw new Error('Field 被冲掉，禁止继续改');
}
```

---

## 五、与交付节奏

- 布局落库成功 → **先交设计器地址**（`report-delivery-contract.md` §〇）。
- 本节自检可后台跑；**FAIL 必须补丁修复并告知**，不得假装完成。
- **禁止**：为修一格 Const 父格而提交残缺 workbook（会导致 Field 全变 Const，或 Const 文案/超链接被冲掉）。修父格必须 **整表 Field + ConstCellType 完整写入 workbook**。

---

## 六、相关文档

| 文档 | 关系 |
|------|------|
| `field-bind-exact-match-guide.md` | name ∈ fieldsKey |
| `datasource-selection-and-parent-filter-guide.md` §〇 | 单数据集左父格默认；**勿**套用到超链接 Const；勿擅自改已有表 |
| `safe-partial-save-guide.md` | 禁止空 workbook；须从 fields 重建 dataTable |
| `e10-cli report verify bind` | 绑定门禁 |
| `targeted-fix-guide.md` | 用户点名某处不对时禁止整表重扫 |
