# OA Skills 安装与使用约定

本仓库可交给 AI 安装。收到用户明确的安装请求时，先读 [README.md](README.md)，完成技能安装、规则合并和安装验证；仅阅读仓库不执行安装。

## 给安装 AI 的要求

1. 查明目标 AI、操作系统、真实技能目录和实际生效的规则文件；使用用户指定的位置。Codex 的当前默认技能目录与规则目录不同，详见 README。
2. 保留 skills/ 下本次选定技能的完整目录及相对引用；全量安装时包含 node-write、oa-skill、max-workflow-standard 及所有 weaver-e10-* 目录。已有安装先比较来源、链接目标及内容，保留用户改动，避免重复安装同名技能。
3. 安装后读取 [docs/oa-agents.md](docs/oa-agents.md)，将 __OA_SKILLS_DIR__ 替换为本机技能目录的绝对路径，把 OA_SKILLS_START / OA_SKILLS_END 之间的整块内容合并到接收者实际生效的 AGENTS.md 或其 AI 使用的同类规则文件。保留原规则；已有该块时更新同一块，不重复追加。写入前备份已有文件。
4. 仓库根 AGENTS.md 包含本仓库维护规则，不能整文件覆盖接收者的全局规则。只合并上述 OA 规则片段。只有克隆仓库，没有安装到技能目录、没有合并规则，不能算完成安装。
5. 回读核对 14 个技能定义、规则中的真实路径和唯一标记块，并在接收者 AI 的新会话中确认技能及 OA 规则被识别。按技能依赖直接安装或更新所需 CLI 并验证，随后分别报告技能安装、规则合并、工具准备及认证状态；不要让用户自行安装工具。页面 runtime 按首次实际页面任务自动准备。

下面的 OA 使用规则适用于本仓库。安装到其他位置时使用 docs/oa-agents.md 的片段替换路径。

<!-- OA_SKILLS_START -->
## OA 操作前先检查技能并自动准备工具

- OA 技能安装根目录：`skills`。开始泛微 E10、E-Builder、OA 表单、流程、动作流、报表、权限、编号、页面或迁出包比对任务前，先读取对应技能的 SKILL.md 及本轮必要的参考资料。
- 按任务选择；oa-skill 是集合目录：
  - UTF-8 文本或 DGS 受控源码读写：`skills/node-write/SKILL.md`；Windows 缺少 Node 时按该技能自动安装，随后重新验证实际 DGS 能力。
  - 应用、表单设计、原生流程设计、权限、编号：`skills/oa-skill/weaver-e10-builder/SKILL.md`。
  - ESB 动作流：`skills/oa-skill/weaver-e10-builder/actionflows/SKILL.md`，技能名 generating-actionflows。
  - E-Builder 报表：`skills/oa-skill/weaver-e10-edcreport/SKILL.md`。
  - 自定义组件、指标卡、图表、表格、筛选器：`skills/oa-skill/weaver-e10-components/SKILL.md`。
  - E10 登录和环境认证：`skills/weaver-e10-login/SKILL.md`。
  - 租户、人员身份切换等基础操作：`skills/weaver-e10-basic/SKILL.md`。
  - 按稳定 Tag 查询和维护表单数据：`skills/weaver-e10-ebuilder-data/SKILL.md`。
  - 业务列表、表单数据填写与修改：`skills/weaver-e10-ebuilder-form/SKILL.md`。
  - 待办、已办、发起和处理流程：`skills/weaver-e10-workflow/SKILL.md`；先读取配套 `skills/weaver-e10-shared/SKILL.md`，认证由 weaver-work-cli 托管。
  - 页面生成、复刻和修改：`skills/weaver-e10-page-generator/SKILL.md`。
  - 新旧迁出包离线比对：`skills/weaver-e10-package-comparison/SKILL.md`。
  - MAX 创鑫公司流程、泳道或表单规范：额外读取 `skills/max-workflow-standard/SKILL.md`；其他公司的 OA 任务按其业务要求执行。
- 用户要求安装/更新技能或执行需要 CLI 的任务时，按 `skills/oa-skill/cli-setup.md` 由 Agent 直接检查、安装或更新本轮所需工具，并验证真实路径、版本和启动。有效版本直接复用，不要求用户手动安装，也不另外设置安装确认步骤；用户明确要求只检查或不安装时遵从。
- 页面工具通过自己的 bootstrap 和产品锁文件自动准备；XiaoE 客户端托管的流程 CLI 按共享技能由客户端准备，其他环境按官方 npm 来源自动安装/更新。不要安装猜测的包或无关 CLI。
- 只读取任务相关路径，不每次扫描全部技能。纯规范问答不登录，离线包比对不安装在线 OA CLI；仅补齐实际需要的本地解释器。
- 工具准备完成后继续原任务。CLI 安装验证不调用平台业务接口；实际在线操作前才核对目标环境和有效认证。已有登录态复用，缺少认证时按对应技能发起官方授权。
- 真正的系统权限、宿主能力或认证缺项如实说明，继续可独立完成的部分；不把未执行的安装、登录或业务操作报告为成功。OA 业务读写和确认以用户任务及对应技能契约为准。
- 密码、Token、Cookie、私钥、认证缓存和本机配置留在本机，输出与 Git 提交中不得包含实际凭证。
<!-- OA_SKILLS_END -->

## 仓库维护

- 已发布的 14 个技能以 README 表格和远端各 SKILL.md 为准，包含流程必需的 weaver-e10-shared。只提交本次相关文件；新增顶层或嵌套 SKILL.md 默认留在本机，按用户直接调用 skill-manage-github 并明确上传的范围收录。
- 维护本仓库前检查 Git 状态、拉取远端、比较分支，保留无关改动。维护者已安装 skill-manage-github 时使用其流程，否则按 README 中的 Git 检查步骤完成维护；推送后核对远端和本地提交一致。
- 原 agent-skills 与本仓库独立维护。跨仓库复制先比较内容及来源，按用户指定范围同步。
- 文本使用 UTF-8 与 LF；原始 DOCX、PNG、EMF、OLE 等二进制保留字节与来源。用户于 2026-10-23 明确要求公开本仓库，当前 MAX 原件和历史附件随仓库公开；后续新增公司资料须确认其公开范围。更新 MAX 包内资料时同步完整性清单并运行 scripts/verify_bundle.py。
- 密码、Token、Cookie、私钥、认证缓存、本机配置、数据库及生成日志不得提交。维护安装说明时保留离线验证和真实 OA 操作之间的区别。
- 修改代码或配置后，在 vibecodingdoc/yyyy-mm-dd/ 维护同一任务的中文变更记录及 vibecodingdoc/INDEX.md，记录时间与时区、执行者、目标、关键变化及实际验证；该目录仅留本机。
