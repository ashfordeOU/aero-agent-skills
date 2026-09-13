#!/usr/bin/env python3
"""Contract test for the bleed resistor test (offline).

Walks the clause workflow step by step: the drawing band and its
asymmetric form, the referral of a reading back to the reference
temperature, the de-embedding of an in-circuit reading and the refusal
to sentence one without a declared parallel path, the value verdicts at
both band edges, the discharge the measured part actually delivers, and
the roll-up into one verdict. This is the gate 3 review evidence for the
leaf.
"""

import copy
import math
import unittest

from e2008_bleed_resistor_test_logic import (
    BLEED_RESISTOR_NOT_EVALUATED,
    BLEED_RESISTOR_NOT_VERIFIED,
    BLEED_RESISTOR_VERIFIED,
    BLEED_TIME_MET,
    BLEED_TIME_NOT_EVALUATED,
    BLEED_TIME_NOT_MET,
    DEFAULT_BLEED_SPEC,
    MEASUREMENT_CONFIGURATIONS,
    VALUE_ABOVE_BAND,
    VALUE_BELOW_BAND,
    VALUE_NOT_EVALUATED,
    VALUE_NOT_MEASURED,
    VALUE_OPEN,
    VALUE_WITHIN_BAND,
    acceptance_band_ohm,
    bleed_time_s,
    deembed_parallel_shunt_ohm,
    discharge_time_constant_s,
    evaluate_bleed_performance,
    evaluate_bleed_resistor_test,
    evaluate_resistance_reading,
    temperature_referred_resistance,
    validate_bleed_spec,
)

SPEC = dict(DEFAULT_BLEED_SPEC)

DISCHARGE = {
    "capacitance_f": 10.0e-6,
    "initial_voltage": 100.0,
    "safe_voltage": 1.0,
    "required_bleed_time_s": 10.0,
}


def _measurement(ohm, configuration="out-of-circuit", **extra):
    record = {"resistance_ohm": ohm, "configuration": configuration}
    record.update(extra)
    return record


class BandTests(unittest.TestCase):
    def test_symmetric_tolerance_gives_a_symmetric_band(self):
        low, high = acceptance_band_ohm(SPEC)
        self.assertAlmostEqual(low, 95000.0, places=9)
        self.assertAlmostEqual(high, 105000.0, places=9)

    def test_asymmetric_tolerance_is_honoured(self):
        spec = dict(SPEC)
        del spec["tolerance_fraction"]
        spec["tolerance_minus_fraction"] = 0.02
        spec["tolerance_plus_fraction"] = 0.10
        low, high = acceptance_band_ohm(spec)
        self.assertAlmostEqual(low, 98000.0, places=9)
        self.assertAlmostEqual(high, 110000.0, places=9)

    def test_minus_tolerance_of_one_rejected(self):
        spec = dict(SPEC)
        spec["tolerance_fraction"] = 1.0
        with self.assertRaises(ValueError):
            acceptance_band_ohm(spec)

    def test_non_positive_nominal_rejected(self):
        spec = dict(SPEC)
        spec["nominal_resistance_ohm"] = 0.0
        with self.assertRaises(ValueError):
            acceptance_band_ohm(spec)

    def test_open_threshold_inside_the_band_rejected(self):
        spec = dict(SPEC)
        spec["open_above_ohm"] = 1.0e4
        with self.assertRaises(ValueError):
            validate_bleed_spec(spec)

    def test_default_spec_validates(self):
        self.assertIn("tcr_ppm_per_k", validate_bleed_spec(dict(SPEC)))


class TemperatureTests(unittest.TestCase):
    def test_reading_at_reference_is_unchanged(self):
        self.assertAlmostEqual(
            temperature_referred_resistance(1.0e5, 22.0, 22.0, 100.0), 1.0e5, places=6
        )

    def test_warm_reading_is_referred_downward(self):
        referred = temperature_referred_resistance(1.0e5, 42.0, 22.0, 100.0)
        self.assertAlmostEqual(referred, 1.0e5 / (1.0 + 100.0e-6 * 20.0), places=6)

    def test_negative_coefficient_moves_the_other_way(self):
        warm = temperature_referred_resistance(1.0e5, 42.0, 22.0, -100.0)
        self.assertAlmostEqual(warm, 1.0e5 / (1.0 - 100.0e-6 * 20.0), places=6)

    def test_correction_beyond_the_linear_model_rejected(self):
        with self.assertRaises(ValueError):
            temperature_referred_resistance(1.0e5, 1.0e6, 22.0, -100.0)

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            temperature_referred_resistance(-1.0, 22.0, 22.0, 100.0)


class DeembedTests(unittest.TestCase):
    def test_parallel_path_is_removed_from_the_reading(self):
        self.assertAlmostEqual(
            deembed_parallel_shunt_ohm(50000.0, 100000.0), 100000.0, places=6
        )

    def test_a_weak_parallel_path_barely_moves_the_reading(self):
        recovered = deembed_parallel_shunt_ohm(99000.0, 1.0e7)
        self.assertAlmostEqual(recovered, 1.0 / (1.0 / 99000.0 - 1.0e-7), places=6)

    def test_parallel_path_at_or_below_the_reading_rejected(self):
        with self.assertRaises(ValueError):
            deembed_parallel_shunt_ohm(100000.0, 100000.0)

    def test_non_positive_reading_rejected(self):
        with self.assertRaises(ValueError):
            deembed_parallel_shunt_ohm(0.0, 100000.0)


class DischargeTests(unittest.TestCase):
    def test_time_constant_is_the_product(self):
        self.assertAlmostEqual(
            discharge_time_constant_s(1.0e5, 10.0e-6), 1.0, places=12
        )

    def test_bleed_time_scales_with_the_voltage_ratio(self):
        elapsed = bleed_time_s(1.0e5, 10.0e-6, 100.0, 1.0)
        self.assertAlmostEqual(elapsed, math.log(100.0), places=9)

    def test_safe_voltage_at_or_above_the_initial_rejected(self):
        with self.assertRaises(ValueError):
            bleed_time_s(1.0e5, 10.0e-6, 100.0, 100.0)

    def test_non_positive_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            discharge_time_constant_s(1.0e5, 0.0)

    def test_adequate_drain_meets_the_required_time(self):
        performance = evaluate_bleed_performance(1.0e5, dict(DISCHARGE))
        self.assertEqual(performance["verdict"], BLEED_TIME_MET)
        self.assertAlmostEqual(performance["time_constant_s"], 1.0, places=12)

    def test_slow_drain_does_not_meet_the_required_time(self):
        discharge = dict(DISCHARGE)
        discharge["required_bleed_time_s"] = 1.0
        performance = evaluate_bleed_performance(1.0e5, discharge)
        self.assertEqual(performance["verdict"], BLEED_TIME_NOT_MET)
        self.assertTrue(performance["findings"])

    def test_no_resistance_leaves_the_drain_unevaluated(self):
        performance = evaluate_bleed_performance(None, dict(DISCHARGE))
        self.assertEqual(performance["verdict"], BLEED_TIME_NOT_EVALUATED)


class ValueVerdictTests(unittest.TestCase):
    def test_part_inside_the_band_passes(self):
        record = evaluate_resistance_reading(SPEC, _measurement(1.0e5))
        self.assertEqual(record["verdict"], VALUE_WITHIN_BAND)
        self.assertTrue(record["within_band"])

    def test_part_exactly_on_the_band_ceiling_passes(self):
        record = evaluate_resistance_reading(SPEC, _measurement(105000.0))
        self.assertAlmostEqual(record["referred_resistance_ohm"], 105000.0, places=6)
        self.assertEqual(record["verdict"], VALUE_WITHIN_BAND)

    def test_part_exactly_on_the_band_floor_passes(self):
        record = evaluate_resistance_reading(SPEC, _measurement(95000.0))
        self.assertAlmostEqual(record["referred_resistance_ohm"], 95000.0, places=6)
        self.assertEqual(record["verdict"], VALUE_WITHIN_BAND)

    def test_high_part_is_above_the_band(self):
        record = evaluate_resistance_reading(SPEC, _measurement(1.3e5))
        self.assertEqual(record["verdict"], VALUE_ABOVE_BAND)

    def test_low_part_is_below_the_band(self):
        record = evaluate_resistance_reading(SPEC, _measurement(7.0e4))
        self.assertEqual(record["verdict"], VALUE_BELOW_BAND)

    def test_no_reading_is_an_open_part(self):
        record = evaluate_resistance_reading(SPEC, _measurement(None))
        self.assertEqual(record["verdict"], VALUE_OPEN)

    def test_reading_above_the_open_threshold_is_an_open_part(self):
        record = evaluate_resistance_reading(SPEC, _measurement(5.0e9))
        self.assertEqual(record["verdict"], VALUE_OPEN)

    def test_absent_measurement_is_not_measured(self):
        record = evaluate_resistance_reading(SPEC, None)
        self.assertEqual(record["verdict"], VALUE_NOT_MEASURED)
        self.assertIsNone(record["within_band"])

    def test_in_circuit_reading_without_a_parallel_value_is_not_evaluated(self):
        record = evaluate_resistance_reading(
            SPEC, _measurement(5.0e4, configuration="in-circuit")
        )
        self.assertEqual(record["verdict"], VALUE_NOT_EVALUATED)
        self.assertTrue(any("in-circuit" in item for item in record["findings"]))

    def test_in_circuit_reading_is_deembedded_before_grading(self):
        record = evaluate_resistance_reading(
            SPEC,
            _measurement(
                5.0e4, configuration="in-circuit", parallel_resistance_ohm=1.0e5
            ),
        )
        self.assertAlmostEqual(record["deembedded_resistance_ohm"], 1.0e5, places=6)
        self.assertEqual(record["verdict"], VALUE_WITHIN_BAND)

    def test_unknown_configuration_rejected(self):
        self.assertEqual(len(MEASUREMENT_CONFIGURATIONS), 2)
        with self.assertRaises(ValueError):
            evaluate_resistance_reading(
                SPEC, _measurement(1.0e5, configuration="somehow")
            )

    def test_warm_reading_is_graded_after_referral(self):
        record = evaluate_resistance_reading(
            SPEC, _measurement(1.0e5, temperature_c=42.0)
        )
        self.assertLess(record["referred_resistance_ohm"], 1.0e5)
        self.assertEqual(record["verdict"], VALUE_WITHIN_BAND)


class CampaignTests(unittest.TestCase):
    def _campaign(self, measurement, discharge=None, spec=None):
        campaign = {
            "spec": dict(spec or SPEC),
            "measurement": copy.deepcopy(measurement),
        }
        if discharge is not None:
            campaign["discharge"] = dict(discharge)
        return campaign

    def test_sound_part_and_drain_is_verified(self):
        result = evaluate_bleed_resistor_test(
            self._campaign(_measurement(1.0e5), DISCHARGE)
        )
        self.assertEqual(result["verdict"], BLEED_RESISTOR_VERIFIED)
        self.assertTrue(result["compliant"])

    def test_out_of_band_part_is_not_verified(self):
        result = evaluate_bleed_resistor_test(
            self._campaign(_measurement(1.3e5), DISCHARGE)
        )
        self.assertEqual(result["verdict"], BLEED_RESISTOR_NOT_VERIFIED)
        self.assertFalse(result["compliant"])

    def test_in_band_part_that_drains_too_slowly_is_not_verified(self):
        discharge = dict(DISCHARGE)
        discharge["required_bleed_time_s"] = 1.0
        result = evaluate_bleed_resistor_test(
            self._campaign(_measurement(1.0e5), discharge)
        )
        self.assertEqual(result["verdict"], BLEED_RESISTOR_NOT_VERIFIED)
        self.assertEqual(result["value"]["verdict"], VALUE_WITHIN_BAND)

    def test_missing_discharge_case_leaves_it_unevaluated(self):
        result = evaluate_bleed_resistor_test(self._campaign(_measurement(1.0e5)))
        self.assertEqual(result["verdict"], BLEED_RESISTOR_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])

    def test_unmeasured_part_leaves_it_unevaluated(self):
        result = evaluate_bleed_resistor_test(self._campaign(None, DISCHARGE))
        self.assertEqual(result["verdict"], BLEED_RESISTOR_NOT_EVALUATED)

    def test_findings_carry_both_halves(self):
        discharge = dict(DISCHARGE)
        discharge["required_bleed_time_s"] = 1.0
        result = evaluate_bleed_resistor_test(
            self._campaign(_measurement(1.3e5), discharge)
        )
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_bleed_resistor_test("the bleed resistor measured fine")


if __name__ == "__main__":
    unittest.main()
