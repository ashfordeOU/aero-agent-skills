"""Contract tests for the clause 7.5.5 bare cell spectral response logic."""

import unittest

from e2008_bare_cell_spectral_response_logic import (
    DEFAULT_REQUIRED_BAND_NM,
    MAX_WAVELENGTH_STEP_NM,
    PLANCK_CHARGE_CONSTANT_NM_V,
    assess_bare_cell_spectral_response,
    common_grid,
    covers_band,
    curve_quantum_efficiencies,
    interpolate_at,
    max_wavelength_step_nm,
    mismatch_error_percent,
    quantum_efficiency,
    spectral_mismatch_factor,
    trapezoidal_integral,
    validate_curve,
    wavelength_coverage_nm,
    weighted_integral,
)

GRID_NM = [400.0 + 20.0 * step for step in range(31)]


def _test_response():
    return [(nm, 0.00050 * nm) for nm in GRID_NM]


def _reference_response():
    return [
        (nm, 0.00050 * nm * (1.0 - 0.0008 * (nm - 400.0))) for nm in GRID_NM
    ]


def _reference_spectrum():
    return [(nm, 1.5) for nm in GRID_NM]


def _simulator_spectrum():
    return [(nm, 1.5 * (1.0 + 0.001 * (nm - 700.0))) for nm in GRID_NM]


def _spec(**overrides):
    spec = {
        "test_response": _test_response(),
        "reference_response": _reference_response(),
        "simulator_spectrum": _simulator_spectrum(),
        "reference_spectrum": _reference_spectrum(),
        "error_budget_percent": 5.0,
    }
    spec.update(overrides)
    return spec


class CurveValidationTests(unittest.TestCase):
    def test_a_well_formed_curve_validates(self):
        points = validate_curve("curve", _test_response())
        self.assertEqual(len(points), len(GRID_NM))
        self.assertAlmostEqual(points[0][0], 400.0, places=9)

    def test_out_of_order_wavelengths_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve("curve", [(500.0, 0.2), (450.0, 0.3)])

    def test_repeated_wavelength_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve("curve", [(500.0, 0.2), (500.0, 0.3)])

    def test_negative_response_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve("curve", [(500.0, 0.2), (520.0, -0.1)])

    def test_single_point_curve_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve("curve", [(500.0, 0.2)])

    def test_malformed_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve("curve", [(500.0, 0.2), (520.0, 0.3, 0.4)])


class QuantumEfficiencyTests(unittest.TestCase):
    def test_efficiency_is_response_times_the_photon_energy_ratio(self):
        value = quantum_efficiency(0.5, 1000.0)
        self.assertAlmostEqual(value, 0.5 * PLANCK_CHARGE_CONSTANT_NM_V / 1000.0, places=9)

    def test_response_proportional_to_wavelength_gives_a_flat_efficiency(self):
        pairs = curve_quantum_efficiencies(_test_response())
        first = pairs[0][1]
        for _, value in pairs:
            self.assertAlmostEqual(value, first, places=9)

    def test_zero_response_gives_zero_efficiency(self):
        self.assertAlmostEqual(quantum_efficiency(0.0, 800.0), 0.0, places=9)

    def test_zero_wavelength_is_rejected(self):
        with self.assertRaises(ValueError):
            quantum_efficiency(0.5, 0.0)


class CoverageTests(unittest.TestCase):
    def test_coverage_reports_the_two_end_wavelengths(self):
        low, high = wavelength_coverage_nm(_test_response())
        self.assertAlmostEqual(low, 400.0, places=9)
        self.assertAlmostEqual(high, 1000.0, places=9)

    def test_step_is_the_widest_gap_in_the_curve(self):
        self.assertAlmostEqual(max_wavelength_step_nm(_test_response()), 20.0, places=9)

    def test_a_curve_reaching_both_band_edges_covers_the_band(self):
        self.assertTrue(covers_band(_test_response(), DEFAULT_REQUIRED_BAND_NM))

    def test_a_curve_stopping_short_of_the_band_does_not_cover_it(self):
        short = [(nm, 0.00050 * nm) for nm in GRID_NM if nm <= 900.0]
        self.assertFalse(covers_band(short, DEFAULT_REQUIRED_BAND_NM))

    def test_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            covers_band(_test_response(), (1000.0, 400.0))


class InterpolationTests(unittest.TestCase):
    def test_value_at_a_recorded_wavelength_is_the_recorded_value(self):
        points = validate_curve("curve", _test_response())
        self.assertAlmostEqual(interpolate_at(points, 600.0), 0.30, places=9)

    def test_value_between_two_points_sits_on_the_straight_line(self):
        points = [(400.0, 0.2), (500.0, 0.4)]
        self.assertAlmostEqual(interpolate_at(points, 450.0), 0.3, places=9)

    def test_value_outside_the_curve_is_zero(self):
        points = [(400.0, 0.2), (500.0, 0.4)]
        self.assertAlmostEqual(interpolate_at(points, 300.0), 0.0, places=9)
        self.assertAlmostEqual(interpolate_at(points, 900.0), 0.0, places=9)

    def test_grid_is_the_sorted_union_of_every_curve(self):
        grid = common_grid([(400.0, 1.0), (600.0, 1.0)], [(500.0, 1.0), (600.0, 1.0)])
        self.assertEqual(grid, [400.0, 500.0, 600.0])


class IntegrationTests(unittest.TestCase):
    def test_integral_of_a_constant_is_the_rectangle(self):
        self.assertAlmostEqual(
            trapezoidal_integral([0.0, 10.0, 20.0], [2.0, 2.0, 2.0]), 40.0, places=9
        )

    def test_integral_of_a_ramp_is_the_triangle(self):
        self.assertAlmostEqual(
            trapezoidal_integral([0.0, 10.0], [0.0, 4.0]), 20.0, places=9
        )

    def test_mismatched_integration_series_are_rejected(self):
        with self.assertRaises(ValueError):
            trapezoidal_integral([0.0, 10.0, 20.0], [2.0, 2.0])

    def test_weighted_integral_multiplies_response_by_spectrum(self):
        response = [(400.0, 0.2), (500.0, 0.2)]
        spectrum = [(400.0, 3.0), (500.0, 3.0)]
        self.assertAlmostEqual(
            weighted_integral(response, spectrum), 0.2 * 3.0 * 100.0, places=9
        )


class MismatchTests(unittest.TestCase):
    def test_identical_devices_cancel_to_unity(self):
        factor = spectral_mismatch_factor(
            _test_response(),
            _test_response(),
            _simulator_spectrum(),
            _reference_spectrum(),
        )
        self.assertAlmostEqual(factor, 1.0, places=9)

    def test_identical_spectra_cancel_to_unity(self):
        factor = spectral_mismatch_factor(
            _test_response(),
            _reference_response(),
            _reference_spectrum(),
            _reference_spectrum(),
        )
        self.assertAlmostEqual(factor, 1.0, places=9)

    def test_different_devices_under_a_tilted_simulator_leave_a_mismatch(self):
        factor = spectral_mismatch_factor(
            _test_response(),
            _reference_response(),
            _simulator_spectrum(),
            _reference_spectrum(),
        )
        self.assertGreater(abs(factor - 1.0), 1e-3)

    def test_a_tilted_simulator_leaves_a_few_percent_of_error(self):
        result = assess_bare_cell_spectral_response(_spec())
        self.assertGreater(result["mismatch_error_percent"], 1.0)
        self.assertLess(result["mismatch_error_percent"], 5.0)

    def test_error_is_the_distance_from_unity_in_percent(self):
        self.assertAlmostEqual(mismatch_error_percent(1.02), 2.0, places=9)
        self.assertAlmostEqual(mismatch_error_percent(0.98), 2.0, places=9)

    def test_a_perfect_factor_contributes_no_error(self):
        self.assertAlmostEqual(mismatch_error_percent(1.0), 0.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_data_set_is_valid(self):
        result = assess_bare_cell_spectral_response(_spec())
        self.assertTrue(result["valid"])
        self.assertTrue(result["within_error_budget"])
        self.assertTrue(result["curve_reports"]["test_response"]["covers_band"])

    def test_a_tight_budget_reports_the_simulator_error(self):
        result = assess_bare_cell_spectral_response(_spec(error_budget_percent=0.001))
        self.assertFalse(result["valid"])
        self.assertFalse(result["within_error_budget"])
        self.assertTrue(any("mismatch error" in item for item in result["findings"]))

    def test_a_coarse_curve_is_reported(self):
        coarse = [(400.0 + 100.0 * step, 0.00050 * (400.0 + 100.0 * step))
                  for step in range(7)]
        result = assess_bare_cell_spectral_response(_spec(test_response=coarse))
        self.assertFalse(result["valid"])
        self.assertTrue(any("coarser" in item for item in result["findings"]))

    def test_a_curve_that_misses_the_band_is_reported(self):
        short = [(nm, 0.00050 * nm) for nm in GRID_NM if nm <= 880.0]
        result = assess_bare_cell_spectral_response(_spec(test_response=short))
        self.assertTrue(any("unmeasured" in item for item in result["findings"]))

    def test_an_impossible_quantum_efficiency_is_reported(self):
        hot = [(nm, 0.00050 * nm * 3.0) for nm in GRID_NM]
        result = assess_bare_cell_spectral_response(_spec(test_response=hot))
        self.assertFalse(result["curve_reports"]["test_response"][
            "quantum_efficiency_plausible"])
        self.assertTrue(any("per photon" in item for item in result["findings"]))

    def test_max_step_is_reported_for_every_curve(self):
        result = assess_bare_cell_spectral_response(_spec())
        self.assertAlmostEqual(
            result["curve_reports"]["simulator_spectrum"]["max_step_nm"], 20.0, places=9
        )

    def test_missing_spec_key_is_rejected(self):
        spec = _spec()
        del spec["reference_spectrum"]
        with self.assertRaises(ValueError):
            assess_bare_cell_spectral_response(spec)

    def test_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_spectral_response(["test_response"])

    def test_negative_error_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_spectral_response(_spec(error_budget_percent=-1.0))

    def test_step_limit_default_matches_the_declared_constant(self):
        result = assess_bare_cell_spectral_response(_spec())
        self.assertLessEqual(
            result["curve_reports"]["test_response"]["max_step_nm"],
            MAX_WAVELENGTH_STEP_NM,
        )


if __name__ == "__main__":
    unittest.main()
