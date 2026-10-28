# OA Skills 安装与使用约定

本仓库可交给 AI 安装。收到用户明确的安装请求时，先读 [README.md](README.md)，完成技能安装、规则合并和安装验证；仅阅读仓库不执行安装。

## 给安装 AI 的要求

1. 查明目标 AI、操作系统、真实技能目录和实际生效的规则文件；使用用户指定的位置。Codex 的当前默认技能目录与规则目录不同，详见 README。
2. 保留完整 skills/oa-skill 和 skills/max-workflow-standard 目录。已有安装先比较来源、链接目标及内容，保留用户改动，避免重复安装同名技能。
3. 安装后读取 [docs/oa-agents.md](docs/oa-agents.md)，将 __OA_SKILLS_DIR__ 替换为本机技能目录的绝对路径，把 OA_SKILLS_START / OA_SKILLS_END 之间的整块内容合并到接收者实际生效的 AGENTS.md 或其 AI 使用的同类规则文件。保留原规则；已有该块时更新同一块，不重复追加。写入前备份已有文件。
4. 仓库根 AGENTS.md 包含本仓库维护规则，不能整文件覆盖接收者的全局规则。只合并上述 OA 规则片段。只有克隆仓库，没有安装到技能目录、没有合并规则，不能算完成安装。
5. 回读核对 5 个技能定义、规则中的真实路径和唯一标记块，并在接收者 AI 的新会话中确认技能及 OA 规则被识别。分别报告技能安装、规则合并、CLI 可用性及认证准备情况。

下面的 OA 使用规则适用于本仓库。安装到其他位置时使用 docs/oa-agents.md 的片段替换路径。

<!-- OA_SKILLS_START -->
## OA 操作前先检查技能

- OA 技能安装根目录：`skills`。开始泛微 E10、E-Builder、OA 表单、流程、动作流、报表、权限或编号相关任务前，先在该目录检查对应技能的 SKILL.md 是否存在，并读取其指令及本次必要的参考资料，再执行操作。
- oa-skill 是技能集合目录，不是单独的技能名称。按任务选择：
  - 应用、表单、原生流程、权限、编号：`skills/oa-skill/weaver-e10-builder/SKILL.md`。
  - ESB 动作流：`skills/oa-skill/weaver-e10-builder/actionflows/SKILL.md`，技能名 generating-actionflows。
  - E-Builder 报表：`skills/oa-skill/weaver-e10-edcreport/SKILL.md`。
  - 自定义组件、指标卡、图表、表格、筛选器：`skills/oa-skill/weaver-e10-components/SKILL.md`；先按组件技能读取相邻 Builder 的基础指令。
  - MAX 创鑫公司流程、泳道或表单规范：额外读取 `skills/max-workflow-standard/SKILL.md`；其他公司的 OA 任务按其业务要求执行。
- 认证任务若本机另有 weaver-e10-login 等匹配技能，先读取对应技能；本仓库未收录认证技能，不编造其存在或安装来源。
- 只检查任务相关的已知技能路径；不要每次遍历整个技能库、加载全部 references，或为规范问答触发登录。遵循对应技能的渐进读取和交付约定。
- 执行平台查询或修改前，检查任务需要的 CLI 是否可用、版本是否与技能匹配，以及目标环境的认证状态；优先使用技能提供的 CLI 和工具，不凭猜测拼接口、字段或资源 ID。
- 技能、工具或认证缺失时，明确说明缺项与影响，继续可独立完成的部分；依赖缺项的平台操作等待准备完成，不报告未执行的成功结果。
- OA 读写范围以用户本次任务及已有授权为准；安装技能不表示获准修改业务系统。密码、Token、Cookie、私钥及认证缓存留在本机，输出与 Git 提交中不得包含实际凭证。
<!-- OA_SKILLS_END -->

## 仓库维护

- 已发布技能为 weaver-e10-builder、generating-actionflows、weaver-e10-edcreport、weaver-e10-components、max-workflow-standard。只提交本次相关文件；新增顶层或嵌套 SKILL.md 默认留在本机，按用户直接调用 skill-manage-github 并明确上传的范围收录。
- 维护本仓库前检查 Git 状态、拉取远端、比较分支，保留无关改动。维护者已安装 skill-manage-github 时使用其流程，否则按 README 中的 Git 检查步骤完成维护；推送后核对远端和本地提交一致。
- 原 agent-skills 与本仓库独立维护。跨仓库复制先比较内容及来源，按用户指定范围同步。
- 文本使用 UTF-8 与 LF；原始 DOCX、PNG、EMF、OLE 等二进制保留字节与来源。用户于 2026-10-23 明确要求公开本仓库，当前 MAX 原件和历史附件随仓库公开；后续新增公司资料须确认其公开范围。更新 MAX 包内资料时同步完整性清单并运行 scripts/verify_bundle.py。
- 密码、Token、Cookie、私钥、认证缓存、本机配置、数据库及生成日志不得提交。维护安装说明时保留离线验证和真实 OA 操作之间的区别。
- 修改代码或配置后，在 vibecodingdoc/yyyy-mm-dd/ 维护同一任务的中文变更记录及 vibecodingdoc/INDEX.md，记录时间与时区、执行者、目标、关键变化及实际验证；该目录仅留本机。
