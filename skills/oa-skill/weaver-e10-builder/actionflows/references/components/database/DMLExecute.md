# DML 操作（`DMLExecute`）

用于执行自定义 SQL 或存储过程。它不是 e-builder 表单数据操作；表单数据请使用 `ActionEbAdd`、`ActionEbUpdate`、`ActionEbDelete`。

## 组件约束

- 只支持新版数仓结构，`operateType` 固定为 `"0"`。
- `sqlContentDw` 必填，必须包含 `dataset.sqlQuery.sql` 和 `dataSetConn.id`。
- `dataSetConn.id` 应先通过 `e10-cli actionflow datasource-list` 查询当前环境的真实数据源连接；不要用其他环境的 ID。
- SQL 使用明文，参数占位符写成 `[${参数名}]` 或 `[ ${参数名} ]`。
- 每个占位符必须在 `fieldSet` 中有同名 `assignName`。`assign` 可直接使用统一动态赋值（固定值、上下文、系统变量、变量、常量、查询结果、函数/公式），也兼容平台原生 FormulaBean 数组。
- SQL 为空、占位符与 `fieldSet` 不匹配、结果集结构非法时，CLI 会在保存前拒绝生成。

## 最小计划

```json
{
  "type": "DMLExecute",
  "params": {
    "sqlContentDw": {
      "dataSetConn": { "id": "<当前环境真实数据源ID>" },
      "dataset": {
        "sqlQuery": {
          "sql": "update t_demo set name = [${name}] where id = [${id}]"
        }
      }
    },
    "fieldSet": [
      { "assignName": "id", "assign": { "kind": "context", "paramKey": "<真实字段paramKey>", "label": "数据ID" } },
      { "assignName": "name", "assign": { "kind": "variable", "id": "<真实变量ID>", "name": "名称变量" } }
    ]
  }
}
```

`dataset.module`、`dataset.type`、`sqlQuery.fields` 缺失时由 CLI 按平台结构补齐；存储过程的输出参数使用 `resultSets`。SQL 不能凭空编造，表名、字段、条件不明确时先确认，CLI 不查询数据库表结构。

平台保存 DML 时的 SQL 分析失败不一定阻止保存和启用，因此含 DML 的生成结果会额外回读 `analysisSql`。终端摘要中的 `sqlAnalysisOk` 必须为 `true`，否则只能说明动作流已保存，不能说明 SQL 可执行。
