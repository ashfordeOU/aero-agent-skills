"""Contract tests for the Table 8-1 ceramic capacitor chip matrix logic.

The cases follow the workflow one step at a time: lot validation, the
sampling rule that turns a percentage into whole devices, the limit
comparison in each declared direction, matrix coverage, the per-row verdict
and the disposition that stops a lot short of acceptance. Each step is
exercised on both sides of its limit, so a review of the record shows what
was judged and not only the verdict.
"""

import unittest

from q6013_ceramic_capacitor_chip_test_table_logic import (
    CEIL_TOLERANCE,
    LIMIT_TOLERANCE,
    REQUIRED_TEST_GROUPS,
    assess_ceramic_chip_test_table,
    evaluate_measurement,
    matrix_coverage,
    resolve_sample_size,
    row_verdict,
    validate_lot_size,
    within_limit,
)


def _row(group, method="method-ref", sampling=None, failures=0, accept_number=0, **extra):
    record = {
        "group": group,
        "method": method,
        "sampling": sampling or {"mode": "fixed", "size": 20},
        "failures": failures,
        "accept_number": accept_number,
    }
    record.update(extra)
    return record


def _full_matrix(**per_group):
    rows = []
    for group in REQUIRED_TEST_GROUPS:
        rows.append(_row(group, **per_group.get(group, {})))
    return rows


def _spec(**overrides):
    spec = {"lot_size": 500, "entries": _full_matrix()}
    spec.update(overrides)
    return spec


class LotValidationTests(unittest.TestCase):
    def test_positive_lot_size_is_returned(self):
        self.assertEqual(validate_lot_size(500), 500)

    def test_single_device_lot_allowed(self):
        self.assertEqual(validate_lot_size(1), 1)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(0)

    def test_negative_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(-5)

    def test_float_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(500.0)

    def test_boolean_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(True)


class SamplingRuleTests(unittest.TestCase):
    def test_all_mode_takes_the_whole_lot(self):
        self.assertEqual(resolve_sample_size({"mode": "all"}, 320), 320)

    def test_fixed_mode_returns_the_declared_sample(self):
        self.assertEqual(resolve_sample_size({"mode": "fixed", "size": 22}, 500), 22)

    def test_percent_mode_rounds_up_to_a_whole_device(self):
        self.assertEqual(resolve_sample_size({"mode": "percent", "percent": 10.0}, 45), 5)

    def test_percent_landing_on_an_integer_is_not_inflated(self):
        # 125 * 2.4 / 100 evaluates a few ULPs above 3.0 in binary floating
        # point; the ceiling must still return three devices, not four.
        self.assertEqual(resolve_sample_size({"mode": "percent", "percent": 2.4}, 125), 3)

    def test_percent_minimum_floors_a_small_lot(self):
        rule = {"mode": "percent", "percent": 1.0, "minimum": 5}
        self.assertEqual(resolve_sample_size(rule, 100), 5)

    def test_percent_is_capped_at_the_lot(self):
        self.assertEqual(resolve_sample_size({"mode": "percent", "percent": 100.0}, 12), 12)

    def test_fixed_sample_larger_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sample_size({"mode": "fixed", "size": 40}, 30)

    def test_zero_percent_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sample_size({"mode": "percent", "percent": 0.0}, 100)

    def test_percent_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sample_size({"mode": "percent", "percent": 120.0}, 100)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sample_size({"mode": "every-other-one"}, 100)

    def test_non_mapping_rule_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sample_size("all", 100)

    def test_minimum_larger_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sample_size({"mode": "percent", "percent": 5.0, "minimum": 50}, 20)


class LimitComparisonTests(unittest.TestCase):
    def test_max_limit_accepts_a_lower_value(self):
        self.assertTrue(within_limit(2.0, 2.5, "max"))

    def test_max_limit_rejects_a_higher_value(self):
        self.assertFalse(within_limit(3.0, 2.5, "max"))

    def test_max_limit_accepts_an_exact_equality(self):
        self.assertTrue(within_limit(2.5, 2.5, "max"))

    def test_min_limit_accepts_an_exact_equality(self):
        self.assertTrue(within_limit(1000.0, 1000.0, "min"))

    def test_min_limit_rejects_a_lower_insulation_resistance(self):
        self.assertFalse(within_limit(800.0, 1000.0, "min"))

    def test_abs_delta_limit_catches_a_downward_drift(self):
        self.assertFalse(within_limit(-12.0, 10.0, "abs-delta"))

    def test_abs_delta_limit_accepts_a_small_drift_either_way(self):
        self.assertTrue(within_limit(-4.0, 10.0, "abs-delta"))

    def test_limit_tolerance_absorbs_representation_error(self):
        self.assertTrue(within_limit(2.5 + LIMIT_TOLERANCE / 2.0, 2.5, "max"))

    def test_negative_abs_delta_limit_rejected(self):
        with self.assertRaises(ValueError):
            within_limit(1.0, -5.0, "abs-delta")

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            within_limit(1.0, 5.0, "roughly")


class MeasurementRecordTests(unittest.TestCase):
    def test_record_carries_the_verdict(self):
        record = evaluate_measurement(
            {"parameter": "dissipation-factor", "measured": 2.0, "limit": 2.5, "direction": "max"}
        )
        self.assertTrue(record["within_limit"])
        self.assertAlmostEqual(record["measured"], 2.0)

    def test_capacitance_drift_outside_its_band_is_flagged(self):
        record = evaluate_measurement(
            {"parameter": "capacitance-drift", "measured": 15.0, "limit": 10.0,
             "direction": "abs-delta"}
        )
        self.assertFalse(record["within_limit"])

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_measurement({"parameter": "dissipation-factor", "measured": 2.0})

    def test_blank_parameter_name_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_measurement(
                {"parameter": "  ", "measured": 2.0, "limit": 2.5, "direction": "max"}
            )


class CoverageTests(unittest.TestCase):
    def test_full_matrix_is_complete(self):
        coverage = matrix_coverage(_full_matrix())
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["missing"], [])

    def test_missing_group_is_named(self):
        rows = [r for r in _full_matrix() if r["group"] != "life-test"]
        coverage = matrix_coverage(rows)
        self.assertIn("life-test", coverage["missing"])
        self.assertFalse(coverage["complete"])

    def test_duplicated_group_is_named(self):
        rows = _full_matrix() + [_row("thermal-shock", method="second-method")]
        coverage = matrix_coverage(rows)
        self.assertEqual(coverage["duplicated"], ["thermal-shock"])

    def test_unrecognized_group_is_reported_without_blocking_coverage(self):
        rows = _full_matrix() + [_row("board-level-reliability")]
        coverage = matrix_coverage(rows)
        self.assertEqual(coverage["unrecognized"], ["board-level-reliability"])
        self.assertTrue(coverage["complete"])

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage([])

    def test_row_without_a_group_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage([{"method": "method-ref"}])


class RowVerdictTests(unittest.TestCase):
    def test_clean_row_accepts(self):
        record = row_verdict(_row("thermal-shock", accept_number=1), 500)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["findings"], [])

    def test_failures_over_the_accept_number_reject(self):
        record = row_verdict(_row("life-test", failures=2, accept_number=1), 500)
        self.assertFalse(record["accepted"])
        self.assertEqual(len(record["findings"]), 1)

    def test_accept_number_used_in_full_is_marginal(self):
        record = row_verdict(_row("life-test", failures=1, accept_number=1), 500)
        self.assertTrue(record["accepted"])
        self.assertTrue(record["marginal"])

    def test_a_measurement_outside_its_limit_rejects_a_clean_count(self):
        record = row_verdict(
            _row(
                "electrical-measurement",
                measurements=[
                    {"parameter": "insulation-resistance", "measured": 500.0,
                     "limit": 1000.0, "direction": "min"}
                ],
            ),
            500,
        )
        self.assertEqual(record["failures"], 0)
        self.assertFalse(record["accepted"])

    def test_failures_larger_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", failures=30, accept_number=1), 500)

    def test_accept_number_larger_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", accept_number=40), 500)

    def test_missing_method_reference_rejected(self):
        entry = _row("life-test")
        del entry["method"]
        with self.assertRaises(ValueError):
            row_verdict(entry, 500)

    def test_blank_method_reference_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", method="   "), 500)


class AssessmentTests(unittest.TestCase):
    def test_complete_clean_matrix_accepts(self):
        result = assess_ceramic_chip_test_table(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["findings"], [])

    def test_total_devices_tested_is_reported(self):
        result = assess_ceramic_chip_test_table(_spec())
        self.assertEqual(result["total_devices_tested"], 20 * len(REQUIRED_TEST_GROUPS))

    def test_missing_group_holds_the_lot(self):
        rows = [r for r in _full_matrix() if r["group"] != "destructive-physical-analysis"]
        result = assess_ceramic_chip_test_table(_spec(entries=rows))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold")

    def test_every_rejecting_group_is_named_not_just_the_first(self):
        rows = _full_matrix(
            **{
                "life-test": {"failures": 3, "accept_number": 0},
                "thermal-shock": {"failures": 2, "accept_number": 0},
            }
        )
        result = assess_ceramic_chip_test_table(_spec(entries=rows))
        self.assertEqual(sorted(result["rejecting_groups"]), ["life-test", "thermal-shock"])

    def test_marginal_row_is_an_advisory_not_a_finding(self):
        rows = _full_matrix(**{"humidity-steady-state": {"failures": 1, "accept_number": 1}})
        result = assess_ceramic_chip_test_table(_spec(entries=rows))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_percent_sampling_scales_with_the_lot(self):
        rows = _full_matrix(**{"visual-inspection": {"sampling": {"mode": "all"}}})
        small = assess_ceramic_chip_test_table({"lot_size": 100, "entries": rows})
        large = assess_ceramic_chip_test_table({"lot_size": 400, "entries": rows})
        self.assertEqual(
            large["total_devices_tested"] - small["total_devices_tested"], 300
        )

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["entries"]
        with self.assertRaises(ValueError):
            assess_ceramic_chip_test_table(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_ceramic_chip_test_table(["lot_size"])

    def test_ceiling_tolerance_is_small_enough_to_keep_one_device(self):
        self.assertLess(CEIL_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
