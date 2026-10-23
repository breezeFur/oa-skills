# 表单视图：新建与验收

表单创建后已有默认台账；只有用户明确需要额外视图时才创建。表格视图是 `nListView` 数据列表，和普通 `formView` 是两条不同链路。

## 需求判别

- “新建表单” → `form create --fields`。
- “客户信息表需要一个客户信息视图”等普通列表需求 → 先查询并复用该表单默认台账；“客户信息表”和“客户信息”的名称差异不构成额外新建理由。
- “在已有表单下明确新增一个额外表格视图” → `form table-view create`；命令必须同时保存显示列并回读。
- “在已有表单下新增表单视图” → `form view create --type formView`，随后必须 `form view populate`；不得新建另一张表单。

## 默认台账复用

1. 用 `form list-view <objId> <appId>` 查询已有列表，确认目标属于当前表单且用途符合需求，记录实际名称和 listId。存在多个候选时核对数据范围、权限和展示配置，不仅凭名称或第一条记录选择。
2. 普通列表需求直接在该 listId 上配置显示列、筛选、排序、统计和事件；需要整组配置显示列时用 `form list-columns <objId> <appId> <listId> --set @columns.json`。`table-view ensure` 只用于空列补齐，不负责视图选择或重命名。
3. 默认视图名称由平台随表单生成，不应机械沿用或统一去掉末尾“表”字。需求明确给出视图名称且与默认名称不一致时，使用 `form view rename` 修改已有默认台账并保留 ID；不要新建同用途视图代替改名。表单名、视图名和菜单名分别处理。例如表单“客户类型表”的视图要求为“客户类型”时，应把默认台账改名为“客户类型”，不能写成“同客户类型”。
4. 只有明确需要“我的客户”“重点客户”等额外独立视图，或不同展示类型时，才进入新增流程。已有重复视图需先核对菜单、关联页签等引用及配置，不能自动删除。

例如：已建“客户信息表”，方案中的“客户信息视图”可由其默认台账满足，plan 标记“复用默认台账”，填写实际 listId 即可。

## 命令

```bash
# 查询表单下全部视图
e10-cli form view list <objId> <appId>

# 修改已有默认台账名称（viewId 从上一条命令取得）
e10-cli form view rename <objId> <appId> <viewId> "客户类型"

# 创建可用表格视图；默认放入全部已有字段
e10-cli form table-view create <objId> <appId> "审批数据表格" --pc-only

# 创建看板视图（默认 PC + FLOW 布局）
e10-cli form view create <objId> <appId> "按状态看板" --type kanbanView

# 新增表单视图——流式布局（FLOW）
e10-cli form view create <objId> <appId> "新增-流式视图" --type formView --layout-type FLOW

# 新增表单视图——表格式布局（EXCEL）
e10-cli form view create <objId> <appId> "新增-EXCEL视图" --type formView --layout-type EXCEL

# 第 2 步：把已有字段按目标布局类型填入新建 formView（流式/EXCEL 各自生成对应组件）
e10-cli form view populate <objId> <appId> <viewId>

# 创建移动端日历视图
e10-cli form view create <objId> <appId> "交付日历" \
  --type calendarView --terminal MOBILE --layout-type FLOW
```

**给已有表单加表单视图是两步闭环**（缺一不可）：
1. `form view create --type formView --layout-type FLOW|EXCEL` —— 建一个**空**的 formView 实体，`--layout-type` 决定流式(FLOW)还是表格式(EXCEL)。同一张表单可同时存在多个 formView，布局类型可不同（如一张表既加流式视图又加 EXCEL 视图）。
2. `form view populate <objId> <appId> <viewId>` —— 把已有字段按目标布局类型填进去。流式视图生成流式组件、EXCEL 视图生成表格定位，**不得把 EXCEL 定位直接复制到 FLOW 视图**。

`form view populate` 以原表单 `formId` 读取字段，以新视图 `viewId` 作为 `layoutMultiId` 读取目标布局，再按目标的 FLOW/EXCEL 类型重新生成字段组件并独立回读。不得把视图的 `versionId` 或 `pageLayoutId` 当成 `formId`。

看板、日历、思维导图目前只确认创建实体和视图列表回读，尚不能据此宣称设计器已有可用组件。

普通 `form view create --type` 只接受：

- `formView`：详情视图
- `kanbanView`：看板视图
- `calendarView`：日历视图
- `mindMapView`：思维导图视图
- `multiView`：多维表格视图（无 layoutType/terminalType，带 `extConfig:{listVersion:5}`）。**数据维度**：缺省主表（`subFormId:""/subFormMain:false`）；明细表维度用 `--detail <明细名>`（按名解析明细 subFormId）或 `--sub-form-id <明细subFormId>`（直传），传值即 `subFormId:<明细subFormId>/subFormMain:true`。明细子表名/subFormId 用 `dataset/v1/getFields` detailFields 查（真 subFormId 在 `fields[].subFormId`，非 `dt.id`）。**多维表格显示列**复用台账同一套 `saveNListConfig/getNListConfig`，直接用 `form list-columns <objId> <appId> <multiView的viewId> --add <fieldId>` 加列。

`tableView`/`nListView` 不得传给普通视图命令。真实表格视图固定使用 `form table-view create`。

## 额外表格视图新建闭环

```bash
# 1. 已确认需要额外独立视图，再查询目标表单和已有列表
e10-cli form list <appId>
e10-cli form list-view <objId> <appId>

# 2. 创建 nListView、写入全部业务显示列和隐藏数据主键、独立回读
e10-cli --json form table-view create <objId> <appId> "<表格视图名>" --pc-only

# 3. 再次独立查询表单下列表
e10-cli --json form list-view <objId> <appId>
```

命令先用 `viewType=nListView` 创建，再以新 `listId` 读取 PC 配置；业务列必须取自 `/api/ebuilder/common/ds/fields` 的完整字段对象，不能只拼字段 ID。保存时保留服务端配置和隐藏主键 `id=5`，最后回读 `tableField` 和列表实体。命令只拦截完全同名的视图，不识别简称或业务用途；执行前必须完成复用判断，不能因名称未完全匹配就新建。已有同名视图时停止，不盲目重建。

`--pc-only` 只用于已确认本次验收为 PC 的场景。未指定时，命令必须取得真实 MOBILE 配置，禁止用 PC 配置推导移动端。

`create` / `ensure` 同样支持 `--terminal pc|mobile`（缺省 `pc`）：决定显示列写进哪一端，另一端原样保留。只给某一端配显示列时用 `--terminal`，两端都要就分两次执行。

```bash
# 只给移动端补显示列，PC 端配置不动
e10-cli --json form table-view create <objId> <appId> "移动端表格" --terminal mobile
```

服务器通过必须同时满足：

- 创建后按返回 `listId` 找到同名列表。
- `persisted=true`。
- `visibleFieldCount` 等于目标业务字段数。
- `tableFieldCount` 还包含隐藏主键。
- 再查 `form list-view` 仍能按相同 ID 和名称找到。

前端无数据时可以没有数据行，但必须看见业务字段列头；否则仍是空壳，不能验收。

## 表格视图展示样式

```bash
e10-cli --json form table-view style <objId> <appId> <listId> <style>
```

`style` 使用前台语义，不直接让使用者猜内部 `mode`：

| style | 前台展示样式 | mode |
|---|---|---|
| `table` | 表格式 | `1` |
| `list` | 列表式 | `2` |
| `left-diagram` | 左图式 | `3` |
| `horizontal-list` | 横向列表式 | `4` |
| `above` | 上图式 | `5` |
| `grid` | 网格列表式 | `7` |
| `editable` | 可编辑表格（编辑态） | `11` |

可编辑表格内部还有数据态 `8` 和只读态 `9`；用户要求“改成可编辑表格”时必须使用编辑态 `11`，不得把只读态 `9` 当成完成。

命令先确认 `listId` 属于目标 `objId`，读取目标终端的完整配置后只修改其顶层 `mode`，保存后重新读取该终端配置核对。

PC 与移动端是**两个独立槽位**（保存接口的 `config` 落 PC、`mConfig` 落移动端），`--terminal` 决定改哪一端，缺省 `pc`：

- `--terminal pc`：只改 PC，移动端配置原样回传；
- `--terminal mobile`：只改移动端，PC 配置原样回传。

末尾会回显实际落点与另一端状态（`终端: 移动端（另一端配置保持原样）`）。另一端配置读取不到时，只有明确 `--pc-only` 才允许继续；`--terminal mobile` 与 `--pc-only` 互斥，同时传会直接报错——不要用 `--pc-only` 去改移动端。

```bash
# 只把移动端改成网格列表式，PC 展示样式保持不动
e10-cli --json form table-view style <objId> <appId> <listId> grid --terminal mobile
```

前端验收：重新进入“基础设置 → 展示样式”仍显示“可编辑表格”，并且列表进入可编辑状态。

## 常用搜索显示方式

```bash
# PC 常用搜索显示为高级搜索；filter 表示筛选
e10-cli --json form table-view search-style <objId> <appId> <listId> advanced
```

显示方式固定为 `advanced → commonSearchType="0"`、`filter → commonSearchType="1"`，不得直接猜内部值。

命令先确认 `listId` 属于目标表单，完整保留目标终端的其他配置，保存后重新读取目标属性；`--terminal` 同上（`pc` 只改 PC、`mobile` 只改移动端，另一端原样回传）。前端验收：“常用搜索 → 基础信息 → 显示方式”能正常打开，且刷新后仍为目标方式；若配置页异常，接口回读成功也不能验收。

## 常用搜索字段

```bash
e10-cli --json form table-view search-field add <objId> <appId> <listId> <fieldId>

# 按前端字段设置面板配置搜索项
e10-cli --json form table-view search-field configure \
  <objId> <appId> <listId> <fieldId> \
  --display-name "单据名称" \
  --default-value "111" \
  --required 0 \
  --full-match 0 \
  --condition like
```

命令必须从当前数据源接口取得完整字段模型，按前端最终保存结构生成搜索项：字段 `id` 与独立的 18 位 `filterId` 不得混用，字段自身 `multiSelect` 原样保留，搜索默认配置单独写入 `listFilterDefaultSets`。保存时完整保留目标终端的其他配置，再独立回读字段及条件关系；`--terminal` 同上（`pc` 只改 PC、`mobile` 只改移动端，另一端原样回传）。

具体配置固定映射：

- `--default-value`：固定默认值，写为 `defaultType="1"` 与 `startValue`；`--clear-default` 清除。`Select` 字段可传选项名称或选项 ID，CLI 必须从当前数据源解析为唯一真实 ID，并保留完整选项对象供前端回显。
- `--required 0|1`：条件是否必填，写为字段级 `required`。
- `--full-match 0|1`：搜索内容是否完整匹配，写入 `listFilterDefaultSets.searchContentFullMatches`。
- `--condition like|eq|...`：必须来自该字段实际允许的条件，同时更新字段层与默认设置层。
- `--display-name`：更新搜索项 `showName`；不得覆盖原字段名和字段 ID。

前端验收：打开“搜索配置”不报异常，目标字段出现在常用搜索字段中；刷新列表后可使用该字段发起搜索。只通过接口回读不能验收。

## 台账显示列/搜索/排序/统计/视图数据条件/行事件/分组/上下级/视图权限/分类搜索

直接改默认台账（nListView）的显示列、搜索条件、排序、顶部统计、视图数据条件。listId 取 `form list-view` 返回的列表视图 ID。默认改 PC 端；`list-columns --terminal mobile` 可改移动端显示列。**保存时先读回真实移动端 mConfig 原样回传，不会清空移动端**（`saveNListConfig` 一次请求里 `config`→PC 端、`mConfig`→移动端，两端列集合/uid 各自独立）。只有明确目标只使用 PC、移动端配置确实不存在时，才加 `--pc-only`。

```bash
# 查看当前显示列
e10-cli form list-columns <objId> <appId> <listId>

# 批量追加字段到显示列 / 移除字段
e10-cli form list-columns <objId> <appId> <listId> --add <fieldId1> <fieldId2>
e10-cli form list-columns <objId> <appId> <listId> --remove <fieldId1> <fieldId2>

# 按文件完整设置业务列顺序、宽度和格式（未列入的业务列会移除）
e10-cli form list-columns <objId> <appId> <listId> --set @columns.json --json
# 详见 references/form/guide-list-columns.md

# 列显示格式：千分位/小数位（Number/Money 列，走列对象 format/decimalLength）
e10-cli form list-format <objId> <appId> <listId> <fieldId> --thousandths --decimal 2
e10-cli form list-format <objId> <appId> <listId> <fieldId> --no-thousandths
# 列显示单位：后缀/前缀（走列 showTrans.ruleConfig，与千分位是两套机制）
e10-cli form list-unit <objId> <appId> <listId> <fieldId> "（元）"

# 配置搜索：--add 进搜索面板，--quick 加顶部快捷筛选（均支持多字段）
e10-cli form list-search <objId> <appId> <listId> --add <fieldId1> <fieldId2>
e10-cli form list-search <objId> <appId> <listId> --quick <fieldId1> <fieldId2>
# 主表字段直接从 ds/fields 解析；明细子字段经 getFormField 单取元数据（ds/fields 合并不展开）

# 配置排序 / 清除（--field 支持多个，按传入顺序多级排序；--order 对所有字段生效）
e10-cli form list-sort <objId> <appId> <listId> --field <fieldId1> <fieldId2> --order ASC
e10-cli form list-sort <objId> <appId> <listId> --clear

# 主表/明细统计完整指南：references/form/guide-list-stats.md
# 明细 count 支持只填 type/subFormId；批量入口：form list-stats detail
# PC/MOBILE 可能共享统计项；以保存后的 mobileStatistics 为准，不能承诺只影响 PC
# 顶部统计：type=sum 求和 / count 计数 / avg 平均 / max 最大 / min 最小
# 可选：thousandths=true 千分位 / decimalPlaces="2" 小数位 / unit="万" 单位（unitType=tenThousand）
e10-cli form list-stats <objId> <appId> <listId> --add '{"fieldId":"...","type":"sum","name":"合同总金额","thousandths":true,"decimalPlaces":"2","unit":"万"}'

# 条件统计：conditions 数组构造明文条件树填 rootdata（发明文保存成功、读回也是明文，无需 LZW 编码）
# func: eq 等于 / neq 不等于 / in 属于 / notIn 不属于 / like 包含 / notLike 不包含 / gt 大于 / lt 小于 / range 区间 / isNull 为空 / isNotNull 不为空
# 单选 Select 用 eq；notEq/between 为兼容别名自动归一为 neq/range；range 的 value 用数组 [起,止]；value 填选项 valueKey、text 填显示名；多条件默认 AND
e10-cli form list-stats <objId> <appId> <listId> --add '{"fieldId":"金额fieldId","type":"sum","name":"研发合同额","thousandths":true,"unit":"万","conditions":[{"fieldId":"项目类型fieldId","func":"eq","value":"研发valueKey","text":"研发"}]}'
e10-cli form list-stats <objId> <appId> <listId> --remove <statId>   # 平台 statisticsList 是 upsert 语义，删除靠标 operation:DELETE（splice 不删）

# 视图数据条件：台账只显示满足条件的数据（走 saveNListConfig config.filter，明文条件树，非独立接口——
# conditionEditor/saveOrUpdate 表单级不挂视图、saveBaseinfo 带 conditionData 都是错误端点）
# func 取值同条件统计（eq 等于 / neq 不等于 / in 属于 / notIn 不属于 / like 包含 / notLike 不包含 / gt 大于 / lt 小于 / range 区间 / isNull 为空 / isNotNull 不为空，单选 Select 用 eq）；value 填选项 valueKey，text 填显示名；多条件默认 AND
e10-cli form list-filter <objId> <appId> <listId> --add '{"conditions":[{"fieldId":"项目类型fieldId","func":"eq","value":"研发valueKey","text":"研发"}]}'
e10-cli form list-filter <objId> <appId> <listId> --clear

# 行事件：点击行数据 NewPage 打开（走 saveNListConfig config.eventGroup，明文 JSON，config+mConfig 都要写）
# --add-page 选页面：pageId 缺省 "1/<objId>"（表单新建布局），"0/<objId>"=显示布局
#   打开方式 openMode（linkInfo.openMode 权威，page.openMode 恒 4）：
#     当前页面=4 / 新窗口=0 / 弹出窗口=5 / 右侧滑出=1(缺省) / 右侧推出=7
#   弹出/滑出/推出 带弹窗宽高（--modal-width/--modal-height，缺省 50%）；滑出/推出 额外带 winSizeNew（--win-size，缺省 100%）
# --add-field 选字段（URL取自行内字段值，urlFieldText/Type自动补）
e10-cli form list-event <objId> <appId> <listId> --add-page '{"pageName":"新建数据"}'
e10-cli form list-event <objId> <appId> <listId> --add-page '{"pageId":"0/<objId>","pageName":"显示布局","openMode":"当前页面"}'
e10-cli form list-event <objId> <appId> <listId> --add-page '{"pageName":"弹窗详情","openMode":"弹出窗口"}' --modal-width 80%
e10-cli form list-event <objId> <appId> <listId> --add-page '{"pageName":"侧滑详情","openMode":"右侧推出"}' --win-size 60%
e10-cli form list-event <objId> <appId> <listId> --add-field '{"urlFieldId":"字段id"}'
e10-cli form list-event <objId> <appId> <listId> --clear

# 字段事件（列点击 list-click，区别于行事件 list-event）：点某列数据打开该行显示布局（带数据 ID）
# 打开方式 --open-mode：当前页面/新窗口/弹出窗口/右侧滑出(缺省)/右侧推出；滑出/推出 --win-size 设宽度（缺省 800px）。具体数值按需求填写：百分比使用 `%`（如 `45%`、`60%`），像素使用 `px`（如 `640px`、`900px`），两种单位不可混用或省略；百分比范围为 0%～100%。
e10-cli form list-click <objId> <appId> <listId> <fieldId> --open-mode 右侧推出 --win-size 50%
e10-cli form list-click <objId> <appId> <listId> <fieldId> --open-mode 右侧推出 --win-size 800px
e10-cli form list-click <objId> <appId> <listId> <fieldId> --target <目标表单objId> --open-mode 弹出窗口
e10-cli form list-click <objId> <appId> <listId> <fieldId> --clear

# 启用分组：台账按某字段分组聚合显示（走 saveNListConfig config.enableGroup 对象 {enable,groupField,groupSize}）
# saveNListConfig 持久化成功，不走 designer/layout/save LZW。group-field 用完整字段对象（自动从 ds/fields 取）
e10-cli form list-group <objId> <appId> <listId> --enable --group-field <分组字段fieldId> --group-size 100
e10-cli form list-group <objId> <appId> <listId> --disable   # 禁用但保留 groupField/groupSize（仅 enable=false）

# 上下级树形展示：根据“上级类型”等自关联字段展示父子层级（走 config.superiorField）
# parent-field 支持字段名称或 ID；必须是主表、单选、关联当前表单自身的 EBuilder 字段
e10-cli form list-hierarchy <objId> <appId> <listId> --enable --parent-field "上级类型" --expand-level 2
e10-cli form list-hierarchy <objId> <appId> <listId> --disable  # 关闭但保留字段及展开设置

# 台账视图权限（查阅/查看权限）：谁能查看这个台账（走 list/permission/save + getList，专用端点，full-replace 语义 omit即删）
# selectedType: all(所有人) / user(人员,带--name) / role(角色,--name 缺省自动查) / matrix(矩阵,用 --add-raw 传整对象)
e10-cli form list-permission <objId> <appId> <listId> --add-all
e10-cli form list-permission <objId> <appId> <listId> --add-user <userId> --name <人员名>
e10-cli form list-permission <objId> <appId> <listId> --add-role <roleId>                # --name 缺省自动从角色树查名
e10-cli form list-permission <objId> <appId> <listId> --add-role <roleId> --share-level 2 # 加同一角色另一个共享级别
e10-cli form list-permission <objId> <appId> <listId> --add-role <roleId> --seclevel 30-80 # 安全级别范围
e10-cli form list-permission <objId> <appId> <listId> --add-raw '{"selectedType":"matrix","name":"...","dataid":"矩阵id",...}'
e10-cli form list-permission <objId> <appId> <listId> --remove <权限id>
e10-cli form list-permission <objId> <appId> <listId> --clear

# 删除指定权限；清理重复“所有人”后保留唯一一条
e10-cli form list-permission <objId> <appId> <listId> --remove <permissionId>
e10-cli form list-permission <objId> <appId> <listId> --remove-all --add-all

# 每条授权对象的两个可配维度（样本坐实，mulinquan 2026-09-02）：
#   安全级别 = levelScope.minShowlevel/maxShowlevel（字符串范围，--seclevel <min>-<max>，如 0-100 / 30-80；role 缺省 0-100、all 缺省空）
#   共享级别 = roleLevel（验证: 总部=1 分部=2 全部=3）。同一角色可按不同共享级别各存一条（同 role 两条 roleLevel 1/2 并存）→ 去重键含 roleLevel
#   幂等：目标(含 roleLevel)已存在时跳过保存，打印「无变化」

# 分类搜索：按选项字段分类筛选（走 saveNListConfig config.searchConditions.groupFilters）
# 仅主表选项类字段（Select/RadioBox/CheckBox），不支持明细字段（产品边界）
e10-cli form list-search-group <objId> <appId> <listId> --add <选项字段fieldId>
e10-cli form list-search-group <objId> <appId> <listId> --remove <fieldId>
e10-cli form list-search-group <objId> <appId> <listId> --clear
```

`list-hierarchy` 与 `list-group` 不可混为一谈：前者按自关联字段建立父子树，后者按普通字段聚合分组。需求出现“上下级”“父级”“树形”“根据上级类型展示”时使用 `list-hierarchy`。字段名不要求固定为“上级类型”，但字段关系必须满足自关联单选。

字段 ID 来自 `form read <objId> --app-id <appId>` 或 `form list-columns` 当前列（系统列如 `2`创建者/`3`创建时间也可增删；`5`数据ID主键自动保留，禁止移除）。显示列命令保存后回读校验，`otherTerminalPreserved:true` 表示另一终端配置核对一致。

## formView 固定闭环

```bash
# 1. 确认目标表单与现有视图
e10-cli form list <appId>
e10-cli form view list <objId> <appId>

# 2. 创建视图并从输出取得 viewId
e10-cli --json form view create <objId> <appId> "<视图名>" --type formView

# 3. 填充已有字段并独立回读
e10-cli --json form view populate <objId> <appId> <viewId>
```

`populate` 只有同时满足以下条件才算服务器验证通过：

- `success=true`
- `componentCount > 0`
- `fieldComponentCount > 0`
- 重复执行返回 `alreadyPopulated=true`

服务器验证通过后仍需用户确认前端不是空画布、字段名称和特殊配置正确。

## 执行与验收

1. 计划中写明表单 objId、视图名称、类型和终端；用户确认后再写入。
2. CLI 先调用 `createView`，再查询该表单的完整视图列表；创建响应本身不是验收。`formView` 随后调用 `populate`：`原 formId + viewId(layoutMultiId)` 读取目标布局，保留目标页面元数据，按目标布局类型重建已有字段组件并保存。
3. 回读以返回的 viewId 优先；服务端未返回 ID 时，才按名称、类型和终端唯一匹配。多个候选视图时停止并让用户确认。
4. `populate` 回读组件数量和字段 ID；用户再确认新视图设计页出现表单既有字段，而非只有“未分组”的空画布。

服务器成功和独立回读成功但尚未前端确认时，只能标记为“待前端确认”。
