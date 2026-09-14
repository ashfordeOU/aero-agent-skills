#!/usr/bin/env python3
"""Contract test for the reflectance cut-on definition (offline)."""

import unittest

from e2008_reflectance_cut_on_definition_logic import (
    CUT_ON_BAND_TOO_WEAK,
    CUT_ON_DETERMINED,
    CUT_ON_EDGE_OUTSIDE_SCAN,
    CUT_ON_RESOLUTION_INSUFFICIENT,
    absolute_measured_reflectance,
    assess_cut_on_determination,
    cut_on_wavelength_nm,
    describe_cut_on,
    half_reflectance_level,
    peak_wavelength_nm,
    validate_band_window,
    validate_cut_on_policy,
    validate_reflectance_scan,
)

# A coarse scan across a reflector band: the edge is bracketed 10 nm apart.
COARSE_SCAN = [
    (300.0, 0.02),
    (310.0, 0.05),
    (320.0, 0.10),
    (330.0, 0.20),
    (340.0, 0.35),
    (350.0, 0.55),
    (360.0, 0.75),
    (370.0, 0.88),
    (380.0, 0.93),
    (400.0, 0.95),
    (450.0, 0.96),
    (500.0, 0.94),
]

# The same edge sampled 2 nm apart.
FINE_SCAN = [
    (300.0, 0.02),
    (340.0, 0.35),
    (342.0, 0.39),
    (344.0, 0.43),
    (346.0, 0.47),
    (348.0, 0.51),
    (360.0, 0.75),
    (400.0, 0.96),
]

# A coating with a weak short-wavelength hump below the main band.
TWO_HUMP_SCAN = [
    (280.0, 0.05),
    (300.0, 0.30),
    (320.0, 0.62),
    (340.0, 0.60),
    (360.0, 0.30),
    (380.0, 0.40),
    (400.0, 0.70),
    (420.0, 0.88),
    (440.0, 0.90),
]

# A plateau that falls back through the half level on its long side.
PLATEAU_SCAN = [
    (300.0, 0.05),
    (320.0, 0.40),
    (340.0, 0.90),
    (400.0, 0.90),
    (420.0, 0.40),
    (440.0, 0.05),
]

# The crossing lands exactly on a measured sample at 320 nm.
ON_SAMPLE_SCAN = [
    (300.0, 0.10),
    (320.0, 0.45),
    (340.0, 0.80),
    (360.0, 0.90),
    (400.0, 0.90),
]

# The shortest wavelength already sits exactly on the half level.
FIRST_SAMPLE_SCAN = [(300.0, 0.40), (320.0, 0.60), (340.0, 0.80)]

# The edge lies below the scanned range.
TRUNCATED_SCAN = [(300.0, 0.80), (320.0, 0.90), (340.0, 0.95)]

# Nothing here is a high reflectance band.
WEAK_SCAN = [(300.0, 0.02), (340.0, 0.10), (400.0, 0.20)]


class ScanValidationTests(unittest.TestCase):
    def test_a_good_scan_is_returned_normalised(self):
        points = validate_reflectance_scan(COARSE_SCAN)
        self.assertEqual(len(points), len(COARSE_SCAN))
        self.assertAlmostEqual(points[0][0], 300.0, places=9)
        self.assertAlmostEqual(points[-1][1], 0.94, places=9)

    def test_a_scan_of_mappings_is_accepted(self):
        points = validate_reflectance_scan(
            [
                {"wavelength_nm": 300.0, "reflectance": 0.10},
                {"wavelength_nm": 320.0, "reflectance": 0.60},
            ]
        )
        self.assertAlmostEqual(points[1][1], 0.60, places=9)

    def test_a_single_sample_scan_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_scan([(300.0, 0.5)])

    def test_a_scan_in_per_cent_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_scan([(300.0, 2.0), (320.0, 96.0)])

    def test_a_negative_reflectance_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_scan([(300.0, -0.01), (320.0, 0.60)])

    def test_wavelengths_that_do_not_advance_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_scan([(320.0, 0.10), (300.0, 0.60)])

    def test_a_repeated_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_scan([(300.0, 0.10), (300.0, 0.60)])

    def test_a_zero_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_scan([(0.0, 0.10), (320.0, 0.60)])

    def test_a_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_scan([(300.0, 0.10, 1.0), (320.0, 0.60)])

    def test_a_non_sequence_scan_rejected(self):
        with self.assertRaises(ValueError):
            validate_reflectance_scan({"300": 0.10})


class BandWindowTests(unittest.TestCase):
    def test_an_absent_window_spans_the_whole_scan(self):
        window = validate_band_window(None, COARSE_SCAN)
        self.assertAlmostEqual(window[0], 300.0, places=9)
        self.assertAlmostEqual(window[1], 500.0, places=9)

    def test_a_window_given_as_a_mapping_is_accepted(self):
        window = validate_band_window(
            {"start_nm": 380.0, "end_nm": 500.0}, COARSE_SCAN
        )
        self.assertAlmostEqual(window[0], 380.0, places=9)

    def test_a_window_that_does_not_advance_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_window((400.0, 400.0), COARSE_SCAN)

    def test_a_window_containing_no_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_window((600.0, 700.0), COARSE_SCAN)

    def test_a_malformed_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_window((400.0,), COARSE_SCAN)


class AbsoluteReflectanceTests(unittest.TestCase):
    def test_the_absolute_reflectance_is_the_measured_peak(self):
        self.assertAlmostEqual(
            absolute_measured_reflectance(COARSE_SCAN), 0.96, places=9
        )

    def test_the_peak_wavelength_is_reported_with_it(self):
        self.assertAlmostEqual(peak_wavelength_nm(COARSE_SCAN), 450.0, places=9)

    def test_the_half_level_is_half_the_absolute_reflectance(self):
        self.assertAlmostEqual(half_reflectance_level(COARSE_SCAN), 0.48, places=9)

    def test_a_window_narrows_which_peak_supplies_the_level(self):
        whole = absolute_measured_reflectance(TWO_HUMP_SCAN)
        hump = absolute_measured_reflectance(TWO_HUMP_SCAN, (280.0, 340.0))
        self.assertAlmostEqual(whole, 0.90, places=9)
        self.assertAlmostEqual(hump, 0.62, places=9)


class CutOnTests(unittest.TestCase):
    def test_the_cut_on_is_interpolated_between_the_bracketing_samples(self):
        self.assertAlmostEqual(cut_on_wavelength_nm(COARSE_SCAN), 346.5, places=9)

    def test_a_finer_scan_of_the_same_edge_agrees(self):
        self.assertAlmostEqual(cut_on_wavelength_nm(FINE_SCAN), 346.5, places=9)

    def test_the_bracket_width_is_the_resolution_of_the_result(self):
        coarse = describe_cut_on(COARSE_SCAN)
        fine = describe_cut_on(FINE_SCAN)
        self.assertAlmostEqual(coarse["bracket_width_nm"], 10.0, places=9)
        self.assertAlmostEqual(fine["bracket_width_nm"], 2.0, places=9)

    def test_the_bracketing_samples_straddle_the_half_level(self):
        described = describe_cut_on(COARSE_SCAN)
        self.assertAlmostEqual(described["bracket_nm"][0], 340.0, places=9)
        self.assertAlmostEqual(described["bracket_nm"][1], 350.0, places=9)
        self.assertFalse(described["on_sample"])

    def test_the_edge_slope_is_reported(self):
        described = describe_cut_on(COARSE_SCAN)
        self.assertAlmostEqual(described["edge_slope_per_nm"], 0.02, places=9)

    def test_a_crossing_on_a_sample_is_not_interpolated(self):
        described = describe_cut_on(ON_SAMPLE_SCAN)
        self.assertAlmostEqual(described["cut_on_wavelength_nm"], 320.0, places=9)
        self.assertTrue(described["on_sample"])
        self.assertAlmostEqual(described["bracket_width_nm"], 0.0, places=9)

    def test_a_first_sample_on_the_half_level_is_the_cut_on(self):
        described = describe_cut_on(FIRST_SAMPLE_SCAN)
        self.assertAlmostEqual(described["cut_on_wavelength_nm"], 300.0, places=9)
        self.assertTrue(described["on_sample"])

    def test_the_short_wavelength_crossing_wins_over_the_long_one(self):
        described = describe_cut_on(PLATEAU_SCAN)
        self.assertAlmostEqual(described["cut_on_wavelength_nm"], 322.0, places=9)
        self.assertLess(
            described["cut_on_wavelength_nm"], described["peak_wavelength_nm"]
        )

    def test_a_short_wavelength_hump_is_stepped_over_for_the_main_band(self):
        self.assertAlmostEqual(
            cut_on_wavelength_nm(TWO_HUMP_SCAN), 309.375, places=9
        )

    def test_windowing_onto_the_hump_moves_the_cut_on(self):
        self.assertAlmostEqual(
            cut_on_wavelength_nm(TWO_HUMP_SCAN, (280.0, 340.0)), 300.625, places=9
        )

    def test_a_scan_starting_above_the_half_level_has_no_cut_on(self):
        with self.assertRaises(ValueError):
            cut_on_wavelength_nm(TRUNCATED_SCAN)

    def test_the_cut_on_sits_where_the_curve_reaches_the_half_level(self):
        described = describe_cut_on(COARSE_SCAN)
        low_wl, low_r = COARSE_SCAN[4]
        high_wl, high_r = COARSE_SCAN[5]
        fraction = (described["half_level"] - low_r) / (high_r - low_r)
        self.assertAlmostEqual(
            described["cut_on_wavelength_nm"],
            low_wl + fraction * (high_wl - low_wl),
            places=9,
        )


class PolicyTests(unittest.TestCase):
    def test_an_absent_policy_falls_back_to_the_declared_default(self):
        policy = validate_cut_on_policy(None)
        self.assertAlmostEqual(policy["min_absolute_reflectance"], 0.30, places=9)
        self.assertAlmostEqual(policy["max_bracket_width_nm"], 5.0, places=9)

    def test_a_minimum_reflectance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_policy({"min_absolute_reflectance": 1.5})

    def test_a_zero_bracket_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_policy({"max_bracket_width_nm": 0.0})

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_policy("default")


class DeterminationTests(unittest.TestCase):
    def test_a_finely_sampled_edge_yields_a_determined_cut_on(self):
        result = assess_cut_on_determination(FINE_SCAN)
        self.assertEqual(result["verdict"], CUT_ON_DETERMINED)
        self.assertAlmostEqual(result["cut_on_wavelength_nm"], 346.5, places=9)

    def test_a_coarse_bracket_is_reported_as_insufficient_resolution(self):
        result = assess_cut_on_determination(COARSE_SCAN)
        self.assertEqual(result["verdict"], CUT_ON_RESOLUTION_INSUFFICIENT)
        self.assertTrue(
            any("not known to the decimals" in f for f in result["findings"])
        )

    def test_a_wider_allowance_accepts_the_same_coarse_scan(self):
        result = assess_cut_on_determination(
            COARSE_SCAN, {"max_bracket_width_nm": 10.0}
        )
        self.assertEqual(result["verdict"], CUT_ON_DETERMINED)

    def test_a_bracket_exactly_on_the_allowance_is_accepted(self):
        result = assess_cut_on_determination(
            COARSE_SCAN, {"max_bracket_width_nm": 10.0}
        )
        self.assertAlmostEqual(result["bracket_width_nm"], 10.0, places=9)
        self.assertEqual(result["verdict"], CUT_ON_DETERMINED)

    def test_a_band_below_the_reflectance_threshold_has_nothing_to_halve(self):
        result = assess_cut_on_determination(WEAK_SCAN)
        self.assertEqual(result["verdict"], CUT_ON_BAND_TOO_WEAK)
        self.assertIsNone(result["cut_on_wavelength_nm"])

    def test_an_edge_below_the_scanned_range_is_named_not_defaulted(self):
        result = assess_cut_on_determination(TRUNCATED_SCAN)
        self.assertEqual(result["verdict"], CUT_ON_EDGE_OUTSIDE_SCAN)
        self.assertIsNone(result["cut_on_wavelength_nm"])

    def test_the_half_level_is_reported_even_when_no_cut_on_exists(self):
        result = assess_cut_on_determination(WEAK_SCAN)
        self.assertAlmostEqual(result["absolute_reflectance"], 0.20, places=9)
        self.assertAlmostEqual(result["half_level"], 0.10, places=9)

    def test_the_finding_quotes_the_half_level_and_the_absolute_reflectance(self):
        result = assess_cut_on_determination(FINE_SCAN)
        self.assertTrue(
            any("absolute measured reflectance" in f for f in result["findings"])
        )

    def test_a_malformed_scan_is_rejected_before_any_verdict(self):
        with self.assertRaises(ValueError):
            assess_cut_on_determination([(300.0, 40.0), (320.0, 96.0)])


if __name__ == "__main__":
    unittest.main()
