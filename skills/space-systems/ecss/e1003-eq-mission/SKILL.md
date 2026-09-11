---
name: e1003-eq-mission
description: "Use when execute equipment mission-specific test verification under
  ECSS-E-ST-10-03C §5.5.6: categorize each test by mission-environment type (acoustic
  sound pressure, dynamic vibration, electromagnetic compatibility, thermal environment,
  or functional performance), validate measured values against acceptance or qualification
  limits, compute test margins, verify all required mission-specific test types are
  present in the campaign, and confirm each result meets its pass criterion. Covers
  airborne sound pressure measurement per §5.5.6.1 and other mission-environment
  verification steps. Trigger: ecss, e-st-10-system-scope, e-st-10-03c,
  equipment-testing, mission-specific-tests, sound-pressure, vibration, emc."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-03c, equipment-testing, mission-specific-tests, sound-pressure, vibration, emc]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment Mission-Specific Tests (space-systems/ecss/e1003-eq-mission)

Use when the task is executing the mission-specific portion of the equipment
test campaign under ECSS-E-ST-10-03C §5.5.6 — running tests that are unique
to the equipment's actual mission environment and function (airborne sound
pressure, dynamic vibration, electromagnetic compatibility, thermal environment,
or functional performance in mission configuration) and verifying each result
against acceptance or qualification limits.

## Domain quick reference

- §5.5.6 requires that equipment undergoing environmental testing address
  any test whose pass/fail criterion is tied directly to the mission it will
  perform, beyond the general environmental sequence. Each such test is tied
  to a specific mission scenario or performance requirement.
- §5.5.6.1 covers airborne sound pressure measurement: the equipment is
  exposed to an acoustic pressure field representative of its launch or
  operational environment, and the overall sound pressure level (SPL)
  measured on or near the equipment must remain at or below the limit defined
  in the test specification.
- Every mission-specific test is categorized into exactly one type:
  acoustic (SPL measurement), vibration (structural dynamic response),
  emc (electromagnetic compatibility in mission configuration), thermal
  (thermal environment representative of on-orbit or re-entry conditions),
  or functional (performance verification under mission loads). An unrecognized
  test type is rejected before it enters the evaluation.
- Test levels are either acceptance (lower stress, production flight hardware)
  or qualification (higher stress, margin demonstration). The limit value
  used in each evaluation must match the level specified in the test procedure.
- A margin is computed for every test: positive means the measurement sits
  below the limit (pass), negative means an exceedance (fail). A zero margin
  is a pass at the exact limit.
- Campaign completeness is verified separately: all test types required by
  the equipment's test specification must appear in the submitted campaign
  before the equipment can be declared mission-test complete.

## Workflow

1. Collect the list of mission-specific tests required for this equipment
   from the test specification (derived from §5.5.6 and the equipment's
   mission requirements document).
2. For each test record, validate that the required fields are present
   (test ID, test type, test level, measured value, limit value) and that
   the test type is one of the recognized mission-specific types. Reject
   any record with missing fields or an unrecognized type before processing.
3. For acoustic tests (§5.5.6.1), compare the measured overall SPL (dB)
   against the SPL limit from the test specification. Record the margin
   (limit minus measured) and mark the test as pass (margin ≥ 0) or
   fail (margin < 0).
4. For all other mission-specific test types, apply the same margin logic:
   compute margin = limit − measured (for tests where a higher value is
   worse) or measured − limit (where a lower value is worse), then pass
   or fail accordingly.
5. Check campaign completeness: confirm that every test type required by
   the specification appears at least once in the submitted records.
   Record any missing types as a completeness gap.
6. Compile a campaign summary: total records, passed, failed, records with
   validation errors, overall campaign status (pass only when all records
   pass and no errors exist), and the completeness gap list.

## Pitfalls

- Mixing acceptance and qualification limits: each evaluation must use the
  limit that matches the stated test level. Applying a qualification limit
  to an acceptance-level test artificially tightens the criterion and may
  cause spurious failures.
- Skipping the test-type validation step: an unrecognized test type silently
  bypasses the evaluation unless it is explicitly rejected, creating a gap
  in the campaign record.
- Reading a zero margin (measured equals limit exactly) as a borderline
  concern: at the limit is a pass per ECSS convention; only a negative
  margin is an exceedance.
- Declaring campaign completeness based on count alone: a campaign with the
  right number of records but missing an entire test type (e.g., no acoustic
  test at all) is incomplete regardless of record count.
- Conflating "no test record submitted" with "test not required": the
  completeness check must be driven by the specification's required-type
  list, not inferred from the submitted records.

## Behavior contract (gate 3)

Mission-specific test categorization, limit comparison, margin computation,
campaign completeness, and sound pressure evaluation are exercised by the
gate 3 contract test: scripts/test_e1003_eq_mission.py against
scripts/e1003_eq_mission_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_mission.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor clause: ECSS-E-ST-10-03C §5.5.6 (equipment mission-specific tests),
  §5.5.6.1 (airborne sound pressure measurement).
