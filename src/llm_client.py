"""
Thin wrapper around the Anthropic Messages API.

Uses the current (GA, non-beta) Structured Outputs feature
(`output_config.format`, type "json_schema") so both the generator and the
judge get schema-guaranteed JSON back instead of hoping the model wraps its
answer in the right shape. See:
https://platform.claude.com/docs/en/build-with-claude/structured-outputs

MOCK_MODE
---------
Set MOCK_MODE=1 (or pass mock=True) to run the whole pipeline without an
API key or network access. This exists purely so the plumbing (schema
shapes, aggregation math, report generation) can be smoke-tested end to
end. Mock output is template-based and NOT a demonstration of reply
quality — see results/mock_smoketest/README.md.
"""

import json
import os
import random
import re


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, mock: bool = False, model: str | None = None):
        self.mock = mock or os.environ.get("MOCK_MODE") == "1"
        self.model = model
        self._client = None
        if not self.mock:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise LLMError(
                    "ANTHROPIC_API_KEY is not set. Either put it in a .env "
                    "file / export it, or run with MOCK_MODE=1 for an "
                    "offline dry run (see README)."
                )
            from anthropic import Anthropic
            self._client = Anthropic(api_key=api_key)

    def complete_json(self, system: str, user: str, schema: dict,
                       max_tokens: int = 1024) -> dict:
        """Call the model and return a dict matching `schema`.

        Real mode: uses Structured Outputs (output_config.format) so the
        response is guaranteed to match `schema` (barring a refusal or a
        max_tokens cutoff, both handled below).
        Mock mode: returns a deterministic, obviously-templated stand-in.
        """
        if self.mock:
            return self._mock_response(system, user, schema)

        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )

        if response.stop_reason == "refusal":
            raise LLMError("Model refused the request.")
        if response.stop_reason == "max_tokens":
            raise LLMError(
                f"Response truncated at max_tokens={max_tokens}; "
                "retry with a higher limit."
            )

        text = response.content[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model did not return valid JSON: {exc}\nRaw: {text[:300]}")

    # ------------------------------------------------------------------ mock
    def _mock_response(self, system: str, user: str, schema: dict) -> dict:
        props = set((schema.get("properties") or {}).keys())

        # Generator-shaped schema: {reply, category, priority}
        if {"reply", "category", "priority"} <= props:
            category = _keyword_guess_category(user)
            return {
                "reply": (
                    "Hi there,\n\n[MOCK REPLY — pipeline smoke test only, "
                    "not a real generated reply] Thanks for reaching out. "
                    "We're looking into this and will follow up shortly.\n\n"
                    "Best,\nNestwell Support"
                ),
                "category": category,
                "priority": "medium",
            }

        # Judge-shaped schema: {criteria_results, scores, overall_comment}
        if {"criteria_results", "scores", "overall_comment"} <= props:
            criteria = _extract_criteria_from_prompt(user)
            rng = random.Random(len(user))  # deterministic per-input
            return {
                "criteria_results": [
                    {"criterion": c, "met": rng.random() > 0.35,
                     "explanation": "[MOCK] heuristic placeholder, not a real judgment."}
                    for c in criteria
                ],
                "scores": {
                    "relevance_correctness": rng.randint(2, 4),
                    "tone_empathy": rng.randint(2, 4),
                    "completeness": rng.randint(2, 4),
                    "actionability": rng.randint(2, 4),
                    "conciseness": rng.randint(2, 4),
                },
                "overall_comment": "[MOCK] placeholder judge output for pipeline testing only.",
            }

        raise LLMError("Mock mode doesn't recognize this schema shape.")


def _keyword_guess_category(user_text: str) -> str:
    text = user_text.lower()
    rules = [
        ("shipping_delay", ["tracking", "shipping", "delayed", "delivery", "package"]),
        ("refund_request", ["refund", "return", "charged twice", "money back"]),
        ("app_bug", ["app crash", "log in", "login", "coupon", "checkout", "reset email"]),
        ("complaint_escalation", ["manager", "scam", "third", "again", "unacceptable"]),
        ("positive_feedback", ["thank", "love", "awesome", "great quality"]),
    ]
    for category, keywords in rules:
        if any(k in text for k in keywords):
            return category
    return "product_question"


def _extract_criteria_from_prompt(user_text: str) -> list[str]:
    # The judge prompt renders criteria as a numbered list; pull them back
    # out so mock mode can still produce one result per criterion.
    lines = re.findall(r"^\s*\d+\.\s*(.+)$", user_text, flags=re.MULTILINE)
    return lines or ["(no criteria found)"]
