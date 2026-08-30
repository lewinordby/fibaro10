$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "deploy-plan.ps1")

$core = Get-DeployPlan -ChangedFiles @("main.py", "BUILD", "scripts/readme.ps1")
if ($core.All -or ($core.Services -join ",") -ne "fibaro10" -or $core.EasyPark -or $core.Roborock -or $core.Dreame) {
    throw "Core deploy plan is wrong: $($core | ConvertTo-Json -Compress)"
}

foreach ($coreModule in @("fibaro_core/models/sun.py", "fibaro_core/schemas/parking.py", "fibaro_core/routers/assets.py", "fibaro_core/database.py", "fibaro_core/services/summaries/parking.py", "fibaro_core/services/comparisons/overview.py", "value_parsing.py")) {
    $plan = Get-DeployPlan -ChangedFiles @($coreModule)
    if ($plan.All -or ($plan.Services -join ",") -ne "fibaro10" -or $plan.EasyPark -or $plan.Roborock -or $plan.Dreame) {
        throw "Core module must only deploy Fibaro10: $coreModule"
    }
}

foreach ($adapter in @(
    "revenue_app", "parking_app", "sun_app", "energy_app",
    "operations_app", "maintenance_app", "system_app", "link_app"
)) {
    $plan = Get-DeployPlan -ChangedFiles @("$adapter/app/main.py")
    if ($plan.All -or ($plan.Services -join ",") -ne $adapter) {
        throw "Adapter deploy plan is wrong for ${adapter}: $($plan | ConvertTo-Json -Compress)"
    }
}

$mobileTheme = Get-DeployPlan -ChangedFiles @("packages/mobile-appkit/lilletorget-appkit.css")
if ($mobileTheme.All -or ($mobileTheme.Services -join ",") -ne "online_dashboard,maintenance_mobile,alarm_mobile") {
    throw "Mobile theme deploy plan is wrong: $($mobileTheme | ConvertTo-Json -Compress)"
}

$cleaningRobotDomain = Get-DeployPlan -ChangedFiles @("cleaning_robot_domain.py")
if ($cleaningRobotDomain.All -or ($cleaningRobotDomain.Services -join ",") -ne "fibaro10,online_dashboard") {
    throw "Cleaning robot domain deploy plan is wrong: $($cleaningRobotDomain | ConvertTo-Json -Compress)"
}

$sharedBackend = Get-DeployPlan -ChangedFiles @("microapp_backend/runtime.py")
foreach ($requiredService in @("fibaro10", "revenue_app", "parking_app", "sun_app", "energy_app", "operations_app", "maintenance_app", "system_app", "link_app", "online_dashboard")) {
    if ($sharedBackend.All -or $sharedBackend.Services.Count -ne 10 -or $requiredService -notin $sharedBackend.Services) {
        throw "Shared backend deploy plan is wrong: $($sharedBackend | ConvertTo-Json -Compress)"
    }
}

$easyPark = Get-DeployPlan -ChangedFiles @("easypark_downloader/app/main.py")
if (-not $easyPark.EasyPark -or $easyPark.Services.Count -ne 0) {
    throw "EasyPark deploy plan is wrong: $($easyPark | ConvertTo-Json -Compress)"
}

$dreame = Get-DeployPlan -ChangedFiles @("dreame_logger/app/main.py")
if (-not $dreame.Dreame -or $dreame.Services.Count -ne 0 -or $dreame.Roborock) {
    throw "Dreame deploy plan is wrong: $($dreame | ConvertTo-Json -Compress)"
}

$multiple = Get-DeployPlan -ChangedFiles @("main.py", "unifi_protect_events/app/main.py")
if ($multiple.All -or ($multiple.Services -join ",") -ne "fibaro10,unifi_protect_events") {
    throw "Multiple-service deploy plan is wrong: $($multiple | ConvertTo-Json -Compress)"
}

$deployScript = Get-Content -LiteralPath (Join-Path $PSScriptRoot "deploy-qnap.ps1") -Raw
foreach ($required in @("deploy-core-qnap.sh", "check-affected.ps1", "smoke-affected.ps1", '$broadValidation')) {
    if ($deployScript -notmatch [regex]::Escape($required)) {
        throw "Deploy script is missing $required."
    }
}
if ($deployScript -notmatch 'DOCKER_BIN="\$Docker" sh scripts/renew-internal-https\.sh') {
    throw "Deploy script must issue the active internal certificate before reloading Caddy."
}

$coreGateway = Get-DeployPlan -ChangedFiles @("Caddyfile.core")
if ($coreGateway.All -or ($coreGateway.Services -join ",") -ne "fibaro10") {
    throw "Core gateway deploy plan is wrong: $($coreGateway | ConvertTo-Json -Compress)"
}

$full = Get-DeployPlan -ChangedFiles @("docker-compose.qnap.yml")
if (-not $full.All -or $full.EasyPark -or $full.Roborock -or $full.Dreame -or $full.Services.Count -lt 18) {
    throw "Full deploy plan is wrong: $($full | ConvertTo-Json -Compress)"
}

$coreCompose = Get-Content -LiteralPath (Join-Path $PSScriptRoot "..\docker-compose.qnap.yml") -Raw
foreach ($required in @("fibaro10_blue", "fibaro10_green", "fibaro10_worker", "Caddyfile.core")) {
    if ($coreCompose -notmatch [regex]::Escape($required)) {
        throw "Core Compose architecture is missing $required."
    }
}
foreach ($retired in @("shell_app:", "fibaro10ipad:")) {
    if ($coreCompose -match [regex]::Escape($retired)) {
        throw "Retired service is still present in Compose: $retired"
    }
}

Write-Output "Deploy plan tests OK"
