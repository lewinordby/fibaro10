param(
    [string[]]$Urls = @(
        "http://192.168.20.218:8110/health",
        "https://online.lilletorget.net/health",
        "https://online.lilletorget.net/",
        "https://online.lilletorget.net/soling",
        "https://online.lilletorget.net/parkering"
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
