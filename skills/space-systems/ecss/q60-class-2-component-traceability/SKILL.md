---
name: q60-class-2-component-traceability
description: "Maintain an unbroken identity trail for class 2 EEE parts from goods receipt through storage and kitting into finished assemblies, under ECSS-Q-ST-60C clause 5.5.4: read the depth each receipt record actually supports, from part number through date code and lot to a serialised one, compare it with the depth the application criticality demands, reconcile received quantity against issued, scrapped and remaining, reject an assembly that consumed a lot never issued to it, flag a bin that mixed two lots into one identity or a lot held past its storage limit, and trace a lot forward into hardware. Use when a class 2 lot must be traced into an assembly. Trigger: ecss, q-st-60c, class-2-eee-traceability, class-2-trace-depth-shortfall, class-2-lot-quantity-reconciliation, class-2-mixed-lot-bin-detection, class-2-forward-and-backward-lot-trace."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c, q60-class-2-component-traceability, class-2-eee-part, class-2-eee-traceability, class-2-trace-depth-shortfall, class-2-lot-quantity-reconciliation, class-2-mixed-lot-bin-detection, class-2-forward-and-backward-lot-trace]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Component Traceability (space-systems/ecss/q60-class-2-component-traceability)

Use when the task is the traceability step of ECSS-Q-ST-60C clause 5.5.4 for
an EEE part procured to the intermediate assurance class — showing that every
part in a finished assembly can be named back to the lot, the manufacturer and
the receipt record it came from, and that every part received can be found
again.

## Domain quick reference

- A class 2 trail has a depth, not a yes or no. It can rest on the part number
  alone, on the date code, on the lot with its conformity reference, or on an
  individual serial number, and each of those is a different amount of evidence
  about which parts are where.
- Depth is only meaningful against a demand. The function the parts go into
  sets the depth owed, so the same receipt record is sufficient for one
  application and short by two steps for another. Reporting the shortfall in
  steps says how far the recovery has to go; a bare fail does not.
- A serial list shorter than the delivered quantity is not a serialised trail.
  It names some parts and leaves the rest resting on the lot, which is the
  depth the trail actually has.
- Quantity is the arithmetic check no paperwork can fake. Received has to equal
  issued plus scrapped plus remaining, and a lot that gave out more than it
  held is broken whatever its certificates say.
- An assembly that consumed a lot never issued to it has no trail at all, and
  it is the one defect that survives every tidy store record, because the
  mismatch only shows when the two sides are compared.
- One bin holding two lots of the same part number merges two identities into
  one and breaks both. Two different part numbers in one bin break nothing.
- Storage has a limit. The identity survives it; the evidence behind the part's
  solderability and packaging does not.

## Workflow

1. Read the depth each receipt record actually supports from the fields it
   carries, treating a partial serial list as lot depth rather than serialised.
2. Read the depth the application criticality demands and report the shortfall
   in steps, zero when the trail already reaches deep enough.
3. Reconcile each lot: received against issued, scrapped and remaining,
   reporting a negative remainder rather than clamping it away.
4. Compare the issue records against the assembly records and list every
   assembly that consumed a lot never issued to it.
5. Detect bins holding more than one lot of the same part number, and lots held
   past the storage limit as of the assessment date.
6. Trace forward from each lot to the assemblies it reached and backward from
   an assembly to the lots it drew on.
7. Return one verdict per lot — unidentified, broken-chain, quantity-imbalance,
   storage-limit-exceeded, incomplete-receipt-record, trace-depth-short or
   traceable — and the share of lots that came out traceable.

## Pitfalls

- Reading a trail as traceable because the paperwork is present. The depth the
  record supports and the depth the application owes are two different numbers.
- Accepting a partial serial list as a serialised trail. The parts without a
  serial are exactly the ones the recall would have to find.
- Clamping a negative remainder to zero. The imbalance is the finding; hiding
  it turns a broken lot into a tidy one.
- Checking store records and assembly records separately. Each looks complete
  on its own, and the unsourced consumption only appears in the comparison.
- Flagging every shared bin. Two part numbers in one bin are two identities
  that never met; only two lots of the same part number merge.
- Treating a storage overrun as a paperwork problem. The identity is intact and
  the supporting evidence is not, which is why it earns its own verdict.

## Behavior contract (gate 3)

The achieved-depth reading, the demanded depth and its shortfall, the quantity
reconciliation, the unsourced-consumption comparison, the mixed-bin detection,
the storage-limit test, the forward and backward traces, the per-lot verdict
ordering and the traceable share are exercised by the gate 3 contract test:
scripts/test_q60_class_2_component_traceability.py against
scripts/q60_class_2_component_traceability_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_component_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
