function Invoke-ProjectScript([string]$Name, [hashtable]$Parameters = @{}) {
    $scriptPath = Join-Path $PSScriptRoot $Name
    if (-not (Test-Path -LiteralPath $scriptPath)) { throw "Missing project script: $Name" }
    $global:LASTEXITCODE = 0
    & $scriptPath @Parameters
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}
