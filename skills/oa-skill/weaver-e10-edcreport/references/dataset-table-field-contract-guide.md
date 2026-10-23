# 数据集表名与字段映射契约（强制 · 历史回归保护）

> **事故（已验证 · 报表 `1313789294296735745`）**  
> 技能包从「手工分步建表」重构为 `build spec`（spec_build 化）后，
> `scripts/build_from_spec.js` 的 `fieldCell()` 在生成 `FieldCellType` 时**丢失了 4 个必需字段**：
>
> | 丢失字段 | 正确值 | 后果 |
> |----------|--------|------|
> | `tableName` | `数据集名(业务模块)` / `数据集名(表单)` | **左侧数据源不显示「模块类型」后缀** |
> | `fieldId` | 数据集字段雪花 id | 属性面板字段回显不全 |
> | `fieldName` | 字段技术名 `field_<id>` | 同上 |
> | `fieldText` | 字段显示名 | 同上 |
>
> 实测证据（同一报表内对照组）：
> - Agent 建的 10 个 Field：`tableName=None`（异常）
> - 用户在设计器手动绑的 2 个 Field：`tableName='党员发展(业务模块)'`（正确）
> - 平台原生报表 `772466395278696448`：`tableName='轻资产处理(表单)'`，9/10 非空
> - 平台原生报表 `799097275701215232`：16/16 非空
>
> **根因不是接口、不是服务端** —— 是建表脚本写入的 `cellType` 本身就缺字段。
> 旧包 `references/data_source_rule.md` §2.2/§2.5 与 `scripts/field_bind.py` 有完整契约，
> 重构时**未迁移**，导致知识随重构丢失。
>
> **⚠️ 2026-09-11 二次实证校正（重要）**：修复该报表时，从设计器抓包解出真实 workbook，
> 对照用户手绑字段发现 —— **`fieldId` / `fieldName` / `fieldText` / `dateTimeProp` 在服务端落库的
> cellType 里同样是缺失的**（用户手绑字段也没有），它们由设计器**运行时装配**，不属落库契约。
> **真正需要落库、且能对照验证的只有 `tableName` 一项。** 上表把三件套标为「必需」属过度设计，
> 但**写上去无害**（幂等），建表脚本保留即可；**修复存量报表时只需补 `tableName`**。
>
> **⚠️⚠️ 2026-09-11 第三次实证校正（关键 · 推翻上一条因果）**：
> 上文「`tableName` 缺失 → 左侧数据源不显示模块类型后缀」的**因果链是错的**。
>
> 决定性对照（同一环境，平台原生/健康报表）：
>
> | 报表 | Field 单元格 `tableName` | 左侧面板显示 | 结论 |
> |---|---|---|---|
> | `1313798296523022337`（销售单，健康） | **全部 10 个为 `None`** | **完全正常** | `tableName` 与显示名**无关** |
> | `1313789294296735745`（党员发展，问题） | 10 个 `None` + 1 个有值 | 出现重复分组/缺后缀 | 真实原因见下 |
>
> **左侧数据源「分组显示名」的唯一权威来源** = `GET /api/bs/edc/dataset/listWithPageReport?hasField=true&reportId=`
> 返回的**源级记录**（`id` 即 **sourceId**，非 datasetId）的 `name` / `tableText`：
>
> | 状态 | `name` / `tableText` 形态 |
> |---|---|
> | 正常 | `事项清单(uf_ydsxqd_1)`、`进销存-销售单(uf_jxcxsd)`（业务模块名 + 物理表名/表单标识） |
> | 异常 | `党员发展`（纯中文名，无后缀） |
>
> **故 `tableName` 的正确落库意义**：它是**单元格级**的字段归属标记（供属性面板/导出识别「这个字段来自哪个源表」），
> **不是**左侧树的显示名来源。补它有益（属性面板回显更全），但**修不了面板显示名问题**。
>
> **面板显示名异常的真实排查路径** → 见 `dataset-sidebar-ops-guide.md` §5.3：
> ① `dataset/list` 是否挂载了重复数据集；② 遍历**全部 sheet** 找引用重复数据集的游离单元格；③ 源级 `name` 是否带后缀。
>
> **校验口径修正**：`tableName` 非空率**不能**作为「面板显示名正确」的判据；
> 应改用 `dataset/list` 去重 + `listWithPageReport.name` 含后缀 + 全 sheet 无游离 `dataSetId` 三项联合校验。

---

## 一、`FieldCellType` 必需字段全表

服务端从 `workbook.sheets.Sheet1.data.dataTable[行][列].style.cellType`
反解出 `getReportDevInfo.fields[]`。**cellType 里没有的字段，回读就是 `None`。**

| 字段 | 是否必需 | 值 | 说明 |
|------|----------|-----|------|
| `typeName` | ✅ | `FieldCellType` | 固定 |
| `cellType` | ✅ | `Field` | 固定 |
| `name` | ✅ | `field_<雪花>` | 必须逐字等于 `fieldsKey[].name` |
| `nameIndex` | ✅ | 底层 FORM sourceId | **不是字段 id** |
| `text` | ✅ | 字段显示名 | |
| `dataSetId` | ✅ | 报表内部注册 id | `dataset/list` 的 `id` |
| **`tableName`** | ○ 建议写 | **`数据集名(业务模块)`** | 单元格级字段归属标记；**非**面板显示名来源（见开头三次校正） |
| `fieldId` | ○ 建议写 | 字段雪花 id | 落库本不含；设计器运行时装配，写入幂等无害 |
| `fieldName` | ○ 建议写 | `field_<雪花>` | 同上 |
| `fieldText` | ○ 建议写 | 字段显示名 | 同上 |
| `fieldKey` | ✅ | `dataSetId.nameIndex.name` | 三段式 |

---

## 二、`tableName` 后缀由注册契约决定

`tableName` = **数据集显示名 + 后缀**，后缀取决于 `addDataset` 的注册类型：

| 注册形态 | `sourceType` / `sourceGroup` | 后缀 | 适用 |
|----------|------------------------------|------|------|
| **A（默认）** | `LOGIC` + `weaver-ebuilder-form-service` | **`(业务模块)`** | 普通应用表单 |
| **B（共享表）** | `form` + `<appId>` | **`(表单)`** | `xxx-共享表` 类应用 |
| **C（数据加工 SQL 视图）** | `ETEAMS` + `sql` | **无后缀**（= `datasetName` 原样） | 数据集来自「数据加工」SQL 视图 |

> **形态 C 实测（2026-09-14 · 报表 `1314970921403138199`）**：数据集「考勤汇总报表(优化)」
> （`sourceType=ETEAMS` / `sourceGroup=sql`）→ 设计器手绑单元格 `tableName` = **`考勤汇总报表(优化)`**，
> 且 `dataset/fieldsAndOriginFields.fieldsKey[].datasetName` / `tableText` 也都是这个裸名。
> **判断口径（三条一致即可定值）**：① 设计器里已有手绑单元格 → 用它的 `tableName`；
> ② 否则用 `fieldsKey[].datasetName`；③ 都没有才按 `dataset/list[].name`。

> 与 `add-dataset-registration-guide.md` §一 的两种注册形态一一对应。
> **禁止**给共享表硬套 `(业务模块)` —— 后缀必须与注册形态一致。

**取值优先级**（服务端常不回传，必须脚本兜底）：

1. `fieldsKey[].tableName`（服务端有则用）
2. `fieldsKey[].datasetName`
3. `datasetLabel + datasetSuffix(sourceType)` ← **兜底，保证恒非空**

`datasetLabel` 来自 `dataset/list` 的 `name`（即 `addDataset` 的 `sourceName`），
由 `spec_lib.resolveDataset()` 回传、`fieldsKeyOf()` 注入到每个字段。

---

## 三、字段三件套取值来源

| 字段 | 来源 |
|------|------|
| `fieldId` | `fieldsKey[].config.fieldId`（**首选**）→ `fieldsKey[].fieldId` |
| `fieldName` | `fieldsKey[].name` |
| `fieldText` | `fieldsKey[].text`（→ `showName` → 列标题） |

`fieldsKey[]` 实测可用键（`fieldsAndOriginFields?isFront=true`）：

```
name / text / originName / fieldType / formatType
dataSetId / nameIndex / tableId / tableText / datasetName
config{ fieldId, formId, sformId, formName, componentKey, ... }
```

### 三点五、两接口返回格式对照（**以 `fieldsAndOriginFields` 为准** · 2026-09-11 实测）

同一表单 `sourceId=753880319550169088` 双接口 30/30 逐条比对：

| 接口 | 信封（顶层） | 字段元素 | `dataSetId` |
|------|--------------|----------|-------------|
| `GET /dataset/fieldsBySource?sourceId=&sourceType=logic&groupId=` | `data` = **裸数组** `[{…}]` | 18 键 | **恒 `"0"`**（未落库） |
| `GET /dataset/fieldsAndOriginFields?datasetId=&hasField=true&isFront=true&reportId=` | `data` = **对象** `{ fieldsKey:[…], originFieldsKey:[…] }` | 18 键 | **真实 datasetId** |

逐键差异统计：**仅 `dataSetId` 30/30 不同**；其余 17 键
（`name` / `text` / `originName` / `fieldType` / `originFieldType` / `usage` / `config` /
`formatType` / `showOrder` / `tableId` / `tableText` / `nameIndex` / `datasetName` /
`originField` / `dsSelectField` / `dsBrowserField` / `deleteType`）**完全一致**。

**统一归一化入口**：`spec_lib.normalizeFieldList(payload, { datasetId })`

```javascript
const { fields } = normalizeFieldList(res, { datasetId });   // 冒号：任一接口 → 字段元素数组
```

- 抹平「裸数组 / `{fieldsKey}` 对象 / `{fields}` 对象」三种信封 → 一律返回**字段元素数组**；
- `datasetId` 传入时**覆盖** `dataSetId`（`fieldsBySource` 恒为 `0`，**直接落库会绑错数据集**）；
- 返回 `{ fields, originFields, shape, dataSetIdInjected }`，`shape ∈ bare-array | fieldsKey-object | fields-array | empty`。

> **禁止**把 `fieldsBySource` 的原始 `data`（裸数组）当成 `{fieldsKey}` 取 —— `data.fieldsKey` 会是 `undefined`。
> **禁止**把 `fieldsBySource` 元素原样写入 `cellType.dataSetId` —— 必须换成**本报表真实 datasetId**。
> 另：语义上的「返回 data」= 接口的 `json.data`；`json.code === 200` 表示成功。

---

## 四、落库后强制门禁

`build spec` 已在 `getReportDevInfo` 回读阶段自动校验：

```javascript
const fieldCells = fields.filter((f) => f.cellType === 'Field');
const missingTableName = fieldCells.filter((f) => !f.tableName);
if (missingTableName.length) {
  console.error(`WARN ${missingTableName.length}/${fieldCells.length} 个 Field 单元格缺 tableName`);
  process.exitCode = 2;   // 非零退出，提示需修正
}
```

输出 JSON 附带：`tableName`（首格值）、`tableNameMissing`（缺失数）。

| 检查 | 通过标准 |
|------|----------|
| `tableName` 非空率 | **100%**（`tableNameMissing == 0`） |
| 后缀与注册形态一致 | LOGIC→`(业务模块)`；form→`(表单)` |
| `fieldId` / `fieldName` / `fieldText` 齐全 | 非空 |
| `name` ∈ fieldsKey | 见 `field-bind-exact-match-guide.md` |

---

## 四点五、修复存量报表（tableName 缺失）— 最小侵入路径 ✅ 已验证

> **场景**：报表已落库，但 `tableName` 缺失（旧脚本产物）。
> **报表 `1313789294296735745` 实测修复成功（HTTP 200 + 双向验证通过）。**

**关键接口认知（务必先读）**

| 接口 | 提交物 | 易错点 |
|------|--------|--------|
| `saveReportDevInfo` | **`workbook`**（gzip + base64） | ❌ 用 `fields=<json>` 提交 → **400 Bad Request** |
| `getReportDevInfo` | 返回 `fields[]` | ⚠️ 只有 `cellType: "Field"/"Const"` **类型标记**，**不含字段绑定明细**；明细只在 workbook 里 |

**`saveReportDevInfo` 完整表单（7 字段，multipart）**

```
groupId / appId / reportId / name / nameLabelId / designKey / workbook
```
- `designKey` 是**乐观锁**，必须取线上当前值（`getReportDevInfo.data.designKey`），否则拒写
- `workbook` = `base64(gzip(json.dumps(workbook), mtime=0))`

**获取「当前真实 workbook」（唯一可靠来源）**

线上 `getReportDevInfo` **拿不到** `dataTable`（其 `workbookProps.sheets` 为空 `{}`）。正确做法：

1. CDP 打开设计器：`https://{host}/sp/edc/report/designer/{reportId}`
2. 派发 **Ctrl+S**（`Input.dispatchKeyEvent`，`modifiers:2`, `key:"s"`）触发一次保存
3. 从 `Network.requestWillBeSent` 抓 `saveReportDevInfo` 的 `postData`
4. 按 `name="workbook"\n\n(.*?)\n-{2,}`（**换行是 `\n`，不是 `\r\n`**）提取 → `gzip.decompress(base64.b64decode(...))`

**修复步骤**

```python
wb = json.loads(解码后的workbook)
dt = wb["sheets"]["Sheet1"]["data"]["dataTable"]      # {row: {col: {"style": {...}, "tag": {...}}}}
for r in dt:
    for c in dt[r]:
        ct = (dt[r][c].get("style") or {}).get("cellType") or {}
        if ct.get("cellType") != "Field": continue
        if str(ct.get("dataSetId")) == DS_OLD and not ct.get("tableName"):
            newct = {}
            for k, v in ct.items():                   # 保持键顺序：插在 dataSetId 之后
                newct[k] = v
                if k == "dataSetId": newct["tableName"] = "党员发展(业务模块)"
            dt[r][c]["style"]["cellType"] = newct
# 重新编码并提交 saveReportDevInfo
```

**验证（双向）**

| 检查 | 通过标准 |
|------|----------|
| `getReportDevInfo` 回读 | `fields[]` 中带 `tableName` 的数量 = Field 总数 |
| 设计器实时 workbook | dataTable 内 `Field` 单元格 `tableName` 缺失数 = 0 |

> 实测结果：12/12 带 tableName ✅；设计器实时 workbook 11/11 Field 全齐、0 缺失 ✅

---

## 四点六、修复存量报表（tableName 缺失）— **免浏览器反向重建** ✅ 已验证（首选）

> **场景**：整张报表的 Field 单元格 `tableName` 全为空 → 设计器里单元格/属性面板不回显数据集名；
> 但**孤例**（某个手绑单元格）是对的。用户会说「参考 XX 单元格的规则才对，调整其他字段」。
>
> **报表 `1314970921403138199` 实测成功（2026-09-14）**：
> 48 个 Field 中 47 个 `tableName=""`，唯 `AM5`（row4,col38）为 `考勤汇总报表(优化)` → 一键补齐。

### 为什么优先走这条路（而不是 §四点五 的 CDP 抓包）

`getReportDevInfo` 的 `workbookProps.sheets` **恒为 `{}`**，拿不到 `dataTable`；
但它的 **`fields[]` 是服务端对 workbook 的逐单元格回读**，字段足够重建：
`x/y`、`xCount/yCount`（合并跨度）、`leftX/leftY/topX/topY`（父子格）、`expandType/displayType`、
`countType`、`style`（整份 style JSON 串）、`name/text/nameIndex/dataSetId/fieldKey/tableName`、`width/height`。
**→ 不需要浏览器、不需要按键抓包**。§四点五 的 CDP 路径仅作兜底。

### 重建规则（照抄即可）

```
dataTable[x][y] = { style: { ...JSON.parse(fields[].style), cellType }, tag: { fixed:false, formatterType:['common'] } }
spans      = 每个 xCount>1 || yCount>1 的单元格 → { row:x, col:y, rowCount:xCount, colCount:yCount }
columns[c] = fields[].width（该列任一单元格）;  rows[r] = fields[].height
sheet.tag  = sheetProps[0] 的 childMerge / showLocation / filterSheet / tableNameSuffix
             + JSON.parse(columnConfig) + JSON.parse(sheetConfig)
workbook   = { version, __scrollbarShowMax, __excelSheet, workbookConfig:{}, sheets }
cellType 键序 = 设计器真实键序（见 §一，逐字照排）
```

### ⚠️ 四个坑（踩过，必须照做，否则 `{"code":500,"msg":"报表内部错误"}`）

| # | 坑 | 正确做法 |
|---|----|----------|
| 1 | **`fields[]` 不回传 `typeName`/`allowOverflow`/`editorType`/`groupType`/`isActiveParent`/`arrowType`**，但服务端保存**必须要 `typeName`** | 这 6 个键由脚本**强制兜底**：`typeName='FieldCellType'/'ConstCellType'`、`allowOverflow=true`、`editorType=1`、`groupType=null`；`arrowType` 由 `expandType` 派生（Vertical/Horizontal/None）；`isActiveParent` = Field 且 `leftX=-1 && topX=-1 && expandType∈{Vertical,Horizontal}` |
| 2 | `dateTimeProps` / `highlightDatas` / `allNeedFields` / `fillDtIndex` / `fillShow` / `fillAddLine` / `fillDelLine` / `fillMergeShow` / `fillSelectId` / `fillTextLength` 是**服务端保存时自行派生**的，设计器保存的 workbook 里**没有** | **排除，不得回写**（回写即 500） |
| 3 | `cellType.formatterType` 设计器保存值是 **`[]`**（不是 `['common']`；`['common']` 在 `tag.formatterType`） | 强制 `formatterType: []` |
| 4 | `designKey` **每次 GET 都返回新值**（即时令牌，不是静态乐观锁）→ 读后隔久了再存会失败 | 读取 `designKey` 与 `saveReportDevInfo` 必须**紧邻** |

两个次要坑：
- `fields[].width/height` **可能合法为 0**（Excel 隐藏列，如「人员ID」）→ 不能用 `Number(w) || 40` 兜底，会把 0 吞成 40。
- 合并区覆盖但**无单元格**的列（日期块被合并掉的第 2/3 列）在 `fields[]` 里不存在 → 沿用左侧最近已知列宽，避免列宽塌成默认值。

> ⚠️ **与 `safe_report_save.js` 的一处分歧**：该脚本的 `stripWorkbookGridlineKeys()` 会删掉
> `gridline` / `__gridline`，注释称「存在即 500」。**在本环境（itsm.hongjing-wh.com:5001）实测不成立**：
> 带 `__gridline: 0` 的 workbook 保存返回 200（报表 `1314970921403138199` 连续两次）。
> 该断言可能只对某站点成立 —— 保留删除动作更安全，但**不要据此判定其他 500 的成因**。

### 合并单元格的副作用（重要）

提交含合并区全部单元格的 workbook 时，**服务端/设计器会丢掉被合并覆盖的单元格，只留左上角**。
例：日期带 `(0,45)(0,46)(0,47)` 三格 + span → 回读只剩 `(0,45)`。
**→ 重建时不要凭空补这些格子**；`fields[]` 里没有就是不该有。

### 现成脚本

```bash
# 默认 dry-run（打印计划 + 保真自检，不落库）
node scripts/fix_table_name_echo.js --report-id <rid> [--app-id <aid>] \
     [--table-name "<数据集名>"] [--restore-from <备份workbook.json>]
# 确认后落库
node scripts/fix_table_name_echo.js --report-id <rid> --apply
```
- 自动定值：`--table-name` > `fieldsKey[].datasetName` > `dataset/list[].name`
- `--restore-from`：把备份 workbook 中「线上已不存在」的单元格补回（例如被误删的手绑单元格）
- 内置门禁：重建保真度不一致即拒绝保存；保存后快照 diff 非 `tableName` 有差异则退出码 2
- 保存**必须** `--apply`（整份替换，防误覆盖）

### 验收口径（保存前后 fields[] 快照 diff）

```
保存前 fields = A（含孤例），保存后 fields = B
diff(A,B) 期望：仅 `tableName` 变化（条数 = 缺失数）+ 可选 `(新增)`（补回的手绑单元格）
            其余键（cellType/name/dataSetId/父子格/expandType/displayType/style…）必须 0 差异
```

再跑 `edc-report verify all <rid> <appId>`（`ok:true, errors:[]`）+ 渲染回读
（`view/analysis` → `getJsonStr` → gunzip：`rowCount`/表头纵向合并条数/数据行非空数）确认版面未坏。

> ⚠️ **重建会覆盖服务端现状**：`saveReportDevInfo` 是**整份替换**。
> 若线上存在「`fields[]` 也看不到」的内容（未知键），重建会丢。故保存前**先把重建出的
> 『原样 workbook』落一份备份**（本脚本 `--restore-from` 亦依赖它补回被误删的手绑单元格）。


---

- ❌ 只在 `fields[]` 回读层「补」tableName —— 必须写入 workbook 的 `cellType`，服务端才会落库
- ❌ **照抄 `fields[]` 的键集重建 cellType** —— `typeName` 等 6 个键服务端不回传，漏了必 500（见 §四点六 坑 1）
- ❌ **把服务端派生键回写 cellType**（`dateTimeProps`/`highlightDatas`/`allNeedFields`/`fill*`）—— 必 500（坑 2）
- ❌ 给共享表（form 契约）写 `(业务模块)` 后缀；给 SQL 视图（ETEAMS/sql）硬加后缀（形态 C 无后缀）
- ❌ 用 `saveReportDevInfo` 的 `fields[]` 数组下发字段 —— 服务端**只认 workbook**
- ❌ 重构时把本契约从 references 删除（本事故成因）

---

## 六、相关文档

| 文档 | 关系 |
|------|------|
| `add-dataset-registration-guide.md` | 两种注册形态（决定后缀） |
| `field-bind-exact-match-guide.md` | `name` 逐字匹配 fieldsKey |
| `spec-build-schema.md` | `build spec` 声明式用法 |
| `query-condition-api-guide.md` §2.1.2 | `browserType` 富对象（关联浏览分类元数据接口） |
| 旧包 `data_source_rule.md` §2.2/§2.5 | 本契约原始出处（已迁回本文件） |
