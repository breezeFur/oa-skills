# 表单查看视图权限

“修改视图权限”指修改表单数据权限中的 PC 查看布局 `layoutId`。可选布局必须来自权限查询响应的 `rightList.layoutMap`；数据列表 `NList` 不属于此处的查看布局。

## 命令

```bash
# 查询可授权布局和 dataRightList
e10-cli form view-permission list <objId> <appId>

# 新增人员查看权限并绑定布局
e10-cli form view-permission grant <objId> <appId> <viewId> \
  --org-type employee --org-id <employeeId> --org-name "<name>"

# 新增所有人查看权限
e10-cli form view-permission grant <objId> <appId> <viewId> --org-type all

# 把既有 dataRight 权限切换到另一个 PC 查看布局
e10-cli form view-permission set <objId> <appId> <rightId> <viewId>
```

`rightId` 必须来自 `view-permission list` 的 `dataRights`，不能使用创建权限或导入导出权限 ID。`viewId` 必须存在于同次查询的 `layoutMap`。

## 安全替换

接口事实没有独立更新端点，`set` 固定执行：

1. 查询并锁定原 `rightId` 和目标 `viewId`。
2. 深拷贝接口允许的权限字段，替换 `layoutId`，不复制原 `id`、租户和创建信息。
3. 调用 `addRight` 新建替代权限并独立回读。
4. 只有替代权限按新 ID、新布局回读成功后，才调用 `deleteRight` 删除旧权限。
5. 再次查询，确认旧 ID 消失、新 ID 保留。

禁止先删旧权限。若删除旧权限失败，命令会报告新权限 ID 并保留两条权限，便于人工恢复。

## 验收

服务器必须返回 `persisted=true`。前端在表单“共享权限/数据权限”中应看到同一授权主体仍存在，但其 PC 查看布局已变为目标视图；实际打开数据时应使用该布局。
