# Wave-31 leaf spec: c3-departure-energy (space-systems, mission-design pack)

- Path: skills/space-systems/mission-design/c3-departure-energy/
- Pack: mission-design (siblings: entry-descent-landing, launch-window-analysis,
  mission-delta-v-budget, radiation-debris). launch-window-analysis computes the
  launch azimuth for an inclination target and launch geometry; it contains no
  C3, hyperbolic excess, or injection-energy content (grep receipt at prep).
  gravity-assist-swingby (orbit-mechanics) computes the FLYBY at a target body;
  it does not compute the DEPARTURE from a parking orbit or C3. This leaf fills
  the deep-space departure-energy gap.
- Standards ids: ecss (reference-only, space convention). Ledger Standard: ecss.
- Family: space-systems

## Claim

Compute the departure energy of an interplanetary mission from a circular
parking orbit around a central body: the hyperbolic excess speed corresponding
to a given C3 (characteristic energy), the injection speed on the departure
hyperbola at the parking orbit radius from the vis-viva integral, the injection
delta-v from the circular parking speed, the parking orbit period, the
declination of the outgoing asymptote from the excess velocity vector, and the
round-trip conversions between C3 and excess speed. Produces the C3, excess
speed, injection speed, injection delta-v, parking period, and asymptote
declination that gate an interplanetary launch-energy and injection burn
assessment.

Does NOT do: the gravity-assist flyby at the destination or an intermediate
body (gravity-assist-swingby owns turn angle, periapsis speed, and delta-v
gain of the flyby); launch azimuth or window geometry (launch-window-analysis);
mission delta-v budgeting across the whole trajectory (mission-delta-v-budget);
heliocentric transfer sizing (hohmann-transfer, bi-elliptic-transfer); orbit
determination. This leaf is the departure-side energy analysis only: parking
orbit to escape hyperbola.

## Model (implement exactly)

Module constants:
- MU_EARTH = 3.986004418e14 (m3/s2, default gravitational parameter, Earth).
- G0 = 9.80665 (m/s2, only used if a function converts to Earth g for
  display; keep SI unless stated).

Functions (pure stdlib):
- c3_from_excess_speed(excess_speed_m_s) -> float: C3 = excess_speed**2
  (m2/s2). ValueError if excess_speed < 0.
- excess_speed_from_c3(c3_m2_s2) -> float: v_inf = sqrt(C3).
  ValueError if C3 < 0.
- circular_speed(mu, radius) -> float: v_c = sqrt(mu / radius). ValueError if
  mu <= 0 or radius <= 0.
- injection_speed(mu, radius, excess_speed_m_s) -> float:
  v_p = sqrt(excess_speed**2 + 2*mu/radius) (vis-viva on the departure
  hyperbola at the parking radius, which is the hyperbola periapsis).
  ValueError if mu <= 0, radius <= 0, excess_speed < 0.
- injection_delta_v(mu, radius, excess_speed_m_s) -> float:
  dv = injection_speed - circular_speed. ValueError as above; the injection
  speed is always above the circular speed for a positive excess speed.
- parking_period(mu, radius) -> float: T = 2*pi*sqrt(radius**3 / mu).
  ValueError if mu <= 0 or radius <= 0.
- asymptote_declination(vx, vy, vz) -> float:
  dec = asin(vz / sqrt(vx**2 + vy**2 + vz**2)) in degrees (the declination of
  the outgoing excess velocity vector). ValueError on the zero vector.
- departure_energy_assessment(mu, parking_radius_m, excess_speed_m_s,
  vx=None, vy=None, vz=None) -> dict: convenience chain returning
  {c3_m2_s2, c3_km2_s2, excess_speed_m_s, circular_speed_m_s,
  injection_speed_m_s, injection_delta_v_m_s, parking_period_s,
  asymptote_declination_deg (None when the velocity components are not
  given)}.

## Worked example

Earth mu = 3.986004418e14 m3/s2, parking orbit radius 6578 km (300 km
circular), target hyperbolic excess 3000 m/s (C3 = 9 km2/s2).

Deterministic anchors (run your module, take the printed values as the assert
targets, then CHECK the magnitude bounds):
- C3 in 8.5-9.5 km2/s2 (exactly 9.0).
- excess speed round trip returns 3000 m/s within 1e-6.
- circular parking speed in 7700-7900 m/s (about 7784).
- injection speed in 11 200-11 700 m/s (about 11 410).
- injection delta-v in 3400-3900 m/s (about 3626).
- parking period in 5300-5600 s (about 5410, about 90 min).
- asymptote declination for v = (2000, 2000, 1000) m/s in 16-20 deg (about
  18.4; the excess speed magnitude is 3000 so the vector matches C3 9).
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: excess_speed < 0, C3 < 0, mu <= 0, radius <= 0, zero velocity
  vector in asymptote_declination.
- Round-trip: excess_speed_from_c3(c3_from_excess_speed(v)) == v within 1e-6.
- Injection delta-v is positive and equals v_p - v_c exactly.
- The injection speed from vis-viva reproduces the excess speed when the
  parking radius is very large (v_p approaches v_inf): check at radius
  1e9 m the difference is below 1 m/s... (numerically assert v_p within
  v_inf +- 50 m/s at radius 1e9).
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-c3-departure-energy.yaml)

Query 1 (copy verbatim):
  "compute the characteristic-energy c3 and the injection-delta-v to depart a circular parking-orbit onto an escape hyperbola for an interplanetary mission"
  intent: "space-systems; interplanetary departure c3 and injection burn"
  expected_skill: "space-systems/mission-design/c3-departure-energy"
Query 2 (copy verbatim):
  "determine the departure hyperbolic-excess speed and the asymptote-declination for a deep space escape-trajectory from a parking orbit"
  intent: "space-systems; departure hyperbolic excess and asymptote declination"
  expected_skill: "space-systems/mission-design/c3-departure-energy"
Task ids: w31-c3-departure-energy-1 and -2.

Forbidden tokens that belong to siblings: do NOT use launch azimuth,
inclination, launch window, gravity assist, swing-by, flyby, turn angle,
periapsis speed, delta-v gain, patched conic flyby, heliocentric transfer,
Lambert. The phrase hyperbolic excess is allowed only as the departure
quantity paired with c3 or injection tokens; never claim flyby mechanics.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the departure energy of an
interplanetary mission from a circular parking orbit:" and include the
outputs listed in the Claim. First tag: c3-departure-energy. Additional tags
only: characteristic-energy, hyperbolic-excess, injection-delta-v,
parking-orbit, asymptote-declination, escape-trajectory. NEVER single generic
words (departure, energy, launch, orbit, mission, escape). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.
