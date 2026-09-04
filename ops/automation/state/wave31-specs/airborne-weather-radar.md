# Wave-31 leaf spec: airborne-weather-radar (avionics, surveillance pack)

- Path: skills/avionics/surveillance/airborne-weather-radar/
- Pack: surveillance (siblings: ads-b-surveillance, tcas-resolution-advisory).
  Neither sibling touches weather radar, reflectivity, or precipitation;
  nothing in the avionics family computes radar tilt management or the
  reflectivity-rainfall relation. This is the third surveillance leaf.
- Standards ids: rtca-do-260b is ADS-B MOPS (wrong for radar); use
  rtca-do-185 (the airborne weather radar MOPS id already in standards-map,
  reference-only, gated true: never reproduce its test text). Ledger
  Standard: rtca-do-185.
- Family: avionics

## Claim

Compute airborne weather radar operating-point quantities for convective
weather avoidance: convert radar reflectivity factor Z to rainfall rate with
the Marshall-Palmer Z-R relation and back, estimate the antenna elevation tilt
needed to scan a storm cell top from the own altitude and slant range, compute
the displayed range to a cell from the slant range and the own altitude with a
flat-earth approximation, check a tilt setting against ground clutter return
geometry, and classify echo intensity into standard levels from the
reflectivity. Produces the rainfall rate, the required tilt angle, the ground
range, the clutter check verdict, and the echo level that gate a weather radar
tilt-management and attenuation assessment in the cockpit.

Does NOT do: TCAS resolution advisories (tcas-resolution-advisory owns RA
logic); ADS-B performance (ads-b-surveillance); radar receiver or antenna
design; attenuation correction beyond a stated one-way specific attenuation
input (no proprietary RTCA test procedures reproduced); lightning or
turbulence detection algorithms beyond the Z-R mapping; Doppler velocity
products.

## Model (implement exactly)

Module constants:
- A_DEFAULT = 200.0 (Marshall-Palmer coefficient, Z = A * R^b).
- B_DEFAULT = 1.6 (Marshall-Palmer exponent).
- RE_ARTH = 6371000.0 (m, used only for the optional earth-curvature note; the
  ground-range model is flat-earth per the claim).
- PI = math.pi.

Functions (pure stdlib):
- reflectivity_from_rainfall(rainfall_mm_h, a=A_DEFAULT, b=B_DEFAULT) ->
  float: Z = a * rainfall**b. ValueError if rainfall < 0, a <= 0.
- rainfall_from_reflectivity(reflectivity, a=A_DEFAULT, b=B_DEFAULT) ->
  float: R = (Z / a)**(1/b). ValueError if reflectivity < 0, a <= 0, b <= 0.
- tilt_to_cell_top(own_altitude_m, cell_top_altitude_m, slant_range_m) ->
  float: tilt = atan((cell_top - own_alt) / slant_range) in degrees (the
  elevation angle that puts the beam axis on the cell top). ValueError if
  slant_range <= 0; the altitude difference may be negative (cell below the
  aircraft) and returns a negative tilt.
- ground_range_from_slant(slant_range_m, own_altitude_m,
  target_altitude_m=0.0) -> float: sqrt(max(0, slant^2 - (own - target)^2))
  flat-earth ground range. ValueError if the slant range is smaller than the
  altitude difference (non-physical): the squared argument would be negative.
- clutter_check(tilt_deg, own_altitude_m, slant_range_m,
  terrain_elevation_m=0.0, beam_width_deg=3.0) -> dict:
  {beam_lowest_edge_deg, clutter_verdict} where the lowest edge of the beam
  at the slant range is tilt - beam_width/2 (degrees) and clutter_verdict is
  True when the beam's lowest edge angle is below the angle to the terrain
  at that range, angle_to_terrain = atan((terrain - own_alt)/slant_range);
  i.e. clutter risk exists when the beam still illuminates the ground.
  ValueErrors: slant_range <= 0, beam_width <= 0.
- echo_level(reflectivity) -> int: return the standard four-level weather
  echo category 1-4 by reflectivity thresholds (level 1 for Z < 30 dBZ,
  level 2 for 30-40 dBZ, level 3 for 40-50 dBZ, level 4 for >= 50 dBZ;
  dBZ = 10*log10(Z)). ValueError if reflectivity < 0.
- weather_radar_assessment(rainfall_mm_h, own_altitude_m, cell_top_altitude_m,
  slant_range_m, terrain_elevation_m=0.0, beam_width_deg=3.0,
  a=A_DEFAULT, b=B_DEFAULT) -> dict: convenience chain returning
  {reflectivity, rainfall_rate, tilt_to_cell_top_deg, ground_range_m,
  clutter: {beam_lowest_edge_deg, clutter_verdict}, echo_level}.

## Worked example

Rainfall 20 mm/h, own altitude 3048 m (10 000 ft), cell top 12 192 m
(40 000 ft), slant range 111 120 m (60 NM), terrain 0 m, beam width 3 deg.

Deterministic anchors (run your module, take the printed values as the assert
targets, then CHECK the magnitude bounds):
- reflectivity at 20 mm/h in 20 000-28 000 mm6/m3 (about 24 137), dBZ about
  43.8.
- rainfall from that reflectivity returns about 20 mm/h (round-trip within
  1%).
- reflectivity at 50 mm/h in 90 000-120 000 mm6/m3 (about 104 564).
- tilt to cell top in 3.5-6.0 deg (about 4.7).
- ground range at 60 NM slant and 3048 m own altitude within 0.5% of the
  slant range (about 111 078 m).
- clutter: beam lowest edge about 3.2 deg (4.7 - 1.5) above the horizon while
  the terrain angle is negative: clutter_verdict False.
- echo_level for 24 137 mm6/m3 is 3 (40-50 dBZ band).
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: rainfall < 0, reflectivity < 0, a <= 0, b <= 0, slant_range <= 0,
  beam_width <= 0, slant range shorter than the altitude difference in
  ground_range_from_slant.
- Round-trip: rainfall_from_reflectivity(reflectivity_from_rainfall(R))
  returns R within 1e-6 relative.
- Monotonicity: reflectivity increases with rainfall; tilt to cell top
  increases as the cell top rises.
- clutter_verdict True when the terrain angle exceeds the beam lowest edge
  (e.g. terrain 1000 m at 5000 m range from own 500 m with 0 deg tilt).
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-airborne-weather-radar.yaml)

Query 1 (copy verbatim):
  "compute the antenna tilt angle to scan a convective storm cell top with an airborne weather radar from own altitude and slant range to the cell"
  intent: "avionics; airborne weather radar tilt management for cell top scan"
  expected_skill: "avionics/surveillance/airborne-weather-radar"
Query 2 (copy verbatim):
  "convert radar reflectivity factor to rainfall rate with the marshall palmer z-r relation and rate the echo level for a cockpit weather display"
  intent: "avionics; weather radar reflectivity rainfall mapping and echo level"
  expected_skill: "avionics/surveillance/airborne-weather-radar"
Task ids: w31-airborne-weather-radar-1 and -2.

Forbidden tokens that belong to siblings: do NOT use ADS-B, DO-260B,
transponder, TCAS, resolution advisory, traffic, RAIM, GNSS. Do NOT claim
attenuation correction or receiver design (not in the claim) and never
reproduce rtca-do-185 test text (gated true).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute airborne weather radar
operating-point quantities for convective weather avoidance:" and include the
outputs listed in the Claim. First tag: airborne-weather-radar. Additional
tags only: weather-radar-tilt, reflectivity-rainfall, marshall-palmer,
echo-level, ground-clutter-check. NEVER single generic words (radar, weather,
rain, tilt, display). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.
