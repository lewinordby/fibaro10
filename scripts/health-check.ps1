param(
    [string]$InternalUrl = "http://192.168.20.218:8110/health",
    [string]$OnlineUrl = "https://online.lilletorget.net/health"
)

$ErrorActionPreference = "Stop"

function Check-Endpoint($Name, $Url) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 20
    if ($response.StatusCode -ne 200) {
        throw "$Name returned HTTP $($response.StatusCode)"
    }
    [pscustomobject]@{
        Name = $Name
        StatusCode = $response.StatusCode
        Content = $response.Content
    }
}

Check-Endpoint "fibaro10" $InternalUrl
Check-Endpoint "online_dashboard" $OnlineUrl
