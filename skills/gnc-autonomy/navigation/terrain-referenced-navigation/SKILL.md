---
name: terrain-referenced-navigation
description: "Use when you must aid an unaided inertial navigation solution from terrain with no GNSS available: correlate a measured radar-altimeter terrain profile (INS altitude minus radar clearance) along the INS indicated track against a stored digital elevation model strip, form the TERCOM correlation surface over the candidate along-track and cross-track offsets, and take the best-match offset as the coarse position correction. Then run the point-mass SITAN fine stage, per-mass terrain-height likelihood updates and the linearized terrain-slope measurement update that refine the inertial correction epoch by epoch. Produces the correlation surface and best-match offset, the corrected inertial position with per-axis 1-sigma, the recovered vertical bias, and each slope update's innovation, variance and gain. Trigger: terrain referenced navigation, tercom correlation, digital elevation model matching, terrain slope update, radar altimeter profile, point mass sitan, ins position correction."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [terrain-referenced-navigation, tercom-correlation, radar-altimeter-profile, digital-elevation-model-matching, terrain-slope-update, sitan-point-mass, ins-position-correction]
  version: 0.1.0
  author: AeroSkills
---

# Terrain-Referenced Navigation (gnc-autonomy/navigation/terrain-referenced-navigation)

Use when you must aid an unaided inertial navigation solution from
terrain with no GNSS available. This leaf implements the classic
terrain-referenced navigation pair: a TERCOM-style grid correlation of
a measured radar-altimeter terrain profile against a stored digital
elevation model (DEM) strip that estimates the INS horizontal position
error to one grid step, followed by a SITAN point-mass fine stage with a
linearized terrain-slope measurement update that refines the correction
epoch by epoch and recovers the vertical INS altitude bias. The radar
altimeter measures geometric clearance; the INS indicated track is a
GIVEN input (never mechanized, never re-integrated), and no GNSS
observable of any kind appears in the loop. Deterministic offline: pure
stdlib math, no RNG. It pairs with inertial-navigation (the INS error
growth this leaf consumes as an input), tightly-coupled-ins-gnss and
ins-gnss-integrated-filter (the GNSS-aided alternatives this leaf
replaces when no GNSS is available), and kalman-filter-design (the
single-state recursions reused per mass).

## Domain quick reference

- Stored DEM strip: analytic rolling terrain sampled on a 25 m grid,
  origin east 3800 m, north -600 m, grid 293 x 113 nodes (east 3800..
  11100 m, north -600..2200 m). Surface h(x, y) = 420.0 + 62.0 sin(2 pi
  x / 2100.0 + 0.55) + 47.0 sin(2 pi y / 1500.0 + 1.25) + 30.0 sin(2 pi
  (0.75 x + 0.66 y) / 2900.0 + 0.15) + 16.0 sin(2 pi (0.50 x - 0.87 y) /
  760.0 + 0.90), east x and north y in metres. The analytic formula
  exists only to BUILD the strip (terrain_height, build_dem_strip); the
  correlator reads ONLY the stored grid through dem_height (bilinear)
  and dem_gradient (centered differences (f[j + 1] - f[j - 1]) / (2 *
  25) at the cell nodes, bilinearly interpolated).
- Measurement: radar clearance c_i = A_true - h_true_i + eta_i with the
  deterministic mismatch offsets eta_i = 1.7 sin(0.4 + 2 pi i / 11) +
  0.9 sin(1.3 + 2 pi i / 6) + 0.55 sin(2.0 + 2 pi i / 4) (RMS 1.451 m,
  radar-altimeter plus DEM error lumped, no RNG). The measured terrain
  profile is z_i = A_ins - c_i (clearance_profile_to_terrain), with
  A_ins the INS indicated barometric altitude carrying the hidden
  vertical error dA.
- INS error convention: e = p_ind - p_true is constant over the profile
  window. The TERCOM best-match offset (dx_best, dy_best) estimates e;
  the coarse correction is dr0 = (-dx_best, -dy_best).
- Correction convention: dr is ADDED to the INS indicated position,
  p_corrected = p_ind + dr; the true correction is dr_true = -e. A
  hypothesis at dr_k evaluates the DEM at (x_ind_i + dr_k_e, y_ind_i +
  dr_k_n). In the worked example e = (450.0, 180.0) m and dr_true =
  (-450.0, -180.0) m.
- TERCOM stage: for candidate (dx, dy) the DEM profile along the
  corrected track is d_i = h_strip(x_ind_i - dx_c, y_ind_i - dy_c).
  Pearson r = covariance(z, d) / (sigma_z * sigma_d) and MSD =
  mean((z_i - d_i)^2) come from profile_metrics; the best match is the
  argmax r over the candidate grid (mean-centered r is immune to the
  constant vertical bias; MSD is reported at the best but never selects
  it).
- SITAN point-mass stage (filter defaults R_MEAS = 2.25 m^2, Q_BIAS =
  0.02 m^2, P0_BIAS = 100.0 m^2): a bank of (2 * half + 1)^2 candidate
  corrections at spacing around dr0 (13 by 13 at 10 m, dr0 +/- 60 m)
  covers the one-grid-step coarse residual. Each mass k carries a scalar
  vertical-bias Kalman state (dA_k init 0, P_k init P0_BIAS). Per epoch:
  P_k += Q_BIAS, innovation y_k = z_i - h_strip(pos_k) - dA_k with S_k =
  P_k + R_MEAS and gain k_k = P_k / S_k, dA_k += k_k * y_k, P_k = (1 -
  k_k) * P_k, log weight += -0.5 * (y_k^2 / S_k + ln(2 pi S_k)); weights
  normalize from log space (subtract the max before exp).
- Linearized terrain-slope update at the weighted centroid: H = [dh/dx,
  dh/dy, 1.0] (slope row from dem_gradient plus the unit vertical-bias
  column), innovation y_c = z_i - h(pos_c) - dA_c, S = H P_c H^T +
  R_MEAS, gain K = P_c H^T / S on the 3 by 3 centroid covariance of
  (east correction, north correction, vertical bias), then P_c = (I - K
  H) P_c. With the DEM rising toward +x, a centroid east of the truth
  gives a negative innovation y_c ~ H * delta and dr_c += K * y_c moves
  the correction back toward dr_true, contracting the state error epoch
  by epoch.

## Workflow

1. Build the DEM strip on the 25 m grid with build_dem_strip; the strip
   statistics (elevation min 266.69 m, max 568.98 m, mean 426.51 m;
   slope magnitude RMS 0.2220) confirm the stored grid carries the
   texture the correlation needs.
2. Convert the radar-altimeter profile to the measured terrain profile
   z_i = A_ins - c_i with clearance_profile_to_terrain (scalar INS
   barometric altitude broadcast, or a per-sample altitude sequence).
3. Run the TERCOM grid correlation with tercom_match over the INS
   indicated track (x_ind_i, y_ind_i): resample the stored DEM along
   each candidate-corrected track, correlate with the measured profile
   through profile_metrics, and read the correlation surface rows plus
   the best-match offset (dx_best, dy_best) that estimates the INS
   horizontal position error. The coarse correction is dr0 =
   (-dx_best, -dy_best).
4. Run the fine SITAN point-mass stage with sitan_point_mass from dr0
   over the epoch sample indices: the per-mass terrain-height likelihood
   updates concentrate the bank, the weighted centroid feeds the
   linearized terrain-slope measurement update each epoch, and the
   per-epoch states (dr, bias, per-axis 1-sigma, slope row, innovation,
   innovation variance, gain) plus the final correction and recovered
   vertical bias gate the map-aided navigation output.
5. Sanity-check the result against the deterministic checks (the
   corrected position p_ind + dr recovers the true track, the final
   horizontal error, the recovered vertical bias) and run the contract
   test.

## Worked example

Demo aircraft flying due east over the stored strip at north 600.0 m,
true track east 5000.0..9800.0 m, sample spacing 200.0 m, 25 samples.
True altitude 700.0 m; the INS indicates 715.0 m (hidden vertical error
15.0 m). INS horizontal error e = (450.0, 180.0) m, so the indicated
track runs 450 m east and 180 m north of the truth. Radar clearance
carries the deterministic mismatch above (RMS 1.451 m). All values are
REAL outputs of this module, matching the wave-44 spec anchors.

- Measured terrain profile z_0..z_24 (m): 410.435, 369.515, 344.917,
  338.265, 347.204, 366.645, 390.313, 413.563, 433.052, 443.588,
  439.197, 419.466, 392.686, 371.474, 366.708, 384.193, 421.515,
  465.407, 495.856, 497.128, 466.217, 412.889, 355.267, 314.301,
  305.266.
- TERCOM stage over the INS indicated track, candidate grid dx -800..
  800 m step 100 (17 values), dy -400..400 m step 100 (9 values): best
  match r = 0.989515 at offset (dx = 400 m, dy = 200 m) with MSD at the
  best 206.4905 m^2 (the 15 m bias dominates the MSD floor). TERCOM
  estimates the INS error at (400, 200) against the truth (450, 180);
  the peak sits one grid step from the truth because the true error is
  off the 100 m candidate grid. Coarse residual after applying dr0 =
  (-400, -200): 50.0 m east, -20.0 m north, horizontal 53.85 m.
- Identity arm (clean profile, no bias, no mismatch, INS error exactly
  on the grid at (500, 200)): argmax (500, 200), r = 1.000000000, MSD
  0.000000 m^2. Bias-immunity arm (15 m bias stripped from the profile):
  argmax stays (400, 200) (identical = True) and the MSD at the best
  drops to 61.7653 m^2.
- SITAN fine stage from dr0 = (-400.0, -200.0), 169 hypotheses at 10 m
  spacing (coverage dr0 +/- 60 m), replaying samples 6..17 (200 m of
  travel per epoch). Epoch-0 slope-update detail (sample 6): centroid
  position east 6261.3 m, north 574.6 m, DEM height 383.482 m, slope
  row H = [0.1232, -0.0742, 1.00], innovation y = 0.8256 m, innovation
  variance S = 2.6432 m^2, gain K = (0.4334, -1.8335, -0.0406).
- Final SITAN correction: east -447.084 m, north -188.925 m (truth
  -450.000, -180.000 m); final error 2.916 m east, -8.925 m north,
  horizontal 9.389 m. Final vertical-bias estimate 13.487 m (truth 15.0
  m). Fine-stage reduction: coarse horizontal residual 53.85 m to 9.389
  m, factor 5.7.

Read-off: with a 1.45 m-RMS radar-altimeter and DEM mismatch on a
267-569 m rolling strip, a 100 m TERCOM grid resolves a 450/180 m INS
error to one grid step (r = 0.9895, 53.85 m residual), and the SITAN
point-mass fine stage with the linearized terrain-slope update pulls the
correction to about 3-9 m per axis (per-axis 1-sigma about 5 m) while
recovering 13.5 m of the 15 m vertical error, all from radar clearance
against the stored grid, with no GNSS in the loop.

## Verification

- Confirm build_dem_strip statistics (min 266.69, max 568.98, mean
  426.51 m within 0.1 m; slope magnitude RMS 0.2220 within 0.001).
- Confirm tercom_match on the worked set returns the argmax at exactly
  (400, 200) with r = 0.989515 (within 1e-4) and MSD at the best
  206.4905 m^2 (within 1.0 m^2); the clean-profile identity returns
  (500, 200) with r = 1.0 (within 1e-9) and MSD 0.0 (within 1e-6); the
  bias-immunity arm keeps (400, 200) with MSD 61.7653 m^2 (within 1.0).
- Confirm the five correlation-surface rows (dy 0..400 m over dx 100..
  700 m) match the anchors within 5e-4 per cell.
- Confirm sitan_point_mass from dr0 = (-400.0, -200.0) over samples
  6..17 gives the epoch-0 slope row H = [0.1232, -0.0742, 1.00] within
  1e-3, innovation 0.8256 m within 0.01, innovation variance 2.6432 m^2
  within 0.01, gain (0.4334, -1.8335, -0.0406) within 0.005, the final
  correction (-447.084, -188.925) within 0.5 m per axis (final
  horizontal error 9.389 m within 1.0 m) and the final bias 13.487 m
  within 0.5 m, with the per-epoch 1-sigma sequence within 1.0 m of the
  anchor values.
- Confirm the correction convention: p_corrected = p_ind + dr recovers
  the true track to within the final error, and dr_true = -e.
- Confirm ValueError rejection of non-physical inputs across the module
  (off-strip and non-finite sampling, malformed grid, empty profiles
  and candidate grids, length mismatches, empty epoch indices,
  non-positive spacing / r_meas / p0_bias, negative half / q_bias).
- Run the contract test offline: python3
  scripts/test_terrain_referenced_navigation.py (deterministic, exits
  0). The same test passes under the pre-push hook interpreter
  (~/.pyenv/versions/3.13.12/bin/python3).

## Related leaves

- gnc-autonomy/navigation/inertial-navigation: the INS error growth this
  leaf consumes as a given, unaided input.
- gnc-autonomy/navigation/tightly-coupled-ins-gnss: the raw-GNSS
  measurement update alternative when GNSS observables exist.
- gnc-autonomy/navigation/ins-gnss-integrated-filter: the GNSS
  position-update alternative for aided inertial filtering.
- gnc-autonomy/navigation/gnss-pseudorange-positioning: the GNSS
  position solution this leaf replaces when no GNSS is available.
- gnc-autonomy/navigation/kalman-filter-design: the single-state Kalman
  recursion reused per mass in the point-mass bank.
- gnc-autonomy/navigation/navigation-frames: frame conventions for the
  east/north grid coordinates.
- gnc-autonomy/guidance/coverage-path-planning: survey path planning
  over (assumed flat) terrain, the planning-side neighbor.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_terrain_referenced_navigation.py

The test covers the DEM strip statistics, node-exact bilinear
reconstruction, the radar-altimeter to terrain conversion, the TERCOM
worked match and its correlation-surface rows, the exact-match and
bias-immunity identities, the SITAN epoch-0 slope-update detail, the
final correction and vertical-bias recovery, the per-epoch 1-sigma
sequence, the correction-convention round trip, determinism, and
ValueError rejection of every non-physical input class listed above.

## Pitfalls

- Feeding the INS indicated altitude error into the DEM correlation: the
  measured profile z_i = A_ins - c_i carries the constant vertical bias
  dA, but mean-centered Pearson r is immune to it, so the TERCOM argmax
  is unbiased; the bias square only lifts the MSD floor (206.4905 m^2
  with the 15 m bias versus 61.7653 m^2 without). Never let MSD select
  the offset, and never strip a bias you cannot prove is constant over
  the window.
- Trusting the coarse TERCOM offset as the final correction: the true
  INS error (450, 180) m is off the 100 m candidate grid, so the argmax
  lands one grid step away at (400, 200) and leaves a 53.85 m residual.
  The fine SITAN stage exists exactly to remove that residual; report
  the coarse offset only as dr0 for the point-mass bank.
- Treating the terrain height as a direct measurement of position: the
  height residual only constrains position through the local slope row
  H = [dh/dx, dh/dy, 1.0], so epochs over flat strip regions (slope near
  zero) barely move the east/north correction. The bank coverage (dr0
  +/- 60 m at 10 m spacing) must always cover the residual from the
  coarse stage or the filter locks onto a false height match.
- Confusing the sign conventions: dr is ADDED to the INS indicated
  position (p_corrected = p_ind + dr, dr_true = -e), while the TERCOM
  offset (dx_best, dy_best) is the estimated INS error e in
  indicated-minus-true form. The coarse correction is dr0 =
  (-dx_best, -dy_best); a sign slip here doubles the error instead of
  removing it.
- Forgetting the vertical bias state: without the per-mass dA_k Kalman
  state and the unit vertical-bias column in H, the constant INS
  altitude error aliases directly into the height innovations and biases
  the position estimate by the slope-to-bias ratio; the recovered bias
  (13.487 m of the 15.0 m truth in the worked example) is a required
  output, not a side effect.
- Sampling the analytic terrain instead of the stored grid: the DEM is a
  given stored strip and the correlator reads only the stored grid
  through bilinear dem_height / centered-difference dem_gradient. The
  analytic TERMS formula exists only inside the strip builder.
- This leaf does NOT do: raw-pseudorange or carrier measurement updates
  with clock states (tightly-coupled-ins-gnss), GNSS position-fix
  updates or the psi-angle error model (ins-gnss-integrated-filter),
  GNSS doppler velocity fixes (gnss-doppler-velocity-positioning),
  code-carrier smoothing (gnss-carrier-smoothing), RAIM fault detection
  (gnss-raim-fde), DOP geometry (dilution-of-precision), INS error
  growth, mechanization, Schuler tuning, alignment or INS/GPS
  integration scoping (inertial-navigation), angle-only bearing
  localization (bearing-only-localization), frame-conversion utilities
  (navigation-frames), single-state Kalman design rules
  (kalman-filter-design), boustrophedon survey swath planning
  (coverage-path-planning), or terrain-following/terrain-avoidance
  guidance. No DEM creation, georeferencing or terrain database
  management: the strip is a given input.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_terrain_referenced_navigation.py

The test exercises the full workflow of this SKILL.md: building the DEM
strip (step 1), converting the radar-altimeter profile (step 2), the
TERCOM grid correlation surface and best-match offset over the INS
indicated track (step 3), and the SITAN point-mass fine stage with the
linearized terrain-slope measurement update, per-epoch states and
recovered vertical bias (step 4). It must pass under /usr/bin/python3
and under the pre-push hook interpreter; both exits 0, offline, in well
under 20 s.

## Compliance

- Standards referenced, not reproduced: arp4754a (SAE, proprietary-sold)
  frames the airborne-system development assurance context for the
  navigation function; name and paraphrase only, per standards-map.yaml.
- The TERCOM and SITAN relations above are standard published
  navigation methodology (terrain contour matching and point-mass
  terrain-referenced navigation), summary-only.
- compliance: STANDARDS-REF, gated: false.
