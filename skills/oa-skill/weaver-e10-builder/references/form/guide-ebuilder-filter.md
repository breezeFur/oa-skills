# EBuilder 关联字段数据过滤

用于配置表单中 EBuilder 关联字段的“数据过滤设置”。它决定关联弹窗里哪些目标表单数据可被选择，不是表格视图的常用搜索。

## 命令

```bash
# 读取并解析当前规则
e10-cli form ebuilder-filter get <源objId> <appId> <EBuilder字段fieldId>

# 设置规则；rules 支持 JSON 字符串或 @文件
e10-cli form ebuilder-filter set <源objId> <appId> <EBuilder字段fieldId> \
  --rules @filter-rules.json \
  --logic and

# 清空规则
e10-cli form ebuilder-filter clear <源objId> <appId> <EBuilder字段fieldId>
```

`--logic and|or` 表示满足全部或任一规则；`--fill-null 0|1` 控制关联值为空时是否填充。未传时保留原设置。

## 规则格式

每条规则统一使用目标字段的准确名称或 `fieldId`，不要手写 `filterParams`：

```json
[
  {
    "field": "合同名称",
    "operator": "like",
    "value": "测试合同"
  },
  {
    "field": "合同金额",
    "operator": "like",
    "value": { "min": 100, "max": 500 }
  },
  {
    "field": "合同状态",
    "operator": "eq",
    "value": ["已退回"]
  }
]
```

字段名重复时必须改用 `fieldId`。Select/RadioBox/CheckBox 的 `value` 可以写选项名称或 `valueKey`，CLI 会查询选项并转换；浏览类字段应写对象 ID。

## 字段与条件

| 目标字段 | operator | value |
|---|---|---|
| 固定标题 `name` | `like`、`eq`、`neq` | 单值 |
| 固定创建者 `creator` | `eq`、`neq` | ID 或 ID 数组 |
| 固定创建时间 `create_time` | `like` | `{"start":"...","end":"..."}` |
| Text/TextArea/Email/Phone/Mobile | `like`、`eq`、`neq`、`null`、`notnull` | 单值；空值条件不传 value |
| Money/Number | `like`、`null`、`notnull` | `like` 使用 `{"min":...,"max":...}` |
| Date/DateComponent | `like`、`beq`、`seq`、`null`、`notnull` | 范围或单值 |
| Select/RadioBox/CheckBox | `eq`、`neq`、`null`、`notnull` | 名称/valueKey 数组 |
| Employee/Department 等浏览类 | `eq`、`neq`、`null`、`notnull` | ID 或 ID 数组 |

条件来自当前设计器契约。未知组件或不支持的条件必须在写入前失败，禁止猜测。

## 保存与验证

CLI 会：

1. 验证源字段确为已绑定目标表单的 EBuilder 字段。
2. 从目标表单读取字段类型和选项，不按名称猜类型。
3. 同时生成运行时 `filterParams` 和设计器回显 `filterQueryParams`。
4. 通过字段布局接口保存，并保留其他字段布局设置。
5. 从 `getFormLayout.fieldLayout` 独立回读；两份配置不一致即报错。

当前只支持常量过滤。变量来源、未确认的新控件和无法取得选项契约的跨应用字段，不应强行写入。
