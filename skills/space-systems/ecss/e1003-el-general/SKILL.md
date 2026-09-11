---
name: e1003-el-general
description: "Use when verify general element test requirements under ECSS-E-ST-10C §6.1: order the test campaign by ascending scope (unit, integration, element), confirm that every declared interface is exercised by at least one passing test, check that all element-level functions are covered by the campaign, and flag missing required test levels before formal acceptance. Trace each test result to its driving requirement and control the test configuration throughout. Trigger: ecss, e-st-10-system-scope, element-testing, test-sequence, interface-verification, functional-check, test-campaign, test-compliance."
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
  tags: [ecss, e-st-10-system-scope, element-testing, test-sequence, interface-verification, functional-check, test-compliance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Element-Level General Test Requirements (space-systems/ecss/e1003-el-general)

Use when the task is applying the general element test requirements of
ECSS-E-ST-10C §6.1 — establishing and verifying the element test
sequence, checking interface coverage, and confirming element-level
functional checks are fully exercised before formal acceptance.

## Domain quick reference

- §6.1 requires that the element test campaign proceed in ascending
  scope order: unit-level tests (individual component) are performed
  before integration-level tests (assemblies and sub-systems), which
  are performed before element-boundary tests (the element as a whole
  interfacing with its neighbours). System-level tests sit above
  element scope and do not substitute for missing element-level tests.
  Any reversal of this order — an element-boundary test conducted
  before its underpinning unit and integration tests are complete —
  is a sequence violation.
- Every interface declared at the element boundary must be exercised by
  at least one passing test before acceptance. An interface that is
  verified only by a test with status "pending", "fail", or "not_run"
  is not considered covered; the interface is carried forward as an
  open finding.
- Every element-level function allocated to the element must be
  exercised by at least one passing test. A function covered only by
  a failing test is not covered; it must appear in the open-findings
  list.
- The minimum required level set for a §6.1-compliant campaign is unit,
  integration, and element. Absence of any of these levels — even if
  other levels pass — is a non-compliance finding.
- Test configuration is controlled: the version of the test item, test
  software, test equipment, and environmental conditions used for each
  test must be recorded and traceable to the test result.

## Workflow

1. Collect all test records for the element and assign a sequence
   position to each test that has been executed or scheduled. Records
   without a position are treated as unordered and excluded from
   sequence checking but still contribute to coverage if they pass.
2. Validate the test sequence: sort records by sequence position and
   confirm that no test at a higher scope (integration, element,
   system) precedes all tests at the next lower scope. Flag every
   out-of-order pair as a sequence violation.
3. Check interface coverage: for each declared interface, confirm at
   least one test record with status "pass" lists that interface.
   Produce a list of uncovered interfaces.
4. Check functional coverage: for each element-level function, confirm
   at least one passing test record lists that function. Produce a
   list of uncovered functions.
5. Check required level presence: confirm the campaign contains at
   least one passing test at each of the three required scopes (unit,
   integration, element). List any scope that is absent.
6. Aggregate the four finding lists (sequence violations, uncovered
   interfaces, uncovered functions, missing levels). The element test
   campaign is §6.1-compliant only when all four lists are empty.

## Pitfalls

- Treating a failing or pending test as coverage — only a test with
  status "pass" counts toward interface and functional coverage. A
  test that runs but fails leaves its target interface and function
  open.
- Relying on system-level tests to satisfy element-level interface
  requirements — §6.1 requires coverage at element scope; system tests
  are above-element scope and do not substitute.
- Skipping sequence validation on the grounds that all tests
  eventually passed — a sequence inversion may mask a dependency not
  yet exercised in the correct order; the inversion itself is a
  finding regardless of individual test outcomes.
- Carrying an element campaign without a unit-level subset — unit
  tests are not optional; their absence is a missing-level finding
  even if integration and element tests are complete.
- Omitting test configuration traceability — an untraceable test
  result cannot be accepted as evidence of compliance regardless of
  the pass/fail verdict.

## Behavior contract (gate 3)

The sequence-validation, interface-coverage, functional-coverage, and
required-level-presence logic is exercised by the gate 3 contract
test: scripts/test_e1003_el_general.py against
scripts/e1003_el_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_el_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
