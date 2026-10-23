# 流程表单指南

## EB 流程与原生工作流程的选择

- 流程体系分为 EB 流程和原生工作流程；公文流程是原生工作流程的特殊类型。
- 固定、自由是流程的流转模式，各类流程均可选择。
- 默认使用 EB 表单和应用内的 `workflow create`。
- 需求明确要求“原生流程表单”“工作流程”或“流程中心建流程”时，使用 `workflow create-workflow`；其表单使用 `wf-form` 命令管理。
- EB 与原生流程表单的资源 ID、接口前缀和布局操作不同，不可混用。EB 应用也不能直接选择表单引擎创建的原生表单。
- 原生流程表单的字段、明细、布局、字段属性和分组分别使用 `wf-form add-field`、`add-detail-table`、`layout init|add|delete`、`field-prop`、`group`；完整参数见 `references/common/ref-cli-commands.md`。
- 平台上各类流程都可选择固定或自由模式。当前 CLI 中，`workflow create-workflow --is-free 0|1` 已支持原生工作流程（含公文）的模式选择；`workflow create` 目前只按固定模式创建 EB 流程，尚未暴露自由模式参数。这是 CLI 能力边界，不代表 EB 流程不支持自由模式。
- 已有数据的字段可能无法删除。删除失败时保留字段定义并从布局移除；CLI 当前不提供 `wf-form delete-field`。

### 公文流程（原生工作流程的可选模式）

需求明确为“公文流程、公文审批、收文、发文”时，在 `workflow create-workflow` 上增加 `--odoc`。公文流程与普通原生工作流程共用表单、节点、出口和操作者机制；差异是创建及查询时使用 `bridgeService=odoc`，并拥有公文设置、正文等专属配置。创建方式和公文专属能力统一读取 [公文流程指南](guide-workflow-odoc.md)，不要用 `workflowType` 代替公文模式。

### 权责表方式

需求明确要求按权责表搭建时，流程表单来源仍按本指南选择，搭建方式切换为权责表。可以随流程新建权责表，也可以复用独立权责表；独立表的变量管理、分支场景、节点路径以及复用时的字段映射统一读取 [权责表指南](guide-workflow-auth-resp.md)。

### 原生工作流程及表单创建顺序

仅在需求明确要求原生流程表单、工作流程或流程中心时使用本节。`workflow create-workflow` 返回的 `workflowId` 用于节点和流程设置，`formId` 用于全部 `wf-form` 命令；不要传 EB 表单的 objId 或 appId。

#### 方式一：随工作流程自建流程表单

```bash
e10-cli workflow create-workflow "费用报销流程" --layout FLOW
# 团队流程默认自动取创建者机构；多机构场景可显式加 --sub-company <机构ID>
# 表格式流程表单改用 --layout EXCEL；自由流程加 --is-free 1
```

不传 `--form-id` 为自建模式。FLOW 直接创建流程及其表单；EXCEL 会先创建表格式流程表单再绑定，最终都会返回后续使用的 `formId`。

#### 方式二：绑定已有原生流程表单

```bash
e10-cli workflow create-workflow "费用报销流程" --form-id <已有formId>
```

绑定模式沿用已有表单自身的布局类型，`--layout` 不负责切换已有表单布局。

#### 建表与布局配置

```bash
# 1. 记录并检查创建命令返回的 formId
e10-cli wf-form read <formId>

# 2. 添加全部主表字段
e10-cli wf-form add-field <formId> "申请人" Employee
e10-cli wf-form add-field <formId> "报销金额" Number --precision 2

# 3. 添加明细表；记录返回的 subFormId，再添加其余明细字段
e10-cli wf-form add-detail-table <formId> "费用明细" "费用类型"
e10-cli wf-form add-field <formId> "费用金额" Number --sub-form-id <subFormId> --precision 2

# 4. 按需求配置选项、公式、联动、查重和值带出
e10-cli wf-form field-options <formId> <fieldId> --options '[{"name":"差旅费"}]'
e10-cli wf-form formula set <formId> --expression "..." --target <fieldId>

# 5. 字段全部创建后配置分组和显示属性
e10-cli wf-form group <formId> --groups '{"基本信息":["申请人","报销金额"]}'
e10-cli wf-form field-prop <formId> --required 申请人 报销金额 --readonly 流程编号 --single-row 备注

# 6. 回读字段与布局结果；只有需求明确要求多套布局时才 layout add
e10-cli wf-form read <formId>
```

字段应先建全，再统一做分组和字段属性，避免反复重建布局。`add-field`、`group`、`field-prop` 内部均会按各自职责保存或重建布局，通常不需要每加一个字段都手工执行 `layout init`；只有明确需要重建默认布局时才单独使用它。多套布局用 `layout add`，删除指定附加布局用 `layout delete`。

## 流程页面 URL

提交流程的页面后缀是 `/sp/workflow/flowpage/create/流程id`：

```
/sp/workflow/flowpage/create/1281910260426555393
```

---

## URL 传参预填

流程页面支持通过 URL query string 传参来预填表单字段。参数名使用**字段 ID**，参数值为要预填的内容。

```js
var WORKFLOW_ID = '1281935012370612224';
var workflowUrl = publicUrl + '/sp/workflow/flowpage/create/' + WORKFLOW_ID;

// 根据上下文拼接预填参数
if (selectedCell) {
  var params = [];
  if (selectedCell.roomId) {
    params.push(F.roomNo + '=' + encodeURIComponent(selectedCell.roomId));
  }
  if (selectedCell.date) {
    params.push(F.bookingDate + '=' + encodeURIComponent(selectedCell.date));
  }
  if (params.length > 0) {
    workflowUrl = workflowUrl + '?' + params.join('&');
  }
}
// 最终 URL 示例：
// /sp/workflow/flowpage/create/1281935012370612224?1281934337846132742=1356890123456789&1281934337846132739=2026-06-17
```

---

## 注意事项

| 规则 | 说明 |
|------|------|
| 参数名 | 用表单字段 ID（纯数字字符串） |
| 参数值 | 需要 `encodeURIComponent` |
| Select 字段 | 传参时用**选项 ID**（`valueKey`），不能传显示名称 |
| 参数名不生效 | 可能需要换成流程表单里定义的字段标识（短码），让用户确认 |

---

## CLI 流程管理

### 创建流程

```bash
e10-cli workflow create <appId> <formObjId> <name> [desc]
# 自动设置所有人可发起；默认不加菜单，要入口加 --menu（「发起菜单」LAYOUT，指向表单新建页，点开即触发流程）
# 漏加可用 `e10-cli menu add-start <appId> <formObjId>` 补
```

### 查看节点

```bash
e10-cli workflow nodes <workflowId>
# 输出节点名称、类型（发起/审批/归档）、操作者、连线关系
```

### 设置审批人

```bash
# 指定人
e10-cli workflow set-operator <workflowId> <nodeId> 张三
# 指定角色
e10-cli workflow set-operator <workflowId> <nodeId> 财务主管 --type role
# 发起人上级
e10-cli workflow set-operator <workflowId> <nodeId> --type superior
# 发起人上级"逐级审批"（直接上级按顺序逐个处理）：
e10-cli workflow set-operator <workflowId> <nodeId> --type superior --sign-order 依次处理
# 上级/本人组支持 --sign-order：会签/非会签/竞签/依次处理(逐级)/抄送/抄送需批注
# "所有上级"（整条上级链，如 结束归档：抄送发起节点所有上级需批注）：
e10-cli workflow set-operator <workflowId> <nodeId> --type initiator                          # ① 审批/处理组=发起人本人
e10-cli workflow set-operator <workflowId> <nodeId> --type superior --superior-scope 所有上级 --sign-order 抄送需批注 --append   # ② 追加抄送组
# 所有人
e10-cli workflow set-operator <workflowId> <nodeId> --type all
# 自由选择（发起时自己选）
e10-cli workflow set-operator <workflowId> <nodeId> --type free
# 上一节点操作者
e10-cli workflow set-operator <workflowId> <nodeId> --type prev-node
# 指定部门（含下级）
e10-cli workflow set-operator <workflowId> <nodeId> 开发部 --type dept
# 多部门 + 跨部门会签、单个部门内非会签（如"营销部,财务部,市场部 会签、部门内非会签"）：
e10-cli workflow set-operator <workflowId> <nodeId> "营销部,财务部,市场部" --type dept --dept-scope 本部门 --org-non-sign
# 指定岗位
e10-cli workflow set-operator <workflowId> <nodeId> 财务经理 --type position
# 岗位限定"发起人所在部门"（如 部门主管/财务经理 只在本部门内找人）：
e10-cli workflow set-operator <workflowId> <nodeId> 部门主管 --type position --pos-scope 发起人同部门 --sign-order 非会签
# 签署顺序 + 批次
e10-cli workflow set-operator <workflowId> <nodeId> 张三 --sign-order 竞签 --orders 0.10
# 组内多操作者（一个节点配多人，任一人或全部审批）
e10-cli workflow set-operator <workflowId> <nodeId> "区域经理,部门领导" --type role --sign-order 竞签
```

**修改已有操作者的签署顺序（会签→非会签/竞签/依次/抄送），不删掉重建**：

```bash
e10-cli workflow operator-sign <workflowId> <nodeId> --sign-order 非会签
e10-cli workflow operator-sign <workflowId> <nodeId> --sign-order 竞签 --group 指定角色
```

> ⚠️ `set-operator` 建的是**会签**；要改成非会签/竞签/依次/抄送，用 `operator-sign`（更新旧组，不重建，避免破坏关联）。`--group` 指定组名可只改某组。

> 🚫 **操作者配置硬规则（防"兜底成具体人员"错配）**：需求里操作者是「角色 / 部门 / 岗位 / 发起人上级 / 本人 / 表单字段 / 矩阵 / 自由选择 / 所有人」时，**必须用对应 `--type`**（role / dept / position / superior / initiator / form / matrix / free / all），并按需求的关键词（角色名/部门名/岗位名/字段名…）配置；**名称解析不到就停下报告或确认，绝不退而求其次去指定某个具体人员顶替**（那会搭错组织权限，典型症状：节点操作者成了某个无关的具体人员）。只有需求明确写"指定某人/张三"时才用默认 `user`。配完用 `workflow nodes` / 节点操作者回读核对类型与需求一致。
>
> 🚫 **抄送组不能是节点唯一操作者**：抄送(含需批注)不产生审批，一个节点必须至少有 1 个审批/处理组；"某人审批 + 抄送xxx" = 先 `set-operator` 建审批组，再 `--append` 追加抄送组（如上方"结束归档"例子）。

**签署方式（--sign-order）概念**——决定"多个审批人之间怎么算通过"：

| 签署方式 | 含义 |
|---------|------|
| **会签**（默认） | 选择的多人**必须都审批通过**才继续流转 |
| **非会签** | 选择的多人中**只要一个人审批通过**就流转下去 |
| **竞签** | 非会签的一种：多人同时可见、**先到先审**，谁先提交谁生效（其他人无需再审） |
| **依次处理** | 按人员选择顺序逐个审批，**全部审完**才流转 |
| **抄送** | 抄送对象，**不影响流转**；需批注的抄送对象批注后转入已办，不需批注的查看即转入已办 |

> **「A 或 B 审批」= 一个节点多人 + 竞签/非会签**，不是物理分两条线。比如"区域经理 或 部门领导审核"：`set-operator <wf> <node> "区域经理,部门领导" --type role --sign-order 竞签`，图上只有一根线。**需求里出现"或/任一人"的审批，优先用竞签/非会签**，只有按条件真正分流（不同分支走不同流程）才拆节点。
> 
> **一个节点多人**：keyword 用逗号分隔（`"角色1,角色2"` 或 `"张三,李四"`）。`set-operator` 每次全量重建该节点操作者组（先清空旧组再新建），重复设置不会堆积。
# 矩阵对应（查矩阵表动态获取审批人）
e10-cli workflow set-operator <workflowId> <nodeId> --type matrix \
  --matrix-id <矩阵ID> --value-config-id <值字段configId> \
  --matrix-rule "<条件configId>:1:1" \
  --batch-condition "(申请人 等于 '张三')"
# matrix-rule 格式: 条件configId:数据来源type:匹配operate（三段）
#   type: 0=指定部门 1=发起人部门 5=当前操作人部门
#   operate: 1=本部门 2=本及下级 3=本及上级 49=逐级向上 67=本及下级逐级向上
# 旧写法末尾还有第 4 段 virtualId（1=行政组织），**平台已不再使用**——照写不会报错但会被忽略，新配置按三段写
# 表单相关人员（从表单数据中动态获取审批人）
e10-cli workflow set-operator <workflowId> <nodeId> --type form \
  --source <表单ID> --target <人员字段ID>
```

### 节点签字意见必填（退回时意见必填）

```bash
e10-cli workflow node sign <workflowId> <nodeId>              # 查看当前意见必填配置
e10-cli workflow node sign <wf> <node> --all-required         # 全部操作类型意见必填
e10-cli workflow node sign <wf> <node> --none-required        # 全部不必填
e10-cli workflow node sign <wf> <node> --select "退回,加签"    # 指定操作类型意见必填
```

> 「退回时意见必填」= `--select 退回`（如：上级审核节点退回时要求填写意见）。操作类型以该节点可选范围为准（不同节点类型可操作类型不同）。

### 节点提交校验（智能审批规则，字段 vs 字段）

```bash
e10-cli workflow node validate <workflowId> <nodeId> --view                          # 查看校验状态
e10-cli workflow node validate <wf> <node> --name "一致性校验" \
  --rule "行程明细.行程开始时间 等于 出差开始日期"     # 设置校验：行程开始时间=出差开始日期
e10-cli workflow node validate <wf> <node> --disable                                # 关闭校验
```

> **规则语法**：`--rule "主题字段 操作 值字段"`。主题字段用「**明细表名.字段名**」可定位明细字段，操作支持 等于/不等于/大于/大于等于/小于/小于等于，值字段为比较引用的另一字段（字段 vs 字段，非字面值）。重复执行是**更新**同一条规则；对已配置节点会复用原 conformanceId。校验不通过默认**阻止提交**（FORBID_SUBMIT）。

**表单相关人员**（`--type form`）从指定表单的 Employee 字段动态获取审批人，支持筛选条件：

```bash
# 无筛选：取表单中所有员工
e10-cli workflow set-operator <wf> <nodeId> --type form \
  --source 1294600110549819401 --target 1294600110549819393

# 带筛选：人员级别 > 100
e10-cli workflow set-operator <wf> <nodeId> --type form \
  --source 1294600110549819401 --target 1294600110549819393 \
  --condition '{"fieldId":"1294600110549819396","fieldType":"Number","fieldName":"人员级别","func":"gt","value":"100"}'

# 筛选值引用表单字段：申请人 == 创建者（valueFieldId 在流程表单中查找）
e10-cli workflow set-operator <wf> <nodeId> --type form \
  --source 1294602202274390029 --target 1294602202274390020 \
  --workflow-form 1294601678154162216 \
  --condition '{"fieldId":"1294602202274390020","fieldType":"Employee","fieldName":"申请人","func":"eq","valueFieldId":"2"}'

# 或签
e10-cli workflow set-operator <wf> <nodeId> --type form \
  --source 1294600110549819401 --target 1294600110549819393 \
  --sign-order 或签
```

> `--condition` 格式：`{"fieldId":"字段ID","fieldType":"字段类型","fieldName":"字段名","func":"比较符","value":"固定值"}`。func 支持：`gt`(大于)、`lt`(小于)、`eq`(等于)、`gte`(≥)、`lte`(≤)、`like`(包含)。用 `valueFieldId` 代替 `value` 表示值引用了表单字段，需同时指定 `--workflow-form <流程表单objId>` 告诉 CLI 在哪个表单里找引用字段。`--sign-order` 默认 `会签`。

### 添加节点

```bash
e10-cli workflow add-node <workflowId> <type> "节点名称"
# type: 0=发起 1=审批 2=确认/会签 3=归档 5=投递 7=自动处理 8=等待
#        forkstart=分流点  forkend=合流点  forkmiddle=分流中间点
# 结束节点 = 归档节点（type=3）；流程末尾的归档节点就是「结束」，二者是同一个节点类型
# --node-attr: 0=一般(默认) 1=分流点 2=分流中间点 3=合流点
```

> **分流节点不能做审批**：`forkstart` / `forkmiddle` / `forkend`（nodeAttr 1/2/3）是**纯路由节点**，配不了审批操作者——节点一旦被标成分流/合流点，`set-operator` 就设不上审批人。分流职责和审批职责必须分开：分流节点只负责分叉/合流，审批人放在各分支的**审批节点（type=1）**上，即 `forkstart → 各分支审批节点(type=1) → forkend`。

### 等待节点（流程机器人，type=8）

等待节点在平台叫「流程机器人」（nodeType=8），配置走 `workflow node-robot`：

```bash
e10-cli workflow node-robot get <wf> <nodeId>                        # 查看当前配置
e10-cli workflow node-robot set <wf> <nodeId> --wait-value 30        # 设置等待时长
e10-cli workflow node-robot set <wf> <nodeId> --processing-interval 5  # 处理间隔
e10-cli workflow node-robot set <wf> <nodeId> --remark "等待审批结果"  # 备注（多语言用 set-remark）
```

> ⚠️ **等待时长 `--wait-value` 的单位是「分钟」，不是小时/天**。`--wait-value 30` = 30 分钟；`--processing-interval` 处理间隔同为分钟。填错单位会导致流程等待时长差 24/60 倍。`--wait-type 1` = 指定时长；`waitTimeValue=0` 是默认值（未配置指定时长）。

### 重命名节点

```bash
e10-cli workflow rename-node <workflowId> <nodeId> "新名称"
```

### 添加连线（节点→节点）

一键添加连线：
```bash
e10-cli workflow add-link <workflowId> <fromNodeId> <toNodeId> "标签"
e10-cli workflow add-link <workflowId> <fromNodeId> <toNodeId> "退回" --reject
e10-cli workflow add-link <workflowId> <fromNodeId> <toNodeId> "主线路" --default
```

批量添加连线（出口表混着退回线和默认出口时用这个）：
```bash
e10-cli workflow add-links <workflowId> @links.json
# links.json:
# [
#   {"from":"拟稿","to":"套红",       "label":"拟稿 至 套红",       "default":true},
#   {"from":"部门经理审稿","to":"拟稿", "label":"部门经理审稿 退回 拟稿","reject":true}
# ]
```

> **退回 / 默认出口逐条给**：`reject` / `default` 写在每条连线上；命令行上的 `--reject` / `--default`
> 是给整批兜底的默认值，逐条给的值优先于它。
>
> **默认出口会自动让位**：指定某条为默认出口时，同一源节点上原有的默认出口会被自动取消，
> 保证一个源节点只有一条默认出口。同一批里给同一源节点指定了两条默认出口会直接报错，
> 不会静默留下两条。
>
> **多条连线用 `add-links`**：`add-link` 内部 read→改→save，并行的会互相覆盖。`add-links` 一次把整批
> 拼好、一次保存，不会丢数据。不要用 `&` 或 `parallel` 并跑 add-link。
>
> 保存后 CLI 会**回读比对**：新连线的退回/默认标志与让位结果都对得上才算成功，
> 对不上会直接报错退出，不会因为服务端回了「保存成功」就放过。

### 删除连线

```bash
# 先用 workflow nodes --json 获取连线的 linkId
e10-cli workflow nodes <workflowId> --json
# 返回的 links 数组每条都有 linkId，可直接删除
e10-cli workflow delete-link <workflowId> <linkId>
# 支持一次删多条
e10-cli workflow delete-link <workflowId> <linkId1> <linkId2>
```

> **注意**：`workflow nodes --json` 返回的每条连线都带 `linkId`，用它来删除，不要用 nodeId。

### 查看出口列表

```bash
e10-cli workflow link-list <workflowId>
# 显示源节点→目标节点、默认出口[默认]、退回出口[退回]、条件状态[有条件]
# --node-id 过滤单个源节点的出口
e10-cli workflow link-list <workflowId> --node-id <nodeId>
```

### 修改/删除出口（列表方式）

```bash
# 先获取当前出口列表作为基线
e10-cli workflow link-list <workflowId> --json > links.json
# 修改后保存
e10-cli workflow link-save <workflowId> @links.json
# 删除指定出口
e10-cli workflow link-save <workflowId> @links.json --delete-rows "linkId1,linkId2"
```

### 查看节点列表（含分流/合流属性）

```bash
e10-cli workflow nodes <workflowId> --mode list
# 显示 nodeAttr（0=一般/1=分流点/2=分流中间点/3=合流点）+ mergeType（全部分支/指定分支/分支数/比例）
```

### 全流程搜索（不依赖 appId）

```bash
e10-cli workflow search --name "费用报销"
e10-cli workflow search --id <workflowId>
e10-cli workflow search --name "审批" --belong 1 --page-size 50
```

### 节点操作菜单

```bash
# 查看菜单
e10-cli workflow node menu <workflowId> <nodeId>
# 切换菜单启用状态
e10-cli workflow node menu <workflowId> <nodeId> --toggle <menuId>
```

### 节点退回设置

```bash
# 查看
e10-cli workflow node reject <workflowId> <nodeId>
# 修改
e10-cli workflow node reject <workflowId> <nodeId> \
  --remind 1 --type 1 --checked-node 1 --submit-type 1
```

### 节点超时处理

```bash
# 查看
e10-cli workflow node timeout <workflowId> <nodeId>
# 新增超时规则（指定时间 48h，下一操作者，超时前 2h 提醒）
e10-cli workflow node timeout <workflowId> <nodeId> \
  --time-type 1 --time-value 48 --flow-type 1 --remind-type 0 --remind-hours 2
```

### 工作流维度设置

```bash
# 提交确认
e10-cli workflow setting submit <workflowId> --confirm 1
# 签字意见
e10-cli workflow setting sign <workflowId> --show-order 1
# 评论
e10-cli workflow setting comment <workflowId> --enable 1
# 批量操作
e10-cli workflow setting batch <workflowId> --enable-batch 1 --enable-reject 1
# 自动处理
e10-cli workflow setting auto <workflowId> --enable 1 --way 0
# 其他设置
e10-cli workflow setting other <workflowId> --message-op 1 --auto-save 1
# 流程标题规则（保存/提交后生成标题）
e10-cli workflow setting title <workflowId>                                   # 查看可用变量
e10-cli workflow setting title <wf> --rule "工作流名称|发起人|提交日期" --sep "-"  # 标题=流程名-发起人-提交日期
e10-cli workflow setting title <wf> --disable                                 # 关闭自动生成标题
```

> **流程标题**：`--rule` 用竖线分隔字段名（可用 `工作流名称`/`发起人`/`提交日期`/`流程编号` 等系统字段或任意表单字段名），`--sep` 指定分隔符（默认 `-`）。CLI 自动把字段名解析成占位编码（如 `工作流名称=-100`）并启用 `subtitleType` 开关。

### 高级设置

```bash
# 流程存档
e10-cli workflow advanced doc <workflowId> --enable 1 --doc-types "0,1"
# 定时触发（每日 09:00）
e10-cli workflow advanced schedule <workflowId> \
  --enable 1 --frequency '{"item1":1,"item2":1}' --time "09:00:00" --weekday-only 1
# 定时触发人员范围
e10-cli workflow advanced schedule-range <workflowId> --list
```

### 整体重写流程图（save-layout）

大规模调整节点连线时，构造完整 XML → 一次性保存覆盖当前布局：

```bash
# 1. 将 XML 文件保存为流程布局（覆盖当前）
e10-cli workflow save-layout <workflowId> @layout.xml

# 2. 构造完整 XML（浏览器 mxGraph 格式）
```

XML 格式示例（浏览器 mxGraph 格式：节点 cell id 用纯数字，带真实 `nodeId`；连线带真实 `linkId`，`source`/`target` 引用节点的数字 id）：
```xml
<mxGraphModel grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1331" pageHeight="888" background="#ffffff"><root>
<mxCell id="0"/><mxCell id="1" parent="0"/>
<!-- 节点：vertex="1"，带 nodeId -->
<mxCell id="2" value="发起节点" style="rounded=1;whiteSpace=wrap;html=1;resizable=1;rotatable=0;arcSize=10;fillColor=#5D9CEC;strokeColor=#5D9CEC;" vertex="1" nodeType="0" nodeId="节点ID" operatorNameStr="    " parent="1"><mxGeometry x="465" y="80" width="170" height="64" as="geometry"/></mxCell>
<mxCell id="3" value="审批节点" style="..." vertex="1" nodeType="1" nodeId="节点ID" parent="1"><mxGeometry x="465" y="220" width="170" height="64" as="geometry"/></mxCell>
<!-- 连线：edge="1"，带 linkId、source、target -->
<mxCell id="6" value="发起 至 审批" style="edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#5D9CEC;" edge="1" linkId="连线ID" isDefault="0" isReject="0" orderId="0.0" source="2" target="3" parent="1"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel>
```

**关键规则**：
- 节点的 `id` 用数字（2, 3, 4...），连线的 `source`/`target` 引用节点的 `id`
- 连线的 `linkId` 是服务端分配的唯一标识，删除连线用这个
- 保存：`e10-cli workflow save-layout <workflowId> @修改后的.xml`
- **务必保持浏览器格式**：服务器 saveLayout 只认纯数字 cell id。`getXml` 输出的 `node_xxx`/`link_xxx` 格式直接回传会解析失败（节点被判为 null/已删除）

### 节点自动排版（auto-layout）

CLI 搭建的流程（add-node 加节点）节点通常挤在一列，用自动排版重排：

```bash
# 默认左右分层（发起在最左）
e10-cli workflow auto-layout <workflowId>

# 上下排布（发起在最顶，平台连线默认纵向）
e10-cli workflow auto-layout <workflowId> --direction ttb

# 只算不打回（看分层结果）
e10-cli workflow auto-layout <workflowId> --dry-run
```

**算法**：读 getXml → 按连线最长路径分层（忽略退回线）→ 全量重排节点 mxGeometry → saveLayout 回写 → 回读验证。分支（forkstart→分支们→forkend）自然融入分层，同层节点垂直排开。只改节点坐标，连线自动正交路由。

**什么时候跑**：`create` / `create-workflow` 建流程时自动跑一次，**之后不再自动跑**。所以**加/删节点、加/删连线之后要补跑一次**（`add-node` 只把新节点丢在图的边上，不会融进流程线）。`rename-node` / `set-operator` / 条件与动作配置不改拓扑，不用跑。

两个边界要知道：

- **会覆盖手工摆放**。它是整图重排，人在浏览器里拖过的坐标一律按算法结果重置。手工调过就别再跑，或跑完重新调。
- **不保证消除交叉**。分层算法只对「跨 ≥2 层的长跳线」把**目标**节点下移一档；跨层连线的水平段仍可能穿过中间层节点。**跑完看一眼流程图**，有交叉只能手工调坐标（或试 `--direction ttb` 换个走线方向）。

---

## 相关指南

- **分支条件 / 出口条件 / 条件 JSON** → `workflow/guide-workflow-condition.md`
- **动作流（跨表单写入）/ 提交事件 / 角色管理** → `workflow/guide-workflow-action.md`
