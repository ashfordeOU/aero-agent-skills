#!/usr/bin/env python3
"""Contract test for the resonance, sine and random vibration runs (offline)."""

import copy
import math
import unittest

from e3102_mechanical_tests_resonance_sine_random_logic import (
    DEFAULT_MAX_NOTCH_DEPTH_DB,
    DEFAULT_SHIFT_LIMIT_PERCENT,
    assess_random_run,
    assess_resonance_search,
    assess_sine_run,
    grade_axis,
    grade_mechanical_campaign,
    grms_after_offset_db,
    level_at_frequency,
    notch_depth_db,
    profile_covers_band,
    psd_segment_area,
    random_overall_grms,
    resonance_shift_percent,
    scale_psd_by_db,
    sine_sweep_duration_s,
    sweep_octaves,
    validate_breakpoints,
)

FLAT_PSD = [(20.0, 0.04), (2000.0, 0.04)]
SINE_PROFILE = [(5.0, 2.5), (20.0, 10.0), (100.0, 10.0)]

RESONANCE = {
    "pre_first_mode_hz": 120.0,
    "post_first_mode_hz": 118.0,
    "f_low_hz": 5.0,
    "f_high_hz": 2000.0,
}

SINE_RUN = {
    "required_profile": SINE_PROFILE,
    "f_low_hz": 5.0,
    "f_high_hz": 100.0,
    "sweep_rate_oct_per_min": 2.0,
}

RANDOM_RUN = {
    "psd_table": FLAT_PSD,
    "level_stage": "qualification",
    "level_offset_db": 0.0,
    "duration_s": 120.0,
    "required_duration_s": 120.0,
    "required_grms": 8.0,
}

AXIS = {
    "axis": "lateral-y",
    "resonance_search": RESONANCE,
    "sine_run": SINE_RUN,
    "random_run": RANDOM_RUN,
}

CAMPAIGN = {
    "axes": [
        dict(AXIS),
        dict(AXIS, axis="lateral-x"),
        dict(AXIS, axis="longitudinal-z"),
    ],
    "required_axes": ["lateral-x", "lateral-y", "longitudinal-z"],
}

FLAT_GRMS = math.sqrt(0.04 * (2000.0 - 20.0))


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class BreakpointTableTests(unittest.TestCase):
    def test_valid_table_is_returned_cleaned(self):
        self.assertEqual(len(validate_breakpoints(SINE_PROFILE)), 3)

    def test_single_point_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_breakpoints([(20.0, 0.04)])

    def test_non_monotonic_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_breakpoints([(100.0, 1.0), (20.0, 1.0)])

    def test_zero_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_breakpoints([(20.0, 0.0), (100.0, 1.0)])

    def test_table_spanning_the_band_covers_it(self):
        self.assertTrue(profile_covers_band(SINE_PROFILE, 5.0, 100.0))

    def test_table_short_of_the_band_does_not_cover_it(self):
        self.assertFalse(profile_covers_band(SINE_PROFILE, 5.0, 2000.0))

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            profile_covers_band(SINE_PROFILE, 100.0, 5.0)


class LogLogInterpolationTests(unittest.TestCase):
    def test_level_on_a_declared_breakpoint(self):
        self.assertAlmostEqual(level_at_frequency(SINE_PROFILE, 20.0), 10.0, places=9)

    def test_level_on_a_log_log_ramp(self):
        self.assertAlmostEqual(
            level_at_frequency([(20.0, 1.0), (80.0, 4.0)], 40.0), 2.0, places=9
        )

    def test_level_on_a_flat_segment(self):
        self.assertAlmostEqual(level_at_frequency(SINE_PROFILE, 60.0), 10.0, places=9)

    def test_frequency_below_the_table_refuses_to_extrapolate(self):
        with self.assertRaises(ValueError):
            level_at_frequency(SINE_PROFILE, 1.0)

    def test_frequency_above_the_table_refuses_to_extrapolate(self):
        with self.assertRaises(ValueError):
            level_at_frequency(SINE_PROFILE, 400.0)


class SweepTests(unittest.TestCase):
    def test_a_doubling_is_one_octave(self):
        self.assertAlmostEqual(sweep_octaves(20.0, 40.0), 1.0, places=9)

    def test_octaves_of_the_full_band(self):
        self.assertAlmostEqual(
            sweep_octaves(20.0, 2000.0), math.log(100.0) / math.log(2.0), places=9
        )

    def test_duration_is_octaves_over_the_rate(self):
        self.assertAlmostEqual(
            sine_sweep_duration_s(20.0, 40.0, 2.0), 30.0, places=9
        )

    def test_two_sweeps_take_twice_as_long(self):
        one = sine_sweep_duration_s(20.0, 40.0, 2.0, sweeps=1)
        two = sine_sweep_duration_s(20.0, 40.0, 2.0, sweeps=2)
        self.assertAlmostEqual(two, 2.0 * one, places=9)

    def test_zero_sweep_rate_rejected(self):
        with self.assertRaises(ValueError):
            sine_sweep_duration_s(20.0, 40.0, 0.0)

    def test_fractional_sweep_count_rejected(self):
        with self.assertRaises(ValueError):
            sine_sweep_duration_s(20.0, 40.0, 2.0, sweeps=1.5)


class NotchTests(unittest.TestCase):
    def test_a_halved_amplitude_is_about_six_decibel(self):
        self.assertAlmostEqual(notch_depth_db(10.0, 5.0), 6.0206, places=4)

    def test_no_notch_is_zero_decibel(self):
        self.assertAlmostEqual(notch_depth_db(10.0, 10.0), 0.0, places=9)

    def test_an_overshoot_is_a_negative_depth(self):
        self.assertLess(notch_depth_db(10.0, 12.0), 0.0)

    def test_zero_applied_level_rejected(self):
        with self.assertRaises(ValueError):
            notch_depth_db(10.0, 0.0)


class SpectralDensityTests(unittest.TestCase):
    def test_flat_segment_area_is_the_rectangle(self):
        self.assertAlmostEqual(
            psd_segment_area(20.0, 0.04, 2000.0, 0.04), 0.04 * 1980.0, places=9
        )

    def test_minus_one_slope_segment_uses_the_logarithmic_form(self):
        self.assertAlmostEqual(
            psd_segment_area(10.0, 1.0, 100.0, 0.1), 10.0 * math.log(10.0), places=9
        )

    def test_flat_table_overall_level(self):
        self.assertAlmostEqual(random_overall_grms(FLAT_PSD), FLAT_GRMS, places=9)

    def test_overall_level_is_not_the_sum_of_breakpoints(self):
        self.assertGreater(random_overall_grms(FLAT_PSD), 0.04 + 0.04)

    def test_reversed_segment_rejected(self):
        with self.assertRaises(ValueError):
            psd_segment_area(2000.0, 0.04, 20.0, 0.04)

    def test_three_decibel_offset_doubles_the_density(self):
        scaled = scale_psd_by_db(FLAT_PSD, 10.0 * math.log(2.0) / math.log(10.0))
        self.assertAlmostEqual(scaled[0][1], 0.08, places=9)

    def test_zero_offset_leaves_the_overall_level_alone(self):
        self.assertAlmostEqual(
            grms_after_offset_db(FLAT_GRMS, 0.0), FLAT_GRMS, places=9
        )

    def test_six_decibel_offset_doubles_the_overall_level(self):
        doubled = grms_after_offset_db(
            FLAT_GRMS, 20.0 * math.log(2.0) / math.log(10.0)
        )
        self.assertAlmostEqual(doubled, 2.0 * FLAT_GRMS, places=9)


class ResonanceSearchTests(unittest.TestCase):
    def test_small_shift_passes(self):
        result = assess_resonance_search(RESONANCE)
        self.assertTrue(result["passed"])
        self.assertLess(result["shift_percent"], 0.0)

    def test_shift_exactly_on_the_limit_passes(self):
        search = _case(RESONANCE, post_first_mode_hz=114.0)
        result = assess_resonance_search(search)
        self.assertAlmostEqual(
            abs(result["shift_percent"]), DEFAULT_SHIFT_LIMIT_PERCENT, places=9
        )
        self.assertTrue(result["passed"])

    def test_large_downward_shift_fails(self):
        search = _case(RESONANCE, post_first_mode_hz=100.0)
        result = assess_resonance_search(search)
        self.assertEqual(result["verdict"], "resonance-search-failed")

    def test_large_upward_shift_also_fails(self):
        search = _case(RESONANCE, post_first_mode_hz=140.0)
        self.assertFalse(assess_resonance_search(search)["passed"])

    def test_first_mode_outside_the_searched_band_is_reported(self):
        search = _case(RESONANCE, f_high_hz=100.0)
        result = assess_resonance_search(search)
        self.assertFalse(result["band_brackets_first_mode"])
        self.assertFalse(result["passed"])

    def test_shift_percent_sign_follows_the_move(self):
        self.assertAlmostEqual(resonance_shift_percent(100.0, 105.0), 5.0, places=9)

    def test_zero_pre_frequency_rejected(self):
        with self.assertRaises(ValueError):
            resonance_shift_percent(0.0, 105.0)


class SineRunTests(unittest.TestCase):
    def test_clean_sine_run_passes(self):
        result = assess_sine_run(SINE_RUN)
        self.assertTrue(result["passed"])
        self.assertEqual(result["notches"], [])

    def test_sine_run_duration_follows_the_rate(self):
        result = assess_sine_run(SINE_RUN)
        self.assertAlmostEqual(
            result["duration_s"],
            60.0 * math.log(20.0) / math.log(2.0) / 2.0,
            places=9,
        )

    def test_a_shallow_notch_is_recorded_and_still_passes(self):
        applied = [(5.0, 2.5), (20.0, 7.0), (100.0, 10.0)]
        result = assess_sine_run(_case(SINE_RUN, applied_profile=applied))
        self.assertTrue(result["passed"])
        self.assertTrue(result["notches"])

    def test_notch_exactly_on_the_floor_passes(self):
        deep = 10.0 / (10.0 ** (DEFAULT_MAX_NOTCH_DEPTH_DB / 20.0))
        applied = [(5.0, 2.5), (20.0, deep), (100.0, 10.0)]
        result = assess_sine_run(
            _case(SINE_RUN, applied_profile=applied, check_frequencies_hz=[20.0])
        )
        self.assertAlmostEqual(
            result["deepest_notch_db"], DEFAULT_MAX_NOTCH_DEPTH_DB, places=9
        )
        self.assertTrue(result["passed"])

    def test_a_notch_past_the_floor_fails(self):
        applied = [(5.0, 2.5), (20.0, 2.0), (100.0, 10.0)]
        result = assess_sine_run(_case(SINE_RUN, applied_profile=applied))
        self.assertFalse(result["passed"])
        self.assertTrue(any("notching floor" in note for note in result["findings"]))

    def test_an_overshoot_is_reported(self):
        applied = [(5.0, 2.5), (20.0, 14.0), (100.0, 10.0)]
        result = assess_sine_run(_case(SINE_RUN, applied_profile=applied))
        self.assertTrue(any("overshoots" in note for note in result["findings"]))

    def test_profile_short_of_the_band_fails(self):
        result = assess_sine_run(_case(SINE_RUN, f_high_hz=2000.0))
        self.assertFalse(result["covers_band"])
        self.assertFalse(result["passed"])

    def test_sweep_short_of_the_required_duration_fails(self):
        result = assess_sine_run(_case(SINE_RUN, required_duration_s=10000.0))
        self.assertFalse(result["passed"])


class RandomRunTests(unittest.TestCase):
    def test_clean_random_run_passes(self):
        result = assess_random_run(RANDOM_RUN)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["delivered_grms"], FLAT_GRMS, places=9)

    def test_delivered_level_exactly_on_the_requirement_passes(self):
        run = _case(RANDOM_RUN, required_grms=FLAT_GRMS)
        result = assess_random_run(run)
        self.assertAlmostEqual(result["delivered_grms"], FLAT_GRMS, places=9)
        self.assertTrue(result["passed"])

    def test_level_short_of_the_requirement_fails(self):
        run = _case(RANDOM_RUN, required_grms=12.0)
        result = assess_random_run(run)
        self.assertEqual(result["verdict"], "random-run-failed")

    def test_a_negative_offset_lowers_the_delivered_level(self):
        run = _case(RANDOM_RUN, level_offset_db=-6.0)
        self.assertLess(assess_random_run(run)["delivered_grms"], FLAT_GRMS)

    def test_short_run_fails_on_duration(self):
        run = _case(RANDOM_RUN, duration_s=30.0)
        result = assess_random_run(run)
        self.assertFalse(result["passed"])
        self.assertTrue(any("lasted" in note for note in result["findings"]))

    def test_unknown_level_stage_rejected(self):
        run = _case(RANDOM_RUN, level_stage="shakedown")
        with self.assertRaises(ValueError):
            assess_random_run(run)

    def test_missing_duration_rejected(self):
        run = _case(RANDOM_RUN)
        del run["duration_s"]
        with self.assertRaises(ValueError):
            assess_random_run(run)


class AxisAndCampaignTests(unittest.TestCase):
    def test_clean_axis_passes(self):
        result = grade_axis(AXIS)
        self.assertEqual(result["verdict"], "axis-passed")
        self.assertEqual(result["findings"], [])

    def test_axis_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            grade_axis(_case(AXIS, axis=""))

    def test_a_failed_resonance_search_fails_the_axis(self):
        axis = _case(AXIS, resonance_search=_case(RESONANCE, post_first_mode_hz=90.0))
        self.assertFalse(grade_axis(axis)["passed"])

    def test_clean_campaign_passes(self):
        result = grade_mechanical_campaign(CAMPAIGN)
        self.assertEqual(result["verdict"], "campaign-passed")
        self.assertEqual(result["passed_axes"], 3)

    def test_a_missing_axis_fails_the_campaign(self):
        campaign = _case(CAMPAIGN, axes=CAMPAIGN["axes"][:2])
        result = grade_mechanical_campaign(campaign)
        self.assertEqual(result["missing_axes"], ["longitudinal-z"])
        self.assertFalse(result["passed"])

    def test_a_repeated_axis_name_rejected(self):
        campaign = _case(CAMPAIGN, axes=[dict(AXIS), dict(AXIS)])
        with self.assertRaises(ValueError):
            grade_mechanical_campaign(campaign)

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            grade_mechanical_campaign(_case(CAMPAIGN, axes=[]))

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            grade_mechanical_campaign("lateral-y")


if __name__ == "__main__":
    unittest.main()
