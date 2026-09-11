---
name: e1003-dev-tests
description: "Use when plan and execute development tests for a space system under
  ECSS-E-ST-10C §4.2: define each test objective with a traceable success criterion,
  specify the test conditions and their acceptable tolerance bands, record actual
  conditions during test execution, evaluate all measurements against minimum and
  maximum requirement bounds, and confirm the development test report contains every
  mandatory element (objective reference, actual conditions, measurements, outcome,
  and anomaly record). Development tests precede the qualification test programme
  and generate design margin data to reduce programme risk. Trigger: ecss,
  e-st-10-system-scope, development-testing, test-objectives, test-conditions,
  test-reporting, test-plan, qualification-precursor."
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
  tags: [ecss, e-st-10-system-scope, development-testing, test-objectives, test-conditions, test-reporting, test-plan]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Systems Testing — Development Tests (space-systems/ecss/e1003-dev-tests)

Use when the task is to plan and execute development tests for a space
system under ECSS-E-ST-10C §4.2 — establishing test objectives with
traceable success criteria, specifying and verifying test conditions,
evaluating measurements against requirement bounds, and producing a
compliant development test report.

## Domain quick reference

- §4.2 defines development tests as tests performed before the
  qualification test programme, intended to verify design approaches,
  explore performance margins, and generate engineering data that reduces
  qualification risk. They are not acceptance tests and are not held to
  the full qualification witness chain.
- Every development test must carry at least one objective with a stated
  success criterion. An objective without a traceable criterion is not
  a valid test objective under §4.2; the criterion must be checkable
  from the test measurements without interpretation.
- Test conditions (temperature, pressure, vibration level, electrical
  supply tolerances, etc.) are specified as nominal values with an
  allowable fractional deviation band. Actual conditions recorded
  during the test must fall within that band; a condition outside the
  band means the test was not executed under the specified environment
  and the results are not attributable to the intended design point.
- Development test types are categorized by their primary stimulus:
  functional, environmental, structural, electrical, thermal, or
  mechanical. A test type outside these categories must be reviewed
  before it enters the test programme.
- A development test report must contain, at minimum: the test
  identifier, the objective references, the recorded actual conditions,
  the measurements, the pass/fail outcome for each measurement, and
  the anomaly record (empty is acceptable; absent is not).

## Workflow

1. Define each test objective: assign a unique identifier, write a
   description of what the test is designed to show, and state the
   success criterion as a checkable bound or observable condition.
   Reject any objective whose success criterion cannot be evaluated
   from the measurements the test will produce.
2. Categorize each test by its primary stimulus type (functional,
   environmental, structural, electrical, thermal, or mechanical).
   Return an error for a type that falls outside the recognized set;
   do not allow uncategorized tests to enter the test programme.
3. Specify test conditions as nominal values with fractional tolerance
   bands. For each condition, record the actual value achieved during
   the test and verify it is within the band. Flag any condition
   outside the band before evaluating measurements; results taken
   outside the specified environment do not confirm compliance with
   the intended design point.
4. Evaluate each measurement against its minimum and maximum
   requirement bounds. A measurement missing from the results is a
   failure; do not treat an absent reading as a pass. Collect all
   failures before determining the overall outcome — do not stop at
   the first failure.
5. Assemble the development test report and verify it contains every
   mandatory element: test identifier, objective references, actual
   conditions, measurements, outcome (pass/fail/inconclusive), and
   anomaly record. Flag any missing element as a reporting gap; an
   incomplete report does not close the test.

## Pitfalls

- Recording the specified (nominal) condition as the actual condition
  in the test report rather than the measured value. The actual
  condition must come from instrumentation during the test run, not
  from the test procedure.
- Treating a missing measurement as implicitly passing because no
  out-of-range value was recorded. An absent measurement means the
  requirement was not checked; that is a failure, not a pass.
- Writing a success criterion that refers only to a design document
  ("meets drawing X") rather than a checkable measured bound. The
  criterion must be evaluable from the test data without consulting
  further documents.
- Omitting the anomaly record from the report because no anomalies
  occurred. The mandatory element is the anomaly record itself; an
  empty record is valid and required.
- Allowing a test condition to drift outside its tolerance band
  mid-test without invalidating the affected measurement window.
  Only measurements taken while all conditions were within their
  bands are attributable to the specified design point.

## Behavior contract (gate 3)

The objective validation, test-condition tolerance check, measurement
evaluation, report completeness check, and test-plan assembly logic
are exercised by the gate 3 contract test:
scripts/test_e1003_dev_tests.py against
scripts/e1003_dev_tests_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_dev_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
