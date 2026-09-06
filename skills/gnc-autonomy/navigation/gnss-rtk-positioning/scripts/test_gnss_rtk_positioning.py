"""Contract test for gnss_rtk_positioning (gnc-autonomy/navigation).

Exercises the SKILL.md RTK workflow end to end: step 2 forms the
per-satellite single differences across the receivers at each epoch of
the observation arc, step 3 forms the double differences across the
satellite pairs and epochs and scales them to metres by the L1
wavelength, step 4 solves the stacked least-squares normal equations
for the float baseline and the float ambiguities with the per-axis and
per-ambiguity sigmas, step 5 resolves the integer ambiguities by the
rounding candidate sets around the rounded float vector with the ratio
test on the float covariance, step 6 imposes the winning integer set
and re-solves for the fixed baseline with per-axis 1-sigma precision,
step 7 reports the fixed baseline as the ENU offset at the base, and
step 8 runs the coarse ambiguity-free time-differenced baseline read
plus the clock-cancellation and ambiguity-constancy identities.

All numeric assertions are order-safe and tolerance-bounded; the test
is deterministic, offline and stdlib only (imports: math, os, sys,
unittest).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gnss_rtk_positioning_logic as rtk

C = rtk.C_LIGHT
F1 = rtk.F_L1
LAM = rtk.LAMBDA_L1

# Worked example (wave-44 spec): six MEO satellites A..F at three
# epochs t = 0, 600, 1200 s of a 20 minute static-baseline arc.
# Positions in km (converted to m in the epoch builders), raw L1
# carrier-phase streams in cycles; satellite order A..F every epoch.
POS_KM = {
    0: [
        (19120.110, -14938.267, 10802.925),
        (15551.646, 19905.200, -8207.491),
        (18771.884, 6099.355, 17772.109),
        (18709.290, -18709.290, 2314.857),
        (22031.951, -4683.036, -14074.656),
        (14799.438, 14799.438, 16351.969),
    ],
    600: [
        (18749.444, -14124.422, 12425.483),
        (15667.733, 20468.594, -6402.531),
        (17506.242, 6688.695, 18820.905),
        (18665.462, -18420.735, 4208.403),
        (22997.332, -4348.931, -12555.601),
        (13513.729, 14643.001, 17561.186),
    ],
    1200: [
        (18347.352, -13195.597, 13952.939),
        (15737.629, 20906.247, -4548.567),
        (16194.882, 7352.429, 19725.648),
        (18544.610, -18019.137, 6069.739),
        (23857.436, -4069.761, -10940.447),
        (12138.099, 14518.950, 18635.993),
    ],
}

ROVER_PHASE = {
    0: [117765968.889984, 122986734.794352, 118285714.739466,
        118378482.055335, 113327803.622843, 124059514.824031],
    600: [118319050.974395, 122820372.773910, 120155561.310159,
          118443677.560855, 111817331.856550, 125871681.057135],
    1200: [118916115.222242, 122720095.973157, 122062740.381419,
           118623257.237451, 110454181.720175, 127782131.050805],
}

BASE_PHASE = {
    0: [117765907.499872, 122987269.188084, 118285575.473841,
        118378751.733719, 113327202.268631, 124059863.883244],
    600: [118318988.861520, 122820905.164047, 120155417.632624,
          118443944.496563, 111816725.752611, 125872022.211648],
    1200: [118916054.174847, 122720627.477878, 122062593.680271,
           118623523.556497, 110453572.715185, 127782465.566851],
}

# Documented double-difference noise offsets eps (m), pair j (B..F) per
# epoch (t0, t1, t2): injected as rover-phase errors on the non-
# reference tracks.
NOISE_M = [
    [0.0014, -0.0009, 0.0011],
    [-0.0012, 0.0016, -0.0007],
    [0.0008, 0.0011, -0.0015],
    [-0.0016, -0.0006, 0.0013],
    [0.0005, -0.0014, -0.0010],
]

# Per-satellite broadcast clock offsets (s) for the clock-cancellation
# test.
DTS_S = [-1.80e-09, 2.40e-09, 9.00e-10, -3.20e-09, 1.50e-09, -7.00e-10]

EPOCH_TIMES = [0, 600, 1200]
BASE_POSITION = (6378137.0, 0.0, 0.0)
TRUE_BASELINE = (-2.0, 20.0, 12.0)
TRUE_AMBIGUITIES = (487, -196, 372, -514, 259)


def worked_epochs():
    """Epoch records: per-epoch dicts with the satellite ECEF positions
    in m, the rover phase stream and the base phase stream in cycles."""
    epochs = []
    for t in EPOCH_TIMES:
        epochs.append({
            "positions": [tuple(1000.0 * c for c in p) for p in POS_KM[t]],
            "rover_phase": list(ROVER_PHASE[t]),
            "base_phase": list(BASE_PHASE[t]),
        })
    return epochs


def noiseless_epochs():
    """Worked epochs with the documented double-difference noise offsets
    zeroed on the rover phases of the non-reference tracks."""
    epochs = []
    for ti, t in enumerate(EPOCH_TIMES):
        rover = list(ROVER_PHASE[t])
        for j in range(1, len(rover)):
            rover[j] -= NOISE_M[j - 1][ti] / LAM
        epochs.append({
            "positions": [tuple(1000.0 * c for c in p) for p in POS_KM[t]],
            "rover_phase": rover,
            "base_phase": list(BASE_PHASE[t]),
        })
    return epochs


def vec3_err(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def epoch_dd_rows(epochs):
    """(y in m, du = u_j - u_0) per pair per epoch, re-derived from the
    raw phase streams exactly as the solver assembly does, for the
    identity checks."""
    out = []
    for epoch in epochs:
        sds = [rtk.single_difference(epoch["rover_phase"][j],
                                     epoch["base_phase"][j])
               for j in range(len(epoch["positions"]))]
        dds = rtk.form_double_differences(sds, 0)
        u_ref, _ = rtk.line_of_sight(epoch["positions"][0], BASE_POSITION)
        rows = []
        k = 0
        for j in range(1, len(epoch["positions"])):
            u_j, _ = rtk.line_of_sight(epoch["positions"][j], BASE_POSITION)
            du = (u_j[0] - u_ref[0], u_j[1] - u_ref[1], u_j[2] - u_ref[2])
            rows.append((LAM * dds[k], du))
            k += 1
        out.append(rows)
    return out


class ClosedFormIdentityTests(unittest.TestCase):
    """Closed-form identities of the difference operators and the ENU
    conversion (spec validation list)."""

    def test_wavelength_identity(self):
        """Step-1 model identity: LAMBDA_L1 * F_L1 equals C_LIGHT to
        float precision (real anchor residual 0.0)."""
        self.assertTrue(math.isclose(LAM * F1, C, rel_tol=1e-12))

    def test_module_constants(self):
        """The L1 wavelength, light speed and the default ratio-test
        threshold anchor every later step."""
        self.assertAlmostEqual(LAM, 0.190293672798, delta=1e-12)
        self.assertEqual(rtk.C_LIGHT, 299792458.0)
        self.assertEqual(rtk.F_L1, 1575.42e6)
        self.assertEqual(rtk.MIN_SATELLITES, 5)
        self.assertEqual(rtk.MIN_EPOCHS, 2)
        self.assertEqual(rtk.DEFAULT_SEARCH_RADIUS, 2)
        self.assertEqual(rtk.DEFAULT_RATIO_MIN, 3.0)

    def test_single_difference_closed_form(self):
        """Step-2 closed form: single_difference(150.25, 152.75) is
        exactly -2.5 cycles (rover minus base)."""
        self.assertAlmostEqual(rtk.single_difference(150.25, 152.75), -2.5,
                               delta=1e-12)

    def test_double_differences_closed_form(self):
        """Step-3 closed form: the double differences of [12.25, 9.75,
        -3.5] against satellite 0 are [-2.5, -15.75] cycles."""
        dds = rtk.form_double_differences([12.25, 9.75, -3.5], 0)
        self.assertEqual(len(dds), 2)
        self.assertAlmostEqual(dds[0], -2.5, delta=1e-12)
        self.assertAlmostEqual(dds[1], -15.75, delta=1e-12)

    def test_double_differences_alternate_reference(self):
        """Step-3 with a non-zero reference index: [12.25, 9.75, -3.5]
        against satellite 1 gives [2.5, -13.25] cycles."""
        dds = rtk.form_double_differences([12.25, 9.75, -3.5], 1)
        self.assertAlmostEqual(dds[0], 2.5, delta=1e-12)
        self.assertAlmostEqual(dds[1], -13.25, delta=1e-12)

    def test_time_differenced_dd_closed_form(self):
        """Step-8 closed form: the ambiguity-free epoch difference
        [1.2, 3.4, 5.6] minus [1.0, 3.0, 5.0] is [0.2, 0.4, 0.6]."""
        d = rtk.time_differenced_dd([1.2, 3.4, 5.6], [1.0, 3.0, 5.0])
        for got, want in zip(d, [0.2, 0.4, 0.6]):
            self.assertAlmostEqual(got, want, delta=1e-12)

    def test_ecef_to_enu_demo_base_exact(self):
        """Step-7 ENU basis identity at the demo base (lat 0, lon 0):
        the offset (-2, 20, 12) ECEF reads (20 E, 12 N, -2 U) exactly,
        because the local basis is (y, z, x) there."""
        enu = rtk.ecef_to_enu((-2, 20, 12), (6378137, 0, 0))
        self.assertAlmostEqual(enu[0], 20.0, delta=1e-12)
        self.assertAlmostEqual(enu[1], 12.0, delta=1e-12)
        self.assertAlmostEqual(enu[2], -2.0, delta=1e-12)

    def test_line_of_sight_unit_and_range(self):
        """Step-1 line-of-sight: the unit vector from the base to the
        satellite has unit length and the range is the geometric
        distance."""
        u, rho = rtk.line_of_sight((19120110.0, -14938267.0, 10802925.0),
                                   BASE_POSITION)
        self.assertAlmostEqual(math.sqrt(sum(c * c for c in u)), 1.0,
                               delta=1e-12)
        want = math.sqrt((19120110.0 - 6378137.0) ** 2 +
                         14938267.0 ** 2 + 10802925.0 ** 2)
        self.assertAlmostEqual(rho, want, delta=1e-6)


class WorkedExampleTests(unittest.TestCase):
    """The wave-44 worked example: six-satellite geometry over three
    epochs, about 1.1 mm double-difference noise, true baseline
    (-2, 20, 12) m ECEF and true integer set (487, -196, 372, -514,
    259)."""

    def test_sd_streams_match_spec_table(self):
        """Step-2 transcription guard: the single differences formed
        from the raw phase streams reproduce the spec table at every
        epoch (max residual 1.1e-6 cycles)."""
        spec = {
            0: [61.390112, -534.393732, 139.265625, -269.678384,
                601.354211, -349.059214],
            600: [62.112875, -532.390137, 143.677535, -266.935707,
                  606.103938, -341.154513],
            1200: [61.047395, -531.504721, 146.701148, -266.319046,
                   609.004990, -334.516046],
        }
        for t in EPOCH_TIMES:
            sds = [rtk.single_difference(ROVER_PHASE[t][j], BASE_PHASE[t][j])
                   for j in range(6)]
            for j in range(6):
                self.assertAlmostEqual(sds[j], spec[t][j], delta=1.1e-6)

    def test_float_baseline_worked_example(self):
        """Step-4 float solve on the worked set: every per-axis error
        stays below 0.10 m and the 3-D error below 0.15 m (real module
        output -2.0264, 19.9805, 12.0470 m, 3-D 0.0574 m)."""
        f = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        b = f["baseline_float_ecef"]
        for i in range(3):
            self.assertLess(abs(b[i] - TRUE_BASELINE[i]), 0.10)
            self.assertAlmostEqual(b[i],
                                   (-2.026416516, 19.980484076,
                                    12.047022656)[i], delta=1e-3)
        self.assertLess(vec3_err(b, TRUE_BASELINE), 0.15)

    def test_float_sigma0_and_rms(self):
        """Step-4 residual statistics on the worked set: sigma0 within
        1e-3 m of the 0.001269 m anchor and the residual RMS below
        0.005 m."""
        f = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        self.assertAlmostEqual(f["sigma0"], 0.0012685565, delta=1e-3)
        self.assertLess(f["residual_rms"], 0.005)

    def test_float_precision_per_axis(self):
        """Step-4 precision identity on the worked set: the per-axis
        1-sigma values hold the anchor values (0.01325, 0.01533,
        0.02850) m within 1e-3 m."""
        f = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        for got, want in zip(f["baseline_sigma_ecef"],
                             (0.01325, 0.01533, 0.02850)):
            self.assertAlmostEqual(got, want, delta=1e-3)

    def test_float_ambiguities_within_half_cycle(self):
        """Step-4 float ambiguities on the worked set: every float
        ambiguity error stays below 0.5 cycles (real anchor max
        0.358), so nearest-integer rounding recovers the true set."""
        f = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        cyc = f["ambiguities_float_cycles"]
        for k in range(5):
            self.assertLess(abs(cyc[k] - TRUE_AMBIGUITIES[k]), 0.5)
        self.assertAlmostEqual(max(abs(cyc[k] - TRUE_AMBIGUITIES[k])
                                   for k in range(5)), 0.357912,
                               delta=1e-3)

    def test_ambiguity_sigma_anchor(self):
        """Step-4 per-ambiguity 1-sigma in cycles holds the anchor
        values (0.21261, 0.05863, 0.04662, 0.20498, 0.08256) within
        1e-2 cycles."""
        f = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        for got, want in zip(f["per_ambiguity_sigma_cycles"],
                             (0.21261, 0.05863, 0.04662, 0.20498, 0.08256)):
            self.assertAlmostEqual(got, want, delta=1e-2)

    def test_covariance_diag_precision_identity(self):
        """Step-4 precision identity: every per-axis 1-sigma equals
        sigma0 times the square root of the matching covariance-diagonal
        entry, and the ambiguity sigmas are the metre covariance
        diagonal divided by the L1 wavelength."""
        f = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        for i in range(3):
            self.assertAlmostEqual(
                f["baseline_sigma_ecef"][i],
                f["sigma0"] * math.sqrt(f["covariance_diag"][i]),
                delta=1e-12)
        for k in range(5):
            self.assertAlmostEqual(
                f["per_ambiguity_sigma_cycles"][k],
                f["sigma0"] * math.sqrt(f["covariance_diag"][3 + k]) / LAM,
                delta=1e-12)

    def test_float_measurement_counts(self):
        """Step-4 system dimensions on the worked set: 6 satellites, 3
        epochs, 15 measurements and 8 unknowns, redundancy 7."""
        f = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        self.assertEqual(f["num_satellites"], 6)
        self.assertEqual(f["num_epochs"], 3)
        self.assertEqual(f["num_measurements"], 15)
        self.assertEqual(f["num_unknowns"], 8)
        self.assertEqual(f["num_measurements"] - f["num_unknowns"], 7)

    def test_clock_cancellation_in_double_differences(self):
        """Step-3 clock-cancellation identity: shifting the rover clock
        by a common offset at every epoch and adding each satellite
        clock offset to both receivers leaves every double difference
        below 1e-6 cycles of leakage (the receiver clock difference and
        the satellite clock offsets vanish from the double
        differences)."""
        base_rows = epoch_dd_rows(worked_epochs())
        shifted = []
        for ti, t in enumerate(EPOCH_TIMES):
            # Receiver clock difference -> common rover offset; the
            # satellite clock offsets enter both receivers per
            # satellite and cancel in the single difference.
            common = F1 * (1.0e-8 + 0.6e-8 * ti)
            rover = [ROVER_PHASE[t][j] + common + F1 * DTS_S[j]
                     for j in range(6)]
            base_ph = [BASE_PHASE[t][j] + F1 * DTS_S[j] for j in range(6)]
            shifted.append({
                "positions": [tuple(1000.0 * c for c in p)
                              for p in POS_KM[t]],
                "rover_phase": rover,
                "base_phase": base_ph,
            })
        max_leak = 0.0
        for e, epoch_rows in enumerate(epoch_dd_rows(shifted)):
            for k in range(5):
                max_leak = max(max_leak,
                               abs(epoch_rows[k][0] - base_rows[e][k][0])
                               / LAM)
        self.assertLess(max_leak, 1e-6)
        # The float solve is invariant to the clock terms.
        f0 = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        f1 = rtk.solve_float_baseline(shifted, BASE_POSITION)
        for i in range(3):
            self.assertAlmostEqual(f0["baseline_float_ecef"][i],
                                   f1["baseline_float_ecef"][i],
                                   delta=1e-4)

    def test_integer_resolution_worked_example(self):
        """Step-5 integer resolution on the worked set: 3125 candidates
        (= 5^5 at the default radius 2), the best candidate is the true
        integer set, the ratio 501.5 holds within 1 percent and the
        resolution is confirmed (resolved True)."""
        r = rtk.resolve_integer_ambiguities(worked_epochs(), BASE_POSITION)
        self.assertEqual(r["candidates_searched"], 3125)
        self.assertEqual(r["best_candidate"], TRUE_AMBIGUITIES)
        self.assertEqual(r["second_best"], (486, -195, 371, -516, 260))
        self.assertTrue(r["resolved"])
        self.assertAlmostEqual(r["ratio"], 501.5, delta=5.1)
        self.assertLess(r["best_q"], 1e-4)
        self.assertGreater(r["second_q"], 1e-3)

    def test_integer_resolution_fixed_rss_ordering(self):
        """Step-5 residual-domain confirmation: the fixed residual RSS
        of the best candidate stays below 1e-4 m^2 (noise level) and the
        second-best RSS exceeds it by a factor of 100 or more, so the
        float-covariance ranking and the residual-domain ranking agree."""
        r = rtk.resolve_integer_ambiguities(worked_epochs(), BASE_POSITION)
        self.assertLess(r["best_rss"], 1e-4)
        self.assertGreater(r["second_rss"], 100.0 * r["best_rss"])
        self.assertLess(r["second_rss"], 1e-2)
        self.assertAlmostEqual(r["best_rss"], 2.0198622256e-05,
                               delta=1e-7)
        self.assertAlmostEqual(r["second_rss"], 4.4918740498e-03,
                               delta=1e-5)

    def test_fixed_baseline_worked_example(self):
        """Step-6 fixed solution on the worked set with the true integer
        set imposed: the baseline lands within 0.001 m of the truth per
        axis (real module errors -0.112, +0.074, +0.159 mm), the 3-D
        error stays below 0.001 m and the ENU offset holds (20.0, 12.0,
        -2.0) within 0.0005 m."""
        fx = rtk.fixed_baseline_solution(worked_epochs(), BASE_POSITION,
                                         TRUE_AMBIGUITIES)
        b = fx["baseline_ecef"]
        for i in range(3):
            self.assertLess(abs(b[i] - TRUE_BASELINE[i]), 0.001)
        self.assertLess(vec3_err(b, TRUE_BASELINE), 0.001)
        enu = rtk.ecef_to_enu(b, BASE_POSITION)
        for i in range(3):
            self.assertLess(abs(enu[i] - (20.0, 12.0, -2.0)[i]), 0.0005)
        self.assertAlmostEqual(b[0], -2.000112388, delta=1e-5)
        self.assertAlmostEqual(b[1], 20.000074474, delta=1e-5)
        self.assertAlmostEqual(b[2], 12.000159243, delta=1e-5)

    def test_fixed_baseline_precision(self):
        """Step-6 fixed-solution precision: the per-axis 1-sigma values
        hold the anchors (0.00346, 0.00061, 0.00078) m within 1e-4 m
        and sigma0 stays within 1e-4 m of 0.001297 m."""
        fx = rtk.fixed_baseline_solution(worked_epochs(), BASE_POSITION,
                                         TRUE_AMBIGUITIES)
        for got, want in zip(fx["per_axis_sigma_ecef"],
                             (0.00346, 0.00061, 0.00078)):
            self.assertAlmostEqual(got, want, delta=1e-4)
        self.assertAlmostEqual(fx["sigma0"], 0.0012973891, delta=1e-4)
        self.assertLess(fx["residual_rms"], 0.005)
        self.assertEqual(fx["num_measurements"], 15)

    def test_td_baseline_worked_example(self):
        """Step-8 time-differenced precursor read on the worked set: the
        ambiguity-free solve over the 10 epoch-difference equations
        returns a 3-D error below 0.2 m (real 0.043 m) with a residual
        RMS below 0.005 m."""
        td = rtk.solve_td_baseline(worked_epochs(), BASE_POSITION)
        self.assertEqual(td["num_equations"], 10)
        self.assertLess(vec3_err(td["baseline_ecef"], TRUE_BASELINE), 0.2)
        self.assertLess(td["residual_rms"], 0.005)
        b = td["baseline_ecef"]
        self.assertAlmostEqual(b[0], -2.022030779, delta=1e-4)
        self.assertAlmostEqual(b[1], 19.986400219, delta=1e-4)
        self.assertAlmostEqual(b[2], 12.034497554, delta=1e-4)

    def test_noiseless_float_curvature_floor(self):
        """Step-4 noiseless cross-check: with the injected noise zeroed
        the float 3-D error stays below 1e-4 m (the O(|b|^2/rho)
        curvature floor, real 1.7e-5 m) and the max ambiguity error
        below 1e-3 cycles (real 1.4e-4)."""
        fn = rtk.solve_float_baseline(noiseless_epochs(), BASE_POSITION)
        self.assertLess(vec3_err(fn["baseline_float_ecef"],
                                 TRUE_BASELINE), 1e-4)
        self.assertLess(max(abs(fn["ambiguities_float_cycles"][k] -
                                TRUE_AMBIGUITIES[k]) for k in range(5)),
                        1e-3)
        self.assertLess(fn["residual_rms"], 1e-5)

    def test_noiseless_rounding_and_fixed(self):
        """Step-6 noiseless cross-check: nearest-integer rounding of the
        float solution equals the true integer set and the fixed 3-D
        error stays below 1e-4 m (real 8.2e-6 m)."""
        fn = rtk.solve_float_baseline(noiseless_epochs(), BASE_POSITION)
        rounded = tuple(int(round(v)) for v in fn["ambiguities_float_cycles"])
        self.assertEqual(rounded, TRUE_AMBIGUITIES)
        fx = rtk.fixed_baseline_solution(noiseless_epochs(), BASE_POSITION,
                                         TRUE_AMBIGUITIES)
        self.assertLess(vec3_err(fx["baseline_ecef"], TRUE_BASELINE), 1e-4)

    def test_ambiguity_constancy_across_epochs(self):
        """Step-6 ambiguity-constancy identity: a double difference
        re-formed from every epoch carries the same integer, so each
        (y_j(t) + du_j . b_fixed) / lambda lands within 0.05 cycles of
        -N_j at every pair and epoch."""
        fx = rtk.fixed_baseline_solution(worked_epochs(), BASE_POSITION,
                                         TRUE_AMBIGUITIES)
        b = fx["baseline_ecef"]
        for epoch_rows in epoch_dd_rows(worked_epochs()):
            for k in range(5):
                y, du = epoch_rows[k]
                val = (y + du[0] * b[0] + du[1] * b[1] + du[2] * b[2]) / LAM
                self.assertLess(abs(val + TRUE_AMBIGUITIES[k]), 0.05)

    def test_time_difference_no_cycle_residue(self):
        """Step-8 no-cycle-residue identity: the epoch difference of the
        double differences carries no ambiguity term, so against the
        geometry-only prediction -ddu . b_true the epoch-differenced
        observables reproduce the documented noise differences within
        1e-3 m (real residual below the 1e-5 m curvature floor; a
        one-cycle residue would be about 0.19 m)."""
        rows = epoch_dd_rows(worked_epochs())
        b_true = TRUE_BASELINE
        for e in range(2):
            for k in range(5):
                y0, du0 = rows[e][k]
                y1, du1 = rows[e + 1][k]
                dy = y1 - y0
                ddu = tuple(du1[i] - du0[i] for i in range(3))
                geo_pred = -(ddu[0] * b_true[0] + ddu[1] * b_true[1] +
                             ddu[2] * b_true[2])
                res = dy - geo_pred
                doc = NOISE_M[k][e + 1] - NOISE_M[k][e]
                self.assertLess(abs(res - doc), 1e-3)


class ValidationTests(unittest.TestCase):
    """ValueError rejection of non-physical inputs across the module
    (spec validation list)."""

    def _bad(self, **over):
        epochs = worked_epochs()
        if "epoch" in over:
            epochs[0] = over["epoch"]
        if "epochs" in over:
            epochs = over["epochs"]
        return epochs

    def test_fewer_than_min_satellites(self):
        """Step-1 rejection: fewer than 5 tracked satellites raises
        ValueError in every solver."""
        epochs = self._bad()
        epochs[0]["positions"] = epochs[0]["positions"][:4]
        epochs[0]["rover_phase"] = epochs[0]["rover_phase"][:4]
        epochs[0]["base_phase"] = epochs[0]["base_phase"][:4]
        for fn in (rtk.solve_float_baseline, rtk.resolve_integer_ambiguities,
                   rtk.solve_td_baseline):
            with self.assertRaises(ValueError):
                fn(epochs, BASE_POSITION)
        with self.assertRaises(ValueError):
            rtk.fixed_baseline_solution(epochs, BASE_POSITION, (0,) * 4)

    def test_fewer_than_min_epochs(self):
        """Step-1 rejection: a single-epoch arc raises ValueError in
        every solver."""
        for fn in (rtk.solve_float_baseline, rtk.resolve_integer_ambiguities,
                   rtk.solve_td_baseline):
            with self.assertRaises(ValueError):
                fn(worked_epochs()[:1], BASE_POSITION)
        with self.assertRaises(ValueError):
            rtk.fixed_baseline_solution(worked_epochs()[:1], BASE_POSITION,
                                        (0,) * 4)

    def test_position_phase_length_mismatch(self):
        """Step-1 rejection: a position/phase length mismatch inside an
        epoch raises ValueError."""
        epochs = self._bad()
        epochs[0]["rover_phase"] = epochs[0]["rover_phase"][:5]
        with self.assertRaises(ValueError):
            rtk.solve_float_baseline(epochs, BASE_POSITION)

    def test_satellite_count_change_between_epochs(self):
        """Step-1 rejection: the satellite count changing between epochs
        raises ValueError (the arc must track a common set)."""
        epochs = self._bad()
        epochs[1]["positions"] = epochs[1]["positions"][:5]
        epochs[1]["rover_phase"] = epochs[1]["rover_phase"][:5]
        epochs[1]["base_phase"] = epochs[1]["base_phase"][:5]
        with self.assertRaises(ValueError):
            rtk.solve_float_baseline(epochs, BASE_POSITION)

    def test_reference_index_out_of_range(self):
        """Step-3 rejection: an out-of-range reference index raises
        ValueError in the solvers and in form_double_differences."""
        for fn in (rtk.solve_float_baseline, rtk.resolve_integer_ambiguities,
                   rtk.solve_td_baseline):
            with self.assertRaises(ValueError):
                fn(worked_epochs(), BASE_POSITION, reference_index=6)
        with self.assertRaises(ValueError):
            rtk.fixed_baseline_solution(worked_epochs(), BASE_POSITION,
                                        (0,) * 4, reference_index=6)
        with self.assertRaises(ValueError):
            rtk.form_double_differences([1.0, 2.0], 2)

    def test_nonfinite_phase_and_position(self):
        """Step-1 rejection: non-finite phases, positions, epochs or a
        non-finite base position raise ValueError."""
        epochs = self._bad()
        epochs[0]["rover_phase"][0] = float("nan")
        with self.assertRaises(ValueError):
            rtk.solve_float_baseline(epochs, BASE_POSITION)
        epochs = self._bad()
        bad_pos = (float("inf"), 0.0, 0.0)
        epochs[0]["positions"][0] = bad_pos
        with self.assertRaises(ValueError):
            rtk.solve_float_baseline(epochs, BASE_POSITION)
        with self.assertRaises(ValueError):
            rtk.solve_float_baseline(worked_epochs(),
                                     (float("nan"), 0.0, 0.0))
        with self.assertRaises(ValueError):
            rtk.single_difference(1.0, float("nan"))
        with self.assertRaises(ValueError):
            rtk.time_differenced_dd([1.0, float("inf")], [1.0, 1.0])

    def test_missing_epoch_key(self):
        """Step-1 rejection: an epoch record missing the phase or
        position keys raises ValueError."""
        epochs = self._bad()
        del epochs[1]["base_phase"]
        with self.assertRaises(ValueError):
            rtk.solve_float_baseline(epochs, BASE_POSITION)

    def test_singular_normal_matrix(self):
        """Step-4 rejection: a degenerate geometry whose normal matrix
        is singular (every satellite seen along the same line of
        sight) raises ValueError."""
        pos = [(20000000.0, 0.0, 0.0)] * 5
        epochs = [
            {"positions": [tuple(p) for p in pos],
             "rover_phase": [100.0 + j for j in range(5)],
             "base_phase": [10.0 + j for j in range(5)]},
            {"positions": [tuple(p) for p in pos],
             "rover_phase": [200.0 + j for j in range(5)],
             "base_phase": [20.0 + j for j in range(5)]},
        ]
        with self.assertRaises(ValueError):
            rtk.solve_float_baseline(epochs, (6378137.0, 0.0, 0.0))

    def test_resolve_integer_validation(self):
        """Step-5 rejection: a search radius below 1 cycle and a ratio
        threshold at or below 1 raise ValueError."""
        with self.assertRaises(ValueError):
            rtk.resolve_integer_ambiguities(worked_epochs(), BASE_POSITION,
                                            search_radius=0)
        with self.assertRaises(ValueError):
            rtk.resolve_integer_ambiguities(worked_epochs(), BASE_POSITION,
                                            search_radius=-2)
        with self.assertRaises(ValueError):
            rtk.resolve_integer_ambiguities(worked_epochs(), BASE_POSITION,
                                            ratio_min=1.0)

    def test_fixed_wrong_ambiguity_length(self):
        """Step-6 rejection: an integer_ambiguities tuple whose length
        differs from S - 1 raises ValueError."""
        for bad in ((487, -196, 372, -514), (487, -196, 372, -514, 259, 1)):
            with self.assertRaises(ValueError):
                rtk.fixed_baseline_solution(worked_epochs(), BASE_POSITION,
                                            bad)

    def test_los_value_errors(self):
        """Step-1 rejection: a coincident satellite (range below 1 m)
        and non-finite inputs raise ValueError in line_of_sight, and a
        zero base position raises ValueError in ecef_to_enu."""
        with self.assertRaises(ValueError):
            rtk.line_of_sight((6378137.0, 0.0, 0.0), (6378137.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            rtk.line_of_sight((float("nan"), 0.0, 0.0), (0.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            rtk.ecef_to_enu((1.0, 2.0, 3.0), (0.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            rtk.ecef_to_enu((float("inf"), 2.0, 3.0), (1.0, 0.0, 0.0))

    def test_small_radius_search_count(self):
        """Step-5 search-count identity: at radius 1 the candidate count
        is 3^m and the true set still wins with a resolved ratio."""
        r = rtk.resolve_integer_ambiguities(worked_epochs(), BASE_POSITION,
                                            search_radius=1)
        self.assertEqual(r["candidates_searched"], 3 ** 5)
        self.assertEqual(r["best_candidate"], TRUE_AMBIGUITIES)
        self.assertTrue(r["resolved"])

    def test_determinism_and_no_rng(self):
        """Steps 4-5 determinism: repeated solves return identical
        outputs and the logic module imports only math (no RNG, no
        orbit propagation)."""
        f0 = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        f1 = rtk.solve_float_baseline(worked_epochs(), BASE_POSITION)
        self.assertEqual(f0["baseline_float_ecef"], f1["baseline_float_ecef"])
        r0 = rtk.resolve_integer_ambiguities(worked_epochs(), BASE_POSITION)
        r1 = rtk.resolve_integer_ambiguities(worked_epochs(), BASE_POSITION)
        self.assertEqual(r0["best_candidate"], r1["best_candidate"])
        self.assertEqual(r0["ratio"], r1["ratio"])
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "gnss_rtk_positioning_logic.py")
        with open(src_path, "r") as fh:
            src = fh.read()
        self.assertNotIn("import random", src)
        self.assertNotIn("numpy", src)
        self.assertNotIn("random.", src)


if __name__ == "__main__":
    unittest.main()
