$ErrorActionPreference = "Stop"

function Run($exe, [string[]]$arguments, [string]$WorkingDirectory = "") {
    $original = (Get-Location).Path
    if ($WorkingDirectory) {
        Set-Location $WorkingDirectory
    }
    try {
        & $exe @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$exe failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Set-Location $original
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$desktopDir = Join-Path $repoRoot "desktop_v2"
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }

Write-Host "Python syntax check"
Run "python" @("-m", "py_compile", "main.py", "build_log.py", "api_contracts.py", "api_types.py", "migration_runner.py", "observability.py", "security.py", "roborock_domain.py", "time_formatting.py", "scripts/run-migrations.py") $repoRoot

Write-Host "Python unit tests"
Run "python" @("-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py") $repoRoot

Write-Host "Frontend typecheck and build"
Run $npm @("run", "check") $desktopDir

Write-Host "Frontend UI smoke"
Run $npm @("run", "smoke:ui") $desktopDir

Write-Host "Git whitespace check"
Run "git" @("diff", "--check") $repoRoot

Write-Host "Local quality check OK"
