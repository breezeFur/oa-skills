# 搭建计划模板（plan.md 强制格式）

> 这是 `plan.md` 的**强制模板**。写 plan.md 必须照此格式逐项梳理资源与规则，**禁止自创格式、禁止预勾 `[x]`**。
> `[ ]` = 待办；执行阶段做完一项、验证通过，才改 `[x]` 并填实际 ID。全部 `[x]` 才算完工。

## 使用方法

1. 复制下方「plan.md 骨架」到工作区 `plan.md`
2. 按需求逐项填实（应用/表单/流程/出口条件清单/菜单/页面/必做项）
3. 规划阶段全部留 `[ ]`，拿给用户确认（此阶段不调 e10-cli 写命令，可 list/read 查现状）
4. 用户确认后逐项执行，每做完一项、验证通过，改 `[x]` 并填 ID——完成一条打勾一条
5. **执行每项前，先按 SKILL.md 决策树读对应 `references` 指南**——命令的完整参数/边界/坑/示例都在指南里，认真阅读再动手，不要凭印象直接调命令

流程明确使用权责表时，在对应流程下列明搭建方式、新建或复用的权责表、变量与字段映射，以及各分支的场景说明、条件、经过节点和顺序；详细配置读取 `references/workflow/guide-workflow-auth-resp.md`。

---

## plan.md 骨架

```md
## 搭建计划

> ⚠️ `[ ]` 是待办，不是"已规划"。规划阶段全部留 `[ ]`；执行阶段做完一项、验证通过，才改 `[x]` 并填 ID。**完成一条打勾一条**，全部 `[x]` 才算完工。**禁止预勾 `[x]`**（=谎报完成）。勿依赖平台默认值——平台默认值≠方案要求。
> **来源标注**：每张表/每个流程/每个节点用分组头声明（名称+ID 占位），其下 `[ ]` 项的来源即该分组；跨表的项内联标「来源: <表单/流程>」。

### 0. 环境
- [ ] 鉴权 `e10-cli auth status`（profile 切换 `auth profile use` / 新环境 `auth set --eteamsid --base-url`）

### 1. 应用
- [ ] <应用名> | `app create` | ID: 待创建
  > 默认一份完整业务方案落在一个主应用；需求明确指定已有应用、跨应用资源或独立业务边界时，按实际范围处理，并标明每项资源归属。

### 2. 角色（来源: 全应用）
- [ ] <角色名> | `role create` + `role add-member <roleId> <keyword>` | 方案要求的每个角色都要建，不会自动有

---

### 3. 表单（每张表一组，逐张复制此分组）

#### ▼ 表单：<表单名A> | objId: 待创建

##### 3.1 字段定义（按[新建 EBuilder 表单](../form/guide-create-form.md)整理，建表时通过 `form create --fields` 一次创建）
- [ ] <表单名> | ID: 待创建
  类型: 普通 EB 表单 / 虚拟表（虚拟表按[虚拟表创建与维护](../form/guide-virtual-form.md)记录来源和字段映射）
  布局: FLOW（流式）/ EXCEL（表格，缺省）
  字段:
    1. 名称(Text, 必填)
    2. 金额(Money, precision=2, 只读)
    3. 备注(TextArea, 独占一行)
    4. 客户名称(Text, group=基本信息, 必填)
    5. 联系电话(Phone, group=基本信息)
    6. 明细表(DetailTable, formFields:[...])
    7. 关联客户(EBuilder, sformId+dataTitle)
    8. 关联流程(Flow, sformId=<流程绑定的表单objId>)  ← sformId 指向哪个流程表单，浏览时就只选该表单绑定的流程数据，创建时自动绑定
  - 选项/编号/默认值/精度/百分比/maxLen 建表时写全；单位无独立属性，**写进字段名**如 `工时单价(元)`
  - **布局与显示属性**：方案文档明确要求的必填(`required`)、只读(`readOnly`)、隐藏(`hidden`)、独占一行(`singleRow`)、分组(`group`)、字段顺序——全部标在字段清单里，建表时 fields.json 一并带上，勿留建后补。方案未提到的用默认（EXCEL 两列、不分组、不必填）
  - **日期区间**：字段本身包含起止含义时优先规划为 `DateRange`；明确分列或需独立参与公式、联动时再拆成两个日期字段
  - **字段多语言**：需求写成 `中文/English` 时，字段清单保留两种名称并注明“多语言”；创建时字段名只用中文，建成取得 fieldId 后执行 `form field-lang set --zh <中文> --en <English>`，不可把斜杠名称原样落库
  - 公式/值带出可 inline：`formula` / `relateFrom`
  - **Flow 字段**：`sformId` 是流程表单 objId（不是 workflowId），建表时写进 fields.json 即自动绑定——关联到哪个流程表单就只能选该范围的流程数据，无需单独配数据范围
  - **二级明细**：逐条列出“父明细 → 子明细”、父级行标识、子级文本行标识和是否默认展开；执行时先读取父明细的可选子明细，再按[二级明细表配置](../form/guide-form-sub-detail.md)创建并回读。
  > **新建表单**时把字段一次规划全、随建表写进 `fields.json`，别先建空表再一个个补——补字段要重排布局，容易漏掉布局属性。
  > 这句只针对「新建」。`add-field` / `edit-field` **是维护已有表的正常命令**，不是补救手段：
  > - 给**已经存在**的表加字段 → `form add-field`
  > - 改已有字段的类型 / 标题 / 必填 / 长度 / 描述 → `form edit-field`（**支持改类型**，走读-改-写，不用删字段重建，显示名 / 列名 / 位置都保留）

虚拟表补充清单（普通 EB 表单删除本段）：
- [ ] 数据源定位 | 来源类别: EB 表单 / 系统业务表 / 数据加工 | 名称/ID: <来源>
- [ ] 数据源预检 | 稳定 ID 校验通过
- [ ] 字段映射 | <来源字段(dataKey/sourceFieldType)> → <虚拟表字段及兼容展示类型>
- [ ] 虚拟表创建 | `form virtual create` | objId/formId: 待回填

##### 3.1.1 表单布局蓝图（按[表单布局规划](../form/guide-form-layout-planning.md)识别；需求提供完整布局样表时必填，否则标“— 未提供，使用默认布局”）
- [ ] 布局类型：EXCEL / FLOW
- [ ] 来源：<需求文档章节或表格标题>
- [ ] 物理列结构：<如 4 列：标签｜字段｜标签｜字段>

| 行 | 类型 | 左侧单元 | 右侧单元 | 跨列/占位 | 原文属性与说明 |
|---|---|---|---|---|---|
| 1 | 标题 | <表单标题> | — | 跨全部列 | |
| 2 | 字段 | <标签> → [<字段名>] | 空 | 右侧留空 | 只读 |
| 3 | 分组 | <分组名> | — | 跨全部列 | |
| 4 | 字段 | <标签> → [<字段名>] | <标签> → [<字段名>] | 双字段 | 必填；只读 |

  > 逐行记录标题、分组、字段同排关系、字段先后、空白占位和可确认的跨列信息；合并范围暂时无法确认时标为“待确认”。
  > 将蓝图中的必填、只读、公式、校验和联动同步写入字段定义或 3.2 表单级配置。
  > 执行时根据蓝图组织 `fields.json`，使用 EXCEL 布局完成创建和初始化；创建后读取实际布局并按需求调整局部位置或显示属性。

##### 3.2 表单级配置（来源: 本表单 <表单名A>；建表后逐项配齐，缺一项这张表不算完成）
- [ ] 字段名称多语言 | `form field-lang set <objId> <appId> <fieldId> --zh <中文> --en <English>`（仅需求明确提供多语言名称时列出；先建中文字段再设置）
- [ ] 复杂编号 | `form serial-mark set <objId> <appId> <fieldId> --segments @json`（纯建模表：fixed/year/serial/field/system/date+代字；⚠ 绑流程表无效→走 `workflow numbering`）
- [ ] 值带出（关联表） | `form relate <appId> <objId> <目标字段> --from <Employee/Department源字段>`（换申请人→填邮箱/工号/部门；HRM属性带出，简单单源）
- [ ] 值带出（跨表/多跳） | `form field-linkage add <appId> <objId> --trigger <触发字段> --target <目标字段> --hops "<源表objId:带出字段,源表objId:带出字段,...>"`（跨表查询带出，支持多跳链式中转；Text 字段必须多跳到名称表取名称不能直接赋 ID）
- [ ] 本表字段自动计算（函数联动） | `form formula-linkage add <appId> <objId> --event changeField --trigger <触发字段> --target <目标字段> --expression "VALUE({主表.数量})*VALUE({主表.单价})"`（本表字段间的公式赋值；表达式只给右侧。系统模块字段如 `{主表.当前日期}` 可作来源/触发，但不可作目标）
- [ ] 关联显示列 | `form ebuilder-columns <objId> <appId> <fieldId> [字段名...]`（先不带参数看业务字段候选清单，去系统字段）
- [ ] 关联数据范围 | `form ebuilder-scope set <objId> <appId> <fieldId> --rules '[...]'`（如客户状态=启用才可选）
- [ ] 字段公式 | `form formula set --expression "DAYS({主表.开始},{主表.结束})" --target <fieldId>`（或 fields.json inline）
- [ ] 查重校验 | `form validate add <objId> <appId> <字段名...>`（项目名称重名/工时日期重复）
- [ ] 显隐联动 | `form linkage add <appId> <objId> <名> --config @json`（prop: hide/show/edit/readonly/required/hideLine）
- [ ] 字段分组 | `form group <objId> <appId> --groups '{"基本信息":[...]}'`（建表时已用 group 则跳过）
- [ ] 表单权限 | `form permission add <objId> <appId> --org-type <all/role/dept/...> --right-type <0/1/2/3>`（勿默认所有人）
- [ ] 表单页按钮 | 名称/位置/来源页面/打开目标/字段映射 | `form button add`（固定URL、视图、布局或流程；[指南](../form/guide-form-button.md)）

##### 3.3 台账/视图配置（来源: 本表单 <表单名A> 的台账；无需求标「— 无」）
- [ ] 显示列批量设置 | `form list-columns <objId> <appId> <listId> --set @columns.json`（[指南](../form/guide-list-columns.md)）
- [ ] 列单位 | `form list-unit <objId> <appId> <listId> <fieldId> "（元）"`
- [ ] 列格式 | `form list-format <objId> <appId> <listId> <fieldId> [--thousandths] [--decimal <n>]`
- [ ] 字段事件（列点击跳转） | `form list-click <objId> <appId> <listId> <fieldId> [--target <objId>]`
- [ ] 搜索条件 | `form list-search <objId> <appId> <listId> [--add <f>] [--quick <f>]`
- [ ] 排序 | `form list-sort <objId> <appId> <listId> [--field <f>] [--order ASC|DESC]`
- [ ] 顶部统计（主表/明细） | `form list-stats <objId> <appId> <listId> --add @json`（[指南](../form/guide-list-stats.md)）
- [ ] 视图数据条件 | `form list-filter <objId> <appId> <listId> --add '{"conditions":[...]}'`
- [ ] 关联页签及目标视图 | `form association create <objId> <appId> <名> --view <viewId> --permissions @json`（[指南](../form/guide-form-association.md)）
- [ ] 关联页签布局与终端 | `form association update <objId> <appId> <associationId> --layouts 显示 --terminals PC MOBILE`（[指南](../form/guide-form-association.md)）
- [ ] 关联页签数据筛选 | `form association set-filter <objId> <appId> <associationId> --mappings @json`（[指南](../form/guide-form-association.md)）
- [ ] 视图按钮 | 名称: <按钮名> | 来源视图: <名称/listId> | 位置: <行上/行末下拉/右上/右上下拉> | 动作: <打开视图/布局/流程/URL及目标ID> | 映射: <目标字段 ← 当前行来源字段；无则“无”> | `form button add` / `form button action-set`（[指南](../form/guide-form-button.md)）
- [ ] 行事件（整行点击） | `form list-event <objId> <appId> <listId> --add-page '{...}'`
- [ ] 视图启用分组 | `form list-group <objId> <appId> <listId> --enable --group-field <fieldId>`（[指南](../form/guide-form-view.md)）
- [ ] 上下级树形展示 | `form list-hierarchy <objId> <appId> <listId> --enable --parent-field <自关联字段名或ID> --expand-level <层级>`（如根据“上级类型”展示；不同于普通字段分组，[指南](../form/guide-form-view.md)）
- [ ] 主表合并行 | `form list-merge <objId> <appId> <listId>`
- [ ] 台账视图权限 | `form list-permission <objId> <appId> <listId> [--add-all|--add-user <id> --name <n>]`
- [ ] 分类搜索 | `form list-search-group <objId> <appId> <listId> [--add <选项fieldId>]`
- [ ] 自定义视图 | `form view create <objId> <appId> <名> --type kanbanView|calendarView|mindMapView|multiView` + `form view populate`
- [ ] 表格视图 | 默认复用台账，记录实际名称/listId；额外新建才用 `form table-view create <objId> <appId> <名>`（[指南](../form/guide-form-view.md)）
  > 表单自带台账（搜索/筛选/导出/批量）。本节只列有需求的项；无需求标「— 无」

#### ▼ 表单：<表单名B> | objId: 待创建
（同上 3.1/3.2/3.3 复制）

---

### 4. 流程（每个流程一组，逐个复制此分组）

#### ▼ 流程：<流程名A> | workflowId: 待创建

- 流程体系：EB / 原生工作流程
- 原生类型：普通 / 公文（EB 流程填“—”）
- 流转模式：固定 / 自由
- 表单来源：EB 表单 / 自建原生表单 / 已有原生 formId

##### 4.1 创建
- [ ] 创建 | `workflow create <appId> <formObjId> <名>`（默认不加菜单；确认需要发起入口时 `--menu` 加）
  > 原生工作流程改用 `workflow create-workflow`；公文类型增加 `--odoc`。布局类型在表单来源后注明。
  > ⚠️ **流程级必做**：① 流程编号（`workflow numbering`）；② 出口名称（`workflow link-rename`，改业务人话）；③ 出口条件清单（见 4.3，先列全表再逐条创建，勿凭印象跳步）

##### 4.2 节点与连线（来源: 本流程 <流程名A>；每节点一行）
> ⚠️ 操作者按需求语义用对应 `--type`（role/dept/position/superior/initiator/form/matrix/free/all），**禁止兜底成具体人员顶替**；名称解析不到先停下确认。
- [ ] 节点1 | 操作者: 创建人
- [ ] 节点2 | 操作者: 区域经理+部门领导(竞签)  ← 「A或B审批」=一节点多人+竞签/非会签，不拆节点
- [ ] 节点3 | 条件: <字段>=<值> 才走到，否则跳过/直达<节点>
- [ ] 节点4 | 操作者: 角色X ｜ 动作流: → <目标表>(add/update/delete, 映射: 源→目标)
- [ ] 连线 | `workflow add-links <wf> @links.json`（`reject`/`default` 逐条给；默认出口同源节点自动让位）
- [ ] 结构改完补排版 | `workflow auto-layout <wf>`（**加/删节点、加/删连线之后必跑**；建流程时自动跑过的那一次不算）

###### 权责表设计（搭建方式为权责表时填写，替代普通节点与连线清单）
- [ ] 权责表来源 | 默认流程内新建；仅多重嵌套或明确复用时选择复用已有 | 权责表：<名称> | authRespId：待回填
- [ ] 首尾设置 | 发起：<类型及操作者> | 结束：<类型及操作者>
- [ ] 中间节点 | <节点名称、类型、操作者>
- [ ] 分支路径 | <场景说明> | 条件：<条件> | 路径：<节点及顺序>
- [ ] 嵌套权责表 | <适用分支> | 引用：<权责表及版本> | 顺序：<序号>
- [ ] 条件字段来源 | 系统字段 / 当前流程表单字段 / 独立权责表变量
- [ ] 变量映射 | <独立权责表变量（主表/明细）> → <当前流程实际表单字段（主表/明细）> / 随流程新建无需映射
> 权责表方式流程的节点、分支条件和流转路径统一在权责表设计中维护；复用独立权责表时逐项列出变量映射。
> 一般权责表流程使用 `auth-resp-flow create --new-table`，条件直接引用流程表单字段；多重嵌套或跨流程共享同一权责规则时，才规划独立权责表、嵌套引用及 `--reuse-table` 变量映射。

##### 4.3 出口条件清单（来源: 本流程 <流程名A>；必填，动手前逐条列出，防遗漏）
段② 执行到条件时，先按此表列出所有连线的完整条件，逐条确认后再 `workflow condition add`：

| 来源节点 | 目标节点 | 连线名 | 条件 | 来源 | 操作 | 值/右字段 | 明细量词 | 备注 |
|---|---|---|---|---|---|---|---|---|
| 发起 | 初审 | 部门初审 | 所属部门=财务部 | form:所属部门 | 等于 | 财务部 | — | |
| 发起 | 初审 | 部门初审 | 报销金额5k~10k | form:报销金额 | 范围 | 5000:10000 | — | 数值范围 |
| 发起 | 初审 | 部门初审 | 发起时间≥报销日期 | system:发起时间 | 大于等于 | field:报销日期 | — | 变量模式 |
| 发起 | 初审 | 部门初审 | 报销类型∈{差旅,住宿} | form:报销类型 | 属于 | 差旅费,住宿费 | 任一 | 与下行OR |
| 发起 | 初审 | 部门初审 | 同上OR组 | form:发票编号 | 包含 | FP | 任一 | 接上行OR |

要点：每行一条原子条件，OR 组拆多行备注"与下行OR"；操作列 等于/大于/小于/范围/属于/包含/为空/不为空/field(变量模式)；值列字面值直接写、`field:`前缀引用另一字段；明细量词 任一(任一行)/所有(所有行)/—(主表)；创建完 `workflow condition list <wf>` 回读核对总数一致

- [ ] 出口名 | `workflow link-rename <wf> <linkId> <业务人话>`（分支连线尤其要改）

##### 4.4 节点级配置（每个审批节点一组，逐个复制）
###### ▶ 节点：<节点名> | nodeId: 待创建
- [ ] 操作者 | `workflow set-operator <wf> <node> [keyword] --type <user/role/dept/position/all/free/superior/initiator/prev-node/form/matrix> --sign-order <会签/竞签/依次/抄送>`（`--append` 多组叠加）
- [ ] 提交校验 | `workflow node validate <wf> <node> --rule "字段 操作 值"`（跨表用"明细表名.字段"，如 `行程明细.开始时间 等于 出差开始日期`）
- [ ] 签字意见必填 | `workflow node sign <wf> <node> --select "退回"`（退回等操作类型必填意见）
- [ ] 节点菜单 | `workflow node menu <wf> <node> --toggle <menuId>`
- [ ] 退回设置 | `workflow node reject <wf> <node>`
- [ ] 超时处理 | `workflow node timeout <wf> <node>`
- [ ] 字段权限 | `workflow node field-permission set <wf> <node> --hide <字段...>`

##### 4.5 流程级设置（来源: 本流程 <流程名A>）
- [ ] 公文设置 | 公文类型、正文、节点、附件、归档、签章、编号及 AI 等配置 | `workflow odoc setting set`（原生类型为公文时按实际需求填写）
- [ ] 流程编号 | `workflow numbering set <wf> --prefix LC --serial 4 --no-year`（REQUEST_NO，绑流程表必走）
- [ ] 流程标题 | `workflow setting title <wf> --rule "发起人|提交日期|客户名称"`（标题=流程名+系统字段则跳过）
- [ ] 提交确认 | `workflow setting submit <wf>`
- [ ] 签字意见 | `workflow setting sign <wf>`
- [ ] 评论 | `workflow setting comment <wf> --enable`
- [ ] 批量操作 | `workflow setting batch <wf>`
- [ ] 自动处理 | `workflow setting auto <wf>`
- [ ] 其他 | `workflow setting other <wf>`
- [ ] 存档 | `workflow advanced doc <wf>`
- [ ] 定时触发 | `workflow advanced schedule <wf>` + `schedule-range <wf>`（人员范围）
- [ ] 消息提醒 | `workflow message create`（IM 提醒动作流）

##### 4.6 动作流（跨表写入/自动化）
- [ ] 动作流生成 | `actionflow generate '{"planFile":"@plan.json",...}'`（来源: 本流程触发 → 目标: <目标表单>）
- [ ] 节点字段赋值 | `workflow save-action @action.json`（来源: 本流程 <节点名>）
- [ ] 数据来源落点 | 目标台账建 Flow 字段 `form add-field <目标台账objId> <app> "数据来源" Flow --sform-id <本流程表单objId>`（来源: 本流程 → 落点: <目标台账表单名>），add 时 `--sysvar` 写 requestId，**update/delete 也靠它定位**

#### ▼ 流程：<流程名B> | workflowId: 待创建
（同上 4.1-4.6 复制）

---

### 5. 菜单（来源: 应用）
- [ ] 台账菜单 | 建表时需要入口则使用 `form create --menu`；未生成入口时用 `menu add-table <appId> <objId>` 补加（默认台账视图存在不等于菜单入口存在）
- [ ] 发起菜单 | `menu add-start <appId> <formObjId>`（来源: <流程名>绑定的表单；workflow create 已自动加）
- [ ] 自定义菜单 | `menu add <名> <path> <appId>`（LINK，ecode 页面）
- [ ] 菜单权限 | `menu permission`（岗位/角色/部门/人员可见）

### 6. 页面（定制）
- [ ] 无定制 | 标「### 页面（无需，表单自带台账）」
- [ ] 定制页面 | Ecode `project create/import` + 页面编码（图表/跨表聚合/特殊交互）

### 7. 矩阵（HRM，按需）
- [ ] <矩阵名> | `matrix create` + `config-edit` + `enable` + `data`（来源: 被 <流程名> 的 `set-operator --type matrix` 引用）

## 执行分段（最多三段，每段完成停下来让用户确认，确认后才进下一段）
以确认后的 `plan.md` 为执行清单，按资源依赖顺序逐项读取相关指南并完成配置；完成并核验一项，就立即勾选对应项并回填实际 ID 或结果。每段结束前检查本段应完成项是否全部销号，依赖后续资源的项目保留 `[ ]` 并注明依赖，不得提前勾选。

- **段①：应用、角色、表单与视图。** 完成应用、角色、全部表单和表单布局，并配齐字段属性、关联、公式、联动、校验、权限、默认台账、新增视图、显示列、搜索排序、筛选统计、分组、上下级、按钮和关联页签等表单及视图相关配置。依赖流程 ID 的配置在 plan 中列明，待段②创建流程后回填。
- **段②：流程与自动化。** 完成流程创建、节点连线、操作者、出口条件、节点配置、流程级设置、矩阵和动作流，并回填段①中依赖流程 ID 的表单字段、表单按钮和视图按钮。完成后**补跑一次 `workflow auto-layout`**，再确认流程结构及关键条件。
- **段③：菜单与页面。** 完成台账、流程发起和自定义菜单，配置菜单权限，并按需求创建配置式页面或定制页面，绑定真实资源 ID 后完成保存、发布和整体收尾。
- 简单单步需求（改字段、查数据）不分段，直接执行
> **表单是流程的地基**：流程绑定表单、条件/动作流/操作者都引用字段，字段设计错了流程全返工——表单段必须确认后再进流程

## 规则备忘
- **改完流程结构要补排版**：`workflow auto-layout <wf>` 只在 `create`/`create-workflow` 建流程时自动跑过一次，**之后一律不会顺带重跑**（add-node/add-link/delete-node/delete-link 都不跑）。所以 4.2 的最后一项别省 —— 加完分支线不补，图上就留着交叉。两个边界：① 它是**整图重排**，人在浏览器里拖过的坐标会被覆盖；② **不保证消除交叉**，跨层连线仍可能穿过中间层节点，跑完看一眼流程图，有交叉手工调。
- **执行前读指南**：每个命令的完整参数/边界/示例在对应 `references` 文档（SKILL.md 决策树按关键词路由），动手前先读，勿凭印象调命令出错
- Plan 阶段不调 e10-cli 写命令（可 list/read 查现状）；必须写 plan.md 落地，不要只在对话里列方案
- 应用数量：默认全需求只建 1 个应用，不按功能点拆；确需多应用先跟用户确认
- 流程按节点逐行，操作者含签署方式/条件/动作流挂节点；**「A 或 B 审批」= 一节点多人 + 竞签/非会签，不拆节点**
- 台账页面不用写，表单自带台账（搜索/筛选/导出/批量）
- 表单字段一次性建好（`form create --fields`）；需求明确的 singleRow/group 建表时写入，字段参数按 `references/form/ref-form-fields.md` 确定
- 需求提供完整布局样表时，字段清单和“表单布局蓝图”必须同时存在：前者定义字段，后者保留空间结构；字段覆盖数、同排关系、分组顺序和原文说明应逐项对应
```

---

## 来源标注方式

| 配置项类型 | 来源标注方式 |
|----------|------------|
| 表单级配置（3.2/3.3） | 分组头 `▼ 表单：<表单名A> | objId: 待创建`，其下项来源=该表单 |
| 流程级配置（4.2/4.3/4.5） | 分组头 `▼ 流程：<流程名A> | workflowId: 待创建`，其下项来源=该流程 |
| 节点级配置（4.4） | 子分组头 `▶ 节点：<节点名> | nodeId: 待创建`，其下项来源=该节点 |
| 跨表项（动作流落点） | 内联标 `来源: 本流程 → 落点: <目标台账表单名>` |
| 菜单/矩阵 | 内联标 `来源: <表单名>` / `被 <流程名> 引用` |

多张表/多个流程时，复制对应 `▼` 分组（每张表/每个流程一组），来源即分组头声明。每个 `[ ]` 都能看清属于哪个表单/流程/节点，不会把 A 表的配置错配到 B 表。
