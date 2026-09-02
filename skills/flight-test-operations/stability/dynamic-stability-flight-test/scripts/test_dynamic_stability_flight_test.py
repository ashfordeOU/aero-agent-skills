#!/usr/bin/env python3
"""Contract tests for the dynamic stability flight test logic (gate 3).

Exercises every public function in dynamic_stability_flight_test_logic.py:
log decrement, damping ratio, frequencies, half and double amplitude
times, peak finding, mode identification, excitation selection, and
handling qualities verdicts. Stdlib unittest only, deterministic,
offline.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dynamic_stability_flight_test_logic as dst


class LogDecrementTest(unittest.TestCase):
    def test_known_value(self):
        # delta = (1/1) * ln(10/1) = ln(10)
        delta = dst.log_decrement(10.0, 1.0, 1)
        self.assertAlmostEqual(delta, math.log(10.0), places=6)

    def test_multi_cycle_average(self):
        # delta = (1/2) * ln(16/4) = 0.5 * ln(4)
        delta = dst.log_decrement(16.0, 4.0, 2)
        self.assertAlmostEqual(delta, 0.5 * math.log(4.0), places=6)

    def test_no_decay_raises(self):
        with self.assertRaises(ValueError):
            dst.log_decrement(10.0, 10.0, 1)

    def test_growing_raises(self):
        with self.assertRaises(ValueError):
            dst.log_decrement(10.0, 12.0, 1)

    def test_bad_cycles_raises(self):
        with self.assertRaises(ValueError):
            dst.log_decrement(10.0, 1.0, 0)


class DampingRatioTest(unittest.TestCase):
    def test_known_value(self):
        zeta = dst.damping_ratio_from_decrement(0.2)
        expected = 0.2 / math.sqrt(0.2 * 0.2 + 4 * math.pi * math.pi)
        self.assertAlmostEqual(zeta, expected, places=6)

    def test_small_delta_approximation(self):
        # For small delta, zeta ~= delta / (2 * pi)
        zeta = dst.damping_ratio_from_decrement(0.01)
        self.assertAlmostEqual(zeta, 0.01 / (2 * math.pi), places=4)

    def test_zero_decrement_zero_zeta(self):
        self.assertAlmostEqual(dst.damping_ratio_from_decrement(0.0), 0.0, places=9)

    def test_negative_delta_raises(self):
        with self.assertRaises(ValueError):
            dst.damping_ratio_from_decrement(-0.1)


class DampedFrequencyTest(unittest.TestCase):
    def test_one_second_period(self):
        result = dst.damped_frequency_from_period(1.0)
        self.assertAlmostEqual(result["damped_frequency_rad_s"], 2 * math.pi, places=6)
        self.assertAlmostEqual(result["damped_frequency_hz"], 1.0, places=6)

    def test_bad_period_raises(self):
        with self.assertRaises(ValueError):
            dst.damped_frequency_from_period(0.0)


class UndampedFrequencyTest(unittest.TestCase):
    def test_undamped_above_damped(self):
        wn = dst.undamped_natural_frequency(2 * math.pi, 0.3)
        self.assertGreater(wn, 2 * math.pi)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            dst.undamped_natural_frequency(0.0, 0.3)
        with self.assertRaises(ValueError):
            dst.undamped_natural_frequency(2 * math.pi, 1.0)


class TimeToHalfAmplitudeTest(unittest.TestCase):
    def test_known_value(self):
        t = dst.time_to_half_amplitude(0.3, 1.0)
        self.assertAlmostEqual(t, math.log(2.0) / 0.3, places=6)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            dst.time_to_half_amplitude(0.0, 1.0)
        with self.assertRaises(ValueError):
            dst.time_to_half_amplitude(0.3, 0.0)


class TimeToDoubleAmplitudeTest(unittest.TestCase):
    def test_known_value(self):
        t = dst.time_to_double_amplitude(-0.1, 1.0)
        self.assertAlmostEqual(t, math.log(2.0) / 0.1, places=6)

    def test_non_divergent_raises(self):
        with self.assertRaises(ValueError):
            dst.time_to_double_amplitude(0.0, 1.0)


class CyclesToHalfAmplitudeTest(unittest.TestCase):
    def test_known_value(self):
        n = dst.cycles_to_half_amplitude(0.1)
        self.assertAlmostEqual(n, math.log(2.0) / (2 * math.pi * 0.1), places=6)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            dst.cycles_to_half_amplitude(0.0)


class LocalMaximaTest(unittest.TestCase):
    def test_indices(self):
        self.assertEqual(dst.local_maxima([1.0, 3.0, 2.0, 5.0, 4.0]), [1, 3])

    def test_flat_peak_not_counted(self):
        # Strict local maxima only: a plateau has no interior point
        # strictly greater than both neighbors.
        self.assertEqual(dst.local_maxima([1.0, 3.0, 3.0, 2.0]), [])

    def test_short_sequence_empty(self):
        self.assertEqual(dst.local_maxima([1.0, 2.0]), [])

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            dst.local_maxima(5)


class ModeIdentificationTest(unittest.TestCase):
    def test_decaying_sequence(self):
        result = dst.mode_identification([10.0, 5.0, 2.5], [0.0, 2.0, 4.0])
        # cycles = 2, delta = 0.5 * ln(4), zeta from the decrement,
        # period = 2.0 s, w_d = pi rad/s.
        expected_delta = 0.5 * math.log(4.0)
        self.assertAlmostEqual(result["decrement"], expected_delta, places=6)
        self.assertAlmostEqual(result["period_s"], 2.0, places=6)
        self.assertAlmostEqual(result["damped_frequency_rad_s"], math.pi, places=6)
        self.assertAlmostEqual(result["damped_frequency_hz"], 0.5, places=6)
        self.assertIsNotNone(result["undamped_frequency_rad_s"])
        self.assertIsNotNone(result["time_to_half_s"])
        self.assertEqual(result["cycles_used"], 2)

    def test_insufficient_peaks_raises(self):
        with self.assertRaises(ValueError):
            dst.mode_identification([10.0], [0.0])

    def test_mismatched_lengths_raise(self):
        with self.assertRaises(ValueError):
            dst.mode_identification([10.0, 5.0], [0.0])

    def test_non_ascending_times_raise(self):
        with self.assertRaises(ValueError):
            dst.mode_identification([10.0, 5.0], [2.0, 0.0])


class ExcitationTechniqueTest(unittest.TestCase):
    def test_short_period(self):
        info = dst.excitation_technique("short-period")
        self.assertEqual(info["control"], "elevator")

    def test_all_modes_present(self):
        for mode in ["short-period", "phugoid", "dutch-roll",
                     "roll-subsidence", "spiral"]:
            info = dst.excitation_technique(mode)
            self.assertIn("control", info)

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            dst.excitation_technique("yaw-oscillation")


class HandlingQualitiesVerdictTest(unittest.TestCase):
    def test_short_period_well_damped(self):
        v = dst.handling_qualities_verdict("short-period", 0.5)
        self.assertEqual(v["verdict"], "acceptable")

    def test_short_period_poorly_damped(self):
        v = dst.handling_qualities_verdict("short-period", 0.05)
        self.assertEqual(v["verdict"], "inadequate")

    def test_dutch_roll_marginal(self):
        v = dst.handling_qualities_verdict("dutch-roll", 0.05)
        self.assertEqual(v["verdict"], "marginal")

    def test_spiral_divergent(self):
        v = dst.handling_qualities_verdict("spiral", -0.1)
        self.assertEqual(v["verdict"], "inadequate")

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            dst.handling_qualities_verdict("yaw-oscillation", 0.5)


if __name__ == "__main__":
    unittest.main()
