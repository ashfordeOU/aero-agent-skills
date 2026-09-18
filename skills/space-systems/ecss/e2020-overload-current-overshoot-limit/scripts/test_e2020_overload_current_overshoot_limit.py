#!/usr/bin/env python3
"""Contract tests for the clause 5.4.1.1.1 overload current overshoot logic."""

import unittest

from e2020_overload_current_overshoot_limit_logic import (
    BEYOND_BOUND,
    DEFAULT_OVERSHOOT_FACTOR,
    PORTS,
    WITHIN_BOUND,
    assess_overload_overshoot,
    assess_port,
    last_crossing_below_s,
    overshoot_bound_a,
    overshoot_fraction,
    overshoot_ratio,
    peak_sample,
    settling_time_s,
    time_above_threshold_s,
    validate_factor,
    validate_waveform,
)

# A single triangular excursion whose crossings of the 2 A limitation value
# fall on exact instants: up through 2 A at 0.5 s, back down at 1.5 s.
RAMP = [(0.0, 0.0), (1.0, 4.0), (2.0, 0.0)]

LIMIT_A = 2.0
ONSET_S = 0.0

# Output port: peaks at 3 A, holds it, and is back under the limitation value
# at 2.5 s.
OUTPUT_SAMPLES = [(0.0, 1.0), (1.0, 3.0), (2.0, 3.0), (3.0, 1.0), (4.0, 1.0)]

# Input port: the input filter softens the same event so far that the port
# never rises above the limitation value at all.
INPUT_SAMPLES = [(0.0, 1.0), (1.0, 2.0), (2.0, 2.0), (3.0, 1.0), (4.0, 1.0)]

# Input port fed harder than the output, which is the cross-port observation.
INPUT_HARD = [(0.0, 1.0), (1.0, 3.5), (2.0, 3.5), (3.0, 1.0), (4.0, 1.0)]

# An excursion that is still above the limitation value when the record ends.
OUTPUT_STUCK = [(0.0, 1.0), (1.0, 3.0), (2.0, 3.0), (3.0, 3.0)]


class ValidateWaveformTests(unittest.TestCase):
    def test_returns_float_pairs(self):
        points = validate_waveform(RAMP)
        self.assertAlmostEqual(points[1][1], 4.0, places=9)
        self.assertIsInstance(points[1][0], float)

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 1.0)])

    def test_non_pair_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 1.0), (1.0, 2.0, 3.0)])

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 1.0), (1.0, -0.5)])

    def test_repeated_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 1.0), (0.0, 2.0)])

    def test_time_running_backwards_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(1.0, 1.0), (0.5, 2.0)])

    def test_non_finite_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 1.0), (1.0, float("inf"))])

    def test_boolean_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_waveform([(0.0, 1.0), (1.0, True)])


class FactorAndBoundTests(unittest.TestCase):
    def test_unity_factor_allowed(self):
        self.assertAlmostEqual(validate_factor(1.0), 1.0, places=12)

    def test_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_factor(0.9)

    def test_non_numeric_factor_rejected(self):
        with self.assertRaises(ValueError):
            validate_factor("1.2")

    def test_bound_is_the_factor_on_the_limitation_value(self):
        self.assertAlmostEqual(overshoot_bound_a(2.0, 1.5), 3.0, places=9)

    def test_default_factor_is_declared_above_unity(self):
        self.assertGreater(DEFAULT_OVERSHOOT_FACTOR, 1.0)

    def test_zero_limitation_value_rejected(self):
        with self.assertRaises(ValueError):
            overshoot_bound_a(0.0, 1.2)


class PeakTests(unittest.TestCase):
    def test_peak_is_the_highest_sample(self):
        self.assertAlmostEqual(peak_sample(RAMP)[1], 4.0, places=9)

    def test_peak_reports_its_instant(self):
        self.assertAlmostEqual(peak_sample(RAMP)[0], 1.0, places=9)

    def test_earliest_sample_wins_an_equal_peak(self):
        self.assertAlmostEqual(peak_sample(OUTPUT_SAMPLES)[0], 1.0, places=9)

    def test_ratio_against_the_limitation_value(self):
        self.assertAlmostEqual(overshoot_ratio(3.0, 2.0), 1.5, places=9)

    def test_fraction_is_the_excess_above_unity(self):
        self.assertAlmostEqual(overshoot_fraction(3.0, 2.0), 0.5, places=9)

    def test_fraction_floors_at_zero_for_a_peak_under_the_limit(self):
        self.assertAlmostEqual(overshoot_fraction(1.0, 2.0), 0.0, places=12)

    def test_negative_peak_rejected(self):
        with self.assertRaises(ValueError):
            overshoot_ratio(-1.0, 2.0)


class TimeAboveThresholdTests(unittest.TestCase):
    def test_interpolated_crossings_give_the_exact_excursion(self):
        self.assertAlmostEqual(time_above_threshold_s(RAMP, 2.0), 1.0, places=9)

    def test_whole_record_counts_above_a_zero_threshold(self):
        self.assertAlmostEqual(time_above_threshold_s(RAMP, 0.0), 2.0, places=9)

    def test_threshold_above_the_peak_gives_no_excursion(self):
        self.assertAlmostEqual(time_above_threshold_s(RAMP, 5.0), 0.0, places=12)

    def test_current_sitting_exactly_on_the_limit_is_not_an_overshoot(self):
        flat = [(0.0, 2.0), (1.0, 2.0)]
        self.assertAlmostEqual(time_above_threshold_s(flat, 2.0), 0.0, places=12)

    def test_two_humps_are_both_counted(self):
        twin = [(0.0, 0.0), (1.0, 4.0), (2.0, 0.0), (3.0, 4.0), (4.0, 0.0)]
        self.assertAlmostEqual(time_above_threshold_s(twin, 2.0), 2.0, places=9)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            time_above_threshold_s(RAMP, -1.0)


class CrossingAndSettlingTests(unittest.TestCase):
    def test_last_crossing_is_interpolated(self):
        self.assertAlmostEqual(last_crossing_below_s(RAMP, 2.0), 1.5, places=9)

    def test_last_crossing_of_two_humps_is_the_later_one(self):
        twin = [(0.0, 0.0), (1.0, 4.0), (2.0, 0.0), (3.0, 4.0), (4.0, 0.0)]
        self.assertAlmostEqual(last_crossing_below_s(twin, 2.0), 3.5, places=9)

    def test_record_ending_above_the_limit_has_no_crossing(self):
        self.assertIsNone(last_crossing_below_s(OUTPUT_STUCK, 2.0))

    def test_record_never_above_the_limit_crosses_at_its_start(self):
        self.assertAlmostEqual(last_crossing_below_s(INPUT_SAMPLES, 2.0), 0.0, places=12)

    def test_settling_time_is_measured_from_the_onset(self):
        self.assertAlmostEqual(
            settling_time_s(OUTPUT_SAMPLES, 2.0, 0.0), 2.5, places=9
        )

    def test_a_later_onset_shortens_the_settling_time(self):
        self.assertAlmostEqual(
            settling_time_s(OUTPUT_SAMPLES, 2.0, 0.5), 2.0, places=9
        )

    def test_settling_time_is_none_when_it_never_settles(self):
        self.assertIsNone(settling_time_s(OUTPUT_STUCK, 2.0, 0.0))

    def test_onset_outside_the_record_rejected(self):
        with self.assertRaises(ValueError):
            settling_time_s(OUTPUT_SAMPLES, 2.0, 9.0)

    def test_non_numeric_onset_rejected(self):
        with self.assertRaises(ValueError):
            settling_time_s(OUTPUT_SAMPLES, 2.0, "0.0")


class AssessPortTests(unittest.TestCase):
    def test_compliant_port_reports_its_measured_quantities(self):
        record = assess_port("output", OUTPUT_SAMPLES, LIMIT_A, 1.6, 3.0, ONSET_S)
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["peak_current_a"], 3.0, places=9)
        self.assertAlmostEqual(record["overshoot_ratio"], 1.5, places=9)
        self.assertAlmostEqual(record["overshoot_fraction"], 0.5, places=9)
        self.assertAlmostEqual(record["time_above_limit_s"], 2.0, places=9)
        self.assertAlmostEqual(record["settling_time_s"], 2.5, places=9)
        self.assertEqual(record["findings"], [])

    def test_peak_exactly_on_the_bound_is_inside_it(self):
        record = assess_port("output", OUTPUT_SAMPLES, LIMIT_A, 1.5, 3.0, ONSET_S)
        self.assertAlmostEqual(record["overshoot_bound_a"], 3.0, places=9)
        self.assertTrue(record["peak_within_bound"])

    def test_peak_beyond_the_bound_is_a_finding(self):
        record = assess_port("output", OUTPUT_SAMPLES, LIMIT_A, 1.2, 3.0, ONSET_S)
        self.assertFalse(record["peak_within_bound"])
        self.assertFalse(record["compliant"])
        self.assertTrue(any("peaks at" in f for f in record["findings"]))

    def test_settling_exactly_on_the_window_is_inside_it(self):
        record = assess_port("output", OUTPUT_SAMPLES, LIMIT_A, 1.6, 2.5, ONSET_S)
        self.assertTrue(record["settles_within_window"])

    def test_excursion_longer_than_the_window_is_a_finding(self):
        record = assess_port("output", OUTPUT_SAMPLES, LIMIT_A, 1.6, 1.0, ONSET_S)
        self.assertFalse(record["settles_within_window"])
        self.assertTrue(any("stays above" in f for f in record["findings"]))

    def test_a_port_that_never_returns_is_its_own_finding(self):
        record = assess_port("output", OUTPUT_STUCK, LIMIT_A, 1.6, 3.0, ONSET_S)
        self.assertIsNone(record["settling_time_s"])
        self.assertFalse(record["compliant"])
        self.assertTrue(any("never returns" in f for f in record["findings"]))

    def test_port_with_no_excursion_is_compliant(self):
        record = assess_port("input", INPUT_SAMPLES, LIMIT_A, 1.2, 3.0, ONSET_S)
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["time_above_limit_s"], 0.0, places=12)
        self.assertAlmostEqual(record["overshoot_fraction"], 0.0, places=12)

    def test_unknown_port_rejected(self):
        with self.assertRaises(ValueError):
            assess_port("midpoint", OUTPUT_SAMPLES, LIMIT_A, 1.2, 3.0, ONSET_S)

    def test_zero_settling_window_rejected(self):
        with self.assertRaises(ValueError):
            assess_port("output", OUTPUT_SAMPLES, LIMIT_A, 1.2, 0.0, ONSET_S)


class AssessOverloadOvershootTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "limitation_value_a": LIMIT_A,
            "onset_time_s": ONSET_S,
            "settling_window_s": 3.0,
            "allowed_factor": 1.6,
            "input_samples": INPUT_SAMPLES,
            "output_samples": OUTPUT_SAMPLES,
        }
        spec.update(overrides)
        return spec

    def test_both_ports_inside_their_bounds(self):
        report = assess_overload_overshoot(self._spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["verdict"], WITHIN_BOUND)
        self.assertEqual(report["findings"], [])

    def test_both_ports_are_assessed(self):
        report = assess_overload_overshoot(self._spec())
        self.assertEqual(set(report["ports"]), set(PORTS))

    def test_output_breach_fails_the_interface(self):
        report = assess_overload_overshoot(self._spec(allowed_factor=1.2))
        self.assertFalse(report["compliant"])
        self.assertEqual(report["verdict"], BEYOND_BOUND)
        self.assertTrue(any("output port" in f for f in report["findings"]))

    def test_per_port_factor_overrides_the_shared_one(self):
        report = assess_overload_overshoot(
            self._spec(allowed_factor=1.2, output_allowed_factor=1.6)
        )
        self.assertTrue(report["compliant"])

    def test_input_peak_above_the_output_peak_is_observed(self):
        report = assess_overload_overshoot(
            self._spec(input_samples=INPUT_HARD, allowed_factor=2.0)
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(len(report["observations"]), 1)
        self.assertIn("input filter", report["observations"][0])

    def test_softened_input_raises_no_observation(self):
        report = assess_overload_overshoot(self._spec())
        self.assertEqual(report["observations"], [])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["output_samples"]
        with self.assertRaises(ValueError):
            assess_overload_overshoot(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_overload_overshoot(["limitation_value_a"])

    def test_negative_limitation_value_rejected(self):
        with self.assertRaises(ValueError):
            assess_overload_overshoot(self._spec(limitation_value_a=-2.0))

    def test_onset_outside_the_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_overload_overshoot(self._spec(onset_time_s=-1.0))


if __name__ == "__main__":
    unittest.main()
