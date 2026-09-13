#!/usr/bin/env python3
"""Contract test for the single-carrier multipactor test-margin leaf."""

import math
import unittest

import e2001_single_carrier_test_margins_logic as m


class TestHardwareCategory(unittest.TestCase):
    def test_equipment_aliases_collapse(self):
        for raw in ("equipment", "Equipment-Level", " unit ", "unit-level"):
            self.assertEqual(m.normalize_hardware_category(raw), "equipment")

    def test_component_aliases_collapse(self):
        for raw in ("component", "COMPONENT-LEVEL", "part", "sub-assembly", "subassembly"):
            self.assertEqual(m.normalize_hardware_category(raw), "component")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_hardware_category("payload")

    def test_empty_category_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_hardware_category("   ")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_hardware_category(7)


class TestHeritage(unittest.TestCase):
    def test_recurrent_aliases(self):
        for raw in ("recurrent", "Recurring", "identical-build", "qualified-design"):
            self.assertEqual(m.normalize_heritage(raw), "recurrent")

    def test_modified_aliases(self):
        for raw in ("modified", "modified-design", "DERIVATIVE"):
            self.assertEqual(m.normalize_heritage(raw), "modified")

    def test_first_of_kind_aliases(self):
        for raw in ("first-of-kind", "new-design", "new", "no-heritage"):
            self.assertEqual(m.normalize_heritage(raw), "first-of-kind")

    def test_unknown_heritage_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_heritage("flight-proven-ish")

    def test_non_string_heritage_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_heritage(None)

    def test_empty_heritage_rejected(self):
        with self.assertRaises(ValueError):
            m.normalize_heritage("")


class TestRequiredMargin(unittest.TestCase):
    def test_equipment_recurrent_multi_article_base(self):
        self.assertAlmostEqual(
            m.required_test_margin_db("equipment", "recurrent", articles_tested=2), 3.0
        )

    def test_equipment_first_of_kind_base(self):
        self.assertAlmostEqual(
            m.required_test_margin_db("equipment", "new-design", articles_tested=3), 6.0
        )

    def test_component_recurrent_base_exceeds_equipment(self):
        comp = m.required_test_margin_db("component", "recurrent", articles_tested=2)
        equip = m.required_test_margin_db("equipment", "recurrent", articles_tested=2)
        self.assertGreater(comp, equip)

    def test_single_article_uplift_applied(self):
        one = m.required_test_margin_db("equipment", "modified", articles_tested=1)
        two = m.required_test_margin_db("equipment", "modified", articles_tested=2)
        self.assertAlmostEqual(one - two, m.SINGLE_ARTICLE_UPLIFT_DB)

    def test_extrapolated_threshold_uplift_applied(self):
        plain = m.required_test_margin_db("component", "modified", articles_tested=2)
        extra = m.required_test_margin_db(
            "component", "modified", articles_tested=2, threshold_extrapolated=True
        )
        self.assertAlmostEqual(extra - plain, m.EXTRAPOLATED_THRESHOLD_UPLIFT_DB)

    def test_both_uplifts_accumulate(self):
        value = m.required_test_margin_db(
            "component", "first-of-kind", articles_tested=1, threshold_extrapolated=True
        )
        self.assertAlmostEqual(value, 6.0 + 1.0 + 1.0)

    def test_zero_articles_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db("equipment", "recurrent", articles_tested=0)

    def test_negative_articles_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db("equipment", "recurrent", articles_tested=-2)

    def test_float_article_count_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db("equipment", "recurrent", articles_tested=2.0)

    def test_bool_article_count_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db("equipment", "recurrent", articles_tested=True)

    def test_non_bool_extrapolation_flag_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db(
                "equipment", "recurrent", articles_tested=2, threshold_extrapolated="yes"
            )

    def test_policy_override_honoured(self):
        policy = {("equipment", "recurrent"): 2.5}
        self.assertAlmostEqual(
            m.required_test_margin_db(
                "equipment", "recurrent", articles_tested=2, policy=policy
            ),
            2.5,
        )

    def test_policy_missing_entry_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db(
                "component", "modified", articles_tested=2, policy={("equipment", "recurrent"): 3.0}
            )

    def test_policy_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db(
                "equipment", "recurrent", articles_tested=2, policy=[3.0]
            )

    def test_policy_negative_entry_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db(
                "equipment", "recurrent", articles_tested=2,
                policy={("equipment", "recurrent"): -1.0},
            )

    def test_policy_non_numeric_entry_rejected(self):
        with self.assertRaises(ValueError):
            m.required_test_margin_db(
                "equipment", "recurrent", articles_tested=2,
                policy={("equipment", "recurrent"): "3 dB"},
            )

    def test_every_category_pair_has_a_base_entry(self):
        for hw in ("equipment", "component"):
            for her in ("recurrent", "modified", "first-of-kind"):
                self.assertIn((hw, her), m.BASE_TEST_MARGIN_DB)

    def test_first_of_kind_never_cheaper_than_recurrent(self):
        for hw in ("equipment", "component"):
            self.assertGreaterEqual(
                m.BASE_TEST_MARGIN_DB[(hw, "first-of-kind")],
                m.BASE_TEST_MARGIN_DB[(hw, "recurrent")],
            )


class TestPowerArithmetic(unittest.TestCase):
    def test_ratio_of_equal_powers_is_zero_db(self):
        self.assertAlmostEqual(m.power_ratio_db(40.0, 40.0), 0.0)

    def test_factor_of_two_is_three_db(self):
        self.assertAlmostEqual(m.power_ratio_db(80.0, 40.0), 3.0103, places=4)

    def test_factor_of_ten_is_ten_db(self):
        self.assertAlmostEqual(m.power_ratio_db(400.0, 40.0), 10.0)

    def test_ratio_below_one_is_negative(self):
        self.assertLess(m.power_ratio_db(20.0, 40.0), 0.0)

    def test_zero_power_rejected(self):
        with self.assertRaises(ValueError):
            m.power_ratio_db(0.0, 40.0)

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            m.power_ratio_db(40.0, -1.0)

    def test_non_finite_power_rejected(self):
        with self.assertRaises(ValueError):
            m.power_ratio_db(float("inf"), 40.0)

    def test_non_numeric_power_rejected(self):
        with self.assertRaises(ValueError):
            m.power_ratio_db("40", 40.0)

    def test_required_test_power_for_three_db(self):
        self.assertAlmostEqual(m.required_test_power_w(50.0, 3.0), 50.0 * 10 ** 0.3)

    def test_required_test_power_zero_margin_is_identity(self):
        self.assertAlmostEqual(m.required_test_power_w(50.0, 0.0), 50.0)

    def test_required_test_power_rejects_negative_margin(self):
        with self.assertRaises(ValueError):
            m.required_test_power_w(50.0, -0.5)

    def test_required_test_power_rejects_non_finite_margin(self):
        with self.assertRaises(ValueError):
            m.required_test_power_w(50.0, float("nan"))

    def test_required_test_power_rejects_bad_power(self):
        with self.assertRaises(ValueError):
            m.required_test_power_w(0.0, 3.0)

    def test_round_trip_margin_recovers_input(self):
        demanded = m.required_test_power_w(37.5, 4.0)
        self.assertAlmostEqual(m.achieved_margin_db(demanded, 37.5), 4.0)


class TestMarginComparison(unittest.TestCase):
    def test_exact_boundary_counts_as_met(self):
        peak = 37.0
        demanded = m.required_test_power_w(peak, 6.0)
        achieved = m.achieved_margin_db(demanded, peak)
        self.assertTrue(m.margin_is_met(achieved, 6.0))

    def test_clear_pass(self):
        self.assertTrue(m.margin_is_met(7.5, 6.0))

    def test_clear_fail(self):
        self.assertFalse(m.margin_is_met(5.2, 6.0))

    def test_tolerance_does_not_forgive_a_real_shortfall(self):
        self.assertFalse(m.margin_is_met(6.0 - 1e-3, 6.0))

    def test_comparison_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            m.margin_is_met("6", 6.0)

    def test_comparison_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            m.margin_is_met(6.0, float("inf"))


class TestEvaluateUnit(unittest.TestCase):
    def base_unit(self, **over):
        unit = {
            "id": "twt-output-filter",
            "hardware_category": "equipment",
            "heritage": "recurrent",
            "max_operating_power_w": 100.0,
            "articles_tested": 2,
            "measured_threshold_w": 400.0,
        }
        unit.update(over)
        return unit

    def test_compliant_unit(self):
        result = m.evaluate_unit(self.base_unit())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["required_margin_db"], 3.0)
        self.assertAlmostEqual(result["achieved_margin_db"], 6.0206, places=4)
        self.assertEqual(result["findings"], [])

    def test_required_test_power_reported(self):
        result = m.evaluate_unit(self.base_unit())
        self.assertAlmostEqual(result["required_test_power_w"], 100.0 * 10 ** 0.3)

    def test_deficient_unit_flagged(self):
        result = m.evaluate_unit(self.base_unit(measured_threshold_w=150.0))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertGreater(result["deficit_db"], 0.0)

    def test_deficit_is_zero_when_compliant(self):
        result = m.evaluate_unit(self.base_unit())
        self.assertAlmostEqual(result["deficit_db"], 0.0)

    def test_missing_threshold_is_a_finding_not_a_pass(self):
        unit = self.base_unit()
        del unit["measured_threshold_w"]
        result = m.evaluate_unit(unit)
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["achieved_margin_db"])
        self.assertIn("no measured multipactor threshold on record", result["findings"])

    def test_exact_boundary_unit_is_compliant(self):
        peak = 90.0
        unit = self.base_unit(
            max_operating_power_w=peak,
            measured_threshold_w=m.required_test_power_w(peak, 3.0),
        )
        result = m.evaluate_unit(unit)
        self.assertTrue(result["compliant"])

    def test_first_of_kind_single_article_needs_more(self):
        unit = self.base_unit(heritage="first-of-kind", articles_tested=1)
        result = m.evaluate_unit(unit)
        self.assertAlmostEqual(result["required_margin_db"], 7.0)
        self.assertFalse(result["compliant"])

    def test_missing_key_rejected(self):
        unit = self.base_unit()
        del unit["heritage"]
        with self.assertRaises(ValueError):
            m.evaluate_unit(unit)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            m.evaluate_unit(["twt-output-filter"])

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            m.evaluate_unit(self.base_unit(id="  "))

    def test_bad_threshold_rejected(self):
        with self.assertRaises(ValueError):
            m.evaluate_unit(self.base_unit(measured_threshold_w=-4.0))

    def test_bad_peak_power_rejected(self):
        with self.assertRaises(ValueError):
            m.evaluate_unit(self.base_unit(max_operating_power_w=0.0))

    def test_identifier_is_stripped(self):
        result = m.evaluate_unit(self.base_unit(id="  ortho-mode-transducer "))
        self.assertEqual(result["id"], "ortho-mode-transducer")


class TestCampaign(unittest.TestCase):
    def units(self):
        return [
            {
                "id": "waveguide-switch",
                "hardware_category": "equipment",
                "heritage": "recurrent",
                "max_operating_power_w": 100.0,
                "articles_tested": 2,
                "measured_threshold_w": 400.0,
            },
            {
                "id": "coaxial-connector",
                "hardware_category": "component",
                "heritage": "first-of-kind",
                "max_operating_power_w": 60.0,
                "articles_tested": 1,
                "measured_threshold_w": 120.0,
            },
        ]

    def test_campaign_reports_both_articles(self):
        results = m.assess_units(self.units())
        self.assertEqual(len(results), 2)

    def test_campaign_summary_counts(self):
        summary = m.summarize_assessment(m.assess_units(self.units()))
        self.assertEqual(summary["articles"], 2)
        self.assertEqual(summary["compliant"], 1)
        self.assertEqual(summary["non_compliant_ids"], ["coaxial-connector"])
        self.assertFalse(summary["campaign_compliant"])

    def test_campaign_worst_deficit_positive(self):
        summary = m.summarize_assessment(m.assess_units(self.units()))
        self.assertGreater(summary["worst_deficit_db"], 0.0)

    def test_all_compliant_campaign(self):
        units = self.units()
        units[1]["measured_threshold_w"] = 600.0
        summary = m.summarize_assessment(m.assess_units(units))
        self.assertTrue(summary["campaign_compliant"])
        self.assertAlmostEqual(summary["worst_deficit_db"], 0.0)

    def test_duplicate_identifier_rejected(self):
        units = self.units()
        units[1]["id"] = "waveguide-switch"
        with self.assertRaises(ValueError):
            m.assess_units(units)

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            m.assess_units([])

    def test_non_list_campaign_rejected(self):
        with self.assertRaises(ValueError):
            m.assess_units({"id": "x"})

    def test_summary_rejects_empty_results(self):
        with self.assertRaises(ValueError):
            m.summarize_assessment([])

    def test_tolerance_constant_is_representation_scale(self):
        self.assertLess(m.MARGIN_TOLERANCE_DB, 1e-6)
        self.assertGreater(m.MARGIN_TOLERANCE_DB, 0.0)

    def test_module_is_offline(self):
        self.assertFalse(hasattr(m, "requests"))
        self.assertTrue(math.isfinite(m.SINGLE_ARTICLE_UPLIFT_DB))


if __name__ == "__main__":
    unittest.main()
