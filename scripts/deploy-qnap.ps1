param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$Git = "git",
    [string]$Branch = "main",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$RemoteBackupRoot = "/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_deploy_backups",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [switch]$SkipPush,
    [switch]$SkipSmoke,
    [switch]$SkipLocalCheck,
    [switch]$PlanOnly,
    [string[]]$ForceServices = @(),
    [switch]$ForceEasyPark,
    [switch]$ForceRoborock,
    [switch]$ForceDreame
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "deploy-plan.ps1")
. (Join-Path $PSScriptRoot "script-runtime.ps1")
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "$exe failed with exit code $LASTEXITCODE" }
}
function Remote([string]$script) {
    & ssh -i $IdentityFile -o BatchMode=yes -o ConnectTimeout=8 $QnapHost ($script.Replace("`r", ""))
    if ($LASTEXITCODE -ne 0) { throw "QNAP command failed ($LASTEXITCODE)" }
}

# These values enter a POSIX command, not just an argument array.
foreach ($value in @($RemoteDir, $RemoteBackupRoot, $Docker, $Branch)) {
    if ($value -notmatch '^[A-Za-z0-9_./-]+$') { throw "Unsupported remote path/ref: $value" }
}
if (-not (Test-Path -LiteralPath $IdentityFile)) { throw "Missing SSH identity file: $IdentityFile" }
Push-Location $repoRoot
try {
    $status = @(& $Git status --porcelain)
    if ($LASTEXITCODE -ne 0 -or $status.Count) { throw "Deploy requires a clean, committed working tree." }
    if ((& $Git branch --show-current).Trim() -ne $Branch) { throw "Deploy expects branch $Branch." }
    $targetCommit = (& $Git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Cannot resolve target revision" }
    $preflight = @"
set -e
if [ -f /opt/etc/profile ]; then . /opt/etc/profile; fi
cd '$RemoteDir'
test -z "`$(git status --porcelain --untracked-files=no)"
git rev-parse HEAD
"@
    $remoteCommit = ([string](Remote $preflight | Select-Object -Last 1)).Trim()
    if ($remoteCommit -notmatch '^[0-9a-f]{40}$') { throw "Cannot resolve a clean QNAP revision. No automatic full deploy." }
    & $Git merge-base --is-ancestor $remoteCommit $targetCommit
    if ($LASTEXITCODE -ne 0) { throw "QNAP revision is not an ancestor of the local revision. Reconcile explicitly." }
    $changedFiles = @(& $Git diff --name-only $remoteCommit $targetCommit)
    if ($LASTEXITCODE -ne 0) { throw "Cannot determine affected files" }
    $deployPlan = Get-DeployPlan -ChangedFiles $changedFiles
    $validServices = @(Get-DeployPlan -ForceAll $true).Services
    if (@($ForceServices | Where-Object { $_ -notin $validServices }).Count) { throw "Unknown forced service" }
    $deployPlan.Services = @($validServices | Where-Object { $_ -in @($deployPlan.Services + $ForceServices) })
    if ($ForceEasyPark) { $deployPlan.EasyPark = $true }
    if ($ForceRoborock) { $deployPlan.Roborock = $true }
    if ($ForceDreame) { $deployPlan.Dreame = $true }
    $deployPlan | Format-List
    if ($PlanOnly) { return }
    $broadValidation = $deployPlan.All -or $deployPlan.Services.Count -gt 4
    if (-not $SkipLocalCheck) {
        if ($broadValidation) {
            Invoke-ProjectScript "check-local.ps1"
        } else {
            Invoke-ProjectScript "check-affected.ps1" @{
                Services=$deployPlan.Services; ChangedFiles=$changedFiles;
                EasyPark=$deployPlan.EasyPark; Roborock=$deployPlan.Roborock; Dreame=$deployPlan.Dreame
            }
        }
    }
    if (-not $SkipPush) { Run $Git @("push", "origin", $Branch) }
    $targets = @($deployPlan.Services)
    if ($deployPlan.EasyPark) { $targets += "easypark_downloader" }
    if ($deployPlan.Roborock) { $targets += "roborock_logger" }
    if ($deployPlan.Dreame) { $targets += "dreame_logger" }
    # Copy only the runner; it checks the revision and performs ff-only itself.
    $remoteRunner = "$RemoteBackupRoot/deploy-release-$($targetCommit.Substring(0,12)).sh"
    Remote "mkdir -p '$RemoteBackupRoot'"
    Run "scp" @("-i", $IdentityFile, (Join-Path $PSScriptRoot "deploy-release.sh"), "${QnapHost}:$remoteRunner")
    Remote "sh '$remoteRunner' '$RemoteDir' '$RemoteBackupRoot' '$Docker' '$remoteCommit' '$targetCommit' '$Branch' $($targets -join ' ')"
    Invoke-ProjectScript "smoke-affected.ps1" @{
        Services=$deployPlan.Services; EasyPark=$deployPlan.EasyPark;
        Roborock=$deployPlan.Roborock; Dreame=$deployPlan.Dreame; SkipRoutes=[bool]$SkipSmoke
    }
} finally { Pop-Location }
