"""Contract tests for the clause 5.5.1.4.5 humidity post-exposure acceptance logic."""

import unittest

from e2008_humidity_test_pass_fail_criteria_logic import (
    DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C,
    LIMIT_TOLERANCE,
    REFERENCE_IRRADIANCE_W_M2,
    REFERENCE_TEMPERATURE_C,
    assess_humidity_acceptance,
    correct_power_to_reference,
    evaluate_continuity,
    evaluate_output_power,
    measurement_power_at_reference,
    power_loss_fraction,
    power_retention_ratio,
    resistance_increase_fraction,
    within_limit,
)

# A coupon measured at reference irradiance and reference cell temperature:
# the correction leaves such a record untouched, so the pre/post comparison in
# these fixtures is a comparison of coupon states alone.
AT_REFERENCE = {
    "power_w": 100.0,
    "irradiance_w_m2": REFERENCE_IRRADIANCE_W_M2,
    "cell_temperature_c": REFERENCE_TEMPERATURE_C,
}

GOOD_CIRCUITS = [
    {"circuit_id": "string-1", "pre_resistance_ohm": 0.400, "post_resistance_ohm": 0.404},
    {"circuit_id": "string-2", "pre_resistance_ohm": 0.500, "post_resistance_ohm": 0.505},
]


def _measurement(power_w, irradiance=REFERENCE_IRRADIANCE_W_M2,
                 temperature=REFERENCE_TEMPERATURE_C):
    return {
        "power_w": power_w,
        "irradiance_w_m2": irradiance,
        "cell_temperature_c": temperature,
    }


class WithinLimitTests(unittest.TestCase):
    def test_value_below_limit_passes(self):
        self.assertTrue(within_limit(0.02, 0.05))

    def test_value_above_limit_fails(self):
        self.assertFalse(within_limit(0.09, 0.05))

    def test_exact_equality_passes(self):
        self.assertTrue(within_limit(0.05, 0.05))

    def test_equality_within_tolerance_passes(self):
        self.assertTrue(within_limit(0.05 + LIMIT_TOLERANCE / 2.0, 0.05))

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            within_limit("0.05", 0.05)

    def test_boolean_limit_rejected(self):
        with self.assertRaises(ValueError):
            within_limit(0.05, True)


class PowerCorrectionTests(unittest.TestCase):
    def test_reference_conditions_leave_the_reading_unchanged(self):
        self.assertAlmostEqual(
            correct_power_to_reference(100.0, REFERENCE_IRRADIANCE_W_M2,
                                       REFERENCE_TEMPERATURE_C),
            100.0,
            places=9,
        )

    def test_half_irradiance_doubles_the_corrected_power(self):
        value = correct_power_to_reference(
            50.0, REFERENCE_IRRADIANCE_W_M2 / 2.0, REFERENCE_TEMPERATURE_C
        )
        self.assertAlmostEqual(value, 100.0, places=9)

    def test_hot_cell_reading_corrects_upward(self):
        hot = correct_power_to_reference(
            100.0, REFERENCE_IRRADIANCE_W_M2, REFERENCE_TEMPERATURE_C + 20.0
        )
        expected = 100.0 / (1.0 + DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C * 20.0)
        self.assertAlmostEqual(hot, expected, places=9)

    def test_cold_cell_reading_corrects_downward(self):
        cold = correct_power_to_reference(
            100.0, REFERENCE_IRRADIANCE_W_M2, REFERENCE_TEMPERATURE_C - 20.0
        )
        expected = 100.0 / (1.0 - DEFAULT_POWER_TEMPERATURE_COEFFICIENT_PER_C * 20.0)
        self.assertAlmostEqual(cold, expected, places=9)

    def test_zero_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            correct_power_to_reference(100.0, 0.0, REFERENCE_TEMPERATURE_C)

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            correct_power_to_reference(-100.0, REFERENCE_IRRADIANCE_W_M2, 25.0)

    def test_non_finite_temperature_rejected(self):
        with self.assertRaises(ValueError):
            correct_power_to_reference(
                100.0, REFERENCE_IRRADIANCE_W_M2, float("nan")
            )

    def test_out_of_range_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            correct_power_to_reference(
                100.0, REFERENCE_IRRADIANCE_W_M2, 25.0, temperature_coefficient_per_c=-4.0
            )

    def test_degenerate_correction_factor_rejected(self):
        with self.assertRaises(ValueError):
            correct_power_to_reference(
                100.0, REFERENCE_IRRADIANCE_W_M2, 45.0,
                temperature_coefficient_per_c=-0.05,
            )

    def test_measurement_record_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            measurement_power_at_reference({"power_w": 100.0})

    def test_measurement_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            measurement_power_at_reference([100.0, 1367.0, 25.0])

    def test_record_coefficient_overrides_the_default(self):
        record = _measurement(100.0, temperature=45.0)
        record["temperature_coefficient_per_c"] = -0.002
        expected = 100.0 / (1.0 - 0.002 * 20.0)
        self.assertAlmostEqual(
            measurement_power_at_reference(record), expected, places=9
        )


class PowerComparisonTests(unittest.TestCase):
    def test_loss_fraction_of_a_degraded_coupon(self):
        self.assertAlmostEqual(power_loss_fraction(100.0, 95.0), 0.05, places=9)

    def test_retention_ratio_complements_the_loss(self):
        self.assertAlmostEqual(power_retention_ratio(100.0, 95.0), 0.95, places=9)

    def test_power_gain_comes_back_negative(self):
        self.assertAlmostEqual(power_loss_fraction(100.0, 102.0), -0.02, places=9)

    def test_zero_pre_exposure_power_rejected(self):
        with self.assertRaises(ValueError):
            power_loss_fraction(0.0, 95.0)

    def test_evaluate_output_power_accepts_a_small_loss(self):
        result = evaluate_output_power(AT_REFERENCE, _measurement(97.0), 0.05)
        self.assertTrue(result["within_limit"])
        self.assertAlmostEqual(result["power_loss_fraction"], 0.03, places=9)

    def test_evaluate_output_power_rejects_a_large_loss(self):
        result = evaluate_output_power(AT_REFERENCE, _measurement(90.0), 0.05)
        self.assertFalse(result["within_limit"])

    def test_loss_exactly_at_the_limit_is_accepted(self):
        result = evaluate_output_power(AT_REFERENCE, _measurement(95.0), 0.05)
        self.assertAlmostEqual(result["power_loss_fraction"], 0.05, places=9)
        self.assertTrue(result["within_limit"])

    def test_measurement_conditions_do_not_create_a_false_loss(self):
        warm_and_dim = _measurement(
            48.0, irradiance=REFERENCE_IRRADIANCE_W_M2 / 2.0, temperature=45.0
        )
        result = evaluate_output_power(AT_REFERENCE, warm_and_dim, 0.05)
        self.assertTrue(result["within_limit"])

    def test_limit_outside_the_unit_range_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_output_power(AT_REFERENCE, _measurement(95.0), 1.5)


class ContinuityTests(unittest.TestCase):
    def test_resistance_increase_fraction(self):
        self.assertAlmostEqual(resistance_increase_fraction(0.5, 0.55), 0.1, places=9)

    def test_resistance_drop_comes_back_negative(self):
        self.assertAlmostEqual(resistance_increase_fraction(0.5, 0.45), -0.1, places=9)

    def test_all_circuits_within_allowance(self):
        records = evaluate_continuity(GOOD_CIRCUITS, 0.05)
        self.assertEqual(len(records), 2)
        self.assertTrue(all(record["within_allowance"] for record in records))

    def test_increase_exactly_at_the_allowance_is_accepted(self):
        records = evaluate_continuity(
            [{"circuit_id": "s", "pre_resistance_ohm": 1.0, "post_resistance_ohm": 1.25}],
            0.25,
        )
        self.assertAlmostEqual(records[0]["resistance_increase_fraction"], 0.25, places=9)
        self.assertTrue(records[0]["within_allowance"])

    def test_increase_past_the_allowance_is_flagged(self):
        records = evaluate_continuity(
            [{"circuit_id": "s", "pre_resistance_ohm": 1.0, "post_resistance_ohm": 2.0}],
            0.25,
        )
        self.assertFalse(records[0]["within_allowance"])

    def test_missing_post_reading_is_an_open_circuit(self):
        records = evaluate_continuity(
            [{"circuit_id": "s", "pre_resistance_ohm": 1.0, "post_resistance_ohm": None}],
            0.25,
        )
        self.assertTrue(records[0]["open_circuit"])
        self.assertFalse(records[0]["within_allowance"])
        self.assertIsNone(records[0]["resistance_increase_fraction"])

    def test_infinite_post_reading_is_an_open_circuit(self):
        records = evaluate_continuity(
            [{"circuit_id": "s", "pre_resistance_ohm": 1.0,
              "post_resistance_ohm": float("inf")}],
            0.25,
        )
        self.assertTrue(records[0]["open_circuit"])

    def test_empty_circuit_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity([], 0.25)

    def test_duplicate_circuit_id_rejected(self):
        circuits = [
            {"circuit_id": "s", "pre_resistance_ohm": 1.0, "post_resistance_ohm": 1.1},
            {"circuit_id": "s", "pre_resistance_ohm": 1.0, "post_resistance_ohm": 1.1},
        ]
        with self.assertRaises(ValueError):
            evaluate_continuity(circuits, 0.25)

    def test_missing_circuit_key_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity([{"circuit_id": "s", "pre_resistance_ohm": 1.0}], 0.25)

    def test_negative_pre_resistance_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity(
                [{"circuit_id": "s", "pre_resistance_ohm": -1.0,
                  "post_resistance_ohm": 1.1}],
                0.25,
            )

    def test_blank_circuit_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity(
                [{"circuit_id": "  ", "pre_resistance_ohm": 1.0,
                  "post_resistance_ohm": 1.1}],
                0.25,
            )

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity(GOOD_CIRCUITS, -0.1)


class AcceptanceTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "pre_exposure_measurement": dict(AT_REFERENCE),
            "post_exposure_measurement": _measurement(97.0),
            "circuits": [dict(circuit) for circuit in GOOD_CIRCUITS],
            "max_power_loss_fraction": 0.05,
            "max_resistance_increase_fraction": 0.05,
            "required_recovery_hours": 24.0,
            "recovery_hours": 26.0,
        }
        spec.update(overrides)
        return spec

    def test_clean_coupon_is_accepted(self):
        result = assess_humidity_acceptance(self._spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_power_shortfall_is_a_finding(self):
        result = assess_humidity_acceptance(
            self._spec(post_exposure_measurement=_measurement(80.0))
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(len(result["findings"]), 1)

    def test_open_circuit_is_a_finding(self):
        circuits = [dict(circuit) for circuit in GOOD_CIRCUITS]
        circuits[1]["post_resistance_ohm"] = None
        result = assess_humidity_acceptance(self._spec(circuits=circuits))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["open_circuit_count"], 1)

    def test_resistance_growth_is_a_finding_even_while_conducting(self):
        circuits = [dict(circuit) for circuit in GOOD_CIRCUITS]
        circuits[0]["post_resistance_ohm"] = 0.8
        result = assess_humidity_acceptance(self._spec(circuits=circuits))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["open_circuit_count"], 0)

    def test_short_recovery_period_is_a_finding(self):
        result = assess_humidity_acceptance(self._spec(recovery_hours=4.0))
        self.assertFalse(result["accepted"])
        self.assertIn("recovery", result["findings"][0])

    def test_recovery_exactly_at_the_required_period_is_accepted(self):
        spec = self._spec(recovery_hours=24.0)
        result = assess_humidity_acceptance(spec)
        self.assertAlmostEqual(spec["recovery_hours"],
                               spec["required_recovery_hours"], places=9)
        self.assertTrue(result["accepted"])

    def test_unrecorded_recovery_period_is_a_finding(self):
        spec = self._spec()
        del spec["recovery_hours"]
        result = assess_humidity_acceptance(spec)
        self.assertFalse(result["accepted"])

    def test_no_required_recovery_period_raises_nothing(self):
        spec = self._spec(required_recovery_hours=0.0)
        del spec["recovery_hours"]
        self.assertTrue(assess_humidity_acceptance(spec)["accepted"])

    def test_findings_accumulate_across_both_conditions(self):
        circuits = [dict(circuit) for circuit in GOOD_CIRCUITS]
        circuits[0]["post_resistance_ohm"] = None
        result = assess_humidity_acceptance(
            self._spec(circuits=circuits, post_exposure_measurement=_measurement(70.0))
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["circuits"]
        with self.assertRaises(ValueError):
            assess_humidity_acceptance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_humidity_acceptance(["circuits"])

    def test_negative_recovery_hours_rejected(self):
        with self.assertRaises(ValueError):
            assess_humidity_acceptance(self._spec(recovery_hours=-2.0))


if __name__ == "__main__":
    unittest.main()
