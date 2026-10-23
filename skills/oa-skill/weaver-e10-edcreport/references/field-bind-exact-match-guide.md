# 字段精确绑定（强制 · 禁止匹配失败）

> **事故案例（已验证）**：报表 `AAA`（`1312677851392417792`）保存了 9 个 Field 格，但 `name` / `fieldKey` 末段写成裸雪花 ID `3506271516100878845`，而数据源真实字段名是 `field_3506271516100878845` → **设计器有字段格、取数全部匹配失败（字段获取不上）**。  
> **前置事故（已验证 · `1312765120721813505`）**：Agent 用错 `addDataset`（`type=form` + `sourceGroup=appId`）时，`fieldsKey` **本身只有裸雪花**；用户在设计器手动「+」同表则得到 `field_*`。  
> **遗漏点**：不是写 Field 时忘加前缀，而是 **注册契约与设计器不一致** —— 必先读 **`add-dataset-registration-guide.md`**，把数据集加成 LOGIC + `weaver-ebuilder-form-service`，再绑定。  
> **唯一标准**：`name` / `fieldKey` 末段必须 **精确等于** 当前数据集 `fieldsAndOriginFields.fieldsKey[].name`（以接口回读为准）。  
> **禁止**：注册错了却在 cell 上「手工补 `field_`」；或对正确的 `field_*` fieldsKey 去前缀。  
> **硬目标**：任意 Field 的 `name` **必须**等于该 dataset 的 `fieldsKey[].name`；**零容忍**猜测、截断、错数据集。

---

## 〇、先保证 fieldsKey 带 `field_`（普通应用）

| 检查 | 说明 |
|------|------|
| addDataset | 默认 `sourceType=LOGIC` + `sourceGroup=weaver-ebuilder-form-service` |
| 门禁 | 业务字段若多为裸雪花 → **注册错误**，`delDataset` 重建；见 `add-dataset-registration-guide.md` |
| 同 sourceId 多实例 | **优先绑**设计器/LOGIC 那条（`field_*`），勿绑旧 form+appId 实例 |

---

## 一、唯一合法字段名来源

```
GET /api/bs/edc/dataset/fieldsAndOriginFields
  ?datasetId={datasetId}&hasField=true&isFront=true&reportId={reportId}
→ data.fieldsKey[]     // 权威列表；isFront=false 常为空，禁止依赖
```

每个 `fieldsKey` 项的关键属性：

| 属性 | 用途 | 示例 |
|------|------|------|
| **`name`** | **写入 Field 的 `name` / fieldKey 末段（唯一正确）** | `field_3506271516100878845`、`create_time` |
| `text` / `showName` | 仅用于按中文显示名**查找**对应 `name` | `资产类别` |
| `originName` | 参考，不可直接当 fieldKey 末段（除非与 `name` 相同） | — |

**禁止**从下列来源臆造 `name`：

| 错误来源 | 错误示例 | 后果 |
|----------|----------|------|
| 表单字段 ID / 雪花 ID（无 `field_`） | `3506271516100878845` | **取数匹配失败**（本案） |
| 显示名 | `资产类别` | 设计器/取数均失败 |
| 截断 / 半截 | `field_5`、`field_3506` | 匹配失败 |
| 去掉 `field_` 前缀 | 把 `field_xxx` 写成 `xxx` | **取数匹配失败** |
| 外部字段表 fieldId 未与 fieldsKey 交叉核对 | 形态可能不同 | 须与 fieldsKey.name 对齐后再用 |

---

## 二、绑定算法（强制）

> **⚠️ 2026-09-11 追加门禁（事故：报表 `1313789294296735745`）**：B3 列文案「姓名」，但该表单**没有「姓名」字段**，
> 旧逻辑静默兜底到系统字段 `name`（真实显示名「标题」）→ 单元格文案与绑定字段语义不符、属性面板回显对不上。
> **新规则：精确匹配失败必须 `exit 4` 提示用户指定字段，禁止任何自动兜底（尤其禁止回退系统字段）。**
> 落地实现：`spec_lib.resolveFieldBindings()` + `edc-report build spec` 的**建表前预检**。

对需求中的每一列（显示名 → 数据字段）：

### 2.0 允许的匹配（命中即止，**全为精确匹配**）

| 顺序 | 依据 | 说明 |
|------|------|------|
| 1 | `column.fieldName` / `spec.fieldMap[列标题]` | 用户/Agent 显式指定（可为 `field_xxx`、显示名、系统字段名） |
| 2 | 列标题 === `fieldsKey[].text/showName`（归一化：去空白、全角括号→半角） | 主路径 |
| 3 | `column.field` === `text/showName` 或 `name` | 兼容旧 spec |
| 4 | 都不中 | **`unmatched` → exit 4**（附模糊候选供用户挑选） |

**禁止**：包含/被包含（`includes`）等模糊规则自动绑定；**禁止**把 `name`/`id`/`create_time` 等系统字段当作兜底。

### 2.0.1 规则 A · 找不到字段 → **停下让用户指定**（强制 · 2026-09-11）

> **核心**：需求里的字段在当前数据集表单里**找不到**时，**不许猜、不许兜底**，必须停下把候选交给用户。

`resolveFieldBindings()` 的 `unmatched[]` 三种 `reason` 及处置：

| `reason` | 含义 | 退出码 | 处置 |
|----------|------|--------|------|
| `no_exact_match` | 列标题在 `fieldsKey.text` 中**无精确命中** | **4** | 把 `candidates` + `allFields` 抛给用户，请其指定字段 |
| `explicit_not_found` | 显式 `fieldName`/`fieldMap` 指向的字段**不存在** | **4** | 同上（禁止臆造字段名） |
| `display_mismatch` | 能绑到，但字段**真实显示名 ≠ 列文案**且未确认 | **4** | 用户确认列名有意如此 → `fieldConfirmed` / `--field-confirmed "列标题"` |

**两阶段拦截**（都不建表 / 删未完成表）：

| 阶段 | 时机 | 未通过 |
|------|------|--------|
| 预检 | `fieldsBySource`（**建表前**） | **exit 4 · 未创建任何报表** |
| 复校 | 本表 `addDataset` → `fieldsKey`（落库前） | **exit 4 · 删除本轮未完成报表** |

输出结构（`rule:"A"`）：

```json
{
  "action": "confirm_field", "rule": "A", "needConfirm": true, "reportCreated": false,
  "unmatched": [ { "column": "姓名", "reason": "no_exact_match", "prompt": "…请用户从 allFields/candidates 中指定字段",
                   "candidates": [ { "name": "field_...", "text": "发展人", "system": false } ] } ],
  "allFields": [ { "name": "field_...", "text": "发展人", "system": false } ],
  "next": { "specFields": { "fieldMap": { "<列标题>": "<字段显示名 | field_雪花 | 系统字段名>" } } }
}
```

用户指定后复跑：`spec.fieldMap = { "姓名": "发展人" }`（或 `field_xxx`）。
若列名坚持与字段显示名不同 → 另加 `fieldConfirmed: ["姓名"]` / CLI `--field-confirmed "姓名"`。

**禁止**：
- 用「最相近的」字段顶上（哪怕语义看似接近）；
- 回退系统字段（`name`→「标题」是历史事故）；
- 先带病落库、事后再让用户改。

> 一页速览：`edc-report policy ask`。

```javascript
// 1. 拉权威列表
const fieldsKey = (await fieldsAndOriginFields(...)).data.fieldsKey;

// 2. 解析（库函数，已含门禁）
const plan = resolveFieldBindings(fieldsKey, spec.columns, { fieldMap, fieldConfirmed });
if (!plan.ok) {
  // exit 4：把每列 candidates 抛给用户，等其指定字段；不要自己猜
}
const nf = plan.bindings.find(b => b.index === colIndex).field;
```

**规则摘要**：

1. **先** `fieldsAndOriginFields`，**再**写任何 Field 单元格  
2. `name` **逐字等于** `fieldsKey[].name`（含 `field_` 前缀；系统字段如 `create_time` 原样）  
3. `fieldKey` = `{datasetId}.{sourceId}.{fieldsKey.name}`，三段齐全  
4. 保存前对**每一个** Field 做 `byName.has(name)`；任一失败 → **中止保存**，禁止带病落库  

---

## 三、保存后强制回读校验（交付门禁）

`getReportDevInfo` 后，对每个 `cellType === 'Field'`：

```javascript
function assertFieldBindExact(devFields, fieldsKey) {
  const legal = new Set(fieldsKey.map(f => f.name));
  const fieldCells = devFields.filter(f => f.cellType === 'Field');
  if (!fieldCells.length) throw new Error('无 Field 单元格');
  for (const f of fieldCells) {
    const last = String(f.fieldKey || '').split('.')[2] || '';
    if (!f.name || !legal.has(f.name)) {
      throw new Error(`字段匹配失败 name=${f.name} text=${f.text}`);
    }
    if (last !== f.name || !legal.has(last)) {
      throw new Error(`fieldKey 末段不在 fieldsKey: ${f.fieldKey}`);
    }
    // 裸雪花：若 fieldsKey 里已有 field_xxx，则禁止用裸名；否则先查 addDataset 是否注册错
  }
}
```

| 检查 | 失败即 FAIL |
|------|-------------|
| 每个 Field 的 `name ∈ fieldsKey.name` | ✅ |
| `fieldKey` 末段 === `name` | ✅ |
| 普通应用：fieldsKey 业务字段含 `field_*`（注册门禁） | ✅ 见 `add-dataset-registration-guide.md` |
| Field 数量 ≥ 需求列数 | ✅ |
| **单元格文案 === 绑定字段真实显示名**（否则须用户确认） | ⚠ `verify bind` 列出 `display_mismatch` |
| **同 sourceId 只挂 1 个数据集**（否则左侧重复分组） | ⚠ `verify bind` 列出 `duplicate_dataset_mount` |

`edc-report verify bind <reportId> [appId] [--strict]`：门禁失败 exit 1；`--strict` 时「待用户确认项」exit 2。

**未通过校验 → 须修正并告知用户**；可与「已交付的设计器链接」并行：先给链接（见 `report-delivery-contract.md` §〇），校验失败再补丁修复，**禁止**为等校验而拖延首轮地址。

---

## 四、故障对照

| 现象 | 根因 | 处理 |
|------|------|------|
| 设计器有 Field 格，预览/取数无数据或字段空白 | `name` 为裸 ID，缺 `field_` | 按 fieldsKey.name 重绑并 saveReportDevInfo |
| **手动加的数据集有 `field_`，API 加的没有** | **addDataset 用了 form+appId，不是设计器 LOGIC** | 按 `add-dataset-registration-guide.md` del 后重建 |
| **单元格表头文案 ≠ 属性面板字段名**（如「姓名」实为「标题」） | 旧逻辑把无匹配列**兜底到系统字段** | 改为 `exit 4` 让用户指定；存量报表用 `fieldMap`/重绑修复 |
| **左侧出现重复数据源分组** | 同 sourceId 被重复 `addDataset` 挂载 + 画布游离单元格引用 | 先改绑/清单元格再 `delDataset`；见 `dataset-sidebar-ops-guide.md §5.3` |
| `matchByName=false`（自检） | 同上 / 用了显示名 | 强制走 §二 resolve |
| 部分列有数据部分没有 | 个别列 name 写错 | 逐列对照 fieldsKey |
| fieldsKey 为空 | 未传 `isFront=true` 或 datasetId 错 | 修正后再绑定，禁止用空列表继续 |

---

## 五、与现有文档关系

| 文档 | 关系 |
|------|------|
| **`add-dataset-registration-guide.md`** | **addDataset 与设计器对齐；fieldsKey 无 `field_` 的根因** |
| `api-report-build-fast-path.md` | 建表流程 §三/§五 引用本节；保存门禁 |
| `cross-dataset-filter-guide.md` | leftFilter 的 fieldKey 末段同样必须是 fieldsKey.name |
| `scripts/verify_field_bind.js` | 保存后一键校验（必跑） |
| `scripts/validate_report_config.py` | 离线 JSON 形态检查；**线上以本节 + verify_field_bind 为准** |

---

## 六、Agent 执行清单（复制即用）

- [ ] `sourceName` 为 `{表单名}(业务模块)`（回显名），不是裸表单名（`build spec` 已自动补后缀）
- [ ] 本报表**已有同 sourceId 数据集 → 复用**，不重复 `addDataset`
- [ ] `addDataset` 为 `LOGIC` + `weaver-ebuilder-form-service`（非共享表特例）
- [ ] `fieldsKey` 业务字段已含 `field_*`（否则先修注册）
- [ ] `fieldsAndOriginFields?isFront=true` 已拿到非空 `fieldsKey`
- [ ] 每个需求列：`显示名 → fieldsKey.name` 映射表已打印确认（`build spec` 输出 `fieldBindings`）
- [ ] **任一无精确命中 → exit 4 时，把 `candidates`/`allFields` 交给用户指定字段，禁止自行猜**
- [ ] 同 sourceId 多实例时绑的是 LOGIC/`field_*` 那条
- [ ] `name` ∈ 当前 dataset 的 fieldsKey（勿臆造 / 勿手工补 `field_`）
- [ ] 保存前 `assert` 全部通过
- [ ] 保存后 `verify_field_bind.js` / 等价断言全部通过
- [ ] 未通过则**不交付**
