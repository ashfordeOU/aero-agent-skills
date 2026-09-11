---
name: e1003-el-mission
description: "Use when run element mission-specific tests under ECSS-E-ST-10C
  clause 6.5.6: determine the applicable test categories for a given element type
  and mission orbit, validate that the planned test programme covers every required
  category, evaluate individual test results against acceptance limits, and produce
  an aggregated per-element mission-test compliance verdict. Test categories are
  divided into functional, environmental, and performance-verification types. Category
  selection depends on both the mission orbit (LEO, GEO, MEO, HEO, interplanetary)
  and the element type (propulsion, structure, avionics, payload, power). Trigger:
  ecss, e-st-10-system-scope, mission-specific-tests, element-testing, test-programme,
  mission-profile, acceptance-criteria, test-compliance."
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
  tags: [ecss, e-st-10-system-scope, mission-specific-tests, element-testing, test-programme, mission-profile, acceptance-criteria, test-compliance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Element Mission-Specific Tests (space-systems/ecss/e1003-el-mission)

Use when the task is to run element mission-specific tests per
ECSS-E-ST-10C clause 6.5.6 — determining which test categories apply
to an element based on its type and mission orbit, confirming test
programme completeness, evaluating test results against acceptance
limits, and aggregating a compliance verdict before proceeding to the
next programme milestone.

## Domain quick reference

- Clause 6.5.6 requires that every element undergoes a set of
  mission-specific tests whose scope is shaped by two inputs: the
  element's functional type (propulsion, structure, avionics, payload,
  power) and the mission orbit (LEO, GEO, MEO, HEO, interplanetary).
  These two inputs together define the minimum required test categories.
- Test categories fall into three groups: **functional** (verify the
  element performs its intended function under nominal conditions),
  **environmental** (expose the element to the mission environment —
  thermal vacuum, vibration, acoustic, shock, radiation, atomic oxygen,
  EMC/EMI, sterilization), and **performance-verification** (confirm
  measured parameters meet acceptance limits — leak, proof pressure,
  static load, calibration, performance). Each test in the planned
  programme is assigned to exactly one group.
- Test programme completeness is verified by comparing the planned set
  against the required set derived from element type and orbit. Any
  required category absent from the plan is a coverage gap — a finding
  that must be resolved before the programme is closed.
- Each test result is evaluated against a numeric acceptance limit with
  a direction: a maximum limit (measured value must not exceed the
  limit) or a minimum limit (measured value must reach the limit). A
  result that fails its direction check is a failing result. A failing
  result and a coverage gap are both compliance findings; the element
  is not mission-test compliant until both lists are empty.
- The LEO orbit adds atomic oxygen as a required environmental test
  because the residual atmosphere at LEO altitudes erodes exposed
  polymer and metallic surfaces; no other orbit triggers this category.
  Interplanetary missions add sterilization to meet planetary protection
  requirements. MEO and HEO omit acoustic and atomic-oxygen categories
  because the relevant environments are absent or below threshold.

## Workflow

1. Identify the element type and mission orbit from the programme
   master schedule or the product tree. Reject inputs outside the
   defined sets before any analysis proceeds.
2. Derive the required test categories by taking the union of the
   orbit-driven categories and the element-type-driven categories.
   Document the derivation and trace it to the mission profile.
3. Compare the planned test programme against the required category
   set. Flag every required category that has no corresponding planned
   test as a coverage gap. Flag planned tests that are not in the
   required set as advisory extras (not findings, but worth recording).
4. For each test executed, record the measured value, the acceptance
   limit, and the limit direction (max or min). Evaluate pass or fail
   for each result. A result that exactly meets a maximum limit is a
   pass; a result that exactly meets a minimum limit is a pass.
5. Aggregate all findings: coverage gaps and failing results. An element
   is mission-test compliant when both the gap list and the failing-
   result list are empty. Report the compliance verdict with a full list
   of findings so that corrective actions can be tracked individually.
6. Carry the compliance verdict forward to the programme milestone review
   as evidence that mission-specific tests have been completed and that
   the element is ready for integration or delivery.

## Pitfalls

- Deriving the required test set from orbit alone and omitting the
  element-type contribution — propulsion elements require leak and
  proof-pressure tests, avionics require EMC/EMI, payload requires
  calibration; these do not come from the orbit table and will be
  missed if only the orbit is consulted.
- Treating "no planned test" as equivalent to "not required" — a
  category absent from the plan but present in the required set is a
  gap finding, not permission to skip the test.
- Reading a maximum-limit result as passing when the measured value
  exactly equals the limit — equality is a pass for both max and min
  limits; margin analysis is a separate activity.
- Closing the programme after all planned tests pass without checking
  coverage — if the plan itself was incomplete, passing every planned
  test still leaves coverage gaps open.
- Applying LEO-specific categories (atomic oxygen) to GEO or MEO
  elements — the environmental driver does not exist at those orbits and
  the test requirement does not apply.

## Behavior contract (gate 3)

The required-test derivation, coverage validation, result evaluation,
and compliance aggregation logic is exercised by the gate 3 contract
test: scripts/test_e1003_el_mission.py against
scripts/e1003_el_mission_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_el_mission.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
