param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteCertificate = "/share/CACHEDEV1_DATA/Public/Fibaro10-HTTPS/fibaro10-internal-ca.crt",
    [string]$HttpsUrl = "https://192.168.20.218:8443/health"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Missing SSH identity file: $IdentityFile"
}

$targetDirectory = Join-Path $env:LOCALAPPDATA "Lilletorget\certificates"
$targetCertificate = Join-Path $targetDirectory "fibaro10-internal-ca.crt"
New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null

& scp -i $IdentityFile -o BatchMode=yes "${QnapHost}:$RemoteCertificate" $targetCertificate
if ($LASTEXITCODE -ne 0) {
    throw "Could not download the Fibaro10 internal CA certificate from QNAP."
}

& certutil.exe -user -addstore Root $targetCertificate | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the Fibaro10 internal CA certificate."
}

$response = Invoke-WebRequest -UseBasicParsing -Uri $HttpsUrl -TimeoutSec 20
if ([int]$response.StatusCode -ne 200) {
    throw "$HttpsUrl returned HTTP $($response.StatusCode)"
}

Write-Host "Fibaro10 internal HTTPS is trusted: $HttpsUrl"
Write-Host "Certificate: $targetCertificate"
