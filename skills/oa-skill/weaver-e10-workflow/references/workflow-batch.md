# 批量流程处理（6 个单命令）

## 什么时候读取

用户要一次性处理多条流程：批量提交、批量置已读 / 已办、批量催办、批量共享、批量转发、批量退回时读取本文件。

## Operation

| Operation | 风险 | 固定规则 |
| --- | --- | --- |
| `workflow.batchSubmit` | high-risk-write | **单命令**：一次调用完成门禁校验 + 置已办 + 提交；必须 `confirm: true` |
| `workflow.batchRead` | high-risk-write | **单命令**：一次调用完成门禁校验 + 置已读 / 已办（doBatchRead）；必须 `confirm: true` |
| `workflow.batchSupervise` | high-risk-write | **单命令**：一次调用完成提醒人解析 + 催办；必须 `confirm: true` |
| `workflow.batchShare` | high-risk-write | **单命令**：一次调用完成门禁校验 + 共享对象解析 + 共享（分批）；必须 `confirm: true` |
| `workflow.batchForward` | high-risk-write | **单命令**：一次调用完成门禁校验 + 接收人解析 + 「转发所有人」配置检查 + 转发（分批）；必须 `confirm: true` |
| `workflow.batchReject` | high-risk-write | **单命令**：一次调用完成门禁校验 + 退回（分批，不传提交参数）；必须 `confirm: true` |

**6 个批量操作全部是单命令**：没有 `Prepare` / `Apply` 两阶段，也没有 `continuation` 句柄；`confirm: true` 与 `requestIds`（及其余参数）都在**同一次调用**里传。

## 确认链：按**目标的来源**分两条路径（6 个批量操作一致）

**先判断目标从哪来，再决定要不要多一轮确认**——两条路径的确认成本不同：

**① 目标是具体几条（`requestIds` 已知）** → **不需要再问一次**：用户已经指明要处理什么，直接把 `requestIds` + `confirm: true` 一次调用完成。
- 只有当用户主动问起条数、来源、差异或风险时，才补一句说明。
- 不要先发一段"摘要/计划"等用户点头（那会白多一轮往返），也不要把 `requestIds` 先"准备"到某个句柄里——门禁校验、名称解析与写入都在这一次调用内完成。

**② 目标是一个范围（没有准确的 `requestId`）** → **必须先数条数、再执行，两轮**：
1. 用 `scopeCondition` + **`action: "total"`** 只查条数（不发写入），把「范围 + 条数」报给用户；
2. 用户确认后，用**同一条 `scopeCondition`** 配 **`action: "execute"`**（+ `confirm: true`）执行。

> **范围驱动**没有"直接执行"这条捷径：`action` 在给了 `scopeCondition` 时是**必填**参数，漏写直接报 `batch_action_required`——"先数条数给用户确认"这一步不允许靠漏写绕过。只有用户**在同一句话里已经给出了明确条数**（如"把刚才那 2 条提交掉"——那其实属于路径 ①，用 `requestIds`）才不需要再数。

**`action:"total"` 返回三个数，都要看**：`total`（**当前能实际处理**的条数）、`scopeTotal`（该范围下的流程总数）、`executable`（能否真取到行）。
- `total = 0 且 scopeTotal > 0` ⇒ **范围内有数据，但没有一条适用本次操作**（常见：都是抄送/传阅/转发类，例如 `batchSubmit` 对它们等同置为已办，应改用 `workflow.batchRead`）。**必须如实向用户说明"有多少条、为什么不适用"，不要报成"没有数据/0 条"**。

**执行后的处理（两条路径共用）**：

- 范围驱动的返回是**聚合结果**：`status`（`COMPLETE` / `PARTIAL`）、`succeededCount`、`failedCount`、**`failures:[{requestId, reason}]`（带逐条原因的失败清单）**、`stoppedReason`（取空时还有 `scopeTotal`；整页抛错时另有 `lastError`）。**照这个汇报**：完成多少条、失败多少条、**每条失败的原因**（`failures[].reason`）——不要只报个数，也不要编造逐条明细。
- **不要向用户提"批次数、分了几批、循环了几次、页数"这类实现细节**——那是 CLI 内部怎么分批取数的事，对用户没有意义（返回里也已经不含这些字段）。用户只关心"处理了多少条、有没有失败"。
- **`stoppedReason` 必须按语义转述，不要一律说成"没有数据"**：
  - `scope_exhausted` ⇒ 该范围**确实没有**可处理的数据了；
  - `scope_not_batch_eligible` ⇒ 范围里**有数据**（`scopeTotal` 条）但本次操作一条都取不到 —— 说明条数与原因，并给替代方案；
  - `max_batches_reached` / `max_items_reached` ⇒ 触达单次调用上限（20 批 / 2000 条），**没跑完**，可用同一 `scopeCondition` + `exRequestIds` 续跑；
  - `batch_failed_stop` ⇒ 某批整体失败已停止。
- 只有 `COMPLETE` 才代表"该范围已处理完"；其余都要说明未跑完的原因。
- 返回 `partial`/`write_uncertain` 时**立即停止**，先只读回查（`workflow.search --category done --requestId <目标ID>`，或看 `--category mine` 是否已出现目标流程），**不自动重放已发出写入的那一批**。核对确认**没生效**后，等约 1 分钟再原样重跑——同一批在保护窗口内还会被拦一次（防止机械式重复执行），窗口过去即可正常执行。
- 返回 `ok:true` + `data.status = "ALREADY_APPLIED"` 时，说明**同一批流程、同一批写向对象刚刚已经执行成功**（例如宿主把同一条命令重跑了一次）——本次没有重复写入。直接按返回值里的 `previousResult` 汇报即可，**不要重复执行同一条命令**。
- 报 `validation/batch_gate_required` 时，说明 `details.missingRequestIds` 里的流程**不在最近一次查询结果里**（门禁只认查询落下的那份结果，不认别的口径）。这只可能发生在**点名 `requestIds`** 的路径上（范围驱动的 ID 就是 CLI 刚查出来的，不存在这种情况）。正确做法：先做 `workflow.search --batchType <类型> --pageSize 100` 查询一页，再立即用该页返回的 ID 调用批量命令；若这些流程其实已被处理过，先只读核对 `workflow.search --category done --requestId <目标ID>`，已处理就按成功汇报。
- 同一操作连续 2 次失败必须停止。

## 输入

**三条路径互斥**：`requestIds`（点名处理）｜`scopeCondition` + `action:"total"`（先数条数）｜`scopeCondition` + `action:"execute"`（按范围执行）。`requestIds` 与 `scopeCondition` 同时给会报 `batch_scope_conflict`——要给范围就**不要**自己先查 ID。

- `requestIds`：待操作流程 ID，类型可为数组（元素为数字或仅数字字符串）或逗号分隔串；**必须来自查询索引结果，模型不能自己编**；拿到后直接用——CLI 按本机索引核对，**不需要为了"校验"再查一次服务端**。
- `action`（string，**给了 `scopeCondition` 时必填**）：`"total"` 只查条数（不发写入，用于先向用户确认）｜`"execute"` 查询并执行。**漏写直接报 `batch_action_required`**——不给默认值，"先数条数"不允许靠漏写绕过。
- `scopeCondition`（object，可选）：**范围条件，与 `workflow.search` 入参同形**（`category` / `workflow` / `creator` / 时间条件 / `filterFields` 等；写法查 [`workflow-query.md`](workflow-query.md)）。CLI 会自动补上本操作的 `batchType`，不需要自己传。给了它就**不要**再自己查 requestIds——循环由 CLI 内部完成。
  - **未显式给 `subCategory`/`tabName`/`tabid` 时，CLI 自动按「全部」子分类取数**（`todo` → `tabid 0`）。原因：低版本模式下 `workflow.search` 对未指定子分类的 todo 默认查「待处理(7)」，而**批量过滤列表端点**在 tabid=7 下只返待处理 ⇒ 范围里全是抄送/传阅/转发类时**恒 0 条**（2026-09-20 真实事故）。范围驱动默认取「全部」，再由 `batchType` 过滤可操作性；**scope 显式给了子分类就用指定的**（只处理待处理就写 `subCategory:"待处理"`）。
- `exRequestIds`（可选）：本次要**排除**的 requestId（数组或逗号分隔串）。用于**续跑**：上一次执行里失败或未处理的 ID 传进来即可跳过（CLI 会把它合并进查询的排除集）。
- `remark`：批量统一意见（submit / supervise / forward / reject 适用；**置已读没有意见参数**）。
- `batchSize`：单批最大条数，`integer` 1–100，默认 100；CLI 自动分批循环（范围驱动时它同时是**内部每页的取数条数**）。
- `confirm`：固定为 `true`。
- `category` / `async`：仅 `workflow.batchSubmit` 使用（分类判断、异步提交开关）。
- 各操作专属字段见下方分节。
- **6 个批量操作都没有 `continuation` 字段**：它们是单命令，不存在需要模型搬运的句柄。

## 请求来源与执行方式

**先判断操作目标的来源，再选路径：**

**① 目标就是「上一轮查询结果」里的具体条目**（用户直接用指代——"前两条 / 刚才那些 / 上一次列表里的流程 / 都处理掉"，或点名该轮里的条目）→ **直接从最近一次查询结果中取对应流程作为操作目标并执行批量命令**。
**指代基准只有一份：最近一次查询结果**（与批量门禁的放行快照同源）；"前两条"＝该列表第 1、2 条（按列表顺序数）。**不要跨轮回溯更早的列表，也不要反问"是哪一份列表"**。**不需要先检查是否可批量操作**（CLI 内部按各流程状态分流：可提交的提交、抄送不需提交／转发不需批注／传阅不需批示类置已办），**也不需要先做一次 `workflow.search --batchType` 来"校验"这些 ID**（门禁按本机索引放行，这一次查询对放行没有帮助）。

**② 目标是一个范围**（"把这些待办都处理了"且未限定上一轮结果，因此没有准确的 requestId）→ **用 `scopeCondition` 交给 CLI**，不要再自己写循环：

```bash
# 第一步：只数条数（不发写入），把条数报给用户确认
weaver-work-cli --json workflow run workflow.batchSubmit --input-json '{"confirm":true,"scopeCondition":{"category":"todo","receiveTime":"2026-09-20 2026-09-20"},"action":"total"}'
# 第二步：用户确认后执行（同一条 scopeCondition）
weaver-work-cli --json workflow run workflow.batchSubmit --input-json '{"confirm":true,"scopeCondition":{"category":"todo","receiveTime":"2026-09-20 2026-09-20"},"action":"execute","remark":"批量同意"}'
```

CLI 内部的循环口径（了解即可，**不要自己复刻**）：

1. 用 `scopeCondition` + 自动补上的 `batchType` 查一页（`batchSize` 即每页条数）；
2. **立即**执行该页，**不先翻完所有页、也不先把全部 requestId 收集起来一次提交**；
3. 把这一页**已处理**与**失败**的 ID 并入排除集，带着排除集（`exRequestId`）**再查下一页**；
4. 重复 2–3，直到取不到数据（`stoppedReason: scope_exhausted`）或触达上限（单次调用最多 20 批 / 2000 条）。

**为什么必须由 CLI 循环、且排除集不能省**：批量门禁的放行依据是**最近一次查询结果**——每次查询都会覆盖上一份结果；若先把所有页的 ID 收集起来再一次性提交，前面几页的 ID 已经被后来的查询挤掉，门禁会判成"不在最近一次查询结果里"（真实事故：3 条一起提交全部 `batch_gate_required`）。而排除集是**两类操作都成立**的翻页依据：提交/置已读会把已处理流程从待办里清掉（不排除也不会重复），催办/共享/转发/退回**不会**消失（不排除就会反复处理同一批）。

**失败时的口径**：分两种——① **内层单批"部分失败"但接口不报错**（转发/退回返回 `status:"PARTIAL"` + `failures`、催办返回 `success:false`、提交返回 CLI **本地**跳过清单 `skippedRequestIds`（`isRemark>=100` 不可批量提交的条目，**不是接口字段**））：CLI 会解析信封，**把失败项从成功数里剔除**、连原因一起收进 `failures`，并把它们并入排除集后继续下一页（不会重复写已失败的条）。② **整页失败且定位不到逐条失败项**（认证/网络/门禁/写结果不确定）：**立即停止**并返回 `PARTIAL` —— 这类失败继续跑只会把同一个错误重复 N 次；此时 `lastError` 给出批次级原因，`failures` 里每条也会带上该原因。

> **不要把"部分失败"当成成功**：`succeededCount` 已扣除失败项。汇报失败时必须带上 `failures[].reason`（接口给的逐条原因，或批次级原因摊派），否则用户只知道"有几条没成"却不知道"为什么"。

**续跑**：带上**同一条 `scopeCondition`** 再执行一次即可——本次已处理的会被自动跳过（排除集同源）。**要重试本次失败的那几条**：先用 `workflow.search --category done --requestId <id>` **只读核对它们是否其实已经生效**（部分失败可能是"已写入但回执异常"），确认没生效再用 `requestIds` 单独重试——**不要**直接把 `failures[].requestId` 当 `exRequestIds` 传回去（那等于永久跳过它们）。

**requestId 提取**：走 `requestIds` 路径时优先用查询返回的**结构化字段** `cards[].requestId` 取本页全部 requestId；只有在需要从 `finalMarkdown` 文本里提取时才用正则 `` \]\(https?://[^\)]*requestId=(\d+)\) ``（**只匹配卡片链接**，避开描述文字里嵌套的 requestId）。批量查询默认跳过卡片业务摘要（只返回系统字段卡片，提速显著）。

- `requestIds` 必须取自上一轮查询结果，或跟随查询分页逐页取本页 ID；**禁止模型臆造 ID**。

## 置已读与提交的区别

- `batchRead`：仅把待办置为已读 / 已办（抄送不需提交、转发不需批注、传阅不需批示类，置已读同时置为已办，即"已阅"）。
- `batchSubmit`：先置已办（BATCH_READ）再提交（BATCH_SUBMIT），同样会处理上述"不需提交"类为已办。
- `batchReject`：**只退回，不传任何提交参数**，退回意见作为签字意见放入请求。

## 各批量操作

### 批量提交 batchSubmit

适用："批量提交 / 全部提交 / 一起提交"多条待办。入参 = `confirm: true` + `requestIds`（+ `remark` / `batchSize` / `async`）。

返回 `readCount`、`submittedCount`、`skippedRequestIds`（**CLI 本地判定**：`isRemark=100` 不可批量提交、被跳过的条目；接口本身不返回该属性）、`batchRead`、`submitResponse`；原样转述返回的结果与提示文案。

### 批量置已读 batchRead

适用："把流程置为已读 / 已阅"。入参 = `confirm: true` + `requestIds`（+ `batchSize`）。

返回 `readCount`、`response`；原样转述返回的结果与提示文案。

### 批量催办 batchSupervise

适用："批量催办 / 全部催办 / 催一催多条流程"。提醒对象按用户说法设置，未指定时默认催当前节点未操作者。

| 字段 | 取值 | 默认 | 含义 |
| --- | --- | --- | --- |
| `currentOperator` | `0`/`1` | `1` | 催办当前节点未操作者 |
| `messageRemind` | `0`/`1` | `0` | 短信提醒 |
| `emailRemind` | `0`/`1` | `0` | 邮件提醒 |
| `doneOperator` | `0`/`1` | `0` | 已审批人 |
| `ccOperator` | `0`/`1` | `0` | 抄送人 |
| `submitOperator` | `0`/`1` | `0` | 发起人 |
| `otherReminder` | 姓名 / `"姓名(ID)"` 逗号分隔 | 空 | 其他提醒人 |

返回 `successNum`、`failNum`、`batches`。

### 批量共享 batchShare

适用："把多条流程共享给 X / 共享给部门 / 共享给所有人"。共享对象 `shareObjects` 每项 `{"type": <类型>, "name": <名称>}`（`all` 不需要 name）：

| type | 共享对象 |
| --- | --- |
| `user` | 人员 |
| `dept` | 部门 |
| `subcompany` | 分部 |
| `group` | 群组 |
| `role` | 角色 |
| `position` | 岗位 |
| `all` | 所有人（无 name） |

名称自动转 ID；`name` 支持 `"名称(ID)"`（此时直接采用括号里的 ID、不再搜名称）。多命中返回候选列表让用户确认（**只问用户完整名称或其它可用于检索的关键词，ID 由你按 `candidates` 拼好，不要向用户索取 ID**），禁止静默全选；0 命中报错提示核对。可选 `minSeclevel` / `maxSeclevel`（用户明确要求限制时传）。返回按每批 `addRequestShare2` 的**逐条结果**计价：`sharedCount` 只数 `data[]` 里 `result === "true"` 的条目，`result === "false"` 的进 `failures`（原因取 `msg`）。

### 批量转发 batchForward

适用："批量转发 / 把多条流程转给 X 看 / 发给 X"。接收人 `receiveTargets` 每项 `{"type": <类型>, "name": <名称>}`（`all` 不需要 name）：

| type | 接收人 |
| --- | --- |
| `user` | 人员 |
| `dept` | 部门 |
| `group` | 群组 |
| `all` | 所有人（无 name） |

`name` 支持 `"名称(ID)"`（此时直接采用括号里的 ID、不再搜名称）；多命中同上——**只问用户完整姓名或其它可用于检索的关键词，ID 由你按候选拼好，不要向用户索取 ID**。接收人含 `all` 时会检查系统是否允许转发给所有人；不允许则停止并提示联系系统管理员，不得去掉 all 后静默继续。返回逐条 `status` / `requestId` / `requestName` / `resultType` / `resultMessage`，批内失败立即停止。

### 批量退回 batchReject

适用："批量退回 / 把多条流程退回去"。退回意见同时作为签字意见放入请求。返回逐条 `status` / `requestId` / `requestName` / `resultMessage`，批内失败立即停止。

## 示例

### 批量提交

Windows PowerShell：

```powershell
weaver-work-cli --json workflow run workflow.batchSubmit --input-json '{"confirm":true,"requestIds":["id1","id2","id3"],"remark":"批量同意","batchSize":100}'
```

macOS/Linux（bash/zsh）：

```bash
weaver-work-cli --json workflow run workflow.batchSubmit --input-json '{"confirm":true,"requestIds":["id1","id2","id3"],"remark":"批量同意","batchSize":100}'
```

目标是一个范围时，**用 `scopeCondition` 交给 CLI 循环**（先数后做）：

```bash
# ① 只查条数，报给用户确认
weaver-work-cli --json workflow run workflow.batchSubmit --input-json '{"confirm":true,"scopeCondition":{"category":"todo","batchType":"submit"},"action":"total"}'
# ② 用户确认后执行（同一条 scopeCondition；CLI 内部查一页→执行→排除→再查）
weaver-work-cli --json workflow run workflow.batchSubmit --input-json '{"confirm":true,"scopeCondition":{"category":"todo"},"action":"execute"}'
# ③ 若上一轮有失败/未处理的，带上它们的 ID 续跑
weaver-work-cli --json workflow run workflow.batchSubmit --input-json '{"confirm":true,"scopeCondition":{"category":"todo"},"action":"execute"}'
# 重试个别失败项（先只读核对确认未生效）
weaver-work-cli --json workflow run workflow.batchSubmit --input-json '{"confirm":true,"requestIds":["<确认未生效的那条>"]}'
```

### 批量置已读

Windows PowerShell：

```powershell
weaver-work-cli --json workflow run workflow.batchRead --input-json '{"confirm":true,"requestIds":["id1","id2"],"batchSize":100}'
```

macOS/Linux（bash/zsh）：

```bash
weaver-work-cli --json workflow run workflow.batchRead --input-json '{"confirm":true,"requestIds":["id1","id2"],"batchSize":100}'
```

### 批量催办（未指定提醒对象 → 默认当前节点未操作者）

Windows PowerShell：

```powershell
weaver-work-cli --json workflow run workflow.batchSupervise --input-json '{"confirm":true,"requestIds":["id1","id2"],"remark":"请尽快处理","currentOperator":1}'
```

macOS/Linux（bash/zsh）：

```bash
weaver-work-cli --json workflow run workflow.batchSupervise --input-json '{"confirm":true,"requestIds":["id1","id2"],"remark":"请尽快处理","currentOperator":1}'
```

### 批量共享

Windows PowerShell：

```powershell
Set-Content -Encoding utf8 -LiteralPath .\batch-share.json -Value @'
{
  "confirm": true,
  "requestIds": ["id1","id2"],
  "shareObjects": ["{\"type\":\"user\",\"name\":\"张三\"}","{\"type\":\"dept\",\"name\":\"产品研发中心\"}","{\"type\":\"all\"}"],
  "batchSize": 100
}
'@
weaver-work-cli --json workflow run workflow.batchShare --input .\batch-share.json
```

macOS/Linux（bash/zsh）：

```bash
cat > ./batch-share.json <<'JSON'
{
  "confirm": true,
  "requestIds": ["id1","id2"],
  "shareObjects": ["{\"type\":\"user\",\"name\":\"张三\"}","{\"type\":\"dept\",\"name\":\"产品研发中心\"}","{\"type\":\"all\"}"],
  "batchSize": 100
}
JSON
weaver-work-cli --json workflow run workflow.batchShare --input ./batch-share.json
```

### 批量转发

Windows PowerShell：

```powershell
Set-Content -Encoding utf8 -LiteralPath .\batch-forward.json -Value @'
{
  "confirm": true,
  "requestIds": ["id1","id2"],
  "receiveTargets": ["{\"type\":\"user\",\"name\":\"张三\"}","{\"type\":\"all\"}"],
  "remark": "请知悉",
  "batchSize": 100
}
'@
weaver-work-cli --json workflow run workflow.batchForward --input .\batch-forward.json
```

macOS/Linux（bash/zsh）：

```bash
cat > ./batch-forward.json <<'JSON'
{
  "confirm": true,
  "requestIds": ["id1","id2"],
  "receiveTargets": ["{\"type\":\"user\",\"name\":\"张三\"}","{\"type\":\"all\"}"],
  "remark": "请知悉",
  "batchSize": 100
}
JSON
weaver-work-cli --json workflow run workflow.batchForward --input ./batch-forward.json
```

### 批量退回

Windows PowerShell：

```powershell
weaver-work-cli --json workflow run workflow.batchReject --input-json '{"confirm":true,"requestIds":["id1","id2"],"remark":"材料不齐全，请补充后重新提交"}'
```

macOS/Linux（bash/zsh）：

```bash
weaver-work-cli --json workflow run workflow.batchReject --input-json '{"confirm":true,"requestIds":["id1","id2"],"remark":"材料不齐全，请补充后重新提交"}'
```

## 返回

- 6 个命令都**直接返回批量结果**：提交（`readCount` / `submittedCount` / `batchRead` / `submitResponse` / 可选 `skippedRequestIds`——CLI 本地的跳过清单）、置已读（`readCount`）、催办（`successNum` / `failNum` / `batches`）、共享（`sharedCount` / 有失败时 `failedCount` + `failures`）、转发（`forwardedCount`）、退回（`rejectedCount`）；**有逐条失败时 `status` 为 `"PARTIAL"`**，并给出 `failures`。**没有任何命令返回 `continuation`。**

> **★ 计数只认服务端逐条结果（2026-09-20 起）**：不再"按发出去的条数"算成功。真机实证过一次 **0 成功被报成 1 成功**——`batchSubmit` 的响应是
> `{"data":{"successRequest":[], "failRequest":{"<id>":"当前工作流未开启允许批量提交"}}}`，
> 当时 CLI 却回 `status:"COMPLETE"` + `submittedCount:1`。现在的口径：
> 1. 成功条数只认逐条结果：`successRequest`（**成功清单**）/ 逐条 `submitResult`·`operateResult` 里 `status===true` 的 ⇒ `submittedCount`；`failRequest` / `failMsg`（**{流程ID: 失败原因} 映射**，两种键名都真机见过）与 `status===false` 的逐条行 ⇒ **`failures:[{requestId, reason, name}]`**（原因原样带出，不再只给 ID）；
> 2. 转发/退回的逐条结果在 `data.data.submitResult` / `operateResult`（`status !== true` 即失败，同样带上 `resultMessage`）；
> 3. **拿不到逐条结果时不得默认"全成功"**：`batchSubmit` 返回 `unverified: true` + `unverifiedRequestIds` + `warnings` 且 `status:"PARTIAL"`；`batchRead` 用 `resultUnverified`；转发/退回返回 `unverified: true`。这类条目要**只读核对**（`workflow.search --category done --requestId <id>`）后再决定重试，**不要按已成功上报**。
> 4. `failures[].name` 是**流程标题**：优先取逐条结果的 `requestName` / `data.requestNameTitle`；那里没有就回退到**最近一次查询结果的快照**（`flowName`，其原始字段是 `requestnameTitle`/`requestnametitle`，真机确认两个键名都存在且同值）。都取不到就只给 ID，**不编造标题**。
> 5. **共享（`batchShare`）的返回结构与其他批量接口不一样**：逐条结果是**根级数组** `data: [{sourceId, result, msg}]`——`data` 不是对象、ID 键名是 **`sourceId`**（不是 `requestId`）、成功标记是**字符串** `"true"`/`"false"`（不是布尔 `status`）、原因在 **`msg`**。CLI 已按它逐条计价：`sharedCount` = `result === "true"` 的条数；`result === "false"` 的进 `failures`（标题回退快照 `flowName`，共享响应本身不带标题），`failedCount` 同步给出。
> 5. 汇报时**失败必须连原因一起说**（`failures[].reason`），并带上标题/编号让用户能对上号，不要只报个数。
- **范围驱动（给了 `scopeCondition`）返回的是聚合结果，不是单批结果**：
  - `action:"total"` → `status:"SCOPE_TOTAL"` + `total`（**当前能实际处理**的条数）+ `scopeTotal`（该范围下的流程总数）+ `executable`（能否真取到行）（**没有写入**）。`total=0 且 scopeTotal>0` 表示"有数据但没有一条适用本次操作"，**不能报成"没有数据"**。
  - `action:"execute"` → `status`（`COMPLETE`/`PARTIAL`）、`succeededCount`、`failedCount`、`failures:[{requestId, reason}]`、`stoppedReason`（`scope_exhausted` / `scope_not_batch_eligible` / `max_batches_reached` / `max_items_reached` / `batch_failed_stop`），取空时另有 `scopeTotal`。**不含 `batches`/`batchSummaries`/`pageSize`**（内部实现细节，2026-09-20 起不再返回）。汇报口径见「确认链」。
- 被重复执行、且上一次已经成功时，返回 `ok:true` + `data.status = "ALREADY_APPLIED"`（幂等回报，含 `previousResult`）——**这不是错误**，本次没有重复写入，按上一次结果汇报即可。
- 任一批失败：CLI 立即停止并在 **stderr** 返回 `ok:false` + `error.message`（含已成功条数），Agent 如实转述，不自行补造；**没有** `success`/`userMessage` 字段。
- **结果展示**：动作与条数用一句话说明；**逐条结果可用 Markdown 表格展示**（序号 / 流程名称 / 动作 / 接收人 / 状态 / 说明）；不展示 `requestId`，除非用户明确要技术定位信息。幂等回报（`ALREADY_APPLIED`）同样**只报业务结果**，不要向用户提及"此前已执行过/没有重复写入"。

## 注意

- `requestIds` 必须来自查询索引，模型不得编造；批量门禁的放行依据是**最近一次查询结果**（与单条操作同一套本地索引口径），不是另做一次实时列表查询；**6 个批量命令都走这道门禁**（催办按 `urge` 口径核对，与 `workflow.search --batchType urge` 共用同一套批量端点）。
- 6 个命令都**没有 Prepare 环节，也没有 continuation**。CLI 用「这次要写什么」作为一次性写入闸门：**同一个操作 + 同一批 requestId + 同一组写向对象**（收件人 / 共享对象 / 提醒人）在约 1 分钟的保护窗口内只写一次。因此宿主重跑同一批只会拿到 `ALREADY_APPLIED`，不会真的写两次；窗口过去后同一批流程可以再次处理（流程被退回后再处理是合法操作）。`remark` / `batchSize` 不参与这个判据：同一批同一对象换个意见再执行一次，仍然算重复执行。
- **换写向对象是另一次操作**：把同一批流程先转给张三、再转给李四，或先共享给甲部门、再共享给乙部门，都必须分别执行（不会被当成重复执行拦下）。
- 写操作报 `batch_gate_required` 时，看 `details.missingRequestIds`：这些 ID 不在最近一次查询结果里。先只读核对 `workflow.search --category done --requestId <目标ID>` 判断是否已被处理；确认没处理就按 `--batchType` 重新查询一页再取该页 ID 执行。**不要**为了"凑上"换 `--tabid`／子分类反复重查，也不要反复重跑同一个命令。
- 分批任一批失败立即停止，如实报告已成功条数与失败原因，不自动重试、不连环重放。
- 写操作遇登录失效 / 超时 / 断连返回 `partial/write_uncertain`，**禁止自动重放**，先只读回查确认状态。
- 同一操作连续 2 次失败必须停止。
- 不写任何凭据（Cookie / ETEAMSID / Token / 操作员标识由 CLI 托管）。
