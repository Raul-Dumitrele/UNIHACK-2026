"""Example schematic plans for web/mobile, one per kind of proposal (offline, deterministic):
    python -m backend.seed.export_planuri
Output in backend/seed/data/exemple/:
- plan_<tip>_<mp>mp.{json,svg,dxf}: the Scene (build_scene) for every kind on the demo plot (600 m²), plus
  276 m² lots 12 m wide like those on the city hall's list;
- proiect_demo_*: the demo project's GET /proiecte/{id}/plan and /materiale bodies and its four documents
  (plan.svg, plan.dxf, dosar.pdf, materiale.csv), for web/mobile mocks of the "Documente" tab.
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


def build_project_examples() -> dict[str, bytes]:
    """The demo project's documents, exactly as GET /proiecte/{id}/... returns them (offline, no AI)."""
    from backend.ai.proiect.documente import build_documente, materiale_json, plan_json
    from backend.seed.export_examples import build_examples as contract_examples

    data = contract_examples()
    proiect = data["proiecte"][0]
    space = next(s for s in data["teren_liber"] if s["id"] == proiect["space_id"])
    files = {"proiect_demo_plan.json": plan_json(proiect, space),
             "proiect_demo_materiale.json": materiale_json(proiect, space)}
    out = {name: (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8") for name, doc in files.items()}
    for name, (content, _media) in build_documente(proiect, space).items():
        out[f"proiect_demo_{name.replace('.', '_', name.count('.') - 1)}"] = content
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {**build_examples(), **build_project_examples()}
    for stale in [*OUT.glob("plan_*"), *OUT.glob("proiect_demo_*")]:
        if stale.name not in files:
            stale.unlink()
    for name, content in files.items():
        (OUT / name).write_bytes(content)  # bytes: identical on every OS (no newline translation)
    print(f"wrote {len(files)} files to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
