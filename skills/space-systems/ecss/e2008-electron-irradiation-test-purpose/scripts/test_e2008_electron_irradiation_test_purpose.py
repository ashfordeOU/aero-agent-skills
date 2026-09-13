"""Contract tests for the clause 6.4.3.11.1 electron irradiation purpose logic."""

import unittest

from e2008_electron_irradiation_test_purpose_logic import (
    MAX_ACCELERATION_FACTOR,
    MIN_CELLS_PER_LEVEL,
    MIN_FLUENCE_LEVELS,
    RELATIVE_TOLERANCE,
    SECONDS_PER_YEAR,
    acceleration_factor,
    assess_electron_irradiation_purpose,
    coverage_findings,
    end_of_life_fluence,
    exposure_time_s,
    mission_mean_flux,
    predicted_retention,
    remaining_fraction,
    validate_fluence_levels,
)

FITS = {
    "isc": {"coefficient": 0.04, "reference_fluence": 1.0e14},
    "voc": {"coefficient": 0.03, "reference_fluence": 1.0e14},
    "pmax": {"coefficient": 0.08, "reference_fluence": 1.0e14},
}
LEVELS = [1.0e13, 5.0e13, 2.0e14, 7.5e14]
CELLS = [5, 5, 5, 5]


class EndOfLifeFluenceTests(unittest.TestCase):
    def test_fluence_is_annual_times_years(self):
        self.assertAlmostEqual(
            end_of_life_fluence(5.0e13, 15.0), 7.5e14, places=3
        )

    def test_margin_scales_the_fluence(self):
        self.assertAlmostEqual(
            end_of_life_fluence(5.0e13, 15.0, 2.0), 1.5e15, places=3
        )

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            end_of_life_fluence(5.0e13, 15.0, 0.9)

    def test_zero_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            end_of_life_fluence(5.0e13, 0.0)

    def test_boolean_annual_fluence_rejected(self):
        with self.assertRaises(ValueError):
            end_of_life_fluence(True, 15.0)

    def test_non_finite_annual_fluence_rejected(self):
        with self.assertRaises(ValueError):
            end_of_life_fluence(float("inf"), 15.0)


class FluxAndAccelerationTests(unittest.TestCase):
    def test_seconds_per_year_constant(self):
        self.assertAlmostEqual(SECONDS_PER_YEAR, 31557600.0, places=6)

    def test_mean_flux_is_annual_fluence_over_a_year(self):
        self.assertAlmostEqual(
            mission_mean_flux(5.0e13), 1584404.3907014476, places=6
        )

    def test_acceleration_is_the_flux_ratio(self):
        self.assertAlmostEqual(
            acceleration_factor(1.0e10, mission_mean_flux(5.0e13)),
            6311.52,
            places=6,
        )

    def test_equal_fluxes_give_unit_acceleration(self):
        self.assertAlmostEqual(acceleration_factor(2.5e6, 2.5e6), 1.0, places=9)

    def test_zero_beam_flux_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(0.0, 1.0e6)

    def test_exposure_time_is_fluence_over_flux(self):
        self.assertAlmostEqual(exposure_time_s(7.5e14, 1.0e10), 75000.0, places=6)

    def test_zero_fluence_exposure_rejected(self):
        with self.assertRaises(ValueError):
            exposure_time_s(0.0, 1.0e10)

    def test_acceleration_ceiling_constant(self):
        self.assertAlmostEqual(MAX_ACCELERATION_FACTOR, 1.0e7, places=1)


class DegradationTests(unittest.TestCase):
    def test_zero_fluence_leaves_the_cell_whole(self):
        self.assertAlmostEqual(
            remaining_fraction(0.0, 0.1, 1.0e14), 1.0, places=9
        )

    def test_reference_fluence_costs_a_log_of_two(self):
        self.assertAlmostEqual(
            remaining_fraction(1.0e14, 0.1, 1.0e14), 0.9698970004336018, places=9
        )

    def test_nine_references_cost_one_full_coefficient(self):
        self.assertAlmostEqual(
            remaining_fraction(9.0e14, 0.1, 1.0e14), 0.9, places=9
        )

    def test_retention_falls_as_fluence_rises(self):
        low = remaining_fraction(1.0e13, 0.08, 1.0e14)
        high = remaining_fraction(1.0e15, 0.08, 1.0e14)
        self.assertLess(high, low)

    def test_retention_is_clamped_at_zero(self):
        self.assertAlmostEqual(
            remaining_fraction(1.0e20, 0.9, 1.0e14), 0.0, places=9
        )

    def test_coefficient_at_zero_rejected(self):
        with self.assertRaises(ValueError):
            remaining_fraction(1.0e14, 0.0, 1.0e14)

    def test_coefficient_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            remaining_fraction(1.0e14, 1.0, 1.0e14)

    def test_negative_fluence_rejected(self):
        with self.assertRaises(ValueError):
            remaining_fraction(-1.0e14, 0.08, 1.0e14)

    def test_zero_reference_fluence_rejected(self):
        with self.assertRaises(ValueError):
            remaining_fraction(1.0e14, 0.08, 0.0)


class RetentionTests(unittest.TestCase):
    def test_every_parameter_is_predicted(self):
        retention = predicted_retention(7.5e14, FITS)
        self.assertEqual(sorted(retention), ["isc", "pmax", "voc"])

    def test_maximum_power_retention_value(self):
        self.assertAlmostEqual(
            predicted_retention(7.5e14, FITS)["pmax"],
            0.9256464859428566,
            places=9,
        )

    def test_short_circuit_current_retention_value(self):
        self.assertAlmostEqual(
            predicted_retention(7.5e14, FITS)["isc"],
            0.9628232429714283,
            places=9,
        )

    def test_voltage_degrades_least_of_the_three(self):
        retention = predicted_retention(7.5e14, FITS)
        self.assertGreater(retention["voc"], retention["pmax"])

    def test_empty_parameter_set_rejected(self):
        with self.assertRaises(ValueError):
            predicted_retention(7.5e14, {})

    def test_fit_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            predicted_retention(7.5e14, {"pmax": {"coefficient": 0.08}})

    def test_non_mapping_fit_rejected(self):
        with self.assertRaises(ValueError):
            predicted_retention(7.5e14, {"pmax": 0.08})


class FluenceLevelTests(unittest.TestCase):
    def test_rising_levels_are_returned_as_floats(self):
        self.assertEqual(
            validate_fluence_levels([1.0e13, 5.0e13]), [1.0e13, 5.0e13]
        )

    def test_repeated_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_levels([1.0e13, 1.0e13, 5.0e13])

    def test_falling_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_levels([5.0e13, 1.0e13])

    def test_empty_level_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_levels([])

    def test_non_sequence_levels_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_levels({"low": 1.0e13})


class CoverageTests(unittest.TestCase):
    def test_adequate_plan_gives_no_finding(self):
        self.assertEqual(coverage_findings(LEVELS, CELLS, 7.5e14), [])

    def test_highest_level_exactly_on_the_target_is_adequate(self):
        self.assertEqual(
            coverage_findings([1.0e13, 5.0e13, 7.5e14], [5, 5, 5], 7.5e14), []
        )

    def test_short_top_level_is_a_finding(self):
        findings = coverage_findings(
            [1.0e13, 5.0e13, 2.0e14], [5, 5, 5], 7.5e14
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("end of life", findings[0])

    def test_too_few_levels_is_a_finding(self):
        findings = coverage_findings([1.0e13, 7.5e14], [5, 5], 7.5e14)
        self.assertEqual(len(findings), 1)
        self.assertIn("degradation trend", findings[0])

    def test_thin_level_is_a_finding(self):
        findings = coverage_findings(LEVELS, [5, 1, 5, 5], 7.5e14)
        self.assertEqual(len(findings), 1)
        self.assertIn("carries 1 cells", findings[0])

    def test_default_level_and_cell_minimums(self):
        self.assertEqual(MIN_FLUENCE_LEVELS, 3)
        self.assertEqual(MIN_CELLS_PER_LEVEL, 3)

    def test_cell_count_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings(LEVELS, [5, 5, 5], 7.5e14)

    def test_non_integer_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings(LEVELS, [5, 5.0, 5, 5], 7.5e14)

    def test_zero_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings(LEVELS, [5, 0, 5, 5], 7.5e14)

    def test_relative_tolerance_is_small(self):
        self.assertAlmostEqual(RELATIVE_TOLERANCE, 1e-9, places=12)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "annual_fluence": 5.0e13,
            "mission_years": 15.0,
            "fluence_levels": list(LEVELS),
            "cells_per_level": list(CELLS),
            "beam_flux": 1.0e10,
            "parameters": dict(FITS),
            "required_eol_fraction": 0.85,
        }
        spec.update(overrides)
        return spec

    def test_sound_campaign_meets_the_purpose(self):
        result = assess_electron_irradiation_purpose(self._spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["purpose_met"])

    def test_end_of_life_fluence_is_reported(self):
        result = assess_electron_irradiation_purpose(self._spec())
        self.assertAlmostEqual(result["eol_fluence"], 7.5e14, places=3)

    def test_acceleration_is_reported(self):
        result = assess_electron_irradiation_purpose(self._spec())
        self.assertAlmostEqual(result["acceleration_factor"], 6311.52, places=6)

    def test_total_beam_time_is_reported(self):
        result = assess_electron_irradiation_purpose(self._spec())
        self.assertAlmostEqual(result["total_exposure_s"], 101000.0, places=6)

    def test_power_retention_and_margin_are_reported(self):
        result = assess_electron_irradiation_purpose(self._spec())
        self.assertAlmostEqual(
            result["power_retention"], 0.9256464859428566, places=9
        )
        self.assertAlmostEqual(
            result["eol_margin"], 0.0756464859428566, places=9
        )

    def test_beam_slower_than_the_environment_is_a_finding(self):
        result = assess_electron_irradiation_purpose(
            self._spec(beam_flux=1.0e5)
        )
        self.assertFalse(result["purpose_met"])
        self.assertTrue(
            any("not an accelerated check" in item for item in result["findings"])
        )

    def test_beam_beyond_the_acceleration_bound_is_a_finding(self):
        result = assess_electron_irradiation_purpose(
            self._spec(beam_flux=1.0e15)
        )
        self.assertTrue(
            any("outruns the recovery" in item for item in result["findings"])
        )

    def test_margin_factor_raises_the_target_fluence(self):
        result = assess_electron_irradiation_purpose(self._spec(margin_factor=2.0))
        self.assertAlmostEqual(result["eol_fluence"], 1.5e15, places=3)
        self.assertFalse(result["purpose_met"])

    def test_shortfall_against_the_power_budget_is_a_finding(self):
        result = assess_electron_irradiation_purpose(
            self._spec(required_eol_fraction=0.98)
        )
        self.assertTrue(
            any("power budget assumes" in item for item in result["findings"])
        )

    def test_every_parameter_appears_in_the_retention_report(self):
        result = assess_electron_irradiation_purpose(self._spec())
        self.assertEqual(sorted(result["retention"]), ["isc", "pmax", "voc"])

    def test_missing_power_parameter_rejected(self):
        spec = self._spec(parameters={"isc": FITS["isc"]})
        with self.assertRaises(ValueError):
            assess_electron_irradiation_purpose(spec)

    def test_required_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_electron_irradiation_purpose(
                self._spec(required_eol_fraction=1.2)
            )

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["beam_flux"]
        with self.assertRaises(ValueError):
            assess_electron_irradiation_purpose(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_electron_irradiation_purpose(["annual_fluence"])

    def test_acceleration_ceiling_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_electron_irradiation_purpose(self._spec(max_acceleration=1.0))


if __name__ == "__main__":
    unittest.main()
