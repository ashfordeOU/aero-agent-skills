---
name: takeoff-distance-determination
description: "Use when you must determine the takeoff distance for a flight test: integrate the measured ground speed samples over the ground roll, add the rotation distance at the rotation speed, and close the airborne climb segment to the 35 ft obstacle height with the climb rate. Produces the ground roll distance, rotation distance, climb distance, and total takeoff distance that gate the takeoff field length assessment. Trigger: takeoff distance, ground roll, rotation speed, 35 ft obstacle, climb segment, flight test."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [takeoff-distance, ground-roll, rotation, flight-test, v1]
  version: 0.1.0
  author: AeroSkills
---

# Takeoff Distance Determination (flight-test-operations/performance/takeoff-distance-determination)

Use when the task is takeoff distance determination for a flight
test: ground roll integration from measured speed samples, rotation
to liftoff, and the airborne climb to the obstacle height.

## Domain quick reference

- Measurement method per the FAR 25.113 / CS-25.113 takeoff distance
  definition: distance from brake release to the point 35 ft above
  the takeoff surface, split into the ground roll, the rotation leg,
  and the airborne climb segment. 35 ft = 10.668 m (TARGET_HEIGHT_M).
- Speeds in m/s, times in s, distances in m. Ground roll distance
  integrates measured ground speed over time with the trapezoid rule:
  s = sum((v_i + v_{i+1}) / 2 * dt_i) over consecutive samples.
- rotation_distance: s_rot = v_rot * t_rot, the constant-speed leg
  from rotation start to liftoff at the rotation speed.
- climb_distance: s_air = v_liftoff * h_target / climb_rate, the
  time to the obstacle height at the climb rate flown at the liftoff
  speed.
- takeoff_distance: total = ground roll + rotation + climb;
  takeoff_distance_from_profile chains all three legs from one
  measured (v, t) sample set.
- Analytic check: samples (0,0), (25,10), (50,20) m/s,s integrate to
  a 500 m ground roll; v_rot = 50 m/s, t_rot = 2 s gives 100 m;
  climb at 5 m/s to 10.668 m gives 106.68 m; total 706.68 m.

## Workflow

1. Collect the measured ground speed samples (v, t) from the ground
   roll of the takeoff run.
2. Integrate the samples with ground_roll_distance.
3. Add the rotation leg with rotation_distance at the rotation
   speed.
4. Close the airborne leg with climb_distance to the 35 ft obstacle
   height.
5. Combine the legs with takeoff_distance and gate the takeoff
   field length assessment on the total.

## Pitfalls

- Integrating speed over distance instead of time: the ground roll
  distance is the time integral of the measured ground speed.
- Using a single speed sample: trapezoid integration needs at least
  two samples with strictly increasing time.
- Adding the rotation leg at the liftoff speed: the rotation leg
  runs at the rotation speed, which is lower.
- Forgetting the 35 ft obstacle: the takeoff distance is measured
  to the obstacle height, not to liftoff.
- Mixing units: m/s and s give m; knots or ft/s need conversion
  before integration.
- Reporting raw test-day distance as the result: measured takeoff
  distance is corrected to standard conditions before it is
  compared against the field length requirement.

## Behavior contract (gate 3)

The takeoff distance logic is exercised by the gate 3 contract test:
scripts/test_takeoff_distance_determination.py against
scripts/takeoff_distance_determination_logic.py (stdlib unittest,
offline). Run: `python3 scripts/test_takeoff_distance_determination.py`

## Compliance

- Standards referenced, not reproduced: FAR-25 (14 CFR Part 25) is
  US government work (public domain) and CS-25 is a free EASA
  download; takeoff distance determination follows the FAR 25.113 /
  CS-25.113 measurement method in summary form per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
