# JSON 输出契约

## 什么时候读取

需要判断命令成功或失败、编写脚本封装、处理 stdout/stderr，或连续执行多个 Agent operation 时读取本文件。

## 成功 envelope

成功写入 stdout，退出码为 0：

```json
{
  "schemaVersion": 1,
  "ok": true,
  "operation": "invoice.list",
  "data": {},
  "meta": { "status": "COMPLETE" },
  "warnings": []
}
```

判断成功使用退出码 0 和 `ok === true`。不要用 `code === 0`，成功 envelope 没有顶层 `code/msg`。

## 失败 envelope

失败写入 stderr，退出码非 0：

```json
{
  "schemaVersion": 1,
  "ok": false,
  "error": {
    "type": "validation",
    "subtype": "input_invalid",
    "message": "必须提供 fid 或 number",
    "retryable": false
  }
}
```

错误判断优先看：

- `error.type`
- `error.subtype`
- `error.message`
- `error.retryable`
- `error.stage`
- 进程退出码

## 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `2` | 参数或业务输入错误 |
| `3` | 认证错误 |
| `4` | 网络错误 |
| `10` | 需要明确确认 |
| `11` | 部分完成或结果不确定 |

`retryable=true` 只表示读操作或准备阶段可能可以重试；写入请求已经发出后，遇到 `partial/write_uncertain` 必须停止并交给用户判断。

## JSON 输入兼容

简单 JSON 优先使用 `--input-json`，两端都可用，能避开 Windows PowerShell 对 `printf`、管道、转义和续行的差异：

Windows PowerShell：

```powershell
weaver-work-cli --json invoice run invoice.list --input-json '{"page_size":10,"start_pos":0}'
```

macOS/Linux（bash/zsh）：

```bash
weaver-work-cli --json invoice run invoice.list --input-json '{"page_size":10,"start_pos":0}'
```

复杂或多行 JSON 优先拆成简单参数并使用 `--input-json`；需要在同一个 shell 内连续调用时，把 stdout 保存在变量里传递。不要把上一步 CLI 的 stdout 重定向到临时文件，再用 `--input <path>` 喂给下一条命令。`--input <path>` 留给用户提供的 JSON 文件或明确需要文件的业务操作。

`--input <path>` 默认会告警但继续执行。可用 `--no-file-input` 或 `WEAVER_WORK_CLI_FILE_INPUT=deny` / config `io.fileInput=deny` 拒绝；需要临时放行时可传 `--allow-file-input`。`--input -`（stdin）和业务附件参数（如 `--file`）不受此策略影响。

Windows PowerShell 的多步传递示例：

```powershell
$cli = "weaver-work-cli"
$out = (& $cli --json invoice run invoice.list --input-json '{"page_size":200}') -join "`n"
if ($LASTEXITCODE -ne 0) { throw $out }
$refId = ($out | ConvertFrom-Json).refId
& $cli --json invoice run invoice.get --input-ref $refId --pick 'items[0].fid' --pick-as fid
```

macOS/Linux（bash/zsh）的多步传递示例：

```bash
out="$(weaver-work-cli --json invoice run invoice.list --input-json '{"page_size":200}')"
ref_id="$(node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>process.stdout.write(JSON.parse(s).refId||""))' <<<"$out")"
weaver-work-cli --json invoice run invoice.get --input-ref "$ref_id" --pick 'items[0].fid' --pick-as fid
```

`--pick` 选出一个对象时，会把该对象直接作为下一条命令的输入。选出单个值时，必须同时用 `--pick-as <字段名>` 指定输入字段，例如 `--pick items[0].fid --pick-as fid`。

Windows/PowerShell 下不要使用 `printf`、bash 反斜杠续行、`$HOME/...` 或 `~/...` 路径、`rm/ls/diff/python3` 等 Unix-only 写法；目录查看用 `Get-ChildItem`，删除用 `Remove-Item`，文件比对用 `Get-FileHash`，Python 启动器优先用 `py -3`。

## 大结果渲染与提效规则

当前 `weaver-work-cli` 输出层是轻量封装：JSON 模式对普通结果写完整 envelope，超预算结果会写入 CLI state 并返回摘要和 `refId`；文本模式写人类可读文本。CLI 不像飞书 CLI 已内置 `--format table/pretty/ndjson`、`--jq` 或通用 `--page-all`。Agent 仍需在调用和回复阶段主动控量，避免把超长接口响应原样渲染给用户。

### 调用前控量

- 列表类 operation 默认先取小页：优先 `page_size=10`，需要更多结果时再按用户目标递增，通常不要超过 `20`。
- 用户只想定位一个对象时，用筛选字段缩小范围；已有 `fid`、`number`、文件路径或 continuation 时直达对应 operation，不要先拉全量列表。
- 用户说“全部 / 全量 / 统计”时，先说明会分页读取；每页读取后只保留任务所需字段和去重键，避免在上下文里累计完整原始响应。
- 有 `hasMore`、`start_pos`、`page_token`、`next_page_token` 等分页字段时，用它们继续翻页；没有明确分页信号时不要无界循环。

### 回复时渲染

- 不要把完整 stdout JSON 直接粘给用户。优先输出结论、命中数量、关键字段、下一页/剩余数据提示和必要的文件路径。
- 列表结果只展示最相关的前 `10` 条；如果用户要求更多，分批展示并说明还可以继续读取。
- 详情结果只展示与用户问题相关的字段。发票类详情通常优先展示 `fid`、号码/代码、购销方、金额、日期、查验/报销状态和附件摘要。
- 大结果会由 CLI 暂存在用户级 state 目录，并返回 `refId`。后续操作用 `--input-ref <refId>` 和可选的 `--pick` / `--pick-as` 取所需数据；不要直接读取暂存文件，也不要用 `head` / `tail` 截取 JSON。
- 如果用户确实需要一个可交付文件，使用业务 operation 提供的下载/导出参数或用户指定的输出路径；不要把 CLI stdout 当成临时中转文件。
- 如果为了调试必须引用原始 envelope，只截取必要字段：`ok`、`operation`、`meta`、`warnings`、`error` 或 `data` 的相关子树。

### 参考飞书 CLI 的实践

- 飞书 CLI 用 `--format json` 保留机器可读 envelope，用 `pretty/table/ndjson/csv` 降低人读成本；本 CLI 目前主要依赖 `--json` envelope，因此 Agent 回复时承担 pretty/table 摘要职责。
- 飞书 CLI 的分页实践是显式页预算（如 `--page-limit`）和页间延迟；本 CLI 业务 operation 应使用自身 schema 中的 `page_size/start_pos` 等字段模拟同样的预算控制。
- 下载和导出产物属于用户文件，按用户指定路径交付；超长命令结果属于 CLI 暂存数据，使用 `refId` 传递并只展示必要摘要。
