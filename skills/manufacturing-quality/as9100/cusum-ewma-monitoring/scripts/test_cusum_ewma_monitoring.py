"""Contract test for cusum_ewma_monitoring_logic (wave-34).

Offline, deterministic, stdlib unittest. Covers the worked-example
anchors (CUSUM S+ path to 1e-9, EWMA e and UCL series against the spec
display list, first signal samples 8 and 7), in-control all-zero CUSUM,
EWMA steady-state sigma_e limit within 0.1 percent, the closed-form UCL
identity, outlier behaviour, dict key contracts and ValueError
rejections. Run with: python3 scripts/test_cusum_ewma_monitoring.py
"""

import math
import unittest

from cusum_ewma_monitoring_logic import (
    DEFAULT_H,
    DEFAULT_K,
    DEFAULT_L,
    DEFAULT_LAM,
    cusum_statistics,
    ewma_statistics,
    monitoring_verdict,
    small_shift_monitoring_report,
)

MU0 = 10.0
SIGMA = 1.0
WORKED_XS = [10.2, 10.5, 11.0, 10.8, 11.5, 11.9, 12.2, 11.6, 12.0, 11.4, 11.8]
# Spec-verified anchors: S+ = [0, 0, 0.5, 0.8, 1.8, 3.2, 4.9, 6.0, 7.5,
# 8.4, 9.7], first CUSUM signal at sample 8 (S+ 6.0 > h 5.0); e-series
# and UCL per the spec list, first EWMA signal at sample 7.
EXPECTED_SP_PLUS = [0.0, 0.0, 0.5, 0.8, 1.8, 3.2, 4.9, 6.0, 7.5, 8.4, 9.7]
EXPECTED_E = [
    10.040, 10.132, 10.306, 10.404, 10.624, 10.879, 11.143, 11.234,
    11.387, 11.390, 11.472,
]
EXPECTED_UCL = [
    10.600, 10.768, 10.859, 10.912, 10.945, 10.965, 10.978, 10.987,
    10.993, 10.997, 11.000,
]


class TestCusumStatistics(unittest.TestCase):
    def test_worked_sp_plus_path_matches_anchor(self):
        result = cusum_statistics(WORKED_XS, MU0, SIGMA)
        self.assertEqual(len(result["sp_plus"]), len(WORKED_XS))
        for actual, expected in zip(result["sp_plus"], EXPECTED_SP_PLUS):
            self.assertAlmostEqual(actual, expected, places=9)

    def test_worked_sp_minus_all_zero(self):
        result = cusum_statistics(WORKED_XS, MU0, SIGMA)
        self.assertTrue(all(v == 0.0 for v in result["sp_minus"]))

    def test_worked_first_signal_index_sample_8(self):
        result = cusum_statistics(WORKED_XS, MU0, SIGMA)
        self.assertEqual(result["first_signal_index"], 8)
        # Sample 8 statistic 6.0 exceeds h 5.0; sample 7 stays at 4.9.
        self.assertGreater(result["sp_plus"][7], DEFAULT_H)
        self.assertLessEqual(max(result["sp_plus"][:7]), DEFAULT_H)

    def test_in_control_constant_series_statistics_all_zero(self):
        xs = [MU0] * 12
        result = cusum_statistics(xs, MU0, SIGMA)
        self.assertTrue(all(v == 0.0 for v in result["sp_plus"]))
        self.assertTrue(all(v == 0.0 for v in result["sp_minus"]))
        self.assertIsNone(result["first_signal_index"])

    def test_sustained_negative_shift_signals_on_lower_side(self):
        xs = [9.0] * 11
        result = cusum_statistics(xs, MU0, SIGMA)
        self.assertEqual(result["first_signal_index"], 11)
        self.assertAlmostEqual(result["sp_minus"][10], 5.5, places=9)
        self.assertAlmostEqual(result["sp_minus"][9], 5.0, places=9)
        self.assertTrue(all(v == 0.0 for v in result["sp_plus"]))

    def test_single_outlier_jump_equals_z_minus_k_then_decays(self):
        # z = 4.8 gives a one-sample jump of z - k = 4.3 below h, then the
        # statistic decays by k per in-control sample back to zero.
        xs = [14.8] + [MU0] * 9
        result = cusum_statistics(xs, MU0, SIGMA)
        self.assertAlmostEqual(result["sp_plus"][0], 4.3, places=9)
        self.assertAlmostEqual(result["sp_plus"][-1], 0.0, places=9)
        self.assertIsNone(result["first_signal_index"])
        self.assertTrue(all(v == 0.0 for v in result["sp_minus"]))

    def test_outlier_above_h_signals_at_sample_1(self):
        # z = 6.0 gives S+ = 5.5 > h at the first sample.
        result = cusum_statistics([16.0], MU0, SIGMA)
        self.assertEqual(result["first_signal_index"], 1)
        self.assertAlmostEqual(result["sp_plus"][0], 5.5, places=9)

    def test_empty_xs_raises_valueerror(self):
        with self.assertRaises(ValueError):
            cusum_statistics([], MU0, SIGMA)
        with self.assertRaises(ValueError):
            cusum_statistics(None, MU0, SIGMA)

    def test_nonpositive_sigma_raises_valueerror(self):
        with self.assertRaises(ValueError):
            cusum_statistics(WORKED_XS, MU0, 0.0)
        with self.assertRaises(ValueError):
            cusum_statistics(WORKED_XS, MU0, -1.0)

    def test_nonpositive_k_or_h_raises_valueerror(self):
        for bad_k in (0.0, -0.5):
            with self.assertRaises(ValueError):
                cusum_statistics(WORKED_XS, MU0, SIGMA, k=bad_k)
        for bad_h in (0.0, -1.0):
            with self.assertRaises(ValueError):
                cusum_statistics(WORKED_XS, MU0, SIGMA, h=bad_h)

    def test_cusum_dict_keys_exact(self):
        keys = set(cusum_statistics(WORKED_XS, MU0, SIGMA).keys())
        self.assertEqual(keys, {"sp_plus", "sp_minus", "first_signal_index"})


class TestEwmaStatistics(unittest.TestCase):
    def test_worked_ewma_series_matches_spec_list(self):
        result = ewma_statistics(WORKED_XS, MU0, SIGMA)
        self.assertEqual(len(result["ewma_series"]), len(WORKED_XS))
        for actual, expected in zip(result["ewma_series"], EXPECTED_E):
            # Spec display list is 3-decimal rounded; module recursion is
            # exact, so allow 1e-3 on the printed anchor values.
            self.assertAlmostEqual(actual, expected, delta=1e-3)

    def test_worked_ucl_series_matches_spec_list(self):
        result = ewma_statistics(WORKED_XS, MU0, SIGMA)
        for actual, expected in zip(result["ucl"], EXPECTED_UCL):
            # Display list rounded to 3 decimals with minor tail rounding
            # anomalies (<= 4e-3); the exact formula is asserted to 1e-9
            # in test_ucl_closed_form_identity_exact.
            self.assertAlmostEqual(actual, expected, delta=5e-3)

    def test_ucl_closed_form_identity_exact(self):
        result = ewma_statistics(WORKED_XS, MU0, SIGMA)
        decay = 1.0 - DEFAULT_LAM
        scale = DEFAULT_LAM / (2.0 - DEFAULT_LAM)
        for index, (upper, lower) in enumerate(zip(result["ucl"], result["lcl"])):
            sigma_e = SIGMA * math.sqrt(scale * (1.0 - decay ** (2 * (index + 1))))
            self.assertAlmostEqual(upper, MU0 + DEFAULT_L * sigma_e, places=9)
            # LCL mirrors UCL around mu0 at every sample.
            self.assertAlmostEqual(lower, 2.0 * MU0 - upper, places=9)

    def test_first_ewma_recursion_identity(self):
        result = ewma_statistics(WORKED_XS, MU0, SIGMA)
        expected = DEFAULT_LAM * WORKED_XS[0] + (1.0 - DEFAULT_LAM) * MU0
        self.assertAlmostEqual(result["ewma_series"][0], expected, places=12)

    def test_worked_first_signal_sample_7(self):
        result = ewma_statistics(WORKED_XS, MU0, SIGMA)
        self.assertEqual(result["first_signal_index"], 7)
        # Sample 7 e = 11.143 exceeds UCL 10.978; sample 6 stays inside.
        self.assertGreater(result["ewma_series"][6], result["ucl"][6])
        self.assertLess(result["ewma_series"][5], result["ucl"][5])

    def test_in_control_constant_series_no_signal(self):
        xs = [MU0] * 30
        result = ewma_statistics(xs, MU0, SIGMA)
        self.assertTrue(all(v == MU0 for v in result["ewma_series"]))
        self.assertIsNone(result["first_signal_index"])
        self.assertTrue(all(e < u for e, u in zip(result["ewma_series"], result["ucl"])))

    def test_ewma_converges_toward_shifted_level(self):
        # Constant series at mu0 + 0.01: e_i approaches mu0 + 0.01 with
        # geometric decay (1 - lam)^i and never crosses the limits.
        xs = [MU0 + 0.01] * 200
        result = ewma_statistics(xs, MU0, SIGMA)
        self.assertAlmostEqual(result["ewma_series"][-1], MU0 + 0.01, places=9)
        self.assertIsNone(result["first_signal_index"])

    def test_ucl_converges_to_steady_state_within_0_1_percent(self):
        xs = [MU0] * 200
        result = ewma_statistics(xs, MU0, SIGMA)
        steady_sigma_e = SIGMA * math.sqrt(DEFAULT_LAM / (2.0 - DEFAULT_LAM))
        last_sigma_e = (result["ucl"][-1] - MU0) / DEFAULT_L
        self.assertLess(abs(last_sigma_e - steady_sigma_e) / steady_sigma_e, 0.001)

    def test_ucl_increasing_lcl_decreasing(self):
        result = ewma_statistics(WORKED_XS, MU0, SIGMA)
        self.assertTrue(all(a < b for a, b in zip(result["ucl"], result["ucl"][1:])))
        self.assertTrue(all(a > b for a, b in zip(result["lcl"], result["lcl"][1:])))

    def test_lam_one_passes_observations_through(self):
        result = ewma_statistics(WORKED_XS, MU0, SIGMA, lam=1.0)
        for actual, expected in zip(result["ewma_series"], WORKED_XS):
            self.assertEqual(actual, expected)

    def test_empty_xs_raises_valueerror(self):
        with self.assertRaises(ValueError):
            ewma_statistics([], MU0, SIGMA)

    def test_nonpositive_sigma_raises_valueerror(self):
        with self.assertRaises(ValueError):
            ewma_statistics(WORKED_XS, MU0, 0.0)

    def test_lam_out_of_range_raises_valueerror(self):
        for bad_lam in (0.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                ewma_statistics(WORKED_XS, MU0, SIGMA, lam=bad_lam)

    def test_nonpositive_L_raises_valueerror(self):
        for bad_l in (0.0, -2.0):
            with self.assertRaises(ValueError):
                ewma_statistics(WORKED_XS, MU0, SIGMA, L=bad_l)

    def test_ewma_dict_keys_exact(self):
        keys = set(ewma_statistics(WORKED_XS, MU0, SIGMA).keys())
        self.assertEqual(keys, {"ewma_series", "ucl", "lcl", "first_signal_index"})


class TestMonitoringVerdict(unittest.TestCase):
    def test_verdict_worked_any_signal_first_sample_7(self):
        verdict = monitoring_verdict(8, 7, len(WORKED_XS))
        self.assertTrue(verdict["cusum_signaled"])
        self.assertTrue(verdict["ewma_signaled"])
        self.assertTrue(verdict["any_signal"])
        self.assertEqual(verdict["first_signal_index"], 7)
        self.assertEqual(
            set(verdict.keys()), {"cusum_signaled", "ewma_signaled",
                                  "any_signal", "first_signal_index"}
        )

    def test_verdict_no_signal_all_clear(self):
        verdict = monitoring_verdict(None, None, 11)
        self.assertFalse(verdict["cusum_signaled"])
        self.assertFalse(verdict["ewma_signaled"])
        self.assertFalse(verdict["any_signal"])
        self.assertIsNone(verdict["first_signal_index"])

    def test_verdict_single_chart_signals(self):
        cusum_only = monitoring_verdict(8, None, 11)
        self.assertTrue(cusum_only["cusum_signaled"])
        self.assertFalse(cusum_only["ewma_signaled"])
        self.assertEqual(cusum_only["first_signal_index"], 8)
        ewma_only = monitoring_verdict(None, 7, 11)
        self.assertFalse(ewma_only["cusum_signaled"])
        self.assertTrue(ewma_only["ewma_signaled"])
        self.assertEqual(ewma_only["first_signal_index"], 7)

    def test_verdict_negative_n_raises_valueerror(self):
        with self.assertRaises(ValueError):
            monitoring_verdict(None, None, -1)


class TestSmallShiftMonitoringReport(unittest.TestCase):
    def test_report_worked_combines_components(self):
        report = small_shift_monitoring_report(WORKED_XS, MU0, SIGMA)
        self.assertEqual(set(report.keys()), {"cusum", "ewma", "verdict"})
        self.assertTrue(report["verdict"]["any_signal"])
        self.assertEqual(report["verdict"]["first_signal_index"], 7)
        self.assertEqual(report["cusum"]["first_signal_index"], 8)
        self.assertEqual(report["ewma"]["first_signal_index"], 7)
        # Report chart dicts equal the standalone function outputs.
        cusum = cusum_statistics(WORKED_XS, MU0, SIGMA)
        ewma = ewma_statistics(WORKED_XS, MU0, SIGMA)
        for key in ("sp_plus", "sp_minus", "first_signal_index"):
            self.assertEqual(report["cusum"][key], cusum[key])
        for key in ("ewma_series", "ucl", "lcl", "first_signal_index"):
            self.assertEqual(report["ewma"][key], ewma[key])

    def test_report_clear_sequence_all_clear(self):
        report = small_shift_monitoring_report([MU0] * 12, MU0, SIGMA)
        self.assertFalse(report["verdict"]["any_signal"])
        self.assertIsNone(report["verdict"]["first_signal_index"])

    def test_report_propagates_valueerrors(self):
        with self.assertRaises(ValueError):
            small_shift_monitoring_report([], MU0, SIGMA)
        with self.assertRaises(ValueError):
            small_shift_monitoring_report(WORKED_XS, MU0, -1.0)
        with self.assertRaises(ValueError):
            small_shift_monitoring_report(WORKED_XS, MU0, SIGMA, k=0.0)
        with self.assertRaises(ValueError):
            small_shift_monitoring_report(WORKED_XS, MU0, SIGMA, lam=1.5)

    def test_report_deterministic_two_runs_identical(self):
        first = small_shift_monitoring_report(WORKED_XS, MU0, SIGMA)
        second = small_shift_monitoring_report(WORKED_XS, MU0, SIGMA)
        self.assertEqual(first["cusum"]["sp_plus"], second["cusum"]["sp_plus"])
        self.assertEqual(first["ewma"]["ewma_series"], second["ewma"]["ewma_series"])
        self.assertEqual(first["ewma"]["ucl"], second["ewma"]["ucl"])


if __name__ == "__main__":
    unittest.main()
