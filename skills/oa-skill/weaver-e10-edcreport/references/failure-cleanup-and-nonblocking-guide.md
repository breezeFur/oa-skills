# 失败清理与非阻塞执行（强制）

> **适用**：API/脚本建表、改查询、改布局等全过程。  
> **目标**：① 失败/中止不留下空壳报表；② 单点失败不卡死整条流水线。

---

## 一、空壳报表必须删除（强制）

### 1.1 何谓空壳 / 废壳

| 情形 | 判定 |
|------|------|
| 已 `baseInfo` 建壳，但 **`saveReportDevInfo` 未成功** 或 fields 为空 | **空壳** |
| 临时名 `__build_*` / `__probe_*` / `__bench_*` 且任务失败或中止 | **废壳** |
| 同任务多次失败留下的多个半成品 reportId | **废壳（全部清）** |
| 布局已成功落库、仅查询条件等附属能力失败 | **不是空壳** → **保留**报表，只提示附属失败 |

### 1.2 何时必须删

出现以下**任一**情况，在收尾或换路径前 **立刻**删除（进回收站即可）：

1. 命令/脚本 **失败**（exit ≠ 0、save 500、抛错未交付可用表）  
2. 用户 **中止** / Agent 放弃本轮建表  
3. 决定 **删壳重建**（新 reportId）之前，旧失败壳必须先删  
4. 探测用临时壳（`__probe_*`）用完必须删  

**优先 CLI**：

```bash
edc-report cleanup shells --app-id <appId> --report-id <reportId>
# 或临时名前缀：
edc-report cleanup shells --app-id <appId> --prefix __build_
```

等价 API：

```
POST 或 GET /api/bs/edc/report/deleteReport
  id={reportId}   # 可逗号分隔批量
  + Header ebBusinessId={appId}
```

见 `report-lifecycle-api-guide.md` §删除。

### 1.3 执行纪律

| 规则 | 说明 |
|------|------|
| **跟踪 reportId** | 建壳成功后立刻记下 `reportId`；`finally`/catch 中若未交付成功布局 → 删除 |
| **禁止留页面垃圾** | 失败后列表页不应残留「点进去空白/无字段」的报表 |
| **告知用户** | 若已删：一句话说明「已删除失败空壳 {name/id}」；若附属失败保留主表：说明「主表已交，XX 未配上请确认」 |
| **禁止** | 失败后不管、叠多个 `__build_*`；或把空壳改成目标名交付 |

```javascript
let reportId = null;
let layoutOk = false;
try {
  reportId = await createShell(tempName);
  // ... addDataset / saveReportDevInfo ...
  layoutOk = true;
  await rename(reportId, targetName);
} catch (e) {
  // 提示用户，勿死循环
} finally {
  if (reportId && !layoutOk) {
    await deleteReport(reportId); // 空壳必删
  }
}
```

---

## 二、单壳搭建（强制 · 一次任务只允许 1 个报表壳）

> **用户强制要求（2026-09-14）**：搭建报表**不要搭多个模板空壳报表**。
> 现象：一次搭建里为每个变体/每次试验各建一个壳（`__probe_*`、`__regtest_*`、`__build_a/__build_b/...`），
> 结果应用列表页堆一堆半成品，既难维护又违反交付契约。

### 2.1 铁律

| # | 规则 |
|---|------|
| 1 | **一次搭建任务从头到尾只建 1 个报表壳**，命名 `__build_<业务>_<时间戳>`，全程复用（失败重试、变体试验、布局迭代都改同一个壳） |
| 2 | **禁止**为「试 A 方案 / 试 B 方案」各建一个壳。变体 = 同一个壳内改单元格后重新 `saveReportDevInfo` |
| 3 | **禁止**为探针建报表壳。只读回读即可满足 90% 探针需求：<br>`getReportDevInfo.fields`（结构/字段/父格）、`GET /api/bs/edc/dataset/list?reportId=`（数据集）、`fieldsAndOriginFields`（字段映射）、`getQueryItemNew`（查询条件） |
| 4 | 仅在「必须验证某个**写**接口行为」时才允许临时壳，命名 `__probe_*`，且**同一时刻最多 1 个、用完立即删** |
| 5 | 主路径成功 → **立刻把唯一那个壳改名为目标名**并交付；主路径失败 → 删掉它（见 §一），**不留待下次** |
| 6 | 交付时向用户交代的 reportId 清单必须**恰好 1 个**（最终表） |

### 2.2 收尾自查（只读，不改任何东西）

```bash
# 全应用空壳体检：列出每张报表的 fields 数，标出 fields=0 的空壳
edc-report cleanup shells --app-id <appId> --list

# 确认没有遗留的建表壳
edc-report cleanup shells --app-id <appId> --prefix __build_ --dry-run

# 确认没有遗留的探针壳
edc-report cleanup shells --app-id <appId> --prefix __probe_ --dry-run
```

`--list` / `--dry-run` 为**只读**模式，只输出 JSON 结论（`verdict: ✅ 无空壳报表`），不会删除任何报表。

### 2.3 报告壳 ≠ 数据集

「空壳报表」是**报表级**残留；报表内**挂错/多余的 dataset 条目**同样算残留，须按 §四清理。

---

## 三、报表内多余数据集清理（强制）

一次 `addDataset` 失败重试、或注册形态返工，很容易在同一张报表上**挂多套数据集**（设计器左侧出现重复数据源）。判定与清理：

| 步骤 | 做法 |
|------|------|
| ① 数引用 | `getReportDevInfo` → 按 `fields[].dataSetId` 分组计数，**计数 = 0 的即为残留** |
| ② 占用检查 | `GET /api/bs/edc/dataset/checkDataSetUsed?datasetId=<dsId>&reportId=<rid>`，`data=false` = 安全 |
| ③ 删除 | `POST /api/bs/edc/report/delDataset`，**multipart 参数是 `reportId` + `sourceIds`**，其中 **`sourceIds` 传的值是 `datasetId`（不是 sourceId！）** |
| ④ 豁免 | 系统默认数据集 `dataUpdateTime` / `数据更新时间` **禁止删除** |
| ⑤ 回归 | 删完再跑 `edc-report verify all <reportId> <appId>`，确认 `fields` 数不变、绑定 PASS |

> ⚠️ 常见坑：`delDataset` 用 `datasetId` / `id` / `sheetId` 作参数名一律 **400 Bad Request**；正确键名只有 `sourceIds`。

---

## 四、单点失败不卡死（强制 · 非阻塞）

### 4.1 原则

| 能力分层 | 失败时 |
|----------|--------|
| **主路径**（找表、建壳、绑数据集、布局 save） | 失败 → 清理空壳 → **提示用户** → 可问清后重试；**禁止**同点无限重试 |
| **附属路径**（查询条件、权限、快照、预聚合、HTML 手册、视觉核对） | 失败 → **提示用户自行确认/可后补** → **继续其它步骤** → 交付主成果 → **末尾再尝试自动修复 1 次** |

**禁止**：在 `saveQueryItem` / 某次 options / 某次 verify 上连试 5～10 轮导致整任务卡死。

### 4.2 重试上限

| 类型 | 上限 | 之后 |
|------|------|------|
| 同一 API/同一步 | **1 次重试**（共 2 次尝试） | 记入「待用户确认 / 待收尾补丁」清单，**跳过** |
| 找表探测 | 见 `app-datasource-lookup-guide.md` §六预算 | **打断询问** |
| 布局 save | 1 次修正后仍失败 | 删壳，提示用户，停止建表 |

### 4.3 提示话术（简短）

附属失败示例：

> 查询条件写入失败（`saveQueryItem` 返回 500/超时）。报表主体已保存，请你在设计器「查询设置」中确认或告知正确条件字段；我先继续其它配置，最后再自动补试一次。

主路径失败示例：

> 布局保存失败，已删除空壳报表 `{临时名}`（`{reportId}`）。请确认应用/数据源是否正确，或提供可用的 sourceId 后我再重建。

### 4.4 推荐流水线顺序

```
1. 主路径：找表 → 建壳 → 布局落库 → 【成功则立刻交设计器地址】
2. 附属：查询条件 / 权限 / …（任一步失败 → 提示 + 跳过）
3. 收尾：对「跳过清单」各自动补试 ≤1 次；仍失败 → 汇总给用户，不阻塞结束
4. finally：若主路径未成功 → deleteReport 空壳
```

### 4.5 与查询条件 500

见 `query-condition-api-guide.md` §二点五：先按调用形态自检 **1 次**；仍失败 → **提示用户 + 继续其它工作**，禁止卡在 saveQueryItem。

---

## 五、与现有文档

| 文档 | 关系 |
|------|------|
| `api-report-build-fast-path.md` | 建表纪律引用本节 |
| `report-delivery-contract.md` | 主路径成功才交链接；附属失败不挡交付 |
| `report-lifecycle-api-guide.md` | deleteReport |
| `app-datasource-lookup-guide.md` §六 | 找表预算与打断 |
| `query-condition-api-guide.md` §二点五 | 查询 500 不卡死 |
| `targeted-fix-guide.md` | 定点改；失败同样清理废壳 |
| `add-dataset-registration-guide.md` | §三「报表内多余数据集清理」的注册形态背景 |
| `report-data-model.md` | 数据集 / 单元格 `dataSetId` 引用模型 |
