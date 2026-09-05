# Wave-40 leaf spec: ground-station-pass-planning (space-systems, mission-design pack)

- Path: skills/space-systems/mission-design/ground-station-pass-planning/
- Pack: mission-design. Closest siblings: satellite-coverage (orbit-
  mechanics pack; owns the single-pass access circle, swath, and the
  first-order access_time_per_pass formula from the central-angle
  half-cone; its body explicitly routes link/radio and scheduling
  questions away), command-data-handling (subsystems pack; owns
  CCSDS/downlink data budgeting, not access scheduling),
  communication-link-budget (owns the RF link math), ground-track-
  repeat and kepler-orbit-propagation (orbit mechanics; own the orbit
  state propagation this leaf consumes). Whole-tree greps at prep:
  "pass planning", "downlink gap", "contact window", "ground station"
  as a scheduling function = 0 hits in skills/space-systems/. GENUINE
  SPACE gap (fresh probe, conf 0.6): the tree has single-pass
  geometry and data budgets but no multi-pass daily contact schedule
  or downlink-gap layer.
- Standards id: ecss (reference-only; space-systems family
  convention). Ledger Standard: ecss.
- Family: space-systems

## Claim

Build the daily ground-station contact schedule of a low-Earth
satellite: propagate the sub-satellite point over the planning
horizon, compute the elevation of the satellite above each station,
detect the contiguous passes above the station mask, aggregate the
daily contact schedule with the downlink gaps, and merge the contacts
of several ground stations into one plan. Produces the per-pass
start/end/duration and maximum elevation, the daily contact totals,
the gap list, the maximum downlink gap, and the merged multi-station
plan that gate the mission data-collection and downlink assessment.
Does NOT do: the single-pass access-circle and access_time_per_pass
formula (satellite-coverage); downlink data budgeting or CCSDS frame
accounting (command-data-handling); RF link budgets
(communication-link-budget); orbit propagation with J2 or drag
(kepler-orbit-propagation and orbital-perturbations own the physical
propagation; this leaf uses a simple circular two-body ground track
and takes the orbit elements as inputs).

## Model (implement exactly)

Functions (pure stdlib; spherical Earth; module constants RE_KM =
6371.0, MU = 398600.4418 km^3/s^2, OMEGA_E = 7.2921159e-5 rad/s,
STEP_S = 30.0 s, GAP_THRESHOLD_S = 600.0):
- orbital_period_s(altitude_km) -> float
  T = 2 pi sqrt(a^3 / mu) with a = RE_KM + altitude_km; ValueError if
  altitude_km < 0.
- subsatellite_point(altitude_km, inclination_deg, raan_deg,
  argument_of_latitude_0_deg, greenwich_0_deg, t_s) -> dict
  {"lat_deg", "lon_deg"} from the circular-orbit inertial position
  rotated by the Earth rotation (lon wrapped to [-180, 180]); no J2;
  ValueError if altitude_km < 0, inclination outside [0, 180], t_s <
  0.
- elevation_angle(station_lat_deg, station_lon_deg, lat_deg,
  lon_deg, altitude_km) -> float
  central angle lam from the station to the sub-satellite point, then
  elevation = atan2(cos(lam) - RE_KM / r, sin(lam)) in degrees, r =
  RE_KM + altitude_km; ValueError if altitude_km < 0.
- detect_passes(altitude_km, inclination_deg, raan_deg,
  argument_of_latitude_0_deg, greenwich_0_deg, station_lat_deg,
  station_lon_deg, min_elevation_deg, horizon_h) -> list of dicts
  {"start_s", "end_s", "duration_s", "max_elevation_deg"}: step t from
  0 to horizon_h * 3600 in STEP_S increments, accumulate contiguous
  samples with elevation >= min_elevation_deg into passes (duration =
  end - start + STEP_S); ValueError if min_elevation_deg < 0 or
  horizon_h <= 0.
- daily_contact_schedule(passes, gap_threshold_s=GAP_THRESHOLD_S) ->
  dict {"n_passes", "total_contact_s", "contacts": [pass dicts],
  "gaps": [{"start_s", "end_s", "duration_s"} for inter-pass gaps at
  least gap_threshold_s]}.
- max_downlink_gap(passes, horizon_h) -> float
  the longest interval with no contact, including the horizon
  boundaries before the first pass and after the last pass (a satellite
  with no passes returns the whole horizon).
- ground_station_contact_plan(stations, altitude_km, inclination_deg,
  raan_deg, argument_of_latitude_0_deg, greenwich_0_deg, horizon_h) ->
  dict {"contacts": merged contact list (each with station_idx),
  "total_contact_s", "max_gap_s"}: run detect_passes for every station
  dict {"lat_deg", "lon_deg", "min_elevation_deg"}, sort all contacts
  by start, and merge contacts whose start is within STEP_S of the
  previous contact end; station_idx records the station of the merged
  contact.
Module constants: RE_KM, MU, OMEGA_E, STEP_S, GAP_THRESHOLD_S as
above.

Identity to test: elevation at the station zenith (station equals
sub-satellite point) is 90 degrees; the coverage inverse identity
holds against the satellite-coverage access-circle convention (a
station at the coverage central angle for mask eps observes the
satellite at elevation eps); total_contact_s equals the sum of the
pass durations; merged total contact is at least the single-station
total and never larger than the sum of the station totals;
max_downlink_gap with no passes equals the full horizon.

## Worked example

Circular LEO at 550 km, inclination 53 deg, RAAN 0, initial argument
of latitude 0, Greenwich angle 0, 24 h horizon, 30 s step; Berlin
station (52.52 N, 13.405 E), mask 10 deg:
- orbital_period_s = 5730.13 s (95.5 min).
- detect_passes returns 5 passes; total contact 2280 s (38.0 min):
  pass 1 start 6540 s end 6900 s dur 390 s max_el 23.350 deg;
  pass 2 start 12450 s end 12900 s dur 480 s max_el 66.945 deg;
  pass 3 start 18390 s end 18870 s dur 510 s max_el 82.905 deg;
  pass 4 start 24360 s end 24840 s dur 510 s max_el 62.159 deg;
  pass 5 start 30360 s end 30720 s dur 390 s max_el 20.611 deg.
- daily_contact_schedule gaps: 5520 s, 5460 s, 5460 s, 5490 s;
  max_downlink_gap = 55650 s (15.46 h, the pre-first-pass horizon
  interval).
- ground_station_contact_plan with Berlin and Madrid (40.42 N,
  3.70 W), both masks 10 deg: 6 merged contacts, total 3540 s (59
  min), max gap 49680 s (13.8 h); first merged contact starts 6270 s
  dur 660 s max_el 24.381 deg.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds, computed by running the prep
anchor script /tmp/w40spec/anchors_gs_plan.py (prep-verified by
stdlib math). The sub-satellite propagation is a simple circular
two-body ground track with no J2; the Earth rotation uses OMEGA_E.

## Validation list (contract test must include)

- orbital_period_s(550.0) = 5730.13 within 0.1; ValueError at -1 km.
- subsatellite_point at t = 0 with u0 = 0, RAAN 0, inc 53: lat 0,
  lon 0; zenith elevation check: elevation_angle(52.52, 13.405,
  52.52, 13.405, 550) = 89.99999 within 1e-3.
- Coverage inverse identity: the satellite-coverage central angle for
  mask 10 deg at 550 km is 14.9676 deg; a station at that central
  angle observes elevation 10.000 deg within 1e-3 (and mask 0 gives
  the horizon central angle 22.9961 deg -> elevation 0).
- detect_passes on the worked example returns 5 passes with the
  listed starts and durations within 1 s; max elevations within 0.01
  deg.
- daily_contact_schedule total 2280.0 within 1 s; 4 gaps with the
  listed durations within 1 s.
- max_downlink_gap = 55650.0 within 1 s; with an empty pass list
  returns 86400.0.
- ground_station_contact_plan (Berlin + Madrid) returns 6 contacts,
  total 3540.0 within 1 s, max gap 49680.0 within 1 s.
- ValueErrors: altitude < 0, inclination > 180, min_elevation < 0,
  horizon <= 0.
- Determinism: identical inputs return identical schedules (the
  propagation is a fixed-step loop with no RNG).

## Corpus fragment (eval/hit1-wave40-ground-station-pass-planning.yaml)

Query 1 (copy verbatim):
  "build the ground-station-pass-planning daily contact-window-schedule of the low-earth satellite and list the downlink-gap-analysis intervals longer than the gap threshold"
  intent: "space-systems; multi-pass ground station contact schedule and downlink gaps"
  expected_skill: "space-systems/mission-design/ground-station-pass-planning"
Query 2 (copy verbatim):
  "propagate the subsatellite ground track and detect the passes above the elevation mask to merge the multi-station contact plan and report the maximum downlink gap"
  intent: "space-systems; pass detection and multi-station contact merge"
  expected_skill: "space-systems/mission-design/ground-station-pass-planning"
Task ids: w40-ground-station-pass-planning-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must build the daily ground
station contact schedule of a low-earth satellite:" and include the
outputs in the Claim. First tag: ground-station-pass-planning.
Additional tags ONLY: contact-window-schedule, downlink-gap-analysis,
pass-detection, multi-station-contact-plan. NEVER single generic words
(ground, station, pass, contact, gap, orbit, satellite, elevation,
schedule). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): access-circle, swath, access-
time-per-pass, coverage-revisit (satellite-coverage); ccsds, downlink-
budget, data-accounting (command-data-handling); link-margin, eirp,
noise-temperature (communication-link-budget); j2, drag, propagation-
physics (orbital-perturbations, kepler-orbit-propagation).
