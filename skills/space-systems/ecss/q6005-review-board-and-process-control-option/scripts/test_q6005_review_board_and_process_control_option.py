#!/usr/bin/env python3
"""Gate 3 contract test for q6005-review-board-and-process-control-option.

Offline, stdlib unittest. Exercises the monitoring window validation, the
window statistics, the control limits drawn from the line's own history, the
out-of-control and drift detection, the review board composition and currency
check and the three-way standing of ECSS-Q-ST-60-05C clause 12.2.2 as
paraphrased in the logic module. Yields, means and limits are floats that
land on a bound exactly in the worked cases, so every numeric bound is
asserted with assertAlmostEqual rather than a strict inequality that libm
could round either way between build host and CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_review_board_and_process_control_option_logic import (  # noqa: E402
    BOARD_QUORUM,
    MIN_MEAN_YIELD,
    MIN_WINDOW_LOTS,
    REQUIRED_BOARD_ROLES,
    RUN_RULE_LENGTH,
    assess_line_monitoring,
    board_status,
    control_limits,
    monitoring_statistics,
    out_of_control_lots,
    run_rule_violations,
    validate_yields,
)

# Twelve lots alternating either side of a settled 0.94 centre.
STABLE_WINDOW = [0.95, 0.93] * 6

# The same line with one collapsed lot at the end.
COLLAPSED_WINDOW = STABLE_WINDOW + [0.60]

# Inside its limits on every point, but walking off centre for seven lots.
DRIFTING_WINDOW = [0.99] * 5 + [0.90] * 7


def board(**overrides):
    base = {
        "roles": list(REQUIRED_BOARD_ROLES),
        "lots_since_last_review": 2,
    }
    base.update(overrides)
    return base


class WindowValidationTests(unittest.TestCase):
    def test_stable_window_validates(self):
        self.assertEqual(len(validate_yields(STABLE_WINDOW)), 12)

    def test_single_lot_window_has_no_spread_and_is_refused(self):
        with self.assertRaises(ValueError):
            validate_yields([0.95])

    def test_string_is_not_a_window(self):
        with self.assertRaises(ValueError):
            validate_yields("0.95,0.93")

    def test_yield_outside_zero_to_one_is_refused(self):
        for bad in ([0.9, 1.4], [0.9, -0.1]):
            with self.assertRaises(ValueError):
                validate_yields(bad)

    def test_boolean_yield_is_refused(self):
        with self.assertRaises(ValueError):
            validate_yields([0.9, True])

    def test_integer_yields_are_accepted_as_fractions(self):
        self.assertEqual(validate_yields([1, 0]), [1.0, 0.0])


class StatisticsTests(unittest.TestCase):
    def test_mean_of_the_stable_window(self):
        self.assertAlmostEqual(monitoring_statistics(STABLE_WINDOW)["mean_yield"], 0.94, places=9)

    def test_window_size_is_the_lot_count(self):
        self.assertEqual(monitoring_statistics(STABLE_WINDOW)["lots"], 12)

    def test_extremes_are_reported(self):
        stats = monitoring_statistics(COLLAPSED_WINDOW)
        self.assertAlmostEqual(stats["minimum"], 0.60, places=9)
        self.assertAlmostEqual(stats["maximum"], 0.95, places=9)

    def test_flat_line_has_no_spread(self):
        self.assertAlmostEqual(monitoring_statistics([0.9] * 8)["stdev"], 0.0, places=9)


class ControlLimitTests(unittest.TestCase):
    def test_limits_sit_either_side_of_the_window_mean(self):
        limits = control_limits(STABLE_WINDOW)
        self.assertAlmostEqual(
            limits["upper_control_limit"] - limits["mean_yield"],
            limits["mean_yield"] - limits["lower_control_limit"],
            places=9,
        )

    def test_upper_limit_is_clamped_to_a_reachable_yield(self):
        limits = control_limits(DRIFTING_WINDOW)
        self.assertAlmostEqual(limits["upper_control_limit"], 1.0, places=9)

    def test_flat_line_collapses_both_limits_onto_the_mean(self):
        limits = control_limits([0.9] * 8)
        self.assertAlmostEqual(limits["lower_control_limit"], 0.9, places=9)
        self.assertAlmostEqual(limits["upper_control_limit"], 0.9, places=9)

    def test_non_positive_sigma_multiplier_is_refused(self):
        for bad in (0, -3):
            with self.assertRaises(ValueError):
                control_limits(STABLE_WINDOW, bad)


class OutOfControlTests(unittest.TestCase):
    def test_stable_window_has_no_lot_outside_its_limits(self):
        self.assertEqual(out_of_control_lots(STABLE_WINDOW), [])

    def test_collapsed_lot_is_found_at_its_position(self):
        self.assertEqual(out_of_control_lots(COLLAPSED_WINDOW), [12])

    def test_flat_line_reports_nothing_outside_zero_width_limits(self):
        self.assertEqual(out_of_control_lots([0.9] * 8), [])

    def test_tighter_limits_catch_more_lots(self):
        self.assertGreater(len(out_of_control_lots(COLLAPSED_WINDOW, 1.0)), 0)


class DriftTests(unittest.TestCase):
    def test_alternating_window_never_runs(self):
        self.assertEqual(run_rule_violations(STABLE_WINDOW), [])

    def test_seven_lots_below_the_mean_are_a_drift(self):
        self.assertEqual(run_rule_violations(DRIFTING_WINDOW), [5])

    def test_drifting_window_is_still_inside_its_control_limits(self):
        self.assertEqual(out_of_control_lots(DRIFTING_WINDOW), [])

    def test_a_shorter_run_rule_catches_the_earlier_run_too(self):
        self.assertEqual(run_rule_violations(DRIFTING_WINDOW, 5), [0, 5])

    def test_run_length_below_two_is_refused(self):
        with self.assertRaises(ValueError):
            run_rule_violations(STABLE_WINDOW, 1)

    def test_default_run_rule_length_is_seven(self):
        self.assertEqual(RUN_RULE_LENGTH, 7)


class BoardTests(unittest.TestCase):
    def test_complete_board_is_quorate_and_current(self):
        status = board_status(board())
        self.assertTrue(status["quorate"])
        self.assertTrue(status["has_customer_member"])
        self.assertFalse(status["review_overdue"])

    def test_absent_board_normalises_to_an_unconvened_one(self):
        status = board_status(None)
        self.assertFalse(status["convened"])
        self.assertEqual(status["roles_present"], [])

    def test_board_short_of_quorum_is_reported_with_its_gaps(self):
        status = board_status(board(roles=list(REQUIRED_BOARD_ROLES[:2])))
        self.assertFalse(status["quorate"])
        self.assertEqual(len(status["roles_missing"]), 2)

    def test_quorum_is_three_required_roles(self):
        self.assertEqual(BOARD_QUORUM, 3)
        self.assertTrue(board_status(board(roles=list(REQUIRED_BOARD_ROLES[:3])))["quorate"])

    def test_review_past_the_interval_is_overdue(self):
        self.assertTrue(board_status(board(lots_since_last_review=9))["review_overdue"])

    def test_review_exactly_at_the_interval_is_not_overdue(self):
        status = board_status(board(lots_since_last_review=6, max_lots_between_reviews=6))
        self.assertFalse(status["review_overdue"])

    def test_role_names_are_matched_case_and_separator_insensitively(self):
        roles = [r.replace("-", " ").upper() for r in REQUIRED_BOARD_ROLES]
        self.assertEqual(len(board_status(board(roles=roles))["roles_present"]), 4)

    def test_negative_lots_since_review_is_refused(self):
        with self.assertRaises(ValueError):
            board_status(board(lots_since_last_review=-1))

    def test_non_mapping_board_is_refused(self):
        with self.assertRaises(ValueError):
            board_status([("roles", [])])


class StandingTests(unittest.TestCase):
    def test_stable_monitored_line_with_a_good_board_continues(self):
        result = assess_line_monitoring({"yields": STABLE_WINDOW, "board": board()})
        self.assertEqual(result["standing"], "continue")
        self.assertTrue(result["sampling_may_be_substituted"])
        self.assertEqual(result["reversions"], [])
        self.assertEqual(result["suspensions"], [])

    def test_out_of_control_lot_reverts_the_line_to_per_lot_testing(self):
        result = assess_line_monitoring({"yields": COLLAPSED_WINDOW, "board": board()})
        self.assertEqual(result["standing"], "revert-to-lot-control")
        self.assertFalse(result["sampling_may_be_substituted"])
        self.assertEqual(result["out_of_control_lots"], [12])

    def test_drift_inside_the_limits_still_reverts_the_line(self):
        result = assess_line_monitoring({"yields": DRIFTING_WINDOW, "board": board()})
        self.assertEqual(result["standing"], "revert-to-lot-control")
        self.assertEqual(result["out_of_control_lots"], [])
        self.assertEqual(result["drift_runs"], [5])

    def test_short_window_reverts_the_line(self):
        result = assess_line_monitoring({"yields": [0.95, 0.93, 0.95], "board": board()})
        self.assertEqual(result["standing"], "revert-to-lot-control")
        self.assertTrue(any("monitoring window holds" in r for r in result["reversions"]))

    def test_mean_yield_below_the_floor_suspends_the_scheme(self):
        result = assess_line_monitoring({"yields": [0.70] * 12, "board": board()})
        self.assertEqual(result["standing"], "suspend")
        self.assertTrue(any("mean yield" in s for s in result["suspensions"]))

    def test_mean_yield_exactly_on_the_floor_does_not_suspend(self):
        result = assess_line_monitoring(
            {"yields": [MIN_MEAN_YIELD] * 12, "board": board()}
        )
        self.assertEqual(result["suspensions"], [])
        self.assertAlmostEqual(result["mean_yield"], MIN_MEAN_YIELD, places=9)

    def test_line_with_no_board_at_all_is_suspended(self):
        result = assess_line_monitoring({"yields": STABLE_WINDOW})
        self.assertEqual(result["standing"], "suspend")
        self.assertTrue(any("no technical review board" in s for s in result["suspensions"]))

    def test_board_without_the_customer_member_reverts_the_line(self):
        roles = [r for r in REQUIRED_BOARD_ROLES if r != "customer-product-assurance"]
        result = assess_line_monitoring({"yields": STABLE_WINDOW, "board": board(roles=roles)})
        self.assertEqual(result["standing"], "revert-to-lot-control")
        self.assertTrue(any("customer product assurance" in r for r in result["reversions"]))

    def test_overdue_board_review_reverts_the_line(self):
        result = assess_line_monitoring(
            {"yields": STABLE_WINDOW, "board": board(lots_since_last_review=20)}
        )
        self.assertEqual(result["standing"], "revert-to-lot-control")

    def test_default_minimum_window_is_ten_lots(self):
        self.assertEqual(MIN_WINDOW_LOTS, 10)

    def test_missing_yields_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_line_monitoring({"board": board()})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_line_monitoring([("yields", STABLE_WINDOW)])

    def test_out_of_range_minimum_mean_yield_is_refused(self):
        for bad in (0.0, 1.4):
            with self.assertRaises(ValueError):
                assess_line_monitoring({"yields": STABLE_WINDOW, "minimum_mean_yield": bad})


if __name__ == "__main__":
    unittest.main(verbosity=2)
