param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [string]$Username = "fibaro-smoke",
    [ValidateSet("viewer", "settings")]
    [string]$Role = "viewer",
    [string]$BaseUrl = "http://192.168.20.218:8110",
    [string]$EnvFile = ".env.live-smoke",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

function NormalizeRemote([string]$script) {
    $script -replace "`r`n", "`n" -replace "`r", "`n"
}

function New-SmokePassword {
    $bytes = [byte[]]::new(24)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function Assert-SafeShellValue([string]$name, [string]$value) {
    if ($value -notmatch '^[A-Za-z0-9._:@/\-]+$') {
        throw "$name contains unsupported characters for non-interactive provisioning."
    }
}

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Missing SSH identity file: $IdentityFile. Run scripts\setup-local-dev.ps1 first."
}

$Username = $Username.Trim().ToLowerInvariant()
if (-not $Username) {
    throw "Username cannot be empty."
}
if (-not $Password) {
    $Password = New-SmokePassword
}

Assert-SafeShellValue "Username" $Username
Assert-SafeShellValue "Password" $Password
Assert-SafeShellValue "Role" $Role
Assert-SafeShellValue "RemoteDir" $RemoteDir
Assert-SafeShellValue "Docker" $Docker

$remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
cd "$RemoteDir"
"$Docker" exec -i \
  -e FIBARO10_SMOKE_USERNAME="$Username" \
  -e FIBARO10_SMOKE_PASSWORD="$Password" \
  -e FIBARO10_SMOKE_ROLE="$Role" \
  fibaro10 python - <<'PY'
import asyncio
import os
from sqlalchemy import select

from main import AccessKey, async_session, credential_hash, credential_prefix, normalize_username


async def run():
    username = normalize_username(os.environ["FIBARO10_SMOKE_USERNAME"])
    password = os.environ["FIBARO10_SMOKE_PASSWORD"].strip()
    role = os.environ.get("FIBARO10_SMOKE_ROLE", "viewer").strip().lower()
    if role not in {"viewer", "settings"}:
        role = "viewer"
    if not username or username == "master":
        raise SystemExit("Invalid smoke username")
    if len(password) < 16:
        raise SystemExit("Smoke password must be at least 16 characters")

    async with async_session() as session:
        existing = (
            await session.execute(select(AccessKey).where(AccessKey.name == username))
        ).scalars().first()
        if existing:
            if existing.is_master:
                raise SystemExit("Refusing to update master user")
            existing.key_hash = credential_hash(username, password)
            existing.key_prefix = credential_prefix(username, password)
            existing.key_plaintext = password
            existing.role = role
            existing.active = True
            action = "updated"
        else:
            existing = AccessKey(
                name=username,
                key_hash=credential_hash(username, password),
                key_prefix=credential_prefix(username, password),
                key_plaintext=password,
                role=role,
                is_master=False,
                active=True,
            )
            session.add(existing)
            action = "created"
        await session.commit()
        print(f"{action}:{username}:{role}")


asyncio.run(run())
PY
"@

ssh -i $IdentityFile -o BatchMode=yes -o ConnectTimeout=8 $QnapHost (NormalizeRemote $remote)
if ($LASTEXITCODE -ne 0) {
    throw "ssh failed with exit code $LASTEXITCODE"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$target = if ([System.IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $repoRoot $EnvFile }
$content = @(
    "# Local credentials for desktop_v2/scripts/smoke-live.mjs. Do not commit.",
    "FIBARO10_LIVE_BASE_URL=$BaseUrl",
    "FIBARO10_LIVE_USERNAME=$Username",
    "FIBARO10_LIVE_PASSWORD=$Password"
) -join "`n"
Set-Content -LiteralPath $target -Value $content -Encoding utf8

Write-Host "Provisioned $Username as $Role on QNAP."
Write-Host "Wrote live smoke credentials to $target"
