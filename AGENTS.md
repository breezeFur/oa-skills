# OA 技能仓库维护约定

- 本项目维护 4 个技能：weaver-e10-builder、generating-actionflows、weaver-e10-edcreport、max-workflow-standard。按任务读取对应 SKILL.md 及必要参考资料，保留目录与相对引用。
- 技能发布按 skill-manage-github 流程：修改已发布内容前检查工作区、拉取远端、比较分支，保留无关改动；只暂存本次相关文件，推送后验证提交一致。
- 新增顶层或嵌套 SKILL.md 默认留在本机；仅当用户直接明确调用 skill-manage-github 并要求上传指定新技能时，才扩大收录范围。
- 原 agent-skills 与本仓库独立维护。跨仓库复制先核对差异和来源，遵守用户指定范围；不以旧副本覆盖新内容。
- 文件采用 UTF-8 与 LF 文本换行；原始 DOCX、PNG、EMF、OLE 等二进制保留字节与来源。用户于 2026-10-23 明确要求公开本仓库，当前收录的 MAX 来源原件和历史附件随仓库公开；后续新增公司资料须确认其公开范围。更新 MAX 资料包时同步完整性清单并运行 scripts/verify_bundle.py。
- 密码、Token、Cookie、私钥、认证缓存、本机配置、数据库及生成日志不得提交。认证环境在本机配置；缺少的外部工具或技能明确说明，不凭空补造。
- 维护技能或上传仓库不授权访问、修改 OA 业务系统。实际 OA 任务按用户请求和对应技能的操作契约执行，验证结果区分离线检查、配置回读、界面效果与真实流转。
- 修改代码或配置后，在 vibecodingdoc/yyyy-mm-dd/ 维护同一任务的中文变更记录及 vibecodingdoc/INDEX.md。记录时间与时区、执行者、目标、涉及文件、关键变化、实际验证和检索关键词；该目录仅留本机。
