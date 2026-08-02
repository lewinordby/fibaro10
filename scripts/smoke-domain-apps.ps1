param(
    [string]$HostAddress = "192.168.20.218",
    [string]$CredentialFile = ".env.live-smoke"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$credentialPath = Join-Path $repoRoot $CredentialFile

if (-not (Test-Path -LiteralPath $credentialPath)) {
    throw "Mangler $credentialPath. Kjor scripts/provision-live-smoke-user.ps1 forst."
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

$apps = @(
    @{ Name = "Soling"; Port = 8153; Source = "sun_app/frontend/src/main.tsx" },
    @{ Name = "Energi"; Port = 8154; Source = "energy_app/frontend/src/main.tsx" },
    @{ Name = "Bygg og drift"; Port = 8155; Source = "operations_app/frontend/src/main.tsx" },
    @{ Name = "Vedlikehold"; Port = 8156; Source = "maintenance_app/frontend/src/main.tsx" },
    @{ Name = "System"; Port = 8157; Source = "system_app/frontend/src/main.tsx" },
    @{ Name = "Koble"; Port = 8158; Source = "link_app/frontend/src/main.tsx" }
)

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-WebRequest -UseBasicParsing -Uri "http://${HostAddress}:8153/auth/login" -Method Post -Body @{
    username = $username
    password = $password
} -WebSession $session -MaximumRedirection 5 -TimeoutSec 30 | Out-Null

$results = [System.Collections.Generic.List[object]]::new()
foreach ($app in $apps) {
    $sourcePath = Join-Path $repoRoot $app.Source
    foreach ($line in Get-Content -LiteralPath $sourcePath -Encoding UTF8) {
        if ($line -notmatch 'to:\s*"(?<route>[^"]+)".*module:\s*"(?<module>[^"]+)".*view:\s*"(?<view>[^"]+)"') { continue }

        $route = $Matches.route
        $module = $Matches.module
        $view = $Matches.view
        $endpoint = if ($module -eq "status" -and $view -eq "drift") {
            "/api/overview"
        } else {
            "/api/modules/$([uri]::EscapeDataString($module))?view=$([uri]::EscapeDataString($view))"
        }
        $uri = "http://${HostAddress}:$($app.Port)$endpoint"
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $payload = Invoke-RestMethod -Uri $uri -WebSession $session -TimeoutSec 90
            $stopwatch.Stop()
            $valid = if ($endpoint -eq "/api/overview") {
                $null -ne $payload.generatedAt -and $null -ne $payload.services
            } else {
                $null -ne $payload.title -and $null -ne $payload.tables
            }
            if (-not $valid) { throw "Svaret mangler obligatoriske felt" }
            $results.Add([pscustomobject]@{
                App = $app.Name
                Route = $route
                Module = "$module/$view"
                Status = "OK"
                Ms = $stopwatch.ElapsedMilliseconds
            })
        } catch {
            $stopwatch.Stop()
            $results.Add([pscustomobject]@{
                App = $app.Name
                Route = $route
                Module = "$module/$view"
                Status = "FEIL: $($_.Exception.Message)"
                Ms = $stopwatch.ElapsedMilliseconds
            })
        }
    }
}

$results | Format-Table -AutoSize
$failed = @($results | Where-Object { $_.Status -ne "OK" })
if ($failed.Count -gt 0) {
    throw "$($failed.Count) av $($results.Count) mikroappruter feilet."
}

Write-Host "$($results.Count) mikroappruter kontrollert uten feil."
