"""Contract tests for the Table 8-5 magnetics procurement test matrix logic.

The cases follow the workflow one step at a time: row validation, the
winding-resistance temperature correction, the three limit shapes, the
dielectric-withstanding run and the lot disposition that carries them. Each
step is exercised on both sides of its limit, so a review of the record shows
what was judged and not only the verdict.
"""

import unittest

from q6013_magnetics_procurement_test_table_logic import (
    COPPER_INFERRED_ZERO_C,
    LIMIT_KINDS,
    LIMIT_TOLERANCE,
    MARGINAL_FRACTION,
    REFERENCE_TEMPERATURE_C,
    assess_magnetics_test_matrix,
    corrected_winding_resistance,
    dielectric_withstanding_verdict,
    limit_verdict,
    row_verdict,
    validate_row,
    winding_resistance_verdict,
)


def _row(method="external-visual", sample_size=20, **extra):
    record = {"method": method, "sample_size": sample_size}
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "lot_size": 150,
        "allowable_percent": 5.0,
        "rows": [
            _row("external-visual", 20, accept_number=1, failures=0),
            _row("winding-resistance", 12, accept_number=0, failures=0),
            _row("insulation-resistance", 12, accept_number=0, failures=0, limit_kind="minimum"),
            _row("turns-ratio", 8, accept_number=0, failures=0, limit_kind="band"),
        ],
    }
    spec.update(overrides)
    return spec


class CorrectionTests(unittest.TestCase):
    def test_reading_at_the_reference_temperature_is_unchanged(self):
        self.assertAlmostEqual(
            corrected_winding_resistance(1.4321, 20.0, 20.0), 1.4321, places=9
        )

    def test_halving_factor_on_a_hand_worked_constant(self):
        # zero point 1.0, reference 1.0, measured 3.0 -> factor (1+1)/(1+3) = 0.5
        self.assertAlmostEqual(
            corrected_winding_resistance(2.0, 3.0, 1.0, 1.0), 1.0, places=9
        )

    def test_copper_correction_from_seventy_five_degrees(self):
        # 1 ohm at 75 degC corrects to (234.5+20)/(234.5+75) = 254.5/309.5 ohm
        self.assertAlmostEqual(
            corrected_winding_resistance(1.0, 75.0), 0.8222940226, places=9
        )

    def test_warm_reading_corrects_downwards(self):
        warm = corrected_winding_resistance(1.0, 60.0)
        self.assertLess(warm, 1.0)

    def test_cold_reading_corrects_upwards(self):
        cold = corrected_winding_resistance(1.0, -30.0)
        self.assertGreater(cold, 1.0)

    def test_non_positive_resistance_rejected(self):
        with self.assertRaises(ValueError):
            corrected_winding_resistance(0.0, 25.0)

    def test_temperature_at_the_inferred_zero_rejected(self):
        with self.assertRaises(ValueError):
            corrected_winding_resistance(1.0, -COPPER_INFERRED_ZERO_C)

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            corrected_winding_resistance(1.0, "warm")


class WindingResistanceTests(unittest.TestCase):
    def test_corrected_readings_under_the_limit_accept(self):
        record = winding_resistance_verdict([(1.15, 60.0), (1.12, 58.0)], 1.10)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["failures"], 0)

    def test_uncorrected_warm_reading_would_have_failed(self):
        record = winding_resistance_verdict([(1.15, 60.0)], 1.10)
        self.assertGreater(1.15, record["limit_ohm"])
        self.assertTrue(record["accepted"])

    def test_corrected_reading_over_the_limit_is_counted(self):
        record = winding_resistance_verdict([(1.40, 25.0)], 1.10)
        self.assertFalse(record["accepted"])
        self.assertEqual(record["over_limit_indices"], [0])

    def test_reading_on_the_limit_is_admissible(self):
        record = winding_resistance_verdict([(1.10, 20.0)], 1.10)
        self.assertTrue(record["accepted"])
        self.assertAlmostEqual(record["used_fraction"], 1.0, places=9)

    def test_malformed_reading_pair_rejected(self):
        with self.assertRaises(ValueError):
            winding_resistance_verdict([(1.10,)], 1.10)

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            winding_resistance_verdict([], 1.10)

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            winding_resistance_verdict([(1.0, 20.0)], 0.0)


class LimitShapeTests(unittest.TestCase):
    def test_three_shapes_are_named(self):
        self.assertEqual(set(LIMIT_KINDS), {"maximum", "minimum", "band"})

    def test_maximum_accepts_a_small_value(self):
        record = limit_verdict([0.4, 0.6], "maximum", upper=1.0)
        self.assertTrue(record["accepted"])

    def test_minimum_rejects_a_small_value(self):
        record = limit_verdict([0.4], "minimum", lower=1.0)
        self.assertFalse(record["accepted"])
        self.assertEqual(record["under_indices"], [0])

    def test_insulation_resistance_high_value_accepts_on_a_minimum(self):
        record = limit_verdict([5000.0, 12000.0], "minimum", lower=1000.0)
        self.assertTrue(record["accepted"])

    def test_band_rejects_on_both_sides(self):
        record = limit_verdict([0.90, 1.00, 1.15], "band", lower=0.95, upper=1.05)
        self.assertEqual(record["under_indices"], [0])
        self.assertEqual(record["over_indices"], [2])
        self.assertEqual(record["failures"], 2)

    def test_value_on_a_band_bound_is_admissible(self):
        record = limit_verdict([0.95, 1.05], "band", lower=0.95, upper=1.05)
        self.assertTrue(record["accepted"])

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            limit_verdict([1.0], "band", lower=1.05, upper=0.95)

    def test_maximum_without_an_upper_bound_rejected(self):
        with self.assertRaises(ValueError):
            limit_verdict([1.0], "maximum")

    def test_minimum_without_a_lower_bound_rejected(self):
        with self.assertRaises(ValueError):
            limit_verdict([1.0], "minimum")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            limit_verdict([1.0], "tolerance", lower=0.0, upper=2.0)


class DielectricTests(unittest.TestCase):
    def test_leakage_under_the_limit_accepts(self):
        record = dielectric_withstanding_verdict(12.0, 50.0, 1500.0, 1500.0)
        self.assertTrue(record["accepted"])

    def test_leakage_on_the_limit_is_admissible(self):
        record = dielectric_withstanding_verdict(50.0, 50.0, 1500.0, 1500.0)
        self.assertTrue(record["accepted"])
        self.assertAlmostEqual(record["used_fraction"], 1.0, places=9)

    def test_leakage_over_the_limit_rejects(self):
        record = dielectric_withstanding_verdict(61.0, 50.0, 1500.0, 1500.0)
        self.assertFalse(record["accepted"])

    def test_run_below_the_required_voltage_refused(self):
        with self.assertRaises(ValueError):
            dielectric_withstanding_verdict(12.0, 50.0, 1000.0, 1500.0)

    def test_negative_leakage_rejected(self):
        with self.assertRaises(ValueError):
            dielectric_withstanding_verdict(-1.0, 50.0, 1500.0, 1500.0)


class RowTests(unittest.TestCase):
    def test_valid_row_is_normalised(self):
        record = validate_row(_row("winding-resistance", 12, accept_number=1), 150)
        self.assertEqual(record["sample_size"], 12)
        self.assertEqual(record["limit_kind"], "maximum")

    def test_declared_limit_kind_is_kept(self):
        record = validate_row(_row("insulation-resistance", 12, limit_kind="minimum"), 150)
        self.assertEqual(record["limit_kind"], "minimum")

    def test_unknown_limit_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("insulation-resistance", 12, limit_kind="ceiling"), 150)

    def test_sample_larger_than_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 151), 150)

    def test_more_failures_than_sampled_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 5, failures=6), 150)

    def test_rate_exactly_on_the_allowance_is_admissible(self):
        record = row_verdict(validate_row(_row("external-visual", 20, accept_number=3, failures=1), 150), 5.0)
        self.assertTrue(record["within_allowance"])
        self.assertAlmostEqual(record["percent_defective"], 5.0, places=9)

    def test_rate_over_the_allowance_rejects_within_the_accept_number(self):
        record = row_verdict(validate_row(_row("external-visual", 10, accept_number=3, failures=2), 150), 5.0)
        self.assertFalse(record["accepted"])
        self.assertTrue(record["within_accept_number"])

    def test_marginal_row_is_flagged_but_accepted(self):
        record = row_verdict(validate_row(_row("external-visual", 25, accept_number=3, failures=1), 150), 5.0)
        self.assertTrue(record["accepted"])
        self.assertTrue(record["marginal"])


class MatrixAssessmentTests(unittest.TestCase):
    def test_clean_matrix_accepts_the_lot(self):
        result = assess_magnetics_test_matrix(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-magnetics-lot")

    def test_every_rejecting_row_is_named_not_only_the_first(self):
        spec = _spec(
            rows=[
                _row("external-visual", 20, accept_number=0, failures=2),
                _row("winding-resistance", 12, accept_number=0, failures=1),
                _row("turns-ratio", 8, accept_number=0, failures=0, limit_kind="band"),
            ]
        )
        result = assess_magnetics_test_matrix(spec)
        self.assertEqual(
            result["rejecting_rows"], ["external-visual", "winding-resistance"]
        )

    def test_repeated_method_rejected(self):
        spec = _spec(rows=[_row("external-visual", 20), _row("external-visual", 8)])
        with self.assertRaises(ValueError):
            assess_magnetics_test_matrix(spec)

    def test_corrected_winding_failure_holds_a_clean_matrix(self):
        spec = _spec(winding_resistance={"readings": [(1.60, 25.0)], "limit_ohm": 1.10})
        result = assess_magnetics_test_matrix(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejecting_rows"], [])

    def test_insulation_resistance_below_its_minimum_holds_the_lot(self):
        spec = _spec(
            measurements=[
                {
                    "name": "insulation-resistance",
                    "kind": "minimum",
                    "values": [400.0],
                    "lower": 1000.0,
                }
            ]
        )
        result = assess_magnetics_test_matrix(spec)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("below the lower bound" in item for item in result["findings"]))

    def test_turns_ratio_above_its_band_holds_the_lot(self):
        spec = _spec(
            measurements=[
                {
                    "name": "turns-ratio",
                    "kind": "band",
                    "values": [1.12],
                    "lower": 0.95,
                    "upper": 1.05,
                }
            ]
        )
        result = assess_magnetics_test_matrix(spec)
        self.assertTrue(any("above the upper bound" in item for item in result["findings"]))

    def test_dielectric_failure_holds_the_lot(self):
        spec = _spec(
            dielectric={
                "leakage_ua": 90.0,
                "limit_ua": 50.0,
                "applied_volts": 1500.0,
                "required_volts": 1500.0,
            }
        )
        result = assess_magnetics_test_matrix(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold-magnetics-lot")

    def test_unnamed_measurement_block_rejected(self):
        spec = _spec(measurements=[{"kind": "maximum", "values": [1.0], "upper": 2.0}])
        with self.assertRaises(ValueError):
            assess_magnetics_test_matrix(spec)

    def test_missing_rows_key_rejected(self):
        spec = _spec()
        del spec["rows"]
        with self.assertRaises(ValueError):
            assess_magnetics_test_matrix(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetics_test_matrix(["not", "a", "mapping"])

    def test_reference_temperature_and_tolerance_are_named_constants(self):
        self.assertAlmostEqual(REFERENCE_TEMPERATURE_C, 20.0, places=9)
        self.assertLess(LIMIT_TOLERANCE, 1e-6)
        self.assertLess(MARGINAL_FRACTION, 1.0)


if __name__ == "__main__":
    unittest.main()
