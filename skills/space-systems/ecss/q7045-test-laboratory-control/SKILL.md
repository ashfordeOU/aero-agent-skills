---
name: q7045-test-laboratory-control
description: "Audit whether a test laboratory is in control of the campaign it is about to run: written procedures, qualified people and equipment records. Use when a mechanical test campaign under ECSS-Q-ST-70-45 has to be shown competently staffed and documented before the first specimen is pulled: walk each qualification and each certificate forward by whole calendar months, decide authorisation on the run day rather than today, refuse a procedure that is draft or held at a superseded revision, refuse an equipment record with no certificate or an empty traceability chain, and cover every method with an operator, a procedure and its equipment. Trigger: ecss, q-st-70-45-mechanical-testing, test-laboratory-quality-control, test-operator-qualification-currency, test-procedure-revision-control, test-equipment-traceability-record, test-campaign-method-coverage."
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
  tags: [ecss, q-st-70-45-mechanical-testing, q7045-test-laboratory-control, test-laboratory-quality-control, test-operator-qualification-currency, test-procedure-revision-control, test-equipment-traceability-record, test-campaign-method-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing — Test Laboratory Control (space-systems/ecss/q7045-test-laboratory-control)

Use when the task is the laboratory-quality step ahead of a mechanical
test campaign under ECSS-Q-ST-70-45: the machines exist and the
specimens are cut, and the question is whether the procedures, the
people and the equipment records behind the campaign will stand up to
being looked at afterwards.

## Domain quick reference

- Currency is a question about the run day, not about today. A campaign
  planned four months out can be staffed entirely by people who are
  qualified now and lapsed by the time the first specimen is pulled.
- Validity is counted in calendar months. Adding twelve months to the
  last day of a long month lands on the last day of the month it
  reaches, and a leap year moves the end of February with it, which is
  exactly where certificates cluster.
- A procedure has two separate defects. It can be in the wrong state --
  draft rather than issued -- and it can be in the right state at a
  revision that has since been superseded; a campaign that names a
  third revision is a third defect again.
- An equipment record is only as good as what it points at. A
  certificate reference with an empty traceability chain is a record
  that leads nowhere, and it fails whether or not the calibration date
  is still in the future.
- Not every observation blocks. A second operator who has lapsed while
  a first is authorised, or a certificate inside its warning window, is
  something the laboratory should know and not something that stops the
  campaign. Mixing the two makes the blocking list unreadable.
- Readiness is per method. A campaign is only as ready as its least
  covered method, and a method is covered when an authorised operator,
  an approved procedure and every named item of equipment all line up.

## Workflow

1. Resolve the run day, and refuse a day the calendar does not have
   rather than rolling it forward.
2. For every operator competency, add the validity in whole months to
   the qualification day, take the days left to the run day, and
   separate lapsed from nearly lapsed.
3. Collect the operators authorised on each method; a method with none
   is a blocking finding, and a lapsed colleague beside an authorised
   one is an advisory.
4. Grade the procedure the method names: held at all, issued rather than
   draft, at the current revision, and at the revision the campaign
   asked for.
5. Grade each equipment record: certificate reference present,
   traceability chain not empty, calibration still current on the run
   day, with the warning window raised as an advisory.
6. Cover the campaign method by method and list the methods that are
   ready.
7. Declare the laboratory ready only when the blocking list is empty,
   and carry the advisories separately so neither hides the other.

## Pitfalls

- Checking qualifications on the day the question is asked. The run day
  governs, and a long campaign can start covered and finish uncovered.
- Adding a year as 365 days. The difference shows at the month ends
  where qualification and calibration records cluster.
- Accepting a procedure because it exists. Existing, issued and current
  are three separate conditions and a campaign can fail any one of them
  with the document sitting open on the bench.
- Treating a certificate number as traceability. The number identifies
  the certificate; the chain is what connects it to a standard, and an
  empty chain is a finding on its own.
- Folding advisories into the blocking list. A laboratory that cannot
  tell which finding stops the campaign starts ignoring all of them.

## Behavior contract (gate 3)

The calendar arithmetic, run-day authorisation, procedure state and
revision grading, equipment traceability and currency grading, and the
per-method coverage that separates blocking findings from advisories
are exercised by the gate 3 contract test:
scripts/test_q7045_test_laboratory_control.py against
scripts/q7045_test_laboratory_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7045_test_laboratory_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
