---
name: q6013-class-3-buy-off-inspection
description: "Evaluate whether a lot of commercial EEE parts may be released at the final customer buy-off of ECSS-Q-ST-60-13C clause 6.3.6, at the lowest assurance class: admit the witnessed, desk-review or delegated route only where it names what makes it auditable, walk the short document pack item by item instead of scoring it as a percentage, reconcile the order against delivery less the receipt rejections and hold an overage past the declared ceiling, send a moisture-sensitive lot in a breached bag to a bake, refuse a use-as-is closure with no named authority or one dated before the delivery, and return release, partial release or hold. Use when a delivery has to become a release verdict. Trigger: ecss, q-st-60-13c-clause-6-3-6, class-three-buy-off-release, buy-off-release-route-admissibility, delivery-quantity-reconciliation, moisture-barrier-bake-decision, use-as-is-closure-authority."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-buy-off-inspection, class-three-buy-off-release, buy-off-release-route-admissibility, delivery-quantity-reconciliation, moisture-barrier-bake-decision, use-as-is-closure-authority]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Buy-Off Inspection (space-systems/ecss/q6013-class-3-buy-off-inspection)

Use when the task is the clause 6.3.6 final inspection of ECSS-Q-ST-60-13C at
the lowest assurance class: a lot of commercial parts has arrived, and the
buy-off decides whether it is released to the project, released in part, or
held where it stands.

## Domain quick reference

- At this class the buy-off is normally taken at the receiving end rather than
  at the manufacturer's bench. A documentary desk review on the delivery pack
  is the ordinary route, a witnessed source inspection is still available, and
  the release may be delegated to the supplier outright. All three are
  admissible; the concession is on the travel, not on the record, so each
  route has to name what makes it auditable -- an independent inspector and
  the organisation behind them, the desk review record, or the delegation
  reference and its issue.
- The required document set is short at this class, which is exactly why it is
  a list of items and not a score. The certificate of conformity, the date
  code traceability record, the packaging and electrostatic evidence and the
  quantity reconciliation each answer a different question, so a pack at three
  of four is a hold on the fourth, never a pass at seventy-five percent.
- The quantity is reconciled, not accepted. What the project has is the
  delivery less the pieces rejected on receipt. A shortfall releases what did
  arrive and keeps the balance open against the supplier; an overage past the
  declared ceiling is a hold, because unordered pieces have no purchase order
  behind them and no place in the stores record.
- A moisture-sensitive part is released against its packaging as much as
  against its paperwork. A breached barrier bag or a humidity indicator past
  its limit sends the lot to a bake before it reaches the line, and a part
  below the sensitivity threshold is untouched by either.
- Nonconformances are grouped by severity and by the way they were closed, and
  each closure route carries its own requirement. A use-as-is decision needs a
  named authority and a decision day that is not earlier than the delivery it
  dispositions; a repair needs its verification reference; a scrapping needs
  neither, because the pieces are gone. A closure missing its requirement is
  an open nonconformance wearing a different word.
- Optional evidence does not block anything. Where none was offered the
  receiving side is taking the lot on the required pack alone, which is worth
  saying out loud and worth keeping out of the blocking findings.

## Workflow

1. Validate the delivery record: a named lot reference, a parsable delivery
   day, and a release block naming its route.
2. Admit the release route only against the references and flags that route
   requires, and name each one that is missing.
3. Walk the required document pack item by item, listing every absent item and
   reporting the share beside the list rather than instead of it.
4. Reconcile the order: delivered less the receipt rejections gives the usable
   quantity, and the declared overage tolerance gives the ceiling above which
   a delivery is held.
5. Take the moisture decision from the sensitivity level, the barrier bag and
   the humidity indicator, comparing the indicator with its limit through a
   named tolerance so a reading on the limit is accepted.
6. Group the nonconformances, refuse each closure that does not carry its own
   requirement, and hold the lot on any open major or on minors past the
   declared allowance.
7. Release the lot when nothing blocks and nothing is short, release it in
   part when only the quantity is short, and otherwise hold it on receipt
   naming every failing check.
8. Report the advisories -- thin optional evidence, an open balance -- apart
   from the findings that actually blocked.

## Pitfalls

- Reading the desk-review route as a lighter record. It is a lighter trip, not
  a lighter file; a desk release with no review record has released a lot on
  nobody's signature.
- Turning the short document pack into a percentage. The pack is short so that
  each item carries more weight, and a missing certificate of conformity
  cannot average away against three items that were present.
- Accepting the delivered count as the usable count. The pieces rejected on
  receipt are already gone, and a stores record built on the delivery note
  overstates what the project can actually build with.
- Waving through an overage because more is better. Unordered pieces have no
  purchase order and no traceable acceptance, and they turn up later as parts
  with no provenance.
- Releasing a moisture-sensitive lot on its paperwork alone. The bag and the
  indicator are part of the release, and a breached bag is a bake, not a note.
- Treating a use-as-is as a closure by itself. Without a named authority, and
  with a decision day earlier than the delivery it is meant to disposition,
  there is nothing for a later reader to audit and the finding is still open.

## Behavior contract (gate 3)

The day parsing, per-route release admissibility, item-by-item document walk,
quantity reconciliation and ceiling, moisture bake decision at the indicator
boundary, nonconformance grouping with a requirement per closure route, and
the release, partial-release or hold disposition are exercised by the gate 3
contract test: scripts/test_q6013_class_3_buy_off_inspection.py against
scripts/q6013_class_3_buy_off_inspection_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_buy_off_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
