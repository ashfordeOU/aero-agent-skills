---
name: q60-class-1-precap-source-inspection
description: "Audit the witnessed pre-cap source inspection covering the Class 1 production lots of an order. Use when a lot is about to be sealed or its inspection record reviewed: place the witness point before the seal in the manufacturing flow, report an assembly or rework step running between the two, reject a witness who is not independent of the manufacturer, count the notice given in working days against the notice required, size the sample each lot owes, and admit an unwitnessed lot only against a referenced nonconformance. Trigger: ecss, ecss-q-st-60c-clause-4-3-4, class-1-precap-source-inspection, precap-witness-independence, source-inspection-notice-working-days, precap-lot-sample-size, precap-nonconformance-waiver."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-1-precap-source-inspection, ecss-q-st-60c-clause-4-3-4, class-1-precap-source-inspection, precap-witness-independence, source-inspection-notice-working-days, precap-lot-sample-size, precap-nonconformance-waiver]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts — Pre-cap Source Inspection (space-systems/ecss/q60-class-1-precap-source-inspection)

Use when the task is the pre-cap source inspection of ECSS-Q-ST-60C clause
4.3.4 — the inspection witnessed at the manufacturer's premises before the
package is sealed, applied across the Class 1 production lots an order
carries.

## Domain quick reference

- The witness point is defined by the seal, not by the calendar. Everything
  the inspection exists to see — die placement, bond quality, foreign
  material in the cavity — stops being visible the moment the lid goes on,
  and no later inspection recovers it without destroying the device.
- Being before the seal is necessary and not sufficient. A die replacement or
  a rework step between the witness and the seal changes what is inside the
  package after the witness signed, so the flow between the two steps is part
  of what is judged.
- Witnessed means witnessed by somebody else. The manufacturer's own
  inspector repeating an in-house check produces the same measurements and
  none of the independence the clause is buying.
- Notice is counted in working days at the manufacturer's site. A witness
  point announced on a Friday afternoon for the following Tuesday is
  arithmetically short however many calendar days sit between, and declared
  non-working days shorten it further.
- The sample a lot owes scales with the lot and has a floor. A percentage
  alone lets a small lot be inspected with one device; a floor alone makes a
  large lot no better covered than a small one.
- A lot sealed without a witness is recoverable, but only on the record. The
  nonconformance carries both a reference and the alternative route agreed in
  its place; either one alone leaves the lot uncovered with paperwork over
  it.
- Coverage is reconciled both ways. A lot on the order with no inspection
  record is the obvious gap; a record naming a lot the order does not carry
  is the one that hides a lot mix-up at the manufacturer.

## Workflow

1. Validate the order and its lot list, rejecting a lot listed twice.
2. For each witnessed lot, locate the inspection step and the seal step in
   the manufacturing flow and confirm the inspection comes first.
3. Report any restricted assembly or rework step running between the
   inspection and the seal.
4. Validate the witness: a named person, a named organisation, and
   independence from the manufacturer.
5. Count the working days between notification and inspection, excluding
   declared non-working days, and compare with the notice required.
6. Size the sample from the lot's device count, taking the larger of the
   percentage and the floor and capping it at the lot, with a
   representation-sized tolerance so a product landing on a whole number is
   not rounded up.
7. For a lot sealed without a witness, require a nonconformance carrying both
   a reference and an agreed alternative route.
8. Reconcile ordered lots against inspection records in both directions, then
   report the per-lot records, the witnessed fraction and a verdict carrying
   every finding.

## Pitfalls

- Scheduling the witness against the seal date rather than the flow. The
  dates move; the step order is what makes the inspection possible.
- Allowing a rework between the witness and the seal because the witness
  already signed. The signature covers the package as it stood, and the
  rework is precisely what nobody saw.
- Accepting the manufacturer's quality department as the witness. The
  inspection is then an in-house check with a customer's form number on it.
- Counting notice in calendar days. A weekend and a plant shutdown can turn a
  comfortable-looking fortnight into fewer working days than the order
  requires.
- Fixing the sample as a flat number for every lot. A large lot then receives
  the coverage that was sized for a small one.
- Rounding a sample up because the arithmetic landed a hair above a whole
  number. The extra device is bought from a floating-point artefact, not from
  the lot size.
- Closing a sealed-without-witness lot with a nonconformance number and no
  alternative route. The number records that the coverage was lost; it does
  not replace it.
- Stopping at the first finding. The inspection owner needs the whole list to
  close the campaign in one pass.

## Behavior contract (gate 3)

The flow sequence check, the restricted-step rule between inspection and
seal, witness independence, the working-day notice arithmetic, the lot sample
sizing, the nonconformance waiver route, the two-way lot reconciliation, the
witnessed fraction and the overall campaign verdict are exercised by the gate
3 contract test: scripts/test_q60_class_1_precap_source_inspection.py against
scripts/q60_class_1_precap_source_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_precap_source_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
