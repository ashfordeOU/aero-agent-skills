"""
test_e1003_test_data.py

Offline deterministic unittest suite for e1003_test_data_logic.py.
Run: python3 test_e1003_test_data.py
Expected output: OK
"""

import sys
import os
import unittest

# Allow running from any working directory.
sys.path.insert(0, os.path.dirname(__file__))

from e1003_test_data_logic import (
    validate_sampling_rate,
    compute_storage_bytes,
    reduce_to_engineering_units,
    check_record_completeness,
    validate_delivery_package,
    categorize_data_channel,
    determine_retention_period_days,
    detect_data_gap,
    validate_data_format,
    compute_channel_data_rate_bps,
    MINIMUM_SAMPLING_RATES_HZ,
    REQUIRED_RECORD_FIELDS,
    REQUIRED_DELIVERY_FIELDS,
)


class TestValidateSamplingRate(unittest.TestCase):

    def test_vibration_at_minimum_passes(self):
        ok, msg = validate_sampling_rate("vibration", 2000.0)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_vibration_above_minimum_passes(self):
        ok, msg = validate_sampling_rate("vibration", 5000.0)
        self.assertTrue(ok)

    def test_vibration_below_minimum_fails(self):
        ok, msg = validate_sampling_rate("vibration", 500.0)
        self.assertFalse(ok)
        self.assertIn("500", msg)

    def test_thermal_at_minimum_passes(self):
        ok, msg = validate_sampling_rate("thermal", 1.0)
        self.assertTrue(ok)

    def test_acoustic_below_minimum_fails(self):
        ok, _ = validate_sampling_rate("acoustic", 9999.0)
        self.assertFalse(ok)

    def test_unknown_channel_type_raises(self):
        with self.assertRaises(ValueError):
            validate_sampling_rate("nuclear", 100.0)

    def test_electrical_exact_minimum_passes(self):
        ok, _ = validate_sampling_rate("electrical", 100.0)
        self.assertTrue(ok)


class TestComputeStorageBytes(unittest.TestCase):

    def test_single_channel_basic(self):
        # 1 channel × 10 s × 100 Hz × 16 bits = 16000 bits = 2000 bytes
        result = compute_storage_bytes(1, 10.0, 100.0, 16)
        self.assertEqual(result, 2000)

    def test_multiple_channels(self):
        # 4 channels × 1 s × 1000 Hz × 32 bits = 128000 bits = 16000 bytes
        result = compute_storage_bytes(4, 1.0, 1000.0, 32)
        self.assertEqual(result, 16000)

    def test_non_positive_channels_raises(self):
        with self.assertRaises(ValueError):
            compute_storage_bytes(0, 10.0, 100.0, 16)

    def test_non_positive_duration_raises(self):
        with self.assertRaises(ValueError):
            compute_storage_bytes(1, -5.0, 100.0, 16)

    def test_result_rounds_up(self):
        # 1 channel × 1 s × 1 Hz × 1 bit = 1 bit → 1 byte (ceil)
        result = compute_storage_bytes(1, 1.0, 1.0, 1)
        self.assertEqual(result, 1)


class TestReduceToEngineeringUnits(unittest.TestCase):

    def test_linear_calibration(self):
        # slope=0.1, offset=10.0, raw=100 → 0.1*100 + 10.0 = 20.0
        result = reduce_to_engineering_units(100.0, 0.1, 10.0)
        self.assertAlmostEqual(result, 20.0)

    def test_identity_calibration(self):
        result = reduce_to_engineering_units(42.0, 1.0, 0.0)
        self.assertAlmostEqual(result, 42.0)

    def test_negative_offset(self):
        result = reduce_to_engineering_units(50.0, 2.0, -5.0)
        self.assertAlmostEqual(result, 95.0)

    def test_zero_slope_raises(self):
        with self.assertRaises(ValueError):
            reduce_to_engineering_units(10.0, 0.0, 5.0)


class TestCheckRecordCompleteness(unittest.TestCase):

    def _complete_record(self):
        return {
            "test_id": "T001",
            "channel_id": "CH01",
            "sampling_rate_hz": 1000.0,
            "unit": "m/s^2",
            "calibration_slope": 0.01,
            "calibration_offset": 0.0,
            "timestamp_utc": "2026-09-11T12:00:00Z",
            "format": "ieee754_float32",
        }

    def test_complete_record_returns_empty(self):
        missing = check_record_completeness(self._complete_record())
        self.assertEqual(missing, [])

    def test_missing_test_id_flagged(self):
        record = self._complete_record()
        del record["test_id"]
        missing = check_record_completeness(record)
        self.assertIn("test_id", missing)

    def test_none_value_treated_as_missing(self):
        record = self._complete_record()
        record["unit"] = None
        missing = check_record_completeness(record)
        self.assertIn("unit", missing)

    def test_empty_string_treated_as_missing(self):
        record = self._complete_record()
        record["format"] = ""
        missing = check_record_completeness(record)
        self.assertIn("format", missing)

    def test_multiple_missing_fields_all_reported(self):
        missing = check_record_completeness({})
        self.assertEqual(sorted(missing), sorted(REQUIRED_RECORD_FIELDS))


class TestValidateDeliveryPackage(unittest.TestCase):

    def _complete_package(self):
        return {
            "test_id": "T001",
            "test_title": "Vibration Survey",
            "date_utc": "2026-09-11",
            "facility": "ESTEC-TV",
            "operator": "J. Smith",
            "channels": ["CH01", "CH02"],
            "data_file": "T001_data.bin",
            "calibration_file": "T001_cal.csv",
            "format": "binary",
        }

    def test_complete_package_returns_empty(self):
        missing = validate_delivery_package(self._complete_package())
        self.assertEqual(missing, [])

    def test_missing_calibration_file_flagged(self):
        pkg = self._complete_package()
        del pkg["calibration_file"]
        missing = validate_delivery_package(pkg)
        self.assertIn("calibration_file", missing)

    def test_empty_package_reports_all_missing(self):
        missing = validate_delivery_package({})
        self.assertEqual(sorted(missing), sorted(REQUIRED_DELIVERY_FIELDS))


class TestCategorizeDataChannel(unittest.TestCase):

    def test_vibration_is_primary(self):
        self.assertEqual(categorize_data_channel("vibration"), "primary")

    def test_acoustic_is_primary(self):
        self.assertEqual(categorize_data_channel("acoustic"), "primary")

    def test_strain_is_primary(self):
        self.assertEqual(categorize_data_channel("strain"), "primary")

    def test_pressure_is_secondary(self):
        self.assertEqual(categorize_data_channel("pressure"), "secondary")

    def test_electrical_is_secondary(self):
        self.assertEqual(categorize_data_channel("electrical"), "secondary")

    def test_thermal_is_housekeeping(self):
        self.assertEqual(categorize_data_channel("thermal"), "housekeeping")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_data_channel("neutrino_flux")


class TestDetermineRetentionPeriod(unittest.TestCase):

    def test_qualification_retention(self):
        self.assertEqual(determine_retention_period_days("qualification"), 3650)

    def test_development_retention(self):
        self.assertEqual(determine_retention_period_days("development"), 365)

    def test_acceptance_retention(self):
        self.assertEqual(determine_retention_period_days("acceptance"), 3650)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            determine_retention_period_days("experimental")


class TestDetectDataGap(unittest.TestCase):

    def test_no_gap_in_uniform_sequence(self):
        ts = [0.0, 0.001, 0.002, 0.003, 0.004]
        gaps = detect_data_gap(ts, max_gap_s=0.0015)
        self.assertEqual(gaps, [])

    def test_single_gap_detected(self):
        ts = [0.0, 0.001, 0.005, 0.006]  # gap between index 1 and 2
        gaps = detect_data_gap(ts, max_gap_s=0.0015)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 0.001)
        self.assertAlmostEqual(gaps[0][1], 0.005)

    def test_non_increasing_timestamps_raises(self):
        with self.assertRaises(ValueError):
            detect_data_gap([0.0, 0.002, 0.001], max_gap_s=0.005)

    def test_non_positive_max_gap_raises(self):
        with self.assertRaises(ValueError):
            detect_data_gap([0.0, 0.001], max_gap_s=0.0)

    def test_empty_sequence_returns_empty(self):
        gaps = detect_data_gap([], max_gap_s=0.01)
        self.assertEqual(gaps, [])


class TestValidateDataFormat(unittest.TestCase):

    def test_binary_is_valid(self):
        self.assertTrue(validate_data_format("binary"))

    def test_csv_is_valid(self):
        self.assertTrue(validate_data_format("csv"))

    def test_hdf5_is_valid(self):
        self.assertTrue(validate_data_format("hdf5"))

    def test_xml_is_not_valid(self):
        self.assertFalse(validate_data_format("xml"))

    def test_empty_string_is_not_valid(self):
        self.assertFalse(validate_data_format(""))


class TestComputeChannelDataRate(unittest.TestCase):

    def test_1000hz_32bit(self):
        self.assertAlmostEqual(compute_channel_data_rate_bps(1000.0, 32), 32000.0)

    def test_zero_rate_raises(self):
        with self.assertRaises(ValueError):
            compute_channel_data_rate_bps(0.0, 16)

    def test_zero_bits_raises(self):
        with self.assertRaises(ValueError):
            compute_channel_data_rate_bps(100.0, 0)


if __name__ == "__main__":
    unittest.main()
