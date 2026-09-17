"""Contract tests for the Table 8-8 thermistor procurement matrix logic.

The cases follow the workflow one step at a time: lot validation, the
sampling rule that turns a percentage into whole devices, the Kelvin
conversion, the two-point beta derivation and the resistance it predicts,
the directional limit comparison, matrix coverage, the per-row verdict and
the disposition that stops a lot short of acceptance. Comparisons against a
computed exponential are made relatively, so the same case passes on every
platform the suite runs on.
"""

import unittest

from q6013_thermistor_procurement_test_table_logic import (
    ABSOLUTE_ZERO_C,
    CEIL_TOLERANCE,
    LIMIT_TOLERANCE,
    REFERENCE_TEMPERATURE_C,
    REQUIRED_TEST_GROUPS,
    assess_thermistor_test_table,
    derive_beta_constant,
    evaluate_characteristic,
    evaluate_measurement,
    matrix_coverage,
    predict_resistance,
    relative_deviation_percent,
    resolve_sample_size,
    row_verdict,
    to_kelvin,
    validate_lot_size,
    within_limit,
)

NOMINAL_OHM = 10000.0
NOMINAL_BETA = 3950.0


def _two_point(beta=NOMINAL_BETA):
    """Return a two-point reading generated from a known beta constant."""
    return {
        "low_ohm": predict_resistance(NOMINAL_OHM, beta, 0.0),
        "low_temperature_c": 0.0,
        "high_ohm": predict_resistance(NOMINAL_OHM, beta, 70.0),
        "high_temperature_c": 70.0,
    }


def _characteristic(**overrides):
    record = {
        "nominal_resistance_ohm": NOMINAL_OHM,
        "resistance_tolerance_percent": 2.0,
        "nominal_beta_kelvin": NOMINAL_BETA,
        "beta_tolerance_percent": 1.0,
        "measured_resistance_ohm": NOMINAL_OHM,
        "two_point": _two_point(),
    }
    record.update(overrides)
    return record


def _row(group, method="method-ref", sampling=None, failures=0, accept_number=0, **extra):
    record = {
        "group": group,
        "method": method,
        "sampling": sampling or {"mode": "fixed", "size": 15},
        "failures": failures,
        "accept_number": accept_number,
    }
    record.update(extra)
    return record


def _full_matrix(**per_group):
    return [_row(group, **per_group.get(group, {})) for group in REQUIRED_TEST_GROUPS]


def _spec(**overrides):
    spec = {
        "lot_size": 600,
        "entries": _full_matrix(),
        "characteristic": _characteristic(),
    }
    spec.update(overrides)
    return spec


class LotValidationTests(unittest.TestCase):
    def test_positive_lot_size_is_returned(self):
        self.assertEqual(validate_lot_size(600), 600)

    def test_single_device_lot_allowed(self):
        self.assertEqual(validate_lot_size(1), 1)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(0)

    def test_negative_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(-3)

    def test_float_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(600.0)

    def test_boolean_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(True)


class TemperatureTests(unittest.TestCase):
    def test_reference_temperature_converts_to_kelvin(self):
        self.assertAlmostEqual(to_kelvin(REFERENCE_TEMPERATURE_C), 298.15, places=9)

    def test_freezing_point_converts_to_kelvin(self):
        self.assertAlmostEqual(to_kelvin(0.0), 273.15, places=9)

    def test_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            to_kelvin(ABSOLUTE_ZERO_C)

    def test_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            to_kelvin(-300.0)

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            to_kelvin("25 C")


class CharacteristicModelTests(unittest.TestCase):
    def test_resistance_at_the_reference_temperature_is_the_nominal(self):
        value = predict_resistance(NOMINAL_OHM, NOMINAL_BETA, REFERENCE_TEMPERATURE_C)
        self.assertAlmostEqual(value / NOMINAL_OHM, 1.0, places=9)

    def test_resistance_falls_as_temperature_rises(self):
        hot = predict_resistance(NOMINAL_OHM, NOMINAL_BETA, 85.0)
        cold = predict_resistance(NOMINAL_OHM, NOMINAL_BETA, -40.0)
        self.assertLess(hot, NOMINAL_OHM)
        self.assertGreater(cold, NOMINAL_OHM)

    def test_two_point_reading_recovers_the_beta_it_was_built_from(self):
        derived = derive_beta_constant(**_two_point())
        self.assertAlmostEqual(derived / NOMINAL_BETA, 1.0, places=9)

    def test_a_higher_beta_gives_a_steeper_characteristic(self):
        steep = derive_beta_constant(**_two_point(beta=4200.0))
        self.assertAlmostEqual(steep / 4200.0, 1.0, places=9)

    def test_zero_reference_resistance_rejected(self):
        with self.assertRaises(ValueError):
            predict_resistance(0.0, NOMINAL_BETA, 50.0)

    def test_negative_beta_rejected(self):
        with self.assertRaises(ValueError):
            predict_resistance(NOMINAL_OHM, -100.0, 50.0)

    def test_two_readings_at_one_temperature_rejected(self):
        with self.assertRaises(ValueError):
            derive_beta_constant(12000.0, 25.0, 11000.0, 25.0)

    def test_resistance_rising_with_temperature_rejected(self):
        with self.assertRaises(ValueError):
            derive_beta_constant(8000.0, 0.0, 9000.0, 70.0)

    def test_deviation_is_signed_and_relative(self):
        self.assertAlmostEqual(relative_deviation_percent(10200.0, 10000.0), 2.0, places=9)

    def test_zero_nominal_deviation_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation_percent(10.0, 0.0)


class SamplingRuleTests(unittest.TestCase):
    def test_all_mode_takes_the_whole_lot(self):
        self.assertEqual(resolve_sample_size({"mode": "all"}, 240), 240)

    def test_fixed_mode_returns_the_declared_sample(self):
        self.assertEqual(resolve_sample_size({"mode": "fixed", "size": 15}, 600), 15)

    def test_percent_mode_rounds_up_to_a_whole_device(self):
        self.assertEqual(resolve_sample_size({"mode": "percent", "percent": 10.0}, 45), 5)

    def test_percent_landing_on_an_integer_is_not_inflated(self):
        # 125 * 2.4 / 100 evaluates a few units in the last place above 3.0;
        # the ceiling must still return three devices, not four.
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

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sample_size({"mode": "every-other-one"}, 100)

    def test_non_mapping_rule_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sample_size("all", 100)


class LimitComparisonTests(unittest.TestCase):
    def test_max_limit_accepts_a_lower_value(self):
        self.assertTrue(within_limit(2.0, 2.5, "max"))

    def test_max_limit_rejects_a_higher_value(self):
        self.assertFalse(within_limit(3.0, 2.5, "max"))

    def test_min_limit_accepts_an_exact_equality(self):
        self.assertTrue(within_limit(100.0, 100.0, "min"))

    def test_min_limit_rejects_a_low_insulation_resistance(self):
        self.assertFalse(within_limit(40.0, 100.0, "min"))

    def test_abs_delta_limit_catches_a_downward_drift(self):
        self.assertFalse(within_limit(-4.0, 3.0, "abs-delta"))

    def test_abs_delta_limit_accepts_a_small_drift_either_way(self):
        self.assertTrue(within_limit(-2.0, 3.0, "abs-delta"))

    def test_limit_tolerance_absorbs_representation_error(self):
        self.assertTrue(within_limit(2.5 + LIMIT_TOLERANCE / 2.0, 2.5, "max"))

    def test_negative_abs_delta_limit_rejected(self):
        with self.assertRaises(ValueError):
            within_limit(1.0, -2.0, "abs-delta")

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            within_limit(1.0, 5.0, "roughly")


class MeasurementRecordTests(unittest.TestCase):
    def test_record_carries_the_verdict(self):
        record = evaluate_measurement(
            {"parameter": "dissipation-constant", "measured": 7.5, "limit": 5.0,
             "direction": "min"}
        )
        self.assertTrue(record["within_limit"])

    def test_resistance_drift_outside_its_band_is_flagged(self):
        record = evaluate_measurement(
            {"parameter": "post-life-resistance-drift", "measured": 6.0, "limit": 3.0,
             "direction": "abs-delta"}
        )
        self.assertFalse(record["within_limit"])

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_measurement({"parameter": "insulation-resistance", "measured": 2.0})

    def test_blank_parameter_name_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_measurement(
                {"parameter": " ", "measured": 2.0, "limit": 2.5, "direction": "max"}
            )


class CharacteristicRecordTests(unittest.TestCase):
    def test_a_device_on_nominal_is_acceptable(self):
        record = evaluate_characteristic(_characteristic())
        self.assertTrue(record["acceptable"])
        self.assertAlmostEqual(record["derived_beta_kelvin"] / NOMINAL_BETA, 1.0, places=9)

    def test_resistance_outside_tolerance_is_a_finding(self):
        record = evaluate_characteristic(
            _characteristic(measured_resistance_ohm=NOMINAL_OHM * 1.05)
        )
        self.assertFalse(record["resistance_within_tolerance"])
        self.assertFalse(record["acceptable"])

    def test_beta_outside_tolerance_is_a_finding(self):
        record = evaluate_characteristic(_characteristic(two_point=_two_point(beta=4200.0)))
        self.assertFalse(record["beta_within_tolerance"])

    def test_predicted_resistance_is_reported_when_a_check_point_is_asked_for(self):
        record = evaluate_characteristic(_characteristic(check_temperature_c=85.0))
        self.assertLess(record["predicted_resistance_ohm"], NOMINAL_OHM)

    def test_missing_two_point_reading_rejected(self):
        record = _characteristic()
        del record["two_point"]
        with self.assertRaises(ValueError):
            evaluate_characteristic(record)

    def test_incomplete_two_point_reading_rejected(self):
        record = _characteristic()
        del record["two_point"]["high_ohm"]
        with self.assertRaises(ValueError):
            evaluate_characteristic(record)


class CoverageTests(unittest.TestCase):
    def test_full_matrix_is_complete(self):
        coverage = matrix_coverage(_full_matrix())
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["missing"], [])

    def test_missing_group_is_named(self):
        rows = [r for r in _full_matrix() if r["group"] != "life-test"]
        coverage = matrix_coverage(rows)
        self.assertIn("life-test", coverage["missing"])

    def test_duplicated_group_is_named(self):
        rows = _full_matrix() + [_row("thermal-shock", method="second-method")]
        coverage = matrix_coverage(rows)
        self.assertEqual(coverage["duplicated"], ["thermal-shock"])

    def test_unrecognized_group_is_reported_without_blocking_coverage(self):
        rows = _full_matrix() + [_row("board-mount-shear")]
        coverage = matrix_coverage(rows)
        self.assertEqual(coverage["unrecognized"], ["board-mount-shear"])
        self.assertTrue(coverage["complete"])

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage([])


class RowVerdictTests(unittest.TestCase):
    def test_clean_row_accepts(self):
        record = row_verdict(_row("thermal-shock", accept_number=1), 600)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["findings"], [])

    def test_failures_over_the_accept_number_reject(self):
        record = row_verdict(_row("life-test", failures=2, accept_number=1), 600)
        self.assertFalse(record["accepted"])

    def test_accept_number_used_in_full_is_marginal(self):
        record = row_verdict(_row("life-test", failures=1, accept_number=1), 600)
        self.assertTrue(record["accepted"])
        self.assertTrue(record["marginal"])

    def test_a_measurement_outside_its_limit_rejects_a_clean_count(self):
        record = row_verdict(
            _row(
                "insulation-resistance",
                measurements=[
                    {"parameter": "insulation-resistance", "measured": 40.0,
                     "limit": 100.0, "direction": "min"}
                ],
            ),
            600,
        )
        self.assertEqual(record["failures"], 0)
        self.assertFalse(record["accepted"])

    def test_failures_larger_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", failures=30, accept_number=1), 600)

    def test_blank_method_reference_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(_row("life-test", method="  "), 600)


class AssessmentTests(unittest.TestCase):
    def test_complete_clean_matrix_accepts(self):
        result = assess_thermistor_test_table(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept")

    def test_total_devices_tested_is_reported(self):
        result = assess_thermistor_test_table(_spec())
        self.assertEqual(result["total_devices_tested"], 15 * len(REQUIRED_TEST_GROUPS))

    def test_missing_group_holds_the_lot(self):
        rows = [r for r in _full_matrix() if r["group"] != "beta-constant-measurement"]
        result = assess_thermistor_test_table(_spec(entries=rows))
        self.assertEqual(result["disposition"], "hold")

    def test_characteristic_failure_holds_an_otherwise_clean_matrix(self):
        spec = _spec(characteristic=_characteristic(measured_resistance_ohm=NOMINAL_OHM * 1.1))
        result = assess_thermistor_test_table(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejecting_groups"], [])

    def test_every_rejecting_group_is_named_not_just_the_first(self):
        rows = _full_matrix(
            **{
                "life-test": {"failures": 3, "accept_number": 0},
                "moisture-resistance": {"failures": 2, "accept_number": 0},
            }
        )
        result = assess_thermistor_test_table(_spec(entries=rows))
        self.assertEqual(
            sorted(result["rejecting_groups"]), ["life-test", "moisture-resistance"]
        )

    def test_marginal_row_is_an_advisory_not_a_finding(self):
        rows = _full_matrix(**{"thermal-shock": {"failures": 1, "accept_number": 1}})
        result = assess_thermistor_test_table(_spec(entries=rows))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_matrix_without_a_characteristic_is_still_assessable(self):
        result = assess_thermistor_test_table({"lot_size": 600, "entries": _full_matrix()})
        self.assertIsNone(result["characteristic"])
        self.assertTrue(result["accepted"])

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["entries"]
        with self.assertRaises(ValueError):
            assess_thermistor_test_table(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermistor_test_table(["lot_size"])

    def test_ceiling_tolerance_is_small_enough_to_keep_one_device(self):
        self.assertLess(CEIL_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
