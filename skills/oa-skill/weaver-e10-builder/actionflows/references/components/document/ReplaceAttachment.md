# 替换附件（`ReplaceAttachment`）

## 何时使用

以新附件替换旧附件并升版。

## 先查询

查询新旧附件来源和操作人。

## 不可猜测

这是独立组件，不能用 `DocumentEdit` 伪装；两个附件都必须真实存在。

## 最小计划

`resourceFileId`、`targetFileId`、`employeeId`。
