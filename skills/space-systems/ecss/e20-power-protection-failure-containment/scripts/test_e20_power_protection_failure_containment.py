#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.3 power protection and
failure containment.

Exercises scripts/e20_power_protection_failure_containment_logic.py
(stdlib unittest, offline). Contract: a protection device type maps to
exactly one family and an unrecognized type raises; a protection that
shares a sense element, reference, control loop, housekeeping supply or
return path with the function it protects is reported, as is one
powered from the rail it protects; the trip window is the larger of
steady-state and inrush current raised by the margin up to the fault
rating reduced by the same margin, an empty window is a sizing defect,
and bad currents or margins raise; selectivity is the upstream/
downstream trip ratio against a required minimum; the protection
response must be strictly faster than the bus ride-through time; and
the aggregated review is compliant only when every list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_power_protection_failure_containment_logic as pc  # noqa: E402


def _clean_branch():
    """A branch that satisfies every clause 5.3 check."""
    return {
        "branch_id": "PDU-BRANCH-07",
        "protections": [
            {
                "protection_id": "LCL-07",
                "protection_type": "latching_current_limiter",
                "shared_resources": ["mounting_bracket"],
                "powered_from_protected_rail": False,
            }
        ],
        "load_steady_a": 2.0,
        "inrush_peak_a": 4.0,
        "fault_rating_a": 12.0,
        "trip_setting_a": 6.0,
        "upstream_trip_a": 20.0,
        "response_time_ms": 0.5,
        "bus_ride_through_ms": 5.0,
    }


class CategorizeProtectionFunctionTest(unittest.TestCase):
    def test_latching_current_limiter_is_current_limiting(self):
        self.assertEqual(
            pc.categorize_protection_function("latching_current_limiter"),
            "current_limiting",
        )

    def test_fuse_is_current_limiting(self):
        self.assertEqual(
            pc.categorize_protection_function("fuse"), "current_limiting"
        )

    def test_undervoltage_lockout_is_voltage_limiting(self):
        self.assertEqual(
            pc.categorize_protection_function("undervoltage_lockout"),
            "voltage_limiting",
        )

    def test_thermal_foldback_is_thermal(self):
        self.assertEqual(
            pc.categorize_protection_function("thermal_foldback"), "thermal"
        )

    def test_blocking_diode_is_isolating(self):
        self.assertEqual(
            pc.categorize_protection_function("blocking_diode"), "isolating"
        )

    def test_unknown_device_raises(self):
        with self.assertRaises(ValueError):
            pc.categorize_protection_function("decorative_led")


class IndependenceFindingsTest(unittest.TestCase):
    def test_no_shared_resource_is_independent(self):
        self.assertEqual(pc.independence_findings("LCL-01", []), [])

    def test_unrelated_shared_resource_is_ignored(self):
        self.assertEqual(
            pc.independence_findings("LCL-01", ["mounting_bracket"]), []
        )

    def test_shared_sense_element_is_reported(self):
        findings = pc.independence_findings("LCL-01", ["sense_element"])
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "shared_resource_defeats_independence"
        )
        self.assertEqual(findings[0]["resource"], "sense_element")

    def test_multiple_shared_resources_are_each_reported(self):
        findings = pc.independence_findings(
            "LCL-01", ["control_loop", "voltage_reference", "paint"]
        )
        self.assertEqual(len(findings), 2)
        self.assertEqual(
            [f["resource"] for f in findings],
            ["control_loop", "voltage_reference"],
        )

    def test_duplicate_shared_resource_reported_once(self):
        findings = pc.independence_findings(
            "LCL-01", ["return_path", "return_path"]
        )
        self.assertEqual(len(findings), 1)

    def test_powered_from_protected_rail_is_reported(self):
        findings = pc.independence_findings(
            "LCL-01", [], powered_from_protected_rail=True
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "protection_powered_from_protected_rail"
        )

    def test_empty_protection_id_raises(self):
        with self.assertRaises(ValueError):
            pc.independence_findings("", ["sense_element"])


class TripThresholdWindowTest(unittest.TestCase):
    def test_window_bounds_use_inrush_and_fault_rating(self):
        low, high = pc.trip_threshold_window(2.0, 4.0, 12.0, 0.25)
        self.assertAlmostEqual(low, 5.0)
        self.assertAlmostEqual(high, 9.0)

    def test_steady_state_drives_lower_bound_when_inrush_equal(self):
        low, _ = pc.trip_threshold_window(3.0, 3.0, 20.0, 0.10)
        self.assertAlmostEqual(low, 3.3)

    def test_zero_margin_gives_raw_bounds(self):
        low, high = pc.trip_threshold_window(2.0, 5.0, 10.0, 0.0)
        self.assertAlmostEqual(low, 5.0)
        self.assertAlmostEqual(high, 10.0)

    def test_window_can_be_empty(self):
        low, high = pc.trip_threshold_window(8.0, 9.0, 10.0, 0.30)
        self.assertGreater(low, high)

    def test_negative_steady_current_raises(self):
        with self.assertRaises(ValueError):
            pc.trip_threshold_window(-1.0, 4.0, 12.0)

    def test_negative_inrush_raises(self):
        with self.assertRaises(ValueError):
            pc.trip_threshold_window(0.0, -4.0, 12.0)

    def test_inrush_below_steady_raises(self):
        with self.assertRaises(ValueError):
            pc.trip_threshold_window(5.0, 4.0, 12.0)

    def test_non_positive_fault_rating_raises(self):
        with self.assertRaises(ValueError):
            pc.trip_threshold_window(2.0, 4.0, 0.0)

    def test_margin_fraction_of_one_raises(self):
        with self.assertRaises(ValueError):
            pc.trip_threshold_window(2.0, 4.0, 12.0, 1.0)

    def test_negative_margin_fraction_raises(self):
        with self.assertRaises(ValueError):
            pc.trip_threshold_window(2.0, 4.0, 12.0, -0.1)


class CheckTripSettingTest(unittest.TestCase):
    def test_setting_inside_window_is_ok(self):
        self.assertEqual(
            pc.check_trip_setting(6.0, (5.0, 9.0)), pc.TRIP_SETTING_OK
        )

    def test_setting_on_lower_bound_is_ok(self):
        self.assertEqual(
            pc.check_trip_setting(5.0, (5.0, 9.0)), pc.TRIP_SETTING_OK
        )

    def test_setting_on_upper_bound_is_ok(self):
        self.assertEqual(
            pc.check_trip_setting(9.0, (5.0, 9.0)), pc.TRIP_SETTING_OK
        )

    def test_setting_below_window_is_reported(self):
        self.assertEqual(
            pc.check_trip_setting(4.0, (5.0, 9.0)), pc.TRIP_SETTING_BELOW_WINDOW
        )

    def test_setting_above_window_is_reported(self):
        self.assertEqual(
            pc.check_trip_setting(9.5, (5.0, 9.0)), pc.TRIP_SETTING_ABOVE_WINDOW
        )

    def test_empty_window_is_infeasible(self):
        self.assertEqual(
            pc.check_trip_setting(6.0, (9.0, 5.0)), pc.TRIP_WINDOW_INFEASIBLE
        )

    def test_non_positive_setting_raises(self):
        with self.assertRaises(ValueError):
            pc.check_trip_setting(0.0, (5.0, 9.0))


class SelectivityTest(unittest.TestCase):
    def test_ratio_is_upstream_over_downstream(self):
        self.assertAlmostEqual(pc.selectivity_ratio(6.0, 15.0), 2.5)

    def test_coordinated_pair_has_no_finding(self):
        self.assertEqual(pc.selectivity_findings("B1", 6.0, 15.0), [])

    def test_ratio_below_minimum_is_reported(self):
        findings = pc.selectivity_findings("B1", 6.0, 7.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "insufficient_trip_selectivity")
        self.assertAlmostEqual(findings[0]["ratio"], 7.0 / 6.0)

    def test_ratio_exactly_at_minimum_passes(self):
        self.assertEqual(pc.selectivity_findings("B1", 6.0, 9.0, 1.5), [])

    def test_non_positive_downstream_raises(self):
        with self.assertRaises(ValueError):
            pc.selectivity_ratio(0.0, 15.0)

    def test_non_positive_upstream_raises(self):
        with self.assertRaises(ValueError):
            pc.selectivity_ratio(6.0, -1.0)

    def test_minimum_ratio_not_above_one_raises(self):
        with self.assertRaises(ValueError):
            pc.selectivity_findings("B1", 6.0, 15.0, 1.0)


class ResponseTimeTest(unittest.TestCase):
    def test_fast_protection_has_no_finding(self):
        self.assertEqual(pc.response_time_findings("B1", 0.5, 5.0), [])

    def test_equal_times_are_reported(self):
        findings = pc.response_time_findings("B1", 5.0, 5.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "protection_slower_than_bus_ride_through"
        )

    def test_slow_protection_is_reported(self):
        self.assertEqual(len(pc.response_time_findings("B1", 9.0, 5.0)), 1)

    def test_non_positive_response_time_raises(self):
        with self.assertRaises(ValueError):
            pc.response_time_findings("B1", 0.0, 5.0)

    def test_non_positive_ride_through_raises(self):
        with self.assertRaises(ValueError):
            pc.response_time_findings("B1", 0.5, 0.0)


class ContainmentReviewTest(unittest.TestCase):
    def test_clean_branch_is_compliant(self):
        review = pc.containment_review(_clean_branch())
        self.assertTrue(pc.is_containment_compliant(review))
        self.assertEqual(review["independence"], [])
        self.assertEqual(review["threshold"], [])

    def test_shared_control_loop_breaks_compliance(self):
        branch = _clean_branch()
        branch["protections"][0]["shared_resources"] = ["control_loop"]
        review = pc.containment_review(branch)
        self.assertFalse(pc.is_containment_compliant(review))
        self.assertEqual(len(review["independence"]), 1)

    def test_low_trip_setting_is_reported_in_threshold(self):
        branch = _clean_branch()
        branch["trip_setting_a"] = 4.0
        branch["upstream_trip_a"] = 20.0
        review = pc.containment_review(branch)
        self.assertEqual(len(review["threshold"]), 1)
        self.assertEqual(
            review["threshold"][0]["issue"], "trip_setting_below_window"
        )

    def test_slow_clearing_shows_in_timing_only(self):
        branch = _clean_branch()
        branch["response_time_ms"] = 12.0
        review = pc.containment_review(branch)
        self.assertEqual(len(review["timing"]), 1)
        self.assertEqual(review["independence"], [])
        self.assertFalse(pc.is_containment_compliant(review))

    def test_unrecognized_protection_type_raises(self):
        branch = _clean_branch()
        branch["protections"][0]["protection_type"] = "decorative_led"
        with self.assertRaises(ValueError):
            pc.containment_review(branch)

    def test_review_does_not_mutate_input(self):
        branch = _clean_branch()
        snapshot = dict(branch)
        pc.containment_review(branch)
        self.assertEqual(branch, snapshot)


if __name__ == "__main__":
    unittest.main()
