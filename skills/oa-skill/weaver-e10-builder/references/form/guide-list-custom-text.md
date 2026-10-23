# 列表自定义文本列

表单的列表式视图（台账）里，列除了直接绑表单字段，还能加一列**自定义文本**：内容是一段富文本，
可以写固定文字、插图，也能在文字中间**插入表单字段**（「合计：〔金额〕元」这种说明性排版）。

命令是 `form nlist apply`：模板里**不给 `fieldId`、改给 `html`** 的列项，就是自定义文本列。

```json
[
  [
    {"fieldId": "1317534123603582976", "text": "金额", "width": 1},
    {"html": "<p>合计：{{金额}} 元</p>", "text": "合计", "width": 1}
  ]
]
```

```bash
e10-cli form nlist apply <objId> <appId> <listId> @template.json
```

## 在自定义文本里插入表单字段

写 `{{字段名}}` 或 `{{fieldId}}`，CLI 查表单元数据后展开成平台的字段引用标记。

上面那段 `html` 存进去的是：

```html
<p>合计：<span contenteditable="false" data-type="list" data-val="{objId.fieldId}">{表名.字段名}</span> 元</p>
```

规则：

- 同一字段写几次就展开几份 —— 平台按**出现位置**逐个记引用，不去重。
- 字段显示名在表单内重复时报错，改用 `fieldId`。
- 字段不存在 → 报错并中止，不会把半截 HTML 写进视图。

## 直接写字段引用标记

已经拿到平台原样标记时，也可以把它整段写进 `html`。CLI 会校验 `data-val` 里的 fieldId 在这张
表单里是否存在，查不到只**告警**（平台对这种引用不报错，只是静默显示不出值，所以提醒一声）。

标记的形状固定为 `<span contenteditable="false" data-type="list" data-val="{objId.fieldId}">{表名.字段名}</span>`：
**身份在 `data-val` 里的 `objId.fieldId`**，span 里的 `{表名.字段名}` 只是占位文本。

## 其它

- 列显示名用模板项的 `text`，缺省「自定义文本」。
- 富文本的配色、字号、背景直接写在内联 `style` 里，与设计器编辑器一致，例如
  `<span style="background-color:#27ae60">应收</span>`。
- `form nlist apply` 按模板整体重建显示列与排布，PC 与移动端两个槽位一并写入；
  当前配置用 `form nlist show <objId> <appId> <listId>` 查看。
- ⚠ 只对列表式（NList）生效，表格式台账用 `form table-view`。
