param([string]$UbuntuDistribution = "Ubuntu")
$ErrorActionPreference = "Stop"
$workspace = Split-Path $PSScriptRoot -Parent
$python = Join-Path $workspace "venv\Scripts\python.exe"
$registry = Join-Path $workspace "registry"
$logs = Join-Path $registry "logs"
if (-not (Test-Path -LiteralPath $python)) { throw "The project venv is missing." }
New-Item -ItemType Directory -Path $logs -Force | Out-Null
# Keep the existing Redis daemon's WSL runtime alive without changing Redis settings.
$runtime = Start-Process -FilePath "wsl.exe" -ArgumentList @("-d", $UbuntuDistribution, "--", "sh", "-lc", '"redis-cli ping >/dev/null && exec sleep infinity"') -WindowStyle Hidden -PassThru
Push-Location $registry
try {
    $inspection = @'
import os,json,sys,time
os.environ.setdefault("DJANGO_SETTINGS_MODULE","registry.settings")
import django; django.setup()
from registry.celery import app
from django.conf import settings
connected=False
for attempt in range(10):
    try:
        with app.connection_for_read(connect_timeout=2) as connection:
            connection.ensure_connection(max_retries=0)
        connected=True; break
    except Exception:
        time.sleep(1)
if not connected:
    print("Local broker is unreachable; verify Ubuntu Redis.",file=sys.stderr); sys.exit(2)
queues=app.control.inspect(timeout=3).active_queues() or {}
print(json.dumps({"queue":settings.PRESCRIPTION_EXTRACTION_QUEUE,"workers":sum(any(q.get("name")==settings.PRESCRIPTION_EXTRACTION_QUEUE for q in value) for value in queues.values())}))
'@
    $stateText = & $python -c $inspection
    if ($LASTEXITCODE -ne 0) { throw "Broker verification failed." }
    $state = $stateText | ConvertFrom-Json
    if ($state.workers -gt 0) {
        Stop-Process -Id $runtime.Id -ErrorAction SilentlyContinue
        Write-Output "An extraction worker is already running. No duplicate worker started."
        return
    }
    $worker = Start-Process -FilePath $python -ArgumentList @("-m", "celery", "-A", "registry", "worker", "--pool=solo", "--concurrency=1", "--queues=$($state.queue)", "--hostname=prescription-extraction@%h", "--loglevel=WARNING") -WorkingDirectory $registry -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs "prescription-worker.stdout.log") -RedirectStandardError (Join-Path $logs "prescription-worker.stderr.log") -PassThru
    @{ worker_pid=$worker.Id; redis_runtime_pid=$runtime.Id; queue=$state.queue } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logs "prescription-worker-processes.json")
    Write-Output "Started the local extraction worker. Health is verified separately; process creation alone is not readiness."
} catch {
    Stop-Process -Id $runtime.Id -ErrorAction SilentlyContinue
    throw
} finally {
    Pop-Location
}
