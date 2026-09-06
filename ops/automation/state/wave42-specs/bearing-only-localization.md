# Wave-42 leaf spec: bearing-only-localization (gnc-autonomy, navigation pack)

- Path: skills/gnc-autonomy/navigation/bearing-only-localization/
- Pack: navigation (siblings navigation-frames, inertial-navigation, dilution-of-precision, kalman-filter-design,
  gnss-pseudorange-positioning, gnss-raim-fde, ins-gnss-integrated-filter; adjacent fences in
  gnc-autonomy/estimation-filtering/extended-kalman-filter and gnc-autonomy/guidance/collision-course-guidance).
- Claim fences (quoted from the sibling frontmatter at prep; none owns a batch bearing-line fix of a stationary
  emitter):
  - extended-kalman-filter (estimation-filtering pack) TRACKS a moving target through the predict-update recursion
    over time rather than forming a static fix: its description reads "Estimate the state of a nonlinear system
    with an extended Kalman filter: linearize the nonlinear dynamics and measurement model about the current
    estimate with the state Jacobian F and the measurement Jacobian H, run the predict step x_hat = f(x_hat),
    P = F P F^T + Q, then the update step with the innovation y = z - h(x_hat), the innovation covariance
    S = H P H^T + R, the Kalman gain K = P H^T S^-1..." with Trigger "...nonlinear state estimation, range
    bearing tracking". Its worked example is a dynamic TRACKING run of a constant-velocity target x = [px, py,
    vx, vy] (position AND velocity states) over 40 sequential range/bearing measurements converging to a final
    position error of about 0.002 m: it consumes one measurement at a time inside a time recursion, needs the
    velocity states, and never forms a batch fix from bearing lines alone; its model consumes ranges together
    with bearings, where this leaf is angle-only.
  - gnss-pseudorange-positioning (this pack) locates the RECEIVER from satellite RANGES: its description reads
    "compute a GNSS receiver position fix from pseudorange measurements: given satellite positions in ECEF and
    their pseudoranges (geometric range plus receiver clock bias), solve the four-unknown navigation equations
    for x, y, z and clock bias with an iterated least-squares adjustment...". Its model rows the geometry matrix
    from unit lines of sight to the satellites plus a final column of ones for the unknown receiver clock offset;
    its measurements are absolute ranges collected at the receiver, never bearing directions measured outward
    from the observers.
  - collision-course-guidance (guidance pack) owns the constant-bearing closing-triangle geometry of an intercept
    in velocity space: its description reads "compute the collision-course intercept geometry for a
    constant-speed pursuer against a constant-velocity target: the lead angle of the pursuer velocity off the
    line of sight that closes the collision triangle..." with sin(LA) = (Vt / Vp) * sin(beta), the
    null-LOS-rotation condition Vp * sin(LA) = Vt * sin(beta). The "constant bearing" there is a property of a
    pursuit triangle (how to point the velocity to meet a moving target), not a measurement-localization
    operation on observed bearing lines.
  Whole-tree greps at prep: "bearing-only|angle-of-arrival|stansfield|aoa measurement" -> 0 hits tree-wide;
  exact re-grep over skills/: 0 files. GENUINE gnc-autonomy gap (fresh probe): no leaf forms a static batch
  position fix from N passive bearing lines measured at known observers, reports the fix covariance error
  ellipse, or states the Stansfield closed-form weighting.
- Standards id: arp4754a (reference-only, present in standards-map.yaml). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Locate a stationary emitter or target from N noisy bearing lines (angle-of-arrival directions) measured at known
observer positions: form the linearized bearing equations sin(beta_i)*(x - xi) - cos(beta_i)*(y - yi) = 0 for
every observer, solve the Stansfield closed-form weighted least-squares system A z = b for the two-dimensional
emitter fix z = (x, y) in two passes (an equal-angle first pass with weights 1/sigma_i^2, then the classical
Stansfield range-weighted second pass with W_ii = 1/(sigma_i^2 * r_i^2) at the pass-1 observer-to-fix distances
r_i), and read the fix covariance C = (A^T W A)^-1, the 1-sigma error ellipse semi-axes and orientation from its
eigenvalues, the per-bearing residual angles (measured minus the bearing predicted at the fix, wrapped to
[-180, 180) degrees) with their RMS, and the observer-geometry dilution verdict on the bearing-line set. An
optional bounded Gauss-Newton refinement iterates the same bearing lines in three dimensions when azimuth and
elevation angles are available. Produces the emitter position fix, the fix covariance and 1-sigma error ellipse,
the per-bearing residual angles and residual RMS, and the observer-geometry dilution factor. Does NOT do:
recursive estimation of a moving target's position and velocity from sequential range and bearing measurements
(extended-kalman-filter); a receiver position fix from measured ranges plus a receiver clock offset to satellites
(gnss-pseudorange-positioning); the constant-bearing closing triangle of pursuit guidance
(collision-course-guidance). Batch fix only: the emitter is stationary, the observers sit at known fixed
positions, and all bearings belong to a single epoch; localization of a moving emitter and recursive bearing
tracking are out of scope.

## Model (implement exactly)

Pure stdlib, math only, closed form (no RNG, no imports beyond math). Angles enter and leave in degrees; radians
are used inside. sigma_i is the 1-sigma bearing error of line i in degrees, converted as sigma_i_rad = sigma_i *
pi/180 (radians are dimensionless).

Defining relations (pin these exactly; every function below derives from them):
- Bearing line i: observer i at o_i = (xi, yi), measured bearing beta_i (degrees from the +x axis toward +y, in
  [0, 360)) pointing at the emitter z = (x, y):
      sin(beta_i)*(x - xi) - cos(beta_i)*(y - yi) = 0.
  Row form with the unit line normal g_i = (sin beta_i, -cos beta_i): g_i . z = g_i . o_i. Stacking the N rows
  gives A z = b with b_i = g_i . o_i; A is N x 2 and every row is a unit vector (sin^2 + cos^2 = 1), so the
  normals carry no range information.
- Stansfield closed-form weighted least squares, two passes, both the exact closed form z = (A^T W A)^-1 A^T W b
  with the 2x2 inverse of the symmetric normal matrix A^T W A:
    - pass 1 (equal-angle): W_ii = 1/sigma_i_rad^2, giving the first estimate z1 (only the relative weights
      shape the fix);
    - pass 2 (Stansfield range weights): r_i = |z1 - o_i| and W_ii = 1/(sigma_i_rad^2 * r_i^2). This is the
      classical Stansfield weighting: an angular error sigma_i on a line at range r_i displaces that line
      cross-range by about sigma_i * r_i, so the position-domain weight of the line falls as 1/r_i^2 and
      distant lines are down-weighted. The final fix is z2.
- Fix covariance: C = (A^T W A)^-1 evaluated with the pass-2 weights, a symmetric 2x2 matrix in m^2 (sigma
  enters as sigma_rad^2 in the denominator of W and r_i in m as r_i^2, so the normal matrix carries 1/m^2 and
  its inverse m^2).
- 1-sigma error ellipse: with eigenvalues lambda_max >= lambda_min > 0 of C, the semi-axes are
  a = sqrt(lambda_max) and b = sqrt(lambda_min) in m and the major-axis orientation is 0.5*atan2(2*C01, C00 -
  C11) wrapped into [-180, 180) degrees.
- Per-bearing residual angle: predicted bearing at the fix beta_hat_i = atan2(y - yi, x - xi) in degrees in
  [0, 360); the residual is delta_i = wrap180(beta_i - beta_hat_i), the signed angular leftover of line i after
  the fix.
- Observer-geometry dilution factor: with S = sum_i g_i g_i^T (the 2x2 Gram matrix of the unit normals),
  d = sqrt(lambda_max(S^-1)) = 1/sqrt(lambda_min(S)), dimensionless. d = 1 exactly for any orthogonal pair of
  lines; three lines spread around the emitter give d < 1 (the redundancy beats the orthogonal two-line
  baseline); near-parallel lines push lambda_min(S) toward 0 and d large. Verdicts: d <= 1.05 good observer
  spread, d < 2.5 moderate, d >= 2.5 poor (near-parallel bearing lines).

Functions (implement exactly):
- bearing_deg(ox, oy, tx, ty) -> float: bearing in degrees in [0, 360) from observer (ox, oy) toward (tx, ty),
  atan2(ty - oy, tx - ox) * 180/pi mod 360. ValueError if any argument is non-finite.
- wls_fix(observers, bearings_deg, sigma_deg=None) -> dict with keys x_m, y_m (final fix z2, or z1 when
  sigma_deg is None), pass1_x_m, pass1_y_m, covariance (pass-2 C in m^2 when sigma_deg is given, else the
  geometry-only matrix (A^T A)^-1), ranges_m (pass-1 distances r_i in m, None when sigma_deg is None),
  iterations (2 with sigma_deg, else 1). observers is a list of (xi, yi) in m, one entry per bearing.
  ValueErrors: fewer than 2 observers; bearings_deg or sigma_deg length mismatch with the observer list;
  non-finite observer coordinates or bearings; a sigma <= 0 or non-finite; a singular normal matrix (det <= 0,
  e.g. duplicate observer positions reporting identical bearings, or any set of all-parallel bearing lines); an
  observer within 1e-9 m of the pass-1 fix.
- error_ellipse(cov) -> dict with keys semi_major_m, semi_minor_m, orientation_deg: a and b as the square roots
  of the eigenvalues of the 2x2 covariance (lambda_max >= lambda_min >= 0), orientation of the major axis
  wrapped to [-180, 180) degrees. ValueError if an eigenvalue is negative (indefinite matrix).
- residual_angles_deg(observers, bearings_deg, x_m, y_m) -> list of per-bearing residual angles in degrees,
  each wrap180(measured - predicted at the fix). ValueErrors as in wls_fix (length and finiteness checks).
- residual_rms_deg(observers, bearings_deg, x_m, y_m) -> float: the RMS of the wrapped per-bearing residual
  angles in degrees.
- geometry_dilution_factor(observers, bearings_deg) -> float: d as defined above from the unit normals.
  ValueError if the normal Gram matrix is singular (all bearing lines parallel, det <= 0).
- refine_3d_gauss_newton(observers_xyz, azimuths_deg, elevations_deg, x0, y0, z0, max_iters=30, tol=1e-9) ->
  dict with keys x_m, y_m, z_m, iterations, residual_norm (optional three-dimensional refinement). Observer i at
  (xi, yi, zi) measures azimuth (degrees from +x toward +y) and elevation (degrees above the horizontal) to the
  emitter; unit line of sight u_i = (cos el * cos az, cos el * sin az, sin el). Residual e_i = u_i x (z - o_i)
  (zero when the emitter lies on the line) with Jacobian block [u_i]_x; the damped normal step
  (J^T J + mu I) dz = -J^T e with mu = 1e-12 * trace(J^T J)/3 is solved by 3x3 Gaussian elimination with
  partial pivoting, z <- z + dz, iterated until |dz| < tol or max_iters (bounded). ValueErrors: fewer than 3
  observers; azimuth/elevation length mismatch; max_iters < 1; non-finite observer coordinates; an elevation
  outside [-90, 90]; a singular 3x3 system; no convergence within max_iters.

Identities to test (closed form, exact):
- Noiseless exactness: wls_fix on bearings computed exactly from the emitter returns the emitter (fix error 0 to
  float precision) and every per-bearing residual at the truth is 0.
- Ellipse consistency: for the pass-2 covariance, trace(C) = a^2 + b^2 and det(C) = a^2 * b^2 (eigenvalue
  relations) within 1e-12 relative.
- Scaling: multiplying every sigma by a common factor c scales both semi-axes by c (the weights all divide by
  c^2, so C scales by c^2).
- Pass invariance on equal ranges: observers equidistant from the noiseless pass-1 fix with equal sigma give
  identical pass-1 and pass-2 fixes (the range weights are then a constant factor of the angle weights).
- Weighting pull: raising sigma_i strongly moves the fix toward the intersection of the remaining lines.
- Dilution: d = 1 exactly (within 1e-12) for an orthogonal pair of lines, and d < 1 for the three-line worked
  geometry.
- ValueErrors across the module as enumerated in the function list.
- Determinism: no RNG anywhere, run-to-run identical floats.

## Worked example

Three observers on a 1 km right triangle at (0, 0), (1000, 0) and (0, 1000) m localize an emitter near
(300, 400) m. The bearings are computed from the truth and corrupted by fixed deterministic offsets
(+0.5, -0.3, +0.2 deg) with sigma 0.5 deg per line. All values below are REAL outputs of the prep anchor
/tmp/w42spec/anchor_bearing_only_localization.py (stdlib math, closed form, deterministic):
- Geometry: observer-to-emitter ranges 500.000, 806.226 and 670.820 m; true bearings 53.130102, 150.255119 and
  296.565051 deg; measured bearings 53.630102, 149.955119 and 296.765051 deg.
- Pass-1 WLS fix (equal-angle weights 1/sigma^2): (299.178622, 405.821689) m, error 5.879347 m against the
  truth, inside the 10-50 m band expected for sub-degree noise on 1 km baselines; pass-1 ranges to the fix
  504.182, 809.841, 665.249 m.
- Final Stansfield fix (range weights 1/(sigma^2 r^2)): (299.150033, 405.988514) m, error 6.048532 m, 2
  passes: the range re-weighting moves the fix by less than 0.2 m on this geometry.
- Fix covariance C = (A^T W A)^-1 = [[16.195587, 1.677004], [1.677004, 25.693501]] m^2; 1-sigma error ellipse
  semi-major a = 5.097147 m, semi-minor b = 3.988506 m, orientation 80.275145 deg, consistent with the ~6 m
  fix error.
- Per-bearing residual angles at the final fix (measured minus the bearing predicted at the fix): +0.014509,
  +0.037982 and +0.034776 deg, residual RMS 0.030890 deg: after the fix every line is left with a small
  angular leftover, well below the 0.5 deg sigma.
- Observer-geometry dilution factor d = 0.957062 -> good observer spread: the three normals spread around the
  emitter condition the line set better than an orthogonal pair (d = 1).
- Weighting sanity: raising sigma of line 1 to 10 deg (others 0.5) pulls the fix to (300.194425, 404.784548)
  m, error 4.788497 m, toward the two-line intersection of the remaining lines.
- Optional 3-D Gauss-Newton refinement (bounded, exact azimuth and elevation): observers at z = 0, emitter
  (300, 400, 50) m, start (280, 380, 60) m -> refined (300.000000, 400.000000, 50.000000) m in 2 iterations,
  residual norm 4.303e-11, final error 0.000e+00 m.
Run your module and take the real outputs as assert targets; the anchors above are prep-verified, computed by
running the prep anchor script /tmp/w42spec/anchor_bearing_only_localization.py (prep-verified by stdlib math).

## Validation list (contract test must include)

- wls_fix on the worked noisy set with sigma 0.5 deg: pass-1 fix (299.178622, 405.821689) and final fix
  (299.150033, 405.988514) within 1e-6 m; pass-1 fix error 5.879347 m and final fix error 6.048532 m within
  1e-6; both fix errors inside the 10-50 m band.
- C entries 16.195587, 1.677004 and 25.693501 within 1e-6; error_ellipse semi-major 5.097147 m, semi-minor
  3.988506 m, orientation 80.275145 deg within 1e-6.
- Per-bearing residuals +0.014509, +0.037982, +0.034776 deg within 1e-6; residual RMS 0.030890 deg within 1e-6.
- geometry_dilution_factor = 0.957062 within 1e-6 with the good-spread verdict; the orthogonal two-line case
  returns 1.0 within 1e-12.
- Noiseless exactness: wls_fix on exact bearings returns (300, 400) with error below 1e-6 m; residual angles at
  the truth are zero within 1e-12 deg.
- Ellipse identities: trace(C) = a^2 + b^2 and det(C) = a^2 b^2 within 1e-12 relative; sigma x2 scales both
  semi-axes by exactly 2.000000 (within 1e-9).
- Weighting pull: sigma1 = 10 deg (others 0.5) gives the fix (300.194425, 404.784548) within 1e-6 m.
- refine_3d_gauss_newton worked case: refined point within 1e-6 m of (300.000000, 400.000000, 50.000000) in at
  most 30 iterations.
- ValueErrors: fewer than 2 observers; length mismatches; non-finite coordinates or bearings; sigma of 0 or
  negative; duplicate observer positions with identical bearings (singular normal matrix); an observer
  coincident with the pass-1 fix; error_ellipse on an indefinite matrix; geometry_dilution_factor on parallel
  bearing lines; refine_3d_gauss_newton with fewer than 3 observers, an elevation outside [-90, 90],
  max_iters below 1, and non-convergence within max_iters.
- Determinism: identical floats on repeated runs; no imports beyond math; no RNG.

## Corpus fragment (eval/hit1-wave42-bearing-only-localization.yaml)

Query 1 (copy verbatim):
  "locate the stationary emitter by bearing-only localization from passive angle-of-arrival bearing lines
  measured at known observer positions: stansfield weighted least squares fix, emitter fix covariance and
  error ellipse, per-bearing residual angles"
  intent: "gnc-autonomy navigation; static emitter geolocation from bearing lines by the Stansfield closed-form
  weighted least squares with the fix covariance error ellipse and per-bearing residual angles"
  expected_skill: "gnc-autonomy/navigation/bearing-only-localization"
Query 2 (copy verbatim):
  "triangulate the passive emitter with aoa measurements from spaced observers, print the two-dimensional fix,
  the 1-sigma error ellipse axes, the per-line residual angles and the observer-geometry dilution verdict"
  intent: "gnc-autonomy navigation; angle-of-arrival triangulation fix with the error ellipse, the per-line
  residual angles and the observer-geometry dilution of the bearing-line set"
  expected_skill: "gnc-autonomy/navigation/bearing-only-localization"
Task ids: w42-bearing-only-localization-1 and -2. Prep grep: none of the distinctive phrases (bearing-only,
angle-of-arrival, stansfield, aoa measurement) appears in any existing skill or hit1-corpus task: the
zero-owner re-grep over skills/ returned 0 files, and no sibling task routes on bearing-line batch fixes
(extended-kalman-filter queries route on recursive tracking wording, gnss-pseudorange-positioning on satellite
range wording, collision-course-guidance on pursuit-triangle wording), so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must locate a stationary emitter from passive angle-of-arrival bearing lines
at known observer positions:" and include the outputs in the Claim. Reference description (gate-verified:
126 words, 879 chars, no em dash):
  "Use when you must locate a stationary emitter from passive angle-of-arrival bearing lines measured at known
  observer positions. Build the linearized bearing equations sin(beta_i)*(x - xi) - cos(beta_i)*(y - yi) = 0
  per observer, solve the Stansfield closed-form weighted least squares for the two-dimensional emitter fix
  with an equal-angle first pass and a distance-weighted second pass, and read the fix covariance error
  ellipse plus the per-bearing residual angles. Produces the emitter position fix, the 1-sigma error ellipse,
  the per-bearing residuals and the observer-geometry dilution verdict. At least two observers with distinct
  bearing lines are required. Deterministic stdlib math only; bounded Gauss-Newton refinement optionally
  extends the fix to three dimensions. Does NOT do recursive tracking of a moving target or satellite range
  positioning with a clock offset."
First tag: bearing-only-localization. Additional tags ONLY: angle-of-arrival-triangulation,
stansfield-weighted-least-squares, bearing-line-intersection, emitter-fix-covariance, per-bearing-residual,
observer-geometry-dilution. NEVER single generic words (bearing, localization, tracking, emitter, triangulation,
angle, aoa, observer, fix, covariance, ellipse, residual, line, dilution). 50-150 words, <=1000 chars, no em
dash, no content-policy sweep term, action verb present.

FORBIDDEN TOKENS (belong to siblings): extended-kalman, jacobian-linearization, innovation-covariance,
kalman-gain, predict-update-recursion, range-bearing-tracking, recursive-prediction, process-noise,
state-covariance, nonlinear-state-estimation (extended-kalman-filter); pseudorange, pseudorange-positioning,
receiver-clock-bias, clock-bias, ecef-position-solution, satellite-pseudorange-residual,
snapshot-navigation-solution, iterated-least-squares-fix, toa-spherical-ranges, range-based-positioning
(gnss-pseudorange-positioning); lead-angle, constant-bearing-intercept, collision-triangle,
predicted-intercept-point, intercept-geometry, closing-speed (collision-course-guidance).
