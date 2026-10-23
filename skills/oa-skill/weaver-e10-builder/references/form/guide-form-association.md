# 关联页签：目标视图、显示布局与数据筛选

在来源表单的记录页面上新增关联页签，打开已有目标视图，并将当前记录字段作为筛选参数传入。例如：客户信息表 → “全部合同”页签 → 合同信息表的“全部合同”视图。

## 配置前查询

```bash
e10-cli form association list <objId> <appId>
e10-cli form association views <objId> <appId>
e10-cli form association fields <objId> <appId> --view <viewId>
e10-cli --json form association get <objId> <appId> <associationId>
```

- `objId` 是放置页签的来源表单，不是目标视图所属表单。
- `views` 返回目标视图 ID、名称、所属表单。名称重复时必须传 ID。
- `fields` 分别返回来源字段 `source` 与目标字段 `target`。不要把两端字段 ID 混用。
- 跨应用通过 `--target-app <appId>` 显式选择，命令验证目标应用菜单树和视图实际归属。
- `get --json` 的正确写法是全局 `--json`（如上），保留原始权限配置，并额外提供解析后的权限条件 `rules`。

## 创建关联页签

```bash
e10-cli form association create <objId> <appId> "全部合同" --view <viewId> --layouts 显示 --terminals PC MOBILE --permissions @association-permissions.json --mappings @association-mappings.json
```

创建时必须明确权限。方案要求所有人可见时，`association-permissions.json` 可写：

```json
[
  {
    "selectedType": "all",
    "dataid": "0",
    "levelScope": {"minShowlevel": "", "maxShowlevel": ""},
    "condition": {"rootdata": ""}
  }
]
```

不要在方案没有要求时默认采用所有人权限。其他组织、角色等权限按平台实际配置提供完整数组；本命令不推断权限对象。

筛选映射文件格式：

```json
[
  {"targetField": "关联客户", "sourceField": "客户名称"}
]
```

每项含义为“目标视图字段 ← 当前来源记录字段”。支持字段 ID 或唯一显示名称，自动补全 `compType/fieldName/dataIndex` 等元数据。仅支持主表字段到主表字段的映射；明细字段及固定值筛选不在本次支持范围。

上例样本中的配置，不代表所有关联字段都应传名称。目标 EBuilder 字段可能需要记录 ID：应按业务语义选择 `sourceField: "数据ID"` 或指定字段，并用实际记录确认筛选结果。命令不会擅自把用户提供的名称字段改成 ID。

默认启用，默认适用于 PC 和 MOBILE，默认仅显示布局。省略 `--mappings` 表示不添加关联参数；目标视图自身的筛选仍独立生效。创建检测同名页签，重复时停止，改用 `update`。

## 显示布局与其他设置

| 参数 | 含义 |
|---|---|
| `--layouts 显示` | `showLayout="0"`：显示布局 |
| `--layouts 新建` | `showLayout="1"`：新建布局 |
| `--layouts 编辑` | `showLayout="2"`：仅编辑布局 |
| `--layouts 显示 新建 编辑` | `showLayout="0,1,2"`：三种布局都显示 |
| `--layouts none` | 三种布局均不显示 |
| `--terminals PC MOBILE` | 两端适用；可只传其中一个 |
| `--enabled true/false` | 启用或停用页签 |

```bash
e10-cli form association update <objId> <appId> <associationId> --layouts 显示
e10-cli form association update <objId> <appId> <associationId> --name "相关合同" --terminals PC --enabled true
e10-cli form association update <objId> <appId> <associationId> --view <newViewId> --mappings @association-mappings.json
```

`update` 保留未指定属性以及原动作、权限条件和提示。布局、终端参数表示替换对应集合。修改绑定视图且已有映射时必须显式提供新映射（`[]` 可清空），避免原目标表字段被用于新视图。

仅启用或停用页签时，`update --enabled true|false` 使用 `updateIsOpenById` 独立接口并通过列表回读状态，不整包保存关联配置。

## 修改和清空关联数据筛选

```bash
e10-cli form association set-filter <objId> <appId> <associationId> --mappings @association-mappings.json
e10-cli form association clear-filter <objId> <appId> <associationId>
```

设置会替换目标动作的全部筛选映射。存在多个视图动作时，用 `--action <actionId>` 明确选择；只修改该动作，其余动作保留。

这里处理的是 `associationActions[].url` 内的 `params`（`nameType/type=FORMFIELDS`），不会修改目标视图的全局过滤，也不会修改页签的权限条件。

## 权限条件是另一项能力

```bash
e10-cli form association set-condition <objId> <appId> <associationId> --perm 1 --rules @permission-rules.json --logic or
e10-cli form association clear-condition <objId> <appId> <associationId> --perm 1
```

这两条操作 `associationPermissions[].condition.rootdata`，规则格式为 `[{"fieldId":"...","func":"contains","value":"..."}]`。`--perm` 为 1 开始的序号或 `selectedType`；支持 `and/or`。此条件按来源表单字段生成，与“目标视图数据筛选映射”分别配置。

平台权限条件读回是明文 JSON，写入需 LZW 压缩。更新布局或数据筛选时也会重新压缩原有权限条件；不要自行传入压缩字符串。

## 验证与计划

保存后回读目标视图、筛选映射、显示布局、终端、动作和权限相关配置，成功输出 `verified: true`。创建响应可能不带顶层 ID，命令通过列表差集和详情确定新关联 ID。若提示已提交但无法匹配，先 `list/get`，不要直接再次创建。

配置回读不等于验证了浏览器展示或实际筛选结果。验收还应打开来源记录的显示/编辑布局，检查页签显示范围，并用已知关联与非关联记录检查目标视图结果。

在计划模板 3.3 中逐项填写：

- 关联页签：来源表单/objId、页签名称/associationId、目标应用/表单/视图 ID、权限依据。
- 布局与终端：显示布局是否开启、编辑布局是否开启、PC/MOBILE、启用状态。
- 数据筛选：每条目标字段 ← 来源字段，注明传记录 ID 还是字段值，以及配置回读和实际结果验收情况。

先创建目标视图，再创建依赖它的关联页签；关联 ID、视图 ID、动作 ID 不能互换。未验证的项保留待办，不预先打勾。
