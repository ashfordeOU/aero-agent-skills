---
name: q7001-receiving-inspection-cleanliness
description: "Assess hardware cleanliness at goods receipt and after transport, then name a disposition. Use when a package arrives, the bag and its indicator tell one story, the transport record tells another, and the measured residue and obscuration have to be judged against what the item was bought to. Compares each measurement with its limit, refuses a figure with no method named, reads packaging integrity and purge pressure, checks shock, humidity and elapsed shelf life, notices a receipt opened in an area dirtier than the item needs, and escalates to accept, re-verify, reclean or nonconformance with the consumed margins behind it. Trigger: ecss, q-st-70-01, receiving-inspection-cleanliness, goods-receipt-contamination-check, transport-exposure-record, packaging-integrity-verdict, receipt-disposition-escalation."
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
  tags: [ecss, q-st-70-cleanliness-control-scope, q7001-receiving-inspection-cleanliness, receiving-inspection-cleanliness, goods-receipt-contamination-check, transport-exposure-record, packaging-integrity-verdict, receipt-disposition-escalation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Control — Receiving Inspection (space-systems/ecss/q7001-receiving-inspection-cleanliness)

Use when the task is deciding what happens to an item at goods receipt:
what the surface measures now, what the packaging and transport records
say happened to it on the way, and which of accept, re-verify, reclean
or nonconformance the two together justify.

## Domain quick reference

- Two independent stories arrive with every package. The measurements
  describe the surface; the packaging and transport records describe
  the journey. Either can condemn the item on its own.
- A clean measurement does not clear a breached bag. The breach means
  the sampled area is no longer representative of the whole surface,
  and the sample was almost certainly taken somewhere accessible.
- A measurement with no method named is not a measurement. Residue by
  solvent rinse and residue by tape lift produce different numbers from
  the same surface, and nobody downstream can repeat an unnamed one.
- The useful margin is the fraction of the limit consumed. An item at
  nine tenths of its residue limit on arrival passes and is still a
  problem, because everything after receipt only adds.
- Exceeding a limit is not automatically a rejection. Contamination
  that recleaning routinely removes goes to recleaning and
  re-verification; contamination past what recleaning recovers goes to
  nonconformance. Where that boundary sits is declared once, not
  improvised per item under schedule pressure.
- The inspection is itself a contamination event. Opening a
  precision-clean item in a hall dirtier than it requires can add more
  than the whole journey did, and the area it was opened in belongs in
  the record beside the measurement.
- Cleanliness expires. An item inside its limits, correctly bagged, and
  long past the interval since its last verified cleaning is
  re-verified rather than accepted on a certificate written a year ago
  for a surface nobody has seen since.

## Workflow

1. Validate each measurement: a positive limit, a non-negative value
   and the method that produced it. A missing value quarantines the
   item; a missing method quarantines it too.
2. Compare each value with its limit, treating a value sitting on the
   limit as inside it, and report the fraction of the limit consumed.
3. For an exceedance, compare it with the declared recleaning ceiling
   and route it to recleaning or to nonconformance accordingly.
4. Grade the packaging: outer bag, inner bag, seal, contamination
   indicator and purge pressure against its floor, each with its own
   consequence rather than one combined pass or fail.
5. Grade the transport record against the environment the item allows:
   shock, humidity, and days elapsed since the last verified cleaning
   against the shelf life.
6. Compare the class of the area the package was opened in with the
   class the item requires, and raise a finding when it is dirtier or
   when it was never recorded.
7. Escalate across all of it — the worst input sets the disposition —
   and report the disposition, the worst measurement by consumed
   fraction, and every finding.

## Pitfalls

- Accepting on the measurement alone. The number is real, the bag was
  open in a lorry for two days, and the sample was taken from the one
  face somebody could reach.
- Recording a residue figure with no method. It is compared against a
  limit set for a different method, and the mismatch is invisible.
- Improvising the reclean-or-reject boundary per item. Two identical
  exceedances get different answers depending on who was on shift and
  how close the delivery date was.
- Opening a precision-clean item in the goods-inwards hall. The receipt
  inspection then contaminates the item it was meant to verify, and the
  measurement afterwards is of the hall.
- Reporting pass or fail without the consumed fraction. Nobody sees the
  item that arrived at nine tenths of its limit until it fails after
  integration, when its history is no longer separable.

## Behavior contract (gate 3)

Measurement validation and the missing-method refusal, the
on-the-limit comparison, the recleaning-ceiling split, packaging and
purge grading, transport shock, humidity and shelf-life rules, the
inspection-area class check and the disposition escalation are
exercised by the gate 3 contract test:
scripts/test_q7001_receiving_inspection_cleanliness.py against
scripts/q7001_receiving_inspection_cleanliness_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_receiving_inspection_cleanliness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
