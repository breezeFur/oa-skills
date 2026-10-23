# 雪花 ID 精度安全指南

> **适用场景**：复制报表、权限绑定、添加到菜单、删除/回收站等一切涉及 `reportId` / `pageId` 的 API 链路。 
> **事故案例**：`copySheet` 返回 `1311221384923619328`，Node `JSON.parse` 后变为 `1311221384923619300`（末位差 28），导致权限与菜单绑到不存在的 ID。

---

## 一、根因

| 项 | 值 |
|----|-----|
| E10 ID 类型 | 64 位雪花 ID（19 位十进制） |
| JS 安全整数上限 | `Number.MAX_SAFE_INTEGER = 9007199254740991`（16 位） |
| 后果 | `JSON.parse('{"id":1311221384923619328}')` → `id === 1311221384923619300` |

**Python 注意**：`json.loads` 大整数默认可保留，但 `int(report_id)` 传给部分接口仍会溢出；**全程用 `str` 承载 ID**。

---

## 二、强制规则（Agent）

1. **禁止**对含 `id` / `reportId` / `pageId` 的 API 响应裸用 `JSON.parse` / `json.loads` 后直接当数字用。
2. **必须**使用 Skill 工具：
 - Node：`内置雪花安全解析` → `parseJsonSnowflakeSafe` / `extractIdFromRaw`
 - Python：`内置雪花安全解析` → 同名函数
3. **copySheet 后取新 ID 双保险**：
 ```javascript
 const newId = extractIdFromRaw(copyRes.raw) || stringifyId(copyRes.json.data?.id);
 ```
 ```python
 new_id = extract_id_from_raw(cli.last_raw) or str((result.get("data") or {}).get("id", ""))
 ```
4. **后续 API 一律字符串**：`pageId`、`sourceId`、`reportId`、`sheetId` 参数禁止 `Number(id)`。
5. **交付给用户/手册的 reportId** 必须来自 raw 提取或 snowflake 安全解析，禁止直接打印 `json.data.id`（未安全解析时）。

---

## 三、安全解析原理

仅对**已知 ID 字段名**的 ≥16 位数字加引号后再 `JSON.parse`，**不**对嵌套 JSON 字符串内数字做全局替换（避免破坏 `tabs` 等字段）。

```javascript
// 内置雪花安全解析
parseJsonSnowflakeSafe(rawText)
extractIdFromRaw(rawText, ['id', 'reportId', 'pageId'])
```

```python
# 内置雪花安全解析
parse_json_snowflake_safe(raw_text)
extract_id_from_raw(raw_text, keys=("id", "reportId", "pageId"))
```

---

## 四、受影响 API（必用安全 ID）

| 操作 | API | ID 字段 |
|------|-----|---------|
| 复制 | `GET copySheet?sheetId=` | 响应 `data.id` |
| 权限 | `POST savePermissions` | body key、`sourceId` |
| 添加到菜单 | `POST savePublishMenu` | `page.pageId` |
| 删除 | `GET deleteReport?id=` | query `id` |
| 设计器 | `GET baseInfo?id=` | query `id` |
| 列表 | `GET report/list` | 每项 `id` |

---

## 五、验证清单

- [ ] copySheet 后 `newReportId` 与设计器 URL 中 ID 一致（末四位无漂移）
- [ ] `baseInfo?id={newId}` 能返回报表名称
- [ ] 菜单 `allMenus` 中 `pageId` 与报表 ID 字符串完全一致
- [ ] 权限 `getQueryItem` / `permission/table/list/new` 的 `sourceId` 正确

---

## 六、相关文档

| 文件 | 用途 |
|------|------|
| `report-lifecycle-api-guide.md` | 复制 / 权限 / 添加到菜单 API |
| `已由 CLI 取代` | Python 客户端（已接入 snowflake 解析） |
| `内置雪花安全解析` / `.py` | 跨语言安全解析 |
