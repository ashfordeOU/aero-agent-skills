---
name: bearing-only-localization
description: "Use when you must locate a stationary emitter from passive angle-of-arrival bearing lines measured at known observer positions. Build the linearized bearing equations sin(beta_i)*(x - xi) - cos(beta_i)*(y - yi) = 0 per observer, solve the Stansfield closed-form weighted least squares for the two-dimensional emitter fix with an equal-angle first pass and a distance-weighted second pass, and read the fix covariance error ellipse plus the per-bearing residual angles. Produces the emitter position fix, the 1-sigma error ellipse, the per-bearing residuals and the observer-geometry dilution verdict. Trigger: bearing-only-localization, angle-of-arrival-triangulation, stansfield-weighted-least-squares, bearing-line-intersection, emitter-fix-covariance, per-bearing-residual, observer-geometry-dilution."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [bearing-only-localization, angle-of-arrival-triangulation, stansfield-weighted-least-squares, bearing-line-intersection, emitter-fix-covariance, per-bearing-residual, observer-geometry-dilution]
  version: 0.1.0
  author: Aero Agent Skills
---

# Bearing-Only Localization (gnc-autonomy/navigation/bearing-only-localization)

Use when you must locate a stationary emitter from passive
angle-of-arrival bearing lines measured at known observer positions:
each observer measures the direction to the emitter, never a range, and
the batch of N bearing lines is fused into one static two-dimensional
fix. This leaf implements the classical Stansfield closed-form weighted
least squares in pure Python, stdlib only, with no RNG and no imports
beyond math. It pairs with gnc-autonomy/navigation/dilution-of-precision
for geometry quality reads on navigation problems and with the
kalman-filter-design and estimation-filtering leaves for the recursive
tracking problems this leaf deliberately does not touch. The emitter is
stationary, the observers sit at known fixed positions and all bearings
belong to a single epoch: batch fix only, no time recursion.

## Domain quick reference

- Bearing line: observer i at o_i = (xi, yi) in m, measured bearing
  beta_i in degrees from the +x axis toward +y, in [0, 360), pointing at
  the emitter z = (x, y). The line equation is
  sin(beta_i)*(x - xi) - cos(beta_i)*(y - yi) = 0, written with the unit
  line normal g_i = (sin beta_i, -cos beta_i) as g_i . z = g_i . o_i.
  Stacking N rows gives A z = b; A is N x 2 and every row is a unit
  vector, so the normals carry no range information.
- Stansfield pass 1, equal-angle weights: sigma_i is the 1-sigma bearing
  error in degrees, converted to radians inside as sigma_i * pi/180.
  With W_ii = 1/sigma_i^2 the first estimate is the exact closed form
  z1 = (A^T W A)^-1 A^T W b with the 2x2 inverse of the symmetric normal
  matrix.
- Stansfield pass 2, range weights: r_i = |z1 - o_i| and
  W_ii = 1/(sigma_i^2 * r_i^2). An angular error sigma_i on a line at
  range r_i displaces the line cross-range by about sigma_i * r_i, so
  the position-domain weight of the line falls as 1/r_i^2 and distant
  lines are down-weighted. The final fix is z2.
- Fix covariance: C = (A^T W A)^-1 evaluated with the pass-2 weights, a
  symmetric 2x2 matrix in m^2.
- 1-sigma error ellipse: eigenvalues lambda_max >= lambda_min > 0 of C
  give the semi-axes a = sqrt(lambda_max) and b = sqrt(lambda_min) in m;
  the major-axis orientation is 0.5*atan2(2*C01, C00 - C11) wrapped into
  [-180, 180) degrees.
- Per-bearing residual angle: the bearing predicted at the fix is
  beta_hat_i = atan2(y - yi, x - xi) in [0, 360); the residual is
  delta_i = wrap180(beta_i - beta_hat_i), the signed angular leftover of
  line i after the fix, and the residual RMS is the RMS of those wrapped
  values.
- Observer-geometry dilution: with S = sum_i g_i g_i^T the Gram matrix
  of the unit normals, d = 1/sqrt(lambda_min(S)), dimensionless. d = 1
  exactly for any orthogonal pair of lines; three lines spread around
  the emitter give d < 1 because the redundancy beats the orthogonal
  two-line baseline; near-parallel lines push lambda_min(S) toward 0 and
  d large. Verdicts: d <= 1.05 good observer spread, d < 2.5 moderate,
  d >= 2.5 poor (near-parallel bearing lines).
- Three-dimensional refinement: observer i at (xi, yi, zi) measures
  azimuth (degrees from +x toward +y) and elevation (degrees above the
  horizontal); the unit line of sight is u_i = (cos el * cos az, cos el
  * sin az, sin el) and the residual e_i = u_i x (z - o_i) is driven to
  zero by the damped Gauss-Newton step (J^T J + mu I) dz = -J^T e with
  mu = 1e-12 * trace(J^T J)/3.
- Units: distances in m, angles in degrees at the interface, radians
  inside the module.

## Workflow

1. Assemble the bearing-line measurement set: the observer positions
   (xi, yi), the measured bearing beta_i from each observer to the
   emitter in degrees (bearing_deg computes it toward a known target)
   and the per-line 1-sigma bearing error sigma_i in degrees. At least
   two observers with distinct bearing lines are required.
2. Form the linearized bearing equations and solve the equal-angle
   first pass: per observer sin(beta_i)*(x - xi) - cos(beta_i)*(y - yi)
   = 0, stacked as A z = b, weighted with W_ii = 1/sigma_i^2 and solved
   by wls_fix pass 1, giving the first estimate z1 (pass1_x_m,
   pass1_y_m). A singular normal matrix (parallel or coincident bearing
   lines) raises ValueError here.
3. Run the Stansfield distance-weighted second pass: pass-1 distances
   r_i = |z1 - o_i|, weights W_ii = 1/(sigma_i^2 * r_i^2), final fix z2
   (x_m, y_m) and the fix covariance C = (A^T W A)^-1 in m^2, all
   returned by the same wls_fix call with sigma_deg given (ranges_m,
   iterations 2). Without sigma_deg the solver returns the
   geometry-only unweighted fix with iterations 1.
4. Read the 1-sigma error ellipse of the fix covariance with
   error_ellipse: semi-major a, semi-minor b and the major-axis
   orientation in degrees, wrapped to [-180, 180).
5. Compute the per-bearing residual angles, measured minus the bearing
   predicted at the fix and wrapped to [-180, 180) degrees, with
   residual_angles_deg, and their RMS with residual_rms_deg. Residuals
   near zero with an RMS well below sigma mean the line set is
   consistent with the fix.
6. Assess the observer geometry with geometry_dilution_factor and read
   the observer-geometry dilution verdict from dilution_verdict (good
   observer spread, moderate, or poor near-parallel lines). Reject or
   flag the fix when the verdict is poor.
7. Optionally refine the fix in three dimensions with
   refine_3d_gauss_newton when azimuth and elevation angles are
   available at each of at least three observers: start from the 2-D fix
   lifted to z = 0 and iterate the damped normal step to the 3-D
   emitter position.
8. Close out with the deterministic contract test
   scripts/test_bearing_only_localization.py, which pins every worked
   output above and the ValueError rejections.

## Worked example

Three observers on a 1 km right triangle at (0, 0), (1000, 0) and
(0, 1000) m localize an emitter near (300, 400) m. The measured
bearings are the exact observer-to-emitter bearings corrupted by fixed
deterministic offsets (+0.5, -0.3, +0.2 deg), sigma 0.5 deg per line.
Module outputs (stdlib math, closed form, deterministic):

- Geometry: observer-to-emitter ranges 500.000, 806.226 and 670.820 m;
  true bearings 53.130102, 150.255119 and 296.565051 deg; measured
  bearings 53.630102, 149.955119 and 296.765051 deg.
- Pass-1 fix (equal-angle weights 1/sigma^2): (299.178622, 405.821689)
  m, error 5.879347 m against the truth, with pass-1 ranges to the fix
  504.182, 809.841 and 665.249 m.
- Final Stansfield fix (range weights 1/(sigma^2 * r^2)):
  (299.150033, 405.988514) m, error 6.048532 m, 2 passes: the range
  re-weighting moves the fix by less than 0.2 m on this spread
  geometry.
- Fix covariance C = [[16.195587, 1.677004], [1.677004, 25.693501]]
  m^2; the 1-sigma error ellipse has semi-major 5.097147 m, semi-minor
  3.988506 m and orientation 80.275145 deg, consistent with the about
  6 m fix error.
- Per-bearing residual angles at the final fix (measured minus the
  bearing predicted at the fix): +0.014509, +0.037982 and +0.034776
  deg, residual RMS 0.030890 deg: after the fix every line keeps a
  small angular leftover, well below the 0.5 deg sigma.
- Observer-geometry dilution factor d = 0.957062, verdict good observer
  spread: the three normals spread around the emitter condition the
  line set better than an orthogonal pair (d = 1).
- Weighting sanity: raising sigma of line 1 to 10 deg with the others
  at 0.5 pulls the fix to (300.194425, 404.784548) m, error 4.788497
  m, toward the two-line intersection of the remaining lines.
- Optional 3-D Gauss-Newton refinement (bounded, exact azimuth and
  elevation): observers at z = 0, emitter (300, 400, 50) m, start
  (280, 380, 60) m refines to (300.000000, 400.000000, 50.000000) m in
  2 iterations with residual norm 1.2e-13.

## Verification

- Confirm wls_fix on the noisy worked set returns pass-1
  (299.178622, 405.821689) and final (299.150033, 405.988514) within
  1e-6 m, with both fix errors inside the 0-50 m expectation for
  sub-degree noise on 1 km baselines.
- Confirm the covariance entries 16.195587, 1.677004 and 25.693501
  m^2 and the ellipse semi-axes 5.097147 m, 3.988506 m at orientation
  80.275145 deg.
- Confirm the per-bearing residuals +0.014509, +0.037982 and +0.034776
  deg with residual RMS 0.030890 deg, and the dilution factor 0.957062
  with the good observer spread verdict.
- Confirm the closed-form identities: noiseless exactness (fix returns
  the emitter, residuals zero), trace(C) = a^2 + b^2 and
  det(C) = a^2 * b^2 within 1e-12 relative, sigma x 2 scaling both
  semi-axes by 2, pass invariance on equal observer ranges, the
  weighting pull of a high-sigma line, d = 1 for an orthogonal pair and
  d < 1 for the three-line set.
- Confirm ValueError rejection of non-physical inputs: fewer than two
  observers, bearing or sigma count mismatches, non-finite coordinates,
  bearings or sigma, sigma <= 0, a singular normal matrix (parallel or
  coincident bearing lines), an observer within 1e-9 m of the pass-1
  fix, an indefinite covariance in error_ellipse, a singular Gram
  matrix in geometry_dilution_factor, and in refine_3d_gauss_newton
  fewer than three observers, an elevation outside [-90, 90],
  max_iters below 1 and non-convergence within max_iters.
- Run the contract test offline: python3
  scripts/test_bearing_only_localization.py (35 tests, deterministic).

## Related leaves

- gnc-autonomy/navigation/gnss-pseudorange-positioning: receiver fixes
  from satellite ranges with a clock offset, the range-based neighbor
  of this angle-only fix.
- gnc-autonomy/navigation/dilution-of-precision: geometry quality reads
  (DOP values) for navigation measurement sets.
- gnc-autonomy/navigation/navigation-frames: ECEF/NED/WGS-84 frame
  conventions for observer and emitter coordinates.
- gnc-autonomy/estimation-filtering/extended-kalman-filter: recursive
  state estimation of a moving target from sequential range and bearing
  measurements over time, the tracking alternative to this batch
  angle-only fix.
- gnc-autonomy/guidance/collision-course-guidance: the constant-bearing
  closing triangle of pursuit guidance, which is a velocity-pointing
  geometry and not a bearing-line localization operation.

## Pitfalls

- Treating the dilution factor as an accuracy number: d describes
  observer geometry only; the fix accuracy also scales with sigma and
  range through the covariance C = (A^T W A)^-1. Read d for the verdict
  and C for the error ellipse.
- Fusing nearly parallel bearing lines: near-parallel lines push the
  normal Gram matrix toward singular, d >= 2.5 (poor spread) and the
  fix covariance blows up along the weak direction, so the ellipse
  semi-major axis flags the unobservable axis long before the fix looks
  wrong.
- Feeding rounded bearings: the measured bearings enter as the fixed
  values at full precision; rounding them to a few decimals before the
  solve shifts the fix by about range times the rounding angle, which
  can exceed the covariance ellipse size on 1 km baselines.
- Expecting the range-weighted second pass to move the fix a lot: on
  well-spread geometry with comparable observer ranges the Stansfield
  re-weighting moves the fix by less than 0.2 m (worked example), while
  on geometry with one distant line it is exactly the correction that
  matters.
- Extending this leaf to moving emitters: the fix is batch-only for a
  stationary emitter at a single epoch; recursive bearing tracking over
  time belongs to the estimation-filtering leaves.
- Reading the ellipse as a hard guarantee: the covariance is the
  first-order linearized spread of the fix, consistent with the
  residual RMS but not a statement about systematic bias.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_bearing_only_localization.py

The test covers bearing_deg and the wrap contract, the worked noisy set
through both Stansfield passes (fix, fix error, pass-1 ranges,
covariance entries), the 1-sigma error ellipse with the trace and
determinant identities, sigma scaling, pass invariance on equal ranges,
the per-bearing residual angles and RMS, the weighting pull of a
high-sigma line, the dilution factor and verdict thresholds, noiseless
exactness, the 3-D Gauss-Newton refinement worked case, the ValueError
rejections across the module, and run-to-run determinism. All numeric
asserts are order-safe tolerances (assertAlmostEqual delta or
math.isclose), never exact float equality on computed sums.

## Compliance

- Standards referenced, not reproduced: ARP4754A (Guidelines for
  Development of Civil Aircraft and Systems) frames the system
  development context; the bearing-line and Stansfield relations above
  are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
