---
name: e1003-test-programme
description: "Use when define the overall test programme for a space system or subsystem under ECSS-E-ST-10C §4.1: identify each hardware model entering the programme (BB, EM, QM, EQM, PFM, FM), derive its corresponding test level (development, qualification, proto-flight, or acceptance), build and validate the ordered test sequence for each model ensuring positions are unique and consecutive, verify that functional tests bookend the sequence at position 1 and the final position, confirm all required programme-level documents are on record before scheduling begins, and validate that the required verification inputs for each test activity are supplied. Trigger: ecss, e-st-10-system-scope, test-programme, models-under-test, test-sequence, verification-inputs, programme-documentation, qualification, acceptance."
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
  tags: [ecss, e-st-10-system-scope, test-programme, models-under-test, test-sequence, verification-inputs, programme-documentation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Test Programme Definition (space-systems/ecss/e1003-test-programme)

Use when the task is to define the test programme for a space system or
subsystem under ECSS-E-ST-10C §4.1: establishing which hardware models
participate, which test level each model is subject to, what ordered test
sequence each model follows, which programme-level documents must be on
record before testing begins, and which verification inputs must be
supplied before each test activity can be scheduled.

## Domain quick reference

- §4.1 distinguishes hardware models by their role in the programme.
  Bread Board (BB) and Engineering Model (EM) are used for development
  verification and are subject to development test levels. Qualification
  Model (QM) and Engineering Qualification Model (EQM) are tested at
  qualification levels to demonstrate design margin. Proto-Flight Model
  (PFM) is tested to qualification levels but is then retained as the
  flight unit rather than being consumed in the programme.  Flight Model
  (FM) is tested to acceptance levels only. Each model type maps to
  exactly one test level — development, qualification, proto-flight, or
  acceptance — and that mapping must be established before any test
  activity is assigned to the model.
- The test sequence for a given model is an ordered list of test
  activities assigned unique consecutive position numbers starting from
  1. A functional test at position 1 provides the performance baseline
  before any environment is applied. A functional test at the final
  position confirms the unit survived the preceding environments without
  degradation. Any gap or duplication in position numbering is a
  programme fault, not a scheduling preference, and must be resolved
  before the sequence is accepted.
- Four programme-level documents must be on record before any test
  activity is scheduled: the test plan, test procedures, verification
  control document, and test reports template. A missing document is a
  programme finding that blocks test scheduling.
- Each test activity type requires specific verification inputs to be
  supplied in advance (for example, a vibration-random activity requires
  a loads environment and qualification levels; a thermal-vacuum activity
  also requires a thermal model). An activity missing any of its
  required inputs is an open finding and must not be scheduled until
  those inputs are resolved.

## Workflow

1. Collect every hardware item entering the test programme and assign
   each one a model type from the recognised set: BB, EM, QM, EQM, PFM,
   FM. Reject any type that is not in that set — an unrecognised type
   signals a programme documentation error upstream.
2. For each model, derive its test level from the model type using the
   fixed mapping (BB/EM → development; QM/EQM → qualification; PFM →
   proto-flight; FM → acceptance). Record this level before assigning
   any test activities, because the level governs the environment
   magnitudes and margin factors for all subsequent activities.
3. For each model, build the ordered test sequence: list every planned
   test activity with a unique, consecutive position starting from 1.
   Validate that each test type is from the recognised set, that all
   positions are unique and consecutive, and that every activity
   references the correct model identifier.
4. Check the functional bookend: confirm the first activity in the
   sequence (position 1) is a functional test and the last activity is
   also a functional test. Both conditions must hold; a missing bookend
   is a sequence fault.
5. Confirm that all programme-level documents are on record: test plan,
   test procedures, verification control document, test reports. Record
   each missing document as a programme finding and do not proceed to
   scheduling until it is resolved.
6. For each test activity across all model sequences, check that the
   activity's required verification inputs are supplied. Record each
   missing input as a verification input gap.
7. Aggregate all findings (model type errors, sequence faults, bookend
   faults, missing documents, input gaps) into a programme summary. The
   programme is valid only when the findings list is empty.

## Pitfalls

- Treating a PFM as equivalent to a QM — PFM maps to the proto-flight
  test level, not qualification, because the hardware is not consumed in
  the programme. Misassigning the level changes the applicable margins
  and the disposition of the unit after testing.
- Allowing non-consecutive or duplicate sequence positions — a gap
  means an activity was silently omitted; a duplicate means two
  activities were merged without programme documentation to record the
  decision.
- Starting test scheduling before all programme documents are confirmed
  — a test plan that is signed off after testing has begun cannot
  govern that testing retroactively.
- Treating "inputs will be supplied later" as a schedule risk rather
  than a programme finding — a test activity with missing inputs is an
  open finding that blocks that activity from being scheduled.
- Omitting the functional bookend check because environmental tests look
  complete — without a post-environmental functional test there is no
  objective evidence that the unit survived the applied environments.

## Behavior contract (gate 3)

The model categorization, sequence validation, functional bookend check,
programme documentation check, and verification input check logic is
exercised by the gate 3 contract test:
scripts/test_e1003_test_programme.py against
scripts/e1003_test_programme_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_test_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
