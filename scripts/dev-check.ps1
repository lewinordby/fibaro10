param(
    [string]$QnapAlias = "qnap-fibaro10",
    [string]$QnapDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [string[]]$SmokeUrls = @(
        "https://online.lilletorget.net/health",
        "https://online.lilletorget.net/",
        "https://online.lilletorget.net/soling",
        "https://online.lilletorget.net/parkering"
    ),
    [switch]$SkipGitPushDryRun,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

function Section($name) {
    Write-Host ""
    Write-Host "== $name =="
}

function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$exe failed with exit code $LASTEXITCODE"
    }
}

function Check-Http($url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 20
        $statusCode = [int]$response.StatusCode
        $bytes = $response.RawContentLength
    } catch [System.Net.WebException] {
        if ($_.Exception.Response -eq $null) {
            throw
        }
        $statusCode = [int]$_.Exception.Response.StatusCode
        $bytes = 0
    }

    if ($statusCode -lt 200 -or ($statusCode -ge 400 -and $statusCode -notin @(401, 403))) {
        throw "$url returned HTTP $statusCode"
    }

    [pscustomobject]@{
        Url = $url
        StatusCode = $statusCode
        Bytes = $bytes
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

Section "Local git"
Run "git" @("fetch", "origin", "main")
Run "git" @("status", "-sb")
$branch = (& git branch --show-current).Trim()
if ($branch -ne "main") {
    throw "Expected branch main, got $branch"
}

if (-not $SkipGitPushDryRun) {
    Section "GitHub push"
    Run "git" @("push", "--dry-run", "origin", "main")
}

Section "QNAP SSH"
$remoteCheck = @"
set -e
source /opt/etc/profile 2>/dev/null || true
echo host=`$(hostname)
echo user=`$(id)
cd "$QnapDir"
git status -sb
git log -1 --oneline --decorate
test -x "$Docker"
"@
$remoteCheck = $remoteCheck -replace "`r`n", "`n" -replace "`r", "`n"
Run "ssh" @("-o", "BatchMode=yes", "-o", "ConnectTimeout=8", $QnapAlias, $remoteCheck)

Section "Health"
Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "health-check.ps1"))

if (-not $SkipSmoke) {
    Section "Online smoke"
    $SmokeUrls | ForEach-Object { Check-Http $_ } | Format-Table -AutoSize
}

Write-Host ""
Write-Host "Dev setup OK."
