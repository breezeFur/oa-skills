# 动作流组件属性级动态赋值矩阵

这份矩阵约束 Skill 的决策方式：**是否支持动态赋值取决于具体组件的具体属性**，不是取决于属性名里是否出现 Browser。矩阵只记录已经在 CLI 编译器和测试中接通的能力；平台新版本新增能力时，先补组件契约、编译器和测试，再把状态改为“已接通”。

## 已接通

| 属性类型 | 代表组件/属性 | 支持的动态来源 | 编译结果 |
| --- | --- | --- | --- |
| 普通字段赋值 | `ActionEbAdd`、`ActionEbUpdate`（含密级、密级有效期）、`HrmEmployeeUpdate.fieldAssignments`、`PersonnelOnboarding.fieldAssignments` | 上下文、循环当前行、系统变量、变量、常量、函数/公式 | 按目标字段类型生成 `type=3/5/6/7/8/9/10` 等 FormulaBean |
| 查询结果字段 | `EnquiryForm` 输出被后续动作引用 | 查询结果字段、第一条记录 `index:0`、函数参数 | 使用查询节点真实 `source`、字段真实 ID 和平台结果字段对象 |
| 查询分页与动态条件 | `EnquiryForm.formPageNo`、`formPageSize`、`conditionFormula` | 固定值、上下文、系统变量、变量、常量、函数/公式 | 页码/条数为 FormulaBean；动态条件使用 `conditionType:"assign"`，不能和普通 `filter` 并存 |
| HTTP 请求参数 | `Http.inputParams.formulaData` | 固定值、上下文、系统变量、变量、常量、函数/公式 | 写入接口详情对应参数行的 FormulaBean，不改写接口参数定义 |
| MQ 发送参数 | `InnerMQSend.queueName`、`inputParams` | 固定值、上下文、系统变量、变量、常量、查询结果、函数/公式 | 保留原生 `sendParams` 参数定义，只向命中的参数行写入 `formulaData` |
| DML SQL 参数 | `DMLExecute.fieldSet.assign` | 固定值、上下文、系统变量、变量、常量、查询结果、函数/公式 | 按 SQL 占位符生成 FormulaBean 数组，同时保留原生 FormulaBean 兼容入口 |
| 消息模板 | `SendMessage.msgTitlev/msgContentv/picLink/msgPcLink/msgMobileLink` | 上下文、系统变量、变量、常量、函数/公式、查询结果 | 五个消息文本/链接字段统一保存为 `ContestSettingDTO`；正文占位符与独立绑定；接收人上下文仍保留为动态人员 FormulaBean |
| 消息接收人 | `SendMessage.receiver` | 当前用户、上游人员上下文、固定人员 | 动态人员使用真实上下文 `paramKey`，固定人员使用当前租户 Browser 对象 |
| 人员参数 | 表单数据动作、流程动作、文档动作、`HrmEmployeeUpdate`、`PersonnelOnboarding`、`AlterPersonStatus`、会议/日程中的人员属性 | 当前用户、上游人员上下文、动作流变量/常量/函数 | 不再强制走固定人员查询；动态引用保持人员 FormulaBean，固定人员仍要求真实 Browser 对象 |
| 会议和日程运行时字段 | `MeetingCreate` 的标题/密级/人员，`ScheduleCreate` 的标题/时间/内容/其他地点/人员 | 上下文、系统变量、变量、常量、函数/公式 | 普通字段生成对应 FormulaBean；人员使用人员 FormulaBean；会议室、日程类型、关联流程等设计期资源仍保持 Browser 对象 |
| 流程和文档运行时字段 | 流程实例 ID、标题、意见、公文正文 ID、关联数据 ID、时间、文档/附件 ID、布尔开关等 `formula_or_reference` 属性 | 固定值、上下文、系统变量、变量、常量、查询结果、函数/公式 | 统一经共享公式编译器生成 FormulaBean；固定流程定义、节点、目录 DTO 不在此列 |
| 循环参数 | `MultipleExecution.cycleTimes`、列表/明细来源 | 上下文、变量、常量、当前循环上下文 | 按循环模式生成对应 `CycleParams`/FormulaBean |
| 条件右值 | `Condition` | 固定值、上下文、系统变量、变量、常量、函数 | 右值保留为公式树，不把动态字段名转成固定字符串 |
| 终止节点动态输出 | `finalOutput.params.reminderContent`、`basisValue` | 富文本 `ContestSettingDTO`；提醒内容支持文本、上下文、系统变量、变量、常量、查询结果、函数/公式 | 自动补充的 `Output` 节点保留高级设置，无需在 `actions` 中手写终止节点；旧 `reminderMsgFormula` 不再用于新生成 |

## 需要按组件协议单独判定

以下不是“永远不支持动态”，而是平台 DTO 对资源对象有额外约束，不能使用普通字段公式规则直接套用：

- 流程定义/流程节点/退回节点/干预节点：通常需要当前租户真实流程 Browser 对象或节点对象；只有 `requestId`、标题、意见等字段类属性按组件契约支持动态。
- 文档、目录、附件、共享权限、按钮、规则：固定对象需要当前租户真实 Browser/权限对象；如果组件说明或回读结构提供动态公式入口，必须单独实现该属性的编译器和回读校验。
- 会议、日程、HRM 选择器的结构化对象：人员属性与会议/日程资源属性分开判断。`MeetingCreate.flag`、日程类型、会议室和 `Output.jumpUrl` 均只接受前端允许的固定选择/固定文本，不能因为底层存储字段是 FormulaBean 就推导其支持动态。
- 触发器配置、接口定义、连接器/资源/接口选择：这些是设计期平台资源，默认必须实时发现真实对象，不能把运行时上下文当成连接器或接口定义。

## 处理规则

1. 先执行 `component-describe <type>`，读取该属性的 `valueType`、`referenceType`、`valueShape`、`propertySources` 和运行时上下文。
2. 若属性是字段值、人员值或公式值，优先调用共享公式编译器；不得在组件内部另写“只接受固定值”的分支。
3. 若属性是平台资源对象，必须查看该组件前端回读/保存 DTO 是否有动态入口；没有证据就保留固定对象约束，并明确指出是平台协议限制，而不是 Skill 偷懒。
4. 每新增一个动态属性，至少增加一个上下文用例和一个固定值回归用例；涉及数组/循环时再增加数组或当前循环用例。
5. 生成成功不等于动态赋值正确：正式回读必须确认参数仍为对应 FormulaBean，来源 `paramKey`、`source/frontId`、变量/常量 ID 和循环作用域没有丢失。
