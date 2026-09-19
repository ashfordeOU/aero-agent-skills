---
name: e2040-data-sheet-detailed-design-update
description: "Maintain a device data sheet through the detailed design refresh ECSS-E-ST-20-40C 5.5.4 asks for: fold every timing, power, area and frequency figure the implementation now yields onto the canonical unit of its kind, compare it with the preliminary estimate it replaces, redo the budget comparison against the refreshed value rather than the estimate, and report the parameters nobody refreshed instead of leaving measured and guessed figures mixed in one sheet. Use when detailed design has produced real figures and the preliminary data sheet has to be brought up to them. Trigger: ecss, e-st-20-electrical-scope, data-sheet-detailed-design-update, preliminary-figure-refresh, data-sheet-unit-folding, refreshed-figure-budget-check, unrefreshed-parameter-detection, data-sheet-refresh-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-data-sheet-detailed-design-update, data-sheet-detailed-design-update, preliminary-figure-refresh, data-sheet-unit-folding, refreshed-figure-budget-check, unrefreshed-parameter-detection, data-sheet-refresh-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Detailed Design — Data Sheet Update (space-systems/ecss/e2040-data-sheet-detailed-design-update)

Use when the task is the refresh duty of ECSS-E-ST-20-40C 5.5.4 -- saying
whether the preliminary data sheet has actually been brought up to the
figures detailed design produced, and whether the refreshed figures still
sit inside the budgets the requirement set fixed.

## Domain quick reference

- The preliminary sheet is written while the device is still an intent.
  Its figures are estimates carried from the architecture, and detailed
  design is the first point at which timing comes out of the synthesised
  paths, power out of the switching estimate and area out of the placed
  cells.
- Figures arrive in whatever unit the tool that produced them printed.
  Nanoseconds against seconds and milliwatts against watts compare fine
  numerically and wrongly physically, so both sides are folded onto the
  canonical unit of the parameter kind before anything is compared.
- The budget comparison has to be redone against the refreshed value. A
  newer figure looks authoritative and is assumed to be better, which is
  exactly how a refresh ships a device over its power ceiling.
- A figure landing exactly on its budget meets it. The comparison absorbs
  representation error rather than failing a device that is precisely on
  target, which a strict comparison against a converted figure does.
- A parameter nobody refreshed stays in the sheet and in the count. It is
  the defect the refresh fraction exists to surface, and dropping it
  produces a sheet reporting a complete refresh of the parameters it chose
  to count.
- Provenance is part of the refresh. A figure still sourced from an
  estimate, or still marked provisional, has not closed the parameter even
  though the number changed.

## Workflow

1. Resolve the preliminary sheet: unique parameter identifiers, a
   recognised kind, the estimate and its unit, and the budget with the
   direction it is written in. Refuse a repeated identifier, an unknown
   key, or a direction declared with no budget.
2. Resolve the detailed-design figures the same way, refusing two figures
   for one parameter and an unrecognised source.
3. Fold every estimate and every refreshed figure onto the canonical unit
   of its kind before comparing them.
4. Report each parameter that received no figure, and keep it in the
   parameter count so the refresh fraction tells the truth.
5. Group each refreshed figure as confirmed, increased or decreased
   against its estimate, treating a movement exactly on tolerance as
   confirmed.
6. Redo the budget comparison against the refreshed value in the direction
   the budget is written, and compute the fractional margin.
7. Report figures still marked provisional or still sourced from an
   estimate, then compare the refresh fraction with the goal.

## Pitfalls

- Comparing a refreshed figure with a budget in the unit the tool printed.
  A 4 ns path against a 5 s ceiling passes every time and the sheet reads
  clean while the device is four orders out.
- Assuming a newer figure is a safer figure. The budget check has to run
  again on the refreshed value; skipping it is how a power figure that
  grew during detailed design reaches layout unnoticed.
- Dropping unrefreshed parameters from the denominator. The refresh
  fraction then measures the sheet's own selection and reads best exactly
  when the refresh is worst.
- Failing a figure that lands exactly on its budget. A converted value can
  sit a unit in the last place either side of the bound, so an exact
  landing has to be absorbed rather than compared strictly.
- Treating a changed number as a closed parameter. A figure still marked
  provisional, or still carried from an estimate, leaves the parameter
  open however different it looks.

## Behavior contract (gate 3)

The unit folding, movement grouping, budget direction handling, exact
budget landings, unrefreshed-parameter detection and refresh-fraction
comparison are exercised by the gate 3 contract test:
scripts/test_e2040_data_sheet_detailed_design_update.py against
scripts/e2040_data_sheet_detailed_design_update_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_data_sheet_detailed_design_update.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
