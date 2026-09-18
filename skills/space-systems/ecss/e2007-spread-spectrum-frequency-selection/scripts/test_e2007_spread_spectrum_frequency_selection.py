#!/usr/bin/env python3
"""Gate 3 contract test for e2007-spread-spectrum-frequency-selection.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_spread_spectrum_frequency_selection.py
"""

import unittest

from e2007_spread_spectrum_frequency_selection_logic import (
    CATEGORY_MARGINAL,
    CATEGORY_REJECTED,
    CATEGORY_USABLE,
    DEFAULT_TUNE_POINT_COUNT,
    MAIN_LOBE_CHIP_RATE_FACTOR,
    MODE_DIRECT_SEQUENCE,
    MODE_FREQUENCY_HOPPING,
    MODE_HYBRID,
    RECOGNIZED_MODES,
    TOL,
    assess_receiver_dwell,
    at_least,
    hop_revisit_period_s,
    normalize_mode,
    occupied_bandwidth_hz,
    plan_spread_spectrum_frequency_selection,
    required_receiver_dwell_s,
    select_hop_channels,
    select_tune_points,
    separation_findings,
    validate_hop_set,
    validate_spread_spectrum_unit,
    validate_tuning_band,
)

BAND = {"low_hz": 2.0e9, "high_hz": 2.4e9}


def direct_sequence_unit(**over):
    record = {
        "mode": "direct-sequence",
        "tuning_band_hz": None,
        "tuning_band": dict(BAND),
        "chip_rate_hz": 10.0e6,
    }
    record.pop("tuning_band_hz")
    record.update(over)
    return record


def hopping_unit(**over):
    record = {
        "mode": "frequency-hopping",
        "tuning_band": dict(BAND),
        "channel_bandwidth_hz": 1.0e6,
        "hop_dwell_s": 1.0e-3,
        "hop_channels_hz": [2.05e9, 2.15e9, 2.25e9, 2.35e9],
    }
    record.update(over)
    return record


def hybrid_unit(**over):
    record = {
        "mode": "hybrid",
        "tuning_band": dict(BAND),
        "chip_rate_hz": 5.0e6,
        "hop_dwell_s": 2.0e-3,
        "hop_channels_hz": [2.10e9, 2.20e9, 2.30e9],
    }
    record.update(over)
    return record


class SpreadSpectrumFrequencySelectionTest(unittest.TestCase):
    # --- declaration validation ---------------------------------------

    def test_recognized_modes_are_the_three_spreading_families(self):
        self.assertEqual(
            set(RECOGNIZED_MODES),
            {MODE_DIRECT_SEQUENCE, MODE_FREQUENCY_HOPPING, MODE_HYBRID},
        )

    def test_normalize_mode_accepts_padded_mixed_case(self):
        self.assertEqual(normalize_mode("  Direct-Sequence "), MODE_DIRECT_SEQUENCE)

    def test_normalize_mode_rejects_unknown_technique(self):
        with self.assertRaises(ValueError):
            normalize_mode("chirp")

    def test_normalize_mode_rejects_non_string(self):
        with self.assertRaises(ValueError):
            normalize_mode(3)

    def test_tuning_band_rejects_inverted_edges(self):
        with self.assertRaises(ValueError):
            validate_tuning_band({"low_hz": 2.4e9, "high_hz": 2.0e9})

    def test_tuning_band_rejects_non_positive_edge(self):
        with self.assertRaises(ValueError):
            validate_tuning_band({"low_hz": 0.0, "high_hz": 2.0e9})

    def test_tuning_band_returns_ordered_pair(self):
        low, high = validate_tuning_band(dict(BAND))
        self.assertAlmostEqual(low, 2.0e9, delta=1e-3)
        self.assertAlmostEqual(high, 2.4e9, delta=1e-3)

    def test_direct_sequence_declaration_requires_a_chip_rate(self):
        unit = direct_sequence_unit()
        del unit["chip_rate_hz"]
        with self.assertRaises(ValueError):
            validate_spread_spectrum_unit(unit)

    def test_hopping_declaration_requires_a_channel_bandwidth(self):
        unit = hopping_unit()
        del unit["channel_bandwidth_hz"]
        with self.assertRaises(ValueError):
            validate_spread_spectrum_unit(unit)

    def test_hopping_declaration_requires_a_positive_hop_dwell(self):
        with self.assertRaises(ValueError):
            validate_spread_spectrum_unit(hopping_unit(hop_dwell_s=0.0))

    def test_hop_set_rejects_a_channel_outside_the_tuning_band(self):
        with self.assertRaises(ValueError):
            validate_hop_set([2.05e9, 2.5e9], (2.0e9, 2.4e9))

    def test_hop_set_rejects_a_duplicate_channel(self):
        with self.assertRaises(ValueError):
            validate_hop_set([2.05e9, 2.05e9, 2.15e9], (2.0e9, 2.4e9))

    def test_hop_set_rejects_a_single_channel_declaration(self):
        with self.assertRaises(ValueError):
            validate_hop_set([2.05e9], (2.0e9, 2.4e9))

    def test_hop_set_is_returned_sorted(self):
        channels = validate_hop_set([2.25e9, 2.05e9, 2.15e9], (2.0e9, 2.4e9))
        self.assertEqual(list(channels), sorted(channels))

    # --- occupied bandwidth -------------------------------------------

    def test_direct_sequence_occupies_twice_the_chip_rate(self):
        unit = validate_spread_spectrum_unit(direct_sequence_unit())
        self.assertAlmostEqual(
            occupied_bandwidth_hz(unit),
            MAIN_LOBE_CHIP_RATE_FACTOR * 10.0e6,
            delta=1e-3,
        )

    def test_hopper_occupies_one_declared_channel_bandwidth(self):
        unit = validate_spread_spectrum_unit(hopping_unit())
        self.assertAlmostEqual(occupied_bandwidth_hz(unit), 1.0e6, delta=1e-3)

    def test_hybrid_occupies_the_spread_channel_not_the_hop_span(self):
        unit = validate_spread_spectrum_unit(hybrid_unit())
        self.assertAlmostEqual(occupied_bandwidth_hz(unit), 10.0e6, delta=1e-3)

    # --- tune-point selection -----------------------------------------

    def test_tune_points_sit_half_a_bandwidth_inside_the_band_edges(self):
        points = select_tune_points((2.0e9, 2.4e9), 20.0e6)
        self.assertEqual(len(points), DEFAULT_TUNE_POINT_COUNT)
        self.assertAlmostEqual(points[0], 2.01e9, delta=1e-3)
        self.assertAlmostEqual(points[-1], 2.39e9, delta=1e-3)

    def test_tune_points_are_evenly_spaced(self):
        points = select_tune_points((2.0e9, 2.4e9), 20.0e6)
        first_gap = points[1] - points[0]
        second_gap = points[2] - points[1]
        self.assertAlmostEqual(first_gap, second_gap, delta=1e-3)

    def test_tune_points_reject_a_band_narrower_than_the_emission(self):
        with self.assertRaises(ValueError):
            select_tune_points((2.0e9, 2.005e9), 20.0e6)

    def test_tune_points_reject_fewer_than_two_points(self):
        with self.assertRaises(ValueError):
            select_tune_points((2.0e9, 2.4e9), 20.0e6, count=1)

    def test_tune_points_reject_a_non_integer_count(self):
        with self.assertRaises(ValueError):
            select_tune_points((2.0e9, 2.4e9), 20.0e6, count=3.0)

    def test_separation_finding_raised_when_points_crowd_together(self):
        findings = separation_findings([2.0e9, 2.000001e9], 20.0e6)
        self.assertEqual(len(findings), 1)

    def test_separation_accepts_a_gap_exactly_one_bandwidth_wide(self):
        self.assertEqual(separation_findings([1.0e9, 1.02e9], 20.0e6), [])

    def test_at_least_absorbs_representation_error_only(self):
        self.assertTrue(at_least(6.0 - TOL / 2.0, 6.0))
        self.assertFalse(at_least(5.5, 6.0))

    # --- hop-channel selection and dwell ------------------------------

    def test_hop_selection_keeps_the_extremes_and_the_centre(self):
        picked = select_hop_channels([2.05e9, 2.15e9, 2.25e9, 2.35e9], 3)
        self.assertAlmostEqual(picked[0], 2.05e9, delta=1e-3)
        self.assertAlmostEqual(picked[-1], 2.35e9, delta=1e-3)
        self.assertEqual(len(picked), 3)

    def test_hop_selection_of_two_takes_only_the_extremes(self):
        picked = select_hop_channels([2.05e9, 2.15e9, 2.35e9], 2)
        self.assertEqual(len(picked), 2)
        self.assertAlmostEqual(picked[1], 2.35e9, delta=1e-3)

    def test_hop_selection_rejects_more_points_than_channels(self):
        with self.assertRaises(ValueError):
            select_hop_channels([2.05e9, 2.35e9], 3)

    def test_revisit_period_is_the_dwell_times_the_channel_count(self):
        self.assertAlmostEqual(hop_revisit_period_s(1.0e-3, 4), 4.0e-3, places=9)

    def test_revisit_period_rejects_a_non_positive_dwell(self):
        with self.assertRaises(ValueError):
            hop_revisit_period_s(0.0, 4)

    def test_required_dwell_applies_the_margin_factor(self):
        self.assertAlmostEqual(
            required_receiver_dwell_s(1.0e-3, 4, 2.0), 8.0e-3, places=9
        )

    def test_dwell_exactly_meeting_the_revisit_period_is_adequate(self):
        report = assess_receiver_dwell(4.0e-3, 4.0e-3)
        self.assertTrue(report["adequate"])
        self.assertAlmostEqual(report["shortfall_s"], 0.0, places=9)

    def test_short_dwell_reports_its_shortfall(self):
        report = assess_receiver_dwell(3.0e-3, 4.0e-3)
        self.assertFalse(report["adequate"])
        self.assertAlmostEqual(report["shortfall_s"], 1.0e-3, places=9)

    # --- aggregate plan ------------------------------------------------

    def test_direct_sequence_plan_is_usable_and_has_no_hop_points(self):
        plan = plan_spread_spectrum_frequency_selection(direct_sequence_unit())
        self.assertEqual(plan["category"], CATEGORY_USABLE)
        self.assertIsNone(plan["hop_points_hz"])
        self.assertEqual(plan["verdict"], "selection-usable")

    def test_hopping_plan_without_a_declared_dwell_is_marginal(self):
        plan = plan_spread_spectrum_frequency_selection(hopping_unit())
        self.assertEqual(plan["category"], CATEGORY_MARGINAL)
        self.assertTrue(plan["limitations"])

    def test_hopping_plan_with_a_short_dwell_is_rejected(self):
        plan = plan_spread_spectrum_frequency_selection(
            hopping_unit(), receiver_dwell_s=1.0e-3
        )
        self.assertEqual(plan["category"], CATEGORY_REJECTED)
        self.assertEqual(plan["verdict"], "selection-rejected")

    def test_hopping_plan_with_a_full_revisit_dwell_passes_the_dwell_check(self):
        plan = plan_spread_spectrum_frequency_selection(
            hopping_unit(), receiver_dwell_s=4.0e-3, hop_point_count=4
        )
        self.assertTrue(plan["receiver_dwell"]["adequate"])
        self.assertEqual(plan["findings"], [])

    def test_plan_reports_the_reduction_of_a_large_hop_set(self):
        plan = plan_spread_spectrum_frequency_selection(
            hopping_unit(), receiver_dwell_s=4.0e-3
        )
        self.assertEqual(len(plan["hop_points_hz"]), 3)
        self.assertTrue(any("reduced" in note for note in plan["limitations"]))

    def test_hybrid_plan_carries_both_tune_points_and_hop_points(self):
        plan = plan_spread_spectrum_frequency_selection(
            hybrid_unit(), receiver_dwell_s=6.0e-3
        )
        self.assertEqual(len(plan["tune_points_hz"]), 3)
        self.assertEqual(len(plan["hop_points_hz"]), 3)
        self.assertEqual(plan["category"], CATEGORY_USABLE)

    def test_plan_rejects_a_band_too_narrow_for_the_spread_emission(self):
        unit = direct_sequence_unit(tuning_band={"low_hz": 2.0e9, "high_hz": 2.01e9})
        with self.assertRaises(ValueError):
            plan_spread_spectrum_frequency_selection(unit)

    def test_plan_rejects_a_non_mapping_declaration(self):
        with self.assertRaises(ValueError):
            plan_spread_spectrum_frequency_selection(["direct-sequence"])


if __name__ == "__main__":
    unittest.main()
