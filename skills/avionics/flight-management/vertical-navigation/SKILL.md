---
name: vertical-navigation
description: "Use when you must compute the vertical navigation (VNAV) descent path for a flight management system: determine the top of descent distance from cruise altitude to an arrival constraint, compute the descent gradient and flight path angle, and check the resulting altitude against waypoint altitude constraints. Produces the top of descent distance, the descent gradient in feet per nautical mile, the flight path angle in degrees, and the constraint verdict for the descent path. Trigger: vertical navigation, vnav, top of descent, descent gradient, flight path angle, altitude constraints, fms."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: flight-management
  tags: [vertical-navigation, vnav, top-of-descent, descent-gradient, flight-path-angle, altitude-constraints, fms]
  version: 0.1.0
  author: Aero Agent Skills
---

# FMS Vertical Navigation (avionics/flight-management/vertical-navigation)

Use when the task is flight management system vertical navigation:
the vertical descent profile from cruise down to an arrival
constraint, its gradient and flight path angle, and altitude
constraint checks along the path.

## Domain quick reference

- Vertical navigation (VNAV) computes the descent profile between
  altitude constraints, not the lateral route geometry.
- Top of descent (TOD) is the point where the descent must start so
  the aircraft reaches the target altitude on the planned gradient.
- Descent gradient is the altitude loss per nautical mile along the
  path, commonly about 318 ft/nm for a 3 degree flight path angle
  (1 nm = 6076.1154 ft).
- Flight path angle is the descent angle derived from the gradient.
- Altitude constraints at waypoints are stated as AT or AT OR ABOVE
  values that the computed path must satisfy.
- An FMS executes this vertical profile under the airborne software
  lifecycle discipline of DO-178C.

## Workflow

1. Collect the cruise altitude, the target constraint altitude, and
   the planned descent gradient.
2. Compute the top of descent distance with tod_distance.
3. Derive the gradient from altitudes and distance with
   descent_gradient when the gradient is not given.
4. Convert the gradient to a flight path angle with fpa_deg.
5. Step down the path with altitude_at and check each waypoint
   constraint with constraint_ok.

## Pitfalls

- Mixing units: altitudes in feet with distances in nautical miles
  requires gradient in feet per nautical mile, not percent.
- Starting the descent late, which forces a steeper gradient than
  the aircraft can fly.
- Treating an AT OR ABOVE constraint as an exact crossing altitude.
- Computing a descent that ends below zero altitude.
- Confusing vertical navigation with lateral flight plan building
  (that is the flight-planning leaf).

## Behavior contract (gate 3)

The TOD, gradient, flight path angle, and constraint logic is
exercised by the gate 3 contract test:
scripts/test_vertical_navigation_logic.py against
scripts/vertical_navigation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_vertical_navigation_logic.py

## Compliance

- Standards referenced, not reproduced: DO-178C text is proprietary
  (RTCA); the VNAV computations here are common methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
