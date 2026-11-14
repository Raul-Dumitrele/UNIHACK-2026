"""Fill the answer cache for the demo, so the presentation does not depend on live APIs.

    python -m backend.ai.llm.pregenerate

Runs the real P3 functions on the demo data (seed ideas, owner messages for the seeded spaces, the demo
project's dossier) through the LLM chain with the cache on. At demo time the same prompts hit the cache.
Only demo data is sent to providers.
"""
import sys
from datetime import date

from backend.ai import owner_message, structure_idea
from backend.ai.costs import estimate_cost
from backend.ai.llm import reset_chain
from backend.ai.proiect import generate_dosar
from backend.ai.references import find_references
from backend.seed.build import build_seed
from backend.seed.contract import contract_rows


def main() -> int:
    reset_chain()
    data = build_seed(date.today())
    rows = contract_rows(data)
    done = 0
    for idea in data.ideas:
        structure_idea(idea["text"])
        done += 1
    spaces = {s["id"]: s for s in rows["Space"]}
    for idea in rows["Idea"]:
        if idea["stare"] == "prag_atins":
            space = next((s for s in rows["Space"] if s["sloturi"]), None)
            if space:
                owner_message(idea, space, space["sloturi"][0])
                done += 1
    for p in rows["Proiect"]:
        idea = next(i for i in rows["Idea"] if i["id"] == p["idea_id"])
        refs = find_references(p["tip_amenajare"], p["suprafata_mp"])
        generate_dosar(idea, spaces[p["space_id"]], p["tip_amenajare"], p["suprafata_mp"], refs,
                       estimate_cost(refs, p["suprafata_mp"]))
        done += 1
    print(f"pregenerate: {done} răspunsuri cerute (cele reușite sunt acum în backend/ai/llm/cache/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
