---
name: weaver-e10-ebuilder-data
display_name: 泛微E10eBuilder专项基础
display_name_en: E10 eBuilder Data Management
description: 根据稳定 Tag 定位 E10 eBuilder 应用与表单，通过自定义接口或 API 查询和维护表单数据，按名称查询人员、部门、分部及各类关联浏览数据，并按 Tag 查询当前数据可用的按钮及动作。适用于跨环境重新定位表单、查询数据或安全变更表单数据的任务。
description_zh: 根据稳定 Tag 定位 E10 eBuilder 应用与表单，通过自定义接口或 API 查询和维护表单数据，按名称解析人员、部门、分部及关联浏览字段，并按 Tag 查询按钮及动作。
description_en: Locate E10 eBuilder apps and forms by stable tags, query and maintain form data via custom APIs or the eBuilder API, resolve people, departments, sub-companies and related browser fields by name, and query form buttons and their actions by tags.
license: "Proprietary"
author: "泛微网络科技股份有限公司"
version: "1.0.4"
agent_created: true
compatibility: "WorkBuddy；需已安装并授权 weaver-e10-login，目标 E10 环境须开放对应 eBuilder 接口。"
dependencies:
  - "weaver-e10-login"
---

# E10 eBuilder 数据管理

## 触发场景

当用户需要以下操作时，使用本技能：

- 按应用 Tag / 表单 Tag 重新定位 E10 eBuilder 应用或表单（如跨环境迁移、恢复配置、核对数据所属表单）。
- 查询、新增、修改或删除 eBuilder 表单数据（已发布自定义接口或 OpenAPI）。
- 按名称查询人员、部门、分部、审批或关联浏览字段，并转换为可写入表单的 `optionId/content`。
- 按 Tag 查询当前数据可用的按钮及其动作。

不属于以上场景（如纯 OA 登录、流程审批流转）请交给对应技能处理，不要自行猜测接口。

## 目标

按统一流程完成“稳定 Tag 定位表单”和“操作表单数据”。先使用应用 Tag 与表单 Tag 获取可靠的 `appId`、`objId` 和表单元数据，再读取字段定义、选项及明细映射，按名称解析人员、部门、分部或其他关联浏览字段，最后路由到自定义接口或 OpenAPI。

先按 [CLI 自动准备](../cli-setup.md) 由 Agent 直接准备 Python 3.10+ 和匹配的 `e10-login@1.5.0`，验证后继续本轮任务；本技能自带 Python 脚本，无需安装猜测的数据 CLI 包。登录技能已随本仓库收录。宿主命名凭据插件仍按本技能接口契约使用，缺少该宿主能力时明确说明，不用 npm 安装冒充已获得插件能力。

仅使用用户明确指定并已授权的 E10 环境。调用前加载 `weaver-e10-login` 建立会话并获取完整请求地址、当前操作人及命名凭据 `key=ETEAMSID`；禁止要求用户在对话中粘贴 Cookie，禁止猜测域名，禁止在 URL、命令行、日志或技能文件中保存凭证。

## 能力边界

| 能力 | 标识 | 风险 |
|---|---|---|
| 应用 Tag 定位 | `appTag -> appId[]` | 只读 |
| 表单 Tag 定位 | `appId + formTag -> obj[]` | 只读 |
| 字段、选项、明细映射 | `objId` | 只读 |
| 人员、部门、分部和关联浏览数据 | 名称与字段定义 | 只读 |
| 详情、分页、总数 | `objId` 或 `interfacePk` | 只读 |
| 新增、修改、删除 | `objId` 或 `interfacePk` | 写操作，按已明确的任务授权执行 |
| 按 Tag 查询按钮及动作 | `objId` + `dataId` + `tags` + `viewType` | 只读 |

不修改应用 Tag 或表单 Tag，不使用 SQL、跨租户查询或未文档化接口兜底。

## 统一流程

1. **准备会话**：加载 `weaver-e10-login`，复用用户已指定的 E10 地址与有效会话；仅目标不明确时询问，认证后由 Agent 核对环境、租户和登录用户。仅从登录技能的命名凭据插件获取 `key=ETEAMSID`。
2. **确认目标**：收集可用的 `appTag`、`formTag`、`appId`、`objId` 或 `interfacePk`。Long 型 ID 始终按字符串保存、比较和展示。
3. **按需定位**：缺少 `appId` 时按 `appTag` 查询；缺少 `objId` 时按已确认的 `appId + formTag` 查询。0 条则停止，多条则列出候选并等待明确选择，禁止默认取第一条。
4. **选择接口族**：已知且明确要求已发布自定义接口时使用 `interfacePk`；直接操作表单或明确要求 OpenAPI 时使用 `objId`。两者同时存在且意图不清时询问，不交叉拼接请求体。
5. **读取元数据**：数据任务先读取字段定义；仅在需要选项名称与 ID 转换时读取选项；涉及明细时读取 `mainTable/detailN` 映射。
6. **解析浏览字段**：新增或修改时，人员、部门、分部或关联浏览字段只给了名称，就按 [浏览字段查询](references/browser-fields.md) 运行 `scripts/query_browser_field.py`；唯一匹配后再使用 `optionId/content` 组装字段值。
7. **组装请求**：字段键使用字段定义中的 `name`，目标接口明确要求组件键时使用 `config.dataKey`；不得用显示文本 `text` 代替。明细数据放入映射得到的 `detailN`。
8. **确认写操作**：新增、修改在目标、字段、数量或条件存在歧义时确认；删除目标及范围已被用户明确指定时核对后执行；目标、条件或数量有歧义或超出请求时先确认。
9. **执行并核验**：依据 [接口索引](catalog.md) 加载单个 reference。检查 HTTP 状态和对应业务状态；写操作核对返回 ID，查询与总数复用相同条件。
10. **输出摘要**：返回目标环境标识、应用/表单、操作类型、数量、结果和脱敏错误；不输出完整 Cookie、敏感字段或完整原始响应。

## Tag 定位规则

- 应用 Tag 查询返回 0 条时报告未找到；返回多条时展示全部 `appId`，由用户指定一个或确认全部处理。
- 表单 Tag 查询返回 1 条时明确 `data[].id` 为 `objId`；`formId` 不得替代 `objId`。
- 核对表单结果的 `appId` 和 `tag` 与请求一致，不依赖数组顺序或未文档化字段判断目标。
- 用户只说“根据 Tag 查询”时分别询问应用 Tag 和表单 Tag，不把同一个值默认用于两者。

## 数据操作规则

- 自定义接口请求以 `datajson` 为根，当前操作人放入 `datajson.header.operator`；接口类型必须与已发布配置一致。
- OpenAPI 数据操作以 `datajson` 为根，表单上下文放入 `datajson.header.objId`。
- 选择字段提交选项 ID，展示时再映射选项名称；不假设自定义接口返回未配置的字段。
- 网络超时后可有限重试只读请求。新增、修改、删除超时后先查询目标状态，禁止直接盲目重试。
- `401/403` 时停止业务调用，交由登录技能刷新会话或确认权限；不得回显命名凭据内容。

## 浏览字段查询规则

- 用户提供人员、部门或分部名称时，直接查询当前账号有权限选择的数据，不反问用户索要系统 ID。
- 已知字段所属表单时优先读取字段定义，并使用字段实际返回的 `config.browserType.module/type`；不得根据字段标题猜浏览接口。
- 没有表单上下文时可显式查询人员、部门或分部；其他浏览类型必须有字段配置或可靠的 `module/browserType`。
- 只有一条完全同名结果时可以继续写入。重名时展示组织路径、编号等已有信息让用户选择；无结果时不能把显示名称当作 ID。
- 查询结果只保留选择和消歧所需信息，不输出完整原始响应。写入结构以目标字段的真实数据结构为准。

## 按钮 Tag 规则

- 按 Tag 查询按钮使用 `queryByTags` 接口，运行 `scripts/button_tag.py query`；`viewType` 仅支持 `"0"`（显示布局）或 `"2"`（编辑布局），不猜测其他布局。
- 按钮 Tag 允许重复，不同按钮可使用相同 Tag，不视为唯一值。
- 调用方同时处理 HTTP 异常、WeaResult 业务失败和 `data` 内单个按钮的 `success=false`；无权限时按钮与 `actions` 仍返回但 `success=false`，原样透传，不在客户端绕过或模拟权限判断。
- 多个 Tag 部分未匹配时保留已匹配按钮并返回失败信息；所有 Tag 均未匹配时接口返回业务异常。
- `objId`、`dataId` 均为 Long 型 ID，按字符串保存、比较和展示。

## 意图路由

| 用户意图 | 接口 | 必需输入 |
|---|---|---|
| 按应用 Tag 查应用 | `getAppIds` | `appTag` |
| 按表单 Tag 查表单 | `getObjsByTag` | `appId`、`formTag` |
| 新增、修改、删除 | 自定义接口或 OpenAPI | `interfacePk` 或 `objId`，业务数据 |
| 详情、分页、总数 | 自定义接口或 OpenAPI | `interfacePk` 或 `objId`，查询条件 |
| 字段、选项、明细映射 | OpenAPI 元数据接口 | `objId`，以及对应 `groupId/fieldId` |
| 按名称查询人员、部门、分部或关联数据 | 浏览字段查询 CLI | 名称，以及字段上下文或明确的浏览类型 |
| 按 Tag 查询按钮及动作 | 按钮 Tag CLI（`queryByTags`） | `objId`、`dataId`、`tags`、`viewType` |

## 输出格式

定位结果优先使用：

| 应用 Tag | appId | 表单 Tag | objId | 表单名称 | formId | tableName | 状态 |
|---|---|---|---|---|---|---|---|

数据操作结果优先使用：

| 环境 | 表单 | 操作 | 条件/数据 ID | 影响数量 | 结果 | 说明 |
|---|---|---|---|---|---|---|

## References

- [catalog.md](catalog.md)：完整接口清单、路由和依赖顺序。
- [应用 Tag 查询](references/get-app-ids-by-tag.md) 与 [表单 Tag 查询](references/get-objs-by-tag.md)：跨环境定位。
- [OpenAPI 公共说明](references/ebuilder-openapi-common.md)：认证、字段键、明细映射和响应校验。
- [浏览字段查询](references/browser-fields.md)：按名称解析人员、部门、分部和其他关联浏览字段。
- [按钮 Tag 查询](references/ebuilder-button-querybytags.md)：按 Tag 查询当前数据可用的按钮及动作，对应 `scripts/button_tag.py`。
- 其余接口文档按 `catalog.md` 的链接按需加载，避免一次性加载全部参考资料。
