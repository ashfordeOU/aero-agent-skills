---
name: oblique-shock
description: "Use when you must analyze an oblique shock in supersonic compressible flow: compute the wave angle beta from the upstream Mach number M1 and the flow deflection angle theta with the theta-beta-M relation, find the weak and strong solutions, the maximum deflection angle for an attached shock, and the downstream Mach number, static pressure, density, temperature, and stagnation pressure ratios across the shock. Covers shock polar basics: the weak branch keeps the flow supersonic with little stagnation pressure loss, the strong branch goes subsonic, and a deflection above the limit detaches the shock. Produces the wave angle, downstream state, and deflection limit for wedge, compression-corner, and inlet analyses. Trigger: oblique shock, shock wave, wave angle, deflection angle, theta-beta, wedge, compression corner, detached shock, shock polar, weak solution, strong solution, supersonic flow."
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
  tags: [oblique-shock, theta-beta, shock-polar, weak-solution, strong-solution, deflection-angle, mach-number, supersonic, compressible-flow, wedge]
  version: 0.1.0
  author: Aero Agent Skills
---

# Oblique Shock Relations (aerodynamics/high-speed/oblique-shock)

Use when the task is an oblique shock in supersonic flow: the wave
angle from the theta-beta-M relation, the weak and strong solutions,
the deflection limit for an attached shock, and the downstream state.

## Domain quick reference

- Geometry: a supersonic flow deflected into itself by the angle theta
  (wedge half-angle or compression-corner turn) forms an attached
  oblique shock inclined at the wave angle beta to the upstream flow,
  with the Mach angle mu = asin(1/M1) < beta <= 90 deg.
- Only the Mach component normal to the shock changes across it:
  M1n = M1 * sin(beta); the tangential component passes through
  unchanged. All downstream ratios come from the normal shock
  relations applied to M1n.
- theta-beta-M relation:
  tan(theta) = 2 * cot(beta) * (M1^2 * sin^2(beta) - 1) /
  (M1^2 * (gamma + cos(2*beta)) + 2). theta = 0 at both beta = mu
  (Mach wave, isentropic) and beta = 90 deg (normal shock).
- Two solutions for theta < theta_max: the weak solution (small beta,
  downstream flow usually still supersonic, the branch physically
  realized on a wedge) and the strong solution (large beta,
  downstream flow subsonic).
- Deflection limit theta_max: the apex of the shock polar, where the
  two branches merge. Above it no attached oblique shock exists and
  the shock detaches. theta_max grows with M1 toward about 45.6 deg
  (gamma = 1.4); at M1 = 2 it is 22.9735 deg.
- Downstream Mach: M2 = M2n / sin(beta - theta), with M2n the
  normal-shock downstream Mach at M1n.
- Ratios: p2/p1 = 1 + 2*gamma/(gamma+1) * (M1n^2 - 1), always > 1;
  rho2/rho1 and T2/T1 = (p2/p1)/(rho2/rho1) follow the normal shock
  relations; p02/p01 < 1 but far gentler than the normal shock at the
  same M1 (the weak oblique shock keeps almost all total pressure).
- Textbook anchor (Anderson, Modern Compressible Flow, Example 4.2)
  at M1 = 2.0, theta = 10 deg, gamma = 1.4: weak beta = 39.3139 deg,
  M2 = 1.6405, p2/p1 = 1.7066, p02/p01 = 0.9846; strong
  beta = 83.7001 deg, M2 = 0.6037, p2/p1 = 4.4438. At theta = 0 the
  strong branch is exactly the normal shock at M1 (p2/p1 = 4.5,
  M2 = 0.5773503).

## Workflow

1. Collect the upstream Mach number M1 (must be > 1), the deflection
   angle theta in degrees, and the specific heat ratio gamma (default
   1.4 for air).
2. Check the deflection limit with deflection_limit: theta above
   theta_max means a detached shock and no attached-shock answer.
3. Find both wave angles with shock_angles; use the weak branch for
   the physically realized wedge flow unless the boundary conditions
   force the strong branch.
4. Compute the downstream state with shock_properties (weak by
   default, strong=True for the strong branch): Mach number and the
   pressure, density, temperature, and stagnation pressure ratios.
5. For the Mach wave limit, use mach_angle for mu at the given M1.

## Pitfalls

- Feeding theta above theta_max: no attached oblique shock exists;
  the shock detaches. The functions raise instead of returning a
  fake wave angle.
- Using the normal shock relations on M1 instead of M1n: the oblique
  shock compresses only the Mach-normal component; using full M1
  overstates every ratio.
- Picking the strong branch by default: on a wedge the weak solution
  is the one realized; the strong branch needs downstream pressure
  high enough to force it.
- Treating the Mach wave as a shock: at theta = 0 the weak branch
  gives beta = mu with p2/p1 = 1, an isentropic limit, not a shock.
- Confusing beta and theta: beta is the shock wave angle to the
  upstream flow, theta the deflection of the flow itself; M2 uses
  sin(beta - theta).
- Feeding a subsonic M1: the relations are only valid for M1 > 1.

## Behavior contract (gate 3)

The oblique shock relation logic is exercised by the gate 3 contract
test: scripts/test_oblique_shock.py against
scripts/oblique_shock_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_oblique_shock.py

## Compliance

- Standards referenced, not reproduced: oblique shock relations are
  standard compressible-flow methodology (public-domain textbook
  content, e.g. Anderson, Modern Compressible Flow, Example 4.2);
  NACA TR 824 is referenced as the pack's public-domain reference
  anchor, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
