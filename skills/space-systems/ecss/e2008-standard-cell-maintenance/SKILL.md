---
name: e2008-standard-cell-maintenance
description: "Audit the thermal custody record of a primary or working solar-array standard cell under ECSS-E-ST-20-08C clause 10.2.4, where the cell stays below fifty degrees Celsius in operation and in storage alike: take every logged reading with its sensor uncertainty, treat a reading whose uncertainty band reaches past the ceiling as indeterminate rather than compliant, size each excursion in degree-minutes above the ceiling instead of by peak alone, and settle one verdict - within limit, excursion tolerated, recalibration required or standard withdrawn - with a primary standard given no excursion budget at all. Use when a standard cell must be shown fit before it calibrates anything. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c, solar-array-standard-cell-maintenance, primary-standard-cell-temperature-ceiling, working-standard-cell-excursion-budget, standard-cell-degree-minute-exposure, standard-cell-sensor-uncertainty-band."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-standard-cell-maintenance, solar-array-standard-cell-maintenance, primary-standard-cell-temperature-ceiling, working-standard-cell-excursion-budget, standard-cell-degree-minute-exposure, standard-cell-sensor-uncertainty-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Standard Cell Maintenance (space-systems/ecss/e2008-standard-cell-maintenance)

Use when the task is clause 10.2.4 of ECSS-E-ST-20-08C -- keeping the
primary and working standard cells of a solar-array measurement chain
below fifty degrees Celsius, in operation and in storage alike. The
ceiling is not a test condition that switches off between campaigns; it
is a custody condition that holds for as long as the cell exists,
because the artefact every array measurement is traced to is the one
piece of hardware whose value cannot be re-derived from anything else
on the floor.

## Domain quick reference

- Two roles, and the severity is not the same. A primary standard is
  the traceable artefact -- it calibrates the working cells, and there
  is nothing above it to restore its value. A working standard is the
  day-to-day cell, itself traced back to the primary, so a bounded
  insult costs an intercomparison rather than the artefact.
- The damage mechanism is the junction, not the reading. Heat degrades
  a cell irreversibly and quietly: the cell still produces current
  afterwards, it simply produces the wrong one, and nothing in a later
  measurement reveals that the reference moved.
- Peak alone is the wrong metric. Two degrees over for an hour and
  twenty degrees over for a minute are different insults, so exposure
  is summed in degree-minutes above the ceiling, weighted by the dwell
  the log actually records.
- Storage counts. Most real excursions happen with nobody watching --
  a cell left in a vehicle, a cabinet against a sunlit wall, a shipment
  held on an apron -- which is exactly why the clause names storage
  next to operation.
- A reading carries sensor uncertainty. A cell logged at the ceiling by
  a sensor good to a degree was never shown to be under the ceiling, so
  that reading is indeterminate, and an indeterminate reading is
  charged at its upper bound rather than waved through.
- The budgets are declared project policy, not physical constants: a
  primary standard carries a tolerated budget of zero, a working
  standard carries a small one, and both carry a larger figure past
  which the cell is withdrawn rather than recalibrated.

## Workflow

1. Declare the role of the cell and the ceiling in force. Reject an
   uncategorized role rather than defaulting it, because the tolerated
   budget and therefore every verdict hangs on it.
2. Normalise the exposure log. Each reading needs a temperature, the
   dwell it represents, the mode it was taken in, and the sensor
   uncertainty if one is known; reject an empty log rather than reading
   silence as compliance.
3. Categorize each reading: above the ceiling, indeterminate because
   the uncertainty band crosses it, or within limit.
4. Sum the exposure in degree-minutes above the ceiling, charging an
   indeterminate reading at its upper bound, and split the total
   between operation and storage so the custody gap is visible.
5. Grade the exposure against the budget the role carries and map it
   to one verdict: within limit, excursion tolerated, recalibration
   required, or standard withdrawn.
6. Report the peak, the margin the peak kept below the ceiling, and
   whether the cell may still calibrate anything before the finding is
   closed.

## Pitfalls

- Reading the ceiling as an operating-only limit. The clause names
  storage as well, and the storage leg is where the unwatched
  excursions live; a record that logs only test days is not a custody
  record at all.
- Judging by peak temperature alone. A brief spike and a long soak can
  share a peak and differ by two orders of magnitude in the damage they
  do, which is why the exposure is weighted by dwell.
- Letting an indeterminate reading pass as compliant. A value sitting
  on the ceiling with a degree of sensor uncertainty is evidence of
  nothing; treating it as a pass silently assumes the sensor erred in
  the convenient direction.
- Giving a primary standard the working-standard budget. The working
  cell can be restored by intercomparison against the primary; the
  primary cannot be restored by anything in the building, so its
  tolerated budget is zero by construction.
- Comparing a summed exposure against a budget by bare arithmetic. A
  total that lands exactly on the budget can fall a few units in the
  last place either side of it, so the comparison absorbs that
  representation error while the budget itself stays untouched.

## Behavior contract (gate 3)

The reading categorization, uncertainty charging, degree-minute
exposure sum, mode split, role-dependent grading and custody verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_standard_cell_maintenance.py against
scripts/e2008_standard_cell_maintenance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_standard_cell_maintenance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
