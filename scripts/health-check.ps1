param(
    [string]$InternalUrl = "http://192.168.20.218:8110/health",
    [string]$RevenueUrl = "http://192.168.20.218:8151/health",
    [string]$ParkingUrl = "http://192.168.20.218:8152/health",
    [string]$SunUrl = "http://192.168.20.218:8153/health",
    [string]$EnergyUrl = "http://192.168.20.218:8154/health",
    [string]$OperationsUrl = "http://192.168.20.218:8155/health",
    [string]$MaintenanceUrl = "http://192.168.20.218:8156/health",
    [string]$SystemUrl = "http://192.168.20.218:8157/health",
    [string]$LinkUrl = "http://192.168.20.218:8158/health",
    [string]$ShellUrl = "http://192.168.20.218:8150/health",
    [string]$OnlineUrl = "https://online.lilletorget.net/health",
    [int]$Retries = 8,
    [int]$DelaySeconds = 3
)

$ErrorActionPreference = "Stop"

function Check-Endpoint($Name, $Url) {
    $lastError = $null
    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 20
            if ($response.StatusCode -eq 200) {
                return [pscustomobject]@{
                    Name = $Name
                    StatusCode = $response.StatusCode
                    Content = $response.Content
                }
            }
            $lastError = "$Name returned HTTP $($response.StatusCode)"
        } catch {
            $lastError = $_.Exception.Message
        }
        if ($attempt -lt $Retries) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    throw "$Name health check failed: $lastError"
}

Check-Endpoint "fibaro10" $InternalUrl
Check-Endpoint "shell_app" $ShellUrl
Check-Endpoint "revenue_app" $RevenueUrl
Check-Endpoint "parking_app" $ParkingUrl
Check-Endpoint "sun_app" $SunUrl
Check-Endpoint "energy_app" $EnergyUrl
Check-Endpoint "operations_app" $OperationsUrl
Check-Endpoint "maintenance_app" $MaintenanceUrl
Check-Endpoint "system_app" $SystemUrl
Check-Endpoint "link_app" $LinkUrl
Check-Endpoint "online_dashboard" $OnlineUrl
