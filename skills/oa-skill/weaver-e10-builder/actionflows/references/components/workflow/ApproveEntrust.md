# 委托流程（`ApproveEntrust`）

## 何时使用

将某人的流程委托给另一人代办。

## 先查询

查询操作人、委托人、受托人，并由预检读取该委托人的真实可用身份。

## 不可猜测

`identityId` 必须由当前租户返回；不能根据名称推断身份或范围。

两张设置表必须使用平台固定业务键（如 `entrustUserId`、`consigneeId`、`entrustType`、`approveId`）保存；预检返回的字段实例 ID 只能用于识别字段，不能作为 `setting.main` 的键，否则设计器会显示为空。

## 最小计划

`operator`、`entrustUser`、`consignee`、`identityId`、`entrustType`。
