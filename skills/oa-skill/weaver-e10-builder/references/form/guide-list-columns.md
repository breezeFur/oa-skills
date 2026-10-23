# 台账显示列批量配置

适用于已有 `nListView`、`multiView` 的显示列。`listId` 取 `form list-view <objId> <appId>`；新建表格视图仍使用 `form table-view create`。关联浏览框的显示字段使用 `form ebuilder-columns`。

## 查看、追加、移除

```shell
e10-cli form list-columns <objId> <appId> <listId> --json
e10-cli form list-columns <objId> <appId> <listId> --add <字段ID1> <字段ID2> --json
e10-cli form list-columns <objId> <appId> <listId> --remove <字段ID1> <字段ID2> --json
```

`--add` 按输入顺序追加到隐藏主键之前，已存在的列复用原配置；重复执行且无变化时返回 `unchanged:true`，不保存。`--remove` 可与 `--add` 同时使用，但不能对同一字段同时增删。移除不存在的列会报错；数据主键禁止移除。

## 一次设置顺序、宽度和格式

先读取当前列，按需求生成 UTF-8 的 `columns.json`。数组表示**完整业务列清单**：未列入的业务列会移除；数组顺序就是显示顺序。字段 ID 使用字符串，支持 `fieldId` 或 `id`，也支持仅填 ID 字符串。

```json
[
  {"fieldId":"1310832462830059523","width":220},
  {"fieldId":"1310832462830059527","width":150,"format":"yyyy-MM-dd"},
  {"fieldId":"1310832462830059528","width":150,"format":"THOUSANDS","decimalLength":2}
]
```

```shell
e10-cli form list-columns <objId> <appId> <listId> --set @columns.json --json
```

示例 ID 来自维森测试93项目任务表，其他表单需替换。`--set` 不能与增删选项混用；空数组只保留数据主键。配置文件不是原始 `tableField` 快照，不要填隐藏主键、uid、eventGroup 等内部属性。

| 属性 | 语义 |
|---|---|
| `fieldId` / `id` | 必填，当前表单的字段 ID，不可重复 |
| `text` | 非空显示名称 |
| `width` | 正数列宽，新列默认 150 |
| `format` | 日期格式或数值 `THOUSANDS`；`null` 清除 |
| `decimalLength` | 0–20 整数；`null` 清除 |
| `hidden` | 是否隐藏业务列，布尔值 |
| `viewDataDetail` | 是否显示关联数据详情，布尔值 |

已有列只覆盖明确提供的属性，未指定的格式、单位、点击事件、uid 等保留；新列从字段元数据构造。明细子字段从 `ds/fields` 嵌套目录解析，必要时 `getFormField` 补查；设置 `mainField:false`，不带明细展开容器属性。不能把明细子表容器作为普通列添加。

## 保存与验收

- 默认改 PC，可用 `--terminal mobile` 修改移动端 `tableField`；移动端卡片布局的 `listField/cardLayout` 不属于此命令。
- 全部字段与参数解析成功后，只调用一次 `saveNListConfig`。先读取真实 PC/MOBILE 配置，另一终端原样回传；读取失败默认中止。仅明确只用 PC 时允许 `--pc-only`，此时若移动端读取失败，结果标明未保留校验。
- 自动保留隐藏数据主键，缺失时补齐。保存后回读核对列 ID、顺序、属性以及另一终端配置；仅忽略平台每次读取重新生成的按钮动作/事件 ID。
- `verified:true` 表示接口回读通过。回读不一致时返回错误，保存可能已发生，应读取配置定位差异后处理；页面实际显示仍按需求验收。

计划模板的「台账/视图配置 → 显示列批量设置」记录目标视图、终端、增量或整组模式、字段顺序、宽度/格式、配置文件路径与回读/页面验收结果。
