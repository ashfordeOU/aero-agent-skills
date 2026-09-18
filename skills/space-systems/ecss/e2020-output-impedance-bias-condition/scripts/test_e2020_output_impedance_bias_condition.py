#!/usr/bin/env python3
"""Contract test for the output impedance bias condition (offline)."""

import copy
import unittest

from e2020_output_impedance_bias_condition_logic import (
    ADVISORY_BUS_SHARE,
    DEFAULT_BIAS_POLICY,
    FINDING_COMMONALITY,
    FINDING_CONSISTENCY,
    FINDING_DISSIPATION,
    FINDING_REFERENCE,
    FINDING_WINDOW,
    VERDICT_COMPLIANT,
    VERDICT_NONCOMPLIANT,
    assess_bias_record,
    assess_bias_reporting,
    declared_drop_spread,
    dissipation_w,
    drop_share_of_bus,
    implied_drop_v,
    relative_deviation,
    validate_bias_policy,
    validate_bias_record,
    validate_bias_records,
)

REFERENCE_DROP_V = 0.30

RECORD_A = {
    "class_name": "lcl-a",
    "declared_drop_v": 0.30,
    "load_current_a": 1.0,
    "series_resistance_ohm": 0.30,
    "bus_voltage_v": 28.0,
}

RECORD_B = {
    "class_name": "lcl-b",
    "declared_drop_v": 0.30,
    "load_current_a": 2.0,
    "series_resistance_ohm": 0.15,
    "bus_voltage_v": 28.0,
}

RECORD_C = {
    "class_name": "lcl-c",
    "declared_drop_v": 0.30,
    "load_current_a": 4.0,
    "series_resistance_ohm": 0.075,
    "bus_voltage_v": 28.0,
}

NOMINAL_SET = (RECORD_A, RECORD_B, RECORD_C)


def _record(base=RECORD_A, **overrides):
    row = copy.deepcopy(base)
    row.update(overrides)
    return row


def _consistent(name, drop_v, bus_voltage_v=28.0, load_current_a=1.0):
    """A record whose current and resistance reproduce the declared drop."""
    return {
        "class_name": name,
        "declared_drop_v": drop_v,
        "load_current_a": load_current_a,
        "series_resistance_ohm": drop_v / load_current_a,
        "bus_voltage_v": bus_voltage_v,
    }


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_bias_policy(DEFAULT_BIAS_POLICY), DEFAULT_BIAS_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_policy("default")

    def test_zero_reference_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_policy(dict(DEFAULT_BIAS_POLICY, reference_drop_rel_tol=0.0))

    def test_consistency_tolerance_at_or_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_policy(
                dict(DEFAULT_BIAS_POLICY, drop_consistency_rel_tol=1.0)
            )

    def test_inverted_operating_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_policy(dict(DEFAULT_BIAS_POLICY, max_operating_drop_v=0.01))

    def test_zero_dissipation_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_policy(
                dict(DEFAULT_BIAS_POLICY, device_dissipation_limit_w=0.0)
            )

    def test_bus_share_ceiling_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_policy(
                dict(DEFAULT_BIAS_POLICY, bus_drop_share_advisory_ceiling=1.5)
            )


class RecordValidationTests(unittest.TestCase):
    def test_nominal_record_validates(self):
        row = validate_bias_record(RECORD_A)
        self.assertEqual(row["class_name"], "lcl-a")
        self.assertAlmostEqual(row["declared_drop_v"], 0.30, places=9)

    def test_record_missing_the_series_resistance_rejected(self):
        row = _record()
        del row["series_resistance_ohm"]
        with self.assertRaises(ValueError):
            validate_bias_record(row)

    def test_zero_declared_drop_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_record(_record(declared_drop_v=0.0))

    def test_negative_load_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_record(_record(load_current_a=-1.0))

    def test_blank_class_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_record(_record(class_name="  "))

    def test_drop_above_the_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_record(_record(declared_drop_v=30.0))

    def test_boolean_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_record(_record(bus_voltage_v=True))

    def test_repeated_class_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_records([_record(), _record()])

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_records([])

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_bias_records(_record())


class ArithmeticTests(unittest.TestCase):
    def test_implied_drop_is_current_times_resistance(self):
        self.assertAlmostEqual(implied_drop_v(2.0, 0.15), 0.30, places=9)

    def test_implied_drop_rises_with_the_current(self):
        self.assertGreater(implied_drop_v(4.0, 0.15), implied_drop_v(1.0, 0.15))

    def test_zero_resistance_has_no_implied_drop(self):
        with self.assertRaises(ValueError):
            implied_drop_v(2.0, 0.0)

    def test_dissipation_is_current_times_drop(self):
        self.assertAlmostEqual(dissipation_w(4.0, 0.30), 1.20, places=9)

    def test_relative_deviation_is_symmetric_in_magnitude(self):
        high = relative_deviation(0.33, 0.30)
        low = relative_deviation(0.27, 0.30)
        self.assertAlmostEqual(high, low, places=9)

    def test_relative_deviation_of_a_match_is_zero(self):
        self.assertAlmostEqual(relative_deviation(0.30, 0.30), 0.0, places=12)

    def test_zero_reference_has_no_relative_deviation(self):
        with self.assertRaises(ValueError):
            relative_deviation(0.30, 0.0)

    def test_bus_share_is_the_drop_over_the_bus(self):
        self.assertAlmostEqual(drop_share_of_bus(0.30, 15.0), 0.02, places=9)


class AssessRecordTests(unittest.TestCase):
    def test_nominal_record_is_acceptable(self):
        result = assess_bias_record(RECORD_A, REFERENCE_DROP_V)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_a_drop_away_from_the_reference_is_a_finding(self):
        result = assess_bias_record(
            _consistent("lcl-a", 0.45), REFERENCE_DROP_V
        )
        self.assertFalse(result["on_reference"])
        self.assertTrue(any(FINDING_REFERENCE in f for f in result["findings"]))

    def test_a_drop_exactly_on_the_reference_tolerance_is_accepted(self):
        tol = float(DEFAULT_BIAS_POLICY["reference_drop_rel_tol"])
        edge = REFERENCE_DROP_V * (1.0 + tol)
        result = assess_bias_record(_consistent("lcl-a", edge), REFERENCE_DROP_V)
        self.assertAlmostEqual(result["reference_deviation"], tol, places=9)
        self.assertTrue(result["on_reference"])

    def test_a_drop_the_current_and_resistance_do_not_support_is_a_finding(self):
        result = assess_bias_record(
            _record(series_resistance_ohm=0.20), REFERENCE_DROP_V
        )
        self.assertTrue(result["on_reference"])
        self.assertFalse(result["consistent"])
        self.assertTrue(any(FINDING_CONSISTENCY in f for f in result["findings"]))

    def test_consistency_uses_the_implied_drop_not_the_reference(self):
        result = assess_bias_record(RECORD_C, REFERENCE_DROP_V)
        self.assertAlmostEqual(
            result["implied_drop_v"],
            RECORD_C["load_current_a"] * RECORD_C["series_resistance_ohm"],
            places=12,
        )
        self.assertTrue(result["consistent"])

    def test_a_drop_above_the_operating_window_is_a_finding(self):
        result = assess_bias_record(_consistent("lcl-a", 1.50), 0.90)
        self.assertFalse(result["within_operating_window"])
        self.assertTrue(any(FINDING_WINDOW in f for f in result["findings"]))

    def test_a_drop_exactly_on_the_window_floor_is_inside_it(self):
        floor = float(DEFAULT_BIAS_POLICY["min_operating_drop_v"])
        result = assess_bias_record(_consistent("lcl-a", floor), floor)
        self.assertTrue(result["within_operating_window"])
        self.assertTrue(result["acceptable"])

    def test_dissipation_above_the_device_limit_is_a_finding(self):
        result = assess_bias_record(
            _consistent("lcl-a", 0.90, load_current_a=40.0), 0.90
        )
        self.assertFalse(result["within_dissipation_limit"])
        self.assertTrue(any(FINDING_DISSIPATION in f for f in result["findings"]))

    def test_dissipation_exactly_on_the_device_limit_is_accepted(self):
        result = assess_bias_record(
            _consistent("lcl-a", 0.50, load_current_a=10.0), 0.50
        )
        self.assertAlmostEqual(
            result["dissipation_w"],
            float(DEFAULT_BIAS_POLICY["device_dissipation_limit_w"]),
            places=9,
        )
        self.assertTrue(result["within_dissipation_limit"])

    def test_a_large_bus_share_is_an_advisory_not_a_finding(self):
        result = assess_bias_record(
            _consistent("lcl-a", 0.30, bus_voltage_v=5.0), REFERENCE_DROP_V
        )
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(ADVISORY_BUS_SHARE in a for a in result["advisories"]))

    def test_a_bus_share_exactly_on_the_ceiling_stays_quiet(self):
        result = assess_bias_record(
            _consistent("lcl-a", 0.30, bus_voltage_v=15.0), REFERENCE_DROP_V
        )
        self.assertAlmostEqual(
            result["bus_share"],
            float(DEFAULT_BIAS_POLICY["bus_drop_share_advisory_ceiling"]),
            places=9,
        )
        self.assertEqual(result["advisories"], [])

    def test_a_reference_outside_the_operating_window_is_refused(self):
        with self.assertRaises(ValueError):
            assess_bias_record(RECORD_A, 2.50)

    def test_a_non_positive_reference_is_refused(self):
        with self.assertRaises(ValueError):
            assess_bias_record(RECORD_A, 0.0)


class ReportingTests(unittest.TestCase):
    def test_nominal_set_is_compliant(self):
        result = assess_bias_reporting(NOMINAL_SET, REFERENCE_DROP_V)
        self.assertEqual(result["verdict"], VERDICT_COMPLIANT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["acceptable_classes"]), 3)

    def test_one_shared_bias_point_reports_no_spread(self):
        result = assess_bias_reporting(NOMINAL_SET, REFERENCE_DROP_V)
        self.assertAlmostEqual(result["declared_drop_spread"], 0.0, places=12)
        self.assertTrue(result["shares_one_bias_point"])

    def test_records_straddling_the_tolerance_break_commonality(self):
        tol = float(DEFAULT_BIAS_POLICY["reference_drop_rel_tol"])
        records = (
            _consistent("lcl-a", REFERENCE_DROP_V * (1.0 + tol)),
            _consistent("lcl-b", REFERENCE_DROP_V * (1.0 - tol)),
        )
        result = assess_bias_reporting(records, REFERENCE_DROP_V)
        for a in result["assessments"]:
            self.assertTrue(a["on_reference"])
        self.assertFalse(result["shares_one_bias_point"])
        self.assertEqual(result["verdict"], VERDICT_NONCOMPLIANT)
        self.assertTrue(any(FINDING_COMMONALITY in f for f in result["findings"]))

    def test_spread_is_taken_against_the_mean_declared_drop(self):
        records = (
            _consistent("lcl-a", 0.33),
            _consistent("lcl-b", 0.27),
        )
        self.assertAlmostEqual(declared_drop_spread(records), 0.2, places=9)

    def test_one_inconsistent_record_turns_the_set_noncompliant(self):
        records = (RECORD_A, _record(RECORD_B, series_resistance_ohm=0.05), RECORD_C)
        result = assess_bias_reporting(records, REFERENCE_DROP_V)
        self.assertEqual(result["verdict"], VERDICT_NONCOMPLIANT)
        self.assertNotIn("lcl-b", result["acceptable_classes"])
        self.assertIn("lcl-a", result["acceptable_classes"])

    def test_every_record_gets_an_assessment_row(self):
        result = assess_bias_reporting(NOMINAL_SET, REFERENCE_DROP_V)
        self.assertEqual(len(result["assessments"]), len(NOMINAL_SET))

    def test_advisories_are_collected_across_the_set(self):
        records = (
            RECORD_A,
            _consistent("lcl-b", 0.30, bus_voltage_v=5.0),
        )
        result = assess_bias_reporting(records, REFERENCE_DROP_V)
        self.assertEqual(result["verdict"], VERDICT_COMPLIANT)
        self.assertTrue(any(ADVISORY_BUS_SHARE in a for a in result["advisories"]))

    def test_a_tighter_reference_tolerance_can_fail_a_passing_set(self):
        tol = float(DEFAULT_BIAS_POLICY["reference_drop_rel_tol"])
        records = (_consistent("lcl-a", REFERENCE_DROP_V * (1.0 + tol)),)
        strict = dict(DEFAULT_BIAS_POLICY, reference_drop_rel_tol=0.001)
        result = assess_bias_reporting(records, REFERENCE_DROP_V, strict)
        self.assertEqual(result["verdict"], VERDICT_NONCOMPLIANT)
        self.assertTrue(any(FINDING_REFERENCE in f for f in result["findings"]))

    def test_a_broken_record_set_is_refused(self):
        with self.assertRaises(ValueError):
            assess_bias_reporting((RECORD_A, _record(RECORD_B, load_current_a=0.0)), REFERENCE_DROP_V)

    def test_a_broken_policy_is_refused(self):
        with self.assertRaises(ValueError):
            assess_bias_reporting(
                NOMINAL_SET,
                REFERENCE_DROP_V,
                dict(DEFAULT_BIAS_POLICY, min_operating_drop_v=0.0),
            )

    def test_the_input_records_are_not_mutated(self):
        records = [_record(), _record(RECORD_B)]
        before = copy.deepcopy(records)
        assess_bias_reporting(records, REFERENCE_DROP_V)
        self.assertEqual(records, before)


if __name__ == "__main__":
    unittest.main()
