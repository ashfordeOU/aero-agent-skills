"""Contract tests for the Table 8-2 solid electrolyte tantalum matrix logic.

The cases follow the workflow one step at a time: the banded sampling plan,
the leakage allowance derived from the capacitance-voltage product, the
voltage derating ceiling, matrix coverage, the per-row verdict including the
surge-cycle count, and the disposition that stops a lot short of acceptance.
Each step is exercised on both sides of its limit, so a review of the record
shows what was judged and not only the verdict.
"""

import unittest

from q6013_tantalum_capacitor_chip_test_table_logic import (
    DEFAULT_DERATING_FACTOR,
    DEFAULT_LEAKAGE_FLOOR_UA,
    DEFAULT_SAMPLE_PLAN,
    LIMIT_TOLERANCE,
    REQUIRED_TEST_GROUPS,
    assess_tantalum_chip_test_table,
    check_application_voltage,
    derated_voltage_v,
    leakage_limit_ua,
    matrix_coverage,
    row_verdict,
    sample_plan_band,
    validate_lot_size,
)


def _row(group, method="method-ref", failures=0, **extra):
    record = {"group": group, "method": method, "failures": failures}
    record.update(extra)
    return record


def _full_matrix(**per_group):
    return [_row(group, **per_group.get(group, {})) for group in REQUIRED_TEST_GROUPS]


def _spec(**overrides):
    spec = {"lot_size": 400, "entries": _full_matrix()}
    spec.update(overrides)
    return spec


class LotAndPlanTests(unittest.TestCase):
    def test_positive_lot_size_is_returned(self):
        self.assertEqual(validate_lot_size(400), 400)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(0)

    def test_float_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(400.0)

    def test_band_is_chosen_by_lot_size(self):
        self.assertEqual(sample_plan_band(400), (20, 1))

    def test_lower_band_carries_a_zero_accept_number(self):
        self.assertEqual(sample_plan_band(120), (13, 0))

    def test_band_ceiling_is_inclusive(self):
        self.assertEqual(sample_plan_band(500), (20, 1))

    def test_one_device_above_a_ceiling_moves_up_a_band(self):
        self.assertEqual(sample_plan_band(501), (32, 1))

    def test_sample_cannot_exceed_a_tiny_lot(self):
        self.assertEqual(sample_plan_band(3), (3, 0))

    def test_lot_above_the_top_band_is_refused(self):
        with self.assertRaises(ValueError):
            sample_plan_band(5000)

    def test_custom_plan_extends_the_top_band(self):
        plan = list(DEFAULT_SAMPLE_PLAN) + [(10000, 80, 3)]
        self.assertEqual(sample_plan_band(5000, plan), (80, 3))

    def test_non_monotone_plan_rejected(self):
        with self.assertRaises(ValueError):
            sample_plan_band(100, [(50, 8, 0), (50, 13, 0)])

    def test_plan_accept_number_over_its_sample_rejected(self):
        with self.assertRaises(ValueError):
            sample_plan_band(100, [(150, 5, 8)])

    def test_malformed_band_rejected(self):
        with self.assertRaises(ValueError):
            sample_plan_band(100, [(150, 13)])


class LeakageAllowanceTests(unittest.TestCase):
    def test_allowance_scales_with_the_cv_product(self):
        self.assertAlmostEqual(leakage_limit_ua(100.0, 16.0), 16.0, places=9)

    def test_doubling_the_capacitance_doubles_the_allowance(self):
        small = leakage_limit_ua(47.0, 25.0)
        large = leakage_limit_ua(94.0, 25.0)
        self.assertAlmostEqual(large, 2.0 * small, places=9)

    def test_small_part_is_held_to_the_floor(self):
        self.assertAlmostEqual(leakage_limit_ua(1.0, 10.0), DEFAULT_LEAKAGE_FLOOR_UA, places=9)

    def test_custom_factor_is_honoured(self):
        self.assertAlmostEqual(leakage_limit_ua(100.0, 16.0, factor=0.02), 32.0, places=9)

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            leakage_limit_ua(0.0, 16.0)

    def test_negative_rated_voltage_rejected(self):
        with self.assertRaises(ValueError):
            leakage_limit_ua(100.0, -16.0)

    def test_non_numeric_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            leakage_limit_ua("100", 16.0)


class DeratingTests(unittest.TestCase):
    def test_default_derating_halves_the_rating(self):
        self.assertAlmostEqual(derated_voltage_v(35.0), 17.5, places=9)

    def test_custom_derating_factor_is_honoured(self):
        self.assertAlmostEqual(derated_voltage_v(35.0, 0.6), 21.0, places=9)

    def test_application_inside_the_ceiling_passes(self):
        record = check_application_voltage(12.0, 35.0)
        self.assertTrue(record["within_derating"])

    def test_application_exactly_on_the_ceiling_passes(self):
        record = check_application_voltage(17.5, 35.0)
        self.assertTrue(record["within_derating"])
        self.assertAlmostEqual(record["derated_ceiling_v"], 17.5, places=9)

    def test_application_over_the_ceiling_fails(self):
        self.assertFalse(check_application_voltage(25.0, 35.0)["within_derating"])

    def test_tolerance_absorbs_representation_error_at_the_ceiling(self):
        record = check_application_voltage(17.5 + LIMIT_TOLERANCE / 2.0, 35.0)
        self.assertTrue(record["within_derating"])

    def test_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            derated_voltage_v(35.0, 1.5)

    def test_zero_derating_factor_rejected(self):
        with self.assertRaises(ValueError):
            derated_voltage_v(35.0, 0.0)

    def test_default_factor_is_a_true_derating(self):
        self.assertLess(DEFAULT_DERATING_FACTOR, 1.0)


class CoverageTests(unittest.TestCase):
    def test_full_matrix_is_complete(self):
        self.assertTrue(matrix_coverage(_full_matrix())["complete"])

    def test_missing_surge_current_group_is_named(self):
        rows = [r for r in _full_matrix() if r["group"] != "surge-current"]
        self.assertIn("surge-current", matrix_coverage(rows)["missing"])

    def test_duplicated_group_is_named(self):
        rows = _full_matrix() + [_row("dc-leakage", method="second-method")]
        self.assertEqual(matrix_coverage(rows)["duplicated"], ["dc-leakage"])

    def test_extra_group_is_reported_as_an_addition(self):
        rows = _full_matrix() + [_row("moisture-sensitivity-level")]
        coverage = matrix_coverage(rows)
        self.assertEqual(coverage["unrecognized"], ["moisture-sensitivity-level"])
        self.assertTrue(coverage["complete"])

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage([])

    def test_row_without_a_group_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage([{"method": "method-ref"}])


class RowVerdictTests(unittest.TestCase):
    def test_clean_row_accepts(self):
        record = row_verdict(_row("thermal-shock"), 20, 1)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["findings"], [])

    def test_failures_over_the_accept_number_reject(self):
        record = row_verdict(_row("life-test", failures=3), 20, 1)
        self.assertFalse(record["accepted"])

    def test_accept_number_used_in_full_is_marginal(self):
        record = row_verdict(_row("life-test", failures=1), 20, 1)
        self.assertTrue(record["accepted"])
        self.assertTrue(record["marginal"])

    def test_leakage_over_its_allowance_rejects_a_clean_count(self):
        record = row_verdict(
            _row("dc-leakage", leakage_ua=25.0, leakage_limit_ua=16.0), 20, 1
        )
        self.assertEqual(record["failures"], 0)
        self.assertFalse(record["accepted"])

    def test_leakage_exactly_on_its_allowance_passes(self):
        record = row_verdict(
            _row("dc-leakage", leakage_ua=16.0, leakage_limit_ua=16.0), 20, 1
        )
        self.assertTrue(record["accepted"])

    def test_esr_over_its_limit_rejects(self):
        record = row_verdict(_row("esr-measurement", esr_ohm=1.4, esr_limit_ohm=1.0), 20, 1)
        self.assertFalse(record["accepted"])

    def test_short_surge_cycle_count_rejects(self):
        record = row_verdict(
            _row("surge-current", surge_cycles=5, required_surge_cycles=10), 20, 1
        )
        self.assertFalse(record["accepted"])

    def test_full_surge_cycle_count_passes(self):
        record = row_verdict(
            _row("surge-current", surge_cycles=10, required_surge_cycles=10), 20, 1
        )
        self.assertTrue(record["accepted"])

    def test_leakage_without_an_allowance_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("dc-leakage", leakage_ua=12.0), 20, 1)

    def test_negative_leakage_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("dc-leakage", leakage_ua=-1.0, leakage_limit_ua=16.0), 20, 1)

    def test_failures_larger_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", failures=30), 20, 1)

    def test_blank_method_reference_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", method="  "), 20, 1)


class AssessmentTests(unittest.TestCase):
    def test_complete_clean_matrix_accepts(self):
        result = assess_tantalum_chip_test_table(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept")

    def test_band_is_reported_with_the_verdict(self):
        result = assess_tantalum_chip_test_table(_spec())
        self.assertEqual(result["sample_size"], 20)
        self.assertEqual(result["accept_number"], 1)

    def test_leakage_allowance_is_derived_when_the_part_is_declared(self):
        result = assess_tantalum_chip_test_table(_spec(capacitance_uf=100.0, rated_voltage_v=16.0))
        self.assertAlmostEqual(result["leakage_allowance_ua"], 16.0, places=9)

    def test_allowance_is_absent_without_a_declared_part(self):
        self.assertIsNone(assess_tantalum_chip_test_table(_spec())["leakage_allowance_ua"])

    def test_overvoltage_application_holds_the_lot(self):
        result = assess_tantalum_chip_test_table(
            _spec(rated_voltage_v=16.0, applied_voltage_v=12.0)
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold")

    def test_derated_application_leaves_the_lot_clean(self):
        result = assess_tantalum_chip_test_table(
            _spec(rated_voltage_v=16.0, applied_voltage_v=8.0)
        )
        self.assertTrue(result["accepted"])
        self.assertTrue(result["derating"]["within_derating"])

    def test_applied_voltage_without_a_rating_rejected(self):
        with self.assertRaises(ValueError):
            assess_tantalum_chip_test_table(_spec(applied_voltage_v=8.0))

    def test_missing_group_holds_the_lot(self):
        rows = [r for r in _full_matrix() if r["group"] != "destructive-physical-analysis"]
        result = assess_tantalum_chip_test_table(_spec(entries=rows))
        self.assertFalse(result["accepted"])

    def test_every_rejecting_group_is_named_not_just_the_first(self):
        rows = _full_matrix(
            **{
                "life-test": {"failures": 4},
                "thermal-shock": {"failures": 3},
            }
        )
        result = assess_tantalum_chip_test_table(_spec(entries=rows))
        self.assertEqual(sorted(result["rejecting_groups"]), ["life-test", "thermal-shock"])

    def test_marginal_row_is_an_advisory_not_a_finding(self):
        rows = _full_matrix(**{"solderability": {"failures": 1}})
        result = assess_tantalum_chip_test_table(_spec(entries=rows))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["entries"]
        with self.assertRaises(ValueError):
            assess_tantalum_chip_test_table(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tantalum_chip_test_table(["lot_size"])

    def test_oversized_lot_without_an_extended_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_tantalum_chip_test_table(_spec(lot_size=9000))


if __name__ == "__main__":
    unittest.main()
