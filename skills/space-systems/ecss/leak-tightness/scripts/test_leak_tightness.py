"""
Offline deterministic unit tests for leak_tightness_logic.py.
Run with: python3 test_leak_tightness.py
Must print OK on success. 10+ tests covering all public functions.
Reference: ECSS-E-ST-32C clause 4.2.1 — leak-tightness assessment.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from leak_tightness_logic import (
    LEAK_TIGHTNESS_CLASSES,
    VALID_PATH_TYPES,
    LeakPathError,
    categorize_leak_path,
    validate_leak_rate,
    scale_leak_rate_to_operating,
    get_allowable_rate,
    check_path_compliance,
    compute_system_leak_rate,
    assess_leak_tightness,
)


class TestCategorizeLeakPath(unittest.TestCase):

    def test_valid_seal(self):
        self.assertEqual(categorize_leak_path("seal"), "seal")

    def test_valid_penetration(self):
        self.assertEqual(categorize_leak_path("penetration"), "penetration")

    def test_valid_weld(self):
        self.assertEqual(categorize_leak_path("weld"), "weld")

    def test_valid_bond_line(self):
        self.assertEqual(categorize_leak_path("bond_line"), "bond_line")

    def test_valid_fitting(self):
        self.assertEqual(categorize_leak_path("fitting"), "fitting")

    def test_strips_whitespace(self):
        self.assertEqual(categorize_leak_path("  weld  "), "weld")

    def test_unrecognized_type_raises(self):
        with self.assertRaises(LeakPathError):
            categorize_leak_path("crack")

    def test_empty_string_raises(self):
        with self.assertRaises(LeakPathError):
            categorize_leak_path("")


class TestValidateLeakRate(unittest.TestCase):

    def test_zero_is_valid(self):
        validate_leak_rate(0.0)  # no exception

    def test_small_positive_is_valid(self):
        validate_leak_rate(1e-10)  # no exception

    def test_negative_raises(self):
        with self.assertRaises(LeakPathError):
            validate_leak_rate(-1e-7)

    def test_string_raises(self):
        with self.assertRaises(LeakPathError):
            validate_leak_rate("1e-6")

    def test_inf_raises(self):
        with self.assertRaises(LeakPathError):
            validate_leak_rate(float("inf"))

    def test_nan_raises(self):
        with self.assertRaises(LeakPathError):
            validate_leak_rate(float("nan"))


class TestScaleLeakRateToOperating(unittest.TestCase):

    def test_same_pressure_no_change(self):
        result = scale_leak_rate_to_operating(1e-6, 1.5, 1.5)
        self.assertAlmostEqual(result, 1e-6)

    def test_double_operating_pressure_doubles_rate(self):
        result = scale_leak_rate_to_operating(1e-6, 1.0, 2.0)
        self.assertAlmostEqual(result, 2e-6)

    def test_half_operating_pressure_halves_rate(self):
        result = scale_leak_rate_to_operating(2e-6, 2.0, 1.0)
        self.assertAlmostEqual(result, 1e-6)

    def test_zero_test_pressure_raises(self):
        with self.assertRaises(LeakPathError):
            scale_leak_rate_to_operating(1e-6, 0.0, 1.5)

    def test_negative_operating_pressure_raises(self):
        with self.assertRaises(LeakPathError):
            scale_leak_rate_to_operating(1e-6, 1.5, -1.0)


class TestGetAllowableRate(unittest.TestCase):

    def test_lt1_is_most_stringent(self):
        self.assertLess(get_allowable_rate("LT1"), get_allowable_rate("LT2"))

    def test_class_ordering_lt2_lt3(self):
        self.assertLess(get_allowable_rate("LT2"), get_allowable_rate("LT3"))

    def test_class_ordering_lt3_lt4(self):
        self.assertLess(get_allowable_rate("LT3"), get_allowable_rate("LT4"))

    def test_lt1_exact_value(self):
        self.assertAlmostEqual(get_allowable_rate("LT1"), 1e-8)

    def test_unknown_class_raises(self):
        with self.assertRaises(LeakPathError):
            get_allowable_rate("LT99")


class TestCheckPathCompliance(unittest.TestCase):

    def test_rate_below_limit_passes(self):
        compliant, msg = check_path_compliance(5e-9, "LT1")
        self.assertTrue(compliant)
        self.assertIn("PASS", msg)

    def test_rate_above_limit_fails(self):
        compliant, msg = check_path_compliance(1e-5, "LT1")
        self.assertFalse(compliant)
        self.assertIn("FAIL", msg)

    def test_rate_exactly_at_limit_passes(self):
        limit = get_allowable_rate("LT2")
        compliant, _ = check_path_compliance(limit, "LT2")
        self.assertTrue(compliant)

    def test_fail_message_includes_excess_factor(self):
        _, msg = check_path_compliance(1e-4, "LT1")
        self.assertIn("excess factor", msg)


class TestComputeSystemLeakRate(unittest.TestCase):

    def test_single_path(self):
        self.assertAlmostEqual(compute_system_leak_rate([1e-7]), 1e-7)

    def test_multiple_paths_sum_correctly(self):
        result = compute_system_leak_rate([1e-7, 2e-7, 3e-7])
        self.assertAlmostEqual(result, 6e-7)

    def test_empty_list_raises(self):
        with self.assertRaises(LeakPathError):
            compute_system_leak_rate([])

    def test_negative_rate_in_list_raises(self):
        with self.assertRaises(LeakPathError):
            compute_system_leak_rate([1e-7, -1e-8])


class TestAssessLeakTightness(unittest.TestCase):

    def _make_paths(self, rates, types=None):
        if types is None:
            types = ["seal"] * len(rates)
        return [
            {"path_id": f"P{i + 1}", "path_type": t, "measured_rate": r}
            for i, (r, t) in enumerate(zip(rates, types))
        ]

    def test_all_paths_compliant_returns_true(self):
        # LT2 allowable=1e-6, margin=2 → effective=5e-7; rates well below
        paths = self._make_paths([1e-8, 2e-8], types=["seal", "weld"])
        result = assess_leak_tightness(paths, "LT2", margin_factor=2.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_single_path_exceeds_limit_fails(self):
        paths = self._make_paths([1e-5], types=["seal"])
        result = assess_leak_tightness(paths, "LT1", margin_factor=1.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_system_total_exceeds_even_when_individual_paths_ok(self):
        # Each path 4e-7 <= effective 5e-7 individually,
        # but system sum 8e-7 > 5e-7 → non-compliant overall
        paths = self._make_paths([4e-7, 4e-7], types=["seal", "fitting"])
        result = assess_leak_tightness(paths, "LT2", margin_factor=2.0)
        self.assertFalse(result["compliant"])

    def test_unrecognized_path_type_captured_as_finding(self):
        paths = [{"path_id": "P1", "path_type": "crack", "measured_rate": 1e-9}]
        result = assess_leak_tightness(paths, "LT3")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("P1" in f for f in result["findings"]))

    def test_margin_factor_below_one_raises(self):
        paths = self._make_paths([1e-9])
        with self.assertRaises(LeakPathError):
            assess_leak_tightness(paths, "LT1", margin_factor=0.5)

    def test_result_has_all_required_keys(self):
        paths = self._make_paths([1e-9])
        result = assess_leak_tightness(paths, "LT1")
        for key in (
            "compliant", "system_rate", "allowable_rate",
            "effective_limit", "margin_factor", "path_results", "findings",
        ):
            self.assertIn(key, result)

    def test_system_rate_equals_sum_of_path_rates(self):
        rates = [1e-9, 3e-9, 2e-9]
        paths = self._make_paths(rates)
        result = assess_leak_tightness(paths, "LT2")
        self.assertAlmostEqual(result["system_rate"], sum(rates))

    def test_lt1_stricter_than_lt4_for_same_rate(self):
        # 5e-3 is within LT4 (1e-2) but far above LT1 (1e-8)
        paths = self._make_paths([5e-3])
        r1 = assess_leak_tightness(paths, "LT1", margin_factor=1.0)
        r4 = assess_leak_tightness(paths, "LT4", margin_factor=1.0)
        self.assertFalse(r1["compliant"])
        self.assertTrue(r4["compliant"])

    def test_all_valid_path_types_accepted(self):
        paths = self._make_paths(
            [1e-9, 2e-9, 1e-9, 5e-10, 3e-10],
            types=["seal", "penetration", "weld", "bond_line", "fitting"],
        )
        result = assess_leak_tightness(paths, "LT2", margin_factor=1.0)
        self.assertTrue(result["compliant"])

    def test_default_margin_factor_is_two(self):
        paths = self._make_paths([1e-9])
        result = assess_leak_tightness(paths, "LT1")
        self.assertAlmostEqual(result["margin_factor"], 2.0)

    def test_effective_limit_equals_allowable_over_margin(self):
        paths = self._make_paths([1e-9])
        result = assess_leak_tightness(paths, "LT2", margin_factor=4.0)
        expected = get_allowable_rate("LT2") / 4.0
        self.assertAlmostEqual(result["effective_limit"], expected)

    def test_path_results_length_matches_input(self):
        paths = self._make_paths([1e-9, 2e-9, 3e-9])
        result = assess_leak_tightness(paths, "LT3")
        self.assertEqual(len(result["path_results"]), 3)


if __name__ == "__main__":
    unittest.main()
