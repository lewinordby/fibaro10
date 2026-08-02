param(
    [string]$HostAddress = "192.168.20.218",
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [int]$Retries = 3,
    [int]$DelaySeconds = 2,
    [switch]$SkipContainerCheck
)

$ErrorActionPreference = "Stop"

$checks = @(
    @{ Name = "fibaro10"; Url = "http://${HostAddress}:8110/health?details=true"; Kind = "core" },
    @{ Name = "shell_app"; Url = "http://${HostAddress}:8150/health"; Kind = "ok" },
    @{ Name = "revenue_app"; Url = "http://${HostAddress}:8151/health"; Kind = "ok" },
    @{ Name = "parking_app"; Url = "http://${HostAddress}:8152/health"; Kind = "ok" },
    @{ Name = "sun_app"; Url = "http://${HostAddress}:8153/health"; Kind = "ok" },
    @{ Name = "energy_app"; Url = "http://${HostAddress}:8154/health"; Kind = "ok" },
    @{ Name = "operations_app"; Url = "http://${HostAddress}:8155/health"; Kind = "ok" },
    @{ Name = "maintenance_app"; Url = "http://${HostAddress}:8156/health"; Kind = "ok" },
    @{ Name = "system_app"; Url = "http://${HostAddress}:8157/health"; Kind = "ok" },
    @{ Name = "link_app"; Url = "http://${HostAddress}:8158/health"; Kind = "ok" },
    @{ Name = "owntracks_service"; Url = "http://${HostAddress}:8128/health"; Kind = "ok" },
    @{ Name = "unifi_protect_events"; Url = "http://${HostAddress}:8130/ready"; Kind = "ok" },
    @{ Name = "axis_camera_snapshots"; Url = "http://${HostAddress}:8125/health"; Kind = "ok" },
    @{ Name = "car_info_lookup"; Url = "http://${HostAddress}:8126/health"; Kind = "ok" },
    @{ Name = "parking_sun_linker"; Url = "http://${HostAddress}:8127/health"; Kind = "ok" },
    @{ Name = "sun2_importer"; Url = "http://${HostAddress}:8096/json"; Kind = "job" },
    @{ Name = "sun2_backfill_downloader"; Url = "http://${HostAddress}:8097/json"; Kind = "job" },
    @{ Name = "sun2_session_scraper"; Url = "http://${HostAddress}:8099/json"; Kind = "job" },
    @{ Name = "easypark_downloader"; Url = "http://${HostAddress}:8109/health"; Kind = "ok" },
    @{ Name = "roborock_logger"; Url = "http://${HostAddress}:8095/health"; Kind = "ok" },
    @{ Name = "online_dashboard"; Url = "https://online.lilletorget.net/health"; Kind = "ok" },
    @{ Name = "owntracks_proxy"; Url = "https://owntracks.lilletorget.net/health"; Kind = "ok" },
    @{ Name = "maintenance_mobile"; Url = "https://vedl.lilletorget.net/health"; Kind = "ok" },
    @{ Name = "fibaro10ipad"; Url = "https://ipad.lilletorget.net/health"; Kind = "ok" }
)

function Test-Payload($Payload, [string]$Kind) {
    if ($null -eq $Payload) {
        throw "Tomt JSON-svar"
    }

    if ($Kind -eq "core") {
        if ($Payload.checks.database.status -ne "ok") {
            throw "Databasen er ikke frisk"
        }
        if ([int]$Payload.summary.sources.total -le 0) {
            throw "Ingen datakilder ble kontrollert"
        }
        if ([int]$Payload.summary.sources.bad -gt 0 -or [int]$Payload.summary.sources.unknown -gt 0) {
            throw "En eller flere datakilder har feil eller ukjent status"
        }
        return "kilder: $($Payload.summary.sources.ok) OK, $($Payload.summary.sources.warn) varsel"
    }

    if ($Payload.PSObject.Properties.Name -contains "ok" -and $Payload.ok -ne $true) {
        throw "Tjenesten rapporterer ok=false"
    }
    if ($Payload.PSObject.Properties.Name -contains "status" -and $Payload.status -in @("bad", "error", "failed")) {
        throw "Tjenesten rapporterer status=$($Payload.status)"
    }

    $lastError = $null
    if ($Payload.PSObject.Properties.Name -contains "last_error") {
        $lastError = $Payload.last_error
    } elseif ($Payload.PSObject.Properties.Name -contains "state" -and $Payload.state.PSObject.Properties.Name -contains "last_error") {
        $lastError = $Payload.state.last_error
    }
    if ($lastError) {
        throw "Siste jobbfeil: $lastError"
    }
    return "OK"
}

function Check-Endpoint($Check) {
    $lastError = $null
    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Check.Url -TimeoutSec 30
            $stopwatch.Stop()
            if ($response.StatusCode -ne 200) {
                throw "HTTP $($response.StatusCode)"
            }
            $payload = $response.Content | ConvertFrom-Json
            $detail = Test-Payload $payload $Check.Kind
            return [pscustomobject]@{
                Name = $Check.Name
                Status = "OK"
                Ms = $stopwatch.ElapsedMilliseconds
                Detail = $detail
            }
        } catch {
            $lastError = $_.Exception.Message
        }
        if ($attempt -lt $Retries) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    throw "$($Check.Name) health check failed: $lastError"
}

$httpResults = foreach ($check in $checks) {
    Check-Endpoint $check
}
$httpResults | Format-Table -AutoSize

if (-not $SkipContainerCheck) {
    if (-not (Test-Path -LiteralPath $IdentityFile)) {
        throw "Mangler SSH-nokkel for containerkontroll: $IdentityFile"
    }
    $expectedContainers = @(
        "postgres-1", "owntracks_postgres", "owntracks_service", "fibaro10", "shell_app",
        "revenue_app", "parking_app", "sun_app", "energy_app", "operations_app",
        "maintenance_app", "system_app", "link_app", "online_dashboard", "maintenance_mobile",
        "fibaro10ipad", "axis_camera_snapshots", "car_info_lookup", "sun2_backfill_downloader",
        "sun2_importer", "sun2_session_scraper", "parking_sun_linker", "unifi_protect_events",
        "visual_anomaly_service", "easypark_downloader", "roborock_logger", "fibaro10_proxy"
    )
    $remote = @"
set -e
for name in $($expectedContainers -join " "); do
    if ! "$Docker" inspect "`$name" >/dev/null 2>&1; then
        echo "`$name|missing|missing"
        continue
    fi
    "$Docker" inspect --format '{{.Name}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "`$name" | sed 's#^/##'
done
"@
    $remote = $remote -replace "`r`n", "`n" -replace "`r", "`n"
    $containerLines = & ssh -i $IdentityFile -o BatchMode=yes -o ConnectTimeout=8 $QnapHost $remote
    if ($LASTEXITCODE -ne 0) {
        throw "Kunne ikke kontrollere containere paa QNAP."
    }
    $containerResults = foreach ($line in $containerLines) {
        $name, $state, $health = $line -split "\|", 3
        $valid = $state -eq "running" -and $health -in @("healthy", "none")
        [pscustomobject]@{
            Name = $name
            State = $state
            Health = $health
            Status = if ($valid) { "OK" } else { "FEIL" }
        }
    }
    $containerResults | Format-Table -AutoSize
    $containerFailures = @($containerResults | Where-Object { $_.Status -ne "OK" })
    if ($containerFailures.Count -gt 0) {
        throw "$($containerFailures.Count) forventede containere mangler eller er ikke friske."
    }
}

Write-Host "$($httpResults.Count) HTTP-kontroller og komplett containerkontroll fullfort uten feil."
