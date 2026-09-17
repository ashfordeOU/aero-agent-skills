---
name: q60-class-3-lot-acceptance-testing
description: "Plan which Class 3 EEE date codes of a delivery still owe a lot acceptance submission under ECSS-Q-ST-60C clause 6.3.5: split the delivery into one submission unit per part number and date code, let a manufacturer report discharge a unit only while it names the part, sits inside the production window around that date code and stays inside its validity, reduce the draw for a preferred-source unit under the quantity ceiling, and size every outstanding draw in exact rational arithmetic against the spares left after build demand. Use when a Class 3 delivery has to become a per-date-code submission plan rather than one pass-fail verdict. Trigger: ecss, q-st-60c-clause-6-3-5, class-3-lot-acceptance-submission, class-3-manufacturer-report-credit, class-3-production-window-date-code, class-3-reduced-submission-draw, class-3-submission-spare-check."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-3-lot-acceptance-testing, class-3-lot-acceptance-submission, class-3-manufacturer-report-credit, class-3-production-window-date-code, class-3-reduced-submission-draw, class-3-submission-spare-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Lot Acceptance Testing (space-systems/ecss/q60-class-3-lot-acceptance-testing)

Use when the task is the lot acceptance submission of ECSS-Q-ST-60C clause
6.3.5 — deciding which parts of a delivered Class 3 shipment still have to be
submitted for lot acceptance verification, how many pieces each submission
draws, and whether the shipment can give those pieces up.

## Domain quick reference

- The submission population at Class 3 is the **part number and date code**
  together. Two deliveries of the same part built in different weeks came off
  the line under different settings, so one submission cannot stand for both;
  merging them buys a smaller plan and evidences less than it appears to.
- Class 3 is the class where the **manufacturer's own** lot acceptance report
  is allowed to discharge the submission. It earns that only on three tests at
  once: it names the same part number, it was raised on a date code inside the
  production window around the submitted one, and it is still inside its
  validity on the planning day. Two out of three is not a credit.
- A report that fails carries the **reason** it failed into the plan. A report
  two weeks outside the window and a report for a different part are different
  problems — one can be closed by asking the manufacturer for the neighbouring
  week's data, the other never can.
- A **preferred source** below the quantity ceiling earns a reduced draw, not a
  waiver. The ceiling exists because the reduction rests on source history, and
  a large delivery carries more of the lot's risk than that history covers.
- Draws are sized in **exact rational arithmetic** and rounded up. A share of a
  quantity computed in floating point can land either side of a whole piece
  depending on the host, and a submission plan that changes with the machine it
  was written on is not a plan.
- Submission pieces are **consumed**. A unit whose spares cannot cover its draw
  is an infeasible unit — the honest output is a finding against the build
  demand, not a quietly smaller draw.

## Workflow

1. Split the delivery into submission units, one per part number and date code,
   merging lines that share a population and refusing a line whose build demand
   exceeds what it delivered.
2. Carry the preferred-source status only when every line feeding the unit
   declares one; a mixed unit is not a preferred-source unit.
3. Test each manufacturer report against each unit on part number, production
   window and validity, recording every reason a report failed.
4. Size the full draw from the unit quantity in exact rational arithmetic,
   raise it to the floor, hold it under the cap, and never draw more pieces
   than the unit holds.
5. Route the unit: credit first, then the reduction for a preferred source
   under the quantity ceiling, then a full submission.
6. Set the acceptance number from the draw size, and check the draw against the
   spares left after the build demand.
7. Report the per-unit plan with its total draw, and raise a finding when no
   report discharged any unit of the delivery.

## Pitfalls

- Planning the delivery as one lot. The date codes are separate populations,
  and a single submission evidences only the one it was drawn from.
- Crediting a report on part number alone. The window and the validity are the
  other two tests, and a report can pass the easy one and fail both others.
- Stretching the production window to absorb a near miss. The window is the
  acceptance criterion; a report two weeks outside it is uncredited data, not
  marginal data.
- Reducing the draw for a preferred source of any size. Above the ceiling the
  source history no longer covers the delivery and the full draw is owed.
- Sizing a draw with floating-point division. The rounding direction at a whole
  piece differs between platforms, so the plan stops being reproducible.
- Under-drawing a unit that cannot spare its pieces. The shortfall then appears
  at kitting instead of in the plan, where it can still be argued.

## Behavior contract (gate 3)

The submission-unit split, manufacturer-report credit on part number, window
and validity, exact rational draw sizing, the reduced route and the spare-unit
feasibility check are exercised by the gate 3 contract test:
scripts/test_q60_class_3_lot_acceptance_testing.py against
scripts/q60_class_3_lot_acceptance_testing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_lot_acceptance_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
