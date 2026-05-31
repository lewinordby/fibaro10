param(
    [string]$InternalUrl = "http://192.168.20.218:8110/health",
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
Check-Endpoint "online_dashboard" $OnlineUrl
