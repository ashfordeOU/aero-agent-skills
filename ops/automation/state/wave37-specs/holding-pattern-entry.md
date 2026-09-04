# Wave-37 leaf spec: holding-pattern-entry (avionics, flight-management pack)

- Path: skills/avionics/flight-management/holding-pattern-entry/
- Pack: flight-management. Closest siblings: flight-planning (FMS
  flight plan: great-circle leg distances, vertical profile, track
  distance - no holding geometry), lateral-navigation (track guidance),
  radius-to-fix-leg (RF leg geometry), rta-time-control (time control
  at a waypoint - not the holding entry sectors), performance-
  computation. Whole-tree grep: "holding pattern" has ZERO owning hits
  in any leaf or family router. ZERO owners. GENUINE AV gap (fresh
  probe).
- Standards id: far-25 (reference-only; family spine - holding is
  procedure context; body names the standard 70/110 degree entry rule
  as operational procedure, paraphrased). Ledger Standard: far-25.
- Family: avionics

## Claim

Determine the holding pattern entry and the pattern timing for an
aircraft joining a hold: classify the entry as direct, teardrop, or
parallel from the angle between the aircraft inbound track and the
holding side using the standard sector rule, compute the outbound leg
timing from the holding altitude (1 minute at or below 14000 ft, 1.5
minutes above), correct the outbound heading for the crosswind with the
1-in-60 rule, and estimate the pattern time for the first (entry) lap.
Produces the entry type, outbound leg seconds, wind-corrected outbound
heading, and the entry-lap time estimate that gate hold joining in an
FMS or manual procedure. Does NOT do: great-circle flight plan
construction (flight-planning); lateral track guidance (lateral-
navigation); radius-to-fix leg geometry (radius-to-fix-leg); RTA time
control (rta-time-control).

## Model (implement exactly)

Conventions: the aircraft approaches the holding fix on the inbound
course (the course it flies TOWARD the fix). The holding side is
right-hand or left-hand. alpha is the smaller angle from the inbound
course to the OUTBOUND end of the holding radial measured on the
holding side, in degrees in [0, 180] (standard entry rule inputs).

Functions (pure stdlib):
- entry_type(alpha_deg, turn_direction) -> "direct" | "teardrop" |
  "parallel": right-hand hold: alpha <= 70 -> direct; 70 < alpha <= 110
  -> teardrop; alpha > 110 -> parallel. Left-hand hold mirrors (use
  alpha measured on the holding side so the same rule applies).
  ValueError: alpha outside [0, 180]; turn_direction not in
  ("right", "left").
- outbound_leg_seconds(altitude_ft) -> 60.0 when altitude_ft <= 14000
  else 90.0. ValueError: altitude_ft < 0.
- wind_correction_heading(outbound_heading_deg, wind_from_deg,
  wind_speed_kt, tas_kt) -> float deg: crosswind component = wind speed
  * sin(radians(wind_from - outbound_heading)); correction =
  crosswind_component / tas * 60 (1-in-60, deg); corrected =
  outbound_heading + correction for a right-hand hold, minus for
  left-hand? use: corrected = (outbound_heading_deg +
  correction_deg) % 360 where correction_deg is signed with the wind
  direction (a wind from the right of the outbound heading pushes the
  aircraft left, so add the correction toward the wind). Implement the
  deterministic rule: correction = 60 * (wind_speed_kt * sin(radians(
  wind_from_deg - outbound_heading_deg))) / tas_kt; corrected =
  outbound_heading + correction. ValueErrors: tas <= 0, wind speed < 0.
- entry_lap_time_seconds(entry, outbound_leg_seconds) -> float: direct:
  2 * outbound + 2 * 60 (two 180 deg turns at 60 s each) + 60 (inbound
  leg) ... documented model: direct entry lap = outbound_leg + 3 * 60;
  teardrop lap = outbound_leg + 4 * 60; parallel lap = outbound_leg +
  5 * 60 (sector geometry constant offsets, documented model).

Identity to test: outbound_leg_seconds is 60 at 14000 ft and 90 just
above; entry_type boundaries at 70 and 110 degrees; wind correction
sign reverses when the wind direction flips 180 degrees.

## Worked example

Right-hand hold; the aircraft approaches with an inbound course such
that alpha = 50 deg -> direct; alpha = 90 -> teardrop; alpha = 130 ->
parallel. Altitude 12000 ft -> outbound 60 s; 20000 ft -> 90 s.
Outbound heading 090, wind from 135 at 20 kt, TAS 180 kt: crosswind =
20*sin(45 deg) = 14.14 kt; correction = 14.14/180*60 = 4.71 deg;
corrected = 094.7. Entry lap at 12000 ft direct = 60 + 180 = 240 s.
Run your module and take the real outputs as assert targets; the anchor
values above are bounds independently verified at prep (trigonometry
and the 1-in-60 rule).

## Validation list (contract test must include)

- ValueError: alpha outside [0,180]; bad turn direction; negative
  altitude; tas <= 0; negative wind speed.
- Entry truth table across the boundaries (70 and 110).
- Leg timing truth table at 14000 and just above.
- Wind correction anchor 4.71 deg at the example within 0.1 deg; sign
  reversal with wind 180 deg opposite.
- Determinism; float outputs as documented.

## Corpus fragment (eval/hit1-wave37-holding-pattern-entry.yaml)

Query 1 (copy verbatim):
  "determine the holding-pattern-entry type direct teardrop or parallel from the approach angle to the holding side"
  intent: "avionics; holding pattern entry classification"
  expected_skill: "avionics/flight-management/holding-pattern-entry"
Query 2 (copy verbatim):
  "compute the holding-pattern-entry outbound leg timing and wind-corrected outbound heading for the hold"
  intent: "avionics; holding pattern timing and wind correction"
  expected_skill: "avionics/flight-management/holding-pattern-entry"
Task ids: w37-holding-pattern-entry-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must determine a holding pattern
entry:" and include the outputs in the Claim. First tag:
holding-pattern-entry. Additional tags ONLY: direct-entry-sector,
teardrop-entry-sector, parallel-entry-sector, outbound-leg-timing,
holding-wind-correction. NEVER single generic words (holding, entry,
pattern, turn, wind). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): great-circle leg, vertical
profile, track distance (flight-planning); lateral track error
(lateral-navigation); RF leg (radius-to-fix-leg); RTA time control
(rta-time-control).
