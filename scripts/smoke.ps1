# Start the API, check /health, stop it. Exit 0 on success. Run from repo root.
$ErrorActionPreference = "Stop"
$py = "backend/.venv/Scripts/python.exe"
$p = Start-Process -FilePath $py -ArgumentList "-m","uvicorn","backend.app.main:app","--port","8765" -PassThru -WindowStyle Hidden
try {
    $ok = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try { $r = Invoke-RestMethod http://127.0.0.1:8765/health; if ($r.status -eq "ok") { $ok = $true; break } } catch {}
    }
    if ($ok) { Write-Host "[OK] /health"; exit 0 } else { Write-Host "[FAIL] /health"; exit 1 }
} finally { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
