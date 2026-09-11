---
name: e1003-pre-launch
description: "Use when running pre-launch health checks, leak verification, functional tests, and campaign constraint checks at the launch site under ECSS-E-ST-10C §7: categorize each health check as structural, electrical, thermal, propulsion, software, or mechanical; compare measured leak rates against the allowable limit for each pressurized system; evaluate functional test outcomes for critical and non-critical subsystems; and verify every launch campaign environmental and temporal constraint is within its bounds before declaring launch readiness. Trigger: ecss, e-st-10-system-scope, pre-launch, launch-site, health-check, leak-verification, functional-test, launch-campaign, launch-readiness."
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
  tags: [ecss, e-st-10-system-scope, pre-launch, launch-site, health-check, leak-verification, functional-test, launch-campaign, launch-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Testing — Pre-Launch Testing (space-systems/ecss/e1003-pre-launch)

Use when the task is the pre-launch testing campaign at the launch site
under ECSS-E-ST-10C §7 — verifying spacecraft health after transport and
integration, confirming pressurized-system leak integrity, evaluating
subsystem functional readiness, and checking all launch campaign
environmental and temporal constraints before authorizing launch.

## Domain quick reference

- §7 pre-launch testing is conducted at the launch site after spacecraft
  transport and integration with the launch vehicle. Its purpose is to
  confirm that no damage was introduced during transport, that all
  pressurized systems are leak-tight within their allowable limits, that
  all critical and non-critical subsystems operate within specification,
  and that the launch campaign environment (temperature, humidity, battery
  charge duration, shelf life, cleanliness) has not drifted outside its
  approved window.
- Health checks cover six categories: structural (mechanical integrity
  after transport), electrical (harness continuity, bonding, and isolation),
  thermal (heater and thermistor continuity), propulsion (valve and line
  integrity pre-pressurization), software (boot, memory, and command-
  execution verification), and mechanical (mechanism deployment and latch
  checks). Each check records a result of pass, fail, or marginal; a fail
  is a launch hold, and a marginal triggers a disposition review before the
  campaign can advance.
- Leak checks are performed on every pressurized system: propulsion tanks
  and lines, pressurized vessels, pneumatic lines, and thruster valves.
  Each check compares the measured steady-state leak rate (sccm) against the
  system's allowable limit; any exceedance is a launch hold regardless of
  margin.
- Functional tests confirm that each subsystem responds correctly to
  launch-configuration commands. A failed critical subsystem test is a
  launch hold; a failed non-critical test is an advisory finding that must
  be formally dispositioned before the launch commit review but does not
  automatically suspend the campaign.
- Campaign constraints are environmental and temporal bounds that must
  remain satisfied throughout the launch campaign window: temperature in °C,
  relative humidity in percent, battery charge duration in hours, shelf life
  of pyrotechnic devices and propellant in days, and storage cleanliness
  level (numeric class). A single out-of-bounds constraint suspends campaign
  advancement until corrective action restores the parameter within bounds.

## Workflow

1. At the start of pre-launch operations, categorize each planned check as
   structural, electrical, thermal, propulsion, software, or mechanical.
   Reject any check category not in the approved set before it enters the
   health-check log.
2. Record the result (pass, fail, marginal) for each health check and
   evaluate it: a fail is an immediate launch hold, a marginal enters the
   advisory queue for disposition, a pass requires no further action. Reject
   an unrecognized result before it is logged.
3. For each pressurized system, record the measured steady-state leak rate
   (sccm) and its system-specific allowable limit (sccm). Compare the
   measured rate against the limit: any exceedance is a launch hold. Negative
   rates or allowable limits are input-validation errors.
4. For each subsystem functional test, record whether the test passed and
   whether the subsystem is critical. A failed critical test is a launch
   hold; a failed non-critical test is an advisory finding. A passed test,
   critical or not, produces no finding.
5. For each campaign constraint, record the constraint type, the measured
   value, and the approved lower and upper bounds. Evaluate: a value below
   the lower bound or above the upper bound is an out-of-bounds finding.
   An unrecognized constraint type is an input-validation error.
6. Aggregate all findings across health checks, leak checks, functional
   tests, and campaign constraints. The system is not launch-ready until
   every category has an empty finding list.

## Pitfalls

- Treating a marginal health-check result as a pass — a marginal result
  requires an explicit engineering disposition before the campaign can
  advance; it is not a green status.
- Skipping the allowable-limit comparison for a pressurized system because
  the measured leak rate appears low — the comparison must be performed and
  documented for every system regardless of the apparent margin.
- Allowing a failed non-critical functional test to carry forward without
  disposition — while it does not automatically hold the launch, it must
  be formally dispositioned (waived, retested, or corrected) before the
  launch commit review.
- Treating a campaign constraint that returned within bounds after a brief
  exceedance as if no exceedance occurred — the exceedance must be
  documented and evaluated for any impact on system life or reliability.

## Behavior contract (gate 3)

The health-check categorization, leak-rate comparison, functional-test
evaluation, and campaign-constraint bound-check logic is exercised by the
gate 3 contract test: scripts/test_e1003_pre_launch.py against
scripts/e1003_pre_launch_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_pre_launch.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
