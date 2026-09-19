---
name: q7028-acceptance-criteria
description: "Evaluate a finished repair or modification of a printed circuit board assembly against the acceptance limits of ECSS-Q-ST-70-28C, which differ by the repair category and by the defect that was treated. Resolve the defect to the category that addresses it and flag a mismatch, scale every ceiling and floor to the assurance level of the product, express each measurement as a utilisation of its own bound so a ceiling and a floor compare on one scale, name the criterion closest to failing, and hold a criterion with no measurement behind it open rather than passing it. Use when dispositioning a repair or auditing an acceptance record. Trigger: ecss, q-st-70-28c, board-repair-acceptance-limits, repair-category-defect-match, repair-assurance-level-scaling, repair-criterion-utilisation, repair-open-measurement-item."
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
  tags: [ecss, q-st-70-28c-pcb-repair-and-modification, q-st-70-28c, q7028-acceptance-criteria, board-repair-acceptance-limits, repair-category-defect-match, repair-assurance-level-scaling, repair-criterion-utilisation, repair-open-measurement-item]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PCB Repair — Acceptance Criteria (space-systems/ecss/q7028-acceptance-criteria)

Use when the task is the acceptance step of ECSS-Q-ST-70-28C: deciding whether
a completed repair or modification of a printed circuit board assembly meets
the limits its repair category carries, at the assurance level the product is
built to, and naming the criterion that governed the decision.

## Domain quick reference

- Acceptance is per repair category and per defect, not per board. A jumper
  across a broken conductor and a rebuilt land are graded on entirely
  different quantities, and a single house limit covers neither properly.
- The defect selects the category. A repair recorded under a category that
  does not treat the defect found was either mis-recorded or performed with
  the wrong procedure; both are findings, and the measurements taken under
  the wrong category cannot be made to answer for the right one.
- The criteria run in two directions. Some quantities may not exceed a
  ceiling — width loss, damage depth, rework cycles — and others may not fall
  below a floor — overlap length, bond strength, coating thickness. A single
  comparison operator applied to both silently inverts half of them.
- Utilisation puts both directions on one scale. A ceiling utilisation is the
  value over its limit; a floor utilisation is the limit over the value. At
  or below one the criterion is met either way, and the highest utilisation
  is the criterion to act on first.
- The assurance level scales the bounds, and it has to scale them together.
  Tightening the ceilings while leaving the floors alone produces a level
  that is stricter about damage and no stricter at all about the repair.
- A criterion with no measurement behind it is an open item. Grading only the
  quantities that happen to have been recorded turns an incomplete inspection
  into an acceptance, and it is the unrecorded one that tends to be the
  awkward one.
- Acceptance is a conjunction. One breached criterion refuses the repair
  however comfortable the others were, and the useful output is the governing
  criterion and its utilisation rather than the verdict alone.

## Workflow

1. Resolve the defect to the repair category that treats it, and compare that
   against the category the repair was recorded under.
2. Pull the criteria that category carries, each with its direction, its unit
   and its stated bound.
3. Scale every bound to the assurance level of the product, bringing ceilings
   down and floors up by the same factor.
4. Reject a measurement that does not belong to the category rather than
   silently ignoring it.
5. Convert each supplied measurement into a utilisation of its own bound, and
   mark it met when the utilisation sits at or below one within a named
   tolerance.
6. List every criterion with no measurement behind it as an open item.
7. Take the governing criterion as the highest utilisation, and return the
   verdict, the breaches, the open items and every finding.

## Pitfalls

- Grading a repair against the limits of the category it was recorded under
  without checking that the category treats the defect. The numbers then all
  pass, against the wrong bounds.
- Applying one comparison direction to every criterion. A floor read as a
  ceiling accepts a one-millimetre overlap and refuses a six-millimetre one.
- Scaling only the ceilings when the assurance level tightens. The floors
  stay where they were and the level buys less than it appears to.
- Reading an absent measurement as a pass. The criterion was never
  demonstrated, and an open item is the honest disposition.
- Reporting accept or reject without the governing criterion. A reject then
  gives the repair station nothing to change, and a pass hides that one
  criterion was at ninety-nine per cent.
- Averaging utilisations across the criteria. Acceptance is a conjunction;
  the mean of a breach and four comfortable margins is a comfortable margin.

## Behavior contract (gate 3)

The defect-to-category resolution and mismatch finding, criterion sets and
their directions, assurance-level scaling of ceilings and floors, utilisation
on one scale, open-item handling and governing-criterion selection are
exercised by the gate 3 contract test:
scripts/test_q7028_acceptance_criteria.py against
scripts/q7028_acceptance_criteria_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7028_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
