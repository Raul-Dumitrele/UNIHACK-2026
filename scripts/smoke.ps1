# Start the API, check /health, then optional e2e and web checks. Stops at the first error. Run from repo root.
$ErrorActionPreference = "Stop"
$py = "backend/.venv/Scripts/python.exe"
$p = Start-Process -FilePath $py -ArgumentList "-m","uvicorn","backend.app.main:app","--port","8765" -PassThru -WindowStyle Hidden
function Step($name, [scriptblock]$cmd) {
    & $cmd
    if ($LASTEXITCODE) { Write-Host "[FAIL] $name"; exit 1 }
    Write-Host "[OK] $name"
}
try {
    $ok = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try { $r = Invoke-RestMethod http://127.0.0.1:8765/health; if ($r.status -eq "ok") { $ok = $true; break } } catch {}
    }
    if (-not $ok) { Write-Host "[FAIL] /health"; exit 1 }
    Write-Host "[OK] /health"

    if (Test-Path tests/e2e/run.ps1) {
        Step "e2e" { powershell -ExecutionPolicy Bypass -File tests/e2e/run.ps1 }
    }
    if (Test-Path web) {
        Push-Location web
        try {
            Step "web build" { npm run build }
            Step "web tsc" { npx tsc --noEmit }
        } finally { Pop-Location }
    }
    exit 0
} finally { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
