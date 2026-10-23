# 公文流程指南

## 定位

公文流程是原生工作流程的特殊类型，由 `bridgeService=odoc` 标识。固定/自由通过 `--is-free 0|1` 设置。需求明确出现公文流程、公文审批、收文、发文、公文设置或正文设置时读取本指南；节点、出口、操作者、条件和布局规则同时读取 [流程表单指南](guide-workflow.md)，公文专属设置读取 [公文设置指南](guide-workflow-odoc-setting.md)。

## 创建方式

### 随流程自建原生流程表单

```bash
e10-cli workflow create-workflow "公文审批流程" --odoc --layout FLOW
```

自建模式提交 `relateForm=0`、`formId=0` 和 `bridgeService=odoc`。表格式布局使用 `--layout EXCEL`。

### 绑定已有原生流程表单

```bash
e10-cli workflow create-workflow "公文审批流程" --odoc --form-id <formId>
```

绑定模式提交 `relateForm=1`、`formId=<已有原生流程表单ID>` 和 `bridgeService=odoc`。后续字段与布局继续使用 `wf-form` 和返回的原生流程表单 `formId`。

团队流程默认使用当前创建者机构；多机构场景显式传 `--sub-company <机构ID>`。`--workflow-type`、`--desc`、`--is-free` 等参数与普通原生工作流程一致。

## 完整搭建顺序

1. 使用 `workflow create-workflow --odoc` 创建流程并取得 `workflowId`、`formId`。
2. 使用 `wf-form` 创建主表字段、明细表及布局，先准备公文设置要引用的标题、正文、文号、目录区分等字段。
3. 使用通用 `workflow` 命令配置节点、操作者、出口、条件、会签、退回、超时、消息、编号及动作流。
4. 使用 `workflow odoc setting get <workflowId>` 读取当前环境提供的公文设置分组、字段候选项、节点候选项及默认值。
5. 按需求使用 `workflow odoc setting set` 配置公文专属内容；字段选择使用字段 ID，节点选择可使用名称或 ID。
6. 读取流程、公文设置和相关表单配置，核对已配置项目。

创建结果以 `flowKind:"odoc"`、`bridgeService:"odoc"` 标识公文流程。每完成一个计划项即在计划中销号。

## 查询与配置入口

```bash
e10-cli workflow odoc list [--name <关键词>] [--sub-company <机构ID>]
e10-cli workflow odoc read <workflowId>
e10-cli workflow odoc setting get <workflowId>
e10-cli workflow odoc setting set <workflowId> --config @odoc-setting.json
```

- `list` 查询公文流程。
- `read` 返回流程名称、绑定表单 `formId` 和公文设置摘要。
- `setting get` 返回完整设置分组、当前值及候选项。
- `setting set` 读取当前配置、合并指定内容、保存并回读。

常用参数示例：

```bash
e10-cli workflow odoc setting set <workflowId> \
  --official-type 1 \
  --request-title-field "公文标题" \
  --upload-word 1 --upload-pdf 1 --upload-ofd 1 \
  --text-in-form 1 --column-position 1 \
  --open-text-select 2 --open-text-node "发起节点" \
  --edit-text-node "发起节点" \
  --attach-area 1 --archive-node "归档节点" \
  --ai-odoc 1 --ai-abstract 1 --ai-format 1
```

字段参数支持字段名称或字段 ID；节点参数支持节点名称或节点 ID。节点名称重复时使用节点 ID。平台开关值使用 `0` 和 `1`。

公文设置的十九个配置分组、字段码表、依赖关系、JSON 写法和支持状态统一见 [公文设置指南](guide-workflow-odoc-setting.md)。
