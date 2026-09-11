---
name: e1003-el-general-tests
description: "Use when run element-level general tests per ECSS-E-ST-10-03C §6.5.1 to verify that all mechanical functions and electrical performance parameters of a space element meet their acceptance requirements: categorize each test item as mechanical-functional (deployment, retraction, separation, latch-release) or electrical-functional (continuity, insulation resistance, bonding); evaluate each measured parameter against its lower and upper acceptance limits; flag any pre-test or post-test inspection failure before accepting results; and confirm the complete set of required test items has been performed before releasing the element for integration. Trigger: ecss, e-st-10-system-scope, e1003, element-general-tests, mechanical-functional, electrical-functional, deployment-test, insulation-resistance, element-acceptance."
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
  tags: [ecss, e-st-10-system-scope, e1003, element-general-tests, mechanical-functional, electrical-functional, deployment-test, insulation-resistance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Element General Tests (space-systems/ecss/e1003-el-general-tests)

Use when the task is running element-level general tests under
ECSS-E-ST-10-03C §6.5.1: executing mechanical functional tests
(§6.5.1.2) and electrical functional tests to verify that all
mechanical functions and electrical performance parameters satisfy
acceptance requirements before the element advances to integration.

## Domain quick reference

- ECSS-E-ST-10-03C §6.5.1 splits element-level general tests into
  two families: mechanical-functional tests and electrical-functional
  tests. Each test item belongs to exactly one family.
- Mechanical-functional tests (§6.5.1.2) verify that every mechanical
  function of the element operates correctly -- deployments, retractions,
  separations, and latch-releases are typical examples. Each test
  measures a parameter (force, torque, displacement, cycle count) and
  evaluates it against a lower and an upper acceptance limit.
- Electrical-functional tests verify electrical performance of the
  element harness and interfaces: continuity checks confirm a conducting
  path meets its maximum resistance budget; insulation-resistance checks
  confirm that galvanically isolated circuits maintain separation above
  a minimum resistance threshold; bonding checks confirm that
  structural-ground paths meet their upper resistance limit.
- Every test item requires a pre-test inspection (physical check of
  the item and test setup before applying stimulus) and a post-test
  inspection (check for damage or anomaly after the stimulus). A
  pre-test inspection failure halts the individual test before any
  measurement is taken; a post-test inspection failure invalidates the
  result even if the measured value was within limits.
- The element may not be released for integration until every required
  test item has been performed and every item verdict is a pass.

## Workflow

1. For each test item in the element test plan, record: its unique test
   identifier, its test type (mechanical-functional or
   electrical-functional), the outcome of the pre-test inspection, the
   measured value, the lower acceptance limit, the upper acceptance
   limit, and the outcome of the post-test inspection.
2. Categorize each test item -- reject any item whose test type is not
   one of the two recognized families before it enters evaluation.
3. Evaluate the pre-test inspection: if it did not pass, assign verdict
   "pre_inspection_fail" and do not proceed to the measurement
   comparison for that item.
4. Evaluate the measured value against the acceptance limits: if the
   value is below the lower limit or above the upper limit, assign
   verdict "out_of_limits".
5. Evaluate the post-test inspection: if it did not pass, assign verdict
   "post_inspection_fail" even when the measurement was within limits.
6. Assign verdict "pass" only when the pre-test inspection passed, the
   measured value is within both limits (inclusive), and the post-test
   inspection passed.
7. Confirm that every required test item identifier has a result entry;
   flag any required item that has no result as "not_performed".
8. Determine element release readiness: the element may proceed to
   integration only when no required item is missing and every item
   verdict is a pass.

## Pitfalls

- Accepting a measurement that is within limits while the post-test
  inspection found damage -- a failed post-test inspection is a
  standalone finding that invalidates the result regardless of the
  numeric outcome.
- Skipping the pre-test inspection and proceeding directly to stimulus
  application -- an anomaly present before the test cannot be
  attributed to the test itself without this reference check.
- Treating a missing required test item as a pass because no failure
  was recorded -- a test that was never performed is neither a pass nor
  a fail; it is an open item that must be dispositioned before release.
- Applying a mechanical-functional acceptance limit (e.g. a force band)
  to an electrical-functional parameter or vice versa -- the limit
  values are type-specific and mixing them produces an undefined
  comparison.

## Behavior contract (gate 3)

The test-type categorization, measurement limit evaluation,
inspection gating, and element release readiness logic is exercised
by the gate 3 contract test:
scripts/test_e1003_el_general_tests.py against
scripts/e1003_el_general_tests_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_el_general_tests.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
