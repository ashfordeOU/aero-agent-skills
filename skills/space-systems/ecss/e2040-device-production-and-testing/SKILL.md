---
name: e2040-device-production-and-testing
description: "Evaluate the production and production-test evidence a device owes per implementation technology under ECSS-E-ST-20-40C clause 5.7.2. Use when the task is confirming every technology the device is built on has its own production report rather than one shared record, checking the unit counts through starts, completions, tests and passes are internally consistent, computing the test coverage and the lot yield from those counts, grading both against the agreed floors, confirming the test program exercises the parameters the technology owes, and aggregating the lots into a per-technology verdict. Trigger: ecss, e-st-20-40c, device-production-and-testing, per-technology-production-report, production-test-coverage-fraction, device-lot-yield-fraction, production-unit-count-consistency, production-test-parameter-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-production-and-testing, device-production-and-testing, per-technology-production-report, production-test-coverage-fraction, device-lot-yield-fraction, production-test-parameter-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Device Production and Testing (space-systems/ecss/e2040-device-production-and-testing)

Use when the task is the production and production-test activity of
ECSS-E-ST-20-40C clause 5.7.2 -- building the device and demonstrating,
technology by technology, that what came out of the line was tested and
what the testing found.

## Domain quick reference

- The reporting unit is the technology, not the device. A device built
  on two technologies has two production lines, two test programs and
  two sets of results, and one merged report hides whichever of them is
  the worse. The obligation is one report per technology used.
- Four counts describe a lot and they nest: units started, units
  completed, units tested, units passed. Each has to be no larger than
  the one before it. A lot reporting more tested than completed is not
  a good lot, it is a bookkeeping error, and its yield figure means
  nothing.
- Coverage and yield answer different questions. Coverage is tested
  over completed and says how much of the output was looked at; yield
  is passed over tested and says what the looking found. High yield on
  low coverage is the combination that ships escapes.
- Coverage and yield are graded differently. A coverage floor short of
  full production test is a deliberate, agreed decision and is checked
  as such. A yield below its expectation is a finding that opens an
  investigation, not automatically a rejection: the lot may still be
  acceptable once the failures are understood.
- A test program is only as good as the parameter list it exercises.
  A program that runs fast, passes everything and never touches a
  parameter the technology owes has coverage of units and none of
  behaviour, so the owed parameter list is checked separately from the
  unit counts.
- Zero completed units is not a zero-yield lot; it is a lot with no
  denominator, and reporting 0.0 for it invents a result.

## Workflow

1. Validate the device record: identifier and a non-empty list of
   implementation technologies with no duplicates.
2. Validate each technology record: the technology name has to be one
   the device declares, the owed parameter list non-empty, and the
   coverage floor and yield expectation fractions inside zero to one.
3. Validate each lot: identifier, and the four unit counts as
   non-negative integers. Reject a count that exceeds the one above it
   in the nesting rather than reporting a fraction above one.
4. Compute coverage as tested over completed and yield as passed over
   tested, refusing a zero denominator instead of substituting zero.
5. Grade coverage against the agreed floor and yield against its
   expectation, absorbing representation error at the boundary with a
   named tolerance so a lot exactly on a floor is not failed by the
   last bit of a division.
6. Check the test program: every parameter the technology owes has to
   appear in the program's parameter list, and the missing ones are
   named.
7. Aggregate per technology over its lots, then over the device: a
   technology with no report at all is its own finding, and the device
   is complete only when every declared technology reported and no lot
   carries a coverage or program finding.

## Pitfalls

- Filing one production report for a multi-technology device. The
  merged figures average a good line with a bad one and neither is
  recoverable afterwards.
- Reporting yield without coverage. Ninety-nine per cent passed means
  one thing when everything was tested and nothing at all when a tenth
  was.
- Treating a low yield as an automatic rejection. It is a finding that
  demands an explanation; the disposition follows the failure analysis,
  not the fraction on its own.
- Dividing by a zero denominator to keep the table full. A lot with no
  completed units has no coverage, and printing 0.0 for it is a
  fabricated number in a report a reviewer will trust.
- Counting units tested as parameter coverage. A program can touch
  every unit and still never exercise a parameter the technology owes.

## Behavior contract (gate 3)

The count-consistency validation, coverage and yield computation,
floor grading with tolerance, owed-parameter program check and
per-technology aggregation are exercised by the gate 3 contract test:
scripts/test_e2040_device_production_and_testing.py against
scripts/e2040_device_production_and_testing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_production_and_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
