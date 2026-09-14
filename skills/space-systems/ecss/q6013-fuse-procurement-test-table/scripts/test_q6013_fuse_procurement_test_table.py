"""Contract tests for the Table 8-4 fuse procurement test matrix logic.

The cases follow the workflow one step at a time: row validation, the
destructive sample budget, the voltage-drop limit, the time-current window,
the rated-current endurance rule and the lot disposition that carries them.
Each step is exercised on both sides of its limit, so a review of the record
shows what was judged and not only the verdict.
"""

import unittest

from q6013_fuse_procurement_test_table_logic import (
    LIMIT_TOLERANCE,
    MARGINAL_FRACTION,
    assess_fuse_test_matrix,
    endurance_verdict,
    fusing_time_verdict,
    row_verdict,
    sample_budget,
    validate_row,
    voltage_drop_verdict,
)


def _row(method="external-visual", sample_size=20, **extra):
    record = {"method": method, "sample_size": sample_size}
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "lot_size": 200,
        "flight_quantity": 40,
        "allowable_percent": 5.0,
        "rows": [
            _row("external-visual", 20, accept_number=1, failures=0),
            _row("fusing-time-current", 12, accept_number=0, failures=0),
            _row("breaking-capacity", 6, accept_number=0, failures=0),
        ],
    }
    spec.update(overrides)
    return spec


class RowValidationTests(unittest.TestCase):
    def test_valid_row_is_normalised(self):
        record = validate_row(_row("external-visual", 20, accept_number=2), 200)
        self.assertEqual(record["method"], "external-visual")
        self.assertEqual(record["sample_size"], 20)
        self.assertEqual(record["accept_number"], 2)

    def test_known_destructive_method_flagged_without_an_override(self):
        record = validate_row(_row("fusing-time-current", 12), 200)
        self.assertTrue(record["destructive"])

    def test_non_destructive_method_defaults_to_returnable(self):
        record = validate_row(_row("external-visual", 12), 200)
        self.assertFalse(record["destructive"])

    def test_declared_override_beats_the_method_default(self):
        record = validate_row(_row("external-visual", 12, destructive=True), 200)
        self.assertTrue(record["destructive"])

    def test_sample_larger_than_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 201), 200)

    def test_zero_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 0), 200)

    def test_accept_number_above_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 5, accept_number=6), 200)

    def test_more_failures_than_sampled_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 5, failures=6), 200)

    def test_empty_method_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("   ", 5), 200)

    def test_non_mapping_row_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(["external-visual", 5], 200)


class SampleBudgetTests(unittest.TestCase):
    def test_destructive_units_added_to_the_flight_quantity(self):
        budget = sample_budget(_spec()["rows"], 200, 40)
        self.assertEqual(budget["destructive_units"], 18)
        self.assertEqual(budget["minimum_purchase_quantity"], 58)

    def test_non_destructive_rows_do_not_consume_units(self):
        budget = sample_budget([_row("external-visual", 20)], 200, 40)
        self.assertEqual(budget["destructive_units"], 0)
        self.assertEqual(budget["minimum_purchase_quantity"], 40)

    def test_lot_short_of_the_budget_reports_a_shortfall(self):
        budget = sample_budget(_spec()["rows"], 50, 40)
        self.assertFalse(budget["lot_covers_budget"])
        self.assertEqual(budget["shortfall"], 8)

    def test_lot_exactly_covering_the_budget_is_sufficient(self):
        budget = sample_budget(_spec()["rows"], 58, 40)
        self.assertTrue(budget["lot_covers_budget"])
        self.assertEqual(budget["shortfall"], 0)

    def test_zero_flight_quantity_rejected(self):
        with self.assertRaises(ValueError):
            sample_budget(_spec()["rows"], 200, 0)

    def test_empty_row_set_rejected(self):
        with self.assertRaises(ValueError):
            sample_budget([], 200, 40)


class VoltageDropTests(unittest.TestCase):
    def test_readings_under_the_limit_accept(self):
        record = voltage_drop_verdict([80.0, 92.5, 88.0], 120.0)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["failures"], 0)

    def test_reading_on_the_limit_is_admissible(self):
        record = voltage_drop_verdict([120.0], 120.0)
        self.assertTrue(record["accepted"])
        self.assertAlmostEqual(record["used_fraction"], 1.0, places=9)

    def test_reading_over_the_limit_is_counted(self):
        record = voltage_drop_verdict([80.0, 131.0], 120.0)
        self.assertFalse(record["accepted"])
        self.assertEqual(record["over_limit_indices"], [1])

    def test_worst_reading_is_reported(self):
        record = voltage_drop_verdict([80.0, 131.0, 99.0], 120.0)
        self.assertAlmostEqual(record["worst_mv"], 131.0, places=9)

    def test_non_positive_reading_rejected(self):
        with self.assertRaises(ValueError):
            voltage_drop_verdict([80.0, 0.0], 120.0)

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            voltage_drop_verdict([80.0], 0.0)

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            voltage_drop_verdict([], 120.0)


class FusingTimeTests(unittest.TestCase):
    def test_times_inside_the_window_accept(self):
        record = fusing_time_verdict([0.9, 1.4, 2.0], 0.5, 3.0, 2.0)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["failures"], 0)

    def test_time_on_the_lower_bound_is_admissible(self):
        record = fusing_time_verdict([0.5], 0.5, 3.0, 2.0)
        self.assertTrue(record["accepted"])
        self.assertAlmostEqual(record["fastest_s"], 0.5, places=9)

    def test_time_on_the_upper_bound_is_admissible(self):
        record = fusing_time_verdict([3.0], 0.5, 3.0, 2.0)
        self.assertTrue(record["accepted"])
        self.assertAlmostEqual(record["slowest_s"], 3.0, places=9)

    def test_early_opening_is_a_reject_not_a_pass(self):
        record = fusing_time_verdict([0.2, 1.0], 0.5, 3.0, 2.0)
        self.assertFalse(record["accepted"])
        self.assertEqual(record["early_indices"], [0])

    def test_late_opening_is_a_reject(self):
        record = fusing_time_verdict([1.0, 4.5], 0.5, 3.0, 2.0)
        self.assertFalse(record["accepted"])
        self.assertEqual(record["late_indices"], [1])

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            fusing_time_verdict([1.0], 3.0, 0.5, 2.0)

    def test_overload_multiple_at_rated_current_rejected(self):
        with self.assertRaises(ValueError):
            fusing_time_verdict([1.0], 0.5, 3.0, 1.0)

    def test_non_positive_time_rejected(self):
        with self.assertRaises(ValueError):
            fusing_time_verdict([0.0], 0.5, 3.0, 2.0)


class EnduranceTests(unittest.TestCase):
    def test_no_unit_opening_accepts(self):
        record = endurance_verdict(0, 10, 1000.0)
        self.assertTrue(record["accepted"])

    def test_one_unit_opening_rejects(self):
        record = endurance_verdict(1, 10, 1000.0)
        self.assertFalse(record["accepted"])

    def test_more_opened_than_sampled_rejected(self):
        with self.assertRaises(ValueError):
            endurance_verdict(11, 10, 1000.0)

    def test_non_positive_duration_rejected(self):
        with self.assertRaises(ValueError):
            endurance_verdict(0, 10, 0.0)


class RowVerdictTests(unittest.TestCase):
    def test_failures_within_both_limits_accept(self):
        record = row_verdict(validate_row(_row("external-visual", 40, accept_number=2, failures=1), 200), 5.0)
        self.assertTrue(record["accepted"])
        self.assertAlmostEqual(record["percent_defective"], 2.5, places=9)

    def test_failures_over_the_accept_number_reject(self):
        record = row_verdict(validate_row(_row("external-visual", 40, accept_number=1, failures=3), 200), 50.0)
        self.assertFalse(record["accepted"])
        self.assertFalse(record["within_accept_number"])

    def test_rate_over_the_allowance_rejects_within_the_accept_number(self):
        record = row_verdict(validate_row(_row("external-visual", 10, accept_number=3, failures=2), 200), 5.0)
        self.assertFalse(record["accepted"])
        self.assertTrue(record["within_accept_number"])
        self.assertFalse(record["within_allowance"])

    def test_rate_exactly_on_the_allowance_is_admissible(self):
        record = row_verdict(validate_row(_row("external-visual", 20, accept_number=3, failures=1), 200), 5.0)
        self.assertTrue(record["within_allowance"])
        self.assertAlmostEqual(record["percent_defective"], 5.0, places=9)

    def test_marginal_row_is_flagged_but_accepted(self):
        record = row_verdict(validate_row(_row("external-visual", 25, accept_number=3, failures=1), 200), 5.0)
        self.assertTrue(record["accepted"])
        self.assertTrue(record["marginal"])

    def test_allowance_outside_zero_to_hundred_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(validate_row(_row("external-visual", 20), 200), 140.0)


class MatrixAssessmentTests(unittest.TestCase):
    def test_clean_matrix_accepts_the_lot(self):
        result = assess_fuse_test_matrix(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-fuse-lot")
        self.assertEqual(result["rejecting_rows"], [])

    def test_every_rejecting_row_is_named_not_only_the_first(self):
        spec = _spec(
            rows=[
                _row("external-visual", 20, accept_number=0, failures=2),
                _row("fusing-time-current", 12, accept_number=0, failures=1),
                _row("breaking-capacity", 6, accept_number=0, failures=0),
            ]
        )
        result = assess_fuse_test_matrix(spec)
        self.assertEqual(
            result["rejecting_rows"], ["external-visual", "fusing-time-current"]
        )

    def test_repeated_method_rejected(self):
        spec = _spec(
            rows=[_row("external-visual", 20), _row("external-visual", 10)]
        )
        with self.assertRaises(ValueError):
            assess_fuse_test_matrix(spec)

    def test_budget_shortfall_holds_an_otherwise_clean_lot(self):
        result = assess_fuse_test_matrix(_spec(lot_size=50))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("cannot cover" in item for item in result["findings"]))

    def test_voltage_drop_failure_holds_the_lot(self):
        spec = _spec(voltage_drop={"readings_mv": [80.0, 140.0], "limit_mv": 120.0})
        result = assess_fuse_test_matrix(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold-fuse-lot")

    def test_early_opening_named_separately_from_late_opening(self):
        spec = _spec(
            fusing_time={
                "times_s": [0.2, 4.0],
                "min_s": 0.5,
                "max_s": 3.0,
                "overload_multiple": 2.0,
            }
        )
        result = assess_fuse_test_matrix(spec)
        self.assertTrue(any("before the" in item for item in result["findings"]))
        self.assertTrue(any("after the" in item for item in result["findings"]))

    def test_endurance_opening_holds_a_lot_with_clean_rows(self):
        spec = _spec(endurance={"opened_units": 1, "sample_size": 10, "hours": 1000.0})
        result = assess_fuse_test_matrix(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejecting_rows"], [])

    def test_missing_rows_key_rejected(self):
        spec = _spec()
        del spec["rows"]
        with self.assertRaises(ValueError):
            assess_fuse_test_matrix(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_fuse_test_matrix(["not", "a", "mapping"])

    def test_non_mapping_voltage_drop_block_rejected(self):
        with self.assertRaises(ValueError):
            assess_fuse_test_matrix(_spec(voltage_drop=[120.0]))

    def test_tolerance_and_marginal_fraction_are_named_constants(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)
        self.assertLess(MARGINAL_FRACTION, 1.0)


if __name__ == "__main__":
    unittest.main()
