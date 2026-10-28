# Windows：Claude 本机数据清理（Agent 提示词，无内置宿主）

适用：用户在 **Windows** 上要清理 Claude Code 或 Claude 桌面端的本地数据。**Windows 没有内置清理宿主和事务引擎**（macOS 才有 `native_cleanup_mac.py`），全部由 Agent 按本文用 PowerShell 一步一步做，每一步按[分级授权](authorization-tiers.md)。路径和行为来自 Claude 官方文档，官方没写的地方明确标出，不凭记忆补。

**硬规则：**
- 不要由正在使用这些目录的 Claude Code 或 Claude 桌面端自己来执行；请用户在普通 PowerShell 或 Codex 里做。
- 不永久删除：移走的东西进私有隔离目录，可还原。
- 不轮换设备标识（`userID`、`machineID`）。不承诺解封或解除关联。
- 执行 `claude` 命令（含 `claude purge`、`/logout`）属于接触 Claude，要先过 PC1；本文的步骤都不运行 `claude`。

## 1. 官方文档给出的路径

| 对象 | Windows 路径 | 来源 |
| --- | --- | --- |
| Claude Code 用户目录 | `%USERPROFILE%\.claude`（设了 `CLAUDE_CONFIG_DIR` 则在那个目录下） | [Explore the .claude directory](https://code.claude.com/docs/en/claude-directory) |
| 全局配置、账号信息 | `%USERPROFILE%\.claude.json` | 同上；[卸载说明](https://code.claude.com/docs/en/setup#uninstall-claude-code) |
| 登录凭据 | `%USERPROFILE%\.claude\.credentials.json`（继承用户目录的访问控制） | [Authentication - Credential management](https://code.claude.com/docs/en/authentication#credential-management) |
| Claude Code 程序 | `%USERPROFILE%\.local\bin\claude.exe`、`%USERPROFILE%\.local\share\claude` | [Uninstall a native installation](https://code.claude.com/docs/en/setup#uninstall-a-native-installation) |
| WinGet 安装 | `winget uninstall Anthropic.ClaudeCode` | 同上 |
| VS Code 扩展数据 | `%APPDATA%\Code\User\globalStorage\anthropic.claude-code` | [卸载说明](https://code.claude.com/docs/en/setup#remove-configuration-files) |
| Anthropic 配置目录（profile） | `%APPDATA%\Anthropic` | [Authentication](https://code.claude.com/docs/en/authentication#anthropic-profiles-and-federation-credentials) |
| 会话临时目录 | `%TEMP%\claude\<project>\<session-id>\scratchpad\` | [claude-directory](https://code.claude.com/docs/en/claude-directory#session-scratchpad-directory) |
| Claude 桌面端配置、日志 | `%APPDATA%\Claude\claude_desktop_config.json`、`%APPDATA%\Claude\logs` | [MCP：连接本地服务器](https://modelcontextprotocol.io/docs/develop/connect-local-servers) |

**官方没有写出的：**桌面端其余本地数据（登录状态、网页存储、MSIX 包的本地应用数据）的具体路径。[部署指南](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows)只说安装器的自动修复会删除“上一个包的本地应用数据，包括应用设置”，聊天记录和你自己文件夹里的文件不受影响。所以先用只读命令列出实际有什么（第 3 步），拿给用户看，**不按猜测的路径动手**。

## 2. 分档（沿用 macOS 宿主的划分）

**可再生，低风险**（官方说删除“没有用户可见损失”或会自动重新获取）：`%USERPROFILE%\.claude\` 下的 `cache`、`stats-cache.json`（只丢 `/usage` 历史合计）、`telemetry`、`usage-data`、`usage.jsonl`、`usage.with-fix.jsonl`、`remote-settings.json`、`policy-limits.json` 和它的 `.stamp.json`、`shell-snapshots`，以及旧版本遗留目录 `statsig`、`logs`、`image-cache`，调试日志 `debug`；桌面端的 `%APPDATA%\Claude\logs`。

**桌面端持久数据，含登录状态：**`%APPDATA%\Claude` 下除 `claude_desktop_config.json` 以外的内容。**`claude_desktop_config.json` 是你的 MCP 服务器配置，默认保留，**要动它必须单独说明并确认（里面的非法 MCP 按[非法工具清理](illegal-tools-cleanup.md)逐项处理）。

**对话记录（先问用户，建议移走）：**`%USERPROFILE%\.claude\projects`（每个项目的会话记录和自动记忆）和 `%USERPROFILE%\.claude\history.jsonl`（输入过的提示词）。会话记录里保存着 Claude Code 跑过的命令和输出，以前让 Claude 查过公网 IP、看过代理配置，真实 IP 和节点信息就在这里。清理时 Agent 要单独问一句“要不要把对话记录也移走？保险起见建议移走”，用户同意才放进范围。后果：旧会话在 Claude Code 里看不到、无法续接，自动记忆也一起移走；隔离可还原。

**始终保护，不进入任何清理范围：**`%USERPROFILE%\.claude` 整个目录，以及里面的 `file-history`、`settings.json`、`settings.local.json`、`CLAUDE.md`、`skills`、`plugins`、`commands`、`agents`、`agent-memory`、`hooks`、`rules`、`output-styles`、`workflows`、`mcp-servers`、`keybindings.json`、`themes`、`plans`、`tasks`、`todos`、`uploads`、`session-env`、`sessions`、`backups`、`jobs`、`daemon`、`.credentials.json`。官方也明确说：不要单独删 `settings.json`、`plugins`，不要删 `~/.claude.json`，除非你要彻底清掉账号、偏好和插件。例外：破限、反代分发等非法工具按[非法工具清理](illegal-tools-cleanup.md)逐项处理，只动查出来、用户确认的那几项。

代理客户端、VPN 和终端历史里的旧 IP 痕迹见[环境痕迹清理](trace-cleanup.md)。

**不在范围：**卸载程序（用 `winget uninstall` 或系统设置，单独确认）、凭据（见第 6 步）、浏览器站点数据、永久删除。

## 3. 只读审计（A 档，范围确认后自行做）

在普通 PowerShell 里，只读：

```powershell
# 有没有 Claude 进程（桌面端、CLI、编辑器里的 Claude Code）
Get-Process | Where-Object { $_.ProcessName -match '^(claude|Claude)' } | Select-Object Id, ProcessName, Path
# 候选目录是否存在、多大（不读文件内容）
foreach ($p in "$env:USERPROFILE\.claude\cache", "$env:USERPROFILE\.claude\telemetry", "$env:USERPROFILE\.claude\usage-data",
              "$env:APPDATA\Claude", "$env:APPDATA\Claude\logs") {
  if (Test-Path -LiteralPath $p) { "{0}  {1:N0} MB" -f $p, ((Get-ChildItem -LiteralPath $p -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB) }
}
# 桌面端是否是 MSIX 包，它的包数据在哪（只列名称和位置）
Get-AppxPackage | Where-Object { $_.Name -match 'Claude' } | Select-Object Name, PackageFamilyName, InstallLocation
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Claude' } | Select-Object FullName
```

把结果列给用户，包括哪些路径存在、各自属于哪一档。**有进程在运行就停，请用户先退出所有 Claude、VS Code 里的 Claude Code 和终端会话。**

## 4. 备份（B 档，整个计划批准一次）

备份会包含登录状态等敏感文件，所以放在只有你自己能访问的目录：

```powershell
$ref = "backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
$backup = "$env:USERPROFILE\.claude-guardian\backups\$ref"
New-Item -ItemType Directory -Path $backup -Force | Out-Null
icacls $backup /inheritance:r /grant:r "$($env:USERNAME):(OI)(CI)F" | Out-Null
# 对每个要处理的目录：复制，再逐文件比对哈希
Copy-Item -LiteralPath $src -Destination (Join-Path $backup 'root-0000') -Recurse -Force
$a = Get-ChildItem -LiteralPath $src -Recurse -Force -File | Get-FileHash -Algorithm SHA256
$b = Get-ChildItem -LiteralPath (Join-Path $backup 'root-0000') -Recurse -Force -File | Get-FileHash -Algorithm SHA256
(Compare-Object ($a | ForEach-Object { $_.Hash }) ($b | ForEach-Object { $_.Hash })) -eq $null   # 必须是 True
```

比对不一致就停止并报告，不继续。备份目录由你自己保管，用完自己删除。

## 5. 隔离（C 档，当场确认）

确认页必须逐项写明：要移走的每个目录及档位、受保护内容、隔离目录、备份位置、后果（桌面端会像新安装一样启动，登录状态丢失）、恢复办法。**你在对话里明确回复后才执行。**Windows 没有 macOS 那样的终端确认短语，沉默和超时都不算同意，Agent 不能自己批准。

```powershell
$q = "$env:USERPROFILE\.claude-guardian\quarantine\$ref"
New-Item -ItemType Directory -Path $q -Force | Out-Null
# 记下原路径，才能还原；然后移走（同一个盘内是重命名，不是复制再删除）
"$src" | Out-File -LiteralPath (Join-Path $q 'root-0000.path') -Encoding utf8
Move-Item -LiteralPath $src -Destination (Join-Path $q 'root-0000')
```

移完核对：受保护路径仍在；用户没选对话记录时 `history.jsonl` 和 `projects` 没动；隔离目录里的内容与备份一致。

**还原（单独再确认一次）：**

```powershell
$orig = (Get-Content -LiteralPath (Join-Path $q 'root-0000.path') -Raw).Trim()
Move-Item -LiteralPath (Join-Path $q 'root-0000') -Destination $orig
```

## 6. 退出登录与凭据（C 档，单独确认）

- **Claude Code：**登录凭据在 `%USERPROFILE%\.claude\.credentials.json`。官方的退出办法是在 Claude Code 里输入 `/logout`，那属于运行 Claude（PC1）。要在不运行 Claude 的情况下退出登录，只能移走这个文件：它属于凭据，先说明后果（需要重新登录），备份后再移，单独确认。
- **Claude 桌面端：**清掉 `%APPDATA%\Claude` 里的持久数据就会退出登录（第 5 步），官方没有单独的退出路径文档。
- Windows 凭据管理器里是否有 Claude 条目，官方文档没有写。如需检查，只读：`cmdkey /list`，把包含 `Claude` 的目标名列给用户看；删除用 `cmdkey /delete:<目标名>`，C 档，不可恢复，且不读取内容。

## 7. 最小提示词模式（可选，C 档）

`CLAUDE_CODE_SIMPLE=1`（官方环境变量，等同 `--bare`）：最小系统提示词，只保留 Bash、文件读写工具，不自动发现 hooks、skills、plugins、MCP、自动记忆和 CLAUDE.md；**不读取 OAuth 令牌和钥匙串凭据，认证只能用 `ANTHROPIC_API_KEY` 或 `apiKeyHelper`，订阅登录在此模式下不可用。**修改 `%USERPROFILE%\.claude\settings.json` 的 `env`：先备份文件，用结构化 JSON 工具改（PowerShell 的 `ConvertTo-Json` 必须加 `-Depth 100`，否则嵌套内容会被截断），只增删这一个键，改完对比其余键完全一致。

## 8. 官方的项目级清理

官方有 `claude purge <项目路径> --dry-run` / `claude purge <项目路径>`，只清一个项目的对话记录、自动记忆和 `~/.claude.json` 里该项目的条目，会先打印计划并要求确认。它要运行 Claude，所以由用户自己决定，且先过 PC1。`shell-snapshots` 和 `backups` 它不处理。

## 9. 不做的事

永久删除；轮换设备标识；改系统时区（属于环境对齐，不在清理里做，按[浏览器环境验收](whole-machine-ipv4.md#browser-acceptance)第 4 条改）；动注册表；用 `Get-AppxPackage | Remove-AppxPackage` 卸载桌面端（单独确认，且官方提醒 Repair/Reset 会删本地应用数据）；读取凭据内容；清理浏览器站点数据；承诺解封。

## 10. 限制

没有内置宿主，所以没有进程独占、没有模块自带的哈希清单，也没有终端确认短语，同意靠对话里的明确回复。命令是 PowerShell 的常规用法，**没有在真实 Windows 机器上跑过**；首次使用先用 `-WhatIf`（`Move-Item`、`Copy-Item` 支持）演练。桌面端的 MSIX 数据路径要在审计里看到实际结果后再用。
