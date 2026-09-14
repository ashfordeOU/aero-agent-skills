---
name: q6013-class-1-incoming-inspection
description: "Determine whether a received delivery of a highest-assurance commercial part goes into bonded store or into quarantine under ECSS-Q-ST-60-13C clause 4.3.7: reconcile part number, date code and quantity against the purchase order, size the external visual sample from the received quantity by an exact integer square-root plan, judge the defects against the accept number, read the bag seal, the humidity indicator card and the elapsed floor-life exposure of the declared moisture sensitivity level, then name every reason a delivery is held. Use when a delivery has to become a receipt disposition. Trigger: ecss, q-st-60-13c-clause-4-3-7, commercial-eee-incoming-inspection, purchase-order-reconciliation, incoming-visual-sample-size, dry-pack-humidity-indicator, msl-floor-life-exposure, receipt-quarantine-disposition."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-incoming-inspection, commercial-eee-incoming-inspection, purchase-order-reconciliation, incoming-visual-sample-size, dry-pack-humidity-indicator, msl-floor-life-exposure, receipt-quarantine-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Incoming Inspection on Receipt (space-systems/ecss/q6013-class-1-incoming-inspection)

Use when the task is the clause 4.3.7 receiving inspection of
ECSS-Q-ST-60-13C: a delivery of commercial parts of the highest
assurance category has arrived, and the question is whether it is
released into bonded store or quarantined at the dock.

## Domain quick reference

- Incoming inspection is the first check the receiving organisation
  performs itself rather than reads about. Everything before it -- the
  lot acceptance tests, the source buy-off -- was carried out by or at
  the supplier, so this is where an independent look at the actual boxes
  first happens.
- Reconciliation is three separate comparisons, not one. The part number
  catches a substitution, the date code catches a lot swap and the
  quantity catches a short or over shipment; a delivery can be correct
  on two of them and wrong on the third.
- The external visual sample has to be reproducible. A square-root plan
  computed in integer arithmetic gives the same sample for the same
  received quantity on every machine that runs it, raised to a declared
  floor for small lots, limited by a declared cap for large ones, and
  never larger than the lot itself.
- Dry-pack integrity is three readings that answer one question. The bag
  seal says whether the barrier held, the humidity indicator card says
  what the inside of the bag saw, and the elapsed factory-floor exposure
  against the floor life of the declared moisture sensitivity level says
  how much of the allowance the parts have already spent. Level 1 needs
  none of it; level 6 has no floor life at all.
- The documents travel with the parts or they are a finding. A
  certificate of conformity promised to follow by email is not a
  certificate of conformity on receipt, and the lot is held until it
  arrives.
- A held delivery gets every reason at once. The dock returns one
  disposition, and a supplier who is told about the seal but not about
  the missing screening data ships the same gap again.

## Workflow

1. Reconcile the part number, the date code and the quantity separately
   against the purchase order, keeping shortfall and overage as distinct
   numbers rather than a signed difference.
2. Size the external visual sample from the received quantity with the
   exact integer square-root plan, applying the declared floor and cap
   and clamping to the lot.
3. Judge the visual defects found against the sample's accept number;
   accept-on-zero is the default, and a higher accept number is declared
   rather than assumed.
4. Read the moisture barrier: seal intact or not, humidity indicator
   against its limit with an exact reading on the limit admissible, and
   exposure against the floor life of the declared level.
5. List the required delivery documents absent or marked not-received.
6. Release to bonded store only when nothing was found; otherwise
   quarantine and report every finding together with the sample size,
   the humidity margin and the floor-life hours remaining.

## Pitfalls

- Reconciling on the part number alone. The right part in the wrong date
  code is a different lot with different test evidence behind it, and
  the date-code traceability of a commercial part is the whole reason
  the highest assurance category tracks it.
- Sizing the visual sample from the ordered quantity. The sample is
  drawn from what actually arrived, so a short delivery is inspected as
  the smaller lot it is.
- Computing the sample with a floating-point square root. A lot size
  that is an exact square can round either way across platforms; integer
  arithmetic makes the sample reproducible and auditable.
- Reading the humidity card without the exposure clock. A card still
  inside its limit on a lot that has already spent its floor life is a
  pass on one question and silence on another.
- Quarantining on the first finding and stopping. The receiving report
  is the supplier's feedback loop; a partial list produces a partial
  correction and the same delivery again.

## Behavior contract (gate 3)

The purchase-order reconciliation, integer square-root sample sizing,
visual accept-number verdict, humidity and floor-life readings, document
check and the overall release-or-quarantine disposition are exercised by
the gate 3 contract test:
scripts/test_q6013_class_1_incoming_inspection.py against
scripts/q6013_class_1_incoming_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_incoming_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
