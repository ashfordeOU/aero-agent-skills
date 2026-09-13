#!/usr/bin/env python3
"""Contract test for photovoltaic-assembly thermal-cycling execution (offline).

This is the gate 3 behaviour contract: every workflow step of the leaf
(cycle-count derivation, extreme selection, profile sizing, cycle grading
and the campaign verdict) is exercised here, including the refusals that
stop a run before the chamber door closes.
"""

import copy
import unittest

from e2008_thermal_cycling_test_execution_logic import (
    CYCLING_COMPLETE,
    CYCLING_NOT_RUN,
    CYCLING_SHORT,
    DEFAULT_CYCLING_POLICY,
    ORBIT_REGIMES,
    campaign_duration_h,
    cycle_period_min,
    evaluate_recorded_cycles,
    plan_and_verify_cycling,
    qualification_temperature_extremes,
    required_cycle_count,
    validate_cycling_policy,
)

BASE_CASE = {
    "orbit_regime": "geo",
    "mission_years": 0.5,
    "predicted_min_c": -100.0,
    "predicted_max_c": 90.0,
    "coupon_limit_min_c": -150.0,
    "coupon_limit_max_c": 120.0,
    "ramp_rate_k_per_min": 10.0,
    "hot_dwell_min": 10.0,
    "cold_dwell_min": 10.0,
}

GOOD_CYCLE = {
    "min_c": -110.0,
    "max_c": 100.0,
    "hot_dwell_min": 10.0,
    "cold_dwell_min": 10.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


def _cycles(count, **overrides):
    return [_case(GOOD_CYCLE, **overrides) for _ in range(count)]


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cycling_policy(DEFAULT_CYCLING_POLICY), DEFAULT_CYCLING_POLICY
        )

    def test_policy_covers_every_orbit_regime(self):
        for regime in ORBIT_REGIMES:
            self.assertIn(regime, DEFAULT_CYCLING_POLICY["eclipse_cycles_per_year"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycling_policy("default")

    def test_policy_missing_a_regime_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        del broken["eclipse_cycles_per_year"]["heo"]
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)

    def test_qualification_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        broken["qualification_factor"] = 0.8
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)

    def test_fractional_minimum_cycle_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        broken["minimum_qualification_cycles"] = 12.5
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)

    def test_negative_temperature_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        broken["temperature_margin_k"] = -5.0
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)

    def test_zero_stabilisation_tolerance_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_POLICY)
        broken["stabilisation_tolerance_k"] = 0.0
        with self.assertRaises(ValueError):
            validate_cycling_policy(broken)


class RequiredCycleCountTests(unittest.TestCase):
    def test_geostationary_mission_cycle_count(self):
        self.assertEqual(required_cycle_count("geo", 15.0), 1688)

    def test_low_orbit_mission_cycle_count(self):
        # 5500 x 5 x 1.25 is exactly 34375; the count must not round up.
        self.assertEqual(required_cycle_count("leo", 5.0), 34375)

    def test_short_mission_is_floored_by_the_policy_minimum(self):
        self.assertEqual(required_cycle_count("geo", 0.5), 100)

    def test_low_orbit_demands_far_more_cycles_than_geostationary(self):
        self.assertGreater(
            required_cycle_count("leo", 5.0), required_cycle_count("geo", 5.0)
        )

    def test_longer_mission_never_lowers_the_count(self):
        shorter = required_cycle_count("meo", 4.0)
        longer = required_cycle_count("meo", 8.0)
        self.assertGreater(longer, shorter)

    def test_unknown_orbit_regime_rejected(self):
        with self.assertRaises(ValueError):
            required_cycle_count("cislunar", 5.0)

    def test_zero_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            required_cycle_count("leo", 0.0)

    def test_non_numeric_mission_duration_rejected(self):
        with self.assertRaises(ValueError):
            required_cycle_count("leo", "five years")


class TemperatureExtremeTests(unittest.TestCase):
    def test_margin_widens_both_predicted_extremes(self):
        result = qualification_temperature_extremes(-100.0, 90.0, -150.0, 120.0)
        self.assertAlmostEqual(result["qual_min_c"], -110.0, places=9)
        self.assertAlmostEqual(result["qual_max_c"], 100.0, places=9)

    def test_range_is_the_span_between_the_extremes(self):
        result = qualification_temperature_extremes(-100.0, 90.0, -150.0, 120.0)
        self.assertAlmostEqual(result["range_k"], 210.0, places=9)

    def test_comfortable_coupon_limits_raise_no_finding(self):
        result = qualification_temperature_extremes(-100.0, 90.0, -150.0, 120.0)
        self.assertEqual(result["findings"], [])

    def test_extreme_sitting_on_the_coupon_limit_is_allowed_with_a_finding(self):
        result = qualification_temperature_extremes(-100.0, 90.0, -110.0, 100.0)
        self.assertAlmostEqual(result["qual_max_c"], 100.0, places=9)
        self.assertEqual(len(result["findings"]), 2)

    def test_hot_extreme_beyond_the_coupon_limit_is_refused(self):
        with self.assertRaises(ValueError):
            qualification_temperature_extremes(-100.0, 90.0, -150.0, 95.0)

    def test_cold_extreme_beyond_the_coupon_limit_is_refused(self):
        with self.assertRaises(ValueError):
            qualification_temperature_extremes(-100.0, 90.0, -105.0, 120.0)

    def test_inverted_prediction_rejected(self):
        with self.assertRaises(ValueError):
            qualification_temperature_extremes(90.0, -100.0, -150.0, 120.0)

    def test_inverted_coupon_limits_rejected(self):
        with self.assertRaises(ValueError):
            qualification_temperature_extremes(-100.0, 90.0, 120.0, -150.0)

    def test_non_numeric_prediction_rejected(self):
        with self.assertRaises(ValueError):
            qualification_temperature_extremes("cold", 90.0, -150.0, 120.0)


class CyclePeriodTests(unittest.TestCase):
    def test_period_is_two_ramps_plus_two_dwells(self):
        self.assertAlmostEqual(cycle_period_min(210.0, 10.0, 10.0, 10.0), 62.0, places=9)

    def test_a_faster_ramp_shortens_the_period(self):
        fast = cycle_period_min(210.0, 20.0, 10.0, 10.0)
        slow = cycle_period_min(210.0, 5.0, 10.0, 10.0)
        self.assertGreater(slow, fast)

    def test_ramp_rate_on_the_policy_ceiling_is_accepted(self):
        ceiling = DEFAULT_CYCLING_POLICY["maximum_ramp_rate_k_per_min"]
        self.assertAlmostEqual(
            cycle_period_min(200.0, ceiling, 5.0, 5.0), 30.0, places=9
        )

    def test_ramp_rate_above_the_policy_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            cycle_period_min(210.0, 50.0, 10.0, 10.0)

    def test_dwell_on_the_policy_floor_is_accepted(self):
        floor = DEFAULT_CYCLING_POLICY["minimum_dwell_min"]
        self.assertAlmostEqual(
            cycle_period_min(100.0, 10.0, floor, floor), 30.0, places=9
        )

    def test_dwell_below_the_policy_floor_rejected(self):
        with self.assertRaises(ValueError):
            cycle_period_min(210.0, 10.0, 1.0, 10.0)

    def test_zero_range_rejected(self):
        with self.assertRaises(ValueError):
            cycle_period_min(0.0, 10.0, 10.0, 10.0)

    def test_negative_ramp_rate_rejected(self):
        with self.assertRaises(ValueError):
            cycle_period_min(210.0, -10.0, 10.0, 10.0)


class CampaignDurationTests(unittest.TestCase):
    def test_duration_converts_cycles_and_period_to_hours(self):
        self.assertAlmostEqual(campaign_duration_h(1688, 62.0), 1744.2666666667, places=6)

    def test_one_cycle_of_sixty_minutes_is_one_hour(self):
        self.assertAlmostEqual(campaign_duration_h(1, 60.0), 1.0, places=9)

    def test_fractional_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            campaign_duration_h(12.5, 60.0)

    def test_zero_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            campaign_duration_h(0, 60.0)

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            campaign_duration_h(10, 0.0)


class RecordedCycleTests(unittest.TestCase):
    def test_clean_run_counts_every_cycle(self):
        run = evaluate_recorded_cycles(_cycles(120), -110.0, 100.0, 10.0, 10.0)
        self.assertEqual(run["cycles_recorded"], 120)
        self.assertEqual(run["conforming_cycles"], 120)
        self.assertEqual(run["non_conforming"], [])

    def test_cycle_inside_the_stabilisation_tolerance_still_counts(self):
        run = evaluate_recorded_cycles(
            _cycles(3, min_c=-108.0, max_c=98.0), -110.0, 100.0, 10.0, 10.0
        )
        self.assertEqual(run["conforming_cycles"], 3)

    def test_cycle_that_never_reached_the_cold_extreme_is_dropped(self):
        run = evaluate_recorded_cycles(
            _cycles(1, min_c=-95.0), -110.0, 100.0, 10.0, 10.0
        )
        self.assertEqual(run["conforming_cycles"], 0)
        self.assertIn("cold extreme not reached", run["non_conforming"][0]["reasons"])

    def test_cycle_that_never_reached_the_hot_extreme_is_dropped(self):
        run = evaluate_recorded_cycles(_cycles(1, max_c=80.0), -110.0, 100.0, 10.0, 10.0)
        self.assertIn("hot extreme not reached", run["non_conforming"][0]["reasons"])

    def test_short_hot_dwell_is_dropped(self):
        run = evaluate_recorded_cycles(
            _cycles(1, hot_dwell_min=2.0), -110.0, 100.0, 10.0, 10.0
        )
        self.assertIn("hot dwell short", run["non_conforming"][0]["reasons"])

    def test_short_cold_dwell_is_dropped(self):
        run = evaluate_recorded_cycles(
            _cycles(1, cold_dwell_min=0.0), -110.0, 100.0, 10.0, 10.0
        )
        self.assertIn("cold dwell short", run["non_conforming"][0]["reasons"])

    def test_a_single_record_can_miss_several_ways(self):
        run = evaluate_recorded_cycles(
            _cycles(1, min_c=-50.0, max_c=10.0, hot_dwell_min=1.0),
            -110.0,
            100.0,
            10.0,
            10.0,
        )
        self.assertEqual(len(run["non_conforming"][0]["reasons"]), 3)

    def test_empty_record_set_conforms_nothing(self):
        run = evaluate_recorded_cycles([], -110.0, 100.0, 10.0, 10.0)
        self.assertEqual(run["conforming_cycles"], 0)

    def test_non_list_record_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_recorded_cycles("120 cycles", -110.0, 100.0, 10.0, 10.0)

    def test_record_missing_a_temperature_rejected(self):
        broken = [{"max_c": 100.0, "hot_dwell_min": 10.0, "cold_dwell_min": 10.0}]
        with self.assertRaises(ValueError):
            evaluate_recorded_cycles(broken, -110.0, 100.0, 10.0, 10.0)

    def test_record_that_is_not_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_recorded_cycles(["cycle one"], -110.0, 100.0, 10.0, 10.0)


class PlanTests(unittest.TestCase):
    def test_plan_reports_the_required_count_and_profile(self):
        result = plan_and_verify_cycling(BASE_CASE)
        self.assertEqual(result["required_cycles"], 100)
        self.assertAlmostEqual(result["qual_min_c"], -110.0, places=9)
        self.assertAlmostEqual(result["qual_max_c"], 100.0, places=9)
        self.assertAlmostEqual(result["cycle_period_min"], 62.0, places=9)

    def test_planned_duration_follows_the_required_count(self):
        result = plan_and_verify_cycling(BASE_CASE)
        self.assertAlmostEqual(
            result["planned_campaign_duration_h"], 103.3333333333, places=6
        )

    def test_run_meeting_the_count_is_complete(self):
        result = plan_and_verify_cycling(
            _case(BASE_CASE, recorded_cycles=_cycles(100))
        )
        self.assertEqual(result["verdict"], CYCLING_COMPLETE)
        self.assertTrue(result["complete"])
        self.assertEqual(result["conforming_cycles"], 100)

    def test_run_one_cycle_short_is_not_complete(self):
        result = plan_and_verify_cycling(_case(BASE_CASE, recorded_cycles=_cycles(99)))
        self.assertEqual(result["verdict"], CYCLING_SHORT)
        self.assertFalse(result["complete"])
        self.assertTrue(any("conforming cycles" in f for f in result["findings"]))

    def test_chamber_hours_do_not_replace_conforming_cycles(self):
        # 100 cycles were run but ten never reached the cold extreme, so the
        # campaign stops short of the requirement and the review has to say so.
        recorded = _cycles(90) + _cycles(10, min_c=-60.0)
        result = plan_and_verify_cycling(_case(BASE_CASE, recorded_cycles=recorded))
        self.assertEqual(result["cycles_recorded"], 100)
        self.assertEqual(result["conforming_cycles"], 90)
        self.assertEqual(result["verdict"], CYCLING_SHORT)
        self.assertTrue(any("do not count" in f for f in result["findings"]))

    def test_plan_without_records_is_not_yet_demonstrated(self):
        result = plan_and_verify_cycling(BASE_CASE)
        self.assertEqual(result["verdict"], CYCLING_NOT_RUN)
        self.assertIsNone(result["complete"])
        self.assertTrue(any("not yet demonstrated" in f for f in result["findings"]))

    def test_plan_carries_the_coupon_limit_finding(self):
        case = _case(BASE_CASE, coupon_limit_min_c=-110.0, coupon_limit_max_c=100.0)
        result = plan_and_verify_cycling(case)
        self.assertEqual(len(result["findings"]), 3)

    def test_plan_refuses_a_profile_the_coupon_cannot_survive(self):
        with self.assertRaises(ValueError):
            plan_and_verify_cycling(_case(BASE_CASE, coupon_limit_max_c=95.0))

    def test_plan_rejects_an_unknown_orbit_regime(self):
        with self.assertRaises(ValueError):
            plan_and_verify_cycling(_case(BASE_CASE, orbit_regime="halo"))

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_and_verify_cycling("geo, fifteen years")

    def test_plan_rejects_a_missing_ramp_rate(self):
        case = _case(BASE_CASE)
        del case["ramp_rate_k_per_min"]
        with self.assertRaises(ValueError):
            plan_and_verify_cycling(case)

    def test_a_longer_mission_phase_raises_the_required_count(self):
        short = plan_and_verify_cycling(BASE_CASE)["required_cycles"]
        long_mission = plan_and_verify_cycling(_case(BASE_CASE, mission_years=15.0))
        self.assertGreater(long_mission["required_cycles"], short)


if __name__ == "__main__":
    unittest.main()
