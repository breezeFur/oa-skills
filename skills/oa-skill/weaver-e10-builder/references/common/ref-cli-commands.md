# e10-cli 命令参考

> **所有系统交互统一使用 `e10-cli`**。auth 文件自动查找，也可 `--auth <path>` 指定。加 `--json` 输出 JSON 格式。

---

## 工具

| 命令 | 说明 |
|------|------|
| `e10-cli docx read <文件>` | 解析 Word 文档为 markdown + 提取图片到 `_images/`。**禁止自己写 python-docx 脚本** |
| `e10-cli interface import <文件> [--system-pool-name <名称>] [--apply] [--out <文件>]` | 解析 `.docx/.pdf/.md/.txt/.xlsx/.xls` 为 Postman Collection（Excel 有解析限额，超限报错不截断）；默认预览，`--apply` 才调用 ESB 创建系统接口。未传系统池名称时从文档文件名推导；完整规则见 `references/esb-interface/guide-import.md` |

---

## Ecode 项目操作

| 命令 | 说明 |
|------|------|
| `e10-cli project create <name> [desc]` | 新建 Ecode 项目（名称自动追加时间戳） |
| `e10-cli project import <projectId> <zip> --main-url <url>` | 导入 zip 包，`--main-url` **必填** |
| `e10-cli project tree <parentId>` | 查看目录结构 |
| `e10-cli project read <fileId>` | 读取代码文件内容 |
| `e10-cli project update <fileId> <content>` | 更新代码文件（content 以 `@` 开头则为文件路径） |
| `e10-cli project create-file <name> <parentId> [type]` | 新建代码文件（默认 js） |
| `e10-cli project create-folder <name> <parentId>` | 新建文件夹 |
| `e10-cli project delete-file <fileId>` | 删除代码文件 |
| `e10-cli project delete-folder <folderId>` | 删除文件夹（= 删除应用） |

- 导入成功后会在 Ecode 项目下生成应用文件夹
- 二次导入之前先删掉旧应用文件夹（通过 `e10-cli project tree` 找到 folderId）

---

## Ebuilder 应用 & 表单

| 命令 | 说明 |
|------|------|
| `e10-cli app create <name> [desc]` | 新建 Ebuilder 应用（scope=PC_MOBILE，INTERNAL 类型）。`--json` 输出 `{id,name}` |
| `e10-cli app list [--name <关键词>]` | 查询应用列表（扁平 id/name/description） |
| `e10-cli app folder [--type 1/2/3]` | 查看应用目录结构（文件夹+应用树，含发布状态）。1=我管理的/2=我创建的/3=全部 |
| `e10-cli app read <appId>` | 查看应用**详情**（全量配置：名称/描述/简称/范围/目录/组织/发布状态）。`--json` 输出完整对象。走 `/app/info` |
| `e10-cli app edit <appId> [--name] [--desc] [--short-name]` | 编辑应用信息（至少指定一个写参数；内部先读 `/app/info` 再合并提交） |
| `e10-cli app delete <appId>` | 删除应用（软删除，可恢复；存在关联资源会提示先清理） |
| `e10-cli form read <objId> [--app-id <appId>] [--out <file>]` | 读取表单字段。`--app-id` 含明细表字段+Select/RadioBox/CheckBox 选项、**并标注每个字段属于哪张物理表**（`· 物理表: 表1`，JSON 里是 `formTable` 键；多物理表见 `form physical-table list`）；`--out fields.json` 写 UTF-8 JSON（推荐，机器可读）。旧版 `[dir]` 参数写 memo.md，已过时 |
| `e10-cli form read <objId> --app-id <appId> --out fields.json` | 读取字段含选项（Select/RadioBox/CheckBox 自动带 options）。**含明细表字段**，配动作流/联动拿明细 fieldId 用这个 |
| `e10-cli form list <appId>` | 列出应用下的所有表单 |
| `e10-cli form create <appId> <name> <dir> --fields @<json文件>` | 创建表单。`--fields` **必填**。支持 DetailTable(嵌套formFields)、EBuilder(sformId+dataTitle)、relateFrom(联动)。fields.json 字段可带 `"required":true`/`"readOnly":true` 直标（写进布局 comps）。**字段名与平台系统字段重名（标题/创建者/创建时间/数据ID/最后更新人/数据状态）→ 不新建物理字段、复用系统字段**，并把该字段在**布局置为可见**（platform 系统字段默认隐藏；可写 `"singleRow":true` 独占一行、`"hidden":true` 保持隐藏）。`--json` 返回 `skippedSys`。**默认不加菜单**，要入口传 `--menu`（台账菜单 VIEWPORT）；漏加 `e10-cli menu add-table <appId> <objId>` 补。**`--table-name <名>` 自定义数据库表名**（平台前缀如 `uf_` 由 CLI 自动补，传 `cs_khxx` 与 `uf_cs_khxx` 等价；字母开头、只含字母数字下划线；自定义部分受平台长度上限约束——`uf_` + 总长 30 时最多 27 位，越界直接报错不建半张表；建成后回读校验实际表名；仅物理表应用适用） |
| `e10-cli form virtual source-groups` / `sources <groupId>` | 查询 EB 表单和系统业务数据源分组、数据源列表 |
| `e10-cli form virtual dataset-groups` / `datasets <groupId>` / `dataset-info <id>` | 查询数据加工分组、数据集和数据集定义 |
| `e10-cli form virtual fields <appId> --source-id ... --source-group ...` | 校验数据源 ID 字段并读取可映射字段 |
| `e10-cli form virtual create <appId> <name> --source-id ... --source-group ... --fields @json` | 创建虚拟表；`--source-type LOGIC|ETEAMS`，支持 `--layout FLOW|EXCEL`。字段默认沿用来源类型，只允许兼容的同族展示类型 |
| `e10-cli form virtual read <objId> <appId>` | 读取虚拟表来源、字段映射和默认视图信息 |
| `e10-cli form virtual add-fields <objId> <appId> <formId> --source-id ... --source-group ... --fields @json` | 从原数据源向虚拟表增加字段 |
| `e10-cli form add-field <objId> <appId> <name> <type> [title]` | 添加字段。`<type>`=componentKey（Text/Select/Employee/Money/DetailTable 等同 form create）；`[title]` 字段显示名，不传同 name。Select 类型需单独 `field-options` 配选项。**默认「增量插入」——只往布局里加这一个字段，不动其它组件、不动样式模板、不动位置**（读快照 → 加一对组件 → 保存）。**`--reinit` 改成整表重建**（initLayout：换样式模板 + 重排所有已有位置 + 标签组件全部换新 id）——**只在是自己建的表上用**；不是自己建的表（尤其字段多、手工调过版式的）绝不能用。**布局里没有同类型字段可参照时命令会中止**并说明，这是设计如此（新组件的键集只能从同类型的现成组件抄，按类型名拼会静默渲染异常）；此时要么先在设计器里手工加一个同类型字段，要么显式 `--reinit`。**`--required` 设为必填**（写布局组件）。**`--sub-form-id <明细表subFormId>` 在明细表里加字段**（同样走增量）。**自动为字段标题建立多语言标签**并写进字段记录。Number 类型：**`--percent` 百分比显示**（numberType=percentage，缺省 1 位小数）、**`--default <值>` 默认值**（如 `--default 1000` 工时单价默认 1000）、`--precision <n>` 精度。**EBuilder/Flow 类型**：`--sform-id <目标表单objId>`（EBuilder 表关联 / Flow 浏览-流程字段，数据来源=浏览流程）。EBuilder 字段**自动配关联浏览弹窗显示列**（=目标表全部业务字段，去系统字段）。**`--multiple` 多选**（人员/部门/EBuilder/Browser 默认单选；**下拉 Select --multiple → SelectMultiple 类型**）。**`--max-len <n>` 文本最大长度**（Text 缺省 100、TextArea 缺省 4000）。**`--single-row` 独占一行显示**。**`--option-template <模板ID或名>` Select 绑定选项预设模板**（选项来自模板，与 `field-options` 二选一）。**`--data-key` / `--column-name` 分别指定字段编码与数据库列名**（两者是两个独立的东西，可分别指定；只给 `--data-key` 时列名跟随，都不给则同为字段名拼音首字母） |
| `e10-cli form detail-table list/read <objId> <appId> [...]` | 列出明细表，或读取指定明细表的二级明细开关与配置 |
| `e10-cli form detail-table sub-detail candidates <objId> <appId> <父明细表>` | 查询当前父明细可选择的子明细；列表排除自身、直属父级和祖先。反转父子方向时，先 `remove` 原关系，再查询新父级候选并 `add` 反向关系 |
| `e10-cli form detail-table sub-detail add <objId> <appId> <父明细表> --target <子明细表> --target-field <子级文本标识> [--parent-field <父级标识>] [--default-expand]` | 保留已有关系并增加或更新一条二级明细关系。父级标识缺省 `rowId`，也支持 Text/RadioBox/Select；子级标识必须是 Text。表和字段可写名称或 ID，保存后自动回读 |
| `e10-cli form detail-table sub-detail set <objId> <appId> <父明细表> --target <子明细表> --target-field <子级文本标识> [--parent-field <父级标识>] [--default-expand]` | 完整替换父明细的子明细配置。另有 `remove --target <子明细表>` 删除指定关系，`enable`、`disable`（保留配置）、`clear`（清空配置）；完整规则见 `references/form/guide-form-sub-detail.md` |
| `e10-cli form edit-field <objId> <appId> <fieldId> [选项]` | 编辑字段属性。`--title` 显示名、**`--type <类型>` 改字段类型**（取值同 `add-field`，如 `Text`/`Number`/`Date`/`Select`/`Department`；走读-改-写，**不用删字段重建**，显示名/列名/位置都保留；改成 `EBuilder`/`Flow` 必须同时给 `--sform-id`）、`--required`/`--no-required`、`--sform-id`（改EBuilder关联）、`--relate-from`（值带出）、**`--multiple`/`--no-multiple`**（人员/部门/EBuilder/Browser 多选切换）、**`--data-title`**（关联字段的标题栏，写 `dataTitle`）。**`--required`/`--no-required` 写的是布局组件**（必填只存在于布局里，字段定义没有这个键），命令会顺带把布局一并保存。改成 `EBuilder` 或换关联表时，**浏览显示列按新目标表自动补齐**（只在没配过、或旧列不属于新目标表时才写，不冲掉手工配的）。**`--data-key` / `--column-name` 分别改字段编码与数据库列名**（两者独立；只给 `--data-key` 时列名跟随）。**⚠ 字段已有数据时平台拒绝改动结构**（显示名例外）——报「此列已存在数据不可修改数据库字段名称」，该文案与实际情况不符，它拦的不止字段名 |
| `e10-cli form field-lang get <objId> <appId> <fieldId>` | 查看字段名称的中英文多语言配置；未配置时返回当前中文名称和 `configured:false` |
| `e10-cli form field-lang set <objId> <appId> <fieldId> --zh <中文> --en <English>` | 设置字段名称多语言。先保存多语言标签，再读取完整字段并回写 `labelObj.title`，不会覆盖字段其他属性 |
| `e10-cli form serial-mark set <objId> <appId> <fieldId> --segments @<json>` | **表单编号**（纯建模表）：用 JSON 数组组合任意编号规则，数组顺序即拼接顺序。段类型 `fixed`/`year`/`serial`/`field`/`system`/`date`；field 段可 inline `shortName` 代字映射。子命令组：`set`(配置,--segments) / `add-segment`(增量追加段) / `short-name`(代字 list/set) / `read`(查看) / `fields`(查可绑定字段) / `enable`(启用) / `disable`(停用，可加 `--field <fieldId>` 只停某一个字段的编号) / `clear`(解除绑定)。**`disable` 停用 ≠ `clear` 解除**：停用只关开关（`isUse=0`），绑定记录与组成段原样保留、可 `enable` 恢复；解除走删除接口，绑定不可逆。要「暂时不生成编号」一律用 `disable`。被编码字段平台自动只读。**⚠ 仅对未绑流程的纯建模表有效——eb表单绑流程后表单编号字段在流程提交时不生效，编号改走流程编号（`workflow numbering`，落到 REQUEST_NO 系统字段）** |
| `e10-cli form field-options <objId> <appId> <fieldId> --options @<json> [--default <key>]` | 设选项/默认值。options.json: `[{"name":"选项名","valueKey":"可选"}]`；`--default` 用平台生成的长 valueKey（`form read --app-id` 获取），不是 name |
| `e10-cli form option-template <list\|read\|create\|copy\|delete>` | **Select 选项预设模板管理**（下拉选项复用：多个表单共享一套选项，模板改了各表单跟着变）。`list [--system]` 列模板（默认自定义模板，--system 看系统内置）；`read <模板ID> [--flat]` 看选项树；`create <名称> --options @<json> [--level 1] [--describe 文本]` 建模板（options.json: `[{"name":"低","valueKey":"10","children":[]}]`，**valueKey 必须数字**，children 嵌套=多级）；`copy <模板ID>` 复制（系统 default 模板不可复制）；`delete <模板ID>` 删模板（被引用时平台拒绝）。**字段引用模板**：`form add-field --option-template <模板ID或名>` 或 fields.json 写 `"optionTemplate":"模板名"`（Select 专有，选项不内联） |
| `e10-cli form linkage add <appId> <objId> <name> --config @<json>` | 添加字段显隐联动规则（`conditions[]` 用 fieldId + operator + value/options；`actions[]` 用 prop + fields[]）。**「为空 / 不为空」的 operator 写 `NULL` / `NOT_NULL`**（写 `EMPTY` 会被归一，但写别的平台不认的码会报一句与条件无关的写库异常）。目标字段 `dataKey` 留空即可（平台按 fieldId 定位）。多条件关系用 `detailType`（`OR`=任一 / `AND`=全部，界面就叫「任一」「全部」，不写则由平台取默认）；生效维度用 `effect`（不写=当前表单，`"formLayout"`=表单布局，或给 `{effectType,effectName,effectValue}` 对象；**布局维度要的是 multipleLayoutId，命令自己查**）。**本命令只有 add / list，没有 delete** —— 建错要去设计器里删。详见 `form/guide-form-linkage.md` |
| `e10-cli form relate <appId> <objId> <目标字段> --from <源字段>` | **HRM 值带出联动**：源字段为表内 Employee（人员）或 Department（部门）类型，换源自动填目标字段（换申请人→填邮箱/工号/部门；换所属部门→填部门编号/上级部门）。`--key` 从平台清单校验（默认 Employee=department、Department=name），`--title` 指定显示名（默认属性中文名）。详见 `form/guide-form-linkage.md` |
| `e10-cli form delete-field <objId> <appId> <fieldId...>` | **删除字段**（可一次多个，批量）。**仍被布局引用的字段平台不允许删除**（报「当前字段已被布局引用，不允许删除」）；加 `--force` 时 CLI 先从布局移除再重试——会**连字段的标题组件一起摘**（一个字段在布局里是「字段本体 + 标题标签」两个组件），否则表单上会留下孤儿标签。字段**有数据**时同样删不掉 |
| `e10-cli form delete <objId> <appId>` | 删除**整个表单**（不是字段；删字段用上面的 delete-field） |
| `e10-cli form permission data add <objId> <appId> --org-type <类型> [--org-id <id>] --rights <view/edit/delete...> [--file-rights <view/download...>]` | **表单数据权限**，`1/view=查看`、`2/edit=编辑`、`3/delete=删除`，可任意组合；附件 `401/view=查看`、`402/download=下载`。固定写入 `obj_data_admin` 并按新增权限 ID 回读。授权对象支持 all/role/department/company/employee/group/post；all 的 orgId 自动为 0 |
| `e10-cli form permission imp-exp <list\|add> <objId> <appId> ...` | **导入导出权限**（独立分类 `data_imp_exp`，⚠ 勿用 `data add` 加——共享权限只有 查看/编辑/删除 三种，导出/导入不在其中）。`list` 查看；`add --org-type <类型> [--org-id] --rights <export/import/delete-import...> [--update-import] [--export-details] [--export-attachment] [--export-field-range listShowField|all]`。`export=8`、`import=9`、`delete-import=93`（93 须与 import 同选，自动带更新导入）；添加后按权限 ID 回读 `impRightList` 校验。删除同 `permission remove --right-id` |
| `e10-cli form permission <list\|add\|remove\|rebuild> <objId> <appId>` | 权限通用管理及兼容入口。新建权限与数据权限分开；旧 `add --right-type` 保留兼容。`list` 查看全部分类；`remove --right-id <id[,id...]>` 删除一条或多条权限；添加后提示 `isShowRebuild=2` 时执行 `rebuild` |
| `e10-cli form list-view <objId> <appId>` | 查看台账/数据列表（获取 viewId 用于菜单配置） |
| `e10-cli form list-columns <objId> <appId> <listId> [--add <fieldId...>] [--remove <fieldId...>] [--set @columns.json] [--terminal pc/mobile] [--pc-only]` | 查看/批量设置台账显示列。增量追加、移除或整组指定顺序/列宽/格式；整组模式与增删互斥。支持主表和明细子字段，保留已有列未指定属性、事件及数据主键；一次保存并回读核对目标列和另一终端。详见 `references/form/guide-list-columns.md` |
| `e10-cli form list-unit <objId> <appId> <listId> <fieldId> <后缀> [--prefix <前缀>] [--clear] [--pc-only]` | 设置台账列显示**单位**（后缀/前缀）。平台无字段级单位属性，靠列表列配置 `showTrans.ruleConfig.suffix/prefix` 实现。如 `form list-unit ... <fieldId> "（元）"` 让列显示单位；`--clear` 清除 |
| `e10-cli form list-format <objId> <appId> <listId> <fieldId> [--thousandths] [--no-thousandths] [--decimal <n>] [--clear] [--pc-only]` | 查看/设置台账列**千分位/小数位**（Number/Money 列）。不加参数显示当前；`--thousandths` 开千分位（列 `format:"THOUSANDS"`）、`--no-thousandths` 关、`--decimal <n>` 小数位数（`decimalLength`）、`--clear` 清除恢复默认。与 `list-unit`（单位，走 `showTrans`）是两套不同机制。**自动保留移动端配置** |
| `e10-cli form list-click <objId> <appId> <listId> <fieldId> [--target <formObjId>] [--open-mode <模式>] [--win-size <尺寸>] [--clear] [--pc-only]` | 设置台账列**点击跳转**。`--open-mode` 支持当前页面/新窗口/弹出窗口/右侧滑出/右侧推出；`--win-size` 仅用于滑出/推出，具体数值按需求填写：百分比使用 `%`（0～100），像素使用 `px`，两种单位不可混用。缺省 `800px` |
| `e10-cli form ebuilder-columns <objId> <appId> <fieldId> [字段名/ID...] [--clear]` | 设置 EBuilder 关联字段的**浏览显示列**（存在字段配置 `ffDisplayColumns:{id,name}[]`）。**缺省查看**：列出当前显示列 + 目标表单全部**业务字段候选**（系统字段已自动过滤，不设显示列时浏览走平台默认列会带系统字段）；**传目标表业务字段名/ID 设置**，系统字段会被拦截提示"系统字段不能设为显示列"；`--clear` 清空。关联浏览显示哪些字段（只留业务字段） |
| `e10-cli form ebuilder-scope <get\|set\|clear> <objId> <appId> <fieldId>` | **浏览数据定义 → 数据范围设置**（关联浏览字段，限定被关联数据须满足条件才可选，如关联客户只选"客户状态=启用"的）。走 `browserDataScope` 接口（独立于字段布局）。`set --rules '[{"field":"客户状态","operator":"eq","value":"启用"}]'`（选项类 value 用选项名，CLI 自动解析 valueKey）；`--logic and/or` 多规则关系；`--fill-null` 关联字段为空时填充；`get` 读已设条件；`clear` 清空。**这是关联浏览筛选的正解**，旧 `ebuilder-filter` 走 layout/save 不被设计器识别 |
| `e10-cli form validate list <objId> <appId>` | 查看表单**查重规则**（字段重复校验，多字段 AND）。`add <objId> <appId> <字段名...> [--help 提示] [--remind]` 新增（缺省禁止提交 NOSUBMISSION，`--remind` 仅提醒）。**`--help` 会建成多语言标签、存的是标签 id**（平台只收 id，传文本会被拒「提示内容格式不正确」；`list` 会解回文本显示，缓存原因刚建完约 10 秒内可能仍显示 id）；`delete <objId> <appId> <ruleId>` 删除。项目名称重名/工时日期重复不允许 |
| `e10-cli form add-detail-table <objId> <appId> <明细表名> [首字段名] [--init]` | 给**已存在的主表**加明细子表（saveSubForm 建子表 + 加首字段使其可见）。`--data-key <物理表名>`、`--first-field-type <类型>`（默认 Text）。⚠ **空子表平台会过滤掉、布局里看不见**，首字段名强烈建议传；`--init` 建完把 DetailTable 组件放进布局。后续往明细里加字段用 `form add-field --sub-form-id <subFormId>`：建表时一次性带明细用 `form create` 的 fields.json `DetailTable`+`formFields` |
| `e10-cli form delete-detail-table <objId> <appId> <subFormId\|明细表名>` | **删除明细表**（连带表里的字段）。平台不允许删**仍被布局引用**的明细表（报「当前【X】明细表已被布局引用，不允许删除」）—— 明细表只要在表单上就必然被引用，所以多数情况要加 `--force`：先把这张表的组件（本体 + 每列的「字段本体 + 标题标签」）从布局摘掉、清掉 workbook 里的残留，再删。删除是**软删**，记录仍在但不再算数 |
| `e10-cli form physical-table list <objId> <appId>` | 列出表单的**全部物理表**（含主表），带 `formTableId` / 显示名 / 库表名 / 表类型(`MAIN`\|`SUBSIDIARY`) / 字段数。走 `getFormAGroupList`（设计器「字段管理」那排 chip 的数据源）。**只列物理表**，明细表要用 `form detail-table list` |
| `e10-cli form add-physical-table <objId> <appId> --name <名> --table-name <uf_xxx>` | 给**已存在的表单**加一张**附属物理表**（设计器「字段管理 → **其他**」页签，用于一个表单的字段分散到多张物理表、字段数过多时的容量兜底）。走 `saveFormTable`，`tableType=SUBSIDIARY`；输出 **`formTableId`**（后续加字段/改名/删除都要用它，忘了用 `form physical-table list` 找）。`--table-name` **必填**（平台的建议命名规则未抓到报文，不猜）。⚠ 与明细表是两根轴，别混 —— 见 `references/form/guide-form-physical-table.md` |
| `e10-cli form add-physical-field <objId> <appId> <formTableId> <字段名> <类型> [标题]` | 往**已有的附属物理表**里加字段。机制是 `saveFormFieldNew` + jsonObj 里的 `formTableId`（**不是**批量端点）。选项与 `form add-field` 同名同义，**两者共用同一份字段构造器**。⚠ **不碰布局** —— 字段不会自动进表单布局。每次写完**回读确认**（平台对形状不认的字段会回 200 却静默不落库） |
| `e10-cli form rename-physical-table <objId> <appId> <formTableId> --name <新名> --table-name <原表名>` | 改物理表**显示名**（同一个 `saveFormTable` 端点，带 `formTable.id` 即改名）。`--table-name` 要**原样回传** |
| `e10-cli form delete-physical-table <objId> <appId> <formTableId...>` | 删除物理表（`deleteFormTable`，可一次删多张）。⚠ **表里的字段一并删除，不可逆**。表 id 用 `form physical-table list` 查 |
| `e10-cli form list-search <objId> <appId> <listId> [--add <fieldId...>] [--quick <fieldId...>] [--remove <fieldId>] [--pc-only]` | 查看/配置台账**搜索条件**。`--add` 进搜索面板、`--quick` 加顶部快捷筛选（均支持多字段）、`--remove` 移除。主表字段直取 ds/fields；明细子字段自动 fallback `getFormField` 单取元数据。**自动保留移动端配置** |
| `e10-cli form list-sort <objId> <appId> <listId> [--field <fieldId...>] [--order ASC\|DESC] [--clear] [--pc-only]` | 查看/配置台账**排序**。`--field` 支持多个（按传入顺序多级排序，`--order` 对所有字段生效）、`--clear` 清除。**自动保留移动端配置** |
| `e10-cli form list-stats <objId> <appId> <listId> [--add <json或@文件>] [--remove <statId>] [--pc-only]` | 主表/明细顶部统计，sum/count/avg/max/min、条件及格式；明细 count 支持 `{ "type":"count", "subFormId":"..." }`。保存后回读、保护移动端；平台可能共享两端统计，输出 mobileStatistics。详见 `references/form/guide-list-stats.md` |
| `e10-cli form list-stats detail <objId> <appId> <listId> <subFormId> [--fields <fieldId...>] [--name-prefix <文本>] [--pc-only]` | 为明细数值字段批量生成 sum 和一项子表 count；重复运行复用同名同配置项 |
| `e10-cli form list-filter <objId> <appId> <listId> [--add '<json>'] [--clear] [--pc-only]` | 查看/配置**视图数据条件**（台账只显示满足条件的数据）。`--add '{"conditions":[{"fieldId":"...","func":"eq","value":"研发valueKey","text":"研发"}]}'`（func: eq 等于 / notEq 不等于 / in 属于 / notIn 不属于 / like 包含 / notLike 不包含 / gt 大于 / lt 小于 / between 介于 / isNull 为空 / isNotNull 不为空，单选 Select 用 eq；value 填选项 valueKey、text 填显示名；多条件默认 AND）、`--clear` 清空。走 saveNListConfig config.filter（明文条件树，非独立接口）。**自动保留移动端配置** |
| `e10-cli form list-event <objId> <appId> <listId> [--add-page '<json>'] [--add-field '<json>'] [--open-mode <模式>] [--modal-width <pct>] [--modal-height <pct>] [--win-size <pct>] [--clear] [--pc-only]` | 查看/配置**行事件**（点击行数据 NewPage 打开表单布局）。`--add-page '{"pageId":"1/<objId>","pageName":"新建数据","openMode":"右侧滑出"}'` 选页面方式（pageId 缺省 `1/<objId>` 新建布局，`0/<objId>`=显示布局）、`--add-field '{"urlFieldId":"字段id"}'` 选字段方式（URL取自行内字段值，urlFieldText/Type自动补）、`--clear` 清空。**打开方式** `--open-mode`（或在 JSON 里写 `openMode`）：当前页面/新窗口/弹出窗口/右侧滑出(缺省)/右侧推出；弹出/滑出/推出 用 `--modal-width`/`--modal-height`（缺省 50%），滑出/推出 用 `--win-size`（缺省 100%）。走 saveNListConfig config.eventGroup（明文 JSON，config+mConfig 都写）。**自动保留移动端配置** |
| `e10-cli form list-group <objId> <appId> <listId> [--enable --group-field <fieldId> [--group-size N]] [--disable] [--pc-only]` | 查看/配置**启用分组**（台账按某字段分组聚合显示）。`--enable --group-field <分组字段id> [--group-size N 默认100]` 启用/换分组字段、`--disable` 禁用（保留 groupField/groupSize 仅 enable=false）。走 saveNListConfig config.enableGroup（对象，持久化，不走 layout/save LZW）。**自动保留移动端配置** |
| `e10-cli form list-hierarchy <objId> <appId> <listId> [--enable --parent-field <名称或fieldId> [--expand-level N]] [--disable] [--pc-only]` | 查看/配置**上下级树形展示**。上级字段必须是主表中单选、关联当前表单自身的 EBuilder 字段（常见名称“上级类型”）；与普通 `list-group` 分组聚合不是同一能力。走 `saveNListConfig config.superiorField`，保存后独立回读并自动保留移动端配置 |
| `e10-cli form list-permission <objId> <appId> <listId> [--add-all] [--add-user <userId> --name <name>] [--add-role <roleId> [--name <name>]] [--add-matrix <矩阵id> --name <name>] [--share-level <n>] [--seclevel <min>-<max>] [--add-raw '<json>'] [--remove <id>] [--remove-all] [--clear]` | 查看/配置**台账视图权限**（谁能查看这个台账）。`--add-all` 所有人（自动把空 dataid 与 0 视为同一主体，避免重复）、`--add-user` 人员、`--add-role` 角色、`--add-matrix` 矩阵。`--remove <id>` 删除指定权限；`--remove-all` 删除全部“所有人”，与 `--add-all` 同用可清理重复后只保留一条；`--clear` 清空全部。保存走 `list/permission/save` 全量覆盖并回读。另支持共享级别和安全级别范围 |
| `e10-cli form list-search-group <objId> <appId> <listId> [--add <fieldId>] [--remove <fieldId>] [--clear] [--pc-only]` | 查看/配置**分类搜索**（按选项字段分类筛选）。`--add <选项字段fieldId>`（须已在显示列）、`--remove <fieldId>`、`--clear`。走 saveNListConfig config.searchConditions.groupFilters（视图级明文）。**仅主表选项类字段 Select/RadioBox/CheckBox，不支持明细字段（产品边界，传明细报错）**。listGroupSets 留空由平台运行时生成 |
| `e10-cli form nlist apply <objId> <appId> <listId> <template>` | 配置**列表式视图**（台账）的显示列：模板是二维数组（行 → 列），列项可绑表单字段（`fieldId`）或做**自定义文本**列（不给 `fieldId`、给 `html`，里面用 `{{字段名}}` 插入表单字段）。自动读移动端槽位一并写入。`show` 查看当前配置。⚠ 仅对列表式(NList)生效，表格式用 `form table-view`。详见 `form/guide-list-custom-text.md` |
| `e10-cli form view list <objId> <appId> [--with-comps]` | 列出表单全部视图。`--with-comps` 额外拉每个视图布局 comps 数、标出空视图（NList 数据视图会显示「读取失败」，正常） |
| `e10-cli form view rename <objId> <appId> <viewId> <新名称>` | 修改已有默认台账（nListView）的名称，保留原视图 ID 和配置，并在保存后回读确认。需求名称与默认名称不一致时统一用此命令，不新建重复视图 |
| `e10-cli form view create <objId> <appId> <视图名> [--type formView\|kanbanView\|calendarView\|mindMapView\|multiView] [--terminal PC\|MOBILE] [--layout-type FLOW\|EXCEL] [--detail <明细名>] [--sub-form-id <明细subFormId>]` | 给**已有表单**添加视图。`formView` 创建后是空布局，需续跑 `form view populate` 填字段；`kanbanView`/`calendarView`/`mindMapView`/`multiView` 建视图实体。**multiView 数据维度**：缺省主表；明细表维度用 `--detail <明细名>`（按名解析）或 `--sub-form-id <明细subFormId>`（直传），传值即明细维度（`subFormMain:true`）。**台账(NList)视图**用 `form table-view create`，不在此命令 |
| `e10-cli form view populate <objId> <appId> <viewId>` | 把已有字段按布局类型填入新增的 formView（视图为空时用这个填充） |
| `e10-cli form native <子命令>` | **原生表单引擎**（formdatareport/biaoge，非 Ebuilder；只有 formId、无 objId、无 appId）的命令组：`create <名称>` 建表、`read <formId>` 读字段、`add-field` / `add-detail-table` / `init` / `field-group`，以及 `list [--keyword]`（存活表单，名称模糊搜）、`trash`（回收站）、`delete <formId...>`（停用→检查→删除，进回收站，删后回读确认）。**注意与 EB 表单不通用**：URL 前缀 `/api/formdatareport/...`、body module `biaoge` 或 `formdatareport` 视接口而定 |
| `e10-cli form layout read <objId> [--view-id <id>]` | 读表单布局结构（comps 坐标/只读）。不传 `--view-id` 读默认布局，传则读指定视图 |
| `e10-cli form layout init <objId> [--style-template <名\|id>] [--view-id <id>] [--read-only] [--required] [--disable-edit] [--single-row]` | 初始化/重建表单布局（initLayout）：**换样式模板** + 覆盖字段 readOnly/required/disableEdit/singleRow（不传这些开关则**保留字段已有设置**）。**⚠ 样式模板流式与表格式是两套**，同名不同 id，按表单实际布局类型实时查（传错套会直接报错并列出可用项；**平台对跨套 id 不报错、只会静默忽略，表现为"命令成功但样式没变"**）。缺省：流式=标准版、表格式=表格版。完整模板表见 `form/style-templates.md`。**建表时不能指定样式，只能建完再用本命令换** |
| `e10-cli form group <objId> <appId> --groups '{"基本信息":["字段名/fieldId",...]}'` | 给**已建好的 eb 表**加字段分组（折叠容器）。建组 saveFieldGroup → 分配 updateFormFieldGroup → initLayout generateCollapse 渲染。`--groups` 可 `@文件`；`--required` 同时设分组内字段必填；同名分组复用不重复建（去重）。建表时一次性带分组用 `form create` 的 fields.json `group` 属性 |
| `e10-cli form data add <objId> <appId> <json>` | 写入表单数据（`@` 开头为 JSON 文件路径）。JSON key 可用 fieldId 或字段名；Select/RadioBox 值填选项名（自动解析 valueKey）或 valueKey、CheckBox/SelectMultiple 用数组、TextArea 直接值、Employee/Department 用 ID。详见 `form/guide-form-data.md` |
| `e10-cli form data list <objId> [--page <n>] [--size <n>]` | 查询表单数据（**只含主表**）。`--page` 页码（缺省1）、`--size` 每页条数（缺省1000；不传 pageInfo 平台默认卡 10） |
| `e10-cli form data detail <objId> <appId> <dataId> [--no-detail]` | 读一条数据详情，**默认连明细一起读**（`--no-detail` 只要主表）。要明细用这条，`list` 不返回明细。详见 `form/guide-form-data.md` |
| `e10-cli form data update <objId> <appId> <dataId> <json> [--detail-mode cover\|append]` | 按数据 ID 修改（`@` 开头为文件路径）。只需写要改的字段；带明细表名即处理明细，缺省 `cover` **整表覆盖**，`append` 只追加 |
| `e10-cli form data delete <objId> <dataId>` | 删除一条表单数据 |

### 表单按钮

| 命令 | 说明 |
|------|------|
| `e10-cli form button list <objId> <appId>` | 列出所有按钮 |
| `e10-cli form button add <objId> <appId> <name> [--url <url>\|--open-view <视图>\|--open-layout <表单>\|--start-workflow <流程>] [--layout-type 新建\|编辑\|显示] [--map "目标字段:来源字段"...] [--target-app <appId>] --view <来源视图> --position <位置...>` | 添加通用打开页面按钮。支持固定 URL、平台视图、表单布局及流程快捷入口。`--map` 把当前行的来源字段传出去，可多项，但**两种动作的写法不同**：视图/布局/流程动作写 `"目标字段:来源字段"`，**URL 动作写 `"参数名:来源字段"`**（参数名会成为目标 URL 的查询键）。⚠ **URL 动作的页面类型缺省 `LINK`**（平台设计器对 URL 路径用的就是这个；`CUSTOMPAGE` 是「自定义页面」，`pageId` 要页面 id，装 URL 路径点不开）。⚠ **平台不认 URL 里的 `{字段}` 占位符**，传参只能用 `--map`。当前行映射只允许行上/行末下拉；右上按钮无单行上下文。目标名称不唯一时使用 ID，保存后回读动作和映射 |
| `e10-cli form button action-set <objId> <appId> <buttonId> [--open-view ...\|--open-layout ...\|--start-workflow ...] [--map ...]` | 更新已有自定义按钮的单一 `openpage` 动作，保留按钮位置和权限；适合修正目标页面或动态字段映射，避免重复创建同名按钮 |
| `e10-cli form button toggle <objId> <appId> <buttonId>` | 启用/禁用按钮 |
| `e10-cli form button position <objId> <appId> <buttonId> [--view <视图...> --position <位置...>] [--show-position <json或@文件>] [--replace]` | 设置已有按钮位置并回读验证。默认合并、保留未指定页面；`--replace` 全量替换。视图支持 ID/唯一名称/新建/编辑/显示；多台账不能省略具体视图。系统按钮适用，保留动作权限及返回的日志/提示配置。详见 `references/form/guide-form-button.md` |
| `e10-cli form button views <objId> <appId> <buttonId>` | 读取该按钮可选视图及当前 showPosition，配置前先查询 |
| `e10-cli form association list/get <objId> <appId> [associationId]` | 查询关联页签列表或详情；get 必须传 associationId，详情含目标视图、筛选映射和权限 |
| `e10-cli form association views <objId> <appId> [--target-app <id>]` | 查询可绑定视图及所属表单 |
| `e10-cli form association fields <objId> <appId> --view <viewId> [--target-app <id>]` | 查询来源表单字段和目标视图字段 |
| `e10-cli form association create <objId> <appId> <name> --view <viewId> --permissions <json或@文件> [--layouts 显示 编辑] [--terminals PC MOBILE] [--mappings <json或@文件>]` | 创建关联页签；默认仅显示布局、PC+MOBILE、启用。权限必须显式提供，筛选映射为 [{targetField,sourceField}] |
| `e10-cli form association update <objId> <appId> <associationId> [--name <名>] [--view <viewId>] [--layouts 显示 新建 编辑] [--terminals PC MOBILE] [--enabled true/false] [--mappings <json或@文件>]` | 保留未指定配置；布局和终端为集合替换；显示=0，新建=1，编辑=2，none 关闭全部布局。仅启停走独立接口并回读；多动作时传 --action |
| `e10-cli form association set-filter <objId> <appId> <associationId> --mappings <json或@文件> [--action <id>]` | 替换目标视图动作的数据筛选字段映射，区别于权限条件 |
| `e10-cli form association clear-filter <objId> <appId> <associationId> [--action <id>]` | 清空指定视图动作的数据筛选映射 |
| `e10-cli form association set-condition <objId> <appId> <associationId> --perm <序号或类型> --rules <json或@文件> [--logic and/or]` | 设置页签权限条件，来源表单字段；与关联目标视图数据筛选独立 |
| `e10-cli form association clear-condition <objId> <appId> <associationId> --perm <序号或类型>` | 清空指定权限条件；完整指南见 references/form/guide-form-association.md |
| `e10-cli form button info <objId> <appId> <buttonId>` | 查看按钮详情 |
| `e10-cli form button sort <objId> <appId> <sourceId> <targetId>` | 调整按钮排序 |
| `e10-cli form button delete <objId> <appId> <buttonId>` | 删除按钮 |

> **除非用户明确要求，否则不要往表单写入任何数据。** 表单创建完成后只需确认字段正确即可，不要自动插入测试数据。

| `e10-cli form field-linkage list <appId> <objId>` | 字段联动（跨表带出赋值）：列出联动 |
| `e10-cli form field-linkage read <appId> <objId> <id>` | 回读单条（inFields/outFields） |
| `e10-cli form field-linkage fields <appId> <formId>` | 查源表可带出字段 |
| `e10-cli form field-linkage delete <appId> <objId> <ids...>` | 删除（批量） |
| `e10-cli form field-linkage add <appId> <objId> --trigger <字段名> --target <字段名> --hops "<objId:字段名,...>"` | 新增。`--hops` 多跳链式（单跳用 `--source-form/--query-field`）。**Text 字段必须多跳取名称**。详见 `form/guide-field-linkage.md` |
| `e10-cli form formula-linkage list <appId> <objId>` | 函数联动（**本表**字段间公式赋值，`linkageType=excel`）：列出 |
| `e10-cli form formula-linkage read <appId> <objId> <id>` | 回读单条（含公式表达式与参数） |
| `e10-cli form formula-linkage events <appId> <objId>` | 列出可用的触发事件（值改变时 / 载入时 / 创建数据时 …） |
| `e10-cli form formula-linkage columns <appId> <objId>` | 列出可引用/可触发的字段（业务字段 / 系统模块字段分两桶） |
| `e10-cli form formula-linkage add <appId> <objId> --target <字段> --expression <函数体>` | 新增函数联动。`--event`（默认 `changeField`）、`--trigger <字段...>`（字段级事件必填）、`--effect form\|formLayout`（生效维度，默认当前表单）、`--name`。表达式**只给右侧**，左侧 `{主表.目标}=` 自动拼。**目标只能是业务字段**，模块字段可作来源/触发。详见 `form/guide-formula-linkage.md` |
| `e10-cli form formula-linkage update <appId> <objId> <id> [--event] [--trigger] [--effect] [--name] [--state on\|off]` | 改触发条件/生效维度/名称/启停。不传则沿用现有 |
| `e10-cli form formula-linkage delete <appId> <objId> <ids...>` | 删除（批量）。`form field-linkage delete` 删不掉这类，会报错指路 |
| `e10-cli form formula set <objId> <appId> --target <fieldId> --expression "<公式>"` | 给 eb 表字段**绑定**计算公式。`{主表.字段}` / `{明细表名.字段}`（平台存储格式）与设计器的 `[字段]` 两种写法都收，保存前归一化成花括号再下发。`--name`、`--return-type`（不传按目标字段类型推断）。**`--formula-id <id>` 原地更新已有公式**（平台认这个字段：不新建、返回 id 不变、字段绑定不受影响），不传才是新建；更新时不传 `--name` 会沿用原公式名，不会被改成「公式_&lt;时间戳&gt;」。另：`formula get <id>` / `list <objId> <appId>` / `functions`。**⚠ 公式语法四条**：函数名必须大写（自定义 JS 脚本函数除外）、逻辑比较用 `==`、给字段赋值用 `=`、跨表粘贴要换掉非本表字段变量 —— 写错**不报错**只是算不对，见 `references/form/guide-form-formula-functions.md` |

> **创建表单流程**：
> 1. 读取 `references/form/guide-create-form.md` 了解标准创建流程；确定字段类型和参数时读取 `references/form/ref-form-fields.md`
> 2. 与用户确认所有字段名和字段类型
> 3. 将字段定义写入临时 JSON 文件（格式：`[{"componentKey":"Text","fieldName":"姓名"},...]`）
> 4. 执行 `e10-cli form create ... --fields @<临时文件路径>`
> 5. 涉及人员的字段统一使用 Employee 类型，不要用 Text

---

## 角色

| 命令 | 说明 |
|------|------|
| `e10-cli role list` | 列出所有角色（树形结构，含层级关系） |
| `e10-cli role create <name>` | 创建角色，`--parent <id>` 指定父角色，`--code` 编码，`--remark` 备注 |
| `e10-cli role delete <ids...>` | 删除角色（可多个） |
| `e10-cli role add-member <roleId> <名字...> [--type <类型>]` | 添加角色成员，**可一次给多个名字**（各自独立搜索）。`--type` 取 `resource`(人员，缺省) / `department`(部门) / `subcompany`(分部) / `position`(岗位) / `channel`(渠道) —— 这几项正是平台 `objectTypeFilter` 白名单里**可以逐个选**的对象，白名单另三项 `all`/`external`/`allExternal` 不是逐个选的对象，本命令不支持。五类走**同一个保存端点**，靠 `objType` 选各自数组（`obj_resource` / `obj_department` / `obj_subcompany` / `obj_position` / `obj_channel`）。搜索**精确同名优先**；同名多条、或多条命中却没有同名项，一律**报错不取首条**（取首条会静默加错人）。`--sec-min/--sec-max`、`--is-seclevel` 覆盖安全级别（**这两个值随租户配置变**，缺省 `0`/`100` + false）；`--department-attribute subordinate,partTimeStaff` 给部门/分部指定是否含下级 / 含兼职。**增量追加**，不会冲掉已有成员 |
| `e10-cli role member-list <roleId>` | 列出角色成员（人员 / 部门 / 分部 / 岗位 / 渠道，含成员级别与分权范围） |
| `e10-cli org department create <name> [--code <编号>] [--parent <父部门id>] [--subcompany <机构id>]` | 新建部门。**四步链**：`organization/getForm` 取保存模板（含平台**现生成**的 targetId）→ `form/core/getFormLayout` 取布局 id → `form/core/saveFormData` 落数据并回吐 recordId → `organization/saveForm` 落组织树。`--parent` 不传即顶层部门，挂在当前用户机构下（机构自动解析，可用 `--subcompany` 覆盖）。⚠ 模板里 `parent` 是数组、`subcompany` 是对象数组，命令内部转成平台要的字符串形状 —— **别拿模板直接发** |
| `e10-cli org department edit <id> [--name] [--code] [--parent] [--disporder]` | 编辑部门：改名 / 改编号 / **移动父级** / 改排序。是「**读现状 → 改 → 写回**」：`organization/getForm?id=` 读回这个部门的**完整当前状态**（含 tenantKey / creator / datarank / createTime 等，全部原样回传，别自己造），改完再 `organization/saveForm`。⚠ 编辑报文与新建**形状不同**（认 `id`，没有 `targetId`/`formdata`/`recordId`，`advanceForm:false`），不能共用构造函数。命令会自动**回读确认**改名生效，静默失败会报错 |
| `e10-cli org department delete <id> [--parent <父部门id>] [--subcompany <机构id>]` | 删除部门。`--parent` 是该部门的**父**（顶层部门的父就是机构 id），不传按当前机构的上下文解析。⚠ 删除是**软删**（`isDelete: true`），删完用 `getForm?id=` 仍能读出来 —— 判存在与否要看 `isDelete` 字段，别看接口有没有返回 |
| `e10-cli org employee template [--out <路径>]` | 导出人员导入模板（xlsx）。**模板是随包发的资源**（含富文本表头和「注意事项」工作表），直接复制，不用代码重建 |
| `e10-cli org employee import <file> [--dry-run] [--mode add\|update] [--find-by <字段>] [--review <n>] [--no-wait] [--wait-timeout <ms>] [--error-file <路径>] [--no-error-file]` | 从 Excel 批量导入人员。**先 `--dry-run` 预览再真导** —— 干跑到「预览」为止不落库，能看出平台解析出的列/行跟你原表对不对。⚠ 模板自带示例行，导入前删掉。导完**默认等结果**，打出 `已导入 N / 失败 M`，**有失败行时退出码非 0**；失败原因（在出错单元格的批注里）会直接打出来，失败数据默认可存成 `<源文件>.错误数据.xlsx`。⚠ **分部名写错不报错**：平台会静默新建一个同名分部再把人放进去。细节见 `references/hrm/guide-org-employee.md` |
| `e10-cli org employee task <taskId> [--error-file <路径>]` | 查人员导入任务的结果（`getByTaskId`）。导入时用了 `--no-wait`、或等超时了，用这个补看：条数 / 失败原因 / 失败数据。⚠ **`status: 0` 不是成功**，判完成看 `callbackData` |

## 流程

| 命令 | 说明 |
|------|------|
| `e10-cli workflow create <appId> <formObjId> <name> [desc]` | 创建 EB 流程，当前命令按固定模式创建并自动设置所有人可发起。**默认不加菜单**，要入口传 `--menu`（发起菜单 LAYOUT，指向表单新建页 `/sp/ebdfpage/card/1/<formObjId>/0`，点开即触发流程）；漏加 `e10-cli menu add-start <appId> <formObjId>` 补 |
| `e10-cli workflow create-workflow <name>` | **非默认路径**。仅当用户明确强调「用流程表单 / 工作流程 / 流程中心建流程、不在应用下」时才用；默认走上一条 `workflow create`（eb 应用内）。关联流程表单：不传 `--form-id` 自建（`relateForm=0`，服务端建表回吐 `data.formId`）/ `--form-id <已有>` 绑定（`relateForm=1`）。`--odoc` 创建公文流程（两种表单方式均支持，增加 `bridgeService=odoc`）；`--workflow-type`（默认 -1=其它）、`--sub-company <机构>`、`--belong-type <0个人/1团队>`（默认 1）、`--table-name`、`--desc`、`--is-free`、`--layout <FLOW流式(默认)/EXCEL表格式>`（自建模式下 EXCEL 走 formmanage/saveForm 建表后绑定；建表后不可切换）。不带 source/messageParams |
| `e10-cli workflow auth-resp <list\|create\|update\|read\|configure\|save-design>` | 独立权责表管理。`configure <id> --config @json` 从零创建变量、开始/结束节点、中间节点及操作者、分支条件和路径并保存回读；条件支持统一的 `system` / `form` 业务来源与原始 `childrens`；`save-design` 用于完整设计结构的保留式保存 |
| `e10-cli workflow auth-resp condition-fields <id> --source-id <分支ID> --workflow-id <流程ID\|-99999999>` | 查询权责表条件来源。流程内返回系统字段与实际表单字段；独立权责表返回系统字段与变量，变量在复用流程时映射为实际表单字段 |
| `e10-cli workflow auth-resp variable <list\|add>` | 独立管理权责表变量，变量先创建后供权责表条件引用。支持字符串、数值、选项、浏览和关联浏览变量；`add ... --detail` 创建明细变量，条件用 `detail:any/all` 表示任一行或所有行 |
| `e10-cli workflow auth-resp reference <list\|add\|remove>` | 管理权责表路径中的嵌套权责表。`list <宿主baseId>` 仅返回首尾为中间节点且不会形成循环引用的权责表；`add` 按分支与顺序写入 `addMethod=2` 的引用；`remove` 删除引用列及对应路径。 |
| `e10-cli workflow auth-resp-flow create <name> --base @json (--new-table <name>\|--reuse-table <id>)` | 按权责表方式创建流程。一般需求默认用 `--new-table`，直接使用当前流程表单字段；仅多重嵌套或明确需要跨流程复用权责规则时使用 `--reuse-table`，并用 `--mappings @json` 保存权责表变量到当前表单字段的映射 |
| `e10-cli workflow auth-resp-flow <bind\|design-read\|design-apply\|mapping-read\|mapping-save>` | 对已有权责表流程维护绑定关系、权责表流转设计及变量映射。明细变量映射到实际表单的同类型明细字段；节点、分支条件和路径通过权责表设计维护。详细顺序见 `workflow/guide-workflow-auth-resp.md` |
| `e10-cli workflow odoc <list\|read>` | 查询公文流程列表，或读取单个公文流程及公文设置摘要。`list` 支持 `--name`、`--sub-company`、`--belong-type`、分页参数 |
| `e10-cli workflow odoc setting <get\|set> <workflowId>` | 读取或修改公文设置。`get` 返回平台设置分组、当前值与候选项；`set --config @json` 读取当前配置后合并保存并回读。常用参数及十九组公文配置见 `workflow/guide-workflow-odoc-setting.md` |
| `e10-cli wf-form read <formId>` | **流程表单管理（非默认路径）**。读流程表单字段（getConfig）。`<formId>` 由 `workflow create-workflow` 回吐。与 eb 表 `form read` 对齐，走 `/api/workflow/core/form/...`（module=workflow、customParam={}、无 apid） |
| `e10-cli wf-form add-field <formId> <字段名> <类型> [标题]` | 给流程表单加字段。类型：Text/TextArea/Number/Money/Date/DateTime/Select/Employee/Department/SubCompany（分部选择）/Browser（浏览按钮），**以及全部富组件类型**（Time/Score/Signature/Project/Location/Order/Contract 等，走与 eb 表同一张映射表）。`--sub-form-id <明细subFormId>` 明细字段；`--multiple` 多选；`--precision`/`--percent`/`--default`（Number/Money）；`--format`（日期精度）。formTableId 省略 |
| `e10-cli wf-form add-field <formId> <名> Browser <标题> --browser-type <源>` | **浏览按钮必须指定浏览数据源**，否则平台报「程序异常」。源可选 `workflow`(缺省=工作流) / `hrcontract` / `role` / `archive` / `form`；用 `form` 时再配 `--browser-form-source business\|ebuilder`。落到平台是 `type=RelateBrowser` + `browserType:{module,name,id,type}` |
| `e10-cli wf-form add-field <formId> <名> Browser <标题> --browser-name "CLM-合同类型"` | **按名字指定浏览数据源**，含自定义浏览框（`customBrowser_xxx`，没有固定 id 必须现查）。名字**精确匹配**，查不到会停下并列候选，不用近似项顶替。优先于 `--browser-type`。批量 `add-fields` 直接在 JSON 里写 `browserType:{...}` 对象 |
| `e10-cli wf-form add-fields <formId> @fields.json [--no-init]` | **批量加字段**：JSON 数组每项 `{name,type,title?,subFormId?,multiple?,precision?,percent?,default?,format?,singleRow?,defaultCurrent?}`；加完**自动跑一次 layout init 重新布局**（`--no-init` 跳过）。字段多时比逐条 `add-field` 省事 |
| `e10-cli wf-form ebuilder-scope <formId> <ebuilder字段Id> --rule "目标表字段:操作:值" [--sform-id <objId>] [--workflow-id <wfId>]` | 给流程表单的**关联浏览字段**设数据范围（如关联客户只选「客户状态=启用」的）。操作用 `eq`/`neq`/`like`/`isnull`/`notnull`；Select 值填**选项名**。对应 eb 表的 `form ebuilder-scope` |
| `e10-cli wf-form edit-field <formId> <fieldId> [--title <标题>] [--multiple|--single]` | 编辑已有字段（read-modify-write）。`--multiple`/`--single`：Employee/Department/SubCompany/Browser 切 isSingle，Select↔SelectMultiple。必填为布局级用 `wf-form layout init --required` |
| `e10-cli wf-form delete-field <formId> <fieldId...> [--force]` | 删除流程表单字段（可批量）。**仍被布局引用的字段平台拒删**；`--force` 让 CLI 先从布局摘掉这些字段的组件（含它的标题标签）再删。eb 表侧对应 `form delete-field` |
| `e10-cli wf-form formula set <formId> --expression "DAYS({主表.开始时间},{主表.结束时间})" --target <fieldId>` | 给流程表单字段绑定计算公式。`{主表.字段}`/`{明细表名.字段}` 引用（getConfig 解析）→ `/api/excel/formula/save`(module=workflow) → ffExpress 绑字段 + saveSourceForm。`--name`/`--return-type`/**`--formula-id <id>`（原地更新已有公式，不新建）**。另：`formula get <id>` / `list <formId>` / `functions`。**⚠ 公式语法四条**：函数名必须大写（自定义 JS 脚本函数除外）、逻辑比较用 `==`、给字段赋值用 `=`、跨表粘贴要换掉非本表字段变量 —— 写错不报错只是算不对，见 `references/form/guide-form-formula-functions.md` |
| `e10-cli wf-form formula-linkage list <formId> --workflow-id <id>` | 流程表单的**函数联动**（`linkageType=excel`，走 `/api/ebuilder/flow/form/linkage`，module=`ebuildercard`）。`read` / `delete <ids...>` 同形 |
| `e10-cli wf-form formula-linkage events <formId> --workflow-id <id>` | 列出触发事件（**17 个**：字段组 5 + 表单组 5 + 流程组 7） |
| `e10-cli wf-form formula-linkage columns <formId> --workflow-id <id>` | 列出可引用/可触发的字段，按「可作 / 不可作赋值目标」分桶。字段清单取自 `findFormDrivingColumns`，**不依赖 getFormLayout**（后者在部分流程表单上会 500） |
| `e10-cli wf-form formula-linkage add <formId> --workflow-id <id> --target <字段> --expression <函数体>` | 新增。`--event`（默认 `changeField`）、`--trigger <字段...>`、`--effect form\|formLayout\|workFlow\|includeNode`（后两者需 `--workflow-id`，`includeNode` 另需 `--node`）、`--name`。表达式只给右侧，左侧自动拼。详见 `form/guide-formula-linkage.md` |
| `e10-cli wf-form formula-linkage update <formId> --workflow-id <id> <linkageId> [--event] [--trigger] [--effect] [--node] [--name] [--state on\|off]` | 改触发条件/生效维度/名称/启停。不传的项沿用现有 |
| `e10-cli wf-form linkage <formId> <联动名> --config '{"conditions":[{"field":"请假天数","operator":"EQUAL","value":"3"}],"actions":[{"prop":"hide","fields":["请假事由"]}]}'` | 显隐联动。`--config` 写字段名（自动解析 fieldId/dataKey）；**为空写 `NULL`（或 `EMPTY`，会归一）、不为空写 `NOT_NULL`**（写错平台报的是一句与条件无关的写库异常）。prop: hide/show/edit/readonly/required/hideLine；operator 另有 EQUAL/NOT_EQUAL/CONTAIN/GREATER/LESS 等。顶层可选 `"detailType":"AND\|OR"`（界面「所有/任一」）。**`"effect"` 指定生效维度**（这条路由有四种）：不写=当前表单、`"formLayout"`=**表单布局**、`"workFlow"`=**当前工作流**、`"includeNode"`+`"nodeId"`=**选择节点**（后两者需配 `--workflow-id`） |
| `e10-cli wf-form validate add <formId> <字段名...> [--remind] [--help <提示>]` | 字段查重规则（多字段 AND，重复禁止提交/提醒）。`list`/`delete <ruleId>`。字段名自动 getConfig 解析 |
| `e10-cli wf-form relate <formId> <目标字段> --from <Employee/Department源字段> [--key email/department/code/name] [--title <名>]` | 值带出：换表内 Employee/Department 字段自动填目标字段（HRM 属性带出）。`--key` 默认 Employee=department/Department=name。机制同 eb 表（ffRelateField，Employee 源 module=hrm） |
| `e10-cli wf-form permission get <formId>` | 查看流程表单字段权限（display/readOnly/required/disableEdit）。**写字段权限用 `workflow node field-permission`**（节点级，流程表单表单级写平台多返 500） |
| `e10-cli wf-form add-detail-table <formId> <明细表名> [首字段名] [--init]` | 给流程表单加明细子表（saveSubForm+首字段+可选 init 放入布局）。机制同 eb 表 `form add-detail-table` |
| `e10-cli wf-form field-options <formId> <fieldId> --options '[{"name":"事假"},...]' [--default <序号>]` | 给流程表单 Select/SelectMultiple 配选项（read-modify-write：getFormField 读全字段→改 options→saveFormFieldNew 重存）。`--options` 支持 `@文件`；`--default` 默认选项 valueKey |
| `e10-cli wf-form layout init <formId> [--layout-id <布局ID>]` | 初始化/重建流程表单布局（initLayout，按 layoutType 选模板，默认 FLOW）。**`--layout-id` 指定要重建哪一套**（节点独立布局的 layoutId），不传则重建默认布局；字段属性用 `--read-only`/`--required`/`--single-row` 覆盖 |
| `e10-cli wf-form layout add <formId> --name <布局名>` | 新增一套流程表单布局。`--layout-type FLOW|EXCEL`（默认 FLOW）、`--terminal-type PC|MOBILE`（默认 PC）、`--describe`、`--workflow-id`；返回 `layoutId`，多套布局并存且不覆盖原布局 |
| `e10-cli wf-form layout delete <formId> <layoutId>` | 删除指定流程表单布局。`layoutId` 取自 `layout add` 返回值；可传 `--workflow-id`、`--terminal PC|MOBILE`（默认 PC）。该操作从布局列表移除目标布局 |
| `e10-cli wf-form field-prop <formId>` | 设置运行时布局字段属性：`--required <字段...>`、`--no-required <字段...>`、`--readonly <字段...>`、`--editable <字段...>`、`--single-row <字段...>`。字段可传名称或 ID；内部 getConfig 读取并由 initLayout 保存，同时保留已有分组和独占一行设置 |
| `e10-cli wf-form group <formId> --groups '{"基本信息":["字段名/ID",...]}'` | 给**已建好的流程表单**加字段分组（折叠容器，对齐 eb 表 `form group`）。建组 saveFieldGroup → 分配 updateFormFieldGroup → initLayout generateCollapse 渲染。`--groups` 可 `@文件`；同名分组复用不重复建（去重） |
| `e10-cli workflow list <appId>` | 列出应用下的所有流程 |
| `e10-cli workflow search` | 通用搜索流程（不依赖 appId）。`--name`/`--id`/`--type`/`--belong`。⚠ 列表只回 id/名称/类型名/描述这一层，**不含「绑了哪张表」** |
| `e10-cli workflow info <workflowId>` | 单个流程的基础信息 + **它关联的表单**（流程 → 表单反查）。给出 `formId`、表单名、启用状态、是 eb 表还是流程表单。⚠ **formId 不是 objId**，表单类命令要 objId，而平台没有直通的 formId → objId 接口 —— 得先确认表单在哪个应用下再按 formId 匹配 |
| `e10-cli workflow nodes <workflowId>` | 查看流程节点详情（名称、类型、操作者、连线含 linkId） |
| `e10-cli workflow nodes <wf> --mode list` | 列表视图：展示全节点含 nodeAttr、合流方式（比 chart XML 更全） |
| `e10-cli workflow set-operator <wf> <node> [keyword]` | 设置节点操作者。`--type user`(指定人) / `role`(指定角色) / `dept`(指定部门) / `position`(指定岗位) / `all`(所有人) / `free`(自由选择) / `superior`(发起人上级) / `initiator`(流程发起人本人) / `prev-node`(上一节点) / `form`(表单相关人员) / `matrix`(矩阵对应,需 `--matrix-id` `--value-config-id` `--matrix-rule`)。`--sign-order` 会签/非会签/竞签/依次处理/抄送/抄送需批注（概念见 guide-workflow）；**`--type form` 另支持「或签」**，等价于竞签（表单字段里多人任一人签，语义一致），已登记的签署顺序里没有单独一档。**依次处理倒序**用 `--execute-order 2-2`(默认)/`2-1`正序/`1-1,2-2`安全级别正序+倒序。**`--dept-scope 本部门`**=单个部门内会签/`本及下级`默认。**一个节点多人用逗号分隔 keyword**（如 `"区域经理,部门领导"`，user/dept 都支持）；默认每次全量重建操作者组（先清空再新建），重复设置不堆积。**多操作者组叠加（如「部门领导矩阵 + 门店经理矩阵」双组会签）：先用 set-operator 配第一组，再用 `--append` 配第二组**，`--append` 不清空已有组，两组合起来就是双矩阵会签 |
| `e10-cli workflow generate-link-id <wf>` | 生成新连线 ID |
| `e10-cli workflow add-node <wf> <type> <name>` | 添加节点（列表 API）。`<type>`: 0=发起 1=审批 2=确认 3=归档 5=投递 7=自动处理 8=等待 / forkstart/forkend/forkmiddle。**结束节点=归档节点（type=3）**。`--node-attr` 节点属性；合流点支持 `--merge-type`（0=全部/1=指定/2=数量/3=比例）、`--merge-num`、`--branch-nodes` |
| `e10-cli workflow rename-node <wf> <nodeId> <name>` | 重命名节点（saveNodeSetForm API） |
| `e10-cli workflow add-link <wf> <from> <to> <label>` | 一键添加连线（列表 API）。`--reject` 退回 / `--default` 默认出口 |
| `e10-cli workflow add-links <wf> @links.json` | 批量添加连线（列表 API，一次保存）。格式：`[{"from":"节点ID","to":"节点ID","label":"标签","reject":true,"default":true}]`。`reject`/`default` 逐条给；设为默认出口时同源节点原有默认出口自动让位 |
| `e10-cli workflow link-list <wf>` | 查看出口列表（含默认/退回/条件标志）。`--node-id` 过滤单节点 |
| `e10-cli workflow link-save <wf> @datas.json` | 修改/删除出口（列表方式）。`--delete-rows`/`--changed-link-ids`/`--update-row-ids` |
| `e10-cli workflow link-rename <wf> <linkId> <名称>` | 重命名出口（连线名称）。linkId 用 link-list 查看。实现：读出口列表 → 改 linkName → saveNodeLinkEditTable(updateRowIds) |
| `e10-cli workflow numbering read <wf>` | 查看流程编号规则 |
| `e10-cli workflow numbering enable <wf>` | 启用流程编号（`--off` 关闭）。方案要求"流程有编号"时必做，平台默认不自动启用 |
| `e10-cli workflow numbering set <wf> [--prefix <前缀>] [--separator <ch>] [--serial <n>] [--no-year] [--dry-run]` | **配置流程编号规则**（一次设全组成）：前缀 + 流水号位数（默认4）+ 可选年份段。**`--separator <ch>` 段间分隔符**（如 `-` `~`）：在相邻段（前缀-年、年-流水）间自动插独立固定段 → `--prefix QXBK --separator ~ --serial 4` = `QXBK~2026~0001`；平台分隔符就是独立 FIX_CONTEXT 段、可多个固定段共存。`--dry-run` 只打印将产出的段序列（复用/新建/删除）不落库。旧版曾按类型只留一段会删掉已有分隔符段。`--prefix LC --serial 4 --no-year` → `LC0001`。比 `add-component` 逐个加更省事，常用这条 |
| `e10-cli workflow numbering add-component <wf> --type fixed\|date\|field --value <text> --format <yyyyMMdd> --field-id <id>` | 添加编号组成项：fixed=固定内容 / date=日期 / field=表单字段 |
| `e10-cli workflow numbering reserve <wf> <count> [--prefix]` | 预留编号。**流程编号=REQUEST_NO 系统字段**：eb表单绑流程后编号走本命令（不要用 `form serial-mark` 表单编号，那对流程表无效） |
| `e10-cli workflow node validate <wf> <nodeId> --rule "主题字段 操作 值字段或字面值"` | 节点提交校验（智能审批规则，提交时拦截）。值可以是**字段**（字段 vs 字段）或**字面值**（字段 vs 常量）；主题字段支持**跨表**——用「明细表名.字段名」定位明细字段做主子表校验：`"请假时长 小于 4"`、`"行程明细.行程开始时间 等于 出差开始日期"`（明细字段=主表字段）。**操作符**：大于 / 大于等于 / 小于 / 小于等于 / 等于 / 不等于 / **为空 / 不为空**（后两个无需值，如 `"备注 不为空"`）。**明细量词**：明细字段的主题末尾可写 `:任一`（任一行，缺省）或 `:所有`（所有行），如 `"货品明细.货品名称:所有 不为空"`；主表字段写量词会报错。`--name` 规则名；`--disable` 关闭；`--view` 查看 |
| `e10-cli workflow node menu <wf> <nodeId>` | 查看/切换节点操作菜单。`--toggle <menuId>` 切换启用状态 |
| `e10-cli workflow node layout list <wf> [--terminal PC\|MOBILE]` | 列出该工作流表单的布局，以及每套被哪些节点引用 |
| `e10-cli workflow node layout get <wf> <nodeId>` | 查看某节点挂的是哪套布局（空 = 跟随表单默认） |
| `e10-cli workflow node layout bind <wf> <nodeId> --layout-id <id>` | 把节点挂到某套布局。**自动从原来那套摘掉**（一个节点同时只属于一套布局）；幂等 |
| `e10-cli workflow node layout unbind <wf> <nodeId>` | 摘下独立布局，回落表单默认布局；幂等 |
| `e10-cli workflow node layout create <wf> --name [--layout-type FLOW\|EXCEL] [--nodes <id...>] [--from <布局ID>\|--empty]` | 新建布局。**默认复制表单默认布局**（`--from` 换来源）；`--empty` 才是空白布局。类型不写则跟随来源，**建后不可切换**。⚠ **复制会锁类型**：从流式来源复制却要求表格式，平台仍会建成流式，命令会**直接拒绝** —— 要建另一种类型请改用 `--empty`。要复制 PC 默认布局去建移动端布局是常见场景，来源按**两个终端的并集**找，不受目标终端限制。删布局用 `wf-form layout delete` |
| `e10-cli workflow node layout init <wf> <布局ID> [--fields <名...>] [--list-fields] [--style-template] [--required\|--readonly\|--single-row]` | 重建某套布局的排版（**只动这一套**）。`--fields` = 只摆这些字段（不传=全摆，没摆的字段在表单上仍在）；`--list-fields` 看可摆清单。`create --init [--fields …]` 可建完直接排。**原生流程表单（不挂应用）与 eb 表关联流程的表单走两套不同路由，命令自动识别**，不需要额外参数 |
| `e10-cli workflow setting tabs <wf> [选项]` | 查看/配置**流程详情页页签**（显示哪些页签、默认打开哪个、移动端）。`--only <页签名...>` **PC 端只显示这些、其余全部不显示**（需求里「显示页签：A/B/C，其余不显示」就用它）、`--show`/`--hide` 单独开关、`--mobile <页签名...>` 移动端只显示这些、`--mobile-menu <...>` 移动端菜单、`--default-open <页签名>`（单选）。页签名可用**名称或类型码**（1 流程表单 / 2 流程图 / 3 流程状态 / 4 共享 / 6 主流程 / 7 子流程 / 8 平行流程 / 12 外部流程）；同流程类型页签集合不同（「正文」只在公文流程上有）。保存后自动回读比对 |
| `e10-cli workflow node-reject get <wf> <nodeId>` | 查看节点退回设置（退回提醒 / 退回方式 / 默认选中 / 退回后提交） |
| `e10-cli workflow node-reject set <wf> <nodeId> [选项]` | 设置节点退回规则。`--reject-type free\|step\|range\|byLink\|preApprover`（自由/逐级/指定范围/按出口/上一审批人）、`--submit-type step\|direct\|fork\|operator`、`--reject-remind none\|all\|nodes\|user`、`--default-node prev\|start\|custom`、`--remind-node-ids`（提醒节点）、`--range-node-ids`（退回范围节点）、`--default-node-id`、`--to-create-node`（出口未配时退发起节点）；`--custom` / `--no-custom` 显式指定是否启用自定义退回设置，**缺省保留节点当前值**。⚠ `--no-custom` 时平台会忽略全部节点级退回值，读回看到的是全局默认回显——不是没保存 |
| `e10-cli workflow node-overtime list <wf> <nodeId>` | 查看节点超时规则（含启用状态与规则描述）。新规则平台默认「未启用」，需跑一遍 `set` 才会启用 |
| `e10-cli workflow node-overtime set <wf> <nodeId> [选项]` | 设置节点超时规则，**建好后自动启用并回读核对**（回读不符即报错）。`--duration <天:时:分>`（如 `0:2:0`）、`--flow-type next\|reject\|submit\|intervene\|operator`（下一操作者/退回节点/提交节点/干预对象/指定操作者）、`--flow-delay <天:时:分>`、`--flow-node <节点ID>`（reject\|submit 的目标节点）、`--intervene-ids <用户ID>`（intervene 的干预对象）、`--operator-group <操作组ID>`（operator 的操作组）、`--disabled`（关闭超时处理且不启用）、`--skip-required`（有必填项也继续自动处理） |
| `e10-cli workflow node-overtime remind <wf> <nodeId> [选项]` | 设置超时提醒。`--name <提醒名>`、`--type 0\|1`（超时前/超时后）、`--offset <天:时:分>`、`--mode 0\|1`（仅提醒本人/逐级提醒）、`--remind-group-id`、`--msg`/`--no-msg`、`--mail`/`--no-mail`、`--sms`/`--no-sms`。`--overtime-id` **可省略**：该节点只有一条超时规则时自动使用，多条时列出候选要求显式指定 |
| `e10-cli workflow node drawback <wf> <nodeId> [--after\|--no-after]` | 查看/配置**节点强制收回设置**（操作菜单「强制收回」按钮的内部设置）。⚠ 建模成**一个开关**而不是两个复选框：「查看前收回」是**平台强制基线，关不掉** —— 发「只要查看后收回」平台会给你**两个都开**（接口回读与页面勾选已双向对齐验证），所以命令只暴露 `--after`（是否额外允许查看后收回）。幂等：本来就是目标状态时不发请求 |
| `e10-cli workflow node addstep <wf> <nodeId> [选项]` | 查看/配置**节点加签设置**（操作菜单「加签」按钮的内部设置）。`--select-mode simple\|list\|chart`（简易/列表/流程图）、`--node-type approve\|confirm\|view`（审批/确认/查阅环节）、`--sign-attr countersign\|non\|order`（会签/非会签/依次逐个处理）、`--flow-type next\|back`（流转结束后自动流转下一节点/回到本节点）、`--back-flow operator\|next\|addstep`（回到本节点后：操作者选择/流转至下一节点/流转至加签环节）、`--field-auth all\|same`（加签人字段权限：所有字段权限/与当前节点保持一致）、`--modify-form`、`--limit-range`。取值可直接写数字码。⚠ 字段权限是 **0 所有字段权限 / 1 与当前节点保持一致**（接口库文档写的 1/2 是错的）。保存后自动回读比对 |
| `e10-cli workflow node menu <wf> <nodeId> [选项]` | 查看/配置节点操作菜单。菜单分**快捷菜单**（批准/保存/退回/强制收回/加签…）与**更多菜单**（转办/转发/传阅/意见征询/催办/打印…）两组。`--quick <names...>` 快捷菜单**只启用这些**（其余快捷菜单关闭，不在该组的会移进来）、`--more` 同理、`--enable`/`--disable` 单独开关（不动分组）、`--rename 批准=发送` 改显示名（可重复，值留空恢复默认名）、`--sign 批准=同意` 设默认签字意见、`--toggle <菜单>` 切换单个。菜单可用**名称 / 类型码(AGREE) / ID** 指定；名字拼错会直接报错并列出候选 |
| `e10-cli workflow node-assign-flow get <wf> <nodeId>` | 查看节点指定流转（工作流界面上的「开一窗流转」）设置：启用、目标节点选择范围、自动流转、操作者/抄送 |
| `e10-cli workflow node-assign-flow set <wf> [nodeId] [选项] [--all-nodes]` | 设置节点指定流转。只改显式给出的项，其余沿用当前值。`--enable`/`--disable`、`--range out\|free\|nodes`（按出口/自由/指定节点范围）、`--nodes <节点ID...>`（`--range nodes` 时必填）、`--node-range all\|condition`（按出口时的可选出口）、`--auto-flow none\|must\|first`、`--must-nodes <节点ID...>`（`--auto-flow must` 时必填）、`--auto-first-node`/`--no-auto-first-node`、`--open-dialog`/`--no-open-dialog`、`--forbid-modify-node`、`--node-alone`（目标节点单选）、`--common-destination`（允许使用常用去向）、`--single-operator`、`--comments`、`--sign-relation user\|countersign\|non\|order\|node\|parallel`、`--cc`/`--no-cc`、`--cc-type user\|off\|submit\|auto`、`--cc-required 0\|1`。**`--all-nodes` 对全流程所有可配置节点统一执行**（跳过结束节点与分流/合流点），用于「全流程统一、节点上不单独配」的场景 |
| `e10-cli workflow node-assign-flow targets <wf> <nodeId>` | 列出该节点已单独设置的目标节点（含稳定独立设置 ID 与接收范围键） |
| `e10-cli workflow node-assign-flow add-target <wf> <nodeId> <目标节点ID...>` | 新增指定流转目标节点。已存在的自动跳过，不重复新增 |
| `e10-cli workflow node-assign-flow range <wf> <nodeId> [--open\|--no-open] [--mode normal\|advanced] [--limit-operator]` | 查看/设置指定流转的**接收人可选范围**（总开关 / 普通·高级模式 / 仅限目标节点操作者范围）。`<nodeId>` 传**配指定流转的那个节点**。保存后自动回读比对（场景号传错时平台会照样回 `data=true`，回读比对是唯一的判据）|
| `e10-cli workflow node vote <wf> <nodeId> --type count\|rate --num <n>` | 配置投票节点规则（**自动把节点置为投票类型** nodeType=5）。`--type count` 通过人数 / `rate` 通过率（`--num 100` = 100%）；`--min-num` 最少通过人数、`--show-results` 投票后显示结果、`--veto` 一票否决 |
| `e10-cli workflow node-robot get <wf> <nodeId>` | 查看机器人节点（等待节点 type 8）配置：等待时长 / 处理间隔 / 操作 / 异常干预 / 动作 |
| `e10-cli workflow node-robot set <wf> <nodeId> [选项]` | 更新机器人节点配置（读-改-写，**未传的字段保留原值**）。`--wait-value <分钟>`、`--processing-interval`、`--operator-name`、`--operate-type-name`、`--remark`、`--intervene-type`、`--enable-remark-custom` |
| `e10-cli workflow node-robot set-remark <wf> <nodeId> --zh <中文> --en <English>` | 设置机器人节点备注的多语言 |
| `e10-cli workflow operator-sign <wf> <nodeId> --sign-order <order>` | 修改节点操作者的签署顺序（会签/非会签/竞签/依次处理/抄送/抄送需批注）。**以「更新旧组」方式改，不删组重建**——只想换签署方式时用它；要重建整组用 `set-operator`。`--group <组名>` 只改指定组。⚠ 平台更新路径会**清空原有的「依次逐个处理-处理顺序」**（命令会显式告警）；需要配处理顺序请用 `set-operator ... --sign-order 依次处理 --execute-order <码>`（走重建） |
| `e10-cli workflow node reject <wf> <nodeId>` | ⚠ **已弃用**，请改用 `workflow node-reject`（get / set）。旧命令只有 4 个数值开关，配不了退回范围/提醒节点、也控制不了「自定义 / 全局」 |
| `e10-cli workflow node timeout <wf> <nodeId>` | ⚠ **已弃用**，请改用 `workflow node-overtime`。旧命令的超时时长与提醒字段名平台不认（时长恒为 0、提醒直接报错），且配不了退回/提交目标节点 |
| `e10-cli workflow node field-permission get <wf> <nodeId>` | 查看节点字段权限（各字段 显示/隐藏）。表单字段在节点上可见与否 |
| `e10-cli workflow node field-permission set <wf> <nodeId> --hide <字段...>` | 设置节点字段显示/隐藏。`--hide 字段名/ID` 隐藏、`--show` 显示；可多个，已设权限则更新、未设则新建 |
| `e10-cli workflow node sign <wf> <nodeId>` | 节点签字意见必填（退回时必填意见等）。缺省查看；`--all-required` 全部必填、`--none-required` 全部不必填、`--select "退回,加签"` 指定操作类型必填（按 mustInputDto=2 + 选中操作类型 id）。`getSignConfigForm` 枚举操作类型 |
| `e10-cli workflow node empty-handle get <wf> <nodeId>` | 查看节点**流程异常处理**（无可处理人时怎么办） |
| `e10-cli workflow node empty-handle set <wf> <nodeId> --handle-way <1-5>` | 设置节点流程异常处理：1=指定人员(`--person 名称/ID`) / 2=用户指定 / 3=发起人 / 4=自动流转下一节点 / 5=提交指定节点(`--assign-node <节点ID>`)；`--off` 关闭；`--sync` 同步所有节点 |
| `e10-cli workflow setting title <wf>` | 流程标题规则（发起后标题按规则生成，如"发起人-提交日期-客户名称"→真实数据）。缺省列出可用变量（发起人/部门/日期/表单字段）；`--rule "发起人\|提交日期\|客户名称"` 竖线分隔字段名设置；`--sep <分隔符>` 默认 `-`；`--disable` 关闭自动生成（标题回退流程名+系统默认）。占位符 `$code$`，平台发起时替换为真实值 |
| `e10-cli workflow setting submit <wf>` | 提交确认设置。`--confirm`/`--node-range`/`--show-way` |
| `e10-cli workflow setting sign <wf>` | 签字意见设置。`--show-order`/`--inform-range` |
| `e10-cli workflow setting comment <wf>` | 评论功能开关。`--enable` |
| `e10-cli workflow setting batch <wf>` | 批量操作设置。`--enable-batch`/`--enable-turn-todo`/`--enable-consult`/`--enable-reject` |
| `e10-cli workflow setting auto <wf>` | 自动处理设置。`--enable`/`--way`/`--follow-type` |
| `e10-cli workflow setting other <wf>` | 其他设置。`--message-op`/`--auto-save`/`--switch-identity` |
| `e10-cli workflow advanced doc <wf>` | 流程存档设置。`--enable`/`--dir-select`/`--doc-types` |
| `e10-cli workflow advanced schedule <wf> [选项]` | 定时触发审批。**没有参数=查看**；配置分两次保存：详细配置（`--frequency` 频率 / `--begin-date` 开始日期 / `--weekday-only` / `--sms` / `--email` / `--message`）与开关（`--enable` 总开关 / `--limit-creator` 限制发起人范围）。`--frequency` 只需写要改的档位（如 `{"item1":"1","item2":"3"}`=按日每 3 天），缺的档位自动补全；item1: 1=日/2=周/3=月/4=季/5=年，item2=每几个周期。**⚠ 触发时间由平台固定，不可配置**（平台上该项为只读，帮助文案「固定晚上触发，不支持修改触发时间」）——没有 `--time` 选项。配完范围用 `workflow plan-range` |
| `e10-cli workflow plan-range list <planId> [--page-size <n>]` | 查看定时计划的人员范围。`<planId>` 是定时计划 ID（`workflow advanced schedule` 输出里的「计划ID」） |
| `e10-cli workflow plan-range add <planId> --obj-type department\|employee --target-id <id> [--target-name <名>]` | 添加定时触发人员范围（多个目标 ID 用逗号分隔） |
| `e10-cli workflow plan-range delete <planId> --id <记录ID[,记录ID]>` | 删除定时触发人员范围（**多条逗号分隔**） |
| `e10-cli workflow advanced schedule-range <wf>` | ⚠ **已弃用**，请改用 `workflow plan-range`。旧命令列表恒显示 0 条、删除恒报「入参不全」 |
| `e10-cli workflow delete <workflowId>` | 删除流程。`--with-form` 同时删除关联表单。⚠⚠ **只接受流程 ID，不解析名称**：平台对**不存在的 workflowId 也回「删除成功！」**（顶层与 data 层全说成功），所以传名称进去会「报成功但什么都没删」。命令现在**删之前先确认该 id 存在**，查不到就中止并提示用 `workflow search --name <名称>` 拿真实 id；删完还会回读确认 |
| `e10-cli workflow delete-link <wf> <linkIds...>` | 删除连线（列表 API，可多个）。自动清理关联节点 |
| `e10-cli workflow delete-node <wf> <nodeId>` | 删除节点（自动清理关联出口）。`--bridge` 桥接上下游 |
| `e10-cli workflow save-layout <wf> @xmlfile` | 保存完整流程图 XML（浏览器 mxGraph 格式：数字 cell id + nodeId/linkId）。服务器只认浏览器格式，勿转 node_X。新增节点/连线会自动注入 flag="add" |
| `e10-cli workflow auto-layout <wf>` | **节点自动排版**（分层布局，全量重排坐标）。`--direction ltr/ttb`(默认ltr)、`--gap-x/--gap-y` 间距、`--dry-run` 只算不打回、`--out` 配合 dry-run 输出新 XML。忽略退回线分层，分支自然融入 |
| `e10-cli workflow condition add <wf> <sourceId> <nodeId> <name> --rule "..."` | **简化语法**添加条件。`sourceId` 是连线 ID（linkId），`nodeId` 是该连线的来源节点 ID（srcNodeId），不是目标节点 ID；可从 `workflow nodes --json` / `link-list` 取得。`--rule "system:流程标题:包含:关键词"` 或 `--rule "form:字段ID|字段名|dataKey:大于:1000"`（fieldId/名/dataKey 均可匹配）。按 fieldType 自动判族校验算子，`--relation AND/OR`。**增强语法**：字段vs字段 `form:字段:大于:field:值字段`（range 用 `form:字段:范围:field:左:右`）；明细量词 规则末尾 `:任一`/`:所有`；多值属于 `form:字段:包含:值1,值2`；人员/部门字段 `form:人员字段:包含:张三,李四` 自动解析成对象；系统字段 `system:紧急程度:等于:紧急`；嵌套 OR 用 `\|` 分隔 `form:关联项目:不为空\|form:关联客户:不为空`。详见 `workflow/guide-workflow-condition.md` |
| `e10-cli workflow save-condition @jsonfile --app-id <appId>` | 保存条件规则（原始 JSON）。CLI 自动生成 ID 并绑定到连线 |
| `e10-cli workflow condition list <wf>` | 列出工作流下所有连线绑定的条件（连线名 + 条件名 + 表达式 + mapId），支持 `--name` 过滤 |
| `e10-cli workflow condition get <wf> <id>` | 查看单个条件详情。`<id>` 可用 conditionKey / mapId / conditionId |
| `e10-cli workflow condition delete <wf> <id> [--link-id <linkId>] [--node-id <nodeId>]` | 删除条件（删定义 + 解绑连线）。`<id>` 同 get |
| `e10-cli workflow set-link-condition-key <wf> <link> <key> <node>` | 绑定条件 Key 到连线 |
| `e10-cli workflow save-action @jsonfile` | 加节点提交动作（常量赋值）。**只接 JSON 一个参数**，`workflowId`/`nodeId` 写在 JSON 内部（不是位置参数）。JSON 格式见 `workflow/guide-workflow-action.md` |
| `e10-cli actionflow generate '{"planFile":"@plan.json","appName":"AI-名称"}'` | **动作流生成**（语义 plan → 编译 → preflight → 保存并启用 → 正式回读，返回设计器链接）。`planFile` 必须以 `@` 引用文件（`@plan.json` 或 `@绝对路径`），CLI 强制要求 `@` 前缀。event 节点 `ApproveTrigger` 自带流程节点触发绑定（`workflowPath`+`triggerTiming`+`approveNode`/`approveLink`），不走 pathdef/addaction，无需单独绑节点。默认保存并启用；`{"mode":"stash",...}` 显式暂存。组件契约/参数/映射/条件的权威是 `e10-cli actionflow component-describe <type>`，详见 `actionflows/SKILL.md`。覆盖 ActionEb 全系列/Approve/Document/Hrm/Http（含 HTTPS 地址和 `inputParams`）/DML 数仓/触发器（含 CustomTrigger、InnerMQListener）/消息（含 InnerMQSend）/会议日程/逻辑 20+ 组件；Http 生成前实时校验当前租户连接器→资源→接口→详情，并按当前连接器回填标题/图标；InnerMQListener 与 InnerMQSend 同流互斥 |
| `e10-cli actionflow datasource-list '{"query":"esb"}'` | 查询当前租户数仓数据源连接；`DMLExecute.params.dataSetConn.id` 必须使用这里返回的真实 ID |
| `e10-cli actionflow http-connectors --out http-connectors.json` | 查询当前租户 HTTP 连接器；后续按 `http-resources` → `http-interfaces` → `http-interface-detail` 继续读取，HTTP 请求参数用接口详情的真实 `inputParams` 配置 |
| `e10-cli actionflow update '@update-plan.json'` | **已有动作流保留式修改**（精确 appId → 读正式设计 → 备份 → 按原节点 ID 显式 operations → saveDesign(saveNewVersion=true) → 正式回读）。**不可改 event 触发器**（触发类型/表单/时机/参数变了就新建）；未声明内容保留。触发类型含按钮触发、自定义触发、内置 MQ 监听/发送 |
| `e10-cli workflow action list-node <wf> <nodeId> [--trigger-type all\|link]` | 列出节点绑定的动作（getAddActionDataList）。显示每条的动作类型/appId/触发时机，type0 还带字段=值 |
| `e10-cli workflow action clear-node <wf> <nodeId> [--trigger-type all\|link]` | **清空节点所有动作绑定**（deleteAddAction + delList）。清理重复 add/已删实体残留的悬空绑定；动作流实体另用 `action delete` 清 |
| `e10-cli workflow action disable <appId> <name>` | 禁用动作流（禁用后才能删除） |
| `e10-cli workflow action delete <appId> <name>` | 删除动作流（自动先禁用再 batchAddRecycle 删实体）。**平台无"按动作流反查绑定节点"接口**：删实体后，绑定了此动作流的节点会残留**悬空引用**（前端显示「被删除」）。CLI 删完会提示，需逐个用 `action clear-node <wf> <node>` 清理节点绑定 |
| `e10-cli workflow action batch-delete @list.json` | 批量删除动作流（每项 `{id,name}`，自动先禁用再 batchAddRecycle） |

### 公用流转片段 & 子流程 & 消息

| 命令 | 说明 |
|------|------|
| `e10-cli workflow segment create <name> [--desc <text>]` | 新建**公用流转片段**并自动启用，返回 segmentId |
| `e10-cli workflow segment list [--type 1\|2] [--sub-company-id <id>]` | 列出公用流转片段。`--type 1`=流转片段（默认）/ `2`=权责表片段 |
| `e10-cli workflow segment enable <segmentId>` / `disable <segmentId>` | 启用 / 停用片段 |
| `e10-cli workflow segment add-link <segmentId> <源节点> <目标节点> [连线名]` | 片段内加连线（读片段图重编号 cell id 后追加） |
| `e10-cli workflow segment embed <wf> <segmentId> [--x <n>] [--y <n>]` | 在主流程里插入**公用流转节点**（引用指定片段，自动拼 group + 子节点 XML 并入主流程图）。`--sub-company-id` 用于查片段名 |
| `e10-cli workflow sub-process list <wf> <nodeId>` | 列出节点上全部子流程配置 |
| `e10-cli workflow sub-process get <wf> <nodeId> <subSetId>` | 查看子流程配置详情（主配置 + detailSet + 触发条件） |
| `e10-cli workflow sub-process set <wf> <nodeId> --sub-wf <子流程ID> [--name <配置名>] [--id <subSetId>]` | 新建/更新子流程主配置（**不传 `--id` 新建，传了则读-改-写**）。`--enable`/`--disable`（默认停用）、`--tri-once` 只触发一次、`--tri-source <主表objId>`、`--time-day`/`--time-hour`/`--time-minute` 延时 |
| `e10-cli workflow sub-process set-condition <wf> <nodeId> <subSetId> --rule "..." [--relation AND\|OR]` | 设置子流程触发条件（复用条件构建器，`--rule` 语法同 `workflow condition add`），并回填到主配置 |
| `e10-cli workflow sub-process set-mapping <wf> --sub-wf <子流程ID> --map 源字段:目标字段[:名] [--field-mapping-id <id>]` | 设置主→子字段映射（`--map` 可多个；不传 `--field-mapping-id` 则新建） |
| `e10-cli workflow sub-process set-detail <wf> <nodeId> <subSetId> [选项]` | 更新明细设置（创建人 / 读意见等，读-改-写）。`--creator <类型:字段ID>`、`--del-old-sub-request 0\|1`、`--read-main`/`--read-paralle`/`--read-sub`、`--auto-show 0\|1`、`--init-default-val` |
| `e10-cli workflow sub-process delete <wf> <subSetId>` | 删除子流程配置（连同 detailSet 一并删） |
| `e10-cli workflow message create <wf> <nodeId> <名称> [选项]` | 创建**消息提醒动作流**并绑定到流程节点。`--title`、`--content`、`--recipients <用户ID>`（缺省流程发起人）、`--channel im\|yunqiao\|email\|sms`、`--event arrive\|leave\|delete\|save\|revert\|pause\|cancel`（触发时机）、`--node-name` |

> **加节点**: add-node 直接操作节点列表 API (getNodeEditTable → saveNodeEditTable)
> **加连线**: add-link/add-links 直接操作出口列表 API (getWfpNodeLinkTable → saveNodeLinkEditTable)
> **删连线**: delete-link 直接操作出口列表 API (getWfpNodeLinkTable → saveNodeLinkEditTable, deleteRows)
> **删节点**: delete-node 直接操作节点列表 API (saveNodeEditTable, deleteRows)，`--bridge` 自动桥接
> **查看节点/出口**: nodes --mode list / link-list 走列表 API（比 chart XML 更完整）
> **加分支条件两种方式**: 
>   - 简化: `condition add` — 一行命令搞定
>   - 完整: generate-link-id → save-layout → save-condition → set-link-condition-key
> **加节点提交动作（字段常量赋值）**: save-action @action.json（格式见 `workflow/guide-workflow-action.md`）
> **加跨表单动作流**: `e10-cli actionflow generate`（语义 plan 生成 + 保存并启用 + 正式回读，event 自带流程节点绑定）；`workflow action` 仅作查/清/删/禁用管理

---

## 菜单

| 命令 | 说明 |
|------|------|
| `e10-cli menu list <appId>` | 列出当前Ebuilder应用下的菜单。**递归展开嵌套菜单**（如「设置 → 个人设置 → 个人菜单设置」），列表即全量 —— 在这里没找到就是真没有，不必再怀疑被折叠 |
| `e10-cli menu rename <appId> <菜单ID或名称> <新名>` | 重命名已有菜单（含嵌套菜单）。名称在应用内重复时必须改用 ID，命令会列出候选让你选。平台系统菜单（回收站/设置等）不能改 |
| `e10-cli menu add <name> <path> <appId>` | 将页面加入左侧导航（LINK 类型，URL path）。ecode 页面 path 如 `/sp/custom/ecode/project-list`。**表单台账/流程发起菜单用下面两条专用命令**（VIEWPORT/LAYOUT 类型，非 URL）。**建完会回读确认**并报出菜单 ID；回读不到就报错退出，不谎报成功 |
| `e10-cli menu add-table <appId> <objId> [name]` | 给表单加**台账菜单**（VIEWPORT，指向数据列表页）。`form create --menu` 才自动加（默认不加），此处用于事后补加。**建完回读确认** |
| `e10-cli menu add-start <appId> <formObjId> [name]` | 给流程绑定的表单加**发起菜单**（LAYOUT，指向表单新建页，点开触发流程）。`workflow create --menu` 才自动加（默认不加）。**建完回读确认** |
| `e10-cli menu permission list <appId> <menuId>` | 列菜单可见范围授权（**默认所有人**；无输出=全可见） |
| `e10-cli menu permission add <appId> <menuId> <目标> --type role\|dept\|user\|all` | 给菜单授权。默认语义：**加角色/人/部门后自动撤「所有人」→ 只有授权对象可见**；`--keep-all` 保留所有人；`--type all` 恢复"所有人可见" |
| `e10-cli menu permission remove <appId> <menuId> <目标> --type role\|dept\|user\|all` | 撤销菜单授权（撤销所有人用 `--type all`） |
| `e10-cli menu delete <menuId> <appId>` | 删除菜单项 |

---

## 页面 & 设计器（配置式页面搭建）

> 设计器页面 vs Ecode 页面：应用内建页**优先用设计器 Ebuilder 页面（配置式）**——`page create` 建页 → `designer comp-add --template` 加组件（28 个内置 factory 模板）→ 组件 setter/脚本绑数据 → `designer save` → `designer unlock` → `page publish-menu` 发布菜单，全程不写前端代码。详见 `ebuilder-designer/guide-designer.md`。

| 命令 | 说明 |
|------|------|
| `e10-cli page list --app-id <appId>` | 列应用下页面（id/name/belongModule/terminalScope） |
| `e10-cli page create <name> <appId> [--scope PC,MOBILE] [--layout-type GRID] [--module EB_PAGE]` | 创建页面（**参数顺序：名称在前、appId 在后，写反会 401**）。免登录页 `--module EB_ANONYMOUS_PAGE` 不支持 Comment/SearchGlobal/FastCreate |
| `e10-cli page get <pageId>` | 页面详情（模块/终端/权限视图） |
| `e10-cli page delete <pageIds...>` | 删除页面（软删除，可多个） |
| `e10-cli page publish-menu <pageId> <appId> [name]` | 页面发布为应用菜单（默认所有人可见，`menu permission` 收窄）。**发布前先 save+unlock**，否则设计器/预览弹「布局未保存」 |
| `e10-cli designer info <pageId>` | 页面元信息。**看 `allowEdit`/`isLock`**：isLock=1 先 unlock 再 save |
| `e10-cli designer layout <pageId> [--json] [--terminal pc\|mobile]` | 读布局（`--json` 输出完整两端 JSON 供 save 复用；摘要模式看组件 id/type/标题/坐标） |
| `e10-cli designer save <pageId> --layouts <json\|@file> [--page-name] [--sync-outdate]` | 保存布局（自动 LZ 压缩）。**入参取自 layout --json、只改 comps；必须含 PC+MOBILE 两端**（缺端丢另一端），CLI 强校验 |
| `e10-cli designer lock <pageId>` / `designer unlock <pageId>` | 锁定/解锁（软锁；**收尾必做 unlock**，每次都递增版本号） |
| `e10-cli designer position <pageId> <compId> --x --y --w --h` | 调 PC 栅格位置（12 列；改后自动保存） |
| `e10-cli designer comp-add <pageId> --template <名\|路径> [--type <Type>] [--x --y --w --h]` | 加组件：内置模板直接传名（`pie`/`bar`/`nlist`/`slide`…28 个，`designer factory-list` 查全表）；也可传任意布局 JSON 路径，或 `--from <srcPage> --comp <id>` 从活页克隆。自动生成新 id + PC/MOBILE refCompId 互连并保存 |
| `e10-cli designer comp-remove <pageId> <compId>` | 移除组件（PC/MOBILE 按 refCompId 联动删） |
| `e10-cli designer factory-list` | 列出 28 个内置 factory 模板（名称↔组件 type 对照） |
| `e10-cli designer chart dataset-set\|measure-add\|dimension-add\|title\|height` | **图表配置（全 11 种）**。dataset-set 绑表单；measure-add 加度量（SUM/AVG/MAX/MIN 用 `--field-id`，COUNT 用 `--count-records`）；dimension-add 加维度（字段名/ID 均可，Date 自动按月）；title 设业务标题；height 设像素高。**Gauge：COUNT+无维度；堆积：2 度量+1 维度；Bubble：只能 1 度量** |
| `e10-cli designer digital-panel panel-add ...` | 数字面板加 KPI 卡（`--field-id --aggregator SUM\|COUNT\|AVG\|MAX\|MIN --label`） |
| `e10-cli designer list dataset-set\|field-add\|order-add` | NList 绑数据源/加显示列（`--type` `--comp-type` 同值传字段类型）/加排序 |
| `e10-cli designer calendar dataset-bind\|field-map\|title` | 日历绑数据源（`--start --end --title-field`，内置全视图渲染）/调映射（`--end clear` 全天单日）/设标题 |
| `e10-cli designer slide pic-add\|title` | 幻灯片加轮播图（**平台资源路径**，已防 Git Bash 路径转换）/设标题 |
| `e10-cli designer nav-panel menu-add\|menu-source-type\|title` | 导航面板加跳页菜单（NewPage 双层 eventGroup 自动构造）/切菜单来源 DEFAULT\|CUSTOM/设标题 |
| `e10-cli designer css read <pageId> <compId> [--terminal pc\|mobile\|both]` | 读组件**自定义 CSS**（`comp.config.styles[].customStyle.base.codeSource`；compId 给任一端都行） |
| `e10-cli designer css write <pageId> <compId> (--css <文本>\|--css-file <路径>) [--append\|--clear] [--terminal] [--yes]` | 写自定义 CSS：默认**双端同写**、默认整段替换；`--append` 非幂等；`--clear` 清空但留记录；两端已分叉时须 `--yes`。写后回读比对，对不上报错 |
| `e10-cli designer dom-list` / `designer dom <type> [--keys] [--section <path>] [--refs]` | 查写 CSS 要用的**组件 DOM 结构索引**（27 个组件，随包分发）。**先 `--keys` 看骨架再 `--section` 取子树**（文档中位数 20 多 KB） |

> **setter 通用**：`--field-id` 传字段名或 fieldId；绑定条目由 CLI 从 ds/fields 取平台原样字段对象自动构造（不用手填 physicalField/browserParams）；其余 12 类非图表组件无 setter，走「导出 layout → 脚本改 config → save」（见 `ebuilder-designer/guide-designer-factory.md` 深度配置节）。
| `e10-cli designer auto-height <pageId>` | **单列纵堆模式**：按组件内容自动定高 + 重排 y（配完字段后跑一次）。**多列栅格勿用**（会覆盖 w/x），手调 position |
| `e10-cli designer version list <pageId> [--page] [--size] [--since/--until] [--remark]` | 版本列表（save 自动产生快照；**versionId 取 records[].id 非 version 号**） |
| `e10-cli designer version revert <pageId> <versionId>` | 还原历史版本（整体替换两端；不可逆，还原前建议 lock） |

> **坑**：① save 入参铁律——取自 `/layout/list` 原值只改 comps，元数据不动；② 组件标题用业务名（comp-add 出来是占位名，配完必改）；③ 高度是内容驱动（h 过低裁切，`position --h` 调大）；④ 非 TTY 环境给 `comp-add` 带 `--yes`。

---

## 报表（设计器报表）

```bash
# 建表（首选）：声明式一步落库，不留空壳
e10-cli report build --spec spec.json                    # 正式
e10-cli report build --spec spec.json --dry-run          # 只定源+字段预检
e10-cli report build --spec spec.json --form-confirmed --source-id <id>   # 用户已确认表
e10-cli report build --spec spec.json --field-confirmed "列A,列B"          # 确认文案≠显示名
# 退出码 3=需选表(未建) 4=需选字段(未建) 2=成功但有警告
e10-cli report find <appId> [表名] | --list | --suggest "关键词"   # 应用内定源
e10-cli report create blank|template|quick --app-id <id> --name "名" [--model-id <id>]
e10-cli report create models                             # 模板列表

# 读 / 改
e10-cli report read <reportId> [--fields]
e10-cli report list --app-id <id>
e10-cli report delete <reportId> --app-id <id>           # 进回收站，可还原
e10-cli report dataset list|rename|preview|check-used|delete|replace ...   # 数据集侧栏
e10-cli report dataset agg|sort get|save|clear --dataset-id <id>

# 查询条件
e10-cli report query list|save|type|check-echo|fix-echo <reportId> --app-id <id>
e10-cli report query verify <reportId> --app-id <id> [--fix]     # Q1~Q10 体检
e10-cli report fix query-default <reportId> --app-id <id> [--set ...] [--apply]
e10-cli report fix query-style   <reportId> --app-id <id> [--delete-id ...] [--apply]

# 权限 / 分组 / 生命周期 / 版本
e10-cli report scope list|set|matrix ... --report-id <id> --app-id <id>
e10-cli report group list|add|delete --app-id <id>
e10-cli report lifecycle copy-and-menu|add-menu|move|transfer ...
e10-cli report lifecycle recycle list|restore|purge ...
e10-cli report version save|list <reportId>
e10-cli report snapshot set|list <reportId> [--cron "0 0 0 * * ?"]
e10-cli report restore <reportId> --version <versionId>
e10-cli report cleanup --app-id <id> [--prefix __build_] [--apply]

# 校验 / 体检 / 修复（fix 默认只预演，--apply 才落库）
e10-cli report validate base|condition|format|transform|href|gridline|blank|style ...
e10-cli report verify bind|all|meta|condition|format|blank|gridline|contract|limit <reportId> [--app-id <id>]
e10-cli report fix table-name <reportId> [--apply]       # 补 tableName
e10-cli report fix freeze <reportId> [--anchor x,y] [--apply]
e10-cli report fix echo <reportId> --app-id <id>

# 分析
e10-cli report join-suggest --app-id <id> (--parent-form 主表 --child-form 子表)
e10-cli report py preagg --report-id <id> [--app-id <id>]
```

> 建表 / 改表 / 查询条件怎么用、踩坑在哪：`references/report/guide-report-build.md`、`guide-report-modify.md`、`guide-report-query.md`、`ref-report-pitfalls.md`。

## 人员 & 图标

| 命令 | 说明 |
|------|------|
| `e10-cli user search <keyword> [count]` | 模糊搜索员工（返回 ID/姓名/部门/手机） |
| `e10-cli icon search <keyword...>` | 搜索 Ebuilder 图标（4999 个，支持多关键词） |

---

## 认证 & 多环境

| 命令 | 说明 |
|------|------|
| `e10-cli auth status` | 查看当前登录状态（cookie 过期会提示）。**认全局 `--profile`**——多环境切换后用它确认登的是哪个环境；该 profile 未登录时直接报错，不会回落到别的环境 |
| `e10-cli auth login` | 浏览器 OIDC SSO 授权 → 本地回调 → 自动保存。**需要用户亲自点**，自动化跑不了 |
| `e10-cli auth set --base-url <url> --eteamsid <值>` | 直接写入认证（**非交互**）。SSO 回调不到 localhost 时用这条：让用户从浏览器 DevTools → Application → Cookies 复制 `ETEAMSID` 值即可 |
| `e10-cli auth profile list\|use <name>\|current` | 多环境 Profile 管理。也可以不切激活项，直接在任意命令前加全局 `--profile <名>` |
| `e10-cli auth export-weaver-env` | 导出当前鉴权为 `WEAVER_*` 环境变量（供外部脚本复用）：`eval "$(e10-cli auth export-weaver-env)"` |

> ⚠ `ETEAMSID` 是会话凭据——只在命令行里传，**不要写进任何项目文件**。

---

## 矩阵

| 命令 | 说明 |
|------|------|
| `e10-cli matrix list [--name <关键词>] [--enable-status 0\|1] [--org-id <id>]` | 查询矩阵列表（**含停用矩阵**，带状态；`--out` 写 JSON 文件） |
| `e10-cli matrix create <name> [选项]` | 新建矩阵（**新建即为启用**，要停用再跑 `matrix disable`）。所属机构的字段名由**分权状态**决定，CLI 自动判断并在缺省时用当前机构兜底，分权租户无需手写机构 |
| `e10-cli matrix config <id>` / `config-edit <id>` | 查看 / 编辑矩阵配置（条件字段 + 值字段）。**`config-edit` 的 `--condition` 可省略**，省略则沿用现有条件列（部门/分部矩阵的条件列是平台建矩阵时自动给的，不该手写；已有列要带 `id`，不带会被当成新列去取号）；保存后按列 id 回读比对 |
| `e10-cli matrix enable <id>` / `disable <id>` | 启用 / 停用（停用后数据只读） |
| `e10-cli matrix update <id>` / `delete <ids...>` | 更新基本信息（名称/描述/同步方式）/ 删除（级联删配置、数据、维护者） |
| `e10-cli matrix data` | 矩阵数据维护（映射行）。`data save` 简写为 `[{rowId?, "<列configId>": ["<实体ID>"]}]`：**带 `rowId` 改那一行、不带为新增**（行 id 用 `data list` 拿；同步型矩阵的行 id 就是部门 id）。改行只给要改的列即可，CLI 自动补全其余列并回读比对 |

> 行从哪来（`syncType`）、字段能不能改（`permList` 里有没有 `FIELD`）、以及「条件列 → 人员列 → 数据映射 → 运行时读回」的完整步骤见 `references/hrm/guide-matrix.md`。

---

## 编译 & Skill 文档

| 命令 | 说明 |
|------|------|
| `e10-cli compile <项目目录> [--strict]` | 编译前端项目（`--strict` 把警告也当错误）。代码质量自检用 `e10-cli check <项目目录>` |
| `e10-cli skill root` | 打印 skill 文档根目录绝对路径（文档版本与 CLI 版本一致） |
| `e10-cli skill copy [目标目录]` | 全量拷贝文档 + 模板到本地（默认当前目录），放出 `references/` `actionflows/` `assets/` `SKILL.md` |
| `e10-cli skill sync [--target <目录>]` | 探测已安装的 skill（`~/.claude/skills`、`~/.workbuddy/skills`、`~/.codex/skills` 等），把文档树 + 薄层指令文件自动拷进对应目录；`--target` 可重复指定额外的安装根目录 |

---

## 版本更新（只提醒，升级需确认）

| 命令 | 说明 |
|------|------|
| `e10-cli update check` | 强制连网查一次（忽略 24h 缓存），显示 当前/最新/结论。`--on`/`--off` 开关注册 |
| `e10-cli update apply [--yes]` | 升级到最新（打印将执行的 `npm install -g weaver-e10-builder@<最新>` 并询问确认；加 `--yes` 跳过确认）。仅在线可用，内网走离线 tgz |

> **自动提醒**：每次 `e10-cli auth status` 末尾静默检查（每 24h 最多连网一次；离线/内网自动跳过不打扰）。检测到新版本只打一行 `💡 有新版本…`，**不自动安装**。

---

## 代码检查

| 命令 | 说明 |
|------|------|
| `e10-cli check <项目目录>` | 代码质量检查，逐条自检，全部确认通过后再 build |

---

## 典型工作流

```bash
# 1. 创建项目ecode
e10-cli project create 会议室预订

# 2. 打包 & 上传
ecodecmd build /path/to/project --target=e10
e10-cli project import <projectId> .target/xxx.zip --main-url /sp/custom/ecode/table-demo

# 3. 后续改代码再上传（先删旧应用文件夹）
ecodecmd build /path/to/project --target=e10
e10-cli project tree <projectId>              # 找旧应用 folderId
e10-cli project delete-folder <folderId>
e10-cli project import <projectId> .target/xxx.zip --main-url /sp/custom/ecode/table-demo

# 4. 需要表单时
e10-cli app create 会议室管理                  # → appId
# 先写字段定义文件 fields.json，然后：
e10-cli form create <appId> 会议室表单 /path/to/project --fields @fields.json  # → objId
e10-cli form read <objId> --app-id <appId> --out fields.json  # 写入 fields.json（推荐）

# 5. 角色管理
e10-cli role create 财务主管 --code CW01 --remark "审批角色"
e10-cli role add-member <roleId> 张三 李四                        # 人员，可一次多个
e10-cli role add-member <roleId> 营销三组 --type department      # 部门
e10-cli role add-member <roleId> 总经理 --type position          # 岗位
e10-cli role add-member <roleId> 华东分部 --type subcompany      # 分部
e10-cli role member-list <roleId>                               # 读回成员

# 6. 创建流程
e10-cli workflow create <appId> <formObjId> 会议室审批
e10-cli workflow nodes <workflowId>                     # 查看节点

# 7. 配置审批节点
e10-cli workflow set-operator <wf> <nodeId> 张三         # 指定人
e10-cli workflow set-operator <wf> <nodeId> 财务主管 --type role  # 指定角色

# 8. 加分支条件（如金额≥1000走CEO审批）
e10-cli workflow generate-link-id <wf>                   # → newLinkId
e10-cli workflow save-layout <wf> @修改后的xml文件
e10-cli workflow save-condition @条件.json                # → conditionKey
e10-cli workflow set-link-condition-key <wf> <linkId> <key> <nodeId>

# 9. 添加菜单
e10-cli menu add 会议室预订 /sp/custom/ecode/meeting/list <appId>

# 10. 配置动作流（新建/修改）—— 新建走 generate，已有流修改走 update
# 先查目标表字段 + 流程上下文 paramKey
e10-cli actionflow form-fields '{"tableId":"<targetTableId>","appId":"<targetAppId>"}'
e10-cli actionflow workflow-context-fields '{"workflowId":"<wf>"}'
# 按名称或 paramKey 筛选；默认每页仅 20 条，避免终端截断
e10-cli actionflow workflow-context-fields '{"workflowId":"<wf>","query":"数据ID"}'
# 输出完整原始 JSON（终端仍只显示可用摘要，避免截断）
e10-cli actionflow workflow-context-fields '{"workflowId":"<wf>"}' --out context.json
# 正式设计回读同理；默认摘要，raw:true 才直接打印完整 JSON
e10-cli actionflow read-design '{"sceneId":"<sceneId>"}' --out design.json
# 写 plan.json（event=ApproveTrigger 带 workflowPath+triggerTiming；actions=ActionEbAdd/Update/Delete）
# mapping: {"源paramKey":"目标字段ID"}，目标ID +前缀=累加 -前缀=累减；明细仅 add；
# update 定位: opType=id(关联字段)/updateData+filterCondition(requestId 定位走 ApprovalData paramKey)
e10-cli actionflow generate '{"planFile":"@plan.json","appName":"AI-动作流名"}'  # planFile 必须以 @ 引用文件（@plan.json 或 @绝对路径）
# 管理: list-node 查节点绑定 / clear-node 清 / delete/disable 删动作流
e10-cli workflow action list-node <wf> <nodeId>
```
