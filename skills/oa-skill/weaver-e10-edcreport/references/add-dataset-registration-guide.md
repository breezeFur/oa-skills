# addDataset 注册契约 · `field_` 前缀门禁（强制）

> **事故（已验证 · 报表 `1312765120721813505`）**  
> 同一 `sourceId=972019393600233477`（轻资产信息）：  
> - **Agent/API 加的数据集** `1312765120721813506`：`type=form` + `sourceGroup=<appId>` → `fieldsKey.name` 业务字段为**裸雪花**（无 `field_`）  
> - **设计器手动「+」加的数据集** `1312794545670627330`：`type=logic` + `sourceGroup=weaver-ebuilder-form-service` → `fieldsKey.name` 业务字段为 **`field_{雪花}`**  
>
> **遗漏点不在「写 Field 时忘加 field_」**，而在 **`addDataset` 注册参数与设计器不一致**，导致权威 `fieldsKey` 本身就没有 `field_`。  
> 后续若按设计器习惯臆造 `field_`，或绑错到「裸雪花」那份 dataset，会出现保存 500 / 取数失败 / 与用户手动数据集字段名对不齐。

---

## 一、两种注册形态（必须分清）

| 形态 | 典型 `addDataset` | `dataset/list` 特征 | 业务字段 `fieldsKey.name` | `tableName` 后缀 | 何时用 |
|------|-------------------|---------------------|---------------------------|------------------|--------|
| **A. 设计器默认（LOGIC）** | `sourceType=LOGIC`（或 `logic`）+ `sourceGroup=weaver-ebuilder-form-service` + `appid=<appId>` | `type:"logic"`，`sourceGroup:"weaver-ebuilder-form-service"` | **`field_{雪花}`** | **`(业务模块)`** | **普通应用表单（默认强制）** |
| **B. 共享表 / form 契约** | `sourceType=form` + `sourceGroup=<appId>` | `type:"form"`，`sourceGroup` 等于 appId | 常为**裸雪花** | **`(表单)`** | 仅「xxx-共享表」类应用且已验证必须用此契约时（见 MEMORY/共享表笔记） |

**禁止**：在普通应用里误用形态 B，再抱怨「没有 field_」——那是注册错了，不是 fieldsKey 坏了。

> ⚠️ **`tableName` 后缀必须与注册形态一致**：形态 A → `(业务模块)`，形态 B → `(表单)`。
> 后缀缺失或写错会导致左侧数据源不显示模块类型。
> 详见 **`dataset-table-field-contract-guide.md`**（含 `FieldCellType` 必需字段全表 + 落库门禁）。

---

## 二、设计器兼容的 addDataset（默认强制）

```
POST /api/bs/edc/report/addDataset
Content-Type: multipart/form-data

reportId     = {reportId}
sourceType   = LOGIC
sourceIds    = {sourceId}          // 表单/数据源 ID
sourceName   = {显示名}             // **回显名强制**：`{表单名}(业务模块)`，如 `轻资产信息(业务模块)`；禁止只传裸表单名
appid        = {appId}             // 注意小写 appid（与设计器一致）
sourceGroup  = weaver-ebuilder-form-service
```
> **回显名（已验证）**：`sourceName` 写入 `edc_dataset_dev.name`，左侧回显应为 **`xxx(业务模块)`**。  
> 只传 `轻资产信息` 会缺后缀；源合并后的 `tableText` 可能仍是 `轻资产信息(uf_xxx)`，与回显名不是同一字段——**以 `name`=sourceName 为准**。

可选字段以设计器抓包为准；**不得**把 `sourceGroup` 写成 appId，除非走 §一 形态 B。

`addDataset` **不返回** datasetId → 短轮询：

```
GET /api/bs/edc/dataset/list?hasField=true&reportId={reportId}
```

按 **sourceId** 命中；若同 sourceId 多条，**优先选** `sourceGroup=weaver-ebuilder-form-service` / `type=logic` 那条。

### 2.1 同源只挂一次（**强制 · 2026-09-11 事故**）

`spec_lib.resolveDataset()` 在 `addDataset` **之前**先查 `dataset/list`：

| 场景 | 行为 |
|------|------|
| 本报表已有同 `sourceId` 数据集 | **复用**（`datasetReused=true`），**不再 addDataset** |
| 发现同源 ≥2 条 | 回传 `datasetDuplicates[]` + WARN（左侧会出现重复分组） |
| 传了别的报表的 `datasetId` | 忽略 + WARN（禁止跨报表复用） |

> 事故：同一表单被 `addDataset` 挂载两次（`type=LOGIC` 与 `type=logic` 各一条），
> 且画布上两个单元格引用第二条 → 设计器左侧出现**两个同名数据源分组**。
> 未先去重就继续绑字段，会让「绑到哪一份数据源」变得不可预测。
> 清理顺序见 `dataset-sidebar-ops-guide.md §5.3`（**先改绑/清单元格 → 再 delDataset**）。

---

## 三、addDataset 后强制门禁（遗漏即本事故）

`fieldsAndOriginFields?isFront=true` 拿到 `fieldsKey` 后立刻检查：

```javascript
const biz = fieldsKey.filter(
  (f) => /^\d{15,}$/.test(f.name) || /^field_\d{15,}$/.test(f.name)
);
const withPrefix = biz.filter((f) => String(f.name).startsWith('field_')).length;
const bare = biz.filter((f) => /^\d{15,}$/.test(f.name)).length;

// 普通应用（非共享表 form 契约）：业务字段应多数带 field_
if (!isSharedFormContract && biz.length > 0 && bare > withPrefix) {
  throw new Error(
    'addDataset 注册错误：fieldsKey 业务字段为裸雪花（无 field_）。' +
      '应使用 sourceType=LOGIC + sourceGroup=weaver-ebuilder-form-service；' +
      'delDataset 后重建，禁止在 Field 上凭记忆加 field_ 前缀凑数。'
  );
}
```

| 检查 | 通过标准 |
|------|----------|
| 普通应用 | 业务字段 `field_` 数量 **≥** 裸雪花数量（通常裸雪花应为 0） |
| 共享表 form 契约 | 允许裸雪花；**禁止**再擅自加 `field_` |
| 同 sourceId 已有手动 LOGIC 数据集 | **绑定/取 fieldsKey 必须用那条**；勿继续用旧的 form+appId 脏注册 |

失败处理：

1. `POST /api/bs/edc/report/delDataset` 删掉错误注册  
   - form：`reportId=<报表ID>` · **`sourceIds=<datasetId>`**（参数名历史遗留，**不是**表单 sourceId）  
   - 建议先 `GET /api/bs/edc/dataset/checkDataSetUsed?reportId=&datasetId=`；CLI：`edc-report dataset delete`  
   - 完整侧栏操作见 `dataset-sidebar-ops-guide.md`  
2. 按 §二 重新 `addDataset`  
3. 再拉 `fieldsKey`，确认出现 `field_*`  
4. 再写 Field / `saveReportDevInfo`

---

## 四、与「字段精确绑定」的关系

| 步骤 | 规则 |
|------|------|
| 1 注册 | 本指南：让 `fieldsKey` **先**变成设计器同款（含 `field_`） |
| 2 绑定 | `field-bind-exact-match-guide.md`：`name` **逐字等于** 当前 dataset 的 `fieldsKey.name` |
| 3 禁止 | 注册错了却在 cell 上「手工补 `field_`」；或注册对了却去前缀 |

**一句话**：`field_` 不是 Agent 写 Field 时发明的，是 **正确 addDataset 之后 fieldsKey 自带的**。

---

## 五、自检清单

- [ ] `addDataset` 使用 `sourceType=LOGIC` + `sourceGroup=weaver-ebuilder-form-service`（除非共享表契约）
- [ ] `dataset/list` 回读该条 `type/sourceGroup` 与设计器一致
- [ ] `fieldsKey` 业务字段已出现 `field_*`（普通应用）
- [ ] Field.`name` / fieldKey 末段 ∈ **该** dataset 的 fieldsKey（`verify_field_bind.js`）
- [ ] 同 sourceId 多实例时，未误绑到旧的 form+appId 裸雪花数据集

---

## 六、相关文档

| 文档 | 关系 |
|------|------|
| `field-bind-exact-match-guide.md` | 绑定名权威来源；前置依赖本指南的注册正确 |
| `api-report-build-fast-path.md` | 建表流程步骤 2 / 2.1 门禁 |
| `report-designer-feature-map.md` §六 | 设计器「+」对应 addDataset 参数 |
| `scripts/verify_field_bind.js` | 交付校验；并对「裸雪花 fieldsKey」给出注册错误提示 |
