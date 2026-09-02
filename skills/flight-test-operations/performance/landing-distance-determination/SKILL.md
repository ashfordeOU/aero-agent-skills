---
name: landing-distance-determination
description: "Use when you must determine the landing distance for a flight test: derive the approach speed Vref from the reference stall speed with the 1.23 factor, add the airborne flare segment and the braking ground roll, apply the 1.67 certification field length factor, and check the result against the available runway length. Produces the airborne and ground roll legs, the total demonstrated landing distance, the certified field length, and the runway fits verdict that gate the FAR 25.125 landing performance assessment. Trigger: landing distance, Vref approach speed, flare distance, braking ground roll, field length factor, runway length."
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
  tags: [landing-distance-determination, landing-distance, vref, approach-speed, flare, ground-roll, braking, field-length-factor, runway-length, flight-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Landing Distance Determination (flight-test-operations/performance/landing-distance-determination)

Use when the task is landing distance determination for a flight
test: approach speed Vref, the airborne flare segment, the braking
ground roll, the 1.67 certification field length factor, and the
runway fits verdict.

## Domain quick reference

- Speeds in m/s, time in s, distances in m, deceleration in m/s^2.
- Vref = factor * vs1g is the reference approach speed, with factor
  defaulting to 1.23 per FAR 25.125 landing approach practice
  (configurable, e.g. 1.3 for a higher margin).
- Airborne flare segment: s_air = Vref * t_air, from the 15.24 m
  (50 ft) threshold crossing to touchdown; t_air defaults to 5 s.
- Braking ground roll: s_ground = Vref^2 / (2 * a_brake), with
  a_brake the braking deceleration magnitude; a_brake = mu * g from
  the braking friction coefficient mu and g = 9.80665 m/s^2.
- Demonstrated landing distance: s_demo = s_air + s_ground.
- Certification field length: s_field = 1.67 * s_demo by default,
  the multiplier applied to the demonstrated distance per FAR 25.125
  landing field length practice.
- Runway verdict: margin = runway_m - required_m; verdict is fits
  when margin >= 0, else too short.
- Analytic check: vs1g = 50 m/s gives Vref = 61.5 m/s; t_air = 5 s
  gives s_air = 307.5 m; mu = 0.45 gives a_brake = 4.4130 m/s^2 and
  s_ground = 428.536 m; total = 736.036 m; the 1.67 factor gives a
  certified field length of 1229.180 m (3 dp).

## Workflow

1. Collect the reference stall speed vs1g, the flare time, the
   braking friction coefficient (or the deceleration directly), and
   the available runway length.
2. Derive the approach speed Vref with approach_speed.
3. Compute the airborne flare segment with airborne_distance and the
   braking ground roll with ground_roll.
4. Combine both legs with total_landing_distance.
5. Apply the certification factor with certified_field_length.
6. Check the certified field length against the available runway
   with runway_verdict and gate the landing on the verdict.

## Pitfalls

- Using the stall speed instead of Vref for the ground roll: the
  ground roll starts at the touchdown speed, which is the approach
  speed Vref in this model.
- Counting the flare leg twice or not at all: the demonstrated
  distance is the airborne leg plus the ground roll, not either
  alone.
- Confusing demonstrated and certified distances: the 1.67 factor
  applies to the demonstrated distance, and the certified field
  length is the larger number that must fit the runway.
- Mixing units: m/s with m/s^2 gives distances in m; knots or ft/s
  need conversion first.
- Reading a negative margin as an error: runway_verdict returns too
  short, which is a real, reportable landing outcome.
- Applying the 1.23 approach factor to the wrong base: the factor
  scales the 1g reference stall speed in the landing configuration
  context, not a takeoff configuration stall speed.

## Behavior contract (gate 3)

The landing distance determination logic is exercised by the gate 3
contract test: scripts/test_landing_distance.py against
scripts/landing_distance_logic.py (stdlib unittest, offline). Run:
`python3 scripts/test_landing_distance.py`

## Compliance

- Standards referenced, not reproduced: FAR-25 (14 CFR Part 25) is
  US government work (public domain) and CS-25 is a free EASA
  download; the landing distance method with the 1.23 approach
  factor and the 1.67 field length factor is common flight-test
  methodology in the FAR 25.125 context, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
