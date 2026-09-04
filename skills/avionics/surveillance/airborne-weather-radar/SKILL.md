---
name: airborne-weather-radar
description: "Use when you must compute airborne weather radar operating-point quantities for convective weather avoidance: convert radar reflectivity factor Z to rainfall rate and back with the Marshall-Palmer Z-R relation, estimate the antenna elevation tilt that scans a storm cell top from own altitude and slant range, derive the flat-earth ground range to the cell, check a tilt setting against ground clutter return geometry, and rate echo intensity into standard levels from the reflectivity. Produces the rainfall rate, the required tilt angle, the ground range, the clutter check verdict and the echo level that gate weather radar tilt management in the cockpit. Trigger: airborne weather radar, convective weather avoidance, storm cell top, antenna tilt, reflectivity factor, rainfall rate, marshall palmer, echo level, ground clutter."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-185
    reference-only: true
gated: false
domain: avionics
pack: surveillance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: surveillance
  tags: [airborne-weather-radar, weather-radar-tilt, reflectivity-rainfall, marshall-palmer, echo-level, ground-clutter-check]
  version: 0.1.0
  author: AeroSkills
---

# Airborne Weather Radar (avionics/surveillance/airborne-weather-radar)

Use when the task is computing airborne weather radar operating-point
quantities for convective weather avoidance: mapping radar reflectivity
factor Z to rainfall rate through the Marshall-Palmer Z-R relation and
back, pointing the antenna tilt at a storm cell top, converting slant
range to displayed ground range, checking a tilt setting for ground
clutter return, and rating echo intensity into standard display levels.
This leaf implements the operating-point model in pure Python, stdlib
only, deterministic. It pairs with the surveillance siblings for the
wider air picture: air-to-air surveillance performance and collision
avoidance logic live in the sibling leaves, not here.

## Domain quick reference

- Marshall-Palmer Z-R relation: Z = a * R^b with Z in mm6/m3 and R in
  mm/h; module constants a = A_DEFAULT = 200.0 and b = B_DEFAULT = 1.6.
  The inverse is R = (Z / a)^(1 / b), so the pair round-trips any rate
  within 1e-6 relative.
- dBZ scale: dBZ = 10 * log10(Z). The Z-R relation is commonly quoted in
  dBZ form (20 mm/h gives about 43.8 dBZ).
- Cell top scan tilt: tilt = atan((cell_top_alt - own_alt) / slant_range)
  in degrees. The altitude difference may be negative when the cell top
  sits below the aircraft, and the tilt is then negative (beam points
  down).
- Displayed ground range (flat-earth): ground =
  sqrt(slant_range^2 - (own_alt - target_alt)^2). The earth-curvature
  constant RE_ARTH = 6371000.0 m is informational only; the model is
  flat-earth, which is valid for the short display ranges here.
- Ground clutter geometry: the lowest edge of the beam at the slant range
  sits at tilt - beam_width / 2. The angle to the terrain at that range
  is atan((terrain - own_alt) / slant_range). Clutter risk exists when
  the lowest beam edge lies below the terrain angle, because the beam
  still illuminates the ground.
- Echo levels: level 1 below 30 dBZ, level 2 from 30 to 40 dBZ, level 3
  from 40 to 50 dBZ, level 4 at 50 dBZ and above. Because log is
  monotonic, the linear Z thresholds 1000 / 10000 / 100000 mm6/m3 mark
  the same band edges.
- RTCA DO-185 frames the airborne weather radar MOPS context. The
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Convert rainfall to reflectivity with reflectivity_from_rainfall
   (Z = a * R^b) when the input is a rain rate, or invert with
   rainfall_from_reflectivity when the radar reports Z.
2. Confirm the conversion round-trips: the inverse of the forward value
   returns the starting rate within 1e-6 relative.
3. Point the beam: tilt_to_cell_top(own_altitude_m, cell_top_altitude_m,
   slant_range_m) returns the elevation tilt that puts the beam axis on
   the cell top. Negative tilt means the cell lies below the aircraft.
4. Get the displayed range: ground_range_from_slant(slant_range_m,
   own_altitude_m, target_altitude_m) with the default 0 m target for the
   surface reference.
5. Check the tilt against terrain: clutter_check(tilt_deg,
   own_altitude_m, slant_range_m, terrain_elevation_m, beam_width_deg)
   returns the beam lowest edge and the clutter verdict.
6. Rate the echo: echo_level(reflectivity) returns the standard four
   level category for the cockpit weather display.
7. For the full operating point in one call, run
   weather_radar_assessment(rainfall_mm_h, own_altitude_m,
   cell_top_altitude_m, slant_range_m, terrain_elevation_m,
   beam_width_deg) and read the six documented keys.
8. Confirm the deterministic checks with the contract test
   scripts/test_airborne_weather_radar.py.

## Worked example

Rainfall 20 mm/h, own altitude 3048 m (10 000 ft), cell top 12 192 m
(40 000 ft), slant range 111 120 m (60 NM), terrain 0 m, beam width 3 deg.

- Reflectivity: Z = 200 * 20^1.6 = 24 136.71 mm6/m3 (43.83 dBZ), inside
  the 20 000 to 28 000 bound. At 50 mm/h the value is 104 563.96 mm6/m3,
  inside the 90 000 to 120 000 bound.
- Rainfall round trip: rainfall_from_reflectivity(24 136.71) returns
  20.00 mm/h, within 1% (1e-6 relative) of the input.
- Tilt to cell top: atan(9144 / 111 120) = 4.704 deg, inside the 3.5 to
  6.0 deg bound (the cell top 9144 m above the aircraft).
- Ground range: sqrt(111 120^2 - 3048^2) = 111 078.19 m, within 0.5% of
  the slant range (displayed range is nearly the slant range at high
  altitude).
- Clutter check: beam lowest edge 4.704 - 1.5 = 3.204 deg above the
  horizon. The terrain angle at 111 120 m is atan(-3048 / 111 120) =
  -1.57 deg, so the beam is clear of the ground and clutter_verdict is
  False.
- Echo level: 24 136.71 mm6/m3 sits in the 40 to 50 dBZ band, so
  echo_level returns 3.

## Verification

- Reflectivity at 20 mm/h stays in 20 000 to 28 000 mm6/m3 and at
  50 mm/h in 90 000 to 120 000 mm6/m3; tilt stays in 3.5 to 6.0 deg;
  ground range stays within 0.5% of the slant range.
- Round trip: the Z-R inverse of the forward value returns the input
  rate within 1e-6 relative for any rate.
- Monotonicity: reflectivity rises with rainfall and tilt rises as the
  cell top rises.
- Clutter verdict flips True when the terrain angle exceeds the beam
  lowest edge (terrain 1000 m at 5000 m range from own 500 m with 0 deg
  tilt returns True).
- Every non-physical input raises ValueError: negative rainfall or
  reflectivity, a <= 0, b <= 0, slant range <= 0, beam width <= 0, and a
  slant range shorter than the altitude difference in
  ground_range_from_slant.
- Determinism: no RNG anywhere, run-to-run identical floats.
- Run the contract test offline: python3
  scripts/test_airborne_weather_radar.py (32 tests, deterministic).

## Related leaves

- avionics/surveillance/ads-b-surveillance: the broadcast surveillance
  sibling for air-to-air position and velocity performance, which owns
  the automatic dependent surveillance broadcast link.
- avionics/surveillance/tcas-resolution-advisory: the collision avoidance
  sibling, which owns resolution advisory decision making and its own
  surveillance logic.

## Pitfalls

- Replacing the module's Z-R constants: the reflectivity conversion
  uses Z = 200.0 * R^1.6 (A_DEFAULT, B_DEFAULT) — swapping in another
  Marshall-Palmer pair (say 300/1.4 for convective rain) without
  touching the module constants changes every reflectivity, echo
  level, and round trip this leaf reports.
- Comparing across the dBZ and linear scales: the echo bands are
  30 / 40 / 50 dBZ, which log-monotonically match the linear Z
  thresholds 1000 / 10000 / 100000 mm6/m3 — a rate compared as linear
  Z against a dBZ band edge mis-ranks the echo level.
- Forgetting the tilt can go negative: tilt is atan((cell_top - own) /
  slant_range), so a cell top below the aircraft gives a downward
  pointing beam — the altitude difference is signed and a negative
  tilt is a valid operating point, not an input error.
- Applying earth curvature to the displayed range: the model is
  flat-earth, ground = sqrt(slant^2 - (own - target)^2), and
  RE_ARTH = 6371000.0 m is informational only — at high altitude the
  displayed range is nearly the slant range (111 078.19 m from a
  111 120 m slant), and a slant range shorter than the altitude
  difference raises ValueError instead of returning an imaginary
  square root.
- Reversing the clutter comparison: clutter exists when the beam's
  lowest edge (tilt - beam_width / 2) lies below the terrain angle,
  because the beam still illuminates the ground — the worked example
  is clear (3.204 deg edge above a -1.57 deg terrain angle), and the
  verdict flips True only when the terrain angle rises above the
  edge, as in the 1000 m terrain case at 5000 m.
- Slipping the echo band edges: level 2 spans 30 to 40 dBZ, level 3
  spans 40 to 50 dBZ, and level 4 starts at 50 dBZ — the 24 136.71
  mm6/m3 worked echo (43.83 dBZ) is level 3, and boundary reflectivity
  must be graded on the linear threshold 1000 / 10000 / 100000, not a
  rounded dBZ guess.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_airborne_weather_radar.py

The test covers the worked-example contract (reflectivity values and
magnitude bounds, tilt and ground range real outputs, clutter lowest edge
and verdict, echo level 3), the Z-R round trip within 1e-6 relative, both
monotonicity directions, echo level band edges at 30 / 40 / 50 dBZ,
clutter verdict truth and toggling geometry, exact convenience-chain keys,
determinism, float output types, module constants, and ValueError
rejection of every non-physical input in the spec validation list.

## Compliance

- RTCA DO-185 (airborne weather radar MOPS) is referenced, reference-only
  and gated in standards-map.yaml: no test text or proprietary tables are
  reproduced. The Marshall-Palmer Z-R relation and the geometry above are
  standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
