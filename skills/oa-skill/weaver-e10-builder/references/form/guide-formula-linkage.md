# 函数联动（本表字段间的公式赋值）指南

## 概述

函数联动：在**本表单内部**，当某个字段变化（或表单载入）时，用一张**公式**算出结果，赋值给本表的另一个字段。

例：`数量` 或 `单价` 变化时 → `销售金额 = 数量 × 单价`。

设计器里的位置是字段属性面板的「函数联动」，要配四件事：**在哪生效**（当前表单 / 某个布局）、**什么时候触发**（事件）、**谁触发**（触发字段）、**赋值给谁 + 怎么算**（目标字段 + 函数体）。

> **不跨表。** 要查另一张表把值带回来，那是 `form field-linkage`（跨表带出），见 `guide-field-linkage.md`。

## 四套联动对比

| | 属性联动（显隐） | 关联表带出 | **字段联动（跨表带出）** | **函数联动（本表赋值）** |
|---|---|---|---|---|
| 命令 | `form linkage add` | `form relate` | `form field-linkage add` | `form formula-linkage add` |
| 取值靠 | — | HRM 源 | ESB 动作流（查另一张表） | **一张公式** |
| `linkageType` | （另一套存储） | — | `template` | `excel` |
| 做的事 | 改字段显示属性 | 换 Employee/Department→带 HRM 属性 | 查任意表→带出字段赋值 | **本表字段→算→赋给本表字段** |
| 跨表 | 否 | 否 | **是** | 否 |

四者可以叠加：同一个字段既可以有显隐联动，也可以被函数联动赋值。

## 赋值式：公式长什么样

落库的 `expressSql` 是一条**赋值式**，左边是目标字段、右边是函数体：

```
{主表.销售金额}=VALUE({主表.数量})*VALUE({主表.单价})
```

CLI 的 `--expression` **只给右边**就行，左边的 `{主表.<目标>}=` 会自动拼上。

从设计器里整段复制也行 —— 如果表达式里已经有赋值式，CLI 会校验它的左侧与 `--target` 是否指向同一字段：一致就沿用，不一致就**报错中止**（不会偷偷改目标）。

> ⚠ **一个等号是赋值，两个等号才是比较 —— 两个层次别写反。**
> - **顶层**那个 `=` 是「赋给谁」：`{主表.销售金额}=…`。**一个等号**。
> - **函数体内部**做判断要用 `==`：`IF({主表.状态}=="已完成", 1, 0)`。**两个等号**。
>
> 函数体里写成单个 `=` 不报错，只是按赋值语义走、算出来不对。另：**函数名必须大写**（自定义 JS 脚本函数除外）、**跨表粘贴的公式要把 `{主表.X}`/`{明细表.X}` 逐个换成本表字段**、**选项型控件要比就得引用选项本身**（`{主表.性别}=={主表.性别.男}`，写成 `=='男'` 恒不成立）—— 合看 `guide-form-formula-functions.md` 的「写公式前先记住这几条」。

### 字段引用的两种写法

| 写法 | 场景 |
|---|---|
| `{主表.字段名}` / `{明细表名.字段名}` | 平台存储格式，整段复制来的就是这种 |
| `[字段名]` / `[表名.字段名]` | 设计器编辑器里的显示格式 |

两种都收，保存前统一归一化成花括号再下发（原样发方括号会静默失效，见 `guide-form-formula-functions.md`）。

**函数体里不要出现裸方括号** —— 解析器把任何 `[...]` 都当字段引用，`SUBSTR("a[1]",…)` 这种会被当成找不到的字段。

## 模块字段（系统字段）

`{主表.主表数据id}`、`{主表.当前日期}`、`{主表.操作者部门}` 这类是**系统模块字段**，可以出现在公式右边，也能当触发字段，但**不能作为赋值目标**。

原因很直白：平台在公式的 `extendParam.unSupportTargets` 里把这 21 个字段列成了「不可赋值」，而 CLI 就用这份清单做判据 —— 传了模块字段当 `--target` 会当场报错，不会建出一条平台不认的规则。

两种写法都能用：

```
{主表.主表数据id}      ← 裸标签，平台存储格式
[formDataId]          ← 语义键，等价；归一化后仍写成裸标签
```

`form formula-linkage columns` 会把两桶分开列：业务字段（可作目标）+ 系统模块字段（不可作目标）。

## CLI 命令

```bash
# 看有哪些事件可选（值改变时 / 载入时 / 创建数据时 …）
e10-cli form formula-linkage events <appId> <objId>

# 看有哪些字段可用（业务字段 / 系统模块字段分两桶）
e10-cli form formula-linkage columns <appId> <objId>
e10-cli form formula-linkage columns <appId> <objId> --keyword 金额

# 列出/回读（read 带公式表达式与参数）
e10-cli form formula-linkage list <appId> <objId>
e10-cli form formula-linkage read <appId> <objId> <linkageId>

# 新增
e10-cli form formula-linkage add <appId> <objId> \
  --event changeField \
  --trigger 数量 --trigger 单价 \
  --target 销售金额 \
  --expression "VALUE({主表.数量})*VALUE({主表.单价})"

# 改（只传要改的；--event/--trigger 不传就沿用现有的）
e10-cli form formula-linkage update <appId> <objId> <linkageId> --trigger 产品类别
e10-cli form formula-linkage update <appId> <objId> <linkageId> --state off
e10-cli form formula-linkage update <appId> <objId> <linkageId> --name "重算金额"

# 删除（批量）
e10-cli form formula-linkage delete <appId> <objId> <linkageId...>
```

### add 的参数

| 参数 | 说明 |
|---|---|
| `--target <字段>` | **赋值目标**，被写入的字段。只能是业务字段 |
| `--expression <函数体>` | 公式右侧。含引号/换行时可用 `@文件路径` |
| `--event <事件>` | 触发事件，默认 `changeField`（值改变时）。可传 `type` 或中文名 |
| `--trigger <字段...>` | 触发字段，可多个。字段级事件必填；表单级事件（如「载入时」）不用给 |
| `--effect <维度>` | 生效维度：`form`（默认，当前表单）/ `formLayout`（表单布局） |
| `--name <名>` | 联动名。默认 `<公式名> - 公式_<时间戳>` |
| `--formula-name <名>` | 公式名，默认取表单名 |
| `--formula-id <id>` | 复用/更新已有公式，不新建 |

### 生效维度（`--effect`）

| 维度 | `--effect` | 生效范围 |
|---|---|---|
| 当前表单（默认） | 不传 或 `form` | 该表单的**所有布局**，以及所有关联了该表单的工作流 |
| 表单布局 | `formLayout` | **只对选定的那一个布局** |

```bash
# 只在这个布局上生效
e10-cli form formula-linkage add <appId> <objId> --effect formLayout \
  --event changeField --trigger 数量 --target 销售金额 \
  --expression "VALUE({主表.数量})"
```

> ⚠ 布局 id 取的是 `getFormLayout` 返回的 **`multipleLayoutId`**，不是 `formLayout.id` —— 同一张表上这两个值相邻但不同（如 `…375` / `…376`），**发错不报错，只是指向另一个布局**，回读时生效范围会是个空白。CLI 走的是与显隐联动同一套解析（`resolveEffect`），不用手填 id。

### 触发事件

| 分组 | 事件 | type | 要触发字段 |
|---|---|---|---|
| 字段 | 值改变时 / 获取输入焦点时 / 失去输入焦点时 / 鼠标单击时 / 鼠标双击时 | `changeField` / `onfocus` / `onblur` / `onclick` / `ondbclick` | 要 |
| 表单 | 载入时 / 载入时(可编辑) / 载入时(新建) / 创建数据时 / 窗口滚动时 | `onLoadForm` / `onLoadFormEdit` / `onLoadFormCreate` / `createData` / `onscroll` | 不要 |

## 示例

### 金额 = 数量 × 单价（两个触发字段）

```bash
e10-cli form formula-linkage add <appId> <objId> \
  --event changeField --trigger 数量 --trigger 单价 \
  --target 销售金额 \
  --expression "VALUE({主表.数量})*VALUE({主表.单价})"
```

### 编号 = 数据ID + 订单号（引用系统模块字段）

```bash
e10-cli form formula-linkage add <appId> <objId> \
  --event onLoadFormCreate \
  --target 订单编号 \
  --expression 'CONCAT({主表.主表数据id},{主表.订单编号})'
```

### 载入时赋当前日期（表单级事件，不给 --trigger）

```bash
e10-cli form formula-linkage add <appId> <objId> \
  --event onLoadForm --target 登记日期 --expression '{主表.当前日期}'
```

## 注意事项

> 公式**语言本身**的硬规则（函数名必须大写 / 比较用 `==` / 赋值用 `=` / 跨表粘贴要换字段变量）在 `guide-form-formula-functions.md` 的「写公式前先记住这四条」，写表达式前先过一遍 —— 这几条写错**不报错**，只是算不对。

1. **目标只能是业务字段**。系统模块字段（`主表数据id`/`当前日期`/`操作者部门` 等 21 个）不能作 `--target`，但可以出现在公式右边、也可以当触发字段。
2. **一个触发字段一条触发动作**。`--trigger` 传多个时，平台侧是 N 条动作记录，不是一条里挂 N 个字段 —— CLI 已按这个形状下发。
3. **触发字段与目标不能搞反**。`--trigger` 是「谁变了」，`--target` 是「谁被写」。写反了规则会反向生效，回读时表达式左边能看到真实目标。
4. **字段名有歧义会报错**，不会默认取第一条。两张明细表里各有一个「编号」时，写 `编号` 会列出两个候选，改用字段 id 或 `明细表名.编号`。
5. **业务字段与模块字段同名时**（如业务字段叫「标题」、模块字段 `name` 的标签也叫「标题」），按裸标签写会报歧义，用字段 id 或完整列名 `主表.标题` 区分。
6. **生效范围两种**：缺省「当前表单」（所有布局 + 所有关联该表单的工作流），`--effect formLayout` 则只对某个布局生效。布局 id 由 CLI 现查（见上「生效维度」）。`update` 不传 `--effect` 会沿用现有维度。
7. **改了公式不会同步 `inFields`/`outFields`**。平台的数据源上带这两组字段（公式用到的来源字段 / 被赋值的字段），它们反映的是**建这条联动时**的公式；后来改公式它们不跟着变。这不影响运行，但别拿它当「当前公式用了哪些字段」的依据 —— 用 `form formula-linkage read` 看表达式。
8. **`form field-linkage` 看不见这类联动**。两者 `linkageType` 不同（`excel` vs `template`），各查各的。`form field-linkage list` 末尾会提示「另有 N 条函数联动」；`form field-linkage delete` 传函数联动的 id 会直接报错指路，不会静默删 0 条。

## 流程表单上的函数联动（`wf-form formula-linkage`）

流程表单也支持函数联动，是**同一能力的另一条路由**。命令面与 eb 表逐字对齐，只有位置参数和多出来的选项不同：

```bash
wf-form formula-linkage list   <formId> --workflow-id <id>
wf-form formula-linkage read   <formId> --workflow-id <id> <linkageId>
wf-form formula-linkage events <formId> --workflow-id <id>
wf-form formula-linkage columns<formId> --workflow-id <id>
wf-form formula-linkage add    <formId> --workflow-id <id> --target <字段> --expression <函数体> [...]
wf-form formula-linkage update <formId> --workflow-id <id> <linkageId> [...]
wf-form formula-linkage delete <formId> --workflow-id <id> <linkageIds...>
```

`--workflow-id` 一个旗标管两件事：**`refId`**（这条联动挂在流程上）+「当前工作流 / 选择节点」两个维度的取值来源。不给就按 `formId` 兜底（查不到时先补上它）。流程 ID 用 `workflow search --name <流程名>` 拿。

### 两条路由的差异

| | eb 表 `form formula-linkage` | **流程表单 `wf-form formula-linkage`** |
|---|---|---|
| 位置参数 | `<appId> <objId>` | **`<formId>`** + `--workflow-id` |
| 联动端点 | `/api/ebuilder/form/form/linkage` | `/api/ebuilder/flow/form/linkage`（**不带 `?apid=`**） |
| `module` | `ebuilderform` | **`ebuildercard`** |
| 定位入参 | `customParam: {appId, objId}` | **顶层 `refId` = workflowId**；`customParam: {scene:'workflow'}` |
| 公式参数里的 `appId` | 有 | **没有这个键** |
| 不可作赋值目标的系统字段 | 21 项 | **30 项**（模块字段桶是 32 —— 差的两个见下） |
| 触发事件 | 10 个（字段组 5 + 表单组 5） | **17 个**（多一组「流程」事件） |
| 生效维度 | 当前表单 / 表单布局 | 当前表单 / 表单布局 / **当前工作流 / 选择节点** |

### 多出来的「流程」触发事件

除了字段组的 5 个与表单组的 5 个，流程表单还多 7 个流程级事件（都不需要 `--trigger`）：

```
EVENT_SUBMIT_OR_AGREE  提交/批准时      EVENT_REJECT        退回时
EVENT_FORWARD          转发时          EVENT_TURNTODO      转办时
EVENT_SAVE_DATA        保存时          EVENT_REMARKADVICE  意见征询时
                                      EVENT_CIRCULATE     传阅时
```

### 生效维度的四种取值

```bash
--effect form          # 默认。当前表单
--effect formLayout    # 表单布局（--layout-id 可指定，不传取默认布局）
--effect workFlow      # 当前工作流，必须给 --workflow-id
--effect includeNode   # 选择节点，必须给 --workflow-id 与 --node
```

「选择节点」的 `--node` 可以给节点 id 或节点名。「当前工作流」的选项名是 `流程名【V活动版本号】`，版本号取活动版本 —— 与设计器发出的形状一致。

### 系统字段里有两个**可以**当赋值目标

流程表单的模块字段桶有 32 项，但平台标「不可赋值」的只有 30 项，差的是：

```
REQ_REQUEST_NAME   流程标题
REQUEST_LEVEL      紧急程度
```

这两个**可以**作 `--target`。`columns` 命令会按「可作 / 不可作赋值目标」分桶列出，别拿「是不是系统字段」去判断。

### 流程表单这条路由读不出字段时

`wf-form` 的多数命令靠 `getFormLayout` + `getConfig` 读字段，但**部分流程表单上 `getFormLayout` 会直接 500**（`Form.isPhysicalTable()` 上 NPE）。函数联动**不受影响** —— 它的字段清单直接取 `findFormDrivingColumns`（这条路由自己给的），没走 `getConfig`。所以 `wf-form read` 读不出来的表单，`wf-form formula-linkage columns` 照样能列出字段。

## 常见报错

| 报错 | 原因 | 怎么办 |
|---|---|---|
| 系统模块字段「X」不能作为赋值目标 | `--target` 写了模块字段 | 换成业务字段；模块字段只能出现在公式右边 |
| 「X」在…上匹配到 N 个字段 | 字段名有歧义 | 用字段 id（`form formula-linkage columns` 里）
| 表达式里写的是一个赋值式，它的左侧是「A」，与 --target「B」不一致 | 粘贴的赋值式目标与 `--target` 不符 | 改 `--target`，或只给右侧函数体 |
| 事件「载入时」不需要触发字段 | 表单级事件给了 `--trigger` | 去掉 `--trigger`（CLI 会忽略并提示） |
| 事件「值改变时」需要指定触发字段 | 字段级事件没给 `--trigger` | 补 `--trigger` |
| 平台回读的表达式与提交不一致 | 归一化猜错了写法 | 以平台为准；把 `read` 的结果记下来反馈 |
