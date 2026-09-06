"""Contract test: terrain-referenced-navigation (gnc-autonomy/navigation).

Deterministic offline unittest (stdlib only, no RNG) that exercises the
SKILL.md workflow end to end: step 1 builds the digital elevation model
strip on the 25 m grid, step 2 converts the radar-altimeter profile
(INS barometric altitude minus radar clearance) to the measured terrain
profile, step 3 runs the TERCOM grid correlation over the INS indicated
track and reads the correlation surface and the best-match offset, and
step 4 runs the fine SITAN point-mass stage with the linearized
terrain-slope measurement update, the per-mass terrain-height likelihood
updates, the per-epoch 1-sigma and the recovered vertical bias. Real
anchor targets from the wave-44 spec (all values reproduced by this
module to printed precision).

Run: python3 scripts/test_terrain_referenced_navigation.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terrain_referenced_navigation_logic as trn

# Demo constants (worked example of the SKILL.md)
N_SAMPLES = 25
DS = 200.0
X_TRUE0 = 5000.0
Y_TRUE = 600.0
E_EAST = 450.0
E_NORTH = 180.0
A_TRUE = 700.0
DA_TRUE = 15.0
A_INS = A_TRUE + DA_TRUE
DXS = list(range(-800, 801, 100))
DYS = list(range(-400, 401, 100))


def mismatch(i):
    """Deterministic radar-altimeter plus DEM mismatch offsets (m)."""
    return (1.7 * math.sin(0.4 + trn.TWO_PI * i / 11.0) +
            0.9 * math.sin(1.3 + trn.TWO_PI * i / 6.0) +
            0.55 * math.sin(2.0 + trn.TWO_PI * i / 4.0))


def build_demo_data():
    """Workflow steps 1-2: strip, indicated track, measured profile."""
    vals = trn.build_dem_strip()
    x_true = [X_TRUE0 + i * DS for i in range(N_SAMPLES)]
    x_ind = [x_true[i] + E_EAST for i in range(N_SAMPLES)]
    y_ind = [Y_TRUE + E_NORTH] * N_SAMPLES
    h_true = [trn.terrain_height(x_true[i], Y_TRUE) for i in range(N_SAMPLES)]
    c_meas = [A_TRUE - h_true[i] + mismatch(i) for i in range(N_SAMPLES)]
    z = trn.clearance_profile_to_terrain(A_INS, c_meas)
    return vals, x_true, x_ind, y_ind, h_true, z


class TerrainRefNavContractTest(unittest.TestCase):
    """Contract battery for the terrain-referenced navigation leaf."""

    @classmethod
    def setUpClass(cls):
        (cls.vals, cls.x_true, cls.x_ind, cls.y_ind,
         cls.h_true, cls.z) = build_demo_data()

    # -------------------------------------------------------------
    # Workflow step 1: build the DEM strip from the TERMS terrain
    # -------------------------------------------------------------
    def test_strip_elevation_statistics(self):
        """Workflow step 1 (build_dem_strip) yields the stored strip:
        elevation extremes and mean of the rolling 267-569 m MSL strip."""
        vals = self.vals
        elev = [vals[jy][jx] for jy in range(trn.DEM_NY)
                for jx in range(trn.DEM_NX)]
        self.assertAlmostEqual(min(elev), 266.69, delta=0.1)
        self.assertAlmostEqual(max(elev), 568.98, delta=0.1)
        self.assertAlmostEqual(sum(elev) / len(elev), 426.51, delta=0.1)

    def test_strip_slope_rms(self):
        """Workflow step 1: the strip carries correlation texture, slope
        magnitude RMS 0.2220 over the interior grid nodes (max 0.4028)."""
        vals = self.vals
        gmag = []
        for jy in range(1, trn.DEM_NY - 1):
            for jx in range(1, trn.DEM_NX - 1):
                gx = (vals[jy][jx + 1] - vals[jy][jx - 1]) / (2.0 * trn.DEM_D)
                gy = (vals[jy + 1][jx] - vals[jy - 1][jx]) / (2.0 * trn.DEM_D)
                gmag.append(math.hypot(gx, gy))
        rms = math.sqrt(sum(g * g for g in gmag) / len(gmag))
        self.assertAlmostEqual(rms, 0.2220, delta=0.001)
        self.assertLess(max(gmag), 0.41)

    def test_dem_height_matches_node_values_exactly(self):
        """Workflow step 1: bilinear dem_height at a grid node returns
        the stored node value exactly (node-aligned reconstruction)."""
        vals = self.vals
        for (jx, jy) in [(0, 0), (100, 50), (292, 112), (37, 89)]:
            x = trn.DEM_X0 + jx * trn.DEM_D
            y = trn.DEM_Y0 + jy * trn.DEM_D
            self.assertEqual(trn.dem_height(vals, x, y), vals[jy][jx])
        # analytic terrain_height and stored node agree at the nodes
        x = trn.DEM_X0 + 200 * trn.DEM_D
        y = trn.DEM_Y0 + 60 * trn.DEM_D
        self.assertAlmostEqual(trn.dem_height(vals, x, y),
                               trn.terrain_height(x, y), delta=0.0)

    def test_terrain_height_nonfinite_raises(self):
        """Non-physical inputs: the analytic terrain surface rejects
        non-finite x or y."""
        for bad in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaises(ValueError):
                trn.terrain_height(bad, 500.0)
            with self.assertRaises(ValueError):
                trn.terrain_height(5000.0, bad)

    def test_dem_height_off_strip_raises(self):
        """Workflow step 3 sampling guard: the stored digital elevation
        model strip rejects points outside east 3800..11100 m, north
        -600..2200 m."""
        vals = self.vals
        x_max = trn.DEM_X0 + (trn.DEM_NX - 1) * trn.DEM_D
        y_max = trn.DEM_Y0 + (trn.DEM_NY - 1) * trn.DEM_D
        for (x, y) in [(trn.DEM_X0 - 1.0, 500.0),
                       (x_max + 1.0, 500.0),
                       (5000.0, trn.DEM_Y0 - 1.0),
                       (5000.0, y_max + 1.0)]:
            with self.assertRaises(ValueError):
                trn.dem_height(vals, x, y)

    def test_dem_height_nonfinite_raises(self):
        """Non-physical inputs: dem_height rejects non-finite x or y."""
        vals = self.vals
        for bad in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                trn.dem_height(vals, bad, 500.0)
            with self.assertRaises(ValueError):
                trn.dem_height(vals, 5000.0, bad)

    def test_dem_height_malformed_grid_raises(self):
        """Non-physical inputs: a malformed stored grid (wrong row count,
        wrong row length, non-finite value) is rejected."""
        vals = self.vals
        with self.assertRaises(ValueError):
            trn.dem_height(vals[:-1], 5000.0, 500.0)
        bad_len = [row[:-1] for row in vals]
        with self.assertRaises(ValueError):
            trn.dem_height(bad_len, 5000.0, 500.0)
        bad_val = [row[:] for row in vals]
        bad_val[50][50] = float("nan")
        with self.assertRaises(ValueError):
            trn.dem_height(bad_val, 5000.0, 500.0)

    def test_dem_gradient_centered_difference_identity(self):
        """Workflow step 4 slope row: dem_gradient at a grid node equals
        the centered difference (f[j + 1] - f[j - 1]) / (2 * DEM_D) of
        the stored strip, east and north."""
        vals = self.vals
        for (jx, jy) in [(50, 50), (100, 40), (200, 80)]:
            x = trn.DEM_X0 + jx * trn.DEM_D
            y = trn.DEM_Y0 + jy * trn.DEM_D
            (gx, gy) = trn.dem_gradient(vals, x, y)
            ex = (vals[jy][jx + 1] - vals[jy][jx - 1]) / (2.0 * trn.DEM_D)
            ey = (vals[jy + 1][jx] - vals[jy - 1][jx]) / (2.0 * trn.DEM_D)
            self.assertAlmostEqual(gx, ex, delta=0.0)
            self.assertAlmostEqual(gy, ey, delta=0.0)
        # slopes are texture-sized on this strip
        (gx, gy) = trn.dem_gradient(vals, 6261.3, 574.6)
        self.assertAlmostEqual(gx, 0.1232, delta=1e-3)
        self.assertAlmostEqual(gy, -0.0742, delta=1e-3)

    def test_dem_gradient_errors(self):
        """Non-physical inputs: dem_gradient rejects off-strip and
        non-finite sampling and malformed grids like dem_height."""
        vals = self.vals
        with self.assertRaises(ValueError):
            trn.dem_gradient(vals, 100.0, 500.0)
        with self.assertRaises(ValueError):
            trn.dem_gradient(vals, float("nan"), 500.0)
        with self.assertRaises(ValueError):
            trn.dem_gradient(vals[:-1], 5000.0, 500.0)

    # -------------------------------------------------------------
    # Workflow step 2: radar-altimeter profile to measured terrain
    # -------------------------------------------------------------
    def test_clearance_to_terrain_scalar_broadcast(self):
        """Workflow step 2 (clearance_profile_to_terrain): z_i = A_ins -
        c_i with the scalar INS barometric altitude broadcast over the
        radar-altimeter clearance profile."""
        clearances = [100.0, 200.0, 300.0]
        z = trn.clearance_profile_to_terrain(715.0, clearances)
        self.assertEqual(z, [615.0, 515.0, 415.0])

    def test_clearance_to_terrain_per_sample_altitude(self):
        """Workflow step 2: a per-sample altitude sequence converts
        sample by sample, and length mismatch raises ValueError."""
        z = trn.clearance_profile_to_terrain([700.0, 710.0, 720.0],
                                             [100.0, 200.0, 300.0])
        self.assertEqual(z, [600.0, 510.0, 420.0])
        with self.assertRaises(ValueError):
            trn.clearance_profile_to_terrain([700.0, 710.0], [100.0, 200.0, 300.0])

    def test_clearance_to_terrain_errors(self):
        """Non-physical inputs: empty profile, length mismatch and
        non-finite clearance or altitude values raise ValueError."""
        with self.assertRaises(ValueError):
            trn.clearance_profile_to_terrain(715.0, [])
        with self.assertRaises(ValueError):
            trn.clearance_profile_to_terrain(715.0, [100.0, float("nan")])
        with self.assertRaises(ValueError):
            trn.clearance_profile_to_terrain(float("inf"), [100.0])
        with self.assertRaises(ValueError):
            trn.clearance_profile_to_terrain("715", [100.0])

    def test_measured_profile_matches_anchor(self):
        """Workflow step 2 output: the measured terrain profile samples
        z_0..z_24 match the spec anchor table within 0.01 m."""
        anchor = [
            410.435, 369.515, 344.917, 338.265, 347.204,
            366.645, 390.313, 413.563, 433.052, 443.588,
            439.197, 419.466, 392.686, 371.474, 366.708,
            384.193, 421.515, 465.407, 495.856, 497.128,
            466.217, 412.889, 355.267, 314.301, 305.266,
        ]
        self.assertEqual(len(self.z), N_SAMPLES)
        for i in range(N_SAMPLES):
            self.assertAlmostEqual(self.z[i], anchor[i], delta=0.01)

    # -------------------------------------------------------------
    # Workflow step 3: TERCOM grid correlation over the INS track
    # -------------------------------------------------------------
    def test_profile_metrics_perfect_match(self):
        """Workflow step 3 metric: identical profiles give Pearson r =
        1.0 and MSD 0.0; anti-correlation gives r = -1.0."""
        a = [1.0, 2.0, 3.0, 4.0]
        (r, msd) = trn.profile_metrics(a, a)
        self.assertAlmostEqual(r, 1.0, delta=0.0)
        self.assertAlmostEqual(msd, 0.0, delta=0.0)
        (r, msd) = trn.profile_metrics(a, [4.0, 3.0, 2.0, 1.0])
        self.assertAlmostEqual(r, -1.0, delta=1e-12)
        (r, msd) = trn.profile_metrics(a, [5.0, 6.0, 7.0, 8.0])
        self.assertAlmostEqual(r, 1.0, delta=0.0)
        self.assertAlmostEqual(msd, 16.0, delta=1e-12)

    def test_profile_metrics_flat_guard(self):
        """Workflow step 3 flat guard: a zero-variance series returns
        r = 0.0 instead of a divide-by-zero."""
        flat = [3.0, 3.0, 3.0, 3.0]
        ramp = [1.0, 2.0, 3.0, 4.0]
        (r, msd) = trn.profile_metrics(flat, ramp)
        self.assertEqual(r, 0.0)
        (r, msd) = trn.profile_metrics(flat, flat)
        self.assertEqual(r, 0.0)
        self.assertAlmostEqual(msd, 0.0, delta=0.0)

    def test_profile_metrics_errors(self):
        """Non-physical inputs: length mismatch, fewer than 2 samples
        and non-finite values raise ValueError."""
        with self.assertRaises(ValueError):
            trn.profile_metrics([1.0, 2.0], [1.0])
        with self.assertRaises(ValueError):
            trn.profile_metrics([1.0], [1.0])
        with self.assertRaises(ValueError):
            trn.profile_metrics([1.0, float("nan")], [1.0, 2.0])

    def test_tercom_exact_match_identity(self):
        """Workflow step 3 identity: with a clean profile (no mismatch,
        no vertical bias) and the INS error exactly on the 100 m
        candidate grid at (500, 200), the correlation surface peaks at
        exactly (500, 200) with r = 1.0 and MSD 0.0 m^2."""
        z_clean = [self.h_true[i] for i in range(N_SAMPLES)]
        x_ind2 = [self.x_true[i] + 500.0 for i in range(N_SAMPLES)]
        y_ind2 = [Y_TRUE + 200.0] * N_SAMPLES
        res = trn.tercom_match(self.vals, z_clean, x_ind2, y_ind2, DXS, DYS)
        self.assertEqual(res["dx_best"], 500)
        self.assertEqual(res["dy_best"], 200)
        self.assertAlmostEqual(res["r_best"], 1.0, delta=1e-9)
        self.assertAlmostEqual(res["msd_best"], 0.0, delta=1e-6)

    def test_tercom_worked_best_match(self):
        """Workflow step 3 (tercom_match over the INS indicated track):
        the worked profile peaks at offset (400, 200) with r = 0.989515,
        one 100 m grid step from the true INS error (450, 180), MSD at
        the best 206.4905 m^2 (the 15 m vertical bias dominates the MSD
        floor)."""
        res = trn.tercom_match(self.vals, self.z, self.x_ind, self.y_ind,
                               DXS, DYS)
        self.assertEqual(res["dx_best"], 400)
        self.assertEqual(res["dy_best"], 200)
        self.assertAlmostEqual(res["r_best"], 0.989515, delta=1e-4)
        self.assertAlmostEqual(res["msd_best"], 206.4905, delta=1.0)
        # coarse residual after the correction dr0 = (-400, -200)
        res_e = E_EAST - res["dx_best"]
        res_n = E_NORTH - res["dy_best"]
        self.assertAlmostEqual(res_e, 50.0, delta=0.5)
        self.assertAlmostEqual(res_n, -20.0, delta=0.5)
        self.assertAlmostEqual(math.hypot(res_e, res_n), 53.85, delta=0.05)
        self.assertEqual(len(res["r_rows"]), len(DYS))
        self.assertEqual(len(res["r_rows"][0]), len(DXS))

    def test_tercom_surface_rows(self):
        """Workflow step 3 correlation surface: the five dy rows of the
        neighborhood around the peak (dy 0..400 m over dx 100..700 m)
        match the spec anchor rows within 5e-4 per cell."""
        res = trn.tercom_match(self.vals, self.z, self.x_ind, self.y_ind,
                               DXS, DYS)
        anchor_rows = {
            0: [0.592429, 0.764315, 0.886609, 0.951138, 0.946697,
                0.863563, 0.703107],
            100: [0.601877, 0.786464, 0.916524, 0.983796, 0.978592,
                  0.891812, 0.722607],
            200: [0.578611, 0.774266, 0.914842, 0.989515, 0.988871,
                  0.905609, 0.739093],
            300: [0.540817, 0.738222, 0.884689, 0.966218, 0.972164,
                  0.896315, 0.739488],
            400: [0.512481, 0.700371, 0.842716, 0.923897, 0.932331,
                  0.862478, 0.716608],
        }
        cols = list(range(100, 701, 100))
        for dy, anchor_row in anchor_rows.items():
            row = res["r_rows"][DYS.index(dy)]
            for dx, anchor_r in zip(cols, anchor_row):
                self.assertAlmostEqual(row[DXS.index(dx)], anchor_r,
                                       delta=5e-4)

    def test_tercom_bias_immunity(self):
        """Workflow step 3 bias immunity: stripping the 15 m constant
        vertical error from the measured profile leaves the argmax at
        (400, 200) unchanged while the MSD at the best drops from
        206.4905 to 61.7653 m^2 (the bias square and the mismatch
        variance)."""
        res = trn.tercom_match(self.vals, self.z, self.x_ind, self.y_ind,
                               DXS, DYS)
        z_nobias = [self.z[i] - DA_TRUE for i in range(N_SAMPLES)]
        res2 = trn.tercom_match(self.vals, z_nobias, self.x_ind, self.y_ind,
                                DXS, DYS)
        self.assertEqual(res2["dx_best"], res["dx_best"])
        self.assertEqual(res2["dy_best"], res["dy_best"])
        self.assertEqual((res2["dx_best"], res2["dy_best"]), (400, 200))
        self.assertAlmostEqual(res2["msd_best"], 61.7653, delta=1.0)
        # the bias square separates the two MSD floors
        self.assertGreater(res["msd_best"] - res2["msd_best"], 100.0)

    def test_tercom_value_errors(self):
        """Non-physical inputs: empty candidate grids and a profile
        length mismatch with the indicated track raise ValueError."""
        with self.assertRaises(ValueError):
            trn.tercom_match(self.vals, self.z, self.x_ind, self.y_ind,
                             [], DYS)
        with self.assertRaises(ValueError):
            trn.tercom_match(self.vals, self.z, self.x_ind, self.y_ind,
                             DXS, [])
        with self.assertRaises(ValueError):
            trn.tercom_match(self.vals, self.z[:-1], self.x_ind, self.y_ind,
                             DXS, DYS)

    # -------------------------------------------------------------
    # Workflow step 4: SITAN point-mass fine stage from dr0
    # -------------------------------------------------------------
    def _run_sitan(self):
        """Chain workflow step 3 into step 4: coarse correction dr0 from
        the TERCOM best-match offset, fine stage over samples 6..17."""
        res = trn.tercom_match(self.vals, self.z, self.x_ind, self.y_ind,
                               DXS, DYS)
        dr0 = (-float(res["dx_best"]), -float(res["dy_best"]))
        return trn.sitan_point_mass(self.vals, self.z, self.x_ind,
                                    self.y_ind, dr0, list(range(6, 18)))

    def test_sitan_epoch0_slope_update_detail(self):
        """Workflow step 4 epoch-0 detail: the linearized terrain-slope
        measurement update at the weighted centroid (east 6261.3 m,
        north 574.6 m) uses the slope row H = [0.1232, -0.0742, 1.00]
        with innovation 0.8256 m, innovation variance 2.6432 m^2 and
        gain (0.4334, -1.8335, -0.0406)."""
        sit = self._run_sitan()
        e0 = sit["epochs"][0]
        self.assertAlmostEqual(e0["slope_e"], 0.1232, delta=1e-3)
        self.assertAlmostEqual(e0["slope_n"], -0.0742, delta=1e-3)
        self.assertAlmostEqual(e0["innovation"], 0.8256, delta=0.01)
        self.assertAlmostEqual(e0["innovation_variance"], 2.6432, delta=0.01)
        self.assertAlmostEqual(e0["gain"][0], 0.4334, delta=0.005)
        self.assertAlmostEqual(e0["gain"][1], -1.8335, delta=0.005)
        self.assertAlmostEqual(e0["gain"][2], -0.0406, delta=0.005)
        self.assertEqual(len(e0["gain"]), 3)

    def test_sitan_final_correction(self):
        """Workflow step 4 convergence: the fine stage pulls the
        correction from the 53.85 m coarse residual to the final
        (-447.084, -188.925) m (truth -450.000, -180.000 m), a 9.389 m
        horizontal error, a factor-5.7 reduction in 12 epochs."""
        sit = self._run_sitan()
        f = sit["final"]
        self.assertAlmostEqual(f["dr_e"], -447.084, delta=0.5)
        self.assertAlmostEqual(f["dr_n"], -188.925, delta=0.5)
        err_e = f["dr_e"] - (-E_EAST)
        err_n = f["dr_n"] - (-E_NORTH)
        self.assertAlmostEqual(math.hypot(err_e, err_n), 9.389, delta=1.0)
        self.assertLess(math.hypot(err_e, err_n), 53.85)
        self.assertEqual(len(sit["epochs"]), 12)

    def test_sitan_vertical_bias_recovery(self):
        """Workflow step 4 bias state: the per-mass vertical-bias Kalman
        states recover 13.487 m of the hidden 15.0 m INS altitude error
        (the shortfall is the nonzero mean of the deterministic
        mismatch over the fine-stage window)."""
        sit = self._run_sitan()
        self.assertAlmostEqual(sit["final"]["bias"], 13.487, delta=0.5)
        # the bias state converges upward from zero epoch by epoch
        biases = [e["bias"] for e in sit["epochs"]]
        self.assertGreater(biases[-1], biases[3])

    def test_sitan_per_epoch_sigma_sequence(self):
        """Workflow step 4 uncertainty: the per-epoch 1-sigma from the
        updated 3 by 3 point-mass covariance matches the anchor sequence
        within 1.0 m and contracts from the 37.42 m uniform-bank value
        to about 5 m."""
        sit = self._run_sitan()
        sig_e = [34.92, 35.10, 34.22, 21.98, 11.20, 6.06,
                 5.19, 5.45, 5.33, 4.27, 4.65, 4.73]
        sig_n = [37.16, 24.63, 17.48, 16.48, 13.49, 10.09,
                 7.51, 6.37, 6.52, 6.64, 6.05, 5.35]
        for i, e in enumerate(sit["epochs"]):
            self.assertAlmostEqual(e["sigma_e"], sig_e[i], delta=1.0)
            self.assertAlmostEqual(e["sigma_n"], sig_n[i], delta=1.0)
        # initial uniform-bank 1-sigma for a 13 by 13 bank at 10 m
        bank_sigma = math.sqrt((13.0 ** 2 - 1.0) / 12.0) * 10.0
        self.assertAlmostEqual(bank_sigma, 37.42, delta=0.01)
        self.assertLess(sit["epochs"][-1]["sigma_e"], 6.0)

    def test_sitan_epoch_state_track(self):
        """Workflow step 4 epoch states: the reported fine fix of each
        epoch (dr east, dr north after the slope update) follows the
        anchor track, ending 2.916 m east and -8.925 m north of the
        truth correction."""
        sit = self._run_sitan()
        dr_e = [-388.334, -390.419, -392.797, -426.035, -440.835,
                -438.230, -438.090, -438.784, -438.589, -443.334,
                -447.469, -447.084]
        dr_n = [-206.929, -200.718, -209.537, -205.651, -196.713,
                -197.970, -198.305, -195.985, -196.780, -194.952,
                -190.265, -188.925]
        for i, e in enumerate(sit["epochs"]):
            self.assertAlmostEqual(e["dr_e"], dr_e[i], delta=0.05)
            self.assertAlmostEqual(e["dr_n"], dr_n[i], delta=0.05)

    def test_correction_convention_recovers_true_track(self):
        """Correction convention: p_corrected = p_ind + dr recovers the
        true track to within the final error, and dr_true = -e."""
        sit = self._run_sitan()
        f = sit["final"]
        last = 17  # last fine-stage sample index
        corrected_east = self.x_ind[last] + f["dr_e"]
        corrected_north = self.y_ind[last] + f["dr_n"]
        self.assertAlmostEqual(corrected_east, self.x_true[last], delta=3.0)
        self.assertAlmostEqual(corrected_north, Y_TRUE, delta=9.0)
        dr_true = (-E_EAST, -E_NORTH)
        self.assertEqual(dr_true, (-450.0, -180.0))

    def test_sitan_value_errors_bank_params(self):
        """Non-physical inputs: empty epoch indices, spacing <= 0,
        half < 0, r_meas <= 0, q_bias < 0 and p0_bias <= 0 raise
        ValueError on the point-mass bank."""
        kw = dict(vals=self.vals, profile=self.z, x_ind=self.x_ind,
                  y_ind=self.y_ind, dr0=(-400.0, -200.0),
                  indices=list(range(6, 18)))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, indices=[]))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, spacing=0.0))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, spacing=-5.0))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, half=-1))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, r_meas=0.0))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, q_bias=-0.1))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, p0_bias=0.0))

    def test_sitan_value_errors_inputs(self):
        """Non-physical inputs: non-finite profile, indicated track or
        dr0, a malformed dr0 and an epoch index outside the profile
        window raise ValueError."""
        kw = dict(vals=self.vals, profile=self.z, x_ind=self.x_ind,
                  y_ind=self.y_ind, dr0=(-400.0, -200.0),
                  indices=list(range(6, 18)))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, dr0=(-400.0, float("nan"))))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, dr0=(-400.0,)))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, profile=self.z[:-1]))
        with self.assertRaises(ValueError):
            bad = self.x_ind[:]
            bad[10] = float("inf")
            trn.sitan_point_mass(**dict(kw, x_ind=bad))
        with self.assertRaises(ValueError):
            trn.sitan_point_mass(**dict(kw, indices=[0, 30]))

    def test_epoch_weights_normalized(self):
        """Workflow step 4 likelihood: the point-mass weights normalize
        from log space to a unit sum each epoch, with a bounded
        weight_max and a non-negative weight entropy."""
        sit = self._run_sitan()
        for e in sit["epochs"]:
            self.assertGreaterEqual(e["weight_entropy"], 0.0)
            self.assertLessEqual(e["weight_max"], 1.0)
        # the bank concentrates as the epochs progress
        self.assertGreater(sit["epochs"][-1]["weight_max"],
                           sit["epochs"][0]["weight_max"])

    def test_determinism_and_no_rng(self):
        """Determinism: two full runs (TERCOM grid correlation plus the
        SITAN point-mass fine stage) return bit-identical results, and
        the module imports no random state."""
        sit1 = self._run_sitan()
        sit2 = self._run_sitan()
        self.assertEqual(sit1["final"]["dr_e"], sit2["final"]["dr_e"])
        self.assertEqual(sit1["final"]["dr_n"], sit2["final"]["dr_n"])
        self.assertEqual([e["innovation"] for e in sit1["epochs"]],
                         [e["innovation"] for e in sit2["epochs"]])
        self.assertEqual([e["gain"] for e in sit1["epochs"]],
                         [e["gain"] for e in sit2["epochs"]])
        self.assertNotIn("random", dir(trn))


if __name__ == "__main__":
    unittest.main()
