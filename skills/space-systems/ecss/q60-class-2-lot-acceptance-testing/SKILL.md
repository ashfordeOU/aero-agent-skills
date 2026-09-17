---
name: q60-class-2-lot-acceptance-testing
description: "Plan which Class 2 EEE lots of a delivery still owe a lot acceptance submission under ECSS-Q-ST-60C clause 5.3.5: split the delivery into one submission unit per part number, date code and manufacturer lot, settle each acceptance test group of a unit separately, credit evidence that names the lot for the endpoint and environmental groups while letting same-family evidence discharge the endurance group alone, and size every outstanding draw per group with exact rational arithmetic. Use when a Class 2 delivery has to become a per-group submission plan rather than one pass-fail verdict. Trigger: ecss, q-st-60c-clause-5-3-5, class-2-lot-acceptance-submission, class-2-acceptance-test-group-coverage, class-2-family-evidence-endurance-credit, class-2-submission-draw-sizing, class-2-date-code-submission-unit."
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
  tags: [ecss, q-st-60c-eee-class-2-scope, q60-class-2-lot-acceptance-testing, class-2-lot-acceptance-submission, class-2-acceptance-test-group-coverage, class-2-family-evidence-endurance-credit, class-2-submission-draw-sizing, class-2-date-code-submission-unit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 EEE Parts -- Lot Acceptance Submission (space-systems/ecss/q60-class-2-lot-acceptance-testing)

Use when the task is the clause 5.3.5 submission duty of ECSS-Q-ST-60C: a
delivery of Class 2 parts has arrived or is being prepared, and the question is
which lots and date codes inside it still have to go for lot acceptance
verification, which acceptance test groups of each of those are already
discharged by evidence on file, and how many pieces the remaining groups draw.

## Domain quick reference

- The submission unit is the material, not the paperwork. A part number, a date
  code and a manufacturer lot identifier together name one unit; two date codes
  on one delivery note are two units and take two submissions, because pieces
  built in different weeks came off different material.
- Quantities of the same triple add. A delivery listing the same lot on three
  lines is one submission unit, and splitting it into three buys nothing but
  three sampling costs.
- A Class 2 unit is settled group by group, not as a whole. Manufacturer
  evidence commonly closes the endpoint group and leaves the endurance group
  open; reporting the unit as simply uncovered throws that away and re-submits
  work already done.
- Evidence scope is what separates Class 2 from Class 1 here. The endpoint and
  environmental groups are lot-level questions and need evidence naming that
  lot. The endurance group is the relaxation: it asks about the technology
  family and the process, so evidence from another lot of the same family
  carries it.
- Each group ages on its own clock. An endurance record outlives an endpoint
  sweep, so one validity window across all groups either expires evidence that
  is still good or honours evidence that has gone stale.
- The draw is per group, sized by a percentage rule that rounds up, raised by
  that group's floor and capped at the unit quantity. A unit smaller than the
  floor is drawn whole rather than refused.

## Workflow

1. Group the delivery lines into submission units by part number, date code and
   lot identifier, adding the quantities of repeated triples and refusing a line
   with a zero quantity, a malformed date code or a technology family that
   contradicts the family already recorded for that lot.
2. Take each required acceptance test group of each unit in turn rather than
   asking one question about the unit as a whole.
3. Test the records against the group: the record has to carry that group, name
   the right material for its scope, be dated no later than the submission day
   and sit inside that group's own validity window.
4. Admit family-scope evidence only for the endurance group, and only when both
   the record and the unit carry a technology family and the two agree.
5. Size the draw of every group left open using exact rational arithmetic, so a
   rate that lands on a whole number of pieces does not round up an extra one on
   one platform and not on another.
6. Route the unit from the groups still open: evidence accepted when none is,
   a partial submission when some are, a full submission when all are.
7. Report the outstanding units, the groups each still owes, the pieces those
   submissions consume, and the fact that the delivery broke into more than one
   unit at all.

## Pitfalls

- Submitting a delivery as one lot. The date code is what makes the material
  homogeneous; pooling two codes under one submission is the defect the
  per-date-code rule exists to prevent.
- Settling the unit with a single yes or no. A record covering the endpoint
  group says nothing about endurance, and treating it as full coverage ships a
  lot whose life data was never obtained.
- Letting family evidence close a lot-level group. The relaxation is narrow and
  reaches the endurance group only; extending it to the endpoint group accepts
  a lot nobody measured.
- Running one validity window across every group. The endurance record and the
  endpoint sweep age at different rates and a single window mis-handles one of
  them in every direction.
- Rounding the draw with float arithmetic. A rate times a quantity that should
  be a whole number of pieces can land either side of it, and the ceiling then
  differs between build machines. The rule is rational here.
- Discarding the reason a record was set aside. A group reported as simply open
  hides that a record existed and had just gone out of window.

## Behavior contract (gate 3)

The date-code normalisation, delivery grouping, per-group draw sizing, the
scope and window tests an acceptance record has to pass, the family-evidence
relaxation and the unit routing are exercised by the gate 3 contract test:
scripts/test_q60_class_2_lot_acceptance_testing.py against
scripts/q60_class_2_lot_acceptance_testing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_2_lot_acceptance_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
