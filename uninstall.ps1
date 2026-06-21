# uninstall.ps1 — remove the Windows shims created by install.ps1.
# Runtime data in %USERPROFILE%\.thmes\ is NOT touched.
# Compatible with Windows PowerShell 5.1 and PowerShell 7+.
#
#   powershell -ExecutionPolicy Bypass -File .\uninstall.ps1

$ErrorActionPreference = 'Stop'
$HomeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
$BinDir = Join-Path (Join-Path $HomeDir '.thmes') 'bin'

foreach ($name in @('thmes', 'thmes-pro', 'thmes-daemon')) {
    $shim = Join-Path $BinDir "$name.cmd"
    if (Test-Path $shim) {
        Remove-Item $shim
        Write-Host "  x removed $shim"
    }
}

# Remove BinDir from the user PATH if present (degrades gracefully off-Windows).
try {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath -and (($userPath -split ';') -contains $BinDir)) {
        $kept = ($userPath -split ';' | Where-Object { $_ -and $_ -ne $BinDir }) -join ';'
        [Environment]::SetEnvironmentVariable('Path', $kept, 'User')
        Write-Host "  x removed $BinDir from your user PATH (restart the terminal)"
    }
} catch { }

Write-Host ""
Write-Host "Done. Shims removed."
Write-Host ""
Write-Host "Runtime data preserved:"
Write-Host "  %USERPROFILE%\.thmes\           (sessions, memory, agents, mcp.json)"
Write-Host "  %USERPROFILE%\.thmes-history    (input history)"
Write-Host ""
Write-Host "To wipe runtime data:  Remove-Item -Recurse -Force $env:USERPROFILE\.thmes"
