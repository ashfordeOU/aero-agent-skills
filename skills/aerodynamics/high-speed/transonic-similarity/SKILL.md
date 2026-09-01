---
name: transonic-similarity
description: "Use when you must apply compressibility corrections to subsonic aerodynamic coefficients: compute the Prandtl-Glauert factor and the refined Karman-Tsien correction for the pressure coefficient at a given Mach number, evaluate the transonic similarity parameter linking thickness and sweep effects, and estimate the critical Mach number at which local flow first reaches sonic speed. Produces corrected pressure coefficients and corrected lift slope, the critical Mach estimate, and drag-divergence Mach guidance for airfoil selection and high-subsonic wing design. Trigger: compressibility correction, Prandtl-Glauert, Karman-Tsien, transonic similarity, critical Mach number, pressure coefficient."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [prandtl-glauert, karman-tsien, transonic, compressibility-correction, critical-mach]
  version: 0.1.0
  author: AeroSkills
---

# Transonic Similarity Corrections (aerodynamics/high-speed/transonic-similarity)

Use when the task is compressibility corrections for high-subsonic
flows: the Prandtl-Glauert and Karman-Tsien pressure coefficient
corrections, the transonic similarity parameter, and critical Mach
estimation.

## Domain quick reference

- Prandtl-Glauert (linearized thin-airfoil theory, valid below
  M ~ 0.7): perturbation quantities scale with the factor
  1 / sqrt(1 - M^2). Pressure coefficient C_p = C_p0 / sqrt(1 - M^2),
  lift coefficient C_L = C_L0 / sqrt(1 - M^2), and section lift-curve
  slope a = a0 / sqrt(1 - M^2), where subscript 0 marks the
  incompressible value.
- Karman-Tsien (extended, usable toward M ~ 0.85):
  C_p = C_p0 / (sqrt(1 - M^2) + (M^2 / (1 + sqrt(1 - M^2))) * C_p0 / 2).
  The denominator shrinks less than the Prandtl-Glauert factor alone,
  so the correction stays finite closer to M = 1.
- Transonic similarity parameter: K = (1 - M^2) / tau^(2/3), with tau
  the thickness ratio (sweep enters through the effective Mach
  M * cos(Lambda)). Two thin configurations with equal K have similar
  pressure fields near M = 1.
- Critical pressure coefficient (isentropic sonic limit at freestream
  Mach M, gamma = 1.4 default):
  C_p* = (2 / (gamma * M^2)) * (((1 + (gamma - 1) / 2 * M^2) /
  (1 + (gamma - 1) / 2))^(gamma / (gamma - 1)) - 1). Local flow is
  sonic where C_p equals C_p*.
- Critical Mach number M_cr: solve C_p0 / sqrt(1 - M^2) = C_p*(M) for
  the smallest M; the peak-suction point is the first to reach sonic
  speed. Drag-divergence Mach M_DD sits roughly 0.05 to 0.08 above
  M_cr for typical sections.
- Rule of thumb: thinner sections and weaker peak suction raise M_cr;
  typical transport sections fall near M_cr 0.70 to 0.78.

## Workflow

1. Obtain the incompressible peak (or local) C_p0 and section slope
   a0 from a panel code, XFOIL, or published data.
2. Below M 0.7 apply the Prandtl-Glauert factor; from 0.7 to 0.85
   prefer the Karman-Tsien correction.
3. Estimate M_cr with critical_mach_number on the peak C_p0; keep the
   cruise Mach below M_cr for attached subsonic flow.
4. Use the transonic similarity parameter to scale thickness or sweep
   effects between configurations.
5. Cross-check with drag-divergence rules of thumb and wind-tunnel
   data when available.

## Pitfalls

- Applying Prandtl-Glauert past M ~ 0.7; linearized theory
  overpredicts suction near M = 1.
- Correcting a pressure coefficient that was already measured at a
  high subsonic Mach; the corrections apply to the incompressible
  reference value.
- Forgetting that C_p* depends on freestream Mach; it is not a fixed
  number.
- Confusing critical Mach with drag-divergence Mach; M_DD is higher
  and depends on thickness ratio and Reynolds number.
- Comparing signed C_p values instead of magnitudes when checking the
  sonic limit; C_p* is negative.
- Applying the similarity parameter to thick or blunt bodies; it is a
  thin-airfoil, small-disturbance result.
- Using gamma = 1.4 without checking the gas; hot or real-gas flows
  shift C_p*.

## Behavior contract (gate 3)

The correction logic is exercised by the gate 3 contract test:
scripts/test_transonic_similarity.py against
scripts/transonic_similarity_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_transonic_similarity.py

## Compliance

- Formulas are standard compressible-flow theory (Anderson; Houghton
  and Carpenter); paraphrase and computed values only, no verbatim
  excerpts of any standard.
- Standards reference: NACA TR 824 (airfoil section data,
  reference-only) per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
