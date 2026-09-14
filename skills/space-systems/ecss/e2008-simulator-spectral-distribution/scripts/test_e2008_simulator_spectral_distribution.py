#!/usr/bin/env python3
"""Contract test for the solar simulator spectrum check, clause 10.1.1 (offline)."""

import unittest

from e2008_simulator_spectral_distribution_logic import (
    DEFAULT_MATCH_GRADE_LIMITS,
    MATCH_TOLERANCE,
    OUTSIDE_MATCH_BANDS,
    SIMULATOR_ACCEPTED,
    SIMULATOR_REJECTED,
    SPECTRAL_MATCH_GRADES,
    band_fractions,
    evaluate_spectral_distribution,
    grade_rank,
    grade_ratio,
    integrate_band,
    integrate_spectrum,
    spectral_irradiance_at,
    spectral_match_ratios,
    validate_bands,
    validate_match_grade_limits,
    validate_spectrum,
    worst_grade,
)

# A flat reference makes every band's share exactly one third, so the
# share ratio of a simulator band is a number a reader can check by hand.
REFERENCE = [(400.0, 1.0), (600.0, 1.0), (800.0, 1.0), (1000.0, 1.0)]
BANDS = [(400.0, 600.0), (600.0, 800.0), (800.0, 1000.0)]

# Uniform at twice the reference: perfect shape, and a level of its own.
UNIFORM = [(400.0, 2.0), (600.0, 2.0), (800.0, 2.0), (1000.0, 2.0)]

# Band integrals 200 / 300 / 300 of 800: shares 0.25 / 0.375 / 0.375, so
# the first band's share ratio sits exactly on the tightest grade limit.
ON_LIMIT = [(400.0, 1.0), (600.0, 1.0), (800.0, 2.0), (1000.0, 1.0)]

# Band integrals 200 / 400 / 400 of 1000: the first band's share ratio
# sits exactly on the second grade's lower limit.
ONE_GRADE_DOWN = [(400.0, 1.0), (600.0, 1.0), (800.0, 3.0), (1000.0, 1.0)]

# Nothing at all in the first band: one band outside, two matching.
BLIND_BAND = [(400.0, 0.0), (600.0, 0.0), (800.0, 3.0), (1000.0, 3.0)]


def _spec(**overrides):
    spec = {
        "simulator_id": "sim-am0-03",
        "simulator_spectrum": UNIFORM,
        "reference_spectrum": REFERENCE,
        "bands": BANDS,
        "target_total_irradiance": 1200.0,
        "total_irradiance_tolerance": 0.02,
        "reference_coverage_floor": 0.9,
    }
    spec.update(overrides)
    return spec


class SpectrumValidationTests(unittest.TestCase):
    def test_a_rising_curve_validates(self):
        self.assertEqual(len(validate_spectrum(REFERENCE)), 4)

    def test_a_single_sample_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(400.0, 1.0)])

    def test_a_repeated_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(400.0, 1.0), (400.0, 2.0), (600.0, 1.0)])

    def test_an_out_of_order_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(600.0, 1.0), (400.0, 1.0)])

    def test_a_negative_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(400.0, 1.0), (600.0, -0.5)])

    def test_a_non_positive_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(0.0, 1.0), (600.0, 1.0)])

    def test_a_boolean_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectrum([(400.0, True), (600.0, 1.0)])


class BandSetValidationTests(unittest.TestCase):
    def test_a_contiguous_band_set_validates(self):
        self.assertEqual(len(validate_bands(BANDS)), 3)

    def test_a_single_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(400.0, 600.0)])

    def test_a_gap_between_bands_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(400.0, 600.0), (650.0, 800.0)])

    def test_overlapping_bands_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(400.0, 600.0), (550.0, 800.0)])

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(600.0, 400.0), (600.0, 800.0)])

    def test_a_band_set_outside_the_measured_range_rejected(self):
        with self.assertRaises(ValueError):
            band_fractions(REFERENCE, [(300.0, 600.0), (600.0, 1000.0)])


class InterpolationAndIntegrationTests(unittest.TestCase):
    def test_interpolation_sits_between_the_bracketing_samples(self):
        self.assertAlmostEqual(
            spectral_irradiance_at([(400.0, 0.0), (500.0, 10.0)], 450.0), 5.0, places=9
        )

    def test_interpolation_at_a_sample_returns_that_sample(self):
        self.assertAlmostEqual(
            spectral_irradiance_at(REFERENCE, 600.0), 1.0, places=9
        )

    def test_interpolation_outside_the_measured_range_rejected(self):
        with self.assertRaises(ValueError):
            spectral_irradiance_at(REFERENCE, 1200.0)

    def test_a_flat_band_integral_is_width_times_height(self):
        self.assertAlmostEqual(
            integrate_band(REFERENCE, 400.0, 600.0), 200.0, places=9
        )

    def test_a_band_edge_between_samples_is_interpolated_not_snapped(self):
        ramp = [(400.0, 0.0), (600.0, 2.0)]
        self.assertAlmostEqual(integrate_band(ramp, 500.0, 600.0), 150.0, places=9)

    def test_the_whole_range_integral_equals_the_sum_of_its_bands(self):
        whole = integrate_spectrum(REFERENCE)
        pieces = sum(integrate_band(REFERENCE, low, high) for low, high in BANDS)
        self.assertAlmostEqual(whole, pieces, places=9)

    def test_an_inverted_integration_interval_rejected(self):
        with self.assertRaises(ValueError):
            integrate_band(REFERENCE, 800.0, 600.0)


class ShareTests(unittest.TestCase):
    def test_a_flat_reference_splits_evenly_across_equal_bands(self):
        shares = band_fractions(REFERENCE, BANDS)
        for fraction in shares["fractions"]:
            self.assertAlmostEqual(fraction, 1.0 / 3.0, places=9)

    def test_shares_are_scale_free_so_twice_the_level_gives_the_same_shares(self):
        one = band_fractions(REFERENCE, BANDS)["fractions"]
        two = band_fractions(UNIFORM, BANDS)["fractions"]
        for left, right in zip(one, two):
            self.assertAlmostEqual(left, right, places=9)

    def test_the_band_set_total_does_follow_the_level(self):
        self.assertAlmostEqual(
            band_fractions(UNIFORM, BANDS)["band_set_total"], 1200.0, places=9
        )

    def test_a_dark_spectrum_has_no_shares_to_report(self):
        dark = [(400.0, 0.0), (600.0, 0.0), (800.0, 0.0), (1000.0, 0.0)]
        with self.assertRaises(ValueError):
            band_fractions(dark, BANDS)

    def test_a_reference_band_with_no_irradiance_has_no_share_ratio(self):
        reference = [(400.0, 1.0), (600.0, 1.0), (800.0, 0.0), (1000.0, 0.0)]
        with self.assertRaises(ValueError):
            spectral_match_ratios(UNIFORM, reference, BANDS)

    def test_a_perfect_shape_gives_unit_ratios_in_every_band(self):
        ratios = spectral_match_ratios(UNIFORM, REFERENCE, BANDS)["ratios"]
        for ratio in ratios:
            self.assertAlmostEqual(ratio, 1.0, places=9)


class GradeTests(unittest.TestCase):
    def test_grades_run_best_first(self):
        self.assertEqual(SPECTRAL_MATCH_GRADES[0], "spectral-match-a")
        self.assertLess(
            grade_rank("spectral-match-a"), grade_rank("spectral-match-c")
        )

    def test_outside_every_band_is_the_worst_rank(self):
        self.assertGreater(
            grade_rank(OUTSIDE_MATCH_BANDS), grade_rank("spectral-match-c")
        )

    def test_a_unit_ratio_takes_the_best_grade(self):
        self.assertEqual(grade_ratio(1.0), "spectral-match-a")

    def test_a_ratio_exactly_on_the_tightest_limit_keeps_the_best_grade(self):
        self.assertEqual(grade_ratio(0.75), "spectral-match-a")
        self.assertEqual(grade_ratio(1.25), "spectral-match-a")

    def test_a_ratio_just_past_the_tightest_limit_drops_one_grade(self):
        self.assertEqual(grade_ratio(0.7), "spectral-match-b")

    def test_a_far_ratio_drops_to_the_loosest_grade(self):
        self.assertEqual(grade_ratio(0.45), "spectral-match-c")

    def test_a_ratio_outside_every_grade_is_named_as_such(self):
        self.assertEqual(grade_ratio(0.2), OUTSIDE_MATCH_BANDS)

    def test_the_worst_band_sets_the_result_not_the_average(self):
        self.assertEqual(
            worst_grade(
                [
                    "spectral-match-a",
                    "spectral-match-a",
                    "spectral-match-a",
                    "spectral-match-a",
                    "spectral-match-a",
                    OUTSIDE_MATCH_BANDS,
                ]
            ),
            OUTSIDE_MATCH_BANDS,
        )

    def test_an_all_matching_set_keeps_the_best_grade(self):
        self.assertEqual(
            worst_grade(["spectral-match-a", "spectral-match-a"]), "spectral-match-a"
        )

    def test_an_empty_grade_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_grade([])

    def test_an_unrecognized_grade_rejected(self):
        with self.assertRaises(ValueError):
            grade_rank("spectral-match-z")

    def test_a_grade_limit_table_missing_a_grade_rejected(self):
        table = dict(DEFAULT_MATCH_GRADE_LIMITS)
        del table["spectral-match-b"]
        with self.assertRaises(ValueError):
            validate_match_grade_limits(table)

    def test_a_grade_limit_table_that_does_not_nest_rejected(self):
        table = dict(DEFAULT_MATCH_GRADE_LIMITS)
        table["spectral-match-b"] = (0.9, 1.1)
        with self.assertRaises(ValueError):
            validate_match_grade_limits(table)

    def test_a_grade_limit_band_that_misses_unity_rejected(self):
        table = dict(DEFAULT_MATCH_GRADE_LIMITS)
        table["spectral-match-a"] = (1.1, 1.3)
        with self.assertRaises(ValueError):
            validate_match_grade_limits(table)

    def test_a_project_grade_table_overrides_the_default(self):
        table = {
            "spectral-match-a": (0.95, 1.05),
            "spectral-match-b": (0.9, 1.1),
            "spectral-match-c": (0.8, 1.2),
        }
        self.assertEqual(grade_ratio(0.92, table), "spectral-match-b")

    def test_match_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(MATCH_TOLERANCE, 1e-6)


class SimulatorEvaluationTests(unittest.TestCase):
    def test_a_matching_simulator_at_the_right_level_is_accepted(self):
        result = evaluate_spectral_distribution(_spec())
        self.assertEqual(result["verdict"], SIMULATOR_ACCEPTED)
        self.assertEqual(result["overall_grade"], "spectral-match-a")
        self.assertAlmostEqual(result["reference_coverage"], 1.0, places=9)

    def test_a_perfect_shape_at_the_wrong_level_is_still_rejected(self):
        result = evaluate_spectral_distribution(
            _spec(target_total_irradiance=600.0)
        )
        self.assertEqual(result["overall_grade"], "spectral-match-a")
        self.assertTrue(result["distribution_acceptable"])
        self.assertFalse(result["level_acceptable"])
        self.assertEqual(result["verdict"], SIMULATOR_REJECTED)

    def test_the_level_deviation_is_signed_against_the_target(self):
        result = evaluate_spectral_distribution(
            _spec(target_total_irradiance=1500.0)
        )
        self.assertAlmostEqual(result["level_deviation"], -0.2, places=9)

    def test_a_level_exactly_on_its_tolerance_is_accepted(self):
        result = evaluate_spectral_distribution(
            _spec(
                target_total_irradiance=1000.0,
                total_irradiance_tolerance=0.2,
            )
        )
        self.assertAlmostEqual(result["level_deviation"], 0.2, places=9)
        self.assertTrue(result["level_acceptable"])

    def test_a_band_share_exactly_on_the_tightest_limit_keeps_the_best_grade(self):
        result = evaluate_spectral_distribution(
            _spec(simulator_spectrum=ON_LIMIT, target_total_irradiance=800.0)
        )
        self.assertAlmostEqual(result["bands"][0]["share_ratio"], 0.75, places=9)
        self.assertEqual(result["overall_grade"], "spectral-match-a")
        self.assertEqual(result["verdict"], SIMULATOR_ACCEPTED)

    def test_one_band_off_shape_drops_the_whole_result_one_grade(self):
        result = evaluate_spectral_distribution(
            _spec(simulator_spectrum=ONE_GRADE_DOWN, target_total_irradiance=1000.0)
        )
        self.assertAlmostEqual(result["bands"][0]["share_ratio"], 0.6, places=9)
        self.assertEqual(result["bands"][1]["grade"], "spectral-match-a")
        self.assertEqual(result["overall_grade"], "spectral-match-b")
        self.assertFalse(result["distribution_acceptable"])
        self.assertEqual(result["verdict"], SIMULATOR_REJECTED)

    def test_a_looser_required_grade_accepts_the_same_measurement(self):
        result = evaluate_spectral_distribution(
            _spec(
                simulator_spectrum=ONE_GRADE_DOWN,
                target_total_irradiance=1000.0,
                required_grade="spectral-match-b",
            )
        )
        self.assertEqual(result["overall_grade"], "spectral-match-b")
        self.assertTrue(result["distribution_acceptable"])
        self.assertEqual(result["verdict"], SIMULATOR_ACCEPTED)

    def test_two_matching_bands_do_not_rescue_one_blind_band(self):
        result = evaluate_spectral_distribution(
            _spec(simulator_spectrum=BLIND_BAND, target_total_irradiance=900.0)
        )
        self.assertAlmostEqual(result["bands"][0]["share_ratio"], 0.0, places=9)
        self.assertEqual(result["bands"][0]["grade"], OUTSIDE_MATCH_BANDS)
        self.assertEqual(result["bands"][1]["grade"], "spectral-match-a")
        self.assertEqual(result["overall_grade"], OUTSIDE_MATCH_BANDS)
        self.assertEqual(result["verdict"], SIMULATOR_REJECTED)

    def test_the_worst_band_is_named_so_the_report_is_not_a_bare_rejection(self):
        result = evaluate_spectral_distribution(
            _spec(simulator_spectrum=BLIND_BAND, target_total_irradiance=900.0)
        )
        self.assertEqual(result["worst_band"], (400.0, 600.0))

    def test_a_band_set_that_spans_part_of_the_reference_is_a_finding(self):
        result = evaluate_spectral_distribution(
            _spec(
                bands=[(400.0, 600.0), (600.0, 700.0)],
                target_total_irradiance=600.0,
            )
        )
        self.assertAlmostEqual(result["reference_coverage"], 0.5, places=9)
        self.assertFalse(result["coverage_acceptable"])
        self.assertTrue(result["distribution_acceptable"])
        self.assertEqual(result["verdict"], SIMULATOR_REJECTED)

    def test_coverage_exactly_on_its_floor_is_accepted(self):
        result = evaluate_spectral_distribution(
            _spec(
                bands=[(400.0, 600.0), (600.0, 700.0)],
                target_total_irradiance=600.0,
                reference_coverage_floor=0.5,
            )
        )
        self.assertTrue(result["coverage_acceptable"])
        self.assertEqual(result["verdict"], SIMULATOR_ACCEPTED)

    def test_every_failing_arm_contributes_its_own_finding(self):
        result = evaluate_spectral_distribution(
            _spec(
                simulator_spectrum=BLIND_BAND,
                bands=[(400.0, 600.0), (600.0, 700.0)],
                target_total_irradiance=50.0,
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 2)
        self.assertEqual(result["verdict"], SIMULATOR_REJECTED)

    def test_a_zero_target_level_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_spectral_distribution(_spec(target_total_irradiance=0.0))

    def test_a_level_tolerance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_spectral_distribution(_spec(total_irradiance_tolerance=1.0))

    def test_a_coverage_floor_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_spectral_distribution(_spec(reference_coverage_floor=0.0))

    def test_a_required_grade_outside_the_ladder_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_spectral_distribution(_spec(required_grade=OUTSIDE_MATCH_BANDS))

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["bands"]
        with self.assertRaises(ValueError):
            evaluate_spectral_distribution(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_spectral_distribution("switch the lamp on")


if __name__ == "__main__":
    unittest.main()
