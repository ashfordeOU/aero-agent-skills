---
name: e2007-indirect-discharge-data-presentation
description: "Evaluate the compliance table an indirect-discharge test result must be presented as under ECSS-E-ST-20-07C clause 5.4.12.5, where each row carries the induced current level observed during the discharges and not the verdict alone. Use when indirect-discharge results are drawn up or reviewed: compute every row margin between the observed induced current and its susceptibility limit, catch a verdict contradicting its own numbers, catch a level cell left empty, and test the table for coverage of every declared application point, both polarities and every monitored circuit. Trigger: ecss, e-st-20-07c, indirect-discharge-data-presentation, induced-current-level-table, discharge-compliance-table, discharge-polarity-coverage, induced-current-susceptibility-margin, unreported-discharge-level."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-indirect-discharge-data-presentation, induced-current-level-table, discharge-compliance-table, discharge-polarity-coverage, induced-current-susceptibility-margin, unreported-discharge-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Indirect-Discharge Data Presentation (space-systems/ecss/e2007-indirect-discharge-data-presentation)

Use when the task is the data-presentation requirement of
ECSS-E-ST-20-07C clause 5.4.12.5 -- showing that an indirect-discharge
result reaches the reader as a table of compliance whose every row also
carries the induced current level the monitored circuit actually saw
while the discharges were being applied.

## Domain quick reference

- The deliverable is two things in one row, not one. A compliance
  column on its own says a decision was taken; the induced current
  column says what it was taken on. Strip the second and the table is
  no longer reviewable, because nothing on the page can be re-graded
  against a limit that later moves.
- The level is a current, on a named circuit. An indirect discharge
  couples into the harness, and what the unit experiences is the
  current that arrives on a particular line, not the kilovolts that
  left the generator. A table that reports the applied discharge level
  and calls that the observed level has reported the stimulus twice
  and the response never.
- A verdict has to agree with its own numbers. A row entered compliant
  whose reported current sits above the susceptibility limit of that
  circuit is a contradiction inside a single row, and it is caught by
  arithmetic rather than by judgement. The same arithmetic clears a
  row honestly entered non-compliant.
- Coverage is part of the presentation, not a separate matter. The
  table is the record that each declared application point was
  discharged, at both polarities, for the number of discharges the
  plan called for, with every declared monitored circuit watched. A
  point or a circuit that appears in no row is missing evidence, and a
  summary count of compliant rows hides that perfectly.
- Not every oddity is a failure. A row that clears its limit by a
  couple of decibels is compliant with no room left, and a row
  reporting a level orders of magnitude under its limit more often
  means the monitor was unconnected or out of range than that the
  circuit was quiet. Both belong in the report as limitations, so the
  reader can act on them without the table being called invalid.

## Workflow

1. Validate each table row: event identifier, application point,
   polarity, discharge count, monitored circuit, susceptibility limit
   and verdict, with the observed induced current carried through as
   absent rather than rejected when the cell is empty.
2. Normalize the verdict and polarity cells to comparison tokens so
   synonyms entered by different test engineers grade alike.
3. Compute the margin in dB between the susceptibility limit and the
   observed induced current of each row, absorbing representation
   error at an exact equality with a named tolerance.
4. Compare each entered verdict with the margin its own row reports,
   and record a finding where the two disagree in either direction.
5. Record a row with no induced current level as the clause's headline
   finding: compliance asserted without the level it rests on.
6. Aggregate coverage: every declared application point present, both
   polarities applied there, the required discharge count reached, and
   every declared monitored circuit appearing somewhere in the table.
7. Report the peak reported level per monitored circuit, then separate
   findings from limitations and return the presentation verdict.

## Pitfalls

- Presenting the compliance column alone. It is the half of the row
  that cannot be re-derived, and a later limit change makes the whole
  campaign unreadable.
- Entering the applied discharge level in the observed-level column.
  The stimulus is not the response, and the substitution is invisible
  once the raw traces are gone.
- Leaving a contradictory row to a reviewer's eye. A pass above the
  limit is arithmetic, and arithmetic should find it before the review
  meeting does.
- Counting compliant rows as coverage. A point never discharged
  contributes no rows at all, so the count goes up as the evidence
  goes down.
- Treating an implausibly quiet channel as a comfortable margin. A
  monitor left unconnected reports the quietest circuit in the test.

## Behavior contract (gate 3)

The row validation, verdict and polarity normalization, induced-current
margin computation, verdict-versus-numbers agreement, unreported-level
detection, coverage-gap aggregation, per-circuit peak reporting and the
overall presentation verdict are exercised by the gate 3 contract test:
scripts/test_e2007_indirect_discharge_data_presentation.py against
scripts/e2007_indirect_discharge_data_presentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_indirect_discharge_data_presentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
