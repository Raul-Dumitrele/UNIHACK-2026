# One-time local setup: venv + backend deps + git hooks. Run from repo root.
$ErrorActionPreference = "Stop"
function Run { & $args[0] $args[1..($args.Count-1)]; if ($LASTEXITCODE) { throw "failed: $args" } }
$py = "backend/.venv/Scripts/python.exe"
if (-not (Test-Path backend/.venv)) { python -m venv backend/.venv }
Run $py -m pip install -q --upgrade pip
Run $py -m pip install -q -r backend/requirements.txt

# Windows Smart App Control blocks SQLAlchemy's freshly downloaded compiled
# extensions (.pyd). Swap in the official pure-Python wheel of the same version.
$sqla = (Select-String -Path backend/requirements.txt -Pattern '^sqlalchemy==(.+)$').Matches[0].Groups[1].Value
$tmp = Join-Path $env:TEMP "loccomun-sqla"
Run $py -m pip download -q "sqlalchemy==$sqla" --no-deps --only-binary :all: --platform any -d $tmp
Run $py -m pip install -q --force-reinstall --no-deps (Get-ChildItem $tmp -Filter "sqlalchemy-$sqla-py3-none-any.whl").FullName
Run $py -c "import sqlalchemy, sqlmodel; print('sqlalchemy', sqlalchemy.__version__, 'ok')"

git config core.hooksPath .githooks
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env from .env.example - set GEMINI_API_KEY" }
Write-Host "Setup done. Next: scripts/test.ps1"
