---
name: e1003-el-thermal
description: "Use when run and validate element-level thermal tests per ECSS-E-ST-10C §6.5.4: thermal vacuum cycling, thermal balance correlation, mission-pressure thermal cases, and Space-Station-specific thermal conditions for a spacecraft element. Checks each test case for conformance with temperature setpoint, soak duration, cycle count, chamber pressure, and margin requirements. Verifies thermal model correlation against balance measurements and confirms the mandatory thermal test campaign is complete before closure. Trigger: ecss, e-st-10c, thermal-vacuum, thermal-balance, tvac, tbal, mission-pressure, iss-thermal, element-thermal-test."
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
  tags: [ecss, e-st-10-system-scope, thermal-vacuum, thermal-balance, mission-pressure, iss-thermal, element-thermal-test, tvac]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS AIT — Element Thermal Tests (space-systems/ecss/e1003-el-thermal)

Use when the task is to plan, execute, and close out element-level thermal
tests required by ECSS-E-ST-10C §6.5.4 — covering thermal vacuum cycling,
thermal balance model correlation, mission-pressure thermal cases, and
Space-Station-specific thermal environment conditions.

## Domain quick reference

- §6.5.4 mandates four categories of element thermal test: (1) thermal
  vacuum, which cycles the element between hot and cold temperature
  extremes inside an evacuated chamber; (2) thermal balance, which
  compares measured node temperatures against thermal model predictions
  to establish model correlation; (3) mission-pressure thermal, applied
  when the element operates in a pressurized environment (e.g., a
  pressurized module instrument); and (4) Space-Station-specific cases,
  which use the ISS external thermal environment bounds as the design
  envelope rather than free-flight limits.
- Qualification and protoflight test levels require larger temperature
  margins above and below the design limits than acceptance tests do, and
  a higher minimum cycle count. Acceptance tests use reduced margins and
  may use fewer cycles, but the chamber pressure and soak duration
  minimums apply at all levels.
- Thermal balance correlation is judged against a maximum allowed
  deviation between any measured node temperature and the corresponding
  model-predicted value. A correlation deviation that exceeds the
  threshold is a test finding that must be resolved before the thermal
  model is accepted for use in subsequent analyses.
- For mission-pressure tests, the chamber pressure must fall within the
  band representing the mission environment; a test run at too low or too
  high a pressure does not adequately represent the convective heat
  transfer regime the hardware will experience.
- ISS-specific cases add an envelope check: the test hot and cold
  setpoints must at minimum bracket the ISS external worst-case
  temperatures. The same chamber vacuum, soak, cycle, and margin rules
  that govern standard thermal vacuum tests also apply.

## Workflow

1. Inventory the thermal test requirements for the element and identify
   which of the four test categories apply (thermal vacuum, thermal
   balance, mission-pressure, ISS-specific). An element that operates in
   a pressurized environment requires a mission-pressure case; an element
   for an ISS-attached payload requires the ISS-specific case; thermal
   vacuum and thermal balance are mandatory for every element-level
   thermal test campaign.
2. For each thermal vacuum or ISS-specific case, confirm the hot and cold
   temperature setpoints provide the required margin above the design hot
   limit and below the design cold limit for the applicable test level
   (qualification/protoflight margin is larger than acceptance margin).
   Flag any setpoint that does not meet its margin requirement before
   authorizing test.
3. Verify the test campaign parameters against the minimum soak duration
   (hours at hot and cold set temperatures), minimum cycle count for the
   test level, and maximum allowable chamber pressure. A chamber
   operating above the vacuum threshold is a thermal-cycle test at
   pressure, not a thermal vacuum test; reject it.
4. During or after thermal balance testing, compare each measured node
   temperature against the corresponding thermal model prediction. Flag
   every node where the absolute deviation exceeds the allowed threshold.
   Do not accept the thermal model for subsequent analysis use until all
   flagged nodes are resolved by model update, measurement recheck, or
   documented justification.
5. For mission-pressure cases, verify the test chamber is set to a
   pressure within the mission-representative band. Check hot and cold
   setpoints and margins as in step 2. Reject a test pressure that is
   outside the mission-representative range.
6. Confirm the test campaign is complete: both thermal vacuum and thermal
   balance cases must be present. If either is absent, the thermal test
   campaign is incomplete regardless of how many other cases were run.
7. Assemble the element thermal test report: test parameters, findings,
   correlation status, and any open items. An element with open thermal
   test findings is not thermally qualified until those items are closed.

## Pitfalls

- Using the design limit temperature as the test setpoint — the test must
  exceed the design limit by the required margin, not merely reach it.
  Testing at the limit provides zero margin and does not demonstrate
  positive thermal design margin.
- Counting a test run at ambient pressure as a thermal vacuum cycle — only
  cycles performed below the chamber pressure threshold count toward the
  minimum thermal vacuum cycle requirement.
- Accepting a thermal balance with unresolved high-deviation nodes on the
  grounds that the overall average deviation is acceptable — clause §6.5.4
  correlation is a per-node check; averaging across nodes can hide a
  locally wrong model region that will cause errors in subsequent analysis.
- Skipping the thermal balance and declaring the thermal model correlated
  based on heritage from a previous campaign with different hardware
  configuration — a materially different configuration requires a new
  balance test against that configuration.
- Omitting the ISS-specific case for an ISS-attached element and relying
  on a generic free-flight thermal vacuum result — the ISS external
  environment is bounded by ISS operational constraints that differ from
  free-flight orbital extremes, and the specific limits must be verified.

## Behavior contract (gate 3)

The test-categorization, TVac parameter validation, thermal balance
correlation check, mission-pressure validation, ISS-specific validation,
and campaign completeness logic are exercised by the gate 3 contract test:
scripts/test_e1003_el_thermal.py against
scripts/e1003_el_thermal_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_el_thermal.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
