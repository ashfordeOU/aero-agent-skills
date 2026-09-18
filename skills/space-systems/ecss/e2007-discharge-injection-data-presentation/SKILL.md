---
name: e2007-discharge-injection-data-presentation
description: "Audit the data package a discharge-injection test hands over under ECSS-E-ST-20-07C clause 5.4.13.5: confirm every generator setting that defines the applied pulse is present, build the planned point, level and polarity matrix, check each cell carries one oscilloscope record and one compliance row, catch reused capture identifiers and ambiguous duplicated cells, and confirm a calibration brackets the run inside its validity window with the amplitude holding from one end to the other. Use when a discharge-injection report is assembled or reviewed. Trigger: ecss, e-st-20-07c, discharge-injection-data-presentation, discharge-generator-settings-record, discharge-compliance-table-coverage, discharge-oscilloscope-record-set, discharge-calibration-bracketing, discharge-injection-package-completeness."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-discharge-injection-data-presentation, discharge-generator-settings-record, discharge-compliance-table-coverage, discharge-oscilloscope-record-set, discharge-calibration-bracketing, discharge-injection-package-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Discharge-Injection Data Presentation (space-systems/ecss/e2007-discharge-injection-data-presentation)

Use when the task is the data-presentation requirement of ECSS-E-ST-20-07C
clause 5.4.13.5 -- showing that a discharge-injection run handed over the
generator settings it was run at, a compliance table covering what was
applied, and the oscilloscope records taken both while calibrating and
while testing, so the run can be read back years later by someone who was
not in the room.

## Domain quick reference

- The package has to let a reader reconstruct the pulse. Charge voltage,
  storage capacitance, discharge resistance, pulse count per polarity and
  repetition interval are what define it; with any one absent the report
  says a unit passed without saying what it passed.
- Coverage is against a matrix, not a list. The run is a grid of
  injection point by amplitude level by polarity, and both the
  oscilloscope records and the compliance table are complete only when
  every cell of that grid is accounted for. Counting records and
  comparing the total against the expected number hides a doubled cell
  sitting next to an empty one.
- Two records for one cell are as bad as none. Which capture speaks for
  that cell is then a matter of opinion, and a reviewer who picks the
  favourable one is not reviewing anything. The same holds for a
  duplicated compliance row carrying a different observed status.
- Capture identifiers are the link between the table and the records.
  Reusing one silently redirects a row to the wrong waveform, and nothing
  downstream can detect it, so a repeated identifier is a defect in the
  package even when every cell is otherwise covered.
- Amplitude levels are written as decimals and must never be matched as
  floats. Quantizing the level to a fixed integer before it is used as a
  key makes a cell written 4.0 in one file and 4.000000 in another one
  cell, on any machine.
- Calibration has to bracket the run. One before it shows the generator
  delivered the set pulse when the run began; one after shows it still
  did when the run ended, which is the only evidence that the amplitude
  did not decay across a long test. A single opening calibration proves
  the start and assumes the rest.
- Amplitude that does not rise with level is a signal, not a nuisance. A
  higher level recording a lower peak usually means a mis-set generator,
  a saturated probe or a mislabelled capture, so it is recorded as an
  unexplained observation rather than quietly accepted.
- Severity ordering matters in the table. The worst observed status is
  what the run is dispositioned on, and statuses outside the agreed set
  are what the disposition has to address.

## Workflow

1. Validate the package: injection points, amplitude ladder, polarities,
   generator settings, calibration records, run captures, compliance rows
   and the run start and stop times.
2. Build the required matrix of point, quantized level and polarity
   cells, rejecting a repeated point, level or polarity.
3. Audit the generator settings, separating a field that is absent or
   blank, which is a gap in the package, from a field present with a
   value of the wrong kind, which is an input error.
4. Normalize the run captures onto matrix cells and report covered,
   missing, duplicated and unplanned cells, plus any reused capture
   identifier and any level pair whose peak current falls as the level
   rises.
5. Normalize the compliance rows the same way, count the observed
   statuses, take the worst, and list the cells whose status falls
   outside the agreed set.
6. Find the opening and closing calibration records inside the validity
   window either side of the run and compare their amplitudes against the
   allowed drift.
7. Aggregate: missing settings, uncovered or duplicated cells, reused
   identifiers, an out-of-set status and an unbracketed or drifted
   calibration are findings; unplanned records and unexplained amplitude
   reversals are limitations. Report both completeness ratios.

## Pitfalls

- Checking that the number of oscilloscope records equals the number of
  planned cells. Two records for one cell and none for another gives the
  same total and passes the check.
- Matching a compliance row to a capture on the level as a float. The
  same level written to a different precision in two tools becomes two
  cells, and the coverage report fills with phantom gaps.
- Accepting a single calibration taken before the campaign. It says
  nothing about whether the generator still delivered that pulse at the
  end of a run that took a day.
- Treating a reused capture identifier as a clerical slip. It rewires a
  compliance row to a waveform from a different cell, and no later check
  can recover which was meant.
- Reporting the first non-conforming status found rather than the worst.
  The run is dispositioned on the most severe observation, not the
  earliest one in the table.
- Dropping records that fall outside the planned matrix. They are usually
  a repeat, a spare point or an aborted attempt, and carrying them as
  unreferenced is honest where deleting them is not.

## Behavior contract (gate 3)

The package validation, matrix construction, level quantization,
generator-settings audit, capture and compliance coverage with duplicate
and identifier detection, status counting and severity ordering,
calibration bracketing and drift comparison are exercised by the gate 3
contract test:
scripts/test_e2007_discharge_injection_data_presentation.py against
scripts/e2007_discharge_injection_data_presentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_discharge_injection_data_presentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
