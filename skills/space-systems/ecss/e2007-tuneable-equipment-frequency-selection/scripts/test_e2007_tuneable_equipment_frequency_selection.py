#!/usr/bin/env python3
"""Gate 3 contract test for e2007-tuneable-equipment-frequency-selection.

Stdlib unittest only, offline, deterministic.
"""

import unittest

from e2007_tuneable_equipment_frequency_selection_logic import (
    DEFAULT_TUNING_SPEC,
    FREQ_EPS,
    band_span_hz,
    channel_centres_hz,
    check_band_coverage,
    evaluate_tuning_plan,
    largest_normalized_gap,
    normalize_band,
    normalized_positions,
    resolve_spec,
    select_band_frequencies,
    select_channel_frequencies,
    tuning_plan_readiness,
)


def tuneable_band():
    return {"name": "s-band-receive", "start_hz": 2.0e9, "stop_hz": 2.4e9}


def channel_band():
    return {
        "name": "uhf-channels",
        "start_hz": 4.0e8,
        "stop_hz": 4.10e8,
        "channel_spacing_hz": 1.0e6,
        "channel_count": 11,
    }


def nominal_config():
    return {
        "bands": [tuneable_band(), channel_band()],
        "plan": {
            "s-band-receive": [2.0e9, 2.2e9, 2.4e9],
            "uhf-channels": [4.0e8, 4.05e8, 4.10e8],
        },
    }


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["min_points_per_band"], 3.0, places=9)
        self.assertEqual(set(spec), set(DEFAULT_TUNING_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"min_points_per_band": 5.0})
        self.assertAlmostEqual(spec["min_points_per_band"], 5.0, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"min_points_per_band": 5.0})
        self.assertAlmostEqual(DEFAULT_TUNING_SPEC["min_points_per_band"], 3.0, places=9)

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"antenna_polarization": 1.0})

    def test_negative_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"edge_tolerance_fraction": -0.1})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("min_points_per_band", 5.0)])


class TestBandValidation(unittest.TestCase):
    def test_a_well_formed_band_is_accepted(self):
        band = normalize_band(tuneable_band())
        self.assertEqual(band["name"], "s-band-receive")
        self.assertAlmostEqual(band["start_hz"], 2.0e9, places=3)
        self.assertAlmostEqual(band["stop_hz"], 2.4e9, places=3)

    def test_span_is_the_band_width(self):
        self.assertAlmostEqual(band_span_hz(tuneable_band()), 4.0e8, places=3)

    def test_inverted_band_is_rejected(self):
        band = tuneable_band()
        band["stop_hz"] = 1.0e9
        with self.assertRaises(ValueError):
            normalize_band(band)

    def test_zero_width_band_is_rejected(self):
        band = tuneable_band()
        band["stop_hz"] = band["start_hz"]
        with self.assertRaises(ValueError):
            normalize_band(band)

    def test_non_positive_start_is_rejected(self):
        band = tuneable_band()
        band["start_hz"] = 0.0
        with self.assertRaises(ValueError):
            normalize_band(band)

    def test_blank_band_name_is_rejected(self):
        band = tuneable_band()
        band["name"] = "   "
        with self.assertRaises(ValueError):
            normalize_band(band)

    def test_non_numeric_edge_is_rejected(self):
        band = tuneable_band()
        band["stop_hz"] = "2.4e9"
        with self.assertRaises(ValueError):
            normalize_band(band)

    def test_channel_plan_is_carried_through(self):
        band = normalize_band(channel_band())
        self.assertEqual(band["channel_count"], 11)

    def test_a_channel_plan_running_past_the_band_is_rejected(self):
        band = channel_band()
        band["channel_count"] = 40
        with self.assertRaises(ValueError):
            normalize_band(band)

    def test_a_fractional_channel_count_is_rejected(self):
        band = channel_band()
        band["channel_count"] = 11.5
        with self.assertRaises(ValueError):
            normalize_band(band)


class TestSelection(unittest.TestCase):
    def test_default_spread_uses_the_minimum_point_count(self):
        chosen = select_band_frequencies(tuneable_band())
        self.assertEqual(len(chosen), 3)

    def test_the_spread_reaches_both_band_edges(self):
        chosen = select_band_frequencies(tuneable_band())
        self.assertAlmostEqual(chosen[0], 2.0e9, places=3)
        self.assertAlmostEqual(chosen[-1], 2.4e9, places=3)

    def test_the_spread_is_even(self):
        chosen = select_band_frequencies(tuneable_band(), 5)
        gaps = [chosen[i + 1] - chosen[i] for i in range(len(chosen) - 1)]
        for gap in gaps:
            self.assertAlmostEqual(gap, 1.0e8, places=3)

    def test_a_single_point_spread_is_rejected(self):
        with self.assertRaises(ValueError):
            select_band_frequencies(tuneable_band(), 1)

    def test_a_non_integer_point_count_is_rejected(self):
        with self.assertRaises(ValueError):
            select_band_frequencies(tuneable_band(), 3.5)

    def test_channel_centres_are_on_the_channel_grid(self):
        centres = channel_centres_hz(channel_band())
        self.assertEqual(len(centres), 11)
        self.assertAlmostEqual(centres[0], 4.0e8, places=3)
        self.assertAlmostEqual(centres[-1], 4.10e8, places=3)

    def test_channel_centres_need_a_channel_plan(self):
        with self.assertRaises(ValueError):
            channel_centres_hz(tuneable_band())

    def test_channel_selection_takes_the_lowest_and_highest_channel(self):
        chosen = select_channel_frequencies(channel_band())
        self.assertAlmostEqual(chosen[0], 4.0e8, places=3)
        self.assertAlmostEqual(chosen[-1], 4.10e8, places=3)

    def test_channel_selection_lands_on_real_channels(self):
        centres = set(channel_centres_hz(channel_band()))
        for value in select_channel_frequencies(channel_band(), 5):
            self.assertTrue(
                any(abs(value - c) < 1.0 for c in centres),
                "%r is not a channel centre" % (value,),
            )

    def test_asking_for_more_channels_than_exist_is_rejected(self):
        with self.assertRaises(ValueError):
            select_channel_frequencies(channel_band(), 40)


class TestCoverage(unittest.TestCase):
    def test_positions_are_fractions_of_the_span(self):
        positions = normalized_positions(tuneable_band(), [2.0e9, 2.2e9, 2.4e9])
        self.assertAlmostEqual(positions[1], 0.5, places=9)

    def test_positions_are_returned_sorted(self):
        positions = normalized_positions(tuneable_band(), [2.4e9, 2.0e9, 2.2e9])
        self.assertEqual(positions, sorted(positions))

    def test_a_frequency_outside_the_band_is_rejected(self):
        with self.assertRaises(ValueError):
            normalized_positions(tuneable_band(), [2.0e9, 3.0e9])

    def test_an_empty_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            normalized_positions(tuneable_band(), [])

    def test_an_even_three_point_plan_leaves_half_band_gaps(self):
        gap = largest_normalized_gap(tuneable_band(), [2.0e9, 2.2e9, 2.4e9])
        self.assertAlmostEqual(gap, 0.5, places=9)

    def test_clustered_points_leave_a_large_gap(self):
        gap = largest_normalized_gap(tuneable_band(), [2.18e9, 2.2e9, 2.22e9])
        self.assertAlmostEqual(gap, 0.45, places=9)

    def test_an_even_plan_is_compliant(self):
        check = check_band_coverage(tuneable_band(), [2.0e9, 2.2e9, 2.4e9])
        self.assertTrue(check["compliant"])
        self.assertTrue(check["bottom_edge_ok"])
        self.assertTrue(check["top_edge_ok"])

    def test_a_gap_exactly_on_the_allowance_is_accepted(self):
        check = check_band_coverage(tuneable_band(), [2.0e9, 2.2e9, 2.4e9])
        self.assertAlmostEqual(check["largest_gap_fraction"], 0.5, places=9)
        self.assertTrue(check["gap_ok"])

    def test_a_clustered_plan_fails_both_edges(self):
        check = check_band_coverage(tuneable_band(), [2.18e9, 2.2e9, 2.22e9])
        self.assertFalse(check["bottom_edge_ok"])
        self.assertFalse(check["top_edge_ok"])
        self.assertFalse(check["compliant"])

    def test_two_points_fail_the_count(self):
        check = check_band_coverage(tuneable_band(), [2.0e9, 2.4e9])
        self.assertFalse(check["enough_points"])
        self.assertFalse(check["gap_ok"])

    def test_a_point_just_inside_the_edge_tolerance_passes(self):
        check = check_band_coverage(tuneable_band(), [2.02e9, 2.2e9, 2.38e9])
        self.assertTrue(check["bottom_edge_ok"])
        self.assertTrue(check["top_edge_ok"])

    def test_a_tighter_edge_tolerance_rejects_the_same_plan(self):
        plan = [2.02e9, 2.2e9, 2.38e9]
        self.assertTrue(check_band_coverage(tuneable_band(), plan)["bottom_edge_ok"])
        tight = check_band_coverage(tuneable_band(), plan, {"edge_tolerance_fraction": 0.01})
        self.assertFalse(tight["bottom_edge_ok"])

    def test_a_higher_point_floor_rejects_a_three_point_plan(self):
        check = check_band_coverage(
            tuneable_band(), [2.0e9, 2.2e9, 2.4e9], {"min_points_per_band": 5.0}
        )
        self.assertFalse(check["enough_points"])


class TestAggregation(unittest.TestCase):
    """End-to-end workflow: every step of the plan review feeds one gate token."""

    def test_a_covered_unit_is_ready(self):
        result = evaluate_tuning_plan(nominal_config())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "ready-for-measurement")

    def test_a_band_with_no_plan_holds_the_run(self):
        config = nominal_config()
        del config["plan"]["uhf-channels"]
        result = evaluate_tuning_plan(config)
        self.assertFalse(result["ready"])
        self.assertTrue(
            any("no measurement frequencies" in f for f in result["findings"]),
            result["findings"],
        )

    def test_a_missing_band_gets_a_recommended_plan(self):
        config = nominal_config()
        del config["plan"]["uhf-channels"]
        result = evaluate_tuning_plan(config)
        self.assertIn("uhf-channels", result["recommended_frequencies_hz"])
        self.assertEqual(len(result["recommended_frequencies_hz"]["uhf-channels"]), 3)

    def test_a_clustered_band_holds_the_run_and_is_named(self):
        config = nominal_config()
        config["plan"]["s-band-receive"] = [2.18e9, 2.2e9, 2.22e9]
        result = evaluate_tuning_plan(config)
        self.assertFalse(result["ready"])
        self.assertTrue(
            any("lower edge" in f for f in result["findings"]), result["findings"]
        )
        self.assertEqual(result["status"], "hold-tuning-plan")

    def test_a_recommended_plan_for_a_channel_range_lands_on_channels(self):
        config = nominal_config()
        config["plan"]["uhf-channels"] = [4.04e8, 4.05e8]
        result = evaluate_tuning_plan(config)
        centres = set(channel_centres_hz(channel_band()))
        for value in result["recommended_frequencies_hz"]["uhf-channels"]:
            self.assertTrue(any(abs(value - c) < 1.0 for c in centres))

    def test_a_plan_naming_an_undeclared_band_is_rejected(self):
        config = nominal_config()
        config["plan"]["x-band"] = [1.0e10]
        with self.assertRaises(ValueError):
            evaluate_tuning_plan(config)

    def test_duplicate_band_names_are_rejected(self):
        config = nominal_config()
        config["bands"].append(tuneable_band())
        with self.assertRaises(ValueError):
            evaluate_tuning_plan(config)

    def test_missing_plan_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tuning_plan({"bands": [tuneable_band()]})

    def test_non_mapping_config_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tuning_plan(["s-band-receive"])

    def test_empty_band_list_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tuning_plan({"bands": [], "plan": {}})

    def test_gate_token_needs_a_sequence(self):
        with self.assertRaises(ValueError):
            tuning_plan_readiness("no findings")

    def test_gate_token_reflects_the_finding_list(self):
        self.assertEqual(tuning_plan_readiness([]), "ready-for-measurement")
        self.assertEqual(tuning_plan_readiness(["one"]), "hold-tuning-plan")

    def test_named_tolerance_is_far_below_any_coverage_limit(self):
        self.assertLess(FREQ_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
