# Wave-27 leaf spec: gravity-assist-swingby (space-systems, orbit-mechanics pack)

- Path: skills/space-systems/orbit-mechanics/gravity-assist-swingby/
- Pack: orbit-mechanics (existing siblings: hohmann-transfer,
  lambert-transfer, low-thrust-spiral, clohessy-wiltshire, eclipse-time,
  orbital-perturbations, satellite-coverage, keplerian-elements,
  sun-synchronous-inclination, orbital-decay, ground-track-repeat)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: space-systems

## Claim

Analyze a gravity-assist (swing-by) maneuver of a spacecraft past a
planet or moon: from the arrival hyperbolic excess speed, the flyby
periapsis radius, and the body gravitational parameter, compute the
periapsis speed with the vis-viva energy integral, the flyby turn
angle, the outgoing excess velocity magnitude (equal to the incoming
for a single flyby), the heliocentric velocity change imparted by the
swing-by for a given incoming direction, and the closest-approach
geometry check against the body radius plus a minimum altitude.
Produces the periapsis speed, turn angle, delta-v gain, and the
feasibility verdict that gate interplanetary trajectory design.

Does NOT do: solve the two-position Lambert transfer (lambert-transfer
owns the p-iteration boundary-value solution); compute Hohmann or
low-thrust transfer budgets (hohmann-transfer, low-thrust-spiral);
propagate relative motion (clohessy-wiltshire); or size launch windows
or radiation/debris environment (mission-design pack leaves). This
leaf is the single hyperbolic flyby only, not a full patched-conic
sequence.

## Model (implement exactly)

Constants:
- MU_EARTH = 3.986004418e14 (used as default when mu_body is not
  given).

Inputs:
- v_inf_ms (float, hyperbolic excess speed relative to the body),
- rp_m (float, periapsis radius from the body center),
- mu_body (float, default MU_EARTH),
- body_radius_m (float, optional, for the minimum-altitude check),
- min_alt_m (float, default 200e3, for the feasibility check).

Functions:
- periapsis_speed(v_inf_ms, rp_m, mu_body) -> float:
  vp = sqrt(v_inf^2 + 2*mu/rp).
- turn_angle_rad(v_inf_ms, rp_m, mu_body) -> float:
  delta = 2*asin(1 / (1 + rp*v_inf^2/mu)).
- dv_gain(v_inf_ms, delta_rad) -> float: 2*v_inf*sin(delta/2) (the
  magnitude of the heliocentric velocity-vector change when the excess
  speed is unchanged and only its direction rotates by delta).
- outgoing_direction_deg(incoming_deg, delta_rad, turn_sign) ->
  float: incoming + turn_sign * delta (turn_sign +1 or -1 selects the
  inside/outside geometry).
- feasibility(rp_m, body_radius_m, min_alt_m) -> dict
  {altitude_m = rp - body_radius, min_alt_m, pass (bool)}; pass when
  altitude >= min_alt and rp >= body_radius.
- analyze(v_inf_ms, rp_m, incoming_dir_deg, mu_body=...,
  body_radius_m=..., min_alt_m=...) -> dict {vp, delta_rad,
  delta_deg, dv, outgoing_deg, altitude_m, pass}.

ValueError on: v_inf < 0, rp <= 0, mu_body <= 0, and when the flyby is
inside the body (rp < body_radius) if body_radius is given.

## Worked example

Earth swing-by: v_inf 3.0 km/s (3000 m/s), rp 7000 km, body radius
6371 km, mu Earth.
- vp = sqrt(9e6 + 2*3.986004418e14/7e6) = sqrt(9e6 + 1.13886e8) =
  sqrt(1.22886e8) = 11085.4 m/s (assert within 0.5),
- 1 + rp*v_inf^2/mu = 1 + 7e6*9e6/3.986004418e14 = 1 + 0.15806 =
  1.15806; delta = 2*asin(1/1.15806) = 2*asin(0.86351) =
  2*59.714 deg = 119.43 deg (assert within 0.01 deg),
- dv = 2*3000*sin(59.714 deg) = 6000*0.86351 = 5181.1 m/s (assert
  within 1.0),
- altitude = 7000-6371 = 629 km >= 200 km -> pass.
- incoming 0 deg, turn +119.43 -> outgoing 119.43 deg (assert).
Second case: v_inf 5 km/s, rp 7000 km -> vp = sqrt(25e6 + 1.13886e8)
= sqrt(1.38886e8) = 11785.0 m/s; delta = 2*asin(1/(1 + 7e6*25e6/
3.986e14)) = 2*asin(1/1.43905) = 2*asin(0.69490) = 2*44.02 = 88.04
deg; dv = 2*5000*sin(44.02) = 10000*0.6949 = 6949 m/s (assert).
ValueErrors: v_inf -1, rp 0, rp < body radius when provided (e.g.,
rp 6000 km with body 6371 km).
Keep at least 16 test methods.

## Corpus tasks (ids w27-gravity-assist-swingby-1/2)

Distinctive tokens: gravity assist, swing-by, hyperbolic excess
velocity, turn angle, periapsis speed, delta-v gain, patched conic
flyby, close approach altitude. Avoid: lambert problem transfer time
(lambert-transfer), hohmann burn impulses (hohmann-transfer), low
thrust Edelbaum (low-thrust-spiral).

1. "compute the gravity assist swing-by at earth: 3 km/s hyperbolic
   excess speed at 7000 km periapsis radius, find the turn angle and
   the delta-v gain"
2. "check the mars flyby feasibility: excess speed 2.5 km/s at 3800 km
   periapsis against the 3390 km body radius with the 200 km minimum
   altitude, and give the outgoing direction for the inside pass"

## SKILL body notes

Pair with lambert-transfer and hohmann-transfer (transfer method
alternatives), orbital-perturbations (flyby effects context), and
mission-design launch-window-analysis (interplanetary geometry). The
single-flyby model assumes the excess speed magnitude is unchanged;
powered and multi-body sequences are out of scope. ECSS referenced
(mission analysis context) not reproduced.
