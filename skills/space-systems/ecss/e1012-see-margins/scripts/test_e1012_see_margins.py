"""
Gate 3 contract tests for e1012_see_margins_logic.
Run: python3 test_e1012_see_margins.py
Deterministic, offline, stdlib only.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from e1012_see_margins_logic import (
    SEEMarginError,
    categorize_see_event,
    check_sel_protection,
    compute_see_margin,
    evaluate_device_see_compliance,
)


class TestCategorizeEventType(unittest.TestCase):

    def test_seu_is_soft(self):
        self.assertEqual(categorize_see_event("SEU"), "soft")

    def test_set_is_soft(self):
        self.assertEqual(categorize_see_event("SET"), "soft")

    def test_sefi_is_soft(self):
        self.assertEqual(categorize_see_event("SEFI"), "soft")

    def test_mbu_is_soft(self):
        self.assertEqual(categorize_see_event("MBU"), "soft")

    def test_sel_is_destructive(self):
        self.assertEqual(categorize_see_event("SEL"), "destructive")

    def test_seb_is_destructive(self):
        self.assertEqual(categorize_see_event("SEB"), "destructive")

    def test_segr_is_destructive(self):
        self.assertEqual(categorize_see_event("SEGR"), "destructive")

    def test_unknown_type_raises(self):
        with self.assertRaises(SEEMarginError):
            categorize_see_event("UNKNOWN_TYPE")

    def test_lowercase_input_accepted(self):
        self.assertEqual(categorize_see_event("seu"), "soft")
        self.assertEqual(categorize_see_event("sel"), "destructive")

    def test_mixed_case_input_accepted(self):
        self.assertEqual(categorize_see_event("Sefi"), "soft")
        self.assertEqual(categorize_see_event("Seb"), "destructive")


class TestComputeSeeMargin(unittest.TestCase):

    def test_pass_case(self):
        # rate=0.01 ev/day, 365 days, margin=2, allowable=10
        # predicted=3.65, margined=7.3, ratio=10/7.3~1.37 -> PASS
        result = compute_see_margin(0.01, 365.0, 2.0, 10.0)
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["predicted_events"], 3.65, places=9)
        self.assertAlmostEqual(result["margined_events"], 7.3, places=9)
        self.assertGreaterEqual(result["margin_ratio"], 1.0)

    def test_fail_case(self):
        # rate=0.1 ev/day, 365 days, margin=2, allowable=10
        # predicted=36.5, margined=73 -> FAIL
        result = compute_see_margin(0.1, 365.0, 2.0, 10.0)
        self.assertEqual(result["status"], "FAIL")
        self.assertLess(result["margin_ratio"], 1.0)

    def test_exact_boundary_is_pass(self):
        # margined == allowable -> ratio exactly 1.0 -> PASS
        result = compute_see_margin(1.0, 10.0, 2.0, 20.0)
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["margin_ratio"], 1.0, places=9)

    def test_zero_rate_yields_pass_and_inf_ratio(self):
        result = compute_see_margin(0.0, 365.0, 2.0, 1.0)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(math.isinf(result["margin_ratio"]))

    def test_large_margin_factor_turns_borderline_to_fail(self):
        # Without margin passes (0.001 * 100 = 0.1 <= 5);
        # with factor=100: margined = 10 > 5 -> FAIL
        result = compute_see_margin(0.001, 100.0, 100.0, 5.0)
        self.assertEqual(result["status"], "FAIL")

    def test_zero_duration_raises(self):
        with self.assertRaises(SEEMarginError):
            compute_see_margin(0.01, 0.0, 2.0, 10.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(SEEMarginError):
            compute_see_margin(0.01, -1.0, 2.0, 10.0)

    def test_margin_factor_below_one_raises(self):
        with self.assertRaises(SEEMarginError):
            compute_see_margin(0.01, 365.0, 0.5, 10.0)

    def test_negative_rate_raises(self):
        with self.assertRaises(SEEMarginError):
            compute_see_margin(-0.01, 365.0, 2.0, 10.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(SEEMarginError):
            compute_see_margin(0.01, 365.0, 2.0, 0.0)

    def test_result_contains_all_keys(self):
        result = compute_see_margin(0.01, 100.0, 2.0, 5.0)
        for key in ("predicted_events", "margined_events", "margin_ratio", "status", "finding"):
            self.assertIn(key, result)

    def test_margin_factor_of_one_is_accepted(self):
        # margin_factor == 1.0 is the minimum valid value
        result = compute_see_margin(0.01, 100.0, 1.0, 5.0)
        self.assertIn(result["status"], ("PASS", "FAIL"))


class TestCheckSelProtection(unittest.TestCase):

    def test_current_limiting_alone_is_sufficient(self):
        result = check_sel_protection(has_current_limiting=True, has_power_cycling=False)
        self.assertTrue(result["protected"])

    def test_power_cycling_alone_is_sufficient(self):
        result = check_sel_protection(has_current_limiting=False, has_power_cycling=True)
        self.assertTrue(result["protected"])

    def test_both_measures_is_protected(self):
        result = check_sel_protection(has_current_limiting=True, has_power_cycling=True)
        self.assertTrue(result["protected"])

    def test_no_measures_is_not_protected(self):
        result = check_sel_protection(has_current_limiting=False, has_power_cycling=False)
        self.assertFalse(result["protected"])

    def test_missing_protection_finding_contains_keyword(self):
        result = check_sel_protection(False, False)
        self.assertIn("MISSING", result["finding"])


class TestEvaluateDeviceCompliance(unittest.TestCase):

    def test_soft_event_within_margin_is_compliant(self):
        result = evaluate_device_see_compliance(
            device_name="SRAM-A",
            event_type="SEU",
            predicted_rate_per_day=0.001,
            mission_duration_days=365.0,
            margin_factor=2.0,
            allowable_events=5.0,
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["category"], "soft")
        self.assertIsNone(result["protection"])

    def test_soft_event_exceeding_margin_is_not_compliant(self):
        result = evaluate_device_see_compliance(
            device_name="SRAM-B",
            event_type="SEU",
            predicted_rate_per_day=1.0,
            mission_duration_days=365.0,
            margin_factor=2.0,
            allowable_events=5.0,
        )
        self.assertFalse(result["compliant"])

    def test_destructive_within_margin_with_protection_is_compliant(self):
        result = evaluate_device_see_compliance(
            device_name="PMIC-C",
            event_type="SEL",
            predicted_rate_per_day=0.0001,
            mission_duration_days=365.0,
            margin_factor=10.0,
            allowable_events=5.0,
            has_current_limiting=True,
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["category"], "destructive")
        self.assertIsNotNone(result["protection"])
        self.assertTrue(result["protection"]["protected"])

    def test_destructive_within_margin_but_no_protection_not_compliant(self):
        result = evaluate_device_see_compliance(
            device_name="PMIC-D",
            event_type="SEL",
            predicted_rate_per_day=0.0001,
            mission_duration_days=365.0,
            margin_factor=10.0,
            allowable_events=5.0,
            has_current_limiting=False,
            has_power_cycling=False,
        )
        self.assertFalse(result["compliant"])

    def test_destructive_exceeding_margin_with_protection_not_compliant(self):
        result = evaluate_device_see_compliance(
            device_name="PMIC-E",
            event_type="SEL",
            predicted_rate_per_day=1.0,
            mission_duration_days=365.0,
            margin_factor=10.0,
            allowable_events=5.0,
            has_current_limiting=True,
        )
        self.assertFalse(result["compliant"])

    def test_empty_device_name_raises(self):
        with self.assertRaises(SEEMarginError):
            evaluate_device_see_compliance(
                device_name="",
                event_type="SEU",
                predicted_rate_per_day=0.001,
                mission_duration_days=365.0,
                margin_factor=2.0,
                allowable_events=5.0,
            )

    def test_whitespace_only_device_name_raises(self):
        with self.assertRaises(SEEMarginError):
            evaluate_device_see_compliance(
                device_name="   ",
                event_type="SEU",
                predicted_rate_per_day=0.001,
                mission_duration_days=365.0,
                margin_factor=2.0,
                allowable_events=5.0,
            )

    def test_findings_list_is_non_empty(self):
        result = evaluate_device_see_compliance(
            device_name="FPGA-X",
            event_type="SEFI",
            predicted_rate_per_day=0.01,
            mission_duration_days=100.0,
            margin_factor=2.0,
            allowable_events=10.0,
        )
        self.assertIsInstance(result["findings"], list)
        self.assertGreater(len(result["findings"]), 0)

    def test_event_type_normalised_to_uppercase(self):
        result = evaluate_device_see_compliance(
            device_name="MCU-Y",
            event_type="seu",
            predicted_rate_per_day=0.001,
            mission_duration_days=200.0,
            margin_factor=2.0,
            allowable_events=5.0,
        )
        self.assertEqual(result["event_type"], "SEU")

    def test_destructive_assessment_includes_two_findings(self):
        # Both margin and protection findings should appear for destructive types
        result = evaluate_device_see_compliance(
            device_name="LDMOS-Z",
            event_type="SEB",
            predicted_rate_per_day=0.00001,
            mission_duration_days=365.0,
            margin_factor=10.0,
            allowable_events=1.0,
            has_power_cycling=True,
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_soft_assessment_includes_one_finding(self):
        result = evaluate_device_see_compliance(
            device_name="DRAM-Q",
            event_type="MBU",
            predicted_rate_per_day=0.005,
            mission_duration_days=365.0,
            margin_factor=2.0,
            allowable_events=10.0,
        )
        self.assertEqual(len(result["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
