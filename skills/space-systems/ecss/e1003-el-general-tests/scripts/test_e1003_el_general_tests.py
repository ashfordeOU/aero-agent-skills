"""stdlib unittest for ECSS-E-ST-10-03C §6.5.1 element general tests logic.

Offline, deterministic. Run: python3 test_e1003_el_general_tests.py
Must print OK on success with 10+ tests.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_general_tests_logic import (
    MECHANICAL_FUNCTIONAL,
    ELECTRICAL_FUNCTIONAL,
    categorize_test,
    evaluate_measurement,
    evaluate_test_item,
    evaluate_test_suite,
    find_missing_required_tests,
    determine_element_release_readiness,
)


def _mech_record(
    test_id="T-M-01",
    pre_passed=True,
    value=50.0,
    lower=40.0,
    upper=60.0,
    post_passed=True,
):
    return {
        "test_id": test_id,
        "test_type": MECHANICAL_FUNCTIONAL,
        "pre_inspection_passed": pre_passed,
        "measured_value": value,
        "lower_limit": lower,
        "upper_limit": upper,
        "post_inspection_passed": post_passed,
    }


def _elec_record(
    test_id="T-E-01",
    pre_passed=True,
    value=2.5,
    lower=0.0,
    upper=5.0,
    post_passed=True,
):
    return {
        "test_id": test_id,
        "test_type": ELECTRICAL_FUNCTIONAL,
        "pre_inspection_passed": pre_passed,
        "measured_value": value,
        "lower_limit": lower,
        "upper_limit": upper,
        "post_inspection_passed": post_passed,
    }


class TestCategorizeTest(unittest.TestCase):
    def test_mechanical_functional_accepted(self):
        self.assertEqual(categorize_test(MECHANICAL_FUNCTIONAL), MECHANICAL_FUNCTIONAL)

    def test_electrical_functional_accepted(self):
        self.assertEqual(categorize_test(ELECTRICAL_FUNCTIONAL), ELECTRICAL_FUNCTIONAL)

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_test("thermal_functional")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_test("")


class TestEvaluateMeasurement(unittest.TestCase):
    def test_value_within_limits(self):
        result = evaluate_measurement(5.0, 3.0, 7.0)
        self.assertTrue(result["within_limits"])

    def test_value_below_lower_limit(self):
        result = evaluate_measurement(2.9, 3.0, 7.0)
        self.assertFalse(result["within_limits"])

    def test_value_above_upper_limit(self):
        result = evaluate_measurement(7.1, 3.0, 7.0)
        self.assertFalse(result["within_limits"])

    def test_value_at_lower_boundary_passes(self):
        result = evaluate_measurement(3.0, 3.0, 7.0)
        self.assertTrue(result["within_limits"])

    def test_value_at_upper_boundary_passes(self):
        result = evaluate_measurement(7.0, 3.0, 7.0)
        self.assertTrue(result["within_limits"])

    def test_inverted_limits_raises(self):
        with self.assertRaises(ValueError):
            evaluate_measurement(5.0, 10.0, 1.0)

    def test_result_is_new_dict_not_mutation(self):
        val, lo, hi = 5.0, 3.0, 7.0
        result = evaluate_measurement(val, lo, hi)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["value"], val)
        self.assertEqual(result["lower_limit"], lo)
        self.assertEqual(result["upper_limit"], hi)


class TestEvaluateTestItem(unittest.TestCase):
    def test_all_pass_gives_pass_verdict(self):
        result = evaluate_test_item(_mech_record())
        self.assertEqual(result["verdict"], "pass")
        self.assertTrue(result["within_limits"])

    def test_pre_inspection_fail_halts_evaluation(self):
        result = evaluate_test_item(_mech_record(pre_passed=False))
        self.assertEqual(result["verdict"], "pre_inspection_fail")
        self.assertIsNone(result["within_limits"])

    def test_out_of_limits_below_lower(self):
        result = evaluate_test_item(_mech_record(value=39.9))
        self.assertEqual(result["verdict"], "out_of_limits")
        self.assertFalse(result["within_limits"])

    def test_out_of_limits_above_upper(self):
        result = evaluate_test_item(_mech_record(value=60.1))
        self.assertEqual(result["verdict"], "out_of_limits")
        self.assertFalse(result["within_limits"])

    def test_post_inspection_fail_invalidates_good_measurement(self):
        result = evaluate_test_item(_mech_record(post_passed=False))
        self.assertEqual(result["verdict"], "post_inspection_fail")
        self.assertTrue(result["within_limits"])

    def test_electrical_functional_pass(self):
        result = evaluate_test_item(_elec_record())
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["test_type"], ELECTRICAL_FUNCTIONAL)

    def test_electrical_functional_out_of_limits(self):
        result = evaluate_test_item(_elec_record(value=5.1))
        self.assertEqual(result["verdict"], "out_of_limits")

    def test_unknown_test_type_raises(self):
        bad = _mech_record()
        bad["test_type"] = "unknown_type"
        with self.assertRaises(ValueError):
            evaluate_test_item(bad)

    def test_result_carries_test_id(self):
        result = evaluate_test_item(_mech_record(test_id="MECH-007"))
        self.assertEqual(result["test_id"], "MECH-007")

    def test_pre_fail_takes_priority_over_out_of_limits(self):
        result = evaluate_test_item(_mech_record(pre_passed=False, value=99.9))
        self.assertEqual(result["verdict"], "pre_inspection_fail")


class TestEvaluateTestSuite(unittest.TestCase):
    def test_suite_returns_one_result_per_record(self):
        records = [_mech_record("T1"), _elec_record("T2")]
        results = evaluate_test_suite(records)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["test_id"], "T1")
        self.assertEqual(results[1]["test_id"], "T2")

    def test_empty_suite_returns_empty_list(self):
        self.assertEqual(evaluate_test_suite([]), [])


class TestFindMissingRequiredTests(unittest.TestCase):
    def test_all_present_returns_empty(self):
        results = [{"test_id": "T1"}, {"test_id": "T2"}]
        self.assertEqual(find_missing_required_tests(["T1", "T2"], results), [])

    def test_missing_id_returned(self):
        results = [{"test_id": "T1"}]
        missing = find_missing_required_tests(["T1", "T2"], results)
        self.assertEqual(missing, ["T2"])

    def test_result_is_sorted(self):
        results = []
        missing = find_missing_required_tests(["T3", "T1", "T2"], results)
        self.assertEqual(missing, ["T1", "T2", "T3"])


class TestDetermineElementReleaseReadiness(unittest.TestCase):
    def test_all_pass_and_complete_is_ready(self):
        records = [_mech_record("T1"), _elec_record("T2")]
        results = evaluate_test_suite(records)
        ready, missing, failed = determine_element_release_readiness(
            ["T1", "T2"], results
        )
        self.assertTrue(ready)
        self.assertEqual(missing, [])
        self.assertEqual(failed, [])

    def test_missing_required_test_blocks_release(self):
        records = [_mech_record("T1")]
        results = evaluate_test_suite(records)
        ready, missing, failed = determine_element_release_readiness(
            ["T1", "T2"], results
        )
        self.assertFalse(ready)
        self.assertIn("T2", missing)

    def test_failed_verdict_blocks_release(self):
        records = [_mech_record("T1", value=99.9), _elec_record("T2")]
        results = evaluate_test_suite(records)
        ready, missing, failed = determine_element_release_readiness(
            ["T1", "T2"], results
        )
        self.assertFalse(ready)
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["test_id"], "T1")

    def test_post_inspection_fail_blocks_release(self):
        records = [_mech_record("T1", post_passed=False)]
        results = evaluate_test_suite(records)
        ready, missing, failed = determine_element_release_readiness(
            ["T1"], results
        )
        self.assertFalse(ready)
        self.assertEqual(failed[0]["verdict"], "post_inspection_fail")

    def test_no_required_tests_and_empty_results_is_ready(self):
        ready, missing, failed = determine_element_release_readiness([], [])
        self.assertTrue(ready)


if __name__ == "__main__":
    unittest.main()
