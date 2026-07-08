# Gen-AI-email-reply

A shared-inbox-style pipeline that (1) suggests a reply + auto-tag for
incoming customer emails, and (2) scores those replies in a way that's
actually defensible, not just a vibe. Built for a fictional Nestwell
(home-goods e-commerce) support inbox, in the spirit of what a Hiver-style
team triages daily.

## TL;DR — how to run it

```bash
git clone <this-repo-url> && cd hiver-genai-reply-challenge
pip install -r requirements.txt
cp .env.example .env               # then paste your ANTHROPIC_API_KEY into .env

python src/run_pipeline.py         # ~2-4 min for 30 emails: generate -> evaluate -> report
```

**Getting a key:** sign up at [console.anthropic.com](https://console.anthropic.com)
— a separate account from claude.ai chat, and not the same as other AI
platforms (e.g. Zerve.ai is an unrelated data-science product; its keys
won't authenticate here). Add a payment method under Settings → Billing
(no ongoing free API tier, but this whole run costs well under $1), then
Settings → API Keys → Create Key. It starts with `sk-ant-` and is shown
once, so copy it straight into `.env` rather than typing it twice.

That writes `results/generated_replies.json`, `results/evaluation_report.json`,
and a human-readable `results/SUMMARY.md`. No key handy? `MOCK_MODE=1 python
src/run_pipeline.py` runs the same plumbing offline (see
[`results/README.md`](results/README.md) for why that output is placeholder-only).

Rebuild or extend the dataset with `python data/build_dataset.py`.
Unit tests: `python tests/test_heuristics.py`.

## Repo map

```
data/
  build_dataset.py      # source of truth for the dataset; run it to emit emails.json
  emails.json           # 30 synthetic support emails, 6 categories, ground-truth labels + criteria
src/
  company.py            # fictional company persona + knowledge base (shared by generator & judge)
  llm_client.py          # Anthropic API wrapper using Structured Outputs; MOCK_MODE for offline runs
  generator.py           # the Gen-AI reply generator
  evaluator.py            # the evaluation system (heuristics + grounded criteria + LLM-judge rubric)
  report.py               # renders evaluation_report.json -> SUMMARY.md
  run_pipeline.py          # generate -> evaluate -> report, one command
results/                   # real run output lands here (see results/README.md)
tests/test_heuristics.py   # unit tests for the deterministic scoring layer
```

## The dataset

`data/emails.json`: 30 synthetic emails, 5 each across 6 categories a
Hiver-style team actually triages — `shipping_delay`, `refund_request`,
`product_question`, `app_bug`, `complaint_escalation`, `positive_feedback`.

About a third of the emails are deliberately awkward on purpose: missing
order IDs, a return outside the policy window, a duplicate charge the KB
doesn't cover, a customer on their third angry email, one with literally no
actionable detail ("this is a scam, fix it"). A generic dataset of easy
emails would make every reply look great; the point of this challenge is
telling good replies from bad ones, so the dataset needs enough hard cases
to actually separate them.

## The generator (`src/generator.py`)

One structured call per email returns three things at once:

```json
{ "reply": "...", "category": "refund_request", "priority": "medium" }
```

Generating the tag + priority alongside the reply — not just the free
text — mirrors Hiver's real AI Tagging / SLA-priority features, and it's
also what makes the evaluation honest (more on that below). The system
prompt carries a small **knowledge base** (shipping windows, return policy,
loyalty points, escalation rules) and explicitly forbids inventing policy
details or product specs that aren't in it — several dataset emails exist
specifically to test whether the model resists that temptation (e.g. a
mattress-comparison question the KB has no specs for).

Uses the Claude API's [Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
(`output_config.format`, JSON-schema mode) rather than "please respond with
only JSON" prompting, so the response is schema-guaranteed instead of
occasionally getting wrapped in markdown fences or a chatty preamble.
Generation defaults to **Claude Haiku 4.5** (cheap/fast — the model you'd
actually pick for "suggest replies at scale"); the judge below defaults to
**Claude Sonnet 5** (a stronger reasoner, used sparingly for QA rather than
per-customer-email, where accuracy matters more than unit cost).

## The evaluator — and why this metric is right

There's no single correct free-text reply to an open-ended email, so a
naive exact-match "% accuracy" number would be meaningless for the reply
itself — reporting one anyway would be answering a different, easier
question than the one this challenge asks. Instead the evaluator scores
every response on three independent layers and combines them into one
transparent formula:

1. **Heuristics** (deterministic, no LLM call, can't be talked around by a
   lenient judge): placeholder/template leakage, reply length sanity,
   whether the order ID was actually referenced when one was given, and —
   the genuinely hard-number part — **did the predicted category/priority
   match ground truth**. That last one is classic, unambiguous classification
   accuracy, and it's real precisely *because* the generator emits a tag,
   not just prose.

2. **Grounded criteria checklist** (LLM-graded, but against the specific,
   concrete requirements written per-email at dataset-build time — not
   "does this feel good"). This is what stops the eval from just rewarding
   confident, well-formatted prose that quietly gets the policy wrong.

3. **Holistic rubric** (LLM-judge, 1-5 on relevance/correctness,
   tone/empathy, completeness, actionability, conciseness) for the
   dimensions that genuinely need judgment rather than a checklist —
   tone is real, and a checklist can't grade it.

**Composite = 0.5 × (criteria pass-rate × 5) + 0.5 × mean(rubric scores)**,
then a hard cap to 1/5 if placeholder text leaked into the reply (an
embarrassing production bug no amount of good tone should paper over), and
small penalties for a missing expected order-ID reference or wildly
off-length replies. The weights, caps, and penalties are named constants at
the top of `evaluator.py`, not tuned in secret — every number in a response's
score is traceable to a specific check.

Why split it this way instead of one end-to-end LLM score? Because "did it
get the facts and required actions right" and "was it delivered well" are
genuinely different failure modes for a support reply — a technically
correct but cold reply and a warm reply that misstates the refund window
are both bad, for different reasons a single number would blur together.
Splitting them (and reporting classification accuracy completely separately
from the composite) means a Hiver reviewer looking at the output can tell
*which* problem a low-scoring reply has, not just that it scored low.

**Where this is weakest, honestly:** the rubric and criteria layers still
run through an LLM judge, which has its own blind spots and could in
principle share biases with the generator (mitigated a little by using a
different, stronger model as judge, and a lot by grounding it in per-email
written criteria instead of an open-ended "rate this" prompt). And with n=5
emails per category, the category breakdown in `SUMMARY.md` is good for
spotting a large gap, not a small one — I said as much directly in the
generated summary rather than let a small-sample table imply more
confidence than it has.

## Sample output

See [`results/mock_smoketest/`](results/mock_smoketest/) for what the file
shapes look like end-to-end (offline, placeholder text only — read
[`results/README.md`](results/README.md) before treating any number in
there as real). Real results land in `results/` after you run the pipeline
with a key; that's the version to commit before submitting.

## How AI tools were used

Built with Claude (Anthropic) throughout: scaffolding the pipeline
structure, writing the dataset (all 30 emails and their criteria),
implementing `src/*.py`, and drafting this README. I reviewed and adjusted
the design choices above (the scoring formula, the KB-grounding approach,
what counts as a critical heuristic failure) rather than taking a first
draft as-is — happy to walk through any of it.

## What I'd do with more time

- Replace the keyword-based mock category-guesser with nothing — it only
  exists so the offline smoke test has *something* schema-valid to score;
  it's not part of the real pipeline.
- Add a human-labeled subset (even 10-15 emails, two people) to sanity-check
  how well the LLM-judge rubric actually correlates with human judgment,
  rather than asserting it does.
- Batch the generation calls (Message Batches API, 50% cheaper) once the
  dataset grows past a few hundred emails.
- A live "does this reply match KB facts" check that's fully deterministic
  (regex/entity-match against KB values like the exact refund window) as a
  fourth layer, so factual grounding doesn't rely on the judge at all.
