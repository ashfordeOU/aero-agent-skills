"""Contract tests for the clause 5.5.3.11.3 post-vacuum-cycling acceptance logic."""

import unittest

from e2008_vacuum_thermal_cycling_criteria_logic import (
    DEFAULT_TEMPERATURE_COEFFICIENTS_PER_C,
    LIMIT_TOLERANCE,
    PERFORMANCE_PARAMETERS,
    REFERENCE_IRRADIANCE_W_M2,
    REFERENCE_TEMPERATURE_C,
    VOC_IRRADIANCE_TOLERANCE,
    assess_vacuum_cycling_criteria,
    correct_reading_to_reference,
    degradation_fraction,
    evaluate_insulation,
    evaluate_performance,
    insulation_decades_lost,
    leakage_current_a,
    reading_at_reference,
    within_allowance,
)

ALLOWANCES = {"pmax_w": 0.03, "isc_a": 0.02, "voc_v": 0.02}


def _reading(pmax=10.0, isc=0.5, voc=25.0,
             irradiance=REFERENCE_IRRADIANCE_W_M2,
             temperature=REFERENCE_TEMPERATURE_C):
    return {
        "pmax_w": pmax,
        "isc_a": isc,
        "voc_v": voc,
        "irradiance_w_m2": irradiance,
        "cell_temperature_c": temperature,
    }


def _insulation(**overrides):
    record = {
        "test_voltage_v": 500.0,
        "min_resistance_ohm": 1.0e8,
        "pre_resistance_ohm": 1.0e10,
        "post_resistance_ohm": 2.0e9,
        "max_decades_lost": 1.0,
        "max_leakage_a": 1.0e-6,
    }
    record.update(overrides)
    return record


def _spec(**overrides):
    spec = {
        "pre_cycling": _reading(),
        "post_cycling": _reading(pmax=9.8, isc=0.495, voc=24.9),
        "allowances": dict(ALLOWANCES),
        "insulation": _insulation(),
    }
    spec.update(overrides)
    return spec


class AllowanceHelperTests(unittest.TestCase):
    def test_value_below_allowance_passes(self):
        self.assertTrue(within_allowance(0.01, 0.03))

    def test_value_above_allowance_fails(self):
        self.assertFalse(within_allowance(0.09, 0.03))

    def test_exact_equality_passes(self):
        self.assertTrue(within_allowance(0.03, 0.03))

    def test_equality_within_tolerance_passes(self):
        self.assertTrue(within_allowance(0.03 + LIMIT_TOLERANCE / 2.0, 0.03))

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            within_allowance("0.03", 0.03)

    def test_boolean_is_not_a_number(self):
        with self.assertRaises(ValueError):
            within_allowance(True, 0.03)


class CorrectionTests(unittest.TestCase):
    def test_a_reading_at_reference_is_unchanged(self):
        value = correct_reading_to_reference(
            10.0, "pmax_w", REFERENCE_IRRADIANCE_W_M2, REFERENCE_TEMPERATURE_C
        )
        self.assertAlmostEqual(value, 10.0, places=9)

    def test_half_irradiance_doubles_a_scaling_parameter(self):
        value = correct_reading_to_reference(
            5.0, "pmax_w", REFERENCE_IRRADIANCE_W_M2 / 2.0, REFERENCE_TEMPERATURE_C
        )
        self.assertAlmostEqual(value, 10.0, places=9)

    def test_open_circuit_voltage_does_not_scale_with_irradiance(self):
        value = correct_reading_to_reference(
            25.0, "voc_v", REFERENCE_IRRADIANCE_W_M2 / 2.0, REFERENCE_TEMPERATURE_C
        )
        self.assertAlmostEqual(value, 25.0, places=9)

    def test_hot_cell_corrects_upward_for_power(self):
        value = correct_reading_to_reference(
            10.0, "pmax_w", REFERENCE_IRRADIANCE_W_M2, 45.0
        )
        expected = 10.0 / (1.0 + DEFAULT_TEMPERATURE_COEFFICIENTS_PER_C["pmax_w"] * 20.0)
        self.assertAlmostEqual(value, expected, places=9)
        self.assertGreater(value, 10.0)

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            correct_reading_to_reference(
                10.0, "fill_factor", REFERENCE_IRRADIANCE_W_M2, REFERENCE_TEMPERATURE_C
            )

    def test_absurd_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            correct_reading_to_reference(
                10.0, "pmax_w", REFERENCE_IRRADIANCE_W_M2, 45.0, coefficient_per_c=3.0
            )

    def test_inconsistent_correction_factor_rejected(self):
        with self.assertRaises(ValueError):
            correct_reading_to_reference(
                10.0, "pmax_w", REFERENCE_IRRADIANCE_W_M2, 400.0
            )

    def test_zero_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            correct_reading_to_reference(10.0, "pmax_w", 0.0, REFERENCE_TEMPERATURE_C)

    def test_missing_reading_key_rejected(self):
        record = _reading()
        del record["cell_temperature_c"]
        with self.assertRaises(ValueError):
            reading_at_reference(record, "pmax_w")

    def test_coupon_coefficient_overrides_the_default(self):
        record = _reading(temperature=45.0)
        record["temperature_coefficients_per_c"] = {"pmax_w": -0.0030}
        value = reading_at_reference(record, "pmax_w")
        self.assertAlmostEqual(value, 10.0 / (1.0 - 0.0030 * 20.0), places=9)

    def test_non_mapping_coefficients_rejected(self):
        record = _reading()
        record["temperature_coefficients_per_c"] = [-0.0045]
        with self.assertRaises(ValueError):
            reading_at_reference(record, "pmax_w")


class DegradationTests(unittest.TestCase):
    def test_a_two_percent_loss_is_reported(self):
        self.assertAlmostEqual(degradation_fraction(10.0, 9.8), 0.02, places=9)

    def test_an_improvement_comes_back_negative(self):
        self.assertLess(degradation_fraction(10.0, 10.5), 0.0)

    def test_zero_before_value_rejected(self):
        with self.assertRaises(ValueError):
            degradation_fraction(0.0, 9.8)


class PerformanceTests(unittest.TestCase):
    def test_all_three_parameters_are_graded(self):
        result = evaluate_performance(_reading(), _reading(pmax=9.8), ALLOWANCES)
        self.assertEqual(
            [record["parameter"] for record in result["parameters"]],
            list(PERFORMANCE_PARAMETERS),
        )

    def test_a_compliant_coupon_raises_no_finding(self):
        result = evaluate_performance(
            _reading(), _reading(pmax=9.8, isc=0.495, voc=24.9), ALLOWANCES
        )
        self.assertTrue(result["within_allowances"])
        self.assertEqual(result["findings"], [])

    def test_a_loss_exactly_on_its_allowance_is_accepted(self):
        result = evaluate_performance(_reading(), _reading(pmax=9.7), ALLOWANCES)
        power = result["parameters"][0]
        self.assertAlmostEqual(power["loss_fraction"], 0.03, places=9)
        self.assertTrue(power["within_allowance"])

    def test_excess_power_loss_is_a_finding(self):
        result = evaluate_performance(_reading(), _reading(pmax=9.0), ALLOWANCES)
        self.assertFalse(result["within_allowances"])
        self.assertEqual(len(result["findings"]), 1)

    def test_each_parameter_is_graded_against_its_own_allowance(self):
        result = evaluate_performance(
            _reading(), _reading(pmax=9.8, isc=0.45, voc=24.9), ALLOWANCES
        )
        self.assertTrue(result["parameters"][0]["within_allowance"])
        self.assertFalse(result["parameters"][1]["within_allowance"])

    def test_retention_ratio_complements_the_loss(self):
        result = evaluate_performance(_reading(), _reading(pmax=9.8), ALLOWANCES)
        power = result["parameters"][0]
        self.assertAlmostEqual(
            power["retention_ratio"] + power["loss_fraction"], 1.0, places=9
        )

    def test_measurements_at_different_conditions_still_compare(self):
        result = evaluate_performance(
            _reading(),
            _reading(pmax=4.9, isc=0.2475, voc=24.9,
                     irradiance=REFERENCE_IRRADIANCE_W_M2 / 2.0),
            ALLOWANCES,
        )
        self.assertAlmostEqual(
            result["parameters"][0]["loss_fraction"], 0.02, places=9
        )

    def test_wide_irradiance_difference_invalidates_the_voltage_comparison(self):
        result = evaluate_performance(
            _reading(),
            _reading(pmax=4.9, isc=0.2475, voc=24.9,
                     irradiance=REFERENCE_IRRADIANCE_W_M2 / 2.0),
            ALLOWANCES,
        )
        self.assertFalse(result["voc_comparison_valid"])
        self.assertAlmostEqual(result["irradiance_deviation"], 0.5, places=9)

    def test_default_irradiance_tolerance_is_honoured(self):
        self.assertAlmostEqual(VOC_IRRADIANCE_TOLERANCE, 0.10, places=12)
        result = evaluate_performance(
            _reading(), _reading(irradiance=REFERENCE_IRRADIANCE_W_M2 * 1.05), ALLOWANCES
        )
        self.assertTrue(result["voc_comparison_valid"])

    def test_missing_allowance_rejected(self):
        allowances = dict(ALLOWANCES)
        del allowances["voc_v"]
        with self.assertRaises(ValueError):
            evaluate_performance(_reading(), _reading(), allowances)

    def test_allowance_outside_zero_to_one_rejected(self):
        allowances = dict(ALLOWANCES)
        allowances["pmax_w"] = 1.5
        with self.assertRaises(ValueError):
            evaluate_performance(_reading(), _reading(), allowances)


class InsulationTests(unittest.TestCase):
    def test_a_sound_insulation_is_acceptable(self):
        result = evaluate_insulation(_insulation())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["outcome"], "measured")

    def test_decades_lost_is_reported(self):
        result = evaluate_insulation(_insulation(post_resistance_ohm=1.0e9))
        self.assertAlmostEqual(result["decades_lost"], 1.0, places=9)

    def test_a_decade_loss_exactly_on_the_allowance_is_accepted(self):
        result = evaluate_insulation(_insulation(post_resistance_ohm=1.0e9))
        self.assertTrue(result["acceptable"])

    def test_excess_decade_loss_is_a_finding(self):
        result = evaluate_insulation(_insulation(post_resistance_ohm=5.0e8))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("decades" in f for f in result["findings"]))

    def test_resistance_below_the_floor_is_a_finding(self):
        result = evaluate_insulation(
            _insulation(post_resistance_ohm=1.0e7, max_decades_lost=5.0)
        )
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("floor" in f for f in result["findings"]))

    def test_resistance_exactly_on_the_floor_is_accepted(self):
        result = evaluate_insulation(
            _insulation(post_resistance_ohm=1.0e8, max_decades_lost=5.0,
                        max_leakage_a=1.0e-3)
        )
        self.assertTrue(result["acceptable"])

    def test_leakage_current_follows_the_test_voltage(self):
        result = evaluate_insulation(_insulation())
        self.assertAlmostEqual(result["leakage_current_a"], 500.0 / 2.0e9, places=15)

    def test_excess_leakage_is_a_finding(self):
        result = evaluate_insulation(
            _insulation(max_leakage_a=1.0e-9, max_decades_lost=5.0)
        )
        self.assertTrue(any("leakage" in f for f in result["findings"]))

    def test_breakdown_is_its_own_outcome(self):
        result = evaluate_insulation(_insulation(breakdown=True))
        self.assertEqual(result["outcome"], "dielectric-breakdown")
        self.assertIsNone(result["decades_lost"])
        self.assertFalse(result["acceptable"])

    def test_a_run_without_a_pre_value_skips_the_decade_check(self):
        record = _insulation()
        record["pre_resistance_ohm"] = None
        result = evaluate_insulation(record)
        self.assertIsNone(result["decades_lost"])
        self.assertTrue(result["acceptable"])

    def test_decades_lost_is_negative_when_resistance_improved(self):
        self.assertLess(insulation_decades_lost(1.0e9, 1.0e10), 0.0)

    def test_leakage_helper_rejects_zero_resistance(self):
        with self.assertRaises(ValueError):
            leakage_current_a(0.0, 500.0)

    def test_non_boolean_breakdown_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_insulation(_insulation(breakdown="yes"))

    def test_missing_post_resistance_rejected(self):
        record = _insulation()
        del record["post_resistance_ohm"]
        with self.assertRaises(ValueError):
            evaluate_insulation(record)

    def test_negative_post_resistance_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_insulation(_insulation(post_resistance_ohm=-1.0))


class AcceptanceTests(unittest.TestCase):
    def test_a_compliant_coupon_is_accepted(self):
        result = assess_vacuum_cycling_criteria(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_findings_accumulate_across_performance_and_insulation(self):
        result = assess_vacuum_cycling_criteria(
            _spec(
                post_cycling=_reading(pmax=8.0, isc=0.495, voc=24.9),
                insulation=_insulation(post_resistance_ohm=5.0e8),
            )
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(len(result["findings"]), 2)

    def test_a_breakdown_alone_rejects_the_coupon(self):
        result = assess_vacuum_cycling_criteria(
            _spec(insulation=_insulation(breakdown=True))
        )
        self.assertFalse(result["accepted"])

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["insulation"]
        with self.assertRaises(ValueError):
            assess_vacuum_cycling_criteria(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_vacuum_cycling_criteria(["insulation"])


if __name__ == "__main__":
    unittest.main()
