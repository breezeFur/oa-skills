# 新建表单数据（`ActionEbAdd`）

## 何时使用

向指定 e-builder 表单新增一条或一批数据；已有数据要修改时改用 `ActionEbUpdate`。

## 选择项跨表映射

来源、目标选择字段的选项 ID 经当前租户字段元数据确认一致时，直接 `mapping` 动态赋值；批量新增会生成“依据值下级”（`switchType:"sub"`），这是任务明细字段的默认做法。需求指定固定选项时，不做动态映射；在 `constants` 中传该字段的真实 `valueKey`（可同时带 `label`），例如 `"<任务类型字段id>":{"kind":"fixed","value":"<研发的valueKey>","label":"研发"}`。CLI 会保留目标字段 `Select` 类型，使设计器以下拉项“研发”回显。只有两边选项 ID 不同、且需求明确要求按语义转换时，才在 `formula`（批量明细为 `detail[].formula`）中用 `SWITCH` 显式映射：

```json
{
  "<目标选择字段id>": {
    "kind": "function",
    "name": "SWITCH",
    "args": [
      {"kind":"context","paramKey":"<来源选择字段paramKey>","label":"来源类型"},
      {"kind":"fixed","value":"<来源选项id1>"}, {"kind":"fixed","value":"<目标选项id1>"},
      {"kind":"fixed","value":"<来源选项id2>"}, {"kind":"fixed","value":"<目标选项id2>"},
      {"kind":"fixed","value":"<默认目标选项id>"}
    ]
  }
}
```

批量新增时，普通 `mapping` 的 `明细表[].字段` 仍编译为 type=10 的“依据值下级”引用。函数参数则是另一套协议：它会明确引用 `明细表[0].字段`，不会把整张明细数组传入函数。

## 先查询

查询目标应用、表单、全量字段及创建人。明细赋值还须查询明细字段。

## 不可猜测

`targetForm`、人员和字段 ID 必须来自当前租户。动态来源只能使用本次触发器的真实 `paramKey`。

`params.setting` 不是前端回读的 `EsbFormDataDto`。语义计划中不要直接复制前端的 `setting.main/detail`；主表使用 `mapping`、`constants`、`formula` 或旧格式赋值数组，明细使用 `detail` 语义项。CLI 会把这些语义项编译为后端 `EbuilderActionDTO.setting`，其核心结构是：

```json
{
  "main": {
    "<目标主表字段ID>": {
      "formFieldKey": "",
      "value": {
        "assign": "<FormulaBean>",
        "fieldType": "<目标字段componentKey/type>",
        "switchType": "assign|fixvalue|sub",
        "assignType": "",
        "multiSelect": false
      }
    }
  },
  "detail": [
    {
      "detailTableId": "<目标明细表ID>",
      "basisValue": "<来源明细表 FormulaBean>",
      "data": { "<目标明细字段ID>": { "formFieldKey": "", "value": { "assign": "<FormulaBean>" } } },
      "deleteFields": []
    }
  ],
  "dataDrWithCalc": false,
  "deleteMainFields": []
}
```

赋值值可以是固定值、上下文、动作流变量、租户常量或函数/公式；变量/常量必须先按 `references/dynamic_resources.md` 使用真实 ID 或顶层定义解析，不能把名称直接当作固定文本。

## 最小计划

`targetForm`、`person`，以及至少一项 `mapping`、`constants`、`formula` 或 `setting`。`setting` 仅表示旧格式赋值数组，不表示上述平台 DTO。

操作人选择：需求明确指定某人时才传该人的真实 Browser 对象并显示为固定值；需求未指定时传 `{"type":"role"}`，生成当前人 `{userid}` 动态值。不得为了补必填项从人员列表任意挑一个人。

`opType:"batchInsert"` 时，`basisValue` 与 `mapping` 都是必填：前者指定要逐行遍历的上游明细，后者指定每行写入哪些目标字段。两者任一缺失，CLI 会在创建动作流前停止，绝不保存空壳批量节点。

若流程触发器上下文中存在 `requestId`，而目标表恰有唯一一个未赋值的流程关联 Browser 字段（如“来源流程”或“关联流程”），CLI 会把它自动映射为当前流程实例 ID，并在结果的 `autoMappings` 中列出。显式映射、固定值、公式和旧 `setting` 始终优先，不会被覆盖；字段不唯一或类型不是流程关联字段时不猜测。

### 明细表规则

新增明细时，前端 `DetailForm` 以 `basisValue` 决定新增行数；没有依据值时会清空动态赋值。因此只要 `detail` 中配置了 `mapping`、`constants` 或 `formula`，就必须同时提供真实的 `basisValue`，通常写成上游明细列表字段并带 `[]`。CLI 不接受没有依据值的明细字段映射。

`ActionEbAdd` 的 `ActionEbDlg` 未开启明细操作策略选择器，明细策略固定为新增。`detail` 不接受 `operateType`、`updateType`、`updateFieldCondition`、`updatePolicy` 或 `rowId`；这些字段会被 CLI 拒绝，明细更新/删除应改用 `ActionEbUpdate`（删除全部等特殊场景也不要伪造为新增）。编译结果不会写入前端不存在的 `operateType:"insert"`，只保存 `detailTableId`、`basisValue`、`data` 和 `deleteFields`。

新增组件的 `person` 按前端结构保存为 type=8 容器，容器内再放当前用户 type=9 或固定人员 type=1 的子 FormulaBean；CLI 会自动补齐该容器。

## 动态来源选择与查询结果引用

- AI 应按需求和已生成上游节点的真实上下文选择来源：流程触发字段、前序动作输出、当次循环、系统变量、固定值或查询结果均可；**不得默认把所有映射绑定到流程触发，也不得默认插入查询节点**。
- 仅当业务需要从另一张表反查、且结果可确定为单条时，才使用 `EnquiryForm` 查询 + 主表字段 `query_result` 引用（手工创建成功样本：`actionflows/references/examples/enquiry-form-batch-insert-scene2.json`）。
  - EnquiryForm 在前，ActionEbAdd 的 sources 指向 EnquiryForm 节点；主表字段 assign `type=3`，`value="FormData.{查询表id}[{positionId}].id"`，`config.comType="EnquiryForm"`、`comId=EnquiryForm 节点 id`、`paramKey="{查询表id}[].id"`，childs 带固定值取下标 `[{type:"1", value:"0", position}]`。
  - 细节见 `EnquiryForm.md`「批量新增主表字段引用查询结果」。
- AI 选择查询结果时，plan 显式写 `kind:"query_result"`、`source:"<查询节点ref>"`、`formId`、`fieldId`、`index:0`；未选择时使用普通 `context`、`fixed`、`system_variable` 或函数树，不产生查询结果公式。`kind:"enquiry"` 与 `sourceId` 不是合法格式，CLI 必须拒绝，不能生成空固定值。

## 函数公式赋值（type=6）

- **plan 写法**：顶层 `formula: {目标字段id: <函数树>}`；函数调用为 `{kind:'function', name:'DATEDIFF', args:[...]}`，args 可为 `{kind:'context', paramKey, label, fieldType}` / `{kind:'fixed', value}` / 嵌套 `{kind:'function'}`。四则运算也写为函数树，禁止 `op + fields` 的旧格式。
- **保存结构**：assign `type=6`，`value="{fnId}#{child.position}#..."`；`childs` 按参数槽位 `position` 串联，且 `detail[i].position` 必须与第 i 个 child 的 `position` 完全相同。`position` 与子公式 `id` 都是数字但不能混用：缺任一处会让设计器只显示根运算符（如 `(*)`），不显示参数。函数内部 `formulaType/config.paramType` 使用函数目录的 `resultType`（如 `double`），目标字段 `NumberComponent` 只写在外层 setting。内层函数同样 type=6 嵌套，叶子上下文 type=3 / 固定值 type=1。
- **函数类别与 excelFunc**：`functionType` 必须原样使用函数目录的 `category`（如四则运算为 `operation`、日期函数为 `date`），不能用结果类型 `double` 代替。仅当函数目录实际返回 `excelFunc` 对象时才透传；没有就省略，尤其不能给 `×/÷/+/-` 伪造通用 `excelFunc`，否则编辑器会丢失运算符。禁止写字符串（如 `'mul'`）。
- **函数来源与参数契约**：除 `custom`（自定义 JS）和 `code`（编码函数）外，标准函数名称、类别与**每个函数自身的完整参数契约**均内置在 Skill/CLI。参数不得泛化为 `param1/param2`：必须保留真实 `paramName`、`paramType`、`isRequire`、说明和枚举选项；例如 `DATEDIFF` 固定为 `startdate/enddate/datepart`。plan 只写函数名及实参；仅当计划实际使用函数时，CLI 才调用当前租户接口校验该函数可用并替换不可迁移的函数 ID，同时保留该租户的完整参数定义。接口不参与未使用函数的生成，也不决定标准函数是否受支持；当前租户缺少所用函数时明确停止。
- 枚举函数参数的固定值必须从对应 `detail.paramSelectDetail` 选择；CLI 按选项的 `value` 写入真实值，并按该参数 detail 的 `paramType` 生成子 FormulaBean，不允许自定义参数类型或写入不存在的下拉值。示例：`DATEDIFF({date}, 预计完成日期, "天数") × 8` 中“天数”应匹配到 `{name:'天数',value:'dy'}`，最终写入 `value:'dy'`；首次用于新租户时仍应保存并回读确认。
- **函数引用明细行字段**：函数参数若来自流程明细表，仍传真实 `paramKey:"<流程id>.<明细表id>[].<字段id>"`，但必须按手工编辑器的真实结构编译为 `type:3` 上下文引用，不能使用 `type:10/sub`，也不能使用 `mainBasis`。`value` 必须为 `FormData.<流程id>.<明细表id>[<索引子节点position>].<字段id>`；同时挂一个 `type:1`、`name/value:"0"` 的索引子节点，`[]` 内填写该子节点的 `position`。`config` 保留逻辑 `paramKey`（其中仍是 `[]`）、`fieldInfo.tablePrimaryKey:"FormData"`、`parentName:"<流程名>.<明细表名>[].<字段名>"` 和同样使用逻辑 `[]` 路径的 `multTypeObj`。缺少索引子节点时，编辑器会只显示红色字段名，丢失“流程触发 → 明细表[0] → 字段”的上下文链。
