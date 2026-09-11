---
name: e1003-el-mechanical
description: "Use when run element-level mechanical tests for a space hardware item under ECSS-E-ST-10C §6.5.2: categorize each test type (physical properties, modal survey, static load, spin, transient/sine-burst, acoustic, random vibration, sinusoidal vibration) into its structural or dynamic family, confirm test levels and durations are within their qualification, protoflight, or acceptance specification, enforce the required test sequence (physical-properties and modal-survey before dynamic tests), and flag any non-compliant result or missing test item. Trigger: ecss, e-st-10c, element-mechanical, modal-survey, random-vibration, sinusoidal-vibration, acoustic, physical-properties, static-load, mechanical-testing."
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
  tags: [ecss, e-st-10c, element-mechanical, modal-survey, random-vibration, sinusoidal-vibration, acoustic, physical-properties, static-load, mechanical-testing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Element-Level Mechanical Testing (space-systems/ecss/e1003-el-mechanical)

Use when the task is to plan, execute, or review element-level mechanical tests
for a space hardware item per ECSS-E-ST-10C §6.5.2 — covering physical
properties, modal survey, static load, spin, transient/sine-burst, acoustic,
random vibration, and sinusoidal vibration.

## Domain quick reference

- §6.5.2 defines eight test types at element level. Each type falls into one of
  three families: mass-properties (physical properties), structural (static load,
  spin, transient/sine-burst), or dynamic (modal survey, acoustic, random
  vibration, sinusoidal vibration). Every test type must be categorized into its
  family before its acceptance criteria are evaluated.
- Test levels drive the applied load and duration: qualification levels are higher
  than acceptance or protoflight levels, and the appropriate level is selected
  from the verification plan before any test is set up.
- Test sequence is constrained: the physical-properties check must precede all
  structural and dynamic tests (baseline mass and inertia must be established
  first); the modal survey must precede all vibration and acoustic tests (the
  element's frequency response must be known before broadband or swept-sine
  excitation is applied).
- Each timed test type (random vibration, sinusoidal vibration, acoustic,
  transient/sine-burst) requires a documented test duration that matches the
  level specification. A duration that is absent or negative is a test-control
  anomaly that must be resolved before the test is counted as complete.
- Physical-properties measurements (mass, centre-of-mass offset, moment of
  inertia) are compared against budgets derived from the system mass budget and
  balance requirements. An exceedance in any parameter is an open finding.
- Vibration levels (Grms) must lie within ±10 % of specification; acoustic
  overall SPL must lie within ±3 dB of specification. Both tolerances follow
  standard industry practice for mechanical test control.

## Workflow

1. Receive the list of required element-level mechanical tests from the
   verification plan. For each entry, confirm the test type is one of the eight
   recognised types; reject any entry with an unknown type before proceeding.
2. Categorize each test into its family (mass-properties, structural, or
   dynamic). Structural and dynamic tests that appear before physical-properties
   or before modal-survey must be flagged as out-of-sequence.
3. For each test, record the nominated test level (acceptance, qualification, or
   protoflight). Reject any test whose level is not one of those three values.
4. For every timed test (random vibration, sinusoidal vibration, acoustic,
   transient/sine-burst), confirm a positive test duration is on record. Flag
   any timed test without a documented duration.
5. After the physical-properties test, compare measured mass, centre-of-mass
   offset, and moment of inertia against their respective budgets. Flag each
   parameter that exceeds its limit.
6. After the modal survey, confirm the measured fundamental frequency clears the
   minimum required frequency derived from the interface control document.
   Record the frequency margin.
7. For static-load tests, apply the safety factor to the limit load and confirm
   the applied load does not exceed the result. Record the load margin.
8. For vibration tests, compare applied Grms against the specification. Flag the
   test if the measured level falls outside the ±10 % control band.
9. For acoustic tests, compare the measured overall SPL against specification.
   Flag any deviation exceeding ±3 dB.
10. Aggregate all findings per test type; an element is not mechanically verified
    until every test is present, correctly sequenced, at a valid level, and has
    no open findings.

## Pitfalls

- Skipping the physical-properties check on the assumption that the element mass
  is known from the design — the test measurement is the formal record; an
  analysis value does not close the verification.
- Running vibration or acoustic tests before the modal survey — the element's
  resonant frequencies must be known in advance so that sweep rates and dwell
  times can be set safely and exceedances can be interpreted correctly.
- Treating a vibration level that is slightly over the upper control band as
  acceptable because the element survived — an out-of-band level means the test
  conditions are not representative of the required environment, which invalidates
  the result regardless of outcome.
- Applying a qualification load level to an acceptance-only item — over-testing
  can consume structural fatigue life allocated for the operational mission.
- Leaving a timed test duration unrecorded and reading the test as complete —
  duration is a primary test-control parameter; its absence makes the test
  non-traceable and prevents comparison with the qualification baseline.

## Behavior contract (gate 3)

The test-type categorization, physical-properties budget check, modal-survey
frequency margin, static-load margin, vibration-level control-band check,
acoustic-level control-band check, test-sequence ordering, and test-level
validation logic are exercised by the gate 3 contract test:
scripts/test_e1003_el_mechanical.py against
scripts/e1003_el_mechanical_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_el_mechanical.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
