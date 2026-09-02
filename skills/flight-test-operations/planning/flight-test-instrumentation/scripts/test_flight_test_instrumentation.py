#!/usr/bin/env python3
"""Gate 3 contract test: flight-test-instrumentation.

Exercises scripts/flight_test_instrumentation_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 -
nyquist_ok checks fs >= 2*fmax; sensor_range_verdict checks
|value| <= range; quantization_error returns the ADC step
range / 2**bits; required_sample_rate returns margin * 2 * fmax;
calibration_verdict returns calibrated and not due. All expected
values are hand-computed analytic results:

  - nyquist_ok(1000, 400): 1000 >= 800, True.
  - nyquist_ok(799, 400): 799 < 800, False.
  - quantization_error(12, 5.0): 5.0 / 4096 = 0.001220703125 V.
  - quantization_error(16, 10.0): 10.0 / 65536 = 0.000152587890625 V.
  - quantization_error(8, 5.0): 5.0 / 256 = 0.01953125 V.
  - required_sample_rate(100): 2.5 * 2 * 100 = 500.0 Hz.
  - required_sample_rate(120, 2.5): 2.5 * 2 * 120 = 600.0 Hz.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flight_test_instrumentation_logic as fti  # noqa: E402


class NyquistOkTest(unittest.TestCase):
    def test_analytic_above_nyquist(self):
        # 1000 Hz sampling of a 400 Hz signal: 1000 >= 2*400 = 800,
        # so the rate is adequate.
        self.assertTrue(fti.nyquist_ok(1000, 400))

    def test_analytic_below_nyquist(self):
        # 799 Hz sampling of a 400 Hz signal: 799 < 800, so the rate
        # aliases the signal.
        self.assertFalse(fti.nyquist_ok(799, 400))

    def test_analytic_exactly_nyquist(self):
        # 800 Hz sampling of a 400 Hz signal: 800 >= 800, the lower
        # bound is inclusive.
        self.assertTrue(fti.nyquist_ok(800, 400))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fti.nyquist_ok(0, 400)  # zero sample rate
        with self.assertRaises(ValueError):
            fti.nyquist_ok(1000, 0)  # zero max frequency
        with self.assertRaises(ValueError):
            fti.nyquist_ok(1000, -5)  # negative max frequency
        with self.assertRaises(ValueError):
            fti.nyquist_ok("1000", 400)  # non-numeric rate
        with self.assertRaises(ValueError):
            fti.nyquist_ok(True, 400)  # bool rate
        with self.assertRaises(ValueError):
            fti.nyquist_ok(1000, None)  # None max frequency


class SensorRangeVerdictTest(unittest.TestCase):
    def test_analytic_inside_range(self):
        # 5.0 g on a 10 g sensor: |5.0| <= 10, ok.
        self.assertEqual(fti.sensor_range_verdict(5.0, 10.0), "ok")

    def test_analytic_negative_inside_range(self):
        # -7.5 N on a 10 N sensor: | -7.5 | <= 10, ok.
        self.assertEqual(fti.sensor_range_verdict(-7.5, 10.0), "ok")

    def test_analytic_edge_is_ok(self):
        # Exactly at the full scale: | -10.0 | <= 10.0, ok.
        self.assertEqual(fti.sensor_range_verdict(-10.0, 10.0), "ok")

    def test_analytic_positive_over_range(self):
        # 10.5 g on a 10 g sensor: over-range and clipped.
        self.assertEqual(fti.sensor_range_verdict(10.5, 10.0), "over-range")

    def test_analytic_negative_over_range(self):
        # -12.0 N on a 10 N sensor: over-range on the negative side.
        self.assertEqual(fti.sensor_range_verdict(-12.0, 10.0), "over-range")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fti.sensor_range_verdict(5.0, 0)  # zero range
        with self.assertRaises(ValueError):
            fti.sensor_range_verdict(5.0, -3.0)  # negative range
        with self.assertRaises(ValueError):
            fti.sensor_range_verdict("5.0", 10.0)  # non-numeric value
        with self.assertRaises(ValueError):
            fti.sensor_range_verdict(5.0, True)  # bool range


class QuantizationErrorTest(unittest.TestCase):
    def test_analytic_12_bit_5v(self):
        # 12 bits over 5.0 V: 5.0 / 4096 = 0.001220703125 V per LSB
        # (1.22 mV), so a 12-bit channel resolves about 1.2 mV.
        self.assertEqual(fti.quantization_error(12, 5.0), 0.001220703125)

    def test_analytic_16_bit_10v(self):
        # 16 bits over 10.0 V: 10.0 / 65536 = 0.000152587890625 V.
        self.assertEqual(fti.quantization_error(16, 10.0), 0.000152587890625)

    def test_analytic_8_bit_5v(self):
        # 8 bits over 5.0 V: 5.0 / 256 = 0.01953125 V.
        self.assertEqual(fti.quantization_error(8, 5.0), 0.01953125)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fti.quantization_error(0, 5.0)  # zero bits
        with self.assertRaises(ValueError):
            fti.quantization_error(12.5, 5.0)  # non-int bits
        with self.assertRaises(ValueError):
            fti.quantization_error(True, 5.0)  # bool bits
        with self.assertRaises(ValueError):
            fti.quantization_error(12, 0)  # zero range
        with self.assertRaises(ValueError):
            fti.quantization_error(12, -1.0)  # negative range


class RequiredSampleRateTest(unittest.TestCase):
    def test_analytic_default_margin(self):
        # 100 Hz signal at the default margin 2.5:
        # 2.5 * 2 * 100 = 500.0 Hz.
        self.assertEqual(fti.required_sample_rate(100), 500.0)

    def test_analytic_custom_margin(self):
        # 120 Hz signal at margin 2.5: 2.5 * 2 * 120 = 600.0 Hz.
        self.assertEqual(fti.required_sample_rate(120, 2.5), 600.0)

    def test_analytic_margin_three(self):
        # 100 Hz signal at margin 3.0: 3.0 * 2 * 100 = 600.0 Hz.
        self.assertEqual(fti.required_sample_rate(100, 3.0), 600.0)

    def test_analytic_margin_one_is_nyquist(self):
        # Margin 1.0 gives exactly the Nyquist rate: 1.0 * 2 * 50 =
        # 100.0 Hz for a 50 Hz signal, and nyquist_ok accepts it.
        self.assertEqual(fti.required_sample_rate(50, 1.0), 100.0)
        self.assertTrue(fti.nyquist_ok(fti.required_sample_rate(50, 1.0), 50))

    def test_analytic_rate_passes_nyquist(self):
        # The default required rate for a 400 Hz signal is 2000.0 Hz,
        # well above the 800 Hz Nyquist bound.
        self.assertEqual(fti.required_sample_rate(400), 2000.0)
        self.assertTrue(fti.nyquist_ok(fti.required_sample_rate(400), 400))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fti.required_sample_rate(0)  # zero max frequency
        with self.assertRaises(ValueError):
            fti.required_sample_rate(-5.0)  # negative max frequency
        with self.assertRaises(ValueError):
            fti.required_sample_rate(100, 0)  # zero margin
        with self.assertRaises(ValueError):
            fti.required_sample_rate(100, -1.0)  # negative margin
        with self.assertRaises(ValueError):
            fti.required_sample_rate("100")  # non-numeric max frequency
        with self.assertRaises(ValueError):
            fti.required_sample_rate(100, True)  # bool margin


class CalibrationVerdictTest(unittest.TestCase):
    def test_analytic_calibrated_and_current(self):
        # Calibrated and not due: the channel may fly.
        self.assertTrue(fti.calibration_verdict(True, False))

    def test_analytic_not_calibrated(self):
        # Not calibrated, even when nothing is due: unusable.
        self.assertFalse(fti.calibration_verdict(False, False))

    def test_analytic_calibration_due(self):
        # Calibrated but recalibration is due: unusable.
        self.assertFalse(fti.calibration_verdict(True, True))

    def test_analytic_not_calibrated_and_due(self):
        self.assertFalse(fti.calibration_verdict(False, True))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fti.calibration_verdict("yes", False)  # non-bool calibrated
        with self.assertRaises(ValueError):
            fti.calibration_verdict(True, 1)  # int not a bool
        with self.assertRaises(ValueError):
            fti.calibration_verdict(None, False)  # None not a bool


class InstrumentationScenarioTest(unittest.TestCase):
    def test_analytic_channel_release_scenario(self):
        # Full contract scenario: a 120 Hz strain channel on a 200 N
        # bridge sensor, 16-bit ADC over 10.0 V, calibrated and not
        # due. Hand-computed: required rate 600.0 Hz, resolution
        # 0.000152587890625 V, range verdict ok for 150 N.
        rate = fti.required_sample_rate(120)
        self.assertEqual(rate, 600.0)
        self.assertTrue(fti.nyquist_ok(rate, 120))
        self.assertFalse(fti.nyquist_ok(239, 120))
        self.assertEqual(fti.sensor_range_verdict(150.0, 200.0), "ok")
        self.assertEqual(fti.sensor_range_verdict(250.0, 200.0), "over-range")
        self.assertEqual(fti.quantization_error(16, 10.0), 0.000152587890625)
        self.assertTrue(fti.calibration_verdict(True, False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
