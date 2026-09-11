---
name: e1003-test-conditions
description: "Use when define test conditions for a space equipment or system verification campaign under ECSS-E-ST-10C §4.4.1: establish the required ambient environment parameter ranges (temperature, pressure, humidity, EMI environment), the cleanliness class for each test area, the ESD protection measures required for each test item, the unit-under-test configuration state and interface definitions, and the monitoring channel set with recording rates and acceptance limits. Each condition input is categorized as compliant or non-compliant; undefined mandatory conditions are flagged; and monitoring coverage is confirmed before test execution is permitted. Trigger: ecss, e-st-10-system-scope, test-conditions, ambient-environment, esd-protection, cleanliness, test-configuration, monitoring."
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
  tags: [ecss, e-st-10-system-scope, test-conditions, ambient-environment, esd-protection, cleanliness, test-configuration, monitoring]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Engineering — Test Conditions Definition (space-systems/ecss/e1003-test-conditions)

Use when the task is to define and validate test conditions prior to a
verification test under ECSS-E-ST-10C §4.4.1 -- establishing the
ambient environment, cleanliness, ESD protection, configuration state,
and monitoring requirements so that the test can proceed in a
controlled, reproducible manner.

## Domain quick reference

- §4.4.1 groups test conditions into five categories that must all be
  defined before any test activity starts: ambient environment
  (temperature, pressure, humidity, EMI background), cleanliness (ISO
  14644-1 class for each test area), ESD protection (wrist strap, mat,
  and area signage for every item sensitive to electrostatic discharge),
  unit-under-test configuration (configuration state ID, interface
  definitions, software baseline), and monitoring (channel list with
  recording rate and acceptance limits for each measured parameter).
- Each ambient environment parameter carries a low limit and a high
  limit; a measured value outside that band makes the condition
  non-compliant and the test cannot begin until the environment is
  restored or the limit is waived.
- Cleanliness class is expressed as an ISO 14644-1 level (ISO1 through
  ISO9, lower number is stricter); the actual class of the test area
  must be equal to or stricter than the required class for the test
  item.
- ESD controls are a set of required measures -- wrist strap, grounded
  mat, and area signage at minimum; any missing control on an ESD-
  sensitive item is a finding that must be resolved before handling.
- Configuration completeness requires that every required configuration
  field (software build ID, hardware configuration state, interface
  connector state, GSE connection list) is documented in the test
  configuration record before the test.
- Monitoring coverage requires that every parameter listed as a
  required channel has a defined recording rate greater than zero and a
  set of acceptance limits; a channel with a zero rate or undefined
  limits is flagged.

## Workflow

1. Enumerate every ambient environment parameter required by the test
   procedure (temperature, pressure, humidity, EMI floor, etc.) and
   assign a low and high limit to each. Verify that each measured value
   is within its assigned band; flag any out-of-range parameter.
2. For each test area, identify the required ISO cleanliness class from
   the test procedure or equipment handling specification. Verify that
   the area's actual class (from the most recent ISO 14644-1 survey or
   continuous particle monitoring) meets or exceeds the required class;
   flag any area whose actual class is less strict than required.
3. For each test item that is sensitive to ESD damage, confirm that the
   required controls are in place: grounded wrist strap on all
   personnel, grounded ESD mat under the item, and ESD-area signage at
   all entry points. Flag any missing control; items not sensitive to
   ESD require no check.
4. Confirm the test configuration record is complete: every field
   required by the test procedure is documented (software build
   identifier, hardware configuration state, interface connector
   allocation, GSE connection list, and any other required fields).
   Flag any required field that is absent.
5. Review the monitoring channel list: every parameter listed as a
   required channel must have a defined recording rate greater than
   zero and a set of acceptance limits. Flag channels with a zero
   recording rate or undefined limits, and flag any required channel
   that is missing from the defined set entirely.
6. Aggregate all findings across the five categories; the test may
   proceed only when the findings list is empty or every outstanding
   finding has been formally waived. Record the condition status in the
   test readiness record before giving proceed authority.

## Pitfalls

- Treating an untested or assumed ambient environment as compliant --
  every parameter must have a measured value compared against its
  defined limit at the time of test, not a prior recording from a
  different run.
- Using a cleanliness class survey result that predates the most recent
  disruption (construction, personnel ingress, hardware movement) to
  the test area -- the survey must be current; a stale survey is not a
  compliant check.
- Omitting ESD checks for items that have no explicit ESD sensitivity
  callout in their datasheet when the item contains ESD-sensitive
  components documented elsewhere in the design -- check against the
  component-level sensitivity data, not only the assembly-level label.
- Treating a configuration record with one or more blank required
  fields as complete -- any blank field means the configuration state
  cannot be unambiguously reconstructed after the test, which
  invalidates traceability.
- Defining monitoring channels without acceptance limits on the grounds
  that the channel is "informational" -- a channel with no limits
  cannot support a pass/fail determination; either assign limits or
  remove the channel from the required set.

## Behavior contract (gate 3)

The environment categorization, cleanliness comparison, ESD control
verification, configuration completeness check, and monitoring coverage
logic are exercised by the gate 3 contract test:
scripts/test_e1003_test_conditions.py against
scripts/e1003_test_conditions_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_test_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
