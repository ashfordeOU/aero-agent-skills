# Wave-27 leaf spec: radio-navigation-aids (avionics, flight-management pack)

- Path: skills/avionics/flight-management/radio-navigation-aids/
- Pack: flight-management (existing siblings: flight-planning,
  lateral-navigation, vertical-navigation, performance-computation)
- Standards ids: do-178c  (Ledger Standard: do-178c)
- Family: avionics

## Claim

Compute the geometric quantities of conventional radio navigation
aids for an aircraft navigation solution: derive the VOR radial and
the bearing from the aircraft to the station from the planar station
and aircraft coordinates, compute the DME slant range from the ground
distance and the aircraft altitude, compute the ILS localizer
deviation angle from the lateral offset and the distance to the
threshold, and compute the ILS glideslope deviation from the height
above the threshold and the distance to the threshold against the
nominal glideslope angle. Produces the VOR bearing and radial, the
slant range, and the localizer and glideslope deviation angles that
gate radio-navigation geometry checks.

Does NOT do: compute the FMS great-circle track, cross-track error,
or turn anticipation between waypoints (lateral-navigation owns the
FMS lateral guidance); plan the FMS vertical profile (vertical-
navigation); or compute position fixes from GNSS pseudoranges
(gnc-autonomy navigation gnss-pseudorange-positioning). This leaf is
the receiver-level geometry of VOR/DME/ILS navaids only.

## Model (implement exactly)

Coordinate convention: local tangent plane with x east (m), y north
(m), z up (m). The VOR/DME station is at the origin; the aircraft is
at (x_ac, y_ac, z_ac = altitude_m).

Functions:
- bearing_deg(x_ac, y_ac) -> float: bearing from the station to the
  aircraft measured clockwise from north: deg(atan2(x, y)) normalized
  to [0, 360).
- radial_deg(bearing_deg) -> float: (bearing + 180) mod 360 (the
  radial FROM the station is the reciprocal bearing).
- dme_slant_range_m(x_ac, y_ac, altitude_m) -> float:
  sqrt(x^2 + y^2 + altitude^2).
- loc_deviation_deg(lateral_offset_m, distance_to_threshold_m) ->
  float: deg(atan(lateral_offset / distance)) (positive offset to the
  right of the approach course gives a positive deviation, i.e. the
  aircraft is right of the localizer centerline).
- gs_deviation_deg(height_agl_m, distance_to_threshold_m,
  gs_angle_deg=3.0) -> float:
  actual = deg(atan(height / distance)); deviation = actual -
  gs_angle (positive when above the glidepath).
- analyze(...) -> dict with all quantities.

ValueError on: altitude < 0, distance_to_threshold <= 0,
gs_angle_deg <= 0 or >= 90, lateral offset and distance both zero for
the localizer case (distance <= 0 handled above).

## Worked example

Aircraft 10 km east and 17.32 km north of the VOR/DME, at 1000 m.
- bearing = atan2(10000, 17320) = 30.0 deg (assert within 0.01),
- radial = 210.0 deg (assert within 0.01),
- slant range = sqrt(1e8 + 2.999e8 + 1e6) = sqrt(4.009e8) =
  20022.5 m? compute: 10000^2 = 1e8, 17320^2 = 2.999e8, sum 3.999e8,
  +1e6 = 4.009e8; sqrt = 20022.5 m (assert within 1.0).
- Localizer: aircraft 100 m right of the centerline at 5000 m to the
  threshold: dev = atan(100/5000) = 1.1458 deg (assert within 0.001).
- Glideslope: 3 deg nominal, height 300 m, distance 5724 m:
  actual = atan(300/5724) = 3.0000 deg; dev = 0.0002 deg (assert
  within 0.001); at 400 m the deviation is +1.0 deg (assert within
  0.01: atan(400/5724)=4.000 deg minus 3 = 0.9974 deg).
- ValueErrors: altitude -1, distance 0, gs angle 0.
Keep at least 15 test methods.

## Corpus tasks (ids w27-radio-navigation-aids-1/2)

Distinctive tokens: VOR radial, DME slant range, ILS localizer
deviation, glideslope deviation, radio navigation geometry, bearing to
the navaid station, approach course offset. Avoid: great-circle
track, cross-track error, fly-by waypoint (lateral-navigation); VNAV
top of descent (vertical-navigation); pseudorange position fix
(gnss-pseudorange-positioning).

1. "compute the VOR radial and the DME slant range for the aircraft
   10 km east and 17.3 km north of the station at 1000 m altitude"
2. "find the ILS localizer deviation for the 100 m lateral offset at
   5 km to the threshold and the glideslope deviation for the 300 m
   height at 5724 m against the 3 degree path"

## SKILL body notes

Pair with lateral-navigation (FMS downstream consumer of the nav
geometry), flight-planning (route context), and the gnc navigation
leaves (position fix boundary). Planar local-tangent geometry is a
documented simplification for short ranges; great-circle corrections
are out of scope. DO-178C referenced (software in the nav receivers)
not reproduced.
