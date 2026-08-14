$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "deploy-plan.ps1")

$core = Get-DeployPlan -ChangedFiles @("main.py", "desktop_v2/src/App.tsx", "BUILD", "scripts/readme.ps1")
if ($core.All -or ($core.Services -join ",") -ne "fibaro10" -or $core.EasyPark -or $core.Roborock -or $core.Dreame) {
    throw "Core deploy plan is wrong: $($core | ConvertTo-Json -Compress)"
}

$shared = Get-DeployPlan -ChangedFiles @("packages/microapp-ui/src/index.ts")
if ($shared.All -or $shared.Services.Count -ne 9 -or "shell_app" -notin $shared.Services) {
    throw "Shared UI deploy plan is wrong: $($shared | ConvertTo-Json -Compress)"
}

$operationsUi = Get-DeployPlan -ChangedFiles @("operations_app/frontend/src/components/RoborockSpecial.tsx")
if ($operationsUi.All -or ($operationsUi.Services -join ",") -ne "operations_app") {
    throw "Operations-owned UI deploy plan is wrong: $($operationsUi | ConvertTo-Json -Compress)"
}

foreach ($ownedUi in @(
    @{ Path = "energy_app/frontend/src/components/EnergyCircuitLoads.tsx"; Service = "energy_app" },
    @{ Path = "sun_app/frontend/src/components/SunSessionsSpecial.tsx"; Service = "sun_app" },
    @{ Path = "link_app/frontend/src/components/LinkReviewSpecial.tsx"; Service = "link_app" },
    @{ Path = "maintenance_app/frontend/src/components/MaintenanceVisitDetailPage.tsx"; Service = "maintenance_app" },
    @{ Path = "system_app/frontend/src/components/SystemSpecial.tsx"; Service = "system_app" }
)) {
    $plan = Get-DeployPlan -ChangedFiles @($ownedUi.Path)
    if ($plan.All -or ($plan.Services -join ",") -ne $ownedUi.Service) {
        throw "App-owned UI deploy plan is wrong for $($ownedUi.Path): $($plan | ConvertTo-Json -Compress)"
    }
}

$mobileTheme = Get-DeployPlan -ChangedFiles @("packages/mobile-appkit/lilletorget-appkit.css")
if ($mobileTheme.All -or ($mobileTheme.Services -join ",") -ne "online_dashboard,maintenance_mobile,alarm_mobile") {
    throw "Mobile theme deploy plan is wrong: $($mobileTheme | ConvertTo-Json -Compress)"
}

$sharedBackend = Get-DeployPlan -ChangedFiles @("microapp_backend/pwa.py")
foreach ($requiredService in @("fibaro10", "shell_app", "online_dashboard")) {
    if ($sharedBackend.All -or $sharedBackend.Services.Count -ne 11 -or $requiredService -notin $sharedBackend.Services) {
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
if ($deployScript -notmatch '\$coreDeployValue' -or $deployScript -notmatch 'deploy-core-qnap\.sh' -or $deployScript -match 'elif \[ -n "\$composeServices" \]') {
    throw "Deploy script must use the boolean service flag for multi-service plans."
}
foreach ($required in @("check-affected.ps1", "smoke-affected.ps1", '$broadValidation')) {
    if ($deployScript -notmatch [regex]::Escape($required)) {
        throw "Deploy script is missing scoped validation marker $required."
    }
}

$coreGateway = Get-DeployPlan -ChangedFiles @("Caddyfile.core")
if ($coreGateway.All -or ($coreGateway.Services -join ",") -ne "fibaro10") {
    throw "Core gateway deploy plan is wrong: $($coreGateway | ConvertTo-Json -Compress)"
}

$full = Get-DeployPlan -ChangedFiles @("docker-compose.qnap.yml")
if (-not $full.All -or $full.EasyPark -or $full.Roborock -or $full.Dreame -or $full.Services.Count -lt 20) {
    throw "Full deploy plan is wrong: $($full | ConvertTo-Json -Compress)"
}

$coreCompose = Get-Content -LiteralPath (Join-Path $PSScriptRoot "..\docker-compose.qnap.yml") -Raw
foreach ($required in @("fibaro10_blue", "fibaro10_green", "fibaro10_worker", "Caddyfile.core")) {
    if ($coreCompose -notmatch [regex]::Escape($required)) {
        throw "Core Compose architecture is missing $required."
    }
}

Write-Output "Deploy plan tests OK"
