---
name: q1009-major-disposition
description: "Determine the disposition a major nonconformance may be granted at the customer nonconformance review board under ECSS-Q-ST-10-09C clause 5.2.3.4. Use when a major NCR needs a use-as-is, rework, repair, scrap or return-to-supplier decision, when a departure left in delivered hardware has to be recorded as a concession, or when the board's quorum is in doubt: assess every disposition against safety, interface and lifetime impact, attach conditions that carry an owner and a means of verification, refuse a request the impacts close off, and hold release while a condition stays open. Trigger: ecss, q-st-10-09c, major-nonconformance-disposition, customer-nrb-quorum, use-as-is-concession, repair-procedure-approval, disposition-conditions, concession-record, ncr-release-hold."
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
  tags: [ecss, q-st-10-09c-nonconformance-scope, q1009-major-disposition, major-nonconformance-disposition, customer-nrb-quorum, use-as-is-concession, repair-procedure-approval, disposition-conditions, concession-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Major Disposition at the Customer Board (space-systems/ecss/q1009-major-disposition)

Use when the task is the disposition step of ECSS-Q-ST-10-09C clause
5.2.3.4 — deciding, at the customer's nonconformance review board, what
may be done with items carrying a major nonconformance, on what
conditions, and what concession the decision leaves behind in the
record.

## Domain quick reference

- Severity decides whose board sits. A major nonconformance is the
  customer's to disposition; a minor one stays with the supplier's own
  board. Routing a major item through a supplier board is not a
  shortcut, it is an unapproved disposition.
- Five dispositions are on the table: use-as-is, rework, repair, scrap
  and return-to-supplier. They split in two. Rework restores the item
  to the original requirement and scrap removes it, so neither leaves
  anything to concede. Use-as-is and repair both hand over hardware
  that departs from an agreed requirement, so both earn a recorded
  concession with a justification the customer signed against.
- Three impacts close the departure route entirely: an effect on
  safety, on an interface, or on the declared lifetime. When any of
  them is present the board cannot accept the item as built or repair
  it into acceptance; the remaining routes are rework, scrap or return.
- Repair is admissible only against an approved repair procedure —
  repairing to an unapproved method substitutes one uncontrolled
  departure for another. Return-to-supplier exists only where a
  supplier furnished the item in the first place.
- A board that is not quorate does not produce a weaker decision, it
  produces no decision. The customer representative, product assurance
  and engineering are the three seats the disposition needs.
- Conditions are part of the grant, not a wish list appended to it.
  Each one carries an owner and a stated means of verification, and
  while one is open the disposition stands but the affected items are
  not released.

## Workflow

1. Confirm the severity is major and the board is the customer's;
   reject a minor item rather than dispositioning it here.
2. Take the board roster and check the quorum. Missing seats defer the
   item to the next sitting; they never downgrade the decision.
3. Establish the three impacts and the two enabling facts — is the item
   reworkable, is a repair procedure approved, was it supplier
   furnished — and derive the admissible dispositions from them rather
   than from what was requested.
4. Compare the requested disposition with that admissible set. A
   request the impacts close off is refused with the blocking reason
   and the alternatives named, so the originator resubmits against a
   route that exists.
5. Where the granted route leaves a departure, record the concession:
   nonconformance identifier, requirement departed from, quantity
   affected, justification and the roles that approved it. A departure
   without a justification is returned, not granted.
6. Evaluate the conditions attached to the grant, flag any that lack an
   owner or a verification means, and permit release only once every
   condition is closed.
7. Report the verdict, the granted route, the concession entry and the
   findings, so the closure step downstream has the criteria it will
   later verify against.

## Pitfalls

- Granting use-as-is because rework is expensive. Cost is not one of
  the three impacts; safety, interface and lifetime are, and an item
  that touches any of them is not acceptable as built whatever the
  rework bill looks like.
- Treating repair as a lighter rework. Repair leaves a departure from
  the drawing in the delivered item, so it carries the same concession
  duty as use-as-is and additionally needs its procedure approved
  before the board can grant it.
- Recording the disposition and losing the conditions. A conditional
  grant that is filed as a plain grant releases hardware whose
  supporting analysis or inspection has not happened yet.
- Counting a quorum by headcount. Four attendees from one discipline
  are not a board; the three named seats are what make the decision
  binding on the customer.
- Leaving the quantity affected out of the concession. The concession
  covers a stated effectivity, and an open-ended one silently extends
  to units that were never assessed.
- Dispositioning without naming the requirement departed from. A
  concession against no identified requirement cannot be verified at
  closure and cannot be rolled into the as-built configuration.

## Behavior contract (gate 3)

The severity routing, board quorum, admissibility derivation, condition
grading, concession record and release decision are exercised by the
gate 3 contract test: scripts/test_q1009_major_disposition.py against
scripts/q1009_major_disposition_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q1009_major_disposition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
