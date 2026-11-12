---
name: node-write
description: 使用 Node.js 读取、创建和改写 UTF-8 文本，保留 BOM/换行并检查覆盖基线；处理 DGS（有时写作 DSG）受控源码或文本时验证实际运行时、同目录同后缀写入和独立密文视角。支持内存/stdin 与 .txt 暂存；Windows 缺少 Node 时自动安装官方 LTS 便携版。
---

# Node Write

使用 Node 内置文件系统 API 或 `scripts/node-write.mjs` 读写文本。无需 Qoder Write。普通文件使用可用的 Node；DGS 文件先阅读 [references/dgs.md](references/dgs.md)，验证实际可执行文件，不能凭 Node、Python、PowerShell 的名称认定能力。

## 选择方式

- UTF-8 源码与文本：优先选已验证的 Node。读取工作区现有内容及明文 SHA-256，保留用户未提交修改。
- 内容已在内存中：用 `--stdin` 输入完整 UTF-8 字节，减少明文暂存和工具之间的编码转换。
- 需要文件草稿：用 `read --out` 创建任务 `work/` 中的新 `.txt`，编辑后使用 `--source`。`.txt` 也可能受 DGS 管控或在读取时改变物理状态；使用前核对实际行为。
- Office、PDF、图片、CAD、压缩包等二进制文件：使用对应格式工具，并验证该工具的 DGS 能力；本脚本不能把它们作为 UTF-8 文本编辑。

保留原 BOM、CRLF/LF、末尾换行，除非用户要求改变。不要用有损解码、删除 NUL 或忽略编码错误来“修复”密文。能获得明文也不代表其编码一定是 UTF-8。

## 准备 Node

文本读写以 Node 为运行时，加密由 DGS 执行。优先复用已验证且可启动的 Node 22 及以上版本，不为本任务强制升级其他安装。Windows 用本 skill 的 `scripts/ensure-node.ps1` 自动发现运行时；缺少时从 Node.js 官方下载当前架构的最新可用 LTS ZIP，校验官方 SHA-256 后安装到 `%LOCALAPPDATA%\CodexTools\node-write\node`。脚本自身只需要 PowerShell 5.1 及以上，无需预先安装 Node。

将变量设为本 skill 文件的实际绝对路径，然后运行：

```powershell
$nodeWriteBootstrap = 'C:/skills/node-write/scripts/ensure-node.ps1'
$nodeWriteSetupJson = & $nodeWriteBootstrap
if ($LASTEXITCODE -ne 0) { throw $nodeWriteSetupJson }
$nodeWriteSetup = $nodeWriteSetupJson | ConvertFrom-Json
$nodeWriteRuntime = $nodeWriteSetup.nodePath
$nodeWriteScript = 'C:/skills/node-write/scripts/node-write.mjs'
```

返回实际 `nodePath`、版本、来源和是否新安装。后续使用返回的绝对路径；不依赖永久 PATH，不需要管理员权限，也不覆盖其他 Node。任务要求更高版本时用 `-MinimumVersion 22.5.0` 等参数；仅查询用 `-CheckOnly`；指定运行时用 `-NodePath <绝对 node.exe 路径>`，无效时直接失败；指定用户安装目录用 `-InstallRoot <绝对目录>`；隔离测试或明确选用便携版时用 `-Portable`，仍复用该目录中的有效缓存。

**安装成功只证明 Node 能启动。** DGS 文件仍须验证实际可执行文件的同目录、同后缀读写及独立密文视角；路径或二进制变化后重做探针。网络、校验、启动或平台策略阻止安装时报告原因并停止受控修改，不反复安装或修改安全策略。macOS/Linux 发现现有运行时或使用环境支持的可信安装方式；此 PowerShell 脚本仅支持 Windows。

## 文本操作

读取时返回 SHA-256、运行时和换行/BOM 元数据；省略 `--out` 时同时返回文本。`.txt` 输出使用排他创建，避免覆盖其他任务草稿。

```powershell
& $nodeWriteRuntime $nodeWriteScript read --target 'D:/repo/src/example.ts' --out 'C:/task/work/example.txt'
& $nodeWriteRuntime $nodeWriteScript write --target 'D:/repo/src/example.ts' --source 'C:/task/work/example.txt' --expect-sha256 '<读取返回的 sha256>'
& $nodeWriteRuntime $nodeWriteScript write --target 'D:/repo/src/new.ts' --source 'C:/task/work/new.txt' --create
```

已有完整内容时，用 Node 工具或脚本把 Buffer 传给子进程 stdin。以下变量应替换成实际绝对路径、文本字节和基线；避免 PowerShell 文本管道改变字节或自动补换行。

```javascript
const result = spawnSync(nodeWriteRuntime, [nodeWriteScript, 'write',
  '--target', target, '--stdin', '--expect-sha256', baselineSha256,
  // DGS 目标加上 '--dgs-evidence', evidencePath, '--observer', observerPath
], { input: fullUtf8Bytes, encoding: 'utf8', windowsHide: true });
if (result.error || result.status !== 0) throw new Error(result.stderr);
```

`--source` 与 `--stdin` 二选一；`--create` 与 `--expect-sha256` 二选一。脚本严格验证 UTF-8、拒绝 NUL，直接写原始目标路径，逐字节核对 Node 读回。基线检查用于发现过期修改，不是文件锁或事务；基线变化时重新读取并合并。

## DGS 操作

首次使用、运行时升级、策略变化或切换目标目录/后缀时，用 `scripts/dgs-check.mjs probe` 创建无业务信息探针，生成本机 `.txt` 证据。观察器必须提供同一文件的独立密文视角，流程见 [DGS 验证](references/dgs.md)。

受控读写在上述命令后追加：

```powershell
--dgs-evidence 'C:/task/work/example-ts-evidence.txt' --observer 'C:/task/work/file-header.exe'
```

证据绑定 Node 和观察器的实际路径及二进制 SHA-256、目标所在目录及后缀（区分 `.ts` 与 `.d.ts`）。脚本拒绝不匹配的证据；已有密文读取前后、写入前后均检查独立视角，写入后必须符合已验证密文前缀。原本为明文的已有文件在该模式下拒绝覆盖：新建探针成功不证明覆盖明文文件会触发加密。普通文件使用普通模式；需要加密时依平台策略支持的方式处理。空文件也可能无法提供密文头，不能将其验证为已加密。

Node 读回成功只证明其明文视角一致。普通模式的 `verified: node-readback` 不代表完成 DGS 验证；需要密文保证时，必须得到 `node-readback+independent-cipher`。前缀检查只提供最低密文证据，仍需检查 Git diff 和项目必要的类型检查、构建或格式验证。

## 异常处理

编码错误、基线变化、证据不符或独立验证失败时，报告具体步骤与实际状态。脚本失败会返回 `readAttempted`、`writeAttempted` 和 `written`；写入中途失败可能已改变文件，DGS 自身也可能在读取时转换物理状态，不能声称自动回滚。

缺少必要能力时停止受控目标修改，保留草稿并说明缺口。不要改 DGS 策略、注入进程或把其他后缀的明文文件 rename 到受控路径；缺少 Qoder 工具不是障碍。
