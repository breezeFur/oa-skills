---
name: generating-actionflows
description: "将业务需求编译为 Weaver ESB 动作流，或读取已有动作流后按原 ID 保留式修改：查询真实对象、正式保存、回读校验并返回设计器链接。运行能力来自 e10-cli 的 actionflow 命令组（复用 e10-cli 登录态）。新建默认保存并启用；仅当用户明确要求暂存时传 mode:stash。已有动作流修改走 update。"
---

# Weaver 动作流生成

将需求编译为「触发器 → 动作链 → 结束」的 ESB 动作流。先发现真实平台数据，再生成；不根据名称、历史场景或示例猜测任何平台对象。

运行能力来自 `e10-cli actionflow` 命令组（已合并进 e10-cli 本体，复用其登录态，无需单独导出环境变量）。默认**保存并启用**（saveDesign saveAndStart=true）；仅当用户明确要求暂存时传 `mode:"stash"` 走暂存（saveStashSnapshot）。

## 运行与维护边界

- **运行模式（默认）**：只运行 `e10-cli actionflow <命令>`、读取本 Skill 的当前阶段/当前组件说明；不得读取或修改 e10-cli 源码（`packages/cli/src/services/actionflow/`）。
- **维护模式**：仅在用户明确要求修复、审计或新增组件时编辑实现；修改后必须跑类型检查、测试、构建和本 Skill 校验。校验目标固定为 `skill/actionflows`：不要把上层 `skill` 或发布目录 `skill-docs` 当作这个动作流 Skill 的标准目录校验。上层入口包含 E10 包的自定义元数据（如 `author`、`category`、`version`、`display_name`），不因通用校验器不认识这些扩展字段而改写、删除或迁移它们。
- 参数、默认值、动态必填、真实对象结构的唯一权威是 `e10-cli actionflow component-describe <type>`，参考文件不重复属性表。
- 动态赋值必须按“组件 × 属性”判断，不能因为属性类型写着 `Browser` 或 `platform_reference` 就一律当成固定值。先读取 [`references/dynamic_capability_matrix.md`](references/dynamic_capability_matrix.md)，再以当前租户 `component-describe`、上下文元数据和组件编译器实际契约为准；矩阵没有明确标记为已支持的属性不得臆造动态 DTO。

## 生成 SOP

按顺序推进；只读取当前步骤需要的信息。每个场景是独立事务。

### 1. 识别与选择

1. 拆出触发器、动作顺序、条件/循环、固定资源与动态来源。
2. 运行 `e10-cli actionflow component-list`，选择已登记组件。
3. 对每一个选中的组件运行 `e10-cli actionflow component-describe <type>`，再只读取下方目录中该组件的 Markdown。
4. 若存在多个业务选择会改变结果，或用户明确指定的资源找不到，暂停说明差异并询问；其余可查询的信息直接查询。

### 2. 发现真实数据

按 `component-describe` 的 `propertySources` 查询本次租户数据：

- 流程：`e10-cli actionflow workflow-browser-list` / `workflow-search` / `workflow-nodes`。
- 流程动态字段：`e10-cli actionflow workflow-context-fields`。默认每页 20 条；按需求字段名先传 `query`（例如 `{"workflowId":"<id>","query":"数据ID"}`），只使用本次返回的 `fields[].paramKey`。完整响应过大时用 `--out context.json` 落盘，禁止依赖终端截断后的片段。
- e-builder（**已知表名时首选**）：`e10-cli actionflow form-search '{"keyword":"<表名>"}'` 一次拿到表单 `objId` 与它所属的业务应用 `appId`。服务端是**子串模糊匹配**，同名表跨多个应用很常见（返回体里的 `完全同名` 即同名条数）—— **多于一条时必须按 `appName` 收窄再取**，不得自行挑一个：`'{"keyword":"<表名>","appName":"<应用名>"}'`。`keyword` 传 `objId` 则是精确命中，可用来由 id 反查所属应用。
  - **`appName` 走服务端过滤**（不是本地二次筛）：应用名精确唯一才用；**同名多命中或查无此名会直接报错并列出候选**，此时改用 `appId` 指定，不要换个近似名重试。
  - **返回体 `total` 是服务端在该筛选下的命中总数，`hits` 可能只是其中一部分。** 默认最多返回 100 条，超出时 `truncated: true` 并给出 `omitted`（未返回条数）。**`truncated` 为真时绝不能判定「表单不存在」** —— 先按 `appName` 收窄，确需全部再传 `{"max":0}`（条数大时用 `--out <file>` 落盘）。判断是否唯一命中以 `唯一命中` 字段为准，不要自己数 `hits` 长度。
- e-builder（**只知道应用、要浏览全表**）：`e10-cli actionflow form-applications` → `form-list` → `form-fields`。`form-applications` 返回的业务应用 `id` 用于下一步：`e10-cli actionflow form-list '{"groupId":"<业务应用ID>"}'`；这里必须是 `groupId`，不能传 `appId`。表单字段查询才使用 `{"tableId":"<表单ID>","appId":"<业务应用ID>"}`。
- 人员：`e10-cli actionflow recipient-search`。
- 人员入职/更新字段：`e10-cli actionflow hrm-onboarding-fields`。
- 文档状态：`e10-cli actionflow document-statuses`。

查不到真实对象、字段或前端 DTO 时，不猜测 ID 或对象结构，说明未支持字段并停止该字段的生成。

### 3. 组装语义计划

1. 写入 `event`、`actions`，条件和循环作为动作拓扑的一部分。
2. 只传 `component-describe` 声明的参数；固定值与动态值根据业务需求选择，不能为了动态而动态。
3. 语义 plan 的节点配置统一放在 `params`：`event.params`、`actions[*].params` 以及条件/循环内部节点的 `params`。`data` 仅属于平台回读/更新 DTO，不能出现在 `generate` 语义计划中；CLI 会在调用任何平台接口前拒绝该结构，并提示具体路径。
4. 中文 plan 写入当前工作区 `.actionflow-plans/`，以 `planFile` 传给 CLI；不在 Skill 目录写临时文件。CLI 不会自动删除 plan；确认 `valid=true`、`saved=true`、`readBackVerified=true` 后才允许手工清理。
5. 不把 `Output` 写入 `actions`。需要配置终止状态、提示或页面动作时使用顶层 `finalOutput.params`；提醒内容使用前端富文本组件对应的 `reminderContent`（`ContestSettingDTO`，动态片段放在 `formulaBeans`），不要使用旧的 `reminderMsgFormula`；平台内部 FormulaBean 由 CLI 生成，只有组件契约明确要求前端原对象时才传原生 DTO。
5.1. 所有 CLI 生成或继续编译的 FormulaBean，只要包含 `frontId`，允许使用空串；非空时必须使用平台真实字段 ID 的纯数字字符串。`field_<数字>` 仅可在生成时规范化为 `<数字>`。禁止把字段名、paramKey 尾段、临时公式 ID 或其他包含字母/符号的值写入 `frontId`；非空值无法解析为纯数字时必须直接报错。
6. 定时组件优先使用平台原生频率：`rate=1` 一次、`2` 按小时、`3` 按日、`4` 按周、`5` 按月，并按需提供 `cycle`、`hour`、`day`、`week`、`atWeek`、`atWeekDetail` 或 `lastWeek`；只有明确选择 `rate=6` 时才传 `cornString`。图形化频率必须提供 `startTime`。
7. 触发器或查询组件未被需求明确限制输出字段时，不传 `queryFields`（或传空数组）：CLI 会默认全选，包含“数据ID”。如果需求明确引用某个业务字段，必须从当前租户的实时字段接口/字段选择器获取完整字段对象并保存真实 `id`，不能凭字段名、临时 ID 或只拼 `id/content`。查询节点还必须使用自身真实节点 ID 作为 `dataSource.enquiryId`，否则平台可能静默丢弃业务字段。正式回读必须确认每个声明的 `queryFields` 仍存在；缺失即生成失败，不能仅凭接口 `code=200`、`saved=true` 判定成功。e-builder 数据触发后发送消息且未显式给链接时，CLI 自动补 PC/移动端当前记录详情链接；不手写 `{formId}` / `{dataId}` 的 FormulaBean。查询结果字段动态赋值必须按手工设计器对象编译：普通业务字段使用 `FormField.<查询表单ID>.field_<真实字段ID>`，`config.paramKey` 使用 `<查询表单ID>.field_<真实字段ID>`，`config.fieldInfo.tablePrimaryKey` 为 `FormField`；系统字段按平台真实字段键（例如 `id`）保留。禁止使用 `FormData.<表单ID>[临时位置]...`，也禁止把临时公式 ID 当作 `frontId`。
8. `ActionEbAdd` 批量新增以 `basisValue` 为明细行上下文：来源于该行的字段都用 `mapping`，编译为“依据值下级”（`switchType:"sub"`），下拉字段也同样处理。只有已核实来源/目标选项 ID 不同且语义需要转换时，才使用 `SWITCH`。关联 e-builder 字段应引用查询结果的 `数据ID`，固定格式为 `{target,kind:"query_result",source:"<EnquiryForm ref>",formId,fieldId:"id",index:0}`；`kind:"enquiry"`、`sourceId` 等旧写法会直接报错，绝不降级为空固定值。
9. 动态赋值可使用或新建动作流变量、租户常量：已有资源必须用真实 ID；计划新建变量写顶层 `variables[]`，新建常量写 `constantDefinitions[]`，常量分组可传 `groupPk` 或 `groupName`。变量按当前 `applicationId + sceneId` 隔离，常量按分组跨动作流复用。生成时先调用真实接口创建/解析资源，再编译为变量 `type:"7"` 或常量 `type:"5"` FormulaBean；详细格式见 `references/dynamic_resources.md`。消息 `SendMessage.msgTitlev/msgContentv/picLink/msgPcLink/msgMobileLink` 的 `parts` 支持 `variable`/`constant` 动态片段，并统一保存为 `ContestSettingDTO`。
9.1. 每个参数先分为“动态公式属性”“动态人员属性”“固定平台资源属性”三类：上下文、系统变量、变量、常量、函数/公式必须保留为 FormulaBean；动态人员必须使用真实人员字段上下文或系统变量，不得把引用里的 `id` 当人员 Browser ID 查询；工作流、文档目录、按钮、规则等平台资源只有在其组件契约明确提供动态引用时才允许动态化。生成前必须记录本次组件/属性的判定，生成后按属性检查回读结果；具体映射和验证状态见 `references/dynamic_capability_matrix.md`。
10. 自定义事件和内置 MQ 的参数必须按对应平台组件说明提供原生参数对象；`CustomTrigger.customData`、`InnerMQListener.receiveParams`、`InnerMQSend.sendParams` 不能用猜测的字段替代。若验证要求“输入参数里有字段”，必须在生成前提供至少一行真实原生参数；`tables:[]`、`tableList:[]` 或省略 `receiveParams` 只能表示无输入参数，不能作为有参数的占位。`InnerMQListener` 与 `InnerMQSend` 是动作流级互斥组件，同一计划（包括条件/循环嵌套）同时出现时，CLI 在任何平台写接口前直接报错。
11. 根触发节点的 `event.attr.icon` 必须使用平台真实图标：`CustomTrigger` 为 `Icon-N-Triggerrul`，`InnerMQListener` 为 `Icon-built-in-mq-listening-mcolor`；组件目录里的动作图标不能覆盖根触发器图标。保存后回读必须同时检查触发器图标、已声明输入参数的数量和查询字段，不能仅凭 `valid=true` / `saved=true` 判定配置正确。
12. `InnerMQSend.sendParams.tableData` 必须遵循“参数类型决定数据类型候选”的平台规则：普通非数组标量通常只有“属性”一个选项，不应伪造可下拉状态；数组或 `json/xml/xml_string` 结构化参数才按真实候选设置 `dataType`，结构化参数的下级用 `parentId` 表达，并保留父子约束。具体规则见 `references/components/message/InnerMQSend.md`。

### 4. 生成与逐场景反馈

1. 一次只运行一个 `generate`。
2. 成功保存并启用后立即返回名称、状态与 `workflowUrl`，再处理下一个场景。
3. 批量任务完成后再给汇总表；一个场景失败不阻断其他场景。

### 4.1 修改已有动作流

已有动作流必须走独立的 `update` 命令，不得把已有 `appId` 塞进 `generate`，也不得按名称猜测目标。只有在没有精确 ID 时，先用 `application-list` 查询动作流应用（不是 `form-applications` 的业务应用列表），按名称和所属业务应用核对；结果必须唯一，查不到或有歧义就请求精确 `appId`，不能自行挑一个：

```bash
e10-cli actionflow update '@update-plan.json' --out update-result.json
```

修改计划必须使用以下结构：

```json
{
  "appId": "已有动作流的精确 ID",
  "operations": [
    {"op":"edit-node", "nodeId":"原节点 ID", "patch":{"data":{"...":"..."}}},
    {"op":"delete-node", "nodeId":"要删除的原节点 ID"},
    {"op":"add-node", "parentPath":"/actions", "index":1, "node":{"type":"平台节点类型","data":{}}},
    {"op":"add-condition-branch", "conditionNodeId":"已有分支节点 ID", "branchName":"新增分支", "conditionDetail":{"conditionDataJson":"平台条件树 JSON"}, "branchActions":[]},
    {"op":"replace", "path":"/actions/0/data/...", "value":"新值"},
    {"op":"remove", "path":"/actions/0/data/..."}
  ]
}
```

操作必须显式声明；`edit-node` 深合并 `patch`，原节点 `id/wId` 不允许修改；`delete-node` 会从设计树移除节点并填充 `deleteActions`；`add-node` 使用 `read-design --out` 得到的平台原生节点结构，可用 `index` 插入指定位置，自动补雪花 ID 并填充 `addIds`。`add-condition-branch` 专门新增 `otherConditionBranch`，必须提供已有 Condition 节点 ID 和包含 `conditionDataJson` 的完整条件详情；CLI 会先调用条件服务保存规则，使用返回的真实 `conditionId/mapId/conditionKey`，再保存动作流，不能手工伪造条件 ID。分支内动作可通过 `branchActions` 提供，缺少节点 ID 时 CLI 自动补 ID 并从当前租户组件目录补齐节点壳。新增执行节点必须插在终止节点之前，且同步修改终止节点的 `sources`。回读对象中的平台展示字段会先转换为 `saveDesign` 接受的写入 DTO（例如 EventButton 的 `eventButtonId` 和按钮对象），不能把回读 JSON 原样作为接口体。更新计划中的节点 ID 必须来自本次正式 `read-design`，不能复用更早版本的 ID。保存新版时平台可能为动作/出口重新分配内部 ID；回读校验优先按 ID，ID 变化时按动作树路径和类型匹配，不能因版本复制产生新 ID 就误判失败。`sources[].id` 由平台保存时动态分配/回读时可能省略，必须通过稳定的 `sources[].wId` 校验。未操作的节点和属性从正式回读原样作为保存基线，不会被新建编译器重建；新建动作流的 `assistLayer` 只写平台空骨架 `{"nodes":[],"layout":{}}`，更新已有动作流保留原生 X6 画布节点，不得伪造扁平 `{id,type,layout}` 节点，也不能把旧版本悬空节点带入新版。更新前自动备份完整正式设计到 `.actionflow-plans/backups/`；也可以传 `backupFile` 指定路径。

更新默认根据目标动作流当前状态决定 `saveAndStart`，保持启用/未启用状态；只有计划显式传 `saveAndStart` 才改变它。触发器 `event` 必须原样保留，禁止通过 `replace/remove` 修改 `/event` 或其子路径；如果要改变触发类型、触发表单、触发时机或触发器参数，必须新建动作流。正式更新固定带 `saveNewVersion:true`，保存为原动作流的新版本。保存后无论目标原本启用还是禁用，CLI 都必须调用设计器真实的 `setActiveVersion/{appId}/{newSceneId}`，再读版本列表确认 `activeVersion` 是新版本；`saveAndStart` 只控制动作流启用状态，不控制活动版本。保存响应未返回新版 ID 时，CLI 必须重新查询版本列表定位版本号更大的新场景，再对新版正式回读；定位不到新版时不能拿旧版冒充校验通过。一次 update 最多执行一次正式保存：如果已保存但激活失败、活动版本回读不一致或正式回读失败，结果必须保留 `saved/sceneId/backupFile` 证据并停止，不能自动重跑、再次新建版本、回滚或删除；需要重试时由用户确认并基于新结果重新规划。保存后必须正式回读并检查编辑、新增、删除及未修改节点是否仍在。

### 5. 回读与异常分流

- 预检/编译失败：修正计划或报告缺失真实对象；不会创建动作流。
- 保存并启用成功但正式回读不一致：不得宣称验证通过；根据回读定位计划或组件问题，修复后重试，旧测试流由 CLI 回收。
- 保存并启用成功且正式回读通过：返回链接。
- 保存失败：返回平台错误原因；不自动退回暂存。
- 平台接口或前端编辑器不可用：明确区分「JSON/readBack 已验证」和「UI 待确认」。

## 流程节点触发绑定

`generate` 的 event 节点（`ApproveTrigger`）自带流程节点触发绑定：单条规则用 `workflowPath`（流程 id）+ `triggerTiming`；同一流程有多个触发时机时用 `triggerRules` 数组，编译为一个 `singleApproveConfigs[workflowId]` 规则数组。节点型时机使用 `approveNode`，出口型 `link` 必须使用真实 `approveLink`；编译器逐条校验可选节点类型与执行时间，不走 pathdef/addaction。多规则需要不同后续动作时，先按触发器上下文 `triggerType` / `executeTime` / `triggerNodeOrLinkId` 放 `Condition` 分支。完整联动表见 `references/components/workflow/ApproveTrigger.md`。

`generate` 默认**保存并启用**（saveDesign saveAndStart=true，正式版本生效），正式回读用 `getDesignBySceneId`。仅 `mode:"stash"` 时走暂存（saveStashSnapshot，非正式生效，需设计器手动发布）。

## CLI

```bash
e10-cli actionflow component-list
e10-cli actionflow component-describe <type>
e10-cli actionflow generate '{"planFile":"@<绝对路径>","appName":"AI-名称"}' --out generate-result.json  # 默认保存并启用
e10-cli actionflow generate '{"planFile":"@...","mode":"stash"}'                   # 显式暂存（不启用）
e10-cli actionflow application-list '{"name":"动作流名称"}'              # 先发现动作流应用，再用唯一结果的精确 appId
e10-cli actionflow activate-version '{"appId":"动作流ID","sceneId":"版本场景ID"}' # 只切换默认打开版本，不改变启用状态
e10-cli actionflow enable '{"appId":"动作流ID"}'                         # 单独启用，不修改设计、不创建版本
e10-cli actionflow disable '{"appId":"动作流ID"}'                        # 单独禁用，不修改设计、不创建版本
e10-cli actionflow update '@update-plan.json' --out update-result.json       # 读取后按原 ID 保留式修改；一次保存，失败停止
```

常用发现命令：`form-search`、`form-applications`、`form-list`、`form-fields`、`workflow-browser-list`、`workflow-search`、`workflow-nodes`、`workflow-context-fields`、`recipient-search`、`document-statuses`、`hrm-onboarding-fields`、`variable-list`、`variable-create`、`constant-list`、`constant-group-list`、`constant-group-create`、`constant-create`、`http-connectors`、`http-resources`、`http-interfaces`、`http-interface-detail`、`application-list`、`design-versions`、`read-stash`。变量/常量计划定义和引用见 `references/dynamic_resources.md`。

## 触发器边界

当前可生成的事件触发器：`ApproveTrigger`（流程事件）、`EventFormData`（e-builder 数据新增/更新/删除/字段变化）、`EventButton`（点击 e-builder 指定按钮）、`DateTrigger`、`TimeBatchTrigger`、`SimpleScheduler`、`CustomTrigger`（自定义事件）、`InnerMQListener`（内置 MQ 监听）和 `WebHookTrigger`（外部 WebHook 请求）。`EventButton` 必须先用 `e10-cli actionflow form-buttons '{"tableId":"<表单ID>","appId":"<应用ID>"}'` 查询真实按钮，再以 `targetForm`、`buttonType:[{id,name,buttonLocation:"before"|"after"}]` 和可选 `triggerType` 生成；不得用 `EventFormData` 冒充按钮点击。`CustomTrigger`、`InnerMQListener` 和 `WebHookTrigger` 的原生参数要求见 `references/components/trigger/CustomTrigger.md`、`references/components/trigger/InnerMQListener.md`、`references/components/trigger/WebHookTrigger.md`。

`CustomTrigger` 的上下文动态赋值使用 `SelectParams` 作为最终上下文根。`paramKey` 只写业务路径，不写 `FormData.`、`ApprovalData.` 或 `SelectParams.` 前缀；主表字段格式为 `主表key.字段key`，明细字段格式为 `主表key.明细表key[].字段key`，主表与明细表必须沿用同一个主表 key。最终公式中的 `value`、`currentParamKey` 和 `allParamKey` 才补 `SelectParams.` 前缀，不能把明细字段写成 `FormData.明细表key[].字段key`。如果动态赋值来源于该触发器生成的 `customData`（`CustSetFormDto`），必须先在 `customData.tableList[]` 定位 `CustFormTableDto`，表维度取表对象 `id`，字段维度再从该表 `fields[]` 定位 `CustFormDetailDto` 并取字段对象 `id`，把这个 ID 设置到关联 FormulaBean.frontId；不得使用目标字段 ID、FormulaBean.id、表/字段名称或 paramKey 尾段。对应 ID 缺失时 frontId 使用空串，非空值必须为纯数字字符串。完整规则见 `references/components/trigger/CustomTrigger.md`。

动作 `Http` 用于调用当前租户已配置的 HTTP/HTTPS 接口，参数要求见 `references/components/http/Http.md`；HTTPS 使用同一个 `Http` 组件，不能把协议地址当成新的组件类型。生成前会实时读取并校验“连接器 → 资源 → 接口 → 接口详情”，节点标题按“当前连接器: 当前接口”回填，图标按当前连接器目录回填；不存在、跨租户或归属不一致时拒绝生成，不信任旧环境的 E9 等名称、地址、图标或原生映射。HTTP 请求字段通过 `inputParams` 配置，必须用接口详情真实返回的 `table`/`paramKey`，CLI 写入参数行的 `formulaData`，支持统一的固定值、上下文、系统变量及函数/公式赋值；不能猜参数或直接改写 `request.tables`。动作 `serverless/Action` 用于执行二开代码，参数要求见 `references/components/serverless/ServerlessAction.md`；输入和输出必须传前端参数设计器生成的原生 ParamBean 结构。动作 `InnerMQSend` 用于向平台内置 MQ 发送消息，参数要求见 `references/components/message/InnerMQSend.md`。`InnerMQListener` 和 `InnerMQSend` 不能放在同一个动作流中；该约束也适用于 `update` 修改后的完整设计。

动作 `DMLExecute` 用于执行自定义 SQL 或存储过程，参数要求见 `references/components/database/DMLExecute.md`。只支持新版数仓结构，`operateType` 固定为 `0`；数据源连接 ID 必须通过 `actionflow datasource-list` 从当前环境取得，SQL 占位符与 `fieldSet` 必须严格对应。含 DML 的生成结果还要检查 `sqlAnalysisOk=true`，因为平台 SQL 分析失败可能不会阻断保存。

含复杂 JSON 时优先用 `generate` 的 `planFile` 参数，且必须写为 `@plan.json` 或 `@绝对路径`，避免 shell 转义改变内容。只以终端摘要的 `valid/saved/readBackVerified/workflowUrl` 判断成功；完整结果用 `--out` 保存，禁止依据截断输出重试。

`update` 同样只以终端摘要的 `valid/saved/readBack.ok/workflowUrl` 判断成功；完整设计和回读结果使用 `--out` 保存。修改计划只接受 `@文件名` 形式，不兼容裸文件名。已有动作流更新时 `event` 触发器是不可变边界：更新计划不得替换或修改 `/event`，若需求要改变触发类型、触发表单、触发时机或触发器参数，CLI 必须在 `check/saveDesign` 前拒绝，并提示新建动作流。通过更新校验后，正式保存固定发送 `saveNewVersion:true`，在原动作流下创建平台新版本；保存后按新版场景 ID 回读，不能因平台重分配动作节点 ID 或终止节点 ID 而误报失败；`saveAndStart` 只继承/控制启用状态，不改变这一版本策略。

成功生成后，CLI 会在应用描述中写入稳定的 `e10-cli:actionflow:v1:<plan指纹>` 标识，并仅清理**同一标识、`AI-` 前缀且不是当前应用**的旧生成尝试；名称可以不同。每条都执行“禁用 → 回收删除 → getAppById 确认不存在”。没有该标识的历史动作流不自动删除，避免误删人工流；清理结果/失败原因返回在 `duplicateCleanup`，当前失败应用的回收失败返回 `cleanupWarning`，不把接口失败归因于 Skill。

## 组件目录

选中类型后只读取 `references/components/<分类>/<type>.md` 对应文件；不读取同分类的其他组件文件。

| 设计器分类 | 组件文件目录 |
|---|---|
| e-builder 数据与表单触发 | `references/components/ebuilder/` |
| 流程 | `references/components/workflow/` |
| 文档 | `references/components/document/` |
| 人员 | `references/components/personnel/` |
| 逻辑 | `references/components/logic/` |
| HTTP/HTTPS 接口 | `references/components/http/` |
| serverless/Action 二开代码 | `references/components/serverless/` |
| 消息提醒 | `references/components/message/` |
| 内置 MQ / 自定义事件 | `references/components/trigger/`、`references/components/message/` |
| 会议、日程 | `references/components/calendar/` |
| 简单定时器 | `references/components/trigger/` |

额外按需规则：

- 使用流程/表单触发器的系统字段、数据 ID 或动态引用时，读取 `references/trigger_runtime_notes.md`。
- 使用 `Condition` 或 e-builder 筛选条件时，读取 `references/condition_rules.md`。
- 组件需要计算、转换或函数树时，读取 `references/function_rules.md`；仅在该组件的说明允许函数树时使用。

筛选条件左值的字段身份必须按实时 `componentKey` 生成，不能只按字段 ID 是否为数字判断。普通 e-builder 业务字段才使用 `field_<id>`；`Workflow` 关联流程字段使用原始数字 `fieldName`、`fieldType:"String"`、空 `module`/`originBrowserType`、`formInfo.formId/layoutId`、顶层 `sformId` 和仅含 `fieldId` 的 `config`。Workflow 的 `sformId` 必须由 `workflowPath.formIds` 反查真实流程表单对象；查不到就停止，不能用目标表单版本 ID兜底。保存后正式回读必须检查左值没有出现“已删除”。

## 不变约束

- 动作流名称默认 `AI-` 前缀。
- 所有流程、表单、字段、人员、目录、规则和身份均取自当前租户。
- 不支持的组件或缺少真实前端对象的属性明确拒绝，不走保底伪造。
- 凭据只复用 e10-cli 登录态，不写入 Skill、计划或输出。
