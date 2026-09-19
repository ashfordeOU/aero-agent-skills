#!/usr/bin/env python3
"""Contract test for the limitation-mode rating limits leaf (offline)."""

import copy
import math
import unittest

from e2020_lcl_limitation_mode_rating_limits_logic import (
    BEYOND_RATINGS,
    DEFAULT_CURRENT_DERATING,
    DEFAULT_JUNCTION_DERATING,
    DEFAULT_VOLTAGE_DERATING,
    MODE_LIMITATION,
    MODE_SWITCH,
    WITHIN_RATINGS,
    assess_limitation_mode,
    derated_junction_limit_c,
    derated_limit,
    junction_temperature_c,
    limitation_dissipation_w,
    limitation_energy_j,
    margin_fraction,
    operating_mode,
    pass_element_voltage_v,
    soa_boundary_current_a,
    soa_curve_span_v,
    soa_voltage_is_covered,
    transient_thermal_impedance,
)

# 1 - exp(-1), written out so the check does not reuse the expression.
ONE_MINUS_INVERSE_E = 0.6321205588285577

# A 10 ms pulse boundary: two decades of the safe operating area corner.
SOA_10MS = [(10.0, 20.0), (40.0, 5.0)]

BASE_CASE = {
    "bus_voltage_v": 28.0,
    "output_voltage_v": 4.0,
    "limit_current_a": 1.5,
    "demanded_current_a": 6.0,
    "trip_off_delay_s": 0.01,
    "reference_temperature_c": 40.0,
    "thermal_resistance_c_per_w": 20.0,
    "thermal_time_constant_s": 1.0,
    "rated_current_a": 4.0,
    "rated_voltage_v": 60.0,
    "rated_junction_c": 150.0,
    "soa_curve": copy.deepcopy(SOA_10MS),
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class OperatingModeTests(unittest.TestCase):
    def test_a_demand_above_the_limit_puts_the_device_into_limitation(self):
        self.assertEqual(operating_mode(6.0, 1.5), MODE_LIMITATION)

    def test_a_demand_below_the_limit_leaves_it_in_switch_mode(self):
        self.assertEqual(operating_mode(1.0, 1.5), MODE_SWITCH)

    def test_a_demand_exactly_at_the_limit_is_still_switch_mode(self):
        self.assertEqual(operating_mode(1.5, 1.5), MODE_SWITCH)

    def test_a_negative_demand_is_refused(self):
        with self.assertRaises(ValueError):
            operating_mode(-1.0, 1.5)

    def test_a_zero_limit_is_refused(self):
        with self.assertRaises(ValueError):
            operating_mode(1.0, 0.0)


class DissipationTests(unittest.TestCase):
    def test_the_pass_element_stands_off_the_difference(self):
        self.assertAlmostEqual(pass_element_voltage_v(28.0, 4.0), 24.0, places=9)

    def test_a_hard_short_puts_the_whole_bus_across_the_element(self):
        self.assertAlmostEqual(pass_element_voltage_v(28.0, 0.0), 28.0, places=9)

    def test_an_output_above_the_bus_is_refused(self):
        with self.assertRaises(ValueError):
            pass_element_voltage_v(28.0, 30.0)

    def test_the_dissipation_is_the_drop_times_the_limited_current(self):
        self.assertAlmostEqual(limitation_dissipation_w(28.0, 4.0, 1.5), 36.0, places=9)

    def test_the_energy_is_the_dissipation_over_the_whole_delay(self):
        self.assertAlmostEqual(limitation_energy_j(36.0, 0.01), 0.36, places=9)

    def test_a_zero_length_delay_is_refused(self):
        with self.assertRaises(ValueError):
            limitation_energy_j(36.0, 0.0)

    def test_a_non_numeric_bus_voltage_is_refused(self):
        with self.assertRaises(ValueError):
            limitation_dissipation_w("28", 4.0, 1.5)


class ThermalTests(unittest.TestCase):
    def test_a_pulse_one_time_constant_long_sees_most_of_the_path(self):
        self.assertAlmostEqual(
            transient_thermal_impedance(1.0, 1.0, 1.0), ONE_MINUS_INVERSE_E, places=9
        )

    def test_a_short_pulse_sees_far_less_than_the_steady_state(self):
        self.assertLess(transient_thermal_impedance(20.0, 1.0, 0.01), 1.0)

    def test_a_long_pulse_approaches_the_steady_state(self):
        self.assertAlmostEqual(
            transient_thermal_impedance(20.0, 1.0, 40.0), 20.0, places=9
        )

    def test_the_impedance_never_exceeds_the_steady_state(self):
        # A single-pole path approaches its steady state from below and then
        # saturates on it. Below a few tens of time constants the impedance
        # is strictly under the steady state; at a hundred of them exp() is
        # around 4e-44, so 1 - exp() is exactly 1.0 in binary64 whatever
        # value libm returns, and the impedance is exactly the steady state.
        # Both are the contract: assert them separately rather than behind
        # one <= that hides which case is which.
        for duration in (0.001, 0.1, 1.0, 10.0):
            self.assertLess(
                transient_thermal_impedance(20.0, 1.0, duration), 20.0
            )
        self.assertEqual(transient_thermal_impedance(20.0, 1.0, 100.0), 20.0)

    def test_a_zero_time_constant_is_refused(self):
        with self.assertRaises(ValueError):
            transient_thermal_impedance(20.0, 0.0, 1.0)

    def test_the_junction_sits_the_rise_above_its_mounting_point(self):
        self.assertAlmostEqual(junction_temperature_c(36.0, 0.2, 40.0), 47.2, places=9)

    def test_a_cold_mounting_reference_is_accepted(self):
        self.assertAlmostEqual(junction_temperature_c(10.0, 2.0, -30.0), -10.0, places=9)

    def test_a_non_positive_thermal_impedance_is_refused(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(36.0, 0.0, 40.0)


class DeratingTests(unittest.TestCase):
    def test_a_derated_current_rating_is_the_factor_times_the_rating(self):
        self.assertAlmostEqual(derated_limit(4.0, 0.75), 3.0, places=9)

    def test_a_factor_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            derated_limit(4.0, 1.25)

    def test_a_zero_factor_is_refused(self):
        with self.assertRaises(ValueError):
            derated_limit(4.0, 0.0)

    def test_the_junction_factor_derates_the_rise_not_the_reading(self):
        self.assertAlmostEqual(
            derated_junction_limit_c(150.0, 40.0, 0.8), 128.0, places=9
        )

    def test_a_rated_junction_below_the_mounting_point_is_refused(self):
        with self.assertRaises(ValueError):
            derated_junction_limit_c(30.0, 40.0, 0.8)

    def test_the_default_factors_are_all_conservative(self):
        for factor in (
            DEFAULT_CURRENT_DERATING,
            DEFAULT_VOLTAGE_DERATING,
            DEFAULT_JUNCTION_DERATING,
        ):
            self.assertGreater(factor, 0.0)
            self.assertLess(factor, 1.0)

    def test_the_margin_is_positive_below_the_limit_and_negative_above_it(self):
        self.assertAlmostEqual(margin_fraction(1.5, 3.0), 0.5, places=9)
        self.assertLess(margin_fraction(4.0, 3.0), 0.0)


class SafeOperatingAreaTests(unittest.TestCase):
    def test_a_curve_point_returns_its_own_current(self):
        self.assertAlmostEqual(soa_boundary_current_a(SOA_10MS, 10.0), 20.0, places=9)
        self.assertAlmostEqual(soa_boundary_current_a(SOA_10MS, 40.0), 5.0, places=9)

    def test_the_geometric_midpoint_returns_the_geometric_mean(self):
        self.assertAlmostEqual(
            soa_boundary_current_a(SOA_10MS, 20.0), math.sqrt(20.0 * 5.0), places=9
        )

    def test_the_boundary_falls_as_the_voltage_rises(self):
        previous = soa_boundary_current_a(SOA_10MS, 10.0)
        for voltage in (12.0, 16.0, 24.0, 32.0, 40.0):
            current = soa_boundary_current_a(SOA_10MS, voltage)
            self.assertLess(current, previous)
            previous = current

    def test_a_voltage_beyond_the_curve_is_not_extrapolated(self):
        with self.assertRaises(ValueError):
            soa_boundary_current_a(SOA_10MS, 80.0)

    def test_a_curve_with_one_point_is_refused(self):
        with self.assertRaises(ValueError):
            soa_boundary_current_a([(10.0, 20.0)], 10.0)

    def test_a_malformed_curve_point_is_refused(self):
        with self.assertRaises(ValueError):
            soa_boundary_current_a([(10.0, 20.0), (40.0,)], 20.0)

    def test_two_points_at_the_same_voltage_are_refused(self):
        with self.assertRaises(ValueError):
            soa_boundary_current_a([(10.0, 20.0), (10.0, 5.0)], 10.0)

    def test_the_span_is_the_lowest_and_highest_voltage_of_the_curve(self):
        low, high = soa_curve_span_v(SOA_10MS)
        self.assertAlmostEqual(low, 10.0, places=9)
        self.assertAlmostEqual(high, 40.0, places=9)

    def test_coverage_follows_the_span_at_its_edges(self):
        self.assertTrue(soa_voltage_is_covered(SOA_10MS, 10.0))
        self.assertTrue(soa_voltage_is_covered(SOA_10MS, 40.0))
        self.assertFalse(soa_voltage_is_covered(SOA_10MS, 9.0))
        self.assertFalse(soa_voltage_is_covered(SOA_10MS, 41.0))

    def test_the_curve_may_arrive_in_any_order(self):
        reversed_curve = list(reversed(SOA_10MS))
        self.assertAlmostEqual(
            soa_boundary_current_a(reversed_curve, 20.0),
            soa_boundary_current_a(SOA_10MS, 20.0),
            places=9,
        )


class AssessmentTests(unittest.TestCase):
    def test_a_short_limitation_event_stays_within_every_rating(self):
        result = assess_limitation_mode(_case())
        self.assertEqual(result["verdict"], WITHIN_RATINGS)
        self.assertTrue(result["within_ratings"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["mode"], MODE_LIMITATION)

    def test_the_reported_dissipation_and_energy_match_the_condition(self):
        result = assess_limitation_mode(_case())
        self.assertAlmostEqual(result["pass_element_voltage_v"], 24.0, places=9)
        self.assertAlmostEqual(result["dissipation_w"], 36.0, places=9)
        self.assertAlmostEqual(result["energy_j"], 0.36, places=9)

    def test_the_derated_limits_are_reported_alongside_the_verdict(self):
        result = assess_limitation_mode(_case())
        self.assertAlmostEqual(result["derated_current_limit_a"], 3.0, places=9)
        self.assertAlmostEqual(result["derated_voltage_limit_v"], 45.0, places=9)
        self.assertAlmostEqual(result["derated_junction_limit_c"], 128.0, places=9)

    def test_a_limited_current_exactly_at_the_derated_rating_is_accepted(self):
        result = assess_limitation_mode(_case(limit_current_a=3.0))
        self.assertAlmostEqual(result["derated_current_limit_a"], 3.0, places=9)
        self.assertAlmostEqual(result["current_margin_fraction"], 0.0, places=9)
        self.assertFalse(any("derated current rating" in f for f in result["findings"]))

    def test_a_limited_current_above_the_derated_rating_is_flagged(self):
        result = assess_limitation_mode(_case(limit_current_a=3.5))
        self.assertEqual(result["verdict"], BEYOND_RATINGS)
        self.assertTrue(any("derated current rating" in f for f in result["findings"]))
        self.assertLess(result["current_margin_fraction"], 0.0)

    def test_a_hard_short_on_a_high_bus_passes_the_derated_voltage_rating(self):
        result = assess_limitation_mode(
            _case(bus_voltage_v=60.0, output_voltage_v=0.0, soa_curve=None)
        )
        self.assertEqual(result["verdict"], BEYOND_RATINGS)
        self.assertTrue(any("derated voltage rating" in f for f in result["findings"]))

    def test_a_drop_outside_the_curve_span_is_reported_not_extrapolated(self):
        result = assess_limitation_mode(_case(bus_voltage_v=60.0, output_voltage_v=0.0))
        self.assertIsNone(result["soa_boundary_current_a"])
        self.assertTrue(any("says nothing at" in f for f in result["findings"]))

    def test_a_long_trip_off_delay_cooks_the_junction(self):
        result = assess_limitation_mode(_case(trip_off_delay_s=5.0, soa_curve=None))
        self.assertEqual(result["verdict"], BEYOND_RATINGS)
        self.assertTrue(any("derated ceiling" in f for f in result["findings"]))
        self.assertGreater(result["junction_temperature_c"], 128.0)

    def test_the_same_condition_held_briefly_stays_under_the_ceiling(self):
        result = assess_limitation_mode(_case(trip_off_delay_s=0.001, soa_curve=None))
        self.assertLess(result["junction_temperature_c"], 128.0)

    def test_a_current_inside_the_rating_can_still_be_outside_the_operating_area(self):
        result = assess_limitation_mode(_case(limit_current_a=10.0, rated_current_a=20.0))
        self.assertEqual(result["verdict"], BEYOND_RATINGS)
        self.assertTrue(any("safe operating area" in f for f in result["findings"]))
        self.assertAlmostEqual(
            result["soa_boundary_current_a"],
            soa_boundary_current_a(SOA_10MS, 24.0),
            places=9,
        )

    def test_a_case_without_a_curve_reports_no_operating_area_boundary(self):
        result = assess_limitation_mode(_case(soa_curve=None))
        self.assertIsNone(result["soa_boundary_current_a"])

    def test_a_device_that_never_entered_limitation_is_reported_as_such(self):
        result = assess_limitation_mode(_case(demanded_current_a=1.0))
        self.assertEqual(result["mode"], MODE_SWITCH)
        self.assertTrue(any("switch mode" in f for f in result["findings"]))

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_limitation_mode([28.0, 4.0])

    def test_a_missing_thermal_time_constant_is_refused(self):
        case = _case()
        del case["thermal_time_constant_s"]
        with self.assertRaises(ValueError):
            assess_limitation_mode(case)

    def test_a_derating_factor_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            assess_limitation_mode(_case(current_derating_factor=1.5))

    def test_the_assessment_does_not_mutate_the_caller_case(self):
        case = _case()
        before = copy.deepcopy(case)
        assess_limitation_mode(case)
        self.assertEqual(case, before)


if __name__ == "__main__":
    unittest.main()
