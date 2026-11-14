"""Check the hand-collected reference base and report rejected entries.
    python -m backend.ai.references.validate          (exit code 1 if anything is rejected)
"""
import sys
from collections.abc import Iterable
from pathlib import Path

from backend.ai.references.core import data_files, read_file


def validate(paths: Iterable[Path] | None = None) -> tuple[dict[str, dict], list[tuple[str, str, str]]]:
    """Per file: counts of valid / usable-for-cost entries; plus (file, id, reason) for rejections."""
    report: dict[str, dict] = {}
    rejected: list[tuple[str, str, str]] = []
    for path in paths if paths is not None else data_files():
        valid, bad = read_file(path)
        report[path.stem] = {
            "valide": len(valid),
            "cu_cost_si_suprafata": sum(r.usable_for_cost for r in valid),
            "surse": sorted({r.sursa_tip for r in valid}),
        }
        rejected += [(path.name, rid, reason) for rid, reason in bad]
    return report, rejected


def main() -> int:
    report, rejected = validate()
    width = max(map(len, report), default=10)
    print(f"{'tip':<{width}}  valide  cu cost+suprafață  surse")
    for tip, r in report.items():
        print(f"{tip:<{width}}  {r['valide']:>6}  {r['cu_cost_si_suprafata']:>17}  {', '.join(r['surse']) or '-'}")
    if rejected:
        print(f"\nRespinse ({len(rejected)}):")
        for name, rid, reason in rejected:
            print(f"  {name} / {rid}: {reason}")
        return 1
    print("\nNicio intrare respinsă.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
