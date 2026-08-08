function Get-DeployPlan([string[]]$ChangedFiles, [bool]$ForceAll = $false) {
    $microApps = @(
        "revenue_app", "parking_app", "sun_app", "energy_app",
        "operations_app", "maintenance_app", "system_app", "link_app"
    )
    $allServices = @(
        "owntracks_service", "fibaro10", "revenue_app", "parking_app", "sun_app",
        "energy_app", "operations_app", "maintenance_app", "system_app", "link_app",
        "shell_app", "unifi_protect_events", "visual_anomaly_service", "online_dashboard",
        "maintenance_mobile", "alarm_mobile", "fibaro10ipad", "axis_camera_snapshots",
        "car_info_lookup", "sun2_backfill_downloader", "sun2_importer",
        "sun2_session_scraper", "parking_sun_linker", "fibaro10_proxy"
    )
    $services = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $deployAll = $ForceAll
    $deployEasyPark = $false
    $deployRoborock = $false

    foreach ($fileName in $ChangedFiles) {
        $path = ([string]$fileName).Replace("\", "/").Trim()
        if (-not $path) { continue }

        if ($path -eq "docker-compose.qnap.yml" -or $path -eq ".dockerignore") {
            $deployAll = $true
        }
        elseif ($path -eq "Caddyfile.core") {
            [void]$services.Add("fibaro10")
        }
        elseif ($path -eq "Caddyfile") {
            [void]$services.Add("fibaro10_proxy")
        }
        elseif ($path -match '^easypark_downloader/') {
            $deployEasyPark = $true
        }
        elseif ($path -match '^roborock_logger/') {
            $deployRoborock = $true
        }
        elseif ($path -match '^microapp_backend/') {
            foreach ($service in $microApps) { [void]$services.Add($service) }
            foreach ($service in @("fibaro10", "shell_app", "online_dashboard")) {
                [void]$services.Add($service)
            }
        }
        elseif ($path -match '^packages/mobile-appkit/') {
            foreach ($service in @("online_dashboard", "maintenance_mobile", "alarm_mobile")) {
                [void]$services.Add($service)
            }
        }
        elseif ($path -match '^packages/') {
            foreach ($service in $microApps) { [void]$services.Add($service) }
            [void]$services.Add("shell_app")
        }
        elseif ($path -match '^(revenue_app|parking_app|sun_app|energy_app|operations_app|maintenance_app|system_app|link_app|shell_app|owntracks_service|unifi_protect_events|visual_anomaly_service|online_dashboard|maintenance_mobile|alarm_mobile|fibaro10ipad|axis_camera_snapshots|car_info_lookup|sun2_backfill_downloader|sun2_importer|sun2_session_scraper|parking_sun_linker)/') {
            [void]$services.Add($Matches[1])
        }
        elseif ($path -match '^(desktop_v2|templates|migrations)/' -or $path -eq "Dockerfile" -or $path -eq "requirements.txt" -or $path -eq "BUILD" -or $path -match '^[^/]+\.py$') {
            [void]$services.Add("fibaro10")
        }
        elseif ($path -match '^static/') {
            foreach ($service in @("fibaro10", "online_dashboard", "maintenance_mobile", "alarm_mobile", "fibaro10ipad")) {
                [void]$services.Add($service)
            }
        }
        elseif ($path -match '^(scripts|tests|docs|deploy|browser_extensions|hc3_vedlikehold|mqtt|v1_reference)/' -or $path -match '^\.(github|audit-cache)/' -or $path -match '^(README|AGENTS|CHANGELOG)' -or $path -match '^\.git') {
            continue
        }
        else {
            Write-Warning "Unknown deploy impact for '$path'; rebuilding the complete stack."
            $deployAll = $true
        }
    }

    if ($deployAll) {
        foreach ($service in $allServices) { [void]$services.Add($service) }
    }

    [pscustomobject]@{
        All = $deployAll
        Services = @($allServices | Where-Object { $services.Contains($_) })
        EasyPark = $deployEasyPark
        Roborock = $deployRoborock
    }
}
