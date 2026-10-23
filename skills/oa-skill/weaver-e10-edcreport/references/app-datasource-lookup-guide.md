# 应用内数据源查找（强制优先级）

> **适用**：能力一/五、API 从零搭建报表时，需要把「需求里的表单/数据源名称」解析为 `sourceId`。  
> **核心规则**：**先当前应用、后别处**；命中即停；**禁止**固定 `sleep`；**禁止**为找表启动 浏览器自动化 开应用页。

---

## 一、判定顺序（任务开始后第一步）

| 输入 | 解析 appId | 找 sourceId |
|------|------------|-------------|
| **appId + 数据源名** | 直接用 | **① 应用内**（§二）→ 未命中再 **② 别处**（§三，有限次） |
| **appName + 数据源名** | `GET /api/bs/ebuilder/app/list?name={appName}&pageNo=1&pageSize=20` **1 次** | 同上 |
| **仅数据源名，无 app** | — | 直接 §三（须带关键字） |
| **appId + sourceId 已给** | 直接用 | **跳过查找**，直接 `addDataset` |

**禁止（已指定 app 时的首轮）**：

- 一上来就 `GET /ds/group` 全系统遍历
- 对每个 `groupId` 循环 `listByPage` 空扫
- 多 module（`ebuilder` / `bs` / `datasource`）无关键字轮询试探
- **先拉系统级分页再本地过滤「当前应用」**（分页也必须带 appId）
- **`sleep` / `setTimeout` 固定等待** 代替「读接口直到有数据」
- **浏览器自动化 打开应用详情页** 扫网络找表单（实测 ~17s，且非必要）

**强制优先级**：`edc-report find form` = `getList/{appId}` → 未命中再问用户 / 有限次应用内关键字 listByPage → **最后**才别处。  
见 `session-build-performance-guide.md` §二。

---

## 二、应用内查找（已指定 appId · 优先 · 通常 1 次）

### 2.0 未指定准确表名（强制 · 二次确认）

> **事故模式**：需求只写业务描述（如「资产统计」「党员发展」）未给表单名 → Agent 模糊匹配错表 → 数据集字段对不上。

| 用户输入 | Agent 行为 | 绑定 |
|----------|------------|------|
| **已给准确表名** 且应用内 **exact 唯一** | 可 `find form` 后绑定 | `autoBind=true`（建议仍口头确认） |
| **未给表名** / 只给业务词 / 报表名 | **只在当前应用** `getList/{appId}` 检索 → 按关键字打分出候选 | **`needConfirm=true`，禁止 addDataset** |
| **模糊命中 1 条或多条** | 展示候选（表名 + sourceId） | **必须等用户确认** 后再绑 |
| 应用内无候选 | 问用户准确表名/sourceId；**禁止**立刻全系统 `/ds/group` | 不绑 |

**二次确认话术（强制）**：

```text
需求未指定准确表名。已在当前应用内检索到以下候选，请确认用哪一张（回复表名或 sourceId）：
1. {nameA}（sourceId=…）
2. {nameB}（sourceId=…）
若都不是，请给出准确表单名或 sourceId。
```

**禁止**：未确认就 `addDataset` / 落库绑字段；禁止用报表标题「看起来像」的表直接当数据源。

CLI：

```bash
edc-report find form <appId> --list
edc-report find form <appId> --suggest "资产,台账"
edc-report find form <appId> "准确表单名"   # exact 才可 autoBind
```

exit code **3** = 须二次确认（`needConfirm=true`）。

按优先级尝试，**命中即停**（合计计入 §六预算）：

### 2.1 【首选 · eteams 已验证】应用表单列表

```
GET /api/bs/ebuilder/form/obj/getList/{appId}?apid={appId}
```

- Header：`eteamsid` + `Cookie: ETEAMSID=…` + `ebBusinessId={appId}`
- 响应为应用内表单数组（或包在 `data`）；按 `name` **精确或包含**匹配需求表名
- 取命中项的 **`id`** 作为 `sourceId`（`addDataset` 用）
- **示例**：应用 `786501450842480640` 中「进销存-销售单」→ `787599094054395904`

```javascript
async function findFormInApp(host, headers, appId, formName) {
  const j = await get(`${host}/api/bs/ebuilder/form/obj/getList/${appId}`, { apid: appId }, headers);
  const rows = Array.isArray(j.data) ? j.data : Array.isArray(j) ? j : j.data?.list || [];
  const exact = rows.find((r) => r.name === formName);
  if (exact) return String(exact.id);
  const fuzzy = rows.find((r) => String(r.name || '').includes(formName) || formName.includes(String(r.name || '')));
  return fuzzy ? String(fuzzy.id) : null;
}
```

### 2.2 CLI（表单类 · 优先）

```bash
edc-report find form <appId> <表单名>    # 推荐（本包唯一 CLI 入口）
node scripts/find_form_in_app.js <appId> <表单名>   # 仅 CLI 未装时
```

若 `edc-report` auth 与 `e10-login` 不同步失败 → **改走 §2.1**，不要去找 e10-cli。

字段核对（已有 sourceId 后）：

```bash
# 报表侧（推荐）：
# GET /api/bs/edc/dataset/fieldsBySource?sourceId=&sourceType=logic&groupId=weaver-ebuilder-form-service
# 或 addDataset 后 fieldsAndOriginFields?isFront=true
```

### 2.3 HTTP 备用（仅当 §2.1 失败）

```
GET /api/datasource/ds/listByPage?sourceType=logic&appid={appId}&condition={关键字}&pageNo=1&pageSize=50
GET /api/ebuilder/form/ds/listByPage?sourceType=LOGIC&groupId=0&name={关键字}&appId={appId}&pageNo=1&pageSize=50
```

> **注意**：部分环境 `form/ds/listByPage` 会 500；**不要**因此改去开 浏览器自动化，应回退 §2.1 或进入 §三 / 询问用户。

---

## 三、别处检索（应用内未命中 或 未给 app）

**仅当**：应用内 §二已试完仍无命中，**或**用户未指定应用。

1. `GET /api/datasource/ds/listByPage`（或 `/api/{module}/ds/listByPage`）带 **`name`/`condition` 关键字** + 必要时 `groupId`
2. **禁止**无关键字翻页扫全库
3. 仍计入 §六预算；用尽 → **打断询问**，不要继续盲扫

> **实测坑（<your-e10-host>）**：按「应用名」找应用这条路在本环境不可用 ——
> `GET /api/bs/ebuilder/app/list?name={kw}` 与 `edc-report app search --name {kw}` **服务端忽略 `name`**，
> 恒返回全量 998 条且顺序固定，**不能**靠它定位应用。找不到表时：直接用 `ds/listByPage` 关键字搜数据源，或向用户要 appId/sourceId。

若用户其实给了应用名但 Agent 漏解析 → 应先补 `app/list` 再回 §二，而不是直接全系统扫。

---

## 四、与报表 API 闭环（禁止固定 sleep）

```
解析 appId（若需要，最多 1 次 app/list）
    → findFormInApp / §二（优先 getList）
    → [未命中] §三 别处（有限次）
    → POST addDataset(sourceId)
    → poll GET dataset/list?reportId=  直到出现匹配 sourceId 的行（见下）
    → GET fieldsAndOriginFields?datasetId=&isFront=true&reportId=
```

### 4.1 addDataset 后：轮询代替 sleep（强制）

**禁止** `await sleep(800)` / `setTimeout(800)` 之类固定等待。

```javascript
async function waitDatasetBySource(reportId, sourceId, { tries = 8, gapMs = 100 } = {}) {
  for (let i = 0; i < tries; i++) {
    const list = await getDatasetList(reportId); // GET /api/bs/edc/dataset/list?hasField=true&reportId=
    const hit = (list || []).find((d) => String(d.sourceId) === String(sourceId));
    if (hit) return hit;
    await new Promise((r) => setTimeout(r, gapMs)); // 仅短间隔重试，非「盲等 800ms」
  }
  throw new Error(`dataset not ready for sourceId=${sourceId}`);
}
```

- 首包常立刻命中（~60ms）；未就绪再 100ms 级重试，总等待远小于固定 800ms。
- `addDataset` 不返回 `datasetId` → **必须**按 **sourceId** 匹配，禁止按下标 `[0]`。

---

## 五、HTTP 客户端优先（强制 · 性能）

| 做法 | 说明 |
|------|------|
| **首选** | Node `https` / `fetch` / 浏览器自动化 **仅** `request` API 发 HTTP（若已有 context） |
| **禁止为找表** | `chromium.launch` + `page.goto(应用详情)` 扫表单（~0.6s+0.5s+打开页数秒） |
| **禁止为纯 API 建表** | 仅为 `baseInfo/addDataset/save` 而启动浏览器；用 https + multipart 即可 |

实测：纯 API 路径找表 + 建表可压到数秒；浏览器自动化 启浏览器 alone ≈ **1s+**。

---

## 六、探测预算与打断询问（强制 · 防空耗）

### 6.1 单次任务硬上限

| 项 | 上限 | 说明 |
|----|------|------|
| 应用解析 `app/list` | **1** | 已有 appId 则 0 |
| **应用内**找表（`getList` / `form list` / scoped listByPage） | **合计 ≤ 2** | 换关键字也算；命中即停 |
| **别处** `group` + `listByPage`（应用内未中或未给 app） | **合计 ≤ 3** | 必须带 name；禁止翻页空扫 |
| 同一关键字换 module 无脑重试 | **禁止** | |
| 固定 `sleep` ≥ 300ms 等数据集 | **禁止** | 用 §4.1 轮询 |
| 浏览器自动化 开应用页找表 | **禁止** | |

### 6.2 何时必须打断并询问用户

1. §6.1 预算用尽仍无唯一命中。  
2. 关键字命中多条，无法确认。  
3. 表名与应用内列表对不上。  
4. 连续 2 轮仍在换词/换接口盲扫。  
5. **用户未指定准确表名**（仅业务描述/报表名）→ 应用内 `--suggest`/`--list` 后 **二次确认**（§2.0）；**禁止**静默绑定。  
6. **模糊匹配**（`match=fuzzy`）→ 即使只有 1 条也必须确认。

询问：应用？准确表名或 **sourceId**？多候选点选哪张？

### 6.3 禁止的空耗行为

- 未给 app 时先全系统 group「碰运气」
- 已给 app 却跳过 §二直接别处扫
- 固定 sleep、开浏览器扫页、输出长探测日志代替提问

---

## 七、耗时对照（优化目标）

| 路径 | 典型耗时 | 说明 |
|------|----------|------|
| `getList/{appId}` 应用内命中 | **~0.2–0.5s** | **推荐** |
| 固定 sleep(800) + 浏览器自动化 启浏览器 | **~2s+** | **禁止** |
| 浏览器自动化 打开应用详情扫表单 | **~15–20s** | **禁止** |
| 全系统 group 遍历 | **数秒～数十秒** | 仅 §三兜底 |

API 从零搭建：数据源定位应控制在 **2 秒内**（已给 app 时）；整段建表（已知名）目标 **≤ 5s**（不含用户确认）。

---

## 八、与现有文档关系

| 文档 | 关系 |
|------|------|
| `scripts/find_form_in_app.js` | 应用内 `getList` 找 sourceId（无 sleep/无浏览器） |
| `api-report-build-fast-path.md` | 建表流程 §〇 / 性能纪律引用本节 |
| `datasource-metadata-guide.md` | 有 app → 本节；无 app → §三 |
| `datasource-selection-and-parent-filter-guide.md` | 少挂源 |
| `e10-cli-integration.md` | 本包不含 e10-cli；勿扫描 |
