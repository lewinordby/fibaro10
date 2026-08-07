$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "deploy-plan.ps1")

$core = Get-DeployPlan -ChangedFiles @("main.py", "desktop_v2/src/App.tsx", "BUILD", "scripts/readme.ps1")
if ($core.All -or ($core.Services -join ",") -ne "fibaro10" -or $core.EasyPark -or $core.Roborock) {
    throw "Core deploy plan is wrong: $($core | ConvertTo-Json -Compress)"
}

$shared = Get-DeployPlan -ChangedFiles @("packages/microapp-ui/src/index.ts")
if ($shared.All -or $shared.Services.Count -ne 9 -or "shell_app" -notin $shared.Services) {
    throw "Shared UI deploy plan is wrong: $($shared | ConvertTo-Json -Compress)"
}

$easyPark = Get-DeployPlan -ChangedFiles @("easypark_downloader/app/main.py")
if (-not $easyPark.EasyPark -or $easyPark.Services.Count -ne 0) {
    throw "EasyPark deploy plan is wrong: $($easyPark | ConvertTo-Json -Compress)"
}

$full = Get-DeployPlan -ChangedFiles @("docker-compose.qnap.yml")
if (-not $full.All -or -not $full.EasyPark -or -not $full.Roborock -or $full.Services.Count -lt 20) {
    throw "Full deploy plan is wrong: $($full | ConvertTo-Json -Compress)"
}

Write-Output "Deploy plan tests OK"
