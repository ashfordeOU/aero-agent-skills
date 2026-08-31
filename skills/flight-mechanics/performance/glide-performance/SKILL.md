---
name: glide-performance
description: "Use when you must compute unpowered glide performance for a fixed-wing aircraft: derive the glide ratio from the lift and drag, convert it into the descent angle, find the sink rate from the airspeed and the descent angle, estimate the time to descend through a given altitude loss, and locate the best glide speed for the maximum lift to drag ratio. Produces the glide ratio, descent angle in degrees, sink rate in m/s, time to descend in seconds, and the best glide speed that gate the glide performance assessment. Trigger: glide ratio, sink rate, best glide speed, descent angle, time to descend, lift to drag."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [glide-performance, glide-ratio, sink-rate, best-glide-speed, descent-angle, lift-to-drag, unpowered-glide, time-to-descend]
  version: 0.1.0
  author: AeroSkills
---

# Glide Performance (flight-mechanics/performance/glide-performance)

Use when the task is unpowered glide analysis: glide ratio,
descent angle, sink rate, best glide speed, and time to descend
for a fixed-wing aircraft.

## Domain quick reference

- Glide ratio: L/D, the lift over the drag in steady unpowered
  flight, also equal to the horizontal distance covered per unit
  altitude lost (E = L/D = horizontal / altitude_lost).
- Descent angle: gamma = atan(1 / (L/D)) in degrees; for small
  angles gamma ~= asin(1 / (L/D)), the difference is negligible
  below about 15 deg.
- Sink rate: V_sink = V * sin(gamma), with true airspeed V in m/s
  and gamma in radians inside the sine.
- Time to descend: t = altitude_loss / V_sink, in seconds, for a
  constant sink rate over the altitude loss in meters.
- Best glide speed: the speed that maximizes L/D (minimum sink
  angle); scaled from a reference condition as
  v_best = v_ref * sqrt((L/D)_max / (L/D)_ref).
- Units are SI throughout: lift L and drag D in newtons (N) (any
  consistent force unit works for the ratio), speeds in m/s,
  angles in degrees, altitude in meters (m), time in seconds (s).
- Glide performance sits in the FAR-25 / CS-25 context for
  emergency descent and dead-stick landing considerations; the
  mathematics here is standard flight mechanics.

## Workflow

1. Collect the lift and drag, or the horizontal distance and the
   altitude lost, for the unpowered condition.
2. Compute the glide ratio with glide_ratio; verify it is
   positive before trusting it.
3. Convert it to the descent angle with descent_angle.
4. Compute the sink rate with sink_rate from the true airspeed
   and the descent angle.
5. Estimate the time to descend with time_to_descend from the
   altitude loss and the sink rate.
6. Locate the best glide speed with best_glide_speed from a
   reference speed and the maximum lift to drag ratio.
7. Report the glide ratio, angle, sink rate, time, and best
   glide speed together for the glide assessment.

## Pitfalls

- Mixing degrees and radians: descent_angle returns degrees and
  sink_rate expects degrees; the sine conversion happens inside
  the function, so never pre-convert.
- Feeding drag of zero: the glide ratio is undefined at D = 0;
  a zero or negative drag must raise, not divide by zero.
- Using the airspeed instead of the sink rate for time to
  descend: t = altitude_loss / V_sink, not altitude_loss / V.
- Forgetting the square root in best_glide_speed: the speed
  scales with sqrt((L/D)_max / (L/D)_ref), not with the ratio
  itself.
- Treating the descent angle as exact at steep angles: atan is
  exact; the asin small-angle form is only an approximation.
- A sink rate of zero or less has no glide: the aircraft is not
  descending, so time to descend is undefined.

## Behavior contract (gate 3)

The glide ratio, descent angle, sink rate, best glide speed, and
time to descend logic is exercised by the gate 3 contract test:
scripts/test_glide_performance.py against
scripts/glide_performance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_glide_performance.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; glide
  performance from lift and drag is common flight-mechanics
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
