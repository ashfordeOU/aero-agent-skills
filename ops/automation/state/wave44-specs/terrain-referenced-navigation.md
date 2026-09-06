# Wave-44 leaf spec: terrain-referenced-navigation (gnc-autonomy,
# navigation pack)

- Path: skills/gnc-autonomy/navigation/terrain-referenced-navigation/
- Pack: navigation (present siblings bearing-only-localization,
  dilution-of-precision, gnss-carrier-smoothing, gnss-doppler-velocity-
  positioning, gnss-pseudorange-positioning, gnss-raim-fde, inertial-
  navigation, ins-gnss-integrated-filter, kalman-filter-design,
  navigation-frames, tightly-coupled-ins-gnss).
- Provenance: wave-44 probe task-7 rank 2 (GNC 49, leaf-plan line 101):
  non-GNSS INS aiding from radar-altimeter terrain profiles against a
  stored digital elevation model (DEM): TERCOM-style grid correlation
  (correlation surface plus best-match offset) followed by a linearized
  terrain-slope measurement update (SITAN point-mass form) correcting
  the inertial position. Prep verified ZERO gnc-autonomy owners: all 9
  terrain-token hits in the tree sit outside the navigation pack (the
  coverage-path-planning flat-terrain survey assumption, the weather-
  radar ground-clutter geometry, the satellite-coverage elevation-mask
  mention, the mil-std-1797a flight-phase "terrain following" category,
  none a map-aiding method). GENUINE gnc-autonomy gap: every existing
  aiding leaf in the navigation pack is GNSS based (pseudorange,
  doppler, carrier smoothing, RAIM, DOP, the two INS/GNSS filters) or
  pure-INS error analysis, and no leaf in the whole skills tree matches
  a measured terrain-height profile against a stored elevation grid.
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  the radar-altimeter/DEM map-aiding measurement update):
  - inertial-navigation (this pack) OWNS the INS error-growth analysis
    and the integration scoping; it has NO external map source. Its
    description reads "estimate position error growth from
    accelerometer bias and gyro drift, check the Schuler period and
    the leveling response, compare strapdown and gimbaled
    mechanization, and scope alignment and INS/GPS integration", its
    body states "An INS measures specific force and rotation rate with
    accelerometers and gyros and integrates them into position,
    velocity, and attitude. It needs no external reference while it
    runs; its errors grow with time", and the coupling paragraph it
    scopes is INS/GPS only ("Loosely coupled (position and velocity
    updates into the navigation filter), tightly coupled (raw
    pseudorange and carrier phase), or deeply coupled"). The sibling
    never introduces a radar altimeter, a DEM or a terrain height
    measurement; the new leaf consumes the INS indicated track as a
    GIVEN input (never mechanized, never re-integrated) and aids it
    from stored terrain, with no GPS in the loop at all.
  - tightly-coupled-ins-gnss (this pack) OWNS the raw-PSEUDORANGE
    measurement update: its description reads "propagate the eight INS
    error states (3 position error, 3 velocity error, receiver clock
    bias in metres, clock drift in m/s) of the constant-velocity-error
    model between epochs, predict each raw pseudorange from the
    inertial position estimate plus the clock bias state, build the
    measurement matrix from the line-of-sight geometry rows with the
    unit clock column, and apply the raw-pseudorange-update Kalman
    correction on the residuals", and its body adds "the INS reference
    trajectory (position and velocity per epoch) is a GIVEN input,
    never re-mechanized". The new leaf carries the same GIVEN-input
    convention for the INS track but its measurement is a terrain
    height from a radar altimeter against the stored DEM; no
    pseudorange, no clock state, no line-of-sight geometry and no GNSS
    observables of any kind appear in it.
  - ins-gnss-integrated-filter (this pack) OWNS the GNSS POSITION
    measurement update: its description reads "assemble the 5-state
    psi-angle error model of the horizontal INS drift from the
    specific forces, discretize it into the state transition matrix,
    predict the position, velocity and heading error states and their
    covariance between GNSS fixes, and apply the GNSS position
    measurement update that drives the estimated error state toward
    the innovation through the Kalman gain". The new leaf corrects the
    inertial position from terrain heights, not from GNSS fixes; it
    carries no psi-angle model, no heading error state and no specific
    forces.
  - coverage-path-planning (gnc-autonomy/guidance, same family) OWNS
    the boustrophedon survey swath model; its body states "The model
    assumes flat terrain, constant cruise speed, no wind and turns"
    and its scripts carry "sensor altitude above the terrain" as a
    swath-width input. "Terrain" there is the flat-ground assumption
    of a path-planning strip pattern (lawnmower lines, swath width,
    pass count), never a measured elevation profile and never an
    aiding source.
  - Whole-tree greps at prep: "tercom|sitan|digital-elevation|radar-
    altimeter" = 0 hits in every SKILL.md of the skills tree and 0
    hits in eval/hit1-corpus.yaml (grep -c 0 per token); "terrain" =
    0 hits in all gnc-autonomy navigation SKILL.md files, with the
    only gnc-autonomy occurrences the two coverage-path-planning
    "flat terrain" assumption lines quoted above plus two docstring
    hits in its scripts. The remaining whole-tree "terrain" hits are
    airborne-weather-radar (ground-clutter beam geometry: "The angle
    to the terrain at that range is atan((terrain - own_alt) /
    slant_range). Clutter risk exists when the lowest beam edge lies
    below the terrain angle", a tilt-setting clutter check, never a
    navigation measurement), satellite-coverage (elevation-mask
    clearance: "typical masks run 5-10 deg to clear terrain and
    atmosphere"), and mil-std-1797a (flight phase category A example
    "terrain following", a handling-qualities phase label).
- Standards id: arp4754a (present in standards-map.yaml at line 38,
  gated: true, SAE proprietary-sold; name + paraphrase only, no
  verbatim sections or tables). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Aid an unaided inertial navigation solution from terrain, with no GNSS
available: correlate a measured radar-altimeter terrain profile against
a stored digital elevation model strip and refine the match with a
linearized terrain-slope measurement update in the SITAN point-mass
form. Build the DEM strip by sampling a deterministic rolling-terrain
surface (four sinusoid terms) on a 25 m grid (the stored strip is the
only terrain information the correlator sees; the analytic formula
exists only to build the strip). Along the INS indicated track, convert
each radar-altimeter clearance measurement to a measured terrain
elevation z_i = A_ins - c_i with A_ins the INS indicated barometric
altitude (a constant here, carrying a hidden vertical error dA). Run
the TERCOM stage: for every candidate offset (dx_c, dy_c) on the search
grid, resample the DEM along the candidate-corrected track
(x_ind_i - dx_c, y_ind_i - dy_c), correlate the measured profile with
the DEM profile by the Pearson coefficient r and the mean squared
deviation, and take the best-match offset as the coarse estimate of the
INS horizontal position error e = (e_east, e_north), where e is the
indicated-minus-true error (450 m east, 180 m north in the demo). The
best-match offset estimates e to within one grid step (the true error
450/180 m is off the 100 m candidate grid, leaving a 53.85 m coarse
residual). Run the fine SITAN point-mass stage from the coarse
correction dr0 = (-dx_best, -dy_best), where dr is the correction ADDED
to the INS indicated position (p_corrected = p_ind + dr, true
correction dr_true = -e): keep a bank of 13 by 13 candidate
corrections at 10 m spacing around dr0, give each mass a scalar
vertical-bias Kalman state, update the mass weights from the terrain
height likelihood of each epoch measurement (innovation
y_k = z_i - h(pos_k) - dA_k against the DEM height at the hypothesis
position, innovation variance S_k = P_k + R), take the weighted
centroid, and apply the linearized terrain-slope measurement update at
the centroid: H = [dh/dx, dh/dy, 1.0] with the slope row from central
differences of the stored grid and the unit vertical-bias column, Kalman
gain K = P H^T (H P H^T + R)^-1 on the 3 by 3 centroid covariance of
(east correction, north correction, vertical bias). Report the
correlation surface (r and MSD over the candidate grid), the best-match
offset, the corrected inertial position after the fine stage with the
per-axis 1-sigma from the point-mass covariance, the recovered vertical
bias, and the innovation, innovation variance and gain of each slope
update that gate the map-aided navigation output. Deterministic
offline: no RNG, no imports beyond math, pure stdlib. Does NOT do:
raw-pseudorange or carrier measurement updates with clock states
(tightly-coupled-ins-gnss); GNSS position-fix updates or the psi-angle
error model (ins-gnss-integrated-filter); GNSS doppler velocity fixes
(gnss-doppler-velocity-positioning); code-carrier smoothing
(gnss-carrier-smoothing); RAIM fault detection or protection levels
(gnss-raim-fde); DOP geometry analysis (dilution-of-precision); INS
error growth, mechanization, Schuler tuning, alignment or INS/GPS
integration scoping (inertial-navigation); angle-only bearing
localization (bearing-only-localization); frame-conversion utilities
(navigation-frames); single-state Kalman recursion design rules
(kalman-filter-design); boustrophedon or lawnmower survey swath
planning (coverage-path-planning); weather-radar tilt, clutter or echo
analysis (airborne-weather-radar); satellite ground-swath coverage
(satellite-coverage); the rotorcraft height-velocity demonstration
flight-test reduction from baro/radar altitude traces
(rotorcraft-height-velocity-diagram-test); generic time-delay
estimation by cross-correlation (cross-correlation-analysis). The DEM
is a given stored strip: no DEM creation, georeferencing, resampling or
terrain database management. Terrain-following/terrain-avoidance
guidance and terrain-following flight phase classification are out of
scope. The radar altimeter measures geometric clearance; the vertical
INS error dA is a constant bias over the profile window and the
altitude channel is not mechanized.

## Model (implement exactly)

Pure stdlib, math only, deterministic (no RNG anywhere, not even
seeded). Module constants: DEM_X0 = 3800.0 m, DEM_Y0 = -600.0 m,
DEM_D = 25.0 m, DEM_NX = 293, DEM_NY = 113, DEM_BASE = 420.0 m, and the
terrain term table TERMS = [(62.0, 1.00, 0.00, 2100.0, 0.55),
(47.0, 0.00, 1.00, 1500.0, 1.25), (30.0, 0.75, 0.66, 2900.0, 0.15),
(16.0, 0.50, -0.87, 760.0, 0.90)] with rows (amplitude m, ux, uy,
wavelength m, phase rad). Filter defaults: R_MEAS = 2.25 m^2,
Q_BIAS = 0.02 m^2, P0_BIAS = 100.0 m^2. Demo-track constants for the
worked example: DS = 200.0 m sample spacing, X_TRUE0 = 5000.0 m,
Y_TRUE = 600.0 m, E_EAST = 450.0 m, E_NORTH = 180.0 m, A_TRUE = 700.0 m,
DA_TRUE = 15.0 m.

Defining relations (pin these exactly; every function below derives
from them):
- DEM surface: h(x, y) = DEM_BASE + sum over TERMS of
  A * sin(2*pi*(ux*x + uy*y)/L + phase), x east and y north in metres.
  The strip stores h at (DEM_X0 + jx*DEM_D, DEM_Y0 + jy*DEM_D) for
  jx in 0..DEM_NX-1, jy in 0..DEM_NY-1 (east 3800..11100 m, north
  -600..2200 m). The correlator reads ONLY the stored grid (bilinear
  interpolation); the analytic formula is not visible past the strip
  builder. The demo track and every candidate path lie exactly on grid
  nodes (spacing 200 m and candidate steps 100 m are multiples of the
  25 m grid), so bilinear reconstruction is exact in the worked
  example and the identity checks are float-exact.
- Measurement: radar clearance c_meas_i = A_TRUE - h_true_i + eta_i
  with eta_i the deterministic mismatch offsets
  eta_i = 1.7*sin(0.4 + 2*pi*i/11) + 0.9*sin(1.3 + 2*pi*i/6) +
  0.55*sin(2.0 + 2*pi*i/4) (RMS 1.451 m, radar-altimeter plus DEM
  error lumped, no RNG). Measured terrain profile
  z_i = A_ins - c_meas_i = h_true_i + DA_TRUE - eta_i with A_ins the
  INS indicated barometric altitude (715.0 m in the demo, carrying the
  hidden DA_TRUE = 15.0 m vertical error).
- INS error: e = (e_east, e_north) = p_ind - p_true, constant over the
  profile window. The TERCOM best-match offset (dx_best, dy_best)
  estimates e; the coarse correction is dr0 = (-dx_best, -dy_best).
- Correction convention: dr is ADDED to the INS indicated position,
  p_corrected = p_ind + dr; the true correction is dr_true = -e
  (-450.0, -180.0 m in the demo). A hypothesis at correction dr_k
  evaluates the DEM at (x_ind_i + dr_k_e, y_ind_i + dr_k_n).
- TERCOM stage: for candidate (dx_c, dy_c), the DEM profile along the
  corrected track is d_i = h_strip(x_ind_i - dx_c, y_ind_i - dy_c).
  Pearson r(dx_c, dy_c) = covariance(z, d)/(sigma_z * sigma_d) and
  MSD(dx_c, dy_c) = mean((z_i - d_i)^2). Best match = argmax r over
  the candidate grid (mean-centered r is immune to the constant DA_TRUE
  height offset; MSD is reported at the best but never selects it).
  The constant vertical bias adds its square to MSD at every candidate:
  the real anchor MSD is 206.4905 m^2 with the 15 m bias versus
  61.7653 m^2 with it removed, while the argmax stays (400, 200).
- SITAN fine stage: bank of (2*half + 1)^2 hypotheses dr_k at spacing
  bd around dr0 (13 by 13 at 10 m, coverage dr0 +/- 60 m, so the
  one-grid-step coarse residual of at most 60 m is always covered).
  Each mass k carries a scalar vertical-bias Kalman state dA_k
  (init 0, P_k init P0_BIAS). Per epoch i (samples advance 200 m):
  (1) predict P_k += Q_BIAS; (2) for each mass, innovation
  y_k = z_i - h_strip(x_ind_i + dr_k_e, y_ind_i + dr_k_n) - dA_k,
  S_k = P_k + R_MEAS, gain k_k = P_k/S_k, dA_k += k_k*y_k,
  P_k = (1 - k_k)*P_k, log-weight += -0.5*(y_k^2/S_k + ln(2*pi*S_k));
  (3) normalize the weights from log space (subtract the max before
  exp); (4) weighted centroid (dr_c, dA_c) and the 3 by 3 weighted
  covariance over (east correction, north correction, vertical bias);
  (5) linearized terrain-slope measurement update at the centroid:
  H = [dh/dx, dh/dy, 1.0] from central differences of the stored grid
  bilinearly interpolated to the centroid position, innovation
  y_c = z_i - h_strip(pos_c) - dA_c, S = H P_c H^T + R_MEAS,
  K = P_c H^T / S, dr_c += K*y_c (first two rows), dA_c += K*y_c
  (third row), P_c = (I - K H) P_c. The epoch state (dr_c, dA_c) after
  the update is the reported fine fix of that epoch.
- Sign of the slope update: with the DEM rising toward +x
  (H east positive), a centroid east of the truth produces a negative
  innovation y_c ~ H*delta, and dr_c += K*y_c moves the correction back
  toward dr_true, so the state error contracts epoch by epoch.

Functions:
- terrain_height(x, y) -> float. Analytic DEM surface of the TERMS
  formula above, used only by the strip builder. ValueError on
  non-finite x or y.
- build_dem_strip() -> list of DEM_NY rows, each DEM_NX floats, h at
  the grid nodes. Deterministic; no arguments.
- dem_height(vals, x, y) -> float. Bilinear interpolation of the
  stored strip at (x, y). ValueErrors: non-finite x or y, point
  outside the strip (x < DEM_X0, y < DEM_Y0, x > DEM_X0 +
  (DEM_NX - 1)*DEM_D, y > DEM_Y0 + (DEM_NY - 1)*DEM_D), malformed
  grid (row count, row length or non-finite values).
- dem_gradient(vals, x, y) -> (gx, gy). Centered differences
  (f[j+1] - f[j-1])/(2*DEM_D) on the stored grid, bilinearly
  interpolated to (x, y). ValueErrors as dem_height.
- clearance_profile_to_terrain(altitude_ins, clearances) -> list
  z_i = altitude_ins - c_i (scalar altitude broadcast over the
  profile). ValueErrors: length mismatch, non-finite inputs,
  empty profile.
- profile_metrics(measured, predicted) -> (r, msd). Pearson r and
  mean squared deviation. ValueErrors: length mismatch, fewer than
  2 samples, non-finite values. Flat guard: a zero-variance series
  returns r = 0.0.
- tercom_match(vals, measured, x_ind, y_ind, dxs, dys) -> dict.
  Full correlation surface over the candidate grid: keys dxs, dys,
  r_rows and msd_rows (one row per dy, one value per dx), r_best,
  dx_best, dy_best, msd_best (MSD at the argmax-r cell), argmax by
  r. ValueErrors: empty dxs or dys, profile length mismatch with
  x_ind/y_ind, off-strip sampling propagated from dem_height.
- sitan_point_mass(vals, profile, x_ind, y_ind, dr0, indices,
  half = 6, spacing = 10.0, r_meas = 2.25, q_bias = 0.02,
  p0_bias = 100.0) -> dict. The fine stage above run over the epoch
  sample indices given. Returns epochs, a list of per-epoch dicts
  (dr_e, dr_n, bias, sigma_e, sigma_n from the updated covariance
  diagonal, slope_e, slope_n, innovation, innovation_variance,
  gain (3-tuple), weight_max, weight_entropy), and final (dr_e,
  dr_n, bias) with the covariance diagonal. ValueErrors: empty
  indices, spacing <= 0, half < 0, r_meas <= 0, q_bias < 0,
  p0_bias <= 0, non-finite inputs, off-strip sampling.

Identities to test (closed form or tolerance-bounded, real anchor
values):
- Exact-match identity: with a clean profile (no mismatch, no bias)
  and the INS error exactly on the candidate grid (500, 200), the
  TERCOM argmax is (500, 200) with r = 1.000000000 and MSD 0.000000
  m^2 (real anchor: the corrected track then lies exactly on the
  profile track, node for node).
- Bias immunity: removing the 15 m constant vertical error from the
  measured profile leaves the TERCOM argmax at (400, 200) unchanged
  (real anchor, identical = True) while the MSD at the best drops from
  206.4905 to 61.7653 m^2, the bias square and the mismatch variance.
- Grid quantization: the true INS error (450, 180) is not
  representable on the 100 m candidate grid; the real-anchor peak sits
  at (400, 200) with r = 0.989515 and leaves a 53.85 m horizontal
  coarse residual that the fine stage must remove.
- Slope row identity: the update row is the DEM slope from the stored
  grid plus the unit bias column, H = [dh/dx, dh/dy, 1.0]; the real
  anchor epoch-0 row is [0.1232, -0.0742, 1.00] at the centroid
  position (6261.3, 574.6) m.
- Fine-stage reduction: the real anchor converges the correction from
  the 53.852 m coarse residual to a 9.389 m final horizontal error
  (2.916 m east, -8.925 m north) in 12 epochs, a factor of 5.7.
- Vertical bias recovery: the fine stage recovers 13.487 m of the
  15.0 m INS altitude error (the 1.5 m shortfall is the nonzero mean
  of the deterministic mismatch over the fine-stage window).
- Determinism; no imports beyond math; no RNG anywhere in the module.

## Worked example

Demo aircraft flying due east over the stored DEM strip at north
600.0 m, true track east 5000.0..9800.0 m, sample spacing 200.0 m, 25
samples. True altitude 700.0 m; the INS indicates 715.0 m (hidden
vertical error 15.0 m). INS horizontal error e = (450.0, 180.0) m, so
the indicated track runs 450 m east and 180 m north of the truth.
Radar clearance c_meas_i = A_TRUE - h_true_i + eta_i with the
deterministic mismatch offsets above (RMS 1.451 m). All values below
are REAL outputs of the prep anchor /tmp/w44spec/anchor_trn.py (stdlib
math, deterministic, exit 0, run under /usr/bin/python3).

DEM strip: origin east 3800 m, north -600 m, spacing 25 m, grid 293 x
113 (east 3800..11100 m, north -600..2200 m). Terrain formula
h = 420.0 + 62.0 sin(2 pi (1.00 x + 0.00 y)/2100.0 + 0.55)
+ 47.0 sin(2 pi (0.00 x + 1.00 y)/1500.0 + 1.25)
+ 30.0 sin(2 pi (0.75 x + 0.66 y)/2900.0 + 0.15)
+ 16.0 sin(2 pi (0.50 x - 0.87 y)/760.0 + 0.90).
Strip statistics: elevation min 266.69 m, max 568.98 m, mean 426.51 m
(rolling terrain, 267 to 569 m MSL); slope magnitude RMS 0.2220 over
the grid nodes, maximum 0.4028, so the strip carries the texture the
correlation needs.

Measured terrain profile z_i = A_ins - c_meas_i (m), samples 0..24
(copy as data, or regenerate from h_true + 15.0 - eta):

- Samples 0-4: 410.435, 369.515, 344.917, 338.265, 347.204.
- Samples 5-9: 366.645, 390.313, 413.563, 433.052, 443.588.
- Samples 10-14: 439.197, 419.466, 392.686, 371.474, 366.708.
- Samples 15-19: 384.193, 421.515, 465.407, 495.856, 497.128.
- Samples 20-24: 466.217, 412.889, 355.267, 314.301, 305.266.

TERCOM stage over the INS indicated track, candidate grid dx
-800..800 m step 100 (17 values), dy -400..400 m step 100 (9 values).
Correlation surface r in the neighborhood of the peak (rows dy, columns
dx):

- dy 0 m: 0.592429, 0.764315, 0.886609, 0.951138, 0.946697, 0.863563,
  0.703107 for dx 100..700 m.
- dy 100 m: 0.601877, 0.786464, 0.916524, 0.983796, 0.978592,
  0.891812, 0.722607.
- dy 200 m: 0.578611, 0.774266, 0.914842, 0.989515, 0.988871,
  0.905609, 0.739093.
- dy 300 m: 0.540817, 0.738222, 0.884689, 0.966218, 0.972164,
  0.896315, 0.739488.
- dy 400 m: 0.512481, 0.700371, 0.842716, 0.923897, 0.932331,
  0.862478, 0.716608.

Best match: r = 0.989515 at offset (dx = 400 m, dy = 200 m), MSD at
the best 206.4905 m^2 (the 15 m bias dominates the MSD floor). TERCOM
estimate of the INS error (400, 200) m against the truth (450, 180) m;
the peak is one grid step from the truth because the true error is off
the 100 m grid. Coarse residual after applying the correction: 50.0 m
east, -20.0 m north, horizontal 53.85 m.

Identity arm (clean profile, no mismatch, no bias, INS error exactly on
the grid at (500, 200) m): correlation surface rows dy 0..400 m over
dx 200..800 m:

- dy 0 m: 0.673328, 0.820188, 0.915343, 0.948646, 0.908556, 0.789908,
  0.603073.
- dy 100 m: 0.697195, 0.853669, 0.952838, 0.985751, 0.942022,
  0.815253, 0.612828.
- dy 200 m: 0.685323, 0.853775, 0.961895, 1.000000, 0.959184,
  0.834169, 0.630236.
- dy 300 m: 0.649275, 0.823995, 0.940042, 0.985379, 0.951299,
  0.834227, 0.639507.
- dy 400 m: 0.612197, 0.782294, 0.898330, 0.946480, 0.917722,
  0.809726, 0.628689.

Identity: best offset (500, 200) equals the truth, r = 1.000000000,
MSD 0.000000 m^2. Bias-immunity arm: with the 15 m altitude error
stripped from the profile, the argmax stays (400, 200) (identical =
True) and the MSD at the best drops to 61.7653 m^2.

SITAN fine stage from the coarse correction dr0 = (-400.0, -200.0) m
(true correction -450.0, -180.0 m): point-mass bank 169 hypotheses at
10 m spacing, coverage dr0 +/- 60 m; initial uniform-bank 1-sigma
37.42 m per axis; coarse residual 50.000 m east, -20.000 m north,
horizontal 53.852 m. Epochs replay samples 6..17 of the recorded
window (200 m of travel per epoch):

- Linearized slope update detail, epoch 0 (sample 6): centroid
  position east 6261.3 m, north 574.6 m, DEM height 383.482 m, slope
  row H = [0.1232, -0.0742, 1.00], innovation y = 0.8256 m,
  innovation variance S = 2.6432 m^2, gain K = (0.4334, -1.8335,
  -0.0406).
- Per-epoch state after the update (dr east, dr north in m; error
  versus dr_true; 1-sigma from the updated covariance; bias in m):
  epoch 0 (sample 6): dr (-388.334, -206.929), err (61.666, -26.929),
    1-sigma (34.92, 37.16), bias 5.972.
  epoch 1 (sample 7): dr (-390.419, -200.718), err (59.581, -20.718),
    1-sigma (35.10, 24.63), bias 6.639.
  epoch 2 (sample 8): dr (-392.797, -209.537), err (57.203, -29.537),
    1-sigma (34.22, 17.48), bias 6.152.
  epoch 3 (sample 9): dr (-426.035, -205.651), err (23.965, -25.651),
    1-sigma (21.98, 16.48), bias 10.328.
  epoch 4 (sample 10): dr (-440.835, -196.713), err (9.165, -16.713),
    1-sigma (11.20, 13.49), bias 13.025.
  epoch 5 (sample 11): dr (-438.230, -197.970), err (11.770, -17.970),
    1-sigma (6.06, 10.09), bias 12.692.
  epoch 6 (sample 12): dr (-438.090, -198.305), err (11.910, -18.305),
    1-sigma (5.19, 7.51), bias 12.643.
  epoch 7 (sample 13): dr (-438.784, -195.985), err (11.216, -15.985),
    1-sigma (5.45, 6.37), bias 13.037.
  epoch 8 (sample 14): dr (-438.589, -196.780), err (11.411, -16.780),
    1-sigma (5.33, 6.52), bias 12.935.
  epoch 9 (sample 15): dr (-443.334, -194.952), err (6.666, -14.952),
    1-sigma (4.27, 6.64), bias 12.933.
  epoch 10 (sample 16): dr (-447.469, -190.265), err (2.531, -10.265),
    1-sigma (4.65, 6.05), bias 13.401.
  epoch 11 (sample 17): dr (-447.084, -188.925), err (2.916, -8.925),
    1-sigma (4.73, 5.35), bias 13.487.

Final SITAN correction: east -447.084 m, north -188.925 m (truth
-450.000, -180.000 m); final error 2.916 m east, -8.925 m north,
horizontal 9.389 m. Final vertical-bias estimate 13.487 m (truth 15.0
m). Fine-stage reduction: coarse horizontal residual 53.85 m to 9.389
m, factor 5.7.

Read-off: with a 1.45 m-RMS radar-altimeter and DEM mismatch on a
267-569 m rolling strip, a 100 m TERCOM grid resolves a 450/180 m INS
error to one grid step (r = 0.9895, 53.85 m residual), and the SITAN
point-mass fine stage with the linearized terrain-slope update pulls
the correction to about 3-9 m per axis (per-axis 1-sigma about 5 m)
while recovering most of the 15 m vertical error, all from radar
clearance against the stored grid, with no GNSS in the loop.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w44spec/anchor_trn.py
(stdlib math, deterministic, exit 0).

## Validation list (contract test must include)

- Strip and truth: build the strip from the TERMS table and constants
  above (east 3800..11100 m, north -600..2200 m); assert the elevation
  extremes (min 266.69, max 568.98, mean 426.51 m within 0.1 m) and
  the slope RMS 0.2220 within 0.001.
- Data: profile z_i as printed above (regenerate from terrain_height +
  15.0 - eta with the mismatch formula for full float exactness, or
  copy the printed values with assert tolerance 0.01 m), x_ind =
  x_true + 450, y_ind = 780 m constant.
- tercom_match on the worked set: argmax at (400, 200) with
  r = 0.989515 within 1e-4 (0.9895 within 1e-3 with transcribed
  inputs), MSD at the best 206.4905 m^2 within 1.0 m^2, dx_best and
  dy_best exactly (400, 200).
- Exact-match identity: clean profile (no bias, no mismatch) with the
  track error exactly (500, 200): argmax (500, 200), r = 1.0 within
  1e-9, MSD 0.0 within 1e-6.
- Bias-immunity identity: the same tercom_match with the 15 m bias
  removed from the profile keeps the argmax (400, 200) and returns MSD
  61.7653 m^2 within 1.0.
- Surface rows: the five dy rows of the worked neighborhood above
  within 5e-4 per cell (transcribed inputs) or 1e-6 (regenerated
  inputs) at dx 100..700 m.
- sitan_point_mass from dr0 = (-400.0, -200.0) over samples 6..17:
  epoch-0 detail row H = [0.1232, -0.0742, 1.00] within 1e-3,
  innovation 0.8256 m within 0.01, innovation variance 2.6432 m^2
  within 0.01, gain (0.4334, -1.8335, -0.0406) within 0.005; the
  final correction (-447.084, -188.925) within 0.5 m per axis (final
  horizontal error 9.389 m within 1.0 m); the final bias 13.487 m
  within 0.5 m; the per-epoch 1-sigma sequence within 1.0 m of the
  printed values.
- Correction convention: p_corrected = p_ind + dr recovers the true
  track to within the final error; dr_true = -e.
- ValueErrors across the module: dem_height and dem_gradient off strip
  and non-finite; malformed grid; clearance_profile_to_terrain length
  mismatch and non-finite input; profile_metrics length mismatch,
  fewer than 2 samples and zero-variance flat guard; tercom_match
  empty dxs/dys and length mismatch; sitan_point_mass empty indices,
  spacing <= 0, half < 0, r_meas <= 0, q_bias < 0, p0_bias <= 0.
- Determinism; no imports beyond math; no RNG anywhere in the module.

## Corpus fragment (eval/hit1-wave44-terrain-referenced-navigation.yaml)

Query 1 (copy verbatim):
  "estimate the along-track and cross-track position error of an
  unaided inertial navigation solution by matching a measured
  radar-altimeter terrain profile against a stored digital elevation
  model strip with TERCOM-style grid correlation and report the
  correlation surface and the best-match position offset"
  intent: "gnc-autonomy; TERCOM terrain contour matching of a
  radar-altimeter terrain profile against a stored DEM strip, the
  correlation surface and the best-match along-track and cross-track
  offset that corrects the inertial position"
  expected_skill: "gnc-autonomy/navigation/
  terrain-referenced-navigation"
Query 2 (copy verbatim):
  "run a point-mass terrain-referenced navigation update with the
  linearized terrain-slope measurement model to correct the inertial
  position from a radar-altimeter clearance measurement against the
  stored digital elevation model"
  intent: "gnc-autonomy; SITAN point-mass fine stage with the
  linearized terrain-slope measurement update correcting the inertial
  position error from radar-altimeter height over digital terrain"
  expected_skill: "gnc-autonomy/navigation/
  terrain-referenced-navigation"
Task ids: w44-terrain-referenced-navigation-1 and -2. Prep grep of
eval/hit1-corpus.yaml: "tercom", "sitan", "digital-elevation",
"radar-altimeter", "terrain-referenced", "terrain-slope" all return
ZERO hits, and "terrain" returns ZERO hits (grep -c 0). The
terrain-adjacent tasks that do exist all route elsewhere: the
w29-coverage-path-planning tasks ("plan a boustrophedon coverage path
for a 1200 by 800 m aerial survey at 120 m altitude with 60 degree
cross-track FOV and 25 percent side overlap: swath width, track
spacing, pass count, total length and survey time") own the survey
swath strip pattern; w31-airborne-weather-radar-1/-2 route on storm-
cell tilt, reflectivity and echo level ("convert radar reflectivity
factor to rainfall rate with the marshall palmer z-r relation and rate
the echo level for a cockpit weather display"), never on a navigation
measurement; w22-part107-sora-1/-2 route on part-107 and SORA
applicability and air-risk class; w17-satellite-coverage-1/-2 route on
access-circle and orbital swath geometry from the minimum elevation
angle; the inertial-navigation tasks route on accelerometer-bias error
growth and Schuler/strapdown/gyrocompass scoping ("estimate the
position error growth of the inertial navigation system from the
accelerometer bias double integration"); the w8-dilution-of-precision
tasks route on satellite elevation-mask and PDOP geometry; the w43-
rotorcraft-height-velocity-diagram-test task consumes "baro/radar
altitude traces" to measure height loss in a flight-test demonstration;
uc2 routes on pressure-unit conversion for the altimeter setting; and
w29-cross-correlation-analysis-1/-2 route on generic time-delay lag
estimation and autocorrelation ("estimate the time delay between two
sampled channels with cross-correlation: find the peak lag and the
normalized correlation coefficient"), a signal-processing domain with
no DEM, no terrain profile and no position correction. None of these
touches DEM matching, a correlation surface over position offsets, or
a terrain-slope update, so the two queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must aid an unaided inertial
navigation solution from terrain with no GNSS available:" and include
the correlation surface, the best-match offset, the terrain-slope
measurement update, the corrected inertial position and the recovered
vertical bias from the Claim. First tag: terrain-referenced-navigation.
Additional tags ONLY: tercom-correlation, radar-altimeter-profile,
digital-elevation-model-matching, terrain-slope-update, sitan-point-
mass, ins-position-correction. NEVER single generic words (terrain,
navigation, correlation, altitude, elevation, radar, altimeter,
profile, correction, matching, position, filter, kalman, ins) and
NEVER tags owned by siblings: the GNSS and pure-INS aiding tags of the
navigation pack (raw-pseudorange-update, ins-gnss-tight-coupling,
clock-state-filter, pseudorange-los-geometry, ins-error-state-ekf,
error-state-filter, loosely-coupled-integration, gnss-position-update,
ins-drift-correction, ins-gps-integration, strapdown, gimbaled, gyro-
drift, accelerometer-bias, schuler, gyrocompass, inertial-measurement-
unit, pseudorange-positioning, gnss-position-fix, receiver-clock-bias,
carrier-phase-smoothing, hatch-filter-recursion, doppler-positioning,
receiver-velocity-fix, raim, horizontal-protection-level,
dilution-of-precision, bearing-only-localization, kalman-filter-
design, navigation-frames), the swath tags of coverage-path-planning
(boustrophedon, lawnmower, swath-width, survey-strip, track-spacing,
side-overlap) and of satellite-coverage (orbital-swath, access-circle,
elevation-mask), the radar tags of airborne-weather-radar (weather-
radar-tilt, reflectivity-rainfall, marshall-palmer, echo-level,
ground-clutter-check), the lag tags of cross-correlation-analysis
(time-delay-estimation, cross-correlation-peak-lag, autocorrelation,
zero-lag-energy), the part107 tags of part107-sora, and the flight-
phase "terrain-following" label of mil-std-1797a. 50-150 words, <=1000
chars, no em dash, no content-policy sweep term (the banned word from
the builder kit), action verb present. Recommended wording (outputs in
Claim order): "Use when you must aid an unaided inertial navigation
solution from terrain with no GNSS available: correlate a measured
radar-altimeter terrain profile (INS barometric altitude minus radar
clearance) sampled along the INS indicated track against a stored
digital elevation model strip, form the TERCOM-style correlation
surface over the candidate along-track and cross-track offsets, and
take the best-match offset as the coarse position correction; then run
the point-mass SITAN fine stage, a bank of candidate corrections with
per-mass terrain-height likelihood updates and the linearized terrain-
slope measurement update (slope row [dh/dx, dh/dy] with the unit
vertical-bias column) that refines the inertial position correction
epoch by epoch. Produces the correlation surface and the best-match
offset, the corrected INS position with the per-axis 1-sigma from the
point-mass covariance, the recovered vertical bias, and the innovation,
innovation variance and gain of each slope update that gate the
map-aided navigation output. Trigger: terrain referenced navigation,
tercom correlation, digital elevation model matching, terrain slope
update, radar altimeter profile, point mass sitan, ins position
correction." The GNSS observable tokens (pseudorange, doppler, carrier
phase, clock bias, satellite line of sight), the GNSS-fix tokens
(gnss position update, position fix) and the survey tokens (swath,
boustrophedon, lawnmower, coverage path) must not appear.
