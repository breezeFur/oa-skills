# API 从零搭建报表 · 快速路径（强制）

> **适用**：用户要求「在 XX 应用下搭建报表」「根据需求文档/Excel 建表」，且走 API/脚本落库。  
> **目标**：**一次跑通**，禁止反复试探性 API、禁止二分调试脚本、禁止无用户许可的 copySheet。  
> **优先级**：与本节冲突的旧文档表述（如「先 cache 后 dev」针对**新空报表**）以本节为准。  
> **模式选型**：列表页「新建报表」三卡片见 **`report-create-modes-guide.md`**（模版创建 / 快速构建-列表式用 `edc-report create`）。**本节默认 = 从空白创建** 后的细粒度搭建。

---

## 〇、上下文与数据源定位（先于一切 ds API）

> **必加载** `app-datasource-lookup-guide.md` — 应用内 vs 全系统查找 + **§六探测预算/打断询问**。  
> **必加载** `datasource-selection-and-parent-filter-guide.md` — **少挂数据源** + 连续区域只配入口父格筛选。

| 用户输入 | 行为 |
|----------|------|
| **已给 appId 或 appName** | 解析 appId → **先** `GET …/form/obj/getList/{appId}`（应用内）→ **未命中再**别处（lookup-guide §三）；合计见探测预算 |
| **未给准确表名**（仅业务词/报表名） | **只在当前应用**检索候选 → **二次确认**后再 `addDataset`（lookup §2.0）；CLI：`find form <appId> --suggest "…"`；**禁止**静默绑错表 |
| **已给 appId + sourceId** | **跳过**数据源搜索 |
| **未给 app** | 才允许全系统带关键字检索（**合计 ≤3**）→ 仍须用户确认唯一表 |
| **预算用尽仍不准** | **打断询问** — **禁止**继续盲扫 / 开浏览器扫页 / 固定 sleep |

**禁止**：用户已指定应用时，仍遍历全系统 `/ds/group` 或多分组空扫 —— 这是「发需求后响应慢」的首要原因。

**少挂源**：主表已有用户/部门等字段时，不要再挂人员表、部门表（见 selection-guide §一）。
---

## 一、执行纪律（响应时间）

| 规则 | 说明 |
|------|------|
| **单脚本单次交付** | 登录 → 定位 sourceId → 建壳 → 绑数据集 → 组 workbook → 保存 → 回读验证；**禁止**为排查再写 3～5 个 debug_*.js |
| **轻量加载文档** | API 建表任务**只加载**：`cold-start-scan-guide.md` + 本节 + `app-datasource-lookup-guide.md` + `datasource-selection-and-parent-filter-guide.md`（父格相关段）+ `safe-partial-save-guide.md`（保存相关段）+ `report-delivery-contract.md`（模式 A）；**跳过** `report-knowledge-base.md` 全文、`report-requirement-analysis-template.md`、`report-help-guide.md`、`report-building-guide.md`、`datasource-metadata-guide.md`、`build_guide_html`、`weaver-e10-login`；**禁止**查找/加载 `e10-cli*` 与 `.workbuddy/**` |
| **找表：先应用后别处** | 已给 app → **先** `GET /api/bs/ebuilder/form/obj/getList/{appId}`；未命中才别处检索；见 lookup-guide §二→§三 |
| **禁止固定 sleep** | `addDataset` 后用 **短轮询** `dataset/list`（如 100ms×≤8），**禁止** `sleep(800)` / 盲等 |
| **禁止为 API 启浏览器** | 建表/找表用 `https` multipart；**禁止** `chromium.launch` + 打开应用页扫表单 |
| **禁止探索性 API** | 未指向明确目的不得 copySheet、preCheck 全表、跨报表对比、全系统 ds/group 首轮遍历；找表超预算必须问用户 |
| **禁止擅自 copySheet** | 仅当用户**明确要求复制某张表**时使用；从模板 JSON 搭布局是默认路径 |
| **失败最多重试 1 次** | 同一 API/步骤最多再试 1 次；布局仍失败 → **删空壳**（见下）禁止同 id 死循环 |
| **失败/中止必删空壳** | 建壳后若布局未成功落库，或任务失败/用户中止 → **`deleteReport` 清掉临时壳**；禁止列表残留空白报表。见 `failure-cleanup-and-nonblocking-guide.md` §一 |
| **附属失败不卡死** | 查询条件/权限/快照等失败 → **提示用户** → 继续其它步骤 → 交付主表 → 收尾再自动补试 1 次；禁止卡在单点。见同指南 §二 |
| **CLI 优先** | 历史沉淀可执行点一律 `edc-report`（见 `edc-report-cli.md` §一映射）；禁止堆 debug 脚本 |
| **多表关联** | 需求写明 → 按需求配；未写明 → `edc-report join suggest` + **提示用户确认**（selection-guide §2.5） |
| **查询条件** | `edc-report query save`（multipart 单对象）；失败提示后继续 |
| **失败删壳** | `edc-report cleanup shells` |
| **交付自检** | `edc-report verify all`（可后台） |
| **交付物克制** | **布局落库成功后立刻给设计器地址并结束**（`report-delivery-contract.md`）；**默认不**做 HTML / verify / 预聚合 / 需求分析；用户要分析时才走分析模板 |
| **默认表头样式** | 用户未指定样式且无效果图 → 自动蓝标题+灰列头（`default-header-style-guide.md`）；有指定/效果图则完全按用户 |
| **文档输入一次解析** | Excel/JSON 需求只解析一次 |
| **首建跳过 cache** | 单数据集、无跨表 leftFilterField 时，首次可省略 `saveReportWithCacheConfig` |
| **页面布局默认关闭** | 网格线 page `gridLine=0`；**workbook 禁写 gridline**（存在→500）；落库前 `validate gridline`（§4.6.1） |
| **耗时目标** | 已给 app+表名：找表 **≤2s**；整段落库 **≤5s**（不含用户确认） |

---

## 二、标准流程（约数秒，非 30～60s）

```
0. e10-login status（本地，勿 sleep）
0.2 【优先 CLI】edc-report find form <appId> <准确表名>
    若用户未给准确表名 → find form <appId> --suggest "需求关键词" → **等用户确认** → 禁止静默 addDataset
0.3 多表且需求未写关联 → edc-report join suggest … → 提示用户确认（可先按 best 配并标注待确认）
0.5 解析 appId；GET form/obj/getList/{appId} → sourceId（未中再别处，见 lookup-guide）
1. POST baseInfo(id=0, **name=目标报表名**) → reportId
2. POST addDataset(sourceId)  **须** `sourceType=LOGIC` + `sourceGroup=weaver-ebuilder-form-service`（普通应用；见 `add-dataset-registration-guide.md`）
2.1 poll dataset/list 直到 sourceId 命中     → datasetId（禁止固定 sleep；**禁止跨报表复用 datasetId**）
3. GET fieldsAndOriginFields?isFront=true   → data.fieldsKey（**同 reportId，禁止另建探测壳取字段**）
3.1 **门禁**：业务字段应含 `field_*`；若多为裸雪花 → 注册错，delDataset 重建（禁止在 Field 上手工补前缀）
4. 按模板 remap 字段 + buildWorkbook（多表入口格配父格筛选）
5. POST saveReportDevInfo(**name=目标报表名**)
6. [可选] saveReportWithCacheConfig
7. GET getReportDevInfo 验证；**禁止**再 rename
```

**失败清理**：步骤 1 已拿到 `reportId`，但步骤 5 未成功或任务中止 → **必须** `deleteReport` 删除空壳，见 `failure-cleanup-and-nonblocking-guide.md`。

### 2.05 提速三件事（实测；细则 `session-build-performance-guide.md` §六补充）

1. **HTTPS 连接复用**：全程一条连接（keep-alive）。每请求 new 一次 ≈271ms/次，复用 ≈115ms/次。
2. **ETEAMSID 只解析一次**：`e10-login status` ≈0.9s，写本地缓存复用；禁止每脚本/每请求 subprocess。
3. **可省的接口**：新空壳 `saveReportDevInfo` 的 `designKey` 传空串即可（无需先 `getReportDevInfo`）；`fillDatasetConfig` 只在运行态取不到数据时补；`dataset/list` 通常首次即命中，**禁止**预 sleep。

> 另：**禁止跨报表复用 datasetId**；仅本 report 已挂载的数据集可复用。取字段必须在本表 `addDataset` 之后。

### 2.1 新建报表命名（禁止空壳临时名）

> **必加载** `report-baseinfo-defaults-guide.md`（平台默认值权威表）。

- **`baseInfo` / `saveReportDevInfo` 全程用目标报表名**；**禁止** `__build_*` / `__probe_*`。  
- **禁止**落库后再 rename（撞名易残留壳名）。  
- **字段先预检再建表**：`fieldsBySource` 精确匹配通过才 `baseInfo`；否则 exit 4（**不建表**）。  
- **同源只挂一次**：本表已有同 `sourceId` 数据集必须复用，禁止二次 `addDataset`（否则左侧重复分组）。  
- **对齐平台默认**：`groupId=0`、`showOrder=1`、`nameLabelId="-1"`；`groupId` 禁止写 `-1`（列表哨兵）。  
- **`name` / `nameLabelId`**：trim；禁控制字符；落库前可 `validate base`。  
- 定源未确认（fuzzy）前 **禁止** `baseInfo`。CLI：`edc-report build spec`。

### 2.2 保存顺序（新空报表 · 已验证）

| 顺序 | 接口 | 新空报表 | 已有 layout 的报表 |
|------|------|----------|-------------------|
| **①** | `saveReportDevInfo` | **必须** | 必须（改 layout） |
| **②** | `saveReportWithCacheConfig` | 可选，且在 ① 成功之后 | 可选（跨表筛选缓存） |

**禁止**：新报表在 **从未** 成功 `saveReportDevInfo` 之前单独调用 `saveReportWithCacheConfig` —— 会损坏报表壳，后续 dev 保存持续 500。

---

## 三、字段映射（禁止字符串全局替换 · 禁止匹配失败）

> **必加载** `field-bind-exact-match-guide.md` — 字段名唯一来源、裸雪花 ID 事故、保存前后门禁。  
> **必加载** `add-dataset-registration-guide.md` — **addDataset 必须与设计器一致**，否则 `fieldsKey` 无 `field_`。

### 3.0 硬约束（零容忍）

| 规则 | 说明 |
|------|------|
| **注册先于绑定** | 普通应用 `addDataset`：`sourceType=LOGIC` + `sourceGroup=weaver-ebuilder-form-service`；错用 `form`+`sourceGroup=appId` → fieldsKey 裸雪花 |
| **唯一来源** | Field 的 `name` **必须**等于 **当前 dataset** 的 `fieldsKey[].name`（不是显示名、不是臆造前缀） |
| **常见形态** | 设计器兼容注册下业务字段为 `field_{雪花}`；系统字段为 `create_time` / `name` / `creator` 等原样 |
| **禁止去前缀** | `field_3506…` **不可**写成 `3506…` —— 设计器有格、取数全挂（事故 AAA） |
| **禁止手工补前缀** | fieldsKey 已是裸雪花时，**先修注册**再绑定；禁止只在 cell 上加 `field_` 凑数 |
| **保存前门禁** | 每个 Field：`fieldsKey.name` 集合 `.has(name)`；失败则**中止保存** |
| **保存后门禁** | `node scripts/verify_field_bind.js <reportId> [appId]` 必须 PASS 才可交付 |

### 3.1 正确做法

对每个 `cellType=Field` 的模板单元格 **逐对象** 改写：

```javascript
// fieldName = fieldsKey 中按 text/showName 命中的那一项的 .name
nf.dataSetId = newDatasetId;
nf.nameIndex = newSourceId;
nf.name = fieldName;           // 必须 === fieldsKey[].name（含 field_ 前缀）
nf.fieldKey = `${newDatasetId}.${newSourceId}.${fieldName}`;
// 同步 patch style 内嵌的 cellType 对象（见 §四）
nf.allNeedFields = '';
assert(legalNames.has(nf.name), `name 必须∈ fieldsKey: ${nf.name}`);
// 裸雪花 / field_ 前缀以 fieldsKey 为准，禁止凭记忆改写

```

### 3.2 禁止

- `JSON.stringify` 全量后 `split(oldId).join(newId)` 替换 fieldKey（datasetId 先替换会导致 fieldKey 替换失败，残留旧字段 ID）
- 用裸雪花 ID（无 `field_`）作 `name` / fieldKey 末段 —— **字段获取不上**
- 用显示名（如「资产类别」）作 `name` 或完整 fieldKey
- 截断字段名（`field_5`）或臆造 `field_*`
- 用表单 fieldId 未与 `fieldsKey.name` 交叉核对就直接写入

### 3.3 字段 discovery

```
# ① 建表前预检（无需报表；与 fieldsKey 同形）
GET /api/bs/edc/dataset/fieldsBySource?sourceId=&sourceType=logic&groupId=weaver-ebuilder-form-service
# ② 落库前权威（本表 addDataset 之后）
GET /api/bs/edc/dataset/fieldsAndOriginFields
  ?datasetId={id}&hasField=true&isFront=true&reportId={reportId}
→ data.fieldsKey[]   // 权威；取 .name 写入；isFront=false 常返回空
```

`addDataset` 不返回 datasetId → 必须 `dataset/list?reportId=` 按 **sourceId** 匹配，**禁止**按数组下标。

**字段绑定门禁（2026-09-11 强制）**：用 `spec_lib.resolveFieldBindings()`，仅**精确**匹配
（`fieldName`/`fieldMap` → 列标题 === `text` → `field` === `text`/`name`）；
任一列无精确命中 → **exit 4**，把 `candidates`/`allFields` 交用户指定，**禁止模糊兜底、禁止回退系统字段**。
详见 `field-bind-exact-match-guide.md §2.0`。

---

## 四、workbook 单元格 style 键名（字段丢失根因）

平台 `getFieldsFromWorkbook` 读取的是 Java 字段 **`style.cellType`**（`AnalysisFieldCellType`），**不是** `analysisFieldCellType`。

| 场景 | 正确键名 |
|------|----------|
| **上传 workbook（saveReportDevInfo）** | `style.cellType` |
| **getReportDevInfo 回读的 fields[].style 字符串** | 可能含 `analysisFieldCellType`（库内序列化） |

**buildCellFromField 模板**：

```javascript
const style = parseJson(f.style, {});
const ct = style.analysisFieldCellType || style.cellType;
if (ct && typeof ct === 'object') {
  style.cellType = ct;
  delete style.analysisFieldCellType;
}
// Formula 另加 cell.formula = f.cellText（无前导 =）
```

**症状**：`fields.length=21` 但 `cellType` 全是 `Const`、设计器无字段绑定 → 即 style 键名错误。

---

## 五、保存后验证（一次回读 · 含字段精确匹配）

```javascript
const dev = getReportDevInfo.data;
const types = countBy(dev.fields, 'cellType');
// 期望示例：{ Const: 11, Field: 8, Formula: 2 }
types.Field >= 1 || FAIL;
dev.fields.some(f => f.fieldKey && f.cellType === 'Field') || FAIL;

// 强制：每个 Field.name / fieldKey末段 ∈ fieldsKey.name（见 field-bind-exact-match-guide.md）
// 或: node scripts/verify_field_bind.js <reportId> <appId>
```

| 检查项 | 通过标准 |
|--------|----------|
| `fields.length` | ≥ 预期单元格数（通常 >15） |
| `cellType` 分布 | 含 `Field` 与（如有公式）`Formula` |
| fieldKey 三段 | `{datasetId}.{sourceId}.{fieldsKey.name}` |
| **精确匹配** | **每个** Field 的 `name` ∈ 当前数据集 `fieldsKey.name`；禁止裸雪花 ID |
| `verify_field_bind.js` | Exit 0；失败则**禁止交付** |
| 损坏壳 | save 500 且 fields 全 Const/0 → `deleteReport` 重建，勿 resume |

---

## 六、故障对照表（禁止盲目重试）

| 现象 | 根因 | 处理 |
|------|------|------|
| saveReportDevInfo **500** 新空壳 | 先调了 cache / 壳已损坏 / dev 保存用了目标名 | 删 reportId → 临时名重建 → dev 保存 **name=临时名** → 成功后再 baseInfo 改名 |
| fields 全 **Const** | workbook 用了 `analysisFieldCellType` | 改为 `style.cellType` 重保存 |
| fieldKey 末段仍是旧雪花 ID | 字符串 replace 顺序错误 | 逐字段对象 remap（§三） |
| **有 Field 格但字段获取不上 / 取数空** | **`name` 为裸雪花 ID（缺 `field_`）或不在 fieldsKey** | 按 `field-bind-exact-match-guide.md` 重绑；`verify_field_bind.js` |
| 设计器 0 字段 / workbook cells 0 | 损坏壳或空 workbook 落库 | deleteReport + 重建；见 `safe-partial-save-guide.md` |
| 同名第二张报表 | 重复 baseInfo | 列表查重，删多余壳，只保留一张 |

---

## 七、禁止走的弯路（已验证浪费时间）

1. **copySheet** 探路 + 再手工建表（用户未要求复制时）
2. **preCheck** 全表二分 / 去掉公式逐格试（应先查 §四 style 键名）
3. **跨报表**把 A 报表 fields 保存到 B 报表壳（壳损坏时仍 500，不能证明 layout 有问题）
4. 在同一损坏 **reportId** 上连续 save 10+ 次
5. 收尾打开源码、changed files；或交链后仍跑 verify/HTML/配置检测  
6. 用户只要搭表时跑需求分析模板或多轮「深度解析」  
7. 「检测生成报表配置」整包自检后再搭表  
8. 查找已删除的测试用例/原型脚本（`generate_test_case` / `prototype-design`）


---

## 八、与现有文档关系

| 文档 | 关系 |
|------|------|
| `safe-partial-save-guide.md` | 已有报表改快照/权限；**新报表首次落 layout 以本节 §二 顺序为准** |
| `cross-dataset-filter-guide.md` | fieldKey / leftFilterField 细节 |
| `formula-cell-api-guide.md` | 公式 cellText、countType |
| `report-delivery-contract.md` | 收尾交付格式 |
| `failure-cleanup-and-nonblocking-guide.md` | 失败删空壳；附属失败不卡死 |
| `app-datasource-lookup-guide.md` | 应用内 sourceId 查找 + 探测预算/打断（§〇 强制） |
| `datasource-selection-and-parent-filter-guide.md` | 少挂源；连续区域仅入口父格筛选 |
| `field-bind-exact-match-guide.md` | Field.name 必须 ∈ fieldsKey；裸 ID 事故与门禁 |
| `add-dataset-registration-guide.md` | addDataset 与设计器对齐；fieldsKey 无 field_ 的根因 |
| `scripts/verify_field_bind.js` | 保存后字段精确匹配校验（交付前必跑） |
| `scripts/safe_report_save.js` | mergeWorkbookSafe；新建布局仍用本节 buildCellFromField |

---

## 九、API 请求头与 multipart 最小集（禁止浏览器自动化）

```javascript
// headers 每次请求
{ eteamsid, ebBusinessId, ebbusinessid, Referer: .../designer/{reportId},
  'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true' }

// saveReportDevInfo multipart
{ groupId, appId, reportId, name, nameLabelId: '-1', designKey, workbook: gzipBase64 }
```

`designKey` 来自当次 `getReportDevInfo`；保存前只拉 **一次**。
