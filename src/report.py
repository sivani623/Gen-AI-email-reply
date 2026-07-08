"""
Turns results/evaluation_report.json into results/SUMMARY.md — a short,
GitHub-renderable summary a reviewer can read without running anything.

Run directly:
    python src/report.py
    MOCK_MODE=1 python src/report.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent


def render(data: dict) -> str:
    agg = data["aggregate"]
    lines = []
    lines.append("# Evaluation Summary\n")
    lines.append(f"- Responses evaluated: **{agg['n']}** ({agg['n_scored']} fully scored)")
    lines.append(f"- Mean composite score: **{agg['mean_composite_score']} / 5** "
                 f"(median {agg['median_composite_score']})")
    if agg["category_classification_accuracy"] is not None:
        lines.append(f"- Category auto-tag accuracy: **{agg['category_classification_accuracy']:.1%}**")
    if agg["priority_classification_accuracy"] is not None:
        lines.append(f"- Priority auto-tag accuracy: **{agg['priority_classification_accuracy']:.1%}**")
    if agg["critical_flags"]:
        lines.append(f"- ⚠️ Critical flags: **{len(agg['critical_flags'])}** "
                     f"({', '.join(f['id'] for f in agg['critical_flags'])})")

    lines.append("\n## Mean rubric scores by dimension (1-5)\n")
    lines.append("| Dimension | Mean |")
    lines.append("|---|---|")
    for dim, val in agg["mean_rubric_scores"].items():
        lines.append(f"| {dim.replace('_', ' ')} | {val if val is not None else 'n/a'} |")

    lines.append("\n## Mean composite score by category\n")
    lines.append("| Category | Mean score | n |")
    lines.append("|---|---|---|")
    for cat, stats in agg["category_breakdown"].items():
        lines.append(f"| {cat} | {stats['mean_score']} | {stats['n']} |")

    lines.append("\n## Lowest-scoring responses (flagged for human review)\n")
    lines.append("| ID | Category | Score | Notes |")
    lines.append("|---|---|---|---|")
    for r in agg["bottom_n"]:
        lines.append(f"| {r['id']} | {r['category']} | {r['composite_score']} | {r['notes']} |")

    lines.append(
        "\n_Note: with n=5 per category, the category breakdown is directional "
        "(useful for spotting large gaps), not statistically rigorous._"
    )
    return "\n".join(lines) + "\n"


def main():
    mock = os.environ.get("MOCK_MODE") == "1"
    result_dir = ROOT / ("results/mock_smoketest" if mock else "results")
    report_path = result_dir / "evaluation_report.json"
    if not report_path.exists():
        raise SystemExit(f"{report_path} not found — run src/evaluator.py first.")

    data = json.loads(report_path.read_text())
    md = render(data)
    out_path = result_dir / "SUMMARY.md"
    out_path.write_text(md)
    print(md)
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
