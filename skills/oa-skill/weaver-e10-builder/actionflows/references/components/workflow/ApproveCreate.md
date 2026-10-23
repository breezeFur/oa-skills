# 新建流程（`ApproveCreate`）

## 何时使用

发起一个新的独立流程，不用于保存或提交已有流程。

## 先查询

查询目标流程、目标流程表单字段及发起人。

## 不可猜测

目标流程必须带真实表单字段；标题可固定、上下文或系统变量，映射目标字段不能猜。保存时按后端 `ApproveCreateDTO` 组织 `workflowPath`、`formData`、`operator`、`applicationId` 等字段；DTO 中的 `fields` 不参与新建流程保存，不能把它当成必填配置。

## 最小计划

`workflowPath`、`operator`、`requestName`；按需求补充表单赋值。`requestName`、`remark`、`odocId`、`dataId`、`secretLevel`、`secretLevelValidity` 均支持统一动态赋值；流程定义和退回节点仍必须使用真实 Browser/节点对象。
