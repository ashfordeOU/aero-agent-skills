#!/usr/bin/env python3
"""Contract test for retriggerable-limiter repetitive-overload endurance (offline)."""

import copy
import unittest

from e2020_rlcl_repetitive_overload_endurance_logic import (
    DEFAULT_RLCL_DERATING_POLICY,
    RELATIVE_TOLERANCE,
    TEMPERATURE_TOLERANCE_C,
    assess_rlcl_repetitive_overload,
    average_dissipation_w,
    limitation_dissipation_w,
    maximum_duty_cycle,
    minimum_off_time_s,
    regulated_output_voltage_v,
    retrigger_count,
    retrigger_duty_cycle,
    retrigger_period_s,
    settled_junction_rise_c,
    validate_rlcl_policy,
)

# A retriggerable outlet re-arming every 200 ms onto a load that keeps stalling.
PATIENT_CASE = {
    "bus_voltage_v": 28.0,
    "limiting_current_a": 3.0,
    "load_resistance_ohm": 0.5,
    "limitation_time_s": 0.010,
    "retrigger_off_time_s": 0.200,
    "fault_window_s": 60.0,
    "rth_jc_k_per_w": 2.0,
    "thermal_tau_s": 0.5,
    "case_temperature_c": 60.0,
    "rated_current_a": 5.0,
    "rated_power_w": 20.0,
    "rated_retrigger_cycles": 1000,
}

# The same outlet re-arming in half a millisecond: it is effectively conducting
# the overload continuously.
IMPATIENT_CASE = dict(PATIENT_CASE, retrigger_off_time_s=0.0005)


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_rlcl_policy(DEFAULT_RLCL_DERATING_POLICY), DEFAULT_RLCL_DERATING_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_policy(["max_duty_cycle"])

    def test_policy_missing_the_duty_cap_rejected(self):
        broken = copy.deepcopy(DEFAULT_RLCL_DERATING_POLICY)
        del broken["max_duty_cycle"]
        with self.assertRaises(ValueError):
            validate_rlcl_policy(broken)

    def test_policy_duty_cap_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_RLCL_DERATING_POLICY)
        broken["max_duty_cycle"] = 1.5
        with self.assertRaises(ValueError):
            validate_rlcl_policy(broken)

    def test_policy_retrigger_margin_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_RLCL_DERATING_POLICY)
        broken["min_retrigger_margin"] = 0.2
        with self.assertRaises(ValueError):
            validate_rlcl_policy(broken)


class RetriggerTimingTests(unittest.TestCase):
    def test_period_is_the_sum_of_the_two_intervals(self):
        self.assertAlmostEqual(retrigger_period_s(0.01, 0.20), 0.21, places=12)

    def test_duty_cycle_is_the_limiting_share_of_the_period(self):
        self.assertAlmostEqual(retrigger_duty_cycle(0.01, 0.03), 0.25, places=12)

    def test_duty_cycle_rises_as_the_off_time_shrinks(self):
        self.assertGreater(retrigger_duty_cycle(0.01, 0.001), retrigger_duty_cycle(0.01, 0.20))

    def test_zero_off_time_rejected_for_a_retriggerable_part(self):
        with self.assertRaises(ValueError):
            retrigger_duty_cycle(0.01, 0.0)

    def test_negative_limitation_time_rejected(self):
        with self.assertRaises(ValueError):
            retrigger_period_s(-0.01, 0.20)

    def test_retrigger_count_floors_a_partial_cycle(self):
        self.assertEqual(retrigger_count(60.0, 0.01, 0.20), 285)

    def test_retrigger_count_keeps_an_exact_multiple_whole(self):
        self.assertEqual(retrigger_count(2.1, 0.01, 0.20), 10)

    def test_a_window_shorter_than_one_period_yields_no_cycle(self):
        self.assertEqual(retrigger_count(0.1, 0.01, 0.20), 0)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            retrigger_count(0.0, 0.01, 0.20)


class DissipationTests(unittest.TestCase):
    def test_regulated_output_is_the_drop_across_the_stalled_load(self):
        self.assertAlmostEqual(regulated_output_voltage_v(3.0, 0.5, 28.0), 1.5, places=9)

    def test_a_load_that_cannot_draw_the_limiting_current_is_refused(self):
        with self.assertRaises(ValueError):
            regulated_output_voltage_v(3.0, 12.0, 28.0)

    def test_dissipation_is_the_limiting_current_across_the_remaining_bus(self):
        self.assertAlmostEqual(limitation_dissipation_w(28.0, 3.0, 0.5), 79.5, places=9)

    def test_average_dissipation_follows_the_duty_cycle(self):
        self.assertAlmostEqual(average_dissipation_w(100.0, 0.01, 0.03), 25.0, places=9)

    def test_boolean_current_rejected(self):
        with self.assertRaises(ValueError):
            limitation_dissipation_w(28.0, True, 0.5)


class ThermalTrainTests(unittest.TestCase):
    def test_a_long_off_time_settles_on_the_single_pulse_rise(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 30.0)
        self.assertAlmostEqual(
            rises["settled_peak_rise_c"], rises["first_pulse_rise_c"], places=9
        )

    def test_a_short_off_time_stacks_the_train(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 0.0005)
        self.assertGreater(rises["settled_peak_rise_c"], 10.0 * rises["first_pulse_rise_c"])

    def test_the_settled_peak_never_passes_the_steady_state_rise(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 0.0005)
        self.assertLessEqual(
            rises["settled_peak_rise_c"], rises["steady_state_rise_c"] * (1.0 + 1e-9)
        )

    def test_the_valley_sits_below_the_peak(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 0.20)
        self.assertLess(rises["settled_valley_rise_c"], rises["settled_peak_rise_c"])

    def test_zero_off_time_is_not_a_retrigger_train(self):
        with self.assertRaises(ValueError):
            settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 0.0)


class OffTimeSolveTests(unittest.TestCase):
    def test_the_solved_off_time_lands_exactly_on_the_rise_limit(self):
        off_time = minimum_off_time_s(79.5, 2.0, 0.5, 0.01, 50.0)
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, off_time)
        self.assertAlmostEqual(rises["settled_peak_rise_c"], 50.0, places=9)

    def test_an_ample_headroom_needs_no_off_time_at_all(self):
        self.assertAlmostEqual(minimum_off_time_s(79.5, 2.0, 0.5, 0.01, 200.0), 0.0, places=12)

    def test_a_headroom_one_interval_already_breaks_is_refused(self):
        with self.assertRaises(ValueError):
            minimum_off_time_s(79.5, 2.0, 0.5, 0.01, 2.0)

    def test_less_headroom_demands_a_longer_off_time(self):
        self.assertGreater(
            minimum_off_time_s(79.5, 2.0, 0.5, 0.01, 20.0),
            minimum_off_time_s(79.5, 2.0, 0.5, 0.01, 50.0),
        )

    def test_the_highest_duty_cycle_matches_the_solved_off_time(self):
        off_time = minimum_off_time_s(79.5, 2.0, 0.5, 0.01, 50.0)
        self.assertAlmostEqual(
            maximum_duty_cycle(79.5, 2.0, 0.5, 0.01, 50.0),
            0.01 / (0.01 + off_time),
            places=12,
        )

    def test_an_unconstrained_part_may_limit_continuously(self):
        self.assertAlmostEqual(maximum_duty_cycle(79.5, 2.0, 0.5, 0.01, 200.0), 1.0, places=12)

    def test_a_non_positive_rise_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_off_time_s(79.5, 2.0, 0.5, 0.01, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_the_patient_case_demonstrates_endurance(self):
        result = assess_rlcl_repetitive_overload(PATIENT_CASE)
        self.assertEqual(result["verdict"], "endurance-demonstrated")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_the_patient_case_reports_its_duty_cycle_and_count(self):
        result = assess_rlcl_repetitive_overload(PATIENT_CASE)
        self.assertAlmostEqual(result["retrigger_duty_cycle"], 0.01 / 0.21, places=12)
        self.assertEqual(result["retrigger_count"], 285)

    def test_the_patient_case_has_off_time_to_spare(self):
        result = assess_rlcl_repetitive_overload(PATIENT_CASE)
        self.assertAlmostEqual(result["off_time_shortfall_s"], 0.0, places=12)
        self.assertLess(result["required_off_time_s"], PATIENT_CASE["retrigger_off_time_s"])

    def test_the_impatient_case_fails_on_every_thermal_check(self):
        result = assess_rlcl_repetitive_overload(IMPATIENT_CASE)
        self.assertFalse(result["compliant"])
        failed = [c["name"] for c in result["checks"] if not c["passed"]]
        for name in (
            "settled-junction-temperature",
            "retrigger-duty-cycle",
            "average-dissipation-derating",
            "retrigger-capability",
        ):
            self.assertIn(name, failed)

    def test_the_impatient_case_names_the_off_time_it_needs(self):
        result = assess_rlcl_repetitive_overload(IMPATIENT_CASE)
        self.assertGreater(result["off_time_shortfall_s"], 0.0)
        self.assertTrue(any("shorter than the" in f for f in result["findings"]))

    def test_every_check_is_reported_in_a_fixed_order(self):
        names = [c["name"] for c in assess_rlcl_repetitive_overload(PATIENT_CASE)["checks"]]
        self.assertEqual(
            names,
            [
                "settled-junction-temperature",
                "retrigger-duty-cycle",
                "limiting-current-derating",
                "average-dissipation-derating",
                "retrigger-capability",
            ],
        )

    def test_a_case_already_at_the_junction_limit_has_no_headroom(self):
        result = assess_rlcl_repetitive_overload(_case(PATIENT_CASE, case_temperature_c=110.0))
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["required_off_time_s"])
        self.assertTrue(any("no retrigger design holds" in f for f in result["findings"]))

    def test_a_window_below_one_period_is_reported(self):
        result = assess_rlcl_repetitive_overload(_case(PATIENT_CASE, fault_window_s=0.05))
        self.assertEqual(result["retrigger_count"], 0)
        self.assertTrue(any("no complete retrigger cycle" in f for f in result["findings"]))

    def test_current_exactly_on_the_derated_rating_passes(self):
        result = assess_rlcl_repetitive_overload(_case(PATIENT_CASE, rated_current_a=3.75))
        check = [c for c in result["checks"] if c["name"] == "limiting-current-derating"][0]
        self.assertAlmostEqual(check["value"], check["limit"], places=9)
        self.assertTrue(check["passed"])

    def test_retriggers_exactly_at_the_rated_count_pass(self):
        result = assess_rlcl_repetitive_overload(_case(PATIENT_CASE, rated_retrigger_cycles=285))
        check = [c for c in result["checks"] if c["name"] == "retrigger-capability"][0]
        self.assertAlmostEqual(check["value"], 1.0, places=9)
        self.assertTrue(check["passed"])

    def test_a_missing_key_is_rejected(self):
        case = _case(PATIENT_CASE)
        del case["fault_window_s"]
        with self.assertRaises(ValueError):
            assess_rlcl_repetitive_overload(case)

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_rlcl_repetitive_overload("retriggerable outlet")

    def test_a_fractional_rated_retrigger_count_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_rlcl_repetitive_overload(_case(PATIENT_CASE, rated_retrigger_cycles=2.5))

    def test_a_load_too_light_to_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_rlcl_repetitive_overload(_case(PATIENT_CASE, load_resistance_ohm=12.0))

    def test_the_declared_tolerances_stay_small_and_positive(self):
        self.assertGreater(TEMPERATURE_TOLERANCE_C, 0.0)
        self.assertLess(TEMPERATURE_TOLERANCE_C, 1e-6)
        self.assertGreater(RELATIVE_TOLERANCE, 0.0)
        self.assertLess(RELATIVE_TOLERANCE, 1e-9)


if __name__ == "__main__":
    unittest.main()
