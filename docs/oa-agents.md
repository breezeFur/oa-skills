<!-- OA_SKILLS_START -->
## OA 操作前先检查技能并自动准备工具

- OA 技能安装根目录：`__OA_SKILLS_DIR__`。开始泛微 E10、E-Builder、OA 表单、流程、动作流、报表、权限、编号、页面或迁出包比对任务前，先读取对应技能的 SKILL.md 及本轮必要的参考资料。
- 按任务选择；oa-skill 是集合目录：
  - UTF-8 文本或 DGS 受控源码读写：`__OA_SKILLS_DIR__/node-write/SKILL.md`；Windows 缺少 Node 时按该技能自动安装，随后重新验证实际 DGS 能力。
  - 应用、表单设计、原生流程设计、权限、编号：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-builder/SKILL.md`。
  - ESB 动作流：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-builder/actionflows/SKILL.md`，技能名 generating-actionflows。
  - E-Builder 报表：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-edcreport/SKILL.md`。
  - 自定义组件、指标卡、图表、表格、筛选器：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-components/SKILL.md`。
  - E10 登录和环境认证：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-login/SKILL.md`。
  - 租户、人员身份切换等基础操作：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-basic/SKILL.md`。
  - 按稳定 Tag 查询和维护表单数据：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-ebuilder-data/SKILL.md`。
  - 业务列表、表单数据填写与修改：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-ebuilder-form/SKILL.md`。
  - 待办、已办、发起和处理流程：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-workflow/SKILL.md`；先读取配套 `__OA_SKILLS_DIR__/oa-skill/weaver-e10-shared/SKILL.md`，认证由 weaver-work-cli 托管。
  - 页面生成、复刻和修改：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-page-generator/SKILL.md`。
  - 新旧迁出包离线比对：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-package-comparison/SKILL.md`。
  - MAX 创鑫公司流程、泳道或表单规范：额外读取 `__OA_SKILLS_DIR__/max-workflow-standard/SKILL.md`；其他公司的 OA 任务按其业务要求执行。
- 用户要求安装/更新技能或执行需要 CLI 的任务时，按 `__OA_SKILLS_DIR__/oa-skill/cli-setup.md` 由 Agent 直接检查、安装或更新本轮所需工具，并验证真实路径、版本和启动。有效版本直接复用，不要求用户手动安装，也不另外设置安装确认步骤；用户明确要求只检查或不安装时遵从。
- 页面工具通过自己的 bootstrap 和产品锁文件自动准备；XiaoE 客户端托管的流程 CLI 按共享技能由客户端准备，其他环境按官方 npm 来源自动安装/更新。不要安装猜测的包或无关 CLI。
- 只读取任务相关路径，不每次扫描全部技能。纯规范问答不登录，离线包比对不安装在线 OA CLI；仅补齐实际需要的本地解释器。
- 工具准备完成后继续原任务。CLI 安装验证不调用平台业务接口；实际在线操作前才核对目标环境和有效认证。已有登录态复用，缺少认证时按对应技能发起官方授权。
- 真正的系统权限、宿主能力或认证缺项如实说明，继续可独立完成的部分；不把未执行的安装、登录或业务操作报告为成功。OA 业务读写和确认以用户任务及对应技能契约为准。
- 密码、Token、Cookie、私钥、认证缓存和本机配置留在本机，输出与 Git 提交中不得包含实际凭证。
- 用户已明确指定目标、操作、字段值/接收人和范围时，其请求即为本次授权；先检查实际目标和预览，匹配后继续执行。只在目标不唯一、范围或数量超出请求、预览出现新的实质变更、不可逆选择缺失或平台强制要求时提问，一次问齐已知缺项。CLI 的 prepare、continuation、confirm=true/--yes 和写后回查必须保留；确认参数是执行校验，不能代替用户授权，也不要求对已授权的相同操作再口头确认。用户明确要求先看方案或逐步确认时遵从。
- 用户已经提供的目标地址、账号密码和登录授权直接沿用，不再次询问是否允许登录或重复索取。已有匹配环境的有效会话直接复用；新会话由 Agent 发起官方 OAuth 登录。CLI 没有账号密码直登参数时，在可控的官方浏览器登录页使用用户提供的账号密码；不把密码作为 ETEAMSID，不猜测登录接口或参数。只有验证码、MFA、平台授权按钮或当前工具无法操作的页面需要用户参与时，说明具体阻碍并交接该步骤。CLI 与浏览器能否访问同一本地回调由 Agent 根据实际运行环境判断，无需用户口头确认同机。不要把凭证或带凭证的工具结果打印到对话、日志或提交中。
- 用户明确要求读取、解析、上传或复用指定附件时，按该任务直接执行，不额外添加通用数据风险警告或 Yes/No 弹框。仅提供路径而没有操作意图时先明确任务；需要把文件发送到任务未涵盖的新外部服务时，先说明实际接收方、用途并取得授权。按实际数据路径描述处理过程，不断言所有附件都会先经过公网大模型。
<!-- OA_SKILLS_END -->
