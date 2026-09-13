#!/usr/bin/env python3
"""Contract test for the multicarrier multipactor margin-overview leaf."""

import math
import unittest

import e2001_multicarrier_margin_overview_logic as m

EQUAL_FOUR = [25.0, 25.0, 25.0, 25.0]
UNEQUAL_THREE = [40.0, 10.0, 10.0]


class TestRouteNormalization(unittest.TestCase):
    def test_analysis_aliases(self):
        for raw in ("analysis", "Analytical", " simulation ", "by-analysis"):
            self.assertEqual(m.normalize_route(raw), "analysis")

    def test_test_aliases(self):
        for raw in ("test", "BY-TEST", "measurement", "measured"):
            self.assertEqual(m.normalize_route(raw), "test")

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_route("inspection")

    def test_empty_route_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_route("  ")

    def test_non_string_route_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_route(3)


class TestBasisAndHeritage(unittest.TestCase):
    def test_measured_basis_aliases(self):
        for raw in ("measured", "measurement", "tested"):
            self.assertEqual(m.normalize_threshold_basis(raw), "measured")

    def test_simulated_basis_aliases(self):
        for raw in ("simulated", "computed", "analysed", "analyzed"):
            self.assertEqual(m.normalize_threshold_basis(raw), "simulated")

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_threshold_basis("assumed")

    def test_heritage_aliases(self):
        self.assertEqual(m.normalize_heritage("qualified-design"), "recurrent")
        self.assertEqual(m.normalize_heritage("DERIVATIVE"), "modified")
        self.assertEqual(m.normalize_heritage("no-heritage"), "first-of-kind")

    def test_unknown_heritage_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_heritage("legacy-ish")

    def test_non_string_heritage_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_heritage(None)


class TestCarrierPlan(unittest.TestCase):
    def test_validate_returns_floats(self):
        self.assertEqual(m.validate_carrier_powers([1, 2]), (1.0, 2.0))

    def test_single_carrier_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carrier_powers([50.0])

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carrier_powers([])

    def test_non_list_plan_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carrier_powers(50.0)

    def test_zero_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carrier_powers([25.0, 0.0])

    def test_negative_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carrier_powers([25.0, -5.0])

    def test_non_finite_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carrier_powers([25.0, float("inf")])

    def test_non_numeric_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carrier_powers([25.0, "25"])

    def test_boolean_carrier_power_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_carrier_powers([25.0, True])


class TestPowerAggregates(unittest.TestCase):
    def test_average_power_is_the_sum(self):
        self.assertAlmostEqual(m.average_power_w(EQUAL_FOUR), 100.0)

    def test_peak_envelope_of_equal_carriers(self):
        self.assertAlmostEqual(m.peak_envelope_power_w(EQUAL_FOUR), 400.0)

    def test_peak_envelope_scales_with_carrier_count(self):
        two = m.peak_envelope_power_w([25.0, 25.0])
        four = m.peak_envelope_power_w(EQUAL_FOUR)
        self.assertAlmostEqual(four / two, 4.0)

    def test_peak_envelope_of_unequal_carriers(self):
        expected = (math.sqrt(40.0) + 2 * math.sqrt(10.0)) ** 2
        self.assertAlmostEqual(m.peak_envelope_power_w(UNEQUAL_THREE), expected)

    def test_peak_never_below_average(self):
        self.assertGreater(
            m.peak_envelope_power_w(UNEQUAL_THREE), m.average_power_w(UNEQUAL_THREE)
        )

    def test_crest_factor_of_n_equal_carriers(self):
        self.assertAlmostEqual(m.crest_factor_db(EQUAL_FOUR), 10.0 * math.log10(4.0))

    def test_crest_factor_of_two_equal_carriers(self):
        self.assertAlmostEqual(m.crest_factor_db([7.0, 7.0]), 10.0 * math.log10(2.0))

    def test_crest_factor_unequal_below_equal_case(self):
        self.assertLess(m.crest_factor_db(UNEQUAL_THREE), 10.0 * math.log10(3.0))

    def test_crest_factor_rejects_single_carrier(self):
        with self.assertRaises(ValueError):
            m.crest_factor_db([25.0])


class TestRequiredMargin(unittest.TestCase):
    def test_analysis_route_base(self):
        self.assertAlmostEqual(m.required_multicarrier_margin_db("analysis"), 6.0)

    def test_test_route_base(self):
        self.assertAlmostEqual(m.required_multicarrier_margin_db("test"), 3.0)

    def test_analysis_costs_more_than_test(self):
        self.assertGreater(
            m.required_multicarrier_margin_db("analysis"),
            m.required_multicarrier_margin_db("test"),
        )

    def test_modified_heritage_uplift(self):
        self.assertAlmostEqual(
            m.required_multicarrier_margin_db("test", heritage="modified"), 4.0
        )

    def test_first_of_kind_heritage_uplift(self):
        self.assertAlmostEqual(
            m.required_multicarrier_margin_db("test", heritage="first-of-kind"), 5.0
        )

    def test_simulated_threshold_uplift_on_analysis_route(self):
        plain = m.required_multicarrier_margin_db("analysis", threshold_basis="measured")
        lifted = m.required_multicarrier_margin_db("analysis", threshold_basis="simulated")
        self.assertAlmostEqual(lifted - plain, m.SIMULATED_THRESHOLD_UPLIFT_DB)

    def test_uplifts_accumulate(self):
        self.assertAlmostEqual(
            m.required_multicarrier_margin_db(
                "analysis", heritage="first-of-kind", threshold_basis="simulated"
            ),
            6.0 + 2.0 + 1.0,
        )

    def test_test_route_with_simulated_basis_is_inconsistent(self):
        with self.assertRaises(ValueError):
            m.required_multicarrier_margin_db("test", threshold_basis="simulated")

    def test_policy_override_honoured(self):
        self.assertAlmostEqual(
            m.required_multicarrier_margin_db("analysis", policy={"analysis": 8.0}), 8.0
        )

    def test_policy_missing_route_rejected(self):
        with self.assertRaises(ValueError):
            m.required_multicarrier_margin_db("test", policy={"analysis": 8.0})

    def test_policy_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            m.required_multicarrier_margin_db("analysis", policy=[6.0])

    def test_policy_negative_base_rejected(self):
        with self.assertRaises(ValueError):
            m.required_multicarrier_margin_db("analysis", policy={"analysis": -1.0})

    def test_policy_non_numeric_base_rejected(self):
        with self.assertRaises(ValueError):
            m.required_multicarrier_margin_db("analysis", policy={"analysis": "6dB"})

    def test_heritage_uplift_table_is_monotonic(self):
        self.assertLess(
            m.HERITAGE_UPLIFT_DB["recurrent"], m.HERITAGE_UPLIFT_DB["modified"]
        )
        self.assertLess(
            m.HERITAGE_UPLIFT_DB["modified"], m.HERITAGE_UPLIFT_DB["first-of-kind"]
        )


class TestReferencePower(unittest.TestCase):
    def test_analysis_reference_is_peak_envelope(self):
        self.assertAlmostEqual(
            m.reference_power_w("analysis", carrier_powers=EQUAL_FOUR), 400.0
        )

    def test_analysis_reference_needs_the_carrier_plan(self):
        with self.assertRaises(ValueError):
            m.reference_power_w("analysis")

    def test_test_reference_is_the_applied_level(self):
        self.assertAlmostEqual(
            m.reference_power_w("test", applied_test_power_w=320.0), 320.0
        )

    def test_test_reference_needs_the_applied_level(self):
        with self.assertRaises(ValueError):
            m.reference_power_w("test", carrier_powers=EQUAL_FOUR)

    def test_test_reference_rejects_non_positive_level(self):
        with self.assertRaises(ValueError):
            m.reference_power_w("test", applied_test_power_w=0.0)


class TestDemonstrationPower(unittest.TestCase):
    def test_three_db_doubles_the_reference(self):
        self.assertAlmostEqual(
            m.demonstration_power_w(100.0, 10.0 * math.log10(2.0)), 200.0
        )

    def test_zero_margin_is_identity(self):
        self.assertAlmostEqual(m.demonstration_power_w(100.0, 0.0), 100.0)

    def test_six_db_over_peak_envelope(self):
        self.assertAlmostEqual(m.demonstration_power_w(400.0, 6.0), 400.0 * 10 ** 0.6)

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            m.demonstration_power_w(100.0, -0.1)

    def test_non_finite_margin_rejected(self):
        with self.assertRaises(ValueError):
            m.demonstration_power_w(100.0, float("nan"))

    def test_non_numeric_margin_rejected(self):
        with self.assertRaises(ValueError):
            m.demonstration_power_w(100.0, "6")

    def test_non_positive_reference_rejected(self):
        with self.assertRaises(ValueError):
            m.demonstration_power_w(0.0, 6.0)

    def test_round_trip_recovers_the_margin(self):
        demanded = m.demonstration_power_w(400.0, 6.0)
        self.assertAlmostEqual(m.achieved_margin_db(demanded, 400.0), 6.0)

    def test_achieved_margin_rejects_bad_threshold(self):
        with self.assertRaises(ValueError):
            m.achieved_margin_db(-1.0, 400.0)


class TestMarginComparison(unittest.TestCase):
    def test_exact_boundary_counts_as_met(self):
        reference = 437.0
        demanded = m.demonstration_power_w(reference, 6.0)
        self.assertTrue(m.margin_is_met(m.achieved_margin_db(demanded, reference), 6.0))

    def test_clear_pass(self):
        self.assertTrue(m.margin_is_met(8.0, 6.0))

    def test_clear_fail(self):
        self.assertFalse(m.margin_is_met(5.9, 6.0))

    def test_tolerance_does_not_forgive_a_real_shortfall(self):
        self.assertFalse(m.margin_is_met(6.0 - 1e-4, 6.0))

    def test_comparison_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            m.margin_is_met(6.0, None)


class TestEvaluateCase(unittest.TestCase):
    def analysis_case(self, **over):
        case = {
            "id": "output-multiplexer",
            "route": "analysis",
            "carrier_powers": EQUAL_FOUR,
            "multipactor_threshold_w": 2000.0,
        }
        case.update(over)
        return case

    def test_analysis_case_is_compliant(self):
        result = m.evaluate_margin_case(self.analysis_case())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["required_margin_db"], 6.0)
        self.assertAlmostEqual(result["reference_power_w"], 400.0)

    def test_analysis_case_demonstration_power(self):
        result = m.evaluate_margin_case(self.analysis_case())
        self.assertAlmostEqual(result["demonstration_power_w"], 400.0 * 10 ** 0.6)

    def test_analysis_case_deficient(self):
        result = m.evaluate_margin_case(
            self.analysis_case(multipactor_threshold_w=900.0)
        )
        self.assertFalse(result["compliant"])
        self.assertGreater(result["deficit_db"], 0.0)
        self.assertEqual(len(result["findings"]), 1)

    def test_missing_threshold_is_a_finding(self):
        case = self.analysis_case()
        del case["multipactor_threshold_w"]
        result = m.evaluate_margin_case(case)
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["achieved_margin_db"])

    def test_exact_boundary_case_is_compliant(self):
        case = self.analysis_case(
            multipactor_threshold_w=m.demonstration_power_w(400.0, 6.0)
        )
        self.assertTrue(m.evaluate_margin_case(case)["compliant"])

    def test_test_route_case_uses_applied_level(self):
        case = {
            "id": "waveguide-run",
            "route": "test",
            "applied_test_power_w": 800.0,
            "multipactor_threshold_w": 1700.0,
        }
        result = m.evaluate_margin_case(case)
        self.assertAlmostEqual(result["reference_power_w"], 800.0)
        self.assertAlmostEqual(result["required_margin_db"], 3.0)
        self.assertTrue(result["compliant"])

    def test_case_missing_route_rejected(self):
        case = self.analysis_case()
        del case["route"]
        with self.assertRaises(ValueError):
            m.evaluate_margin_case(case)

    def test_case_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            m.evaluate_margin_case(self.analysis_case(id="   "))

    def test_case_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            m.evaluate_margin_case(["output-multiplexer"])

    def test_case_identifier_is_stripped(self):
        result = m.evaluate_margin_case(self.analysis_case(id="  input-filter "))
        self.assertEqual(result["id"], "input-filter")

    def test_case_heritage_raises_the_demand(self):
        base = m.evaluate_margin_case(self.analysis_case())
        harsh = m.evaluate_margin_case(self.analysis_case(heritage="first-of-kind"))
        self.assertGreater(
            harsh["required_margin_db"], base["required_margin_db"]
        )


class TestOverviewAndSummary(unittest.TestCase):
    def test_overview_reports_both_routes(self):
        overview = m.route_overview(EQUAL_FOUR)
        self.assertEqual(overview["carriers"], 4)
        self.assertIn("analysis", overview)
        self.assertIn("test", overview)

    def test_overview_analysis_demand_exceeds_test_demand(self):
        overview = m.route_overview(EQUAL_FOUR)
        self.assertGreater(
            overview["analysis"]["demonstration_power_w"],
            overview["test"]["demonstration_power_w"],
        )

    def test_overview_crest_factor(self):
        overview = m.route_overview(EQUAL_FOUR)
        self.assertAlmostEqual(overview["crest_factor_db"], 10.0 * math.log10(4.0))

    def test_overview_rejects_single_carrier(self):
        with self.assertRaises(ValueError):
            m.route_overview([100.0])

    def test_summary_counts_open_cases(self):
        cases = [
            {
                "id": "omux",
                "route": "analysis",
                "carrier_powers": EQUAL_FOUR,
                "multipactor_threshold_w": 2000.0,
            },
            {
                "id": "imux",
                "route": "analysis",
                "carrier_powers": EQUAL_FOUR,
                "multipactor_threshold_w": 800.0,
            },
        ]
        summary = m.summarize_cases(cases)
        self.assertEqual(summary["cases"], 2)
        self.assertEqual(summary["open_ids"], ["imux"])
        self.assertFalse(summary["all_routes_compliant"])
        self.assertGreater(summary["worst_deficit_db"], 0.0)

    def test_summary_all_compliant(self):
        cases = [
            {
                "id": "omux",
                "route": "analysis",
                "carrier_powers": EQUAL_FOUR,
                "multipactor_threshold_w": 2000.0,
            }
        ]
        summary = m.summarize_cases(cases)
        self.assertTrue(summary["all_routes_compliant"])
        self.assertAlmostEqual(summary["worst_deficit_db"], 0.0)

    def test_summary_rejects_duplicate_ids(self):
        case = {
            "id": "omux",
            "route": "analysis",
            "carrier_powers": EQUAL_FOUR,
            "multipactor_threshold_w": 2000.0,
        }
        with self.assertRaises(ValueError):
            m.summarize_cases([case, dict(case)])

    def test_summary_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            m.summarize_cases([])

    def test_summary_rejects_non_list(self):
        with self.assertRaises(ValueError):
            m.summarize_cases("omux")

    def test_tolerance_is_representation_scale(self):
        self.assertLess(m.MARGIN_TOLERANCE_DB, 1e-6)
        self.assertGreater(m.MARGIN_TOLERANCE_DB, 0.0)


if __name__ == "__main__":
    unittest.main()
