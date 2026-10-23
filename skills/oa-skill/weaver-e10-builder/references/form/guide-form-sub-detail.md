# 二级明细表配置

二级明细表配置在父明细表上。父明细的每一行分别拥有一组子明细数据；新增子明细数据时，平台把对应父行的行标识自动写入子级行标识字段，用于维持归属关系。

## 结构规则

- 一个父明细可以关联多个子明细。
- 同一个子明细可以被多个父明细复用。
- 明细关系可以继续向下嵌套，例如 A → B → C。
- 当前明细不能选择自身、直属父级或任一祖先作为子明细。通过候选列表选择目标即可。
- 调换父子方向时，先删除原关系，再重新查询新父明细的候选列表并建立反向关系。例如将 `A → B` 改为 `B → A`，依次执行：删除 `A → B`、查询 B 的候选列表、新增 `B → A`。
- 父级行标识支持行 ID、单行文本 `Text`、单选框 `RadioBox`、下拉单选框 `Select`，没有明确要求时使用行 ID。
- 子级行标识必须使用单行文本 `Text`。

## 创建时配置

先定义全部明细表，再把 `enableSubDetail` 和 `subDetailConfig` 写在父明细表上：

```json
[
  {
    "componentKey": "DetailTable",
    "fieldName": "任务明细",
    "enableSubDetail": true,
    "defaultExpandRow": true,
    "subDetailConfig": [
      {"subForm": "工时明细", "subField": "父任务标识"}
    ],
    "formFields": [
      {"componentKey": "Text", "fieldName": "任务名称"}
    ]
  },
  {
    "componentKey": "DetailTable",
    "fieldName": "工时明细",
    "formFields": [
      {"componentKey": "Text", "fieldName": "父任务标识"},
      {"componentKey": "Number", "fieldName": "工时", "precision": 2}
    ]
  }
]
```

缺省父级行标识为 `rowId`。需要使用父明细字段时，在关系中增加 `parentField`，可传字段名或字段 ID：

```json
{"subForm":"工时明细","subField":"父任务标识","parentField":"任务编码"}
```

## 已有表单维护

先查询父明细当前可选的子明细，再配置关系：

```shell
e10-cli form detail-table sub-detail candidates <objId> <appId> <父明细>
e10-cli form detail-table sub-detail add <objId> <appId> <父明细> --target <子明细> --target-field <子级文本标识>
```

常用命令：

| 操作 | 命令 |
| --- | --- |
| 查询全部明细表 | `form detail-table list <objId> <appId>` |
| 查询某父明细当前配置 | `form detail-table read <objId> <appId> <父明细>` |
| 查询可选子明细 | `form detail-table sub-detail candidates <objId> <appId> <父明细>` |
| 增加或更新一条关系 | `form detail-table sub-detail add ... --target <子明细> --target-field <子级标识> [--parent-field <父级标识>]` |
| 完整替换关系 | `form detail-table sub-detail set ... --target <子明细> --target-field <子级标识> [--parent-field <父级标识>]` |
| 删除一条关系 | `form detail-table sub-detail remove ... --target <子明细>` |
| 启用或停用 | `form detail-table sub-detail enable\|disable ...` |
| 清空全部关系 | `form detail-table sub-detail clear ...` |

`add` 保留父明细已有的其他子明细关系；`set` 完整替换父明细的关系配置。删除最后一条关系后，二级明细功能随之关闭。`disable` 仅停用并保留关系，后续可用 `enable` 恢复。

## 执行顺序

1. 创建父、子明细表及字段。
2. 确认子明细存在可用的 `Text` 行标识字段。
3. 使用 `candidates` 查询当前父明细可选目标。
4. 使用 `add` 或 `set` 保存关系；未指定父级字段时使用 `rowId`。
5. 使用 `read` 回读父明细的 `enableSubDetail`、`defaultExpandRow` 和 `subDetailConfig`。

关系方向发生变化时，先对原父明细执行 `remove`，再按第 3～5 步以新的父明细重新配置。
