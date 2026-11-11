---
name: weaver-e10-page-generator
display_name: 泛微E10页面生成工具
display_name_en: Weaver E10 Page Generator
description: 根据文字、截图或现有工程生成、复刻、修改并交付页面。页面制作需求中提到 ecology、泛微、E10、ECode、系统页面、门户、办公、OA 时使用，也适用于静态 HTML 页面和 HTML 页面包。用户要求把代码保存到指定本地目录时同样使用，无需点名工具或先提出发布部署。
description_zh: 根据文字、截图或现有工程生成、复刻、修改并交付页面。页面制作需求中提到 ecology、泛微、E10、ECode、系统页面、门户、办公、OA 时使用，也适用于静态 HTML 页面和 HTML 页面包。用户要求把代码保存到指定本地目录时同样使用，无需点名工具或先提出发布部署。
description_en: Generate, recreate, modify, and deliver pages from text, screenshots, or existing projects. Use for Ecology, Weaver, E10, ECode, portal, office, and OA pages, static HTML pages and packages, including requests to save code to a local directory without explicitly asking to deploy.
version: 0.1.71
author: 泛微网络科技股份有限公司
agent_created: true
---

# 泛微E10页面生成工具

本 Skill 的产品名称是“泛微E10页面生成工具”。文中的 `ui-code-agent` 只表示后台命令入口，
内部组件事实服务只表示 E10 页面分支的技术依赖，不是产品名称。

## 适用请求与产品入口

在页面生成、截图复刻或页面修改语境中，ecology、泛微、E10、ECode、系统页面、门户、办公、OA
都是本产品的命中线索，英文大小写不影响判断。用户无需点名“泛微E10页面生成工具”或
`ui-code-agent`。例如“分析图片，生成 ecology 页面，代码放到 xxx 文件夹”应进入本产品。

用户指定的本地目录是工程或源码的位置约束，应传递给后续工程命令；不能据此判断“不适合使用
产品”。要求 HTML、没有主动要求发布或真实数据、尚未提供登录信息，也都不是绕过产品的理由。
页面产物类型只决定进入产品后的 HTML 或公共组件分支，不决定是否使用产品。

命中后先按下文固定入口调用 bootstrap，读取当前 CLI 返回的正式协议，再按实际 `NEXT:` 推进。
不要在入口预判必须登录或必须发布，也不要以旧版本使用记忆或对流程复杂度的猜测替代本次执行。
实际命令报错时按当前 `FIX:`/`NEXT:` 处理并如实报告。

## 页面产物类型确认

用户可见名称固定为两种：`React + 公共组件体系` 和 `HTML 页面`。内部工程键
`e10-page`/`static-html` 不作为用户选项展示，也不使用“E10 前端页面”“HTML 静态页面包”等旧名称。

新页面任务默认使用 `static-html`，不要询问 A/B。只有用户明确要求“使用组件”或
“使用公共组件体系”时，才判定为 `e10-page`。E10、门户、前端页面、React、ECode、Runtime、
SDK、数据接口或其他技术措辞本身都不触发 `e10-page`；未明确要求使用组件时一律使用
`static-html`。

已有工程按 `.ui-code-agent/project.json` 或既有工程骨架锁定类型，后续修改不重新推断或切换。
新建静态页显式使用 `init --name <项目英文名> --parent <父目录> --kind static-html`；明确要求使用组件时才使用
`init --name <项目英文名> --parent <父目录> --kind e10-page`。

## 固定入口

Agent 先按 [CLI 自动准备](../oa-skill/cli-setup.md) 检查 Node.js >=22.5；缺少或版本不足时直接准备符合要求的 LTS 并验证。页面 CLI 与组件运行时仍只通过本技能 bootstrap 自动安装或更新到 `product.json` / `runtime-lock.json` 声明的版本，不要求用户手动安装、不额外确认安装。用户要求更新页面技能时，清单与锁文件一起更新后再执行 `ensure`，不单独改产品版本或全局安装 `ui-code-agent`。

处理任何页面任务前，先把本文件所在目录记为 `<SKILL_DIR>`，后台执行：

```text
node "<SKILL_DIR>/scripts/bootstrap.mjs" status --json
```

状态不是 `ready` 时，先向用户发送且只发送一次：

```text
首次使用需要在本机准备页面生成环境，预计需要几分钟。准备完成后会继续当前任务，以后使用不再重复安装。
```

这条消息必须在任何 `ensure` 或 `run` 写调用之前发送。随后直接执行：

```text
node "<SKILL_DIR>/scripts/bootstrap.mjs" ensure --json
```

本次 WorkBuddy Bash tool 调用必须把 `timeout` metadata 设置为 `600000 ms`（10 分钟）。这是
Bash tool 的调用字段，不是上述命令的参数。命令必须直接执行，禁止附加 `head`、`tail`、
`grep`、`rg`、`more`、`findstr` 或任何 pipeline/包装脚本。必须检查 Bash tool 返回的进程
退出码；只有退出码为 0 才能继续。非零、timeout 或中断时立即停止，不得执行 `protocol`，
也不得调用半安装 runtime 中的任何 CLI。

初始化失败时，向用户报告失败阶段、原因摘要和日志路径，然后结束当前回合。
禁止自行执行 `npm install`、`npm ci`、`npm rebuild`，下载或补写 `node_modules` 中的文件，
删除 runtime、lock 或 cache，以及修改 bootstrap；不得用管道或追加成功命令掩盖失败退出码。
后续任务仍只调用本 Skill 的 `ensure`：它会持锁保留未就绪的旧安装，从空目录使用原包来源
完整重装并自检。即使报错是缺少某个依赖，也不要逐个修补或换用线上同版本产品包。

随后所有产品命令都只能通过官方 wrapper 执行：

```text
node "<SKILL_DIR>/scripts/bootstrap.mjs" run -- <ui-code-agent 参数>
```

`run` 会原子确保本地 runtime 就绪并继续执行当前命令。初始化成功后不得要求用户重新提问。
不得要求用户打开终端、安装 npm 包、配置 MCP 或重启 WorkBuddy。

## 公共组件运行环境

首次准备只包含 HTML 页面所需环境。`React + 公共组件体系`（`e10-page`）另需组件运行环境；
HTML 页面任务不得准备它。任务确定为 `e10-page` 后、执行 `init --kind e10-page` 之前，查看
`status --json` 返回的 `features.e10-page`；不是 `ready` 时，先向用户发送且只发送一次：

```text
使用公共组件体系需要在本机准备组件运行环境，预计需要几分钟，准备完成后继续当前任务。
```

再直接执行下面的命令。Bash tool 的 `timeout` 同样设置为 `600000 ms`，同样禁止附加任何
pipeline 或包装脚本，同样只有退出码为 0 才能继续：

```text
node "<SKILL_DIR>/scripts/bootstrap.mjs" ensure --feature e10-page --json
```

`run` 返回 `E10_PAGE_RUNTIME_NOT_READY` 时按其 `FIX:`/`NEXT:` 同样处理，成功后重新执行原命令。

## 读取正式协议

`status` 原本就是 `ready`，或上述 `ensure` 明确退出 0 后，后台执行：

```text
node "<SKILL_DIR>/scripts/bootstrap.mjs" protocol --json
```

先完整读取返回的 `skill` 绝对路径，再按其工程类型指引只读取对应的 `agentsStatic` 或 `agents`
协议，并在整个任务中遵守。不得读取 SkillHub 临时目录外猜测的仓库副本、旧 runtime 或旧安装状态。

后续只加载产品协议指定的当前阶段内容；不要在首次生成前预读数据、配置页、发布或失败恢复规范。
页面要有必要的交互。WorkBuddy 的 Read/present_files 审计顺序由所选页面协议规定。
普通进度用简短助手文本，不调用 TaskCreate/TaskUpdate；不逐条播报命令。
需要用户选择时原样使用 CLI 的 WORKBUDDY_TOOL_ARGS/CLI_CONTEXT，转发 USER_MESSAGE 正文。
成功后执行权威 NEXT；相同输入和状态下重复失败则按 FIX 处理，不机械重试。
