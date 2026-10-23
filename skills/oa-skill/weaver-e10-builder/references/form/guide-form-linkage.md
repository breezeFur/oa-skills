# 表单字段显隐联动指南

## 概述

字段显隐联动：当某些字段的值满足条件时，自动改变其他字段的显示属性（隐藏/显示/编辑/只读/必填）。

## CLI 命令

```bash
e10-cli form linkage add <appId> <objId> <name> --config @<json文件>
```

## 配置 JSON 格式

```json
{
  "conditions": [
    {
      "fieldId": "触发字段ID",
      "operator": "EQUAL",
      "options": [{"optionId": "选项ID", "content": "选项名"}]
    }
  ],
  "actions": [
    {
      "prop": "hide",
      "fields": [
        {
          "fieldId": "目标字段ID",
          "name": "字段名称",
          "dataKey": "字段编码",
          "fieldType": "Employee",
          "isDetail": false
        }
      ]
    }
  ]
}
```

### actions[].fields[]（联动目标字段）

| 键 | 说明 |
|------|------|
| fieldId | 目标字段的 fieldId（从 `form read --app-id` 获取） |
| name | 字段名（显示用） |
| dataKey | 字段编码；`form read` 不返回它，**留空即可**（用 fieldId 代替可行） |
| fieldType | 字段类型，如 `Text` / `Employee` / `Date` |
| **`isDetail`** | **目标落在明细表里时必须为 `true`**。不传 = 主表字段 |

**目标字段在明细表里，就加 `"isDetail": true`** —— 这是「主表字段控制明细列显隐」的写法，两个方向都支持（`hide` / `required` 均可）：

```json
{
  "conditions": [{ "fieldId": "<主表字段ID>", "operator": "EQUAL", "value": "Y" }],
  "actions": [{
    "prop": "hide",
    "fields": [{ "fieldId": "<明细列ID>", "name": "明细列A", "dataKey": "", "fieldType": "Text", "isDetail": true }]
  }]
}
```

**怎么认出明细字段**：`form read` 的输出里，明细字段会标注所属明细表 —— 带 `明细表: xxx` 那些就是，照它填 `isDetail: true`。

### conditions（触发条件）

多个条件之间是 **AND** 关系（全部满足才触发）。

| 字段 | 说明 |
|------|------|
| fieldId | 触发字段的 fieldId（从 `form read --app-id` 获取） |
| operator | 比较符，见下表 |
| value | 普通字段的比较值（文本/数字）。**「为空 / 不为空」不要给** |
| options | Select/RadioBox 字段的选项，格式：`[{"optionId": "选项ID", "content": "选项名"}]` |

比较符：

| 写法 | 含义 | 备注 |
|------|------|------|
| `EQUAL` / `NOT_EQUAL` | 等于 / 不等于 | |
| `CONTAIN` / `NOT_CONTAIN` | 包含 / 不包含 | |
| `GREATER` / `LESS` / `GREATER_EQUAL` / `LESS_EQUAL` | 大于 / 小于 / 大于等于 / 小于等于 | |
| **`NULL`** | **为空** | 也可以写 `EMPTY` / `IS_NULL`，命令会归一成平台码 |
| **`NOT_NULL`** | **不为空** | 也可以写 `NOT_EMPTY` / `IS_NOT_NULL` |

**「为空」的算子写错，报错会指向完全无关的地方。** 平台不认 `EMPTY` 这类写法时不会说「算子不合法」，而是在写库时抛一句 `mybatis PersistenceException / Error updating database` —— 容易让人误判成字段配置问题（真实发生过：被当成「目标字段 `dataKey` 为空导致 NOT NULL」去查，而 `dataKey` 留空本身是没问题的）。用 `NULL` / `NOT_NULL`，或者写 `EMPTY` 交给命令归一。

### 多个条件之间：任一 / 全部

界面上的「满足以下**任一**条件」= `OR`，「满足以下**全部**条件」= `AND`。在 config 顶层写 `detailType`：

```json
{ "detailType": "OR", "conditions": [ ... ], "actions": [ ... ] }
```

**不写这个键时由平台取自己的默认值** —— 设计器每次都显式发，所以缺省行为没有依据，命令不替平台决定。多条件时建议明确写。

## 生效维度（生效范围）

联动可以只对**某一种展示形态**生效。在 config 里用 `effect` 指定：

| 写法 | 含义 |
|------|------|
| 不写 | **当前表单**（最常见） |
| `"effect": "formLayout"` | 只对**某个表单布局**生效（布局 id 现查） |
| `"effect": { ... }` | 直接给 `{effectType, effectName, effectValue}`，自行指定 |

⚠ **布局维度的值要的是 `multipleLayoutId`，不是 `formLayout.id`** —— 同一张表上这两个值**相邻但不同**（例如 `…375` 与 `…376`）。给错了命令**不报错**，只是指向另一个布局，而且平台按这个 id 解析不出名字，回读时生效范围是个空白（`表单布局: `）。命令取的是前者，不用手填。

### 工作流表单那条路由的维度不一样

上面的表是 **eb 表**（`form linkage add`）的。**原生工作流程表单**（`wf-form linkage`）提供的是另外四种，写法也不同：

| 界面上的维度 | `effect` 写什么 | 取值 | 额外参数 |
|---|---|---|---|
| 当前表单 | 不写（缺省） | 表单 formId | — |
| **表单布局** | `"formLayout"` | **布局 id**（默认布局；可用 `"layoutId"` 指定别的） | — |
| **当前工作流** | `"workFlow"` | **流程 ID** | `--workflow-id` |
| **选择节点** | `"includeNode"` | **节点 ID** | `--workflow-id` + `"nodeId"`（可写节点名） |

```bash
e10-cli wf-form linkage <formId> "规则名" --workflow-id <流程ID> --config @cfg.json
```

```json
{ "effect": "workFlow",  "conditions": [ ... ], "actions": [ ... ] }
{ "effect": "includeNode", "nodeId": "1级审批", "conditions": [ ... ], "actions": [ ... ] }
```

**这条路由的 `refId` 始终是流程 ID**，是「这条联动挂在哪个流程上」，**不是**选项的取值 —— 给「选择节点」时选项取值是节点 ID，两者不同，别照着取值抄。流程表单 formId 与流程 ID 不是一回事，用 `workflow info <流程ID>` 可以反查。

选项的显示名里那个 `【V1】` 是**平台按活动版本自己加的**，写节点名进去它会补成「节点名【V1】」。

### actions（联动效果）

| 属性 | prop 值 | 效果 |
|------|---------|------|
| 隐藏 | `hide` | 字段隐藏不可见 |
| 隐藏行 | `hideLine` | 字段所在行整行隐藏（仅表格布局；`hideRow` 兼容旧写法） |
| 显示（只读） | `show` | 字段显示但不可编辑 |
| 编辑 | `edit` | 字段显示且可编辑 |
| 只读 | `readonly` | 字段显示且不可编辑（同 show） |
| 必填 | `required` | 字段显示且必填（条件满足时必填） |

**优先级**：`hide` > `readonly` > `edit`

多个联动规则同时满足时，优先级高的生效。

## 示例

### 示例 1：优先级=高 时隐藏负责人字段

```json
{
  "conditions": [
    {
      "fieldId": "1290473132445114373",
      "operator": "EQUAL",
      "options": [{"optionId": "1290473132445114394", "content": "高"}]
    }
  ],
  "actions": [
    {
      "prop": "hide",
      "fields": [
        {
          "fieldId": "1290473132445114370",
          "name": "负责人",
          "dataKey": "fzr48cef",
          "fieldType": "Employee"
        }
      ]
    }
  ]
}
```

### 示例 2：金额 > 10000 时审批人变为只读

```json
{
  "conditions": [
    {
      "fieldId": "金额字段ID",
      "operator": "GREATER_THAN",
      "value": "10000"
    }
  ],
  "actions": [
    {
      "prop": "readonly",
      "fields": [
        {
          "fieldId": "审批人字段ID",
          "name": "审批人",
          "dataKey": "spr89abc",
          "fieldType": "Employee"
        }
      ]
    }
  ]
}
```

## 注意事项

1. **主表 vs 明细表**：主表触发字段可修改主表或明细字段；明细表触发字段只能修改本行字段。
   目标落在明细表里时，`actions[].fields[]` 那个条目**必须带 `isDetail: true`**；不带的话这个目标会被当作主表字段提交
2. **表格布局限制**：通过隐藏行/列/单元格自定义属性隐藏的字段，无法通过联动显示出来
3. **明细表字段列隐藏**：需在明细表第一行配置操作按钮元素
4. **多规则冲突**：避免同一个触发字段或同一个目标字段出现在多个规则里
5. **默认属性**：字段的默认显示属性为设计器中设置的"读写属性"或"字段权限"
6. **目标字段 dataKey**：`form read` 不返回它，**留空即可** —— 平台按 `fieldId` 定位，`dataKey` 空着能正常建规则（已对照验证）。填上真值也行，但别为了凑它去猜；它**不是**某些报错的原因。
7. **Select 选项 ID**：必须用 `form read --app-id` 返回的真实 `valueKey`（自动生成的长 ID，如 `1294601918674214939`），不能用建表单时给的短 `valueKey`（如 `"GQ"` / `"5"`）

---

## 值带出（编辑已有字段的 ffRelateField）

值带出不是 `linkage add` 的显隐规则，而是**字段级配置**（`ffRelateField`）：当 EBuilder 关联字段选中某条记录后，自动将该记录的某个字段值复制到当前字段。例如：选客户→自动带出联系人；选合同→自动带出合同金额。

### 创建时配置

`form create --fields` 里用 `relateFrom` 定义，CLI 在 create Step 3 自动配置 ffRelateField：

```json
{ "componentKey": "Text", "fieldName": "联系人",
  "relateFrom": { "ebuilderField": "关联客户", "sourceFieldId": "1296220571782152194" } }
```

### 创建后补配

```bash
e10-cli form edit-field <objId> <appId> <fieldId> \
  --relate-from <EBuilder字段名> \
  --relate-from-source <目标表单源字段fieldId>
```

> ⚠️ **`sourceFieldId` 和 `--relate-from-source` 必须传字段的数字 fieldId**（如 `1296220571782152194`），不能传字段名（如"联系人姓名"）。用 `form read <objId> --app-id <appId>` 获取字段的 fieldId。

- `--relate-from`：本表单中的 EBuilder 关联字段名（如 `"关联客户"`）
- `--relate-from-source`：关联目标表单中要复制值的字段 fieldId

### HRM 值带出（form relate，表内 Employee/Department 源）

换表内的**人员字段**或**部门字段**自动填目标字段。源字段是表单里的 Employee/Department 类型，目标字段按 HRM 属性带出值。结构差异：**Employee 源 ffRelateField 带 `module:"hrm"`，Department 源不带**。

```bash
# 换「申请人」(Employee) → 自动填「申请人工号」为邮箱
e10-cli form relate <appId> <objId> 申请人工号 --from 申请人 --key email

# 换「所属部门」(Department) → 自动填「申请人工号」为部门编号
e10-cli form relate <appId> <objId> 申请人工号 --from 所属部门 --key code
```

参数：
| 参数 | 说明 |
|------|------|
| `<targetField>` | 目标字段（被填充），名称或 fieldId |
| `--from <field>` | 源字段（触发），必须 Employee 或 Department 类型 |
| `--key <key>` | 带出属性 key。默认 Employee=`department`、Department=`name`。不传 `--title` 时自动取属性中文名 |

`--key` 从平台清单校验（`listBusinessField`），非法 key 会报错并列出可选属性：

**Employee 源**（人员属性，部分）：`username`姓名 / `email`邮箱 / `superior`上级 / `mobile`手机 / `jobNum`工号 / `hiredate`入职时间 / `department`部门 / `position`岗位 / `grade`职级 / `allSuperiors`所有上级 …

**Department 源**（部门属性，全部）：`name`部门名称(→Text) / `code`部门编号(→Text) / `parent`上级部门(→Department) / `fullname`部门全称(→Text) / `department.coadjutant`协办人(→RelateBrowser) / `deptEmployee`部门人员(→Employee)

> 目标字段类型与属性不匹配时命令只提示警告、不阻止（如 `deptEmployee` 通常只能填 Employee 字段）。
