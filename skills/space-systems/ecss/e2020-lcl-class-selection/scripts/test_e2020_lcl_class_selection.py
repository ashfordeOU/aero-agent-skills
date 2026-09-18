#!/usr/bin/env python3
"""Contract test for the LCL class selection (offline)."""

import copy
import unittest

from e2020_lcl_class_selection_logic import (
    DEFAULT_CLASS_TABLE,
    DEFAULT_SELECTION_POLICY,
    FINDING_CAPABILITY,
    FINDING_HARNESS,
    FINDING_OVERSIZED,
    FINDING_STARTUP,
    VERDICT_NO_CLASS,
    VERDICT_SELECTED,
    assess_class,
    candidate_classes,
    derated_capability_a,
    inrush_charge_time_s,
    select_lcl_class,
    utilisation_ratio,
    validate_class_entry,
    validate_class_table,
    validate_load,
    validate_selection_policy,
)

NOMINAL_LOAD = {
    "steady_state_current_a": 1.5,
    "load_capacitance_f": 220.0e-6,
    "bus_voltage_v": 28.0,
    "harness_rating_a": 8.0,
}

SMALL_LOAD = {
    "steady_state_current_a": 0.2,
    "load_capacitance_f": 22.0e-6,
    "bus_voltage_v": 28.0,
    "harness_rating_a": 16.0,
}


def _entry(name="lcl-b"):
    for row in DEFAULT_CLASS_TABLE:
        if row["name"] == name:
            return copy.deepcopy(row)
    raise AssertionError("no such class row: %s" % name)


def _load(**overrides):
    case = copy.deepcopy(NOMINAL_LOAD)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_selection_policy(DEFAULT_SELECTION_POLICY),
            DEFAULT_SELECTION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy("default")

    def test_derating_above_unity_rejected(self):
        policy = dict(DEFAULT_SELECTION_POLICY, derating_factor=1.4)
        with self.assertRaises(ValueError):
            validate_selection_policy(policy)

    def test_zero_derating_rejected(self):
        policy = dict(DEFAULT_SELECTION_POLICY, derating_factor=0.0)
        with self.assertRaises(ValueError):
            validate_selection_policy(policy)

    def test_startup_margin_below_unity_rejected(self):
        policy = dict(DEFAULT_SELECTION_POLICY, startup_time_margin=0.9)
        with self.assertRaises(ValueError):
            validate_selection_policy(policy)

    def test_advisory_floor_at_or_above_unity_rejected(self):
        policy = dict(DEFAULT_SELECTION_POLICY, utilisation_advisory_floor=1.0)
        with self.assertRaises(ValueError):
            validate_selection_policy(policy)


class ClassTableTests(unittest.TestCase):
    def test_default_table_validates(self):
        rows = validate_class_table(DEFAULT_CLASS_TABLE)
        self.assertEqual(len(rows), len(DEFAULT_CLASS_TABLE))

    def test_every_row_keeps_its_limiting_band_above_its_continuous_rating(self):
        for row in validate_class_table(DEFAULT_CLASS_TABLE):
            self.assertGreater(row["limit_min_a"], row["max_continuous_current_a"])

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_class_table([])

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_class_table(_entry())

    def test_row_missing_a_performance_figure_rejected(self):
        row = _entry()
        del row["trip_off_time_min_s"]
        with self.assertRaises(ValueError):
            validate_class_entry(row)

    def test_inverted_limiting_band_rejected(self):
        row = _entry()
        row["limit_min_a"], row["limit_max_a"] = row["limit_max_a"], row["limit_min_a"]
        with self.assertRaises(ValueError):
            validate_class_entry(row)

    def test_inverted_trip_off_window_rejected(self):
        row = _entry()
        row["trip_off_time_min_s"] = row["trip_off_time_max_s"] * 2.0
        with self.assertRaises(ValueError):
            validate_class_entry(row)

    def test_limiting_band_at_the_continuous_rating_rejected(self):
        row = _entry()
        row["limit_min_a"] = row["max_continuous_current_a"]
        with self.assertRaises(ValueError):
            validate_class_entry(row)

    def test_negative_current_rejected(self):
        row = _entry()
        row["max_continuous_current_a"] = -1.0
        with self.assertRaises(ValueError):
            validate_class_entry(row)

    def test_boolean_current_rejected(self):
        row = _entry()
        row["limit_max_a"] = True
        with self.assertRaises(ValueError):
            validate_class_entry(row)

    def test_repeated_class_name_rejected(self):
        table = [_entry("lcl-a"), _entry("lcl-a")]
        with self.assertRaises(ValueError):
            validate_class_table(table)

    def test_non_ascending_table_rejected(self):
        table = [_entry("lcl-c"), _entry("lcl-b")]
        with self.assertRaises(ValueError):
            validate_class_table(table)

    def test_blank_class_name_rejected(self):
        row = _entry()
        row["name"] = "   "
        with self.assertRaises(ValueError):
            validate_class_entry(row)


class LoadValidationTests(unittest.TestCase):
    def test_nominal_load_validates(self):
        case = validate_load(NOMINAL_LOAD)
        self.assertAlmostEqual(case["steady_state_current_a"], 1.5, places=12)

    def test_load_missing_capacitance_rejected(self):
        case = _load()
        del case["load_capacitance_f"]
        with self.assertRaises(ValueError):
            validate_load(case)

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(_load(load_capacitance_f=0.0))

    def test_non_mapping_load_rejected(self):
        with self.assertRaises(ValueError):
            validate_load("28 V")


class CapabilityTests(unittest.TestCase):
    def test_derated_capability_applies_the_factor(self):
        self.assertAlmostEqual(derated_capability_a(_entry("lcl-c"), 0.8), 1.6, places=12)

    def test_derating_above_unity_rejected_at_the_call(self):
        with self.assertRaises(ValueError):
            derated_capability_a(_entry("lcl-c"), 1.1)

    def test_utilisation_is_the_load_over_the_derated_capability(self):
        self.assertAlmostEqual(
            utilisation_ratio(_entry("lcl-c"), 1.6, 0.8), 1.0, places=9
        )

    def test_utilisation_falls_as_the_class_grows(self):
        small = utilisation_ratio(_entry("lcl-c"), 1.5, 0.8)
        large = utilisation_ratio(_entry("lcl-e"), 1.5, 0.8)
        self.assertGreater(small, large)


class InrushTests(unittest.TestCase):
    def test_charge_time_is_capacitance_times_voltage_over_current(self):
        self.assertAlmostEqual(
            inrush_charge_time_s(220.0e-6, 28.0, 1.2), 220.0e-6 * 28.0 / 1.2, places=12
        )

    def test_charge_time_falls_with_a_larger_limiting_current(self):
        slow = inrush_charge_time_s(220.0e-6, 28.0, 1.2)
        fast = inrush_charge_time_s(220.0e-6, 28.0, 2.4)
        self.assertGreater(slow, fast)

    def test_zero_charge_current_rejected(self):
        with self.assertRaises(ValueError):
            inrush_charge_time_s(220.0e-6, 28.0, 0.0)

    def test_negative_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            inrush_charge_time_s(220.0e-6, -28.0, 1.2)


class AssessClassTests(unittest.TestCase):
    def test_undersized_class_reports_a_capability_finding(self):
        result = assess_class(_entry("lcl-a"), NOMINAL_LOAD)
        self.assertFalse(result["carries_steady_load"])
        self.assertTrue(any(FINDING_CAPABILITY in f for f in result["findings"]))

    def test_adequate_class_reports_no_findings(self):
        result = assess_class(_entry("lcl-c"), NOMINAL_LOAD)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])

    def test_large_capacitance_trips_the_start_up_check(self):
        result = assess_class(_entry("lcl-c"), _load(load_capacitance_f=4.7e-3))
        self.assertFalse(result["permits_start_up"])
        self.assertTrue(any(FINDING_STARTUP in f for f in result["findings"]))

    def test_harness_below_the_upper_limit_is_a_finding(self):
        result = assess_class(_entry("lcl-c"), _load(harness_rating_a=2.5))
        self.assertFalse(result["protects_harness"])
        self.assertTrue(any(FINDING_HARNESS in f for f in result["findings"]))

    def test_oversized_class_raises_an_advisory_not_a_finding(self):
        result = assess_class(_entry("lcl-e"), SMALL_LOAD)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(FINDING_OVERSIZED in a for a in result["advisories"]))

    def test_load_exactly_on_the_derated_capability_is_carried(self):
        capability = derated_capability_a(_entry("lcl-c"), 0.8)
        self.assertAlmostEqual(capability, 1.6, places=9)
        result = assess_class(_entry("lcl-c"), _load(steady_state_current_a=capability))
        self.assertAlmostEqual(result["utilisation"], 1.0, places=9)
        self.assertTrue(result["carries_steady_load"])

    def test_upper_limit_exactly_on_the_harness_rating_still_protects(self):
        row = _entry("lcl-c")
        result = assess_class(row, _load(harness_rating_a=row["limit_max_a"]))
        self.assertAlmostEqual(result["harness_slack_a"], 0.0, places=9)
        self.assertTrue(result["protects_harness"])

    def test_start_up_slack_shrinks_as_the_capacitance_grows(self):
        small = assess_class(_entry("lcl-c"), _load(load_capacitance_f=100.0e-6))
        large = assess_class(_entry("lcl-c"), _load(load_capacitance_f=470.0e-6))
        self.assertGreater(small["startup_slack_s"], large["startup_slack_s"])

    def test_start_up_uses_the_lower_limiting_current(self):
        row = _entry("lcl-c")
        result = assess_class(row, NOMINAL_LOAD)
        expected = inrush_charge_time_s(
            NOMINAL_LOAD["load_capacitance_f"],
            NOMINAL_LOAD["bus_voltage_v"],
            row["limit_min_a"],
        )
        self.assertAlmostEqual(result["startup_charge_time_s"], expected, places=12)


class SelectionTests(unittest.TestCase):
    def test_smallest_adequate_class_is_taken(self):
        result = select_lcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        self.assertEqual(result["verdict"], VERDICT_SELECTED)
        self.assertEqual(result["selected"], "lcl-c")

    def test_candidates_are_a_superset_of_the_choice(self):
        result = select_lcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        self.assertIn(result["selected"], result["candidates"])
        self.assertGreater(len(result["candidates"]), 1)

    def test_candidate_helper_agrees_with_the_selection(self):
        cands = candidate_classes(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        result = select_lcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        self.assertEqual([c["name"] for c in cands], result["candidates"])

    def test_a_load_beyond_the_table_selects_nothing(self):
        result = select_lcl_class(
            DEFAULT_CLASS_TABLE, _load(steady_state_current_a=40.0, harness_rating_a=60.0)
        )
        self.assertEqual(result["verdict"], VERDICT_NO_CLASS)
        self.assertIsNone(result["selected"])
        self.assertTrue(result["findings"])

    def test_a_tight_harness_rating_can_empty_the_candidate_set(self):
        result = select_lcl_class(DEFAULT_CLASS_TABLE, _load(harness_rating_a=1.0))
        self.assertEqual(result["verdict"], VERDICT_NO_CLASS)
        self.assertTrue(any(FINDING_HARNESS in f for f in result["findings"]))

    def test_tighter_derating_can_push_the_choice_one_class_up(self):
        loose = select_lcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        strict = select_lcl_class(
            DEFAULT_CLASS_TABLE,
            NOMINAL_LOAD,
            dict(DEFAULT_SELECTION_POLICY, derating_factor=0.5),
        )
        self.assertEqual(loose["selected"], "lcl-c")
        self.assertEqual(strict["selected"], "lcl-d")

    def test_selection_reports_every_assessment_it_looked_at(self):
        result = select_lcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        self.assertEqual(len(result["assessments"]), len(DEFAULT_CLASS_TABLE))

    def test_selection_rejects_a_broken_table(self):
        table = [_entry("lcl-c"), _entry("lcl-a")]
        with self.assertRaises(ValueError):
            select_lcl_class(table, NOMINAL_LOAD)

    def test_selection_rejects_a_broken_load(self):
        with self.assertRaises(ValueError):
            select_lcl_class(DEFAULT_CLASS_TABLE, _load(steady_state_current_a=0.0))


if __name__ == "__main__":
    unittest.main()
