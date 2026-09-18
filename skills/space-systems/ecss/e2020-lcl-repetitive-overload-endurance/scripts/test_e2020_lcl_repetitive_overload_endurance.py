#!/usr/bin/env python3
"""Contract test for latching-current-limiter repetitive-overload endurance (offline)."""

import copy
import math
import unittest

from e2020_lcl_repetitive_overload_endurance_logic import (
    DEFAULT_DERATING_POLICY,
    RELATIVE_TOLERANCE,
    TEMPERATURE_TOLERANCE_C,
    assess_lcl_repetitive_overload,
    average_dissipation_w,
    cycle_margin,
    enters_limitation,
    limiting_output_voltage_v,
    pass_element_dissipation_w,
    prospective_current_a,
    settled_junction_rise_c,
    thermal_impedance_k_per_w,
    trip_energy_j,
    validate_derating_policy,
)

# A power-distribution outlet that rides out fifty commanded re-closures onto a
# hard short with several seconds of recovery between attempts.
RELAXED_CASE = {
    "bus_voltage_v": 28.0,
    "limiting_current_a": 3.0,
    "load_resistance_ohm": 0.5,
    "trip_delay_s": 0.010,
    "recovery_interval_s": 5.0,
    "applied_cycles": 50,
    "rated_cycles": 500,
    "rth_jc_k_per_w": 2.0,
    "thermal_tau_s": 0.5,
    "case_temperature_c": 60.0,
    "pass_element_rated_current_a": 5.0,
    "pass_element_rated_power_w": 20.0,
}

# The same outlet re-closed almost immediately: the junction never gets back to
# the case between attempts and the train settles far above the first pulse.
HAMMERED_CASE = dict(RELAXED_CASE, recovery_interval_s=0.001)


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class DeratingPolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_derating_policy(DEFAULT_DERATING_POLICY), DEFAULT_DERATING_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_derating_policy("default")

    def test_policy_missing_a_key_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_POLICY)
        del broken["max_current_fraction"]
        with self.assertRaises(ValueError):
            validate_derating_policy(broken)

    def test_policy_fraction_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_POLICY)
        broken["max_average_power_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_derating_policy(broken)

    def test_policy_cycle_margin_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_POLICY)
        broken["min_cycle_margin"] = 0.5
        with self.assertRaises(ValueError):
            validate_derating_policy(broken)


class LimitationEntryTests(unittest.TestCase):
    def test_prospective_current_follows_ohms_law(self):
        self.assertAlmostEqual(prospective_current_a(28.0, 0.5), 56.0, places=9)

    def test_a_hard_short_enters_limitation(self):
        self.assertTrue(enters_limitation(56.0, 2.7))

    def test_a_light_load_does_not_enter_limitation(self):
        self.assertFalse(enters_limitation(1.2, 2.7))

    def test_a_load_exactly_on_the_band_edge_enters_limitation(self):
        self.assertTrue(enters_limitation(2.7, 2.7))

    def test_negative_load_resistance_rejected(self):
        with self.assertRaises(ValueError):
            prospective_current_a(28.0, -0.5)

    def test_boolean_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            prospective_current_a(True, 0.5)

    def test_limited_output_voltage_is_the_drop_across_the_load(self):
        self.assertAlmostEqual(limiting_output_voltage_v(3.0, 0.5, 28.0), 1.5, places=9)

    def test_load_too_light_for_limitation_is_refused(self):
        with self.assertRaises(ValueError):
            limiting_output_voltage_v(3.0, 20.0, 28.0)

    def test_dissipation_is_the_limiting_current_across_the_remaining_bus(self):
        self.assertAlmostEqual(pass_element_dissipation_w(28.0, 3.0, 0.5), 79.5, places=9)


class ThermalModelTests(unittest.TestCase):
    def test_zero_duration_impedance_is_zero(self):
        self.assertAlmostEqual(thermal_impedance_k_per_w(2.0, 0.5, 0.0), 0.0, places=12)

    def test_impedance_saturates_at_the_steady_state_resistance(self):
        self.assertAlmostEqual(thermal_impedance_k_per_w(2.0, 0.5, 40.0), 2.0, places=9)

    def test_impedance_is_below_the_steady_state_resistance_for_a_short_pulse(self):
        self.assertLess(thermal_impedance_k_per_w(2.0, 0.5, 0.01), 1.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            thermal_impedance_k_per_w(2.0, 0.5, -1.0)

    def test_zero_recovery_settles_on_the_steady_state_rise(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 0.0)
        self.assertAlmostEqual(rises["settled_peak_rise_c"], 159.0, places=9)

    def test_long_recovery_settles_on_the_first_pulse_rise(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 20.0)
        self.assertAlmostEqual(
            rises["settled_peak_rise_c"], rises["first_pulse_rise_c"], places=9
        )

    def test_short_recovery_stacks_the_train_well_above_one_pulse(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 0.001)
        self.assertGreater(rises["settled_peak_rise_c"], 10.0 * rises["first_pulse_rise_c"])

    def test_settled_valley_sits_below_the_settled_peak(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 0.001)
        self.assertLess(rises["settled_valley_rise_c"], rises["settled_peak_rise_c"])

    def test_settled_peak_never_exceeds_the_steady_state_rise(self):
        rises = settled_junction_rise_c(79.5, 2.0, 0.5, 0.01, 0.001)
        self.assertLessEqual(
            rises["settled_peak_rise_c"], rises["steady_state_rise_c"] * (1.0 + 1e-9)
        )

    def test_zero_on_time_rejected(self):
        with self.assertRaises(ValueError):
            settled_junction_rise_c(79.5, 2.0, 0.5, 0.0, 1.0)


class EnergyAndCycleTests(unittest.TestCase):
    def test_trip_energy_is_power_times_delay(self):
        self.assertAlmostEqual(trip_energy_j(79.5, 0.010), 0.795, places=9)

    def test_trip_energy_rejects_a_zero_delay(self):
        with self.assertRaises(ValueError):
            trip_energy_j(79.5, 0.0)

    def test_average_dissipation_scales_with_the_duty_cycle(self):
        self.assertAlmostEqual(average_dissipation_w(100.0, 1.0, 3.0), 25.0, places=9)

    def test_average_dissipation_with_no_recovery_is_the_full_power(self):
        self.assertAlmostEqual(average_dissipation_w(100.0, 1.0, 0.0), 100.0, places=9)

    def test_cycle_margin_is_the_rated_over_the_applied_count(self):
        self.assertAlmostEqual(cycle_margin(50, 500), 10.0, places=9)

    def test_fractional_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            cycle_margin(50.5, 500)

    def test_zero_rated_cycles_rejected(self):
        with self.assertRaises(ValueError):
            cycle_margin(50, 0)


class AssessmentTests(unittest.TestCase):
    def test_relaxed_case_demonstrates_endurance(self):
        result = assess_lcl_repetitive_overload(RELAXED_CASE)
        self.assertEqual(result["verdict"], "endurance-demonstrated")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_relaxed_case_reports_the_expected_dissipation(self):
        result = assess_lcl_repetitive_overload(RELAXED_CASE)
        self.assertAlmostEqual(result["pass_element_dissipation_w"], 79.5, places=9)
        self.assertAlmostEqual(result["limited_output_voltage_v"], 1.5, places=9)

    def test_hammered_case_fails_on_junction_temperature(self):
        result = assess_lcl_repetitive_overload(HAMMERED_CASE)
        self.assertEqual(result["verdict"], "endurance-not-demonstrated")
        self.assertFalse(result["compliant"])
        failed = [c["name"] for c in result["checks"] if not c["passed"]]
        self.assertIn("settled-junction-temperature", failed)

    def test_hammered_case_flags_the_train_stacking(self):
        result = assess_lcl_repetitive_overload(HAMMERED_CASE)
        self.assertTrue(any("settled peak rise" in f for f in result["findings"]))

    def test_every_check_is_reported_whatever_the_verdict(self):
        names = [c["name"] for c in assess_lcl_repetitive_overload(RELAXED_CASE)["checks"]]
        self.assertEqual(
            names,
            [
                "settled-junction-temperature",
                "limiting-current-derating",
                "average-dissipation-derating",
                "repetitive-trip-capability",
            ],
        )

    def test_current_above_the_derated_rating_fails_that_check(self):
        result = assess_lcl_repetitive_overload(
            _case(RELAXED_CASE, pass_element_rated_current_a=3.2)
        )
        failed = [c["name"] for c in result["checks"] if not c["passed"]]
        self.assertIn("limiting-current-derating", failed)

    def test_current_exactly_on_the_derated_rating_passes(self):
        result = assess_lcl_repetitive_overload(
            _case(RELAXED_CASE, pass_element_rated_current_a=3.75)
        )
        check = [c for c in result["checks"] if c["name"] == "limiting-current-derating"][0]
        self.assertAlmostEqual(check["value"], check["limit"], places=9)
        self.assertTrue(check["passed"])

    def test_more_trips_than_rated_fails_the_capability_check(self):
        result = assess_lcl_repetitive_overload(_case(RELAXED_CASE, applied_cycles=600))
        failed = [c["name"] for c in result["checks"] if not c["passed"]]
        self.assertIn("repetitive-trip-capability", failed)

    def test_trips_exactly_at_the_rated_count_pass(self):
        result = assess_lcl_repetitive_overload(_case(RELAXED_CASE, applied_cycles=500))
        check = [c for c in result["checks"] if c["name"] == "repetitive-trip-capability"][0]
        self.assertAlmostEqual(check["value"], 1.0, places=9)
        self.assertTrue(check["passed"])

    def test_a_load_below_the_limiting_band_is_not_an_overload_cycle(self):
        result = assess_lcl_repetitive_overload(_case(RELAXED_CASE, load_resistance_ohm=20.0))
        self.assertEqual(result["verdict"], "overload-below-limitation")
        self.assertIsNone(result["compliant"])
        self.assertTrue(any("not a repetitive-overload cycle" in f for f in result["findings"]))

    def test_the_limiting_band_tolerance_widens_the_entry_threshold(self):
        case = _case(RELAXED_CASE, load_resistance_ohm=5.0, limiting_current_tolerance=0.20)
        result = assess_lcl_repetitive_overload(case)
        self.assertAlmostEqual(result["limiting_current_min_a"], 2.4, places=9)
        self.assertEqual(result["verdict"], "endurance-demonstrated")

    def test_a_load_inside_the_band_but_under_the_setting_is_indeterminate(self):
        case = _case(RELAXED_CASE, load_resistance_ohm=10.0, limiting_current_tolerance=0.20)
        result = assess_lcl_repetitive_overload(case)
        self.assertEqual(result["verdict"], "overload-inside-limiting-band")
        self.assertIsNone(result["compliant"])
        self.assertEqual(result["checks"], [])
        self.assertTrue(any("band edge" in f for f in result["findings"]))

    def test_a_tolerance_of_one_or_more_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_lcl_repetitive_overload(_case(RELAXED_CASE, limiting_current_tolerance=1.0))

    def test_a_missing_key_is_rejected(self):
        case = _case(RELAXED_CASE)
        del case["thermal_tau_s"]
        with self.assertRaises(ValueError):
            assess_lcl_repetitive_overload(case)

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_lcl_repetitive_overload("28 V outlet")

    def test_a_negative_thermal_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_lcl_repetitive_overload(_case(RELAXED_CASE, rth_jc_k_per_w=-2.0))

    def test_a_hotter_case_raises_the_settled_junction_temperature(self):
        cool = assess_lcl_repetitive_overload(RELAXED_CASE)
        warm = assess_lcl_repetitive_overload(_case(RELAXED_CASE, case_temperature_c=80.0))
        self.assertAlmostEqual(
            warm["settled_peak_junction_temperature_c"]
            - cool["settled_peak_junction_temperature_c"],
            20.0,
            places=9,
        )

    def test_tolerances_are_small_positive_constants(self):
        self.assertGreater(TEMPERATURE_TOLERANCE_C, 0.0)
        self.assertLess(TEMPERATURE_TOLERANCE_C, 1e-6)
        self.assertGreater(RELATIVE_TOLERANCE, 0.0)
        self.assertLess(RELATIVE_TOLERANCE, 1e-9)
        self.assertTrue(math.isfinite(RELATIVE_TOLERANCE))


if __name__ == "__main__":
    unittest.main()
