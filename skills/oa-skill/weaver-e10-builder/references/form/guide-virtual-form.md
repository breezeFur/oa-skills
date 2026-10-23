# 虚拟表创建与维护

虚拟表把已有数据源的字段映射为 EB 表单，用于统一展示 EB 表单、系统业务表或数据加工结果。虚拟表保留来源字段的数据键与类型，布局、视图和菜单继续使用表单现有能力。

## 创建顺序

1. 确定来源类别和数据源。
2. 校验数据源具有稳定 ID 字段。
3. 读取来源字段，选择需要展示的字段。
4. 按来源类型保留字段映射，设置名称、顺序和显示属性。
5. 创建虚拟表并初始化 FLOW 或 EXCEL 布局。
6. 按需求配置分组、默认台账、显示列和菜单。

## 数据源类别

| 来源 | `dataSourceType` | `dataSourceGroup` |
| --- | --- | --- |
| EB 表单 | `LOGIC` | `weaver-ebuilder-form-service` |
| 系统业务表 | `LOGIC` | 对应业务服务，如 `weaver-hrm-service` |
| 数据加工 | `ETEAMS` | 数据集分组 ID |

查询普通逻辑数据源：

```bash
e10-cli form virtual source-groups --source-type LOGIC
e10-cli form virtual sources <groupId> --source-type LOGIC --name <名称>
```

查询数据加工：

```bash
e10-cli form virtual dataset-groups
e10-cli form virtual datasets <groupId> --name <名称>
e10-cli form virtual dataset-info <datasetId>
```

## 数据源与字段预检

```bash
e10-cli form virtual fields <appId> \
  --source-type LOGIC \
  --source-group weaver-hrm-service \
  --source-id <数据源ID>
```

命令先检查来源是否具有稳定 ID，再返回可选字段。每个字段重点保留：

```text
dataKey
virtualFieldId
sourceFieldType
sourceFieldTitle
type / componentKey
```

## 字段选择文件


```json
[
  "username",
  {
    "sourceField": "ACTIVE_DATE",
    "fieldName": "激活时间",
    "componentKey": "DateTime",
    "format": "yyyy-MM-dd HH:mm",
    "readOnly": true,
    "singleRow": false
  }
]
```

- 字符串简写按 `dataKey`、`virtualFieldId` 或来源字段名称匹配。
- 未指定 `componentKey` 时使用平台推荐类型。
- `fieldName`、`required`、`readOnly`、`hidden`、`singleRow` 用于表单展示。
- 来源字段标识由 CLI 从接口结果中补齐。

## 类型兼容

| 来源类型 | 默认类型 | 可用的同族展示类型 |
| --- | --- | --- |
| `String-普通文本` | `Text` | `Text`、`TextArea` |
| `Number-数值` | `Number` | `Number`、`Money` |
| `Date-日期` | `Date` | `Date`、`DateTime` |
| 选项、人员、部门、关联等复杂字段 | 来源组件 | 保留来源组件类型与配置 |

CLI 在保存前校验类型兼容性。长度、数字精度和日期格式可在同族类型内设置；复杂字段沿用数据源返回的组件结构。

## 创建

系统业务表：

```bash
e10-cli form virtual create <appId> "人员虚拟表" \
  --source-type LOGIC \
  --source-group weaver-hrm-service \
  --source-id <人员表数据源ID> \
  --source-name "人员表" \
  --source-module hrm \
  --fields @virtual-fields.json \
  --layout FLOW
```

EB 表单：

```bash
e10-cli form virtual create <appId> "项目虚拟表" \
  --source-type LOGIC \
  --source-group weaver-ebuilder-form-service \
  --source-id <来源表单数据源ID> \
  --source-app-id <来源应用ID> \
  --fields @virtual-fields.json \
  --layout FLOW
```

数据加工：

```bash
e10-cli form virtual create <appId> "合同加工结果" \
  --source-type ETEAMS \
  --source-group <数据集分组ID> \
  --source-id <数据集ID> \
  --dataset-type sql \
  --fields @virtual-fields.json \
  --layout FLOW
```

创建结果返回 `objId`、`formId` 和默认视图 ID。来源访问范围随已选择的数据源配置保存，虚拟表命令不单独修改数据源权限。

## 读取与增加字段

```bash
e10-cli form virtual read <objId> <appId>

e10-cli form virtual add-fields <objId> <appId> <formId> \
  --source-type LOGIC \
  --source-group weaver-hrm-service \
  --source-id <数据源ID> \
  --fields @add-fields.json
```

增加字段时重新从原数据源读取当前可选字段，并保留来源映射。字段移除和更换数据源按取得的实际接口配置另行维护。

## 后续配置

虚拟表创建后继续使用现有命令：

- 布局：`form layout read/init/move/set-read-only/set-required`
- 分组：`form group`
- 默认台账和显示列：`form list-columns`、`form nlist`
- 视图：`form view`、`form table-view`
- 菜单：`menu add-table`

## Plan 记录

虚拟表在表单清单中注明：名称、来源类别、数据源名称或 ID、选用字段、字段映射、布局和视图。执行时依次销号数据源定位、主键校验、字段映射、创建、布局和视图配置。
