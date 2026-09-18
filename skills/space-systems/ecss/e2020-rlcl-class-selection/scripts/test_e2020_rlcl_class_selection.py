#!/usr/bin/env python3
"""Contract test for the RLCL class selection (offline)."""

import copy
import unittest

from e2020_rlcl_class_selection_logic import (
    DEFAULT_CLASS_TABLE,
    DEFAULT_SELECTION_POLICY,
    FINDING_ATTEMPTS,
    FINDING_ATTEMPT_BUDGET,
    FINDING_CAPABILITY,
    FINDING_ENERGY,
    FINDING_MEAN,
    FINDING_NO_CHARGE,
    FINDING_PEAK,
    VERDICT_NO_CLASS,
    VERDICT_SELECTED,
    assess_rlcl_class,
    candidate_rlcl_classes,
    fault_energy_per_attempt_j,
    mean_fault_current_a,
    retrigger_duty_cycle,
    select_rlcl_class,
    startup_attempts_needed,
    validate_load,
    validate_rlcl_class_entry,
    validate_rlcl_class_table,
    validate_selection_policy,
    worst_case_duty_cycle,
)

NOMINAL_LOAD = {
    "steady_state_current_a": 1.5,
    "load_capacitance_f": 220.0e-6,
    "bus_voltage_v": 28.0,
    "harness_peak_rating_a": 8.0,
    "harness_mean_rating_a": 2.0,
    "fault_energy_allowance_j": 4.0,
}


def _entry(name="rlcl-c"):
    for row in DEFAULT_CLASS_TABLE:
        if row["name"] == name:
            return copy.deepcopy(row)
    raise AssertionError("no such class row: %s" % name)


def _load(**overrides):
    case = copy.deepcopy(NOMINAL_LOAD)
    case.update(overrides)
    return case


def _policy(**overrides):
    policy = dict(DEFAULT_SELECTION_POLICY)
    policy.update(overrides)
    return policy


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_selection_policy(DEFAULT_SELECTION_POLICY),
            DEFAULT_SELECTION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(["derating"])

    def test_derating_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(derating_factor=1.2))

    def test_charge_retention_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(charge_retention=1.5))

    def test_zero_charge_retention_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(charge_retention=0.0))

    def test_attempt_advisory_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy(_policy(attempt_advisory_fraction=1.4))


class ClassTableTests(unittest.TestCase):
    def test_default_table_validates(self):
        rows = validate_rlcl_class_table(DEFAULT_CLASS_TABLE)
        self.assertEqual(len(rows), len(DEFAULT_CLASS_TABLE))

    def test_every_row_keeps_a_bounded_attempt_allowance(self):
        for row in validate_rlcl_class_table(DEFAULT_CLASS_TABLE):
            self.assertGreaterEqual(row["max_retrigger_attempts"], 1)

    def test_row_missing_the_hold_off_window_rejected(self):
        row = _entry()
        del row["retrigger_off_time_min_s"]
        with self.assertRaises(ValueError):
            validate_rlcl_class_entry(row)

    def test_inverted_hold_off_window_rejected(self):
        row = _entry()
        row["retrigger_off_time_min_s"] = row["retrigger_off_time_max_s"] * 2.0
        with self.assertRaises(ValueError):
            validate_rlcl_class_entry(row)

    def test_inverted_trip_off_window_rejected(self):
        row = _entry()
        row["trip_off_time_min_s"] = row["trip_off_time_max_s"] * 2.0
        with self.assertRaises(ValueError):
            validate_rlcl_class_entry(row)

    def test_inverted_limiting_band_rejected(self):
        row = _entry()
        row["limit_min_a"], row["limit_max_a"] = row["limit_max_a"], row["limit_min_a"]
        with self.assertRaises(ValueError):
            validate_rlcl_class_entry(row)

    def test_zero_attempt_allowance_rejected(self):
        row = _entry()
        row["max_retrigger_attempts"] = 0
        with self.assertRaises(ValueError):
            validate_rlcl_class_entry(row)

    def test_fractional_attempt_allowance_rejected(self):
        row = _entry()
        row["max_retrigger_attempts"] = 2.5
        with self.assertRaises(ValueError):
            validate_rlcl_class_entry(row)

    def test_boolean_attempt_allowance_rejected(self):
        row = _entry()
        row["max_retrigger_attempts"] = True
        with self.assertRaises(ValueError):
            validate_rlcl_class_entry(row)

    def test_limiting_band_at_the_continuous_rating_rejected(self):
        row = _entry()
        row["limit_min_a"] = row["max_continuous_current_a"]
        with self.assertRaises(ValueError):
            validate_rlcl_class_entry(row)

    def test_repeated_class_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_class_table([_entry("rlcl-c"), _entry("rlcl-c")])

    def test_non_ascending_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_class_table([_entry("rlcl-d"), _entry("rlcl-c")])

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_class_table([])


class LoadValidationTests(unittest.TestCase):
    def test_nominal_load_validates(self):
        case = validate_load(NOMINAL_LOAD)
        self.assertAlmostEqual(case["fault_energy_allowance_j"], 4.0, places=12)

    def test_load_missing_the_energy_allowance_rejected(self):
        case = _load()
        del case["fault_energy_allowance_j"]
        with self.assertRaises(ValueError):
            validate_load(case)

    def test_mean_rating_above_peak_rating_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(_load(harness_mean_rating_a=12.0))

    def test_non_mapping_load_rejected(self):
        with self.assertRaises(ValueError):
            validate_load("28 V bus")


class DutyAndEnergyTests(unittest.TestCase):
    def test_duty_cycle_is_on_over_the_full_period(self):
        self.assertAlmostEqual(
            retrigger_duty_cycle(20.0e-3, 80.0e-3), 0.2, places=12
        )

    def test_equal_on_and_off_times_give_a_half_duty(self):
        self.assertAlmostEqual(retrigger_duty_cycle(5.0e-3, 5.0e-3), 0.5, places=12)

    def test_zero_hold_off_rejected(self):
        with self.assertRaises(ValueError):
            retrigger_duty_cycle(20.0e-3, 0.0)

    def test_worst_case_duty_pairs_the_longest_trip_with_the_shortest_hold_off(self):
        row = _entry("rlcl-c")
        self.assertAlmostEqual(
            worst_case_duty_cycle(row),
            retrigger_duty_cycle(
                row["trip_off_time_max_s"], row["retrigger_off_time_min_s"]
            ),
            places=12,
        )

    def test_worst_case_duty_exceeds_the_nominal_pairing(self):
        row = _entry("rlcl-c")
        nominal = retrigger_duty_cycle(
            row["trip_off_time_min_s"], row["retrigger_off_time_max_s"]
        )
        self.assertGreater(worst_case_duty_cycle(row), nominal)

    def test_mean_fault_current_scales_with_the_duty(self):
        self.assertAlmostEqual(mean_fault_current_a(3.4, 0.25), 0.85, places=12)

    def test_duty_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            mean_fault_current_a(3.4, 1.4)

    def test_fault_energy_is_voltage_times_current_times_on_time(self):
        self.assertAlmostEqual(
            fault_energy_per_attempt_j(28.0, 3.4, 16.0e-3), 28.0 * 3.4 * 16.0e-3,
            places=12,
        )

    def test_fault_energy_rejects_a_zero_on_time(self):
        with self.assertRaises(ValueError):
            fault_energy_per_attempt_j(28.0, 3.4, 0.0)


class StartupAttemptTests(unittest.TestCase):
    def test_a_small_load_comes_up_on_the_first_attempt(self):
        self.assertEqual(startup_attempts_needed(_entry("rlcl-c"), NOMINAL_LOAD), 1)

    def test_charge_retention_changes_the_attempt_count(self):
        case = _load(load_capacitance_f=500.0e-6)
        ideal = startup_attempts_needed(
            _entry("rlcl-c"), case, _policy(charge_retention=1.0)
        )
        lossy = startup_attempts_needed(
            _entry("rlcl-c"), case, _policy(charge_retention=0.9)
        )
        self.assertEqual(ideal, 2)
        self.assertEqual(lossy, 3)

    def test_a_load_beyond_the_allowance_returns_no_attempt_count(self):
        case = _load(load_capacitance_f=2200.0e-6)
        self.assertIsNone(startup_attempts_needed(_entry("rlcl-c"), case))

    def test_a_steady_draw_above_the_lower_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            startup_attempts_needed(_entry("rlcl-b"), NOMINAL_LOAD)

    def test_a_larger_class_needs_no_more_attempts(self):
        case = _load(load_capacitance_f=500.0e-6)
        small = startup_attempts_needed(_entry("rlcl-c"), case)
        large = startup_attempts_needed(_entry("rlcl-d"), case)
        self.assertLessEqual(large, small)


class AssessClassTests(unittest.TestCase):
    def test_adequate_class_reports_no_findings(self):
        result = assess_rlcl_class(_entry("rlcl-c"), NOMINAL_LOAD)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])

    def test_undersized_class_reports_a_capability_finding(self):
        result = assess_rlcl_class(_entry("rlcl-a"), NOMINAL_LOAD)
        self.assertFalse(result["carries_steady_load"])
        self.assertTrue(any(FINDING_CAPABILITY in f for f in result["findings"]))

    def test_a_class_whose_lower_limit_cannot_charge_is_named_as_such(self):
        result = assess_rlcl_class(_entry("rlcl-b"), NOMINAL_LOAD)
        self.assertFalse(result["permits_start_up"])
        self.assertTrue(any(FINDING_NO_CHARGE in f for f in result["findings"]))

    def test_peak_harness_rating_below_the_upper_limit_is_a_finding(self):
        result = assess_rlcl_class(_entry("rlcl-e"), NOMINAL_LOAD)
        self.assertFalse(result["protects_harness_peak"])
        self.assertTrue(any(FINDING_PEAK in f for f in result["findings"]))

    def test_thermal_harness_rating_below_the_mean_current_is_a_finding(self):
        result = assess_rlcl_class(
            _entry("rlcl-c"), _load(harness_mean_rating_a=0.2)
        )
        self.assertFalse(result["protects_harness_mean"])
        self.assertTrue(any(FINDING_MEAN in f for f in result["findings"]))

    def test_energy_allowance_below_the_per_attempt_pulse_is_a_finding(self):
        result = assess_rlcl_class(
            _entry("rlcl-c"), _load(fault_energy_allowance_j=0.5)
        )
        self.assertFalse(result["energy_within_allowance"])
        self.assertTrue(any(FINDING_ENERGY in f for f in result["findings"]))

    def test_a_load_that_outruns_the_allowance_is_a_start_up_finding(self):
        result = assess_rlcl_class(
            _entry("rlcl-c"), _load(load_capacitance_f=2200.0e-6)
        )
        self.assertFalse(result["permits_start_up"])
        self.assertTrue(any(FINDING_ATTEMPTS in f for f in result["findings"]))

    def test_heavy_attempt_use_raises_an_advisory_not_a_finding(self):
        result = assess_rlcl_class(
            _entry("rlcl-c"), _load(load_capacitance_f=785.7e-6)
        )
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["startup_attempts_needed"], 4)
        self.assertTrue(any(FINDING_ATTEMPT_BUDGET in a for a in result["advisories"]))

    def test_mean_current_exactly_on_the_thermal_rating_still_protects(self):
        row = _entry("rlcl-c")
        mean = mean_fault_current_a(row["limit_max_a"], worst_case_duty_cycle(row))
        result = assess_rlcl_class(row, _load(harness_mean_rating_a=mean))
        self.assertAlmostEqual(result["harness_mean_slack_a"], 0.0, places=9)
        self.assertTrue(result["protects_harness_mean"])

    def test_energy_exactly_on_the_allowance_is_within_it(self):
        row = _entry("rlcl-c")
        energy = fault_energy_per_attempt_j(
            NOMINAL_LOAD["bus_voltage_v"], row["limit_max_a"], row["trip_off_time_max_s"]
        )
        result = assess_rlcl_class(row, _load(fault_energy_allowance_j=energy))
        self.assertTrue(result["energy_within_allowance"])

    def test_mean_current_never_exceeds_the_upper_limiting_current(self):
        for row in DEFAULT_CLASS_TABLE:
            result = assess_rlcl_class(
                row, _load(harness_peak_rating_a=20.0, harness_mean_rating_a=20.0)
            )
            self.assertLess(result["mean_fault_current_a"], row["limit_max_a"])


class SelectionTests(unittest.TestCase):
    def test_smallest_adequate_class_is_taken(self):
        result = select_rlcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        self.assertEqual(result["verdict"], VERDICT_SELECTED)
        self.assertEqual(result["selected"], "rlcl-c")

    def test_candidate_helper_agrees_with_the_selection(self):
        cands = candidate_rlcl_classes(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        result = select_rlcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        self.assertEqual([c["name"] for c in cands], result["candidates"])

    def test_more_than_one_class_can_qualify(self):
        result = select_rlcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        self.assertIn("rlcl-d", result["candidates"])

    def test_a_tight_thermal_rating_can_empty_the_candidate_set(self):
        result = select_rlcl_class(
            DEFAULT_CLASS_TABLE, _load(harness_mean_rating_a=0.05)
        )
        self.assertEqual(result["verdict"], VERDICT_NO_CLASS)
        self.assertIsNone(result["selected"])
        self.assertTrue(any(FINDING_MEAN in f for f in result["findings"]))

    def test_tighter_derating_can_push_the_choice_one_class_up(self):
        loose = select_rlcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        strict = select_rlcl_class(
            DEFAULT_CLASS_TABLE, NOMINAL_LOAD, _policy(derating_factor=0.5)
        )
        self.assertEqual(loose["selected"], "rlcl-c")
        self.assertEqual(strict["selected"], "rlcl-d")

    def test_selection_reports_every_assessment_it_looked_at(self):
        result = select_rlcl_class(DEFAULT_CLASS_TABLE, NOMINAL_LOAD)
        self.assertEqual(len(result["assessments"]), len(DEFAULT_CLASS_TABLE))

    def test_selection_carries_the_advisory_of_the_retained_class(self):
        result = select_rlcl_class(
            DEFAULT_CLASS_TABLE, _load(load_capacitance_f=785.7e-6)
        )
        self.assertEqual(result["selected"], "rlcl-c")
        self.assertTrue(result["advisories"])

    def test_selection_rejects_a_broken_table(self):
        with self.assertRaises(ValueError):
            select_rlcl_class([_entry("rlcl-d"), _entry("rlcl-c")], NOMINAL_LOAD)

    def test_selection_rejects_a_broken_load(self):
        with self.assertRaises(ValueError):
            select_rlcl_class(DEFAULT_CLASS_TABLE, _load(bus_voltage_v=0.0))


if __name__ == "__main__":
    unittest.main()
