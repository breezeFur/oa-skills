# 报表事件 · 超链接传参（强制）

> **UI**：设计器右侧 **事件** Tab — PC链接地址 / H5链接地址 / 打开方式
> **帮助手册依据**：知识库 §5.3「查询条件传参」、§6.6「跳转数据列表页」；搭建指南「事件」Tab
> **源码**：`HreflinkTrans` · `SpreadUtil.getFormulaParams` · `DynamicParamsBuilder` · `HreflinkCellType`
> **CLI**：`e10-cli report validate href --file cell.json` / `--map "弹出页"`

---

## 〇、能力与落库键

| UI | 落库字段 | 说明 |
|----|----------|------|
| PC链接地址 | **`pcHreflink`** | 分析页 PC 点击跳转；运行时别名 `hreflink` |
| H5链接地址 | **`h5Hreflink`** | 移动端优先；运行时别名 `mbhreflink`；有值且移动端时覆盖 PC 链接 |
| 打开方式 | **`openType`** | 见 §二 |

须写入 **`fields[]` + workbook `style.cellType`**（Const/Field 均可配事件；超链接占位 Const 另遵守父格规则）。

---

## 一、帮助手册规则（产品语义）

摘自报表功能说明 / 知识库（Agent 须按此话术与用户对齐）：

1. **事件动作可传递单元格值**（当前格及其父格值；**父格的父格也支持**）。
2. **可传递查询条件值**（查询条件标识形如 `{searchfield001}`）。
3. **跳转列表示例**：在链接中拼接单元格坐标参数，如
 `/sp/ebdfpage/list/xxx?ry=B5&kssj=E3`
 （`B5`/`E3` 表示取该格展开后的实际值）。
4. 打开方式 UI：**弹出页 / 当前页 / 执行js代码**。

---

## 二、打开方式 `openType`

| UI（事件面板） | 落库值 | 运行时 |
|----------------|--------|--------|
| **弹出页** | **`blank`**（默认；空则归一为 blank） | 新窗口/弹层 |
| **当前页** | **`self`** | 当前页跳转 |
| **执行js代码** | **`jsscript`** | 将链接内容当 JS 执行 |

禁止自造 `popup` / `window` 等别名。

**链接字符**：`?` / `&` 必须是 **ASCII**（`?`=U+003F）。禁止中文全角 `？`（U+FF1F），否则预览点击无反应（事故：E7 全角 vs F7 半角）。

```bash
e10-cli report validate href --map "弹出页"
e10-cli report validate href --map "执行js代码"
e10-cli report validate href --file cell.json --fix # 全角？→ASCII ?
```

---

## 三、传「单元格值」语法（帮助手册 · 强制）

> **范围**：仅当前格 + 设置链接字段的**左/上父格**（父格的父格也支持）。超出父格链的坐标**不能**取值。

### 3.1 查询串传参（台账过滤 / 外链最常用）

格式：`参数名=字段坐标`（坐标**不加** `{}`）。

| 规则 | 说明 |
|------|------|
| 链接**已有** `?` | 用 `&` 拼接：`...&aa=D4&bb=C4` |
| 链接**没有** `?` | 第一个参数用 `?`：`...?aa=D4&bb=C4` |
| 多值 | 多个 `&参数名=坐标` |
| 参数名 | **避免**系统关键字：`id`、`name` 等 |
| 父格链 | 左父格为默认时，E4→D4→C4，故 E4 链接可传 E4/D4/C4 |

```text
# 示例1（已有 ?）
https://weapp.xxx.cn/sp/ebdfpage/list/1092...?id=1123...&aa=D4&bb=C4

# 示例2（无业务 ? 时，第一个单元格参用 ?）
https://weapp.xxx.cn/sp/ebdfpage/list/1092...?aa=D3&bb=C4

# 百度等外链（勿用 id/name 作参数名）
https://www.baidu.com/s?zclb=D7&zcmc=E7&cx={searchfield001}
```

运行时将 `D4`/`C4` 替换为对应单元格展开后的**实际值**。

### 3.2 路径占位（表单布局 card 等）

布局地址里的 `$dataid$` 等改为 **`{坐标}`**（**带花括号**）：

```text
/sp/ebdfpage/card/0/1123053786772799489/{C4}
```

### 3.3 其它写法（次要）

| 写法 | 说明 |
|------|------|
| **`{L4}` / `{A1}`** | 路径或需花括号的场景 |
| **`$datasetId.fieldName$`** | 同行数据集字段（引擎支持；**手册主推仍是坐标传参**） |

**超链接 Const 父格（强制）**：若链接依赖坐标数据格且该格是 Const 占位：

- **左父格**须指向提供该值的数据格，**禁止**默认 / `(0,0)`
- **上父格**通常 `-1`

普通 **Field** 纵向列表、左父格默认时：可按 §3.1 传当前格及左侧父格链坐标（如 E4 传 D4、C4）。

详见 `report-self-check-guide.md` §2.2。

---

## 四、传「查询条件值」语法

查询条件在高级搜索中的标识：

| 标识 | 含义 |
|------|------|
| `{searchfield001}` | `asNameIndex=1` → `searchfield` + 三位补零 |
| `{searchfield002}` | `asNameIndex=2` |
| `{searchfield001_start}` / `{searchfield001_end}` | 日期区间起止 |

规则：

1. `asNameIndex` 与 `showOrder` 一致且唯一 >0（见 `query-condition-api-guide.md`）。
2. 链接中写 `{searchfield00x}`，预览时替换为用户当前查询值。
3. 也可在表头 Const 的 `cellText` 中引用同一标识显示查询值。
4. 系统参数（如 `{userid}`、`{date}`、`{year}`）亦可出现在链接中（`DynamicParamsBuilder`）。

示例：

```text
/sp/ebdfpage/list/864399547574140928?creator={searchfield001}&dept=B5
```

> 查询条件用 `{searchfield00x}`；单元格在查询串里用 **无花括号** 坐标（`dept=B5`）。

---

## 五、完整写入示例

```json
{
 "cellType": "Field",
 "name": "3506271460832878820",
 "text": "资产名称",
 "pcHreflink": "https://www.baidu.com/s?zclb=D7&zcmc=E7&cx={searchfield001}",
 "h5Hreflink": "",
 "openType": "blank"
}
```

路径型示例（Const/Field 均可）：

```json
{
 "cellType": "Const",
 "cellText": "点击查看",
 "pcHreflink": "/sp/ebdfpage/card/0/1123053786772799489/{C4}",
 "openType": "blank",
 "leftX": 3,
 "leftY": 2,
 "topX": -1,
 "topY": -1
}
```

---

## 六、Agent 检查清单

- [ ] `openType` ∈ `blank|self|jsscript`，UI 文案已映射
- [ ] 传单元格：查询串用 `参数名=坐标`（无 `{}`）；路径用 `{坐标}`；仅当前格+父格链
- [ ] 传查询条件：`{searchfield00x}`，asNameIndex 已对齐
- [ ] 参数名避免 `id`/`name` 等系统关键字
- [ ] PC/H5 分端：移动需要时填 `h5Hreflink`
- [ ] 双写 fields + workbook；`safe_report_save` / fieldToCell 不丢链接键

---

## 关联

- `report-help-guide.md` §事件（摘要）
- `report-knowledge-base.md` §5.3 / §6.6
- `query-condition-api-guide.md` — asNameIndex / searchfield
- `report-self-check-guide.md` — 超链接父格
- `report-designer-feature-map.md` §7.2
