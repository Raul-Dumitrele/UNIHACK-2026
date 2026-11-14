"""Measure idea structuring against the labelled set in eval_ideas.json.

    python -m backend.ai.evaluate            # fallback only (offline)
    python -m backend.ai.evaluate --gemini   # also Gemini, if GEMINI_API_KEY is set (uses quota)
"""
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from backend.ai.config import get_settings
from backend.ai.fallback import build_fallback
from backend.ai.gemini import ask_gemini
from backend.ai.schemas import DossierBase

EVAL_FILE = Path(__file__).resolve().parent / "eval_ideas.json"


def load_cases(split: str = "ideas") -> list[dict]:
    """'ideas': the set the fallback was tuned on; 'holdout': unseen ideas (honest accuracy)."""
    return json.loads(EVAL_FILE.read_text(encoding="utf-8"))[split]


@dataclass
class Score:
    name: str
    total: int = 0
    category_ok: int = 0
    participants_total: int = 0
    participants_ok: int = 0
    setting_total: int = 0
    setting_ok: int = 0
    failed: int = 0  # Gemini returned nothing (fallback would be used)
    seconds: float = 0.0
    misses: list[str] = field(default_factory=list)

    def add(self, case: dict, d: DossierBase | None, seconds: float = 0.0) -> None:
        self.total += 1
        self.seconds += seconds
        if d is None:
            self.failed += 1
            return
        if d.category.value == case["category"]:
            self.category_ok += 1
        else:
            self.misses.append(f"{case['category']} -> {d.category.value}: {case['text'][:70]}")
        if "participants" in case:
            self.participants_total += 1
            self.participants_ok += d.expected_participants == case["participants"]
        if "setting" in case:
            self.setting_total += 1
            self.setting_ok += d.setting.value == case["setting"]

    @property
    def category_accuracy(self) -> float:
        return self.category_ok / self.total if self.total else 0.0

    def report(self) -> str:
        pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f}%)" if b else "-"  # noqa: E731
        lines = [
            f"== {self.name}",
            f"  categorie:    {pct(self.category_ok, self.total)}",
            f"  participanți: {pct(self.participants_ok, self.participants_total)}",
            f"  interior/ext: {pct(self.setting_ok, self.setting_total)}",
        ]
        if self.failed:
            lines.append(f"  fără răspuns: {self.failed}")
        if self.seconds:
            lines.append(f"  timp mediu:   {self.seconds / self.total:.1f} s")
        lines += [f"  greșit: {m}" for m in self.misses]
        return "\n".join(lines)


def evaluate_fallback(cases: list[dict], name: str = "fallback") -> Score:
    score = Score(name)
    for case in cases:
        score.add(case, build_fallback(case["text"]))
    return score


def evaluate_gemini(cases: list[dict], delay_s: float = 0.0) -> Score:
    settings = get_settings()
    score = Score(f"gemini ({settings.gemini_model})")
    for case in cases:
        t = time.perf_counter()
        d = ask_gemini(case["text"], settings)
        score.add(case, d, time.perf_counter() - t)
        time.sleep(delay_s)  # free tier is rate limited (429 RESOURCE_EXHAUSTED)
    return score


def main(argv: list[str]) -> int:
    tuned, holdout = load_cases("ideas"), load_cases("holdout")
    print(evaluate_fallback(tuned, "fallback - set de ajustare").report())
    print(evaluate_fallback(holdout, "fallback - set nevăzut (holdout)").report())
    if "--gemini" in argv:
        if not get_settings().gemini_api_key:
            print("GEMINI_API_KEY not set; skipping Gemini")
        else:
            print(evaluate_gemini(tuned + holdout, delay_s=4.0).report())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
