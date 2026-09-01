---
name: wind-effects
description: "Use when you must resolve the wind triangle for a fixed-wing aircraft: decompose the wind into the headwind, tailwind, and crosswind components along the track, combine the true airspeed with the wind components to find the groundspeed, derive the wind correction angle needed to hold the track against the crosswind, and convert a leg distance into the enroute time at the resulting groundspeed. Produces the wind components, the groundspeed, the wind correction angle, and the enroute time that gate the wind effects assessment. Trigger: headwind, crosswind, wind correction angle, crab angle, groundspeed, enroute time, wind triangle."
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
  tags: [wind-effects, headwind, tailwind, crosswind, wind-correction-angle, groundspeed, crab-angle, enroute-time]
  version: 0.1.0
  author: AeroSkills
---

# Wind Effects (flight-mechanics/performance/wind-effects)

Use when the task is the wind triangle for flight planning: wind
components along the track, groundspeed from true airspeed and
wind, the wind correction angle to hold the track, and the
enroute time from the resulting groundspeed.

## Domain quick reference

- Wind components along the track: with delta the angle from the
  track to the wind direction, the headwind component is
  hw = W * cos(delta) and the crosswind component is
  xw = W * sin(delta); positive hw slows the aircraft and
  positive xw is a crosswind from the right. Wind direction is
  the direction toward which the wind blows, degrees true.
- Groundspeed from the wind triangle: GS = sqrt(TAS^2 - XW^2) +
  HW. The square root keeps the ground track constant while the
  aircraft crabs into the wind.
- Wind correction angle (crab angle) in degrees:
  WCA = asin(XW / TAS).
- Enroute time is the leg distance divided by the groundspeed:
  t = d / GS.
- Units: speeds in m/s (or knots consistently), angles in
  degrees, distance in meters, time in seconds. Wind effects sit
  in the FAR-25 / CS-25 transport flight planning context.

## Workflow

1. Collect the wind speed and direction, the track, and the true
   airspeed.
2. Decompose the wind into headwind and crosswind components
   with wind_components.
3. Combine the components with the true airspeed into the
   groundspeed with groundspeed.
4. Derive the wind correction angle with wind_correction_angle.
5. Convert the leg distance into the enroute time with
   enroute_time.

## Pitfalls

- Using the meteorological convention where the wind direction
  is the direction FROM which the wind blows; this skill takes
  the direction TOWARD which it blows, so convert by adding 180
  degrees first.
- Adding the full crosswind into the groundspeed; the wind
  triangle uses the square root so the track stays constant.
- A crosswind at or above the true airspeed; the track cannot be
  held and groundspeed and wind_correction_angle raise
  ValueError.
- Mixing m/s with knots inside one equation; keep every speed in
  the same unit.

## Behavior contract (gate 3)

The wind triangle logic is exercised by the gate 3 contract test:
scripts/test_wind_effects.py against scripts/wind_effects_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_wind_effects.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the
  wind triangle is common navigation and flight planning
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
