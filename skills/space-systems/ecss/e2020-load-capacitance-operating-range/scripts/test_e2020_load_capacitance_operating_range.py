#!/usr/bin/env python3
"""Contract test for the load capacitance operating range check (offline)."""

import copy
import unittest

from e2020_load_capacitance_operating_range_logic import (
    ADVISORY_LOW_USAGE,
    ADVISORY_THIN_RANGE,
    DEFAULT_CAPACITANCE_CONTRIBUTORS,
    DEFAULT_CLASS_TABLE,
    DEFAULT_RANGE_POLICY,
    FINDING_ABOVE_TABULATED,
    FINDING_NO_CLASS,
    FINDING_RANGE_NOT_STARTABLE,
    VERDICT_COVERED,
    VERDICT_NOT_COVERED,
    assess_class_capacitance_range,
    assess_load_capacitance_operating_range,
    charge_time_s,
    effective_capacitance_range,
    select_capacitance_class,
    startable_capacitance_f,
    sweep_operating_range,
    validate_capacitance_contributor,
    validate_capacitance_contributors,
    validate_class_row,
    validate_class_table,
    validate_range_policy,
)

NOMINAL_CASE = {
    "declared_capacitance_f": 150.0e-6,
    "contributors": DEFAULT_CAPACITANCE_CONTRIBUTORS,
    "class_table": DEFAULT_CLASS_TABLE,
    "bus_voltage_v": 28.0,
}

# A single-class table whose tabulated maximum is exactly what the class
# can charge inside the shortest trip-off delay with the default margin.
EXACT_TABLE = (
    {
        "name": "class-exact",
        "max_load_capacitance_f": 200.0e-6,
        "limiting_current_min_a": 0.84,
        "trip_off_time_min_s": 8.0e-3,
    },
)


def _case(**overrides):
    case = dict(copy.deepcopy(NOMINAL_CASE))
    case["contributors"] = DEFAULT_CAPACITANCE_CONTRIBUTORS
    case["class_table"] = DEFAULT_CLASS_TABLE
    case.update(overrides)
    return case


def _contrib(name="initial-tolerance"):
    for row in DEFAULT_CAPACITANCE_CONTRIBUTORS:
        if row["name"] == name:
            return copy.deepcopy(row)
    raise AssertionError("no such contributor: %s" % name)


def _class(name="class-2"):
    for row in DEFAULT_CLASS_TABLE:
        if row["name"] == name:
            return copy.deepcopy(row)
    raise AssertionError("no such class: %s" % name)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_range_policy(DEFAULT_RANGE_POLICY), DEFAULT_RANGE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_range_policy(1.2)

    def test_margin_below_one_rejected(self):
        policy = dict(DEFAULT_RANGE_POLICY)
        policy["start_up_time_margin"] = 0.9
        with self.assertRaises(ValueError):
            validate_range_policy(policy)

    def test_advisory_fraction_above_unity_rejected(self):
        policy = dict(DEFAULT_RANGE_POLICY)
        policy["low_usage_advisory_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_range_policy(policy)

    def test_two_sweep_points_rejected(self):
        policy = dict(DEFAULT_RANGE_POLICY)
        policy["sweep_points"] = 2
        with self.assertRaises(ValueError):
            validate_range_policy(policy)

    def test_non_integer_sweep_points_rejected(self):
        policy = dict(DEFAULT_RANGE_POLICY)
        policy["sweep_points"] = 9.0
        with self.assertRaises(ValueError):
            validate_range_policy(policy)


class ContributorTests(unittest.TestCase):
    def test_default_derating_set_validates(self):
        rows = validate_capacitance_contributors(DEFAULT_CAPACITANCE_CONTRIBUTORS)
        self.assertEqual(len(rows), len(DEFAULT_CAPACITANCE_CONTRIBUTORS))

    def test_contributor_missing_a_side_rejected(self):
        row = _contrib()
        del row["plus"]
        with self.assertRaises(ValueError):
            validate_capacitance_contributor(row)

    def test_negative_derating_rejected(self):
        row = _contrib()
        row["minus"] = -0.05
        with self.assertRaises(ValueError):
            validate_capacitance_contributor(row)

    def test_relative_derating_at_unity_rejected(self):
        row = _contrib()
        row["minus"] = 1.0
        with self.assertRaises(ValueError):
            validate_capacitance_contributor(row)

    def test_unknown_contributor_kind_rejected(self):
        row = _contrib()
        row["kind"] = "statistical"
        with self.assertRaises(ValueError):
            validate_capacitance_contributor(row)

    def test_two_sided_zero_contributor_rejected(self):
        with self.assertRaises(ValueError):
            validate_capacitance_contributor(
                {"name": "spare", "kind": "absolute", "minus": 0.0, "plus": 0.0}
            )

    def test_repeated_contributor_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_capacitance_contributors([_contrib(), _contrib()])

    def test_empty_derating_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_capacitance_contributors([])


class EffectiveCapacitanceTests(unittest.TestCase):
    def test_high_end_is_the_value_compared_with_the_table(self):
        spread = effective_capacitance_range(
            150.0e-6, DEFAULT_CAPACITANCE_CONTRIBUTORS
        )
        self.assertAlmostEqual(spread["max_f"], 172.5e-6, places=12)

    def test_low_end_carries_the_downward_derating(self):
        spread = effective_capacitance_range(
            150.0e-6, DEFAULT_CAPACITANCE_CONTRIBUTORS
        )
        self.assertAlmostEqual(spread["min_f"], 75.0e-6, places=12)

    def test_absolute_contributor_does_not_scale_with_the_declaration(self):
        rows = [{"name": "stray", "kind": "absolute", "minus": 1.0e-6, "plus": 2.0e-6}]
        small = effective_capacitance_range(10.0e-6, rows)
        large = effective_capacitance_range(100.0e-6, rows)
        self.assertAlmostEqual(small["plus_f"], large["plus_f"], places=15)

    def test_a_derating_that_consumes_the_declaration_is_rejected(self):
        rows = [{"name": "wild", "kind": "relative", "minus": 0.99, "plus": 0.01}]
        with self.assertRaises(ValueError):
            effective_capacitance_range(1.0e-6, rows + [
                {"name": "extra", "kind": "absolute", "minus": 1.0e-6, "plus": 0.0}
            ])

    def test_zero_declared_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            effective_capacitance_range(0.0, DEFAULT_CAPACITANCE_CONTRIBUTORS)


class ClassTableTests(unittest.TestCase):
    def test_default_table_validates(self):
        rows = validate_class_table(DEFAULT_CLASS_TABLE)
        self.assertEqual(len(rows), len(DEFAULT_CLASS_TABLE))

    def test_non_ascending_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_class_table([_class("class-3"), _class("class-2")])

    def test_repeated_class_name_rejected(self):
        second = _class("class-2")
        second["max_load_capacitance_f"] = 300.0e-6
        second["name"] = "class-1"
        with self.assertRaises(ValueError):
            validate_class_table([_class("class-1"), second])

    def test_class_row_missing_a_field_rejected(self):
        row = _class()
        del row["trip_off_time_min_s"]
        with self.assertRaises(ValueError):
            validate_class_row(row)

    def test_zero_trip_off_delay_rejected(self):
        row = _class()
        row["trip_off_time_min_s"] = 0.0
        with self.assertRaises(ValueError):
            validate_class_row(row)

    def test_empty_class_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_class_table([])


class ChargeTests(unittest.TestCase):
    def test_charge_time_is_linear_in_capacitance(self):
        one = charge_time_s(100.0e-6, 28.0, 1.70)
        two = charge_time_s(200.0e-6, 28.0, 1.70)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_zero_capacitance_charges_instantly(self):
        self.assertAlmostEqual(charge_time_s(0.0, 28.0, 1.70), 0.0, places=15)

    def test_zero_limiting_current_rejected(self):
        with self.assertRaises(ValueError):
            charge_time_s(100.0e-6, 28.0, 0.0)

    def test_startable_capacitance_inverts_the_charge_time(self):
        top = startable_capacitance_f(28.0, 1.70, 8.0e-3, 1.20)
        self.assertAlmostEqual(
            charge_time_s(top, 28.0, 1.70) * 1.20, 8.0e-3, places=12
        )

    def test_startable_capacitance_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            startable_capacitance_f(28.0, 1.70, 8.0e-3, 0.8)


class SweepTests(unittest.TestCase):
    def test_sweep_walks_from_nothing_to_the_tabulated_maximum(self):
        samples = sweep_operating_range(_class("class-2"), 28.0)
        self.assertAlmostEqual(samples[0]["capacitance_f"], 0.0, places=15)
        self.assertAlmostEqual(samples[-1]["capacitance_f"], 220.0e-6, places=12)

    def test_sweep_returns_the_requested_number_of_points(self):
        samples = sweep_operating_range(_class("class-2"), 28.0)
        self.assertEqual(len(samples), DEFAULT_RANGE_POLICY["sweep_points"])

    def test_charge_time_rises_across_the_sweep(self):
        samples = sweep_operating_range(_class("class-2"), 28.0)
        times = [s["charge_time_s"] for s in samples]
        self.assertEqual(times, sorted(times))

    def test_a_class_that_covers_its_range_passes_every_sample(self):
        samples = sweep_operating_range(_class("class-3"), 28.0)
        self.assertTrue(all(s["within_trip_off"] for s in samples))

    def test_a_high_bus_voltage_fails_the_upper_samples_first(self):
        samples = sweep_operating_range(_class("class-2"), 120.0)
        self.assertTrue(samples[0]["within_trip_off"])
        self.assertFalse(samples[-1]["within_trip_off"])


class ClassAssessmentTests(unittest.TestCase):
    def test_nominal_class_covers_its_own_tabulated_range(self):
        assessment = assess_class_capacitance_range(_class("class-2"), 28.0)
        self.assertTrue(assessment["covers_own_range"])
        self.assertGreater(assessment["range_headroom_f"], 0.0)

    def test_a_tabulated_maximum_exactly_on_the_bound_still_covers(self):
        assessment = assess_class_capacitance_range(EXACT_TABLE[0], 28.0)
        self.assertTrue(assessment["covers_own_range"])
        self.assertAlmostEqual(assessment["range_headroom_f"], 0.0, places=9)

    def test_a_high_bus_voltage_breaks_the_tabulated_range(self):
        assessment = assess_class_capacitance_range(_class("class-2"), 120.0)
        self.assertFalse(assessment["covers_own_range"])
        self.assertLess(assessment["range_headroom_f"], 0.0)


class SelectionTests(unittest.TestCase):
    def test_smallest_covering_class_is_taken(self):
        selection = select_capacitance_class(DEFAULT_CLASS_TABLE, 172.5e-6, 28.0)
        self.assertEqual(selection["selected"]["name"], "class-2")

    def test_a_class_too_small_for_the_load_is_rejected_by_name(self):
        selection = select_capacitance_class(DEFAULT_CLASS_TABLE, 172.5e-6, 28.0)
        rejected = {r["name"] for r in selection["rejections"]}
        self.assertIn("class-1", rejected)

    def test_every_class_is_assessed_even_after_one_is_taken(self):
        selection = select_capacitance_class(DEFAULT_CLASS_TABLE, 172.5e-6, 28.0)
        self.assertEqual(len(selection["assessments"]), len(DEFAULT_CLASS_TABLE))

    def test_a_load_above_every_tabulated_maximum_takes_no_class(self):
        selection = select_capacitance_class(DEFAULT_CLASS_TABLE, 2300.0e-6, 28.0)
        self.assertIsNone(selection["selected"])

    def test_rejection_names_both_reasons_when_both_apply(self):
        selection = select_capacitance_class(DEFAULT_CLASS_TABLE, 172.5e-6, 120.0)
        reasons = [r for row in selection["rejections"] for r in row["reasons"]]
        self.assertTrue(any(FINDING_ABOVE_TABULATED in r for r in reasons))
        self.assertTrue(any(FINDING_RANGE_NOT_STARTABLE in r for r in reasons))


class AssessmentTests(unittest.TestCase):
    def test_nominal_case_is_compliant_and_quiet(self):
        result = assess_load_capacitance_operating_range(NOMINAL_CASE)
        self.assertEqual(result["verdict"], VERDICT_COVERED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_nominal_case_names_the_class_it_took(self):
        result = assess_load_capacitance_operating_range(NOMINAL_CASE)
        self.assertEqual(result["selected_class"], "class-2")
        self.assertAlmostEqual(result["tabulated_usage"], 172.5 / 220.0, places=9)

    def test_an_oversized_load_has_no_class_and_says_so(self):
        result = assess_load_capacitance_operating_range(
            _case(declared_capacitance_f=2000.0e-6)
        )
        self.assertEqual(result["verdict"], VERDICT_NOT_COVERED)
        self.assertTrue(any(FINDING_NO_CLASS in f for f in result["findings"]))

    def test_a_bus_voltage_no_class_can_charge_against_is_not_covered(self):
        result = assess_load_capacitance_operating_range(_case(bus_voltage_v=120.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any(FINDING_RANGE_NOT_STARTABLE in f for f in result["findings"])
        )

    def test_a_tiny_load_on_a_large_class_raises_a_usage_advisory(self):
        result = assess_load_capacitance_operating_range(
            _case(declared_capacitance_f=20.0e-6)
        )
        self.assertTrue(result["compliant"])
        self.assertTrue(any(ADVISORY_LOW_USAGE in a for a in result["advisories"]))

    def test_a_table_sitting_on_its_own_bound_raises_a_headroom_advisory(self):
        result = assess_load_capacitance_operating_range(
            _case(declared_capacitance_f=100.0e-6, class_table=EXACT_TABLE)
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(ADVISORY_THIN_RANGE in a for a in result["advisories"]))

    def test_assessment_rejects_a_case_missing_the_class_table(self):
        case = _case()
        del case["class_table"]
        with self.assertRaises(ValueError):
            assess_load_capacitance_operating_range(case)

    def test_assessment_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            assess_load_capacitance_operating_range("150 uF")

    def test_assessment_reports_the_effective_range_it_worked_from(self):
        result = assess_load_capacitance_operating_range(NOMINAL_CASE)
        self.assertAlmostEqual(
            result["effective_capacitance"]["max_f"], 172.5e-6, places=12
        )


if __name__ == "__main__":
    unittest.main()
