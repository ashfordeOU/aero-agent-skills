#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-netlist-verification.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_netlist_verification.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_netlist_verification_logic import (  # noqa: E402
    EQUIVALENT,
    FAIL,
    NOT_EQUIVALENT,
    NOT_RUN,
    NOT_VERIFIED,
    OUTCOMES,
    PASS,
    POINT_STATES,
    UNMAPPED,
    VERIFIED,
    VERIFIED_WITH_WAIVERS,
    WAIVED,
    equivalence_fraction,
    evaluate_netlist_verification,
    meets_equivalence_goal,
    netlist_verification_outcome,
    normalize_point_state,
    normalize_test_result,
    points_in_state,
    rerun_completeness,
    tests_already_failing,
    tests_broken_by_synthesis,
    tests_not_rerun,
    unjustified_waivers,
    validate_points,
    validate_tests,
)


def base_check():
    return {
        "points": [
            {"id": "P-1", "state": "equivalent", "region": "control"},
            {"id": "P-2", "state": "equivalent", "region": "datapath"},
            {"id": "P-3", "state": "equivalent", "region": "datapath"},
            {"id": "P-4", "state": "equivalent", "region": "interface"},
        ],
        "tests": [
            {"id": "T-1", "source_result": "pass", "netlist_result": "pass"},
            {"id": "T-2", "source_result": "pass", "netlist_result": "pass"},
            {"id": "T-3", "source_result": "pass", "netlist_result": "pass"},
        ],
        "equivalence_goal": 1.0,
        "outcome_record": "netlist verification report issue 1",
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_matched_folds_to_equivalent(self):
        self.assertEqual(normalize_point_state("Matched"), EQUIVALENT)

    def test_mismatch_folds_to_not_equivalent(self):
        self.assertEqual(normalize_point_state("mismatch"), NOT_EQUIVALENT)

    def test_no_mapping_folds_to_unmapped(self):
        self.assertEqual(normalize_point_state("no mapping"), UNMAPPED)

    def test_accepted_folds_to_waived(self):
        self.assertEqual(normalize_point_state("accepted"), WAIVED)

    def test_unknown_point_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_point_state("probably fine")

    def test_four_point_states_are_the_whole_set(self):
        self.assertEqual(len(POINT_STATES), 4)

    def test_skipped_folds_to_not_run(self):
        self.assertEqual(normalize_test_result("skipped"), NOT_RUN)

    def test_passed_folds_to_pass(self):
        self.assertEqual(normalize_test_result("Passed"), PASS)

    def test_unknown_test_result_rejected(self):
        with self.assertRaises(ValueError):
            normalize_test_result("inconclusive")

    def test_three_outcomes_are_the_whole_set(self):
        self.assertEqual(len(OUTCOMES), 3)


class TestValidation(unittest.TestCase):
    def test_points_resolve_in_declared_order(self):
        points = validate_points(base_check()["points"])
        self.assertEqual([p["id"] for p in points], ["P-1", "P-2", "P-3", "P-4"])

    def test_duplicate_point_id_rejected(self):
        records = base_check()["points"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_points(records)

    def test_unknown_point_key_rejected(self):
        records = base_check()["points"]
        records[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_points(records)

    def test_point_without_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_points([{"id": "P-9"}])

    def test_duplicate_test_id_rejected(self):
        records = base_check()["tests"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_tests(records)

    def test_test_results_default_to_not_run(self):
        tests = validate_tests([{"id": "T-9"}])
        self.assertEqual(tests[0]["source_result"], NOT_RUN)
        self.assertEqual(tests[0]["netlist_result"], NOT_RUN)

    def test_non_list_points_rejected(self):
        with self.assertRaises(ValueError):
            validate_points({"id": "P-1"})


class TestEquivalenceArithmetic(unittest.TestCase):
    def test_a_clean_comparison_is_fully_equivalent(self):
        points = validate_points(base_check()["points"])
        self.assertAlmostEqual(equivalence_fraction(points), 1.0, places=12)

    def test_an_unmapped_point_stays_in_the_denominator(self):
        records = base_check()["points"]
        records[3]["state"] = "unmapped"
        points = validate_points(records)
        self.assertAlmostEqual(equivalence_fraction(points), 0.75, places=12)
        self.assertEqual(points_in_state(points, UNMAPPED), ["P-4"])

    def test_a_waived_point_stays_in_the_denominator(self):
        records = base_check()["points"]
        records[3]["state"] = "waived"
        records[3]["justification"] = "clock gating cell handled by hand"
        points = validate_points(records)
        self.assertAlmostEqual(equivalence_fraction(points), 0.75, places=12)

    def test_equivalence_needs_a_point(self):
        with self.assertRaises(ValueError):
            equivalence_fraction([])

    def test_a_goal_met_exactly_is_met(self):
        self.assertTrue(meets_equivalence_goal(3 / 4, 0.75))

    def test_a_goal_met_by_a_third_landing_is_met(self):
        self.assertTrue(meets_equivalence_goal(1 / 3, 1 / 3))

    def test_a_goal_missed_is_missed(self):
        self.assertFalse(meets_equivalence_goal(0.74, 0.75))

    def test_a_goal_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_equivalence_goal(0.5, 1.2)

    def test_an_unjustified_waiver_is_found(self):
        records = base_check()["points"]
        records[0]["state"] = "waived"
        points = validate_points(records)
        self.assertEqual(unjustified_waivers(points), ["P-1"])


class TestTestResultReading(unittest.TestCase):
    def test_a_full_rerun_is_complete(self):
        tests = validate_tests(base_check()["tests"])
        self.assertAlmostEqual(rerun_completeness(tests), 1.0, places=12)
        self.assertEqual(tests_not_rerun(tests), [])

    def test_a_missing_rerun_is_found_and_lowers_completeness(self):
        records = base_check()["tests"]
        records[2]["netlist_result"] = "skipped"
        tests = validate_tests(records)
        self.assertEqual(tests_not_rerun(tests), ["T-3"])
        self.assertAlmostEqual(rerun_completeness(tests), 2 / 3, places=12)

    def test_a_test_broken_by_synthesis_is_found(self):
        records = base_check()["tests"]
        records[1]["netlist_result"] = "fail"
        tests = validate_tests(records)
        self.assertEqual(tests_broken_by_synthesis(tests), ["T-2"])

    def test_a_test_already_failing_stays_separate(self):
        records = base_check()["tests"]
        records[1]["source_result"] = "fail"
        records[1]["netlist_result"] = "fail"
        tests = validate_tests(records)
        self.assertEqual(tests_already_failing(tests), ["T-2"])
        self.assertEqual(tests_broken_by_synthesis(tests), [])

    def test_rerun_completeness_needs_a_source_level_pass(self):
        tests = validate_tests([{"id": "T-9", "source_result": "fail"}])
        with self.assertRaises(ValueError):
            rerun_completeness(tests)


class TestOutcome(unittest.TestCase):
    def setUp(self):
        self.points = validate_points(base_check()["points"])
        self.tests = validate_tests(base_check()["tests"])

    def test_clean_evidence_is_verified(self):
        self.assertEqual(
            netlist_verification_outcome(self.points, self.tests), VERIFIED
        )

    def test_a_justified_waiver_is_verified_with_waivers(self):
        records = base_check()["points"]
        records[3]["state"] = "waived"
        records[3]["justification"] = "clock gating cell handled by hand"
        points = validate_points(records)
        self.assertEqual(
            netlist_verification_outcome(points, self.tests), VERIFIED_WITH_WAIVERS
        )

    def test_an_unmapped_point_is_not_verified(self):
        records = base_check()["points"]
        records[3]["state"] = "unmapped"
        points = validate_points(records)
        self.assertEqual(netlist_verification_outcome(points, self.tests), NOT_VERIFIED)

    def test_a_not_equivalent_point_is_not_verified(self):
        records = base_check()["points"]
        records[0]["state"] = "mismatch"
        points = validate_points(records)
        self.assertEqual(netlist_verification_outcome(points, self.tests), NOT_VERIFIED)

    def test_an_unjustified_waiver_is_not_verified(self):
        records = base_check()["points"]
        records[3]["state"] = "waived"
        points = validate_points(records)
        self.assertEqual(netlist_verification_outcome(points, self.tests), NOT_VERIFIED)

    def test_a_missing_rerun_is_not_verified(self):
        records = base_check()["tests"]
        records[0]["netlist_result"] = "skipped"
        tests = validate_tests(records)
        self.assertEqual(netlist_verification_outcome(self.points, tests), NOT_VERIFIED)

    def test_a_test_broken_by_synthesis_is_not_verified(self):
        records = base_check()["tests"]
        records[0]["netlist_result"] = "fail"
        tests = validate_tests(records)
        self.assertEqual(netlist_verification_outcome(self.points, tests), NOT_VERIFIED)


class TestEvaluateNetlistVerification(unittest.TestCase):
    def test_a_clean_check_is_verified_and_lets_work_continue(self):
        result = evaluate_netlist_verification(base_check())
        self.assertEqual(result["outcome"], VERIFIED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["detailed_design_may_continue"])

    def test_figures_reach_the_result(self):
        result = evaluate_netlist_verification(base_check())
        self.assertEqual(result["point_count"], 4)
        self.assertAlmostEqual(result["equivalence"], 1.0, places=12)

    def test_a_goal_met_exactly_does_not_fail_the_check(self):
        check = base_check()
        check["equivalence_goal"] = 4 / 4
        result = evaluate_netlist_verification(check)
        self.assertNotIn("equivalence-below-goal", codes(result))

    def test_an_unmapped_point_is_reported(self):
        check = base_check()
        check["points"][3]["state"] = "unmapped"
        result = evaluate_netlist_verification(check)
        self.assertIn("comparison-point-unmapped", codes(result))
        self.assertIn("equivalence-below-goal", codes(result))
        self.assertEqual(result["outcome"], NOT_VERIFIED)

    def test_a_not_equivalent_point_is_reported(self):
        check = base_check()
        check["points"][0]["state"] = "mismatch"
        result = evaluate_netlist_verification(check)
        self.assertIn("comparison-point-not-equivalent", codes(result))

    def test_an_unjustified_waiver_is_reported(self):
        check = base_check()
        check["points"][3]["state"] = "waived"
        result = evaluate_netlist_verification(check)
        self.assertIn("waiver-without-justification", codes(result))

    def test_a_justified_waiver_is_not_reported(self):
        check = base_check()
        check["points"][3]["state"] = "waived"
        check["points"][3]["justification"] = "clock gating cell handled by hand"
        check["equivalence_goal"] = 0.75
        result = evaluate_netlist_verification(check)
        self.assertNotIn("waiver-without-justification", codes(result))
        self.assertEqual(result["outcome"], VERIFIED_WITH_WAIVERS)

    def test_a_missing_rerun_is_reported(self):
        check = base_check()
        check["tests"][0]["netlist_result"] = "skipped"
        result = evaluate_netlist_verification(check)
        self.assertIn("source-pass-not-rerun-on-netlist", codes(result))

    def test_a_test_broken_by_synthesis_is_reported(self):
        check = base_check()
        check["tests"][0]["netlist_result"] = "fail"
        result = evaluate_netlist_verification(check)
        self.assertIn("test-broken-by-synthesis", codes(result))

    def test_a_test_already_failing_is_reported_separately(self):
        check = base_check()
        check["tests"][0]["source_result"] = "fail"
        check["tests"][0]["netlist_result"] = "fail"
        result = evaluate_netlist_verification(check)
        self.assertIn("test-already-failing-before-synthesis", codes(result))
        self.assertNotIn("test-broken-by-synthesis", codes(result))

    def test_an_unrecorded_outcome_is_reported(self):
        check = base_check()
        check["outcome_record"] = ""
        result = evaluate_netlist_verification(check)
        self.assertIn("outcome-not-recorded", codes(result))
        self.assertFalse(result["detailed_design_may_continue"])

    def test_unknown_check_key_rejected(self):
        check = base_check()
        check["engineer"] = "someone"
        with self.assertRaises(ValueError):
            evaluate_netlist_verification(check)

    def test_missing_tests_rejected(self):
        check = base_check()
        del check["tests"]
        with self.assertRaises(ValueError):
            evaluate_netlist_verification(check)

    def test_empty_points_rejected(self):
        check = base_check()
        check["points"] = []
        with self.assertRaises(ValueError):
            evaluate_netlist_verification(check)

    def test_empty_tests_rejected(self):
        check = base_check()
        check["tests"] = []
        with self.assertRaises(ValueError):
            evaluate_netlist_verification(check)

    def test_non_mapping_check_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_netlist_verification([("points", [])])


if __name__ == "__main__":
    unittest.main()
