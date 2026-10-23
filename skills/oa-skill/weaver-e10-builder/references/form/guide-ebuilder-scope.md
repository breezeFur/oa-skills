# 关联浏览数据范围设置（浏览数据定义 → 数据范围）

配置表单中 EBuilder 关联字段的**数据范围设置**——决定关联浏览弹窗里**哪些被关联数据可选**（如关联客户时只选"客户状态=启用"的客户）。对应设计器「浏览数据定义 → 数据范围设置」面板。

走平台 `browserDataScope` 接口（selectPage 读 / batchSave 写+清），设计器能识别、浏览时生效。

## 命令

```bash
# 读取已设数据范围
e10-cli form ebuilder-scope get <源objId> <appId> <EBuilder字段fieldId>

# 设置数据范围：被关联数据须满足条件才可选
e10-cli form ebuilder-scope set <源objId> <appId> <EBuilder字段fieldId> \
  --rules @scope-rules.json --logic and

# 清空
e10-cli form ebuilder-scope clear <源objId> <appId> <EBuilder字段fieldId>
```

- `<源objId>`：含关联浏览字段的表单 objId
- `<appId>`：应用 ID
- `<EBuilder字段fieldId>`：关联浏览字段的 fieldId（`form read` 获取，类型为 Ebuilder）
- `--logic and|or`：多规则关系（默认 `and`）
- `--fill-null`：关联字段为空时是否填充（默认关闭）

## 规则格式

```json
[
  {"field":"客户状态","operator":"eq","value":"启用"},
  {"field":"客户名称","operator":"like","value":"上海"}
]
```

| 字段 | 说明 |
|------|------|
| `field` | 目标表单字段名或 fieldId（CLI 自动解析） |
| `operator` | `eq`(等于)/`neq`(不等于)/`like`(包含)/`isnull`(为空)/`notnull`(不为空) |
| `value` | 选项类用**选项名**，CLI 自动解析 valueKey；文本/数字/日期用字面值。`isnull`/`notnull` 不需要 value |

> 选项类字段（Select/Radio/CheckBox）：`value` 填选项名，CLI 自动反查目标表该字段的选项、解析出 valueKey，填 `selectValue`/`customBrowserValue`/`config.options`。选项名必须在目标表选项中存在，否则报错并列出可选值。

## 示例

**关联客户只选启用状态**（典型场景：客户状态=启用才可选）：

```bash
e10-cli form ebuilder-scope set <源objId> <appId> <EBuilder字段fieldId> \
  --rules '[{"field":"客户状态","operator":"eq","value":"启用"}]'
```

**多条件**（启用且名称含上海）：

```bash
e10-cli form ebuilder-scope set <源objId> <appId> <EBuilder字段fieldId> \
  --rules '[{"field":"客户状态","operator":"eq","value":"启用"},{"field":"客户名称","operator":"like","value":"上海"}]' \
  --logic and
```

**清空恢复全部可选**：

```bash
e10-cli form ebuilder-scope clear <源objId> <appId> <EBuilder字段fieldId>
```

## 验证

- `set` 命令保存后自动回读校验规则数是否一致
- 设计器打开「数据范围设置」面板应显示所设条件
- 关联浏览时被关联数据应按条件过滤（不满足的不可选）

## 与旧 `ebuilder-filter` 的区别

| | `ebuilder-scope`（推荐） | `ebuilder-filter`（已废弃，保留兼容） |
|---|---|---|
| 接口 | `browserDataScope`（数据范围专用） | 字段布局 `filterParams` |
| 设计器识别 | ✅ | ❌ |
| 浏览时生效 | ✅ | 不保证 |
| 用途 | 关联浏览筛选 | 旧机制，已被 scope 取代 |

> ⚠️ `ebuilder-filter` 的旧配置不保证被设计器识别；新建关联浏览筛选一律用 `ebuilder-scope`。
