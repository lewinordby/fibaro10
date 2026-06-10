param(
    [Parameter(Mandatory = $true)]
    [string]$Name
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$versionsDir = Join-Path $repoRoot "migrations\versions"
New-Item -ItemType Directory -Force -Path $versionsDir | Out-Null

$safeName = $Name.Trim().ToLowerInvariant() -replace '[^a-z0-9]+', '-'
$safeName = $safeName.Trim("-")
if (-not $safeName) {
    throw "Migration name must contain at least one letter or number."
}

$stamp = Get-Date -Format "yyyyMMdd_HHmm"
$path = Join-Path $versionsDir "$stamp`_$safeName.sql"
if (Test-Path -LiteralPath $path) {
    throw "Migration already exists: $path"
}

$content = @"
-- Migration: $safeName
-- Created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
-- Notes:
--   Add purpose, execution notes, and rollback considerations here.

BEGIN;

-- SQL goes here.

COMMIT;
"@

Set-Content -LiteralPath $path -Value $content -Encoding UTF8
Write-Host $path
