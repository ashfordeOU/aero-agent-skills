# Wave-29 leaf spec: plane-change-maneuver (space-systems, orbit-mechanics pack)

- Path: skills/space-systems/orbit-mechanics/plane-change-maneuver/
- Pack: orbit-mechanics (existing siblings: clohessy-wiltshire,
  conjunction-assessment, eclipse-time, gravity-assist-swingby,
  ground-track-repeat, hohmann-transfer, keplerian-elements,
  lambert-transfer, low-thrust-spiral, orbital-decay,
  orbital-perturbations, satellite-coverage, sun-synchronous-
  inclination)
- Standards ids: ecss (reference-only; the orbit-mechanics pack
  convention). Ledger Standard: ecss.
- Family: space-systems

## Claim

Compute the delta-v of an orbital plane-change maneuver and compare
the pure inclination-change burn against the combined burn performed
together with an orbit transfer: evaluate the circular-orbit speed at
the maneuver radius, the pure plane-change delta-v 2 v sin(di/2), the
speed on an elliptic transfer orbit at the maneuver point, and the
combined-burn delta-v from the law of cosines when the plane change
and the transfer are done in one burn at the apogee. Produces the
orbit speeds, the pure and combined delta-v values, and the
maneuver-selection verdict that gate the orbit maneuver plan.

Does NOT do: size a coplanar Hohmann transfer between two circular
orbits (hohmann-transfer owns the two-impulse transfer ellipse,
speeds, and burn impulses for coplanar cases); build the whole mission
delta-v budget with margin and propellant conversion
(mission-delta-v-budget owns the summed budget); analyze low-thrust
spiral plane changes over many revolutions (low-thrust-spiral owns
the continuous low-thrust case); compute launch-window plane changes
(launch-window-analysis owns the launch geometry). This leaf computes
the impulsive plane-change burn and its combined-transfer variant.

## Model (implement exactly)

Module constants:
- MU_EARTH = 398600.4418 (km3/s2).
- G0 unused here.

Functions (pure stdlib, floats):
- circular_orbit_speed(mu, radius_km) -> float:
  v = sqrt(mu / radius_km). ValueError on radius_km <= 0 or mu <= 0.
- plane_change_dv(speed, inclination_change_deg) -> float:
  dv = 2 * speed * sin(pi/180 * di / 2). ValueError if di not in
  (-180, 180].
- transfer_speed_at_radius(mu, radius_km, semimajor_axis_km) ->
  float: v = sqrt(mu * (2/radius_km - 1/semimajor_axis_km)) (vis-viva).
  Valid at any point of the ellipse (periapsis OR apoapsis); require
  the point to lie on the ellipse: radius_km > 0, semimajor_axis_km >
  0, and 2*semimajor_axis_km > radius_km (an ellipse point satisfies
  r < 2a). ValueError otherwise.
- combined_burn_dv(v_before, v_after, inclination_change_deg) ->
  float: dv = sqrt(v_before^2 + v_after^2 - 2 v_before v_after
  cos(pi/180 * di)). ValueError on negative speeds or di outside
  (-180, 180].
- maneuver_verdict(pure_dv_total, combined_dv) -> str:
  "combined-cheaper" if combined_dv < pure_dv_total - 1e-9 else
  "pure-cheaper-or-equal".
- analyze_plane_change(mu, radius_km, inclination_change_deg,
  transfer_semimajor_axis_km=None, target_radius_km=None) -> dict:
  convenience chain for the two standard cases.
  (a) Pure-only: when transfer_semimajor_axis_km is None: the maneuver
  is a pure plane change on the circular orbit at radius_km:
  v = circular_orbit_speed(mu, radius_km); dv_pure =
  plane_change_dv(v, di); returns {speed_km_s: v,
  pure_plane_change_dv_km_s: dv_pure, combined_dv_km_s: None,
  separate_total_km_s: None, verdict: "pure-only"}.
  (b) Combined: when transfer_semimajor_axis_km and target_radius_km
  are given (a Hohmann-like transfer from radius_km to
  target_radius_km with the plane change at the apoapsis end, i.e. at
  target_radius_km): v_before = transfer_speed_at_radius(mu,
  target_radius_km, transfer_semimajor_axis_km) (the transfer speed at
  its apoapsis); v_after = circular_orbit_speed(mu,
  target_radius_km); dv_pure_at_circular = plane_change_dv(v_after,
  di); dv_combined = combined_burn_dv(v_before, v_after, di);
  separate_total = (v_after - v_before) + dv_pure_at_circular;
  returns {speed_at_maneuver_km_s: v_before,
  circular_speed_km_s: v_after, pure_plane_change_dv_km_s:
  dv_pure_at_circular, combined_dv_km_s: dv_combined,
  separate_total_km_s: separate_total, verdict:
  maneuver_verdict(separate_total, dv_combined)}. ValueErrors
  propagate.

## Worked example

Case A (pure plane change): 300 km circular orbit (radius 6678 km),
28.5 deg inclination change.
Deterministic anchors:
- circular_orbit_speed(MU_EARTH, 6678) = 7.7258 km/s (within 1e-3).
- plane_change_dv(7.7258, 28.5) = 2 * 7.7258 * sin(14.25 deg) =
  3.803 km/s (within 0.001).
- GEO: circular_orbit_speed(MU_EARTH, 42164) = 3.0747 km/s (within
  1e-3); plane_change_dv(3.0747, 28.5) = 1.514 km/s (within 0.001).

Case B (combined with transfer): GTO from 300 km to GEO, plane change
28.5 deg done at apogee together with the circularization burn.
Transfer semimajor axis a = (6678 + 42164)/2 = 24421 km.
Deterministic anchors:
- transfer_speed_at_radius(MU_EARTH, 42164, 24421) = 1.6057 km/s
  (within 1e-3; the classic GTO apogee speed).
- circular_orbit_speed(MU_EARTH, 42164) = 3.0747 km/s.
- combined_burn_dv(1.6057, 3.0747, 28.5) = 1.832 km/s (within 0.001;
  the classic ~1.83 km/s combined GTO-to-GEO plane change).
- separate_total = (3.0747 - 1.6057) + 1.514 = 2.983 km/s (within
  0.01).
- maneuver_verdict(2.983, 1.832) = "combined-cheaper" (saves ~1.15
  km/s).
- ValueErrors: radius 0, sma 0, 2*sma <= radius (point off the
  ellipse), di outside (-180, 180]. Boundary sanity: di = 0 returns
  zero delta-v, di = 90 pure plane change at circular speed gives
  dv = v*sqrt(2) = 10.926 km/s at 300 km (within 0.001).

Keep at least 18 test methods: circular speed anchors LEO and GEO,
pure plane change anchors, vis-viva apogee speed anchor, combined
burn anchor (the 1.832 case), separate total, verdict, di = 0 zero
delta-v, di = 90 case sanity (dv = v sqrt(2) for a pure 90 deg change
at circular speed: 7.7258*sqrt(2) = 10.926 km/s within 0.001),
ValueErrors. Runs offline in under 20 s.

## Corpus tasks (ids w29-plane-change-maneuver-1/2)

Distinctive tokens: plane change maneuver, inclination change delta-v,
combined burn, orbital plane change, 2 v sin half inclination,
apsidal plane change at apogee. Avoid: Hohmann transfer ellipse, two
impulse coplanar transfer (hohmann-transfer); mission delta-v budget,
margin allocation, propellant mass conversion (mission-delta-v-
budget); low-thrust spiral plane change (low-thrust-spiral); launch
window geometry (launch-window-analysis).

1. "compute the delta-v for a 28.5 degree orbital plane change at 300
   km circular altitude and compare it with the combined burn at GTO
   apogee"
2. "is it cheaper to do the GEO inclination change together with the
   circularization burn at apogee, and what does the combined burn
   delta-v come to?"

## SKILL body notes

Pair with hohmann-transfer (the coplanar transfer this leaf extends
with an inclination change), mission-delta-v-budget (where the
maneuver contribution is summed), launch-window-analysis (the launch
side of plane changes), sun-synchronous-inclination (inclination set
by sun-sync geometry). State the boundary: hohmann-transfer explicitly
treats coplanar orbits and defers the plane change here; the mission
budget leaf sums contributions, this leaf computes the maneuver. ecss
is reference-only. Mirror the orbit-mechanics pack SKILL body style (SI
units, stdlib only, deterministic offline).
