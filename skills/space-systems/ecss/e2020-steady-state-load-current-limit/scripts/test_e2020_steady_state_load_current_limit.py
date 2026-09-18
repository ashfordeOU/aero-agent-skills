#!/usr/bin/env python3
"""Contract test for the steady-state load current limit check (offline)."""

import copy
import unittest

from e2020_steady_state_load_current_limit_logic import (
    ADVISORY_HIGH_UTILISATION,
    DEFAULT_LIMIT_POLICY,
    DEFAULT_OPERATING_MODES,
    DEFAULT_UNCERTAINTIES,
    FINDING_AT_OR_ABOVE_CLASS,
    FINDING_AT_OR_ABOVE_DERATED,
    VERDICT_BELOW,
    VERDICT_NOT_BELOW,
    assess_steady_state_load_current,
    bounding_mode_current,
    derated_class_current_a,
    mode_current_a,
    rank_modes,
    stack_uncertainties,
    validate_bus_window,
    validate_limit_policy,
    validate_mode,
    validate_modes,
    validate_uncertainties,
    validate_uncertainty,
    verify_below_class_current,
    worst_case_mode,
    worst_case_steady_current_a,
)

NOMINAL_CASE = {
    "modes": DEFAULT_OPERATING_MODES,
    "bus_min_v": 26.0,
    "bus_max_v": 29.0,
    "uncertainties": DEFAULT_UNCERTAINTIES,
    "class_current_a": 1.70,
}


def _case(**overrides):
    case = dict(copy.deepcopy(NOMINAL_CASE))
    case["modes"] = DEFAULT_OPERATING_MODES
    case["uncertainties"] = DEFAULT_UNCERTAINTIES
    case.update(overrides)
    return case


def _mode(name="acquisition"):
    for row in DEFAULT_OPERATING_MODES:
        if row["name"] == name:
            return copy.deepcopy(row)
    raise AssertionError("no such mode: %s" % name)


def _unc(name="temperature-drift"):
    for row in DEFAULT_UNCERTAINTIES:
        if row["name"] == name:
            return copy.deepcopy(row)
    raise AssertionError("no such uncertainty: %s" % name)


def _nominal_steady_a():
    return worst_case_steady_current_a(
        DEFAULT_OPERATING_MODES, 26.0, 29.0, DEFAULT_UNCERTAINTIES
    )


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_limit_policy(DEFAULT_LIMIT_POLICY), DEFAULT_LIMIT_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_policy(0.8)

    def test_derating_factor_above_unity_rejected(self):
        policy = dict(DEFAULT_LIMIT_POLICY)
        policy["class_current_derating_factor"] = 1.1
        with self.assertRaises(ValueError):
            validate_limit_policy(policy)

    def test_zero_derating_factor_rejected(self):
        policy = dict(DEFAULT_LIMIT_POLICY)
        policy["class_current_derating_factor"] = 0.0
        with self.assertRaises(ValueError):
            validate_limit_policy(policy)

    def test_advisory_fraction_above_unity_rejected(self):
        policy = dict(DEFAULT_LIMIT_POLICY)
        policy["utilisation_advisory_fraction"] = 1.2
        with self.assertRaises(ValueError):
            validate_limit_policy(policy)


class BusWindowTests(unittest.TestCase):
    def test_default_window_validates(self):
        self.assertEqual(validate_bus_window(26.0, 29.0), (26.0, 29.0))

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_window(29.0, 26.0)

    def test_zero_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_window(0.0, 29.0)


class ModeTests(unittest.TestCase):
    def test_default_mode_set_validates(self):
        rows = validate_modes(DEFAULT_OPERATING_MODES)
        self.assertEqual(len(rows), len(DEFAULT_OPERATING_MODES))

    def test_mode_missing_a_field_rejected(self):
        row = _mode()
        del row["value"]
        with self.assertRaises(ValueError):
            validate_mode(row)

    def test_unknown_mode_kind_rejected(self):
        row = _mode()
        row["kind"] = "constant-resistance"
        with self.assertRaises(ValueError):
            validate_mode(row)

    def test_zero_consumption_rejected(self):
        row = _mode()
        row["value"] = 0.0
        with self.assertRaises(ValueError):
            validate_mode(row)

    def test_efficiency_above_unity_rejected(self):
        row = _mode()
        row["efficiency"] = 1.05
        with self.assertRaises(ValueError):
            validate_mode(row)

    def test_efficiency_on_a_constant_current_mode_rejected(self):
        row = _mode("survival-heater")
        row["efficiency"] = 0.9
        with self.assertRaises(ValueError):
            validate_mode(row)

    def test_blank_mode_name_rejected(self):
        row = _mode()
        row["name"] = "   "
        with self.assertRaises(ValueError):
            validate_mode(row)

    def test_repeated_mode_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_modes([_mode(), _mode()])

    def test_empty_mode_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_modes([])


class ModeCurrentTests(unittest.TestCase):
    def test_constant_power_draws_harder_at_the_low_bus(self):
        low = mode_current_a(_mode("acquisition"), 26.0)
        high = mode_current_a(_mode("acquisition"), 29.0)
        self.assertGreater(low, high)

    def test_constant_current_ignores_the_bus_voltage(self):
        low = mode_current_a(_mode("survival-heater"), 26.0)
        high = mode_current_a(_mode("survival-heater"), 29.0)
        self.assertAlmostEqual(low, high, places=12)

    def test_efficiency_scales_the_constant_power_current(self):
        row = _mode("acquisition")
        row["efficiency"] = 1.0
        self.assertAlmostEqual(
            mode_current_a(row, 26.0), 22.0 / 26.0, places=12
        )

    def test_bounding_voltage_for_a_constant_power_mode_is_the_low_end(self):
        bounding = bounding_mode_current(_mode("acquisition"), 26.0, 29.0)
        self.assertAlmostEqual(bounding["bounding_bus_voltage_v"], 26.0, places=12)

    def test_bounding_current_for_a_constant_current_mode_is_its_value(self):
        bounding = bounding_mode_current(_mode("survival-heater"), 26.0, 29.0)
        self.assertAlmostEqual(bounding["current_a"], 0.25, places=12)


class RankTests(unittest.TestCase):
    def test_modes_are_ranked_heaviest_first(self):
        ranked = rank_modes(DEFAULT_OPERATING_MODES, 26.0, 29.0)
        currents = [row["current_a"] for row in ranked]
        self.assertEqual(currents, sorted(currents, reverse=True))

    def test_every_mode_survives_the_ranking(self):
        ranked = rank_modes(DEFAULT_OPERATING_MODES, 26.0, 29.0)
        self.assertEqual(len(ranked), len(DEFAULT_OPERATING_MODES))

    def test_worst_case_mode_is_the_heaviest_constant_power_mode(self):
        self.assertEqual(
            worst_case_mode(DEFAULT_OPERATING_MODES, 26.0, 29.0)["name"], "acquisition"
        )


class UncertaintyTests(unittest.TestCase):
    def test_default_uncertainty_set_validates(self):
        rows = validate_uncertainties(DEFAULT_UNCERTAINTIES)
        self.assertEqual(len(rows), len(DEFAULT_UNCERTAINTIES))

    def test_uncertainty_missing_its_side_rejected(self):
        row = _unc()
        del row["plus"]
        with self.assertRaises(ValueError):
            validate_uncertainty(row)

    def test_negative_uncertainty_rejected(self):
        row = _unc()
        row["plus"] = -0.01
        with self.assertRaises(ValueError):
            validate_uncertainty(row)

    def test_relative_uncertainty_at_unity_rejected(self):
        row = _unc()
        row["plus"] = 1.0
        with self.assertRaises(ValueError):
            validate_uncertainty(row)

    def test_zero_uncertainty_rejected(self):
        row = _unc()
        row["plus"] = 0.0
        with self.assertRaises(ValueError):
            validate_uncertainty(row)

    def test_unknown_uncertainty_kind_rejected(self):
        row = _unc()
        row["kind"] = "statistical"
        with self.assertRaises(ValueError):
            validate_uncertainty(row)

    def test_repeated_uncertainty_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_uncertainties([_unc(), _unc()])

    def test_empty_uncertainty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_uncertainties([])


class StackTests(unittest.TestCase):
    def test_arithmetic_stack_sums_the_contributors(self):
        self.assertAlmostEqual(
            stack_uncertainties(1.0, DEFAULT_UNCERTAINTIES, "arithmetic"),
            0.11,
            places=12,
        )

    def test_root_sum_square_stack_is_smaller_than_arithmetic(self):
        arith = stack_uncertainties(1.0, DEFAULT_UNCERTAINTIES, "arithmetic")
        rss = stack_uncertainties(1.0, DEFAULT_UNCERTAINTIES, "rss")
        self.assertLess(rss, arith)

    def test_root_sum_square_of_one_contributor_equals_that_contributor(self):
        one = [_unc("return-path-offset")]
        self.assertAlmostEqual(
            stack_uncertainties(1.0, one, "rss"),
            stack_uncertainties(1.0, one, "arithmetic"),
            places=12,
        )

    def test_unknown_stack_method_rejected(self):
        with self.assertRaises(ValueError):
            stack_uncertainties(1.0, DEFAULT_UNCERTAINTIES, "monte-carlo")


class ComparisonTests(unittest.TestCase):
    def test_derated_capability_is_the_class_times_the_factor(self):
        self.assertAlmostEqual(derated_class_current_a(1.70, 0.80), 1.36, places=12)

    def test_a_derating_factor_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_class_current_a(1.70, 1.05)

    def test_nominal_steady_current_sits_below_both_figures(self):
        result = verify_below_class_current(_nominal_steady_a(), 1.70)
        self.assertTrue(result["below_derated"])
        self.assertTrue(result["below_class"])

    def test_utilisation_is_the_steady_current_over_the_derated_capability(self):
        steady = _nominal_steady_a()
        result = verify_below_class_current(steady, 1.70)
        self.assertAlmostEqual(result["utilisation"], steady / 1.36, places=9)

    def test_a_current_exactly_on_the_derated_capability_is_not_below_it(self):
        steady = _nominal_steady_a()
        policy = {
            "class_current_derating_factor": 1.0,
            "utilisation_advisory_fraction": 0.90,
        }
        result = verify_below_class_current(steady, steady, policy)
        self.assertAlmostEqual(result["margin_a"], 0.0, places=12)
        self.assertFalse(result["below_derated"])


class AssessmentTests(unittest.TestCase):
    def test_nominal_case_is_compliant_and_quiet(self):
        result = assess_steady_state_load_current(NOMINAL_CASE)
        self.assertEqual(result["verdict"], VERDICT_BELOW)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_nominal_case_names_the_mode_and_voltage_that_bind(self):
        result = assess_steady_state_load_current(NOMINAL_CASE)
        self.assertEqual(result["bounding_mode"], "acquisition")
        self.assertAlmostEqual(result["bounding_bus_voltage_v"], 26.0, places=12)

    def test_a_small_class_puts_the_load_above_the_derated_capability(self):
        result = assess_steady_state_load_current(_case(class_current_a=1.20))
        self.assertEqual(result["verdict"], VERDICT_NOT_BELOW)
        self.assertTrue(
            any(FINDING_AT_OR_ABOVE_DERATED in f for f in result["findings"])
        )

    def test_a_class_under_the_load_itself_names_the_limitation_finding(self):
        result = assess_steady_state_load_current(_case(class_current_a=1.05))
        self.assertTrue(any(FINDING_AT_OR_ABOVE_CLASS in f for f in result["findings"]))
        self.assertEqual(len(result["findings"]), 2)

    def test_a_tight_but_passing_class_raises_a_utilisation_advisory(self):
        result = assess_steady_state_load_current(_case(class_current_a=1.45))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(
            any(ADVISORY_HIGH_UTILISATION in a for a in result["advisories"])
        )

    def test_root_sum_square_lowers_the_reported_steady_current(self):
        arith = assess_steady_state_load_current(_case(method="arithmetic"))
        rss = assess_steady_state_load_current(_case(method="rss"))
        self.assertLess(rss["steady_current_a"], arith["steady_current_a"])

    def test_a_narrow_bus_window_at_the_low_end_is_the_bounding_one(self):
        wide = assess_steady_state_load_current(_case(bus_min_v=24.0))
        narrow = assess_steady_state_load_current(_case(bus_min_v=27.0))
        self.assertGreater(wide["steady_current_a"], narrow["steady_current_a"])

    def test_assessment_rejects_an_unknown_method(self):
        with self.assertRaises(ValueError):
            assess_steady_state_load_current(_case(method="worst-of-three"))

    def test_assessment_rejects_a_case_missing_the_class_current(self):
        case = _case()
        del case["class_current_a"]
        with self.assertRaises(ValueError):
            assess_steady_state_load_current(case)

    def test_assessment_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            assess_steady_state_load_current("1.7 A")

    def test_assessment_reports_the_uncertainty_it_added(self):
        result = assess_steady_state_load_current(NOMINAL_CASE)
        worst = worst_case_mode(DEFAULT_OPERATING_MODES, 26.0, 29.0)
        self.assertAlmostEqual(
            result["steady_current_a"],
            worst["current_a"] + result["uncertainty_a"],
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
