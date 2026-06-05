param(
    [string]$QnapAlias = "qnap-fibaro10",
    [string]$QnapDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [int]$LogLines = 25
)

$ErrorActionPreference = "Stop"

$remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
cd "$QnapDir"
echo "== Host =="
hostname
date
echo
echo "== Git =="
git status -sb
git log -1 --oneline --decorate
echo
echo "== Compose =="
"$Docker" compose -f docker-compose.qnap.yml ps
echo
echo "== Recent fibaro10 logs =="
"$Docker" logs --tail $LogLines fibaro10 || true
echo
echo "== Recent online_dashboard logs =="
"$Docker" logs --tail $LogLines online_dashboard || true
echo
echo "== Health watch =="
tail -n $LogLines /share/CACHEDEV1_DATA/Public/containerdata/logs/fibaro10-health.log 2>/dev/null || true
"@

$remote = $remote -replace "`r`n", "`n" -replace "`r", "`n"
ssh -o BatchMode=yes -o ConnectTimeout=8 $QnapAlias $remote
if ($LASTEXITCODE -ne 0) {
    throw "ssh failed with exit code $LASTEXITCODE"
}
