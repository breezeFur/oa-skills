# 局部功能保存 · 设计区保护规范

> **适用场景**：通过 API / 脚本修改**快照、权限、查询条件、数据集筛选、页面布局**等「非布局主体」能力时。 
> **事故根因（已验证）**：对 `saveReportDevInfo` 提交**空 workbook** 或 **workbookProps.sheets 无单元格** 的 payload，会**全量替换** `edc_reportsheetfield_dev` 等表，导致设计器字段与单元格配置被清空。 
> **硬约束**：除非用户**明确要求删除/清除字段**，否则设计区域内容**不得被置空**。

---

## 一、核心原则

| 原则 | 说明 |
|------|------|
| **布局不可丢** | `getReportDevInfo.fields.length > 0` 是保存前最低门槛；保存后必须回读验证 |
| **禁止空 workbook 落库** | `workbookProps.sheets` 为空 **且** `fields` 为空 → **禁止**调用 `saveReportDevInfo`；`fields>0` 但 sheets 空 → **必须从 fields 重建**（含 spans）后再存 |
| **剔除 `(0,0)` 空 Const** | `x=0,y=0` 且文案空的 Const 为异常幽灵格，保存前删除 |
| **workbookProps 不可盲信** | 线上常见 `fields=12` 但 `workbookProps.dataTable` 为空；此时必须从 **fields 重建** dataTable |
| **groupId 原样回传** | `saveReportDevInfo` 的 `groupId`/`nameLabelId` 取自 `baseInfo`，禁止硬编码改分组 |
| **专用接口优先** | 权限 → `savePermissions`；查询 → `saveQueryItem`；数据集筛选 → `queryInfoSave`；版本还原 → `rollbackReport` |
| **快照是唯一例外需写 workbook** | 快照配置挂在 `workbook.snapshot`，必须走 `saveReportDevInfo`，但须套用 **§三 安全合并** |
| **快照 ID 禁 Number()** | `sheetId`/`id`/`jobId` 必须 **String(雪花)**；`Number(reportId)` 截断 → **设计区空白**（见 `designer-blank-prevention-guide.md`） |
| **快照默认名** | 未指定时 **`{报表名}-{date}-{time}`** |
| **showLocation 禁 0** | 合并 workbook 时若为 0 → 改为 **2**（或用户点名居左则 1） |
| **保存前快照版本** | 对已有报表做任意 `saveReportDevInfo` 前，建议 `saveAsVersion --list-only` 确认有版本可还原 |

---

## 二、接口与布局影响矩阵

| 操作 | 推荐接口 | 是否触及 layout/fields | 备注 |
|------|----------|------------------------|------|
| 使用/禁用权限 | `permission/table/savePermissions` | **否** | 全量替换权限 JSON，不动 fields |
| 矩阵权限 | `permission/matrix/save` | **否** | |
| 查询条件 | `saveQueryItem` / `saveQueryConfig` | **否** | |
| 数据集筛选 | `queryInfoSave` | **否** | |
| 存为新版本 | `saveAsVersion` | **否**（复制快照） | |
| 还原版本 | `GET rollbackReport` | **是**（整表替换） | 用户显式还原；会重置快照配置 |
| 页面布局/分页 | `allPageSetting` | **否**（pageSetting 独立） | |
| 定时快照 | `saveReportDevInfo` + `workbook.snapshot` | **是（若 workbook 空则灾难）** | 必须 §三 |
| 修改单元格/父格 | `saveReportDevInfo` +（可选）`saveReportWithCacheConfig` | **是** | **新空报表必须先 dev 后 cache**；见 `api-report-build-fast-path.md` |

---

## 三、saveReportDevInfo 安全合并流程（强制）

凡必须调用 `saveReportDevInfo` 且**不是**「从零新建报表」或「用户要求清空」：

```
1. GET getReportDevInfo?reportId=
2. fields = data.fields || []
3. IF fields.length === 0 → ABORT（提示先 rollbackReport 或从版本还原）
4. wb = mergeWorkbookSafe(data, patchFn)
 ├─ 若 countCells(workbookProps) > 0 → 深拷贝 workbookProps
 └─ 否则 → buildWorkbookFromFields(fields, sheetProps) // 禁止提交空 sheets
5. patchFn(wb) // 仅改 snapshot / 必要字段，勿删 sheets/dataTable
6. POST saveReportDevInfo（带当前 designKey + ebBusinessId）
7. GET getReportDevInfo 回读：
 - fields.length 不得小于保存前
 - 若用户未要求删除，fields.length === 0 → 视为事故，立即 rollbackReport
```

### 3.1 buildWorkbookFromFields 最低要求

从 `fields[]` 重建时，每个 field 须写入 `data.dataTable[x][y].style`（含 `cellType` 关键属性：父格、fieldKey、leftFilterField 等）。 
**禁止**只提交 `{ version, sheets: {} }` 或 `{ sheets: { Sheet1: { data: { dataTable: {} } } } }`。

**Const（强制）**：`style.cellType` 须为完整 `ConstCellType`，至少包含：

| 属性 | 说明 |
|------|------|
| `cellText` | 有展示文案时必填 |
| `leftX/leftY/topX/topY` | **禁止省略**（省略 → Java int 默认 0 → 伪自定义 A1） |
| `pcHreflink` / `openType` | 超链接 Const 必填；服务端**只认 workbook cellType**，不只认 `fields[]` 顶层 |

普通 Const 父格写 `-1`；超链接含 `{L4}` 时左父格指向依赖数据格。见 `report-self-check-guide.md` §2.2。

**定点修改**：用户只点一格时，语义上只改该格，但仍须整表 fields 原样写回 + 完整 workbook（见 `targeted-fix-guide.md`）。

### 3.2 快照配置 patch 示例

```javascript
const wb = mergeWorkbookSafe(dev.data, (wb) => {
 wb.snapshot = {
 enableSnapshot: true,
 cron: '0 0 0 * * ?',
 // 未指定名称时的平台默认
 snapshotName: `${reportName}-{date}-{time}`,
 params: JSON.stringify({ searchCondition: {} }),
 // 雪花 ID 必须字符串，禁止 Number(reportId)（超 MAX_SAFE_INTEGER 会截断，设计器空白）
 sheetId: String(reportId),
 // 更新已有配置时可带 id/jobId（同样用 String）；rollback 后建议 omit 让服务端重建调度
 };
 // 禁止 showLocation=0
 for (const sh of Object.values(wb.sheets || {})) {
 if (!sh.tag) sh.tag = {};
 if (!sh.tag.showLocation || sh.tag.showLocation === 0) sh.tag.showLocation = 2;
 }
});
```

### 3.3 保存后验证清单

| 检查项 | 通过标准 |
|--------|----------|
| `fields.length` | ≥ 保存前数量（允许只增不减，除非用户要求删格） |
| 关键单元格抽样 | 如 `(1,0)` 供应商等级 `(1,5)` 进货单编号 仍存在 |
| `snapshot.enableSnapshot` | 若本次任务为开快照，回读为 true |
| 设计器肉眼 | 提示用户 Ctrl+F5 强刷 |

---

## 四、事故恢复

| 现象 | 处理 |
|------|------|
| 设计器空白、`fields.length===0` | `GET rollbackReport?sheetId={版本snapshotId}&originSheetId={reportId}` |
| 无版本 | 查 `getVersionWithPage`；或本地 `inspect_*.json` / 脚本备份 |
| 快照误伤后 layout 已还原 | 快照需在设计器 **页面→快照设置** 重配，或 `set_snapshot_schedule.js`（已含保护） |

**版本 ID 来源**：`save_as_version.js --list-only` → `snapshotId` 列。

---

## 五、脚本与模块

| 文件 | 用途 |
|------|------|
| `e10-cli report fix（内部走安全局部保存）` | **安全合并 workbook**、保存前断言、保存后验证 |
| `e10-cli report snapshot set` | 定时快照（默认名 `{报表名}-{date}-{time}`；ID 字符串；依赖 safe_report_save） |
| `e10-cli report verify blank` | 防设计区空白门禁（sheetId/showLocation/scrollPage） |
| `e10-cli report restore` | 从版本 snapshotId 还原 layout |
| `references/designer-blank-prevention-guide.md` | **设计区空白禁令与定位** |
| `已由 CLI 取代` | `merge_workbook_safe` / `assert_layout_not_empty` / `verify_layout_preserved` |

---

## 六、Agent 硬约束（写入 SKILL 摘要）

1. **默认禁止**对已有报表提交空 workbook 或 0 fields 的 `saveReportDevInfo`。
2. 设置权限 / 查询 / 数据集筛选 / 菜单 / 复制 → **不得**调用 `saveReportDevInfo`。
3. 设置快照 → **必须** `mergeWorkbookSafe` + 保存前后 `fields.length` 校验。
4. 用户未说「删除」「清空」「重置布局」→ **任何步骤不得使 fields 归零**。
5. 保存前：`saveAsVersion` 或确认 `getVersionWithPage` 有可用版本。
6. 保存后：`getReportDevInfo` 回读失败 → **停止后续操作**，优先 `rollbackReport`。

---

## 七、源码依据

- `EdcReportDevDesignServiceImpl.saveReportDevInfoLast`：解压 workbook → `getFieldsFromWorkbook(wb)` → **全量** `saveFields` 覆盖 DB。
- `Workbook.snapshot`：`saveSnapshot(wb, reportId)` 仅在 workbook 含 snapshot 对象时执行；与 fields 同一保存事务。
- `workbookProps` 与 `fields` 分离存储；API 返回的 `workbookProps.sheets` 常不含 dataTable，**不能**作为唯一布局来源。
