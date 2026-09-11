"""
Offline unit tests for e1003_input_tolerances_logic.py.
Run: python3 test_e1003_input_tolerances.py
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1003_input_tolerances_logic import (
    SUPPORTED_INPUT_TYPES,
    ToleranceBand,
    check_all_inputs,
    check_input_tolerance,
    compute_deviation,
    get_tolerance,
)


class TestGetTolerance(unittest.TestCase):
    def test_temperature_band_type(self):
        band = get_tolerance("temperature")
        self.assertEqual(band.bound_type, "absolute")

    def test_temperature_band_limits(self):
        band = get_tolerance("temperature")
        self.assertEqual(band.lo, -2.0)
        self.assertEqual(band.hi, 2.0)

    def test_pressure_band_type(self):
        band = get_tolerance("pressure")
        self.assertEqual(band.bound_type, "percent")

    def test_voltage_band_limits(self):
        band = get_tolerance("voltage")
        self.assertEqual(band.lo, -1.0)
        self.assertEqual(band.hi, 1.0)

    def test_duration_lower_bound_zero(self):
        band = get_tolerance("duration")
        self.assertEqual(band.lo, 0.0)

    def test_random_vibration_psd_upper_bound_zero(self):
        band = get_tolerance("random_vibration_psd")
        self.assertEqual(band.hi, 0.0)

    def test_acoustic_spl_asymmetric(self):
        band = get_tolerance("acoustic_spl")
        self.assertLess(band.lo, 0.0)
        self.assertGreater(band.hi, 0.0)
        self.assertNotEqual(abs(band.lo), band.hi)

    def test_unrecognized_type_raises(self):
        with self.assertRaises(ValueError):
            get_tolerance("gamma_radiation")

    def test_unrecognized_empty_string_raises(self):
        with self.assertRaises(ValueError):
            get_tolerance("")

    def test_supported_types_contains_all_nine(self):
        self.assertGreaterEqual(len(SUPPORTED_INPUT_TYPES), 9)

    def test_supported_types_includes_humidity(self):
        self.assertIn("humidity", SUPPORTED_INPUT_TYPES)

    def test_returns_tolerance_band_namedtuple(self):
        band = get_tolerance("sine_vibration")
        self.assertIsInstance(band, ToleranceBand)


class TestComputeDeviation(unittest.TestCase):
    def test_absolute_positive_shift(self):
        dev = compute_deviation(100.0, 102.0, "absolute")
        self.assertAlmostEqual(dev, 2.0)

    def test_absolute_negative_shift(self):
        dev = compute_deviation(100.0, 97.5, "absolute")
        self.assertAlmostEqual(dev, -2.5)

    def test_absolute_no_shift(self):
        dev = compute_deviation(20.0, 20.0, "absolute")
        self.assertAlmostEqual(dev, 0.0)

    def test_percent_positive(self):
        dev = compute_deviation(28.0, 28.28, "percent")
        self.assertAlmostEqual(dev, 1.0, places=3)

    def test_percent_negative(self):
        dev = compute_deviation(28.0, 27.72, "percent")
        self.assertAlmostEqual(dev, -1.0, places=3)

    def test_db_unity_ratio(self):
        dev = compute_deviation(1.0, 1.0, "db")
        self.assertAlmostEqual(dev, 0.0)

    def test_db_doubled_power(self):
        dev = compute_deviation(1.0, 2.0, "db")
        self.assertAlmostEqual(dev, 10.0 * math.log10(2.0), places=6)

    def test_db_halved_power(self):
        dev = compute_deviation(1.0, 0.5, "db")
        self.assertAlmostEqual(dev, 10.0 * math.log10(0.5), places=6)

    def test_percent_zero_nominal_raises(self):
        with self.assertRaises(ValueError):
            compute_deviation(0.0, 5.0, "percent")

    def test_db_zero_nominal_raises(self):
        with self.assertRaises(ValueError):
            compute_deviation(0.0, 1.0, "db")

    def test_db_negative_actual_raises(self):
        with self.assertRaises(ValueError):
            compute_deviation(1.0, -0.5, "db")

    def test_unknown_bound_type_raises(self):
        with self.assertRaises(ValueError):
            compute_deviation(1.0, 1.0, "ratio")


class TestCheckInputTolerance(unittest.TestCase):
    def test_temperature_within_upper(self):
        res = check_input_tolerance("temperature", 20.0, 21.5)
        self.assertTrue(res["within_tolerance"])
        self.assertIsNone(res["finding"])

    def test_temperature_within_lower(self):
        res = check_input_tolerance("temperature", 20.0, 18.5)
        self.assertTrue(res["within_tolerance"])

    def test_temperature_exceeds_upper(self):
        res = check_input_tolerance("temperature", 20.0, 23.0)
        self.assertFalse(res["within_tolerance"])
        self.assertIsNotNone(res["finding"])

    def test_temperature_exceeds_lower(self):
        res = check_input_tolerance("temperature", 20.0, 17.0)
        self.assertFalse(res["within_tolerance"])

    def test_temperature_at_boundary(self):
        res = check_input_tolerance("temperature", 20.0, 22.0)
        self.assertTrue(res["within_tolerance"])

    def test_voltage_within_tolerance(self):
        res = check_input_tolerance("voltage", 28.0, 27.99)
        self.assertTrue(res["within_tolerance"])

    def test_voltage_exceeds_band(self):
        res = check_input_tolerance("voltage", 28.0, 30.0)
        self.assertFalse(res["within_tolerance"])

    def test_random_vibration_psd_within(self):
        # 10*log10(0.9) ≈ -0.46 dB, within [-1, 0]
        res = check_input_tolerance("random_vibration_psd", 1.0, 0.9)
        self.assertTrue(res["within_tolerance"])

    def test_random_vibration_psd_exceeds_upper(self):
        # actual > nominal → positive dB → above 0 dB upper limit
        res = check_input_tolerance("random_vibration_psd", 1.0, 1.2)
        self.assertFalse(res["within_tolerance"])

    def test_random_vibration_psd_too_low(self):
        # 10*log10(0.7) ≈ -1.55 dB, below -1 dB lower limit
        res = check_input_tolerance("random_vibration_psd", 1.0, 0.7)
        self.assertFalse(res["within_tolerance"])

    def test_duration_cannot_be_shorter(self):
        # deviation = (3500-3600)/3600*100 ≈ -2.78%, below 0% lower bound
        res = check_input_tolerance("duration", 3600.0, 3500.0)
        self.assertFalse(res["within_tolerance"])

    def test_duration_longer_within_band(self):
        # deviation = (3636-3600)/3600*100 = 1.0%, within [0, 2]
        res = check_input_tolerance("duration", 3600.0, 3636.0)
        self.assertTrue(res["within_tolerance"])

    def test_humidity_at_upper_boundary(self):
        # +5 %RH absolute = exactly at limit, should be within tolerance
        res = check_input_tolerance("humidity", 50.0, 55.0)
        self.assertTrue(res["within_tolerance"])

    def test_humidity_exceeds_upper(self):
        res = check_input_tolerance("humidity", 50.0, 56.0)
        self.assertFalse(res["within_tolerance"])

    def test_acoustic_spl_asymmetric_lower(self):
        # -2 dB lower limit: 10*log10(0.63) ≈ -2.0 dB → at boundary
        actual = 1.0 * (10 ** (-2.0 / 10.0))
        res = check_input_tolerance("acoustic_spl", 1.0, actual)
        self.assertTrue(res["within_tolerance"])

    def test_result_dict_has_all_keys(self):
        res = check_input_tolerance("temperature", 20.0, 20.0)
        for key in ("input_type", "nominal", "actual", "deviation",
                    "band", "within_tolerance", "finding"):
            self.assertIn(key, res)

    def test_unrecognized_type_raises(self):
        with self.assertRaises(ValueError):
            check_input_tolerance("cosmic_ray_flux", 1.0, 1.0)

    def test_finding_contains_input_type_name(self):
        res = check_input_tolerance("temperature", 20.0, 25.0)
        self.assertIn("temperature", res["finding"])

    def test_deviation_stored_in_result(self):
        res = check_input_tolerance("temperature", 20.0, 21.0)
        self.assertAlmostEqual(res["deviation"], 1.0)


class TestCheckAllInputs(unittest.TestCase):
    def test_all_compliant_returns_true(self):
        inputs = [
            {"input_type": "temperature", "nominal": 20.0, "actual": 21.0},
            {"input_type": "voltage", "nominal": 28.0, "actual": 28.2},
        ]
        result = check_all_inputs(inputs)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["results"]), 2)

    def test_single_exceedance_flags_not_compliant(self):
        inputs = [
            {"input_type": "temperature", "nominal": 20.0, "actual": 25.0},
            {"input_type": "voltage", "nominal": 28.0, "actual": 28.2},
        ]
        result = check_all_inputs(inputs)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_multiple_exceedances_all_reported(self):
        inputs = [
            {"input_type": "temperature", "nominal": 20.0, "actual": 25.0},
            {"input_type": "pressure", "nominal": 100.0, "actual": 105.0},
        ]
        result = check_all_inputs(inputs)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_actual_key_raises(self):
        inputs = [{"input_type": "temperature", "nominal": 20.0}]
        with self.assertRaises(ValueError):
            check_all_inputs(inputs)

    def test_missing_input_type_key_raises(self):
        inputs = [{"nominal": 20.0, "actual": 21.0}]
        with self.assertRaises(ValueError):
            check_all_inputs(inputs)

    def test_empty_input_list_is_compliant(self):
        result = check_all_inputs([])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["results"], [])

    def test_result_count_matches_input_count(self):
        inputs = [
            {"input_type": "temperature", "nominal": 20.0, "actual": 21.0},
            {"input_type": "humidity", "nominal": 50.0, "actual": 50.0},
            {"input_type": "frequency", "nominal": 1000.0, "actual": 1001.0},
        ]
        result = check_all_inputs(inputs)
        self.assertEqual(len(result["results"]), 3)

    def test_unrecognized_type_in_batch_raises(self):
        inputs = [{"input_type": "dark_matter", "nominal": 1.0, "actual": 1.0}]
        with self.assertRaises(ValueError):
            check_all_inputs(inputs)


if __name__ == "__main__":
    unittest.main()
