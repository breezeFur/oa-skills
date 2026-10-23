---
name: weaver-e10-builder
display_name: 泛微E10智能搭建Skill
display_name_en: E10 Builder
description: 泛微E10智能搭建skill v2（通用版），辅助编写泛微Ebuilder自定义应用，对应CLI版本1.5.4
description_zh: 泛微Ebuilder低代码应用智能搭建工具 v2（通用版），辅助编写自定义应用（表单/流程/列表/动作流/权限/分组/编号等），与 e10-cli 配套使用，当前对应 CLI 版本 1.5.4。
description_en: E10 Ebuilder low-code app builder skill v2 (general) — helps build Weaver E10 custom apps (forms/workflows/lists/actionflows/permissions/groups/numbering) via e10-cli, currently paired with CLI 1.5.4.
category: coding
version: 1.5.4
author: 泛微网络科技股份有限公司
auto: true
---

# Ebuilder 智能搭建 Skill

## 安装与升级

本 skill 需与 CLI **版本匹配**（当前对应 CLI `1.5.4`）。版本不一致时命令/文档/选项可能对不上——升级前先对齐：

```shell
e10-cli --version          # 查 CLI 版本，应与上方 description 标注一致

# CLI 从 npm 装（升级先卸旧包 e10-cli，避免 bin 残留冲突）：
** 注意 如果你使用的是workbuddy **
先用 bash 直接删掉旧包目录（不走 npm 的删除），再让 npm 纯安装，必须指定一个有权限的工作目录作为缓存地址

其他工具可以使用 npm rm -g weaver-e10-builder

npm install -g weaver-e10-builder

# skill 升级：先卸旧（旧名 skill-e10-cli；删掉的命令文档/actionflows 不会自动清，是"删不干净"主因），再装新
npx -y skills remove skill-e10-cli
npx -y skills add ./weaver-e10-builder.zip --skill -y
```

> 若 `skills remove` 无效，手动删后再 add，安装位置按工具区分：
> - Claude Code：`rm -rf ~/.claude/skills/skill-e10-cli` → 新 skill 装到 `~/.claude/skills/weaver-e10-builder`
> - WorkBuddy：`rm -rf ~/.workbuddy/skills/skill-e10-cli` → 新 skill 装到 `~/.workbuddy/skills/weaver-e10-builder`

> 📌 **1.1.0 起发布的 skill 都是「薄指令层」扁平简化版**：只带 SKILL.md / _catalog / actionflows 指令层 / scripts（不含深目录文档树，适配 marketplace 两级目录限制）。**完整文档（references 等）随配套 CLI 的 skill-docs 分发**——npm 安装 CLI 时 postinstall 会自动同步，或装完跑一次 `e10-cli auth status` 触发同步。**因此装完 skill 后，看到目录里多出/更新 references 文档、或旧文档被清理，都是正常的同步现象**，不是装错或重复安装。

## 文档与模板取用

**skill 只带指令层；文档/模板随配套 CLI 包发布**（marketplace skill 包限两级目录，深目录文档树走 npm）。

**文档通常已就位，无需手动拷贝**：
- 每次会话跑 `e10-cli auth status` 时，CLI 自动探测本机已装 skill（`~/.claude/skills`、`~/.workbuddy/skills`、`~/.codex/skills`），把文档树同步进对应 skill 目录（SKILL.md 版本一致则跳过）。装好 skill 后第一次 `auth status` 即可。
- 手动刷新：`e10-cli skill sync`（可 `--target <安装根目录>` 指定其他工具目录）。

**读取**：文档在 **skill 目录内**（如 `~/.claude/skills/weaver-e10-builder/`），`references/...`、`actionflows/...`、`assets/...` 均相对该目录。按需读取对应文件（决策树命中哪个读哪个，不要一次性全部读入）。

**模板拷贝**：页面模板（assets/sample）用 `e10-cli skill copy [目录]` 拷到工作区（默认当前目录，直接放出 `references/`、`actionflows/`、`assets/`）。

> **读 `references/...` 提示文件不存在** → 本机 skill 文档还没同步 → 先 `e10-cli skill sync`，或确认 skill 已装后重跑 `e10-cli auth status`。

> 文档版本 = CLI 版本（`e10-cli --version`）。升级 CLI 后跑一次 `skill sync`（或 auth status）即可带新文档。

## 核心理念

> **默认一份完整业务方案落在一个主应用。** 需求明确指定已有应用、跨应用资源或独立业务边界时，按实际范围处理，并在 `plan.md` 中标明每项资源的所属应用和跨应用关系。

```
一份完整业务方案 → 一个主应用（默认）
 └→ 应用下的资源: 表单 → 流程 → 菜单 → 页面
跨应用/已有应用增强 → 按实际边界规划并明确资源归属
```

接到需求不要一上来就写页面代码。先想清楚这一个应用下需要哪些表单、字段怎么设计、流程怎么走。

**能力范围**：应用与资源、表单与字段、视图与按钮、流程与动作流、设计器报表、权限、页面、数据操作，以及从接口文档批量创建 ESB 系统接口。具体能力、命令与限制以本页决策树路由到的 `_catalog.md` 和 `references/` 为准；规划时应一次覆盖需求中已明确的配置项，不因主文档未枚举某条命令而遗漏。

---

## 关于「流程表单 / 工作流程」（非默认路径）

流程体系分为 **EB 流程**和**原生工作流程**，两者的表单、资源 ID 与接口不可混用；公文流程是原生工作流程的特殊类型。固定/自由是各类流程的流转模式。

默认使用 **EB 表单**及应用内流程。只有需求明确要求原生流程表单、工作流程或流程中心建流程时，才切换到 `wf-form` / `workflow create-workflow` 路径。不确定且选择会改变资源归属时，再向用户确认。具体规则读取 `references/workflow/guide-workflow.md`；公文流程创建读取 `references/workflow/guide-workflow-odoc.md`，公文专属设置读取 `references/workflow/guide-workflow-odoc-setting.md`。
---

## 面向人群






- 本 skill 面向非编程人员。用户不懂技术，不会描述字段类型、数据关系。
- 你要主动引导，把模糊需求翻译成精确的平台资源设计。

### 工作流

```
0. 远程操作前确认环境
   a. 仅在即将执行远程查询或写入前运行 `e10-cli auth status`；纯文档、代码、日志分析及本地 CLI 修改不鉴权
   b. 同一连续执行阶段已确认当前环境时不重复检查；切换系统地址、profile 或凭证后必须重新确认
   c. 需要读取配套文档但 skill 目录内不存在 `references/` 时，执行 `e10-cli skill sync`
   d. 用户提到不同系统地址（如"在 xxx 搭建"）→ 必须切换鉴权：
      - 已有 profile（凭证已存）：e10-cli auth profile use <name>（直接切，无需重新登录）
      - 新环境：e10-cli auth set --eteamsid "<ETEAMSID>" --base-url <url>
        （ETEAMSID 从浏览器 DevTools → Application → Cookies 复制；浏览器 OIDC 登录暂未实现，不要用 auth login）

1. 判断需求复杂度
   ├─ 涉及 2+ 模块（应用/表单/流程/页面）→ 进入步骤 2
   └─ 简单单步操作（改字段、查数据）→ 直接执行

2. 全局资源设计（复杂需求必经）
   a. 理解需求，不够清楚的地方反问用户
   b. 写 plan 前扫描需求中的布局章节和表格。**每张表单建表前先向用户确认布局类型：流式(FLOW)还是表格式(EXCEL)**——平台建表后不可切换，需求没明说就不要默认。出现“表格式布局/Excel样式/按照如下布局”、`[字段名]`、标签与字段交替、分组标题或有意义的空白单元格时，按“布局样表”解析；识别方法读取 `references/form/guide-form-layout-planning.md`
   c. 在本地写 `plan.md`：**认真阅读用户提供的实施方案/需求文档** **严格按照 `references/common/guide-plan-template.md` 的模板格式，梳理所有需要搭建的资源和配置项**（应用/表单/字段/布局蓝图/流程/出口条件/联动/权限/编号/台账配置等编写`plan.md`，需求里提到的每项都要在 plan 中体现，不能凭记忆遗漏），禁止自创格式、禁止预勾。布局样表必须逐行写入对应表单的“表单布局蓝图”，不得仅压缩成 `group`、`singleRow` 或字段顺序
   d. **编写完成后打开 `plan.md` 和用户确认**（此阶段 plan 里所有 `[ ]` 保持未勾——是待办清单，不是完成清单）
   e. 用户确认后按大纲**逐项执行、逐项打勾**：每做完一项、验证通过，才把 `[ ]` 改 `[x]` 并填入实际 ID。**完成一条打勾一条**，禁止预勾。

3. 执行搭建（**最多分三段，每段完成停下来让用户确认，确认后才进下一段**）
   - 以用户确认的 `plan.md` 作为唯一执行清单，按照资源依赖顺序逐项读取对应指南并完成全部配置。每完成并核验一项，立即将对应 `[ ]` 更新为 `[x]`，同时回填实际资源 ID 或配置结果；未完成的项目不得预勾、合并销号或遗漏。进入下一执行段前，确认本段所有应完成项均已销号；依赖后续资源的项目继续保留 `[ ]` 并注明依赖。
   - **段①：应用、角色、表单与视图。** 完成应用、角色、全部表单和表单布局，并配齐字段属性、关联、公式、联动、校验、权限、默认台账、新增视图、显示列、搜索排序、筛选统计、分组、上下级、按钮和关联页签等表单及视图相关配置。依赖流程 ID 的配置在 plan 中列明，待段②创建流程后回填。
   - **段②：流程与自动化。** 完成流程创建、节点连线、操作者、出口条件、节点配置、流程级设置、矩阵和动作流，并回填段①中依赖流程 ID 的表单字段、表单按钮和视图按钮。完成后确认流程结构及关键条件。
   - **段③：菜单与页面。** 完成台账、流程发起和自定义菜单，配置菜单权限，并按需求创建配置式页面或定制页面，绑定真实资源 ID 后完成保存、发布和整体收尾。分段细节见 `references/common/guide-plan-template.md`「执行分段」。
   - 布局样表已进入 plan 时，据蓝图组织 `fields.json`，用现有 `form create --layout EXCEL` 创建并初始化；CLI 不消费蓝图本身。创建后仅在实际需要时读取当前布局并逐项调整，不生成额外布局 JSON、不改初始化逻辑。
   - 简单单步需求（改字段、查数据）不分段，直接执行。
```

**关键约束**：
- plan.md 强制按 `references/common/guide-plan-template.md` 格式写；规划阶段不调写命令、逐项销号、分段确认、字段一次性建好等规则见模板「规则备忘」
- 本服务运行于 Windows 环境，注意命令行兼容性
- 不要多说废话，直接干活。用户等的是结果。
- **写代码不要犹豫**，按模板直接出完整代码，写完用 `e10-cli check` 验证。错了报错再改。
- **解析 Word 文档**：用 `e10-cli docx read <文件>` 一键转 markdown + 提取图片，**禁止自己写 python-docx 脚本**。读取后必须逐张 Read `_images/` 目录里的图片做多模态理解，**把分析结果写回 md**（替换图片占位符为实际描述，让文档完整可读）。表格若承载表单布局，还要按布局样表规则保留空白、同排和分组关系；Markdown 无法确定合并范围时才查看原 DOCX 对应页面或表格结构。

---

## 决策树

> **根据用户需求自动加载对应子文档，不要一次性读取全部 reference。**
>
> **动作流两种用法**：动作流「生成」一律走 native `e10-cli actionflow generate`（语义 plan → 编译 → preflight → 保存并启用 → 正式回读，event 节点自带流程节点触发绑定，**推荐**）；`e10-cli workflow action` 仅作动作流管理（`list-node`/`clear-node` 查清节点绑定、`delete`/`disable`/`batch-delete` 禁用删除动作流 app）。本表字段赋值/节点附加操作（actionType=0）用 `e10-cli workflow save-action`。
> ```bash
> e10-cli actionflow component-list                          # 列已登记组件
> e10-cli actionflow component-describe <type>               # 读组件契约
> e10-cli actionflow generate '{"planFile":"@plan.json","appName":"AI-名称"}'  # 生成+保存并启用+正式回读；planFile 必须以 @ 引用文件（@plan.json 或 @绝对路径），CLI 强制要求 @ 前缀
> e10-cli workflow action list-node <wf> <node>             # 查节点绑定；clear-node 清；delete/disable 删动作流
> ```

| 用户关键词 | 加载文档 |
|-----------|---------|
| 写plan、搭建计划、plan.md、资源梳理、搭建模板、必做项清单 | `references/common/guide-plan-template.md` |
| 建应用、创建应用、app、应用列表、应用详情、应用目录、app read/list/folder/edit/delete | `references/common/ref-cli-commands.md` |
| 字段联动、跨表带出赋值、FormDataLinkage、多跳带出、关联客户带出客户类型、field-linkage、Text字段赋值名称 | `references/form/guide-field-linkage.md`（三种联动对比 + 单跳/多跳 + --hops 格式 + Text 字段必须多跳取名称） |
| 函数联动、本表字段间公式赋值、赋值式公式、EXCEL 公式联动、字段自动计算、form formula-linkage、wf-form formula-linkage、流程表单函数联动、触发事件、模块字段不能作目标 | `references/form/guide-formula-linkage.md`（四套联动对比 + 赋值式语法 + 触发事件表 + 模块字段 + 流程表单那条路由 + 常见报错） |
| 鉴权、登录、ETEAMSID、多环境、profile、切换环境 | `references/auth/guide-auth.md` |
| 表单数据读写、getSimpleData、withDisplayNames、getFieldOptions、saveFormData、updateFormData | `references/coding/guide-form-crud.md`（前端代码） |
| form data add、form data list、form data delete、写入数据、查询数据、删除数据 | `references/form/guide-form-data.md` |
| 编辑回显、handleEdit、getAllData、数据回填 | `references/coding/guide-edit-backfill.md`（前端代码） |
| 字段联动、显隐联动、条件显示、form linkage、为空/不为空条件、NULL 算子 | `references/form/guide-form-linkage.md` |
| 新建表单、form create、EB表单创建流程、fields.json | `references/form/guide-create-form.md`；确定具体字段参数时再读 `references/form/ref-form-fields.md` |
| 虚拟表、虚拟表单、绑定数据源、业务表展示、数据加工结果 | `references/form/guide-virtual-form.md`；字段类型按来源映射，不按普通字段重新猜测 |
| Excel样式、表格式布局、布局样表、布局蓝图、标签字段交替、合并单元格 | `references/form/guide-form-layout-planning.md` |
| 流程、审批、workflow、提交流程、预填 | `references/workflow/guide-workflow.md` |
| 流程绑了哪张表、流程对应表单、workflow info、从流程找表单 | 命令速查 `references/common/ref-cli-commands.md` 的 `workflow info` 一行（**流程列表接口不含这个信息**；拿到的是 formId，不是 objId） |
| 权责表、权责矩阵、权责表方式流程、分支场景、变量映射 | `references/workflow/guide-workflow-auth-resp.md`（操作者和条件同时遵循流程基础指南） |
| 公文流程、公文审批、收文、发文 | `references/workflow/guide-workflow-odoc.md`（基础节点/出口/操作者同时遵循 `guide-workflow.md`） |
| 公文设置、正文设置、痕迹、套红、排版、文号、附件区、归档、智能助手 | `references/workflow/guide-workflow-odoc-setting.md` |
| 流程节点、操作者、审批人、连线、添加节点、删除连线、删除节点、delete-node、节点操作者、set-operator、出口名称、link-rename、节点字段权限、field-permission | `references/workflow/guide-workflow.md` |
| 节点独立布局、节点换布局、node layout、节点用哪套布局、流程布局、流式/表格式布局、引用节点、updateQuoteNode | `references/workflow/guide-workflow-node-layout.md` |
| 节点校验、提交校验、node validate、智能审批规则、字面值校验、禁止提交 | `references/common/ref-cli-commands.md` |
| 分支条件、出口条件、条件JSON、save-condition、连线条件 | `references/workflow/guide-workflow-condition.md` |
| 动作流、跨表单、写入台账、ActionEbAdd/ActionEbUpdate/ActionEbDelete、提交事件、数据来源、requestId、按流程定位、回写数据ID、HTTP/HTTPS、DML/数仓、自定义事件、内置 MQ | `references/workflow/guide-workflow-action.md`（动作流生成走 `e10-cli actionflow generate`；`workflow action` 仅查/清/删/禁用；本表字段赋值走 `save-action`；复杂组件契约按需读取 `actionflows/SKILL.md` 及其 `references/components/`） |
| 菜单、导航、左侧菜单、系统页面、待办、已办、流程监控、菜单改名、重命名菜单 | `references/menu/system-menus.md` |
| 角色、角色管理、权限、成员 | `references/common/ref-cli-commands.md` |
| 新页面、导出、路由、entry.js、asyncImport | `references/coding/guide-page-export.md`（前端代码） |
| 写页面、页面代码、React编码、组件、entry.js模板 | `references/coding/guide-page-code.md`（前端代码） |
| CLI命令、打包、build、import、创建应用/表单/菜单 | `references/common/ref-cli-commands.md` |
| 编译报错、语法不支持、babel | `references/coding/ref-compile-rules.md`（前端代码） |
| Word文档、docx、需求文档、解析文档 | `e10-cli docx read` 一键转换，禁止自己写脚本 |
| 接口文档、Postman、系统接口、批量导入接口、创建连接器接口 | `references/esb-interface/guide-import.md`；使用 `e10-cli interface import` |
| 新建视图、表格视图、看板、日历、思维导图、form view、台账显示列、显示列、list-columns、搜索条件、排序、list-sort、上下级、父级、树形展示、上级类型、list-hierarchy | `references/form/guide-form-view.md` |
| 视图权限、查看布局、修改共享权限、view permission | `references/form/guide-form-view-permission.md` |
| EBuilder关联、关联表单、数据过滤设置、ebuilder-filter、EBuilder显示列、ebuilder-columns、去掉系统字段、只留业务字段 | `references/form/guide-ebuilder-filter.md` |
| 关联浏览筛选、数据范围设置、浏览数据定义、只选启用状态、关联客户过滤、ebuilder-scope | `references/form/guide-ebuilder-scope.md` |
| 字段分组、分组容器、字段分段、基本信息/合同信息分段、Collapse、Fold、字段归组 | `references/form/guide-form-layout-planning.md`（**按需**：用户明确要求字段分组才在 fields.json 写 `group`，默认不加分组） |
| 独占一行、整行显示、字段换行、singleRow、--single-row | `references/form/guide-form-layout-planning.md`（fields.json 字段写 `"singleRow":true`；add-field 用 `--single-row`） |
| 布局样式、样式模板、换配色、表单皮肤、layout init、style-template | `references/form/style-templates.md`（**⚠ 流式与表格式是两套独立模板，同名不同 id**，命令按布局类型实时查；缺省 流式=标准版、表格式=表格版） |
| 给已有表单加字段、改必填/只读、表单不是自己建的、--reinit、布局被重建、字段在布局里对不上、字段标题显示不出来 | `references/form/guide-form-layout-incremental.md`（**⚠ 不是自己建的表不要用 `--reinit`**；设必填是改布局组件，字段定义里没有 `required`） |
| 字段类型、字段码表、日期区间、关联浏览、关联订单、关联合同、Order、Contract、字段多选、multiple、--multiple | `references/form/ref-form-fields.md` |
| 表单复杂编号、serial-mark、流水号、年份编号、代字 | `references/form/guide-form-serial-mark.md` |
| 函数公式、字段公式、formula、DAYS、日期差、expressId、公式绑定 | `references/form/guide-form-formula-functions.md`（219 个函数速查矩阵，写 `fields.json` 的 `formula` 或 `form formula set --expression` 时查函数格式/示例；**日期差用 `DAYS(开始,结束)`**） |
| 显示列批量设置、批量加列、列宽、列顺序、list-columns --set | `references/form/guide-list-columns.md` |
| 顶部统计、明细统计、付款记录数、list-stats、子表计数 | `references/form/guide-list-stats.md` |
| 关联页签、关联视图、association、页签显示布局、关联数据筛选、set-filter | `references/form/guide-form-association.md` |
| 表单按钮、button、自定义按钮、视图按钮、行上、行末下拉、右上、打开视图、打开布局、发起流程、按钮预填、按钮字段映射、action-set | `references/form/guide-form-button.md`；`references/common/ref-cli-commands.md` |
| 表单权限、permission、数据权限 | `references/common/ref-cli-commands.md` |
| 消息提醒、消息动作流、workflow message、IM提醒 | `references/common/ref-cli-commands.md` |
| 编号规则、serial-mark、自动编号、流水号、年份编号、流程编号、numbering、停用编号、禁用编号、启用编号、解除编号 | `references/common/ref-cli-commands.md` |
| 超时处理、节点超时、超时提醒、node-overtime、node timeout | `references/common/ref-cli-commands.md` |
| 退回设置、退回方式、退回范围、node-reject、node reject | `references/common/ref-cli-commands.md` |
| 指定流转、开一窗流转、选择下一节点、node-assign-flow | `references/common/ref-cli-commands.md` |
| 投票、投票节点、通过率、一票否决、node vote | `references/common/ref-cli-commands.md` |
| 签署顺序、会签、非会签、竞签、或签、依次处理、抄送、operator-sign | `references/workflow/guide-workflow.md`；命令速查 `references/common/ref-cli-commands.md` |
| 机器人节点、等待节点、流程机器人、node-robot、处理间隔 | `references/common/ref-cli-commands.md` |
| 公用流转片段、流转片段、片段引用、segment、embed、权责表片段 | `references/common/ref-cli-commands.md` |
| 子流程、调用子流程、主子流程、字段映射、sub-process | `references/common/ref-cli-commands.md` |
| 人员范围、定时触发范围、plan-range、schedule-range | `references/common/ref-cli-commands.md` |
| 节点菜单、node menu、节点操作菜单 | `references/common/ref-cli-commands.md` |
| 流程设置、提交确认、签字意见、批量操作、setting | `references/common/ref-cli-commands.md` |
| 流程存档、定时触发、高级设置、advanced | `references/common/ref-cli-commands.md` |
| 编译、build、compile、代码质量检查、check、skill 文档、skill sync/copy/root | `references/common/ref-cli-commands.md` |
| 页面设计器、配置式页面、仪表盘、看板页、designer、page create、comp-add、工厂模板、factory、组件模板、页面布局、designer layout/save、页面版本、version revert、发布页面菜单、publish-menu、**自定义CSS、组件样式、改样式、选择器、DOM结构、样式不生效、designer css、designer dom** | `references/ebuilder-designer/guide-designer.md`（布局层）；组件配置见 `guide-designer-components.md`，**自定义 CSS 与 DOM 结构索引见 `guide-designer-css.md`**，工厂模板见 `guide-designer-factory.md`，版本见 `guide-designer-version.md`，命令速查见 `references/common/ref-cli-commands.md`「页面 & 设计器」节 |
| HRM、矩阵、条件矩阵、部门矩阵、分部矩阵、matrix、映射表、行 id、rowId | `references/hrm/guide-matrix.md` |
| 报表、设计器报表、EDC 报表、report build、新建报表、数据集、报表列、报表查询条件、报表权限、报表快照、report | `references/report/guide-report-build.md`（建表主干）；改已有报表见 `guide-report-modify.md`，查询条件见 `guide-report-query.md`，命令速查见 `ref-report-commands.md`；踩坑先扫 `ref-report-pitfalls.md` |
| 报表多数据源、跨数据集、跨表关联、主从报表、两个表单合成一张报表、父格筛选、subordination、leftFilterField、render 渲染回读 | `references/report/guide-report-multisource.md`（spec 写法 + 区域/入口格 + 双保存与关预聚合 + 验证） |
| 报表单元格、父格、扩展方向、合并、冻结、隐藏行、条件格式、数据条、图标集、tableName、字段三件套 | `references/report/ref-report-pitfalls.md` + `report-data-model.md`（枚举）· `layout-showlocation-freeze-guide.md`（冻结/居左）· `hidden-row-and-header-merge-guide.md`（空白行与表头合并） |

> 组件文档（Button/Table/Input/Upload 等）在 `references/` 中按文件名查找。完整索引见 `_catalog.md`。

> **表单自带默认台账** — 普通列表需求先查询并复用已有默认台账，记录实际名称/listId；“客户信息表／客户信息”这类简称差异不构成新建理由，默认保留原名，不统一去掉“表”字。仅名称需对齐时应改名而非另建。用户明确要求额外表格视图时，用 `form table-view create` 原子完成 `nListView` 创建、显示列配置和回读；禁止用 `form view create --type tableView` 创建空壳。`formView` 使用 `form view create` 后必须执行 `form view populate`。

---

## 平台架构

- **Ecode** — 存放和运行代码的平台，自定义页面在这里编码、构建、运行
- **Ebuilder 应用** — 独立的概念，包含表单、流程等元素（与 Ecode 项目不同）
- **默认台账与菜单入口是两件事** — 表单创建后会生成默认台账/列表视图，但当前 CLI 的 `form create` 默认不添加应用菜单；需求需要入口时使用 `--menu`，或建表后执行 `menu add-table`。不要因默认台账已存在而假定菜单入口也存在。只有图表仪表盘、跨表单聚合视图、特殊交互流程、对外公开页面等场景才需要自定义页面。
- 所有系统交互命令均通过 `e10-cli` 执行（已全局 link）。auth 文件自动查找，也可 `--auth <path>` 指定。
- 用户的 userId 是固定的变量 `TEAMS.currentUser.id`，系统里已支持，js 代码里可以直接写。

---

## 平台能力边界（禁止编造）

> **以下能力 CLI 不支持、平台也不支持，AI 禁止声称可以做、禁止输出操作步骤。**

| 不支持的能力 | 说明 |
|-------------|------|
| **H5/移动端菜单** | 移动端是独立体系（不同 URL + 不同 pageId），尚未整理，禁止编造 |

> 遇到用户要求以上不支持的能力时，必须明确告知"当前平台/CLI 不支持"，不要给出虚假操作步骤。

---

## 关键数据操作速查

### 表单数据 API

| API | 用途 | 返回内容 |
|-----|------|---------|
| `getSimpleData(objId, userId)` | 读 ID、写回 formToSave | 所有特殊字段统一返回 `fieldOptionId`（纯数字串） |
| `getAllData(objId, userId)` | 提取名称、编辑回显 | 含 `fieldOptionName`，mainTable key 是随机哈希 |
| `withDisplayNames(rows, map)` | 表格展示：ID → 名称 | 把 Select 的 `valueKey` 映射为中文名 |
| `getFieldOptions(fieldId, objId)` | 拿下拉选项 | `[{valueKey, name}]` |

### 不同字段类型，名称来源不同

| 字段类型 | getSimpleData 返回 | 展示时名称来源 |
|---------|-------------------|--------------|
| Text / Number / Date | `"值"` / `123` / `"2026-01-01"` | 直接展示 |
| Select / RadioBox / CheckBox | `"1283421826353889337"`（选项 ID） | `getFieldOptions` → `withDisplayNames` 映射 |
| **Employee** | `"2765550234448235905"`（用户 ID） | `getAllData` 的 `fieldOptionName`，**不是** getFieldOptions |
| **Department** | `"2765550234448235905"`（部门 ID） | 同上 |
| FileComponent | `"fileid1,fileid2"`（文件 ID 串） | 上传组件的 `name` |

> 完整数据读写指南见 `references/coding/guide-form-crud.md`（前端代码），编辑回显见 `references/coding/guide-edit-backfill.md`（前端代码）。

---

## 页面编码

> **页面是搭建流程的最后一步。** 写页面代码前，确保应用、表单、流程都已建好。

**应用内建页优先用设计器 Ebuilder 页面（配置式）**——`page create` → `designer comp-add --template`（28 个内置工厂模板）→ 绑数据 → `designer save` → `designer unlock` → `page publish-menu`，全程不写前端代码；详见 `references/ebuilder-designer/guide-designer.md`。**只有设计器组件无法满足的深度定制交互（特殊交互逻辑、复杂跨表联动 UI）才用 Ecode React 编码**。

页面编码规范、entry.js 模板、@weapp/ui 组件清单、编译规则、代码质量检查清单 → 详见 `references/coding/guide-page-code.md`（前端代码）。

---

## 快速参考

- 入口注册 + 新页面导出 → `references/coding/guide-page-export.md`（前端代码）
- 流程 URL 透传、预填 → `references/workflow/guide-workflow.md`
- 编译约束（var 声明、不支持的语法）→ `references/coding/ref-compile-rules.md`（前端代码）
- CLI 命令速查 → `references/common/ref-cli-commands.md`
- 组件完整索引 → `_catalog.md`
