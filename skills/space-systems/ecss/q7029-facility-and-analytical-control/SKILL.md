---
name: q7029-facility-and-analytical-control
description: "Assess the facility blank, analytical calibration and contamination controls behind an offgassing run under ECSS-Q-ST-70-29. Use when a crew-compartment offgassing result is reported, re-run or disputed. Subtract the facility blank from every reported compound and mark a net that fell under the quantitation limit as not-quantified, return the blank as a fraction of the gross reading, grade the curve on point count, response-factor spread and its age against the validity window, recover the check standard against nominal, test the chamber for carryover from the previous specimen, and close with one run-valid, run-valid-with-actions or run-invalid disposition. Trigger: ecss, q-st-70-29, offgassing-facility-blank, offgassing-blank-corrected-yield, offgassing-calibration-response-factor-spread, offgassing-calibration-validity-window, offgassing-check-standard-recovery, offgassing-chamber-carryover, offgassing-run-validity-disposition."
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
  tags: [ecss, q-st-70-29-offgassing-determination, q-st-70-29, q7029-facility-and-analytical-control, offgassing-facility-blank, offgassing-blank-corrected-yield, offgassing-calibration-response-factor-spread, offgassing-calibration-validity-window, offgassing-check-standard-recovery, offgassing-chamber-carryover, offgassing-run-validity-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Facility and Analytical Control (space-systems/ecss/q7029-facility-and-analytical-control)

Use when the task is the quality-assurance side of ECSS-Q-ST-70-29: the facility
blank, the analytical calibration and the contamination controls that decide
whether the numbers an offgassing run produced may be used at all. This leaf
grades one run's controls, not the material that sat in the chamber.

## Domain quick reference

- An offgassing chamber offgasses. The facility blank is the run made on the
  empty, cleaned chamber through the same sampling train and the same analytical
  column, and it is the only thing that separates what the specimen released
  from what the apparatus released. A result reported without its blank is a
  number about the facility as much as about the material.
- Blank subtraction has a floor. A gross reading close to its blank leaves a net
  that the analytical train cannot resolve, so the net is carried as
  not-quantified rather than as a small positive number that later sums into a
  cabin load as though it had been measured.
- A calibration curve is graded on three separate things, and passing one says
  nothing about the others: how many points it was drawn through, how far the
  response factors scatter across those points, and how old the curve is against
  the window it was declared valid for. A fresh curve through three points and a
  two-year-old curve through nine both fail, for different reasons.
- The check standard is the independent read. It is prepared to a known amount
  and put through the train as a specimen would be, so its recovery reports the
  whole chain rather than the curve fit alone.
- Carryover is a property of the previous specimen, not of this one. A chamber
  that has just held a heavily loaded article can hand its residue to the next
  run, which is why the residue is expressed as a fraction of the previous gross
  reading rather than as an absolute mass.

## Workflow

1. Validate the run record: a gross reading and a facility blank for each
   reported compound, and the quantitation limit of the analytical train.
2. Subtract the blank, floor the net at zero, and separate the compounds into
   quantified and not-quantified rather than reporting sub-limit numbers.
3. Return each blank as a fraction of its gross reading and raise a finding
   where the facility dominates the compound. A fraction landing exactly on the
   limit is counted as inside by a named tolerance, not by moving the limit.
4. Grade the calibration on point count, response-factor spread, age against the
   validity window, and check-standard recovery against its band.
5. Express the post-run chamber residue as a fraction of the previous specimen's
   gross reading and grade the cleaning and bake-out record.
6. Rank findings by severity and close with one disposition: run-valid,
   run-valid-with-actions, or run-invalid.

## Pitfalls

- Reporting a net without the blank that produced it. The subtraction is not
  bookkeeping; a compound that is ninety percent facility reads as a material
  property once the blank is dropped from the record.
- Carrying a sub-limit net forward as a number. Ten compounds each below the
  quantitation limit sum into a cabin load that no instrument ever measured.
- Grading the calibration on the correlation coefficient alone. A curve through
  three points fits anything, and a well-fitted curve six months past its
  validity window is still a curve about a detector that has since drifted.
- Treating the check standard as a formality. It is the only measurement in the
  run whose true value is known, so a recovery outside its band invalidates
  every specimen number the same train produced.
- Testing carryover as an absolute mass. The same residue is negligible after a
  lightly loaded specimen and a clear handover of contamination after a heavy
  one, which the ratio shows and the mass hides.
- Relaxing a control limit so a boundary case passes. A ratio sitting exactly on
  its limit is a representation question, handled by the tolerance inside the
  comparison; the declared limit stays as specified.

## Behavior contract (gate 3)

The blank subtraction and quantitation floor, the blank fraction, the
calibration point count, response-factor spread, validity window and check
standard recovery, the carryover ratio, the cleaning record and the run
disposition are exercised by the gate 3 contract test:
scripts/test_q7029_facility_and_analytical_control.py against
scripts/q7029_facility_and_analytical_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7029_facility_and_analytical_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
