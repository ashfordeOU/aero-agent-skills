#!/usr/bin/env python3
"""Contract test for the load response to a dissipative switch failure."""

import copy
import unittest

from e2020_load_response_to_switch_failure_logic import (
    ADVISORY_STABILITY_MARGIN,
    CATEGORY_DEGRADED,
    CATEGORY_INHIBITED,
    CATEGORY_UNDERVOLTED,
    CATEGORY_UNSUSTAINED,
    DEFAULT_LOAD,
    DEFAULT_RESPONSE_POLICY,
    DEFAULT_SWITCH,
    FINDING_CURRENT,
    FINDING_DISSIPATION,
    FINDING_NO_INHIBIT,
    FINDING_RETRIGGER,
    FINDING_STABILITY,
    FINDING_UNSUSTAINED,
    MODEL_CONSTANT_CURRENT,
    MODEL_CONSTANT_POWER,
    MODEL_RESISTIVE,
    assess_load_response,
    inhibited_operating_point,
    maximum_deliverable_power_w,
    solve_operating_point,
    stability_boundary_voltage_v,
    switch_dissipation_w,
    validate_load,
    validate_response_policy,
    validate_switch,
)

BUS_V = 28.0


def _load(**overrides):
    case = copy.deepcopy(DEFAULT_LOAD)
    case.update(overrides)
    return case


def _switch(**overrides):
    device = copy.deepcopy(DEFAULT_SWITCH)
    device.update(overrides)
    return device


def _constant_current(amps, **overrides):
    return _load(
        model=MODEL_CONSTANT_CURRENT, constant_current_a=amps, **overrides
    )


def _resistive(ohms, **overrides):
    return _load(model=MODEL_RESISTIVE, load_resistance_ohm=ohms, **overrides)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_response_policy(DEFAULT_RESPONSE_POLICY), DEFAULT_RESPONSE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_policy(0.8)

    def test_derating_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_policy(
                dict(DEFAULT_RESPONSE_POLICY, dissipation_derating=1.2)
            )

    def test_stability_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_policy(
                dict(DEFAULT_RESPONSE_POLICY, stability_voltage_margin=0.9)
            )


class SwitchValidationTests(unittest.TestCase):
    def test_default_switch_validates(self):
        device = validate_switch(DEFAULT_SWITCH)
        self.assertAlmostEqual(device["failed_series_resistance_ohm"], 12.0, places=12)

    def test_switch_missing_a_rating_rejected(self):
        device = _switch()
        del device["dissipation_rating_w"]
        with self.assertRaises(ValueError):
            validate_switch(device)

    def test_zero_series_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_switch(failed_series_resistance_ohm=0.0))

    def test_negative_series_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_switch(failed_series_resistance_ohm=-1.0))

    def test_blank_switch_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_switch(name="  "))


class LoadValidationTests(unittest.TestCase):
    def test_default_load_validates(self):
        case = validate_load(DEFAULT_LOAD)
        self.assertEqual(case["model"], MODEL_CONSTANT_POWER)

    def test_a_normalised_load_revalidates_unchanged(self):
        once = validate_load(DEFAULT_LOAD)
        twice = validate_load(once)
        self.assertAlmostEqual(
            twice["parameter_value"], once["parameter_value"], places=12
        )

    def test_unknown_model_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(_load(model="constant-impedance"))

    def test_model_without_its_parameter_rejected(self):
        case = _load(model=MODEL_RESISTIVE)
        with self.assertRaises(ValueError):
            validate_load(case)

    def test_non_boolean_inhibit_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(_load(has_undervoltage_inhibit="yes"))

    def test_inverted_inhibit_hysteresis_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(
                _load(undervoltage_threshold_v=22.0, inhibit_release_threshold_v=20.0)
            )

    def test_equal_thresholds_accepted_as_zero_hysteresis(self):
        case = validate_load(
            _load(undervoltage_threshold_v=20.0, inhibit_release_threshold_v=20.0)
        )
        self.assertAlmostEqual(
            case["inhibit_release_threshold_v"], 20.0, places=12
        )

    def test_negative_inhibit_draw_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(_load(inhibit_draw_a=-0.01))

    def test_zero_inhibit_draw_accepted(self):
        self.assertAlmostEqual(
            validate_load(_load(inhibit_draw_a=0.0))["inhibit_draw_a"], 0.0, places=12
        )

    def test_boolean_power_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(_load(constant_power_w=True))

    def test_non_mapping_load_rejected(self):
        with self.assertRaises(ValueError):
            validate_load("payload-unit")


class ElectricalHelperTests(unittest.TestCase):
    def test_dissipation_is_current_squared_times_resistance(self):
        self.assertAlmostEqual(switch_dissipation_w(0.5, 12.0), 3.0, places=12)

    def test_dissipation_of_no_current_is_zero(self):
        self.assertAlmostEqual(switch_dissipation_w(0.0, 12.0), 0.0, places=12)

    def test_dissipation_rejects_a_zero_resistance(self):
        with self.assertRaises(ValueError):
            switch_dissipation_w(0.5, 0.0)

    def test_maximum_deliverable_power_is_v_squared_over_four_r(self):
        self.assertAlmostEqual(
            maximum_deliverable_power_w(28.0, 12.0), 28.0 * 28.0 / 48.0, places=12
        )

    def test_maximum_deliverable_power_falls_as_the_failure_hardens(self):
        self.assertGreater(
            maximum_deliverable_power_w(28.0, 6.0),
            maximum_deliverable_power_w(28.0, 24.0),
        )

    def test_stability_boundary_is_half_the_bus_voltage(self):
        self.assertAlmostEqual(stability_boundary_voltage_v(28.0), 14.0, places=12)

    def test_stability_boundary_rejects_a_zero_bus(self):
        with self.assertRaises(ValueError):
            stability_boundary_voltage_v(0.0)


class OperatingPointTests(unittest.TestCase):
    def test_constant_power_point_satisfies_its_own_equation(self):
        point = solve_operating_point(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertTrue(point["sustained"])
        rebuilt = point["load_voltage_v"] + point["load_current_a"] * 12.0
        self.assertAlmostEqual(rebuilt, BUS_V, places=9)

    def test_constant_power_takes_the_upper_root(self):
        point = solve_operating_point(_load(constant_power_w=15.0), DEFAULT_SWITCH, BUS_V)
        self.assertAlmostEqual(point["load_voltage_v"], 18.0, places=9)

    def test_constant_power_current_rises_as_the_voltage_droops(self):
        light = solve_operating_point(_load(constant_power_w=6.0), DEFAULT_SWITCH, BUS_V)
        heavy = solve_operating_point(_load(constant_power_w=15.0), DEFAULT_SWITCH, BUS_V)
        self.assertGreater(heavy["load_current_a"], light["load_current_a"])
        self.assertGreater(light["load_voltage_v"], heavy["load_voltage_v"])

    def test_constant_power_beyond_the_deliverable_power_has_no_point(self):
        point = solve_operating_point(_load(constant_power_w=20.0), DEFAULT_SWITCH, BUS_V)
        self.assertFalse(point["sustained"])
        self.assertIsNone(point["load_voltage_v"])

    def test_constant_power_at_the_deliverable_power_sits_on_the_boundary(self):
        edge = maximum_deliverable_power_w(BUS_V, 12.0)
        point = solve_operating_point(_load(constant_power_w=edge), DEFAULT_SWITCH, BUS_V)
        self.assertTrue(point["sustained"])
        self.assertAlmostEqual(point["load_voltage_v"], 14.0, places=9)
        self.assertTrue(point["at_stability_boundary"])

    def test_constant_current_point_is_a_fixed_drop(self):
        point = solve_operating_point(_constant_current(0.5), DEFAULT_SWITCH, BUS_V)
        self.assertAlmostEqual(point["load_voltage_v"], 22.0, places=9)
        self.assertAlmostEqual(point["load_current_a"], 0.5, places=12)

    def test_constant_current_beyond_the_bus_has_no_point(self):
        point = solve_operating_point(_constant_current(3.0), DEFAULT_SWITCH, BUS_V)
        self.assertFalse(point["sustained"])

    def test_resistive_point_is_a_divider(self):
        point = solve_operating_point(_resistive(100.0), DEFAULT_SWITCH, BUS_V)
        self.assertAlmostEqual(point["load_voltage_v"], BUS_V * 100.0 / 112.0, places=9)

    def test_resistive_load_droops_less_than_a_constant_power_load(self):
        resistive = solve_operating_point(_resistive(37.5), DEFAULT_SWITCH, BUS_V)
        constant = solve_operating_point(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertGreater(resistive["load_voltage_v"], constant["load_voltage_v"])

    def test_a_harder_failure_droops_the_load_further(self):
        soft = solve_operating_point(DEFAULT_LOAD, _switch(failed_series_resistance_ohm=2.0), BUS_V)
        hard = solve_operating_point(DEFAULT_LOAD, _switch(failed_series_resistance_ohm=12.0), BUS_V)
        self.assertGreater(soft["load_voltage_v"], hard["load_voltage_v"])


class InhibitTests(unittest.TestCase):
    def test_inhibited_input_recovers_towards_the_bus(self):
        point = inhibited_operating_point(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertAlmostEqual(point["load_voltage_v"], BUS_V - 0.02 * 12.0, places=9)
        self.assertLess(point["load_voltage_v"], BUS_V)

    def test_a_recovering_input_restarts_the_load(self):
        point = inhibited_operating_point(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertTrue(point["restarts"])

    def test_a_heavy_inhibit_draw_keeps_the_load_off(self):
        point = inhibited_operating_point(
            _load(inhibit_draw_a=0.6), DEFAULT_SWITCH, BUS_V
        )
        self.assertFalse(point["restarts"])

    def test_inhibited_dissipation_is_small(self):
        point = inhibited_operating_point(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertLess(point["switch_dissipation_w"], 0.01)


class ResponseTests(unittest.TestCase):
    def test_a_light_load_rides_the_failure_at_a_degraded_voltage(self):
        result = assess_load_response(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertEqual(result["category"], CATEGORY_DEGRADED)
        self.assertEqual(result["findings"], [])

    def test_voltage_retention_is_the_share_of_the_bus_that_survives(self):
        result = assess_load_response(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertAlmostEqual(
            result["voltage_retention"],
            result["operating_point"]["load_voltage_v"] / BUS_V,
            places=12,
        )

    def test_an_undeliverable_load_reports_a_collapsed_feed(self):
        result = assess_load_response(
            _load(constant_power_w=20.0), DEFAULT_SWITCH, BUS_V
        )
        self.assertEqual(result["category"], CATEGORY_UNSUSTAINED)
        self.assertTrue(any(FINDING_UNSUSTAINED in f for f in result["findings"]))
        self.assertIsNone(result["operating_point"]["load_voltage_v"])

    def test_a_droop_below_the_threshold_inhibits_a_load_that_can(self):
        result = assess_load_response(
            _load(constant_power_w=15.0), DEFAULT_SWITCH, BUS_V
        )
        self.assertEqual(result["category"], CATEGORY_INHIBITED)
        self.assertIsNotNone(result["inhibited_point"])

    def test_an_inhibiting_load_that_recovers_is_reported_as_cycling(self):
        result = assess_load_response(
            _load(constant_power_w=15.0), DEFAULT_SWITCH, BUS_V
        )
        self.assertTrue(any(FINDING_RETRIGGER in f for f in result["findings"]))

    def test_a_load_without_an_inhibit_keeps_drawing_undervolted(self):
        result = assess_load_response(
            _load(constant_power_w=15.0, has_undervoltage_inhibit=False),
            DEFAULT_SWITCH,
            BUS_V,
        )
        self.assertEqual(result["category"], CATEGORY_UNDERVOLTED)
        self.assertTrue(any(FINDING_NO_INHIBIT in f for f in result["findings"]))

    def test_heat_beyond_the_derated_rating_is_a_finding(self):
        result = assess_load_response(
            _load(constant_power_w=15.0), DEFAULT_SWITCH, BUS_V
        )
        self.assertTrue(any(FINDING_DISSIPATION in f for f in result["findings"]))

    def test_heat_exactly_on_the_derated_rating_is_accepted(self):
        point = solve_operating_point(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        derating = float(DEFAULT_RESPONSE_POLICY["dissipation_derating"])
        rating = point["switch_dissipation_w"] / derating
        result = assess_load_response(
            DEFAULT_LOAD, _switch(dissipation_rating_w=rating), BUS_V
        )
        self.assertAlmostEqual(
            result["allowed_dissipation_w"], point["switch_dissipation_w"], places=9
        )
        self.assertFalse(any(FINDING_DISSIPATION in f for f in result["findings"]))

    def test_current_beyond_the_input_rating_is_a_finding(self):
        result = assess_load_response(
            _load(constant_power_w=15.0, input_current_rating_a=0.4),
            DEFAULT_SWITCH,
            BUS_V,
        )
        self.assertTrue(any(FINDING_CURRENT in f for f in result["findings"]))

    def test_an_operating_point_on_the_boundary_is_a_finding(self):
        edge = maximum_deliverable_power_w(BUS_V, 12.0)
        result = assess_load_response(
            _load(constant_power_w=edge), DEFAULT_SWITCH, BUS_V
        )
        self.assertTrue(any(FINDING_STABILITY in f for f in result["findings"]))

    def test_a_point_just_above_the_boundary_is_only_an_advisory(self):
        result = assess_load_response(
            _load(constant_power_w=16.25), DEFAULT_SWITCH, BUS_V
        )
        self.assertAlmostEqual(
            result["operating_point"]["load_voltage_v"], 15.0, places=9
        )
        self.assertFalse(any(FINDING_STABILITY in f for f in result["findings"]))
        self.assertTrue(
            any(ADVISORY_STABILITY_MARGIN in a for a in result["advisories"])
        )

    def test_a_comfortable_point_raises_no_stability_advisory(self):
        result = assess_load_response(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertEqual(result["advisories"], [])

    def test_a_resistive_load_survives_a_failure_that_collapses_a_constant_power_one(self):
        collapsed = assess_load_response(
            _load(constant_power_w=20.0), DEFAULT_SWITCH, BUS_V
        )
        benign = assess_load_response(_resistive(60.0), DEFAULT_SWITCH, BUS_V)
        self.assertEqual(collapsed["category"], CATEGORY_UNSUSTAINED)
        self.assertEqual(benign["category"], CATEGORY_DEGRADED)

    def test_a_softer_failure_keeps_the_load_in_normal_operation(self):
        result = assess_load_response(
            _load(constant_power_w=15.0), _switch(failed_series_resistance_ohm=1.0), BUS_V
        )
        self.assertEqual(result["category"], CATEGORY_DEGRADED)

    def test_response_rejects_a_broken_switch(self):
        with self.assertRaises(ValueError):
            assess_load_response(
                DEFAULT_LOAD, _switch(dissipation_rating_w=0.0), BUS_V
            )

    def test_response_rejects_a_broken_load(self):
        with self.assertRaises(ValueError):
            assess_load_response(_load(constant_power_w=0.0), DEFAULT_SWITCH, BUS_V)

    def test_response_rejects_a_non_positive_bus_voltage(self):
        with self.assertRaises(ValueError):
            assess_load_response(DEFAULT_LOAD, DEFAULT_SWITCH, 0.0)

    def test_response_names_the_load_and_the_switch_it_looked_at(self):
        result = assess_load_response(DEFAULT_LOAD, DEFAULT_SWITCH, BUS_V)
        self.assertEqual(result["load"], DEFAULT_LOAD["name"])
        self.assertEqual(result["switch"], DEFAULT_SWITCH["name"])


if __name__ == "__main__":
    unittest.main()
