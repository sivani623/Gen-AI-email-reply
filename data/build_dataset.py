"""
Builds data/emails.json — the synthetic support-inbox dataset used by the
rest of the pipeline.

HOW THIS DATASET WAS BUILT
--------------------------
Real Hiver customer emails aren't available to a candidate outside the
company, and scraping/using real support tickets from elsewhere would raise
privacy and provenance problems for a "your own work" submission. Instead,
this is a synthetic dataset representing a fictional Nestwell (home-goods
e-commerce) shared support inbox, written with Claude's help to hit two
goals a scraped dataset wouldn't give us:

  1. Deliberate coverage of the 6 email types a Hiver-style team actually
     triages (see CATEGORIES below), spanning easy/short, long/rambling,
     angry, ambiguous, and multi-issue emails.
  2. Per-email GROUND TRUTH: a `category` + `priority` label (so we can score
     auto-tagging accuracy, mirroring Hiver's real AI Tagging/SLA features)
     and a short list of `criteria` — concrete, checkable things a *correct*
     reply to *this specific email* must do. The criteria are what let
     evaluator.py grade substance, not just vibes (see README).

A handful of emails are deliberately adversarial test cases for the
generator: missing order IDs, policy edge cases (used returns, 45-day-old
returns, duplicate charges the KB doesn't cover), and a no-information
hostile message. These are noted with a `note` field (dev-facing only,
never shown to the generator or judge).

Run this file to (re)generate data/emails.json:
    python data/build_dataset.py
"""

import json
from pathlib import Path

COMPANY_NAME = "Nestwell"

# Valid values — single source of truth, imported by src/company.py too.
CATEGORIES = [
    "shipping_delay",
    "refund_request",
    "product_question",
    "app_bug",
    "complaint_escalation",
    "positive_feedback",
]
PRIORITIES = ["low", "medium", "high", "urgent"]

EMAILS = [
    # ---------------------------------------------------------------- shipping_delay
    {
        "id": "e01", "category": "shipping_delay", "priority": "medium",
        "customer_name": "Priya Nair",
        "subject": "Order still not moving",
        "body": "Hi team, I ordered the Marlow Bookshelf and the Ridge Side "
                "Table almost two weeks ago now (order NW-48213) with standard "
                "shipping. The tracking page hasn't updated in 6 days and it's "
                "still sitting at 'label created.' Could someone take a look "
                "and let me know what's going on? Thanks, Priya",
        "order_id": "NW-48213",
        "criteria": [
            "Acknowledges the specific 6-day tracking stall rather than a generic 'orders can take time' response",
            "References order NW-48213",
            "Offers a concrete next step (checking with the carrier/logistics) without inventing a guaranteed new delivery date",
        ],
    },
    {
        "id": "e02", "category": "shipping_delay", "priority": "high",
        "customer_name": "Marcus Webb",
        "subject": "wheres my order",
        "body": "ordered almost a month ago and nothing. no order number on "
                "hand rn just check by my email. this is ridiculous for a "
                "company that seems otherwise decent",
        "order_id": None,
        "criteria": [
            "Asks for or attempts to locate order details since no order number was given, rather than guessing",
            "Apologizes for the extended delay (nearly a month is well beyond the 5-7 business day window)",
            "Does not promise an exact delivery date that isn't knowable",
        ],
        "note": "No order ID provided — tests whether the model asks for identifying info instead of fabricating a lookup.",
    },
    {
        "id": "e03", "category": "shipping_delay", "priority": "medium",
        "customer_name": "Grace Okonkwo",
        "subject": "Paid for expedited shipping but it wasn't expedited?",
        "body": "Hello, I placed order NW-51002 last Monday and paid extra for "
                "expedited (2-3 business day) shipping. It's now been 6 "
                "business days and the item only just shipped today. Can you "
                "explain why, and is there any way to get the expedited fee "
                "refunded since the timeline wasn't met?",
        "order_id": "NW-51002",
        "criteria": [
            "Acknowledges the expedited-shipping promise was not met for order NW-51002",
            "Directly addresses the refund-of-shipping-fee request rather than ignoring it",
            "Keeps tone apologetic/accountable, not defensive",
        ],
    },
    {
        "id": "e04", "category": "shipping_delay", "priority": "medium",
        "customer_name": "Tomás Rivera",
        "subject": "Need this by Friday if possible",
        "body": "Hi there — I ordered the Alder Guest Bedding Set (order "
                "NW-33210) hoping to have it before my in-laws visit this "
                "Friday. The site said 5-7 business days at checkout and "
                "we're on day 5 now. Is there any way to check if it'll make "
                "it, or should I look at other options? Really appreciate any "
                "info you can give me.",
        "order_id": "NW-33210",
        "criteria": [
            "Directly addresses whether Friday is realistic given day 5 of a 5-7 business day window, without over-promising",
            "References order NW-33210",
            "Offers a practical alternative or next step given the uncertainty",
        ],
    },
    {
        "id": "e05", "category": "shipping_delay", "priority": "high",
        "customer_name": "Aiko Tanaka",
        "subject": "unbelievable",
        "body": "Still haven't gotten my package. This is ridiculous. I'm one "
                "step away from just disputing the charge with my bank.",
        "order_id": None,
        "criteria": [
            "Takes the dispute-threat seriously and responds with urgency/empathy rather than a generic templated line",
            "Asks for an order number or identifying details since none were given",
            "Avoids sounding dismissive given the short, angry tone",
        ],
        "note": "Short, angry, no order info, borders on escalation — tests tone-matching without guessing at specifics.",
    },

    # ---------------------------------------------------------------- refund_request
    {
        "id": "e06", "category": "refund_request", "priority": "low",
        "customer_name": "Sam Delgado",
        "subject": "Return request - unopened rug",
        "body": "Hi, I'd like to return the Bramwell Wool Rug (order "
                "NW-29981). It's still sealed in the original packaging, "
                "delivered 10 days ago. Can you send me return instructions?",
        "order_id": "NW-29981",
        "criteria": [
            "Confirms the item qualifies for return (within 30 days, unused, original packaging)",
            "Provides clear return instructions or next steps",
            "States the correct refund timeline (5-7 business days after the return is received)",
        ],
    },
    {
        "id": "e07", "category": "refund_request", "priority": "medium",
        "customer_name": "Helen Achebe",
        "subject": "want to return this",
        "body": "I bought the Fenwick Throw Pillow set and honestly the color "
                "just doesn't work in my living room. I've had them out on the "
                "couch for about two weeks so they've been used a little, but "
                "they're basically like new. Can I still get a refund?",
        "order_id": None,
        "criteria": [
            "Correctly notes that policy requires unused items/original packaging and addresses that this one has been used, without being harsh",
            "Does not falsely promise a full refund if the item doesn't clearly qualify",
            "Offers a reasonable path forward rather than a flat no",
        ],
        "note": "Item may not strictly qualify (used) — tests whether the model invents a guaranteed answer or handles the gray area.",
    },
    {
        "id": "e08", "category": "refund_request", "priority": "low",
        "customer_name": "Devon Clarke",
        "subject": "refund timing",
        "body": "Hey, I mailed back my return last Tuesday (about a week ago) "
                "— how much longer until I see the refund on my card?",
        "order_id": None,
        "criteria": [
            "States the correct refund timeline: 5-7 business days after the returned item is received (not after it was mailed)",
            "Asks for or acknowledges missing order/tracking info if needed to check received status",
            "Sets realistic expectations rather than guaranteeing an exact day",
        ],
    },
    {
        "id": "e09", "category": "refund_request", "priority": "high",
        "customer_name": "Ingrid Larsen",
        "subject": "Charged twice for one order",
        "body": "I just noticed I was charged twice for order NW-15532 — "
                "$142.50 appears twice on my card statement from the same day. "
                "I only ordered one of everything. Can you refund the "
                "duplicate charge?",
        "order_id": "NW-15532",
        "criteria": [
            "Recognizes this is a billing/duplicate-charge issue, not a standard product return, and doesn't misapply the 30-day return policy",
            "Commits to investigating/escalating the duplicate charge rather than inventing a resolution timeline not covered by the KB",
            "Reassures the customer this will be looked into promptly given it's a billing error",
        ],
        "note": "Duplicate charge isn't explicitly covered by the KB — tests escalation instead of fabricated policy.",
    },
    {
        "id": "e10", "category": "refund_request", "priority": "medium",
        "customer_name": "Chidi Umeh",
        "subject": "Return after 45 days",
        "body": "I know it's been a little while (I think I got this about a "
                "month and a half ago) but the Wexford Armchair has a wobble I "
                "only just noticed once I moved it. Can I still return or "
                "exchange it?",
        "order_id": "NW-60011",
        "criteria": [
            "Correctly notes that 45 days is outside the standard 30-day return window rather than promising an automatic refund",
            "Handles it diplomatically given it's a possible manufacturing defect, not a change of mind — doesn't just flatly refuse",
            "Offers a reasonable next step (e.g. escalate for a defect review) rather than inventing a guaranteed outcome",
        ],
        "note": "Outside the return window but possibly a defect — tests nuanced handling instead of a rigid or invented answer.",
    },

    # ---------------------------------------------------------------- product_question
    {
        "id": "e11", "category": "product_question", "priority": "low",
        "customer_name": "Olivia Bennett",
        "subject": "Quick question about the Haven Throw Blanket",
        "body": "Hi! Is the Haven Throw Blanket machine washable? Thinking of "
                "getting it for my couch but want to make sure I can actually "
                "clean it easily. Thanks!",
        "order_id": None,
        "criteria": [
            "Directly answers the washability question, or clearly says this needs to be checked rather than guessing",
            "Keeps the tone friendly and brief given this is a simple pre-sales question",
        ],
        "note": "KB has no product-spec sheet — tests whether the model invents an answer instead of flagging it needs to check.",
    },
    {
        "id": "e12", "category": "product_question", "priority": "low",
        "customer_name": "Rahul Mehta",
        "subject": "Aster dining table dimensions + assembly",
        "body": "Hello, I'm considering the Aster Dining Table for a fairly "
                "small apartment. Could you tell me the exact dimensions, and "
                "whether it arrives assembled or needs to be put together? "
                "Trying to figure out if it'll fit through my doorway in one "
                "piece. Thanks in advance.",
        "order_id": None,
        "criteria": [
            "Addresses both sub-questions (dimensions and assembly), not just one",
            "If exact dimensions aren't available to the agent, says so clearly rather than inventing numbers",
            "Stays helpful and concise",
        ],
        "note": "Two-part question — tests completeness.",
    },
    {
        "id": "e13", "category": "product_question", "priority": "low",
        "customer_name": "Beatriz Souza",
        "subject": "Different color available?",
        "body": "Love the Linden Accent Chair but I don't see it in burgundy "
                "on the site — just gray and navy. Is burgundy coming, or "
                "available some other way?",
        "order_id": None,
        "criteria": [
            "Answers honestly based on what's knowable (site only shows gray/navy) without inventing a burgundy option or release date",
            "Offers a reasonable next step if sensible (e.g. offering to flag interest) without over-promising",
        ],
    },
    {
        "id": "e14", "category": "product_question", "priority": "low",
        "customer_name": "Noah Fitzgerald",
        "subject": "Difference between the two mattress models?",
        "body": "Trying to decide between the Drift Hybrid and the Drift Foam "
                "mattresses before I order. What's actually different between "
                "them? Firmness, materials, anything else worth knowing.",
        "order_id": None,
        "criteria": [
            "Attempts to address the comparison or clearly states the specific specs aren't available and offers to find out, rather than inventing detailed specs",
            "Doesn't sound like it's dodging the question entirely",
        ],
        "note": "KB has no mattress specs — good hallucination-resistance test on a detailed product question.",
    },
    {
        "id": "e15", "category": "product_question", "priority": "low",
        "customer_name": "Lindiwe Dube",
        "subject": "Materials question",
        "body": "Before I order the Meadow Bedding Set — are your materials "
                "cruelty-free / vegan? This matters a lot to me and I "
                "couldn't find a clear answer on the product page.",
        "order_id": None,
        "criteria": [
            "Answers honestly based on available info, or clearly says this needs to be checked rather than assuming",
            "Takes the values-based question seriously and respectfully",
        ],
    },

    # ---------------------------------------------------------------- app_bug
    {
        "id": "e16", "category": "app_bug", "priority": "medium",
        "customer_name": "Jake Sullivan",
        "subject": "App keeps crashing",
        "body": "The Nestwell app crashes every time I try to open my order "
                "history. Happens on both wifi and cellular. iPhone 14, "
                "latest app version. Really annoying since I was trying to "
                "check on a return.",
        "order_id": None,
        "criteria": [
            "Acknowledges the specific crash-on-order-history bug and the device/context details given",
            "Offers a reasonable troubleshooting step or workaround (e.g. website) and/or commits to escalating to the tech team",
            "Doesn't just give a generic 'have you tried restarting' with no acknowledgment of specifics",
        ],
    },
    {
        "id": "e17", "category": "app_bug", "priority": "medium",
        "customer_name": "Mei Lin Zhou",
        "subject": "App says delivered but I never got it",
        "body": "The app shows my order as 'delivered' as of yesterday "
                "afternoon, but there's nothing here — I checked with my "
                "building's front desk too. Is this an app glitch or did "
                "something actually go wrong with delivery?",
        "order_id": None,
        "criteria": [
            "Acknowledges both possibilities raised (tracking glitch vs. a genuine delivery problem) rather than assuming only one",
            "Mentions the known app tracking lag as a *possible* explanation without dismissing a real missing-package concern",
            "Provides a next step, e.g. checking with the carrier or filing a missing-package report",
        ],
        "note": "Deliberately ambiguous between app_bug and shipping_delay — realistic edge case for the classifier and for reply completeness.",
    },
    {
        "id": "e18", "category": "app_bug", "priority": "high",
        "customer_name": "Fatima Al-Sayed",
        "subject": "Charged twice, checkout said it failed",
        "body": "My payment failed twice at checkout (got an error both "
                "times) but I just checked my bank app and I was charged for "
                "both attempts. Can someone sort this out?",
        "order_id": None,
        "criteria": [
            "Recognizes this as a billing/technical hybrid issue rather than treating it as a simple app crash",
            "Commits to investigating/reversing the erroneous charge(s) rather than inventing a specific resolution timeline",
            "Treats it with appropriate urgency given it's a real financial issue",
        ],
        "note": "Billing + technical overlap, same family as e09 — tests consistent handling of duplicate-charge scenarios.",
    },
    {
        "id": "e19", "category": "app_bug", "priority": "medium",
        "customer_name": "Connor Byrne",
        "subject": "Can't log in, no reset email",
        "body": "I'm locked out of my account. I tried the 'forgot password' "
                "link three times over the last hour and the reset email "
                "never shows up, checked spam too. Can you help me get back "
                "in?",
        "order_id": None,
        "criteria": [
            "Acknowledges the specific issue (reset emails not arriving after multiple attempts), not a generic 'try resetting your password'",
            "Offers a concrete alternative path since the standard flow already failed 3 times",
        ],
    },
    {
        "id": "e20", "category": "app_bug", "priority": "low",
        "customer_name": "Zoe Anagnostou",
        "subject": "Coupon code not working",
        "body": "Trying to use code WELCOME10 at checkout and it says "
                "'invalid code' even though I just got it in your welcome "
                "email today. Cart total is $86, want to make sure I don't "
                "miss out before it expires.",
        "order_id": None,
        "criteria": [
            "Addresses the specific code (WELCOME10) and checkout error described",
            "Offers a concrete resolution (apply manually, extend the offer, or escalate) rather than only apologizing",
            "Reflects the time-sensitivity the customer mentioned",
        ],
    },

    # ---------------------------------------------------------------- complaint_escalation
    {
        "id": "e21", "category": "complaint_escalation", "priority": "urgent",
        "customer_name": "Robert Klein",
        "subject": "THIRD EMAIL - still no refund",
        "body": "This is the THIRD time I'm emailing about this. I returned "
                "the Holloway Lamp three weeks ago and STILL no refund. I've "
                "been more than patient. If this isn't resolved by end of "
                "week I'm disputing the charge with my bank and leaving a "
                "review everywhere I can. I want an actual answer this time, "
                "not a copy-paste apology.",
        "order_id": None,
        "criteria": [
            "Acknowledges this is a repeat/escalated contact rather than responding as if it's a first-time request",
            "Avoids sounding like a generic templated apology, given the customer explicitly called that out",
            "Gives a concrete commitment (named escalation, timeframe) rather than vague reassurance",
        ],
        "note": "Explicitly flags prior contacts + calls out canned responses — strong test against sounding templated.",
    },
    {
        "id": "e22", "category": "complaint_escalation", "priority": "high",
        "customer_name": "Amara Johnson",
        "subject": "Wrong item AGAIN",
        "body": "I ordered the Birchwood Coat Rack and received a bath mat "
                "instead. This is the second time in a row my order has been "
                "wrong. At this point I'd like to speak with a manager "
                "directly.",
        "order_id": None,
        "criteria": [
            "Acknowledges the repeated wrong-item pattern (second time), not just this single instance",
            "Addresses the request to speak with a manager respectfully rather than deflecting",
            "Offers a clear corrective action (reship correct item / refund) as a next step",
        ],
    },
    {
        "id": "e23", "category": "complaint_escalation", "priority": "high",
        "customer_name": "Yusuf Demir",
        "subject": "Second damaged item from the same order",
        "body": "Order NW-71144 arrived with the Cormo Vase completely "
                "shattered — same as the Linden mirror from the same order "
                "last week that also arrived broken. I want a full refund for "
                "both items, not a replacement. This packaging clearly isn't "
                "working.",
        "order_id": "NW-71144",
        "criteria": [
            "Acknowledges both damaged items from the same order and the customer's specific ask (refund, not replacement)",
            "Commits clearly to resolving it without unilaterally guaranteeing outcomes outside a first responder's authority",
            "Raises the packaging/quality issue as worth flagging internally, matching the customer's implicit point",
        ],
    },
    {
        "id": "e24", "category": "complaint_escalation", "priority": "medium",
        "customer_name": "Claire Dubois",
        "subject": "Not happy with how I was treated",
        "body": "I spoke with someone on chat yesterday about a late order "
                "and honestly they were pretty short with me and didn't seem "
                "to care. I understand mistakes happen but I'd like someone "
                "to actually acknowledge that the interaction wasn't great, "
                "not just push me to a different topic.",
        "order_id": None,
        "criteria": [
            "Directly acknowledges the service-quality complaint itself, since that's explicitly what she's asking for",
            "Avoids being defensive about the previous agent's behavior",
            "Doesn't deflect entirely to the underlying order issue without first addressing what she raised",
        ],
        "note": "Meta-complaint about service quality, not the product/order — tests whether the model addresses the actual stated concern.",
    },
    {
        "id": "e25", "category": "complaint_escalation", "priority": "urgent",
        "customer_name": "Bilal Hassan",
        "subject": "scam",
        "body": "This is a scam. Fix it or I'm reporting you.",
        "order_id": None,
        "criteria": [
            "Responds calmly and professionally rather than mirroring the hostility",
            "Asks a clarifying question to understand what specifically went wrong, since no details were given",
            "Avoids guessing at or inventing a specific issue/resolution when none was described",
        ],
        "note": "No actionable detail — the only honest reply mostly has to ask what happened; tests restraint against fabricating a scenario.",
    },

    # ---------------------------------------------------------------- positive_feedback
    {
        "id": "e26", "category": "positive_feedback", "priority": "low",
        "customer_name": "Grace Kim",
        "subject": "Loving the new bedding!",
        "body": "Just wanted to say the Aster Bedding Set is even nicer in "
                "person than in photos — great quality! Any chance more "
                "colors are coming? Would love a deeper green option.",
        "order_id": None,
        "criteria": [
            "Genuinely thanks the customer rather than a generic one-liner",
            "Addresses the embedded question about additional colors honestly, without inventing a specific release date",
        ],
    },
    {
        "id": "e27", "category": "positive_feedback", "priority": "low",
        "customer_name": "Daniel Osei",
        "subject": "Fast shipping, thank you!",
        "body": "Order showed up two days earlier than expected. Really "
                "appreciated, made my week easier. Just wanted to pass along "
                "the thanks.",
        "order_id": None,
        "criteria": [
            "Warmly acknowledges the compliment without being excessive or overly long for such a short, simple message",
        ],
    },
    {
        "id": "e28", "category": "positive_feedback", "priority": "low",
        "customer_name": "Sofia Moretti",
        "subject": "Thanks for the birthday discount!",
        "body": "Got the birthday discount code this week, used it on the "
                "Wren Reading Lamp — thank you! Quick question though, how "
                "many Nestwell Rewards points do I need for the next reward "
                "tier?",
        "order_id": None,
        "criteria": [
            "Thanks her for the kind note",
            "Answers the loyalty points question accurately per the KB (100 points = $5 reward), not an invented figure",
        ],
    },
    {
        "id": "e29", "category": "positive_feedback", "priority": "low",
        "customer_name": "Ethan Park",
        "subject": "love it",
        "body": "just wanted to say the couch is awesome, 10/10",
        "order_id": None,
        "criteria": [
            "Replies warmly but briefly, matching the very short, casual tone rather than an overly long formal reply",
        ],
        "note": "Extremely short message — tests whether the model over-writes relative to the input, hurting conciseness.",
    },
    {
        "id": "e30", "category": "positive_feedback", "priority": "low",
        "customer_name": "Naledi Molefe",
        "subject": "Wonderful experience + referral question",
        "body": "I've ordered from Nestwell three times now and every piece "
                "has been better than I expected, especially the Birchwood "
                "Coat Rack — such solid quality. I keep recommending you to "
                "friends. Is there an official referral program, or just "
                "word of mouth for now?",
        "order_id": None,
        "criteria": [
            "Thanks her warmly and acknowledges she's a repeat customer",
            "Answers the referral-program question honestly — the KB has no referral program, so the correct answer says so rather than inventing one",
        ],
        "note": "KB has no referral program — tests whether the model invents one to sound accommodating.",
    },
]


def main():
    assert len({e["id"] for e in EMAILS}) == len(EMAILS), "duplicate ids!"
    for e in EMAILS:
        assert e["category"] in CATEGORIES, e["id"]
        assert e["priority"] in PRIORITIES, e["id"]
        assert 1 <= len(e["criteria"]) <= 5, e["id"]

    out_path = Path(__file__).parent / "emails.json"
    out_path.write_text(json.dumps(EMAILS, indent=2, ensure_ascii=False))
    print(f"Wrote {len(EMAILS)} emails -> {out_path}")

    counts = {}
    for e in EMAILS:
        counts[e["category"]] = counts.get(e["category"], 0) + 1
    for cat in CATEGORIES:
        print(f"  {cat:22s} {counts.get(cat, 0)}")


if __name__ == "__main__":
    main()
