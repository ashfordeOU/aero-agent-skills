# Wave-27 leaf spec: gnss-pseudorange-positioning (gnc-autonomy, navigation pack)

- Path: skills/gnc-autonomy/navigation/gnss-pseudorange-positioning/
- Pack: navigation (existing siblings: navigation-frames,
  kalman-filter-design, dilution-of-precision, inertial-navigation)
- Standards ids: arp4754a  (Ledger Standard: arp4754a)
- Family: gnc-autonomy

## Claim

Compute a GNSS receiver position fix from pseudorange measurements:
given the satellite positions in ECEF and their pseudoranges (range
plus the receiver clock bias), solve the four-unknown navigation
equations (x, y, z, clock bias) with an iterated linearized least-
squares adjustment, update the satellite elevation and the geometric
range each iteration, and report the converged receiver ECEF position,
the clock bias, the residuals, and the post-fit position error from
the geometry matrix. Produces the position fix, the clock bias, the
residual RMS, and the fix-quality flags that gate navigation
processing.

Does NOT do: compute the dilution-of-precision geometry factors or the
1-sigma position error from a user-equivalent range error for
satellite subset selection (dilution-of-precision owns GDOP/PDOP and
geometry); design a Kalman filter that fuses the fix over time with
process noise (kalman-filter-design owns recursive filtering); or
rotate between navigation frames (navigation-frames). This leaf is the
single-epoch snapshot position solution from pseudoranges.

## Model (implement exactly)

ECEF coordinates, WGS-84-style Earth radius constants only for the
optional geodetic conversion (documented approximate):
- use a spherical Earth radius R_E = 6378137.0 m for the lat/lon
  conversion output (flag it approximate; WGS-84 ellipsoid out of
  scope).

Inputs:
- satellites: list of dict {x, y, z (ECEF m), pseudorange (m),
  elevation_rad optional},
- x0, y0, z0, b0 optional initial guess (default zeros).

Functions:
- geometric_range(recv, sat) -> float.
- predicted_pseudorange(recv, sat, clock_bias) -> range + bias.
- residual(recv, sat, clock_bias) -> measured - predicted.
- geometry_matrix(satellites, recv) -> H (n x 4): rows
  [-(sx-rx)/range, -(sy-ry)/range, -(sz-rz)/range, 1].
- solve_iterated(satellites, iters=8, tol=1e-6) -> dict:
  initialize x,y,z,b; each iteration build H and residuals, solve the
  normal equations (H^T H)^{-1} H^T dr with a 4x4 Gaussian
  elimination or explicit inverse (implement a small 4x4 solver),
  update the state; stop when the correction norm < tol; return
  {x, y, z, clock_bias, residuals (list), residual_rms, iterations,
  converged (bool)}. Require n >= 4 satellites.
- position_error_estimate(satellites, fix) -> dict: post-fit
  geometry: gdop = sqrt(trace(inv(H^T H))), uere_equiv =
  residual_rms, pos_1sigma = uere_equiv * pdop (pdop =
  sqrt(trace of the first 3 diagonal of inv(H^T H))).
  (Companion to the dilution-of-precision leaf; here the DOP comes
  from the post-fit geometry and is labeled post-fit.)
- to_geodetic_approx(x, y, z) -> dict {lat_rad, lon_rad, alt_m} using
  the spherical Earth approximation.

ValueError on: fewer than 4 satellites, missing sat keys, non-finite
pseudoranges, iters < 1.

## Worked example

Four satellites in a tetrahedral-like configuration around an origin
receiver near the ECEF origin (documented test constellation):
- sat1 (0, 0, 20000 km)  -> pseudorange 20000000 + 100 (bias 100 m),
- sat2 (20000 km, 0, 0)  -> 20000000 + 100,
- sat3 (0, 20000 km, 0)  -> 20000000 + 100,
- sat4 (14142 km, 14142 km, 14142 km) -> sqrt(3)*14142000? compute the
  true range 24494897.42 + 100.
  Receiver true position (0,0,0), clock bias 100 m.
- Run the leaf: assert the converged position is within 0.5 m of
  (0,0,0) in each axis (the linearized fix converges in a few
  iterations; assert the exact module outputs deterministically),
  clock_bias within 0.5 m of 100.0, residual RMS below 0.5 m,
  iterations <= 8, converged True.
- Perturbation case: add a 3 m error to one pseudorange; assert the
  fix shifts by an amount consistent with the geometry (record the
  exact module values in the test header) and residual_rms > 0.
- ValueErrors: 3 satellites, iters 0.
Keep at least 15 test methods.

## Corpus tasks (ids w27-gnss-pseudorange-positioning-1/2)

Distinctive tokens: pseudorange positioning, GNSS position fix,
receiver clock bias, iterated least squares fix, ECEF position
solution, satellite pseudorange residual, snapshot navigation
solution. Avoid: gdop pdop elevation mask satellite selection
(dilution-of-precision); kalman gain covariance process noise
(kalman-filter-design); inertial navigation drift (inertial-navigation).

1. "compute the GNSS receiver position fix and clock bias from the
   four satellite pseudoranges with the iterated least squares
   adjustment in ECEF coordinates"
2. "solve the snapshot pseudorange navigation equations for the
   receiver position and report the post-fit residuals and the
   residual RMS against the satellite geometry"

## SKILL body notes

Pair with dilution-of-precision (geometry quality), kalman-filter-design
(time-domain fusion), and navigation-frames (coordinate conventions).
Document that the leaf is a single-epoch snapshot solution (no
smoothing), requires at least four satellites, and treats the Earth as
spherical for the geodetic conversion only. Standards referenced
(ARP4754A development context) not reproduced.
