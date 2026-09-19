"""Contract test for the radiation test-report leaf (stdlib unittest)."""

import unittest

from q7006_test_report_logic import (
    ENVIRONMENT_NUMERIC_FIELDS,
    ENVIRONMENT_TEXT_FIELDS,
    EXPOSURE_QUANTITIES,
    EXPOSURE_TOLERANCE,
    IDENTIFICATION_FIELDS,
    MAX_CHAMBER_PRESSURE_PA,
    MAX_PARTICLE_ACCELERATION,
    MAX_UV_ACCELERATION_SUNS,
    REPORT_DECIMALS,
    RESULT_FIELDS,
    acceleration_factor,
    assess_test_report,
    combined_standard_uncertainty,
    expanded_uncertainty,
    exposure_deviation,
    exposure_within_tolerance,
    missing_environment,
    missing_exposure,
    missing_identification,
    missing_results,
    resolution_findings,
    round_to_report,
)


def report(**kw):
    record = {
        "report_id": "RAD-2026-0084",
        "material_designation": "white pigmented silicone coating",
        "batch_or_lot": "L-4471",
        "dosimetry_traceability": "Faraday cup calibrated against a national standard",
        "particle_species": "electron",
        "uv_spectral_band": "near and vacuum ultraviolet",
        "particle_energy_kev": 100.0,
        "particle_flux_cm2_s": 1.0e9,
        "uv_irradiance_suns": 3.0,
        "chamber_pressure_pa": 2.0e-4,
        "specimen_temperature_c": 20.0,
        "mission_particle_flux_cm2_s": 1.0e8,
        "exposure": {
            "particle_fluence_cm2": {"planned": 1.0e15, "achieved": 1.02e15},
            "uv_dose_esh": {"planned": 1000.0, "achieved": 990.0},
            "exposure_duration_h": {"planned": 500.0, "achieved": 505.0},
        },
        "results": {"pristine_value": 0.200, "exposed_value": 0.264},
        "uncertainty_components": {
            "reflectometer": 0.004,
            "dosimetry": 0.003,
            "specimen-scatter": 0.002,
        },
        "coverage_factor": 2.0,
        "deviation_notes": [],
    }
    record.update(kw)
    return record


class TestCompleteness(unittest.TestCase):
    def test_a_full_report_is_missing_nothing(self):
        self.assertEqual(missing_identification(report()), [])
        self.assertEqual(missing_environment(report()), [])
        self.assertEqual(missing_exposure(report()), [])
        self.assertEqual(missing_results(report()), [])

    def test_every_identification_field_is_checked(self):
        self.assertEqual(
            sorted(missing_identification({})), sorted(IDENTIFICATION_FIELDS)
        )

    def test_every_environment_field_is_checked(self):
        self.assertEqual(
            missing_environment({}),
            sorted(ENVIRONMENT_TEXT_FIELDS + ENVIRONMENT_NUMERIC_FIELDS),
        )

    def test_a_blank_traceability_statement_is_missing(self):
        self.assertIn(
            "dosimetry_traceability",
            missing_identification(report(dosimetry_traceability="   ")),
        )

    def test_every_exposure_quantity_is_checked(self):
        self.assertEqual(missing_exposure({}), sorted(EXPOSURE_QUANTITIES))

    def test_an_exposure_reported_only_as_achieved_is_incomplete(self):
        record = report()
        del record["exposure"]["uv_dose_esh"]["planned"]
        self.assertIn("uv_dose_esh.planned", missing_exposure(record))

    def test_every_result_field_is_checked(self):
        self.assertEqual(sorted(missing_results({})), sorted(RESULT_FIELDS))

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            missing_environment("RAD-2026-0084")


class TestExposureTolerance(unittest.TestCase):
    def test_an_overshoot_is_a_positive_deviation(self):
        self.assertAlmostEqual(exposure_deviation(1000.0, 1050.0), 0.05, places=9)

    def test_an_undershoot_is_a_negative_deviation(self):
        self.assertAlmostEqual(exposure_deviation(1000.0, 900.0), -0.10, places=9)

    def test_a_small_deviation_is_inside_the_tolerance(self):
        self.assertTrue(exposure_within_tolerance(1000.0, 1020.0))

    def test_a_deviation_exactly_on_the_tolerance_is_inside_it(self):
        self.assertTrue(
            exposure_within_tolerance(1000.0, 1000.0 * (1.0 + EXPOSURE_TOLERANCE))
        )

    def test_a_large_undershoot_is_outside_the_tolerance(self):
        self.assertFalse(exposure_within_tolerance(1000.0, 700.0))

    def test_a_zero_planned_exposure_raises(self):
        with self.assertRaises(ValueError):
            exposure_deviation(0.0, 900.0)


class TestAcceleration(unittest.TestCase):
    def test_the_factor_is_the_flux_ratio(self):
        self.assertAlmostEqual(acceleration_factor(1.0e9, 1.0e8), 10.0, places=6)

    def test_a_zero_mission_flux_raises(self):
        with self.assertRaises(ValueError):
            acceleration_factor(1.0e9, 0.0)

    def test_a_negative_test_flux_raises(self):
        with self.assertRaises(ValueError):
            acceleration_factor(-1.0, 1.0e8)


class TestUncertainty(unittest.TestCase):
    def test_components_combine_in_quadrature(self):
        self.assertAlmostEqual(
            combined_standard_uncertainty({"a": 3.0, "b": 4.0}), 5.0, places=9
        )

    def test_an_empty_budget_raises(self):
        with self.assertRaises(ValueError):
            combined_standard_uncertainty({})

    def test_a_negative_component_raises(self):
        with self.assertRaises(ValueError):
            combined_standard_uncertainty({"a": -1.0})

    def test_the_expanded_figure_is_the_combined_one_times_the_factor(self):
        self.assertAlmostEqual(expanded_uncertainty(0.005, 2.0), 0.010, places=9)

    def test_a_coverage_factor_outside_the_reportable_range_raises(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty(0.005, 4.0)

    def test_a_value_is_rounded_to_the_reporting_resolution(self):
        self.assertAlmostEqual(
            round_to_report(0.2648), round(0.2648, REPORT_DECIMALS), places=9
        )

    def test_an_uncertainty_swamping_the_change_is_a_finding(self):
        self.assertIn(
            "expanded-uncertainty-exceeds-the-reported-change",
            resolution_findings(0.002, 0.010),
        )

    def test_an_uncertainty_far_under_the_reporting_step_is_a_finding(self):
        self.assertIn(
            "expanded-uncertainty-finer-than-the-reporting-step",
            resolution_findings(0.064, 0.00001),
        )


class TestAssessment(unittest.TestCase):
    def test_a_sound_report_is_reportable(self):
        assessment = assess_test_report(report())
        self.assertEqual(assessment["findings"], [])
        self.assertTrue(assessment["reportable"])
        self.assertAlmostEqual(
            assessment["particle_acceleration_factor"], 10.0, places=6
        )

    def test_a_missing_traceability_statement_blocks_the_report(self):
        record = report()
        del record["dosimetry_traceability"]
        assessment = assess_test_report(record)
        self.assertIn(
            "identification-or-traceability-incomplete", assessment["findings"]
        )
        self.assertFalse(assessment["reportable"])

    def test_an_out_of_tolerance_exposure_is_a_finding(self):
        record = report()
        record["exposure"]["uv_dose_esh"]["achieved"] = 600.0
        assessment = assess_test_report(record)
        self.assertIn(
            "achieved-exposure-outside-its-reporting-tolerance", assessment["findings"]
        )
        self.assertIn("uv_dose_esh", assessment["out_of_tolerance_exposures"])

    def test_an_out_of_tolerance_exposure_with_a_note_still_needs_the_note(self):
        record = report(
            deviation_notes=[
                {"quantity": "uv_dose_esh", "justification": "lamp changed mid-run"}
            ]
        )
        record["exposure"]["uv_dose_esh"]["achieved"] = 600.0
        assessment = assess_test_report(record)
        self.assertEqual(assessment["unexplained_exposures"], [])
        self.assertNotIn(
            "out-of-tolerance-exposure-without-a-recorded-note", assessment["findings"]
        )

    def test_an_unexplained_out_of_tolerance_exposure_is_its_own_finding(self):
        record = report()
        record["exposure"]["particle_fluence_cm2"]["achieved"] = 4.0e14
        assessment = assess_test_report(record)
        self.assertIn(
            "out-of-tolerance-exposure-without-a-recorded-note", assessment["findings"]
        )

    def test_an_over_accelerated_particle_run_is_a_finding(self):
        assessment = assess_test_report(
            report(mission_particle_flux_cm2_s=1.0e9 / (MAX_PARTICLE_ACCELERATION * 10.0))
        )
        self.assertIn(
            "particle-dose-rate-acceleration-beyond-the-limit", assessment["findings"]
        )

    def test_an_acceleration_exactly_on_the_limit_is_accepted(self):
        assessment = assess_test_report(
            report(mission_particle_flux_cm2_s=1.0e9 / MAX_PARTICLE_ACCELERATION)
        )
        self.assertNotIn(
            "particle-dose-rate-acceleration-beyond-the-limit", assessment["findings"]
        )

    def test_a_run_with_no_mission_flux_cannot_state_its_acceleration(self):
        record = report()
        del record["mission_particle_flux_cm2_s"]
        assessment = assess_test_report(record)
        self.assertIn(
            "particle-dose-rate-acceleration-not-reported", assessment["findings"]
        )

    def test_an_over_bright_uv_run_is_a_finding(self):
        assessment = assess_test_report(
            report(uv_irradiance_suns=MAX_UV_ACCELERATION_SUNS + 5.0)
        )
        self.assertIn(
            "uv-irradiance-beyond-the-acceleration-limit", assessment["findings"]
        )

    def test_a_soft_vacuum_run_is_a_finding(self):
        assessment = assess_test_report(
            report(chamber_pressure_pa=MAX_CHAMBER_PRESSURE_PA * 100.0)
        )
        self.assertIn(
            "chamber-pressure-above-the-representative-ceiling", assessment["findings"]
        )

    def test_a_missing_uncertainty_budget_is_a_finding(self):
        record = report()
        del record["uncertainty_components"]
        assessment = assess_test_report(record)
        self.assertIn("uncertainty-budget-absent", assessment["findings"])
        self.assertIsNone(assessment["combined_standard_uncertainty"])

    def test_the_reported_values_are_written_at_the_report_resolution(self):
        assessment = assess_test_report(report())
        self.assertAlmostEqual(
            assessment["reported_values"]["exposed_value"], 0.264, places=9
        )

    def test_a_malformed_deviation_note_raises(self):
        with self.assertRaises(ValueError):
            assess_test_report(report(deviation_notes=[{"quantity": "uv_dose_esh"}]))

    def test_a_non_sequence_deviation_note_list_raises(self):
        with self.assertRaises(ValueError):
            assess_test_report(report(deviation_notes="none"))

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            assess_test_report(["RAD-2026-0084"])


if __name__ == "__main__":
    unittest.main()
