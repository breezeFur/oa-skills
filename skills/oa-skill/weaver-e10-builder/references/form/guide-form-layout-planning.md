# EB 表单布局规划

本指南用于从需求文档识别 FLOW/EXCEL 布局，并将布局要求完整写入 plan 和 `fields.json`。表单创建顺序见 [新建 EBuilder 表单](guide-create-form.md)。

## 确认布局类型

- `FLOW`：流式布局。
- `EXCEL`：表格式布局。
- 使用 `form create --layout FLOW|EXCEL` 在创建时指定。
- 需求未明确且选择会改变最终布局时，建表前向用户确认。

## 识别布局样表

识别发生在读取需求文档之后、编写 `plan.md` 之前。先整理字段定义，再扫描布局章节和表格。

出现以下特征时，将表格作为布局样表：

- 上下文说明“表格式布局”“Excel 样式”或“按照如下布局”；
- 单元格包含 `[字段名]`，或呈现标签与字段控件交替结构；
- 存在表单标题、分组标题、合并单元格、有意义的空白位置；
- 表格表达字段摆放位置，而不是重复列出字段名称、类型和说明。

逐行识别表单标题、分组标题、字段标签、字段控件、空白占位、同排字段、合并和跨列关系，以及必填、只读、独占一行等显示属性。优先使用 `e10-cli docx read` 生成的 Markdown 表格；合并区域不清晰时查看原 DOCX 中对应表格结构。

## 写入 Plan

识别结果分别写入同一表单的两个部分：

1. “字段定义”：保存字段类型和可以直接创建的属性。
2. “表单布局蓝图”：逐行保存标题、分组、字段同排关系、顺序、空白占位、跨列信息和原文说明。

```markdown
##### 表单布局蓝图

| 行 | 区域/分组 | 左侧 | 右侧 | 布局说明 |
|---|---|---|---|---|
| 1 | 标题 | 项目信息表 | — | 合并整行 |
| 2 | 基本信息 | 项目名称 | 项目编号 | 同排两列 |
| 3 | 基本信息 | 项目简介 | — | 独占整行 |
```

轻量核对原样表中的每个字段，确保同时出现在字段定义和布局蓝图中，并保留同排关系和分组顺序。

## 转换为 fields.json

- 数组顺序表示字段展示顺序。
- `group` 表示需求明确的分组。
- `singleRow:true` 表示独占一行。
- `required:true`、`readOnly:true`、`hidden:true` 表示显示属性。

```json
[
  {"componentKey":"Text","fieldName":"项目名称","group":"基本信息","required":true},
  {"componentKey":"Text","fieldName":"项目编号","group":"基本信息","readOnly":true},
  {"componentKey":"TextArea","fieldName":"项目简介","group":"基本信息","singleRow":true}
]
```

只有需求明确要求分组时才设置 `group`；需求未要求时保持不分组。

## 创建与局部调整

```bash
e10-cli form create <appId> "<表单名>" --fields @fields.json --layout EXCEL
e10-cli form layout read <objId>
```

创建后需要调整局部位置或显示属性时，使用 `form layout` 下的移动、只读和必填设置命令；具体参数通过 `form layout --help` 查询。
