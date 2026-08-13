param(
    [string[]]$Services = @(),
    [switch]$EasyPark,
    [switch]$Roborock,
    [switch]$SkipRoutes
)

$ErrorActionPreference = "Stop"
$hostAddress = "192.168.20.218"
$healthUrls = @{
    fibaro10 = "http://${hostAddress}:8110/health"
    shell_app = "http://${hostAddress}:8150/ready"
    revenue_app = "http://${hostAddress}:8151/ready"
    parking_app = "http://${hostAddress}:8152/ready"
    sun_app = "http://${hostAddress}:8153/ready"
    energy_app = "http://${hostAddress}:8154/ready"
    operations_app = "http://${hostAddress}:8155/ready"
    maintenance_app = "http://${hostAddress}:8156/ready"
    system_app = "http://${hostAddress}:8157/ready"
    link_app = "http://${hostAddress}:8158/ready"
    owntracks_service = "http://${hostAddress}:8128/health"
    unifi_protect_events = "http://${hostAddress}:8130/ready"
    axis_camera_snapshots = "http://${hostAddress}:8125/health"
    car_info_lookup = "http://${hostAddress}:8126/health"
    parking_sun_linker = "http://${hostAddress}:8127/health"
    online_dashboard = "https://online.lilletorget.net/health"
    maintenance_mobile = "https://vedl.lilletorget.net/health"
    alarm_mobile = "http://${hostAddress}:8114/health"
    fibaro10ipad = "https://ipad.lilletorget.net/health"
}

foreach ($service in $Services) {
    $url = $healthUrls[$service]
    if (-not $url) { continue }
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 30
    if ($response.StatusCode -ne 200) { throw "$service returnerte HTTP $($response.StatusCode)" }
    Write-Host "Health OK: $service"
}
if ($EasyPark) {
    Invoke-WebRequest -UseBasicParsing -Uri "http://${hostAddress}:8109/health" -TimeoutSec 30 | Out-Null
    Write-Host "Health OK: easypark_downloader"
}
if ($Roborock -or "operations_app" -in $Services) {
    Invoke-WebRequest -UseBasicParsing -Uri "http://${hostAddress}:8095/health" -TimeoutSec 30 | Out-Null
    Write-Host "Health OK: roborock_logger"
}

$appIds = @{
    revenue_app = "revenue"; parking_app = "parking"; sun_app = "sun"; energy_app = "energy";
    operations_app = "operations"; maintenance_app = "maintenance"; system_app = "system"; link_app = "link"
}
$affectedApps = @($Services | ForEach-Object { $appIds[$_] } | Where-Object { $_ })
if (-not $SkipRoutes -and $affectedApps.Count -gt 0) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "smoke-domain-apps.ps1") -AppIds $affectedApps
    if ($LASTEXITCODE -ne 0) { throw "Rutekontroll av berørte apper feilet" }
}

Write-Host "Avgrenset produksjonskontroll OK: $($Services -join ', ')"
