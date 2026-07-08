"""
The Gen-AI reply generator.

For every email in data/emails.json, calls Claude with the Nestwell company
persona + knowledge base and asks for THREE things in one structured call:
  - `reply`     the suggested email reply text
  - `category`  auto-tag (mirrors Hiver's real AI Tagging feature)
  - `priority`  auto-priority (mirrors Hiver's SLA/priority automation)

Producing the tag + priority alongside the reply — rather than just the
reply text — is what lets evaluator.py report a hard, unambiguous accuracy
number (did the tag match ground truth?) *and* a justified quality score for
the open-ended reply (see README, "why this metric is right").

Run directly:
    python src/generator.py                  # real call, needs ANTHROPIC_API_KEY
    MOCK_MODE=1 python src/generator.py       # offline smoke test
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from company import COMPANY_NAME, KB_TEXT, CATEGORIES, PRIORITIES  # noqa: E402
from llm_client import LLMClient, LLMError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = os.environ.get("GENERATOR_MODEL", "claude-haiku-4-5-20251001")

SYSTEM_PROMPT = f"""You are a customer support agent for {COMPANY_NAME}, a \
home-goods e-commerce company. You are drafting a suggested reply inside a \
shared team inbox (like Hiver) for a human agent to review and send.

Write warm, professional, concise replies (roughly 2-6 sentences unless the \
issue genuinely needs more). Address the customer by first name if given. \
Reference specific details from their email (order numbers, product names, \
the specific issue) instead of generic boilerplate. Match your reply's \
length and formality to the customer's message — a one-line thank-you does \
not need a five-paragraph response.

Never invent policy details, dates, or product specifications that are not \
in the knowledge base below. If information you'd need is missing or not in \
the KB, say so plainly and offer to find out or ask the customer for it, \
rather than guessing.

KNOWLEDGE BASE:
{KB_TEXT}

Also classify the email with a `category` (one of: {", ".join(CATEGORIES)}) \
and a `priority` (one of: {", ".join(PRIORITIES)}), per the escalation \
policy in the KB.
"""

REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string", "description": "The full suggested email reply, including greeting and sign-off."},
        "category": {"type": "string", "enum": CATEGORIES},
        "priority": {"type": "string", "enum": PRIORITIES},
    },
    "required": ["reply", "category", "priority"],
    "additionalProperties": False,
}


def build_user_message(email: dict) -> str:
    lines = [
        f"From: {email['customer_name']}",
        f"Subject: {email['subject']}",
    ]
    if email.get("order_id"):
        lines.append(f"(Order ID visible in system: {email['order_id']})")
    lines.append("")
    lines.append(email["body"])
    return "\n".join(lines)


def generate_replies(emails: list[dict], client: LLMClient) -> list[dict]:
    results = []
    for i, email in enumerate(emails, 1):
        user_msg = build_user_message(email)
        try:
            parsed = client.complete_json(SYSTEM_PROMPT, user_msg, REPLY_SCHEMA)
            results.append({
                "id": email["id"],
                "ok": True,
                "generated_reply": parsed["reply"],
                "predicted_category": parsed["category"],
                "predicted_priority": parsed["priority"],
            })
        except LLMError as exc:
            results.append({"id": email["id"], "ok": False, "error": str(exc)})
        print(f"  [{i}/{len(emails)}] {email['id']} -> "
              f"{'ok' if results[-1]['ok'] else 'ERROR: ' + results[-1]['error']}")
        if not client.mock:
            time.sleep(0.3)  # gentle client-side pacing
    return results


def main():
    mock = os.environ.get("MOCK_MODE") == "1"
    emails = json.loads((ROOT / "data" / "emails.json").read_text())
    client = LLMClient(mock=mock, model=DEFAULT_MODEL)

    print(f"Generating replies for {len(emails)} emails "
          f"({'MOCK MODE' if client.mock else DEFAULT_MODEL})...")
    results = generate_replies(emails, client)

    out_dir = ROOT / ("results/mock_smoketest" if mock else "results")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "generated_replies.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    n_ok = sum(1 for r in results if r["ok"])
    print(f"\nDone: {n_ok}/{len(results)} succeeded -> {out_path}")


if __name__ == "__main__":
    main()
