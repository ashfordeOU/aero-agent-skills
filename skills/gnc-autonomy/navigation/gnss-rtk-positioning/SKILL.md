---
name: gnss-rtk-positioning
description: "Use when you must compute the position of a GNSS rover relative to a fixed base station from double-difference carrier-phase observables: form the per-satellite single differences across the receivers at each epoch of a common-view observation arc, then the double differences across satellite pairs and epochs, and solve the stacked least-squares normal equations for the float baseline and the per-pair float ambiguities. Resolve the integer ambiguities by rounding candidate sets around the float solution with a ratio test on the float covariance, impose the winning integer set, and re-solve for the fixed baseline with per-axis 1-sigma precision. Produces the float baseline and the fixed rover baseline in ECEF, the resolved integer ambiguity set with its ratio, and the fixed ENU offset at the base. Trigger: carrier phase differential, RTK positioning, integer ambiguity resolution, double difference baseline, fixed baseline ENU offset."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-229
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [gnss-rtk-positioning, gnss-rtk, rtk-positioning, carrier-phase-differential, integer-ambiguity-resolution, double-difference-baseline]
  version: 0.1.0
  author: AeroSkills
---

# GNSS RTK Positioning (gnc-autonomy/navigation/gnss-rtk-positioning)

Use when you must compute the ECEF position of a GNSS rover relative to a
fixed base station, the baseline vector b = rover minus base, from
common-view L1 carrier-phase observables recorded at both receivers over
the epochs of an observation arc. For every epoch and every tracked
satellite with a supplied ECEF position, the leaf forms the single
difference across the receivers, then the double differences across
satellite pairs (non-reference minus reference), scales them to metres by
the L1 wavelength, and solves the stacked least-squares normal equations
for the float baseline and the float ambiguities. The integer
double-difference ambiguities are resolved by enumerating rounding
candidate sets around the rounded float vector, scoring each candidate by
the quadratic form on the float covariance, and applying a ratio test;
the winning integer set is then imposed and the measurements re-solved
for the FIXED baseline, reported as the ENU offset at the base. The
module is pure stdlib math, deterministic, no RNG, and performs no orbit
propagation: the satellite ECEF positions at each epoch are supplied
inputs, as a receiver would receive them from an ephemeris service. It
pairs with gnss-pseudorange-positioning (code absolute), gnss-carrier-
smoothing (code smoothing, not differencing) and gnss-doppler-velocity-
positioning (single-receiver velocity), which own the single-receiver
steps below this differential step; the fences are described under
Related leaves.

## Domain quick reference

- Module constants: C_LIGHT = 299792458.0 m/s, F_L1 = 1575.42e6 Hz,
  LAMBDA_L1 = C_LIGHT / F_L1 = 0.190293672798 m/cycle (the L1
  wavelength, exact by construction), R_EARTH = 6378137.0 m
  (spherical-Earth demo context for the ENU conversion only),
  MIN_SATELLITES = 5 (4 non-reference pairs), MIN_EPOCHS = 2,
  PIVOT_MIN = 1e-300 (singularity floor of the Gaussian elimination),
  DEFAULT_SEARCH_RADIUS = 2 cycles, DEFAULT_RATIO_MIN = 3.0.
- Phase model: the raw L1 carrier phase in cycles at receiver i (base r
  or rover u) for satellite j at epoch t is phi_i^j(t) = rho_i^j(t)/lambda
  + f*dt_i(t) - f*dts^j - N_i^j, with rho the geometric range, dt_i the
  receiver clock offset, dts^j the broadcast satellite clock offset and
  N_i^j a per-receiver per-satellite integer tracking constant. Nothing
  in the module needs the absolute phase level: the double differences
  use only differences of the printed phase streams.
- Single difference (cycles): SD^j(t) = phi_u^j(t) - phi_r^j(t); the
  satellite clock term f*dts^j cancels exactly, the receiver clock
  difference f*(dt_u - dt_r) remains, common to every satellite at the
  epoch.
- Double difference (cycles) of pair j against reference satellite 0:
  DD^j(t) = SD^j(t) - SD^0(t); the receiver clock difference cancels
  exactly, and in metres y_j(t) = LAMBDA_L1*DD^j(t) =
  (rho_u^j - rho_r^j - rho_u^0 + rho_r^0)(t) - LAMBDA_L1*(N^j - N^0),
  where the true integer double-difference ambiguity of the pair is
  N_j = N^j - N^0, constant across the arc when no cycle slip occurs.
- Linearized geometry: for a baseline b short against the slant range,
  (rho_u^j - rho_r^j)(t) = -u_j(t) dot b to first order, so
  y_j(t) = -(u_j(t) - u_0(t)) dot b - LAMBDA_L1*N_j + eps_j(t), with u
  the unit line of sight from the BASE position to the satellite. The
  single-pass linear model leaves an O(|b|^2/rho) curvature residual of
  about 1e-5 m on the 23 m demo baseline, absorbed by the least squares
  as the model floor.
- Float system: unknowns x = (b_x, b_y, b_z, A_1 ... A_m) with
  A_j = LAMBDA_L1*N_j in metres; the measurement row for pair j at
  epoch t is [-du_x, -du_y, -du_z, 0 ... -1 ... 0] with du = u_j - u_0
  and the -1 on the j-th ambiguity column; y = H x + eps. Normal
  equations (H^T H) x = H^T y are solved once (the model is linear at
  the base), no iteration. m = S - 1 pairs, m*T measurements, 3 + m
  unknowns, redundancy m*T - (3 + m) = 7 on the worked example.
- Precision: residual r_i = y_i - (H x)_i; sigma0 =
  sqrt(sum(r_i^2) / (m*T - (3 + m))); per-axis 1-sigma
  sigma0*sqrt(diag_ii((H^T H)^-1)) for the three baseline axes, and
  sigma0*sqrt(diag_jj(...))/LAMBDA_L1 for the ambiguities (cycles).
- Integer resolution: with n_float the float ambiguities in cycles,
  round to n_round and enumerate every integer vector n within
  Chebyshev distance SEARCH_RADIUS of n_round (5^5 = 3125 candidates on
  the worked example). Score each candidate by the float-covariance
  quadratic form q(n) = (n - n_float)^T Q^-1 (n - n_float), with Q the
  m x m float ambiguity covariance block in cycles^2 taken from the
  inverse normal matrix scaled by 1/LAMBDA_L1^2. ratio =
  q(second-best)/q(best); the set is resolved when ratio >= RATIO_MIN.
  The fixed residual RSS of a candidate, min_b ||y + lambda*n +
  du*b||^2 over the baseline only, ranks the candidates the same way.
- Fixed solution: impose the winning integer set n and re-solve the
  baseline-only least squares over the shifted measurements
  y_j(t) + LAMBDA_L1*n_j with rows -du_j(t); per-axis 1-sigma from
  sigma0*sqrt(diag((G^T G)^-1)) with sigma0 over m*T - 3 degrees of
  freedom.
- ENU conversion: spherical base latitude and longitude from the base
  ECEF position, local basis e = (-sin lon, cos lon, 0), n = (-sin lat
  cos lon, -sin lat sin lon, cos lat), u = (cos lat cos lon, cos lat
  sin lon, sin lat); the ENU offset is (b dot e, b dot n, b dot u). At
  the demo base (lat 0, lon 0) this is exactly (b_y, b_z, b_x).
- Time-differenced arm: the per-pair epoch difference y_j(t2) - y_j(t1)
  = -(du_j(t2) - du_j(t1)) dot b + (eps_j(t2) - eps_j(t1)) carries NO
  ambiguity term (the integers are constant across a slip-free arc),
  giving the ambiguity-free baseline-only geometry solve used as the
  coarse precursor read.
- RTCA DO-229 frames the GNSS airborne navigation context; the relations
  above are standard engineering methodology, name and paraphrase only.

## Workflow

1. Fix the observation arc: per-epoch records with the satellite ECEF
   positions (supplied inputs, no orbit propagation), the raw rover and
   base L1 phase streams in cycles (same satellite order every epoch),
   the base ECEF position and the reference satellite index. The module
   constants anchor every later step; line_of_sight checks each
   satellite for coincidence with the base.
2. Form the per-satellite single differences across the receivers at
   each epoch: single_difference returns rover minus base phase in
   cycles; the broadcast satellite clock offsets cancel in every single
   difference.
3. Form the double differences across the satellite pairs and epochs:
   form_double_differences subtracts the reference-satellite single
   difference from every non-reference one, and the solvers scale the
   cycles by LAMBDA_L1 to the metre observables y. The receiver clock
   difference cancels exactly in the double differences.
4. Solve the float baseline: solve_float_baseline stacks the rows
   [-du, -e_j] over (b_x, b_y, b_z, A_1 ... A_m) and solves the normal
   equations (H^T H) x = H^T y, returning the float baseline, the float
   ambiguities in metres and cycles, sigma0, the residual RMS, the
   covariance diagonal and the per-axis and per-ambiguity 1-sigma
   precision.
5. Resolve the integer ambiguities: resolve_integer_ambiguities
   enumerates the rounding candidate sets within a Chebyshev radius of
   the rounded float vector, scores each by the float-covariance
   quadratic form, applies the ratio test (threshold 3.0) and returns
   the winning integer set with its ratio and the fixed residual RSS of
   the two best candidates.
6. Impose the winning integer set: fixed_baseline_solution re-solves
   the baseline-only least squares over the shifted measurements
   y_j(t) + LAMBDA_L1*n_j and returns the FIXED baseline with the
   per-axis 1-sigma precision from the baseline-only normal matrix.
7. Report the fixed baseline as the ENU offset at the base:
   ecef_to_enu converts the fixed baseline ECEF vector to the local
   east, north, up offset at the base position.
8. Run the ambiguity-free time-differenced precursor read and the
   identity checks: solve_td_baseline fits the epoch-differenced double
   differences (no ambiguity term in a slip-free arc) as the coarse
   geometry read; the clock-cancellation, ambiguity-constancy and
   no-cycle-residue identities confirm the double-difference model.
9. Confirm the deterministic checks with the contract test of the
   Behavior contract (gate 3) section.

## Worked example

Fixed base station at the equator on the prime meridian, ECEF position
(6378137.000, 0.000, 0.000) m (lat 0, lon 0, sea level on the spherical
earth). TRUE rover baseline ECEF (-2.000, 20.000, 12.000) m, length
23.409 m, so the TRUE ENU offset is (20.000 E, 12.000 N, -2.000 U) m.
Six MEO satellites at 55.5 deg inclination, semi-major axis 2.656e7 m,
tracked at three epochs t = 0, 600 and 1200 s of a 20 minute static-
baseline observation arc; the reference satellite is A. TRUE integer
double-difference ambiguities versus A (cycles): DD1 (B) 487, DD2 (C)
-196, DD3 (D) 372, DD4 (E) -514, DD5 (F) 259. About 1.1 mm of
deterministic double-difference noise is documented per pair per epoch.
All values below are REAL outputs of the leaf module (stdlib math,
deterministic, no RNG, exit 0), matching the wave-44 spec anchors.

Single differences (cycles, rover minus base) per epoch, re-formed from
the phase streams:

- t = 0 s: 61.390112, -534.393732, 139.265625, -269.678384, 601.354211,
  -349.059214.
- t = 600 s: 62.112875, -532.390137, 143.677535, -266.935707,
  606.103938, -341.154513.
- t = 1200 s: 61.047395, -531.504721, 146.701148, -266.319046,
  609.004990, -334.516046.

Float solution (single-pass linear least squares at the base, direct
normal equations, 15 measurements, 8 unknowns, 7 degrees of freedom):

- Baseline float ECEF (-2.026417, 19.980484, 12.047023) m; per-axis
  error versus truth (-0.0264, -0.0195, 0.0470) m and 3-D error
  0.0574 m (0.25 percent of the 23.4 m baseline): the float baseline is
  metre-to-decimetre level, as expected before the integer fix.
- Per-axis 1-sigma (0.013254, 0.015327, 0.028501) m: the radial (x,
  local vertical) axis is the weakest.
- sigma0 0.001269 m, residual RMS 0.000867 m (the ~1.1 mm injected
  noise plus the 1e-5 m curvature terms).
- Float ambiguities (cycles) with error versus the true integers and
  the 1-sigma from the covariance: DD1 487.333307 (+0.3333, sigma
  0.21262), DD2 -195.980692 (+0.0193, sigma 0.05863), DD3 372.069111
  (+0.0691, sigma 0.04662), DD4 -513.642088 (+0.3579, sigma 0.20499),
  DD5 259.050702 (+0.0507, sigma 0.08256). Max float ambiguity error
  0.358 cycles, every error below 0.5 cycles, so nearest-integer
  rounding of the float solution IS the true integer set.

Integer resolution (rounding candidate sets at radius 2 cycles around
the rounded float, 5 dimensions, ratio test on the float covariance at
threshold 3.0):

- Candidates searched 3125 (= 5^5).
- Best candidate (487, -196, 372, -514, 259) = the true set,
  float-covariance q 8.93e-6, fixed residual RSS 2.020e-05 m^2 (noise
  level).
- Second-best (486, -195, 371, -516, 260), q 4.481e-3, fixed residual
  RSS 4.492e-03 m^2 (two orders above the best RSS).
- Ratio q_second/q_best = 501.5 >= 3.0, resolved True; the residual-RSS
  ranking agrees (ratio about 222).

Fixed solution (integer set (487, -196, 372, -514, 259) imposed):

- Baseline ECEF (-2.000112, 20.000074, 12.000159) m; per-axis error
  versus truth (-0.112, +0.074, +0.159) mm and 3-D error 0.209 mm:
  imposing the integers moves the rover fix from the 5.7 cm float level
  to the sub-millimetre level.
- Per-axis 1-sigma (0.003460, 0.000614, 0.000782) m (3.46 mm radial,
  0.61 and 0.78 mm along-track/cross-track): the vertical (radial) axis
  carries the weakest precision, as for the single-receiver geometry.
- sigma0 0.001297 m, residual RMS 0.001160 m.
- ENU offset (E 20.000074, N 12.000159, U -2.000112) m; error versus
  truth (+0.074, +0.159, -0.112) mm.

Time-differenced arm (ambiguity-free double differences across adjacent
epochs, geometry-only precursor solve over 10 equations):

- Baseline (-2.022031, 19.986400, 12.034498) m, per-axis error
  (-0.0220, -0.0136, 0.0345) m and 3-D error 0.0431 m: the coarse
  decimetre-level geometry read that the float/fix pipeline refines.
- Residual RMS 0.001816 m; no cycle-level integer residue survives the
  epoch difference (a one-cycle residue would be about 0.19 m).

Noiseless cross-check (noise offsets zeroed, curvature terms still
present):

- Float baseline 3-D error 1.74e-05 m, max ambiguity error 1.36e-04
  cycles, residual RMS 6.31e-07 m: the O(|b|^2/rho) curvature of the
  linearized model is the float floor.
- Nearest-integer rounding equals the true set; noiseless fixed
  baseline 3-D error 8.22e-06 m.

Read-off: L1 double-difference carrier-phase observables from a 6-
satellite geometry over a 20 minute arc with about 1.1 mm noise give a
float baseline accurate to about 6 cm (0.25 percent of the 23.4 m
baseline) with float ambiguities within 0.36 cycles of the integers, so
the rounding-candidate search resolves the true integer set with a ratio
of 501.5 and the fixed rover baseline lands within 0.21 mm (3-D) of the
truth with a 3.5 mm vertical 1-sigma.

## Verification

- Run scripts/test_gnss_rtk_positioning.py; the contract test must pass
  under both the system python3 and the pyenv 3.13.12 hook interpreter
  (39 tests, offline, deterministic).
- Confirm the worked-example contract: float per-axis error below
  0.10 m on every axis and 3-D error below 0.15 m (module 0.0574 m),
  sigma0 within 1e-3 m of 0.001269 m, residual RMS below 0.005 m, every
  float ambiguity within 0.5 cycles of the true integer (module max
  0.358) and the per-ambiguity 1-sigma within 1e-2 cycles of the anchor
  values (0.21261, 0.05863, 0.04662, 0.20498, 0.08256).
- Confirm the precision identity: every per-axis 1-sigma equals sigma0
  times the square root of the covariance diagonal, the anchor values
  (0.01325, 0.01533, 0.02850) m hold within 1e-3 m, and the ambiguity
  sigmas are the metre covariance diagonal divided by LAMBDA_L1.
- Confirm the integer-resolution contract: candidates_searched 3125,
  best_candidate (487, -196, 372, -514, 259), resolved True, ratio
  501.5 within 1 percent, second_best (486, -195, 371, -516, 260),
  best_rss below 1e-4 m^2 and second_rss above best_rss by a factor of
  100 or more.
- Confirm the fixed-solution contract: baseline within 0.001 m of the
  truth per axis (module errors -0.112, +0.074, +0.159 mm), 3-D error
  below 0.001 m, per-axis 1-sigma within 1e-4 m of (0.00346, 0.00061,
  0.00078) m and the ENU offset within 0.0005 m of (20.0, 12.0, -2.0).
- Confirm the time-differenced arm: 3-D error below 0.2 m (module
  0.0431 m), residual RMS below 0.005 m, and the epoch-differenced
  observables reproduce the documented noise differences with no
  cycle-level residue.
- Confirm the closed-form identities: single_difference(150.25, 152.75)
  = -2.5 cycles, form_double_differences([12.25, 9.75, -3.5], 0) =
  [-2.5, -15.75] cycles, time_differenced_dd([1.2, 3.4, 5.6],
  [1.0, 3.0, 5.0]) = [0.2, 0.4, 0.6] cycles, ecef_to_enu((-2, 20, 12),
  (6378137, 0, 0)) = (20, 12, -2) and LAMBDA_L1*F_L1 = C_LIGHT.
- Confirm the clock-cancellation identity: shifting the rover clock by
  a common offset at every epoch and adding the satellite clock offsets
  to both receivers leaves every double difference at machine precision
  (below 1e-6 cycles of leakage) and leaves the float solve unchanged.
- Confirm the noiseless identity: with the noise offsets zeroed the
  float 3-D error stays below 1e-4 m and the fixed 3-D error below
  1e-4 m.
- Confirm ValueError rejection of every non-physical input: fewer than
  5 satellites or fewer than 2 epochs, position/phase length mismatch,
  satellite count changing between epochs, reference index out of
  range, search_radius below 1 cycle, ratio_min at or below 1, an
  integer_ambiguities tuple of the wrong length, a coincident satellite,
  non-finite positions, phases, epochs or base position, a zero base
  position in ecef_to_enu, and a singular normal matrix.
- Confirm determinism: repeated solves return identical outputs; the
  module imports nothing beyond math and contains no RNG and no orbit
  propagation.

## Related leaves

- skills/gnc-autonomy/navigation/gnss-pseudorange-positioning: owns the
  single-receiver absolute code fix (position and clock bias from
  pseudoranges); this leaf is differential and carrier-phase based,
  solves no pseudorange and estimates no receiver clock bias (the
  receiver clock terms cancel in the double differences).
- skills/gnc-autonomy/navigation/gnss-carrier-smoothing: owns the Hatch
  smoothing side of the carrier observable (smoothing CODE with carrier
  increments in one receiver); this leaf differences raw carrier phases
  between two receivers, never smooths code and never runs a Hatch
  recursion, and integer ambiguity resolution is in scope here only.
- skills/gnc-autonomy/navigation/gnss-doppler-velocity-positioning:
  owns the single-receiver snapshot velocity step from carrier-phase
  delta-range-rate observables with Kepler propagation; this leaf
  consumes static carrier-phase accumulations, estimates no velocity
  and performs no orbit propagation (the satellite ECEF positions at
  each epoch are supplied inputs).
- skills/gnc-autonomy/navigation/gnss-raim-fde: owns integrity on the
  single-receiver measurement set; this leaf produces no detection
  verdict and no protection level (the arc is fault-free by
  assumption).
- skills/gnc-autonomy/navigation/dilution-of-precision and the other
  GNSS navigation siblings of the pack: the remaining single-receiver
  geometry and quality context around this differential step.
- skills/gnc-autonomy/space/orbit-determination and
  skills/gnc-autonomy/space/orbit-dynamics: the space-domain siblings;
  their propagation machinery is never needed here because satellite
  positions arrive as per-epoch inputs.

## Pitfalls

- Confusing this leaf with the code position fix: the rover position
  this leaf reports is the differential baseline relative to a FIXED
  base from double-difference carrier phase, not an absolute
  single-point code fix. Code pseudorange positioning and receiver
  clock-bias estimation belong to gnss-pseudorange-positioning.
- Treating the carrier observable as something to smooth: this leaf
  differences raw carrier-phase streams between two receivers and never
  smooths code pseudoranges. Hatch smoothing, smoothed ranges and
  code-carrier divergence monitoring belong to gnss-carrier-smoothing;
  the smoothing leaf explicitly excludes the integer ambiguity
  resolution that is the core step here.
- Expecting a velocity or a propagated constellation: this leaf
  estimates no velocity, no range rate and no clock drift, and it
  performs no Kepler or broadcast-ephemeris propagation; the satellite
  ECEF positions at each epoch are supplied inputs (the domain of
  gnss-doppler-velocity-positioning).
- Forgetting that the clock terms cancel in the double differences:
  the receiver clock difference is common to every satellite at an
  epoch and cancels when the reference satellite is subtracted, so no
  clock-bias unknown appears in the state; the state is the 3-axis
  baseline plus one ambiguity per non-reference pair.
- Solving only the baseline: the float state is (b_x, b_y, b_z,
  A_1 ... A_m) with one float ambiguity per pair, 8 unknowns for 6
  satellites; dropping the ambiguity columns leaves the decimetre-level
  time-differenced read (step 8) rather than the fixed solution.
- Reading the float baseline as the final answer: the float fix is at
  the 6 cm level on the worked example; the integer-constrained fix
  lands at 0.21 mm, so reporting the float baseline without running the
  integer resolution undersells the observable by two orders of
  magnitude.
- Quoting the vertical axis precision as if it matched the horizontal:
  the radial (local vertical) axis is the weakest for the geometry
  (anchor 1-sigma 3.46 mm against 0.61 and 0.78 mm on the other axes).
- Trusting an arc with a cycle slip: the double-difference ambiguities
  are constant only across a slip-free arc; the model assumes no cycle
  slip (cycle-slip detection and repair are out of scope for this
  leaf), so a slipped arc corrupts the integer search before the ratio
  test can catch it.
- Treating the q-form weight as a full covariance with the sigma0
  scale: Q is the inverse-normal ambiguity block scaled by
  1/LAMBDA_L1^2 per the defining relation; the sigma0 scale cancels in
  the ratio test and is omitted from the quadratic-form weight.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/gnc-autonomy/navigation/gnss-rtk-positioning/scripts/test_gnss_rtk_positioning.py

The test covers the worked-example contract with the module's real
outputs as targets: the step-1 module constants and line-of-sight
geometry, the step-2 single-difference traverse with the spec phase-
stream table, the step-3 double-difference traverse with the clock-
cancellation identity below 1e-6 cycles, the step-4 float solve on the
worked set (baseline, ambiguities, sigma0, residual RMS, covariance
precision identity, system dimensions), the step-5 integer resolution
(candidate count 3125, best and second-best candidate sets, ratio 501.5
within 1 percent, residual-RSS ordering), the step-6 fixed solution with
the imposed integer set (sub-mm baseline, per-axis sigmas) and the
ambiguity-constancy identity across epochs, the step-7 ENU offset at the
demo base, the step-8 time-differenced precursor read with the
no-cycle-residue identity, the noiseless curvature-floor cross-check,
ValueError rejection of every non-physical input in the spec validation
list (fewer than 5 satellites, fewer than 2 epochs, length mismatch,
count change, reference index, search radius, ratio threshold, wrong
ambiguity tuple length, coincident satellite, non-finite values, zero
base, singular normal matrix), determinism across reruns and the
pure-stdlib no-RNG import check. It passes under both the system python3
and the pyenv 3.13.12 hook interpreter.

## Compliance

- Standards referenced, not reproduced: RTCA DO-229 frames the GNSS
  airborne navigation context; this leaf implements standard engineering
  methodology with name and paraphrase only, no MOPS algorithm or table
  text, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
