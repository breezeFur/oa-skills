# 发起流程

## 什么时候读取

用户要"发起/创建/提交一个 XX 流程""按某工作流填写表单并发起"时读取本文件。覆盖 `workflow.createForm` / `workflow.createRequest` 两条命令。

## Operation

| Operation | 风险 | 固定规则 |
| --- | --- | --- |
| `workflow.createForm` | read | 必传 `workflow`（`名称(ID)` / 名称（**可一次给多个说法**：数组多元素，或一个元素内用英文逗号分隔）/ ID）：内部解析出**可发起**的工作流并载入发起表单（runtime/frame/字段清单/fileUploadParams），顺带返回该工作流的发起偏好。不落任何业务数据。解析不出唯一目标时回澄清（`NEEDS_CLARIFICATION`，候选见 `candidates`）。**已给 `名称(ID)` / 纯 ID 时不查可发起列表**（名称与可发起性直接由表单载入接口给出），该 ID 不存在 / 无发起权限时同样回澄清，但带 `clarificationReason` 区分 |
| `workflow.createRequest` | high-risk-write | requiresConfirmation；必传 `context`/`data`/`action`；`action` **必填**（`draft` 存草稿 / `submit` 提交审批）；遇 `partial`/`write_uncertain` 禁止重试 |

## 发起链路（两条命令，模型不需要自己判断必填）

1. `workflow.createForm`：按用户说法解析可发起的工作流并载入表单，拿回 `continuation`（表单会话短句柄，载荷由 CLI 托管在本机）与必填/可写字段清单；**同时返回 `historyRequestData`**——本表单必填字段在历史流程里的取值参考（`null` = 没有可参考的）。
   - 返回 `NEEDS_CLARIFICATION` 时按 `candidates` 向用户确认（只问完整名称或其它可用于检索的关键词，**不要向用户索取 ID**），确认后由你按 `名称(ID)` 拼好、重发**同一条命令**。
2. 按用户意图把字段值填进 `data`（键用字段 id）：**用户说了的照用户说的填；用户没提到的必填字段，先看第 1 步的 `historyRequestData`**——能直接照用的就填上（不必再问用户），其余留空。
3. `workflow.createRequest`：`context` 传第 1 步返回的 `continuation`，`action` 按用户意图取 `draft`/`submit`。
   - `action: "submit"` 且仍有必填缺失 → **命令不会创建流程**，返回 `NEEDS_INPUT` + `missingFields` + `historyRequestData`（**只含本次新出现的必填字段**的历史参考值，可能为 `null`）；**先按 `historyRequestData` 判断这些字段能不能参考**，能参考的直接填入重发，不能的再把缺失项**一次问齐**后带同一 `context` 重发 `action: "submit"`。
   - `action: "draft"` 且仍有必填缺失 → 照常建草稿，`missingFields` 只作提醒（必须原样转述给用户）。
   - **不要（也无法）自己判断"必填是否齐"**：缺失与否由命令按**实际所填数据**（含联动带出值）实时算出，照 `missingFields` 走即可。
4. 成功时命令**直接返回 `requestId` / `requestName` / `url`**（`status` 为 `CREATED` = 已建草稿、`CREATED_SUBMITTED` = 已提交审批）——**按返回值汇报即可，不需要再去查询反查**。
   - **发起/查询完成后不要主动打开任何页面**：`url` **只在回复文本里以可点链接给出**，**不要**把它交给浏览器预览面板、也**不要**顺手调 `workflow.open` / `workflow.pageOpen` 去"打开看看"。**只有用户明确说"打开这条 / 打开看看 / 给我链接"时**才打开——用 `workflow.pageOpen`（动态页 `page:"view"` 配 `requestId`）或 `workflow.open` 走正规入口，**地址一律由 CLI 按内置地址表生成，不要自行拼接 OA URL**。
5. 遇 `partial`/`write_uncertain` 停止，先只读回查（detail/summary），不自动重放。
6. 被重复执行时按句柄状态分流（**不要一看到"用过"就重跑整条链路**）：
   - `ok:true` + `data.status = "ALREADY_APPLIED"`：该 `context` 上一次已经**发起成功**，本次没有重复写入——按返回值里的 `requestId` / `previousResult` 作为成功结果汇报，**不要重跑 createForm、不要再 createRequest**；
   - `partial`/`write_uncertain`：上一次已经发出写入、结果未确认——先只读回查（`workflow.search --category mine --requestId <目标ID>`）确认是否已发起，确认没发起才重跑；
   - `validation/continuation_busy`：该 `context` 正被另一次执行占用、上一次还没发出写入——**稍后原样重试同一条命令**即可（不要重跑 createForm、不要换句柄）；
   - `validation/continuation_consumed`：占用该句柄的执行停在无法判定的旧状态——先只读回查确认是否已发起，确认没发起才重跑。

**省时纪律（这几件事一次都别做，每违反一条就多烧一轮工具往返）**：① 拿字段清单**不要**写脚本解析 `resultFile`——输出里给了 `largeOutputNotice` 时直接照抄它给的那条读命令（路径与 `limit` 都写好了）把文件一次读完；② `data` 的键**不要**写 `"字段名(字段ID)"`（只认字段 id）；③ 只读字段**不要**传（看 `editableFields`）；④ 读命令输出**不要**用 `head`/`tail` 截断；⑤ 输出被宿主截断时**不要**去找宿主的工具结果目录（`~/.workbuddy/projects/**/tool-results/**`：读不了，去了必白跑一轮），按输出最前面的 `resultFile` 取。

**输出纪律（与上面的省时纪律同理：多写的每一句都在拖长回复，并让用户看不懂）**：① 面向用户**只给三样**——"这次做了什么、结果如何" ＋ "**已填内容预览**"（展示口径见下文「主表（已填内容）展示规则」）＋ "需要用户提供什么"，其余不说——**尤其不要交代"用了哪个流程 / 编号是多少 / 我是怎么判断的"这类内部依据**（**唯一例外**：**本次决策若依据了历史记忆，必须按 `SKILL.md`「总原则」里的全局规则向用户说明依据了记忆**）；② **不要复述自己的判断过程、取舍与推演**，也不要写自我批评或事后反省——用户要的是结果，不是你怎么想的；③ **不要把澄清分支的区别讲给用户**（如"不是有多个候选要挑，而是一条都没命中"）：该报"系统里没有「XX」"就按下文浏览按钮口径直接说结论，**不要解释你是怎么判定出来的**；④ 需要用户给值时**只说清"要什么值"**，不要顺带解释"我为什么判断不出来"。

## 输入

### workflow.createForm

- `workflow`（string[]，必填）：工作流条件——`"名称(ID)"` / 纯名称 / 纯数字 ID。
  - **自带显式 ID（`"名称(ID)"` 或纯数字）时不查可发起列表**：流程名与"你能不能发起"都由表单载入接口直接给出，因此比"按名称解析"少一整次往返。该 ID 不可用时仍回澄清，但会带 `clarificationReason` 说明是**哪一种**（见下）。
  - **纯名称**按当前用户**可发起**的工作流做模糊匹配，**可一次给多个说法**：数组多个元素（`["<说法1>","<说法2>"]`）与一个元素内用英文逗号分隔（`["<说法1>,<说法2>"]`）**完全等价**，CLI 会把各说法拆成关键词、命中取并集去重。
  - **直接选定并载入表单**时，`selectionSource` 标明是如何选定的：`workflowId`（按 ID 命中）/ `single`（唯一命中）/ `exactName`（全名精确匹配）。`exactName` 表示 CLI 已替用户选定，**不要再反问“您指的是哪一个”**。
  - **0 命中**，或**多命中且没有与所写完全一致的** → **澄清**：返回 `status: "NEEDS_CLARIFICATION"` + `candidates`（每项含 `id`/`name`/`display`，`display` 是 `名称(ID)`），此时**不返回任何表单数据**。把候选**原样**列给用户（不加 "(Recommended)"/"推荐" 等后缀，由用户明确选择），选定后用 `display` 的 `名称(ID)` 重发同一条命令。
  - **自带显式 ID 但该 ID 不可用** → 同样回澄清（`candidates` 为空），并带 `clarificationReason` 标明是**哪一种**——这两句话**必须分开说、不许混**：
    - `clarificationReason = "workflow_not_exist"`：该目标不存在（可能已删除或被停用）。如实告知"这个目标不存在"，请用户改用该流程的**完整名称**（或其它可用于检索的关键词）重发——**不要向用户索取 ID**；**不要**说成"没有可发起的工作流"这类模糊说法。
    - `clarificationReason = "no_create_right"`：流程**存在**，但当前账号**没有发起权限**。**必须明确说出「存在但没有发起权限」**，绝不能转述成"流程不存在"；并给出下一步：改用其他可发起的流程，或联系管理员为该流程授予发起权限。
- `relatesTo`（string，可选）：关联对象 id，仅透传不影响表单初始化。
- 返回 `continuation`（表单会话短句柄 `wc-…`，形如 `wc-1a2b3c4d5e6f7a8b`；载荷由 CLI 托管在本机，**它就是第 3 步 `createRequest` 的 `context` 入参**）、`runtime`/`frame`、字段清单、`initialValues`、`historyRequestData`（本表单**必填字段**的历史参考值，`null` = 无可参考）、`systemFields`、`fileUploadParams`、`workflow`、`launchPreferences`。
- **字段多的表单只回一条提示**（字段少时无此形态、就是原样全量）：此时结果里**只有** `resultFile` / `persistedResult` / `outputBytes` / `largeOutputNotice` 四个键，**不带任何表单属性**。
  - **看到 `largeOutputNotice` 就照抄它给的那条读命令、把文件一次读完——这是继续下一步的前置动作**：那条命令里文件路径与 `limit` 都已经算好（`limit` = 该文件总行数，一次就能读完），直接执行即可。**字段清单、必填、`initialValues`、`historyRequestData`，以及第 3 步 `createRequest` 要用的 `contextId` 全都在那个文件里**，不读它手里就没有任何字段信息。**不要重跑 `createForm`、不要分段读、不要用 `head`/`tail` 截断、也不要用脚本去挖文件。**
  - 文件里是**完整结果**（未裁剪的 pretty JSON）：`fields` 是**完整结构**（每个字段带 `id` / `name` / `subFormId` / `componentKey`，另有 `options` / `format` / `fileUploadParams` 等按需出现的键），并带 `requiredFields` / `subFormRequired` / `editableFields` / `initialValues` / `systemFields` / `continuation`。**`fields` 里不标必填**——哪些是必填只看 `requiredFields` / `subFormRequired`。
  - **`fields` 是「布局级字段全集」，不等于"页面上肉眼可见的字段数"**：它含联动隐藏、以及未在当前页展示的字段（真机实例：某表单 `fields` 278 个，其中 178 个是明细列，而真正能填的只有 60 个）。**判断"哪些字段能填"只看 `requiredFields` + `subFormRequired` + `editableFields`**，不要拿 `fields` 的条数当可填字段数，也不要因为"表单上看着没这么多"就怀疑字段清单不对。
  - **输出被宿主截断时**（只看到 2048 字节预览、或提示"已保存到文件"）：**不要去读宿主的工具结果目录**（`~/.workbuddy/projects/**/tool-results/**`：没有读权限，去了必白跑一轮），按同一份输出最前面的 `resultFile` 取完整结果。
  - **不要为了"看清字段"重跑 `createForm`**：返回什么就按什么拼 `data`。

**查询词策略**：

- **优先用记忆别名改写后再传**：用户给出的表达命中记忆别名（如"手机话费报销"含别名"费用报销"）→ **直接传记忆别名**（可与原词并列成一次多关键词，见下条），**不要分两次命令试探**（先只传原词、没命中再换一个词）。
- **一次给多个说法**：`workflow` 同一批次可并列多个说法（数组多元素 或 英文逗号分隔，见输入节）；**不确定完整名称时，把①用户说法 ②可能的全名/同义说法 ③一个更宽的「上位词」都并列进这一批**（如 `["原说法","同义说法","上位词"]`）。**同一批次加词不额外花往返**：命中取并集去重，某个词命不中只是白给，命中了就多一条线索。
- **上位词可以放进批次，但命中后必须核对**：`"话费"` / `"会议"` 这类宽词可能命中**语义无关**的工作流（如“话费”→“话费补贴标准审批流程”）。载入表单后**先核对 `workflow` 里的名称/类型与用户意图是否一致**（报销类意图 → 名称应含“报销/费用”，不应是“补贴标准/行政事务”类）；**不一致就绝不要往下填字段**，改用记忆别名或更准的说法重发 createForm。**`selectionSource: "single"`（唯一命中即选定、不澄清）是最该核对的一档**。
- **真正被禁的是"分多次命令逐词去撞"**：禁止先甲、再乙、再丙地反复试（把"换词"当检索策略，每试一次多烧一轮往返）；**同一条命令里并列多个词、其中包括一个上位词，都不属于被禁的情形**——那是**补充召回**，不是拿宽泛词当主力检索。
- **不要再继续换词试探**（一次多关键词后仍未定，就反问用户确认）。

**拿到 form 返回后直接按用户已给信息拼 `data` 并立即调用 `createRequest`**——不分析字段、不猜映射、不比对选项，**也不要用空 `data` 先探测必填清单**（用户说了什么字段就填什么、值用用户说过的说法；必填缺失由 `createRequest` 的 `missingFields` 告知）。

**`initialValues`**：OA 初始化表单时预填的字段值（含 onLoadForm 联动带出值），`data` 应包含这些值（用户明确填写的以用户为准）；**带 `subFormId` 的是明细表字段**（放进 `details` 对应行对象），**不带的是主表字段**（放 `main`）。这些默认值 **CLI 会自动并入**（主表进 `main`，明细按你建的行补），**漏带不会因此被报成缺必填**——不要为了"怕丢默认值"多跑一轮。反过来：**`missingFields` 里出现的字段就是真的没值**（OA 对浏览按钮类默认值可能只下发类型标记、不下发值），此时必须问用户，不要猜值。

**`systemFields`**：`permissions` 给各系统字段的 isview/isedit/ismandatory，`defaults` 是默认值，`levelOptions`/`secLevelOptions` 是紧急程度/密级选项。**只有 `isview=true` 且 `isedit=true` 的系统字段才需要填**；紧急程度/密级**只从这两个 options 取**（不得使用记忆、表单字段或其他来源）；**`defaults` 已有非空值即视为已满足，不要询问用户、直接采用**；仅当 ismandatory=true 且默认值为空时才需要用户提供。

**`launchPreferences`**：该工作流的发起偏好（`available` + `promptText`）。`promptText` **只是「该工作流维度」那一段记忆**——全局画像 / 全局别名（`user.md` / `memory.md`）已由入口的 `workflow.memoryPrompt`（无参）给过，这里不再重复下发，所以**不要再调一次无参 `memoryPrompt` 来"补全"、也不要把两份拼接**（会重复）。`available: true` 时**优先按 `promptText` 里用户过往的常用取值/口径来补当前 `data` 里用户没说的字段**；与用户本次明说的冲突时以用户本次为准。`available: false`（或带 `note`）说明该工作流还没有偏好或读取失败——**按新用户处理，不要重试读取**。

### workflow.createRequest

- `context`（string，必填，minLength 1）：**第 1 步 `createForm` 返回的 `continuation`**，原样回传；两条命令必须同一值，禁止手工构造/修改/复用他处。
- `data`（object，必填）：表单字段值，结构 `{"main":{...},"details":{"<subFormId>":[{...}]}}`。
- `action`（enum `submit`|`draft`，必填）：`submit`=提交审批（必填缺失阻断，返回 `NEEDS_INPUT`，**不创建流程**）；`draft`=仅保存草稿（必填缺失不阻断、状态仍是 `CREATED`，**但 `missingFields` 仍随结果返回**，供模型查看并提示用户提交前补齐）。
- `requestName`（string，可选）：流程标题。form 返回 `requestName` 非空（OA 已有标题）时用其值；为空时**只有用户原话明确给了标题**（如"标题叫 X"）才用用户给的；**用户没给就不要自己编**——标题 `ismandatory=true` 且没有可用的默认值时，`createRequest` 会返回 `NEEDS_INPUT`，按 `missingFields` 向用户问一次并补齐。**标题不得用其他字段值（留言内容/工作流名/事由等）替代**：标题是用户可见的流程名称，用别的字段内容做标题会与流程内容耦合，OA 列表里难以辨识。
- `requestLevel`（string，可选）：紧急程度，取 `systemFields.levelOptions` 的 code。
- `secLevel`（string，可选）：密级，取 `systemFields.secLevelOptions` 的 id。
- `remark`（string，可选）：签字意见。
- `verificationConfirmed`（boolean，可选）：节点字段校验需用户确认时显式确认继续提交。

## 示例

### ① 解析工作流并载入表单（拿到 continuation）

Windows PowerShell：

```powershell
weaver-work-cli --json workflow run workflow.createForm --input-json '{"workflow":["<工作流名称>"]}'
```

macOS/Linux（bash/zsh）：

```bash
weaver-work-cli --json workflow run workflow.createForm --input-json '{"workflow":["<工作流名称>"]}'
```

### ② 填好字段后一次完成发起（action 必填）

Windows PowerShell：

```powershell
weaver-work-cli --json workflow run workflow.createRequest --input-json '{"context":"<createForm返回的continuation>","data":{"main":{"<字段id>":"<字段值>"}},"action":"submit"}'
```

macOS/Linux（bash/zsh）：

```bash
weaver-work-cli --json workflow run workflow.createRequest --input-json '{"context":"<createForm返回的continuation>","data":{"main":{"<字段id>":"<字段值>"}},"action":"submit"}'
```

## 返回

- createForm：`status` 为 `FORM_READY` 时给 `continuation`、`workflow`、`runtime`、`frame`、`requiredFields`（字段 id 数组）、`subFormRequired`（subFormId → 字段 id 数组）、`editableFields`（**可写字段 id 白名单**，已并入 `requiredFields` 的字段）、`fields`（**布局级字段全集**，含联动隐藏/未在当前页展示的字段，**不等于"页面上肉眼可见的字段数"**）。**字段多的表单只回一条提示**：此时只有 `resultFile` / `persistedResult` / `outputBytes` / `largeOutputNotice` 四个键，照抄提示里的读命令把文件一次读完即可拿到这里列出的全部内容（含 `contextId`）、`initialValues`、`systemFields`、`fileUploadParams`、`launchPreferences`、`requiredInfoWarning`。**不返回 OA 的联动（显示属性）规则**——必填一律以 `createRequest` 的 `missingFields` 为准（见「注意」）。`status` 为 `NEEDS_CLARIFICATION` 时只给 `candidates` / `clarificationKeyword` / `clarificationReason`（存在时，见「输入」里的 `workflow_not_exist` / `no_create_right`）/ `candidateCount` / `clarificationQuestion` / `note`，**不含任何表单数据**——它不是失败（`ok:true`），也不代表查询已执行。
- createRequest：`status`（`CREATED` / `CREATED_SUBMITTED` / `CREATED_SUBMIT_FAILED` / `NEEDS_INPUT` / `NEEDS_CONFIRMATION` / `ALREADY_APPLIED`）、`requestId`、`requestMark`、`requestName`、`url`、`contextId`、`fields`（确认预览：本次所填字段的落库结果，"我填的值到底存成了什么"就看这里）、`previewDetails`（明细表按列组织：`columns` 表头 + `rows` 每行明细；明细表按它排 Excel 列表格）、`missingFields`（**恒有值**：submit 成功时是空数组，draft 时是"提交前还需补齐"的提醒）、`missingFieldsNotice`（draft 且有缺失时的一段可直接转述的提醒文本）、`linkageResult`（联动带出/清空，原样转述）、`verification`（节点字段校验结果）、`attachmentFolderIds`、`submitResult`（提交结果，`success` / `failed`；**只在本命令真正发起过提交（`action:submit`）时出现**，`action:draft` 不带）、`submitFailReason`（**提交失败原因**：接口返回的可执行文案，仅 `submitResult: "failed"` 时出现）。
  - `NEEDS_CONFIRMATION`（`ambiguities` 非空）时同时给 `resolvedValues`（"我传的值 → 服务端最终值"的回显）与 `missingFields`——先把 `ambiguities` 解决掉，再用同一 `context` 重发。
  - `needVerificationConfirm: true` 时流程**已创建但未提交**：向用户确认后，用本次返回的 `requestId` 走提交（`workflow operateApply action=submit`）；**不要用同一个 `context` 重发**——该句柄已消费，重发只会拿到 `ALREADY_APPLIED`。
  - **`CREATED_SUBMIT_FAILED`（提交结果＝失败）**：流程**已创建为草稿**，但提交被服务端拒绝、**未进入审批**——表单数据已经落库，`requestId` / `requestName` / `url` 与成功时一样都给了（可直接打开查看或编辑），差别只在提交结果。此时 `submitResult: "failed"`、`submitFailReason` 是接口给出的失败原因。**处置：把失败原因原样转述给用户，并给出 `url`**；**不要**读成"什么都没做成"，也**不要**原样重发同一次提交（会再堆一份草稿）。
  - `submitResult`：`CREATED_SUBMITTED` 时为 `"success"`（不带 `submitFailReason`）；`CREATED_SUBMIT_FAILED` 时为 `"failed"`；**被节点字段校验拦下或未确认校验（`needVerificationConfirm`）时本就未提交，不返回该字段**。
  - **`historyRequestData`（历史参考值，两条命令都会给）**：范围是**本工作流**、**近一年、非草稿、按发起时间倒序的前 5 条**「我发起的」流程——不是"所有流程混在一起"，所以里面每条都是同一张表单的单据，字段可直接对照；形如 `[{requestId, requestName, createTime, fieldValues: [{fieldId, fieldName, value}]}]`；`value` 已按字段类型给出**可直接复用**的写法——浏览按钮 / 选项类为 `名称(id)`（多值以 `、` 分隔）；**附件类为对象**（形如 `{"formField":{"id":"<字段id>"},"dataOptions":[{"optionId":"<附件ID>","content":"<文件名>","type":"<文件类型>"}]}`，可整块放进 `data`，见「历史流程数据参考规则」第三条）；其余为普通字符串。**`null` 表示没有可参考的历史数据**（不返回空数组）；某条历史流程在这批字段上一个值都没命中时会被整条剔除（所以条数可能少于 5）。**你不需要自己再去查历史流程。** 两条命令给的覆盖范围不同：
    - `createForm` 返回的那份：**本表单必填字段**（`requiredFields` / `subFormRequired`）的取值——填 `data` 时就用它把能补的必填字段补上。
    - `createRequest` 返回的那份（`NEEDS_INPUT` / `NEEDS_CONFIRMATION` 且 `missingFields` 非空时附带，其余情形不出现）：**只含本次新出现的必填字段**（`createForm` 时还不是必填、联动命中后才变成必填的那些；`createForm` 已给过值的字段**不重复返回**）。
  - **处置顺序（必守）**：`missingFields` 非空时**先看 `historyRequestData`**——这些字段的历史值能直接照用时，**直接填进 `data` 重发，不要拿去问用户**（这正是它存在的意义；`createForm` 已经给过的字段这里不会再给，那些值在第 2 步就该用上）；**历史值缺失、或与本次情形明显不适用**时，才把这些字段一次问齐后带同一 `context` 重发 `action: "submit"`。**不要**把 `historyRequestData` 原样抛给用户当"参考列表"。

## 历史流程数据参考规则

历史流程数据有两个来源：命令随 `createForm` / `createRequest` 直接给的 `historyRequestData`，以及你自己按它的范围说明核对过的同类历史流程。**历史流程里的字段值只能按下面四条使用**——四条之外一律不推算、不拼接、不凭印象补值：

1. **取值一致、且能推断与本次业务同类 → 可直接采用**：某个字段在**命中的历史流程里取值完全一致**（**一条也算**），并且对照这些历史流程的**其他字段值**，能推断它们和本次要填写的表单属于同一类业务时，直接把这个值填进 `data`，不必再问用户；**取值不一致**时，才需要**三条及以上**取值相同（同样要满足"能推断与本次同类业务"），否则按规则 2 处理或问用户。
2. **看得出规律 → 按规律生成新值**：历史取值呈现可推断的规律（如编号递增、日期递推、金额分档）时，按该规律生成本次的新值；**规律推不出来就不要用**，照常问用户。
3. **附件对象 → 直接复用，不要重新上传**：`historyRequestData` 里附件字段的 `value` **就是可直接使用的完整对象**（形如 `{"formField":{"id":"<字段id>"},"dataOptions":[{"optionId":"<附件ID>","content":"<文件名>","type":"<文件类型>"}]}`）——**把它整块放进 `data` 里该字段的位置**（主表字段进 `main`，明细字段进对应行的对象）即可，**不要自己拆解或改造**。两条硬要求：① `optionId` 只能用历史值里给的这个 ID，**不要拿文件名或其它字符串去拼**——拼出来的 ID 指向不存在的文件，命令不会报错、但附件是坏的；② `type` 照抄历史值（图片是 `image`、普通文件是 `file`），**不要改成别的**。这样复用就**不需要重新上传本地文件**（因此也不触发附件上传前的那句提醒）；只有用户本次要换成新附件时，才走上文的上传流程。
4. **发票字段 → 一律不允许复用**：历史流程里填过的发票**不得**用作本次的发票值，任何情形下都要按用户本次提供的发票重新取值（见「注意」的发票字段条目）。

## 注意

- 不传凭据：业务输入禁止出现 Cookie/ETEAMSID/Token/`header.operator`（CLI 托管）。
- **`data` 的键只能取 `editableFields` 里的字段 id**（可写字段白名单；**明细表的必填字段**见 `subFormRequired`，它们照常可写、但不在 `editableFields` 里）。**唯一例外：`missingFields` 点名的字段，即使不在 `editableFields` 里也必须传**——`missingFields` 是**按你本次实际填的值、结合显示属性（联动）规则实时算出来的"最新缺失必填项"**，而 `editableFields` / `requiredFields` 是 `createForm` 那一刻的**静态快照**：那时联动还没跑，联动命中后才变成必填的字段当时既不在 `requiredFields`、也不在 `editableFields` 里。所以补值**一律以 `missingFields` 为准**，不要因为"它不在 `editableFields` 里"就把用户给的这条值丢掉。**大表单只回提示时，可写白名单就在该文件的 `editableFields` 里**——它是**完整**的可写字段 id 列表（= 非必填的可写字段 ∪ `requiredFields`）。`readOnly` / `disableEdit` / 不可见字段**一个都不要传**——传了整单会被拒（`notEditable`），得把只读字段全部摘掉重跑一轮。**看到 `notEditable` 不要重试、不要换字段 id 绕过**，移除这些字段后重跑。
- 附件/文件：字段值是附件项数组需上传本地文件时，按用户明确的附件上传任务调用实际可用的上传工具；已有授权不重复警告，新增外部接收方才说明并询问。
- 附件上传限制：上传前核对该字段的上传限制，不满足先告知用户、不执行上传。看该字段的 `fileUploadParams` 三项——`sizeLimit`（MB）、`formatLimit`（`mode` + `formats`；`formats` 为 `*.*` / `*` 表示不限制后缀）、`maxNum`（数量上限）：小表单看 stdout 的 `fields`，大表单看你已经读到的 `resultFile` 里的 `fields`。
- 发票字段（componentKey `EinvoiceComponent`）：支持两种赋值方式：① 从票夹选取：使用 `weaver-e10-yepiaotong` 技能查询票夹里已有的发票对象；② 使用 `weaver-e10-yepiaotong` 技能上传本地发票文件，并取上传后的发票对象。方式 ② 按用户明确的上传授权执行；若实际需要发送到请求未涵盖的新外部服务，说明接收方和用途后询问。用户未明确发票字段如何赋值时，先反问用户，不需要提前检测 `weaver-e10-yepiaotong` 技能是否可用，真正需要使用上述两种方式给发票赋值时，workbuddy环境下可直接到技能市场搜索【泛微E10业票通发票管理】并自动安装，搜索不到时反馈给用户，其余环境遇到技能缺失时直接反馈给用户。
- 发票类字段的历史值不可照抄。
- 发票值拿不到时直接问用户。
- 日期强规则：字段带 `format`（如 `yyyy-MM-dd HH:mm`）时必须严格按 `format` 传完整值，只传日期会报 `DATETIME_FORMAT`，按提示补时间重传，不要靠命令自动补时间。`format` 就在 `fields[].format` 上（**没有该键就是没有格式要求**）：小表单看 stdout 的 `fields`，大表单看你已经读到的 `resultFile` 里的 `fields`，**不要为了拿 `format` 再读一次文件**。
- **富文本字段（componentKey `RichText`）**：支持 HTML 内容、不受 maxLength 限制。**内容来自本地文档（docx/pptx/md 等）或结构化材料时，必须先把源内容转成 HTML（保留 h1-h3 层级、table 表格、ul/ol 列表结构）再填入，禁止直接填纯文本**；用户明确只要纯文本时除外。文本 / 富文本字段直接传字符串即可（CLI 按字段元数据落库），不需要也不允许把它包装成 `{id,name}` 之类的浏览按钮结构。
- **字段键**：`main` 的键、`details[subFormId]` 行对象的键**都必须是字段 id**（`fields[].id`）。`"字段名(字段ID)"` 这种写法**表单 data 不支持**（那是查询条件 `filterFields` 的写法），混用会报「存在重名或无法识别的表单字段，请改用字段 id」并白跑一轮。
- 字段**值**格式：选项传 `name`；人员范围（EmployeeScope）传对象数组 `{"name":名称,"type":类型}`，类型取 user/dept/subcompany/group/role/position/external/all/allExternal。
- **浏览按钮 / 人员 / 部门类字段**（值传字符串，CLI 自动转 ID）：可写 `名称`，也可写 `名称(ID)`（括号内是纯数字时按 ID 用、不再查名）；纯名称**首轮就该一次给多个说法**（与上面 `workflow` 同口径：**同一字符串内用英文逗号分隔**，如 `"全称写法,简称写法"`；说不出完整名称时的展开口径见下文「必填的浏览 / 人员 / 发票类字段」那条），CLI 会把这些说法拆开、连同整串一起拿候选：**只有命中唯一、或某个候选与整串／某个说法完全同名时才会自动采用**，否则会把所有候选列出来让你向用户确认（不会拿一个“最接近”的结果蒙过去）。**该字段允许多选时，多值用数组**（每个元素各自可以带多个说法）。**不支持裸 ID**——只写数字会被当名称去查，查不到就是 `NOT_FOUND`。
- **澄清时一律不向用户索取 ID**：任何"名称没对上 / 候选要确认"的场合，只问该对象的**完整名称**，或**其它可用于检索的关键词**；确认候选后的回传值（`{"id":…,"name":…}`）由你按候选自行拼好，**不要让用户提供 ID**。
- **人员范围（EmployeeScope）解析失败**：`createRequest` 返回 `NEEDS_CONFIRMATION`，`ambiguities` 里 `kind = "EMPLOYEE_SCOPE"`：
  - `reason = "NOT_FOUND"` → 系统里没有该名称，**一次明确告知用户**“没找到「XX（类型）」，请给出该对象的完整名称，或其它可用于检索的关键词”，最多重试 1 次；
  - `reason = "MULTIPLE_MATCHES"` → 列出候选（`candidates`）让用户选，选定后按 `{"optionId","content","type"}` 回传；
  - `reason = "NOT_RESOLVED"` → 名称/类型齐了但没拿到 ID，通常上一次解析没成功，按上面两种口径让用户确认；
  - **禁止**因为"命令返回 ok"就当作字段已填好——出现 `ambiguities` 时必须先解决，否则该字段不会进入保存体。
- **静态必填标记未下发（`requiredInfoWarning`）**：`createForm` 返回的 `requiredInfoWarning` 非空时，说明 OA 没下发该表单的**静态**必填配置，此时 `requiredFields` / `subFormRequired` 只含系统字段（流程标题等）——**不代表该表单没有业务必填项**（本租户的业务必填多为**条件必填**：OA 的联动规则只在字段组合命中时才要求必填）。处置一句话：**照常调 `createRequest`，按 `missingFields` 补齐**。
  - **不要自己推演"必填是否齐"**：`createForm` **不下发** OA 的联动（显示属性）规则——规则的触发条件往往取决于你还没填的字段，**发起前无从判断**（本文档不列任何具体条件；**也不要把你从文档或记忆里看到的任何条件样例当作本次的命中原因**）。缺失与否由 `createRequest` 按**实际所填数据**实时算出，看它返回的 `missingFields` 即可，**禁止**为了"提前问齐必填"去猜条件、也**禁止**逐个字段推演。
  - **`missingFields` 可信**：条件命中与否由 `createRequest` 按**实际所填数据**（含联动带出值）实时计算，`missingFields` 就是当前真实缺失的必填项——照常调用，按它的返回补齐。**禁止**对用户说"系统不会校验必填项"，也**禁止**用 `requiredInfoWarning` 非空当作"无法校验必填"的理由跳过校验。
  - 只有需要向用户交代"OA 页面上带红色星号的字段"时，才提示用户对照表单红星核对（含明细表里的列，如费用明细的「发票」）。
- **必填缺失一次问齐**：`createRequest` 返回 `NEEDS_INPUT`（`missingFields`）时，**把主表 + 明细表全部缺失字段一次性列给用户**（每项注明需要的值类型/建议默认值），**禁止逐字段推演或逐个追问**；联动/默认值/记忆已覆盖的字段不会出现在 missing 里，直接采用即可。**`action: draft` 时缺失不阻断、状态是 `CREATED`，但 `missingFields` 同样会返回——必须原样转述（提交前需补齐），不要把 `CREATED` 读成"没有缺失"**（此时命令还会附一段 `missingFieldsNotice`，可直接用它）。
- **必填的浏览 / 人员 / 发票类字段：值来自用户的话 ＋ 服务端解析（这里不存在"猜"）**：从用户本轮说过的话里**取线索**——**含指路性的模糊线索**（楼层 / 楼栋 / 区域 / 简称等只有部分信息的说法）——**第一次调用就传进 `data`**。**线索不是完整名称时，首轮就把它的多种写法一次并列传完**（同 `workflow` 名的「一次给多个说法」口径，同一字符串内用英文逗号分隔）：写法展开＝**保留用户原话作锚点**，再补**全称 / 简称、去掉或补上单位词、数字写法变体**（如 `"全称写法,简称写法,去掉单位词的写法"`）——**只做同一个对象的写法变体，不要换另一个对象去试**。服务端只会有三种结果，按结果处置：**唯一命中**（直接可用，并按「主表（已填内容）展示规则」说明它命中成了什么）／**`MULTIPLE_MATCHES`**（列出 `candidates` 让用户点选，选定后按 `{"id":"候选id","name":"候选名称"}` 回传）／**`NOT_FOUND`**（明确告知"系统里没有「XX」，请提供该对象的完整名称，或其它可用于检索的关键词"，最多重试 1 次）。**只有用户本轮完全没提到该字段时才留空**——留空是为了让 `missingFields` 把它列出来、连同其它缺失项**一次问齐**，这是**省往返手段，不是"不许传"**。真正**禁止**的只有两条：① **编造用户没说过的值**，或**凭空构造 `{id,name}` 绕过澄清**（就算被服务端接受，你也不知道它解析成了哪个对象）——**对用户原话做写法展开不算编造**（展开里始终留着用户原话作锚点）；② 把多个说法拆成**一轮一轮重发**（同一条命令里并列多个说法属"补充召回"，不额外花往返）。发票类走外部技能（`weaver-e10-yepiaotong`）。
- **特例 · 会议室字段（`browserType = mt_room`）**：房间名里**没有楼层 / 区域这类描述**，所以用户口里的楼层线索**本身不是房间名的子串**——只传带描述后缀的说法会 0 命中（`NOT_FOUND`、`candidates` 为空）。该字段首轮必须把线索的**最小可检索片段**（去掉描述性后缀后剩下的那部分）与**用户原话**一起**并列**传；命中多个候选时照常把 `candidates` 原样列给用户选。
  - 这个字段**不做值推演**：最小可检索片段按上一条口径取定即可，**一次并列传完就下发命令**，不要在下发前反复比较"哪种写法更可能命中"；**拿到候选就停**——照常把 `candidates` 原样列给用户选，不为"再试一次能否唯一命中"改写或收窄写法重发。
  - 其它浏览按钮字段出现同类问题时，在本条下按同一格式**追加同级「特例 · <字段>（<browserType>）」小条**：只写该字段特有的匹配口径，**不写示例**。
- **`resolvedValues` / `fields` 既用来自查解析结果、也是「已填内容预览」的数据源**：`NEEDS_INPUT` / `NEEDS_CONFIRMATION` 时看 `resolvedValues`，成功时看 `fields`——都是"我传的值 → 服务端最终值"的回显（选项给名称，浏览/人员/部门给 `{id,name}` 数组）。**解析结果与预期不符就不要往下走**（例如传「泛微」被解析成了另一个主体），按上面的口径向用户确认，后续用完整名称。**这些回显同时要按下文「主表（已填内容）展示规则」转成给用户看的表格，不要只留在心里自查。**
- **浏览按钮值匹配不上（BROWSER NOT FOUND）**：`createRequest` 返回 `NEEDS_CONFIRMATION`（`ambiguities` 里 `kind = "BROWSER"`）时按 `reason` 分别处理。`candidates` 里**只会出现按你写的说法真实命中的值**，不会混进与该说法无关的系统默认清单：
  - `reason = "MULTIPLE_MATCHES"` → 列出 `candidates` 让用户选，选定后按 `{"id":"候选id","name":"候选名称"}` 回传；
  - `reason = "NOT_FOUND"`（`candidatesAvailable = false`、`candidates` 为空）→ **一次明确告知用户"系统里没有「XX」，请提供该对象的完整名称，或其它可用于检索的关键词"**，用户给出后最多重试 1 次；
  - 一个值有多种叫法时，**首轮就把这些写法一次用英文逗号串起来传**（展开口径见上文「必填的浏览 / 人员 / 发票类字段」那条）——同一条命令里并列多个说法属"补充召回"，不额外花往返。**禁止的是拿一个说法试一次、失败后再换一个说法重发**（那是多轮逐词去撞），也**禁止凭空构造 `{id,name}` 绕过澄清**。
- 明细表：`details` 的 key 是 subFormId，value 是行对象数组。
- **明细表（子表单）展示规则（Excel 列展示）**：以 `previewDetails`（明细表按列组织：`columns` 表头 + `rows` 每行明细）为准——明细表**必须用 Excel 列展示**（表头 + 每行一条明细，形如 `| 序号 | 费用日期 | 费用类型 | 费用说明 | 申请金额 |`，每行一行），**禁止把明细字段按"字段\|内容"平铺**；`previewDetails` 为空时才用 `fields` 平铺兜底。多条明细时逐行展示（序号递增）。
- **主表（已填内容）展示规则（字段 / 值两列，单独成表）**：面向用户回显"这次填了什么"时，用**「字段 / 值」两列表格**展示，**只列本次实际填写的字段**——成功时取 `fields`、`NEEDS_INPUT` / `NEEDS_CONFIRMATION` 时取 `resolvedValues`；`requestName`（流程标题）已确定时在表内一并列出。**主表表格与明细表表格必须分开列**（先主表、后明细表），**禁止**把两表合成一张、也**禁止**用 bullet 列表代替表格；`missingFields` / `ambiguities` 里等用户确定的字段列为"未确定"，并照常向用户询问。
- 目录联动：附件字段 `folderDependsOnOption=true` 时，按最近一次返回的 `attachmentFolderIds` 取 `folderId`（null=不指定目录）再上传。
- 初始化值：`createForm` 返回 `initialValues`（OA 预填值，含 onLoadForm 联动带出），`data` 应包含这些初始化字段值（用户明确填写的以用户为准）；含 subFormId 的放 details 对应行，主表字段放 main。**漏带不会导致缺必填**（默认值由 CLI 自动并入主表与明细行）；`missingFields` 里出现它就是真的没值，按上面口径问用户。
- 不重试：saveFormData/flow/create 失败、超时或结果不确定（`SAVE_UNCERTAIN`/`PARTIAL_SAVED`/`CONTEXT_ALREADY_WRITTEN`/`WRITE_UNCERTAIN`）禁止重试，返回恢复信息并让用户人工检查。
- 写操作遇登录失效：禁止自动重登重放，返回 `WRITE_UNCERTAIN` 停止，先只读回查。
- `context` 与工作流强绑定：只用最终选定工作流那次 `createForm` 返回的 `continuation`；澄清后换了工作流就要重新 `createForm` 拿新句柄。
- **记忆保存（发起流程口径）**：本轮发起过程中，**只有用户有新的明确澄清**——① 工作流名称；② 字段名称；③ 浏览按钮字段值；④ 选项字段的选项值——才做记忆保存。**这四类之外一律不保存**：用户只是给出普通文本 / 日期 / 金额等字段的本次取值，或只是正常走完一次填单，都不构成记忆。满足条件时按 memory 规则在任务结束时**实际调用** `workflow.memoryExtract` 保存（见 workflow-memory.md）。
