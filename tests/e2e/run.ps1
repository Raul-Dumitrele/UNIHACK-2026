# Wrapper for: python -m pytest tests/e2e (uses the backend venv). Works from any directory.
$root = Resolve-Path (Join-Path $PSScriptRoot "../..")
$py = @("backend/.venv/Scripts/python.exe", "backend/.venv/bin/python") |
    ForEach-Object { Join-Path $root $_ } | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $py) { Write-Error "backend venv not found; run scripts/setup.ps1 first"; exit 1 }
Push-Location $root
try { & $py -m pytest tests/e2e @args; exit $LASTEXITCODE } finally { Pop-Location }
