param(
    [Parameter(Mandatory = $true)][string]$HostName,
    [string]$UserName = 'linux1',
    [Parameter(Mandatory = $true)][string]$KeyPath
)
$ErrorActionPreference = 'Stop'
if ($HostName -notmatch '^[a-zA-Z0-9.-]+$' -or $UserName -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid SSH host or user.' }
$projectDirectory = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectDirectory
$resolvedKeyPath = (Resolve-Path -LiteralPath $KeyPath).Path
python -m tradeoff package
if ($LASTEXITCODE -ne 0) { throw 'Source packaging failed.' }
# Deliberately retain normal SSH host-key verification. Accept the expected
# fingerprint only after checking it in your VM portal.
$sshTarget = "$UserName@$HostName"
scp -i $resolvedKeyPath 'dist/tradeoff-source.zip' "${sshTarget}:/tmp/tradeoff-source.zip"
if ($LASTEXITCODE -ne 0) { throw 'SSH source upload failed.' }
$remoteCommand = @'
set -eu
work_dir=$(mktemp -d /tmp/tradeoff-install.XXXXXX)
python3 -m zipfile -e /tmp/tradeoff-source.zip "$work_dir"
sudo bash "$work_dir/infra/install_linuxone.sh"
'@
$remoteCommand | ssh -i $resolvedKeyPath $sshTarget 'bash -s'
if ($LASTEXITCODE -ne 0) { throw 'Remote installation failed; inspect the output.' }
