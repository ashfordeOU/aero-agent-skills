"""Contract tests for the clause 5.4.2.5.1 output pulse duration assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a capture that reverses in
time, a tail that never settles, a zero-width band, a crossing placed by
interpolation rather than by sample counting, a momentary re-entry absorbed
by the dead time, an excursion shorter than the points that bracket it, a
record that ends with the output still outside its band, and a duration
landing exactly on the limit.
"""

import unittest

from e2020_startup_output_pulse_duration_logic import (
    ABOVE_BAND,
    BASELINE_NOT_SETTLED,
    BELOW_BAND,
    BOTH_SIDES,
    CAPTURE_NOT_ESTABLISHED,
    DURATION_LIMIT_NOT_ESTABLISHED,
    OUTPUT_NEVER_ENTERED_BAND,
    PULSE_DURATION_EXCEEDED,
    PULSE_DURATION_NOT_BOUNDED,
    PULSE_DURATION_WITHIN_LIMIT,
    assess_startup_output_pulse_duration,
    coalesce_excursions,
    coarsest_sample_interval,
    crossing_time,
    first_in_band_index,
    in_band,
    longest_excursion,
    permitted_band,
    raw_excursions,
    resolution_limited,
    settled_baseline,
    total_excursion_time,
    validate_capture,
    validate_sample,
)

BASELINE_V = 28.0


def _band():
    return permitted_band(BASELINE_V, 0.0, 1.0)


def _capture():
    """Ramp to 28 V, one 1 ms excursion to 30 V, then a flat tail."""
    return [
        {"time_s": 0.000, "voltage_v": 0.0},
        {"time_s": 0.001, "voltage_v": 14.0},
        {"time_s": 0.002, "voltage_v": 28.0},
        {"time_s": 0.003, "voltage_v": 30.0},
        {"time_s": 0.004, "voltage_v": 30.0},
        {"time_s": 0.005, "voltage_v": 28.0},
        {"time_s": 0.006, "voltage_v": 28.0},
        {"time_s": 0.007, "voltage_v": 28.0},
    ]


def _case(**overrides):
    case = {
        "unit_id": "pcu-out-1",
        "samples": _capture(),
        "settle_window_s": 0.002,
        "baseline_spread_limit_v": 0.1,
        "band_fraction": 0.0,
        "band_floor_v": 1.0,
        "re_entry_dead_time_s": 0.0,
        "max_pulse_duration_s": 0.005,
    }
    case.update(overrides)
    return case


class CaptureTests(unittest.TestCase):
    def test_the_reference_capture_validates(self):
        self.assertEqual(len(validate_capture(_capture())), 8)

    def test_a_two_point_capture_is_refused(self):
        with self.assertRaises(ValueError):
            validate_capture(_capture()[:2])

    def test_a_capture_that_reverses_in_time_is_refused(self):
        points = _capture()
        points[4]["time_s"] = 0.0005
        with self.assertRaises(ValueError):
            validate_capture(points)

    def test_a_non_mapping_sample_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sample([0.0, 28.0])

    def test_the_coarsest_interval_is_the_widest_gap(self):
        points = _capture()
        points[-1]["time_s"] = 0.020
        self.assertAlmostEqual(coarsest_sample_interval(points), 0.014, places=9)


class BandTests(unittest.TestCase):
    def test_the_baseline_is_the_average_of_the_tail(self):
        baseline = settled_baseline(_capture(), 0.002)
        self.assertAlmostEqual(baseline["baseline_v"], 28.0, places=9)

    def test_a_settling_window_longer_than_the_capture_is_refused(self):
        with self.assertRaises(ValueError):
            settled_baseline(_capture(), 1.0)

    def test_the_band_half_width_takes_the_larger_of_share_and_floor(self):
        band = permitted_band(28.0, 0.01, 1.0)
        self.assertAlmostEqual(band["half_width_v"], 1.0, places=9)
        wide = permitted_band(28.0, 0.1, 1.0)
        self.assertAlmostEqual(wide["half_width_v"], 2.8, places=9)

    def test_a_zero_width_band_is_refused(self):
        with self.assertRaises(ValueError):
            permitted_band(28.0, 0.0, 0.0)

    def test_a_band_fraction_at_unity_is_refused(self):
        with self.assertRaises(ValueError):
            permitted_band(28.0, 1.0, 0.0)

    def test_a_sample_on_the_band_edge_is_inside_it(self):
        self.assertTrue(in_band(29.0, _band()))
        self.assertTrue(in_band(27.0, _band()))
        self.assertFalse(in_band(29.5, _band()))


class CrossingTests(unittest.TestCase):
    def test_a_crossing_is_placed_between_the_samples(self):
        placed = crossing_time(
            {"time_s": 0.002, "voltage_v": 28.0},
            {"time_s": 0.003, "voltage_v": 30.0},
            29.0,
        )
        self.assertAlmostEqual(placed, 0.0025, places=9)

    def test_a_flat_segment_crosses_nothing(self):
        with self.assertRaises(ValueError):
            crossing_time(
                {"time_s": 0.0, "voltage_v": 28.0},
                {"time_s": 0.001, "voltage_v": 28.0},
                29.0,
            )

    def test_a_level_outside_the_segment_is_refused(self):
        with self.assertRaises(ValueError):
            crossing_time(
                {"time_s": 0.0, "voltage_v": 28.0},
                {"time_s": 0.001, "voltage_v": 29.0},
                31.0,
            )

    def test_a_segment_that_does_not_advance_is_refused(self):
        with self.assertRaises(ValueError):
            crossing_time(
                {"time_s": 0.001, "voltage_v": 28.0},
                {"time_s": 0.001, "voltage_v": 30.0},
                29.0,
            )


class ExcursionTests(unittest.TestCase):
    def test_the_window_opens_at_the_first_in_band_point(self):
        self.assertEqual(first_in_band_index(_capture(), _band()), 2)

    def test_a_capture_that_never_enters_the_band_returns_no_index(self):
        points = [
            {"time_s": 0.0, "voltage_v": 0.0},
            {"time_s": 0.001, "voltage_v": 1.0},
            {"time_s": 0.002, "voltage_v": 2.0},
        ]
        self.assertIsNone(first_in_band_index(points, _band()))

    def test_the_excursion_is_timed_between_interpolated_crossings(self):
        found = raw_excursions(_capture(), _band(), 2)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["start_s"], 0.0025, places=9)
        self.assertAlmostEqual(found[0]["end_s"], 0.0045, places=9)
        self.assertAlmostEqual(found[0]["duration_s"], 0.002, places=9)

    def test_sample_counting_would_have_given_a_different_duration(self):
        found = raw_excursions(_capture(), _band(), 2)
        self.assertNotAlmostEqual(found[0]["duration_s"], 0.001, places=6)

    def test_an_excursion_above_the_band_is_grouped_as_such(self):
        self.assertEqual(raw_excursions(_capture(), _band(), 2)[0]["direction"], ABOVE_BAND)

    def test_an_excursion_below_the_band_is_grouped_as_such(self):
        points = _capture()
        points[3]["voltage_v"] = 26.0
        points[4]["voltage_v"] = 26.0
        self.assertEqual(raw_excursions(points, _band(), 2)[0]["direction"], BELOW_BAND)

    def test_an_excursion_leaving_both_edges_is_grouped_as_both(self):
        points = _capture()
        points[3]["voltage_v"] = 31.0
        points[4]["voltage_v"] = 25.0
        self.assertEqual(raw_excursions(points, _band(), 2)[0]["direction"], BOTH_SIDES)

    def test_a_record_ending_outside_the_band_is_left_open(self):
        points = _capture()[:5]
        found = raw_excursions(points, _band(), 2)
        self.assertTrue(found[0]["open_end"])

    def test_a_window_starting_outside_the_band_is_left_open(self):
        points = [
            {"time_s": 0.000, "voltage_v": 28.0},
            {"time_s": 0.001, "voltage_v": 31.0},
            {"time_s": 0.002, "voltage_v": 31.0},
            {"time_s": 0.003, "voltage_v": 28.0},
            {"time_s": 0.004, "voltage_v": 28.0},
        ]
        found = raw_excursions(points, _band(), 1)
        self.assertTrue(found[0]["open_start"])

    def test_a_from_index_off_the_end_is_refused(self):
        with self.assertRaises(ValueError):
            raw_excursions(_capture(), _band(), 99)


class CoalesceTests(unittest.TestCase):
    def _twin(self):
        return [
            {"time_s": 0.000, "voltage_v": 28.0},
            {"time_s": 0.001, "voltage_v": 31.0},
            {"time_s": 0.002, "voltage_v": 28.0},
            {"time_s": 0.003, "voltage_v": 31.0},
            {"time_s": 0.004, "voltage_v": 28.0},
            {"time_s": 0.005, "voltage_v": 28.0},
            {"time_s": 0.006, "voltage_v": 28.0},
        ]

    def test_two_excursions_stay_two_without_a_dead_time(self):
        found = raw_excursions(self._twin(), _band(), 0)
        self.assertEqual(len(coalesce_excursions(found, 0.0)), 2)

    def test_a_dead_time_absorbs_the_momentary_re_entry(self):
        found = raw_excursions(self._twin(), _band(), 0)
        merged = coalesce_excursions(found, 0.002)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["coalesced_count"], 2)

    def test_a_negative_dead_time_is_refused(self):
        with self.assertRaises(ValueError):
            coalesce_excursions(raw_excursions(_capture(), _band(), 2), -1.0)

    def test_the_longest_excursion_is_the_widest_duration(self):
        found = raw_excursions(self._twin(), _band(), 0)
        self.assertAlmostEqual(longest_excursion(found)["duration_s"], 4.0 / 3000.0, places=9)

    def test_the_total_excursion_time_sums_every_stay_outside(self):
        found = raw_excursions(self._twin(), _band(), 0)
        self.assertAlmostEqual(total_excursion_time(found), 8.0 / 3000.0, places=9)

    def test_the_longest_helper_refuses_an_empty_set(self):
        with self.assertRaises(ValueError):
            longest_excursion([])

    def test_an_excursion_shorter_than_its_bracketing_points_is_resolution_limited(self):
        self.assertTrue(resolution_limited({"duration_s": 0.0005}, 0.001))
        self.assertFalse(resolution_limited({"duration_s": 0.002}, 0.001))

    def test_an_excursion_exactly_one_sample_long_is_not_resolution_limited(self):
        self.assertFalse(resolution_limited({"duration_s": 0.001}, 0.001))


class AssessmentTests(unittest.TestCase):
    def test_the_nominal_capture_is_within_limit(self):
        result = assess_startup_output_pulse_duration(_case())
        self.assertEqual(result["verdict"], PULSE_DURATION_WITHIN_LIMIT)
        self.assertAlmostEqual(result["longest_duration_s"], 0.002, places=9)

    def test_a_missing_capture_closes_the_assessment(self):
        case = _case()
        del case["samples"]
        self.assertEqual(
            assess_startup_output_pulse_duration(case)["verdict"],
            CAPTURE_NOT_ESTABLISHED,
        )

    def test_a_missing_duration_limit_closes_the_assessment(self):
        case = _case()
        del case["max_pulse_duration_s"]
        self.assertEqual(
            assess_startup_output_pulse_duration(case)["verdict"],
            DURATION_LIMIT_NOT_ESTABLISHED,
        )

    def test_an_unsettled_tail_closes_the_assessment(self):
        points = _capture()
        points[-1]["voltage_v"] = 26.0
        self.assertEqual(
            assess_startup_output_pulse_duration(_case(samples=points))["verdict"],
            BASELINE_NOT_SETTLED,
        )

    def test_a_band_narrower_than_the_ripple_is_never_entered(self):
        points = [
            {"time_s": 0.000, "voltage_v": 0.0},
            {"time_s": 0.001, "voltage_v": 14.0},
            {"time_s": 0.002, "voltage_v": 28.05},
            {"time_s": 0.003, "voltage_v": 27.95},
            {"time_s": 0.004, "voltage_v": 28.05},
        ]
        result = assess_startup_output_pulse_duration(
            _case(
                samples=points,
                settle_window_s=0.002,
                baseline_spread_limit_v=0.2,
                band_floor_v=0.001,
            )
        )
        self.assertEqual(result["verdict"], OUTPUT_NEVER_ENTERED_BAND)

    def test_a_duration_exactly_on_the_limit_passes(self):
        result = assess_startup_output_pulse_duration(
            _case(max_pulse_duration_s=0.002)
        )
        self.assertAlmostEqual(result["longest_duration_s"], 0.002, places=9)
        self.assertEqual(result["verdict"], PULSE_DURATION_WITHIN_LIMIT)

    def test_a_duration_past_the_limit_is_reported(self):
        result = assess_startup_output_pulse_duration(
            _case(max_pulse_duration_s=0.001)
        )
        self.assertEqual(result["verdict"], PULSE_DURATION_EXCEEDED)
        self.assertIn("longest excursion", result["findings"][0])

    def test_a_total_excursion_budget_can_fail_on_its_own(self):
        result = assess_startup_output_pulse_duration(
            _case(max_total_excursion_time_s=0.001)
        )
        self.assertEqual(result["verdict"], PULSE_DURATION_EXCEEDED)
        self.assertTrue(any("in total" in note for note in result["findings"]))

    def test_a_record_ending_outside_the_band_bounds_nothing(self):
        points = [
            {"time_s": 0.000, "voltage_v": 28.0},
            {"time_s": 0.001, "voltage_v": 28.0},
            {"time_s": 0.002, "voltage_v": 28.0},
            {"time_s": 0.003, "voltage_v": 30.0},
            {"time_s": 0.004, "voltage_v": 30.0},
        ]
        result = assess_startup_output_pulse_duration(
            _case(
                samples=points,
                settle_window_s=0.002,
                settled_output_v=28.0,
                max_pulse_duration_s=0.01,
            )
        )
        self.assertEqual(result["verdict"], PULSE_DURATION_NOT_BOUNDED)

    def test_a_declared_settled_output_far_from_the_tail_is_advised(self):
        points = [
            {"time_s": 0.000, "voltage_v": 28.0},
            {"time_s": 0.001, "voltage_v": 28.0},
            {"time_s": 0.002, "voltage_v": 28.0},
            {"time_s": 0.003, "voltage_v": 30.0},
            {"time_s": 0.004, "voltage_v": 30.0},
        ]
        result = assess_startup_output_pulse_duration(
            _case(
                samples=points,
                settle_window_s=0.002,
                settled_output_v=28.0,
                max_pulse_duration_s=0.01,
            )
        )
        self.assertTrue(
            any("may end before the output holds" in n for n in result["advisories"])
        )

    def test_a_flat_capture_reports_no_excursion(self):
        points = [
            {"time_s": 0.000, "voltage_v": 28.0},
            {"time_s": 0.001, "voltage_v": 28.0},
            {"time_s": 0.002, "voltage_v": 28.0},
            {"time_s": 0.003, "voltage_v": 28.0},
        ]
        result = assess_startup_output_pulse_duration(
            _case(samples=points, settle_window_s=0.002)
        )
        self.assertEqual(result["verdict"], PULSE_DURATION_WITHIN_LIMIT)
        self.assertAlmostEqual(result["total_excursion_time_s"], 0.0, places=12)

    def test_a_coalesced_pair_is_advised(self):
        points = [
            {"time_s": 0.000, "voltage_v": 28.0},
            {"time_s": 0.001, "voltage_v": 31.0},
            {"time_s": 0.002, "voltage_v": 28.0},
            {"time_s": 0.003, "voltage_v": 31.0},
            {"time_s": 0.004, "voltage_v": 28.0},
            {"time_s": 0.005, "voltage_v": 28.0},
            {"time_s": 0.006, "voltage_v": 28.0},
        ]
        result = assess_startup_output_pulse_duration(
            _case(samples=points, re_entry_dead_time_s=0.002)
        )
        self.assertTrue(
            any("absorbed into" in note for note in result["advisories"])
        )

    def test_a_long_excursion_near_the_limit_is_advised(self):
        result = assess_startup_output_pulse_duration(
            _case(max_pulse_duration_s=0.00205)
        )
        self.assertEqual(result["verdict"], PULSE_DURATION_WITHIN_LIMIT)
        self.assertTrue(
            any("little room for a later" in note for note in result["advisories"])
        )

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_startup_output_pulse_duration(["samples"])


if __name__ == "__main__":
    unittest.main()
