---
name: e1003-el-acceptance
description: "Use when determine the acceptance test baseline for a space hardware
  element under ECSS-E-ST-10C §6.3 and Tables 6-3/6-4: identify which test types
  are mandatory for the element category, derive acceptance levels from qualification
  levels by applying the prescribed margin factors (vibration random −3 dB, thermal
  range narrowed by the acceptance margin), confirm each test duration meets the
  category minimum, and verify the complete proposed test plan contains no missing
  required tests before acceptance test review is convened. Trigger: ecss,
  e-st-10c, element-acceptance, acceptance-test, test-baseline, acceptance-levels,
  test-duration, vibration-acceptance, thermal-acceptance, acceptance-margin."
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
  tags: [ecss, e-st-10-system-scope, element-acceptance, acceptance-test, test-baseline, acceptance-levels, test-duration, acceptance-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Systems — Element Acceptance Test Baseline (space-systems/ecss/e1003-el-acceptance)

Use when the task is to determine the acceptance test baseline for a flight
hardware element under ECSS-E-ST-10C §6.3, Tables 6-3/6-4 -- deriving
acceptance test levels from qualification levels, mapping mandatory test types
to the element category, and verifying that every proposed test duration meets
the specified minimum before the acceptance test review is convened.

## Domain quick reference

- ECSS-E-ST-10C §6.3 distinguishes three element categories that govern which
  tests are mandatory (Table 6-4, paraphrased): **simple** elements require
  visual inspection and functional tests only; **standard** elements add random
  vibration and thermal cycling; **critical** elements further add sine
  vibration, thermal vacuum, and EMC. Each element is placed into exactly one
  category before the mandatory test set is determined.
- Acceptance levels are derived from the corresponding qualification levels by
  applying a fixed reduction margin. For random vibration the acceptance power
  spectral density is 3 dB below the qualification PSD, which reduces the
  overall grms level by a factor of approximately 0.707. For sine vibration the
  acceptance amplitude (g) is likewise reduced by 3 dB in amplitude (factor
  ≈ 0.707). For thermal tests the acceptance temperature range is the
  qualification range narrowed by the acceptance margin (nominally 5 °C) at
  each extreme; a qualification range too narrow to accommodate the margin at
  both ends is flagged as degenerate before any test planning proceeds.
- Minimum test durations are specified per test type in Table 6-3 (paraphrased):
  vibration sine 4 min total, vibration random 2 min total, thermal cycling
  480 min, thermal vacuum 1 440 min, EMC 60 min, functional 30 min, visual
  inspection 15 min. A test whose actual duration falls short of the minimum is
  a duration finding, independent of whether all test types are present.
- A proposed acceptance test plan must pass two independent checks before the
  baseline is confirmed: (1) baseline completeness -- all mandatory test types
  for the element category are present; (2) duration compliance -- every listed
  test meets its minimum duration.

## Workflow

1. Assign the element to one of the three categories (simple, standard,
   critical) based on its design complexity, functional criticality, and
   mission class per the project's element-category rationale document. Reject
   an unrecognised category before any further processing.
2. Retrieve the mandatory test set for the assigned category from the Table 6-4
   mapping. Any test type in the proposed plan that is not in the defined
   vocabulary is rejected as an unrecognised entry before the baseline check
   runs.
3. For each test type in the mandatory set, derive the acceptance level from the
   qualification baseline: apply the −3 dB grms factor for random vibration,
   the −3 dB amplitude factor for sine vibration, and the ±5 °C thermal margin
   for thermal tests. Verify that the qualification input values are positive
   (vibration) or produce a non-degenerate acceptance range (thermal) before
   any level is issued.
4. Compare the proposed test plan against the mandatory set: record every
   mandatory test type absent from the proposed plan as a missing-test finding.
   Additional tests beyond the mandatory set are allowed and do not generate a
   finding.
5. For each test entry in the proposed plan, compare its declared duration
   against the Table 6-3 minimum for that test type; record the shortfall in
   minutes for every entry that falls short.
6. Combine the findings: the acceptance test baseline is confirmed only when
   both the missing-test list and the duration-failure list are empty. Any
   remaining finding must be resolved and re-verified before the acceptance
   test review board considers the plan closed.

## Pitfalls

- Applying qualification levels directly as acceptance levels -- acceptance
  tests run at reduced levels (−3 dB for vibration, narrowed thermal range);
  using qualification levels over-stresses the flight article and voids the
  acceptance rationale.
- Omitting the category assignment step and treating all elements as standard
  -- a simple element tested at the standard mandatory set incurs unnecessary
  risk of overstress; a critical element tested at the standard set leaves EMC,
  sine vibration, and thermal vacuum uncovered.
- Reading a duration shortfall as a minor administrative issue -- a test that
  runs below its minimum duration has not demonstrated the required exposure
  and must be repeated; it is a test-validity finding, not a paperwork gap.
- Accepting a degenerate thermal range without flagging it -- when the
  qualification temperature band is too narrow to accommodate the acceptance
  margin at both extremes, the acceptance range is undefined and the thermal
  test cannot be planned until the qualification range is reviewed.
- Treating extra tests in the proposed plan as evidence that the baseline is
  complete -- baseline completeness is determined by the mandatory set; extra
  tests do not compensate for missing mandatory ones.

## Behavior contract (gate 3)

The category mapping, level derivation, duration check, baseline completeness,
and full plan validation logic is exercised by the gate 3 contract test:
scripts/test_e1003_el_acceptance.py against
scripts/e1003_el_acceptance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_el_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
