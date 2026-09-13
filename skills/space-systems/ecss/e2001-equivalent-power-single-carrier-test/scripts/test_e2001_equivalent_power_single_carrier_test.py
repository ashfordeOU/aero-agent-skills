#!/usr/bin/env python3
"""Gate 3 contract tests for the clause 6.4.3.2 single-carrier logic."""

import math
import unittest

import e2001_equivalent_power_single_carrier_test_logic as logic


def carrier(cid, power_w, frequency_hz):
    return {"id": cid, "power_w": power_w, "frequency_hz": frequency_hz}


FOUR_EQUAL = [
    carrier("c1", 25.0, 11.70e9),
    carrier("c2", 25.0, 11.75e9),
    carrier("c3", 25.0, 11.80e9),
    carrier("c4", 25.0, 11.85e9),
]

TWO_EQUAL_50W = [
    carrier("a", 50.0, 4.00e9),
    carrier("b", 50.0, 4.04e9),
]

UNEQUAL_THREE = [
    carrier("hi", 64.0, 12.10e9),
    carrier("lo", 16.0, 12.00e9),
    carrier("mid", 36.0, 12.05e9),
]


class TestCarrierSetValidation(unittest.TestCase):
    def test_valid_set_is_sorted_by_frequency(self):
        result = logic.validate_carrier_set(UNEQUAL_THREE)
        self.assertEqual([item["id"] for item in result], ["lo", "mid", "hi"])

    def test_validation_returns_a_copy(self):
        source = [carrier("only", 10.0, 1.0e9)]
        result = logic.validate_carrier_set(source)
        result[0]["power_w"] = 999.0
        self.assertAlmostEqual(source[0]["power_w"], 10.0)

    def test_ids_are_stripped(self):
        result = logic.validate_carrier_set([carrier("  pad  ", 5.0, 2.0e9)])
        self.assertEqual(result[0]["id"], "pad")

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set({"id": "x", "power_w": 1.0, "frequency_hz": 1.0})

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([("c1", 10.0, 1.0e9)])

    def test_missing_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([{"power_w": 10.0, "frequency_hz": 1.0e9}])

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("   ", 10.0, 1.0e9)])

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", 10.0, 1.0e9), carrier("c", 20.0, 2.0e9)])

    def test_zero_power_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", 0.0, 1.0e9)])

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", -5.0, 1.0e9)])

    def test_non_finite_power_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", float("inf"), 1.0e9)])

    def test_boolean_power_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", True, 1.0e9)])

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", 10.0, 0.0)])

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", 10.0, -1.0e9)])

    def test_nan_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_set([carrier("c", 10.0, float("nan"))])


class TestEquivalentPower(unittest.TestCase):
    def test_voltage_sum_of_four_equal_carriers(self):
        self.assertAlmostEqual(logic.envelope_voltage_sum(FOUR_EQUAL), 20.0)

    def test_equivalent_power_is_n_squared_for_equal_carriers(self):
        self.assertAlmostEqual(
            logic.equivalent_single_carrier_power_w(FOUR_EQUAL), 400.0
        )

    def test_single_carrier_equivalent_equals_itself(self):
        self.assertAlmostEqual(
            logic.equivalent_single_carrier_power_w([carrier("solo", 73.5, 8.0e9)]), 73.5
        )

    def test_equivalent_power_unequal_carriers(self):
        # sqrt(16)+sqrt(36)+sqrt(64) = 4+6+8 = 18 -> 324 W
        self.assertAlmostEqual(
            logic.equivalent_single_carrier_power_w(UNEQUAL_THREE), 324.0
        )

    def test_total_average_power(self):
        self.assertAlmostEqual(logic.total_average_power_w(UNEQUAL_THREE), 116.0)

    def test_equivalent_power_exceeds_average_power(self):
        self.assertGreater(
            logic.equivalent_single_carrier_power_w(FOUR_EQUAL),
            logic.total_average_power_w(FOUR_EQUAL),
        )

    def test_thermal_over_test_ratio_equals_carrier_count(self):
        self.assertAlmostEqual(logic.thermal_over_test_ratio(FOUR_EQUAL), 4.0)

    def test_thermal_over_test_ratio_unequal_carriers(self):
        self.assertAlmostEqual(
            logic.thermal_over_test_ratio(UNEQUAL_THREE), 324.0 / 116.0
        )

    def test_equivalent_power_propagates_validation_error(self):
        with self.assertRaises(ValueError):
            logic.equivalent_single_carrier_power_w([])


class TestPowerRatio(unittest.TestCase):
    def test_ten_times_is_ten_db(self):
        self.assertAlmostEqual(logic.power_ratio_db(1000.0, 100.0), 10.0)

    def test_equal_powers_are_zero_db(self):
        self.assertAlmostEqual(logic.power_ratio_db(42.0, 42.0), 0.0)

    def test_zero_numerator_rejected(self):
        with self.assertRaises(ValueError):
            logic.power_ratio_db(0.0, 10.0)

    def test_negative_denominator_rejected(self):
        with self.assertRaises(ValueError):
            logic.power_ratio_db(10.0, -1.0)


class TestCarrierSpacing(unittest.TestCase):
    def test_uniform_spacing(self):
        self.assertAlmostEqual(logic.carrier_spacing_hz(FOUR_EQUAL), 50.0e6, places=1)

    def test_envelope_repetition_period(self):
        self.assertAlmostEqual(
            logic.envelope_repetition_period_s(FOUR_EQUAL), 1.0 / 50.0e6
        )

    def test_single_carrier_has_no_spacing(self):
        with self.assertRaises(ValueError):
            logic.carrier_spacing_hz([carrier("solo", 10.0, 1.0e9)])

    def test_repeated_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.carrier_spacing_hz(
                [carrier("a", 10.0, 1.0e9), carrier("b", 10.0, 1.0e9)]
            )

    def test_non_uniform_spacing_rejected(self):
        with self.assertRaises(ValueError):
            logic.carrier_spacing_hz(
                [
                    carrier("a", 10.0, 1.00e9),
                    carrier("b", 10.0, 1.01e9),
                    carrier("c", 10.0, 1.05e9),
                ]
            )

    def test_bad_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            logic.carrier_spacing_hz(FOUR_EQUAL, rel_tol=0.0)


class TestTransitAndCrossings(unittest.TestCase):
    def test_first_order_transit_is_half_a_period(self):
        self.assertAlmostEqual(logic.electron_transit_time_s(1.0e9), 0.5e-9)

    def test_third_order_transit(self):
        self.assertAlmostEqual(
            logic.electron_transit_time_s(1.0e9, resonant_order=3), 1.5e-9
        )

    def test_even_order_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(1.0e9, resonant_order=2)

    def test_zero_order_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(1.0e9, resonant_order=0)

    def test_float_order_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(1.0e9, resonant_order=3.0)

    def test_excessive_order_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(1.0e9, resonant_order=99)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.electron_transit_time_s(0.0)

    def test_crossings_in_finite_dwell(self):
        crossings = logic.gap_crossings_in_dwell(10.0e-9, 1.0e9)
        self.assertAlmostEqual(crossings, 20.0)

    def test_continuous_wave_dwell_is_unbounded(self):
        self.assertEqual(logic.gap_crossings_in_dwell(math.inf, 12.0e9), math.inf)

    def test_negative_dwell_rejected(self):
        with self.assertRaises(ValueError):
            logic.gap_crossings_in_dwell(-1.0e-9, 1.0e9)


class TestMargin(unittest.TestCase):
    def test_three_db_margin_doubles_power(self):
        self.assertAlmostEqual(logic.apply_test_margin(100.0, 3.0103), 200.0, places=3)

    def test_zero_margin_is_identity(self):
        self.assertAlmostEqual(logic.apply_test_margin(137.0, 0.0), 137.0)

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            logic.apply_test_margin(100.0, -1.0)

    def test_zero_power_rejected(self):
        with self.assertRaises(ValueError):
            logic.apply_test_margin(0.0, 3.0)


class TestDriveCapability(unittest.TestCase):
    def test_deliverable_drive_has_no_findings(self):
        self.assertEqual(logic.assess_drive_capability(400.0, 500.0, 600.0), [])

    def test_source_shortfall_reported(self):
        findings = logic.assess_drive_capability(400.0, 300.0, 600.0)
        self.assertEqual(
            [item["code"] for item in findings],
            ["equivalent-drive-exceeds-source-capability"],
        )

    def test_component_rating_breach_reported(self):
        findings = logic.assess_drive_capability(400.0, 500.0, 350.0)
        self.assertEqual(
            [item["code"] for item in findings],
            ["equivalent-drive-exceeds-component-rating"],
        )

    def test_both_limits_breached(self):
        findings = logic.assess_drive_capability(900.0, 500.0, 350.0)
        self.assertEqual(len(findings), 2)

    def test_exact_boundary_from_square_root_sum_is_compliant(self):
        # sqrt(50)+sqrt(50) squared is 200.00000000000003 in binary floating
        # point; an exactly 200 W source is physically adequate.
        required = logic.equivalent_single_carrier_power_w(TWO_EQUAL_50W)
        self.assertGreater(required, 200.0)
        self.assertEqual(logic.assess_drive_capability(required, 200.0, 200.0), [])

    def test_genuine_exceedance_is_not_absorbed(self):
        findings = logic.assess_drive_capability(200.5, 200.0, 1000.0)
        self.assertEqual(len(findings), 1)

    def test_non_positive_required_drive_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_drive_capability(0.0, 500.0, 600.0)

    def test_non_positive_source_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_drive_capability(400.0, 0.0, 600.0)

    def test_non_positive_component_rating_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_drive_capability(400.0, 500.0, -1.0)


class TestFullAssessment(unittest.TestCase):
    def setUp(self):
        self.report = logic.assess_single_carrier_equivalent_power_test(
            FOUR_EQUAL,
            source_max_power_w=1000.0,
            component_peak_power_rating_w=1200.0,
            margin_db=3.0103,
        )

    def test_report_is_compliant(self):
        self.assertTrue(self.report["compliant"])

    def test_verdict_token(self):
        self.assertEqual(
            self.report["verdict"], "single-carrier-equivalent-drive-acceptable"
        )

    def test_equivalent_power_in_report(self):
        self.assertAlmostEqual(self.report["equivalent_power_w"], 400.0)

    def test_required_drive_includes_margin(self):
        self.assertAlmostEqual(self.report["required_drive_power_w"], 800.0, places=2)

    def test_over_test_factor_in_report(self):
        self.assertAlmostEqual(self.report["thermal_over_test_ratio"], 4.0)

    def test_continuous_wave_drive_is_not_dwell_limited(self):
        self.assertFalse(self.report["dwell_limited"])
        self.assertEqual(self.report["gap_crossings"], math.inf)

    def test_drive_over_average_db(self):
        self.assertAlmostEqual(
            self.report["drive_over_average_db"],
            10.0 * math.log10(800.0 / 100.0),
            places=3,
        )

    def test_carrier_ids_are_ordered(self):
        self.assertEqual(self.report["carrier_ids"], ["c1", "c2", "c3", "c4"])

    def test_source_shortfall_makes_it_not_acceptable(self):
        report = logic.assess_single_carrier_equivalent_power_test(
            FOUR_EQUAL,
            source_max_power_w=250.0,
            component_peak_power_rating_w=1200.0,
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(
            report["verdict"], "single-carrier-equivalent-drive-not-acceptable"
        )

    def test_over_test_allowance_makes_it_conditional(self):
        report = logic.assess_single_carrier_equivalent_power_test(
            FOUR_EQUAL,
            source_max_power_w=1000.0,
            component_peak_power_rating_w=1200.0,
            max_thermal_over_test_ratio=3.0,
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(
            report["verdict"], "single-carrier-equivalent-drive-conditional"
        )

    def test_over_test_allowance_exactly_met_is_compliant(self):
        report = logic.assess_single_carrier_equivalent_power_test(
            FOUR_EQUAL,
            source_max_power_w=1000.0,
            component_peak_power_rating_w=1200.0,
            max_thermal_over_test_ratio=4.0,
        )
        self.assertTrue(report["compliant"])

    def test_over_test_allowance_below_one_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_single_carrier_equivalent_power_test(
                FOUR_EQUAL,
                source_max_power_w=1000.0,
                component_peak_power_rating_w=1200.0,
                max_thermal_over_test_ratio=0.5,
            )

    def test_empty_carrier_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_single_carrier_equivalent_power_test([], 1000.0, 1200.0)

    def test_transit_time_uses_highest_carrier_frequency(self):
        self.assertAlmostEqual(
            self.report["electron_transit_time_s"], 1.0 / (2.0 * 11.85e9)
        )


class TestCategorizationAndSummary(unittest.TestCase):
    def test_categorize_rejects_non_report(self):
        with self.assertRaises(ValueError):
            logic.categorize_substitution({"nope": 1})

    def test_summary_mentions_verdict(self):
        report = logic.assess_single_carrier_equivalent_power_test(
            UNEQUAL_THREE, 1000.0, 1000.0
        )
        text = logic.summarize_report(report)
        self.assertIn("verdict: single-carrier-equivalent-drive-acceptable", text)

    def test_summary_lists_findings(self):
        report = logic.assess_single_carrier_equivalent_power_test(
            UNEQUAL_THREE, 100.0, 100.0
        )
        text = logic.summarize_report(report)
        self.assertIn("finding: equivalent-drive-exceeds-source-capability", text)

    def test_summary_rejects_non_report(self):
        with self.assertRaises(ValueError):
            logic.summarize_report({"findings": []})


if __name__ == "__main__":
    unittest.main()
