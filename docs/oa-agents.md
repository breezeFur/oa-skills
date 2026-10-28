<!-- OA_SKILLS_START -->
## OA 操作前先检查技能

- OA 技能安装根目录：`__OA_SKILLS_DIR__`。开始泛微 E10、E-Builder、OA 表单、流程、动作流、报表、权限或编号相关任务前，先在该目录检查对应技能的 SKILL.md 是否存在，并读取其指令及本次必要的参考资料，再执行操作。
- oa-skill 是技能集合目录，不是单独的技能名称。按任务选择：
  - 应用、表单、原生流程、权限、编号：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-builder/SKILL.md`。
  - ESB 动作流：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-builder/actionflows/SKILL.md`，技能名 generating-actionflows。
  - E-Builder 报表：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-edcreport/SKILL.md`。
  - 自定义组件、指标卡、图表、表格、筛选器：`__OA_SKILLS_DIR__/oa-skill/weaver-e10-components/SKILL.md`；先按组件技能读取相邻 Builder 的基础指令。
  - MAX 创鑫公司流程、泳道或表单规范：额外读取 `__OA_SKILLS_DIR__/max-workflow-standard/SKILL.md`；其他公司的 OA 任务按其业务要求执行。
- 认证任务若本机另有 weaver-e10-login 等匹配技能，先读取对应技能；本仓库未收录认证技能，不编造其存在或安装来源。
- 只检查任务相关的已知技能路径；不要每次遍历整个技能库、加载全部 references，或为规范问答触发登录。遵循对应技能的渐进读取和交付约定。
- 执行平台查询或修改前，检查任务需要的 CLI 是否可用、版本是否与技能匹配，以及目标环境的认证状态；优先使用技能提供的 CLI 和工具，不凭猜测拼接口、字段或资源 ID。
- 技能、工具或认证缺失时，明确说明缺项与影响，继续可独立完成的部分；依赖缺项的平台操作等待准备完成，不报告未执行的成功结果。
- OA 读写范围以用户本次任务及已有授权为准；安装技能不表示获准修改业务系统。密码、Token、Cookie、私钥及认证缓存留在本机，输出与 Git 提交中不得包含实际凭证。
<!-- OA_SKILLS_END -->
