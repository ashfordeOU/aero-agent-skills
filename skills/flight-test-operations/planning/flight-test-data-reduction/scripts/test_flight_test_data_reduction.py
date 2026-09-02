#!/usr/bin/env python3
"""Gate 3 contract test: flight-test-data-reduction.

Exercises scripts/flight_test_data_reduction.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - apply_calibration
corrects a raw reading with the calibration line; align_time_series
shifts a trace by a constant offset; moving_average smooths with a
window (odd windows centered, even windows with a half-sample lag);
corrected_airspeed follows from the impact pressure and density;
combined_uncertainty combines independent sources by root sum square;
data_quality_verdict flags NaN samples, out-of-range values, and time
gaps. All expected values are hand-computed analytic results in SI
units (m/s, Pa, kg/m^3, s).
"""

import unittest

import flight_test_data_reduction as fdr


class ApplyCalibrationTest(unittest.TestCase):
    def test_analytic_slope_intercept(self):
        # 50.0 m/s raw with slope 1.02 and intercept -0.5 m/s gives
        # 50.0 * 1.02 - 0.5 = 50.5 m/s.
        self.assertAlmostEqual(fdr.apply_calibration(50.0, 1.02, -0.5), 50.5, places=7)

    def test_identity_calibration(self):
        # Slope 1.0, intercept 0.0 passes the raw value through.
        self.assertAlmostEqual(fdr.apply_calibration(37.2, 1.0, 0.0), 37.2, places=7)

    def test_negative_inputs(self):
        # Negative raw and negative intercept combine: -10 * 2 + 3 = -17.
        self.assertAlmostEqual(fdr.apply_calibration(-10.0, 2.0, 3.0), -17.0, places=7)

    def test_returns_float(self):
        self.assertIsInstance(fdr.apply_calibration(10, 2, 1), float)

    def test_bool_raw_raises(self):
        with self.assertRaises(ValueError):
            fdr.apply_calibration(True, 1.0, 0.0)

    def test_string_slope_raises(self):
        with self.assertRaises(ValueError):
            fdr.apply_calibration(10.0, "1.02", 0.0)

    def test_none_intercept_raises(self):
        with self.assertRaises(ValueError):
            fdr.apply_calibration(10.0, 1.0, None)


class AlignTimeSeriesTest(unittest.TestCase):
    def test_analytic_offset(self):
        # 0.25 s offset shifts every sample later in time.
        self.assertEqual(fdr.align_time_series([0.0, 1.0, 2.0], 0.25), [0.25, 1.25, 2.25])

    def test_negative_offset_shifts_earlier(self):
        self.assertEqual(fdr.align_time_series([0.0, 1.0], -0.5), [-0.5, 0.5])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            fdr.align_time_series([], 1.0)

    def test_non_numeric_element_raises(self):
        with self.assertRaises(ValueError):
            fdr.align_time_series([0.0, "1.0"], 1.0)

    def test_bool_offset_raises(self):
        with self.assertRaises(ValueError):
            fdr.align_time_series([0.0], True)


class MovingAverageTest(unittest.TestCase):
    def test_odd_window_centered(self):
        # Window 3 over [1,2,3,4,5] gives [(1+2+3)/3, (2+3+4)/3, (3+4+5)/3].
        self.assertEqual(fdr.moving_average([1, 2, 3, 4, 5], 3), [2.0, 3.0, 4.0])

    def test_even_window_parity(self):
        # Window 2 over 5 samples gives 4 outputs; the trace lags by
        # half a sample by construction.
        self.assertEqual(
            fdr.moving_average([1, 2, 3, 4, 5], 2), [1.5, 2.5, 3.5, 4.5]
        )

    def test_window_one_identity(self):
        self.assertEqual(fdr.moving_average([4.0, 5.0], 1), [4.0, 5.0])

    def test_window_equals_length_single_mean(self):
        self.assertEqual(fdr.moving_average([2, 4, 6], 3), [4.0])

    def test_window_greater_than_length_raises(self):
        with self.assertRaises(ValueError):
            fdr.moving_average([1, 2, 3], 4)

    def test_float_window_raises(self):
        with self.assertRaises(ValueError):
            fdr.moving_average([1, 2, 3], 2.5)

    def test_bool_window_raises(self):
        with self.assertRaises(ValueError):
            fdr.moving_average([1, 2, 3], True)

    def test_empty_values_raises(self):
        with self.assertRaises(ValueError):
            fdr.moving_average([], 3)


class CorrectedAirspeedTest(unittest.TestCase):
    def test_analytic_sea_level(self):
        # q_c = 6125 Pa at rho = 1.225 kg/m^3: sqrt(2*6125/1.225) = 100 m/s.
        self.assertAlmostEqual(fdr.corrected_airspeed(6125.0, 1.225), 100.0, places=7)

    def test_zero_impact_pressure_zero_speed(self):
        self.assertAlmostEqual(fdr.corrected_airspeed(0.0, 1.225), 0.0, places=7)

    def test_denser_air_lowers_speed(self):
        # Same impact pressure at rho = 1.5 kg/m^3: sqrt(12250/1.5).
        self.assertAlmostEqual(fdr.corrected_airspeed(6125.0, 1.5), 90.3696, places=3)

    def test_zero_density_raises(self):
        with self.assertRaises(ValueError):
            fdr.corrected_airspeed(6125.0, 0.0)

    def test_negative_impact_pressure_raises(self):
        with self.assertRaises(ValueError):
            fdr.corrected_airspeed(-1.0, 1.225)

    def test_bool_density_raises(self):
        with self.assertRaises(ValueError):
            fdr.corrected_airspeed(6125.0, True)


class CombinedUncertaintyTest(unittest.TestCase):
    def test_analytic_rss(self):
        # sqrt(0.5^2 + 1.0^2) = sqrt(1.25) = 1.1180 m/s.
        self.assertAlmostEqual(
            fdr.combined_uncertainty([0.5, 1.0]), 1.11803398875, places=9
        )

    def test_single_source(self):
        self.assertAlmostEqual(fdr.combined_uncertainty([2.0]), 2.0, places=7)

    def test_three_sources(self):
        # sqrt(3^2 + 4^2 + 12^2) = sqrt(169) = 13.
        self.assertAlmostEqual(fdr.combined_uncertainty([3.0, 4.0, 12.0]), 13.0, places=7)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            fdr.combined_uncertainty([])

    def test_negative_source_raises(self):
        with self.assertRaises(ValueError):
            fdr.combined_uncertainty([0.5, -1.0])

    def test_non_numeric_source_raises(self):
        with self.assertRaises(ValueError):
            fdr.combined_uncertainty([0.5, "1.0"])


class DataQualityVerdictTest(unittest.TestCase):
    def test_clean_series_ok(self):
        out = fdr.data_quality_verdict(
            [0.0, 1.0, 2.0],
            [100.0, 101.0, 100.5],
            valid_min=95.0,
            valid_max=105.0,
            max_gap=1.0,
        )
        self.assertEqual(out["verdict"], "ok")
        self.assertEqual(out["issues"], [])

    def test_flags_nan_and_out_of_range(self):
        # NaN at index 1; 130 above 105 at index 2; 90 below 95 at index 3.
        out = fdr.data_quality_verdict(
            [0.0, 1.0, 2.0, 3.0, 4.0],
            [100.0, float("nan"), 130.0, 90.0, 95.0],
            valid_min=95.0,
            valid_max=105.0,
            max_gap=1.0,
        )
        self.assertEqual(out["verdict"], "flagged")
        self.assertEqual(
            [i["type"] for i in out["issues"]],
            ["nan", "out-of-range", "out-of-range"],
        )
        self.assertEqual([i["index"] for i in out["issues"]], [1, 2, 3])

    def test_flags_time_gap(self):
        # 1.0 s to 5.0 s is a 4 s gap, above max_gap 1.0 s.
        out = fdr.data_quality_verdict(
            [0.0, 1.0, 5.0, 6.0],
            [100.0, 101.0, 100.5, 100.2],
            max_gap=1.0,
        )
        self.assertEqual(out["verdict"], "flagged")
        self.assertEqual([i["type"] for i in out["issues"]], ["gap"])
        self.assertEqual(out["issues"][0]["index"], 2)

    def test_unbounded_range_skips_range_check(self):
        # No bounds: the 130 value is not flagged as out-of-range.
        out = fdr.data_quality_verdict([0.0, 1.0], [100.0, 130.0])
        self.assertEqual(out["verdict"], "ok")

    def test_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            fdr.data_quality_verdict([0.0, 1.0], [100.0])

    def test_nan_time_raises(self):
        with self.assertRaises(ValueError):
            fdr.data_quality_verdict([0.0, float("nan")], [100.0, 101.0])

    def test_non_positive_max_gap_raises(self):
        with self.assertRaises(ValueError):
            fdr.data_quality_verdict([0.0, 1.0], [100.0, 101.0], max_gap=0.0)


class ReductionScenarioTest(unittest.TestCase):
    def test_end_to_end_reduction(self):
        # Raw airspeed trace through the full reduction chain. Calibration
        # with slope 1.02, intercept -1.0 m/s, then a window-3 moving
        # average, a combined uncertainty of 0.5 and 1.0 m/s, and a clean
        # quality verdict.
        raw = [98.0, 99.0, 101.0, 100.0, 102.0]
        cal = [fdr.apply_calibration(v, 1.02, -1.0) for v in raw]
        for got, want in zip(cal, [98.96, 99.98, 102.02, 101.0, 103.04]):
            self.assertAlmostEqual(got, want, places=7)

        aligned = fdr.align_time_series([0.0, 1.0, 2.0, 3.0, 4.0], 0.5)
        self.assertEqual(aligned, [0.5, 1.5, 2.5, 3.5, 4.5])

        smoothed = fdr.moving_average(cal, 3)
        self.assertAlmostEqual(smoothed[0], 100.32, places=7)
        self.assertAlmostEqual(smoothed[1], 101.0, places=7)
        self.assertAlmostEqual(smoothed[2], 102.02, places=7)

        # The window-3 average centers on the first three samples, so
        # the smoothed trace sits on the window-start times 0.5, 1.5,
        # 2.5 s.
        smoothed_times = aligned[:3]

        vc = fdr.corrected_airspeed(6125.0, 1.225)
        self.assertAlmostEqual(vc, 100.0, places=7)

        uc = fdr.combined_uncertainty([0.5, 1.0])
        self.assertAlmostEqual(uc, 1.11803398875, places=9)

        verdict = fdr.data_quality_verdict(
            smoothed_times, smoothed, valid_min=95.0, valid_max=105.0, max_gap=1.0
        )
        self.assertEqual(verdict["verdict"], "ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)
