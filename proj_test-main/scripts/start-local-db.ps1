$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$binaryPath = Join-Path $projectRoot '.tools/mariadb-11.4.5-winx64/bin/mariadbd.exe'
$dataPath = Join-Path $projectRoot '.runtime/mariadb'
if (-not (Test-Path -LiteralPath $binaryPath) -or -not (Test-Path -LiteralPath $dataPath)) {
    throw 'Portable local MariaDB is not present. Follow docs/setup.md to configure MariaDB or Docker.'
}
$existingConnection = Get-NetTCPConnection -LocalPort 13306 -State Listen -ErrorAction SilentlyContinue
if ($existingConnection) {
    Write-Output 'Port 13306 is already listening. Check the existing instance before starting another.'
    exit 0
}
$process = Start-Process -FilePath $binaryPath -ArgumentList ('--datadir="{0}"' -f $dataPath), '--port=13306', '--bind-address=127.0.0.1', '--console' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot '.runtime/mariadb.stdout.log') -RedirectStandardError (Join-Path $projectRoot '.runtime/mariadb.stderr.log')
$process.Id | Set-Content -LiteralPath (Join-Path $projectRoot '.runtime/mariadb.pid')
Write-Output 'Started MariaDB on 127.0.0.1:13306. Credentials remain in backend/.env.'
