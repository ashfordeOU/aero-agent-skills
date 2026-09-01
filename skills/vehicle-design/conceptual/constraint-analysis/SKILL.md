---
name: constraint-analysis
description: "Use when you must run the aircraft constraint analysis matching chart in conceptual design: compute the stall constraint wing loading from the maximum lift coefficient and the stall speed, the takeoff distance constraint thrust to weight curve, the climb gradient constraint from the excess thrust and the lift to drag ratio, the cruise constraint, and the maneuvering constraint from the load factor, then assemble the feasible design region lower bounds that gate the conceptual design trade. Produces the constraint dict, the feasible region boundary, and the required thrust to weight at the design point. Trigger: constraint analysis, matching chart method, feasible region, stall constraint, takeoff distance, climb gradient, cruise constraint, maneuvering constraint, load factor."
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
  subdomain: conceptual
  tags: [constraint-analysis, matching-chart, feasible-region, stall-constraint, takeoff-constraint, climb-gradient, cruise-constraint, maneuvering-constraint, load-factor, wing-loading, thrust-to-weight]
  version: 0.1.0
  author: AeroSkills
---

# Aircraft Constraint Analysis (vehicle-design/conceptual/constraint-analysis)

Use when the task is aircraft constraint analysis for conceptual
design: the matching chart method that computes required thrust to
weight and wing loading from the stall, takeoff distance, climb
gradient, cruise, and maneuvering constraints, and the feasible design
region that bounds the propulsion and wing sizing trade.

## Domain quick reference

- Wing loading W/S is in N/m^2, thrust to weight T/W is unitless,
  air density rho in kg/m^3 (default 1.225 kg/m^3, sea-level ISA),
  speeds in m/s, takeoff distance in m, flight path angle gamma in
  rad, load factor n unitless, and g = 9.80665 m/s^2.
- Stall constraint (maximum wing loading): W/S = 0.5 * rho * CLmax *
  VS^2, from lift equal to weight at the stall speed VS.
- Takeoff distance constraint (required T/W): T/W = 1.21 * (W/S) /
  (rho * g * CLmax * s_TO), with s_TO the takeoff distance in m.
- Climb gradient constraint (required T/W): T/W = 1/LD + gamma, the
  level-flight drag term plus the small-angle climb term, gamma in
  rad; equivalently the excess thrust fraction (T - D)/W equals the
  climb gradient.
- Cruise constraint (required T/W at speed V): T/W = 0.5 * rho * V^2
  * CD0 / (W/S) + k * (W/S) / (0.5 * rho * V^2), the zero-lift drag
  term plus the lift-induced drag term, k = 1/(pi * e * AR).
- Maneuvering constraint (required T/W in a level turn at load factor
  n): T/W = 0.5 * rho * V^2 * CD0 / (W/S) + k * n^2 * (W/S) /
  (0.5 * rho * V^2); the induced drag term grows with n^2, and at n = 1
  the maneuvering curve reduces to the cruise curve.
- The matching chart plots required T/W against W/S, one curve per
  constraint. At a given wing loading the feasible region lower bound
  is the maximum of the required T/W values over the active
  constraints; the boundary of the feasible design region is the set
  of those lower bounds across the wing loading sweep, and every point
  above the boundary is feasible for the constraint set.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context
  (stall speed, takeoff field length, and climb gradients for
  transport-category aeroplanes); the constraint equations are common
  conceptual sizing practice.

## Workflow

1. Set the design point: stall speed, maximum lift coefficient, air
   density, takeoff distance, lift-to-drag ratio, climb gradient,
   cruise speed, zero-lift drag coefficient, induced drag factor k,
   and the maneuvering load factor.
2. Compute the maximum wing loading allowed by the stall speed with
   stall_constraint.
3. Compute the required T/W from the takeoff distance with
   takeoff_constraint.
4. Compute the required T/W from the climb gradient with
   climb_constraint.
5. Compute the required T/W at the cruise speed with
   cruise_constraint.
6. Compute the required T/W in the level turn with
   maneuvering_constraint.
7. Sweep candidate wing loadings, evaluate the constraint curves, and
   assemble the feasible region lower bounds with
   feasible_region_lower_bounds; the returned (W/S, T/W) pairs bound
   the feasible design region and gate the conceptual design trade.

## Pitfalls

- Mixing units: wing loading in kg/m^2 instead of N/m^2, or gamma in
  degrees with the small-angle formula; keep everything SI with gamma
  in rad.
- Forgetting the density default: rho defaults to 1.225 kg/m^3
  (sea level); at altitude the lower density tightens the takeoff and
  climb constraints.
- Treating the climb term as 1/LD only: the gamma term is the climb
  gradient itself; dropping it understates the required T/W.
- Using the maneuvering curve at n = 1 for a turn case: the induced
  drag term scales with the load factor squared; the required T/W in
  a sustained turn is larger than at level flight.
- Averaging the constraint T/W values instead of taking the maximum:
  the feasible region lower bound is the maximum, not the mean, and it
  defines the boundary of the feasible design region.
- Using the stall constraint as a required T/W curve: it gives a
  maximum wing loading boundary, not a thrust requirement.
- Passing an empty constraints dict to feasible_region_lower_bounds;
  the module raises ValueError instead of guessing.

## Behavior contract (gate 3)

The stall, takeoff distance, climb gradient, cruise, and maneuvering
constraints plus the feasible region lower bound logic are exercised
by the gate 3 contract test: scripts/test_constraint_analysis.py
against scripts/constraint_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_constraint_analysis.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the constraint
  equations are common conceptual design methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
