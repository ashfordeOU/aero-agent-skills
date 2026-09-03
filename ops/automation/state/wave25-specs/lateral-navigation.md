# Wave-25 leaf spec: lateral-navigation (avionics, flight-management pack)

- Path: skills/avionics/flight-management/lateral-navigation/
- Pack: flight-management (existing siblings: flight-planning,
  performance-computation, vertical-navigation)
- Standards ids: do-178c  (Ledger Standard: do-178c)
- Family: avionics

## Claim

Compute the lateral navigation (LNAV) guidance quantities of a flight
management system between and along the flight plan legs: compute the
great-circle track angle and distance from the current position to the
next waypoint, determine the cross-track error to the active leg, derive
the track angle error and the required intercept course, compute the
turn anticipation distance and the fly-by versus fly-over transition
point at the waypoint, and judge the along-track position against the
leg. Produces the track, distance, cross-track error, intercept
guidance, and the turn transition point that gate LNAV guidance.

Does NOT do: building or validating the whole flight plan with the
vertical profile (flight-planning owns the plan leg distances and
constraint check), the vertical navigation descent path (vertical-
navigation owns VNAV top of descent and flight path angle), or the
performance prediction (performance-computation). This leaf is the
lateral track guidance math, the lateral counterpart of vertical-
navigation.

## Model (implement exactly)

Use the spherical earth great-circle formulas (module constant Earth
radius R = 6371000 m), inputs in radians internally:

- Initial great-circle track from point A to point B (standard
  formula): track = atan2(sin(dLon)*cos(latB),
  cos(latA)*sin(latB) - sin(latA)*cos(latB)*cos(dLon)) normalized to
  0..2pi. Distance: d = R * acos(sin(latA)*sin(latB) +
  cos(latA)*cos(latB)*cos(dLon)) (guard the acos argument to [-1,1]).
- Cross-track error to the leg from A to B at position P: compute the
  angular distance d_AP and the track AP and track AB; xtk = asin(
  sin(d_AP/R) * sin(track_AB - track_AP)) with the sign convention that
  positive is right of the track; return meters.
- Along-track distance: atd = acos(cos(d_AP/R) / cos(xtk_angle)) * R
  from A (or project with the spherical law of cosines); return the
  distance to go to B as max(0, leg_length - atd).
- Track angle error: tke = wrap(track_AB - track_current) to
  [-pi, pi].
- Intercept: intercept_angle = wrap(desired_track - track_current);
  required bank or the intercept heading = desired_track + sign *
  intercept_limit (simplified: provide the heading to capture the track
  with a fixed intercept angle module constant, default 30 deg).
- Turn anticipation: at a fly-by waypoint, the aircraft begins the turn
  before the waypoint; anticipation distance d_ant = R_turn *
  tan(delta_track/2) where R_turn = V^2/(g*tan(bank)) (bank module
  constant default 25 deg, V input), delta_track the track change at the
  waypoint; fly-over waypoints have d_ant = 0 (turn starts at the
  waypoint).
- Transition point: distance to the waypoint equal to d_ant -> begin
  turn; output the fly-by or fly-over classification.
Functions:
- great_circle_track(lat_a, lon_a, lat_b, lon_b) -> rad
- great_circle_distance(lat_a, lon_a, lat_b, lon_b) -> m
- cross_track_error(lat_a, lon_a, lat_b, lon_b, lat_p, lon_p) -> (m,
  sign)
- along_track_distance(...) -> m
- track_angle_error(track_current, track_desired) -> rad
- intercept_heading(track_desired, track_current) -> rad
- turn_anticipation_distance(v, delta_track, bank_deg) -> m
- waypoint_transition(...) -> dict (fly_by/fly_over, d_ant, turn start)
- lnav_guidance(...) -> dict summary
ValueError on: latitudes outside [-pi/2, pi/2], non-finite inputs,
v <= 0, identical positions (guard the acos domain).

## Worked example

Great-circle: from (50N, 0E) to (50N, 10E): track ~90 deg, distance ~
10 deg * cos(50) * R ~ 713 km (compute exactly with the module and
assert). Cross-track: at (51N, 5E) the xtk sign and magnitude; turn
anticipation at 90 m/s with a 30 deg track change at 25 deg bank.
Assert the module's real numbers.

## Corpus tasks (ids w25-lateral-navigation-1/2)

Distinctive tokens: lateral navigation, LNAV, cross-track error, track
angle error, great-circle track, turn anticipation, fly-by waypoint,
fly-over waypoint, intercept heading, FMS lateral guidance. Avoid:
top of descent, descent gradient, vertical profile constraint, flight
plan leg distance totals, fuel planning (owned by vertical-navigation /
flight-planning).

1. "compute the LNAV cross-track error and track angle error for the
   active flight plan leg and the intercept heading to recapture the
   track"
2. "find the fly-by turn anticipation distance at the waypoint for the
   lateral navigation guidance at the given speed and bank angle"

## SKILL body notes

Pair with vertical-navigation (lateral counterpart), flight-planning
(leg source), performance-computation. Worked example uses module
constants and real outputs. Compliance: DO-178C FMS function development
referenced by name; standard great-circle formulas, no reproduced text.
