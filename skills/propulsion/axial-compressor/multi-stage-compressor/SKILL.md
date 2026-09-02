---
name: multi-stage-compressor
description: "Use when you must design or match a multi-stage axial compressor for a gas turbine: compute the overall pressure ratio as the product of the stage pressure ratios, size the stage count required to reach the target pressure ratio from a design stage pressure ratio, account for the reheat factor that inflates the actual work split, size the annulus area from the mass flow, the axial velocity, and the density, distribute the stage work with equal or rising schemes, and correct the rotor speed to the reference temperature for off-design matching. Produces the stage count, overall pressure ratio, reheat factor, annulus area, and work distribution in SI units that gate the FAR-33 compressor architecture review. Trigger: multi-stage compressor, stage matching, overall pressure ratio, stage count, reheat factor, annulus area, work distribution."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: axial-compressor
  tags: [multi-stage, multi-stage-compressor, stage-matching, overall-pressure-ratio, stage-count, reheat-factor, annulus-area, work-distribution, corrected-speed, axial-compressor]
  version: 0.1.0
  author: Aero Agent Skills
---

# Multi-Stage Compressor (propulsion/axial-compressor/multi-stage-compressor)

Use when the task is multi-stage axial compressor design and
matching: overall pressure ratio from the stage pressure ratios, the
stage count to meet a target ratio, the reheat factor, the annulus
area layout, the stage work distribution, and the corrected speed for
off-design matching.

## Domain quick reference

- Overall pressure ratio: PR_overall = product of the stage pressure
  ratios, PR_overall = pi_1 * pi_2 * ... * pi_n, dimensionless. Each
  stage pressure ratio must exceed 1. Example: 6 stages at 1.45 give
  1.45**6 = 9.29.
- Stage count: n = ceil(ln(PR_overall) / ln(pi_stage)), with ln the
  natural logarithm. The result is the number of identical design
  stages and is always at least 1. Example: PR_overall 40 with 1.20
  per stage gives ceil(20.23) = 21 stages.
- Reheat factor: RF = W_actual / W_ideal_sum, dimensionless, always
  at or above 1. W_actual is the total work absorbed by all stages,
  W_ideal_sum the sum of the ideal (isentropic) stage works. Each
  stage re-compresses the reheat loss of the previous stage, so the
  actual total work exceeds the ideal sum; typical values run from
  1.01 to 1.06 and grow with the stage count.
- Stage work distribution: W_total = sum of the stage works w_k.
  Equal scheme: w_k = W_total / n for every stage. Rising scheme:
  w_k = W_total * 2*k / (n*(n+1)) for k = 1 to n, a linear ramp that
  puts about twice the first-stage work on the last stage, matching
  the rising back pressure along the flow path.
- Annulus area: A = m_dot / (rho * V_ax) in m^2, with mass flow m_dot
  in kg/s, density rho in kg/m^3, axial velocity V_ax in m/s. Density
  rises through the compressor, so for a constant axial velocity the
  annulus area shrinks toward the rear stages.
- Corrected speed: N_corr = N * sqrt(t_ref / t) in rpm, the rotor
  speed referred to the reference temperature for off-design
  matching. Standard day t_ref = 288.15 K; at t = t_ref the corrected
  speed equals the physical speed.
- Units: pressures dimensionless, work in J/kg (or J), area in m^2,
  flows in kg/s, velocities in m/s, densities in kg/m^3, speeds in
  rpm, temperatures in K.
- FAR-33 (14 CFR Part 33) sets the engine type certification context;
  it calls for demonstrating compression system operability but does
  not prescribe the matching relations above, which are common
  turbomachinery design practice.

## Workflow

1. Fix the design point: mass flow, overall pressure ratio target,
   inlet temperature, axial velocity, and density.
2. Choose the design stage pressure ratio (or a per-stage ratio
   list) and compute the stage count with
   stage_count(total_pressure_ratio, stage_pressure_ratio).
3. Compute the achieved overall pressure ratio from the stage ratio
   list with overall_pressure_ratio and confirm the product meets the
   target.
4. Distribute the total work with stage_work_distribution using the
   equal or rising scheme; prefer rising when the rear stages would
   otherwise be under-loaded at the rising back pressure.
5. Estimate the reheat factor with reheat_factor(actual_work,
   ideal_work_sum) and check it stays at or above 1.
6. Size the annulus at each station with annulus_area(mass_flow,
   axial_velocity, density), letting the local density grow along the
   flow path so the area shrinks.
7. For off-design matching, refer the rotor speed with
   corrected_speed(physical_speed, t_ref, t) before comparing with
   map data.

## Pitfalls

- Adding stage pressure ratios instead of multiplying: the overall
  pressure ratio is the product, so 6 stages at 1.45 give 9.29, not
  8.70.
- Rounding the stage count down: the count is the ceiling of the log
  ratio; 6 stages at 1.45 reach only 9.29, so a target of 10 needs 7
  stages at that loading.
- Trusting a reheat factor below 1: the actual total work can never
  sit below the ideal stage work sum, so such a value is a data
  error; the function raises ValueError instead of returning it.
- Mixing corrected and physical speed: corrected speed equals the
  physical speed only at the reference temperature; comparing raw
  speeds measured on a different day shifts the matching point.
- Passing a stage or total pressure ratio at or below 1: no
  compression happens, and the functions raise ValueError rather than
  divide by zero or return a nonsense count.
- Assuming an equal work split everywhere: rising back pressure
  unloads the rear stages of an equal-scheme machine; use the rising
  scheme or accept the matching penalty.
- Mixing units: keep everything SI (kg/s, m/s, kg/m^3, K, Pa); a
  density in kg/L or a flow in lb/s breaks the annulus area.
- Sizing the annulus with the inlet density at every station: the
  area must shrink as density grows, or the axial velocity falls and
  the rear stages stall.

## Behavior contract (gate 3)

The design and matching relations are exercised by the gate 3
contract test: scripts/test_multi_stage_compressor.py against
scripts/multi_stage_compressor.py (stdlib unittest, offline). Run:
python3 scripts/test_multi_stage_compressor.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain) and covers engine type certification, not stage
  matching methods; the pressure ratio, reheat factor, annulus, and
  work distribution relations are common turbomachinery methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
