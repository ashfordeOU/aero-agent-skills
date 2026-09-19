"""Contract tests for the clause 5.7.2.5 redundancy management logic."""

import unittest

from e50_on_board_network_redundancy_management_logic import (
    EFFECTIVE,
    SINGLE_POINT_OF_FAILURE,
    TOO_SLOW,
    assess_redundancy_management,
    detection_budget,
    shared_elements,
    single_points_of_failure,
    switchover_time,
    validate_path,
    validate_time,
)

NOMINAL = ["obc-a", "switch-a", "harness"]
REDUNDANT = ["obc-b", "switch-b", "harness"]
CLEAN_A = ["obc-a", "switch-a", "node-a"]
CLEAN_B = ["obc-b", "switch-b", "node-b"]
DETECTION = 0.5
DECISION = 0.2
RECONFIG = 0.3
MAX_OUTAGE = 2.0


class ValidationTests(unittest.TestCase):
    def test_zero_time_accepted(self):
        self.assertAlmostEqual(validate_time(0), 0.0, places=9)

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(-0.1)

    def test_boolean_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(True)

    def test_text_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time("0.5")

    def test_infinite_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(float("inf"))

    def test_zero_time_rejected_where_forbidden(self):
        with self.assertRaises(ValueError):
            validate_time(0.0, "max_outage_s", allow_zero=False)

    def test_a_bare_string_is_not_a_path(self):
        with self.assertRaises(ValueError):
            validate_path("obc-a")

    def test_empty_path_rejected(self):
        with self.assertRaises(ValueError):
            validate_path([])

    def test_repeated_element_rejected(self):
        with self.assertRaises(ValueError):
            validate_path(["obc-a", "obc-a"])

    def test_blank_element_rejected(self):
        with self.assertRaises(ValueError):
            validate_path(["obc-a", "  "])

    def test_path_order_is_preserved(self):
        self.assertEqual(validate_path(NOMINAL), ("obc-a", "switch-a", "harness"))

    def test_zero_tolerated_outage_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_redundancy_management(
                CLEAN_A, CLEAN_B, DETECTION, DECISION, RECONFIG, 0.0
            )


class TopologyTests(unittest.TestCase):
    def test_shared_element_is_found(self):
        self.assertEqual(shared_elements(NOMINAL, REDUNDANT), ("harness",))

    def test_disjoint_paths_share_nothing(self):
        self.assertEqual(shared_elements(CLEAN_A, CLEAN_B), ())

    def test_shared_elements_follow_nominal_order(self):
        self.assertEqual(
            shared_elements(["a", "b", "c"], ["c", "b"]), ("b", "c")
        )

    def test_an_unaccepted_shared_element_is_a_single_point_of_failure(self):
        self.assertEqual(single_points_of_failure(NOMINAL, REDUNDANT), ("harness",))

    def test_an_accepted_shared_element_is_not_counted(self):
        self.assertEqual(
            single_points_of_failure(NOMINAL, REDUNDANT, ["harness"]), ()
        )

    def test_accepting_an_element_that_is_not_shared_is_an_input_error(self):
        with self.assertRaises(ValueError):
            single_points_of_failure(NOMINAL, REDUNDANT, ["switch-a"])

    def test_a_bare_string_is_not_a_tolerated_list(self):
        with self.assertRaises(ValueError):
            single_points_of_failure(NOMINAL, REDUNDANT, "harness")


class TimingTests(unittest.TestCase):
    def test_switchover_is_the_sum_of_three_terms(self):
        self.assertAlmostEqual(
            switchover_time(DETECTION, DECISION, RECONFIG), 1.0, places=9
        )

    def test_detection_budget_is_what_the_other_two_leave(self):
        self.assertAlmostEqual(
            detection_budget(DECISION, RECONFIG, MAX_OUTAGE), 1.5, places=9
        )

    def test_no_detection_budget_when_the_other_two_overrun(self):
        self.assertIsNone(detection_budget(1.5, 1.0, MAX_OUTAGE))

    def test_a_budget_of_exactly_zero_is_still_a_budget(self):
        self.assertAlmostEqual(detection_budget(1.0, 1.0, MAX_OUTAGE), 0.0, places=9)

    def test_the_stated_detection_budget_meets_the_outage(self):
        budget = detection_budget(DECISION, RECONFIG, MAX_OUTAGE)
        result = assess_redundancy_management(
            CLEAN_A, CLEAN_B, budget, DECISION, RECONFIG, MAX_OUTAGE
        )
        self.assertTrue(result["fast_enough"])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_arrangement_is_effective(self):
        result = assess_redundancy_management(
            CLEAN_A, CLEAN_B, DETECTION, DECISION, RECONFIG, MAX_OUTAGE
        )
        self.assertEqual(result["verdict"], EFFECTIVE)
        self.assertEqual(result["findings"], [])

    def test_a_shared_element_dominates_the_verdict(self):
        result = assess_redundancy_management(
            NOMINAL, REDUNDANT, DETECTION, DECISION, RECONFIG, MAX_OUTAGE
        )
        self.assertEqual(result["verdict"], SINGLE_POINT_OF_FAILURE)
        self.assertFalse(result["single_failure_survivable"])

    def test_accepting_the_shared_element_restores_the_verdict(self):
        result = assess_redundancy_management(
            NOMINAL, REDUNDANT, DETECTION, DECISION, RECONFIG, MAX_OUTAGE, ["harness"]
        )
        self.assertEqual(result["verdict"], EFFECTIVE)
        self.assertEqual(result["tolerated_shared"], ["harness"])

    def test_a_slow_switchover_is_reported(self):
        result = assess_redundancy_management(
            CLEAN_A, CLEAN_B, 5.0, DECISION, RECONFIG, MAX_OUTAGE
        )
        self.assertEqual(result["verdict"], TOO_SLOW)
        self.assertTrue(any("detection must come down to" in f for f in result["findings"]))

    def test_a_switchover_exactly_on_the_bound_is_fast_enough(self):
        result = assess_redundancy_management(
            CLEAN_A, CLEAN_B, 1.5, DECISION, RECONFIG, MAX_OUTAGE
        )
        self.assertAlmostEqual(result["switchover_time_s"], result["max_outage_s"], places=9)
        self.assertEqual(result["verdict"], EFFECTIVE)

    def test_an_unreachable_outage_says_detection_cannot_save_it(self):
        result = assess_redundancy_management(
            CLEAN_A, CLEAN_B, 0.1, 1.5, 1.0, MAX_OUTAGE
        )
        self.assertTrue(any("faster detection cannot meet it" in f for f in result["findings"]))
        self.assertIsNone(result["detection_budget_s"])

    def test_identical_paths_are_named_as_such(self):
        result = assess_redundancy_management(
            CLEAN_A, list(reversed(CLEAN_A)), DETECTION, DECISION, RECONFIG, MAX_OUTAGE,
            CLEAN_A,
        )
        self.assertTrue(result["paths_identical"])
        self.assertTrue(any("second name rather than" in f for f in result["findings"]))

    def test_outage_margin_is_reported(self):
        result = assess_redundancy_management(
            CLEAN_A, CLEAN_B, DETECTION, DECISION, RECONFIG, MAX_OUTAGE
        )
        self.assertAlmostEqual(result["outage_margin_s"], 1.0, places=9)

    def test_both_failures_are_reported_together(self):
        result = assess_redundancy_management(
            NOMINAL, REDUNDANT, 5.0, DECISION, RECONFIG, MAX_OUTAGE
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_topology_outranks_timing_in_the_verdict(self):
        result = assess_redundancy_management(
            NOMINAL, REDUNDANT, 5.0, DECISION, RECONFIG, MAX_OUTAGE
        )
        self.assertEqual(result["verdict"], SINGLE_POINT_OF_FAILURE)
        self.assertFalse(result["fast_enough"])

    def test_the_shared_element_list_is_carried_in_the_result(self):
        result = assess_redundancy_management(
            NOMINAL, REDUNDANT, DETECTION, DECISION, RECONFIG, MAX_OUTAGE, ["harness"]
        )
        self.assertEqual(result["shared_elements"], ["harness"])
        self.assertEqual(result["single_points_of_failure"], [])

    def test_a_bad_reconfiguration_time_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_redundancy_management(
                CLEAN_A, CLEAN_B, DETECTION, DECISION, -1.0, MAX_OUTAGE
            )


if __name__ == "__main__":
    unittest.main()
