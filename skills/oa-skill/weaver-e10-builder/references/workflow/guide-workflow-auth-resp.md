# 权责表与权责表方式流程

权责表把多个条件场景及其审批路径维护为“节点列 × 分支行”。它属于工作流公用流转资源，与 HRM 矩阵、普通公共片段和流程图布局分别管理。

## 一、选择方式

- **默认选择随流程新建权责表**：创建权责表方式流程时使用 `--new-table`，条件直接引用当前流程表单字段。这条路径配置更直接，不需要额外维护变量映射，适用于一般权责表流程。
- 只有权责规则需要被多个流程复用时，才先创建独立权责表，再使用 `--reuse-table` 引用并映射变量。
- 需要多重嵌套权责表时，独立创建可复用的中间片段型权责表，首尾位置使用审批、确认等中间节点类型，再由宿主权责表按分支引用。
- 普通顺序、分支流程继续使用流程图方式；只有需求明确要求权责表时才使用本指南。

## 二、独立权责表搭建顺序

1. `workflow auth-resp create` 创建权责表并记录 `authRespId`。
2. 条件可以直接使用系统字段；需要表达业务表单字段时，先用 `workflow auth-resp variable add` 创建变量。变量必须在某个分支条件里被引用，复用到流程后再映射为实际表单字段（见 §五）。
3. 建立发起、结束设置和多个中间审批节点。中间节点统一作为列创建，操作者规则沿用工作流节点操作者规则。
4. 为每个有效分支填写分支场景说明并创建条件。
5. 每个分支从已有中间节点中选择自己的路径，通过顺序号表达串行或并行。
6. `workflow auth-resp save-design --config @design.json` 保存并回读。

从零完整搭建优先使用：

```bash
e10-cli workflow auth-resp configure <authRespId> --config @auth-resp.json
```

`auth-resp.json` 使用业务结构描述变量、节点、操作者、分支条件及路径：

```json
{
  "baseId": "创建权责表返回的baseId",
  "name": "合同分级审批权责表",
  "workflowId": "-99999999",
  "usage": "workflow",
  "variables": [
    { "id": "-自定义稳定ID", "name": "合同金额", "type": "wf_number" }
  ],
  "start": { "name": "开始节点", "operator": { "type": "all" } },
  "end": { "name": "结束节点", "operator": { "type": "initiator" } },
  "nodes": [
    { "key": "manager", "name": "部门负责人审批", "type": "approve", "operator": { "type": "user", "keyword": "张三" } },
    { "key": "finance", "name": "财务审批", "type": "approve", "operator": { "type": "user", "keyword": "李四" } }
  ],
  "branches": [
    {
      "scenario": "合同金额不超过5万元",
      "condition": {
        "relation": "AND",
        "rules": [
          { "source": "form", "field": "合同金额", "operator": "小于等于", "value": 50000 }
        ]
      },
      "path": [
        { "node": "manager", "order": 1 },
        { "node": "finance", "order": 2 }
      ]
    }
  ]
}
```

流程内新建权责表时，`workflowId` 写真实流程 ID，`source=form` 直接解析当前流程表单字段；独立权责表使用 `workflowId=-99999999`，`source=form` 会解析为 `variables` 中的同名变量。系统字段统一使用 `source=system`。复杂条件也可直接提供平台原始 `childrens`。操作者类型直接支持 `all`、`user`、`initiator`；其他已有操作者类型使用 `raw` 并提供平台 `itemDatas`，结构与普通流程操作者一致。

条件字段查询：

```bash
e10-cli workflow auth-resp condition-fields <authRespId> --source-id <分支sourceId> --workflow-id <流程ID|-99999999>
```

| 业务来源 | 随流程新建权责表 | 独立或复用权责表 |
|---|---|---|
| 系统字段 `system` | 直接选择并保存 | 直接选择并保存 |
| 表单字段 `form` | 直接选择当前流程实际表单字段 | 选择权责表变量作为表单字段的抽象 |
| 变量 `variable` | 一般不需要 | 创建后用于条件，复用流程时映射到实际表单字段 |

因此两种搭建方式都可以配置系统字段和表单字段条件；区别是独立权责表尚未绑定具体表单，配置时以变量表示表单字段，并在流程引用该权责表后完成变量映射。

`usage=workflow` 表示完整流转，首尾默认使用发起和结束节点。`usage=fragment` 表示供其他权责表路径引用的中间片段，`start.type` 与 `end.type` 均配置为 `approve`、`confirm` 等中间节点类型；首尾位置不能使用 `start` 或 `end`。

```bash
e10-cli workflow auth-resp create "合同分级审批权责表"
e10-cli workflow auth-resp variable add <authRespId> "合同金额" wf_number
e10-cli workflow auth-resp variable add <authRespId> "出行人" wf_browser --second-type wf_sub_company --detail
e10-cli workflow auth-resp variable list <authRespId>
e10-cli workflow auth-resp read <authRespId> --base-id <baseId> > design.json
e10-cli workflow auth-resp save-design <authRespId> --config @design.json
```

变量类型码当前已确认：

| 类型码 | 含义 | 补充配置 |
|---|---|---|
| `wf_string` | 字符串 | — |
| `wf_number` | 数值 | — |
| `wf_select` | 选项 | `--option-template '{"id":"...","name":"..."}'` |
| `wf_browser` | 浏览 | `--second-type` |
| `wf_browser_relate` | 关联浏览 | `--relate-browser @browser.json` |

变量既可以属于主表，也可以通过 `--detail` 创建为明细变量。明细变量用于表达未来流程表单中的某个明细字段，分支条件必须同时指定行量词：

```json
{
  "condition": {
    "relation": "AND",
    "rules": [
      { "source": "form", "field": "出行人", "operator": "等于", "value": [{ "id": "分部ID", "name": "泛微西安" }], "detail": "any" },
      { "source": "form", "field": "出行人", "operator": "不为空", "detail": "all" }
    ]
  }
}
```

- `detail: "any"`：任一行满足该条件，保存为 `detailOption=1`。
- `detail: "all"`：所有行满足该条件，保存为 `detailOption=2`。
- 字符串规则也可在末尾写 `:任一` 或 `:所有`。
- 独立权责表中的 `source=form` 会按变量解析；明细变量被分支条件引用后，复用到流程时映射至类型匹配的实际明细字段。

## 三、表格设计结构

`read` 返回的设计以 `columns` 和 `rows` 为核心：

- 固定列：发起设置 `creator`、分支场景说明 `eventColumn`、条件 `condition`、结束设置 `endOperator`。
- 动态节点列：名称为 `pubNode-<节点ID>`，`pubNodeInfo` 保存节点类型和操作者摘要。
- 嵌套权责表列：名称为 `pubNode-<权责表sourceId>`，`addMethod=2`，同时保存被引用表的 `baseId` 和版本。
- 分支行：保存场景说明、`conditionKey`、发起/结束配置及选中的节点单元格。
- 节点单元格：`nodeInfo` 表示该分支经过此节点；`approveNum` 是执行顺序，相同值表示并行。

每个有效分支必须有非空 `eventColumn` 和 `conditionKey`。界面用于继续录入的空白占位行不进入 CLI 保存数据。

操作者和条件的业务规则与普通工作流一致，具体语法读取 [流程指南](guide-workflow.md) 和 [流程条件指南](guide-workflow-condition.md)。权责表命令自动补充 `belongScene=3`、权责表 ID、分支 ID 等上下文；独立权责表使用变量表达未来需要映射的表单字段。

## 四、在分支中引用权责表

先查询当前宿主权责表可以引用的中间型权责表：

```bash
e10-cli workflow auth-resp reference list <宿主baseId> --name "金额复核"
```

平台按首尾节点类型过滤可引用项，并排除自身和循环引用。添加时指定被引用权责表的具体版本，以及它出现在哪些分支和对应执行顺序：

```bash
e10-cli workflow auth-resp reference add <宿主sourceId> --base-id <宿主baseId> --workflow-id <流程ID> --reference @reference.json
```

```json
{
  "id": "被引用权责表sourceId",
  "name": "金额复核权责表【V1】",
  "baseId": "被引用权责表baseId",
  "versionNum": 1,
  "paths": [
    { "branch": "金额超过50万元", "order": 2 }
  ]
}
```

相同顺序号表示并行，不同顺序号表示串行。移除引用时，同时删除节点列和各分支中的对应路径单元格：

```bash
e10-cli workflow auth-resp reference remove <宿主sourceId> <被引用sourceId> --base-id <宿主baseId> --workflow-id <流程ID>
```

## 五、权责表方式创建流程

权责表是流程的搭建方式，流程表单来源仍按原生工作流程规则选择：自建流程表单、绑定已有流程表单或绑定 EB 表单。基础表单参数写入 `base.json`，其字段与 `workflow create-workflow` 的创建结构一致。

一般需求默认使用“随流程新建权责表”；仅在需求明确要求复用已有权责规则，或需要以独立中间型权责表组成多重嵌套结构时，使用“复用已有权责表”。

### 默认：随流程新建权责表

```bash
e10-cli workflow auth-resp-flow create "合同审批流程" --base @base.json --new-table "合同审批权责表"
```

服务端在创建流程时生成并返回 `workflowId`、`formId` 和 `newAuthRespId`。这种方式已确定实际表单，分支条件直接选择表单字段，不做变量映射；发起和结束位置直接设置操作者。

### 按需：复用已有权责表

```bash
e10-cli workflow auth-resp-flow create "合同审批流程" --base @base.json --reuse-table <authRespId> --mappings @mappings.json
```

也可以对已经创建的流程分步执行：

```bash
e10-cli workflow auth-resp-flow bind <workflowId> <authRespId>
e10-cli workflow auth-resp-flow mapping-read <workflowId>
e10-cli workflow auth-resp-flow mapping-save <workflowId> --mappings @mappings.json
```

复用模式把独立权责表变量映射为当前流程表单字段。先用 `mapping-read` 取得平台返回的变量项和可用字段结构，在对应项补全 `fieldBrowser` 后整体保存；变量类型必须与表单字段匹配，明细变量必须选择实际表单的明细字段。

> **前置条件：只有「已被分支条件引用」的变量才会出现在映射列表里。**
>
> `mapping-read` 返回的 `variableMappingList` 由平台按「该变量是否被本权责表的条件引用」筛出，未被引用的变量**不会出现**，因而无从映射 —— 列表为空不一定是故障。
>
> 自查：`e10-cli workflow auth-resp variable list <authRespId>` 里的 `referred` 字段，为 `false` 的变量不进映射列表。
>
> 由此推出搭建顺序：**变量 → 用条件引用它 → 再建/绑流程 → 映射**。反过来（先建流程、后补变量）不会自动补进列表，且 `auth-resp-flow bind` 对已引用过权责表的流程会拒绝重复绑定，只能重建流程。

## 六、已有权责表流程的维护

权责表方式流程的节点、分支条件、流转路径和生成出口统一通过绑定的权责表设计维护：

```bash
e10-cli workflow auth-resp-flow design-read <workflowId> --auth-resp-id <sourceId> --base-id <baseId> > design.json
e10-cli workflow auth-resp-flow design-apply <workflowId> --auth-resp-id <sourceId> --config @design.json
```

权责表设计保存后，平台生成流程节点和出口。流程的出口列表用于查看生成结果及继续配置出口附加能力；改变分支、条件、经过节点和执行顺序时修改权责表设计。

变量映射是独立的流程功能。复用权责表时，将权责表变量映射到当前流程实际表单字段：

```bash
e10-cli workflow auth-resp-flow mapping-read <workflowId>
e10-cli workflow auth-resp-flow mapping-save <workflowId> --mappings @mappings.json
```

映射项保留变量的 `varId`、`varName`、`varType`、主表/明细位置和筛选参数，在 `fieldBrowser` 中写入实际字段；主表变量映射主表字段，明细变量映射明细字段，且变量类型与字段类型保持匹配。条件中的“任一行/所有行”属于权责表条件本身，映射后继续生效。流程内新建权责表并直接使用表单字段时无需变量映射。

## 七、Plan 记录

流程计划中写清搭建方式、新建或复用的权责表、变量及字段映射、每个分支的场景说明与条件、经过节点和顺序、中间节点类型及操作者。执行时按“表单确定 → 权责表/流程创建 → 变量或字段条件 → 中间节点 → 分支路径 → 映射 → 其他流程设置”的顺序逐项销号。
