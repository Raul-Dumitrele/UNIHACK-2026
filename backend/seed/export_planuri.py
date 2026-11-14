"""Example schematic plans for web/mobile, one per kind of proposal (offline, deterministic):
    python -m backend.seed.export_planuri
Output: backend/seed/data/exemple/plan_<tip>_<mp>mp.{json,svg,dxf}. The JSON is the Scene (build_scene).
Sizes: the demo plot (600 m²) for every kind, plus 276 m² lots 12 m wide like those on the city hall's list.
"""
import json
from pathlib import Path

from backend.ai.proiect.design import build_plan_dxf, build_plan_svg, build_scene

OUT = Path(__file__).resolve().parent / "data" / "exemple"
CASES = [
    *[(tip, 600, None) for tip in ("skatepark", "loc_de_joaca", "parc_caini", "pista_biciclete",
                                   "gradina_comunitara", "teren_sport", "foisor", "fântână arteziană")],
    ("loc_de_joaca", 276, 12.0),
    ("gradina_comunitara", 276, 12.0),
]


def build_examples() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for tip, area, width in CASES:
        scene = build_scene(tip, area, width)
        name = f"plan_{scene.tip_amenajare}_{area}mp"
        title = f"Plan schematic: {scene.eticheta}, {area} mp"
        data = {**scene.model_dump(), "suprafata_ocupata_mp": scene.suprafata_ocupata_mp, "is_demo": True}
        files[f"{name}.json"] = (json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
        files[f"{name}.svg"] = build_plan_svg(scene, title).encode("utf-8")
        files[f"{name}.dxf"] = build_plan_dxf(scene, title).encode("ascii")
    return files


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    files = build_examples()
    for stale in OUT.glob("plan_*"):
        if stale.name not in files:
            stale.unlink()
    for name, content in files.items():
        (OUT / name).write_bytes(content)  # bytes: identical on every OS (no newline translation)
    print(f"wrote {len(files)} files to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
