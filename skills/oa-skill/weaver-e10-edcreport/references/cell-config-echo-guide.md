# 单元格配置回显契约（数字格式 / 日期分组 / 统计等）

> **根因（已验证 · 设计器 `main.js` `getFormaterInfo`）**：工具栏「数字格式」按下拉回显时，用 `getFormaterInfo(formatter, formatterType)` 在目录中查找：`item.id === formatter || item.key1 === formatterType[0]`。  
> 若只写了近似的 `formatter`（如 `¥#,##0.00`）而 `formatterType` 仍为 `["common"]`，会**命中「常规」**，预览可能仍按货币算，但工具栏回显为「常规」。  
> **日期分组**等右侧属性回显依赖 `fields[].groupType`（及 workbook `style.cellType.groupType`）；重建 workbook 时 **禁止丢** `groupType` / `formatterType`。

---

## 一、硬约束

1. **写数字格式必须「formatter + formatterType」成对**，且取值来自下表目录，禁止自造格式串。
2. **写日期分组必须写 `groupType` 枚举**（见 §三），并写入 `fields[].groupType` + workbook `style.cellType.groupType`。
3. **重建 workbook（`fieldToCell`）须透传**：`groupType`、`formatterType`、`countType`、`orderType`、`displayType`、`expandType`；`tag.formatterType` 与 `fields[].formatterType` 一致。
4. **禁止整表一键刷单元格样式/边框**（用户未点名区域时）：见 `user-request-scope-only-guide.md`；若用户要求「整表设样式」→ **提示不支持全量**，请其给出区域（如 B3:H5）。
5. **字体/字号**须匹配设计器支持列表；不支持时 **提示用户**，按默认字号继续落库，**不要卡住**（见 §五）。
6. **同款样式复用（强制 · 性能）**：多个单元格配置**相同**数字格式/字体/边框/对齐时 → **只校验/确认一次**，其余格 **深拷贝同一 style 模板**；**禁止**逐格再跑 `validate format`、禁止逐格翻 JSON 样例对照。

---

## 一补充、同款样式复用（强制）

| 场景 | 正确做法 | 禁止 |
|------|----------|------|
| N 个度量列都要「货币」 | `edc-report validate format --map "货币"` **一次** → 得到成对 formatter/formatterType → 赋给所有目标格 | 对每一格再 `--map` / 再读一遍样例 JSON |
| 同区标题行同字体同色 | 建 `styleHeader` 对象，循环 `Object.assign` / 结构化克隆 | 每格单独拼 style、每格问目录 |
| 交付前抽检 | 对**唯一样式指纹**各验 1 次即可 | 按 cells.length 循环 `validate format --file` |

**指纹示例**：`formatterType[0] + '|' + formatter + '|' + font + '|' + backColor`  
相同指纹 → 直接复用已通过的 style 对象引用（或深拷贝），**不再**走 JSON 样例确认。

## 二、数字格式目录（工具栏回显金标准）

> 来源：设计器静态资源 `main.js` 中格式下拉 `g()` 目录。`￥` 为全角 `U+FFE5`（JSON 中写 `\uFFE5`）。

| 中文（工具栏） | `style.formatter`（必须全等） | `formatterType[0]`（key1） |
|----------------|------------------------------|----------------------------|
| 常规 | `General` | `common` |
| 数值 | `0.00_);[Red](0.00)` | `value` |
| **货币** | `"￥"#,##0.00_);[Red]("￥"#,##0.00)` | **`huobi`** |
| 会计专用 | `_ "￥"* #,##0.00_ ;_ "￥"* -#,##0.00_ ;_ "￥"* "-"??_ ;_ @_ ` | `kuaiji` |
| 短日期 | `yyyy/m/d;@__@` | `shortdate` |
| 长日期 | `yyyy"年"m"月"d"日";@` | `longdate` |
| 时间 | `h:mm:ss;@` | `time` |
| 百分比 | `0.00%` | `percent` |
| 分数 | `# ?/?` | `fenshu` |
| 科学计数 | `0.00E+00` | `kexuejishu` |
| 文本 | `@` | `text` |
| 其他 | （自定义） | `custom` |

### 错误写法（会导致回显「常规」）

| 错误 | 原因 |
|------|------|
| `formatter: "¥#,##0.00"` + `formatterType: ["common"]` | id 不在目录；key1=common → 命中常规 |
| 只改 `formatter`、不改 `formatterType` | key1 仍为 common → 常规 |
| 半角 `¥`（U+00A5）代替全角 `￥`（U+FFE5） | 与目录 id 不全等 |

### 正确写入示例（货币）

```json
{
  "style": {
    "formatter": "\"￥\"#,##0.00_);[Red](\"￥\"#,##0.00)"
  },
  "formatterType": ["huobi"],
  "tag": { "formatterType": ["huobi"] }
}
```

UI 内部拼串形态（勿原样当 formatter）：`"<formatter>__@__<key1>"`，如 `..."__@__huobi`。

---

## 三、日期分组（右侧「单元格」面板回显）

| 中文 | `groupType`（落库 / cellType） |
|------|-------------------------------|
| 不设置 | `none`（或未设置；面板默认） |
| **年份** | **`year`** |
| 年月 | `yearmonth`（部分 UI 文案控件曾用 `yearAndMonth`，**落库一律 `yearmonth`**） |
| 月份 | `month` |
| 年月日 | `yearmonthday` |
| 年周 | `yearweekday` |
| 月周 | `monthweekday` |

### 写入要求

1. `fields[].groupType = "year"`（等）
2. workbook `style.cellType.groupType` 同步（`fieldToCell` 必须带上，禁止只改 fields 行却重建时丢掉）
3. 回读校验：`getReportDevInfo` → 目标格 `groupType` 等于预期
4. **选中正确单元格再看回显**（例：D5=年月字段才看「日期分组」；在金额格上看必然是「不设置」）

---

## 四、其它常见配置项回显对照（检查清单）

| 设计器位置 | 配置项 | 回显字段 | 注意 |
|------------|--------|----------|------|
| 开始 · 数字格式 | 常规/货币/… | `style.formatter` + `formatterType`/`tag.formatterType` | §二 成对 |
| 单元格 · 日期分组 | 年份/年月/… | `groupType` | §三 |
| 单元格 · 显示 | 分组/列表/… | `displayType` | `Group` / `List` / … |
| 单元格 · 扩展 | 纵向/横向/不扩展 | `expandType` | |
| 单元格 · 汇总 | 求和/计数/… | `countType` | |
| 单元格 · 排序 | 升/降/无 | `orderType` | `asc`/`desc`/`no` |
| 开始 · 字体 | 字体名/字号/粗斜体/下划线 | `style.font`、`textDecoration` | §五 |
| 开始 · 颜色/填充/边框 | fore/back/border* | `style.*` | 禁止未点名整表刷 |
| 左父格筛选 | 筛选字段 | `leftFilterField` 完整 fieldKey | 见 cross-dataset 回显 |
| 查询条件 | 类型/默认值 | saveQueryItem 形态 | 见 query-condition 回显 |
| 数据集名 | 左侧列表名 | addDataset `sourceName`=`{表}(业务模块)` | 见 add-dataset |

**原则**：凡设计器有下拉/单选回显的项，必须以**平台枚举/目录全等值**写入；「看起来生效、面板不对」优先查是否写了近似值或缺了成对字段。

---

## 五、字体与字号（不支持时提示、不卡住）

1. 写入前用 CLI `validate format` / 本指南目录校验字体、字号是否在设计器支持列表内。
2. **不支持**（例：用户要 10 号但当前租户目录无 10）→ **明确提示用户**：「报表不支持 N 号字体，已按默认字号（通常 12）展示」→ **继续用默认字号落库**，禁止中断任务。
   - **禁止变通**：不要手工换算 px（如 10pt→`13.3333px`）绕过目录。后端不校验会照存，但设计器无该项、工具栏回显异常，属于假装支持。
3. 字体名优先使用设计器可选名（如 `微软雅黑`）；未知字体 → 提示并回退默认字体，同样不卡住。

---

## 六、禁止整表全量设样式 / 边框（提示话术）

用户要求「整表单元格样式 / 整表边框」时：

> **不支持**：报表不允许对**整个报表**一次性全量设置单元格样式或边框样式（易误伤未点名区域，且与「仅改用户点名项」冲突）。  
> 请给出具体区域（如 `B3:H5` 或「表头行」），我再按区域设置。

然后 **不要执行**整表 style/border patch。

---

## 七、CLI

```bash
# 校验 / 规范化数字格式与日期分组（不落库）
edc-report validate format --map "货币"
# 「转换」面板（字段转换/HTML/条码/隐藏/文字方向）→ cell-transform-guide.md
edc-report validate transform --map "人员"
edc-report validate transform --map "部门全路径"
edc-report validate transform --list
```
edc-report validate format --map "货币"
edc-report validate format --map "年份"
edc-report validate format --file cell.json

# 线上回读检查（formatterType 与 groupType）
edc-report verify format <reportId> [appId]
```

脚本：`scripts/validate_cell_config_echo.js`。

---

## 八、Agent 检查清单

- [ ] 货币等格式：formatter **全等**目录 id，且 `formatterType`/`tag` = 对应 key1（货币=`huobi`）
- [ ] 日期分组：`groupType` 为 `year`/`yearmonth`/…；workbook cellType 未丢
- [ ] 重建 workbook 使用已修补的 `fieldToCell`（透传 groupType/formatterType）
- [ ] 未点名禁止整表刷样式/边框；不支持字号已提示并默认继续
- [ ] 回读 VERIFY：目标格 `formatter`+`formatterType`、`groupType` 与需求一致
