# 自动安装与可用性检查

仅准备当前任务所需的 weaver-work-cli。XiaoE 客户端已经托管配套运行时，按共享入口的宿主规则由客户端自动更新，不另装可能指向其他环境的全局副本。非 XiaoE 环境按 [CLI 自动准备](../../oa-skill/cli-setup.md) 直接补齐运行时和 CLI。

## 定位与复用

检查 `weaver-work-cli --version` 和当前业务命令 `--help`。命令找不到时先执行 `npm prefix -g`；Windows 全局命令通常在该目录，macOS/Linux 通常在其 bin 子目录。找到真实可执行文件后前置当前进程 PATH 或用绝对路径调用，再核对版本；不能把 PATH 缺项当作包缺少。

## Agent 直接安装或更新

用户要求安装/更新技能或运行依赖该 CLI 的任务时，缺少、版本低于基线 0.1.49 或明确不兼容就直接执行下面命令。版本匹配时复用，用户明确要求更新时核对官方最新版本。无需安装选择弹框，也不把命令交给用户手动执行。

```text
node --version
npm --version
npm install -g weaver-work-cli@latest --registry=https://registry.npmjs.org
weaver-work-cli --version
weaver-work-cli workflow --help
```

Windows 依据宿主采用 npm.cmd 或已确认的 Node/npm 入口；macOS/Linux 使用实际可用的 npm。权限受限时使用用户可写的 prefix 及绝对路径，不清空缓存、不删认证文件、不自动覆盖其他技能。仅用户指定源码安装时才在确认过的该源码目录执行 npm install、npm run build、npm link；不要猜测仓库地址。

## 共享技能与副本更新

本仓库已包含完整 weaver-e10-shared。需要修复缺失副本时：

```text
weaver-work-cli skills install shared --target-dir "<业务技能上一级的绝对目录>"
```

更新前比较来源、版本和用户修改，备份到技能目录之外，按 skills install --help 更新同一目标。已有符号链接或 Junction 时保留并更新实际来源，不递归删除链接。回读共享规则及相对 references，避免留下重复同名技能。

## 验证与认证

核对实际命令路径、版本及 --help 的退出码。安装成功后继续原任务；安装失败时如实报告阶段、原因和受影响操作。只读命令帮助不需要登录。在线任务的环境、认证及业务写入按共享入口执行；CLI 安装不能证明业务 API 或登录态已可用。
