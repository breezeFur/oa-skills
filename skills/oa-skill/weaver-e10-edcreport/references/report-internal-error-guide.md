# 报表内部错误 · 规则校验 / 修复 / 优化

> **现象**：接口或页面返回 `code=500` / `msg=报表内部错误`，或列表页整页失败。  
> **原则**：先用 CLI 校验定位，再定点修复；禁止反复对损坏壳盲 save。  
> **相关**：`report-baseinfo-defaults-guide.md` · `condition-format-guide.md` · `api-report-build-fast-path.md` · `safe-partial-save-guide.md`

---

## 一、常见根因速查

| 根因 | 典型表现 | 校验 | 修复 |
|------|----------|------|------|
| `nameLabelId` 含 `\r\n` 等控制符 | 应用报表列表 `list?groupid=-1` 整页 500 | `edc-report verify meta` | `baseInfo` 强制改写干净 `name` + `nameLabelId=-1` |
| `name` 含控制符 / 保存时 `name` 为空/`undefined` | `saveReportDevInfo` → 报表内部错误 | `validate base`；保存前从 `baseInfo` 取名 | multipart `name` 必填且干净 |
| `groupId=-1` 入库 | 与 list「全部」哨兵易混淆；部分租户 baseInfo 默认即 `-1` | `verify meta`（warning） | **勿擅自改**；保存时 `baseInfo.groupId` 原样回传；新建未指定用 `0` |
| workbook / designKey 错乱 | 偶发 500 或「数据不是最新」 | 回读 `designKey` | 用当次 `getReportDevInfo.designKey`；必要时新会话 |
| **空 workbook 落库**（提交 `sheets:{}`） | 保存控制台报错 / 布局被清空 | 保存前 rebuild 后 cells=0 且 fields>0 | 从 fields 重建完整 Sheet1 + spans 再 save；**禁止**把读到的空 sheets 原样回写 |
| **`(0,0)` 空 Const 幽灵格** | 异常格、父格误判、保存预检失败 | fields 含 x=0,y=0 且 text 空 | **删除该幽灵格**后再重建 workbook |
| **workbook sheet 含 `gridline` 键** | `saveReportDevInfo` → **500「报表内部错误」**（二分：存在即 500） | `edc-report validate gridline` | **删除** sheets.* 上的 `gridline`/`gridLine`/`__gridline`；网格线只写 page 层 `gridLine:0\|1` |

> **注意**：`getReportDevInfo` 回读时 `workbookProps.sheets` 常为 `{}`、`sheetCount=0`（与正常报表一致，布局在 `fields`）。判断「空 workbook」以**保存载荷**是否含 cell 为准，不要因回读 sheets 空就乱改 `groupId` 或清布局。
| 条件格式 `highlight:between` 等非法算子 | **不一定 500**，但规则**静默不生成** | `edc-report verify condition` | 改为 `highlight:interval` 等白名单 |

---

## 二、强制校验门禁（落库前 / 交付前）

```bash
# 1) base 元数据（防列表 500）
edc-report validate base --name "报表名" --name-label-id -1 --group-id 0
edc-report verify meta <reportId> [appId]

# 2) 网格线（防 workbook.gridline → 500「报表内部错误」）
edc-report validate gridline --file workbook-or-patch.json
edc-report verify gridline <reportId> [appId]

# 3) 条件格式（防静默丢规则 / 冲突）
edc-report validate condition --file rule.json
edc-report verify condition <reportId> [appId]

# 4) 综合
edc-report verify all <reportId> [appId]
```

| 时机 | 必须 |
|------|------|
| `baseInfo` / `saveReportDevInfo` **前** | `validate base`；**`validate gridline`（workbook 禁含 gridline 键）** |
| 写入条件格式 **前** | `validate condition`（白名单 + 冲突 warnings） |
| 交付 / 定点改完 | `verify meta` + `verify gridline` + `verify condition` 或 `verify all` |
| `validate`/`verify` exit≠0 | **禁止**跳过继续 save；有 warnings（冲突）须**提示用户确认** |

---

## 三、修复优化步骤

1. **定位**：`verify meta` → 看 name/nameLabelId/groupId；`verify condition` → 看非法 relation / 冲突。  
2. **元数据**：干净 `name` + `nameLabelId` 用 baseInfo 原值；**`groupId` 用 baseInfo 原值，禁止脚本硬编码**（改分组仅用户明确要求后 `removeReport`）。  
3. **布局保存**：`name`/`groupId`/`nameLabelId` 从 `baseInfo` 读取；带当前 `designKey`；`mergeWorkbookSafe` 防空表；**若 `sheets` 空但 fields 有内容 → 从 fields 重建 workbook（含 spans）**；**剔除 `(0,0)` 空 Const**；**剔除 sheets.* 上的 `gridline` 族键**。  
4. **条件格式**：`between`→`interval`；区间一条介于；重叠档位请用户确认后改 `interval`+`greater`。  
5. **壳已损坏**（空 fields + 持续 500）：`cleanup shells` / `lifecycle delete` 后按临时名重建（见 `failure-cleanup-and-nonblocking-guide.md`）。  
6. **列表页**：修完后用 `groupid=-1` 与真实分组各拉一次 list，确认不再 500。

---

## 四、与条件格式的关系

「报表内部错误」≠「条件格式不显示」。  
非法 `relation`（如 `between`）通常**不抛 500**，而是引擎跳过 → 设计器无规则。  
两者都纳入 **同一交付校验包**：`verify all` = 自检 + 绑定 + **条件格式** +（建议另跑）`verify meta`。

详见 `condition-format-guide.md` §CLI。

---

## 五、Agent 话术（冲突 / 不支持）

- 元数据失败：直接报 CLI errors，禁止编造默认值绕过。  
- 条件格式映射失败 / 冲突：按 `condition-format-guide.md` §四、§五 **请用户确认** 后再写入。
