"""Contract tests for the clause 6.4.3.5.1 spectral response purpose logic."""

import math
import unittest

from e2008_sca_spectral_response_purpose_logic import (
    DEFAULT_SPECTRAL_POLICY,
    ERROR_BUDGET_EXCEEDED,
    SIMULATOR_SPECTRUM_NOT_ACCEPTED,
    SPECTRAL_DATA_INSUFFICIENT,
    SPECTRAL_RESPONSE_SUPPORTED,
    assess_spectral_response_purpose,
    band_is_covered,
    band_span_nm,
    combined_uncertainty_fraction,
    corrected_short_circuit_current_a,
    max_wavelength_step_nm,
    mismatch_deviation,
    mismatch_within_tolerance,
    sample_count,
    shared_grid,
    spectral_mismatch_factor,
    trapezoidal_integral,
    validate_series,
    validate_spectral_policy,
    weighted_integral,
)

BAND_START_NM = 350.0
BAND_END_NM = 1800.0
GRID_POINTS = 60


def _grid(start=BAND_START_NM, end=BAND_END_NM, count=GRID_POINTS):
    step = (end - start) / (count - 1)
    return [start + index * step for index in range(count)]


def _reference_spectrum(grid=None):
    grid = _grid() if grid is None else grid
    return [
        (w, 1.6 * math.exp(-((w - 500.0) / 420.0) ** 2) + 0.05) for w in grid
    ]


def _simulator_spectrum(tilt=0.1, grid=None):
    return [
        (w, v * (1.0 + tilt * (w - 1075.0) / 725.0))
        for w, v in _reference_spectrum(grid)
    ]


def _test_cell_response(grid=None):
    grid = _grid() if grid is None else grid
    return [(w, math.exp(-((w - 800.0) / 450.0) ** 2)) for w in grid]


def _reference_cell_response(grid=None):
    grid = _grid() if grid is None else grid
    return [(w, math.exp(-((w - 700.0) / 400.0) ** 2)) for w in grid]


def _policy(**overrides):
    policy = dict(DEFAULT_SPECTRAL_POLICY)
    policy.update(overrides)
    return policy


def _case(tilt=0.1, grid=None, **overrides):
    case = {
        "reference_spectrum": _reference_spectrum(grid),
        "simulator_spectrum": _simulator_spectrum(tilt, grid),
        "test_cell_response": _test_cell_response(grid),
        "reference_cell_response": _reference_cell_response(grid),
        "measured_short_circuit_current_a": 0.5,
        "other_uncertainty_fractions": [0.008, 0.005],
    }
    case.update(overrides)
    return case


def _factor(tilt=0.1):
    return spectral_mismatch_factor(
        _reference_spectrum(),
        _simulator_spectrum(tilt),
        _test_cell_response(),
        _reference_cell_response(),
    )


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_spectral_policy(DEFAULT_SPECTRAL_POLICY), DEFAULT_SPECTRAL_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_policy("am0")

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_policy(_policy(band_start_nm=1800.0, band_end_nm=350.0))

    def test_a_two_sample_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_policy(_policy(min_samples=2))

    def test_zero_mismatch_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_policy(_policy(max_mismatch_deviation=0.0))


class SeriesTests(unittest.TestCase):
    def test_a_well_formed_series_validates(self):
        self.assertEqual(
            sample_count("reference_spectrum", _reference_spectrum()), GRID_POINTS
        )

    def test_an_unordered_series_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_series("test_cell_response", [(500.0, 1.0), (400.0, 1.0), (600.0, 1.0)])

    def test_a_repeated_wavelength_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_series("test_cell_response", [(400.0, 1.0), (400.0, 0.9), (600.0, 1.0)])

    def test_a_negative_response_value_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_series("test_cell_response", [(400.0, 1.0), (500.0, -0.1), (600.0, 1.0)])

    def test_a_two_sample_series_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_series("reference_spectrum", [(400.0, 1.0), (600.0, 1.0)])

    def test_a_malformed_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_series("reference_spectrum", [(400.0, 1.0), (500.0,), (600.0, 1.0)])

    def test_the_coarsest_step_is_reported(self):
        step = max_wavelength_step_nm("reference_spectrum", _reference_spectrum())
        self.assertAlmostEqual(
            _ratio(step, (BAND_END_NM - BAND_START_NM) / (GRID_POINTS - 1)),
            1.0,
            places=12,
        )

    def test_the_span_reports_both_ends(self):
        start, end = band_span_nm("reference_spectrum", _reference_spectrum())
        self.assertAlmostEqual(start, BAND_START_NM, places=9)
        self.assertAlmostEqual(end, BAND_END_NM, places=9)

    def test_a_series_spanning_the_whole_band_is_covered(self):
        self.assertTrue(band_is_covered("reference_spectrum", _reference_spectrum()))

    def test_a_series_starting_inside_the_band_is_not_covered(self):
        truncated = _reference_spectrum(_grid(start=500.0))
        self.assertFalse(band_is_covered("reference_spectrum", truncated))

    def test_a_series_stopping_short_of_the_band_is_not_covered(self):
        truncated = _reference_spectrum(_grid(end=1200.0))
        self.assertFalse(band_is_covered("reference_spectrum", truncated))


class IntegralTests(unittest.TestCase):
    def test_a_triangle_integrates_to_its_area(self):
        series = [(100.0, 0.0), (200.0, 2.0), (300.0, 0.0)]
        self.assertAlmostEqual(
            _ratio(trapezoidal_integral("triangle", series), 200.0), 1.0, places=12
        )

    def test_a_flat_series_integrates_to_its_rectangle(self):
        series = [(100.0, 3.0), (200.0, 3.0), (300.0, 3.0)]
        self.assertAlmostEqual(
            _ratio(trapezoidal_integral("flat", series), 600.0), 1.0, places=12
        )

    def test_a_zero_series_integrates_to_zero(self):
        series = [(100.0, 0.0), (200.0, 0.0), (300.0, 0.0)]
        self.assertAlmostEqual(trapezoidal_integral("empty", series), 0.0, places=12)

    def test_the_weighted_integral_multiplies_point_by_point(self):
        spectrum = [(100.0, 2.0), (200.0, 2.0), (300.0, 2.0)]
        response = [(100.0, 0.5), (200.0, 0.5), (300.0, 0.5)]
        self.assertAlmostEqual(
            _ratio(weighted_integral("s", spectrum, "r", response), 200.0),
            1.0,
            places=12,
        )

    def test_two_series_on_one_grid_share_it(self):
        grid = shared_grid(
            "reference_spectrum", _reference_spectrum(),
            "test_cell_response", _test_cell_response(),
        )
        self.assertEqual(len(grid), GRID_POINTS)

    def test_series_of_different_lengths_are_refused(self):
        with self.assertRaises(ValueError):
            shared_grid(
                "reference_spectrum", _reference_spectrum(),
                "test_cell_response", _test_cell_response(_grid(count=30)),
            )

    def test_series_on_shifted_grids_are_refused(self):
        with self.assertRaises(ValueError):
            shared_grid(
                "reference_spectrum", _reference_spectrum(),
                "test_cell_response", _test_cell_response(_grid(start=360.0)),
            )


class MismatchTests(unittest.TestCase):
    def test_a_simulator_matching_the_reference_gives_unity(self):
        self.assertAlmostEqual(_factor(0.0), 1.0, places=12)

    def test_unity_shows_no_deviation(self):
        self.assertAlmostEqual(mismatch_deviation(_factor(0.0)), 0.0, places=12)

    def test_a_tilted_simulator_moves_the_factor_off_unity(self):
        self.assertGreater(mismatch_deviation(_factor(0.3)), 0.01)

    def test_a_larger_tilt_moves_the_factor_further(self):
        self.assertGreater(mismatch_deviation(_factor(0.6)), mismatch_deviation(_factor(0.3)))

    def test_a_small_tilt_stays_inside_the_tolerance(self):
        self.assertTrue(mismatch_within_tolerance(_factor(0.1)))

    def test_a_large_tilt_falls_outside_the_tolerance(self):
        self.assertFalse(mismatch_within_tolerance(_factor(0.6)))

    def test_a_tolerance_set_at_the_deviation_admits_it(self):
        deviation = mismatch_deviation(_factor(0.3))
        self.assertTrue(
            mismatch_within_tolerance(
                _factor(0.3), _policy(max_mismatch_deviation=deviation)
            )
        )

    def test_a_zero_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            mismatch_deviation(0.0)

    def test_the_correction_divides_the_measured_current(self):
        self.assertAlmostEqual(
            _ratio(corrected_short_circuit_current_a(0.5, 1.25), 0.4), 1.0, places=12
        )

    def test_a_unity_factor_leaves_the_current_alone(self):
        self.assertAlmostEqual(
            _ratio(corrected_short_circuit_current_a(0.5, 1.0), 0.5), 1.0, places=12
        )

    def test_a_negative_measured_current_is_rejected(self):
        with self.assertRaises(ValueError):
            corrected_short_circuit_current_a(-0.5, 1.0)


class UncertaintyTests(unittest.TestCase):
    def test_terms_combine_as_a_root_sum_of_squares(self):
        self.assertAlmostEqual(
            _ratio(combined_uncertainty_fraction([0.03, 0.04]), 0.05), 1.0, places=12
        )

    def test_a_single_term_survives_unchanged(self):
        self.assertAlmostEqual(
            _ratio(combined_uncertainty_fraction([0.02]), 0.02), 1.0, places=12
        )

    def test_an_empty_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_fraction([])

    def test_a_negative_term_is_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_fraction([0.02, -0.01])

    def test_a_non_sequence_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_fraction(0.02)


class AssessmentTests(unittest.TestCase):
    def test_a_good_data_set_supports_both_uses(self):
        result = assess_spectral_response_purpose(_case())
        self.assertEqual(result["verdict"], SPECTRAL_RESPONSE_SUPPORTED)
        self.assertEqual(result["findings"], [])

    def test_the_mismatch_factor_is_reported(self):
        result = assess_spectral_response_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["mismatch_factor"], _factor(0.1)), 1.0, places=12
        )

    def test_the_corrected_current_is_reported(self):
        result = assess_spectral_response_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["corrected_current_a"], 0.5 / _factor(0.1)), 1.0, places=12
        )

    def test_the_mismatch_term_enters_the_uncertainty_budget(self):
        result = assess_spectral_response_purpose(_case())
        self.assertGreater(
            result["combined_uncertainty_fraction"],
            result["mismatch_deviation"],
        )

    def test_a_coarse_grid_makes_the_data_insufficient(self):
        result = assess_spectral_response_purpose(_case(grid=_grid(count=25)))
        self.assertEqual(result["verdict"], SPECTRAL_DATA_INSUFFICIENT)
        self.assertIsNone(result["mismatch_factor"])

    def test_a_short_band_makes_the_data_insufficient(self):
        result = assess_spectral_response_purpose(_case(grid=_grid(end=1200.0)))
        self.assertEqual(result["verdict"], SPECTRAL_DATA_INSUFFICIENT)
        self.assertTrue(result["band_gaps"])

    def test_every_series_with_a_gap_is_named(self):
        result = assess_spectral_response_purpose(_case(grid=_grid(start=500.0)))
        self.assertEqual(len(result["band_gaps"]), 4)

    def test_a_badly_tilted_simulator_is_not_accepted(self):
        result = assess_spectral_response_purpose(_case(tilt=0.6))
        self.assertEqual(result["verdict"], SIMULATOR_SPECTRUM_NOT_ACCEPTED)
        self.assertFalse(result["mismatch_in_tolerance"])

    def test_a_thin_error_budget_is_exceeded_by_the_mismatch_term(self):
        result = assess_spectral_response_purpose(
            _case(tilt=0.3, other_uncertainty_fractions=[0.025])
        )
        self.assertEqual(result["verdict"], ERROR_BUDGET_EXCEEDED)
        self.assertTrue(result["mismatch_in_tolerance"])

    def test_an_absent_response_curve_is_rejected(self):
        case = _case()
        del case["reference_cell_response"]
        with self.assertRaises(ValueError):
            assess_spectral_response_purpose(case)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_spectral_response_purpose(["reference_spectrum"])

    def test_a_non_sequence_uncertainty_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_spectral_response_purpose(_case(other_uncertainty_fractions=0.01))

    def test_a_case_without_a_measured_current_still_judges_the_simulator(self):
        case = _case()
        del case["measured_short_circuit_current_a"]
        result = assess_spectral_response_purpose(case)
        self.assertEqual(result["verdict"], SPECTRAL_RESPONSE_SUPPORTED)
        self.assertIsNone(result["corrected_current_a"])


if __name__ == "__main__":
    unittest.main()
