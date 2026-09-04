# Wave-37 leaf spec: geostationary-station-keeping (space-systems, orbit-mechanics pack)

- Path: skills/space-systems/orbit-mechanics/geostationary-station-keeping/
- Pack: orbit-mechanics. Closest siblings: mission-delta-v-budget (sums
  the delta-v budget and takes the station-keeping contribution as an
  INPUT line item - it does not compute the maneuvers), three-body-
  libration (CR3BP libration POINT station-keeping sites - not the GEO
  orbit), orbital-perturbations (perturbation environment context),
  walker-delta-constellation (constellation design, not per-satellite
  orbit keeping), plane-change-maneuver (single impulsive plane change,
  not the annual inclination-drift control). Whole-tree grep: no leaf
  computes GEO station-keeping maneuvers; "station keeping" appears only
  as a budget line or context. ZERO owners. GENUINE gap (fresh probe).
- Standards id: ecss (reference-only; family spine, orbit/space
  environment context). Ledger Standard: ecss.
- Family: space-systems

## Claim

Compute the geostationary station-keeping plan quantities for a GEO
satellite: the geosynchronous radius and orbital speed from the sidereal
day, the annual north-south delta-v from the inclination drift amplitude
with the two-burn-per-year model, the per-burn delta-v, the burn time
from the thruster thrust and spacecraft mass, the propellant mass from
the specific impulse over the annual delta-v, the east-west deadband
drift-cycle period and maneuver cadence from the longitude acceleration
magnitude and the box half-width, and the uncontrolled drift time until
the inclination tolerance is exceeded. Produces the radius, speed,
annual and per-burn delta-v, burn time, annual propellant, E/W cycle
period and cadence, and the uncontrolled-drift verdict that gate a GEO
propulsion budget. Does NOT do: total mission delta-v summation
(mission-delta-v-budget); libration-point orbit maintenance (three-body-
libration); constellation phasing (walker-delta-constellation); single
impulsive plane change (plane-change-maneuver).

## Model (implement exactly)

Module constants: MU = 398600.4418 (km3/s2), SIDEREAL_DAY = 86164.0905
(s), G0 = 9.80665 (m/s2), PI as math.pi. Conversions inside functions
are explicit (km vs m for speed).

Functions (pure stdlib):
- geosynchronous_radius() -> km = (MU * (SIDEREAL_DAY / (2*pi))**2) **
  (1/3).
- geo_speed() -> m/s = 1000 * sqrt(MU / geosynchronous_radius()).
- ns_annual_delta_v(inc_drift_deg_per_year) -> m/s =
  2 * geo_speed() * sin(radians(inc_drift_deg_per_year) / 2). ValueError:
  drift < 0.
- ns_per_burn_delta_v(inc_drift_deg_per_year) -> m/s = half the annual
  value (two burns per year).
- burn_time(delta_v_m_s, thrust_N, mass_kg) -> s = mass_kg *
  delta_v_m_s / thrust_N. ValueErrors: thrust <= 0, mass <= 0,
  delta_v < 0.
- annual_propellant(delta_v_m_s, isp_s, mass_kg) -> kg = mass_kg *
  (1 - exp(-delta_v_m_s / (isp_s * G0))). ValueErrors: isp <= 0,
  mass <= 0, delta_v < 0.
- ew_cycle_period(box_half_width_deg, lon_accel_deg_day2) -> days =
  2 * sqrt(2 * box_half_width_deg / lon_accel_deg_day2). ValueErrors:
  half width <= 0, accel <= 0.
- ew_maneuvers_per_year(box_half_width_deg, lon_accel_deg_day2) ->
  float = 365.25 / ew_cycle_period(...).
- uncontrolled_drift_years(inc_tolerance_deg, inc_drift_deg_per_year) ->
  years = tolerance / drift. ValueErrors: tolerance <= 0, drift <= 0.

Identity to test: ns_annual_delta_v == 2 * ns_per_burn_delta_v;
ew_cycle_period * ew_maneuvers_per_year == 365.25; annual_propellant at
tiny delta_v ~ mass * delta_v / (isp * G0).

## Worked example

Run your module and take the real outputs as assert targets; bounds
independently verified at prep:
- geosynchronous_radius() = 42164.2 km; geo_speed() = 3074.7 m/s.
- ns_annual_delta_v(0.85) = 45.61 m/s; per-burn = 22.81 m/s.
- burn_time(22.81, 400.0, 2000.0) = 114.0 s.
- annual_propellant(45.61, 280.0, 2000.0) = 33.0 kg (within 0.2).
- ew_cycle_period(0.05, 0.0018) = 14.907 days; maneuvers per year =
  24.5.
- uncontrolled_drift_years(0.1, 0.85) = 0.1176 years.

## Validation list (contract test must include)

- ValueError: negative inclination drift; thrust/mass/isp <= 0; box half
  width <= 0; accel <= 0; tolerance <= 0.
- Radius and speed anchors 42164.2 km / 3074.7 m/s within tolerance.
- Annual N/S anchor 45.61 m/s at 0.85 deg/yr within 0.05.
- E/W period anchor 14.907 days at (0.05, 0.0018) within 0.05; cadence
  24.5 per year.
- Identity: annual = 2 * per-burn; period * cadence == 365.25.
- Determinism; float outputs as documented.

## Corpus fragment (eval/hit1-wave37-geostationary-station-keeping.yaml)

Query 1 (copy verbatim):
  "size the geostationary-station-keeping north south delta-v and propellant from the inclination drift for a geo satellite"
  intent: "space-systems; GEO north-south station keeping delta-v and propellant"
  expected_skill: "space-systems/orbit-mechanics/geostationary-station-keeping"
Query 2 (copy verbatim):
  "compute the east-west deadband drift cycle and maneuver cadence for geostationary station keeping in the longitude box"
  intent: "space-systems; GEO east-west deadband cycle and cadence"
  expected_skill: "space-systems/orbit-mechanics/geostationary-station-keeping"
Task ids: w37-geostationary-station-keeping-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute geostationary station
keeping quantities:" and include the outputs in the Claim. First tag:
geostationary-station-keeping. Additional tags ONLY: north-south-
station-keeping, inclination-drift-control, east-west-deadband-cycle,
geo-propellant-budget, longitude-acceleration. NEVER single generic
words (station, keeping, delta-v, orbit, satellite, maneuver, box).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): delta-v budget rollup, propellant
mass budget margins (mission-delta-v-budget); libration point, halo,
L1/L2 (three-body-libration); constellation plane slot (walker-delta-
constellation); single impulsive plane change (plane-change-maneuver).
