# EB 表单复杂编号

复杂编号用于在文本字段上配置固定内容、日期、流水号、表单字段、系统字段和代字组合。

## 设置编号

```bash
e10-cli form serial-mark set <objId> <appId> <字段ID> --segments @segments.json
```

数组顺序就是编号拼接顺序：

```json
[
  {"type":"field","fieldId":"<项目类型字段ID>","shortName":{"研发":"YF","实施":"SS"}},
  {"type":"fixed","value":"-"},
  {"type":"year","format":"four","alone":true},
  {"type":"fixed","value":"-"},
  {"type":"serial","digits":4,"zero":true}
]
```

## 编号段

| `type` | 含义 | 常用属性 |
|---|---|---|
| `fixed` | 固定文本 | `value` |
| `year` | 年份 | `format:four|two`、`alone` |
| `serial` | 流水号 | `digits`、`zero`、`alone` |
| `field` | 表单字段值 | `fieldId`、`shortName`、`alone` |
| `system` | 系统字段 | `systemField:creator|creator-dept`、`alone` |
| `date` | 日期 | `format:yyyy|yyyyMM|yyyyMMdd`、`source` |

`alone:true` 用于按该段分别计数；`shortName` 用于将选项值映射为代字。

## 增量调整、查询和清除

```bash
e10-cli form serial-mark add-segment <objId> <appId> <字段ID> --type field --field-id <取值字段ID> --position 0
e10-cli form serial-mark short-name list <objId> <appId> <选择字段ID>
e10-cli form serial-mark short-name set <objId> <appId> <选择字段ID> --map '{"研发":"YF","实施":"SS"}'
e10-cli form serial-mark read <objId> <appId>
e10-cli form serial-mark fields <objId> <appId>
e10-cli form serial-mark clear <objId> <appId> <字段ID>
```

配置复杂编号后，目标字段由平台自动生成编号并按只读方式使用。
