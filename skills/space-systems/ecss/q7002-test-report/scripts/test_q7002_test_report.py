"""Contract test for the outgassing test-report leaf (stdlib unittest)."""

import unittest

from q7002_test_report_logic import (
    CONDITION_FIELDS,
    DEFAULT_COVERAGE_FACTOR,
    IDENTIFICATION_FIELDS,
    MIN_SPECIMEN_COUNT,
    REPORT_DECIMALS,
    RESULT_FIELDS,
    assess_test_report,
    check_uncertainty_resolution,
    combined_standard_uncertainty,
    condition_within_window,
    expanded_uncertainty,
    missing_conditions,
    missing_identification,
    missing_results,
    out_of_window_conditions,
    round_to_report,
)


def report(**kw):
    record = {
        "report_id": "OG-2026-0041",
        "material_designation": "EPX-114 two-part epoxy",
        "manufacturer": "Beispiel Polymere",
        "batch_or_lot": "L-77321",
        "processing_state": "cured 24 h at 60 C, post-baked 2 h at 100 C",
        "preconditioning_temperature_c": 23.0,
        "preconditioning_humidity_pct": 50.0,
        "preconditioning_duration_h": 24.0,
        "specimen_temperature_c": 125.0,
        "collector_temperature_c": 25.0,
        "chamber_pressure_pa": 2.0e-4,
        "test_duration_h": 24.0,
        "total_mass_loss_pct": 0.62,
        "cvcm_pct": 0.04,
        "specimen_count": 3,
        "uncertainty_components_pct": {
            "specimen-weighing": 0.004,
            "collector-weighing": 0.003,
            "temperature-control": 0.002,
        },
        "coverage_factor": 2.0,
    }
    record.update(kw)
    return record


class TestCompleteness(unittest.TestCase):
    def test_a_full_report_is_missing_nothing(self):
        self.assertEqual(missing_identification(report()), [])
        self.assertEqual(missing_conditions(report()), [])
        self.assertEqual(missing_results(report()), [])

    def test_a_blank_manufacturer_is_missing(self):
        self.assertIn("manufacturer", missing_identification(report(manufacturer="  ")))

    def test_a_trade_name_without_a_batch_is_incomplete(self):
        record = report()
        del record["batch_or_lot"]
        self.assertIn("batch_or_lot", missing_identification(record))

    def test_every_identification_field_is_checked(self):
        record = {}
        self.assertEqual(
            sorted(missing_identification(record)), sorted(IDENTIFICATION_FIELDS)
        )

    def test_every_condition_field_is_checked(self):
        self.assertEqual(sorted(missing_conditions({})), sorted(CONDITION_FIELDS))

    def test_every_result_field_is_checked(self):
        self.assertEqual(sorted(missing_results({})), sorted(RESULT_FIELDS))

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            missing_identification("OG-2026-0041")


class TestConditionWindows(unittest.TestCase):
    def test_a_nominal_condition_is_inside_its_window(self):
        self.assertTrue(condition_within_window("specimen_temperature_c", 125.0))

    def test_a_condition_exactly_on_the_window_edge_is_inside_it(self):
        self.assertTrue(condition_within_window("specimen_temperature_c", 126.0))
        self.assertTrue(condition_within_window("specimen_temperature_c", 124.0))

    def test_a_condition_past_the_window_is_outside_it(self):
        self.assertFalse(condition_within_window("specimen_temperature_c", 130.0))

    def test_a_duration_floor_is_met_exactly(self):
        self.assertTrue(condition_within_window("test_duration_h", 24.0))

    def test_a_short_run_misses_the_duration_floor(self):
        self.assertFalse(condition_within_window("test_duration_h", 18.0))

    def test_a_pressure_ceiling_is_met_exactly(self):
        self.assertTrue(condition_within_window("chamber_pressure_pa", 1.0e-3))

    def test_a_poor_vacuum_misses_the_pressure_ceiling(self):
        self.assertFalse(condition_within_window("chamber_pressure_pa", 1.0e-1))

    def test_an_unknown_condition_field_raises(self):
        with self.assertRaises(ValueError):
            condition_within_window("operator_mood", 1.0)

    def test_out_of_window_list_names_the_offending_field(self):
        fields = out_of_window_conditions(report(collector_temperature_c=40.0))
        self.assertEqual(fields, ["collector_temperature_c"])


class TestUncertainty(unittest.TestCase):
    def test_components_combine_in_quadrature(self):
        value = combined_standard_uncertainty({"a": 0.03, "b": 0.04})
        self.assertAlmostEqual(value, 0.05, places=9)

    def test_a_single_component_combines_to_itself(self):
        self.assertAlmostEqual(
            combined_standard_uncertainty({"a": 0.012}), 0.012, places=12
        )

    def test_an_empty_budget_raises(self):
        with self.assertRaises(ValueError):
            combined_standard_uncertainty({})

    def test_a_negative_component_raises(self):
        with self.assertRaises(ValueError):
            combined_standard_uncertainty({"a": -0.01})

    def test_a_blank_component_name_raises(self):
        with self.assertRaises(ValueError):
            combined_standard_uncertainty({"  ": 0.01})

    def test_expansion_scales_by_the_coverage_factor(self):
        self.assertAlmostEqual(expanded_uncertainty(0.02, 2.0), 0.04, places=12)

    def test_the_default_coverage_factor_is_applied(self):
        self.assertAlmostEqual(
            expanded_uncertainty(0.02),
            DEFAULT_COVERAGE_FACTOR * 0.02,
            places=12,
        )

    def test_an_unreportable_coverage_factor_raises(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty(0.02, 9.0)

    def test_an_uncertainty_larger_than_the_value_is_a_finding(self):
        findings = check_uncertainty_resolution(0.01, 0.06)
        self.assertIn("expanded-uncertainty-exceeds-the-reported-value", findings)

    def test_an_uncertainty_below_the_reporting_step_is_a_finding(self):
        findings = check_uncertainty_resolution(0.40, 0.0001)
        self.assertIn(
            "expanded-uncertainty-finer-than-the-reporting-step", findings
        )

    def test_a_matched_value_and_uncertainty_give_no_findings(self):
        self.assertEqual(check_uncertainty_resolution(0.40, 0.02), [])


class TestRounding(unittest.TestCase):
    def test_a_value_is_rounded_to_the_report_resolution(self):
        self.assertAlmostEqual(round_to_report(0.6249), 0.62, places=9)

    def test_the_report_resolution_is_two_decimals(self):
        self.assertEqual(REPORT_DECIMALS, 2)

    def test_non_numeric_rounding_input_raises(self):
        with self.assertRaises(ValueError):
            round_to_report("0.62")


class TestAssessTestReport(unittest.TestCase):
    def test_a_complete_report_is_reportable(self):
        assessment = assess_test_report(report())
        self.assertTrue(assessment["reportable"])
        self.assertEqual(assessment["findings"], [])
        self.assertAlmostEqual(
            assessment["reported_values"]["cvcm_pct"], 0.04, places=9
        )

    def test_the_expanded_uncertainty_is_carried_into_the_report(self):
        assessment = assess_test_report(report())
        self.assertAlmostEqual(
            assessment["expanded_uncertainty_pct"],
            2.0 * assessment["combined_standard_uncertainty_pct"],
            places=12,
        )

    def test_a_missing_manufacturer_is_a_finding(self):
        assessment = assess_test_report(report(manufacturer=""))
        self.assertFalse(assessment["reportable"])
        self.assertIn("identification-incomplete", assessment["findings"])

    def test_an_out_of_window_condition_without_a_deviation_is_two_findings(self):
        assessment = assess_test_report(report(specimen_temperature_c=110.0))
        self.assertIn("test-condition-outside-its-window", assessment["findings"])
        self.assertIn(
            "out-of-window-condition-without-a-recorded-deviation",
            assessment["findings"],
        )

    def test_a_declared_deviation_removes_the_undeclared_finding(self):
        assessment = assess_test_report(
            report(
                specimen_temperature_c=110.0,
                deviations=[
                    {
                        "condition": "specimen_temperature_c",
                        "justification": "maximum use temperature of the material",
                    }
                ],
            )
        )
        self.assertEqual(assessment["undeclared_deviations"], [])
        self.assertNotIn(
            "out-of-window-condition-without-a-recorded-deviation",
            assessment["findings"],
        )
        self.assertIn("test-condition-outside-its-window", assessment["findings"])

    def test_a_deviation_against_an_in_window_condition_is_a_finding(self):
        assessment = assess_test_report(
            report(
                deviations=[
                    {
                        "condition": "collector_temperature_c",
                        "justification": "none needed",
                    }
                ]
            )
        )
        self.assertIn(
            "deviation-recorded-for-an-in-window-condition", assessment["findings"]
        )

    def test_a_deviation_without_a_justification_raises(self):
        with self.assertRaises(ValueError):
            assess_test_report(
                report(deviations=[{"condition": "specimen_temperature_c"}])
            )

    def test_a_non_sequence_deviations_field_raises(self):
        with self.assertRaises(ValueError):
            assess_test_report(report(deviations="none"))

    def test_too_few_specimens_is_a_finding(self):
        assessment = assess_test_report(report(specimen_count=MIN_SPECIMEN_COUNT - 1))
        self.assertIn(
            "fewer-specimens-than-the-method-requires", assessment["findings"]
        )

    def test_a_fractional_specimen_count_is_a_finding(self):
        assessment = assess_test_report(report(specimen_count=2.5))
        self.assertIn(
            "specimen-count-is-not-a-whole-number", assessment["findings"]
        )

    def test_a_missing_uncertainty_budget_is_a_finding(self):
        record = report()
        del record["uncertainty_components_pct"]
        assessment = assess_test_report(record)
        self.assertIn("uncertainty-budget-absent", assessment["findings"])
        self.assertIsNone(assessment["combined_standard_uncertainty_pct"])

    def test_an_uncertainty_swamping_the_result_is_a_finding(self):
        assessment = assess_test_report(
            report(cvcm_pct=0.01, uncertainty_components_pct={"weighing": 0.05})
        )
        self.assertIn(
            "expanded-uncertainty-exceeds-the-reported-value", assessment["findings"]
        )

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            assess_test_report(["OG-2026-0041"])


if __name__ == "__main__":
    unittest.main()
