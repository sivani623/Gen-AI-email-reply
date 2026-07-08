"""
Quick unit tests for the deterministic (no-API-call) parts of evaluator.py.
Run with: python tests/test_heuristics.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from evaluator import heuristic_checks, composite_score  # noqa: E402


def test_placeholder_leak_detected():
    email = {"order_id": None}
    gen = {"generated_reply": "Hi [Customer Name], thanks for reaching out. Best,"}
    checks = heuristic_checks(email, gen)
    assert checks["placeholder_leak"] is True


def test_order_id_reference_detected():
    email = {"order_id": "NW-12345"}
    gen = {"generated_reply": "Hi Sam, I checked order NW-12345 and it has shipped. Best, Team"}
    checks = heuristic_checks(email, gen)
    assert checks["mentions_order_id"] is True


def test_missing_order_id_reference_detected():
    email = {"order_id": "NW-12345"}
    gen = {"generated_reply": "Hi Sam, thanks for reaching out, we'll look into it. Best, Team"}
    checks = heuristic_checks(email, gen)
    assert checks["mentions_order_id"] is False


def test_signoff_detected_in_multiword_tail():
    email = {"order_id": None}
    gen = {"generated_reply": "Hi there, we're on it.\n\nBest,\nNestwell Support"}
    checks = heuristic_checks(email, gen)
    assert checks["has_signoff"] is True


def test_composite_score_caps_on_placeholder_leak():
    heuristics = {"placeholder_leak": True, "mentions_order_id": None, "length_ok": True}
    judge = {"scores": {"a": 5, "b": 5, "c": 5, "d": 5, "e": 5},
             "criteria_results": [{"met": True}]}
    score, notes = composite_score(heuristics, judge)
    assert score <= 1.0
    assert "CRITICAL" in notes


def test_composite_score_penalizes_missing_order_id():
    heuristics_with = {"placeholder_leak": False, "mentions_order_id": True, "length_ok": True}
    heuristics_without = {"placeholder_leak": False, "mentions_order_id": False, "length_ok": True}
    judge = {"scores": {"a": 4, "b": 4, "c": 4, "d": 4, "e": 4},
             "criteria_results": [{"met": True}, {"met": True}]}
    score_with, _ = composite_score(heuristics_with, judge)
    score_without, _ = composite_score(heuristics_without, judge)
    assert score_without < score_with



if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
