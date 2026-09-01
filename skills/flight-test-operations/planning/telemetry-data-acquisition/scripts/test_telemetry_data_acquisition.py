#!/usr/bin/env python3
"""Gate 3 contract test: telemetry-data-acquisition.

Exercises scripts/telemetry_data_acquisition_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 -
pcm_frame_size returns words_per_frame * bits_per_word;
pcm_bit_rate returns frame_rate * words_per_frame * bits_per_word;
supercommutated_instances returns the integer channel to frame rate
ratio > 1; subcommutated_instances returns the integer frame to
channel rate ratio > 1; irig_b_time_of_year returns
(day_of_year - 1) * 86400 + seconds_of_day; conditioning_verdict
returns ok when gain * sensor_span <= adc_range; total_latency sums
the three delays; latency_ok checks total <= requirement;
latency_buffer_samples returns ceil(latency * sample_rate);
ground_link_ok checks received - sensitivity >= min margin;
telemetry_quality_ok checks ber <= limit and dropout <= limit.
All expected values are hand-computed analytic results:

  - pcm_frame_size(64, 16): 64 * 16 = 1024 bits.
  - pcm_bit_rate(50, 64, 16): 50 * 64 * 16 = 51200.0 bit/s.
  - supercommutated_instances(200, 50): 200 / 50 = 4 per frame.
  - subcommutated_instances(100, 25): 100 / 25 = 4 frames per sample.
  - irig_b_time_of_year(32, 43200.0): 31 * 86400 + 43200 =
    2721600.0 s.
  - total_latency(5.0, 10.0, 25.0): 40.0 ms.
  - latency_buffer_samples(0.05, 200): ceil(10.0) = 10 samples.
  - ground_link_ok(-95.0, -110.0, 10.0): margin 15.0 >= 10.0, True.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import telemetry_data_acquisition_logic as tda  # noqa: E402


class PcmFrameSizeTest(unittest.TestCase):
    def test_analytic_64_words_16_bits(self):
        # 64 words of 16 bits: 64 * 16 = 1024 bits per minor frame.
        self.assertEqual(tda.pcm_frame_size(64, 16), 1024)

    def test_analytic_32_words_10_bits(self):
        # 32 words of 10 bits: 32 * 10 = 320 bits per minor frame.
        self.assertEqual(tda.pcm_frame_size(32, 10), 320)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.pcm_frame_size(0, 16)  # zero words
        with self.assertRaises(ValueError):
            tda.pcm_frame_size(64, 0)  # zero bits per word
        with self.assertRaises(ValueError):
            tda.pcm_frame_size(64.0, 16)  # non-int words
        with self.assertRaises(ValueError):
            tda.pcm_frame_size(True, 16)  # bool words
        with self.assertRaises(ValueError):
            tda.pcm_frame_size(64, "16")  # non-int bits per word


class PcmBitRateTest(unittest.TestCase):
    def test_analytic_50_fps_64_words(self):
        # 50 frames/s of 64 x 16 bit words: 50 * 64 * 16 = 51200.0
        # bit/s.
        self.assertEqual(tda.pcm_bit_rate(50, 64, 16), 51200.0)

    def test_analytic_100_fps_16_words(self):
        # 100 frames/s of 16 x 8 bit words: 100 * 16 * 8 = 12800.0
        # bit/s.
        self.assertEqual(tda.pcm_bit_rate(100, 16, 8), 12800.0)

    def test_analytic_200_fps_128_words(self):
        # 200 frames/s of 128 x 16 bit words: 200 * 128 * 16 =
        # 409600.0 bit/s.
        self.assertEqual(tda.pcm_bit_rate(200, 128, 16), 409600.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.pcm_bit_rate(0, 64, 16)  # zero frame rate
        with self.assertRaises(ValueError):
            tda.pcm_bit_rate(-5.0, 64, 16)  # negative frame rate
        with self.assertRaises(ValueError):
            tda.pcm_bit_rate(50, 0, 16)  # zero words
        with self.assertRaises(ValueError):
            tda.pcm_bit_rate(50, 64.0, 16)  # non-int words
        with self.assertRaises(ValueError):
            tda.pcm_bit_rate(50, 64, 0)  # zero bits per word
        with self.assertRaises(ValueError):
            tda.pcm_bit_rate(True, 64, 16)  # bool frame rate
        with self.assertRaises(ValueError):
            tda.pcm_bit_rate(50, 64, True)  # bool bits per word


class SupercommutatedInstancesTest(unittest.TestCase):
    def test_analytic_200hz_on_50fps(self):
        # A 200 Hz channel on a 50 frame/s stream: 200 / 50 = 4
        # appearances per frame.
        self.assertEqual(tda.supercommutated_instances(200, 50), 4)

    def test_analytic_500hz_on_100fps(self):
        # A 500 Hz channel on a 100 frame/s stream: 500 / 100 = 5
        # appearances per frame.
        self.assertEqual(tda.supercommutated_instances(500, 100), 5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.supercommutated_instances(0, 50)  # zero channel rate
        with self.assertRaises(ValueError):
            tda.supercommutated_instances(200, 0)  # zero frame rate
        with self.assertRaises(ValueError):
            tda.supercommutated_instances(50, 50)  # ratio 1, not super
        with self.assertRaises(ValueError):
            tda.supercommutated_instances(30, 50)  # ratio below 1
        with self.assertRaises(ValueError):
            tda.supercommutated_instances(225, 50)  # ratio 4.5, not int
        with self.assertRaises(ValueError):
            tda.supercommutated_instances("200", 50)  # non-numeric
        with self.assertRaises(ValueError):
            tda.supercommutated_instances(200, True)  # bool frame rate


class SubcommutatedInstancesTest(unittest.TestCase):
    def test_analytic_25hz_on_100fps(self):
        # A 25 Hz channel on a 100 frame/s stream: 100 / 25 = 4 frames
        # per sample.
        self.assertEqual(tda.subcommutated_instances(100, 25), 4)

    def test_analytic_20hz_on_100fps(self):
        # A 20 Hz channel on a 100 frame/s stream: 100 / 20 = 5 frames
        # per sample.
        self.assertEqual(tda.subcommutated_instances(100, 20), 5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.subcommutated_instances(0, 25)  # zero frame rate
        with self.assertRaises(ValueError):
            tda.subcommutated_instances(100, 0)  # zero channel rate
        with self.assertRaises(ValueError):
            tda.subcommutated_instances(25, 25)  # ratio 1, not sub
        with self.assertRaises(ValueError):
            tda.subcommutated_instances(50, 100)  # channel above frame
        with self.assertRaises(ValueError):
            tda.subcommutated_instances(100, 30)  # ratio 3.33, not int
        with self.assertRaises(ValueError):
            tda.subcommutated_instances(100, "25")  # non-numeric
        with self.assertRaises(ValueError):
            tda.subcommutated_instances(True, 25)  # bool frame rate


class IrigBTimeOfYearTest(unittest.TestCase):
    def test_analytic_day_one_midnight(self):
        # Day 1 at 0 s: (1 - 1) * 86400 + 0 = 0.0 s of year.
        self.assertEqual(tda.irig_b_time_of_year(1, 0), 0.0)

    def test_analytic_day_32_noon(self):
        # Day 32 at 43200 s: 31 * 86400 + 43200 = 2678400 + 43200 =
        # 2721600.0 s of year.
        self.assertEqual(tda.irig_b_time_of_year(32, 43200.0), 2721600.0)

    def test_analytic_leap_day(self):
        # Day 366 at 0 s: 365 * 86400 = 31536000.0 s of year.
        self.assertEqual(tda.irig_b_time_of_year(366, 0), 31536000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.irig_b_time_of_year(0, 0)  # day zero
        with self.assertRaises(ValueError):
            tda.irig_b_time_of_year(367, 0)  # day beyond 366
        with self.assertRaises(ValueError):
            tda.irig_b_time_of_year(32.0, 0)  # non-int day
        with self.assertRaises(ValueError):
            tda.irig_b_time_of_year(True, 0)  # bool day
        with self.assertRaises(ValueError):
            tda.irig_b_time_of_year(32, -1.0)  # negative seconds
        with self.assertRaises(ValueError):
            tda.irig_b_time_of_year(32, 86400.0)  # seconds out of day
        with self.assertRaises(ValueError):
            tda.irig_b_time_of_year(32, "43200")  # non-numeric seconds


class ConditioningVerdictTest(unittest.TestCase):
    def test_analytic_fits_adc(self):
        # 5.0 V span at gain 2.0 gives 10.0 V, exactly the 10.0 V ADC
        # full scale: ok.
        self.assertEqual(tda.conditioning_verdict(5.0, 2.0, 10.0), "ok")

    def test_analytic_inside_adc(self):
        # 4.0 V span at gain 2.0 gives 8.0 V on a 10.0 V ADC: ok.
        self.assertEqual(tda.conditioning_verdict(4.0, 2.0, 10.0), "ok")

    def test_analytic_over_range(self):
        # 6.0 V span at gain 2.0 gives 12.0 V on a 10.0 V ADC: the
        # amplifier clips before the converter.
        self.assertEqual(tda.conditioning_verdict(6.0, 2.0, 10.0), "over-range")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.conditioning_verdict(0, 2.0, 10.0)  # zero span
        with self.assertRaises(ValueError):
            tda.conditioning_verdict(5.0, 0, 10.0)  # zero gain
        with self.assertRaises(ValueError):
            tda.conditioning_verdict(5.0, 2.0, -1.0)  # negative adc range
        with self.assertRaises(ValueError):
            tda.conditioning_verdict("5.0", 2.0, 10.0)  # non-numeric span
        with self.assertRaises(ValueError):
            tda.conditioning_verdict(5.0, True, 10.0)  # bool gain


class TotalLatencyTest(unittest.TestCase):
    def test_analytic_sum(self):
        # 5 ms + 10 ms + 25 ms = 40.0 ms end to end.
        self.assertEqual(tda.total_latency(5.0, 10.0, 25.0), 40.0)

    def test_analytic_integer_inputs(self):
        # 8 ms + 12 ms + 30 ms = 50.0 ms end to end.
        self.assertEqual(tda.total_latency(8, 12, 30), 50.0)

    def test_analytic_zero_delay(self):
        # A direct recording with no link: 2 ms + 1 ms + 0 ms = 3.0 ms.
        self.assertEqual(tda.total_latency(2.0, 1.0, 0), 3.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.total_latency(-1.0, 10.0, 25.0)  # negative acquisition
        with self.assertRaises(ValueError):
            tda.total_latency(5.0, -1.0, 25.0)  # negative processing
        with self.assertRaises(ValueError):
            tda.total_latency(5.0, 10.0, -1.0)  # negative link
        with self.assertRaises(ValueError):
            tda.total_latency("5.0", 10.0, 25.0)  # non-numeric
        with self.assertRaises(ValueError):
            tda.total_latency(5.0, True, 25.0)  # bool delay


class LatencyOkTest(unittest.TestCase):
    def test_analytic_within_requirement(self):
        # 40.0 ms against a 50.0 ms requirement: within, True.
        self.assertTrue(tda.latency_ok(40.0, 50.0))

    def test_analytic_at_requirement(self):
        # Exactly at the requirement: 50.0 <= 50.0, True.
        self.assertTrue(tda.latency_ok(50.0, 50.0))

    def test_analytic_exceeds_requirement(self):
        # 40.0 ms against a 30.0 ms requirement: over, False.
        self.assertFalse(tda.latency_ok(40.0, 30.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.latency_ok(-1.0, 50.0)  # negative total
        with self.assertRaises(ValueError):
            tda.latency_ok(40.0, 0)  # zero requirement
        with self.assertRaises(ValueError):
            tda.latency_ok(40.0, -5.0)  # negative requirement
        with self.assertRaises(ValueError):
            tda.latency_ok("40.0", 50.0)  # non-numeric total
        with self.assertRaises(ValueError):
            tda.latency_ok(40.0, True)  # bool requirement


class LatencyBufferSamplesTest(unittest.TestCase):
    def test_analytic_exact_samples(self):
        # 0.05 s at 200 samples/s: ceil(10.0) = 10 samples.
        self.assertEqual(tda.latency_buffer_samples(0.05, 200), 10)

    def test_analytic_partial_sample_rounds_up(self):
        # 0.031 s at 200 samples/s: ceil(6.2) = 7 samples.
        self.assertEqual(tda.latency_buffer_samples(0.031, 200), 7)

    def test_analytic_zero_latency(self):
        # No latency: ceil(0.0) = 0 samples buffered.
        self.assertEqual(tda.latency_buffer_samples(0.0, 200), 0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.latency_buffer_samples(-0.1, 200)  # negative latency
        with self.assertRaises(ValueError):
            tda.latency_buffer_samples(0.05, 0)  # zero sample rate
        with self.assertRaises(ValueError):
            tda.latency_buffer_samples(0.05, -10.0)  # negative rate
        with self.assertRaises(ValueError):
            tda.latency_buffer_samples("0.05", 200)  # non-numeric
        with self.assertRaises(ValueError):
            tda.latency_buffer_samples(0.05, True)  # bool sample rate


class GroundLinkOkTest(unittest.TestCase):
    def test_analytic_margin_meets_minimum(self):
        # -95.0 dBm received at -110.0 dBm sensitivity: margin 15.0 dB
        # against a 10.0 dB minimum, True.
        self.assertTrue(tda.ground_link_ok(-95.0, -110.0, 10.0))

    def test_analytic_margin_below_minimum(self):
        # -103.0 dBm received at -110.0 dBm sensitivity: margin 7.0 dB
        # against a 10.0 dB minimum, False.
        self.assertFalse(tda.ground_link_ok(-103.0, -110.0, 10.0))

    def test_analytic_exact_margin(self):
        # Margin exactly at the minimum: 10.0 >= 10.0, True.
        self.assertTrue(tda.ground_link_ok(-100.0, -110.0, 10.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.ground_link_ok(-95.0, -110.0, 0)  # zero minimum margin
        with self.assertRaises(ValueError):
            tda.ground_link_ok(-95.0, -110.0, -1.0)  # negative minimum
        with self.assertRaises(ValueError):
            tda.ground_link_ok("95.0", -110.0, 10.0)  # non-numeric power
        with self.assertRaises(ValueError):
            tda.ground_link_ok(-95.0, None, 10.0)  # None sensitivity
        with self.assertRaises(ValueError):
            tda.ground_link_ok(-95.0, -110.0, True)  # bool minimum


class TelemetryQualityOkTest(unittest.TestCase):
    def test_analytic_both_pass(self):
        # 1e-5 errors per bit and 0.5 % dropouts against limits of 1e-4
        # and 1.0: both pass, True.
        self.assertTrue(tda.telemetry_quality_ok(1e-5, 0.5, 1e-4, 1.0))

    def test_analytic_ber_fails(self):
        # 2e-4 errors per bit against a 1e-4 limit: fails, False.
        self.assertFalse(tda.telemetry_quality_ok(2e-4, 0.5, 1e-4, 1.0))

    def test_analytic_dropout_fails(self):
        # 2.0 % dropouts against a 1.0 % limit: fails, False.
        self.assertFalse(tda.telemetry_quality_ok(1e-5, 2.0, 1e-4, 1.0))

    def test_analytic_at_limits(self):
        # Exactly at both limits: 1e-4 <= 1e-4 and 1.0 <= 1.0, True.
        self.assertTrue(tda.telemetry_quality_ok(1e-4, 1.0, 1e-4, 1.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(-1e-5, 0.5, 1e-4, 1.0)  # negative ber
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(1.5, 0.5, 1e-4, 1.0)  # ber above 1
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(1e-5, -0.5, 1e-4, 1.0)  # negative dropout
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(1e-5, 101.0, 1e-4, 1.0)  # dropout above 100
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(1e-5, 0.5, 0, 1.0)  # zero ber limit
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(1e-5, 0.5, 2.0, 1.0)  # ber limit above 1
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(1e-5, 0.5, 1e-4, 0)  # zero dropout limit
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(1e-5, 0.5, 1e-4, 150.0)  # limit above 100
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok("1e-5", 0.5, 1e-4, 1.0)  # non-numeric ber
        with self.assertRaises(ValueError):
            tda.telemetry_quality_ok(1e-5, True, 1e-4, 1.0)  # bool dropout


class TelemetryScenarioTest(unittest.TestCase):
    def test_analytic_chain_release_scenario(self):
        # Full contract scenario: a 200 Hz vibration channel on a 50
        # frame/s stream of 64 x 16 bit words (1024 bit frame,
        # 51200 bit/s), 4 supercommutated instances, IRIG day 32 at
        # 43200 s, a 5.0 V bridge at gain 2.0 on a 10.0 V ADC,
        # 40.0 ms latency against a 50.0 ms requirement, 15.0 dB of
        # link margin, and a quality pass at 1e-5 errors per bit and
        # 0.5 % dropouts. Hand-computed: frame 1024, rate 51200.0,
        # instances 4, time 2721600.0 s, latency 40.0 ms, buffer 10.
        self.assertEqual(tda.pcm_frame_size(64, 16), 1024)
        self.assertEqual(tda.pcm_bit_rate(50, 64, 16), 51200.0)
        self.assertEqual(tda.supercommutated_instances(200, 50), 4)
        self.assertEqual(tda.irig_b_time_of_year(32, 43200.0), 2721600.0)
        self.assertEqual(tda.conditioning_verdict(5.0, 2.0, 10.0), "ok")
        self.assertEqual(tda.total_latency(5.0, 10.0, 25.0), 40.0)
        self.assertTrue(tda.latency_ok(40.0, 50.0))
        self.assertEqual(tda.latency_buffer_samples(0.05, 200), 10)
        self.assertTrue(tda.ground_link_ok(-95.0, -110.0, 10.0))
        self.assertTrue(tda.telemetry_quality_ok(1e-5, 0.5, 1e-4, 1.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
