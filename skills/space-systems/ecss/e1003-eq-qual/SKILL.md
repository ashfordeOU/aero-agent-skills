---
name: e1003-eq-qual
description: "Use when defining the equipment qualification test baseline of an ECSS-E-ST-10-03C testing programme: select which test families apply to a piece of equipment and in what sequence (Table 5-1), and derive each applicable test's qualification level and duration from its reference level/duration plus a margin and duration factor (Table 5-2). Trigger: equipment qualification test, qualification baseline, test sequence, Table 5-1, Table 5-2, qualification level, qualification duration, margin factor, E-ST-10-03, ecss, e-st-10c."
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
  tags: [ecss, e-st-10-03c, equipment-testing, qualification, test-sequence, test-levels]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment Qualification Test Baseline (space-systems/ecss/e1003-eq-qual)

Use when the task is defining the equipment qualification test baseline
of an ECSS-E-ST-10-03C testing programme: which test families apply and
in what order (clause 5.2 + Table 5-1), and the qualification level and
duration each applicable test must demonstrate (Table 5-2), ahead of
running the per-test-family rules owned by the sibling 5.5.x leaves.

## Domain quick reference

- ECSS-E-ST-10-03C clause 5.2 sets the qualification test baseline for
  equipment: a fixed catalogue of test families (physical properties,
  functional/performance, mechanical, pressure integrity, thermal,
  electrical/RF, mission-specific) run in a defined sequence, with
  functional/performance checks bracketing the environmental exposures
  so any induced degradation is caught before and after stress.
- Table 5-1 tailors which test families actually apply to a given piece
  of equipment: physical-properties, functional/performance, and
  thermal are baseline for essentially all equipment, while mechanical,
  pressure-integrity, electrical/RF, and mission-specific tests are
  enabled by the equipment's own characteristics (it carries mechanical
  loads, is pressurized, contains electronics, or has a mission-unique
  test need).
- Table 5-2 derives each applicable test's qualification level and
  duration from its reference (predicted/design) level and duration by
  applying a margin and a duration factor -- qualification demonstrates
  margin beyond the flight-reference environment, not just reproduction
  of it. A margin can be applied multiplicatively (e.g. a levels ratio)
  or additively (e.g. a temperature offset); the duration factor is
  always multiplicative.
- The per-test-family numeric rules (actual levels, durations,
  tolerances, success criteria for mechanical/pressure/thermal/
  electrical/mission-specific tests) are owned by the sibling 5.5.x
  leaves (e1003-eq-mechanical, e1003-eq-pressure, e1003-eq-thermal,
  e1003-eq-electrical, e1003-eq-mission); this leaf only fixes the
  baseline sequence and the level/duration derivation rule that those
  per-family inputs plug into.

## Workflow

1. Capture the equipment's test-applicability attributes: does it carry
   mechanical (launch) loads, is it pressurized, does it contain
   electronics, does it have a mission-specific test need.
2. Select the applicable test families from those attributes
   (physical-properties, functional/performance, and thermal are always
   in scope; the rest are enabled per attribute).
3. Build the baseline sequence: physical-properties and an initial
   functional/performance check first, then the applicable
   environmental families in their fixed clause order (mechanical,
   pressure-integrity, thermal, electrical), then a closing
   functional/performance retest, then any mission-specific test last.
4. For every environmental family in the sequence, gather its Table 5-2
   inputs: reference level, reference duration, margin, duration
   factor, and margin mode (multiplicative or additive).
5. Derive the qualification level and duration for each of those
   families from its inputs, and attach the result to its sequence
   step.
6. Before handing the baseline to test-programme execution, confirm
   every environmental family in the sequence has a qualification
   level/duration attached; list any family still missing one rather
   than assuming the baseline is ready.

## Pitfalls

- Dropping the initial or final functional/performance check from the
  sequence -- without both, degradation caused by the environmental
  tests in between cannot be attributed to a specific test.
- Reusing the flight-reference (acceptance-level) environment as the
  qualification level/duration directly, instead of applying the
  margin and duration factor -- qualification without margin does not
  demonstrate the robustness the stage exists to prove.
- Applying a multiplicative margin where the input is actually an
  additive offset (e.g. treating a temperature margin as a ratio) --
  the margin mode must match how the family's environment is expressed.
- Treating the baseline as ready for execution while an applicable
  environmental family still has no qualification level/duration
  attached.

## Behavior contract (gate 3)

The applicability-selection, sequence-building, and level/duration
derivation logic is exercised by the gate 3 contract test:
scripts/test_e1003_eq_qual.py against scripts/e1003_eq_qual_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_qual.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
