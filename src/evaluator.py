"""
The evaluation system — "how good is this reply, actually?"

There is no single ground-truth reply for open-ended text, so a naive
exact-match "accuracy" number is meaningless for the free-text reply itself.
Instead this module scores each response on three independent layers, then
combines them into one transparent, documented formula (see README for the
full justification):

  1. HEURISTICS (deterministic, no API call, cannot be gamed by a smooth-
     talking judge): greeting/sign-off presence, placeholder leakage,
     length sanity, whether the order ID was referenced, and whether the
     predicted category/priority match ground truth (a genuine, classic
     accuracy metric for that sub-task).

  2. GROUNDED CRITERIA CHECKLIST (LLM-graded, but against concrete, specific,
     per-email requirements written at dataset-build time — not vibes).

  3. RUBRIC SCORES (LLM-graded, holistic 1-5 scores across five dimensions:
     relevance/correctness, tone/empathy, completeness, actionability,
     conciseness).

Run directly:
    python src/evaluator.py                  # needs results/generated_replies.json
    MOCK_MODE=1 python src/evaluator.py       # scores results/mock_smoketest/*
"""

import json
import os
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from company import COMPANY_NAME, KB_TEXT  # noqa: E402
from llm_client import LLMClient, LLMError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-5")

RUBRIC_DIMENSIONS = [
    "relevance_correctness", "tone_empathy", "completeness",
    "actionability", "conciseness",
]

# ----------------------------------------------------------------- weights
# Kept as named constants (not magic numbers) so the scoring formula is
# auditable at a glance — see README "why this metric is right".
CRITERIA_WEIGHT = 0.5          # grounded, per-email checklist
RUBRIC_WEIGHT = 0.5            # holistic LLM-judge rubric
PLACEHOLDER_LEAK_CAP = 1.0     # hard cap: unresolved template text is a critical bug
MISSING_ORDER_ID_PENALTY = 0.5
LENGTH_OUT_OF_RANGE_PENALTY = 0.25
MIN_WORDS, MAX_WORDS = 15, 220

JUDGE_SYSTEM_PROMPT = f"""You are a meticulous QA reviewer for the {COMPANY_NAME} \
customer support team. Score the drafted reply honestly and critically — do \
not default to high scores. You will be given the company knowledge base, \
the original customer email, a list of specific criteria this exact reply \
must satisfy, and the drafted reply.

Scoring guide for each 1-5 dimension: 5 = excellent, matches what a top-tier \
human agent would send. 3 = acceptable but with clear room for improvement. \
1 = poor, would need to be rewritten before sending.

KNOWLEDGE BASE:
{KB_TEXT}
"""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria_results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "met": {"type": "boolean"},
                    "explanation": {"type": "string", "description": "One sentence."},
                },
                "required": ["criterion", "met", "explanation"],
                "additionalProperties": False,
            },
        },
        "scores": {
            "type": "object",
            "properties": {dim: {"type": "integer", "description": "1 to 5"} for dim in RUBRIC_DIMENSIONS},
            "required": RUBRIC_DIMENSIONS,
            "additionalProperties": False,
        },
        "overall_comment": {"type": "string", "description": "1-2 sentences."},
    },
    "required": ["criteria_results", "scores", "overall_comment"],
    "additionalProperties": False,
}


# ------------------------------------------------------------------ layer 1
def heuristic_checks(email: dict, gen: dict) -> dict:
    reply = gen.get("generated_reply") or ""
    word_count = len(reply.split())

    tail = reply.strip()[-60:]  # sign-offs live at the very end of the email
    checks = {
        "has_greeting": bool(re.search(r"\b(hi|hello|dear|hey)\b", reply, re.I)),
        "has_signoff": bool(re.search(
            r"\b(regards|sincerely|best|thanks|thank you|cheers)\b", tail, re.I)),
        "placeholder_leak": bool(re.search(
            r"\[[A-Za-z_ ]+\]|\{\{.*?\}\}|lorem ipsum|MOCK REPLY", reply, re.I)),
        "word_count": word_count,
        "length_ok": MIN_WORDS <= word_count <= MAX_WORDS,
        "category_correct": gen.get("predicted_category") == email.get("category"),
        "priority_correct": gen.get("predicted_priority") == email.get("priority"),
    }
    if email.get("order_id"):
        checks["mentions_order_id"] = email["order_id"] in reply
    else:
        checks["mentions_order_id"] = None  # not applicable
    return checks


# ------------------------------------------------------------------ layer 2+3
def build_judge_user_message(email: dict, gen: dict) -> str:
    criteria_block = "\n".join(f"{i+1}. {c}" for i, c in enumerate(email["criteria"]))
    return f"""ORIGINAL CUSTOMER EMAIL
From: {email['customer_name']}
Subject: {email['subject']}
{email['body']}

CRITERIA THIS REPLY MUST SATISFY:
{criteria_block}

DRAFTED REPLY TO SCORE:
{gen.get('generated_reply', '')}
"""


def judge_reply(email: dict, gen: dict, client: LLMClient) -> dict:
    user_msg = build_judge_user_message(email, gen)
    return client.complete_json(JUDGE_SYSTEM_PROMPT, user_msg, JUDGE_SCHEMA, max_tokens=1500)


# ------------------------------------------------------------------ combine
def composite_score(heuristics: dict, judge: dict) -> tuple[float, str]:
    scores = judge.get("scores", {})
    rubric_mean = statistics.mean(scores.values()) if scores else 0.0

    criteria_results = judge.get("criteria_results", [])
    pass_rate = (sum(1 for c in criteria_results if c.get("met")) / len(criteria_results)
                 if criteria_results else 0.0)

    base = CRITERIA_WEIGHT * (pass_rate * 5) + RUBRIC_WEIGHT * rubric_mean

    if heuristics.get("placeholder_leak"):
        return round(min(base, PLACEHOLDER_LEAK_CAP), 2), "CRITICAL: placeholder/template leakage in reply"

    penalty = 0.0
    notes = []
    if heuristics.get("mentions_order_id") is False:
        penalty += MISSING_ORDER_ID_PENALTY
        notes.append("missing expected order-ID reference")
    if not heuristics.get("length_ok"):
        penalty += LENGTH_OUT_OF_RANGE_PENALTY
        notes.append(f"length out of range ({heuristics.get('word_count')} words)")

    final = max(0.0, base - penalty)
    return round(final, 2), ("; ".join(notes) if notes else "ok")


def evaluate_all(emails: list[dict], generations: list[dict], client: LLMClient) -> list[dict]:
    by_id = {e["id"]: e for e in emails}
    per_response = []
    for i, gen in enumerate(generations, 1):
        email = by_id[gen["id"]]
        if not gen.get("ok"):
            per_response.append({
                "id": gen["id"], "category": email["category"],
                "composite_score": 0.0, "notes": f"generation failed: {gen.get('error')}",
                "heuristics": None, "judge": None,
            })
            print(f"  [{i}/{len(generations)}] {gen['id']} -> skipped (generation failed)")
            continue

        h = heuristic_checks(email, gen)
        try:
            j = judge_reply(email, gen, client)
        except LLMError as exc:
            per_response.append({
                "id": gen["id"], "category": email["category"],
                "composite_score": 0.0, "notes": f"judge failed: {exc}",
                "heuristics": h, "judge": None,
            })
            print(f"  [{i}/{len(generations)}] {gen['id']} -> judge ERROR: {exc}")
            continue

        score, notes = composite_score(h, j)
        per_response.append({
            "id": gen["id"],
            "category": email["category"],
            "composite_score": score,
            "notes": notes,
            "heuristics": h,
            "judge": j,
        })
        print(f"  [{i}/{len(generations)}] {gen['id']} -> {score}/5 ({notes})")
    return per_response


# ------------------------------------------------------------------ aggregate
def aggregate(per_response: list[dict], bottom_n: int = 5) -> dict:
    scored = [r for r in per_response if r["heuristics"] is not None]
    scores = [r["composite_score"] for r in per_response]

    cat_correct = [r["heuristics"]["category_correct"] for r in scored]
    pri_correct = [r["heuristics"]["priority_correct"] for r in scored]

    dim_means = {}
    for dim in RUBRIC_DIMENSIONS:
        vals = [r["judge"]["scores"][dim] for r in scored if r["judge"]]
        dim_means[dim] = round(statistics.mean(vals), 2) if vals else None

    by_category: dict[str, list[float]] = {}
    for r in per_response:
        by_category.setdefault(r["category"], []).append(r["composite_score"])
    category_breakdown = {
        cat: {"mean_score": round(statistics.mean(v), 2), "n": len(v)}
        for cat, v in sorted(by_category.items())
    }

    ranked = sorted(per_response, key=lambda r: r["composite_score"])
    critical_flags = [r for r in per_response if "CRITICAL" in (r.get("notes") or "")]

    return {
        "n": len(per_response),
        "n_scored": len(scored),
        "mean_composite_score": round(statistics.mean(scores), 2) if scores else 0.0,
        "median_composite_score": round(statistics.median(scores), 2) if scores else 0.0,
        "category_classification_accuracy": round(statistics.mean(cat_correct), 4) if cat_correct else None,
        "priority_classification_accuracy": round(statistics.mean(pri_correct), 4) if pri_correct else None,
        "mean_rubric_scores": dim_means,
        "category_breakdown": category_breakdown,
        "bottom_n": [
            {"id": r["id"], "category": r["category"],
             "composite_score": r["composite_score"], "notes": r["notes"]}
            for r in ranked[:bottom_n]
        ],
        "critical_flags": [{"id": r["id"], "notes": r["notes"]} for r in critical_flags],
    }


def main():
    mock = os.environ.get("MOCK_MODE") == "1"
    result_dir = ROOT / ("results/mock_smoketest" if mock else "results")

    emails = json.loads((ROOT / "data" / "emails.json").read_text())
    gen_path = result_dir / "generated_replies.json"
    if not gen_path.exists():
        raise SystemExit(f"{gen_path} not found — run src/generator.py first.")
    generations = json.loads(gen_path.read_text())

    client = LLMClient(mock=mock, model=DEFAULT_MODEL)
    print(f"Evaluating {len(generations)} responses "
          f"({'MOCK MODE' if client.mock else DEFAULT_MODEL})...")
    per_response = evaluate_all(emails, generations, client)
    agg = aggregate(per_response)

    (result_dir / "evaluation_report.json").write_text(
        json.dumps({"per_response": per_response, "aggregate": agg}, indent=2, ensure_ascii=False)
    )

    print(f"\nMean composite score: {agg['mean_composite_score']}/5")
    print(f"Category accuracy:    {agg['category_classification_accuracy']:.1%}")
    print(f"Priority accuracy:    {agg['priority_classification_accuracy']:.1%}")
    print(f"-> {result_dir / 'evaluation_report.json'}")


if __name__ == "__main__":
    main()
