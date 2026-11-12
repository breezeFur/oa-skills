# 表单数据接口路由

仅在用户要求详情、新增、修改、删除、表单级分页/总数、字段或选项查询时读取本文件。当前 List/NList 页面的数据查询继续使用页面运行时接口，以保留页面固定条件、搜索、排序、显示字段和权限语义。

## 选择接口族

- 已知 `objId` 或明确要求 OpenAPI：使用 OpenAPI。
- 已知 `interfacePk`、已发布自定义接口或接口配置类型：使用自定义接口。
- 同时存在两套标识而用户没有指定接口族：先消歧，不能把 `interfacePk` 当作 `objId`，也不能交叉拼接请求体。
- 菜单流程解析出的 `objId` 默认进入 OpenAPI，不虚构 `interfacePk`。

详细索引见 [catalog.md](catalog.md)。只读取本次操作对应的文档，不一次加载所有接口说明。

## 共同前置

1. 复用 [会话与路径路由](session-and-routing.md) 已确认的 origin、认证和 `/form/**` 所需的 `apiPrefix`。
2. OpenAPI 或需要解释真实字段的自定义接口任务，先读取[字段定义](ebuilder-openapi-formdata-getfields.md)。用字段 `text` 匹配用户描述，但请求键优先使用真实 `name`；只有目标接口明确要求组件键时才使用 `config.dataKey`。
3. 普通选择类字段需要名称与值转换时读取[字段选项](ebuilder-openapi-formdata-getoptions.md)，写入选项 `id`，不要把显示名称直接当作业务值。
4. 人员、部门、分部、审批、文档或关联浏览字段只提供显示名称时，读取[按名称查询人员、部门和关联数据](browser-fields.md)，运行 `../../scripts/query_browser_field.py` 解析当前账号可选的数据。名称唯一时使用返回的 `optionId`；重名时先让用户选择，不能要求用户预先知道系统 ID，也不能默认取第一条。
5. 有主明细数据时读取[主明细映射](ebuilder-openapi-formdata-gettablemapping.md)。主表使用 `mainTable`，明细使用返回关系对应的 `detailN`，不能按名称或本地顺序自行编号。
6. 菜单流程使用菜单返回的 `appId` 作为字段/选项接口的 `groupId`；直接入口没有可靠 `groupId` 时必须从当前应用上下文取得，不能猜测。

## OpenAPI

OpenAPI 请求以 `datajson` 为根，表单上下文放在 `datajson.header.objId`。只有 `/api/ebuilder/form/**` 路径按部署结果替换为已确认的 `apiPrefix`；字段、选项等 `/api/ebuilder/common/**` 接口始终使用公共路径。主明细映射位于 `/form/**`，仍按部署结果路由。

新增、修改、详情和删除优先运行[统一表单数据 CLI](cli.md)。它统一处理字段数据键、选择项和浏览字段转换，并在新增或修改后只用 `getDataById` 回查。现有分接口文档仍是请求契约来源，在统一 CLI 无法表达特殊明细或条件操作时按需读取。

执行后依次检查 HTTP 结果、`message.code`/`message.msg`、`data.datajson.status`，并核对 `dataIds` 或查询结果。

## 自定义接口

自定义接口必须与已发布的配置类型一致。请求以 `datajson` 为根；需要 `operator` 时，只使用当前会话已经确认的操作人 ID。自定义接口返回字段取决于接口配置，不能假设返回完整表单数据。

自定义接口均位于 `/api/ebuilder/form/**`。已确认独立部署时，把这部分路径的公共前缀替换为 `/api/ebuilder{appId}`。

## 写操作安全

- 新增和修改在目标、字段、条件或数量有歧义时先确认。
- 用户当前请求已经明确指定删除目标和范围时可直接执行，不再要求用户重复确认；未明确时先展示目标和范围。执行统一 CLI 时仍传入与目标一致的 `--confirm-delete`，该参数是程序内部防误删校验，不代表再次打扰用户。
- 请求超时或结果不明确时，先用详情或分页查询确认是否已经生效，不直接重试。
- 业务 `status=false` 时优先读取 `data.datajson.message`，不能让外层的 `message.msg=success` 覆盖真实失败原因。
- 不得通过 `checkRight=false` 绕过数据创建、修改或删除权限。
- 失败时仅保留脱敏状态、接口阶段和错误信息，不输出凭证或完整敏感数据。
