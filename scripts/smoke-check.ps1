param(
    [string[]]$Urls = @(
        "http://192.168.20.218:8110/health",
        "http://192.168.20.218:8170/ready",
        "http://192.168.20.218:8163/health",
        "http://192.168.20.218:8151/health",
        "http://192.168.20.218:8152/health",
        "http://192.168.20.218:8153/health",
        "http://192.168.20.218:8154/health",
        "http://192.168.20.218:8155/health",
        "http://192.168.20.218:8156/health",
        "http://192.168.20.218:8157/health",
        "http://192.168.20.218:8158/health",
        "http://192.168.20.218:8128/health",
        "http://192.168.20.218:8128/",
        "http://192.168.20.218:8130/ready",
        "http://192.168.20.218:8130/",
        "http://192.168.20.218:8125/health",
        "http://192.168.20.218:8125/",
        "http://192.168.20.218:8126/health",
        "http://192.168.20.218:8126/",
        "http://192.168.20.218:8127/health",
        "http://192.168.20.218:8127/",
        "http://192.168.20.218:8096/json",
        "http://192.168.20.218:8097/json",
        "http://192.168.20.218:8099/json",
        "http://192.168.20.218:8109/health",
        "http://192.168.20.218:8095/health",
        "http://192.168.20.218:8094/health",
        "http://192.168.20.218:8094/",
        "https://online.lilletorget.net/health",
        "https://online.lilletorget.net/",
        "https://online.lilletorget.net/soling",
        "https://online.lilletorget.net/parkering",
        "https://owntracks.lilletorget.net/health",
        "https://owntracks.lilletorget.net/",
        "https://vedl.lilletorget.net/health",
        "https://vedl.lilletorget.net/",
        "http://192.168.20.218:8114/health",
        "http://192.168.20.218:8114/"
    ),
    [int[]]$AllowedAuthStatusCodes = @(401, 403)
)

$ErrorActionPreference = "Stop"

$results = foreach ($url in $Urls) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 20
        $statusCode = [int]$response.StatusCode
        $bytes = $response.RawContentLength
    } catch [System.Net.WebException] {
        if ($_.Exception.Response -eq $null) {
            throw
        }
        $statusCode = [int]$_.Exception.Response.StatusCode
        $bytes = 0
    }

    if ($statusCode -lt 200 -or ($statusCode -ge 400 -and $statusCode -notin $AllowedAuthStatusCodes)) {
        throw "$url returned HTTP $statusCode"
    }

    [pscustomobject]@{
        Url = $url
        StatusCode = $statusCode
        Bytes = $bytes
    }
}

$results | Format-Table -AutoSize
