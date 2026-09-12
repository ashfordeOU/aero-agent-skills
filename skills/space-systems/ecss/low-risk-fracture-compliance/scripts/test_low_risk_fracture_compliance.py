import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import low_risk_fracture_compliance_logic as logic


class TestCheckLoadLimited(unittest.TestCase):

    def test_passes_well_below_threshold(self):
        result = logic.check_load_limited(100.0, 400.0)
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["stress_ratio"], 0.25, places=4)
        self.assertGreater(result["margin"], 0)
        self.assertEqual(result["criterion"], "load_limited")

    def test_passes_at_exactly_threshold(self):
        result = logic.check_load_limited(240.0, 400.0)  # ratio = 0.6 exactly
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["stress_ratio"], 0.6, places=4)
        self.assertGreaterEqual(result["margin"], 0)

    def test_fails_above_threshold(self):
        result = logic.check_load_limited(280.0, 400.0)  # ratio = 0.7
        self.assertFalse(result["passes"])
        self.assertAlmostEqual(result["stress_ratio"], 0.7, places=4)
        self.assertLess(result["margin"], 0)

    def test_custom_threshold_tighter_fails(self):
        # ratio = 0.5 > 0.45
        result = logic.check_load_limited(200.0, 400.0, threshold_ratio=0.45)
        self.assertFalse(result["passes"])

    def test_custom_threshold_looser_passes(self):
        # ratio = 0.75 <= 0.80
        result = logic.check_load_limited(300.0, 400.0, threshold_ratio=0.80)
        self.assertTrue(result["passes"])

    def test_negative_stress_raises_error(self):
        with self.assertRaises(logic.LowRiskFractureError):
            logic.check_load_limited(-50.0, 400.0)

    def test_zero_stress_raises_error(self):
        with self.assertRaises(logic.LowRiskFractureError):
            logic.check_load_limited(0.0, 400.0)

    def test_zero_yield_raises_error(self):
        with self.assertRaises(logic.LowRiskFractureError):
            logic.check_load_limited(100.0, 0.0)

    def test_threshold_above_one_raises_error(self):
        with self.assertRaises(logic.LowRiskFractureError):
            logic.check_load_limited(100.0, 400.0, threshold_ratio=1.5)

    def test_threshold_zero_raises_error(self):
        with self.assertRaises(logic.LowRiskFractureError):
            logic.check_load_limited(100.0, 400.0, threshold_ratio=0.0)


class TestCheckNonFractureCritical(unittest.TestCase):

    def test_contained_failure_passes(self):
        result = logic.check_non_fracture_critical("contained_failure")
        self.assertTrue(result["passes"])
        self.assertEqual(result["criterion"], "non_fracture_critical")

    def test_redundant_load_path_passes(self):
        result = logic.check_non_fracture_critical("redundant_load_path")
        self.assertTrue(result["passes"])

    def test_cosmetic_only_passes(self):
        result = logic.check_non_fracture_critical("cosmetic_only")
        self.assertTrue(result["passes"])

    def test_loss_of_crew_safety_fails(self):
        result = logic.check_non_fracture_critical("loss_of_crew_safety")
        self.assertFalse(result["passes"])
        self.assertEqual(result["basis"], "fracture_critical_consequence")

    def test_loss_of_mission_fails(self):
        result = logic.check_non_fracture_critical("loss_of_mission")
        self.assertFalse(result["passes"])

    def test_pressure_vessel_failure_fails(self):
        result = logic.check_non_fracture_critical("pressure_vessel_failure")
        self.assertFalse(result["passes"])

    def test_unrecognized_consequence_raises_error(self):
        with self.assertRaises(logic.LowRiskFractureError):
            logic.check_non_fracture_critical("unknown_category")

    def test_empty_string_raises_error(self):
        with self.assertRaises(logic.LowRiskFractureError):
            logic.check_non_fracture_critical("")

    def test_case_insensitive_lookup(self):
        result = logic.check_non_fracture_critical("  Contained_Failure  ")
        self.assertTrue(result["passes"])


class TestQualifyLowRiskItem(unittest.TestCase):

    def test_qualifies_via_load_limited(self):
        item = {"name": "bracket_A", "max_stress_mpa": 150.0, "yield_strength_mpa": 400.0}
        result = logic.qualify_low_risk_item(item)
        self.assertTrue(result["qualifies"])
        self.assertEqual(result["path"], "load_limited")

    def test_qualifies_via_non_fracture_critical_when_stress_too_high(self):
        item = {
            "name": "clip_B",
            "max_stress_mpa": 300.0,
            "yield_strength_mpa": 400.0,
            "failure_consequence": "contained_failure",
        }
        result = logic.qualify_low_risk_item(item)
        self.assertTrue(result["qualifies"])
        self.assertEqual(result["path"], "non_fracture_critical")

    def test_fracture_critical_consequence_disqualifies_regardless_of_stress(self):
        item = {
            "name": "primary_fitting_C",
            "max_stress_mpa": 100.0,
            "yield_strength_mpa": 400.0,
            "failure_consequence": "loss_of_mission",
        }
        result = logic.qualify_low_risk_item(item)
        self.assertFalse(result["qualifies"])
        self.assertIsNone(result["path"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_no_evaluation_path_raises_error(self):
        item = {"name": "item_D"}
        with self.assertRaises(logic.LowRiskFractureError):
            logic.qualify_low_risk_item(item)

    def test_consequence_data_only_no_stress_data(self):
        item = {"name": "washer_F", "failure_consequence": "cosmetic_only"}
        result = logic.qualify_low_risk_item(item)
        self.assertTrue(result["qualifies"])
        self.assertEqual(result["path"], "non_fracture_critical")

    def test_stress_exceeds_threshold_no_consequence_data_not_qualified(self):
        item = {"name": "lug_G", "max_stress_mpa": 350.0, "yield_strength_mpa": 400.0}
        result = logic.qualify_low_risk_item(item)
        self.assertFalse(result["qualifies"])
        self.assertIsNone(result["path"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_custom_threshold_overrides_default(self):
        item = {
            "name": "shim_H",
            "max_stress_mpa": 280.0,
            "yield_strength_mpa": 400.0,
            "threshold_ratio": 0.75,
        }
        result = logic.qualify_low_risk_item(item)
        self.assertTrue(result["qualifies"])
        self.assertEqual(result["path"], "load_limited")


class TestAssessCompliance(unittest.TestCase):

    def test_all_items_qualified_is_fully_compliant(self):
        items = [
            {"name": "part1", "max_stress_mpa": 100.0, "yield_strength_mpa": 400.0},
            {"name": "part2", "failure_consequence": "redundant_load_path"},
        ]
        report = logic.assess_compliance(items)
        self.assertTrue(report["fully_compliant"])
        self.assertEqual(report["qualified"], 2)
        self.assertEqual(report["not_qualified"], 0)
        self.assertEqual(report["errors"], 0)

    def test_mixed_results_not_fully_compliant(self):
        items = [
            {"name": "part1", "max_stress_mpa": 100.0, "yield_strength_mpa": 400.0},
            {"name": "part2", "failure_consequence": "loss_of_mission"},
        ]
        report = logic.assess_compliance(items)
        self.assertFalse(report["fully_compliant"])
        self.assertEqual(report["qualified"], 1)
        self.assertEqual(report["not_qualified"], 1)

    def test_empty_list_returns_compliant(self):
        report = logic.assess_compliance([])
        self.assertTrue(report["fully_compliant"])
        self.assertEqual(report["total"], 0)

    def test_invalid_item_counted_as_error(self):
        items = [{"name": "bad_item"}]  # no evaluation path
        report = logic.assess_compliance(items)
        self.assertEqual(report["errors"], 1)
        self.assertFalse(report["fully_compliant"])

    def test_total_count_matches_input_length(self):
        items = [
            {"name": "a", "max_stress_mpa": 50.0, "yield_strength_mpa": 400.0},
            {"name": "b", "max_stress_mpa": 50.0, "yield_strength_mpa": 400.0},
            {"name": "c", "max_stress_mpa": 50.0, "yield_strength_mpa": 400.0},
        ]
        report = logic.assess_compliance(items)
        self.assertEqual(report["total"], 3)
        self.assertEqual(len(report["results"]), 3)

    def test_non_list_input_raises_error(self):
        with self.assertRaises(logic.LowRiskFractureError):
            logic.assess_compliance({"name": "not_a_list"})


if __name__ == "__main__":
    unittest.main()
