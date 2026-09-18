#!/usr/bin/env python3
"""Contract test for the thermal cycling conditions (offline)."""

import copy
import math
import unittest

from q7004_thermal_cycling_conditions_logic import (
    ACCEPTANCE_VERIFICATION,
    DEFAULT_CYCLING_POLICY,
    OBJECTIVES,
    QUALIFICATION,
    SCREENING,
    cycle_count,
    cycle_duration_s,
    cycling_span_k,
    define_cycling_conditions,
    dwell_time_s,
    effective_ramp_rate_k_per_min,
    stabilization_time_s,
    transition_time_s,
    validate_cycling_policy,
)

BASE_CASE = {
    "objective": QUALIFICATION,
    "test_min_k": 213.15,
    "test_max_k": 373.15,
    "requested_rate_k_per_min": 5.0,
    "chamber_capability_k_per_min": 8.0,
    "item_allowable_k_per_min": 10.0,
    "time_constant_s": 900.0,
    "hot_soak_s": 1800.0,
    "cold_soak_s": 1800.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cycling_policy(DEFAULT_CYCLING_POLICY), DEFAULT_CYCLING_POLICY
        )

    def test_policy_covers_every_objective(self):
        for objective in OBJECTIVES:
            self.assertIn(objective, DEFAULT_CYCLING_POLICY["cycle_count"])

    def test_policy_missing_an_objective_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        del broken["cycle_count"][ACCEPTANCE_VERIFICATION]
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)

    def test_policy_qualifying_on_fewer_cycles_than_screening_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        broken["cycle_count"][QUALIFICATION] = 3
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)

    def test_policy_with_a_zero_dwell_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        broken["minimum_dwell_s"] = 0.0
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)

    def test_policy_with_a_negative_tolerance_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        broken["stabilization_tolerance_k"] = -1.0
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycling_policy("default")


class SpanTests(unittest.TestCase):
    def test_span_is_the_difference_of_the_limits(self):
        self.assertAlmostEqual(cycling_span_k(213.15, 373.15), 160.0, places=9)

    def test_a_span_exactly_on_the_policy_floor_is_accepted(self):
        floor = DEFAULT_CYCLING_POLICY["min_span_k"]
        self.assertAlmostEqual(cycling_span_k(280.0, 280.0 + floor), floor, places=9)

    def test_a_span_below_the_policy_floor_rejected(self):
        with self.assertRaises(ValueError):
            cycling_span_k(295.0, 300.0)

    def test_inverted_limits_rejected(self):
        with self.assertRaises(ValueError):
            cycling_span_k(373.15, 213.15)

    def test_a_non_absolute_limit_rejected(self):
        with self.assertRaises(ValueError):
            cycling_span_k(-60.0, 100.0)


class RampRateTests(unittest.TestCase):
    def test_the_requested_rate_survives_when_it_is_the_slowest(self):
        rate = effective_ramp_rate_k_per_min(5.0, 8.0, 10.0)
        self.assertAlmostEqual(rate["rate_k_per_min"], 5.0, places=9)
        self.assertEqual(rate["limited_by"], "requested")

    def test_the_chamber_can_set_the_rate(self):
        rate = effective_ramp_rate_k_per_min(9.0, 3.0, 10.0)
        self.assertAlmostEqual(rate["rate_k_per_min"], 3.0, places=9)
        self.assertEqual(rate["limited_by"], "chamber")

    def test_the_item_allowable_can_set_the_rate(self):
        rate = effective_ramp_rate_k_per_min(9.0, 8.0, 2.0)
        self.assertAlmostEqual(rate["rate_k_per_min"], 2.0, places=9)
        self.assertEqual(rate["limited_by"], "item")

    def test_the_policy_ceiling_can_set_the_rate(self):
        rate = effective_ramp_rate_k_per_min(50.0, 60.0, 40.0)
        self.assertAlmostEqual(
            rate["rate_k_per_min"], DEFAULT_CYCLING_POLICY["max_ramp_rate_k_per_min"],
            places=9,
        )
        self.assertEqual(rate["limited_by"], "policy")

    def test_a_zero_chamber_capability_rejected(self):
        with self.assertRaises(ValueError):
            effective_ramp_rate_k_per_min(5.0, 0.0, 10.0)

    def test_a_non_numeric_requested_rate_rejected(self):
        with self.assertRaises(ValueError):
            effective_ramp_rate_k_per_min("five", 8.0, 10.0)


class TransitionTests(unittest.TestCase):
    def test_transition_time_is_the_span_over_the_rate(self):
        self.assertAlmostEqual(transition_time_s(160.0, 5.0), 1920.0, places=9)

    def test_halving_the_rate_doubles_the_transition(self):
        fast = transition_time_s(160.0, 8.0)
        slow = transition_time_s(160.0, 4.0)
        self.assertAlmostEqual(slow / fast, 2.0, places=9)

    def test_a_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            transition_time_s(160.0, 0.0)


class StabilizationTests(unittest.TestCase):
    def test_stabilization_follows_the_exponential_decay_of_the_lag(self):
        expected = 900.0 * math.log(160.0 / 1.0)
        self.assertAlmostEqual(
            stabilization_time_s(900.0, 160.0, 1.0) / expected, 1.0, places=9
        )

    def test_one_time_constant_closes_the_lag_by_a_factor_of_e(self):
        tau = 900.0
        self.assertAlmostEqual(
            stabilization_time_s(tau, math.e, 1.0), tau, places=9
        )

    def test_an_item_already_inside_tolerance_needs_no_stabilization(self):
        self.assertAlmostEqual(stabilization_time_s(900.0, 0.5, 1.0), 0.0, places=9)

    def test_an_offset_exactly_on_tolerance_needs_no_stabilization(self):
        self.assertAlmostEqual(stabilization_time_s(900.0, 1.0, 1.0), 0.0, places=9)

    def test_a_slower_item_takes_proportionally_longer(self):
        quick = stabilization_time_s(300.0, 160.0, 1.0)
        slow = stabilization_time_s(1200.0, 160.0, 1.0)
        self.assertAlmostEqual(slow / quick, 4.0, places=9)

    def test_a_zero_time_constant_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_time_s(0.0, 160.0, 1.0)

    def test_a_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_time_s(900.0, 160.0, 0.0)


class DwellTests(unittest.TestCase):
    def test_dwell_is_stabilization_plus_soak_when_that_beats_the_floor(self):
        dwell = dwell_time_s(900.0, 160.0, 1800.0)
        expected = 900.0 * math.log(160.0) + 1800.0
        self.assertAlmostEqual(dwell["dwell_s"] / expected, 1.0, places=9)
        self.assertEqual(dwell["set_by"], "stabilization-and-soak")

    def test_the_policy_floor_takes_over_for_a_fast_item_and_no_soak(self):
        dwell = dwell_time_s(1.0, 160.0, 0.0)
        self.assertAlmostEqual(
            dwell["dwell_s"], DEFAULT_CYCLING_POLICY["minimum_dwell_s"], places=9
        )
        self.assertEqual(dwell["set_by"], "policy-floor")

    def test_the_dwell_reports_its_stabilization_share(self):
        dwell = dwell_time_s(900.0, 160.0, 1800.0)
        self.assertGreater(dwell["stabilization_s"], 0.0)
        self.assertAlmostEqual(dwell["soak_s"], 1800.0, places=9)

    def test_a_negative_soak_rejected(self):
        with self.assertRaises(ValueError):
            dwell_time_s(900.0, 160.0, -60.0)

    def test_a_non_numeric_time_constant_rejected(self):
        with self.assertRaises(ValueError):
            dwell_time_s("fifteen minutes", 160.0, 1800.0)


class CycleArithmeticTests(unittest.TestCase):
    def test_a_cycle_is_two_transitions_and_two_dwells(self):
        self.assertAlmostEqual(
            cycle_duration_s(1920.0, 3000.0, 3000.0), 2 * 1920.0 + 6000.0, places=9
        )

    def test_a_zero_dwell_rejected(self):
        with self.assertRaises(ValueError):
            cycle_duration_s(1920.0, 0.0, 3000.0)

    def test_qualification_runs_more_cycles_than_screening(self):
        self.assertGreater(cycle_count(QUALIFICATION), cycle_count(SCREENING))

    def test_an_unknown_objective_rejected(self):
        with self.assertRaises(ValueError):
            cycle_count("burn-in")


class ProfileTests(unittest.TestCase):
    def test_the_base_case_profile_is_internally_consistent(self):
        profile = define_cycling_conditions(BASE_CASE)
        self.assertAlmostEqual(profile["span_k"], 160.0, places=9)
        self.assertAlmostEqual(profile["rate_k_per_min"], 5.0, places=9)
        self.assertAlmostEqual(profile["transition_s"], 1920.0, places=9)
        self.assertAlmostEqual(
            profile["cycle_duration_s"],
            2 * profile["transition_s"]
            + profile["hot_dwell"]["dwell_s"]
            + profile["cold_dwell"]["dwell_s"],
            places=9,
        )

    def test_the_campaign_duration_is_the_cycle_count_times_the_cycle(self):
        profile = define_cycling_conditions(BASE_CASE)
        self.assertAlmostEqual(
            profile["campaign_duration_s"],
            profile["cycle_duration_s"] * profile["cycle_count"],
            places=6,
        )

    def test_a_screening_campaign_is_shorter_than_a_qualification_one(self):
        screening = define_cycling_conditions(_case(BASE_CASE, objective=SCREENING))
        qualification = define_cycling_conditions(BASE_CASE)
        self.assertGreater(
            qualification["campaign_duration_s"], screening["campaign_duration_s"]
        )

    def test_a_chamber_limited_profile_is_flagged(self):
        profile = define_cycling_conditions(
            _case(BASE_CASE, chamber_capability_k_per_min=1.5)
        )
        self.assertEqual(profile["rate_limited_by"], "chamber")
        self.assertTrue(any("chamber" in f for f in profile["findings"]))

    def test_an_item_limited_profile_is_flagged(self):
        profile = define_cycling_conditions(
            _case(BASE_CASE, item_allowable_k_per_min=1.0)
        )
        self.assertEqual(profile["rate_limited_by"], "item")
        self.assertTrue(any("allowable rate" in f for f in profile["findings"]))

    def test_a_floor_set_dwell_is_flagged(self):
        profile = define_cycling_conditions(
            _case(BASE_CASE, time_constant_s=1.0, hot_soak_s=0.0, cold_soak_s=0.0)
        )
        self.assertTrue(any("policy floor" in f for f in profile["findings"]))

    def test_a_stabilization_dominated_dwell_carries_a_duty(self):
        profile = define_cycling_conditions(
            _case(BASE_CASE, time_constant_s=3600.0, hot_soak_s=60.0)
        )
        self.assertTrue(
            any("dominated by stabilization" in d for d in profile["duties"])
        )

    def test_every_profile_carries_the_dwell_clock_duty(self):
        profile = define_cycling_conditions(BASE_CASE)
        self.assertTrue(any("dwell clock" in d for d in profile["duties"]))

    def test_a_profile_with_too_narrow_a_span_rejected(self):
        with self.assertRaises(ValueError):
            define_cycling_conditions(
                _case(BASE_CASE, test_min_k=295.0, test_max_k=300.0)
            )

    def test_a_profile_without_a_time_constant_rejected(self):
        case = _case(BASE_CASE)
        del case["time_constant_s"]
        with self.assertRaises(ValueError):
            define_cycling_conditions(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            define_cycling_conditions("minus sixty to plus one hundred")

    def test_an_unknown_objective_in_the_case_rejected(self):
        with self.assertRaises(ValueError):
            define_cycling_conditions(_case(BASE_CASE, objective="burn-in"))


if __name__ == "__main__":
    unittest.main()
