param([ValidateSet("status", "logs", "stop")][string]$Action = "status", [ValidateSet("frontend", "backend")][string]$Service = "frontend")
$ErrorActionPreference = "Stop"
$workspace = Split-Path $PSScriptRoot -Parent
$logRoot = Join-Path $workspace "registry\logs"
$metadata = Join-Path $logRoot "dev-web-processes.json"
if ($Action -eq "logs") {
    Get-Content -LiteralPath (Join-Path $logRoot "dev-$Service.stdout.log"), (Join-Path $logRoot "dev-$Service.stderr.log") -Tail 30 -Wait
    return
}
if (-not (Test-Path -LiteralPath $metadata)) { throw "No managed web process record found." }
$state = Get-Content -LiteralPath $metadata -Raw | ConvertFrom-Json
$processes = @(Get-CimInstance Win32_Process)
foreach ($name in @("frontend", "backend")) {
    $registeredId = [int]$state."${name}_pid"
    $root = $processes | Where-Object ProcessId -eq $registeredId | Select-Object -First 1
    if (-not $root) { Write-Output "$name : stopped (recorded PID $registeredId)"; continue }
    $owned = ($root.ExecutablePath -and $root.ExecutablePath.StartsWith($workspace + "\", [StringComparison]::OrdinalIgnoreCase)) -or ($root.CommandLine -and $root.CommandLine.IndexOf($workspace, [StringComparison]::OrdinalIgnoreCase) -ge 0)
    if (-not $owned) { Write-Warning "$name : PID $registeredId no longer identifies a verified workspace process; refusing to stop it."; continue }
    if ($Action -eq "status") { Write-Output "$name : running (PID $registeredId, port $($state."${name}_port"))"; continue }
    $ownedTree = [System.Collections.Generic.List[object]]::new()
    $ownedTree.Add($root)
    for ($index = 0; $index -lt $ownedTree.Count; $index++) {
        foreach ($child in $processes | Where-Object ParentProcessId -eq $ownedTree[$index].ProcessId) { $ownedTree.Add($child) }
    }
    for ($index = $ownedTree.Count - 1; $index -ge 0; $index--) {
        $record = $ownedTree[$index]
        $live = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.ProcessId)"
        if ($live -and $live.CreationDate -eq $record.CreationDate) { Stop-Process -Id $live.ProcessId -ErrorAction SilentlyContinue }
    }
    Write-Output "Stopped $name and its child processes."
}
