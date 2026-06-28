param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [string]$HostIp = "192.168.20.218",
    [int]$Port = 8111,
    [string]$SourceCommit = "487044d"
)

$ErrorActionPreference = "Stop"

function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$exe failed with exit code $LASTEXITCODE"
    }
}

function NormalizeRemote([string]$script) {
    $script -replace "`r`n", "`n" -replace "`r", "`n"
}

function WaitHttp([string]$Url, [int]$Attempts = 30) {
    for ($i = 1; $i -le $Attempts; $i++) {
        & curl.exe -s -f $Url | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "HTTP endpoint did not become ready: $Url"
}

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Missing SSH identity file: $IdentityFile. Run scripts\setup-local-dev.ps1 first."
}

foreach ($path in @(
    "docker-compose.v1-reference.yml",
    "v1_reference/Dockerfile",
    "v1_reference/requirements.txt",
    "v1_reference/app/main.py"
)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing V1 reference deploy file: $path"
    }
}

$uploadDir = "$RemoteDir/.v1_reference_upload"

$prepareRemote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
test -d "$RemoteDir"
test -x "$Docker"
cd "$RemoteDir"
rm -rf "$uploadDir"
mkdir -p "$uploadDir/v1_reference/app"
"@

Run "ssh" @("-i", $IdentityFile, $QnapHost, (NormalizeRemote $prepareRemote))

Run "scp" @("-i", $IdentityFile, "docker-compose.v1-reference.yml", "${QnapHost}:${uploadDir}/docker-compose.v1-reference.yml")
Run "scp" @("-i", $IdentityFile, "v1_reference/Dockerfile", "v1_reference/requirements.txt", "${QnapHost}:${uploadDir}/v1_reference/")
Run "scp" @("-i", $IdentityFile, "v1_reference/app/main.py", "${QnapHost}:${uploadDir}/v1_reference/app/")

$remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
test -d "$RemoteDir"
test -x "$Docker"
cd "$RemoteDir"
cp "$uploadDir/docker-compose.v1-reference.yml" docker-compose.v1-reference.yml
rm -rf v1_reference.prev
if [ -d v1_reference ]; then
    mv v1_reference v1_reference.prev
fi
mv "$uploadDir/v1_reference" v1_reference
rm -rf v1_reference.prev "$uploadDir"
"$Docker" rm -f fibaro10_v1 >/dev/null 2>&1 || true
APP_BUILD=v1-reference V1_SOURCE_COMMIT="$SourceCommit" "$Docker" compose -f docker-compose.v1-reference.yml up -d --build fibaro10_v1
"$Docker" compose -f docker-compose.v1-reference.yml ps
echo "V1 reference UI: http://${HostIp}:${Port}"
echo "V1 source commit: $SourceCommit"
"@

Run "ssh" @("-i", $IdentityFile, $QnapHost, (NormalizeRemote $remote))
WaitHttp "http://${HostIp}:${Port}/health"

$health = (& curl.exe -sS "http://${HostIp}:${Port}/health").Trim()
if ($health -notmatch '"mode"\s*:\s*"reference_only"') {
    throw "V1 reference health check failed: $health"
}

Write-Host ""
Write-Host "V1 reference UI is available at http://${HostIp}:${Port}"
