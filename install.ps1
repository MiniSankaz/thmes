# install.ps1 — Windows installer for thmes (best-effort; full features need WSL/macOS/Linux).
#
# Creates .cmd shims for the cross-platform Python entry points and adds them to your
# user PATH. The bash / MLX / PTY tools (gemma, mlx-serve-*, thmes-web) are Unix-only
# and are NOT installed on Windows — run thmes under WSL for those.
#
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#
# Override the interpreter with  $env:THMES_PYTHON  before running.
# Compatible with Windows PowerShell 5.1 and PowerShell 7+.

$ErrorActionPreference = 'Stop'

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Definition
$HomeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
# Nested Join-Path keeps this working on Windows PowerShell 5.1 (no 3-arg Join-Path).
$BinDir = Join-Path (Join-Path $HomeDir '.thmes') 'bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# Resolve a Python invocation (quoted so spaces in the path are safe).
$PyInvoke = $null
if ($env:THMES_PYTHON) {
    $PyInvoke = $env:THMES_PYTHON
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PyInvoke = 'py -3'
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PyInvoke = '"' + (Get-Command python).Source + '"'
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PyInvoke = '"' + (Get-Command python3).Source + '"'
}
if (-not $PyInvoke) {
    Write-Error 'No Python found. Install Python 3.11+ (https://python.org) or set $env:THMES_PYTHON.'
    exit 1
}

Write-Host "Platform: Windows"
Write-Host "Repo:     $Repo"
Write-Host "Target:   $BinDir"
Write-Host "Python:   $PyInvoke"
Write-Host ""

# Cross-platform Python entry points only (bash/MLX/PTY launchers are Unix-only).
$Entries = @('thmes', 'thmes-pro', 'thmes-daemon')
foreach ($name in $Entries) {
    $src = Join-Path (Join-Path $Repo 'bin') $name
    if (-not (Test-Path $src)) { continue }
    $shim = Join-Path $BinDir "$name.cmd"
    "@echo off`r`n$PyInvoke `"$src`" %*`r`n" | Set-Content -Path $shim -Encoding ASCII -NoNewline
    Write-Host "  + $name.cmd  ->  $src"
}

# Add BinDir to the USER PATH (idempotent). Wrapped so a non-Windows host or a locked-down
# environment degrades to a manual instruction instead of crashing.
try {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if (-not $userPath) { $userPath = '' }
    if (($userPath -split ';') -notcontains $BinDir) {
        $newPath = if ($userPath) { "$userPath;$BinDir" } else { $BinDir }
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        Write-Host "`n  + added $BinDir to your user PATH (open a NEW terminal to pick it up)"
    } else {
        Write-Host "`n  ($BinDir already on PATH)"
    }
} catch {
    Write-Host "`n  ! could not update PATH automatically — add this folder to your PATH manually:"
    Write-Host "      $BinDir"
}

Write-Host ''
Write-Host 'Done. Open a NEW terminal, then run:  thmes'
Write-Host ''
Write-Host 'Windows notes:'
Write-Host '  * MLX is Apple-Silicon only -> use an Ollama model:  set THMES_MODEL=ol:llama3.2:3b'
Write-Host '    (install Ollama from https://ollama.com, then: ollama pull llama3.2:3b)'
Write-Host '  * The bash tool, gemma, mlx-serve-* and the web terminal (thmes-web) are Unix-only.'
Write-Host '  * For full features (web terminal, bash tool) run thmes under WSL:'
Write-Host '        wsl --install   then inside WSL:  ./install.sh'
