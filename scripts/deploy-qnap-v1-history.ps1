param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$V1Dir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10_v1_487044d",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [string]$Commit = "487044d",
    [string]$HostIp = "192.168.20.218",
    [int]$Port = 8111
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

$readOnlyPatch = @'
from pathlib import Path

path = Path("main.py")
text = path.read_text(encoding="utf-8")

env_marker = 'EASYPARK_DOWNLOADER_URL = os.getenv("EASYPARK_DOWNLOADER_URL", "http://127.0.0.1:8109").rstrip("/")\n'
if "READ_ONLY_MODE =" not in text:
    text = text.replace(
        env_marker,
        env_marker
        + 'READ_ONLY_MODE = os.getenv("READ_ONLY_MODE", "false").strip().lower() in {"1", "true", "yes", "ja"}\n',
    )

guard_marker = "templates.env.globals.update(app_version=APP_VERSION, app_build=APP_BUILD, build_log=BUILD_LOG)\n\n"
guard = '''READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


@app.middleware("http")
async def read_only_guard(request: Request, call_next):
    if READ_ONLY_MODE and request.method.upper() not in READ_ONLY_METHODS:
        return JSONResponse({"detail": "Historisk V1 er skrivebeskyttet."}, status_code=405)
    return await call_next(request)


'''
if "async def read_only_guard" not in text:
    text = text.replace(guard_marker, guard_marker + guard)

engine_line = 'engine = create_async_engine(DATABASE_URL, echo=False)\n'
engine_replacement = (
    'ENGINE_CONNECT_ARGS = {"server_settings": {"default_transaction_read_only": "on"}} if READ_ONLY_MODE else {}\n'
    + 'engine = create_async_engine(DATABASE_URL, echo=False, connect_args=ENGINE_CONNECT_ARGS)\n'
)
if engine_line in text and engine_replacement not in text:
    text = text.replace(engine_line, engine_replacement)

false_log = '        await log_access_attempt(request, False, "missing_or_invalid_key", attempted_username=username)\n'
if false_log in text:
    text = text.replace(
        false_log,
        '        if not READ_ONLY_MODE:\n'
        + '            await log_access_attempt(request, False, "missing_or_invalid_key", attempted_username=username)\n',
    )

true_log = '    await log_access_attempt(request, True, "ok", access_key)\n'
if true_log in text:
    text = text.replace(
        true_log,
        '    if not READ_ONLY_MODE:\n'
        + '        await log_access_attempt(request, True, "ok", access_key)\n',
    )

startup_marker = "async def startup():\n    global svv_sync_task\n"
startup_replacement = "async def startup():\n    global svv_sync_task\n    if READ_ONLY_MODE:\n        return\n"
if startup_marker in text and startup_replacement not in text:
    text = text.replace(startup_marker, startup_replacement)

path.write_text(text, encoding="utf-8")
'@
$readOnlyPatchBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($readOnlyPatch))

$remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
test -d "$RemoteDir"
test -x "$Docker"
cd "$RemoteDir"
git fetch origin main
git cat-file -e "$Commit^{commit}"

if [ -d "$V1Dir/.git" ] || [ -f "$V1Dir/.git" ]; then
    cd "$V1Dir"
    git checkout --detach "$Commit"
    git reset --hard "$Commit"
    git clean -fdx -e .env -e '.env.*'
else
    if [ -e "$V1Dir" ]; then
        echo "V1 path exists but is not a git worktree: $V1Dir" >&2
        exit 1
    fi
    git worktree add --detach "$V1Dir" "$Commit"
    cd "$V1Dir"
fi

cat > /tmp/fibaro10_v1_readonly_patch.py.b64 <<'EOF_PATCH'
$readOnlyPatchBase64
EOF_PATCH
base64 -d /tmp/fibaro10_v1_readonly_patch.py.b64 > /tmp/fibaro10_v1_readonly_patch.py 2>/dev/null || test -s /tmp/fibaro10_v1_readonly_patch.py
"$Docker" run --rm -v "${V1Dir}:/work" -v /tmp/fibaro10_v1_readonly_patch.py:/patch.py:ro -w /work python:3.12-slim python /patch.py
rm -f /tmp/fibaro10_v1_readonly_patch.py /tmp/fibaro10_v1_readonly_patch.py.b64

cp -p "$RemoteDir/.env" "$V1Dir/.env"
cat > "$V1Dir/docker-compose.v1.yml" <<'EOF'
services:
  fibaro10_v1:
    build: .
    image: fibaro10:v1-487044d
    container_name: fibaro10_v1
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp
    env_file:
      - .env
    environment:
      READ_ONLY_MODE: "true"
      SVV_SYNC_ENABLED: "false"
      APP_BUILD: "v1-487044d"
      MET_USER_AGENT: "fibaro10-v1/1.0 http://${HostIp}:${Port}"
    ports:
      - "${HostIp}:${Port}:8110"
EOF

"$Docker" compose -f "$V1Dir/docker-compose.v1.yml" up -d --build fibaro10_v1
"$Docker" compose -f "$V1Dir/docker-compose.v1.yml" ps
echo "V1 historical UI: http://${HostIp}:${Port}"
echo "V1 commit: $Commit"
"@

Run "ssh" @("-i", $IdentityFile, $QnapHost, (NormalizeRemote $remote))
WaitHttp "http://${HostIp}:${Port}/health"
$postStatus = (& curl.exe -sS -o NUL -w "%{http_code}" -X POST "http://${HostIp}:${Port}/auth/login").Trim()
if ($postStatus -ne "405") {
    throw "V1 read-only check failed. Expected POST /auth/login to return 405, got $postStatus."
}
Write-Host ""
Write-Host "V1 historical UI is available at http://${HostIp}:${Port}"
