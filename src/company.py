"""
Single source of truth for the fictional company the generator/judge both
reference. Keeping this in one module means the generator's system prompt
and the judge's grounding prompt can never drift out of sync on policy facts.
"""

COMPANY_NAME = "Nestwell"

CATEGORIES = [
    "shipping_delay",
    "refund_request",
    "product_question",
    "app_bug",
    "complaint_escalation",
    "positive_feedback",
]
PRIORITIES = ["low", "medium", "high", "urgent"]

KB_TEXT = """\
COMPANY: Nestwell — direct-to-consumer home goods (furniture, bedding, decor).

SHIPPING: Standard shipping is 5-7 business days. Expedited shipping is 2-3
business days. If a standard order exceeds 10 business days with no tracking
movement, escalate to the logistics team.

RETURNS & REFUNDS: Items may be returned within 30 days of delivery if unused
and in original packaging. Final-sale items are not eligible for return.
Refunds are issued to the original payment method and typically post within
5-7 business days AFTER Nestwell receives the returned item (not after the
customer ships it).

DAMAGED / DEFECTIVE ITEMS: Do not require the standard return process,
even outside the 30-day window — flag for a supervisor/replacement-or-refund
decision rather than applying the return-window rule.

BILLING ERRORS (e.g. duplicate charges): Not covered by the standard return
policy. These should be escalated to the billing team for investigation;
agents should not promise a specific refund timeline for these since it
depends on the payment processor.

APP / WEBSITE: Customers track orders via the Nestwell app or account page.
Known issue: order status can lag up to 24 hours behind actual carrier scans.

SUPPORT HOURS: Monday-Friday, 9am-6pm ET.

LOYALTY PROGRAM: "Nestwell Rewards" — members earn 1 point per $1 spent;
100 points = a $5 reward.

REFERRAL PROGRAM: Nestwell does not currently have a formal referral program.

ESCALATION POLICY: Any customer on their 2nd+ unresolved contact about the
same issue, or raising a chargeback/legal threat, should be flagged as
priority "urgent" for a human supervisor rather than handled with a routine
reply.

Agents must not invent policy details, product specs, or dates that are not
listed above. If the needed information isn't in this KB, say so and offer
to find out, rather than guessing.
"""
