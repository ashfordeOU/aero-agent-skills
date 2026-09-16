---
name: q60-class-1-lot-acceptance-testing
description: "Use when a delivery has to become a submission plan rather than a pass-fail verdict. Plan which Class 1 EEE units of a delivery still owe a lot acceptance submission under ECSS-Q-ST-60C clause 4.3.5: split the delivery into one submission unit per part number, date code and manufacturer lot, size each draw with exact rational arithmetic that rounds the percentage rule up and clamps it between the declared floor and the unit quantity, and test every acceptance record on file for the same material, a date no later than the submission day and a validity window counted in whole calendar months. Trigger: ecss, q-st-60c-clause-4-3-5, class-1-lot-acceptance-submission, date-code-submission-unit, lat-record-validity-window, lat-submission-draw-sizing, outstanding-lot-submission."
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
  tags: [ecss, q-st-60c-eee-class-1-scope, q60-class-1-lot-acceptance-testing, class-1-lot-acceptance-submission, date-code-submission-unit, lat-record-validity-window, lat-submission-draw-sizing, outstanding-lot-submission]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts -- Lot Acceptance Submission (space-systems/ecss/q60-class-1-lot-acceptance-testing)

Use when the task is the clause 4.3.5 submission duty of ECSS-Q-ST-60C: a
delivery of Class 1 parts has arrived or is being prepared, and the question
is which lots and date codes inside it still have to go for lot acceptance
verification, and how many pieces each of those submissions draws.

## Domain quick reference

- The submission unit is the material, not the paperwork. A part number, a
  date code and a manufacturer lot identifier together name one unit; two
  date codes in one delivery note are two units and take two submissions,
  because pieces built in different weeks came off different material.
- Quantities of the same triple add. A delivery that lists the same lot on
  three lines is still one submission unit, and splitting it into three
  submissions buys nothing but three sampling costs.
- The draw is sized by a percentage rule that rounds up, raised by a declared
  floor for small units and capped at the unit quantity. A unit smaller than
  the floor is drawn whole rather than refused.
- An existing acceptance record closes a unit only when it names the same
  material: same part number, same date code, and the same lot identifier
  where both carry one. A record from the neighbouring week is a record about
  other material.
- Record currency is a whole-month question against the submission day. A
  record dated after the day it is offered against is not evidence yet, and a
  record past its window has stopped being evidence.

## Workflow

1. Group the delivery lines into submission units by part number, date code
   and lot identifier, adding the quantities of repeated triples and refusing
   a line with a zero quantity or a malformed date code.
2. Size each unit's draw from the percentage rule using exact rational
   arithmetic, so a rate that lands exactly on a whole number of pieces does
   not round up an extra one on one platform and not on another.
3. Raise the draw to the declared floor, then clamp it to the unit quantity;
   report the clamp rather than silently sampling the whole unit.
4. Test each acceptance record against each unit in turn, and keep the reason
   a record was set aside so a near miss can be shown to the reviewer.
5. Mark a unit covered only on a record that names its material, is dated on
   or before the submission day and sits inside the validity window.
6. Report the outstanding units, the pieces those submissions will consume,
   and the fact that the delivery broke into more than one unit at all.

## Pitfalls

- Submitting a delivery as one lot. The date code is what makes the material
  homogeneous; pooling two codes under one submission is the defect the
  per-date-code rule exists to prevent.
- Rounding the draw with float arithmetic. A rate times a quantity that should
  be a whole number of pieces can land a few units either side of it, and the
  ceiling then differs between build machines. The rule is rational here.
- Letting a record from an adjacent date code close a unit. It names other
  material, however close the week and however identical the part number.
- Treating a record dated after the submission day as coverage. Evidence that
  does not exist yet on the day of the question is not evidence.
- Discarding the reason a record was set aside. A unit reported as simply
  uncovered hides that a record existed and had just gone out of window.

## Behavior contract (gate 3)

The date-code normalisation, delivery grouping, exact draw sizing, record
coverage test and the outstanding-unit plan are exercised by the gate 3
contract test:
scripts/test_q60_class_1_lot_acceptance_testing.py against
scripts/q60_class_1_lot_acceptance_testing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_1_lot_acceptance_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
