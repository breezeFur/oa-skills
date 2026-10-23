# 多物理表（一个表单的字段分散到多张物理表）

设计器里「表单 → 字段管理」有三个页签：**主表 | 明细表 | 其他**。本文说的是**「其他」** —— 同一个表单的字段分散在多张**物理表**上。

## 什么时候用

**字段数过多时的容量兜底**（单表字段超过 100 个左右）。正常表单用不到，属于偶尔一用的结构级能力。业务上要「一行对多行」请用**明细表**，那是另一回事（见 `guide-form-sub-detail.md`）。

## ⚠ 和「明细表」是两根轴，别混

| | 明细表 | **物理表（本文）** |
|---|---|---|
| 建表命令 | `form add-detail-table` | **`form add-physical-table`** |
| 加字段命令 | `form add-field --sub-form-id` | **`form add-physical-field`** |
| 建表端点 | `saveSubForm` | **`saveFormTable`** |
| 标志 | `isSubForm: true` | **`isSubForm: false`** |
| `tableType` | `MAIN` | **`SUBSIDIARY`** |
| 布局里 | `DetailTable` 组件 | 无（不自动进布局，见下） |
| 语义 | 一对多业务建模 | 一个表单自己的字段拆到多张表 |

## 命令

```shell
# 1) 列出表单的全部物理表（含主表）—— 忘掉 formTableId 时就用它
e10-cli form physical-table list <objId> <appId>

# 2) 建一张附属物理表 —— 输出 formTableId，后面都要用它
e10-cli form add-physical-table <objId> <appId> \
  --name 物理表A \
  --table-name uf_ryxxb_6_1

# 3) 往那张表里加字段（任意类型，能力同 form add-field）
e10-cli form add-physical-field <objId> <appId> <formTableId> <字段名> <类型> [标题] [选项]

# 4) 改名
e10-cli form rename-physical-table <objId> <appId> <formTableId> \
  --name 新名字 --table-name uf_ryxxb_6_1

# 5) 删除（可一次删多张；表里的字段一并删除，不可逆）
e10-cli form delete-physical-table <objId> <appId> <formTableId...>
```

`add-physical-field` 的选项与 `form add-field` 同名同义（`--precision` / `--format` / `--default` / `--data-key` / `--column-name` / `--multiple` / `--option-template` / `--browser-type` / `--sform-id` …）—— 两者**共用同一份字段构造器**，所以字段形状是同一套，不存在「这个命令能建那个命令不能建」的差异。

| 参数 | 说明 |
|---|---|
| `--name <名>` | 物理表**显示名**，设计器里那排 chip 上的字 |
| `--table-name <名>` | **数据库表名**（如 `uf_ryxxb_6_1`）。⚠ 平台的建议命名规则未抓到报文，**必填**；改名时也要原样回传 |

## 表 id 从哪来

建表输出里就带着：

```
物理表已建: 物理表A  formTableId=1323895867900731392  tableName=uf_ryxxb_6_1
```

事后想找回，用 `form physical-table list`（走 `getFormAGroupList`，就是设计器那排 chip 的数据源）：

```
$ e10-cli form physical-table list 1323898521989193728 1323897873591762945
表单 1323898521989193728 共 3 张物理表:
  多物理表测试表单  [主表]  formTableId=1323898521989193731  库表=uf_dwlbcsbd_5766  字段2
  表1  [附属]  formTableId=1323898595055067136  库表=uf_dwlbcs_t1  字段3
  表2  [附属]  formTableId=1323898612300947456  库表=uf_dwlbcs_t2  字段3
```

⚠ 注意这只列**物理表**。`form detail-table list`（走 `querySubForms`）是另一回事，只列**明细表**。

字段**归属**也随时可读：`form read <objId> --app-id <appId>` 每个字段后面会带 `· 物理表: 表1`。

> 读 `getFormAGroupList` 时别碰那条记录里的 `id` 键 —— 它是 **formId**，`formTableId` 才是表 id。这个子系统里 `id` 反复是这个陷阱。

## ⚠ `add-physical-field` **不碰布局**

字段建在这张物理表上，但**不会自动进表单布局**——它是否需要在布局里出现、怎么放，尚未抓到报文。别默认它已经挂在表单上了；要不要进布局请在设计器里确认。

（`form add-field` 会做布局插入，是因为它落在主表/明细表这些**本来就在布局里**的落点上。）

## 报文契约

### 建表 / 改名 —— 同一个端点，带不带 `id` 决定是哪种

```
POST /api/ebuilder/form/form/field/manage/saveFormTable?apid=<appId>
header ebbusinessid: <formId>
```

```json
{"module":"ebuilderform",
 "formTable":{"id":"<表id：改名时带，新建时不带>",
              "name":"物理表A",
              "tableName":"uf_ryxxb_6_1",
              "tableType":"SUBSIDIARY",
              "form":{"id":"<formId>"},
              "otherProperties":"{}"},
 "customParam":{"appId":"...","objId":"..."}}
```

响应：`{"code":200,"status":true,"data":{"formTableId":"..."}}` —— 新表的 id 在 `data.formTableId`。

### 加字段 —— **不是**批量端点

```
POST /api/ebuilder/form/form/field/manage/saveFormFieldNew
body {"formId":...,"module":"ebuilderform","jsonObj":"{... 带 \"formTableId\":\"<表id>\" ...}"}
```

字段落点由 **jsonObj 里的 `formTableId`** 决定。这条与「建表时连字段一起建」的 `batch/save/formField` + `formTableList` **不是同一条路**。

### 删表

```
POST /api/ebuilder/form/form/field/manage/deleteFormTable?apid=<appId>
body {"module":"ebuilderform","formId":"<formId>","ids":["<表id>"],"customParam":{...}}
```

### 列表（`form physical-table list`）

```
POST /api/ebuilder/form/form/field/manage/getFormAGroupList?apid=<appId>
body {"module":"ebuilderform","formId":"<formId>","customParam":{...}}
```

响应 `data.formList[]` 每条：`name`（显示名）/ `tableName` / `tableType`（`MAIN` | `SUBSIDIARY`）/ `formTableId` / `systemTable` / `dataCount`；
另外 `data.groupList[]` 是字段分组。**主表也在 `formList` 里**（`tableType: MAIN`）。

⚠ 记录里的 `id` 键是 **formId**，不是表 id。

## 踩过的两条坑（都别再走）

**1. 不能把已有字段搬到另一张表。** 试过把字段的 `formTableId` 改成新表再整份写回，平台明确拒绝：

```
【备注】此字段不属于当前物理表，不能更改位置
```

所以**别指望「字段超 100 之后把老字段挪走」**——至少这条路径不行。能做的只有：**一开始就把新字段建到新表上**。这也解释了设计器的真实用法：先建附属表，后续新增的字段直接落在它上面。

**2. 平台会对形状不认的字段回 `200` 但静默不落库。** 在 `batch/save/formField` 那条路上，`DateTime` / `Percent` / `Browser` 三种就是这样——接口回成功，字段根本没建出来。所以 `add-physical-field` **每次写完都回读确认**，「接口回 200」不等于「建上了」。带配置的类型（如 Select 的选项）建完再用对应命令补。

## 注意事项

1. **删除不可逆**，表里的字段一并删除。执行前先确认表 id。
2. **`--table-name` 必填**。设计器用的是 `uf_<表单名拼音>_<n>_<m>` 这类命名，但规则没抓到报文，CLI 不替你猜 —— 重名/非法由平台报错（`此表的数据库表名称与数据库现有表存在冲突`）。
3. **建完的空表照样存在**于「其他」页签里；要清掉用 `delete-physical-table`。
