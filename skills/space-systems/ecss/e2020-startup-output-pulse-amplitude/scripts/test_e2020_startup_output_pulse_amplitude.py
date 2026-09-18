"""Contract tests for the clause 5.4.2.4.1 output pulse amplitude assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a capture that reverses in
time, a tail that never settles, an output that never reaches its settled
value, the start-up ramp being read as an undershoot, a separate undershoot
limit and its fallback, the instrument uncertainty widening a peak, and a
peak landing exactly on its limit.
"""

import unittest

from e2020_startup_output_pulse_amplitude_logic import (
    BASELINE_NOT_SETTLED,
    CAPTURE_NOT_ESTABLISHED,
    NO_DEPARTURE,
    OUTPUT_NEVER_SETTLED,
    OVERSHOOT,
    PULSE_AMPLITUDE_EXCEEDED,
    PULSE_AMPLITUDE_WITHIN_LIMIT,
    PULSE_LIMIT_NOT_ESTABLISHED,
    UNDERSHOOT,
    assess_startup_output_pulse_amplitude,
    baseline_has_settled,
    departures,
    first_arrival_index,
    judge_amplitude,
    peak_departures,
    settled_baseline,
    validate_capture,
    validate_sample,
    widen_for_uncertainty,
    worst_direction,
)

BASELINE_V = 28.0


def _capture(peak_v=29.0, dip_v=27.6):
    """A ramp from zero, one overshoot, one dip, then a flat tail at 28 V."""
    return [
        {"time_s": 0.0000, "voltage_v": 0.0},
        {"time_s": 0.0005, "voltage_v": 12.0},
        {"time_s": 0.0010, "voltage_v": 24.0},
        {"time_s": 0.0015, "voltage_v": BASELINE_V},
        {"time_s": 0.0020, "voltage_v": peak_v},
        {"time_s": 0.0025, "voltage_v": dip_v},
        {"time_s": 0.0030, "voltage_v": 28.05},
        {"time_s": 0.0040, "voltage_v": 28.0},
        {"time_s": 0.0050, "voltage_v": 28.0},
        {"time_s": 0.0060, "voltage_v": 28.0},
    ]


def _case(**overrides):
    case = {
        "unit_id": "pcu-out-1",
        "samples": _capture(),
        "settle_window_s": 0.002,
        "baseline_spread_limit_v": 0.1,
        "arrival_tolerance_v": 0.2,
        "max_positive_pulse_v": 2.0,
        "max_negative_pulse_v": 1.0,
        "amplitude_relative_uncertainty": 0.0,
        "amplitude_absolute_uncertainty_v": 0.0,
    }
    case.update(overrides)
    return case


class CaptureTests(unittest.TestCase):
    def test_the_reference_capture_validates(self):
        points = validate_capture(_capture())
        self.assertEqual(len(points), 10)

    def test_a_two_point_capture_is_refused(self):
        with self.assertRaises(ValueError):
            validate_capture(_capture()[:2])

    def test_a_capture_that_reverses_in_time_is_refused(self):
        points = _capture()
        points[4]["time_s"] = 0.0005
        with self.assertRaises(ValueError):
            validate_capture(points)

    def test_a_non_numeric_voltage_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sample({"time_s": 0.0, "voltage_v": "28"})

    def test_a_non_mapping_sample_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sample([0.0, 28.0])


class BaselineTests(unittest.TestCase):
    def test_the_baseline_is_the_average_of_the_tail(self):
        baseline = settled_baseline(_capture(), 0.002)
        self.assertAlmostEqual(baseline["baseline_v"], 28.0, places=9)
        self.assertAlmostEqual(baseline["spread_v"], 0.0, places=12)

    def test_a_settling_window_longer_than_the_capture_is_refused(self):
        with self.assertRaises(ValueError):
            settled_baseline(_capture(), 1.0)

    def test_a_settling_window_holding_one_point_is_refused(self):
        with self.assertRaises(ValueError):
            settled_baseline(_capture(), 0.0005)

    def test_a_moving_tail_is_not_a_settled_baseline(self):
        points = _capture()
        points[-1]["voltage_v"] = 26.0
        baseline = settled_baseline(points, 0.002)
        self.assertFalse(baseline_has_settled(baseline, 0.1))

    def test_a_flat_tail_is_a_settled_baseline(self):
        self.assertTrue(baseline_has_settled(settled_baseline(_capture(), 0.002), 0.1))


class WindowTests(unittest.TestCase):
    def test_the_excursion_window_opens_at_the_first_arrival(self):
        self.assertEqual(first_arrival_index(_capture(), BASELINE_V, 0.2), 3)

    def test_an_output_that_never_arrives_returns_no_index(self):
        points = [
            {"time_s": 0.0, "voltage_v": 0.0},
            {"time_s": 0.001, "voltage_v": 1.0},
            {"time_s": 0.002, "voltage_v": 2.0},
        ]
        self.assertIsNone(first_arrival_index(points, BASELINE_V, 0.2))

    def test_the_ramp_is_excluded_from_the_departure_window(self):
        window = departures(_capture(), BASELINE_V, 3)
        self.assertEqual(len(window), 7)
        self.assertAlmostEqual(window[0]["departure_v"], 0.0, places=12)

    def test_a_from_index_off_the_end_is_refused(self):
        with self.assertRaises(ValueError):
            departures(_capture(), BASELINE_V, 99)

    def test_the_whole_record_read_from_zero_would_call_the_ramp_an_undershoot(self):
        peaks = peak_departures(_capture(), BASELINE_V, 0)
        self.assertAlmostEqual(peaks["undershoot_v"], 28.0, places=9)

    def test_the_windowed_read_keeps_the_real_dip(self):
        peaks = peak_departures(_capture(), BASELINE_V, 3)
        self.assertAlmostEqual(peaks["undershoot_v"], 0.4, places=9)
        self.assertAlmostEqual(peaks["overshoot_v"], 1.0, places=9)


class UncertaintyTests(unittest.TestCase):
    def test_a_zero_uncertainty_leaves_the_amplitude_alone(self):
        self.assertAlmostEqual(widen_for_uncertainty(1.0, 0.0, 0.0), 1.0, places=12)

    def test_a_relative_uncertainty_scales_the_amplitude(self):
        self.assertAlmostEqual(widen_for_uncertainty(1.0, 0.05, 0.0), 1.05, places=9)

    def test_an_absolute_uncertainty_adds_to_the_amplitude(self):
        self.assertAlmostEqual(widen_for_uncertainty(1.0, 0.0, 0.02), 1.02, places=9)

    def test_a_relative_uncertainty_at_unity_is_refused(self):
        with self.assertRaises(ValueError):
            widen_for_uncertainty(1.0, 1.0, 0.0)

    def test_a_negative_uncertainty_is_refused(self):
        with self.assertRaises(ValueError):
            widen_for_uncertainty(1.0, -0.1, 0.0)


class JudgementTests(unittest.TestCase):
    def test_an_amplitude_on_its_limit_is_within_limit(self):
        judged = judge_amplitude(2.0, 2.0)
        self.assertTrue(judged["within_limit"])
        self.assertAlmostEqual(judged["margin_v"], 0.0, places=9)
        self.assertAlmostEqual(judged["limit_share"], 1.0, places=9)

    def test_an_amplitude_past_its_limit_is_not_within_limit(self):
        self.assertFalse(judge_amplitude(2.5, 2.0)["within_limit"])

    def test_a_zero_limit_is_refused(self):
        with self.assertRaises(ValueError):
            judge_amplitude(1.0, 0.0)

    def test_no_departure_either_way_is_reported_as_such(self):
        flat = judge_amplitude(0.0, 2.0)
        self.assertEqual(worst_direction(flat, judge_amplitude(0.0, 1.0)), NO_DEPARTURE)

    def test_the_worst_direction_is_the_larger_share_of_its_own_limit(self):
        over = judge_amplitude(1.0, 2.0)
        under = judge_amplitude(0.8, 1.0)
        self.assertEqual(worst_direction(over, under), UNDERSHOOT)

    def test_the_overshoot_wins_an_equal_share(self):
        over = judge_amplitude(1.0, 2.0)
        under = judge_amplitude(0.5, 1.0)
        self.assertEqual(worst_direction(over, under), OVERSHOOT)


class AssessmentTests(unittest.TestCase):
    def test_the_nominal_capture_is_within_limit(self):
        result = assess_startup_output_pulse_amplitude(_case())
        self.assertEqual(result["verdict"], PULSE_AMPLITUDE_WITHIN_LIMIT)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["baseline_v"], 28.0, places=9)

    def test_a_missing_capture_closes_the_assessment(self):
        case = _case()
        del case["samples"]
        result = assess_startup_output_pulse_amplitude(case)
        self.assertEqual(result["verdict"], CAPTURE_NOT_ESTABLISHED)

    def test_a_missing_limit_closes_the_assessment(self):
        case = _case()
        del case["max_positive_pulse_v"]
        result = assess_startup_output_pulse_amplitude(case)
        self.assertEqual(result["verdict"], PULSE_LIMIT_NOT_ESTABLISHED)

    def test_an_unsettled_tail_closes_the_assessment(self):
        points = _capture()
        points[-1]["voltage_v"] = 26.5
        result = assess_startup_output_pulse_amplitude(_case(samples=points))
        self.assertEqual(result["verdict"], BASELINE_NOT_SETTLED)

    def test_an_arrival_tolerance_inside_the_ripple_finds_no_arrival(self):
        points = [
            {"time_s": 0.0000, "voltage_v": 0.0},
            {"time_s": 0.0010, "voltage_v": 14.0},
            {"time_s": 0.0020, "voltage_v": 28.3},
            {"time_s": 0.0030, "voltage_v": 27.7},
            {"time_s": 0.0040, "voltage_v": 28.3},
            {"time_s": 0.0050, "voltage_v": 27.7},
        ]
        result = assess_startup_output_pulse_amplitude(
            _case(
                samples=points,
                settle_window_s=0.003,
                baseline_spread_limit_v=1.0,
                arrival_tolerance_v=0.05,
            )
        )
        self.assertEqual(result["verdict"], OUTPUT_NEVER_SETTLED)
        self.assertTrue(
            any("inside the ripple" in note for note in result["advisories"])
        )

    def test_an_overshoot_past_the_limit_is_reported(self):
        result = assess_startup_output_pulse_amplitude(
            _case(samples=_capture(peak_v=31.0))
        )
        self.assertEqual(result["verdict"], PULSE_AMPLITUDE_EXCEEDED)
        self.assertEqual(result["worst_direction"], OVERSHOOT)

    def test_an_undershoot_past_its_own_limit_is_reported(self):
        result = assess_startup_output_pulse_amplitude(
            _case(samples=_capture(dip_v=26.0))
        )
        self.assertEqual(result["verdict"], PULSE_AMPLITUDE_EXCEEDED)
        self.assertEqual(result["worst_direction"], UNDERSHOOT)

    def test_an_overshoot_exactly_on_the_limit_passes(self):
        result = assess_startup_output_pulse_amplitude(
            _case(samples=_capture(peak_v=30.0))
        )
        self.assertAlmostEqual(
            result["overshoot"]["judged_amplitude_v"], 2.0, places=9
        )
        self.assertEqual(result["verdict"], PULSE_AMPLITUDE_WITHIN_LIMIT)

    def test_the_uncertainty_can_push_a_passing_peak_over(self):
        result = assess_startup_output_pulse_amplitude(
            _case(
                samples=_capture(peak_v=29.9),
                amplitude_relative_uncertainty=0.1,
                amplitude_absolute_uncertainty_v=0.05,
            )
        )
        self.assertEqual(result["verdict"], PULSE_AMPLITUDE_EXCEEDED)

    def test_a_missing_undershoot_limit_falls_back_and_is_advised(self):
        case = _case()
        del case["max_negative_pulse_v"]
        result = assess_startup_output_pulse_amplitude(case)
        self.assertTrue(
            any("no separate undershoot limit" in note for note in result["advisories"])
        )
        self.assertAlmostEqual(result["undershoot"]["limit_v"], 2.0, places=9)

    def test_a_capture_starting_at_the_settled_value_is_advised(self):
        points = [
            {"time_s": 0.0000, "voltage_v": 28.0},
            {"time_s": 0.0005, "voltage_v": 28.4},
            {"time_s": 0.0010, "voltage_v": 28.0},
            {"time_s": 0.0020, "voltage_v": 28.0},
            {"time_s": 0.0030, "voltage_v": 28.0},
        ]
        result = assess_startup_output_pulse_amplitude(
            _case(samples=points, settle_window_s=0.002)
        )
        self.assertTrue(
            any("may have started after the ramp" in n for n in result["advisories"])
        )

    def test_a_peak_eating_most_of_its_limit_is_advised(self):
        result = assess_startup_output_pulse_amplitude(
            _case(samples=_capture(peak_v=29.95))
        )
        self.assertEqual(result["verdict"], PULSE_AMPLITUDE_WITHIN_LIMIT)
        self.assertTrue(
            any("little room for a later" in note for note in result["advisories"])
        )

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_startup_output_pulse_amplitude(["samples"])


if __name__ == "__main__":
    unittest.main()
