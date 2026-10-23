# HRM 矩阵指南（条件矩阵 / 部门矩阵 / 分部矩阵）

> 矩阵 = 「条件维度（行）→ 值维度（列）」的映射查询表。例如：部门 + 费用类型 → 审批人。用于流程中的矩阵对应操作者类型。

## 命令参考

### 矩阵管理

| 命令 | 说明 |
|------|------|
| `e10-cli matrix create <name>` | 新建矩阵。`--type 0=分部/1=部门/2=自定义` `--desc` `--org-id` |
| `e10-cli matrix update <id>` | 更新矩阵。`--name` `--desc` `--type` |
| `e10-cli matrix list` | 查询矩阵列表。`--name` `--enable-status` `--org-id`。非 JSON 输出会标出「行随组织同步 / 行手工维护」「字段只读」 |
| `e10-cli matrix config <id>` | 查看矩阵配置（条件字段 + 值字段） |
| `e10-cli matrix config-edit <id>` | 编辑配置。`--value`（配合可选 `--condition`）或 `--config` 一次性提交。**`--condition` 可省略**，省略则沿用现有条件列 |
| `e10-cli matrix enable <id>` | 启用矩阵 |
| `e10-cli matrix disable <id>` | 停用矩阵 |
| `e10-cli matrix delete <ids...>` | 删除矩阵。**矩阵里有数据行时平台会拒绝删除**（报"存在不能删除的矩阵"且不指出是哪个）——先 `matrix data delete <id> <rowIds...>` 清空数据行再删；批量删除时只要有**一条**不可删，整批都失败 |

### 矩阵数据维护

| 命令 | 说明 |
|------|------|
| `e10-cli matrix data list <matrixId>` | 分页查询矩阵数据行。`--condition` `--value` 过滤 |
| `e10-cli matrix data save <matrixId> --rows @file` | 保存数据行（新增/修改）。简写: `[{rowId?, "字段configId":["实体ID"]}]` —— 带 `rowId` 为改该行，不带为新增 |
| `e10-cli matrix data delete <matrixId> <ids...>` | 删除数据行 |
| `e10-cli matrix data template <matrixId>` | 下载导入模板（Excel） |
| `e10-cli matrix data import <matrixId> <file>` | 从 Excel 导入。`--mode add/cover` |

---

## 典型工作流

```bash
# 1. 创建矩阵（新建即启用；分权租户的所属机构自动取当前机构）
e10-cli matrix create "审批人映射表" --type 2 --desc "部门→审批人"

# 2. 查 ID
e10-cli matrix list --name "审批人"

# 3. 配字段（条件=部门，值=审批人）—— 直接可用，不需要先开设计器
e10-cli matrix config-edit <matrixId> \
  --condition '[{"type":"department","name":"所属部门"}]' \
  --value '[{"type":"resource","name":"审批人","singleType":1}]'

# 4. 启用
e10-cli matrix enable <matrixId>

# 5. 填数据
echo '[{"<条件configId>":["<部门ID>"],"<值configId>":["<人员ID>"]}]' > rows.json
e10-cli matrix data save <matrixId> --rows @rows.json

# 6. 查数据
e10-cli matrix data list <matrixId>

# 7. 在流程中使用矩阵
e10-cli workflow set-operator <wf> <nodeId> --type matrix \
  --matrix-id <matrixId> --value-config-id <值configId> \
  --matrix-rule "<条件configId>:1:1:1"
```

部门矩阵少一步 —— 条件列是平台建矩阵时自动给的，只配值列：

```bash
# 1. 建（--sync-depart = 界面上那个「从组织架构中同步部门」；行随组织同步，不可增删）
e10-cli matrix create "部门负责人" --type 1 --sync-depart --desc "部门→负责人"

# 2. 只配值列，--condition 省略（CLI 会沿用平台建好的「部门」条件列）
e10-cli matrix config-edit <matrixId> \
  --value '[{"type":"resource","name":"部门负责人","singleType":0}]'

# 3. 看行 —— 同步型矩阵的行是组织架构带来的，行 id 就是部门 id
e10-cli matrix data list <matrixId>

# 4. 给某一行填值（带 rowId 才是改那一行，不带就是新增一行）
echo '[{"rowId":"<部门id>","<值configId>":["<人员ID>"]}]' > rows.json
e10-cli matrix data save <matrixId> --rows @rows.json
```

---

## 行从哪来、字段能不能改：看 `syncType` 和 `permList`

`matrix list --json` 每条记录带几个标记位。**不要拿 `sysType` 当判据** —— 它只说明是不是平台内置的，不决定能力：

| 字段 | 取值 | 含义 |
|---|---|---|
| `type` | `0` / `1` / `2` | `0`=分部矩阵、`1`=部门矩阵、`2`=自定义矩阵 |
| `syncType` | `1` / `0` | **行从哪来**。`1`=数据行随组织架构同步（**行不可增删，行 id 就是部门/分部 id**）；`0`=行手工维护（行 id 是平台发号的雪花） |
| `permList` | 数组 | **含 `FIELD` 才能改字段配置**；不含就是字段只读（平台内置矩阵是这种） |
| `sysType` | `1` / `0` | 是否平台内置。只影响名字语义，**不影响能做什么** |

`matrix list` 的非 JSON 输出会直接把这两条标出来：`行随组织同步 / 行手工维护`、`字段只读`。

同一租户里四个矩阵的对照，四个象限都出现过：

| 矩阵 | type | sysType | syncType | permList 有 `FIELD` | 结果 |
|---|---|---|---|---|---|
| 平台内置的部门矩阵 | 1 | 1 | 1 | 否 | 行随组织同步、字段只读 |
| 部门负责人矩阵 | 1 | 0 | 0 | 是 | 行手工维护、字段可改 |
| 自建并勾了「同步部门」 | 1 | 0 | 1 | 是 | 行随组织同步、字段可改 |
| 自建未勾同步 | 1 | 0 | 0 | 是 | 行手工维护、字段可改 |

> **`type` 与 `syncType` 互相独立**：`type=1` 的部门矩阵既可以是同步的、也可以是手工维护的；创建时用 `--sync-depart` / `--sync-subcompany` 决定，事后也能用 `matrix update --sync-depart` 改。
>
> 不管哪种，**在流程里的用法完全一样**（都是 `workflow set-operator --type matrix`）。

## 部门矩阵 / 分部矩阵：条件列是平台给的

建部门矩阵（`matrix create <name> --type 1 --sync-depart`）时，平台会**自动把条件列建好**：

```json
"conditionConfigList": [
  { "id": "<矩阵id + 1>", "name": "部门", "type": "department", "singleType": 1 }
],
"valueConfigList": []          ← 这才是你要配的
```

所以配列时**只给值列就行**，`--condition` 省略掉：

```bash
e10-cli matrix config-edit <matrixId> \
  --value '[{"type":"resource","name":"部门负责人","singleType":0}]'
```

CLI 会把现有条件列原样带上（会打印一行 `ℹ 未指定条件列，已沿用现有的: 部门`）。

> **别手写条件列。** 写一个不带 `id` 的 `{"type":"department","name":"部门"}` 进去，CLI 会当成新列去 `addField` 取号，结果矩阵里多出一条一模一样的「部门」列。
>
> 可用类型用 `GET /api/bs/hrm/matrix2/config/typeList?id=<matrixId>&matrixType=<0|1|2>` 查：部门矩阵返回 `conditionTypeList:[department]` / `valueTypeList:[resource]`。

**所属机构与分权**：矩阵强制校验"所属机构"，而落到哪个字段由**分权状态**决定——分权开启时平台读 `belong_org_id`（归属机构），关闭时读 `targetId`。CLI 建矩阵前会自动查 `check-detach` 判断并选对字段，分权租户还会直接用返回的当前机构兜底，所以 `matrix create` 通常不用手写机构；只有"非分权租户"或"归属机构与目标机构必须不同"时才需要 `--org-id` / `--target-id`。

**列表的状态过滤**：`matrix list` 走管理端点 `matrix2/list`，能看到**停用的矩阵**并显示真实状态；`--name`（模糊）、`--enable-status`、`--org-id` 都是服务端过滤。

## 完整配置：条件列 → 人员列 → 数据映射 → 运行时读回

```bash
# ① 建矩阵（自定义矩阵。系统矩阵是平台内置的，用 matrix list 找现成的）
#    新建即为「启用」状态，不需要再 enable；要停用才跑 matrix disable
#    所属机构：分权租户自动取当前机构，非分权租户用 --org-id 显式指定（不加会有"所属机构不能为空"）
e10-cli matrix create "部门审批人" --type 2 --desc "部门→审批人"

# ② 配列：条件列 + 值列。值列 type=resource 就是"人员列"；singleType 0=多选 1=单选
e10-cli matrix config-edit <matrixId> \
  --condition '[{"type":"department","name":"所属部门"}]' \
  --value '[{"type":"resource","name":"审批人","singleType":1}]'

# ③ 取各列 configId（数据映射的键就是它），再填数据行
e10-cli matrix config <matrixId>            # → conditionConfigList[].id / valueConfigList[].id
e10-cli matrix data save <matrixId> --rows @rows.json
e10-cli matrix data list <matrixId>         # 回读数据行

# ④ 启用并挂到流程节点
e10-cli matrix enable <matrixId>
e10-cli workflow set-operator <wf> <nodeId> --type matrix \
  --matrix-id <matrixId> --value-config-id <值列configId> \
  --matrix-rule "<条件列configId>:1:1:1"

# ⑤ 运行时读回：确认条件列/值列是否就是流程实际在读的那一组
e10-cli matrix config <matrixId>
```

> **矩阵类型不用手填**：`--type matrix` 的 `sourceType` / 条件列中文名由 CLI 自动读 `GET /api/bs/hrm/matrix2/config?id=<matrixId>` 解析——`conditionConfigList[].type` 是 `department` 即部门矩阵、`subcompany` 即分部矩阵。条件列不在目标矩阵里时会直接报错并列出可选列，不会静默挂错。
>
> 排查"取不到人"时按这个顺序看：`matrix config`（列对不对）→ `matrix data list`（行有没有）→ 流程节点的矩阵规则是否引用了正确的 `条件configId`。

## 字段类型枚举

| 中文 | API 值 |
|------|--------|
| 人员 | `resource` |
| 部门 | `department` |
| 分部 | `subcompany` |
| 岗位 | `position` |
| 客户 | `customer` |
| 项目 | `project` |
| 数据源 | `datasource` |

## config-edit 参数

```json
{
  "id": "<矩阵ID>",
  "conditionConfigList": [
    { "id": "<现有条件列id>", "type": "department", "name": "显示名", "sort": 1 }
  ],
  "valueConfigList": [
    { "id": "<现有值列id>", "type": "resource", "name": "显示名", "singleType": 1, "sort": 1 },
    { "type": "resource", "name": "新加的列", "singleType": 0, "sort": 2 }
  ],
  "conditionDelList": [],
  "valueDelList": []
}
```

- `singleType`: 0=多选, 1=单选。值字段必传，条件字段可省（省了沿用现有的）。条件列在平台上**本身是必填的**，空着下发会被拒（「请至少维护一个条件字段」）。
- **已有的列要带 `id`**（从 `matrix config` 拿）；不带 `id` 的会被当成新列去 `addField` 取号，**等于多建一列**。不带 id 但与现有列重名时 CLI 会告警。
- **列 id 必须属于该矩阵**。传了别的矩阵的列 id，平台只回一句「系统内部错误」（NPE），CLI 会抢先报错并点名是哪一列。
- ⚠ **保存是「按 id 合并」，不是整表替换**：没传的列**不会**被删（删列要走 `--value-del`）。所以「加一列」只传那一列就够了，不必把现有列全列一遍。
- 保存后回读比对提交的列（在不在、名字对不对），平台回 200 但没按提交落库会直接报错。

## data save 简写格式

```json
[
  {"<条件configId>": ["<实体ID>"], "<值configId>": ["<实体ID>"]},
  {"rowId": "<行id>", "<值configId>": ["<实体ID>"]}
]
```

- 不带 `rowId` = 新增一行；带 `rowId`（或写作 `id`）= 改那一行。行 id 用 `matrix data list <matrixId>` 拿。
- **改行只给要改的列就行**：平台是整行覆盖，CLI 会先读回该行、把没给的列补上再发。
- 键不是该矩阵的列时直接报错并列出可用列，不会静默发出去。

CLI 自动查 config 判断 `conditionAble` 标记并展开为完整格式；改过的行保存后会回读比对，平台回 200 但没按提交落库会直接报错。

