# 公式单元格 API 写入规范

> **适用场景**：通过 API / 脚本写入报表 workbook（`saveReportWithCacheConfig` + `saveReportDevInfo`），或生成含 Formula 单元格的 ReportProps JSON。  
> **权威原则**：设计器手动保存的格式为准；文档与脚本冲突时以 `getReportDevInfo` 回读结果为准。

---

## 一、问题现象

设计器里输入 `=IF(J3=0,0,L3/J3)` 能正常保存并展示，但 **API 脚本写入「相同公式」可能导致设计器整页空白**。

**根因不是 IF 函数被禁用**，而是持久化字段格式与手动保存不一致：

| 字段 | 设计器手动保存 ✅ | 脚本 API 常见错误 ❌ |
|------|-------------------|----------------------|
| `cellText` / 顶层 `formula` | `IF(J3=0,0,L3/J3)` **无前导 `=`** | `=IF(J3=0,0,L3/J3)` **带 `=`** |
| `countType` | `count` | `none` |
| `displayType` | `Group` | `List` |
| `groupType` | `null` | `none` |
| `style.formatter` | 空字符串 | `0.00%`、`General` 等 |

平台源码（`EdcReportDevDesignServiceImpl`）从 workbook 提取 Formula 时：

```java
if (field.getCellType() == Formula) {
    field.setCellText(cell.getFormula());  // 原样写入 DB
}
```

设计器保存时会去掉 leading `=`；脚本若 workbook 顶层 `formula` 带 `=`，DB 里 `cellText` 也会带 `=`。  
设计器再次加载时 SpreadJS 可能再补 `=` → 变成 `==IF(...)` 或解析失败 → **整页空白**。

DB 种子数据同样 **不带 `=`**：`'IFERROR(G5/F5,"--")'`、`'SUM(F5)'`。

---

## 二、Agent 必遵守则（硬约束）

生成或修改含公式单元格的报表时，**必须**同时满足：

1. **`cellText` 与 workbook 顶层 `formula` 均不带前导 `=`**  
   - 设计器输入：`=IF(J3=0,0,L3/J3)`  
   - API 存储：`IF(J3=0,0,L3/J3)`  
   - 写入前统一：`bare = formula_expr.lstrip("=")`

2. **`countType` 必须为 `count`**（勿用 `none`）

3. **`displayType` 必须为 `Group`**（分组报表中的公式格；勿用 `List`）

4. **`groupType` 必须为 `null`**（JSON 中写 `null`，勿写 `"none"`）

5. **`expandType` 为 `NoExpand`**

6. **`style.formatter` 为空字符串**（与手动保存对齐；百分比展示依赖公式结果或后续在设计器设格式，脚本勿擅自写 `0.00%`）

7. **父格坐标**：公式格与同级 Field 子格一致，指向根格（如 `leftX=2, leftY=5` 对应 F 列责任人，0-based）

8. **双保存**：`saveReportWithCacheConfig` + `saveReportDevInfo`，保存后用 `getReportDevInfo` 回读验证

9. **除零保护**：占比/达成率类公式推荐 `IF(分母=0,0,分子/分母)`，与设计器手动写法一致

---

## 三、workbook 单元格结构（dataTable）

Formula 单元格在 workbook `dataTable[row][col]` 中的标准结构：

```json
{
  "formula": "IF(J3=0,0,L3/J3)",
  "style": {
    "hAlign": 1,
    "vAlign": 1,
    "formatter": "",
    "cellType": {
      "typeName": "FormulaCellType",
      "editorType": 1,
      "cellType": "Formula",
      "cellText": "IF(J3=0,0,L3/J3)",
      "displayType": "Group",
      "countType": "count",
      "groupType": null,
      "expandType": "NoExpand",
      "leftX": 2,
      "leftY": 5,
      "topX": -1,
      "topY": -1,
      "refX": -1,
      "refY": -1,
      "subordination": ["", ""],
      "formatterType": [],
      "orderType": "no",
      "isActiveParent": false,
      "arrowType": "None",
      "textDirection": "FromLeftToRight",
      "allowOverflow": true,
      "hiddenContext": "0",
      "transSelectOptions": [],
      "browserType": [],
      "thumbnail": "NoDisplay"
    }
  },
  "tag": { "formatterType": ["common"] }
}
```

**注意**：顶层 `formula` 与 `style.cellType.cellText` **内容相同且均无前导 `=`**。

---

## 四、参考实现 `make_formula()`

```python
def make_formula(formula_expr, formatter=""):
    """构建 Formula 单元格，格式对齐设计器手动保存。"""
    bare = formula_expr.lstrip("=")
    ct = {
        "allowOverflow": True,
        "typeName": "FormulaCellType",
        "editorType": 1,
        "leftX": ROOT_ROW,
        "leftY": ROOT_COL,
        "topX": -1,
        "topY": -1,
        "refX": -1,
        "refY": -1,
        "expandType": "NoExpand",
        "displayType": "Group",
        "cellType": "Formula",
        "cellText": bare,
        "transSelectOptions": [],
        "browserType": [],
        "thumbnail": "NoDisplay",
        "hiddenContext": "0",
        "orderType": "no",
        "formatterType": [],
        "subordination": ["", ""],
        "countType": "count",
        "groupType": None,
        "isActiveParent": False,
        "arrowType": "None",
        "textDirection": "FromLeftToRight",
    }
    fmt = formatter if formatter is not None else ""
    return {
        "style": {"hAlign": 1, "vAlign": 1, "formatter": fmt, "cellType": ct},
        "formula": bare,
        "tag": {"formatterType": ["common"]},
    }
```

项目参考：`.workbuddy/apply_ebu_from_xlsx.py` 的 `make_formula()`。

---

## 五、公式表达式规范

### 5.1 单元格引用

- 使用 Excel A1 风格：`J3`、`L3`、`AA3`
- 行号与数据行一致（通常第 3 行即 `x=2` 的数据行写 `...3`）
- 引用同报表内 Field 汇总格，不引用数据集字段名

### 5.2 常用模式

| 场景 | 设计器输入 | API 存储（无前导 `=`） |
|------|-----------|------------------------|
| 达成率 | `=IF(J3=0,0,L3/J3)` | `IF(J3=0,0,L3/J3)` |
| 业绩占比 | `=IF(L3=0,0,M3/L3)` | `IF(L3=0,0,M3/L3)` |
| 合计 | `=SUM(F4:F10)` | `SUM(F4:F10)` |
| 安全除法 | `=IFERROR(G5/F5,"--")` | `IFERROR(G5/F5,"--")` |

### 5.3 IF / IFERROR

- **IF、IFERROR 均允许**通过 API 写入；此前「IF 导致空白」是格式错误，不是函数限制
- 占比类公式 **推荐** `IF(分母=0,0,...)` 而非裸除法

### 5.4 禁止写法

| 禁止 | 原因 |
|------|------|
| `cellText: "=SUM(A1)"` | 双 `=` 导致 SpreadJS 解析失败 |
| `countType: "none"` | 与手动保存不一致，可能引发展示异常 |
| `displayType: "List"` | 公式格应为 `Group` |
| `groupType: "none"` | 应为 `null` |
| 仅写 `style.cellType.cellText` 不写顶层 `formula` | workbook 与设计器可能不同步 |

---

## 六、验证清单

写入公式后，Agent **必须**执行：

### 6.1 `getReportDevInfo` 回读

对每个 Formula 格（如 K3 → `x=2, y=10`）检查：

- [ ] `cellType` 为 `Formula`
- [ ] `cellText` **不以 `=` 开头**
- [ ] `countType` 为 `count`
- [ ] `displayType` 为 `Group`
- [ ] `groupType` 为 `null`
- [ ] 公式内容与预期一致（如 `IF(J3=0,0,L3/J3)`）

### 6.2 保存接口

- [ ] `saveReportWithCacheConfig` 返回 200
- [ ] `saveReportDevInfo` 返回 200
- [ ] `checkSave` 返回 200（可选）

### 6.3 设计器 smoke test

- [ ] 刷新设计器 URL 后页面非空白
- [ ] 公式格可点击编辑，显示为 `=IF(...)`（设计器 UI 会自动加 `=`）
- [ ] 预览/解析后公式列有数值

### 6.4 本地预检

```bash
python scripts/validate_report_config.py <配置文件路径>
```

脚本会对 Formula 单元格检查前导 `=`、`countType`、`displayType` 等（见脚本内 `validate_formula_fields`）。

---

## 七、与父格 / 跨数据集筛选的关系

- 公式格 **不参与** subordination / leftFilterField（通常 `subordination: ["", ""]`）
- 公式引用的是 **同报表内已配置好的 Field 汇总格**（如 L3 总业绩、J3 指标）
- 被引用的 Field 格若跨数据集，须先按 `cross-dataset-filter-guide.md` 配好筛选；公式本身不再重复配 fieldKey

---

## 八、EBU 经营报表示例（37 列）

| 列 | 字段 | 公式（API 存储，无前导 `=`） |
|----|------|------------------------------|
| K | 达成率 | `IF(J3=0,0,L3/J3)` |
| R | 新客户业绩占比 | `IF(L3=0,0,M3/L3)` |
| S | 纯专项业绩占比 | `IF(L3=0,0,N3/L3)` |
| T | 信创客户业绩占比 | `IF(L3=0,0,O3/L3)` |
| X | 新签合同个数占比 | `IF(V3=0,0,W3/V3)` |
| Z | 纯专项合同个数占比 | `IF(V3=0,0,Y3/V3)` |
| AB | 信创合同个数占比 | `IF(V3=0,0,AA3/V3)` |

报表 ID 示例：`1304979556231593985`  
验证脚本：`.workbuddy/verify_formulas.py`

---

## 九、相关文档

- `SKILL.md` — 能力一步骤 6.2 公式配置
- `ai-report-workflow.md` §六 — 工作流中的公式规则
- `report-config-schema.md` §2.5 — Formula Schema
- `cross-dataset-filter-guide.md` — 跨数据集筛选（与公式格配合）
- `report-building-guide.md` §8.2 — 占比/同环比为前端 SpreadJS 计算
