#!/usr/bin/env python3
"""Contract test for the additional series switch provision (offline)."""

import copy
import unittest

from e2020_additional_series_switch_provision_logic import (
    ADVISORY_SHARED_TECHNOLOGY,
    ADVISORY_THIN_INDEPENDENCE,
    ARRANGEMENT_PARALLEL,
    DEFAULT_ADDITIONAL_SWITCH,
    DEFAULT_LINE,
    DEFAULT_MAIN_SWITCH,
    DEFAULT_PROVISION_POLICY,
    FINDING_BREAKING,
    FINDING_CURRENT_RATING,
    FINDING_NOT_IN_SERIES,
    FINDING_RESIDUAL,
    FINDING_SERIES_DROP,
    FINDING_SHARED_COMMAND,
    FINDING_SHARED_DRIVE,
    FINDING_VOLTAGE_RATING,
    VERDICT_ADEQUATE,
    VERDICT_INADEQUATE,
    assess_independence,
    assess_switch_capability,
    evaluate_series_switch_provision,
    residual_stuck_on_probability,
    series_conduction_drop_v,
    validate_line,
    validate_provision_policy,
    validate_switch,
)


def _main(**overrides):
    row = copy.deepcopy(DEFAULT_MAIN_SWITCH)
    row.update(overrides)
    return row


def _aux(**overrides):
    row = copy.deepcopy(DEFAULT_ADDITIONAL_SWITCH)
    row.update(overrides)
    return row


def _line(**overrides):
    row = copy.deepcopy(DEFAULT_LINE)
    row.update(overrides)
    return row


def _policy(**overrides):
    row = copy.deepcopy(DEFAULT_PROVISION_POLICY)
    row.update(overrides)
    return row


class SwitchValidationTests(unittest.TestCase):
    def test_default_main_switch_validates(self):
        row = validate_switch(DEFAULT_MAIN_SWITCH)
        self.assertAlmostEqual(row["continuous_rating_a"], 4.0, places=12)

    def test_non_mapping_switch_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch("a relay")

    def test_switch_missing_a_figure_rejected(self):
        row = _main()
        del row["breaking_capacity_a"]
        with self.assertRaises(ValueError):
            validate_switch(row)

    def test_blank_command_path_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_main(command_path="   "))

    def test_negative_on_state_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_main(on_state_resistance_ohm=-0.01))

    def test_zero_on_state_resistance_accepted(self):
        row = validate_switch(_main(on_state_resistance_ohm=0.0))
        self.assertAlmostEqual(row["on_state_resistance_ohm"], 0.0, places=12)

    def test_probability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_main(stuck_on_probability=1.5))

    def test_boolean_rating_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_main(continuous_rating_a=True))

    def test_switch_that_breaks_less_than_it_carries_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_main(breaking_capacity_a=1.0))

    def test_additional_switch_without_an_arrangement_rejected(self):
        row = _aux()
        del row["arrangement"]
        with self.assertRaises(ValueError):
            validate_switch(row, require_arrangement=True)

    def test_unknown_arrangement_word_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch(_aux(arrangement="anti-series"), require_arrangement=True)

    def test_parallel_arrangement_is_a_valid_word(self):
        row = validate_switch(_aux(arrangement=ARRANGEMENT_PARALLEL), require_arrangement=True)
        self.assertEqual(row["arrangement"], ARRANGEMENT_PARALLEL)


class LineValidationTests(unittest.TestCase):
    def test_default_line_validates(self):
        case = validate_line(DEFAULT_LINE)
        self.assertAlmostEqual(case["load_current_a"], 2.5, places=12)

    def test_line_missing_the_allowable_drop_rejected(self):
        case = _line()
        del case["allowable_drop_v"]
        with self.assertRaises(ValueError):
            validate_line(case)

    def test_zero_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_line(_line(bus_voltage_v=0.0))

    def test_fault_current_below_the_load_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_line(_line(prospective_fault_current_a=1.0))

    def test_non_mapping_line_rejected(self):
        with self.assertRaises(ValueError):
            validate_line(28.0)


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_validates(self):
        rules = validate_provision_policy(DEFAULT_PROVISION_POLICY)
        self.assertAlmostEqual(rules["current_derating_factor"], 0.75, places=12)

    def test_current_derating_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision_policy(_policy(current_derating_factor=1.2))

    def test_voltage_derating_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision_policy(_policy(voltage_derating_factor=1.1))

    def test_common_cause_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision_policy(_policy(common_cause_beta=1.4))

    def test_common_cause_factor_below_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision_policy(_policy(common_cause_beta=-0.1))

    def test_policy_missing_the_allowable_rejected(self):
        rules = _policy()
        del rules["allowable_stuck_on_probability"]
        with self.assertRaises(ValueError):
            validate_provision_policy(rules)


class ConductionDropTests(unittest.TestCase):
    def test_drop_is_the_current_times_the_summed_resistance(self):
        self.assertAlmostEqual(
            series_conduction_drop_v(DEFAULT_MAIN_SWITCH, DEFAULT_ADDITIONAL_SWITCH, 2.5),
            2.5 * (0.035 + 0.020),
            places=12,
        )

    def test_drop_grows_with_the_line_current(self):
        low = series_conduction_drop_v(DEFAULT_MAIN_SWITCH, DEFAULT_ADDITIONAL_SWITCH, 1.0)
        high = series_conduction_drop_v(DEFAULT_MAIN_SWITCH, DEFAULT_ADDITIONAL_SWITCH, 4.0)
        self.assertGreater(high, low)

    def test_zero_line_current_rejected_at_the_drop_call(self):
        with self.assertRaises(ValueError):
            series_conduction_drop_v(DEFAULT_MAIN_SWITCH, DEFAULT_ADDITIONAL_SWITCH, 0.0)

    def test_the_second_device_always_adds_to_the_drop(self):
        both = series_conduction_drop_v(DEFAULT_MAIN_SWITCH, DEFAULT_ADDITIONAL_SWITCH, 2.5)
        ideal = series_conduction_drop_v(
            DEFAULT_MAIN_SWITCH, _aux(on_state_resistance_ohm=0.0), 2.5
        )
        self.assertGreater(both, ideal)


class ResidualProbabilityTests(unittest.TestCase):
    def test_a_zero_common_cause_factor_gives_the_bare_product(self):
        self.assertAlmostEqual(
            residual_stuck_on_probability(2.0e-4, 5.0e-4, 0.0), 1.0e-7, places=15
        )

    def test_a_unity_common_cause_factor_gives_the_larger_probability(self):
        self.assertAlmostEqual(
            residual_stuck_on_probability(2.0e-4, 5.0e-4, 1.0), 5.0e-4, places=15
        )

    def test_residual_rises_with_the_common_cause_factor(self):
        previous = residual_stuck_on_probability(2.0e-4, 5.0e-4, 0.0)
        for beta in (0.05, 0.1, 0.25, 0.5, 0.9):
            current = residual_stuck_on_probability(2.0e-4, 5.0e-4, beta)
            self.assertGreater(current, previous)
            previous = current

    def test_residual_stays_below_the_worse_single_device(self):
        residual = residual_stuck_on_probability(2.0e-4, 5.0e-4, 0.1)
        self.assertLess(residual, 5.0e-4)

    def test_residual_never_falls_below_the_independent_product(self):
        product = 2.0e-4 * 5.0e-4
        # With no shared cause the model IS the independent product: the
        # shared term is exactly zero and (1 - 0) ** 2 is exactly one, so
        # both sides are the same float on every platform - an equality,
        # not a bound. Any shared cause adds a term orders of magnitude
        # larger than the product, so the residual then sits strictly
        # above it.
        self.assertEqual(
            residual_stuck_on_probability(2.0e-4, 5.0e-4, 0.0), product
        )
        for beta in (0.1, 0.5, 1.0):
            self.assertGreater(
                residual_stuck_on_probability(2.0e-4, 5.0e-4, beta), product
            )

    def test_probability_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            residual_stuck_on_probability(-0.1, 5.0e-4, 0.1)

    def test_common_cause_factor_outside_its_range_rejected(self):
        with self.assertRaises(ValueError):
            residual_stuck_on_probability(2.0e-4, 5.0e-4, 1.2)


class IndependenceTests(unittest.TestCase):
    def test_distinct_command_and_drive_read_as_independent(self):
        result = assess_independence(DEFAULT_MAIN_SWITCH, DEFAULT_ADDITIONAL_SWITCH)
        self.assertTrue(result["independent"])
        self.assertEqual(result["findings"], [])

    def test_a_shared_command_path_is_a_finding(self):
        result = assess_independence(
            DEFAULT_MAIN_SWITCH, _aux(command_path=DEFAULT_MAIN_SWITCH["command_path"])
        )
        self.assertFalse(result["independent"])
        self.assertTrue(any(FINDING_SHARED_COMMAND in f for f in result["findings"]))

    def test_a_shared_drive_domain_is_a_finding(self):
        result = assess_independence(
            DEFAULT_MAIN_SWITCH, _aux(drive_domain=DEFAULT_MAIN_SWITCH["drive_domain"])
        )
        self.assertFalse(result["independent"])
        self.assertTrue(any(FINDING_SHARED_DRIVE in f for f in result["findings"]))

    def test_a_shared_technology_is_an_advisory_not_a_finding(self):
        result = assess_independence(
            DEFAULT_MAIN_SWITCH, _aux(technology=DEFAULT_MAIN_SWITCH["technology"])
        )
        self.assertTrue(result["independent"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(ADVISORY_SHARED_TECHNOLOGY in a for a in result["advisories"]))


class CapabilityTests(unittest.TestCase):
    def test_nominal_additional_switch_is_capable(self):
        result = assess_switch_capability(DEFAULT_ADDITIONAL_SWITCH, DEFAULT_LINE)
        self.assertTrue(result["capable"])
        self.assertEqual(result["findings"], [])

    def test_a_small_continuous_rating_is_a_finding(self):
        result = assess_switch_capability(
            _aux(continuous_rating_a=1.0, breaking_capacity_a=12.0), DEFAULT_LINE
        )
        self.assertFalse(result["carries_line_current"])
        self.assertTrue(any(FINDING_CURRENT_RATING in f for f in result["findings"]))

    def test_a_small_voltage_rating_is_a_finding(self):
        result = assess_switch_capability(_aux(voltage_rating_v=20.0), DEFAULT_LINE)
        self.assertFalse(result["holds_off_bus_voltage"])
        self.assertTrue(any(FINDING_VOLTAGE_RATING in f for f in result["findings"]))

    def test_a_breaking_capacity_below_the_fault_current_is_a_finding(self):
        result = assess_switch_capability(
            _aux(breaking_capacity_a=6.0), _line(prospective_fault_current_a=10.0)
        )
        self.assertFalse(result["breaks_fault_current"])
        self.assertTrue(any(FINDING_BREAKING in f for f in result["findings"]))

    def test_a_line_current_exactly_on_the_derated_rating_is_carried(self):
        derated = DEFAULT_ADDITIONAL_SWITCH["continuous_rating_a"] * (
            DEFAULT_PROVISION_POLICY["current_derating_factor"]
        )
        self.assertAlmostEqual(derated, 3.0, places=9)
        result = assess_switch_capability(
            DEFAULT_ADDITIONAL_SWITCH, _line(load_current_a=derated)
        )
        self.assertAlmostEqual(result["current_slack_a"], 0.0, places=9)
        self.assertTrue(result["carries_line_current"])


class ProvisionEvaluationTests(unittest.TestCase):
    def test_nominal_provision_is_adequate(self):
        result = evaluate_series_switch_provision()
        self.assertEqual(result["verdict"], VERDICT_ADEQUATE)
        self.assertEqual(result["findings"], [])

    def test_a_parallel_extra_switch_cannot_open_the_line(self):
        result = evaluate_series_switch_provision(
            additional_switch=_aux(arrangement=ARRANGEMENT_PARALLEL)
        )
        self.assertEqual(result["verdict"], VERDICT_INADEQUATE)
        self.assertFalse(result["in_series"])
        self.assertTrue(any(FINDING_NOT_IN_SERIES in f for f in result["findings"]))

    def test_a_shared_command_path_makes_the_provision_inadequate(self):
        result = evaluate_series_switch_provision(
            additional_switch=_aux(command_path=DEFAULT_MAIN_SWITCH["command_path"])
        )
        self.assertEqual(result["verdict"], VERDICT_INADEQUATE)
        self.assertTrue(any(FINDING_SHARED_COMMAND in f for f in result["findings"]))

    def test_a_large_common_cause_factor_breaches_the_allowable_residual(self):
        result = evaluate_series_switch_provision(policy=_policy(common_cause_beta=0.5))
        self.assertEqual(result["verdict"], VERDICT_INADEQUATE)
        self.assertTrue(any(FINDING_RESIDUAL in f for f in result["findings"]))

    def test_resistive_devices_breach_the_allowable_line_drop(self):
        result = evaluate_series_switch_provision(
            main_switch=_main(on_state_resistance_ohm=0.2),
            additional_switch=_aux(on_state_resistance_ohm=0.2),
        )
        self.assertEqual(result["verdict"], VERDICT_INADEQUATE)
        self.assertTrue(any(FINDING_SERIES_DROP in f for f in result["findings"]))

    def test_a_drop_exactly_on_the_allowable_is_accepted(self):
        drop = series_conduction_drop_v(
            DEFAULT_MAIN_SWITCH, DEFAULT_ADDITIONAL_SWITCH, DEFAULT_LINE["load_current_a"]
        )
        result = evaluate_series_switch_provision(line=_line(allowable_drop_v=drop))
        self.assertAlmostEqual(result["drop_slack_v"], 0.0, places=9)
        self.assertFalse(any(FINDING_SERIES_DROP in f for f in result["findings"]))

    def test_the_provision_improves_on_the_main_switch_alone(self):
        result = evaluate_series_switch_provision()
        self.assertGreater(result["improvement_factor"], 1.0)

    def test_a_shared_cause_dominated_residual_raises_an_advisory(self):
        result = evaluate_series_switch_provision()
        self.assertTrue(any(ADVISORY_THIN_INDEPENDENCE in a for a in result["advisories"]))

    def test_a_zero_common_cause_factor_drops_that_advisory(self):
        result = evaluate_series_switch_provision(policy=_policy(common_cause_beta=0.0))
        self.assertFalse(any(ADVISORY_THIN_INDEPENDENCE in a for a in result["advisories"]))

    def test_residual_margin_shrinks_as_the_common_cause_factor_grows(self):
        loose = evaluate_series_switch_provision(policy=_policy(common_cause_beta=0.02))
        tight = evaluate_series_switch_provision(policy=_policy(common_cause_beta=0.30))
        self.assertGreater(loose["residual_margin"], tight["residual_margin"])

    def test_evaluation_rejects_a_broken_line(self):
        with self.assertRaises(ValueError):
            evaluate_series_switch_provision(line=_line(bus_voltage_v=-28.0))

    def test_evaluation_rejects_a_broken_policy(self):
        with self.assertRaises(ValueError):
            evaluate_series_switch_provision(policy=_policy(common_cause_beta=2.0))

    def test_evaluation_reports_both_device_assessments(self):
        result = evaluate_series_switch_provision()
        self.assertEqual(result["main_capability"]["name"], DEFAULT_MAIN_SWITCH["name"])
        self.assertEqual(
            result["additional_capability"]["name"], DEFAULT_ADDITIONAL_SWITCH["name"]
        )


if __name__ == "__main__":
    unittest.main()
