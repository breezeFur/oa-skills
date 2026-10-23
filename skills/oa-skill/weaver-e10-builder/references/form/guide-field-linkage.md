# 字段联动（跨表带出赋值）指南

## 概述

字段联动（FormDataLinkage）：表单字段值改变时，自动查询**另一张表**（按数据ID=触发字段值过滤），把查到的字段值**带出赋值**到本表单字段。支持单跳（一次直接带出）和多跳链式（多次中转后带出）。

背后是一个 ESB FieldLinkage 动作流（触发 + N 个 EnquiryForm 查询 + Output 赋值），CLI 自动完成建 ESB app + saveDesign + 绑定。

## 三种联动对比

| | 属性联动（显隐） | 关联表带出（form relate） | **字段联动（field-linkage）** |
|---|---|---|---|
| 命令 | `form linkage add` | `form relate` | `form field-linkage add` |
| 接口 | viewlinkage | ffRelateField module:hrm | saveFormDataLinkage + saveDesign（ESB） |
| 作用 | 改字段显示属性（hide/show/required） | 换 Employee/Department→带 HRM 属性 | **查任意表→带出任意字段赋值** |
| 源 | 表单字段值条件 | Employee/Department（HRM 源） | 任意字段→任意表查询 |
| 复杂度 | 简单 | 简单（单源单属性） | 复杂（跨表多跳，ESB 动作流） |
| 关系 | — | — | **字段联动是关联表带出的进阶版** |

> 本文讲的是**跨表**带出。本表字段之间用公式互相计算赋值的是**函数联动**（eb 表 `form formula-linkage`、流程表单 `wf-form formula-linkage`），见 `guide-formula-linkage.md` —— 两者 `linkageType` 不同（`excel` vs `template`），`form field-linkage list/delete` 看不到也删不掉函数联动。

## 何时用多跳

**Text 字段赋值必须用名称（多跳），不能直接赋 ID。**

| 场景 | 跳数 | 示例 |
|------|------|------|
| 带出字段是 EBuilder（存 ID）→ 目标也是 EBuilder | 单跳 | 关联合同→查合同信息表→带出关联客户（ID→EBuilder 字段） |
| 带出字段存 ID → 目标是 Text（要名称） | **多跳** | 关联客户→查客户信息表→客户类型(ID)→查客户类型表→类型名称(Text)→填 Text 字段 |

**判断原则**：目标字段是 EBuilder/Select（存 ID）→ 单跳即可；目标字段是 Text（要展示名称）→ 必须多跳到名称表取名称。

## CLI 命令

```bash
# 列出
e10-cli form field-linkage list <appId> <objId>

# 回读单条
e10-cli form field-linkage read <appId> <objId> <linkageId>

# 查源表可带出字段
e10-cli form field-linkage fields <appId> <formId>

# 删除（批量）
e10-cli form field-linkage delete <appId> <objId> <linkageId...>
```

### 新增（add）

**单跳**（一次直接带出）：
```bash
e10-cli form field-linkage add <appId> <objId> \
  --trigger <触发字段名> \
  --source-form <目标表objId> \
  --query-field <目标表带出字段名> \
  --target <本表目标字段名>
```

**多跳**（多次中转后带出）：
```bash
e10-cli form field-linkage add <appId> <objId> \
  --trigger <触发字段名> \
  --target <本表目标字段名> \
  --hops "<源表objId:带出字段名,源表objId:带出字段名,...>"
```

`--hops` 格式：每跳 `objId:字段名`，逗号分隔。前一跳的带出值 = 下一跳的过滤值（数据ID=前一跳结果）。最后一跳的带出值赋给 `--target`。

## 配置示例

### 示例1：单跳——关联合同→合同信息表→关联客户

```
关联合同(EBuilder→合同信息表) 值改变
→ 查合同信息表 by 数据ID=关联合同
→ 带出关联客户(EBuilder→客户信息表，存ID)
→ 赋值到本表.关联客户(EBuilder字段，存ID)
```

```bash
e10-cli form field-linkage add <appId> <objId> \
  --trigger 关联合同 --source-form <合同信息表objId> --query-field 关联客户 --target 关联客户
```

### 示例2：多跳——关联客户→客户信息表→客户类型→客户类型表→类型名称→填Text

```
关联客户(EBuilder→客户信息表) 值改变
→ Step1: 查客户信息表 by 数据ID=关联客户 → 带出客户类型(EBuilder→客户类型表，存ID)
→ Step2: 查客户类型表 by 数据ID=客户类型(Step1结果) → 带出类型名称(Text)
→ 赋值到本表.客户类型(Text字段，要名称不要ID)
```

```bash
e10-cli form field-linkage add <appId> <objId> \
  --trigger 关联客户 --target 客户类型 \
  --hops "<客户信息表objId>:客户类型,<客户类型表objId>:类型名称"
```

### 示例3：链式联动（两条独立 linkage 串联）

关联合同→(linkage1)→关联客户→(linkage2)→客户类型→(linkage3)→类型名称

每条 linkage 的 `--trigger` 是上一条的 `--target`。分开 `add` 多次即可。

## 查源表字段

```bash
# 查某表单有哪些可带出字段
e10-cli form field-linkage fields <appId> <formId>
```

或用 `e10-cli form read <objId> --app-id <appId>` 取字段 fieldId（配置 --hops 时需知道字段名）。

## 注意事项

1. **Text 字段必须多跳取名称**：目标字段是 Text → 带出值必须是名称（文本），不能是 ID。如果源表存的是 ID（EBuilder/Select），需多跳到名称表取名称。
2. **orgId 必须正确**：CLI 自动从 getForm 取 orgId，传给 application/save 建 ESB app。没有 orgId 的 app 不完整，saveDesign 会 500。
3. **多跳 EnquiryForm 需要 sources**：非首跳的查询动作必须有 `sources` 指向前一跳，否则服务器报"有两个起始执行组件"（CLI 已处理）。
4. **FormData 引用格式**：触发字段 `FormData.<本表formId>.<触发字段id>`；查询结果 `FormData.<源表objId>[].field_<带出字段id>`。
5. **--hops 的 objId 是表单 objId**（不是 formId）。CLI 内部自动解析 objId→formId。
6. **联动名称**：不传 `--name` 时自动生成 `<本表名>.<触发字段>→<最后源表名>.<最后带出字段>`。
