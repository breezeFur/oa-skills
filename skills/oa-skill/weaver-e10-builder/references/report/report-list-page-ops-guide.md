# 报表列表页操作（分组 / 视图 / 权限矩阵 / 移动 / 转移）

> **页面**：`/sp/ebdapp/detail/{appId}/report`
> **源码**：`MenuGroupController` · `EdcReportDevBaseController.removeReport|transferReport` · `EdcDataPermissionController` · 前端 `localStorage edc_report_view_type`
> **CLI**：`e10-cli report group|lifecycle move|lifecycle transfer|app search|scope matrix|policy list-page`
> **鉴权**：e10-login 三项头（`api-auth-headers.md`）

---

## 〇、能力总表

| # | UI | 是否服务端 API | Skill/CLI |
|---|-----|----------------|-----------|
| 1 | 新建/删除分组（分组设置） | ✅ `group/list` + `group/save` | ✅ |
| 2 | 视图切换卡片/列表 + 快速排序 | ❌ 纯前端 localStorage / 内存排序 | 文档化（无服务端写） |
| 3 | 报表权限 · 矩阵添加/删除 | ✅ `matrix/list` + `savePermissions.viewMatrixRight` / `matrix/save` | ✅（补齐 CLI） |
| 4 | 移动到其他分组 | ✅ `removeReport`（改 `group_id`） | ✅；无自建分组则不可选 |
| 5 | 转移到其他应用 | ✅ `transferReport` + `ebuilder/app/list` | ✅；重名须用户确认 |

---

## 一、分组：新建 / 删除（强制）

### 1.1 接口

| 动作 | 方法 | 路径 | 参数 |
|------|------|------|------|
| 列表 | GET | `/api/bs/edc/report/group/list` | `appid` · `groupType`（后台默认 **0**） |
| 保存 | POST | `/api/bs/edc/report/group/save` | multipart/form：`appid` · `groupType` · **`groups`=JSON 字符串** |

**无单独 delete API**。删除 = 从 `groups` 数组中**去掉**该分组后全量 `save`（替换语义）。

侧栏哨兵（**不是**可保存/可移动目标）：

| id | 含义 |
|----|------|
| `-1` | 全部 |
| `-2` | 我创建 |
| `-3` | 未分组（部分租户） |

`save` 前须过滤掉 `id === "-1"` 等哨兵；只提交用户自建分组。

### 1.2 新建流程

1. `group list` 取当前自建分组
2. 追加一项：`{ "id": "", "name": "<新名称>", "showOrder": <max+1>, "nameLabelId": "-1" }`（字段以 list 回包为准透传）
3. `group save`
4. 再 list 确认拿到真实 id

```bash
e10-cli report group list --app-id <appId>
e10-cli report group add --app-id <appId> --name "销售组"
e10-cli report group delete --app-id <appId> --group-id <id>
```

### 1.3 禁令

- 禁止把 `-1/-2/-3` 当自建分组写入 save
- 禁止未读 list 就臆造整表 groups（丢分组）
- 删除分组前若组内有报表，先 `move` 走或告知用户（产品侧行为以页面为准）

---

## 二、视图切换与快速排序（无服务端写）

| 能力 | 机制 | 说明 |
|------|------|------|
| 卡片视图 | `localStorage.edc_report_view_type = "grid"` | 默认 |
| 列表视图 | `localStorage.edc_report_view_type = "table"` | 列表数据另调 `GET /api/bs/edc/report/tableView` |
| 快速排序 | 前端内存 `sortBy` / `sortType` | 字段常见：`UpdateTime` / `CreateTime` / `Name` / `Creator`；**不落库** |

Agent：

- **不要**发明「保存视图偏好」的报表 API
- 用户若要「列表视图数据」：可调 `tableView?appId=&groupId=&filterStr=&pageNo=&pageSize=`
- 卡片列表仍用 `GET /api/bs/edc/report/list?appid=&groupid=&objId=`

```bash
e10-cli report --help-page # 打印本节政策
```

---

## 三、报表权限 · 矩阵添加 / 删除

完整对象类型与通用 Tab 见 **`report-permission-guide.md`**。本节只强调矩阵 CRUD。

### 3.1 读

```http
POST /api/bs/edc/report/permission/matrix/list
{ "target": "<reportId>", "type": "1" } # 使用范围矩阵
{ "target": "<reportId>", "type": "-1" } # 禁用范围矩阵
```

### 3.2 添加

| 范围 | 写接口 |
|------|--------|
| **使用范围 · 矩阵** | `POST .../permission/table/savePermissions`，带完整 `viewRight`/`disableRight`/`viewMatrixRight`（全量）；服务端先把使用矩阵 `deleteType=1` 再插入新行 |
| **禁用范围 · 矩阵** | **单独** `POST .../permission/matrix/save`，`rightsType:"-1"`；**不要**只靠 savePermissions |

矩阵行字段：`selectedType` · `dataId` · `matrixConditionData` · `matrixValueRelation` · `targetId` · `rightsType` · `rightsName`
**条件/取值字段 JSON 必须以设计器 Network 实际请求为准**，禁止臆造键名。

### 3.3 删除

| 范围 | 做法 |
|------|------|
| 使用矩阵 | `matrix/list` → 去掉目标行 → `savePermissions` 提交剩余 `viewMatrixRight`（可空数组=全清使用矩阵） |
| 禁用矩阵 | `matrix/list type=-1` → 对目标行 `matrix/save` 且 **`deleteType: 1`**（或只保留要留下的行再 save；以实际请求为准） |

```bash
e10-cli report scope matrix list --report-id <id> --app-id <appId> [--type 1|-1]
e10-cli report scope matrix save --report-id <id> --app-id <appId> --file matrix-row.json [--type 1|-1]
e10-cli report scope matrix delete --report-id <id> --app-id <appId> --matrix-id <id> [--type 1|-1]
```

---

## 四、移动到其他分组（强制规则）

### 4.1 接口

```http
POST /api/bs/edc/report/removeReport
Content-Type: multipart/form-data
reportId=<id>&groupId=<目标分组ID>
```

> 名称是历史遗留：**不是删除报表**，只改 `edc_report_dev.group_id`。

### 4.2 可选目标规则（产品硬约束）

1. 先 `GET group/list?appid=&groupType=0`
2. **可移动目标 = 用户自己创建的分组**（真实雪花/数字 id）
3. **排除** 哨兵 `-1/-2/-3`
4. 若过滤后 **列表为空** → **无可选移动位置**，Agent 须提示用户先「分组设置 → 添加分组」，**禁止**瞎传 groupId

```bash
e10-cli report lifecycle move --app-id <appId> --report-id <id> --group-id <gid>
# 无自建分组时 exit≠0，message 提示先建分组
```

---

## 五、转移到其他应用（强制规则）

### 5.1 转移接口

```http
POST /api/bs/edc/report/transferReport
reportIds=<id>[&reportIds=<id2>]&appId=<目标应用ID>
```

服务端副作用：目标应用下报表 **`group_id = -1`**（未分组）；同步版本与菜单 remote appId。

### 5.2 应用选择框（UI：选择 e-Builder 应用）

| 步骤 | API / 规则 |
|------|------------|
| 检索应用 | `GET /api/bs/ebuilder/app/list?name={关键字}&pageNo=1&pageSize=20`（可翻页） |
| 范围 | **当前用户有权限且启用**的 EB 应用（以 list 回包 `enable`/`status` 等字段过滤；禁用应用勿作目标） |
| 重名 | **同名多条 → 必须 AskUserQuestion** 让用户确认到底是哪一个 `appId`，禁止自动挑第一条 |
| 可选校验 | `GET /api/bs/edc/report/appRight?appId={目标}` 确认可操作 |

```bash
e10-cli report app-search --name "办公" [--page 1] [--size 20]
e10-cli report lifecycle transfer --report-id <id> --app-id <目标appId>
e10-cli report lifecycle transfer --report-id <id> --app-name "xxx"
# --app-name 命中多条 → 输出 candidates，要求 --confirm-app-id
```

---

## 六、Agent 检查清单

- [ ] 分组增删走 `group/save` 全量，未丢其它分组
- [ ] 未把视图/快速排序当成服务端配置去「保存」
- [ ] 矩阵：使用走 savePermissions / 禁用走 matrix/save；删除未臆造 DSL
- [ ] 移动前 list 自建分组；空则提示先建组
- [ ] 转移前 app/list；重名用户确认；目标为启用且有权限应用

---

## 关联

- `report-lifecycle-api-guide.md` — 列表页总览
- `report-permission-guide.md` — 权限对象类型与通用 Tab
- `report-create-modes-guide.md` — 新建报表三模式
- `api-auth-headers.md` — 鉴权
