param(
    [Parameter(Mandatory=$true)][string]$Config,
    [string]$OutputDirectory = [Environment]::GetFolderPath('Desktop')
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'windows-desktop.ps1') -Config $Config
$configPath = (Resolve-Path -LiteralPath $Config).Path
$null = Read-DesktopConfig $configPath On
$entry = Join-Path $PSScriptRoot 'windows-desktop.ps1'
$icon = Join-Path $PSScriptRoot 'icon.ico'
foreach ($path in @($entry,$icon,(Join-Path $PSScriptRoot 'windows-switch.ps1'))) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "缺少随包资产：$path" }
}
$items = @(@{Action='On';Name='开启保护（限制直连）'},@{Action='Off';Name='关闭保护（恢复联网）'})
foreach ($item in $items) {
    if (Test-Path -LiteralPath (Join-Path $OutputDirectory ($item.Name + '.lnk'))) { throw '同名快捷方式已存在，请先核对，避免覆盖已有入口。' }
}
if (-not (Test-Path -LiteralPath $OutputDirectory)) { $null = New-Item -ItemType Directory -Path $OutputDirectory }
$directory = Get-Item -LiteralPath $OutputDirectory
$shell = New-Object -ComObject WScript.Shell
foreach ($item in $items) {
    $link = $shell.CreateShortcut((Join-Path $directory.FullName ($item.Name + '.lnk')))
    $link.TargetPath = "$PSHOME\powershell.exe"
    $link.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $entry + '" -Action ' + $item.Action + ' -Config "' + $configPath + '"'
    $link.WorkingDirectory = $PSScriptRoot
    $link.IconLocation = $icon + ',0'
    $link.Description = $item.Name + '；操作后显示真实状态，图标不代表当前状态'
    $link.Save()
}
Write-Output '已生成两个 PowerShell 桌面快捷方式。请保持 Skill 及配置路径固定。'
