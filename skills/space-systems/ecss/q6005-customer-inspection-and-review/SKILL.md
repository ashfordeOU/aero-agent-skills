---
name: q6005-customer-inspection-and-review
description: "Audit how a hybrid build honoured the customer's rights to witness operations, review records and release product at defined points, under ECSS-Q-ST-60-05C clause 11. Use when a production plan's hold, witness, record-review and notification points have to be graded after the fact: measure the notice each point actually gave against what it required, list the records that were never made available, separate a breach of a hold point from a finding on notice or attendance, and return cleared, cleared-with-findings or release-withheld with the compliant fraction. Trigger: ecss, q-st-60-05c, hybrid-customer-hold-point, hybrid-witness-point-notice, hybrid-customer-record-review, hybrid-production-release-point, hybrid-customer-inspection-plan."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-customer-inspection-and-review, hybrid-customer-hold-point, hybrid-witness-point-notice, hybrid-customer-record-review, hybrid-production-release-point, hybrid-customer-inspection-plan]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Customer Inspection and Review (space-systems/ecss/q6005-customer-inspection-and-review)

Use when the task is clause 11 of ECSS-Q-ST-60-05C: the points at which the
buyer may stop the line, stand at the bench, read the paperwork or let the
product go, and whether a build that has already run actually honoured them.

## Domain quick reference

- The four kinds of point are not degrees of the same thing. A hold point
  stops work until the customer acts. A witness point offers attendance but
  lets the work go ahead once proper notice has been given. A record-review
  point turns on paperwork rather than presence. A notification point only
  has to be told. Grading them all as one loses the only distinction that
  matters when something goes wrong.
- Notice is a measured quantity, not a box. It is the gap between telling the
  customer and running the operation, and it can be short, adequate or
  negative — a notification issued after the event is a real and common case
  and reads as negative days rather than as no notice.
- A hold point passed without a release or a recorded waiver is a breach,
  and no amount of downstream testing converts it back. The customer's right
  at that point was to decide, and the decision was taken away rather than
  failed.
- Silence is not consent at a hold point and is not refusal at a witness
  point. At a witness point the work may go ahead, but only if the
  non-attendance is written down — the record is what makes the customer's
  absence a choice rather than an omission.
- A record review the customer could not perform is not a review. Where the
  records were not available, the point produced no scrutiny whatever the
  response field says, so missing records are graded on the records, not on
  the sign-off.
- A released hold point whose operation never happened is its own finding.
  The permission was granted against a plan, and a plan that moved on without
  performing the step leaves the release attached to nothing.
- The plan itself is graded, not only its points. A set of customer points
  the customer never agreed to is a plan written by one party; every point in
  it can be run perfectly and the arrangement still owes a finding.

## Workflow

1. Validate each point: kind, the scheduled date, the notification date, the
   customer's response from the recognised set, the notice the point
   required, whether the operation went ahead, and the records required
   against the records provided.
2. Take the notice requirement from the point kind unless the plan named one,
   so a plan that is silent is graded against the default rather than against
   zero.
3. Measure the notice as a signed number of days and compare it with the
   requirement, treating notice exactly equal to the requirement as adequate.
4. Fold record names to one spelling before comparing them, so a differently
   punctuated traveller still counts as provided, and list what is missing by
   name rather than as a count.
5. Grade each point into breach, finding or compliant: passing a hold point
   without release and continuing past an unreviewed record review breach;
   short notice, absent records, unrecorded non-attendance and an unperformed
   released operation are findings.
6. Refuse duplicate point identities in a plan — two points with one name
   cannot both be evidenced, and the ambiguity would be silently resolved to
   whichever came last.
7. Roll up: report the compliant fraction, list the breached and flagged
   points by name, add any plan-level finding, and return cleared,
   cleared-with-findings or release-withheld.

## Pitfalls

- Treating every point as a hold point. Doing so makes an ordinary witness
  point that the customer chose not to attend look like an unreleased
  stoppage, and the real breaches disappear into the noise.
- Reading a missing response as consent. At a hold point silence is the
  absence of the decision the customer was entitled to make, and proceeding
  on it is the breach itself.
- Recording attendance and not recording non-attendance. The second is the
  one that matters later: it is the evidence that the customer was offered
  the point and declined it.
- Grading a record-review point on its sign-off. If the records were not
  available, the review did not happen; the sign-off records only that
  someone signed.
- Counting a release as a completed step. A released hold point whose
  operation was never performed leaves an authorisation floating free of any
  work, which is a different defect from an unreleased one and needs saying.
- Comparing the compliant fraction strictly against one. A clean plan lands
  exactly on one, and a strict comparison there answers differently on
  different machines; the equality needs a tolerance.
- Grading only the points and not the plan. A set of customer points the
  customer never agreed is an arrangement defect, and every individual point
  can be flawless while the plan is not.

## Behavior contract (gate 3)

The point validation, the notice arithmetic, the record availability check,
the per-point grading into compliant, finding and breach, the duplicate-id
refusal and the plan-level release decision are exercised by the gate 3
contract test: scripts/test_q6005_customer_inspection_and_review.py against
scripts/q6005_customer_inspection_and_review_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_customer_inspection_and_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
