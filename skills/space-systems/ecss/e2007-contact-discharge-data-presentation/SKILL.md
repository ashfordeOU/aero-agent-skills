---
name: e2007-contact-discharge-data-presentation
description: "Evaluate the report a direct contact discharge result reaches the reader as, under ECSS-E-ST-20-07C clause 5.4.14.5, where the generator settings, the calibration oscilloscope records and a compliance table all have to be on the page. Use when contact discharge results are drawn up or reviewed: check every settings field is filled, require an oscilloscope record for each applied level and polarity, derive the bandwidth a sub-nanosecond edge needs and de-embed the scope rise time from the trace, grade each row response against its performance criterion, catch a verdict contradicting its own response cell, and test the table for point, polarity and count coverage. Trigger: ecss, e-st-20-07c, contact-discharge-data-presentation, esd-generator-settings-record, contact-discharge-calibration-oscilloscope-trace, esd-scope-bandwidth-adequacy, contact-discharge-compliance-table, esd-performance-criterion-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-contact-discharge-data-presentation, esd-generator-settings-record, contact-discharge-calibration-oscilloscope-trace, esd-scope-bandwidth-adequacy, contact-discharge-compliance-table, esd-performance-criterion-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Contact-Discharge Data Presentation (space-systems/ecss/e2007-contact-discharge-data-presentation)

Use when the task is the data-presentation requirement of
ECSS-E-ST-20-07C clause 5.4.14.5 -- showing that a direct contact
discharge result reaches the reader as three things on the page at once:
the generator settings the run was produced with, the oscilloscope
records taken when the discharge current waveform was calibrated, and a
table of compliance covering the application points.

## Domain quick reference

- The settings block is what makes the run reproducible. A charge level
  in kilovolts means nothing on its own; the discharge resistor, the
  storage capacitor, the tip that was fitted, the polarities and the
  discharges per point are what turn it into an event somebody else can
  produce again. A field left empty is missing evidence, not a
  formatting slip, and an empty cell is not a zero.
- The oscilloscope record is the only thing on the page that shows what
  the generator actually delivered. Every level and polarity the table
  reports needs one; a table with rows at levels no trace covers rests
  those rows on the generator's front panel alone.
- A trace is only as fast as the instrument that took it. An edge under
  a nanosecond needs a front end whose bandwidth is around the
  rise-time-bandwidth product over that edge, and below it the recorded
  rise time is the scope's own step response wearing the event's name.
- Adequacy is graded against the specified edge, never against the edge
  the trace reports. A slow front end records a slow edge, so a check
  fed its own output calls every slow instrument fast enough for what it
  managed to capture -- the oracle and the measurement share the same
  error and cannot disagree.
- Even an adequate instrument adds something. The recorded edge is the
  event and the instrument in quadrature, so de-embedding the front end
  gives the rise time that belongs to the discharge; when the instrument
  contributed a material share of what was printed, the de-embedded
  value travels with the report rather than replacing it silently.
- A verdict has to agree with its own response cell. The performance
  criterion says how far the unit was allowed to move -- no effect, a
  response that clears itself, or one an operator had to clear -- and a
  row entered compliant whose response sits past that allowance is a
  contradiction inside a single row, caught by ordering rather than by
  judgement. The same ordering clears a row honestly entered
  non-compliant.
- Coverage is part of the presentation. The table is the record that
  each declared point was discharged at both polarities for the number
  of discharges the plan called for; a point appearing in no row is
  missing evidence, and a count of compliant rows hides that perfectly.
- A row clearing its criterion by nothing at all is compliant with no
  room left, and that belongs in the report as a limitation so the
  reader can act on it without the table being called invalid.

## Workflow

1. Audit the generator settings block: report every required field that
   is absent, blank or empty rather than filling it in, and refuse a
   field carrying a value of the wrong kind altogether.
2. Validate each oscilloscope record: a trace identifier, the level and
   polarity it was taken at, the front-end bandwidth and the recorded
   rise time, with the specified edge defaulted only when the record
   declares none.
3. Derive the bandwidth the specified edge needs, grade each instrument
   against it, de-embed the front end from the recorded rise time, and
   report the share of the printed edge the instrument put there.
4. Validate each compliance-table row: identifier, application point,
   polarity, level, discharges applied, performance criterion and
   verdict, with an empty response cell carried through as absent rather
   than rejected.
5. Re-derive each verdict by ordering the observed response against the
   allowance of its criterion, and record a finding wherever the entered
   verdict and its own numbers disagree in either direction.
6. Record a row with no observed response as the clause's headline
   finding: compliance asserted without the observation it rests on.
7. Match the level and polarity of every row against the oscilloscope
   records, and aggregate coverage over declared points, polarities and
   the required discharge count.
8. Separate findings from limitations and return the presentation
   verdict.

## Pitfalls

- Presenting the compliance column alone. The settings and the traces
  are the halves that cannot be re-derived later, and a campaign without
  them is unreadable the moment a limit or a criterion moves.
- Grading the scope against the edge it recorded. That is the one
  comparison that can never fail, because both sides carry the same
  instrument error.
- Printing the recorded rise time as the event's. The front end is in
  the number, and on a marginal instrument it is most of it.
- Leaving a contradictory row to a reviewer's eye. A pass past the
  criterion's allowance is an ordering, and an ordering should find it
  before the review meeting does.
- Counting compliant rows as coverage. A point never discharged
  contributes no rows at all, so the count goes up as the evidence goes
  down.
- Reading an empty response cell as no effect. Nothing observed and
  nothing happening are different claims, and only one of them was made.
- Treating a row at the very top of its allowance as comfortable. It
  passed, with nothing left over, and the reader has to be told.

## Behavior contract (gate 3)

The settings audit, oscilloscope-record validation, required-bandwidth
derivation, front-end de-embedding and contribution share, row
validation with an absent response carried through, verdict re-derivation
against the performance criterion, unreported-response detection,
trace-to-row matching, coverage-gap aggregation and the overall
presentation verdict are exercised by the gate 3 contract test:
scripts/test_e2007_contact_discharge_data_presentation.py against
scripts/e2007_contact_discharge_data_presentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_contact_discharge_data_presentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
