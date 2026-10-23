# 设计器版本层指南

> 本文件为 `SKILL.md` 的子模块，在用户查看页面历史版本或还原版本时加载。覆盖：版本列表（version list）、版本还原（version revert）。
>
> **契约来源**：全部字段、参数、取值枚举来自 page/version/list 与 page/version/revert 两个 HTTP 接口规约。本指南几乎完全由接口契约推导。

---

## designer version list — 版本列表

**接口契约**：GET `/api/bs/ebuilder/designer/page/version/list`，请求头 `ETEAMSID`，需 `ObjType.PAGE`+`OptType.READONLY` 权限。

### Query 参数

| 参数名 | 类型 | 必填 | 默认值 | 取值范围/约束 | 说明 |
|--------|------|------|--------|----------------|------|
| pageId | Long | 是 | 无 | 正整数 | 目标页面 ID |
| pageNo | Integer | 否 | 1 | 正整数 | 页码 |
| pageSize | Integer | 否 | 10 | 1-200 | 每页条数 |
| creator | Long | 否 | 无 | 正整数 | 创建人 ID 筛选 |
| startTime | String | 否 | 无 | `yyyy-MM-dd` | 起始日期（系统时区，拼 `00:00:00`） |
| endTime | String | 否 | 无 | `yyyy-MM-dd` | 结束日期（系统时区，拼 `23:59:59`） |
| remark | String | 否 | 无 | - | 版本备注筛选 |
| funcType | Enum | 否 | `contains` | 见下表 | remark 匹配方式 |

### funcType 取值枚举（接口文档给全，可抄）

| funcType | 含义 |
|----------|------|
| `contains` | 包含（默认） |
| `uncontains` | 不包含 |
| `empty` | 为空 |
| `nempty` | 不为空 |
| `startWith` | 开头包含 |
| `endWith` | 结尾包含 |
| `eq` | 等于 |
| `neq` | 不等于 |

> `funcType` 是服务端 switch-case 白名单（防 SQL 注入），传白名单外值会被拒绝。

### 返回结构

`data` = `Pagination<PageVersionEntity>`：`{ count, pageNo, pageSize, hitCache, records[] }`，按 `version` **降序**排列，只返 `deleteType=0`。

**PageVersionEntity 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 版本记录 ID（**版本还原用的 versionId 取此 `id`，不是 `version` 号**） |
| version | Integer | 版本号，从 1 递增 |
| pageId | Long | 所属页面 ID |
| remark | String | 版本备注 |
| remarkLabelId | Long | 备注多语言标签 ID（`!= -1` 时按用户语言自动翻译 remark） |
| creator | Long | 创建人 ID |
| creatorName | String | 创建人姓名（来自员工缓存，**可能为 null**） |
| createTime | Long | 创建时间（Unix 毫秒） |
| updateTime | Long | 更新时间 |
| tenantKey | String | 租户标识 |
| deleteType | Integer | 删除标识（只返 `0`） |

> **坑**：
> - `creatorName` 来自员工缓存，员工已删除时为 `null`——别当异常。
> - `startTime` 系统自动拼 `00:00:00`、`endTime` 拼 `23:59:59`（系统时区）。
> - 默认保留最近 **20** 个版本（可通过 `weaver.ebuilder.designer.version-reserve-count` 配置）；无备注的旧版本会被自动清理。
> - 版本由 `designer save` 自动产生（每次 save 触发 `updatePageVersion` + 历史快照）。

---

## designer version revert — 版本还原

**接口契约**：POST `/api/bs/ebuilder/designer/page/version/revert`，Query `pageId`（必填）、`versionId`（必填，取 version list 返回的 `records[].id`）、`pageName`（可选，用于日志），请求头 `ETEAMSID`，需 `ObjType.PAGE`+`OptType.EDIT` 权限。返回 `data: true`。

### 校验

- `versionId` 所属页面必须与 `pageId` 一致（跨页 versionId 被拒）。

### 连锁操作

还原会整体替换 PC + MOBILE 两端布局，并执行：更新布局（updateLayouts）→ 重新生成源码（createOrUpdateEcode）→ 更新页面版本（updatePageVersion）→ 记录操作日志（`revertPage`）。

> **坑**：
> - **非幂等**：重复调同一 `versionId` 会产生重复连锁操作，多次还原。别循环重试。
> - **不可逆**：还原后未保存的当前编辑丢失。建议还原前先 `designer lock`。
> - 还原**本身不自动产生新版本快照**（之前的 save 才触发快照）；还原后须重新 `designer layout <pageId>` 刷新看新状态。
> - 兼容性：旧模块 id（`EB`→`EB_PAGE`、`PORTAL`→`PORTAL_PAGE`）与旧终端字段会被重映射。
>
> **⚠️ CLI 行为（非接口契约）**：`--yes` 非交互要求（非 TTY 自动化下不加 `--yes` 会"已取消"）属 CLI 行为，非接口契约——本骨架不展开。

---

## 版本管理速查

调用顺序：

```bash
e10-cli designer info <pageId>                              # 看 allowEdit / isLock
e10-cli designer version list <pageId> --size 20      # 列历史版本（--page/--size/--since/--until/--creator/--remark/--func，非 --page-no/--page-size）
# （可选）e10-cli designer lock <pageId>                    # 还原前锁定防并发
e10-cli designer version revert <pageId> <versionId> --yes  # 还原（versionId 取 list 返回的 id）
e10-cli designer layout <pageId>                           # 还原后刷新看新状态
e10-cli designer unlock <pageId>                           # 解锁
```

> **关键**：`versionId` 用 version list 返回的 `records[].id`（版本记录 ID），不是 `version` 号。

---

## 相关指南

- 布局层（info/layout/save/lock）→ `guide-designer.md`
- 命令速查 → `../common/ref-cli-commands.md`「designer」节
