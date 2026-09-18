#!/usr/bin/env python3
"""Contract test for the load input filter charge time (offline)."""

import copy
import unittest

from e2020_input_filter_charge_time_logic import (
    DEFAULT_CHARGE_POLICY,
    DEFAULT_CONDITIONS,
    DEFAULT_FILTER_STAGES,
    FINDING_NO_CURRENT,
    FINDING_UTILISATION,
    FINDING_WINDOW,
    VERDICT_CHARGED,
    VERDICT_NOT_CHARGED,
    VERDICT_NO_CHARGING,
    assess_filter_charge,
    filter_charge_time_s,
    largest_supportable_capacitance_f,
    net_charging_current_a,
    total_filter_capacitance_f,
    validate_charge_policy,
    validate_conditions,
    validate_filter,
    validate_filter_stage,
    window_utilisation,
)


def _stages(*extra):
    rows = [copy.deepcopy(s) for s in DEFAULT_FILTER_STAGES]
    rows.extend(copy.deepcopy(e) for e in extra)
    return rows


def _conditions(**overrides):
    case = copy.deepcopy(DEFAULT_CONDITIONS)
    case.update(overrides)
    return case


def _single(capacitance_f):
    return [{"name": "only-stage", "capacitance_f": capacitance_f}]


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_charge_policy(DEFAULT_CHARGE_POLICY), DEFAULT_CHARGE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_charge_policy(["charge_time_margin"])

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_charge_policy(dict(DEFAULT_CHARGE_POLICY, charge_time_margin=0.8))

    def test_advisory_ceiling_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_charge_policy(
                dict(DEFAULT_CHARGE_POLICY, utilisation_advisory_ceiling=1.2)
            )

    def test_zero_advisory_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_charge_policy(
                dict(DEFAULT_CHARGE_POLICY, utilisation_advisory_ceiling=0.0)
            )


class FilterValidationTests(unittest.TestCase):
    def test_default_filter_validates(self):
        rows = validate_filter(DEFAULT_FILTER_STAGES)
        self.assertEqual(len(rows), len(DEFAULT_FILTER_STAGES))

    def test_empty_filter_rejected(self):
        with self.assertRaises(ValueError):
            validate_filter([])

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_filter({"name": "x", "capacitance_f": 1.0e-6})

    def test_stage_missing_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            validate_filter_stage({"name": "x"})

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            validate_filter_stage({"name": "x", "capacitance_f": 0.0})

    def test_negative_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            validate_filter_stage({"name": "x", "capacitance_f": -1.0e-6})

    def test_boolean_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            validate_filter_stage({"name": "x", "capacitance_f": True})

    def test_blank_stage_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_filter_stage({"name": "   ", "capacitance_f": 1.0e-6})

    def test_repeated_stage_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_filter(
                [
                    {"name": "bulk-hold-up", "capacitance_f": 1.0e-6},
                    {"name": "bulk-hold-up", "capacitance_f": 2.0e-6},
                ]
            )


class ConditionValidationTests(unittest.TestCase):
    def test_default_conditions_validate(self):
        case = validate_conditions(DEFAULT_CONDITIONS)
        self.assertAlmostEqual(case["bus_voltage_v"], 28.0, places=12)

    def test_missing_window_rejected(self):
        case = _conditions()
        del case["charging_window_s"]
        with self.assertRaises(ValueError):
            validate_conditions(case)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions(_conditions(charging_window_s=0.0))

    def test_negative_load_draw_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions(_conditions(load_draw_during_charge_a=-0.1))

    def test_zero_load_draw_accepted(self):
        case = validate_conditions(_conditions(load_draw_during_charge_a=0.0))
        self.assertAlmostEqual(case["load_draw_during_charge_a"], 0.0, places=12)

    def test_non_mapping_conditions_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions("28 V")


class CapacitanceTests(unittest.TestCase):
    def test_total_is_every_stage_in_parallel(self):
        expected = sum(s["capacitance_f"] for s in DEFAULT_FILTER_STAGES)
        self.assertAlmostEqual(
            total_filter_capacitance_f(DEFAULT_FILTER_STAGES), expected, places=15
        )

    def test_total_exceeds_the_largest_single_stage(self):
        largest = max(s["capacitance_f"] for s in DEFAULT_FILTER_STAGES)
        self.assertGreater(total_filter_capacitance_f(DEFAULT_FILTER_STAGES), largest)

    def test_stage_shares_sum_to_one(self):
        result = assess_filter_charge(DEFAULT_FILTER_STAGES, DEFAULT_CONDITIONS)
        self.assertAlmostEqual(
            sum(s["share"] for s in result["stage_shares"]), 1.0, places=12
        )


class NetCurrentTests(unittest.TestCase):
    def test_net_current_is_the_held_current_less_the_load_draw(self):
        self.assertAlmostEqual(net_charging_current_a(2.4, 0.15), 2.25, places=12)

    def test_net_current_can_reach_zero_without_raising(self):
        self.assertAlmostEqual(net_charging_current_a(2.4, 2.4), 0.0, places=12)

    def test_net_current_can_go_negative_without_raising(self):
        self.assertLess(net_charging_current_a(2.4, 3.0), 0.0)

    def test_non_positive_held_current_rejected(self):
        with self.assertRaises(ValueError):
            net_charging_current_a(0.0, 0.15)


class ChargeTimeTests(unittest.TestCase):
    def test_charge_time_is_capacitance_times_voltage_over_current(self):
        self.assertAlmostEqual(
            filter_charge_time_s(207.0e-6, 28.0, 2.25),
            207.0e-6 * 28.0 / 2.25,
            places=12,
        )

    def test_charge_time_falls_with_a_larger_net_current(self):
        slow = filter_charge_time_s(207.0e-6, 28.0, 1.0)
        fast = filter_charge_time_s(207.0e-6, 28.0, 2.25)
        self.assertGreater(slow, fast)

    def test_charge_time_rises_with_the_bus_voltage(self):
        self.assertGreater(
            filter_charge_time_s(207.0e-6, 50.0, 2.25),
            filter_charge_time_s(207.0e-6, 28.0, 2.25),
        )

    def test_zero_charging_current_rejected(self):
        with self.assertRaises(ValueError):
            filter_charge_time_s(207.0e-6, 28.0, 0.0)

    def test_window_utilisation_is_the_time_over_the_window(self):
        self.assertAlmostEqual(window_utilisation(4.0e-3, 8.0e-3), 0.5, places=12)

    def test_window_utilisation_rejects_a_zero_window(self):
        with self.assertRaises(ValueError):
            window_utilisation(4.0e-3, 0.0)


class SupportableCapacitanceTests(unittest.TestCase):
    def test_largest_supportable_capacitance_is_positive(self):
        self.assertGreater(largest_supportable_capacitance_f(DEFAULT_CONDITIONS), 0.0)

    def test_a_filter_at_the_supportable_figure_exactly_fits_the_window(self):
        biggest = largest_supportable_capacitance_f(DEFAULT_CONDITIONS)
        result = assess_filter_charge(_single(biggest), DEFAULT_CONDITIONS)
        self.assertAlmostEqual(
            result["required_time_s"], DEFAULT_CONDITIONS["charging_window_s"], places=9
        )
        self.assertEqual(result["verdict"], VERDICT_CHARGED)

    def test_supportable_capacitance_is_zero_when_nothing_charges(self):
        self.assertAlmostEqual(
            largest_supportable_capacitance_f(
                _conditions(load_draw_during_charge_a=2.4)
            ),
            0.0,
            places=15,
        )

    def test_a_wider_window_supports_a_bigger_filter(self):
        wide = largest_supportable_capacitance_f(_conditions(charging_window_s=16.0e-3))
        narrow = largest_supportable_capacitance_f(DEFAULT_CONDITIONS)
        self.assertGreater(wide, narrow)


class AssessmentTests(unittest.TestCase):
    def test_nominal_filter_charges_inside_the_window(self):
        result = assess_filter_charge(DEFAULT_FILTER_STAGES, DEFAULT_CONDITIONS)
        self.assertEqual(result["verdict"], VERDICT_CHARGED)
        self.assertEqual(result["findings"], [])
        self.assertGreater(result["window_slack_s"], 0.0)

    def test_an_oversized_bulk_stage_misses_the_window(self):
        result = assess_filter_charge(
            _stages({"name": "extra-bulk", "capacitance_f": 4.7e-3}),
            DEFAULT_CONDITIONS,
        )
        self.assertEqual(result["verdict"], VERDICT_NOT_CHARGED)
        self.assertTrue(any(FINDING_WINDOW in f for f in result["findings"]))

    def test_a_load_draw_equal_to_the_held_current_never_charges(self):
        result = assess_filter_charge(
            DEFAULT_FILTER_STAGES, _conditions(load_draw_during_charge_a=2.4)
        )
        self.assertEqual(result["verdict"], VERDICT_NO_CHARGING)
        self.assertIsNone(result["charge_time_s"])
        self.assertTrue(any(FINDING_NO_CURRENT in f for f in result["findings"]))

    def test_a_load_draw_above_the_held_current_never_charges(self):
        result = assess_filter_charge(
            DEFAULT_FILTER_STAGES, _conditions(load_draw_during_charge_a=3.0)
        )
        self.assertEqual(result["verdict"], VERDICT_NO_CHARGING)
        self.assertLess(result["net_charging_current_a"], 0.0)

    def test_the_load_draw_lengthens_the_charge(self):
        quiet = assess_filter_charge(
            DEFAULT_FILTER_STAGES, _conditions(load_draw_during_charge_a=0.0)
        )
        busy = assess_filter_charge(DEFAULT_FILTER_STAGES, DEFAULT_CONDITIONS)
        self.assertGreater(busy["charge_time_s"], quiet["charge_time_s"])

    def test_a_nearly_full_window_raises_an_advisory_not_a_finding(self):
        biggest = largest_supportable_capacitance_f(DEFAULT_CONDITIONS)
        result = assess_filter_charge(_single(biggest * 0.95), DEFAULT_CONDITIONS)
        self.assertEqual(result["verdict"], VERDICT_CHARGED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(FINDING_UTILISATION in a for a in result["advisories"]))

    def test_a_comfortable_filter_raises_no_advisory(self):
        result = assess_filter_charge(DEFAULT_FILTER_STAGES, DEFAULT_CONDITIONS)
        self.assertEqual(result["advisories"], [])

    def test_a_tighter_margin_can_turn_a_pass_into_a_finding(self):
        biggest = largest_supportable_capacitance_f(DEFAULT_CONDITIONS)
        stages = _single(biggest * 0.95)
        loose = assess_filter_charge(stages, DEFAULT_CONDITIONS)
        strict = assess_filter_charge(
            stages, DEFAULT_CONDITIONS, dict(DEFAULT_CHARGE_POLICY, charge_time_margin=2.0)
        )
        self.assertEqual(loose["verdict"], VERDICT_CHARGED)
        self.assertEqual(strict["verdict"], VERDICT_NOT_CHARGED)

    def test_utilisation_and_slack_agree_with_the_window(self):
        result = assess_filter_charge(DEFAULT_FILTER_STAGES, DEFAULT_CONDITIONS)
        rebuilt = result["charging_window_s"] * (1.0 - result["window_utilisation"])
        self.assertAlmostEqual(rebuilt, result["window_slack_s"], places=12)

    def test_assessment_rejects_a_broken_filter(self):
        with self.assertRaises(ValueError):
            assess_filter_charge([], DEFAULT_CONDITIONS)

    def test_assessment_rejects_broken_conditions(self):
        with self.assertRaises(ValueError):
            assess_filter_charge(
                DEFAULT_FILTER_STAGES, _conditions(held_limiting_current_a=0.0)
            )

    def test_assessment_names_every_stage_it_totalled(self):
        result = assess_filter_charge(DEFAULT_FILTER_STAGES, DEFAULT_CONDITIONS)
        self.assertEqual(
            [s["name"] for s in result["stage_shares"]],
            [s["name"] for s in DEFAULT_FILTER_STAGES],
        )


if __name__ == "__main__":
    unittest.main()
