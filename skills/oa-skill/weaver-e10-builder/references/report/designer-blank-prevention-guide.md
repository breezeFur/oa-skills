# 设计器空白防护（强制 · 不允许发生）

> **事故（已验证 · 报表 `1312790168931180545`）**：设计区中间空白，但 `fields.length` 仍 > 0 —— **不是删格**，是配置毒化导致前端加载崩溃/空白。
> **硬约束**：下列写入错误 **一律禁止**；落库前必须校验；发现设计区空白优先按本指南定位，禁止盲目整表覆盖。

---

## 一、已验证会导致「设计区空白」的写入（禁令）

| # | 错误写法 | 后果 | 正确做法 |
|---|----------|------|----------|
| **1** | `snapshot.sheetId = Number(reportId)`（及 `id`/`jobId` 用 Number） | 雪花 ID 超 `MAX_SAFE_INTEGER` 截断（`…0545`→`…0500`），快照 sheetId 错位 → **设计区空白** | **一律 `String(reportId)`**；禁止对雪花 ID 做 `Number()` |
| **2** | `showLocation: 0`（或从 sheetProps 原样回传 0） | 前端 truthy 判断异常，布局空白/错乱 | 仅允许 **`1`（居左）或 `2`（居中）**；读到 0 必须改成 2（或用户点名居左则 1） |
| **3** | `scrollPage: "1"` 且 `scrollContentField` 为空 | 滑动分页表单项 required，配置残缺 → 设计器异常 | 开滑动分页必须带有效 `scrollContentField`；否则 **`scrollPage: "0"`** |
| **4** | 空 workbook / 空 dataTable 提交 `saveReportDevInfo` | fields 被全量清空 → 真空白 | `mergeWorkbookSafe` / 从 fields 重建；见 `safe-partial-save-guide.md` |
| **5** | Formula `cellText` 带前导 `=` / 错误 countType | 设计器整页空白 | 见 `formula-cell-api-guide.md` |

**禁止**：为「开快照 / 改分页 / 改打印」而提交会触发上表任一错误的 payload。

---

## 二、定时快照命名与 ID 契约

### 2.1 默认快照名称（强制）

用户**未指定**快照名称时，默认：

```text
{当前报表名}-{date}-{time}
```

示例：报表名 `测试报表-chl` → `测试报表-chl-{date}-{time}`

| 占位符 | 含义 |
|--------|------|
| `{date}` | 生成日（平台解析） |
| `{time}` | 生成时分（平台解析） |

**禁止**再默认写成 `{year}-{month}-{day}`（旧习惯）。用户显式传入 `--snapshot-name` 时才用自定义名。

### 2.2 sheetId / id / jobId

```javascript
{
 enableSnapshot: true,
 cron: '0 0/1 * * * ?', // 例：每分钟
 snapshotName: `${reportName}-{date}-{time}`,
 params: JSON.stringify({ searchCondition: {} }),
 sheetId: String(reportId), // 禁止 Number()
 // id / jobId 若回传：同样 String(...)
}
```

落库后门禁：

- `enableSnapshot === true`（若本次为开启）
- `String(snapshot.sheetId) === String(reportId)`（在**未经过 JSON number 污染的原始串**上比；Node `JSON.parse` 大整数可能已截断，**写入侧必须保证字符串**）
- `fields.length` 不下降

CLI：`e10-cli report snapshot set --report-id <id> [--cron "..."] [--snapshot-name "..."]`

---

## 三、其它本会话沉淀（写入时一并遵守）

| 主题 | 规则 | 文档 / CLI |
|------|------|------------|
| 数字格式回显 | formatter **目录全等** + `formatterType` 成对；货币=`huobi`+全角￥格式串 | `cell-config-echo-guide.md`；`validate format` |
| 日期分组回显 | `groupType=year/yearmonth/...` 写入 fields + cellType | 同上 |
| 字体字号 | 不支持则**提示**并用默认字号继续，**不卡住** | 同上 |
| 禁整表刷样式/边框 | 用户要整表设样式 → **提示不支持**，须给区域 | 同上 + scope |
| `showLocation` | 禁止 0 | `layout-showlocation-freeze-guide.md` |
| **网格线** | workbook **禁止** `gridline` 键（存在→500）；page `gridLine=0` | §4.6.1；`validate gridline` |
| 滑动分页 | `scrollPage=1` 须有内容字段；每页条数 `pageRowCount` | `allPageSetting` |
| 打印眉头页码 | Spread `headerCenter: "&[Page]"`；重复行 0-based | sheet `printInfo` |
| 局部保存 | 快照必须 `mergeWorkbookSafe`；禁空 workbook | `safe-partial-save-guide.md` |

---

## 四、保存前 Agent / CLI 检查清单（防空白）

任意 `saveReportDevInfo`（含快照）前：

- [ ] `fields.length > 0`（已有报表）
- [ ] workbook 重建后 `countCells > 0`
- [ ] `showLocation` ∈ `{1, 2}`，若为 0 → 改为 2
- [ ] **网格线**：workbook sheets **无** `gridline`/`gridLine`/`__gridline`；page 层默认 `gridLine=0` → `validate gridline`
- [ ] 若写 snapshot：`sheetId`/`id`/`jobId` 均为**字符串**；`snapshotName` 未指定则用 `{报表名}-{date}-{time}`
- [ ] 若 `scrollPage==="1"` → `scrollContentField` 非空，否则改 `"0"`
- [ ] 保存后 `fields.length` 不降；提示用户 Ctrl+F5

CLI 自检：`e10-cli report verify blank <reportId>`（含网格线联动）；`e10-cli report validate gridline --inline '...'`

---

## 五、设计区已空白时的处置

1. **先** `getReportDevInfo`：若 `fields.length > 0` → 多半是配置毒化（快照 ID / showLocation / scrollPage），**不是**删光了
2. 关闭或修复坏快照（`enableSnapshot:false` 或重写 **String** sheetId）
3. 纠正 `showLocation`、关闭残缺滑动分页
4. 从 fields 安全重建 workbook 再存
5. 仅当 `fields.length===0` 才走 `rollbackReport`（版本 snapshotId）

---

## 六、与 Skill 映射

- SKILL 硬规则 **§L**
- `safe-partial-save-guide.md` §3.2
- `e10-cli report -cli.md` §一
- 脚本：`set_snapshot_schedule.js`、`validate_designer_blank_guard.js`
