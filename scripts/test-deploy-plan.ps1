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

$multiple = Get-DeployPlan -ChangedFiles @("main.py", "unifi_protect_events/app/main.py")
if ($multiple.All -or ($multiple.Services -join ",") -ne "fibaro10,unifi_protect_events") {
    throw "Multiple-service deploy plan is wrong: $($multiple | ConvertTo-Json -Compress)"
}

$deployScript = Get-Content -LiteralPath (Join-Path $PSScriptRoot "deploy-qnap.ps1") -Raw
if ($deployScript -notmatch '\$hasComposeServicesValue' -or $deployScript -match 'elif \[ -n "\$composeServices" \]') {
    throw "Deploy script must use the boolean service flag for multi-service plans."
}

$full = Get-DeployPlan -ChangedFiles @("docker-compose.qnap.yml")
if (-not $full.All -or -not $full.EasyPark -or -not $full.Roborock -or $full.Services.Count -lt 20) {
    throw "Full deploy plan is wrong: $($full | ConvertTo-Json -Compress)"
}

Write-Output "Deploy plan tests OK"
