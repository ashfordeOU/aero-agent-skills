---
name: ws-tw-trade
description: "Use when you must size the aircraft by matching wing loading and thrust to weight: compute the takeoff distance constraint, climb gradient constraint, and cruise constraint curves, and find the binding constraint that sets the minimum thrust to weight at a given wing loading. Produces the wing loading constraint envelope and the required thrust to weight for the sizing matching chart that gate the conceptual sizing trade. Trigger: wing loading, thrust to weight, matching chart, sizing, takeoff distance, climb gradient, binding constraint."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [wing-loading, thrust-to-weight, matching-chart, sizing, takeoff-distance, climb-gradient]
  version: 0.1.0
  author: AeroSkills
---

# W/S and T/W Matching (vehicle-design/sizing/ws-tw-trade)

Use when the task is wing loading and thrust to weight matching for
conceptual sizing: the stall, takeoff distance, climb gradient, and
cruise constraints that draw the sizing matching chart, and the
binding constraint that sets the minimum thrust to weight at a given
wing loading.

## Domain quick reference

- Wing loading W/S is in N/m^2, thrust to weight T/W is unitless,
  air density rho in kg/m^3 (default 1.225 kg/m^3, sea-level ISA),
  speeds in m/s, takeoff distance in m, flight path angle gamma in
  rad, and g = 9.80665 m/s^2.
- Stall constraint (maximum wing loading): W/S = 0.5 * rho * CLmax *
  VS^2, from lift equal to weight at the stall speed VS.
- Takeoff distance constraint (required T/W): T/W = 1.21 * (W/S) /
  (rho * g * CLmax * s_TO), with s_TO the takeoff distance in m.
- Climb gradient constraint (required T/W): T/W = 1/LD + gamma, the
  level-flight drag term plus the small-angle climb term, gamma in
  rad.
- Cruise constraint (required T/W at speed V): T/W = 0.5 * rho * V^2
  * CD0 / (W/S) + k * (W/S) / (0.5 * rho * V^2), the zero-lift drag
  term plus the lift-induced drag term, k = 1/(pi * e * AR).
- The matching chart plots required T/W against W/S, one curve per
  constraint; at a given wing loading the binding constraint is the
  curve with the largest required T/W, which sets the minimum thrust
  to weight for the propulsion sizing.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context
  (stall speed, takeoff field length, and climb gradients for
  transport-category aeroplanes); the constraint equations are common
  conceptual sizing practice.

## Workflow

1. Set the design point: stall speed, maximum lift coefficient, air
   density, takeoff distance, lift-to-drag ratio, climb gradient,
   cruise speed, zero-lift drag coefficient, and induced drag factor
   k.
2. Compute the maximum wing loading allowed by the stall speed with
   stall_constraint.
3. Compute the required T/W from the takeoff distance with
   takeoff_constraint.
4. Compute the required T/W from the climb gradient with
   climb_constraint.
5. Compute the required T/W at the cruise speed with
   cruise_constraint.
6. Sweep candidate wing loadings and find the binding constraint with
   feasible_min_tw; the returned min_tw is the required thrust to
   weight that sizes the propulsion system.

## Pitfalls

- Mixing units: wing loading in kg/m^2 instead of N/m^2, or gamma in
  degrees with the small-angle formula; keep everything SI with gamma
  in rad.
- Forgetting the density default: rho defaults to 1.225 kg/m^3
  (sea level); at altitude the lower density tightens the takeoff and
  climb constraints.
- Treating the climb term as 1/LD only: the gamma term is the climb
  gradient itself; dropping it understates the required T/W.
- Averaging the constraint T/W values instead of taking the maximum:
  the binding constraint is the maximum, not the mean, and it defines
  the feasible design point on the matching chart.
- Using the stall constraint as a required T/W curve: it gives a
  maximum wing loading boundary, not a thrust requirement.
- Passing an empty constraints dict to feasible_min_tw; the module
  raises ValueError instead of guessing.

## Behavior contract (gate 3)

The stall, takeoff distance, climb gradient, and cruise constraints
plus the binding-constraint minimum T/W logic are exercised by the
gate 3 contract test: scripts/test_ws_tw_trade.py against
scripts/ws_tw_trade_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_ws_tw_trade.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the constraint
  equations are common conceptual sizing methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
