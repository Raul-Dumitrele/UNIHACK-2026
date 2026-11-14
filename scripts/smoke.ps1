# Seed the demo data, start the API, check /health and the demo project's documents, then optional e2e and web checks. Stops at the first error. Run from repo root.
$ErrorActionPreference = "Stop"
$py = "backend/.venv/Scripts/python.exe"
& $py -m backend.seed.run | Out-Null
if ($LASTEXITCODE) { Write-Host "[FAIL] seed"; exit 1 }
Write-Host "[OK] seed"
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

    # Documents of the seeded demo project (author demo-user-5): plan, DXF, PDF and material list.
    $h = @{ "X-User-Id" = "demo-user-5" }
    foreach ($doc in "plan.svg", "plan.dxf", "dosar.pdf", "materiale.csv") {
        try { $d = Invoke-WebRequest "http://127.0.0.1:8765/proiecte/demo-proiect-1/documente/$doc" -Headers $h -UseBasicParsing }
        catch { Write-Host "[FAIL] document $doc ($($_.Exception.Message))"; exit 1 }
        if ($d.StatusCode -ne 200 -or $d.RawContentLength -lt 100) { Write-Host "[FAIL] document $doc"; exit 1 }
    }
    Write-Host "[OK] documents (plan.svg, plan.dxf, dosar.pdf, materiale.csv)"

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
