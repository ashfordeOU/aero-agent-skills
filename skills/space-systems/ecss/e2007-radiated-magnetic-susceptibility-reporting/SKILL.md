---
name: e2007-radiated-magnetic-susceptibility-reporting
description: "Evaluate the reporting pack a radiated magnetic susceptibility run must leave behind under ECSS-E-ST-20-07C clause 5.4.10.5. Use when a test record is assembled or reviewed: confirm the exposure-level table, the setup diagram and the loop verification record are all carried, recompute the axial flux density the radiating loop produces from its current, turns, radius and separation, compare that prediction against the verification reading, grade every recorded frequency by the margin between the exposure level reached and the level required, group each as reached, short or above, and report a required frequency the table never records. Trigger: ecss, e-st-20-07c, radiated-magnetic-susceptibility-reporting, radiating-loop-verification, magnetic-exposure-level-table, magnetic-susceptibility-setup-diagram, loop-axial-field-prediction, magnetic-exposure-frequency-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-magnetic-susceptibility-reporting, radiating-loop-verification, magnetic-exposure-level-table, magnetic-susceptibility-setup-diagram, loop-axial-field-prediction, magnetic-exposure-frequency-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Magnetic Susceptibility, Test Reporting (space-systems/ecss/e2007-radiated-magnetic-susceptibility-reporting)

Use when the task is the reporting requirement of ECSS-E-ST-20-07C
clause 5.4.10.5 -- showing that the record of a radiated magnetic
susceptibility run carries the tables and diagrams that say how the
radiating loop was verified and what magnetic exposure level the run
actually reached at each frequency.

## Domain quick reference

- The clause asks for three artefacts, not one narrative. A table of
  the levels reached against frequency, a diagram of the bench that
  fixes loop position and separation, and the loop verification
  record that ties the two together. A pack missing any one of them
  cannot be repaired by a longer prose section, because each answers a
  question the others do not.
- Loop verification is a prediction compared against a reading, in
  that order. The field the loop geometry produces is computed from
  the drive current, the turn count, the loop radius and the
  separation; the probe reading is then graded against it. Taking the
  reading as truth lets a drifted probe certify itself, which is
  exactly what the verification exists to prevent.
- The axial field of a loop falls off far faster than a bench operator
  expects. Past roughly one loop radius the separation term dominates
  and the field drops with the cube of distance, so a loop held a few
  centimetres further out than the diagram shows can miss the required
  level by tens of decibels with nothing on the bench looking wrong.
- The graded quantity per frequency is a margin: the level reached
  less the level required. Reaching the requirement exactly is
  compliance. Falling short is a finding -- the unit was never exposed
  to what the specification asks. Exceeding it is not a finding at
  all, but it is carried as a limitation, because a unit overdriven
  well past its requirement may have been stressed beyond what the
  qualification intended.
- A margin is a difference of two decibel levels, so a level sitting
  exactly on its requirement can land a few units in the last place
  either side of zero. That is absorbed with a named tolerance inside
  the comparison, never by moving the requirement.
- Frequency coverage is graded against the specified frequency list,
  not against the rows that happen to be present. A table with no row
  at a required frequency has not reported that frequency, however
  complete the rest of it looks.

## Workflow

1. Validate the artefact declaration: the exposure-level table, the
   setup diagram and the loop verification record are each declared
   with a boolean, and any that is absent is named.
2. Validate the loop verification entry, then compute the axial flux
   density its geometry produces and convert it to the decibel scale
   the exposure table is written on.
3. Compare the verification reading against that prediction and grade
   the deviation against the allowed agreement window.
4. Validate the exposure table: at least one row, strictly increasing
   positive frequencies, and both a reached and a required level at
   every row.
5. Compute the margin at every frequency and group it as reached,
   short of the requirement or above it, absorbing representation
   error at zero with the named decibel tolerance.
6. Match the specified frequency list against the recorded rows and
   name every required frequency the table never reports.
7. Aggregate: an absent artefact, a loop reading outside the agreement
   window, a level short of the requirement or an unreported required
   frequency are findings; an overdriven frequency is a limitation on
   an otherwise complete pack.

## Pitfalls

- Reporting the drive current and calling the exposure documented. The
  current is an input to the field, not the field; without the
  geometry beside it the table says nothing about what the unit saw.
- Grading the loop verification by how close two readings are to each
  other. Two probes agreeing with one another agree about nothing if
  neither was compared with the field the geometry predicts.
- Reading the loop separation off the photograph rather than the
  diagram. The axial field is a cube law in that distance once the
  loop is more than its own radius away, so a centimetre of slack
  turns into decibels.
- Treating an overdriven frequency as a pass with margin to spare. It
  is compliant, but it is also a unit exposed harder than the
  specification asks, and that belongs on the record as a limitation.
- Checking that the table has rows instead of checking it has the
  rows the specification requires. A dense sweep that skips a
  required frequency has still not reported that frequency.

## Behavior contract (gate 3)

The artefact-declaration check, loop axial-field prediction, decibel
scale conversion, verification-deviation grading, exposure-table
validation, per-frequency margin and grouping, required-frequency
coverage and the aggregate verdict are exercised by the gate 3
contract test:
scripts/test_e2007_radiated_magnetic_susceptibility_reporting.py
against
scripts/e2007_radiated_magnetic_susceptibility_reporting_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radiated_magnetic_susceptibility_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
