"""Accuracy floor for the deterministic fallback, so keyword edits cannot silently regress it.
The holdout split is never used for tuning; its floor reflects measured generalization (75% on 2026-11-14)."""
from backend.ai.evaluate import evaluate_fallback, load_cases


def test_fallback_accuracy_on_tuned_set():
    assert evaluate_fallback(load_cases("ideas")).category_accuracy >= 0.9


def test_fallback_accuracy_on_holdout():
    assert evaluate_fallback(load_cases("holdout")).category_accuracy >= 0.7


def test_eval_labels_are_valid_categories():
    from backend.ai.schemas import Category

    valid = {c.value for c in Category}
    assert all(c["category"] in valid for c in load_cases("ideas") + load_cases("holdout"))
