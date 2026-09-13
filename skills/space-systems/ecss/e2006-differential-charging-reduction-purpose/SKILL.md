---
name: e2006-differential-charging-reduction-purpose
description: "Use when evaluate whether a mission holds differential-charging and stored-discharge-energy below its acceptable levels under ECSS-E-ST-20-06C clause 6.1.2: take the predicted absolute potential of each adjacent surface-pair, derive the differential-potential across the dielectric gap, compute the pair capacitance from coated-area, dielectric-thickness and relative-permittivity, convert it into the stored-discharge-energy an electrostatic-discharge would release, grade each pair against the mission differential-potential limit and energy budget, solve the minimum dielectric-thickness or maximum coated-area that would meet that budget, and aggregate a mission verdict carrying the reduction-factor still outstanding. Trigger: ecss-e-st-20-06c, clause-6-1-2, differential-charging, differential-potential-limit, stored-discharge-energy, electrostatic-discharge-energy, dielectric-capacitance, charging-mitigation-objective."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-differential-charging-reduction-purpose, ecss-e-st-20-06c, differential-charging, stored-discharge-energy, electrostatic-discharge-energy, differential-potential-limit, charging-mitigation-objective]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Differential-Charging Reduction Objective (space-systems/ecss/e2006-differential-charging-reduction-purpose)

Use when the task is stating and checking the mission-level aim of
ECSS-E-ST-20-06C clause 6.1.2 -- keeping the differential-potential
between neighbouring surfaces, and the energy an
electrostatic-discharge could release, beneath levels the mission has
declared acceptable.

## Domain quick reference

- Clause 6.1.2 is an objective clause, not a numeric-table clause. It
  fixes *what* the design must achieve on every mission: a
  differential-potential small enough not to initiate a discharge, and
  a stored energy small enough that a discharge which does occur cannot
  damage or upset the affected unit. The numeric limits themselves come
  from the mission specification; the objective is what makes an
  unset limit a finding rather than a free pass.
- The absolute potential of the whole spacecraft with respect to the
  ambient environment is not the hazard. A structure floating uniformly
  at a large negative potential drives no internal arc. The hazard is
  the *difference* between a floating-dielectric outer face and the
  grounded conductor beneath or beside it, because that difference
  appears across a short dielectric path.
- Energy, not potential, sets the damage severity. An adjacent
  surface-pair behaves as a parallel-plate capacitance of
  permittivity-of-free-space times relative-permittivity times
  coated-area divided by dielectric-thickness. The stored energy is
  half that capacitance times the differential-potential squared, so it
  grows linearly with area and quadratically with the
  differential-potential, and falls as the dielectric is made thicker.
- Two levers reduce the stored energy for a fixed differential-potential:
  shrink the coated-area of a single continuous dielectric patch (split
  a large sheet into smaller electrically-separated patches), or
  increase the dielectric-thickness. A third lever -- lowering the
  differential-potential itself by making the outer layer conductive and
  bonding it -- is the more effective one, because the energy depends on
  the square of that potential.

## Workflow

1. Establish the mission acceptance levels before any pair is graded: a
   differential-potential limit and a stored-discharge-energy budget. An
   absent level is an open finding; do not substitute a house default
   silently.
2. For every adjacent surface-pair, take the two predicted absolute
   potentials and derive the differential-potential as the magnitude of
   their difference. Sign conventions cancel here, so record the
   magnitude and keep the two absolute values for traceability.
3. Compute the pair capacitance from the coated-area, the
   dielectric-thickness and the relative-permittivity of the dielectric
   between the two faces. Reject a non-positive area, thickness, or a
   relative-permittivity below unity.
4. Convert capacitance and differential-potential into the
   stored-discharge-energy, then grade that energy into a severity band
   and compare it with the mission budget. Compare with a relative
   tolerance so an exactly-at-budget pair reads compliant; never widen
   the budget itself.
5. Where a pair exceeds the budget, compute the reduction-factor needed
   and the two design answers that deliver it: the minimum
   dielectric-thickness at the present area, and the maximum coated-area
   at the present thickness.
6. Aggregate over the mission: the objective of clause 6.1.2 is met only
   when every pair is inside both the differential-potential limit and
   the energy budget, and no pair is missing a level or an input.

## Pitfalls

- Grading the absolute spacecraft potential instead of the
  differential-potential. A uniformly charged structure can sit
  thousands of volts from the ambient plasma and still be benign; two
  adjacent faces a few hundred volts apart across a thin dielectric are
  not.
- Declaring a pair acceptable on potential alone. A modest
  differential-potential over a large continuous dielectric sheet stores
  more energy than a higher potential over a small patch, and the damage
  threshold is written in energy.
- Treating a missing mission limit as an implicit pass. Clause 6.1.2
  requires the acceptable level to exist; a pair graded against nothing
  is unverified, which is an open finding.
- Reducing the coated-area on paper without electrically separating the
  patches. Two patches that remain connected through a continuous
  conductive layer still discharge as one capacitance.
- Assuming a thicker dielectric is always the cheaper fix. Energy falls
  only in inverse proportion to thickness, while it falls with the
  square of the differential-potential, so lowering the potential buys
  far more than the same fractional change in thickness.

## Behavior contract (gate 3)

The differential-potential, pair-capacitance, stored-energy,
severity-band, reduction-factor and mission-aggregation logic is
exercised by the gate 3 contract test:
scripts/test_e2006_differential_charging_reduction_purpose.py against
scripts/e2006_differential_charging_reduction_purpose_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2006_differential_charging_reduction_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
