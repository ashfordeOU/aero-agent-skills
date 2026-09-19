#!/usr/bin/env python3
"""Contract test for the mechanism kinematic performance case (offline)."""

import copy
import math
import unittest

from e3301_system_mechanism_functional_performance_logic import (
    DEFAULT_PERFORMANCE_POLICY,
    PROFILE_TRAPEZOIDAL,
    PROFILE_TRIANGULAR,
    assess_functional_performance,
    function_duration_s,
    minimum_transition_time_s,
    peak_velocity,
    profile_kind,
    saturation_travel,
    time_margin,
    transition_compliance,
    validate_performance_policy,
    validate_transition,
)


def transition(
    identifier,
    travel=1.5708,
    allowed_time_s=30.0,
    max_velocity=0.10,
    max_acceleration=0.05,
    dwell_s=0.0,
    position_tolerance=0.001,
    position_error=0.0004,
):
    record = {
        "id": identifier,
        "travel": travel,
        "allowed_time_s": allowed_time_s,
        "max_velocity": max_velocity,
        "max_acceleration": max_acceleration,
        "dwell_s": dwell_s,
    }
    if position_tolerance is not None:
        record["position_tolerance"] = position_tolerance
    if position_error is not None:
        record["position_error"] = position_error
    return record


GOOD_CASE = {
    "transitions": [
        transition("stow-to-deploy", travel=1.5708, allowed_time_s=40.0),
        transition("deploy-to-track", travel=0.10, allowed_time_s=10.0, dwell_s=2.0),
    ],
    "function_time_budget_s": 120.0,
}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_performance_policy(DEFAULT_PERFORMANCE_POLICY),
            DEFAULT_PERFORMANCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_performance_policy("default")

    def test_margin_of_one_or_more_rejected(self):
        broken = dict(DEFAULT_PERFORMANCE_POLICY)
        broken["required_time_margin"] = 1.0
        with self.assertRaises(ValueError):
            validate_performance_policy(broken)

    def test_negative_margin_rejected(self):
        broken = dict(DEFAULT_PERFORMANCE_POLICY)
        broken["required_time_margin"] = -0.1
        with self.assertRaises(ValueError):
            validate_performance_policy(broken)

    def test_non_boolean_tolerance_flag_rejected(self):
        broken = dict(DEFAULT_PERFORMANCE_POLICY)
        broken["require_position_tolerance"] = "yes"
        with self.assertRaises(ValueError):
            validate_performance_policy(broken)


class ProfileTests(unittest.TestCase):
    def test_saturation_travel_is_velocity_squared_over_acceleration(self):
        self.assertAlmostEqual(saturation_travel(0.10, 0.05), 0.2, places=12)

    def test_a_short_travel_stays_triangular(self):
        self.assertEqual(profile_kind(0.05, 0.10, 0.05), PROFILE_TRIANGULAR)

    def test_a_long_travel_saturates_the_velocity_limit(self):
        self.assertEqual(profile_kind(1.5708, 0.10, 0.05), PROFILE_TRAPEZOIDAL)

    def test_a_travel_exactly_at_saturation_is_read_as_trapezoidal(self):
        threshold = saturation_travel(0.10, 0.05)
        self.assertEqual(profile_kind(threshold, 0.10, 0.05), PROFILE_TRAPEZOIDAL)

    def test_zero_travel_rejected(self):
        with self.assertRaises(ValueError):
            profile_kind(0.0, 0.10, 0.05)

    def test_zero_acceleration_limit_rejected(self):
        with self.assertRaises(ValueError):
            saturation_travel(0.10, 0.0)


class PeakVelocityTests(unittest.TestCase):
    def test_a_triangular_profile_never_reaches_the_limit(self):
        reached = peak_velocity(0.05, 0.10, 0.05)
        self.assertAlmostEqual(reached, math.sqrt(0.05 * 0.05), places=12)
        self.assertLess(reached, 0.10)

    def test_a_trapezoidal_profile_sits_at_the_limit(self):
        self.assertAlmostEqual(peak_velocity(1.5708, 0.10, 0.05), 0.10, places=12)

    def test_at_saturation_the_peak_equals_the_limit(self):
        threshold = saturation_travel(0.10, 0.05)
        self.assertAlmostEqual(peak_velocity(threshold, 0.10, 0.05), 0.10, places=9)

    def test_negative_travel_rejected(self):
        with self.assertRaises(ValueError):
            peak_velocity(-0.1, 0.10, 0.05)


class TransitionTimeTests(unittest.TestCase):
    def test_triangular_time_is_twice_the_root_of_travel_over_acceleration(self):
        self.assertAlmostEqual(
            minimum_transition_time_s(0.05, 0.10, 0.05),
            2.0 * math.sqrt(0.05 / 0.05),
            places=12,
        )

    def test_trapezoidal_time_adds_the_ramp_to_the_coast(self):
        self.assertAlmostEqual(
            minimum_transition_time_s(1.0, 0.10, 0.05),
            1.0 / 0.10 + 0.10 / 0.05,
            places=12,
        )

    def test_both_expressions_agree_at_the_saturation_travel(self):
        # The branch boundary is where the two closed forms must meet;
        # they agree to within representation error, never exactly.
        threshold = saturation_travel(0.10, 0.05)
        trapezoid = threshold / 0.10 + 0.10 / 0.05
        triangle = 2.0 * math.sqrt(threshold / 0.05)
        self.assertAlmostEqual(trapezoid, triangle, places=9)
        self.assertAlmostEqual(
            minimum_transition_time_s(threshold, 0.10, 0.05), trapezoid, places=9
        )

    def test_a_longer_travel_takes_longer(self):
        self.assertGreater(
            minimum_transition_time_s(2.0, 0.10, 0.05),
            minimum_transition_time_s(1.0, 0.10, 0.05),
        )

    def test_a_higher_acceleration_limit_never_takes_longer(self):
        slow = minimum_transition_time_s(1.0, 0.10, 0.05)
        quick = minimum_transition_time_s(1.0, 0.10, 0.20)
        self.assertGreater(slow, quick)

    def test_zero_velocity_limit_rejected(self):
        with self.assertRaises(ValueError):
            minimum_transition_time_s(1.0, 0.0, 0.05)


class TimeMarginTests(unittest.TestCase):
    def test_half_the_window_used_leaves_half_the_margin(self):
        self.assertAlmostEqual(time_margin(20.0, 10.0), 0.5, places=12)

    def test_a_full_window_leaves_no_margin(self):
        self.assertAlmostEqual(time_margin(20.0, 20.0), 0.0, places=12)

    def test_an_overrun_gives_a_negative_margin(self):
        self.assertLess(time_margin(10.0, 20.0), 0.0)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            time_margin(0.0, 1.0)


class TransitionValidationTests(unittest.TestCase):
    def test_a_complete_transition_normalises(self):
        record = validate_transition(transition("a"))
        self.assertEqual(record["id"], "a")
        self.assertAlmostEqual(record["dwell_s"], 0.0, places=12)

    def test_non_mapping_transition_rejected(self):
        with self.assertRaises(ValueError):
            validate_transition("a")

    def test_blank_transition_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_transition(transition("  "))

    def test_negative_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_transition(transition("a", dwell_s=-1.0))

    def test_a_signed_position_error_is_taken_as_a_magnitude(self):
        record = validate_transition(transition("a", position_error=-0.0004))
        self.assertAlmostEqual(record["position_error"], 0.0004, places=12)


class TransitionComplianceTests(unittest.TestCase):
    def test_a_comfortable_position_change_is_compliant(self):
        result = transition_compliance(transition("a", allowed_time_s=40.0))
        self.assertTrue(result["compliant"])
        self.assertTrue(result["feasible"])
        self.assertEqual(result["findings"], [])

    def test_an_impossible_window_is_reported(self):
        result = transition_compliance(transition("a", allowed_time_s=5.0))
        self.assertFalse(result["feasible"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("is allowed" in f for f in result["findings"]))

    def test_a_feasible_change_with_too_little_margin_is_reported(self):
        minimum = minimum_transition_time_s(1.5708, 0.10, 0.05)
        result = transition_compliance(
            transition("a", allowed_time_s=minimum * 1.02)
        )
        self.assertTrue(result["feasible"])
        self.assertFalse(result["time_margin_met"])
        self.assertFalse(result["compliant"])

    def test_a_margin_exactly_on_the_requirement_is_accepted(self):
        minimum = minimum_transition_time_s(1.5708, 0.10, 0.05)
        allowed = minimum / (1.0 - DEFAULT_PERFORMANCE_POLICY["required_time_margin"])
        result = transition_compliance(transition("a", allowed_time_s=allowed))
        self.assertAlmostEqual(result["time_margin"], 0.10, places=9)
        self.assertTrue(result["time_margin_met"])

    def test_an_end_position_outside_tolerance_fails(self):
        result = transition_compliance(
            transition("a", allowed_time_s=40.0, position_error=0.002)
        )
        self.assertFalse(result["position_within_tolerance"])
        self.assertFalse(result["compliant"])

    def test_an_end_position_exactly_on_tolerance_passes(self):
        result = transition_compliance(
            transition("a", allowed_time_s=40.0, position_tolerance=0.001,
                       position_error=0.001)
        )
        self.assertTrue(result["position_within_tolerance"])

    def test_a_stated_tolerance_with_no_measurement_is_not_demonstrated(self):
        result = transition_compliance(
            transition("a", allowed_time_s=40.0, position_error=None)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no demonstrated" in f for f in result["findings"]))

    def test_a_missing_tolerance_is_reported_when_the_policy_demands_one(self):
        result = transition_compliance(
            transition("a", allowed_time_s=40.0, position_tolerance=None,
                       position_error=None)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("states no end-position" in f for f in result["findings"]))

    def test_the_policy_can_waive_the_tolerance_requirement(self):
        policy = dict(DEFAULT_PERFORMANCE_POLICY)
        policy["require_position_tolerance"] = False
        result = transition_compliance(
            transition("a", allowed_time_s=40.0, position_tolerance=None,
                       position_error=None),
            policy,
        )
        self.assertTrue(result["compliant"])

    def test_the_profile_is_reported_with_the_result(self):
        result = transition_compliance(transition("a", allowed_time_s=40.0))
        self.assertEqual(result["profile"], PROFILE_TRAPEZOIDAL)
        self.assertTrue(result["velocity_limit_reached"])


class FunctionDurationTests(unittest.TestCase):
    def test_duration_sums_the_changes_and_the_dwells(self):
        total = function_duration_s(
            [transition("a", travel=1.0, dwell_s=3.0),
             transition("b", travel=1.0, dwell_s=2.0)]
        )
        single = minimum_transition_time_s(1.0, 0.10, 0.05)
        self.assertAlmostEqual(total, 2.0 * single + 5.0, places=9)

    def test_empty_transition_list_rejected(self):
        with self.assertRaises(ValueError):
            function_duration_s([])


class AssessmentTests(unittest.TestCase):
    def test_good_case_is_demonstrated(self):
        result = assess_functional_performance(GOOD_CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "performance-demonstrated")
        self.assertEqual(result["failing_transitions"], [])

    def test_a_failing_change_names_itself(self):
        case = copy.deepcopy(GOOD_CASE)
        case["transitions"][0]["allowed_time_s"] = 5.0
        result = assess_functional_performance(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["failing_transitions"], ["stow-to-deploy"])
        self.assertEqual(result["verdict"], "position-change-not-demonstrated")

    def test_a_tight_function_budget_is_reported(self):
        case = copy.deepcopy(GOOD_CASE)
        case["function_time_budget_s"] = 10.0
        result = assess_functional_performance(case)
        self.assertFalse(result["function_budget_met"])
        self.assertEqual(result["verdict"], "function-budget-exceeded")

    def test_without_a_budget_the_changes_still_grade(self):
        case = copy.deepcopy(GOOD_CASE)
        del case["function_time_budget_s"]
        result = assess_functional_performance(case)
        self.assertIsNone(result["function_budget_met"])
        self.assertTrue(result["compliant"])

    def test_duplicate_transition_id_rejected(self):
        case = copy.deepcopy(GOOD_CASE)
        case["transitions"][1]["id"] = "stow-to-deploy"
        with self.assertRaises(ValueError):
            assess_functional_performance(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_functional_performance("deploy")

    def test_empty_transitions_rejected(self):
        with self.assertRaises(ValueError):
            assess_functional_performance({"transitions": []})


if __name__ == "__main__":
    unittest.main()
