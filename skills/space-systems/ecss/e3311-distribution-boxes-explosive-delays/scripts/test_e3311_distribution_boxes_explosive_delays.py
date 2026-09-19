#!/usr/bin/env python3
"""Contract test for distribution boxes and explosive delays (offline)."""

import copy
import unittest

from e3311_distribution_boxes_explosive_delays_logic import (
    DEFAULT_DISTRIBUTION_POLICY,
    MARGIN_MET,
    MARGIN_NOT_MET,
    ORDER_MET,
    ORDER_NOT_MET,
    SPREAD_MET,
    SPREAD_NOT_MET,
    TRANSFER_MEDIA,
    assess_delay_train,
    assess_distribution_box,
    branch_delivered_energy_j,
    branch_transfer_margin,
    delay_window_ms,
    plan_distribution_and_delays,
    simultaneity_spread_ms,
    validate_distribution_policy,
)

GOOD_CASE = {
    "input_energy_j": 12.0,
    "branches": [
        {"id": "b1", "medium": "detonating-cord", "threshold_energy_j": 1.0},
        {"id": "b2", "medium": "detonating-cord", "threshold_energy_j": 1.0},
        {"id": "b3", "medium": "through-bulkhead-initiator", "threshold_energy_j": 1.0},
    ],
    "branch_function_times_ms": [0.10, 0.35, 0.42],
    "delay_elements": [
        {"id": "d1", "nominal_delay_ms": 20.0, "unit_tolerance_ms": 1.0},
        {
            "id": "d2",
            "nominal_delay_ms": 80.0,
            "unit_tolerance_ms": 2.0,
            "temperature_coefficient_per_k": 0.0005,
            "temperature_excursion_k": 40.0,
        },
    ],
}

WEAK_CASE = {
    "input_energy_j": 6.0,
    "branches": [
        {"id": "b1", "medium": "detonating-cord", "threshold_energy_j": 1.0},
        {"id": "b2", "medium": "through-bulkhead-initiator", "threshold_energy_j": 2.5},
        {"id": "b3", "medium": "explosive-transfer-line", "threshold_energy_j": 1.0},
    ],
    "branch_function_times_ms": [0.10, 1.90, 0.42],
    "delay_elements": [
        {"id": "d1", "nominal_delay_ms": 20.0, "unit_tolerance_ms": 3.0},
        {"id": "d2", "nominal_delay_ms": 25.0, "unit_tolerance_ms": 3.0},
    ],
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_distribution_policy(DEFAULT_DISTRIBUTION_POLICY),
            DEFAULT_DISTRIBUTION_POLICY,
        )

    def test_policy_covers_every_transfer_medium(self):
        for medium in TRANSFER_MEDIA:
            self.assertIn(medium, DEFAULT_DISTRIBUTION_POLICY["transfer_loss_fraction"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_distribution_policy("default")

    def test_policy_missing_a_medium_rejected(self):
        broken = copy.deepcopy(DEFAULT_DISTRIBUTION_POLICY)
        del broken["transfer_loss_fraction"]["detonating-cord"]
        with self.assertRaises(ValueError):
            validate_distribution_policy(broken)

    def test_policy_loss_fraction_of_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_DISTRIBUTION_POLICY)
        broken["transfer_loss_fraction"]["detonating-cord"] = 1.0
        with self.assertRaises(ValueError):
            validate_distribution_policy(broken)

    def test_policy_with_zero_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_DISTRIBUTION_POLICY)
        broken["min_transfer_margin"] = 0.0
        with self.assertRaises(ValueError):
            validate_distribution_policy(broken)


class BranchEnergyTests(unittest.TestCase):
    def test_split_and_loss_are_both_applied(self):
        self.assertAlmostEqual(
            branch_delivered_energy_j(12.0, 3, "detonating-cord"), 3.6, places=9
        )

    def test_a_sealed_crossing_loses_more_than_a_cord(self):
        cord = branch_delivered_energy_j(12.0, 3, "detonating-cord")
        bulkhead = branch_delivered_energy_j(12.0, 3, "through-bulkhead-initiator")
        self.assertLess(bulkhead, cord)

    def test_more_branches_lower_the_delivered_energy(self):
        few = branch_delivered_energy_j(12.0, 2, "detonating-cord")
        many = branch_delivered_energy_j(12.0, 6, "detonating-cord")
        self.assertLess(many, few)

    def test_unknown_medium_rejected(self):
        with self.assertRaises(ValueError):
            branch_delivered_energy_j(12.0, 3, "string-and-hope")

    def test_fractional_branch_count_rejected(self):
        with self.assertRaises(ValueError):
            branch_delivered_energy_j(12.0, 2.5, "detonating-cord")

    def test_zero_branch_count_rejected(self):
        with self.assertRaises(ValueError):
            branch_delivered_energy_j(12.0, 0, "detonating-cord")

    def test_negative_input_energy_rejected(self):
        with self.assertRaises(ValueError):
            branch_delivered_energy_j(-12.0, 3, "detonating-cord")

    def test_margin_is_a_ratio_not_a_difference(self):
        self.assertAlmostEqual(branch_transfer_margin(3.6, 1.2), 3.0, places=9)

    def test_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            branch_transfer_margin(3.6, 0.0)


class SimultaneityTests(unittest.TestCase):
    def test_spread_is_the_earliest_to_latest_difference(self):
        self.assertAlmostEqual(
            simultaneity_spread_ms([0.10, 0.35, 0.42]), 0.32, places=9
        )

    def test_identical_times_give_zero_spread(self):
        self.assertAlmostEqual(simultaneity_spread_ms([0.2, 0.2, 0.2]), 0.0, places=12)

    def test_a_single_time_is_not_a_spread(self):
        with self.assertRaises(ValueError):
            simultaneity_spread_ms([0.2])

    def test_negative_function_time_rejected(self):
        with self.assertRaises(ValueError):
            simultaneity_spread_ms([0.2, -0.1])

    def test_non_sequence_times_rejected(self):
        with self.assertRaises(ValueError):
            simultaneity_spread_ms("0.2, 0.3")


class DelayWindowTests(unittest.TestCase):
    def test_tolerance_alone_widens_the_window_symmetrically(self):
        window = delay_window_ms(20.0, 1.0)
        self.assertAlmostEqual(window["earliest_ms"], 19.0, places=9)
        self.assertAlmostEqual(window["latest_ms"], 21.0, places=9)
        self.assertAlmostEqual(window["drift_ms"], 0.0, places=12)

    def test_temperature_drift_scales_with_the_nominal_delay(self):
        short = delay_window_ms(20.0, 0.0, 0.0005, 40.0)["drift_ms"]
        long = delay_window_ms(80.0, 0.0, 0.0005, 40.0)["drift_ms"]
        self.assertAlmostEqual(short, 0.4, places=9)
        self.assertAlmostEqual(long, 1.6, places=9)

    def test_tolerance_and_drift_stack(self):
        window = delay_window_ms(80.0, 2.0, 0.0005, 40.0)
        self.assertAlmostEqual(window["half_width_ms"], 3.6, places=9)

    def test_a_window_that_collapses_to_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            delay_window_ms(2.0, 2.0)

    def test_negative_temperature_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            delay_window_ms(20.0, 1.0, -0.0005, 40.0)

    def test_zero_nominal_delay_rejected(self):
        with self.assertRaises(ValueError):
            delay_window_ms(0.0, 1.0)


class DelayTrainTests(unittest.TestCase):
    def test_well_separated_delays_are_ordered(self):
        train = assess_delay_train(GOOD_CASE["delay_elements"])
        self.assertEqual(train["verdict"], ORDER_MET)
        self.assertEqual(train["overlaps"], [])

    def test_windows_are_returned_in_nominal_order(self):
        train = assess_delay_train(list(reversed(GOOD_CASE["delay_elements"])))
        self.assertEqual([w["id"] for w in train["windows"]], ["d1", "d2"])

    def test_nominally_ordered_delays_can_overlap_at_the_corners(self):
        train = assess_delay_train(WEAK_CASE["delay_elements"])
        self.assertEqual(train["verdict"], ORDER_NOT_MET)
        self.assertEqual(train["overlaps"][0]["earlier_id"], "d1")
        self.assertEqual(train["overlaps"][0]["later_id"], "d2")

    def test_a_gap_exactly_on_the_separation_is_ordered(self):
        events = [
            {"id": "d1", "nominal_delay_ms": 20.0, "unit_tolerance_ms": 1.0},
            {"id": "d2", "nominal_delay_ms": 27.0, "unit_tolerance_ms": 1.0},
        ]
        train = assess_delay_train(events)
        gap = train["windows"][1]["earliest_ms"] - train["windows"][0]["latest_ms"]
        self.assertAlmostEqual(gap, 5.0, places=9)
        self.assertEqual(train["verdict"], ORDER_MET)

    def test_an_event_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_delay_train([{"nominal_delay_ms": 20.0}])

    def test_an_empty_train_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_delay_train([])


class DistributionBoxTests(unittest.TestCase):
    def test_good_box_meets_the_transfer_margin(self):
        box = assess_distribution_box(GOOD_CASE)
        self.assertEqual(box["verdict"], MARGIN_MET)
        self.assertEqual(box["findings"], [])

    def test_the_weakest_branch_is_the_sealed_crossing(self):
        box = assess_distribution_box(GOOD_CASE)
        self.assertEqual(box["weakest_branch_id"], "b3")

    def test_a_branch_below_the_margin_is_reported(self):
        box = assess_distribution_box(WEAK_CASE)
        self.assertEqual(box["verdict"], MARGIN_NOT_MET)
        self.assertTrue(any("b2" in finding for finding in box["findings"]))

    def test_branch_count_comes_from_the_branch_list(self):
        self.assertEqual(assess_distribution_box(GOOD_CASE)["branch_count"], 3)

    def test_a_margin_exactly_on_the_policy_floor_passes(self):
        case = {
            "input_energy_j": 3.0,
            "branches": [
                {"id": "b1", "medium": "detonating-cord", "threshold_energy_j": 0.675},
                {"id": "b2", "medium": "detonating-cord", "threshold_energy_j": 0.675},
            ],
        }
        box = assess_distribution_box(case)
        self.assertAlmostEqual(box["weakest_transfer_margin"], 2.0, places=9)
        self.assertEqual(box["verdict"], MARGIN_MET)

    def test_an_empty_branch_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_distribution_box({"input_energy_j": 12.0, "branches": []})

    def test_a_branch_without_a_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_distribution_box(
                {
                    "input_energy_j": 12.0,
                    "branches": [{"id": "b1", "medium": "detonating-cord"}],
                }
            )

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_distribution_box("one input three outputs")


class PlanTests(unittest.TestCase):
    def test_good_case_is_acceptable(self):
        result = plan_distribution_and_delays(GOOD_CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "distribution-acceptable")
        self.assertEqual(result["simultaneity_verdict"], SPREAD_MET)
        self.assertEqual(result["delay_verdict"], ORDER_MET)

    def test_weak_case_needs_rework_on_every_axis(self):
        result = plan_distribution_and_delays(WEAK_CASE)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["box"]["verdict"], MARGIN_NOT_MET)
        self.assertEqual(result["simultaneity_verdict"], SPREAD_NOT_MET)
        self.assertEqual(result["delay_verdict"], ORDER_NOT_MET)
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_spread_exactly_on_the_allowance_passes(self):
        case = _case(GOOD_CASE, branch_function_times_ms=[0.0, 1.0, 0.5])
        result = plan_distribution_and_delays(case)
        self.assertAlmostEqual(result["simultaneity_spread_ms"], 1.0, places=9)
        self.assertEqual(result["simultaneity_verdict"], SPREAD_MET)

    def test_missing_function_times_leave_simultaneity_undemonstrated(self):
        case = _case(GOOD_CASE)
        del case["branch_function_times_ms"]
        result = plan_distribution_and_delays(case)
        self.assertEqual(result["simultaneity_verdict"], "simultaneity-not-evaluated")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("not yet demonstrated" in f for f in result["findings"]))

    def test_a_box_with_no_delays_still_reaches_a_verdict(self):
        case = _case(GOOD_CASE)
        del case["delay_elements"]
        result = plan_distribution_and_delays(case)
        self.assertEqual(result["delay_verdict"], "delay-train-not-evaluated")
        self.assertTrue(result["compliant"])

    def test_a_tighter_policy_margin_can_fail_a_passing_box(self):
        policy = copy.deepcopy(DEFAULT_DISTRIBUTION_POLICY)
        policy["min_transfer_margin"] = 6.0
        result = plan_distribution_and_delays(GOOD_CASE, policy)
        self.assertFalse(result["compliant"])

    def test_plan_rejects_an_unknown_medium(self):
        case = _case(GOOD_CASE)
        case["branches"] = copy.deepcopy(case["branches"])
        case["branches"][0]["medium"] = "hope"
        with self.assertRaises(ValueError):
            plan_distribution_and_delays(case)


if __name__ == "__main__":
    unittest.main()
