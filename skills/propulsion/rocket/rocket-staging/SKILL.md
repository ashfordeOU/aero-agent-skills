---
name: rocket-staging
description: "Use when you must analyze multi-stage rocket staging for a launch vehicle: compute the ideal delta-v per stage from the rocket equation, allocate the stage mass ratios and the payload fraction across the stages, derive the structural index from the inert and the propellant masses, and optimize the stage count for a target total delta-v. Produces the per-stage delta-v, the stage mass ratio, the stage payload fraction, the structural index, the optimal stage split, and the minimum stage count, in SI units. Applies the equal-stage optimum split for identical stages. Trigger: rocket staging, stage mass ratio, payload fraction, structural index, stage count, delta-v."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [rocket-staging, delta-v, mass-ratio, payload-fraction, structural-index, stage-optimization, stage-count]
  version: 0.1.0
  author: AeroSkills
---

# Rocket Staging (propulsion/rocket/rocket-staging)

Use when the task is multi-stage rocket staging: per-stage ideal
delta-v, stage mass ratio and payload fraction allocation, structural
index, and stage optimization for a target total delta-v.

## Domain quick reference

- Per-stage ideal delta-v from the rocket equation:
  delta-v = g0 * Isp * ln(m0 / mf), with g0 = 9.80665 m/s^2.
- Worked: Isp = 300 s and m0 / mf = 2 give
  delta-v = 9.80665 * 300 * ln(2) = 2039.24 m/s.
- Stage mass ratio from a delta-v requirement:
  m0 / mf = exp(delta-v / (g0 * Isp)). Worked: 2040 m/s at Isp = 300 s
  gives m0 / mf = 2.00.
- Structural index eps = m_struct / (m_struct + m_prop). Worked:
  10000 kg structure and 90000 kg propellant give eps = 0.1.
- Payload fraction lam = m_payload / m0. Worked: 5000 kg payload on a
  100000 kg stage gives lam = 0.05.
- Stage mass ratio from the allocation indices:
  m0 / mf = 1 / (lam + eps * (1 - lam)). Worked: eps = 0.1 and lam =
  0.05 give m0 / mf = 6.8966 and delta-v = 5681.06 m/s at Isp = 300 s.
- Equal-stage optimum split for a target total delta-v:
  r* = exp(dv_total / (n * g0 * Isp)); every stage takes the same ratio
  and the total payload fraction is lam^n with
  lam = (1 / r* - eps) / (1 - eps). Worked: 9000 m/s, 2 stages, Isp =
  300 s, eps = 0.1 give r* = 4.6162 and lam_total = 0.01679.
- Minimum stage count for a payload target: 9000 m/s at Isp = 300 s
  and eps = 0.1 needs 3 stages for lam_total >= 0.02 (3 stages give
  0.0243). The achievable payload fraction is bounded by
  exp(-dv_total / (g0 * Isp * (1 - eps))) = 0.0334 as the stage count
  grows, so a 0.05 target is infeasible.

## Workflow

1. Collect the target total delta-v, the per-stage specific impulse,
   the structural indices, and the payload mass.
2. Compute each stage delta-v with stage_delta_v, or convert a stage
   delta-v requirement to a stage mass ratio with mass_ratio_from_delta_v.
3. Allocate the payload fraction and the structural index with
   payload_fraction and structural_index; combine them with
   mass_ratio_from_indices.
4. Check the per-stage delta-v implied by the allocation with
   stage_delta_v_from_indices.
5. Optimize the split of identical stages with
   optimal_equal_stage_split.
6. Find the minimum stage count for the payload target with
   stage_count_for_delta_v; sum per-stage delta-v with
   total_staged_delta_v.

## Pitfalls

- Confusing the structural index eps (inert fraction of the dry stage)
  with the payload fraction lam (payload over initial stage mass).
- Using the full-vehicle mass ratio in every stage: each stage burns
  with only the stages above it as payload, so each stage has its own
  mass ratio.
- Forgetting that stage payload fractions multiply, not add: the total
  payload fraction is lam^n, which is why 2 stages with lam = 0.13 give
  only 1.68% total payload.
- Treating the single-stage rocket equation as the staging answer:
  staging exists precisely because one stage cannot carry both the
  propellant and the structure for a large delta-v.
- Assuming more stages are always better: the payload fraction
  saturates at exp(-dv_total / (g0 * Isp * (1 - eps))), and each extra
  stage adds separation mass and failure modes.
- Confusing this leaf with rocket-sizing (which sizes the propellant
  mass and sums stage delta-v), with nozzle-design (which sizes the
  nozzle area ratio and exit Mach), or with propellant-selection
  (which trades propellant families and density impulse).
- Using inconsistent units: Isp in seconds, masses in kg, delta-v in
  m/s, with g0 = 9.80665 m/s^2.

## Behavior contract (gate 3)

The staging logic is exercised by the gate 3 contract test:
scripts/test_rocket_staging.py against scripts/rocket_staging_logic.py
(stdlib unittest, offline). Run:
python3 skills/propulsion/rocket/rocket-staging/scripts/test_rocket_staging.py

## Compliance

- Standards referenced, not reproduced: ECSS space-systems standards
  frame the launch-vehicle engineering context (free ESA download,
  ecss.nl/standards); the rocket equation and the staging optimum are
  common propulsion methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
