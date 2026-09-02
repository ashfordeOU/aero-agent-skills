---
name: root-locus-design
description: "Use when you must design a feedback loop with the classical root locus method: compute the closed loop pole locations as the forward-path gain K varies, find the gain that places the dominant poles at a target damping ratio zeta, and judge closed loop stability from the characteristic equation 1 + K*G(s) = 0. Applies to the canonical type-1 plant G(s) = 1/(s(s + a)) used in flight control analysis. Produces the pole pair, the gain for the requested zeta, and the stability verdict that feeds control law iteration. Trigger: root locus, closed loop poles, damping ratio, gain selection, characteristic equation, pole locations, zeta, stability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [root-locus-design, root-locus, closed-loop-poles, damping-ratio, gain-selection, characteristic-equation, stability, zeta]
  version: 0.1.0
  author: Aero Agent Skills
---

# Root Locus Design (gnc-autonomy/control/root-locus-design)

Use when the task is classical root locus design for a feedback
loop: tracing closed-loop pole trajectories against forward-path
gain, picking the gain for a target damping ratio, and judging
closed-loop stability from the characteristic equation.

## Domain quick reference

- For the canonical type-1 plant G(s) = 1/(s(s + a)) the closed
  loop is 1 + K*G(s) = 0, which reduces to s^2 + a*s + K = 0.
- The closed-loop poles are the roots of that quadratic; their
  motion in the complex plane as K grows is the root locus.
- Underdamped poles sit at -a/2 +/- j*wd with
  wd = sqrt(K - a^2/4) and damping ratio zeta = a/(2*sqrt(K)).
- The gain for a target damping ratio is K = a^2/(4*zeta^2).
- All poles with negative real part give a stable closed loop; a
  pole on the imaginary axis is marginal, not stable.
- Units: a in rad/s (open-loop pole location), K dimensionless,
  zeta dimensionless, poles as (re, im) pairs in rad/s.

## Workflow

1. Write the plant as G(s) = 1/(s(s + a)) with the open-loop pole
   location a in rad/s.
2. Pick a forward-path gain K and locate the closed-loop poles with
   closed_loop_poles(a, K).
3. Read the damping ratio of the resulting poles with
   damping_ratio(a, K).
4. Choose the gain for the target damping with
   gain_for_damping(a, zeta).
5. Confirm stability of the chosen loop with
   stability_verdict(a, K); iterate on K until the verdict is stable
   and the damping target is met.

## Pitfalls

- Reading the damping ratio from the gain formula when the loop is
  overdamped (K < a^2/4); the ratio is reported as 1 by convention.
- Calling a pole on the imaginary axis (K = 0, pole at the origin)
  stable; marginal cases are not asymptotically stable.
- Mixing units: a is in rad/s and K is dimensionless, so wd and the
  pole coordinates stay in rad/s throughout.
- Forgetting to validate that a > 0 and K >= 0 before computing.

## Behavior contract (gate 3)

The pole, gain, damping, and stability logic is exercised by the
gate 3 contract test: scripts/test_root_locus_logic.py against
scripts/root_locus_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_root_locus_logic.py

## Compliance

- ARP4754A is proprietary (SAE); name + paraphrase only per
  standards-map.yaml (ARP4754B supersedes; this skill keys to A,
  the certification-baseline revision).
- compliance: STANDARDS-REF, gated: false.
