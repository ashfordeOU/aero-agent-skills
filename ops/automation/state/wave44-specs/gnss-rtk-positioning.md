# Wave-44 leaf spec: gnss-rtk-positioning (gnc-autonomy,
# navigation pack)

- Path: skills/gnc-autonomy/navigation/gnss-rtk-positioning/
- Pack: navigation (present siblings bearing-only-localization,
  dilution-of-precision, gnss-carrier-smoothing, gnss-doppler-velocity-
  positioning, gnss-pseudorange-positioning, gnss-raim-fde, inertial-
  navigation, ins-gnss-integrated-filter, kalman-filter-design,
  navigation-frames, tightly-coupled-ins-gnss; adjacent fences in
  gnc-autonomy/space/orbit-determination and gnc-autonomy/space/
  orbit-dynamics).
- Provenance: wave-44 leaf-plan entry 11 (GNC 49, probe task-7 rank 3
  fresh find, wave44-leaf-plan.md lines 109-117): "rover fix relative to
  a fixed base from double-difference carrier-phase - single then double
  differences across satellite pairs and epochs, float baseline +
  ambiguity by LS normal equations, integer rounding candidate sets +
  ratio test, fixed baseline/ENU offset; gnss-carrier-smoothing smooths
  CODE with carrier increments (explicitly not differencing), doppler
  leaf is velocity single-receiver, pseudorange leaf is code absolute;
  rtca-do-229". The three in-pack GNSS leaves own the single-receiver
  code/doppler steps only; the differential-precision step above them
  (two receivers, common-view carrier phase, baseline estimation with
  integer ambiguity resolution) has no owner anywhere in the tree
  (verified below).
- Claim fences (quoted from the sibling frontmatter and body at prep,
  none owns the differential carrier-phase baseline fix):
  - gnss-carrier-smoothing (this pack) OWNS the smoothing side of the
    carrier observable only: its description reads "smooth GNSS code
    pseudoranges with carrier-phase delta ranges before positioning: run
    the first-order Hatch recursion at a smoothing time constant, carry
    the smoothed range between epochs on the precise carrier increments,
    and monitor the code-carrier ionospheric divergence" and its body
    states "Continuous carrier phase between epochs is assumed; cycle-
    slip repair and integer ambiguity resolution are out of scope" and
    "the recursion needs an unbroken carrier arc between epochs; cycle-
    slip repair and integer ambiguity resolution are out of scope for
    this leaf". It smooths CODE pseudoranges with carrier-phase delta
    ranges in one receiver; it does NOT difference two receivers, does
    NOT estimate a baseline and explicitly excludes integer ambiguity
    resolution. The new leaf never runs a Hatch recursion, never
    produces a smoothed range and never monitors code-carrier
    divergence; it differences raw carrier phases between a base and a
    rover receiver.
  - gnss-doppler-velocity-positioning (this pack) OWNS the single-
    receiver snapshot velocity step: its description reads "estimate
    the 3-D velocity of a GNSS receiver and its receiver clock drift at
    a single epoch from carrier-phase delta-range-rate (doppler)
    observables: propagate each satellite ECEF position and velocity
    from the broadcast-ephemeris Kepler elements ...". The new leaf
    estimates no velocity, no range rate and no clock drift; it
    consumes static carrier-phase accumulations (not delta-range-rates)
    and performs no Kepler propagation: the satellite ECEF positions at
    each epoch are supplied inputs.
  - gnss-pseudorange-positioning (this pack) OWNS the single-receiver
    absolute code fix: its description reads "compute a GNSS receiver
    position fix from pseudorange measurements: given satellite
    positions in ECEF and their pseudoranges (geometric range plus
    receiver clock bias), solve the four-unknown navigation equations
    for x, y, z and clock bias" and its body states "The leaf is a
    snapshot solution: no smoothing, no dynamics model". The new leaf
    is differential and carrier-phase based: the position it reports is
    the rover baseline relative to a FIXED BASE from common-view
    double-difference carrier phase, not an absolute code fix; no
    pseudorange is solved and no receiver clock bias is estimated (the
    receiver clock terms cancel in the double differences).
  - gnss-raim-fde (this pack) OWNS integrity on the single-receiver
    measurement set; the new leaf produces no detection verdict, no
    protection level and no satellite exclusion.
  Whole-tree greps at prep: "rtk|integer-ambiguity|double-difference|
  carrier-phase-differential" = 1 file in skills/, gnss-carrier-
  smoothing/SKILL.md, with exactly the two quoted "integer ambiguity
  resolution are out of scope" lines and NO owner; "differential|rtk"
  = 0 hits in skills/gnc-autonomy and no GNSS differential content
  anywhere in the tree (the other "differential" hits are cabin
  pressure, differential-equation and radiation contexts). In eval/
  hit1-corpus.yaml the same rtk tokens return ZERO hits; "integer"
  appears only in the orbit "integer repeat cycle" task; the carrier
  tasks (w42-gnss-carrier-smoothing-1/-2) route on Hatch smoothing and
  divergence monitors, the doppler tasks (w43-gnss-doppler-velocity-
  positioning-1/-2, w38-doppler-shift-1/-2) route on range-rate and
  s-band comm frequency content. GENUINE gnc-autonomy gap (fresh probe,
  GO 2): no leaf computes a differential carrier-phase baseline fix
  with integer ambiguity resolution relative to a fixed base.
- Standards id: rtca-do-229 (reference-only, present in standards-map.yaml
  at line 303, gated: true, RTCA MOPS proprietary; name + paraphrase only,
  no MOPS algorithm or table text). Ledger Standard: rtca-do-229.
- Family: gnc-autonomy

## Claim

Compute the ECEF position of a GNSS rover relative to a fixed base
station (the baseline vector b = rover - base) from common-view L1
carrier-phase observables recorded at both receivers over several
epochs of an observation arc. For each epoch and each tracked satellite
with a supplied ECEF position, form the single difference between the
receivers (rover phase minus base phase, per satellite, in cycles), then
form the double differences across satellite pairs (non-reference
satellite minus reference satellite), scaled to metres by the L1
wavelength. The double-difference phase of pair j at epoch t obeys
y_j(t) = -(u_j(t) - u_0(t)) dot b - lambda*N_j + eps_j(t), where u is
the unit line of sight from the base to the satellite, lambda is the L1
wavelength and N_j is the integer double-difference ambiguity of the
pair, constant across the arc when no cycle slip occurs. Stack the
double differences over the satellite pairs and the epochs and solve the
least-squares normal equations with geometry rows [-du_j(t), -e_j] over
the unknown state (b_x, b_y, b_z, A_1 ... A_m) with A_j = lambda*N_j in
metres: the FLOAT baseline and FLOAT ambiguities, with the per-axis and
per-ambiguity 1-sigma precision from sigma0 times the square root of the
inverse-normal-matrix diagonal. Resolve the integer ambiguities by
enumerating rounding candidate sets (integer vectors within a Chebyshev
radius of the rounded float ambiguity vector), evaluating each candidate
by the quadratic form (n - n_float)^T Q^-1 (n - n_float) on the float
ambiguity covariance, and applying a ratio test (second-best over best,
threshold 3.0) on the float covariance; the winning candidate set is
then imposed and the measurements are re-solved for the FIXED baseline
with per-axis 1-sigma precision, and the fixed baseline is reported as
the ENU offset at the base position. Deterministic offline: linearized
double-difference model at the base position, direct normal-equation
solves, candidate enumeration without random search. Does NOT do:
carrier smoothing, the Hatch recursion, smoothed ranges or code-carrier
divergence monitoring (gnss-carrier-smoothing; this leaf differences raw
carrier phases between two receivers and never smooths code); doppler/
range-rate observables, receiver velocity or clock-drift estimation,
Kepler/broadcast-ephemeris propagation of satellite states
(gnss-doppler-velocity-positioning; the satellite ECEF positions at each
epoch are supplied inputs); code pseudorange positioning, absolute
single-point fixes or receiver clock-bias estimation (gnss-pseudorange-
positioning; the receiver clock difference cancels in the double
difference); RAIM fault detection, protection levels or exclusion
(gnss-raim-fde); cycle-slip detection and repair (the arc is
slip-free by assumption); ionospheric and tropospheric double-difference
residuals (a short baseline cancels them to first order in the model);
multipath, antenna phase-center offsets, precise ephemeris products or
second-frequency (wide-lane) combinations. The single-pass linear model
at the base leaves an O(|b|^2/rho) curvature residual of about 1e-5 m on
the 23 m demo baseline (real anchor), absorbed by the least squares as
the model floor.

## Model (implement exactly)

Pure stdlib, math only, deterministic (no RNG anywhere, not even seeded).
Module constants: C_LIGHT = 299792458.0 m/s, F_L1 = 1575.42e6 Hz,
LAMBDA_L1 = C_LIGHT/F_L1 = 0.190293672798 m/cycle (the L1 wavelength,
exact by construction), R_EARTH = 6378137.0 m (spherical-Earth demo
context for the ENU conversion only), MIN_SATELLITES = 5 (4 non-
reference pairs), MIN_EPOCHS = 2, PIVOT_MIN = 1e-300 (singularity floor
of the Gaussian elimination), DEFAULT_SEARCH_RADIUS = 2 cycles,
DEFAULT_RATIO_MIN = 3.0.
The module performs NO orbit propagation: every epoch carries the
satellite ECEF positions as supplied inputs (as a receiver would receive
them from a broadcast or precise ephemeris service), so there is no
Kepler machinery, no GMST rotation and no ephemeris window in this leaf.
A small Gaussian-elimination solver with partial pivoting and an inverse
helper are private internals; the module exposes 9 functions.

Defining relations (pin these exactly; every function below derives from
them):
- Phase streams: the raw L1 carrier phase in cycles at receiver i
  (base r or rover u) for satellite j at epoch t is
  phi_i^j(t) = rho_i^j(t)/lambda + f*dt_i(t) - f*dts^j - N_i^j, with
  rho the geometric range, dt_i the receiver clock offset (s), dts^j the
  broadcast satellite clock offset (s) and N_i^j a per-receiver per-
  satellite integer tracking constant. Nothing in the module needs the
  absolute phase level: the double differences use only differences of
  the printed phase streams.
- Single difference (cycles): SD^j(t) = phi_u^j(t) - phi_r^j(t). The
  satellite clock term f*dts^j cancels exactly; the receiver clock
  difference f*(dt_u(t) - dt_r(t)) remains, common to all satellites at
  the epoch.
- Double difference (cycles) of pair j against reference satellite 0:
  DD^j(t) = SD^j(t) - SD^0(t). The receiver clock difference cancels
  exactly; in metres y_j(t) = lambda*DD^j(t) =
  (rho_u^j - rho_r^j - rho_u^0 + rho_r^0)(t) - lambda*(N^j - N^0), where
  the true integer double-difference ambiguity is N_j = N^j - N^0.
- Linearized geometry: for a baseline b short against the slant range,
  (rho_u^j - rho_r^j)(t) = -u_j(t) dot b to first order, so
  y_j(t) = -(u_j(t) - u_0(t)) dot b - lambda*N_j + eps_j(t), with u the
  unit line of sight from the BASE position to the satellite. The
  linearization curvature O(|b|^2/rho) is about 1e-5 m on the worked
  example and is the float model floor (real anchor).
- Float system: unknowns x = (b_x, b_y, b_z, A_1 ... A_m) with A_j =
  lambda*N_j in metres; measurement row for pair j at epoch t is
  [-du_x, -du_y, -du_z, 0 ... -1 ... 0] with du = u_j - u_0 and the -1
  on the j-th ambiguity column; y = H x + eps. Normal equations
  (H^T H) x = H^T y solved once (the model is linear at the base); no
  iteration. m = S - 1 pairs, measurements m*T, unknowns 3 + m,
  redundancy m*T - (3 + m) = 7 on the worked example.
- Precision: residual r_i = y_i - (H x)_i; sigma0 =
  sqrt(sum(r_i^2)/(m*T - (3 + m))); per-axis 1-sigma
  sigma0*sqrt(diag_ii((H^T H)^-1)) for the three baseline axes (m) and
  sigma0*sqrt(diag_jj(...))/LAMBDA_L1 for the ambiguities (cycles).
- Integer resolution: with n_float the float ambiguities in cycles,
  round to n_round and enumerate every integer vector n within Chebyshev
  distance SEARCH_RADIUS of n_round (5^5 = 3125 candidates on the worked
  example). Score each candidate by the float-covariance quadratic form
  q(n) = (n - n_float)^T Q^-1 (n - n_float) with Q the m x m float
  ambiguity covariance block in cycles^2 (from the inverse normal
  matrix, scaled by 1/LAMBDA_L1^2). ratio = q(second-best)/q(best);
  resolved True when ratio >= RATIO_MIN. Residual-domain confirmation:
  the fixed residual RSS of a candidate, min_b ||y + lambda*n + du*b||^2
  over the baseline only, ranks the candidates the same way (real
  anchor).
- Fixed solution: impose the winning integer set n and re-solve the
  baseline-only least squares over the shifted measurements
  y_j(t) + lambda*n_j with rows -du_j(t); per-axis 1-sigma from
  sigma0*sqrt(diag((G^T G)^-1)) with sigma0 over m*T - 3 degrees of
  freedom.
- ENU conversion: spherical base latitude/longitude from the base ECEF
  position, local basis e = (-sin lon, cos lon, 0), n = (-sin lat cos
  lon, -sin lat sin lon, cos lat), u = (cos lat cos lon, cos lat sin
  lon, sin lat); the ENU offset is (b dot e, b dot n, b dot u). At the
  demo base (lat 0, lon 0) this is exactly (b_y, b_z, b_x).
- Time-differenced arm: the per-pair epoch difference
  y_j(t2) - y_j(t1) = -(du_j(t2) - du_j(t1)) dot b + (eps_j(t2) -
  eps_j(t1)) carries NO ambiguity term (the integers are constant across
  a slip-free arc), giving the ambiguity-free baseline-only geometry
  solve used as the coarse precursor read (real anchor: integer residue
  below 1.3e-6 m, the curvature floor).

Functions:
- line_of_sight(sat_pos, recv_pos) -> (u, rho) tuple. Unit vector from
  recv_pos to sat_pos and the range in m. ValueError if the range is
  below 1 m (coincident) or the input is non-finite.
- single_difference(rover_phase, base_phase) -> float. Rover minus base
  carrier phase in cycles for one satellite at one epoch. ValueError on
  non-finite input.
- form_double_differences(sds, reference_index = 0) -> list of floats.
  Double differences in cycles of every non-reference satellite against
  the reference satellite (sd[j] - sd[reference]). ValueErrors: fewer
  than 2 entries; reference index out of range; non-finite entries.
- time_differenced_dd(dd_cycles_later, dd_cycles_earlier) -> list of
  floats. Per-pair cycle difference later minus earlier (ambiguity-free
  in a slip-free arc). ValueErrors: length mismatch; fewer than 1 pair;
  non-finite input.
- solve_float_baseline(epochs, base_position, reference_index = 0) ->
  dict. epochs is a list (length >= MIN_EPOCHS) of per-epoch dicts with
  keys "positions" (list of S ECEF 3-tuples, m, same satellite order in
  every epoch), "rover_phase" and "base_phase" (lists of S raw L1 phases
  in cycles). Forms the single differences, then the double differences,
  scales by LAMBDA_L1 and solves the float normal equations above.
  Returns baseline_float_ecef (3-tuple m), ambiguities_float_m (tuple),
  ambiguities_float_cycles (tuple), baseline_sigma_ecef (3-tuple m),
  per_ambiguity_sigma_cycles (tuple), sigma0, residual_rms,
  covariance_diag (tuple of length 3 + m), num_satellites, num_epochs,
  num_measurements, num_unknowns. ValueErrors: fewer than MIN_SATELLITES
  satellites or MIN_EPOCHS epochs; position/phase length mismatch in an
  epoch; inconsistent satellite counts across epochs; reference index
  out of range; non-finite positions, phases, epochs or base position; a
  coincident satellite; a singular normal matrix (pivot below
  PIVOT_MIN).
- resolve_integer_ambiguities(epochs, base_position,
  reference_index = 0, search_radius = DEFAULT_SEARCH_RADIUS,
  ratio_min = DEFAULT_RATIO_MIN) -> dict. Enumerates the rounding
  candidate sets, scores by the float-covariance quadratic form and
  applies the ratio test. Returns best_candidate (tuple of ints),
  second_best (tuple), best_q, second_q, ratio, resolved (bool),
  candidates_searched, best_rss, second_rss (fixed residual RSS of the
  two best candidates). ValueErrors as in solve_float_baseline plus
  search_radius < 1 and ratio_min <= 1.
- fixed_baseline_solution(epochs, base_position, integer_ambiguities,
  reference_index = 0) -> dict. Baseline-only least squares with the
  integer set imposed. Returns baseline_ecef (3-tuple m),
  per_axis_sigma_ecef (3-tuple m), sigma0, residual_rms,
  num_measurements. ValueErrors as in solve_float_baseline plus an
  integer_ambiguities length mismatch (must equal S - 1).
- solve_td_baseline(epochs, base_position, reference_index = 0) -> dict.
  Baseline-only least squares over the ambiguity-free time-differenced
  double differences. Returns baseline_ecef, residual_rms,
  num_equations. ValueErrors as in solve_float_baseline (needs at least
  2 epochs).
- ecef_to_enu(delta_ecef, base_position) -> (e, n, u) tuple in m.
  Spherical-Earth local ENU offset of delta_ecef at the base. ValueError
  on non-finite input or a zero base position.

Identities to test (closed form or tolerance-bounded):
- Wavelength identity: LAMBDA_L1*F_L1 = C_LIGHT to float precision (real
  anchor residual 0.000e+00).
- Clock cancellation: the receiver clock difference and every satellite
  clock offset vanish from the double differences (real anchor max
  leakage 2.799e-08 cycles over all pairs and epochs, below 1e-6).
- ENU basis identity at the demo base: ecef_to_enu((-2, 20, 12),
  (6378137, 0, 0)) = (20, 12, -2) exactly (the basis is (y, z, x) at
  lat 0, lon 0).
- Ambiguity constancy: a double difference re-formed from a later epoch
  carries the same integer; the epoch difference y(t2) - y(t1) shows no
  cycle-level residue (real anchor 1.289e-06 m, the curvature floor; a
  one-cycle residue would be about 0.19 m).
- Rounding identity on the noisy worked run: every float ambiguity error
  is below 0.5 cycles (real anchor max 0.357900), so nearest-integer
  rounding of the float solution equals the true integer set.
- Noiseless identity: with the noise offsets zeroed, the float solve
  recovers the baseline to the curvature floor (real anchor 3-D error
  1.533e-05 m, max ambiguity error 1.087e-04 cycles, residual RMS
  5.325e-07 m) and the fixed solve to 9.093e-06 m.
- Search-count identity: candidates_searched = (2*search_radius + 1)^m
  = 5^5 = 3125 at the default radius on the worked example.
- Ratio ordering identity: best and second best by the float-covariance
  q-form are also best and second best by the fixed residual RSS (real
  anchor: both pick the true set first).
- Determinism; no imports beyond math; no RNG; no orbit propagation
  anywhere in the module.

## Worked example

Fixed base station at the equator on the prime meridian, ECEF position
(6378137.000, 0.000, 0.000) m (lat 0, lon 0, sea level on the spherical
earth). TRUE rover baseline ECEF (-2.000, 20.000, 12.000) m, length
23.409 m, so the TRUE ENU offset is (20.000 E, 12.000 N, -2.000 U) m.
Six MEO satellites at 55.5 deg inclination, semi-major axis 2.656e7 m,
tracked at three epochs t = 0, 600 and 1200 s of a 20 minute static-
baseline observation arc; reference satellite is A. TRUE integer
double-difference ambiguities versus A (cycles): DD1 (B) 487, DD2 (C)
-196, DD3 (D) 372, DD4 (E) -514, DD5 (F) 259. All values below are REAL
outputs of the prep anchor /tmp/w44spec/anchor_rtk.py (stdlib math,
deterministic, no RNG, exit 0, run under /usr/bin/python3).

Scenario provenance (anchor internals, not module logic): circular-
orbit element records solved from the target subpoints (raan and M0 in
deg, toe 0, dts0 in s; the module never sees these, it receives the
positions below):

- A: raan 7.2072, M0 29.5733, dts0 -1.80e-09.
- B: raan 127.9289, M0 -22.0220, dts0 2.40e-09.
- C: raan 42.7946, M0 54.2847, dts0 9.00e-10.
- D: raan 14.5781, M0 6.0707, dts0 -3.20e-09.
- E: raan 76.4587, M0 -40.0164, dts0 1.50e-09.
- F: raan 75.5482, M0 48.3353, dts0 -7.00e-10.

Rover-minus-base receiver clock offsets at the three epochs: 1.0e-08,
1.6e-08, 2.1e-08 s (they cancel in the double differences). Documented
double-difference noise offsets eps (m), injected deterministically as
per-satellite rover-phase errors on the non-reference tracks (no RNG):

- DD1: 0.0014, -0.0009, 0.0011 m over t0, t1, t2.
- DD2: -0.0012, 0.0016, -0.0007 m.
- DD3: 0.0008, 0.0011, -0.0015 m.
- DD4: -0.0016, -0.0006, 0.0013 m.
- DD5: 0.0005, -0.0014, -0.0010 m.

Satellite ECEF positions at the three epochs (km) and elevation from the
base (deg), the module inputs per epoch:

- epoch t = 0 s:
  - A: (19120.110, -14938.267, 10802.925) km, elev 34.65 deg.
  - B: (15551.646, 19905.200, -8207.491) km, elev 23.08 deg.
  - C: (18771.884, 6099.355, 17772.109) km, elev 33.41 deg.
  - D: (18709.290, -18709.290, 2314.857) km, elev 33.19 deg.
  - E: (22031.951, -4683.036, -14074.656) km, elev 46.54 deg.
  - F: (14799.438, 14799.438, 16351.969) km, elev 20.90 deg.
- epoch t = 600 s:
  - A: (18749.444, -14124.422, 12425.483) km, elev 33.33 deg.
  - B: (15667.733, 20468.594, -6402.531) km, elev 23.42 deg.
  - C: (17506.242, 6688.695, 18820.905) km, elev 29.12 deg.
  - D: (18665.462, -18420.735, 4208.403) km, elev 33.04 deg.
  - E: (22997.332, -4348.931, -12555.601) km, elev 51.36 deg.
  - F: (13513.729, 14643.001, 17561.186) km, elev 17.33 deg.
- epoch t = 1200 s:
  - A: (18347.352, -13195.597, 13952.939) km, elev 31.93 deg.
  - B: (15737.629, 20906.247, -4548.567) km, elev 23.63 deg.
  - C: (16194.882, 7352.429, 19725.648) km, elev 25.00 deg.
  - D: (18544.610, -18019.137, 6069.739) km, elev 32.61 deg.
  - E: (23857.436, -4069.761, -10940.447) km, elev 56.26 deg.
  - F: (12138.099, 14518.950, 18635.993) km, elev 13.70 deg.

Raw L1 carrier-phase streams (cycles) at the rover and the base, the
module inputs per epoch (satellite order A through F):

- epoch t = 0 s: rover 117765968.889984, 122986734.794352,
  118285714.739466, 118378482.055335, 113327803.622843, 124059514.824031;
  base 117765907.499872, 122987269.188084, 118285575.473841,
  118378751.733719, 113327202.268631, 124059863.883244.
- epoch t = 600 s: rover 118319050.974395, 122820372.773910,
  120155561.310159, 118443677.560855, 111817331.856550, 125871681.057135;
  base 118318988.861520, 122820905.164047, 120155417.632624,
  118443944.496563, 111816725.752611, 125872022.211648.
- epoch t = 1200 s: rover 118916115.222242, 122720095.973157,
  122062740.381419, 118623257.237451, 110454181.720175, 127782131.050805;
  base 118916054.174847, 122720627.477878, 122062593.680271,
  118623523.556497, 110453572.715185, 127782465.566851.

Single differences (cycles, rover minus base) per epoch:

- t = 0 s: 61.390112, -534.393732, 139.265625, -269.678384, 601.354211,
  -349.059214.
- t = 600 s: 62.112875, -532.390137, 143.677535, -266.935707,
  606.103938, -341.154513.
- t = 1200 s: 61.047395, -531.504721, 146.701148, -266.319046,
  609.004990, -334.516046.

Clock-cancellation identity on the phase streams: max receiver-clock +
satellite-clock leakage into any double difference = 2.799e-08 cycles.

Double-difference observables y (m) from the phase streams, decomposed
as y = geo + (-lambda*N) + noise + curv, with geo = -du dot b_true,
-lambda*N the true ambiguity term and curv the O(|b|^2/rho)
linearization curvature term:

- DD1 t0: geo -20.702275 | -lN -92.673019 | noise 0.0014 |
  curv -1.926e-06 | y -113.373896 m.
- DD1 t1: geo -20.456240 | -lN -92.673019 | noise -0.0009 |
  curv -3.214e-06 | y -113.130162 m.
- DD1 t2: geo -20.086995 | -lN -92.673019 | noise 0.0011 |
  curv -4.421e-06 | y -112.758918 m.
- DD2 t0: geo -22.477140 | -lN 37.297560 | noise -0.0012 |
  curv -2.602e-06 | y 14.819217 m.
- DD2 t1: geo -21.777917 | -lN 37.297560 | noise 0.0016 |
  curv -3.855e-06 | y 15.521239 m.
- DD2 t2: geo -20.997488 | -lN 37.297560 | noise -0.0007 |
  curv -4.980e-06 | y 16.299367 m.
- DD3 t0: geo 7.788211 | -lN -70.789246 | noise 0.0008 |
  curv -4.407e-06 | y -63.000240 m.
- DD3 t1: geo 8.172287 | -lN -70.789246 | noise 0.0011 |
  curv -4.044e-06 | y -62.615863 m.
- DD3 t2: geo 8.494987 | -lN -70.789246 | noise -0.0015 |
  curv -3.574e-06 | y -62.295762 m.
- DD4 t0: geo 4.942406 | -lN 97.810948 | noise -0.0016 |
  curv -2.149e-06 | y 102.751752 m.
- DD4 t1: geo 5.707712 | -lN 97.810948 | noise -0.0006 |
  curv -2.009e-06 | y 103.518057 m.
- DD4 t2: geo 6.460617 | -lN 97.810948 | noise 0.0013 |
  curv -1.759e-06 | y 104.272863 m.
- DD5 t0: geo -28.820341 | -lN -49.286061 | noise 0.0005 |
  curv -7.530e-06 | y -78.105910 m.
- DD5 t1: geo -27.451763 | -lN -49.286061 | noise -0.0014 |
  curv -8.348e-06 | y -76.739232 m.
- DD5 t2: geo -25.986150 | -lN -49.286061 | noise -0.0010 |
  curv -8.998e-06 | y -75.273220 m.

Float solution (single-pass linear LS at the base, direct normal
equations, 15 measurements, 8 unknowns, 7 degrees of freedom):

- Baseline float ECEF (-2.026418, 19.980488, 12.047022) m; per-axis
  error versus truth (-0.026418, -0.019512, 0.047022) m and 3-D error
  0.057356 m (0.24 percent of the 23.4 m baseline): the float baseline
  is metre-to-decimetre level, as expected before the integer fix.
- Per-axis 1-sigma (0.01325, 0.01533, 0.02850) m: the radial (x, local
  vertical) axis is the weakest.
- sigma0 0.001269 m, residual RMS 0.000867 m (the ~1.1 mm injected noise
  plus the 1e-5 m curvature terms).
- Float ambiguities (cycles) with error versus the true integers and the
  1-sigma from the covariance:
  - DD1 float 487.333272, error +0.333272, sigma 0.21261.
  - DD2 float -195.980711, error +0.019289, sigma 0.05863.
  - DD3 float 372.069115, error +0.069115, sigma 0.04662.
  - DD4 float -513.642100, error +0.357900, sigma 0.20498.
  - DD5 float 259.050675, error +0.050675, sigma 0.08256.
  Max float ambiguity error 0.357900 cycles, every error below 0.5
  cycles, so nearest-integer rounding of the float solution IS the true
  integer set (rounding identity, real anchor True).

Integer resolution (rounding candidate sets at radius 2 cycles around
the rounded float, 5 dimensions, ratio test on the float covariance at
threshold 3.0):

- Candidates searched 3125 (= 5^5).
- Best candidate (487, -196, 372, -514, 259) = the true set,
  float-covariance q 0.000009, fixed residual RSS 2.019764e-05 m^2
  (noise level).
- Second-best (486, -195, 371, -516, 260), q 0.004481, fixed residual
  RSS 4.491915e-03 m^2 (two orders above the best RSS).
- Ratio q_second/q_best = 501.5 >= 3.0, resolved True; the residual-RSS
  ranking agrees (ratio about 222).

Fixed solution (integer set (487, -196, 372, -514, 259) imposed):

- Baseline ECEF (-2.000113, 20.000075, 12.000159) m; per-axis error
  versus truth (-0.1133, +0.0745, +0.1591) mm and 3-D error 0.209051 mm:
  imposing the integers moves the rover fix from the 5.7 cm float level
  to the sub-millimetre level.
- Per-axis 1-sigma (0.00346, 0.00061, 0.00078) m (3.46 mm radial, 0.61
  and 0.78 mm along-track/cross-track): the vertical (radial) axis
  carries the weakest precision, as for the single-receiver geometry.
- sigma0 0.001297 m, residual RMS 0.001160 m.
- ENU offset (E 20.00007, N 12.00016, U -2.00011) m; error versus truth
  (+0.075, +0.159, -0.113) mm.

Time-differenced arm (ambiguity-free double differences across epochs,
geometry-only precursor solve over 10 equations):

- Baseline (-2.02203, 19.98640, 12.03450) m, per-axis error (-0.0220,
  -0.0136, 0.0345) m and 3-D error 0.0431 m: the coarse decimetre-level
  geometry read that the float/fix pipeline refines.
- Residual RMS 0.001816 m; max residual versus geometry + noise
  1.289e-06 m, i.e. no cycle-level integer residue survives the epoch
  difference (a one-cycle residue would be about 0.19 m).

Noiseless cross-check (noise offsets zeroed, curvature terms still
present):

- Float baseline 3-D error 1.533e-05 m, max ambiguity error 1.087e-04
  cycles, residual RMS 5.325e-07 m: the O(|b|^2/rho) curvature of the
  linearized model is the float floor.
- Nearest-integer rounding equals the true set, True; noiseless fixed
  baseline 3-D error 9.093e-06 m.

Read-off: L1 double-difference carrier-phase observables from a 6-
satellite geometry over a 20 minute arc with about 1.1 mm noise give a
float baseline accurate to about 6 cm (0.24 percent of the 23.4 m
baseline) with float ambiguities within 0.36 cycles of the integers, so
the rounding-candidate search resolves the true integer set with a ratio
of 501.5 and the fixed rover baseline lands within 0.21 mm (3-D) of the
truth with a 3.5 mm vertical 1-sigma.

Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w44spec/anchor_rtk.py (stdlib math,
deterministic, exit 0).

## Validation list (contract test must include)

- Scenario and truth: the six satellite position tables above, the raw
  rover and base phase streams above (copy the printed values as
  inputs), base position (6378137.0, 0.0, 0.0) m, reference index 0,
  true baseline (-2.0, 20.0, 12.0) m and true integer ambiguities
  (487, -196, 372, -514, 259) cycles. No RNG needed in the test.
- solve_float_baseline on the worked set: per-axis error below 0.10 m on
  every axis (anchor -0.026418, -0.019512, 0.047022), 3-D error below
  0.15 m (anchor 0.057356), sigma0 within 1e-3 m of 0.001269 m, residual
  RMS below 0.005 m, every float ambiguity within 0.5 cycles of the true
  integer (anchor max 0.357900), per-ambiguity 1-sigma within 1e-2
  cycles of the anchor values (0.21261, 0.05863, 0.04662, 0.20498,
  0.08256).
- Precision identity: per-axis 1-sigma equals sigma0 times the square
  root of the covariance diagonal, and the anchor values (0.01325,
  0.01533, 0.02850) m hold within 1e-3 m; ambiguity sigmas are the
  covariance diagonal in metres divided by LAMBDA_L1.
- resolve_integer_ambiguities on the worked set: candidates_searched
  3125, best_candidate (487, -196, 372, -514, 259), resolved True,
  ratio 501.5 within 1 percent, second_best (486, -195, 371, -516, 260),
  best_rss below 1e-4 m^2 (anchor 2.019764e-05), second_rss above
  best_rss by a factor of 100 or more.
- fixed_baseline_solution on the worked set with the true integer set:
  baseline within 0.001 m of the truth per axis (anchor errors
  -0.1133, 0.0745, 0.1591 mm), 3-D error below 0.001 m (anchor
  0.209051 mm), per-axis 1-sigma within 1e-4 m of (0.00346, 0.00061,
  0.00078) m, ENU offset within 0.0005 m of (20.0, 12.0, -2.0) (anchor
  error below 0.16 mm per axis).
- solve_td_baseline on the worked set: 3-D error below 0.2 m (anchor
  0.0431 m) and residual RMS below 0.005 m.
- Closed-form identities: single_difference(150.25, 152.75) = -2.5
  cycles; form_double_differences([12.25, 9.75, -3.5], 0) = [-2.5,
  -15.75] cycles; time_differenced_dd([1.2, 3.4, 5.6], [1.0, 3.0, 5.0])
  = [0.2, 0.4, 0.6] cycles; ecef_to_enu((-2, 20, 12), (6378137, 0, 0))
  = (20, 12, -2); LAMBDA_L1*F_L1 = C_LIGHT to 1e-12.
- Noiseless identity: with the noise offsets zeroed the float 3-D error
  stays below 1e-4 m (anchor 1.533e-05), max ambiguity error below 1e-3
  cycles (anchor 1.087e-04) and the fixed 3-D error below 1e-4 m.
- Clock-cancellation identity: re-derive the double differences from
  the phase streams and confirm the max clock leakage stays below 1e-6
  cycles (anchor 2.799e-08).
- ValueErrors across the module: fewer than MIN_SATELLITES (5)
  satellites or MIN_EPOCHS (2) epochs; position/phase length mismatch;
  satellite count changing between epochs; reference_index out of
  range; search_radius = 0; ratio_min = 1.0; a coincident satellite in
  line_of_sight (range below 1 m); non-finite positions, phases or
  epoch values; an integer_ambiguities tuple of the wrong length in
  fixed_baseline_solution; a singular normal matrix.
- Determinism; no imports beyond math; no RNG anywhere in the module;
  no orbit propagation.

## Corpus fragment (eval/hit1-wave44-gnss-rtk-positioning.yaml)

Query 1 (copy verbatim):
  "resolve the integer carrier-phase ambiguities and compute the rover
  position relative to a fixed base from double-difference carrier-
  phase observables: form the single and double differences across the
  satellite pairs and epochs, solve for the float baseline and
  ambiguities, then apply the ratio test to the rounding candidate
  sets"
  intent: "gnc-autonomy; differential GNSS rover fix relative to a fixed
  base from double-difference carrier-phase observables with float
  baseline and integer ambiguity resolution by rounding candidate sets
  and a ratio test on the float covariance"
  expected_skill: "gnc-autonomy/navigation/gnss-rtk-positioning"
Query 2 (copy verbatim):
  "carrier-phase differential positioning: given the common-view L1
  phase streams at a fixed base and a rover over several epochs,
  resolve the double-difference integer ambiguities and report the
  fixed baseline as the ENU offset at the base"
  intent: "gnc-autonomy; RTK fixed baseline and ENU offset from carrier-
  phase differential double-difference observables with the integer
  ambiguities resolved"
  expected_skill: "gnc-autonomy/navigation/gnss-rtk-positioning"
Task ids: w44-gnss-rtk-positioning-1 and -2. Prep grep of eval/hit1-
corpus.yaml: "gnss-rtk", "rtk-positioning", "carrier-phase-
differential", "integer-ambiguity-resolution" and "double-difference-
baseline" all return ZERO hits; "differential" appears only in cabin-
pressure, differential-equation and radiation contexts, never in a GNSS
one, and "integer" only in the orbit ground-track "integer repeat
cycle" task. The w42-gnss-carrier-smoothing-1/-2 tasks route on Hatch
smoothing and divergence monitors, the w43-gnss-doppler-velocity-
positioning-1/-2 tasks route on the single-receiver range-rate velocity
fix, the w38-doppler-shift-1/-2 tasks route on the s-band comm frequency
domain and the w27-gnss-pseudorange-positioning-1/-2 tasks route on the
code position fix and clock bias, so the queries above are collision-
free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the position of a GNSS
rover relative to a fixed base station from double-difference carrier-
phase observables:" and include the float and fixed baseline, the
integer ambiguity resolution and the ENU offset from the Claim.
First tag: gnss-rtk-positioning. Additional tags ONLY: gnss-rtk,
rtk-positioning, carrier-phase-differential, integer-ambiguity-
resolution, double-difference-baseline. NEVER single generic words
(gnss, rtk, carrier, phase, baseline, ambiguity, positioning, receiver,
rover, base, navigation, estimation) and NEVER tags owned by siblings:
the code-positioning tags of gnss-pseudorange-positioning
(pseudorange-positioning, gnss-position-fix, receiver-clock-bias,
iterated-least-squares-fix, ecef-position-solution, satellite-
pseudorange-residual, snapshot-navigation-solution), the smoothing tags
of gnss-carrier-smoothing (carrier-phase-smoothing, hatch-filter-
recursion, code-carrier-divergence-monitor, ionospheric-divergence-
check, smoothed-range-noise-reduction), the velocity tags of gnss-
doppler-velocity-positioning (receiver-velocity-fix, doppler-
positioning, clock-drift-estimate, carrier-delta-range-rate, velocity-
fix-per-axis-precision), the integrity tags of gnss-raim-fde (raim,
fault-detection-and-exclusion, horizontal-protection-level, chi-square-
threshold, gnss-integrity) and the comm tags of space-systems/
subsystems/doppler-shift (doppler-shift, range-rate-frequency-offset,
doppler-rate, acquisition-frequency-offset, worst-case-doppler).
Description constraints: 50-150 words and <=1000 chars; verified count
of the recommended wording below: 140 words, 946 chars, action verb
present, no em dash. Recommended wording (outputs in Claim order): "Use
when you must compute the position of a GNSS rover relative to a fixed
base station from double-difference carrier-phase observables: form the
per-satellite single differences across the receivers at each epoch of
a common-view observation arc, then the double differences across
satellite pairs and epochs, and solve the stacked least-squares normal
equations for the float baseline and the per-pair float ambiguities.
Resolve the integer ambiguities by rounding candidate sets around the
float solution with a ratio test on the float covariance, impose the
winning integer set, and re-solve for the fixed baseline with per-axis
1-sigma precision. Produces the float baseline and the fixed rover
baseline in ECEF, the resolved integer ambiguity set with its ratio,
and the fixed ENU offset at the base. Trigger: carrier phase
differential, RTK positioning, integer ambiguity resolution, double
difference baseline, fixed baseline ENU offset." The single-receiver
deliverables of the siblings must not appear: no code pseudorange fix,
no absolute single-point position, no receiver clock bias, no Hatch
smoothing, no doppler/range-rate/velocity/clock-drift content and no
orbit propagation wording (satellite positions arrive as per-epoch
inputs).

FORBIDDEN TOKENS (belong to siblings): pseudorange-positioning,
gnss-position-fix, receiver-clock-bias, snapshot-navigation-solution,
iterated-least-squares-fix, ecef-position-solution, satellite-
pseudorange-residual (gnss-pseudorange-positioning); hatch-recursion,
smoothed-range, code-carrier-divergence, ionospheric-divergence,
smoothing-time-constant (gnss-carrier-smoothing); receiver-velocity-
fix, doppler-positioning, clock-drift-estimate, carrier-delta-range-
rate, velocity-fix-per-axis-precision (gnss-doppler-velocity-
positioning); protection-level, fault-detection, satellite-exclusion,
chi-square, false-alarm, integrity-monitoring (gnss-raim-fde);
received-frequency, delta-f-offset, s-band-downlink, worst-case-doppler
(space-systems/subsystems/doppler-shift); orbit-determination, gibbs-
method (gnc-autonomy/space/orbit-determination). The RTK leaf works in
the baseline domain between two receivers only; code-pseudorange,
doppler and clock-bias outputs are never computed.
