param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [switch]$SkipLocalChecks
)

& (Join-Path $PSScriptRoot "deploy-domain-app-qnap.ps1") `
    -App parking_app `
    -QnapHost $QnapHost `
    -IdentityFile $IdentityFile `
    -RemoteDir $RemoteDir `
    -Docker $Docker `
    -SkipLocalChecks:$SkipLocalChecks
exit $LASTEXITCODE
