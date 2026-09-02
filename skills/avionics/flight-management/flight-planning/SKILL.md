---
name: flight-planning
description: "Use when you must build and check a flight management system flight plan: compute great-circle leg distances between waypoints, verify the vertical profile against crossing constraints, and total the track distance for fuel and time planning. Produces the leg distance check, the vertical constraint verdict, and the flight plan validity flag that gates dispatch planning. Trigger: flight planning, flight management system, waypoints, vertical profile, track distance, fms."
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
  tags: [flight-planning, flight-management-system, waypoints, vertical-profile, track-distance, fms]
  version: 0.1.0
  author: Aero Agent Skills
---

# FMS Flight Planning (avionics/flight-management/flight-planning)

Use when the task is flight management system flight planning:
waypoint geometry, vertical profile constraint checks, and track
distance accounting for a planned route.

## Domain quick reference

- A flight plan is a sequence of waypoints and the legs between
  them; each leg has a great-circle distance.
- The vertical profile must satisfy crossing constraints: floor and
  ceiling altitudes at waypoints.
- Track distance drives fuel and time planning.
- A flight management system executes the plan under the airborne
  software lifecycle discipline of DO-178C.

## Workflow

1. Collect the waypoint sequence with coordinates.
2. Compute each leg distance with leg_distance_km.
3. Check the planned altitude against every crossing constraint
   with vertical_constraint_ok.
4. Total the track with total_distance_km.
5. Gate the plan with flight_plan_ok.

## Pitfalls

- Using flat-earth distances on long oceanic legs.
- Ignoring a floor constraint when cleared higher.
- Planning altitude against the wrong constraint pair.

## Behavior contract (gate 3)

The leg-distance, constraint, and validity logic is exercised by the
gate 3 contract test: scripts/test_flight_planning.py against
scripts/flight_planning_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_flight_planning.py

## Compliance

- Standards referenced, not reproduced: DO-178C text is proprietary
  (RTCA); the flight planning process here is common methodology,
  summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
