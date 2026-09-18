#!/usr/bin/env python3
"""Contract test for the switch-on inrush allowance check (offline)."""

import copy
import unittest

from e2020_switch_on_inrush_allowance_logic import (
    ADVISORY_WINDOW_USE,
    DEFAULT_INRUSH_POLICY,
    DEFAULT_TURN_ON_PROFILE,
    FINDING_EXCESS_LONGER_THAN_NEED,
    FINDING_EXCESS_OUTRUNS_TRIP,
    FINDING_EXCESS_SHORTER_THAN_NEED,
    FINDING_NO_SETTLING,
    FINDING_PEAK_ABOVE_LIMITING,
    FINDING_UNATTRIBUTED_EXCESS,
    VERDICT_ALLOWED,
    VERDICT_NOT_ALLOWED,
    assess_switch_on_inrush,
    categorize_turn_on_excess,
    charge_current_available_a,
    input_filter_charge_time_s,
    settles_below_class_current,
    validate_inrush_policy,
    validate_profile,
    validate_segment,
    verify_excess_attribution,
    verify_excess_within_trip_window,
)

NOMINAL_CASE = {
    "profile": DEFAULT_TURN_ON_PROFILE,
    "class_current_a": 1.70,
    "limiting_current_a": 2.20,
    "steady_current_a": 1.05,
    "input_filter_capacitance_f": 220.0e-6,
    "bus_voltage_v": 28.0,
    "trip_off_time_min_s": 8.0e-3,
}


def _case(**overrides):
    case = dict(copy.deepcopy(NOMINAL_CASE))
    case["profile"] = DEFAULT_TURN_ON_PROFILE
    case.update(overrides)
    return case


def _segment(label="input-filter-charge"):
    for row in DEFAULT_TURN_ON_PROFILE:
        if row["label"] == label:
            return copy.deepcopy(row)
    raise AssertionError("no such segment: %s" % label)


def _profile_with_charge(duration_s):
    charge = _segment()
    charge["duration_s"] = duration_s
    return (charge,) + tuple(copy.deepcopy(DEFAULT_TURN_ON_PROFILE[1:]))


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_inrush_policy(DEFAULT_INRUSH_POLICY), DEFAULT_INRUSH_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_inrush_policy(1.2)

    def test_margin_below_one_rejected(self):
        policy = dict(DEFAULT_INRUSH_POLICY)
        policy["trip_off_time_margin"] = 0.95
        with self.assertRaises(ValueError):
            validate_inrush_policy(policy)

    def test_attribution_tolerance_at_unity_rejected(self):
        policy = dict(DEFAULT_INRUSH_POLICY)
        policy["attribution_tolerance"] = 1.0
        with self.assertRaises(ValueError):
            validate_inrush_policy(policy)

    def test_zero_attribution_tolerance_rejected(self):
        policy = dict(DEFAULT_INRUSH_POLICY)
        policy["attribution_tolerance"] = 0.0
        with self.assertRaises(ValueError):
            validate_inrush_policy(policy)

    def test_advisory_fraction_above_unity_rejected(self):
        policy = dict(DEFAULT_INRUSH_POLICY)
        policy["window_advisory_fraction"] = 1.3
        with self.assertRaises(ValueError):
            validate_inrush_policy(policy)


class SegmentTests(unittest.TestCase):
    def test_default_profile_validates(self):
        rows = validate_profile(DEFAULT_TURN_ON_PROFILE)
        self.assertEqual(len(rows), len(DEFAULT_TURN_ON_PROFILE))

    def test_segment_missing_a_field_rejected(self):
        row = _segment()
        del row["cause"]
        with self.assertRaises(ValueError):
            validate_segment(row)

    def test_unknown_cause_rejected(self):
        row = _segment()
        row["cause"] = "because-it-always-did"
        with self.assertRaises(ValueError):
            validate_segment(row)

    def test_zero_duration_rejected(self):
        row = _segment()
        row["duration_s"] = 0.0
        with self.assertRaises(ValueError):
            validate_segment(row)

    def test_negative_current_rejected(self):
        row = _segment()
        row["current_a"] = -0.1
        with self.assertRaises(ValueError):
            validate_segment(row)

    def test_blank_segment_label_rejected(self):
        row = _segment()
        row["label"] = "  "
        with self.assertRaises(ValueError):
            validate_segment(row)

    def test_repeated_segment_label_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([_segment(), _segment()])

    def test_empty_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([])


class ChargeTests(unittest.TestCase):
    def test_available_current_is_the_difference(self):
        self.assertAlmostEqual(charge_current_available_a(2.20, 1.05), 1.15, places=12)

    def test_a_steady_load_equal_to_the_limiting_current_is_rejected(self):
        with self.assertRaises(ValueError):
            charge_current_available_a(2.20, 2.20)

    def test_a_steady_load_above_the_limiting_current_is_rejected(self):
        with self.assertRaises(ValueError):
            charge_current_available_a(2.20, 2.50)

    def test_charge_uses_the_leftover_current_not_the_limiting_current(self):
        leftover = input_filter_charge_time_s(220.0e-6, 28.0, 2.20, 1.05)
        naive = 220.0e-6 * 28.0 / 2.20
        self.assertGreater(leftover, naive)

    def test_charge_time_is_linear_in_capacitance(self):
        one = input_filter_charge_time_s(220.0e-6, 28.0, 2.20, 1.05)
        two = input_filter_charge_time_s(440.0e-6, 28.0, 2.20, 1.05)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_zero_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            input_filter_charge_time_s(220.0e-6, 0.0, 2.20, 1.05)


class GroupingTests(unittest.TestCase):
    def test_only_the_filter_segment_sits_above_the_class_current(self):
        grouped = categorize_turn_on_excess(DEFAULT_TURN_ON_PROFILE, 1.70)
        self.assertEqual(len(grouped["excess_segments"]), 1)
        self.assertEqual(grouped["excess_segments"][0]["label"], "input-filter-charge")

    def test_attributed_duration_is_the_filter_segment_duration(self):
        grouped = categorize_turn_on_excess(DEFAULT_TURN_ON_PROFILE, 1.70)
        self.assertAlmostEqual(grouped["attributed_duration_s"], 5.5e-3, places=12)

    def test_a_load_segment_above_the_class_current_is_unattributed(self):
        profile = tuple(copy.deepcopy(DEFAULT_TURN_ON_PROFILE)) + (
            {
                "label": "late-enable",
                "cause": "load-operation",
                "current_a": 1.90,
                "duration_s": 2.0e-3,
            },
        )
        grouped = categorize_turn_on_excess(profile, 1.70)
        self.assertEqual(len(grouped["unattributed_segments"]), 1)
        self.assertAlmostEqual(grouped["total_excess_duration_s"], 7.5e-3, places=12)

    def test_peak_current_is_the_largest_declared(self):
        grouped = categorize_turn_on_excess(DEFAULT_TURN_ON_PROFILE, 1.70)
        self.assertAlmostEqual(grouped["peak_current_a"], 2.20, places=12)

    def test_a_profile_wholly_below_the_class_current_has_no_excess(self):
        grouped = categorize_turn_on_excess(DEFAULT_TURN_ON_PROFILE, 3.00)
        self.assertEqual(grouped["excess_segments"], ())
        self.assertAlmostEqual(grouped["total_excess_duration_s"], 0.0, places=15)


class SettlingTests(unittest.TestCase):
    def test_nominal_profile_settles_below_the_class_current(self):
        self.assertTrue(settles_below_class_current(DEFAULT_TURN_ON_PROFILE, 1.70))

    def test_a_profile_ending_above_the_class_current_does_not_settle(self):
        profile = list(copy.deepcopy(DEFAULT_TURN_ON_PROFILE))
        profile[-1]["current_a"] = 1.80
        self.assertFalse(settles_below_class_current(profile, 1.70))

    def test_a_profile_ending_on_the_class_current_does_not_settle(self):
        profile = list(copy.deepcopy(DEFAULT_TURN_ON_PROFILE))
        profile[-1]["current_a"] = 1.70
        self.assertFalse(settles_below_class_current(profile, 1.70))


class TripWindowTests(unittest.TestCase):
    def test_required_time_is_the_excess_times_the_margin(self):
        window = verify_excess_within_trip_window(5.5e-3, 8.0e-3, 1.20)
        self.assertAlmostEqual(window["required_time_s"], 6.6e-3, places=12)

    def test_an_excess_exactly_on_the_delay_is_inside_it(self):
        window = verify_excess_within_trip_window(8.0e-3, 8.0e-3, 1.0)
        self.assertAlmostEqual(window["slack_s"], 0.0, places=12)
        self.assertTrue(window["within_trip_window"])

    def test_window_usage_is_the_excess_over_the_delay(self):
        window = verify_excess_within_trip_window(5.5e-3, 8.0e-3, 1.20)
        self.assertAlmostEqual(window["window_usage"], 5.5 / 8.0, places=9)

    def test_window_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            verify_excess_within_trip_window(5.5e-3, 8.0e-3, 0.9)


class AttributionTests(unittest.TestCase):
    def test_nominal_declared_excess_matches_what_the_filter_needs(self):
        needed = input_filter_charge_time_s(220.0e-6, 28.0, 2.20, 1.05)
        result = verify_excess_attribution(5.5e-3, needed, 0.15)
        self.assertTrue(result["not_shorter_than_needed"])
        self.assertTrue(result["not_longer_than_needed"])

    def test_an_excess_far_shorter_than_the_charge_is_flagged(self):
        needed = input_filter_charge_time_s(220.0e-6, 28.0, 2.20, 1.05)
        result = verify_excess_attribution(3.0e-3, needed, 0.15)
        self.assertFalse(result["not_shorter_than_needed"])

    def test_an_excess_far_longer_than_the_charge_is_flagged(self):
        needed = input_filter_charge_time_s(220.0e-6, 28.0, 2.20, 1.05)
        result = verify_excess_attribution(6.5e-3, needed, 0.15)
        self.assertFalse(result["not_longer_than_needed"])

    def test_an_attribution_tolerance_at_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_excess_attribution(5.5e-3, 5.0e-3, 1.0)


class AssessmentTests(unittest.TestCase):
    def test_nominal_case_is_compliant_and_quiet(self):
        result = assess_switch_on_inrush(NOMINAL_CASE)
        self.assertEqual(result["verdict"], VERDICT_ALLOWED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_nominal_case_reports_the_current_left_for_the_filter(self):
        result = assess_switch_on_inrush(NOMINAL_CASE)
        self.assertAlmostEqual(result["charge_current_available_a"], 1.15, places=12)
        self.assertAlmostEqual(
            result["charge_time_s"], 220.0e-6 * 28.0 / 1.15, places=12
        )

    def test_a_load_segment_above_the_class_current_is_a_finding(self):
        profile = tuple(copy.deepcopy(DEFAULT_TURN_ON_PROFILE)) + (
            {
                "label": "late-enable",
                "cause": "load-operation",
                "current_a": 1.90,
                "duration_s": 2.0e-3,
            },
        )
        result = assess_switch_on_inrush(_case(profile=profile))
        self.assertEqual(result["verdict"], VERDICT_NOT_ALLOWED)
        self.assertTrue(
            any(FINDING_UNATTRIBUTED_EXCESS in f for f in result["findings"])
        )

    def test_a_peak_above_the_limiting_current_is_a_finding(self):
        profile = list(copy.deepcopy(DEFAULT_TURN_ON_PROFILE))
        profile[0]["current_a"] = 2.50
        result = assess_switch_on_inrush(_case(profile=profile))
        self.assertTrue(
            any(FINDING_PEAK_ABOVE_LIMITING in f for f in result["findings"])
        )

    def test_an_excess_that_outruns_the_delay_is_a_finding_on_its_own(self):
        result = assess_switch_on_inrush(
            _case(
                input_filter_capacitance_f=300.0e-6,
                profile=_profile_with_charge(7.3e-3),
            )
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertTrue(
            any(FINDING_EXCESS_OUTRUNS_TRIP in f for f in result["findings"])
        )

    def test_an_excess_longer_than_the_filter_needs_is_a_finding_on_its_own(self):
        result = assess_switch_on_inrush(_case(profile=_profile_with_charge(6.5e-3)))
        self.assertEqual(len(result["findings"]), 1)
        self.assertTrue(
            any(FINDING_EXCESS_LONGER_THAN_NEED in f for f in result["findings"])
        )

    def test_an_excess_shorter_than_the_filter_needs_is_a_finding_on_its_own(self):
        result = assess_switch_on_inrush(_case(profile=_profile_with_charge(3.0e-3)))
        self.assertEqual(len(result["findings"]), 1)
        self.assertTrue(
            any(FINDING_EXCESS_SHORTER_THAN_NEED in f for f in result["findings"])
        )

    def test_a_profile_that_never_settles_is_a_finding(self):
        profile = list(copy.deepcopy(DEFAULT_TURN_ON_PROFILE))
        profile[-1]["current_a"] = 1.80
        result = assess_switch_on_inrush(_case(profile=profile))
        self.assertTrue(any(FINDING_NO_SETTLING in f for f in result["findings"]))

    def test_a_tight_but_passing_turn_on_raises_a_window_advisory(self):
        result = assess_switch_on_inrush(
            _case(
                input_filter_capacitance_f=260.0e-6,
                profile=_profile_with_charge(6.5e-3),
            )
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(ADVISORY_WINDOW_USE in a for a in result["advisories"]))

    def test_a_limiting_current_at_the_class_current_leaves_no_allowance(self):
        with self.assertRaises(ValueError):
            assess_switch_on_inrush(_case(limiting_current_a=1.70))

    def test_a_steady_load_consuming_the_limiting_current_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_switch_on_inrush(_case(steady_current_a=2.20))

    def test_assessment_rejects_a_case_missing_the_trip_off_delay(self):
        case = _case()
        del case["trip_off_time_min_s"]
        with self.assertRaises(ValueError):
            assess_switch_on_inrush(case)

    def test_assessment_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            assess_switch_on_inrush("2.2 A for 5.5 ms")


if __name__ == "__main__":
    unittest.main()
