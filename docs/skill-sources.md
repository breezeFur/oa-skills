# 技能来源与本仓库维护

2026-11-11 按维护者要求，将其 Codex 已安装的 OA 技能及完整配套资源同步到本仓库，并调整为由 Agent 自动准备所需 CLI。现有 MAX 原件、图片及附件继续沿用已有公开范围和来源记录；不加入用户运行产生的业务导出文件或认证资料。

weaver-e10-shared 是流程技能明确要求的配套依赖，补自官方 npm 包 weaver-work-cli@0.1.49 的 skills/weaver-e10-shared，原技能版本 1.2.5；下载内容已按 registry 元数据的 SHA-512 integrity 核对。仅收录该共享依赖及其五篇 references，未导入该 npm 包内其他业务技能。

本仓库维护版在各入口和共享安装规则中使用 [CLI 自动准备](../skills/oa-skill/cli-setup.md)，安装或更新由 Agent 执行，CLI 契约匹配时复用，认证及业务写入仍遵守对应技能。页面生成使用随技能的产品清单、锁文件和 bootstrap。

同步排除本机配置、数据库、缓存、日志、凭据、生成的报表调试 JSON 和 Python bytecode。会话与 secretKey 示例使用占位符；公开内容没有授予超出原来源的额外许可。

2026-11-12 按维护者要求从 breezeFur/agent-skills 同步 node-write 及全部七个技能配套文件，接入 UTF-8/DGS 读写指南和 Windows Node 自动准备脚本。运行时、探针、观察器二进制、证据和本机盘点不随技能发布；Node 安装后仍需独立验证 DGS。
