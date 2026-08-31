---
name: normal-shock
description: "Use when you must compute normal shock relations for compressible flow: find the downstream Mach number, static pressure, density, and temperature ratios across the shock, and the stagnation pressure loss from the upstream Mach number. Produces the five shock ratios that gate inlet and high-speed aerodynamic analysis of a supersonic flow. Trigger: normal shock, oblique shock, mach number, compressible flow, pressure ratio, stagnation pressure, supersonic inlet, shock relations."
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
  tags: [normal-shock, compressible-flow, mach-number, shock-relations, supersonic, stagnation-pressure]
  version: 0.1.0
  author: AeroSkills
---

# Normal Shock Relations (aerodynamics/high-speed/normal-shock)

Use when the task is the normal shock relations of compressible flow:
downstream Mach number, static pressure, density, and temperature
ratios, and the stagnation pressure loss across the shock, from the
upstream Mach number M1 and the specific heat ratio gamma.

## Domain quick reference

- All inputs are unitless: the upstream Mach number M1 (must be > 1,
  supersonic) and the specific heat ratio gamma (default 1.4 for air).
- Downstream Mach: M2 = sqrt((1 + (gamma-1)/2 * M1^2) / (gamma * M1^2
  - (gamma-1)/2)); M2 < 1 whenever M1 > 1.
- Static pressure ratio: p2/p1 = 1 + 2*gamma/(gamma+1) * (M1^2 - 1),
  always > 1.
- Density ratio: rho2/rho1 = ((gamma+1) * M1^2) / (2 + (gamma-1) *
  M1^2).
- Temperature ratio: T2/T1 = (p2/p1) / (rho2/rho1), from the ideal-gas
  relation.
- Stagnation pressure ratio: p02/p01 = (p2/p1)^(1/(1-gamma)) *
  (rho2/rho1)^(gamma/(gamma-1)), always < 1 for M1 > 1: the total
  pressure loss is the entropy gain of shock compression.
- Textbook anchor (Anderson, Modern Compressible Flow, Table A.2) at
  M1 = 2.0, gamma = 1.4: M2 = 0.5773503, p2/p1 = 4.5, T2/T1 = 1.6875,
  rho2/rho1 = 2.6666667, p02/p01 = 0.720875.

## Workflow

1. Collect the upstream Mach number M1 and the specific heat ratio
   gamma (default 1.4 for air).
2. Compute the downstream Mach number with downstream_mach.
3. Compute the static ratios with pressure_ratio, density_ratio, and
   temperature_ratio.
4. Compute the stagnation pressure loss with stagnation_pressure_ratio.
5. Get all five ratios at once with shock_properties for the inlet or
   high-speed analysis.

## Pitfalls

- Feeding a subsonic M1: the relations are only valid for M1 > 1; a
  subsonic upstream flow has no normal shock.
- Using gamma <= 1: the specific heat ratio must exceed 1, or the
  square roots and exponents lose physical meaning.
- Reading the temperature ratio as a sum instead of a ratio: T2/T1 is
  p2/p1 divided by rho2/rho1, never p2/p1 minus something.
- Expecting stagnation pressure to rise: p02/p01 is always below 1
  for M1 > 1; a loss above 1 signals a sign or exponent error.
- Using the normal shock relations for an oblique shock: the oblique
  shock needs the Mach-normal component, a different analysis.

## Behavior contract (gate 3)

The shock relation logic is exercised by the gate 3 contract test:
scripts/test_normal_shock.py against scripts/normal_shock_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_normal_shock.py

## Compliance

- Standards referenced, not reproduced: normal shock relations are
  standard compressible-flow methodology (public-domain textbook
  content, e.g. Anderson, Modern Compressible Flow); NACA TR 824 is
  referenced as the pack's public-domain reference anchor, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
