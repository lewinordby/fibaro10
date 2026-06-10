param(
    [string]$QnapHostName = "192.168.20.218",
    [string]$QnapUser = "admin",
    [string]$QnapAlias = "qnap-fibaro10",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [switch]$InstallQnapKey
)

$ErrorActionPreference = "Stop"

function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$exe failed with exit code $LASTEXITCODE"
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sshDir = Join-Path $env:USERPROFILE ".ssh"
$sshConfig = Join-Path $sshDir "config"
$publicKey = "$IdentityFile.pub"

New-Item -ItemType Directory -Force $sshDir | Out-Null

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    Run "ssh-keygen" @("-t", "ed25519", "-f", $IdentityFile, "-C", "lewi-codex-qnap-fibaro10", "-N", '""')
}

$aliasBlock = @"
Host $QnapAlias
    HostName $QnapHostName
    User $QnapUser
    IdentityFile ~/.ssh/$(Split-Path $IdentityFile -Leaf)
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
"@.Trim()

if (Test-Path -LiteralPath $sshConfig) {
    $existingConfig = Get-Content -LiteralPath $sshConfig -Raw
    if ($existingConfig -notmatch "(?m)^Host\s+$([regex]::Escape($QnapAlias))\s*$") {
        Add-Content -LiteralPath $sshConfig -Value "`r`n$aliasBlock`r`n" -Encoding ascii
    }
} else {
    Set-Content -LiteralPath $sshConfig -Value "$aliasBlock`r`n" -Encoding ascii
}

Run "git" @("config", "--global", "--add", "safe.directory", ($repoRoot -replace "\\", "/"))
Run "git" @("config", "user.name", "Codex")
Run "git" @("config", "user.email", "codex@openai.com")

$desktopDir = Join-Path $repoRoot "desktop_v2"
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$npx = if ($env:OS -eq "Windows_NT") { "npx.cmd" } else { "npx" }
if (Test-Path -LiteralPath (Join-Path $desktopDir "package.json")) {
    Push-Location $desktopDir
    try {
        Run $npm @("install")
        Run $npx @("playwright", "install", "chromium")
    }
    finally {
        Pop-Location
    }
}

if ($InstallQnapKey) {
    $key = (Get-Content -LiteralPath $publicKey -Raw).Trim()
    $remote = @"
set -e
umask 077
mkdir -p ~/.ssh
touch ~/.ssh/authorized_keys
grep -qxF '$key' ~/.ssh/authorized_keys || printf '%s\n' '$key' >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
"@
    $remote = $remote -replace "`r`n", "`n" -replace "`r", "`n"
    ssh "$QnapUser@$QnapHostName" $remote
}

Write-Host "Local dev setup complete."
Write-Host "Repo: $repoRoot"
Write-Host "QNAP alias: $QnapAlias"
Write-Host "Public key: $publicKey"
Write-Host ""
Write-Host "Next check:"
Write-Host "powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev-check.ps1"
