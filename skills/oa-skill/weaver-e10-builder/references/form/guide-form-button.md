# 台账视图按钮显示位置

用于将已有系统按钮或自定义按钮显示在指定视图的行上、行末下拉或顶部。配置的是按钮 `showPosition`，与整行点击的 `form list-event`、字段点击的 `form list-click` 独立。

## 查询与设置

```bash
e10-cli form button list <objId> <appId>
e10-cli form button views <objId> <appId> <buttonId>
e10-cli form button position <objId> <appId> <buttonId> --view <listId> --position 行上
```

`views` 返回平台 `getViewDatas` 对此按钮开放的视图，以及现有位置配置。`--view` 支持视图 ID、唯一名称、表单页语义“新建/编辑/显示”；多个同名视图必须用 ID。省略视图或使用“台账”时，必须只有一个可选台账，否则拒绝保存。

| 显示位置 | 平台值 |
|---|---|
| 右上 | `rightTop` |
| 右上下拉 | `rightTopDropDown` |
| 行上（行内） | `lineEnd` |
| 行末下拉 | `LineEndDropDown` |

行上、行末下拉只适用于台账，不适用于表单新建/编辑/显示页。

## 多视图及替换语义

普通设置默认合并：仅更新指定视图，保留其余台账及表单页的位置。同一视图的旧位置数组由此次指定的位置数组替换；需要多位置时一次传齐。

```bash
e10-cli form button position <objId> <appId> <buttonId> --view <listId> --position 行上 右上
e10-cli form button position <objId> <appId> <buttonId> --show-position @button-positions.json
```

不同视图使用不同位置时，JSON 文件示例（将 ID 占位替换为实际值）：

```json
{
  "<listIdA>_table": ["lineEnd"],
  "<listIdB>_table": ["LineEndDropDown"],
  "show_form": ["rightTop"],
  "edit_form": ["rightTopDropDown"]
}
```

`--show-position` 也默认合并，不能与 `--position/--view` 同时使用。显式 `--replace` 才替换全部页面配置；未列出的页面不再显示该按钮。`--show-position '{}' --replace` 清空所有显示位置。

新建自定义按钮也支持 `form button add ... --view <listId> --position 行上`。按钮点击动作仍由原有动作配置决定；改变显示位置不会自动添加行数据参数。

## 打开页面与当前行字段映射

按钮可以打开固定 URL、平台视图或表单布局；流程快捷入口本质上打开流程绑定表单的“新建布局”。四种目标参数互斥：

```bash
# 打开目标视图并按当前行过滤：目标字段 ← 来源字段
e10-cli form button add <objId> <appId> "查看明细" --open-view <视图名或viewId> --map "关联主表:数据ID" --view <来源视图> --position 行上

# 打开表单新建/编辑/显示布局并预填，可通过 --target-app 跨应用
e10-cli form button add <objId> <appId> "新建明细" --open-layout <目标表名或objId> --layout-type 新建 --map "关联主表:数据ID" --view <来源视图> --position 行上

# 发起当前应用内流程；内部解析流程绑定表单并打开新建布局
e10-cli form button add <objId> <appId> "发起申请" --start-workflow <流程名或workflowId> --map "关联主表:数据ID" --view <来源视图> --position 行上

# 无当前行参数的顶部入口
e10-cli form button add <objId> <appId> "发起申请" --start-workflow <流程> --view <来源视图> --position 右上
```

`--map` 可连续传多项，字段两端均支持唯一名称或 ID。视图动作生成原生 `VIEWPORT + autoFillParams`，布局动作生成 `LAYOUT + paramsMode=2`，不是拼固定 URL。EBuilder 目标字段通常映射来源“数据ID”。行上/行末下拉存在当前行上下文，可以使用映射；右上/右上下拉没有确定的单行上下文，禁止使用 `--map`。

更新已有按钮动作而不改变位置和权限：

```bash
e10-cli form button action-set <objId> <appId> <buttonId> --open-view <视图> --map "关联主表:数据ID"
```

当前仅管理一个 `openpage` 动作，不用于复杂多动作编排。`--start-workflow` 暂只解析当前应用内流程；跨应用普通视图/布局使用 `--target-app`。

## 保存与验证

命令先分页查找按钮，再读取动作、权限和可选视图。提交时保留按钮基础配置、完整动作和权限，及接口返回的日志/自定义提示设置，并按视图实际名称重建 `showPositionSpan`。

保存后回读按钮位置并核对动作、权限 ID 集合；成功输出 `verified: true`。若提示“已保存，但回读不一致”，远端可能已修改，必须先重新查询再处理。该验证属于配置回读，不代表已验证按钮点击行为或浏览器渲染。

计划模板 3.3 中必须记录：按钮名称/ID、来源视图名称/ID、显示位置、目标类型与名称/ID、每条“目标字段 ← 来源字段”映射、验证结果。只有需求涉及按钮展示时才填写，无需求标“— 无”。系统删除按钮测试仅核对配置和显示，不点击删除业务数据。
