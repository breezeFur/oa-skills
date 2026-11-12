---
name: weaver-e10-workflow
display_name: 泛微E10流程智能助手
display_name_en: Weaver E10 Workflow Assistant
description: "泛微 E10 流程智能助手：查询待办/已办/我发起/全部流程，查看详情与摘要，处理、批量处理、共享和发起/修改流程。"
description_zh: "泛微 E10/OA 流程智能助手。支持按流程标题/编号/发起时间/完成时间/操作时间/紧急程度/发起人/工作流/表单字段等条件查询待办、已办、我发起和全部流程，支持查看详情、生成摘要、打开流程、同意/提交/批准、退回、转办/委托/转发/抄送/加审、批量提交/置已读/催办/共享/转发/退回，以及发起创建流程和修改已存在流程表单。"
description_en: "Weaver E10/OA workflow assistant skill. Query pending, done, initiated and all workflows by title/number/time/urgency/initiator/workflow/form fields; view details, generate summaries, open flows, approve/submit, return, transfer/delegate/forward/cc/add review, run batch submit, mark-read, supervise, share, forward and reject operations, and initiate or edit workflow forms."
version: 1.0.3
author: 泛微网络科技股份有限公司
agent_created: true
requires:
  bins: ["weaver-work-cli"]
dependencies:
  - weaver-e10-shared
cliHelp: "weaver-work-cli workflow --help"
---

**开始前先读取 [`../weaver-e10-shared/SKILL.md`](../weaver-e10-shared/SKILL.md)。CLI 缺少、版本不匹配或用户要求更新时，按 [CLI 自动准备](../cli-setup.md) 直接执行 `npm install -g weaver-work-cli@latest --registry=https://registry.npmjs.org` 并核对版本与 `workflow --help`；XiaoE 客户端托管的 CLI 按共享规则由客户端自动准备，不另装全局副本。共享技能已随本仓库收录，缺少时直接执行 `weaver-work-cli skills install shared --target-dir "<SKILLS_ROOT>"`，`<SKILLS_ROOT>` 是本技能上一级的绝对目录；已有共享技能需要更新时先比较并备份用户修改，再按 CLI 帮助更新同一位置。安装不另设确认弹框、不要求用户手动执行；完成后回读共享规则并继续原任务。认证、JSON 输出、业务写入确认仍按共享规则执行；安装失败或共享规则仍不可读时停止依赖它的平台操作，如实说明结果。**
**`--is-connector` 判据**：用户明确使用连接器、或上下文要求用连接器完成任务 → 传 `true`；本次任务或上下文直接选择单独技能 → 不传；用户没有明确说明时，按**正在运行的这份 Skill 是哪一级**定——**用户级（条目标 `(user)`）不传，连接器级（标 `(connector)`）传**（同名 Skill 只会运行用户级那一份）。传 `true` 时不要再写 `--profile` / `--base-url`。完整规则见 [`../weaver-e10-shared/SKILL.md`](../weaver-e10-shared/SKILL.md)。

认证和登录态只能按共享规则通过 `weaver-work-cli auth ...` 命令判断；禁止直接读取、列出、打印或解析用户主目录下的旧 `.e10-cli`、auth、config 或 Keychain 数据。
所有命令通过 `weaver-work-cli --json workflow run <operation>` 执行：**统一用 `--input-json '<json>'` 内联传入**——`planJson`、`filterFields` 这类嵌套结构也一样内联（总量通常只有几百字符，内联完全够用；**不要因为"看着复杂"就去写 JSON 文件**，那会白白多出一次文件写入与一次工具往返）。仅当 JSON 确实很大（几十 KB 级，如超长消息列表）或含难以在 shell 里转义的单引号时，才改写 UTF-8 文件配 `--input <path>`；只有确认当前 shell 能稳定传管道时才用 `--input -`。调用前先按需读取 references 下对应的文件，查参数结构，不要猜字段；**references 是第一信息源**，`weaver-work-cli workflow schema` 是 operation、字段和风险等级的合约来源。
生成或改写的 docs、reference、提示词和命令示例必须同时兼容 Windows 和 macOS/Linux。凡涉及 JSON 输入、用户目录、路径分隔符、文件删除、目录查看或文件比对，必须同时给出 Windows PowerShell 与 macOS/Linux（bash/zsh）两套示例；Agent 先根据当前系统和 shell 选择对应示例，不确定时用 `node -p "process.platform"` 判断。Windows/PowerShell 示例不要使用 `printf`、`$HOME/...`、`~/...`、bash 反斜杠续行、`rm/ls/diff/python3` 等 Unix-only 写法。
用户明确要求读取、解析、上传或复用指定附件时，按该任务直接执行，不额外添加通用数据风险警告或 Yes/No 弹框。仅提供路径而没有操作意图时先明确任务；需要把文件发送到任务未涵盖的新外部服务时，先说明实际接收方、用途并取得授权。按实际数据路径描述处理过程，不断言所有附件都会先经过公网大模型。

# 泛微E10流程智能助手

## 适用场景（何时使用本技能）

用户提到待办、已办、我发起的流程、流程详情与摘要、同意/退回/转办/加审等流程操作、批量处理、共享流程、发起创建流程或修改流程表单时，使用本技能。

用户要查组织架构与人员 ID 时转 `weaver-e10-hrm`；查发票、邮件、日程、费控时转对应业务技能。

## 认证与请求头契约

登录与会话由 `weaver-e10-shared` 共享规则和 `weaver-work-cli auth ...` 命令体系统一托管。业务 Skill 不自建登录流程，不索取、打印或转存任何凭证。


## 任务入口（每收到用户任务，先按本固定步骤执行）

收到用户任务（查询/查看/操作/批量/共享/发起/修改）后，**不要先推理规划、不要以翻文档代替执行、不要把 references 通读一遍**，按下面两步固定执行：

1. **第一轮就并行发起（关键：不要串行拆成多轮往返）**：在**同一条消息**里同时发出下列调用——
    - Read `../weaver-e10-shared/SKILL.md`（若尚未读过）；
    - `weaver-work-cli [--is-connector true] --json workflow run workflow.memoryPrompt`——该命令**无入参**；**先按本文件开头的 `--is-connector` 判据确定前缀，再直接执行**（仅"非首次对话且距上次成功读取记忆不足 6 小时"时跳过）；
    - **查询类意图**只读 [`workflow-query.md`](references/workflow-query.md) 一份（已覆盖 `workflow.search` 与 `workflow.todoStat`，不要再读其他查询文档）；**但该文件约 108 KB / 835 行——整读会超单次读取上限被明确拒绝**（Read 单次上限约 **20,000 tokens ≈ 100 KB / 800 行**）：**首轮一次读完开头的契约段**（`offset 1 limit 244`，约 30 KB，已覆盖 Operation、全部输入参数含「大分类判定」、时间条件与「待办时间默认语义」、执行流程），其余章节（`planJson` 编排、汇报式分组骨架、渲染规则与示例）**只在需要的那一刻按它开头的「分段索引」给出的行区间补读**；查看/操作/共享/发起/修改等意图读对应那一份 reference 即可，不要顺手把查询文档也一起读；**唯一例外是批量操作**——用 `scopeCondition` 走范围驱动时要构造与 `workflow.search` 同形的查询条件，**这一轮可以同时读 [`workflow-query.md`](references/workflow-query.md) 与 [`workflow-batch.md`](references/workflow-batch.md)**（前者给条件写法，后者给 `scopeCondition`/`action` 的执行口径），其余意图仍只读对应那一份；
    - **泛化待办查询**（如"今天有哪些待办"）先看上一步 `memoryPrompt` 返回的 `oaContext.smartGrouping`：`false`（低版本）→ **直接** `workflow.search`（category=todo，**不要带 `planJson`/`subCategory`**），CLI 已自带分组统计与卡片，原样渲染即结束；`true`（智能分组）→ 才追加 `workflow.todoStat` 做统计规划，再带 `planJson` 取数。**不要在 `smartGrouping` 为 `true` 之前先调 `workflow.todoStat`**——低版本必然失败（报 `todo_stat_requires_smart_mode`）白费一次调用。
   > 以上调用**互不依赖，必须并行**：串行拆轮会成倍拉长耗时。**实测基准**：一次泛化待办查询全程约 70s，其中**模型轮次占 ~95%**（每轮约 8~25s，主因是模型输出量），CLI 命令本身合计只有 1~2s。**能省一轮就省一轮**——尤其不要为"解析上一轮输出""取流程 ID"另起一轮。
    - **[`workflow-memory.md`](references/workflow-memory.md) 本步不读**——记忆读取的命令形态见上一行（**含 `--is-connector` 判据**，按它确定前缀后执行），**记忆保存的规则已在本文件「记忆保存（全局规则）」章节给全**（本轮任务结束时按那一节执行）；只有需要判断"放 `user.md` / `memory.md` / `workflow:{id}` 哪一类"或其它字段细节时，才在需要的那一刻去读它。
    - **读被拒就按行段重读源文件，不要去读宿主的落盘文件**：Read 单次超限是**明确报错**（提示改用 `offset`/`limit`），照提示把源文件分行段重读即可；**不要**去读宿主的落盘文件（`~/.workbuddy/projects/**/tool-results/**`：**没有读取权限**，去读必然拿一句 `Permission … has been denied`、白费一轮——那是**命令输出**超线时的落盘预览，不是 Read 的读取路径）。
2. **执行用户任务**：按下方「选哪个命令」与「处理链」选定 operation 并执行，参数以对应 reference 为准。

> `workflow.memoryPrompt` 返回的 `oaContext` 已含 OA 版本、**当前环境是否支持智能分组（`smartGrouping`）**与当前用户身份（岗位/部门/分部）——判模式直接看 `smartGrouping`（不要自己比版本号）、引用身份直接用它，不要再单独查组织信息。

## 总原则

- **全程中文**；输出时把技术术语翻译成普通用户能看懂的话（命令要求对返回内容原样输出的除外）。
- **列表/详情最终回复 = 原样粘贴命令返回的渲染文本全文，一字不改**：**`workflow.search` 用 `finalMarkdown`**（卡片列表；`smart` 模式无顶部行）、**`workflow.detail` 用 `renderMarkdown`**（该 operation 没有 `finalMarkdown`）——两者不要混用、不要自己拼装；其中禁止出现 `<div>`/`<span>`/`style` 等 HTML 标签。
- 只执行本 skill 列出的 operation，把命令返回的结果、提示、候选**原样呈现**；命令没做的、没返回的、查不到的，反馈用户或停止——**绝不自行发明、探测、绕过**。
- **澄清一律不向用户索取 ID**：凡是"名称没匹配到 / 有多个候选待确认"的情形（填单、查询、转发接收人、共享对象等一律适用），只问该对象的**完整名称**或**其它可用于检索的关键词**；`名称(ID)`（或 `{id,name}` 这类结构）由你按命令返回的 `candidates` 自己拼好、重发同一条命令，**不要让用户提供 ID**。
- 失败、超时、登录失效、业务错误一律立即停止，不自动重试、不延长等待、不切换地址、不换接口。**例外**：读操作遇登录失效时按 `weaver-e10-shared` 的认证引导处理，认证完成后重放原请求（写操作见「写操作失败处理」）。
- **接口异常一律原样反馈给用户，禁止自行尝试解决方案**：命令返回里出现接口报错（`error.type = api`）时，把接口提示原文转述给用户、并说明本次操作**没有完成**；不得替接口解释原因，不得自行改用别的做法去绕。
- **若决策依据了历史记忆，最终回复要说明；若本轮保存了记忆，要说明会记住什么。**
- **不得写 agent 工具的工作日志/工程日志/对话记录**；**不读取、不处理与本任务无关的工作区引导/身份文件**（如工作区根的引导说明、身份档案等——那是别的流程负责的事，在本轮纠结它只会让任务跑偏并白白多花几秒）；不读取命令源码、不执行调试命令、不使用调试参数。

## 记忆保存（全局规则，每轮任务结束都要执行）

**每轮完整实质任务结束、向用户输出最终回复之前**，必须自行判断本轮是否出现**新的、有价值的语义记忆**（例如用户新澄清/确认了具体工作流、**字段名 / 浏览按钮字段值 / 选项字段的选项值**；与已有记忆重复的不算）：

- **有** → 组装本轮「用户原始意图 + 澄清过程 + 确认结果」的消息列表，**实际调用** `weaver-work-cli [--is-connector true] --json workflow run workflow.memoryExtract --input-json '{"msgList":[{"msgRole":"user","msgValue":"…"},{"msgRole":"assistant","msgValue":"…"}],"async":true}'`（**要不要带 `workflowId` 见下一条**）：
    - **`msgList` 每项的字段名固定是 `msgRole` / `msgValue`**（按对话顺序：user 放用户原话/澄清回复，assistant 放命令返回/你的确认说明），**不要写成 `role` / `content`**；
    - **`workflowId` 只在「这条记忆换个工作流就不成立」时才带**——① 澄清**工作流本身**（业务别名、名称消歧、把口语简称落到某个工作流）⇒ **不带**：这类事实跨工作流通用，带上会被锁进该工作流维度，**而别名存在的意义正是"还没确定工作流时用它去找工作流"**；② 澄清**该工作流内部**（表单字段与选项含义、节点流转、提交节奏、审批规则）⇒ **带上**。一句话判据：**换个工作流还成立吗？成立 → 不带；只在某个工作流里成立 → 带**；
    - **保存「业务别名 → 工作流」映射时，ID 必须来自本轮命令返回**：`workflow.search` / plan 的 **`cards[].workflowId`**、`workflow.createForm` 澄清候选的 `id`、`workflow.todoStat` 的 `countDetails[].workflowId`——拿到就必须把 ID 写进 `msgValue` 的事实句（如「业务别名"问题流程"= 工作流"E10客户问题支持解决流程"，workflowId=1003655203465764898」）；**不允许只记名称、把 ID 留空**——留空就是「（待确认）」，后续查询只能拿纯名称去试探，多命中还要再澄清一次；
    - `saved:true` → **用自然语言告知用户会记住什么**（如"后续再发起请假流程时会默认按本次偏好（年假）填写"），不展示接口原文；
    - `saved:false` → 按静默失败处理，不告知用户、不重试，直接继续回答用户原本问题。
- **没有** → 不调用 `workflow.memoryExtract`，直接输出最终回复；**不要纠结"一次性原因（如请假事由）是否值得记忆"**。

**硬禁令（违反即为没保存）**：

- **不允许只在思考里写"应该保存记忆"**：判断"有"后必须**真的发出 `workflow.memoryExtract` 命令**，拿到真实 `saved` 结果后再输出最终回复。只在内心说"要保存"而不执行 = 没保存。
- **发起流程（`workflow.createForm` / `workflow.createRequest`）按本节更窄的口径**：本轮发起过程中，只有**用户有新的明确澄清**——① 工作流名称；② 字段名称；③ 浏览按钮字段值；④ 选项字段的选项值——才属于要保存的情形（口径见 [`workflow-create.md`](references/workflow-create.md)）；**这四类之外一律不保存**（用户只是给出普通文本 / 日期 / 金额字段的本次取值、或只是正常走完一次填单，都不算记忆），不要漏也不要多存。
- 用户澄清后确认的**工作流名称 / 字段名称 / 浏览按钮字段值 / 选项字段的选项值**属于典型的"有价值记忆"，**属于要保存的情形**，不要漏。
- **记忆里的别名条目写「（待确认）」时，它是一张待办、不是终态**：本轮只要把该别名唯一解析出了 `workflowId`（**`cards[].workflowId`** 或 `countDetails[].workflowId` 里就有），任务结束时**必须再保存一次把 ID 补上**（口径同上），不要放着不管。

> 本节的规则已足够直接执行；仅当需要判断"放 user.md / memory.md / workflow:{id} 哪一类"或需要其它字段细节时，才去读 [`workflow-memory.md`](references/workflow-memory.md)。

## 路由优先级（先判断是不是流程业务，再选 operation）

流程不是组织、发票或邮件能力。**只要用户的核心对象是待办、已办、我发起的流程、流程详情、流程操作或流程发起，就优先使用 `weaver-e10-workflow`。**

### 明确归 `weaver-e10-workflow` 的高优先级语义

- 待办 / 已办 / 我发起 / 全部流程 / 流程列表 / 我的流程 / 待我处理 / 我审批过的
- 流程详情 / 流程摘要 / 打开流程 / 签字意见 / 流转日志 / 审批记录
- 同意 / 提交 / 批准 / 通过 / 退回 / 驳回 / 转办 / 委托 / 转发 / 抄送 / 加签 / 加审 / 强制收回 / 强制结束 / 意见征询 / 催办 / 删除流程
- 批量处理 / 批量提交 / 批量置已读 / 批量催办 / 批量共享 / 批量转发 / 批量退回
- 共享流程 / 把流程共享给某人或某部门
- 发起流程 / 创建流程 / 提交审批 / 填单 / 起草 / 存草稿
- 修改流程表单 / 改已发起流程的字段

**判定规则：** 用户核心对象是流程实例（request）或流程发起表单时走本 Skill。要发起某个流程用 `workflow.createForm`（它内部解析当前用户**可发起**的工作流，解析不出唯一目标时直接给出候选）；查询"我有哪些待办"用 `workflow.search`。涉及"姓名转人员 ID / 组织架构 / 部门岗位"时，人员与组织解析交给 `weaver-e10-hrm`，本 Skill 只在操作流程时消费其返回的人员 ID。

## 选哪个命令

| 想做什么 | 命令 | 按需读取 reference |
| --- | --- | --- |
| 查看可用 operation、字段和风险等级、输出契约 | `workflow schema` | [`workflow-agent-entry.md`](references/workflow-agent-entry.md) |
| 查询待办/已办/我发起/全部流程，按条件筛选，待办智能分组取数 | `workflow run workflow.search` | [`workflow-query.md`](references/workflow-query.md) |
| 待办整体分组计数（智能分组第二步；须先确认 `oaContext.smartGrouping === true`） | `workflow run workflow.todoStat` | [`workflow-query.md`](references/workflow-query.md) |
| 查看流程完整详情、生成摘要、打开流程、查签字意见/流转日志 | `workflow run workflow.detail` / `workflow.summary` / `workflow.open` / `workflow.requestLog` | [`workflow-view.md`](references/workflow-view.md) |
| 打开 OA 页面（待办/已办/草稿/监控/创建/查看） | `workflow run workflow.pageOpen` | [`workflow-view.md`](references/workflow-view.md) |
| 单条流程操作：同意/提交/退回/转办/委托/转发/抄送/加审/收回/结束/征询/删除/催办 | `workflow run workflow.operatePrepare` / `workflow.operateApply` | [`workflow-operate.md`](references/workflow-operate.md) |
| 批量提交 / 置已读 / 催办 / 共享 / 转发 / 退回（均为单命令，一次调用完成） | `workflow run workflow.batchSubmit` / `workflow.batchRead` / `workflow.batchSupervise` / `workflow.batchShare` / `workflow.batchForward` / `workflow.batchReject` | [`workflow-batch.md`](references/workflow-batch.md) |
| 单条流程共享（人/部门/分部/群组/角色/岗位/所有人） | `workflow run workflow.sharePrepare` / `workflow.shareApply` | [`workflow-share.md`](references/workflow-share.md) |
| 发起/创建流程、填单、存草稿 | `workflow run workflow.createForm` / `workflow.createRequest` | [`workflow-create.md`](references/workflow-create.md) |
| 修改已存在流程的表单内容 | `workflow run workflow.editLoad` / `workflow.editPrepare` / `workflow.editApply` | [`workflow-edit.md`](references/workflow-edit.md) |
| 读取用户记忆偏好、OA 版本与当前用户身份；保存本轮语义记忆 | `workflow run workflow.memoryPrompt` / `workflow.memoryExtract` | [`workflow-memory.md`](references/workflow-memory.md) |

处理链：

- 记忆前置：新一轮对话或距上次成功读取记忆超过 6 小时 -> 先执行 `workflow.memoryPrompt`，顺带拿到 `oaContext`（OA 版本 + 当前用户身份），不要单独再查组织信息。
- 查询类意图 -> `workflow.search`。泛化待办查询**先看 `oaContext.smartGrouping`**（`memoryPrompt` 已给）：`false`（低版本）直接 `workflow.search` 原样渲染（CLI 自带分组统计，闭环，**不要带 `planJson`/`subCategory`**）；`true` 再 `workflow.todoStat` 统计分组，并**严格按 [`workflow-query.md`](references/workflow-query.md) 的「汇报式分组骨架」+「参与身份 → 分组去向表」划组**，把分组计划打包为一次带 `planJson` 的 `workflow.search`（不要自创分组体系）。
- 查看类意图 -> 优先用列表返回的 `requestId`；只有用户明确指向"第 N 条"时才用 `index`（分组场景加 `group`）定位。
- 单条操作 -> `workflow.operatePrepare` -> 核对预览与已有授权（存在差异才询问） -> `workflow.operateApply`。
- 批量处理（提交/置已读/催办/共享/转发/退回）-> **6 个都是单命令**（`workflow.batchSubmit` / `workflow.batchRead` / `workflow.batchSupervise` / `workflow.batchShare` / `workflow.batchForward` / `workflow.batchReject`）：`confirm: true` 与 `requestIds` 在**同一次调用**里传，**不需要先跑 Prepare，也没有 continuation**。三条路径按**目标的来源**选：
    - **目标是上一轮查询结果里的具体几条**（"前两条/刚才那些"、或点名条目）→ 直接把 `requestIds`（+ `confirm:true`）传给对应批量命令，**一次调用完成**，不要再多发一轮确认摘要。
    - **目标是一个范围（没有准确 `requestId`）** → **必须先数条数再执行**：先用 `scopeCondition`（与 `workflow.search` 同形的条件）+ `action:"total"` **只查条数**（`action` 在给了 `scopeCondition` 时**必填**，漏写报 `batch_action_required`），把「范围 + 条数」报给用户确认（`total=0` 但 `scopeTotal>0` 时要说明"有 N 条但不适用本次操作"，不能说成没有数据）。
    - **目标是一个范围、用户已确认条数** → 再用同一条 `scopeCondition` 配 `action:"execute"`；**循环由 CLI 内部完成**（查一页→执行→排除已处理/失败的 ID→再查，直到取完或触达上限），**不要自己写"查一页→数 ID→再执行"的多轮流程**。返回里给的是成功/失败条数、失败清单与 `stoppedReason`（**不含批次数等内部细节**），照它汇报即可——`scope_not_batch_eligible` 表示"范围内有数据但本次操作一条都取不到"（**不是**"没有数据"），要说明原因并给替代操作（如改 `workflow.batchRead`）。
- 单条共享 -> `workflow.sharePrepare` -> 核对预览与已有授权（存在差异才询问） -> `workflow.shareApply`。
- 发起流程 -> `workflow.createForm`（传 `workflow`，**目标写法优先用 `名称(ID)`**：自带显式 ID 时不查可发起列表、少一次往返，纯名称才走可发起列表模糊匹配；解析可发起的工作流并拿到 `continuation`；返回 `NEEDS_CLARIFICATION` 时按 `candidates` 与用户确认后用 `名称(ID)` 重发）-> 按用户意图填 `data` -> `workflow.createRequest`（`context` 传上一步的 `continuation`，`action` 取 `draft`/`submit`）。**必填是否齐不用模型判断**：`action:"submit"` 缺必填时命令不会创建流程，返回 `NEEDS_INPUT` + `missingFields`，一次问齐后带同一 `context` 重发；`action:"draft"` 则照常建草稿、缺失项只作提醒。
- 修改表单 -> `workflow.editLoad` 拿 `context` -> `workflow.editPrepare` -> 核对预览与已有授权（存在差异才询问） -> `workflow.editApply`。

## 执行原则（减少误路由、误重试和无效消耗）

### 1) 先拿最小必要信息，再执行

- 只是查待办时，直接 `workflow.search`，不要先做全量探查
- 用户已给出流程标题、编号或 `requestId` 时，不要先拉全量列表再本地过滤
- 批量操作的目标已有明确 `requestId` 时，直接把 `requestIds` 传给对应的 `workflow.batch*` 单命令（连同 `confirm: true`），**不要为了"看看哪些能批量提交"先做一次 `--batchType` 查询**（批量门禁按本机查询索引放行，那一次查询不参与放行）；**不要先跑任何 `Prepare`**——6 个批量命令都是一次调用完成，不存在两阶段。
- 查询条件里的名称解析不出唯一对象时，**按 CLI 返回的形态分两种处理**（对齐 V11.3，不要混为一谈）：① **澄清信封**（`ok:true` + `status=NEEDS_CLARIFICATION` + `data.candidates`）——工作流多/零命中、工作流类型/发起人/部门/分部/紧急程度**多命中**、表单字段名或选项值不唯一、字段元数据不可用；**用 `data.candidates` 与用户确认，拿到确认后用 `名称(ID)` 重发同一条命令**，**不要**另起一条"拉全量清单再自己筛"的命令（查询侧没有任何无条件的全量列举）；要发起流程时用 `workflow.createForm`，它走的是同一条澄清通道、同样会给出候选；**不要把它转述成"没有匹配的流程"或"查询结果为 0 条"**。② **`ok:false` + `error.subtype=*_not_found`**——工作流类型/发起人/部门/分部/紧急程度**0 命中**（V11.3 即硬失败，因为放行会静默丢掉该条件返回全量数据）；按 `error.message` 的提示（紧急程度会列出全部可选等级）与用户核对后改用 `名称(ID)` 重发
- 缺少的关键信息（目标流程、接收人、发起工作流）只问一次；能从记忆 `oaContext` 或上下文推断的不要反问
- **查询范围的缺省口径不要反问**：时间词 + 动作词（"本周接收的""今天有哪些待办"等）的默认含义已由 `references/workflow-query.md`「待办时间默认语义」定死，**照表直接执行**；`category` 按该文「大分类判定」定（句中出现"我/我的"或"提交/发起/创建"**不等于** `mine`）；不要因为用户没说"待办/已办"、或没说是发起时间还是接收时间就停下来反问——只有该文所列的三种真歧义才问

### 1.5) 大结果只摘要给用户

- 当前 CLI 的 `--json` 会把完整 JSON envelope 写 stdout；Agent 回复时不要原样粘贴完整 JSON
- 列表默认先取小页，优先 `pageSize=10`；若记忆里的展示偏好另有条数（如"每页 5 条"），以记忆为准；用户没有要求全量时不要自动扫完整数据集
- 需要全量统计时，按 `current` 分页分批读取，只累计任务所需字段和去重键，并报告已读取页数、命中数和是否还有更多
- 超长文本、大数组、详情原始响应或调试 JSON 需要保留时，优先落本地文件并向用户提供摘要和路径

### 2) 已知对象时直达动作

- 已知 `requestId` 或已从列表定位到目标时，直接对目标 operation 执行，不要重复查询
- 单条操作不要用批量能力替代；批量能力只用于用户明确要求处理多条

### 3) 错误语义驱动，而不是盲目重试

- 失败后先看进程退出码、`error.type`、`error.subtype` 和 `error.message`
- **除非错误明确提示可恢复或需要补充参数，否则不要重复刷同一个 operation**
- 写请求已经发出后，遇到结果不确定必须停止；不要把 `.apply` 当成可重试读操作
- 同一操作连续 2 次失败必须停止，不得第 3 次重试
- **认证失效以 `error.type=authentication` 为准**（`subtype` 多为 `session_expired`）：判据只看 `type`，**不要重试、不要当成"没有数据/筛选无匹配"**——按 `weaver-e10-shared` 的认证引导让用户重新完成 E10 登录授权，成功后重放原请求。探查、名称解析等子请求同样会抛认证错误（此前被包装成「接口未返回有效数据」，现已原样透出），先看 `type` 再判因。

### 4) 附件、图片和文件解析确认

- 用户明确要求读取、解析、上传或复用指定附件时，按该任务直接执行，不额外添加通用数据风险警告或 Yes/No 弹框。仅提供路径而没有操作意图时先明确任务；需要把文件发送到任务未涵盖的新外部服务时，先说明实际接收方、用途并取得授权。按实际数据路径描述处理过程，不断言所有附件都会先经过公网大模型。
- 风险提醒必须说明文件内容可能进入大模型上下文，也可能被发送到业务系统或解析服务。
- 上传前先按表单返回的 `fileUploadParams` 核对文件大小、扩展名格式和数量限制；不满足时先告知用户、不执行上传。
- 用户未确认前，不要运行会读取、上传或解析该文件的命令。

### 5) 命令输出读取纪律（禁止截断、禁止重复取数）

- **禁止对命令输出做管道截断**：不要用 `| head`、`| tail`、`| more` 等处理 `weaver-work-cli --json ...` 的 stdout。截断会破坏 JSON，并且必然导致重复执行同一条命令（实测最常见的一条命令被执行 2 次，就是 `| head` 引起的）。
- **一律直读 stdout（失败时读 stderr，见下条），不要落盘、不要写脚本回读**：`--json` 输出是**多行 pretty JSON**，且已按体积做过控制（`workflow.todoStat` 约 20 KB/400 余行；`workflow.search` 的条目已收窄到必要字段、泛化待办查询实测约 **14 KB**；`workflow.detail` 只有几 KB；`workflow.createForm` / `editLoad` 遇到大表单会落盘、stdout **只回一条提示**（提示里直接给出可照抄的读命令））——都在宿主单次输出上限以内，每行也都不长——**直接读即可**，不存在行长截断问题。**禁止**把 stdout 重定向到文件（`> /tmp/xxx.json`）再写脚本解析回读：它不会带来任何新信息，只会白白多出一次工具往返（实测多一轮约 +7s，占整轮耗时可观）。
- **`workflow.search` 的体积纪律（别等被截断）**：泛化待办按要求走 `planJson` 分组（各组独立渲染、各 10 条，体积天然分散）；要看更多用 `current` 分页续查；**不要靠加大 `pageSize` 一次拉全**。CLI 侧已按 **24 KB（美化口径）** 设体积守卫：超线时自动把完整结果落盘，并在结果**最前面**给出 `resultFile`（结构化 JSON）+ `resultMdFile`（纯 `finalMarkdown`），**stdout 仍保留全量 `finalMarkdown`** ⇒ 正常渲染**直接用 stdout 即可、不需要读文件**；只有需要完整结构化明细（如逐条 `requestId`）时才从 `resultFile` 按需提取，并一次读完（不要 `| head`/`| tail`）。宿主把输出截成一小段预览时：**不要重跑同一条命令**（结果一样、白烧一轮），改用更小页或 `planJson` 分组重取；宿主提示的落盘副本（`~/.workbuddy/projects/**/tool-results/**`）**不能用 Read 工具读**（会拿 `Permission … has been denied`），确实要用时以 shell 命令读取并只提取需要的字段。
- **失败出口在 stderr（stdout 为空即失败）**：命令失败时退出码非 0、**错误 JSON 只出现在 stderr**（`{ok:false, error:{type,subtype,message,retryable}}`），**stdout 是空的**。因此：**stdout 为空 → 一律视为失败并去读 stderr**，按 `error.subtype` 决定下一步（如 `todo_stat_requires_smart_mode` → 不要重试 todoStat，改走 `workflow.search`；`plan_requires_smart_mode` → 去掉 `planJson` 重查）；判断成败**以 `ok` 字段为准**，宿主界面把命令显示成"运行成功"只代表进程结束，不代表业务成功。
- **同一个 operation 最多执行一次**：拿到 stdout 后一次性解析完，不要先截断看一眼再重跑。
- **结果里出现 `resultFile` 时不要重跑命令**：`workflow.search`、`workflow.todoStat`、`workflow.createForm`、`workflow.editLoad` 等大输出 operation 会把完整数据落盘，并在结果**最前面**返回 `resultFile` 与 `largeOutputNotice`；`workflow.search` / `workflow.todoStat` 的 stdout 已保留可用内容，被省略的大字段（如查询的逐条明细、某工作流的 `formFields`、通知正文 `formFieldValues` 全文）再**按需提取**（只取要用的键，不要把整份读进上下文）；**`createForm` / `editLoad` 则相反——stdout 里已没有任何表单属性，必须照抄提示里的读命令把该文件整份读完**，之后不要再重读。两类都**不要重新执行 operation**。
- **`createForm` / `editLoad` 大表单超线时只回一条提示**（字段少时就是原样全量）：结果里**只有** `resultFile` / `persistedResult` / `outputBytes` / `largeOutputNotice` 四个键，**不带任何表单属性**。`largeOutputNotice` 里直接给出可照抄执行的读命令（文件路径 + `limit` = 该文件总行数），**先照抄它把文件一次读完、再继续下一步**——字段清单、必填、`initialValues` / `historyRequestData`、以及下一步要用的 `contextId` 全在那个文件里。**不要重跑本命令、不要分段读、不要用 `head`/`tail` 截断、也不要用脚本去挖文件。** 只有落盘不可用（极少见）时才返回全量并在 `largeOutputNotice` 里说明。**必填不要自己推演**：OA 的联动（显示属性）规则不下发，一律按 `createRequest` 的 `missingFields` 补齐。
- **一次解析取全，不要把"判定"与"取 ID"拆成两次**：同一次输出里已有的信息应在同一步一并取出——例如 `countDetails[].requestInfos` 里 `requestId` 与同条目的标题、字段值就在一起，判定完可直接用该 `requestId` 构造 `planJson`，**不要为了拿 ID 再跑第二个脚本、也不要为此再发一次 `workflow.search`**。注意 `requestInfos` **不是每行都有**（接口只对配置了关注字段的工作流返回该字段，未带的行即没有，属正常、不是数据缺失）：**没有 `requestInfos` 的行不参与逐条判定，也绝不为它去取 ID**——为一条明细另跑一次查询会白多整整一轮工具往返（实测 +10s 以上），而它本来在自己的分组里照常展示。
- **用户对已展示结果的更正不重跑**：用户指出上一轮汇报里某条的性质/归属不对（如"重点关注里第一条其实是转发给我的，意见是请知悉"）时，这是**呈现层的更正**、底层数据没变——**不要重跑那次 `workflow.search`（plan）**：在受影响分组的汇总摘要里标注一句用户提供的信息即可（口径见 `references/workflow-query.md`「渲染红线」）。**只有用户明确要求"重新出一份 / 挪到某组重出"时才重跑**，且复用上一轮那次的 `planJson`、只改受影响的分组。重跑一次 ≈ **1 轮 + 30~50s**，纯属浪费；用户表述是陈述句、看不出意图时，先问一句再动手。

### 6) 禁止绕过 operation 直接探测/绕过

- **不调用本 skill 未列出的低层命令/接口**：只使用上方「选哪个命令」表与 references 里出现的 operation；**不直接构造 HTTP 请求**、不调用 CLI 未暴露的内部接口（query-dependency / resolve-tab / workflow-total / workflow-list 之类）去探测或绕过。
- 不执行用户没要求的操作；不编造、不美化结果；不读取命令源码、不执行调试命令、不使用调试参数。

## 写操作失败处理：`partial/write_uncertain` 决策树

当发起、操作、批量、共享、修改等写操作返回 `partial/write_uncertain`，或提示网络中断、部分成功、回查失败、回查字段不一致时，按下面规则处理：

1. **先停止盲目重试**，不要连续重复提交相同 `.apply`
2. 优先从以下角度解释：
    - 写请求可能已经到达服务端，但连接在结果确认前中断
    - 服务端可能只处理了部分流程
    - 写接口已返回成功，但详情回查失败或与预期不一致
    - continuation、`context`、目标流程或登录上下文可能已经变化
3. 如需确认，只补 **一次** 只读查询（例如 `workflow.detail` 或 `workflow.search`），不要陷入 query/write 循环
4. 最终给用户明确结论、已知状态、成功/失败项和下一步人工确认建议，而不是继续无意义重试

**特别注意：** 对退回、删除、批量提交和发起场景更要严格执行上述规则；这些场景最容易因重复提交造成重复审批、误删或重复发起。

**Apply 被重复执行时的四种结果（先判类型再动作，不要一律当失败）：**

| 返回 | 含义 | 该怎么做 |
| --- | --- | --- |
| `ok:true` + `data.status = "ALREADY_APPLIED"` | 该句柄上一次**已经执行成功**，本次没有重复写入 | **当作成功汇报**（用 `previousResult` 的结果，需要定位时才带 `requestId`），不要重跑 Prepare、不要再 apply |
| `partial/write_uncertain` | 上一次**已发出写入请求、结果未确认** | 先只读核对目标是否已生效；已生效按成功汇报，确认没生效才重跑 Prepare |
| `validation/continuation_busy` | 句柄正被另一次执行占用，上一次**还没发出写入**（可安全重试） | **稍后原样重试同一条命令**，不要重跑 Prepare、不要换句柄 |
| `validation/continuation_consumed` | 占用该句柄的执行停在**无法判定的旧状态**（旧版本标记） | 先只读核对目标是否已生效，再决定是否重跑 Prepare |

> 不要只凭"命令报错"就认定"没做成"：`ALREADY_APPLIED` 是成功，`busy` 可以直接重试；只有 `write_uncertain` 和 `consumed` 才需要先只读核对。**任何时候都不要靠反复重跑 Prepare 来"试"。**

> **6 个批量单命令（`workflow.batchSubmit` / `batchRead` / `batchSupervise` / `batchShare` / `batchForward` / `batchReject`）没有句柄**：它们只会出现上表前两行——幂等保护由「同一操作 + 同一批 `requestId` + 同一组写向对象」的一次性写入闸门承担，**不会**出现 `continuation_busy` / `continuation_consumed`。`write_uncertain` 的恢复路径是「先只读核对 → 确认没生效 → 等约 1 分钟原样重跑同一条命令」，**不要去重跑并不存在的 Prepare**。

> **`ALREADY_APPLIED` 对用户只报结果**：这是 CLI 内部的幂等保护（防止重试造成重复写入），不是用户关心的事件。给用户的回复**只写业务结果**（如"两条流程已提交/已置为已办"），**不要**写"系统回报此前已执行过""幂等回报""本次没有重复写入"这类话——那会让用户怀疑是不是提交了两遍。只有当 `previousResult` **不是成功态**、或需要解释"为什么这次没有再次写入"时才说明。

Windows PowerShell：

```powershell
weaver-work-cli workflow schema
weaver-work-cli --json workflow run workflow.search --input-json '{"category":"todo","pageSize":10}'
weaver-work-cli --json workflow run workflow.todoStat --input-json '{"category":"todo"}'
weaver-work-cli --json workflow run workflow.detail --input-json '{"requestId":"123456"}'
weaver-work-cli --json workflow run workflow.operatePrepare --input-json '{"requestId":"123456","action":"submit","opinion":"同意"}'
weaver-work-cli --json workflow run workflow.operateApply --input-json '{"requestId":"123456","action":"submit","continuation":"wc-1a2b3c4d5e6f7a8b","confirm":true}'
weaver-work-cli --json workflow run workflow.createForm --input-json '{"workflow":["费用报销"]}'
weaver-work-cli --json workflow run workflow.createRequest --input-json '{"context":"wc-1a2b3c4d5e6f7a8b","data":{"main":{}},"action":"submit"}'
```

macOS/Linux（bash/zsh）：

```bash
weaver-work-cli workflow schema
weaver-work-cli --json workflow run workflow.search --input-json '{"category":"todo","pageSize":10}'
weaver-work-cli --json workflow run workflow.todoStat --input-json '{"category":"todo"}'
weaver-work-cli --json workflow run workflow.detail --input-json '{"requestId":"123456"}'
weaver-work-cli --json workflow run workflow.operatePrepare --input-json '{"requestId":"123456","action":"submit","opinion":"同意"}'
weaver-work-cli --json workflow run workflow.operateApply --input-json '{"requestId":"123456","action":"submit","continuation":"wc-1a2b3c4d5e6f7a8b","confirm":true}'
weaver-work-cli --json workflow run workflow.createForm --input-json '{"workflow":["费用报销"]}'
weaver-work-cli --json workflow run workflow.createRequest --input-json '{"context":"wc-1a2b3c4d5e6f7a8b","data":{"main":{}},"action":"submit"}'
```

## 不在本 skill 范围

- 「姓名 → 人员 ID / 部门 / 分部 / 岗位」解析交给 `weaver-e10-hrm`，本 Skill 不自行解析组织对象。
- 非流程类 E10 能力（发票、邮件、日程、组织、费控等）不由本 Skill 承载。
