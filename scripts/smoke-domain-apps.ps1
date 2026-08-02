param(
    [string]$HostAddress = "192.168.20.218",
    [string]$CredentialFile = ".env.live-smoke",
    [int]$WarnAfterMs = 1500,
    [int]$FailAfterMs = 10000
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$credentialPath = Join-Path $repoRoot $CredentialFile

if (-not (Test-Path -LiteralPath $credentialPath)) {
    throw "Mangler $credentialPath. Kjør scripts/provision-live-smoke-user.ps1 først."
}

$credentials = @{}
foreach ($line in Get-Content -LiteralPath $credentialPath) {
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { continue }
    $key, $value = $line -split "=", 2
    $credentials[$key.Trim()] = $value.Trim()
}

$username = $credentials["FIBARO10_LIVE_USERNAME"]
$password = $credentials["FIBARO10_LIVE_PASSWORD"]
if (-not $username -or -not $password) {
    throw "Credential-filen mangler FIBARO10_LIVE_USERNAME eller FIBARO10_LIVE_PASSWORD."
}

$genericApps = @(
    @{ Name = "Soling"; Port = 8153; Source = "sun_app/frontend/src/main.tsx" },
    @{ Name = "Energi"; Port = 8154; Source = "energy_app/frontend/src/main.tsx" },
    @{ Name = "Bygg og drift"; Port = 8155; Source = "operations_app/frontend/src/main.tsx" },
    @{ Name = "Vedlikehold"; Port = 8156; Source = "maintenance_app/frontend/src/main.tsx" },
    @{ Name = "System"; Port = 8157; Source = "system_app/frontend/src/main.tsx" },
    @{ Name = "Koble"; Port = 8158; Source = "link_app/frontend/src/main.tsx" }
)

$customChecks = @(
    @{ App = "Omsetning"; Port = 8151; Route = "/"; Endpoint = "/api/overview"; Kind = "json" },
    @{ App = "Omsetning"; Port = 8151; Route = "/oversikt"; Endpoint = "/api/modules/omsetning?view=oversikt"; Kind = "module" },
    @{ App = "Omsetning"; Port = 8151; Route = "/sammenligning"; Endpoint = "/api/status/comparison"; Kind = "json" },
    @{ App = "Omsetning"; Port = 8151; Route = "/ar"; Endpoint = "/api/omsetning/year-comparison"; Kind = "json" },
    @{ App = "Omsetning"; Port = 8151; Route = "/maned"; Endpoint = "/api/revenue/month"; Kind = "json" },
    @{ App = "Parkering"; Port = 8152; Route = "/"; Endpoint = "/api/modules/parkering?view=oversikt"; Kind = "module" },
    @{ App = "Parkering"; Port = 8152; Route = "/parkeringer"; Endpoint = "/api/modules/parkering?view=parkeringer"; Kind = "module" },
    @{ App = "Parkering"; Port = 8152; Route = "/dagslinje"; Endpoint = "/api/modules/parkering?view=dagslinje"; Kind = "module" },
    @{ App = "Parkering"; Port = 8152; Route = "/kjoretoy"; Endpoint = "/api/modules/parkering?view=kjoretoy"; Kind = "module" },
    @{ App = "Parkering"; Port = 8152; Route = "/omrade"; Endpoint = "/api/modules/parkering?view=omrade"; Kind = "module" },
    @{ App = "Parkering"; Port = 8152; Route = "/prognose"; Endpoint = "/api/modules/parkering?view=prognose"; Kind = "module" },
    @{ App = "Parkering"; Port = 8152; Route = "/oppgjor"; Endpoint = "/api/modules/parkering?view=oppgjor"; Kind = "module" },
    @{ App = "Parkering"; Port = 8152; Route = "/arsutvikling"; Endpoint = "/api/parkering/year-comparison"; Kind = "json" },
    @{ App = "Parkering"; Port = 8152; Route = "/tidspunkt"; Endpoint = "/api/parkering/time-distribution"; Kind = "json" },
    @{ App = "Parkering"; Port = 8152; Route = "/ukesnitt"; Endpoint = "/api/parkering/weekly-averages"; Kind = "json" },
    @{ App = "Parkering"; Port = 8152; Route = "/bilstatistikk"; Endpoint = "/api/modules/parkering?view=bilstatistikk"; Kind = "module" },
    @{ App = "Parkering"; Port = 8152; Route = "/oppslag"; Endpoint = "/api/modules/parkering?view=oppslag"; Kind = "module" }
)

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -UseBasicParsing -Uri "http://${HostAddress}:8151/auth/login" -Method Post -Body @{
    username = $username
    password = $password
} -WebSession $session -MaximumRedirection 5 -TimeoutSec 30 | Out-Null

$results = [System.Collections.Generic.List[object]]::new()

function Invoke-DomainCheck([string]$App, [int]$Port, [string]$Route, [string]$Endpoint, [string]$Kind) {
    $uri = "http://${HostAddress}:$Port$Endpoint"
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $payload = Invoke-RestMethod -Uri $uri -WebSession $session -TimeoutSec 90
        $stopwatch.Stop()
        $valid = $null -ne $payload
        if ($Kind -eq "module") {
            $valid = $null -ne $payload.title -and $null -ne $payload.tables
        } elseif ($Kind -eq "operations") {
            $valid = $null -ne $payload.generatedAt -and $null -ne $payload.services
        }
        if (-not $valid) { throw "Svaret mangler obligatoriske felt" }
        $status = if ($stopwatch.ElapsedMilliseconds -gt $FailAfterMs) { "FEIL: over ${FailAfterMs} ms" } else { "OK" }
        $performance = if ($stopwatch.ElapsedMilliseconds -gt $FailAfterMs) { "KRITISK" } elseif ($stopwatch.ElapsedMilliseconds -gt $WarnAfterMs) { "TREG" } else { "BRA" }
        $results.Add([pscustomobject]@{ App = $App; Route = $Route; Status = $status; Ytelse = $performance; Ms = $stopwatch.ElapsedMilliseconds })
    } catch {
        $stopwatch.Stop()
        $results.Add([pscustomobject]@{ App = $App; Route = $Route; Status = "FEIL: $($_.Exception.Message)"; Ytelse = "-"; Ms = $stopwatch.ElapsedMilliseconds })
    }
}

foreach ($port in 8150..8158) {
    Invoke-DomainCheck -App "Tjeneste $port" -Port $port -Route "/ready" -Endpoint "/ready" -Kind "json"
}

foreach ($check in $customChecks) {
    Invoke-DomainCheck -App $check.App -Port $check.Port -Route $check.Route -Endpoint $check.Endpoint -Kind $check.Kind
}

foreach ($app in $genericApps) {
    $sourcePath = Join-Path $repoRoot $app.Source
    foreach ($line in Get-Content -LiteralPath $sourcePath -Encoding UTF8) {
        if ($line -notmatch 'to:\s*"(?<route>[^"]+)".*module:\s*"(?<module>[^"]+)".*view:\s*"(?<view>[^"]+)"') { continue }
        $route = $Matches.route
        $module = $Matches.module
        $view = $Matches.view
        $endpoint = if ($module -eq "status" -and $view -eq "drift") { "/api/overview" } else { "/api/modules/$([uri]::EscapeDataString($module))?view=$([uri]::EscapeDataString($view))" }
        $kind = if ($endpoint -eq "/api/overview") { "operations" } else { "module" }
        Invoke-DomainCheck -App $app.Name -Port $app.Port -Route $route -Endpoint $endpoint -Kind $kind
    }
}

$results | Format-Table -AutoSize
$failed = @($results | Where-Object { $_.Status -ne "OK" })
$slow = @($results | Where-Object { $_.Ytelse -eq "TREG" })
$successfulTimes = @($results | Where-Object { $_.Status -eq "OK" } | ForEach-Object { [int]$_.Ms } | Sort-Object)
if ($successfulTimes.Count -gt 0) {
    $p50 = $successfulTimes[[math]::Floor(($successfulTimes.Count - 1) * 0.50)]
    $p95 = $successfulTimes[[math]::Floor(($successfulTimes.Count - 1) * 0.95)]
    Write-Host "Ytelse: p50 ${p50} ms, p95 ${p95} ms, $($slow.Count) over varselgrensen på ${WarnAfterMs} ms."
}
if ($failed.Count -gt 0) {
    throw "$($failed.Count) av $($results.Count) kontroller feilet."
}

Write-Host "$($results.Count) readiness- og rutekontroller fullført uten feil."
