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

$navigationPath = Join-Path $repoRoot "packages/microapp-ui/src/navigation.json"
$navigation = (Get-Content -LiteralPath $navigationPath -Raw -Encoding UTF8 | ConvertFrom-Json).apps

function Resolve-RouteCheck($app, $item) {
    $key = "$($app.id):$($item.to)"
    $special = @{
        "revenue:/" = @{ Endpoint = "/api/overview"; Kind = "json" }
        "revenue:/maned" = @{ Endpoint = "/api/revenue/month"; Kind = "json" }
        "revenue:/ar" = @{ Endpoint = "/api/omsetning/year-comparison"; Kind = "json" }
        "revenue:/sammenligning" = @{ Endpoint = "/api/status/comparison"; Kind = "json" }
        "parking:/" = @{ Endpoint = "/api/overview"; Kind = "json" }
        "parking:/periode" = @{ Endpoint = "/api/status/comparison"; Kind = "json" }
        "parking:/arsutvikling" = @{ Endpoint = "/api/parkering/year-comparison"; Kind = "json" }
        "parking:/tidspunkt" = @{ Endpoint = "/api/parkering/time-distribution"; Kind = "json" }
        "parking:/ukesnitt" = @{ Endpoint = "/api/parkering/weekly-averages"; Kind = "json" }
        "parking:/observerte-biler" = @{ Endpoint = "/api/cars/day"; Kind = "json" }
        "parking:/oppslag/navn" = @{ Endpoint = "/api/parkering/kjoretoy/mangler-navn?limit=1&offset=0"; Kind = "json" }
        "parking:/oppslag/omrade" = @{ Endpoint = "/api/parkering/kjoretoy/mangler-omrade?limit=1&offset=0"; Kind = "json" }
        "sun:/" = @{ Endpoint = "/api/overview"; Kind = "json" }
        "sun:/periode" = @{ Endpoint = "/api/status/comparison"; Kind = "json" }
        "sun:/sammenligning" = @{ Endpoint = "/api/soling/year-comparison"; Kind = "json" }
        "operations:/" = @{ Endpoint = "/api/overview"; Kind = "operations" }
    }
    if ($special.ContainsKey($key)) { return $special[$key] }
    return @{
        Endpoint = "/api/modules/$([uri]::EscapeDataString($item.module))?view=$([uri]::EscapeDataString($item.view))"
        Kind = "module"
    }
}

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

function Invoke-FrontendRouteCheck([string]$App, [int]$Port, [string]$Route) {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://${HostAddress}:$Port$Route" -WebSession $session -TimeoutSec 30
        $stopwatch.Stop()
        if ($response.StatusCode -ne 200 -or $response.Content -notmatch '<div id="root">') {
            throw "Frontend returnerte ikke app-skallet"
        }
        $results.Add([pscustomobject]@{ App = $App; Route = "$Route [side]"; Status = "OK"; Ytelse = if ($stopwatch.ElapsedMilliseconds -gt $WarnAfterMs) { "TREG" } else { "BRA" }; Ms = $stopwatch.ElapsedMilliseconds })
    } catch {
        $stopwatch.Stop()
        $results.Add([pscustomobject]@{ App = $App; Route = "$Route [side]"; Status = "FEIL: $($_.Exception.Message)"; Ytelse = "-"; Ms = $stopwatch.ElapsedMilliseconds })
    }
}

foreach ($port in 8150..8158) {
    Invoke-DomainCheck -App "Tjeneste $port" -Port $port -Route "/ready" -Endpoint "/ready" -Kind "json"
}

foreach ($app in $navigation) {
    foreach ($group in $app.groups) {
        foreach ($item in $group.items) {
            $check = Resolve-RouteCheck $app $item
            Invoke-FrontendRouteCheck -App $app.shortName -Port $app.port -Route $item.to
            Invoke-DomainCheck -App $app.shortName -Port $app.port -Route $item.to -Endpoint $check.Endpoint -Kind $check.Kind
        }
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
