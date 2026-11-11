# 按名称查询人员、部门和关联数据

当用户填写人员、部门、分部、审批数据、文档或其他关联浏览字段时，用户提供业务名称即可。先根据字段定义查询当前账号有权限选择的数据，将名称解析成系统 ID，再组装新增或修改请求；不要直接要求用户提供 ID。

## 统一 CLI

运行 `scripts/query_browser_field.py`。先通过 `weaver-e10-login` 建立或复用目标环境的有效会话，再把其确认的 `origin` 和运行时认证注入当前进程；不要把凭证写入命令、文档或输出。

已知字段所属表单时，优先按字段查询：

```powershell
python scripts/query_browser_field.py "秦珂珂" `
  --field "负责人" `
  --group-id "{{groupId}}" `
  --source-id "{{sourceId}}" `
  --source-type FORM `
  --origin "{{origin}}" `
  --api-prefix "{{apiPrefix}}" `
  --require-unique
```

布局逻辑字段把 `--source-type` 改为 `LOGIC`。没有表单上下文、只是查询通用数据时，可直接指定业务类型：

```powershell
python scripts/query_browser_field.py "秦珂珂" --kind person --origin "{{origin}}"
python scripts/query_browser_field.py "研发部" --kind department --origin "{{origin}}"
python scripts/query_browser_field.py "华东分部" --kind subcompany --origin "{{origin}}"
```

字段定义暂时无法取得，但已经从可靠配置中确认关联浏览的模块和类型时，可显式查询任意标准浏览接口：

```powershell
python scripts/query_browser_field.py "任务类型名称" `
  --module task `
  --browser-type taskTypeBrowser `
  --origin "{{origin}}"
```

个别浏览数据需要额外上下文时，通过 `--extra-json` 传入已确认的请求参数。该参数可以是 JSON 对象字符串，也可以使用 `@文件路径`；不能用它猜测未知的模块、浏览类型或权限参数。

## 字段到浏览数据的路由

CLI 先匹配字段的显示名称、字段名、数据键或字段 ID，再按以下顺序确定接口：

1. 关联浏览字段存在 `config.browserType.module` 和 `config.browserType.type` 时，直接使用两个实际配置值。
2. 人员字段使用 `hrm/resource`，部门字段使用 `hrm/department`，分部字段使用 `hrm/subcompany`。
3. 审批数据字段使用 `workflow/core/wfcRequest`；这里查询的是审批实例，不是流程定义。
4. 文档字段使用 `doc/document`。
5. 其他字段没有返回完整浏览配置时停止，并要求补充可靠的模块与浏览类型；不能根据字段标题或相似接口猜地址。

CLI 调用统一的只读联想接口：

```text
POST /api/{module}/common/browser/complete/{browserType}
```

对于表单字段，CLI 会把字段定义中的 `formId`、`layoutId`、`fieldId` 和 `serviceModule` 带入 `formParam`，保留字段自身的筛选范围。

## 结果与消歧

输出只保留用于选择和消歧的字段。每个可选项至少包含：

```json
{
  "id": "{{optionId}}",
  "name": "{{content}}",
  "dataOption": {
    "optionId": "{{optionId}}",
    "content": "{{content}}"
  }
}
```

- `matchCount=0`：说明当前账号下没有可选结果。不得把名称直接写入，也不能绕过权限换接口查询。
- 返回结果中只有一条与用户输入完全同名时，CLI 优先采用该条，忽略名称仅包含关键词的联想项。
- `unique=true`：可以使用返回的 `dataOption` 继续组装字段值。
- `ambiguous=true`：列出名称、ID、时间、编号或组织路径等已有差异，让用户选择；不得默认取第一条。
- `--require-unique` 在结果不唯一时返回退出码 `2`，应在新增或修改前使用。

写入时以目标数据接口和字段已有数据的真实结构为准。字段结构不明确时，先查询一条已有数据，确认该组件需要 `fieldOptionId`、对象数组还是其他格式，不能仅凭组件名称猜测。

## 认证和部署

- 字段定义接口使用已确认的 `apiPrefix`；浏览数据接口使用字段配置对应的业务模块路径，不拼接 eBuilder `apiPrefix`。
- 可选的 `EBUILDER_BUSINESS_ID` 和 `EBUILDER_SECOND_EMP_ID` 只从当前运行时读取，不写入 Skill。
- 所有请求只发送到当前任务确认的 E10 `origin`，不得把业务数据或认证信息发送到第三方域名。
- 查询受当前账号的数据权限约束。未查到数据不代表数据不存在，也可能是当前账号不可选。
