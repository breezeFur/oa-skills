# 流程节点独立布局

> **命令**：`e10-cli workflow node layout list | get | bind | unbind | create`
> **同族功能**：`e10-cli workflow node field-permission`（节点字段权限）
> **相关**：`wf-form layout add` / `wf-form layout delete`（表单自己的多套布局）

流程表单可以有多套布局（每套是流式 FLOW 或表格式 EXCEL），默认那一套作用于所有节点。
**节点独立布局**是让某个节点单独挂另一套布局 —— 比如审批节点只显示审批相关字段、
归档节点全只读且换成表格式。

```
表单默认布局 ──┬── 节点：发起报销申请
（FLOW）       ├── 节点：报销初审
               └── …
PC1 布局 ──────┬── 节点：财务部专项复核     ← 独立布局
（EXCEL）      └── 节点：流程归档
```

---

## 一、三条硬规则

1. **一个节点同时只属于一套布局。** 把节点从 A 挪到 B，服务端会自动把它从 A 摘掉，不会两套都留着。
2. **摘掉后回落到表单默认布局**（该节点 `layoutId` 置空），不是「没有布局」。
3. **PC 端与移动端是两套独立的关系。** 移动端另有「独立布局 / 读取PC端布局」的模式开关，
   `--terminal MOBILE` 操作的是另一份映射，互不影响。

> ⚠️ **布局类型（流式/表格式）在新建布局时就要定死**，建完不能切换。这是 `form create --layout` 同一类约束。

---

## 二、命令

```bash
# 这个工作流有哪些布局，每套被哪些节点引用
e10-cli workflow node layout list <workflowId> [--terminal PC|MOBILE]

# 某个节点挂的是哪套
e10-cli workflow node layout get <workflowId> <nodeId>

# 把节点挂到某套布局（自动从原来那套摘掉）
e10-cli workflow node layout bind <workflowId> <nodeId> --layout-id <布局ID> [--terminal PC]

# 摘下来，回落表单默认布局
e10-cli workflow node layout unbind <workflowId> <nodeId> [--terminal PC]

# 新建一套布局：默认**复制表单默认布局**（推荐），可同时挂上若干节点
e10-cli workflow node layout create <workflowId> --name "项目费用报销流程表PC2" \
    --layout-type EXCEL --nodes <nodeId1> <nodeId2> [--describe "…"]

# 从指定布局复制
e10-cli workflow node layout create <workflowId> --name "…" --from <来源布局ID>

# 建空白布局（字段与排版全部从零配，慎用）
e10-cli workflow node layout create <workflowId> --name "…" --empty

# 建完立刻排版；只摆指定字段（审批节点常见诉求）
e10-cli workflow node layout create <workflowId> --name "审批专用PC" --init     --fields 报销单号 报销金额 关联客户

# 对已有布局重排（只动这一套）
e10-cli workflow node layout init <workflowId> <布局ID> [--fields …]

# 先看看这张表单有哪些字段可摆
e10-cli workflow node layout init <workflowId> x --list-fields
```

`bind` / `unbind` **幂等**：节点本来就在目标状态时不发写请求，重复执行安全。

### `create` 的两种模式：复制 vs 空白

| 模式 | 触发 | 结果 |
|---|---|---|
| **复制**（默认） | 不写 `--empty`；默认复制**表单默认布局**，可用 `--from <布局ID>` 换来源 | 内容与来源一致，拿到手就能微调 |
| **空白** | `--empty` | 字段与排版都是空的，全都要重新配 |

同一份默认布局下的对比（内容体积）：来源 28,941 / 复制出来 28,980 / **空白只有 5,622**。
空白布局挂到节点上，该节点打开时**几乎什么都没有** —— 除非确实要从零设计，否则用默认的复制模式。

`--layout-type` 不写时**跟随来源布局的类型**（复制表格式布局就还是表格式），显式传则覆盖。
平台设计器上的「新建」按钮走的是空白那条分支。

### 只摆指定字段

`--init --fields A B C` 会让这套布局**只放这三个字段**。

**没摆的字段只是在这套布局里不显示，字段本身仍在表单上**，其它布局照旧 —— 已回读核对：
过滤后目标布局 3 个组件，表单默认布局仍是完整的 17 个，一个没少。

不传 `--fields` 就是把这套布局按全部字段重排。

```bash
# 审批节点：只看单号/金额/客户
e10-cli workflow node layout create <workflowId> --name "审批专用PC" --init     --fields 报销单号 报销金额 关联客户

# 事后改主意，重排成别的字段组合
e10-cli workflow node layout init <workflowId> <布局ID> --fields 报销单号 报销人
```

字段名写错会**直接报错并列出可用字段**，不会闷头建出一套空布局。
`--list-fields` 可以先看清单。

删除布局用 `wf-form layout delete <formId> <layoutId>`。

---

## 三、典型用法

**给审批节点换一套只看关键字段的布局**

```bash
# 1. 先建布局（表格式），建完在设计器里把需要的字段排好
e10-cli workflow node layout create <workflowId> --name "审批专用PC" --layout-type EXCEL

# 2. 从列表里拿到新布局的 ID
e10-cli workflow node layout list <workflowId>

# 3. 把审批节点挂上去
e10-cli workflow node layout bind <workflowId> <nodeId> --layout-id <新布局ID>

# 4. 核对
e10-cli workflow node layout get <workflowId> <nodeId>
```

**改回默认**

```bash
e10-cli workflow node layout unbind <workflowId> <nodeId>
```

---

## 四、接口（排查用）

| 用途 | 接口 |
|---|---|
| 布局列表 | `POST /api/ebuilder/flow/form/layout/list` → `data.formLayoutMultiplePage.result[]` |
| 每套布局 ← 哪些节点 | `GET /api/bs/workflow/pathdef/pathLayoutManage/getLayoutInfoParams?terminalType&workflowId` → `formId` + `layoutReferNodeInfo` |
| 节点 → 哪套布局 | `GET /api/bs/workflow/pathdef/nodeLayout/getDisplayLayoutForm?workflowId&nodeId` → `layoutId`/`defaultLayoutId`/`mLayoutId`/`mLayoutMode` |
| 绑定 / 解绑 | `POST /api/bs/workflow/pathdef/form/layout/updateQuoteNode` |
| 新建布局 | `POST /api/ebuilder/flow/form/layout/save` |
| 布局内容 | `POST /api/ebuilder/form/builder/getFormLayout`（带 `layoutMultiId`；不传读默认） |

**新建布局的 `sourceId` 决定复制还是空白**：不传 `sourceId` 时服务端建出的是空壳，传了才按 `copyConfig` 复制。
`copyConfig` 四项全开才是完整复制（`{formDataLinkage, excelLinkage, viewLinkage, displayFormat}`）——
少 `viewLinkage` / `displayFormat` 时复制出来的布局会缺视图关联与显示格式，体积只有完整复制的五分之一左右。

**`updateQuoteNode` 是整集合覆盖，不是增量追加**：

```json
{ "terminal": "PC", "workflowId": "…", "layoutId": "…",
  "nodeIds": ["变更后该布局引用的全部节点"],
  "sourceNodeIds": ["变更前的全部节点"] }
```

所以 CLI 的 `bind` 是「先读现状 → 加上这个节点 → 整包提交」。**不要**直接拿单个节点当 `nodeIds` 提交，
否则该布局上原有的其它节点会被摘掉。

**重建布局必须走 ebuilder 路径**：`initLayout` 用 `/api/ebuilder/form/form/view/relate/initLayout`
（`module:"ebuilderform"`）。流程表单那套 `/api/workflow/core/form/...` 在 **eb 表关联流程**的表单上会直接
回「无工作流修改权限或工作流维护权限」500，用不了 —— `wf-form layout init` 因此对这类表单不可用。

**「只摆某些字段」的实现**：`getConfig` 恒返回表单**全量**字段的 configs（与布局无关），
过滤掉不要的再 `initLayout`，就是「这套布局只显示这些字段」。系统字段的 config 项保留（不会变成组件）。

**节点布局面板的完整定义**在 `getDisplayLayoutForm.displayLayoutForm` 里（`groups` / `layout` / `items`），
`items.layoutId.browserBean` 描述了 PC 端布局选择器（`module:"workflow/core"`, `type:"nodeLayoutBrowser"`,
参数 `{formId, terminal, workflowId}`）；`items.mLayoutMode` 是移动端那个 radio（`0`=独立布局 / `1`=读取PC端布局）。
要确认面板上还有哪些可配项，读它比翻文档准。

---

## 五、与本文件其它节点的关系

| 功能 | 命令 | 说明 |
|---|---|---|
| 节点字段权限 | `workflow node field-permission` | 控制字段在节点上 显示/只读/必填 |
| 节点操作菜单 | `workflow node menu` | 节点上显示哪些操作按钮 |
| **节点独立布局** | `workflow node layout` | 节点上换一整套排版 |

节点布局与字段权限是**叠加**的：布局管「字段怎么排」，字段权限管「字段能不能改」。
两者都挂在同一条节点表单关联记录上，互不覆盖，可以同时用。
