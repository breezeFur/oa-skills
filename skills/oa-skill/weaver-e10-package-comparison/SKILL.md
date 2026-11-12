---
name: weaver-e10-package-comparison
display_name: 泛微E10离线包功能比对
display_name_en: Weaver E10 Package Comparison
description: 离线对比新旧迁出包，生成业务功能差异、明细差异、风险验证点及可视化报告。
description_zh: 离线对比新旧迁出包，生成业务功能差异、明细差异、风险验证点及可视化报告。
description_en: Compares Weaver E10 offline packages and generates business differences, detailed changes, risk validation points, and visual reports.
version: 1.2.0
author: 泛微网络科技股份有限公司
agent_created: true
slug: weaver-e10-package-comparison
displayName: 泛微E10离线包功能比对
summary: 离线对比新旧迁出包，生成业务功能差异、明细差异、风险验证点及可视化报告。
license: MIT
---

# 泛微E10离线包功能比对

完全离线、独立对比两个同类型的泛微 E10/eBuilder 迁出 ZIP。公开版 1.2.0 同步 V15.6：每个 ZIP 只完整解析一次并复用 canonical IR，新旧包解析及两版全景重建确定性并行；流程模式进一步还原属性联动、字段联动和函数联动。不要连接数据库、网络、源码工程、外部插件或其他 Skill，不执行迁入，也不调用任何 E10 在线服务，无需登录态或会话凭证。

## 输入与方向

- 接收两个存在的 ZIP，递归解析外层及嵌套 ZIP 中的 `profile.json`、`KEYS_*.idm` 和业务记录。
- 用户明确指定旧包、新包时严格保持方向。
- 用户未指定方向时，只按两个包最外层唯一且可解析的 `profile.json.exportTime` 判断；无法唯一判断时停止并请用户明确方向。
- 不得根据文件名、大小、修改时间或名称中的数字推断方向。
- 两个包的最外层 `profile.json.ietype` 必须一致：`ebuilder` 进入应用模式，`workflow` 进入流程模式；冲突、缺失或类型不同则停止。
- 批量包只在同一顶层应用单元内匹配，禁止跨顶层单元合并同名对象。

## 执行

Agent 先检查可启动的 Python 3.10+（Windows 可使用 `py -3`、真实 `python` 或宿主解释器绝对路径）。缺少或版本不足时，直接通过当前系统已有的官方包管理器安装/更新 Python 并验证，准备成功后继续本轮比对，不要求用户手动装工具。解析和比对阶段仍完全离线；脚本只依赖 Python 标准库，无需 pip 包或在线 OA CLI。用户明确限制网络时使用已有离线解释器或安装包，缺少离线来源时说明阻断。

选择不存在或为空的输出目录，默认运行：

```bash
python3 scripts/run_compact_comparison.py \
  --old "/path/to/old.zip" \
  --new "/path/to/new.zip" \
  --output "/path/to/new-output"
```

未指定方向时运行：

```bash
python3 scripts/run_compact_comparison.py \
  --package "/path/to/package-a.zip" \
  --package "/path/to/package-b.zip" \
  --output "/path/to/new-output"
```

脚本使用 Python 标准库完成解析、同源匹配、差异计算、应用全景或 Workflow IR 重建、风险与验证点生成、报告渲染和内部校验。只有全部门禁通过后，才把三份客户报告复制到正式输出目录；临时证据与日志自动清理。

## 同源与差异规则

- 以 `KEYS_*.idm` 中 camelCase `sourceId` 作为记录级跨环境同源首要证据；要求当前记录可解析且两侧唯一。
- `importId`、`exportId` 只用于解析当前记录和关系，冲突、缺失、一对多或证据不足时不得强配。
- `profile.json` 的同源字段只作应用或模块层佐证与回退。
- 保守抑制缺字段与显式空值、名称时间戳、迁移 `_V长编号` 别名、同内容共享明细重建及仅引用解析形态变化。
- 保留可观察的真实业务变化，包括字段前后值、结构、菜单打开配置、动作流启停、节点类型、流程版本、表单与布局变化。
- 流程模式还原属性联动的条件、显示效果与适用范围，字段联动的触发字段与数据来源，以及函数联动的触发字段与客户可读计算公式；变化流程还应展示当前联动能力概览。
- 不得用无证据的“节点参数变化”“配置发生变化”等模糊结论兜底。

## 输出

正式目录必须恰好包含三份非空报告。

应用模式：

- `应用版本功能差异报告.md`
- `应用版本功能差异可视化.html`
- `应用版本功能明细差异报告.md`

流程模式：

- `流程版本功能差异报告.md`
- `流程版本功能差异可视化.html`
- `流程版本功能明细差异报告.md`

主报告面向客户说明业务功能变化、影响、风险和验证步骤；明细报告展示对象及配置前后值；HTML 必须是无 CDN、无网络依赖的单文件离线可视化。不得在客户报告中泄露原始服务端地址、密码、Token、私钥、数据库流水或大段技术 JSON。

## 结论边界

- 只证明离线包静态差异与包内证据，不证明迁入成功、目标环境可运行或数据库状态正确。
- 无法确认的包外资源和跨服务绑定标为未知，不描述为确定故障。
- 仅基于迁出 ZIP 内的静态文件（`profile.json`、`KEYS_*.idm`、业务记录等）做解析，不向任何服务端发起 HTTP 请求，无接口调用，不依赖登录态或会话凭证。
- 返回新旧方向、业务变化统计、重点验证结论、三份报告路径及上述边界。
