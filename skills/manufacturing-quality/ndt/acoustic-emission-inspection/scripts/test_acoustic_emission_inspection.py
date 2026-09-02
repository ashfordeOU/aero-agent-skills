#!/usr/bin/env python3
"""Gate 3 contract test: acoustic emission inspection logic.

Exercises scripts/acoustic_emission_inspection_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3. Covers
amplitude threshold crossing including a zero threshold, signal energy
weighting, hit-to-event grouping with the HDT window, linear source
location including impossible arrival times, planar source location
including inconsistent time sets and out-of-grid sources, the Felicity
ratio, the Kaiser effect verdict, and invalid-input edge cases.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import acoustic_emission_inspection_logic as ae  # noqa: E402


def arrival_times_for(source, sensors, speed):
    """Deterministic helper: times = distance / speed per sensor."""
    x, y = source
    return [math.hypot(x - sx, y - sy) / speed for sx, sy in sensors]


SQUARE = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
TRIANGLE = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
SPEED = 3000.0


class HitThresholdTest(unittest.TestCase):
    def test_threshold_crossing(self):
        result = ae.hit_threshold_check([55.0, 42.0, 38.0, 60.0, 45.0], 40.0)
        self.assertEqual(result["hit_count"], 4)
        self.assertEqual(result["total_signals"], 5)
        self.assertEqual(result["hits"], [55.0, 42.0, 60.0, 45.0])

    def test_zero_threshold_keeps_everything_non_negative(self):
        result = ae.hit_threshold_check([0.0, 10.0, 5.0], 0.0)
        self.assertEqual(result["hit_count"], 3)
        self.assertEqual(result["hits"], [0.0, 10.0, 5.0])

    def test_below_threshold_are_not_hits(self):
        result = ae.hit_threshold_check([55.0, 30.0], 40.0)
        self.assertEqual(result["hit_count"], 1)
        self.assertEqual(result["hits"], [55.0])

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            ae.hit_threshold_check([10.0], -1.0)


class SignalEnergyTest(unittest.TestCase):
    def test_energy_is_dt_weighted_sum_of_squares(self):
        self.assertAlmostEqual(ae.signal_energy([2.0, 3.0], 0.5), 6.5)

    def test_energy_of_empty_signal_is_zero(self):
        self.assertEqual(ae.signal_energy([], 1.0), 0.0)

    def test_non_positive_dt_raises(self):
        with self.assertRaises(ValueError):
            ae.signal_energy([1.0], 0.0)
        with self.assertRaises(ValueError):
            ae.signal_energy([1.0], -0.1)


class EventGroupingTest(unittest.TestCase):
    def test_hits_within_hdt_form_one_event(self):
        events = ae.group_hits_to_events([1.0, 1.2, 1.3, 5.0, 5.1], 0.5)
        self.assertEqual(events, [[1.0, 1.2, 1.3], [5.0, 5.1]])

    def test_unsorted_input_is_grouped_chronologically(self):
        events = ae.group_hits_to_events([5.1, 1.0, 1.3, 5.0, 1.2], 0.5)
        self.assertEqual(events, [[1.0, 1.2, 1.3], [5.0, 5.1]])

    def test_every_hit_its_own_event_with_tiny_hdt(self):
        events = ae.group_hits_to_events([1.0, 2.0, 3.0], 0.1)
        self.assertEqual(events, [[1.0], [2.0], [3.0]])

    def test_empty_input_returns_empty(self):
        self.assertEqual(ae.group_hits_to_events([], 0.5), [])

    def test_non_positive_hdt_raises(self):
        with self.assertRaises(ValueError):
            ae.group_hits_to_events([1.0], 0.0)


class LinearLocationTest(unittest.TestCase):
    def test_source_at_known_position(self):
        # Sensors at 0 and 1 m, source at 0.3 m, speed 3000 m/s.
        t1 = 0.3 / SPEED
        t2 = 0.7 / SPEED
        x = ae.source_location_linear(1.0, [t1, t2], SPEED)
        self.assertAlmostEqual(x, 0.3, places=9)

    def test_source_closer_to_sensor_two(self):
        t1 = 0.7 / SPEED
        t2 = 0.3 / SPEED
        x = ae.source_location_linear(1.0, [t1, t2], SPEED)
        self.assertAlmostEqual(x, 0.7, places=9)

    def test_impossible_arrival_times_raise(self):
        with self.assertRaises(ValueError):
            ae.source_location_linear(1.0, [1e-4, 6e-4], SPEED)
        with self.assertRaises(ValueError):
            ae.source_location_linear(1.0, [5e-4, 1e-4], SPEED)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ae.source_location_linear(0.0, [1e-4, 2e-4], SPEED)
        with self.assertRaises(ValueError):
            ae.source_location_linear(1.0, [1e-4, 2e-4], 0.0)
        with self.assertRaises(ValueError):
            ae.source_location_linear(1.0, [1e-4], SPEED)
        with self.assertRaises(ValueError):
            ae.source_location_linear(1.0, [-1e-4, 2e-4], SPEED)


class PlanarLocationTest(unittest.TestCase):
    def test_square_array_known_source(self):
        times = arrival_times_for((0.4, 0.6), SQUARE, SPEED)
        result = ae.source_location_planar(SQUARE, times, SPEED)
        self.assertAlmostEqual(result["x"], 0.4, places=6)
        self.assertAlmostEqual(result["y"], 0.6, places=6)
        self.assertLess(result["residual"], 1e-9)

    def test_triangle_array_known_source(self):
        times = arrival_times_for((0.3, 0.25), TRIANGLE, SPEED)
        result = ae.source_location_planar(TRIANGLE, times, SPEED)
        self.assertAlmostEqual(result["x"], 0.3, places=6)
        self.assertAlmostEqual(result["y"], 0.25, places=6)

    def test_impossible_arrival_times_raise(self):
        # v*(t1 - t0) = 1.5 m exceeds the 1 m sensor spacing.
        times = [0.0, 5e-4, 0.0, 0.0]
        with self.assertRaises(ValueError):
            ae.source_location_planar(SQUARE, times, SPEED)

    def test_inconsistent_time_set_raises(self):
        times = arrival_times_for((0.4, 0.6), SQUARE, SPEED)
        times[3] += 2e-4  # corrupt one arrival; passes pair checks, no common point
        with self.assertRaises(ValueError):
            ae.source_location_planar(SQUARE, times, SPEED)

    def test_out_of_grid_source_raises(self):
        times = arrival_times_for((5.0, 5.0), SQUARE, SPEED)
        with self.assertRaises(ValueError):
            ae.source_location_planar(SQUARE, times, SPEED)

    def test_fewer_than_three_sensors_raises(self):
        two = SQUARE[:2]
        times = arrival_times_for((0.4, 0.6), two, SPEED)
        with self.assertRaises(ValueError):
            ae.source_location_planar(two, times, SPEED)

    def test_mismatched_lengths_raise(self):
        times = arrival_times_for((0.4, 0.6), SQUARE, SPEED)[:3]
        with self.assertRaises(ValueError):
            ae.source_location_planar(SQUARE, times, SPEED)

    def test_non_positive_speed_raises(self):
        times = arrival_times_for((0.4, 0.6), SQUARE, SPEED)
        with self.assertRaises(ValueError):
            ae.source_location_planar(SQUARE, times, -1.0)


class KaiserFelicityTest(unittest.TestCase):
    def test_felicity_ratio_value(self):
        self.assertAlmostEqual(ae.felicity_ratio(88.0, 100.0), 0.88)

    def test_felicity_ratio_unit_when_kaiser_holds(self):
        self.assertAlmostEqual(ae.felicity_ratio(102.0, 100.0), 1.02)

    def test_kaiser_holds_above_previous_max(self):
        verdict = ae.kaiser_effect_check(102.0, 100.0)
        self.assertTrue(verdict["kaiser_effect_holds"])
        self.assertFalse(verdict["felicity_effect"])
        self.assertFalse(verdict["damage_indicated"])

    def test_damage_indicated_below_threshold(self):
        verdict = ae.kaiser_effect_check(88.0, 100.0)
        self.assertAlmostEqual(verdict["felicity_ratio"], 0.88)
        self.assertFalse(verdict["kaiser_effect_holds"])
        self.assertTrue(verdict["felicity_effect"])
        self.assertTrue(verdict["damage_indicated"])

    def test_custom_threshold_respected(self):
        verdict = ae.kaiser_effect_check(93.0, 100.0, felicity_threshold=0.90)
        self.assertTrue(verdict["felicity_effect"])
        self.assertFalse(verdict["damage_indicated"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ae.felicity_ratio(50.0, 0.0)
        with self.assertRaises(ValueError):
            ae.felicity_ratio(-1.0, 100.0)
        with self.assertRaises(ValueError):
            ae.kaiser_effect_check(50.0, 100.0, felicity_threshold=1.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
