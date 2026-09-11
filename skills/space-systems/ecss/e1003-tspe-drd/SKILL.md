---
name: e1003-tspe-drd
description: "Use when validate or generate a Test Specification (TSPE) document against the ECSS-E-ST-10C Annex B Data Requirement Document: verify the document carries a test identification block (ID, name, and test-type category), a substantive description of the test objective, a conditions block covering environment, configuration, and stimuli, an ordered procedure list with step numbers and actions, and at least one measurable success criterion with parameter, limit, and measurement unit. Flag each absent or incomplete section as a compliance finding before the review board accepts the document. Trigger: ecss, e-st-10c, tspe, test-specification, drd, test-conditions, success-criteria, annex-b."
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
  tags: [ecss, e-st-10c, tspe, test-specification, drd, test-conditions, success-criteria, annex-b]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Testing — Test Specification DRD (space-systems/ecss/e1003-tspe-drd)

Use when the task is to validate or generate a Test Specification (TSPE)
document so that it satisfies the ECSS-E-ST-10C Annex B Data Requirement
Document — confirming that a test identification block, a clear objective
statement, a complete conditions record, an ordered procedure, and measurable
success criteria are all present before the document reaches a review board.

## Domain quick reference

- Annex B of ECSS-E-ST-10C defines the mandatory content structure for a
  Test Specification document. The DRD is a content contract: every TSPE
  submitted for formal review must satisfy it or be returned.
- A TSPE covers one logical test. Its identification block names the test
  with a unique ID, a human-readable name, and a test-type category
  (functional, performance, qualification, acceptance, proto-flight,
  verification, or environmental). Each test belongs to exactly one
  category; an uncategorized or unknown type is a DRD non-conformance.
- The conditions block records the complete test boundary: the physical
  environment (thermal, vacuum, vibration level), the unit configuration
  (hardware build state, software version, EGSE connected), and the input
  stimuli (commands, electrical signals, injected loads). All three
  sub-fields are mandatory — a conditions block missing any one of them
  cannot reproduce the test.
- Success criteria must be expressed as measurable thresholds, each
  carrying a parameter name, a numeric limit, and a measurement unit.
  A criterion without a unit or limit is unverifiable and must be flagged
  as an error, not a warning.
- The procedure is an ordered list of steps. Each step carries a step
  number and an action description. An empty procedure or a step with no
  action makes the test non-reproducible.

## Workflow

1. Check that the TSPE document contains every top-level DRD key:
   test_id, test_name, test_type, description, conditions, procedure,
   and success_criteria. Report any missing key as a structural error
   before inspecting sub-fields.
2. Validate the identification block: confirm test_id and test_name are
   non-empty strings, and that test_type matches one of the seven
   recognized ECSS-E-ST-10C test categories. Reject an unrecognized
   test-type string with an error.
3. Check the description field contains a substantive objective statement
   (at minimum ten words). An empty description is an error; a very short
   one is a warning that the objective is likely underspecified.
4. Validate the conditions block: confirm all three sub-fields —
   environment, configuration, and stimuli — are present and non-empty.
   Each absent sub-field is a separate error.
5. Validate the procedure: confirm the procedure is a non-empty list of
   step mappings, each containing step_number and action. A missing action
   or missing step_number is an error.
6. Validate every success criterion: each must carry parameter, limit, and
   unit. A criterion missing any of these three fields is an error because
   the pass/fail condition cannot be objectively evaluated.
7. Aggregate all errors and warnings into a DRD compliance report. The
   document is DRD-compliant only when the error list is empty. Warnings
   do not block compliance but must be recorded for the review board.

## Pitfalls

- Accepting a test type that is not in the ECSS-E-ST-10C vocabulary as
  though it were valid. An unrecognized test type means the document
  cannot be linked to the correct verification method and flow-down
  requirement, which is a DRD non-conformance.
- Treating a conditions block as complete because it exists as a key in
  the document, without inspecting its sub-fields. A conditions dict that
  is present but missing stimuli or environment is as incomplete as a
  conditions block that is absent entirely.
- Reading a success criterion as acceptable because it has a parameter
  name and a limit, without checking that a measurement unit is also
  present. A limit value without a unit is dimensionally ambiguous and
  cannot be independently verified.
- Allowing the procedure to be a single-step list when the test clearly
  requires multiple distinct actions. The DRD does not set a minimum step
  count, but a one-step procedure for a multi-phase test is a warning
  that the procedure has been underspecified.

## Behavior contract (gate 3)

The identification, description, conditions, procedure, and success-criteria
validation logic is exercised by the gate 3 contract test:
scripts/test_e1003_tspe_drd.py against scripts/e1003_tspe_drd_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1003_tspe_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
