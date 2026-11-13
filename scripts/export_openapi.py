"""Write the FastAPI OpenAPI schema to docs/openapi.json (run from repo root)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.main import app  # noqa: E402

out = ROOT / "docs" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {out}")
