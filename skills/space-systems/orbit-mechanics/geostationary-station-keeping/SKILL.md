---
name: geostationary-station-keeping
description: "Use when you must compute geostationary station keeping quantities for a GEO satellite: the geosynchronous radius and orbital speed from the sidereal day, the annual north-south delta-v from the inclination drift with the two-burn-per-year model, the per-burn delta-v, the burn time from thrust and spacecraft mass, the annual propellant from the specific impulse, the east-west deadband drift-cycle period and maneuver cadence from the longitude acceleration and box half-width, and the uncontrolled drift time to the inclination tolerance. Produces the radius, speed, annual and per-burn delta-v, burn time, annual propellant, east-west cycle period and cadence, and the uncontrolled-drift verdict that gate a GEO propulsion budget. Trigger: geostationary station keeping, geosynchronous orbit radius, north-south station keeping, inclination drift control, east-west deadband cycle, longitude acceleration, station keeping delta-v, geo propellant budget, uncontrolled drift time."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: orbit-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: orbit-mechanics
  tags: [geostationary-station-keeping, north-south-station-keeping, inclination-drift-control, east-west-deadband-cycle, geo-propellant-budget, longitude-acceleration]
  version: 0.1.0
  author: AeroSkills
---

# Geostationary Station Keeping (space-systems/orbit-mechanics/geostationary-station-keeping)

Use when the task is building the geostationary station-keeping plan
quantities for a GEO satellite at the conceptual level: turning the
sidereal day into the geosynchronous radius and speed, the inclination
drift amplitude into the annual north-south delta-v with the
two-burn-per-year model, the thrust and mass into burn time, the
specific impulse into the annual propellant, and the longitude
acceleration with the east-west deadband box into the drift-cycle
period and maneuver cadence. This leaf implements the standard GEO
station-keeping model (two north-south burns per year, box-limited
east-west cycling) in pure Python, stdlib only. It pairs with
space-systems/mission-design/mission-delta-v-budget, which sums the
delta-v budget and takes the annual station-keeping contribution as an
input line item, and with space-systems/orbit-mechanics/orbital-
perturbations for the perturbation environment that drives the drift.
It does NOT do total mission delta-v summation, three-body equilibrium
orbit maintenance, constellation phasing, or one-shot plane rotation;
those belong to sibling leaves.

## Domain quick reference

- Geosynchronous radius from the sidereal day: r = (MU * (T_sid / (2
  * pi))**2) ** (1/3), with MU = 398600.4418 km3/s2 and the sidereal
  day T_sid = 86164.0905 s, giving 42164.2 km. The solar day of 86400 s
  must not be used here.
- Geosynchronous orbital speed: v = 1000 * sqrt(MU / r) with the radius
  in km, giving 3074.7 m/s (3.075 km/s).
- Annual north-south delta-v: the inclination drifts about one degree
  per year under lunisolar gravity, and two burns per year hold it in a
  band of half-width drift/2, so dv_annual = 2 * v * sin(radians(drift)
  / 2), 45.61 m/s at 0.85 deg/yr; the per-burn value is exactly half,
  22.81 m/s.
- Burn time at constant thrust: t = m * delta_v / F, valid while the
  burn is short against the orbital period.
- Annual propellant by the rocket equation: m_prop = m * (1 - exp(-
  delta_v / (Isp * g0))) over the year, g0 = 9.80665 m/s2; for small
  delta_v this approaches m * delta_v / (Isp * g0).
- East-west deadband cycling: inside a longitude box of half-width h
  (deg) under a residual longitude acceleration a (deg/day2) the
  satellite drifts box edge to box edge in T = 2 * sqrt(2 * h / a)
  days, and the correction cadence is 365.25 / T maneuvers per year,
  14.9 days and 24.5 per year at h = 0.05 deg, a = 0.0018 deg/day2.
- Uncontrolled drift: with station keeping off the inclination grows
  linearly, t = tolerance / drift, 0.1176 years at 0.1 deg tolerance
  and 0.85 deg/yr.
- Units are explicit per function: radius in km, speeds and delta-v in
  m/s, burn time in s, periods in days, drift time in years, mass in
  kg.
- ECSS frames the space systems and orbit environment context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Get the orbit geometry: geosynchronous_radius() and geo_speed()
   from the sidereal-day constants.
2. Fix the annual inclination drift amplitude in deg/yr from the
   lunisolar environment and compute ns_annual_delta_v; confirm the
   band model with ns_per_burn_delta_v, exactly half.
3. Turn the per-burn delta-v into a maneuver: burn_time with the
   thruster thrust and spacecraft mass.
4. Size the annual propellant: annual_propellant with the specific
   impulse over the annual delta-v.
5. Set the east-west control box: ew_cycle_period from the box
   half-width and the residual longitude acceleration, then
   ew_maneuvers_per_year for the cadence.
6. For the no-keeping case, run uncontrolled_drift_years to find how
   long the inclination tolerance holds before control is required.
7. Feed the annual delta-v and propellant as the station-keeping line
   item into a mission-delta-v-budget summation.
8. Confirm the deterministic checks with the contract test
   scripts/test_geostationary_station_keeping.py.

## Worked example

A GEO satellite at 2000 kg wet mass with a 400 N apogee-class thruster
at Isp = 280 s, an inclination drift of 0.85 deg/yr, and an east-west
control box of 0.1 deg full width (0.05 deg half width) under a
residual longitude acceleration of 0.0018 deg/day2.

- Geosynchronous radius: geosynchronous_radius() = 42164.17 km, the
  42164.2 km anchor; geo_speed() = 3074.66 m/s, the 3074.7 m/s anchor.
- Annual north-south delta-v at 0.85 deg/yr:
  ns_annual_delta_v(0.85) = 45.61 m/s; per burn,
  ns_per_burn_delta_v(0.85) = 22.81 m/s, and the identity dv_annual =
  2 * dv_per_burn holds exactly.
- Burn time per N/S burn: burn_time(22.81, 400.0, 2000.0) = 114.05 s,
  the 114.0 s anchor within 0.1 s.
- Annual propellant: annual_propellant(45.61, 280.0, 2000.0) =
  32.95 kg, the 33.0 kg anchor within 0.2 kg.
- East-west cycle: ew_cycle_period(0.05, 0.0018) = 14.907 days and
  ew_maneuvers_per_year(0.05, 0.0018) = 24.50 per year; the product
  period * cadence = 365.25 days exactly.
- Uncontrolled drift: uncontrolled_drift_years(0.1, 0.85) = 0.1176
  years, so a 0.1 deg inclination tolerance is spent in about 43 days
  with station keeping off, which motivates the two-burn-per-year N/S
  control.

## Verification

- Confirm geosynchronous_radius() returns 42164.2 km and geo_speed()
  3074.7 m/s within tolerance, and that r * v**2 = MU * 1e6 closes the
  circular-orbit identity.
- Confirm ns_annual_delta_v(0.85) returns 45.61 m/s within 0.05 and
  that the annual value equals twice the per-burn value at any drift.
- Confirm ew_cycle_period(0.05, 0.0018) returns 14.907 days within
  0.05 and the cadence 24.5 per year, with period times cadence equal
  to 365.25.
- Confirm the small-delta-v linearization of annual_propellant and the
  sqrt scaling of the deadband cycle with box half-width and
  acceleration.
- Confirm every non-physical input raises ValueError: negative
  inclination drift, thrust or mass or Isp at zero or below, negative
  delta-v, box half width or acceleration at zero or below, tolerance
  at zero or below, drift rate at zero or below.
- Confirm repeated calls are bit-identical (pure deterministic
  functions, no RNG).
- Run the contract test offline: python3
  scripts/test_geostationary_station_keeping.py (33 tests,
  deterministic).

## Related leaves

- space-systems/mission-design/mission-delta-v-budget: the mission
  delta-v summation that consumes the annual station-keeping delta-v
  from this leaf as an input line item.
- space-systems/orbit-mechanics/orbital-perturbations: the
  perturbation environment (lunisolar gravity, longitude acceleration)
  that drives the drift this leaf controls.
- space-systems/orbit-mechanics/three-body-libration: equilibrium
  orbit maintenance in the circular restricted three-body problem, a
  different regime from the GEO ring.
- space-systems/orbit-mechanics/walker-delta-constellation:
  constellation design and phasing, not per-satellite orbit keeping.
- space-systems/orbit-mechanics/plane-change-maneuver: a one-shot
  plane rotation between circular orbits, not the annual
  inclination-drift control loop.

## Pitfalls

- Quoting the annual N/S delta-v as the per-burn value: the year is
  controlled with two burns, so the maneuver and its burn time run on
  22.81 m/s, not 45.61 m/s, and the burn time anchor is 114 s, not
  228 s.
- Sizing the radius with the solar day: the geosynchronous period is
  the sidereal day, 86164.0905 s, not 86400 s; the solar-day radius
  comes out about 70 km high.
- Mixing kilometers and meters: the speed is 3074.7 m/s or 3.075 km/s;
  feeding 3074.7 into an equation expecting km/s inflates the delta-v
  by a factor of 1000.
- Treating the E/W drift cycle as linear: under a constant residual
  longitude acceleration the longitude follows a parabola in the box,
  so the cycle period carries the sqrt(2 * h / a) dependence; a naive
  linear crossing estimate shortens the period and inflates the
  cadence.
- Reading the east-west box as full width: the cycle period uses the
  half width; a 0.1 deg box is 0.05 deg half width, which is why the
  worked example cycles in 14.9 days and not 21.1 days.
- Ignoring the uncontrolled-drift verdict: 0.1 deg of inclination
  tolerance is consumed in 0.1176 years (about 43 days) without N/S
  control, so a GEO payload that needs tight pointing cannot ride the
  natural drift.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_geostationary_station_keeping.py

The test covers the geosynchronous radius and speed anchors (42164.2
km, 3074.7 m/s) and the circular-orbit identity, the annual and
per-burn N/S delta-v anchors at 0.85 deg/yr with the annual-equals-
twice-per-burn identity and the small-drift linear approximation, the
burn-time anchor and thrust scaling, the annual propellant anchor with
the small-delta-v rocket-equation linearization, the east-west cycle
and cadence anchors with the period-times-cadence identity of 365.25
and the sqrt scaling laws, the uncontrolled-drift anchor and its
scaling, ValueError rejection of every non-physical input, and
determinism of repeated calls.

## Compliance

- Standards referenced, not reproduced: ECSS is the family spine for
  space systems and the orbit environment context (ecss.nl/standards);
  the station-keeping relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
