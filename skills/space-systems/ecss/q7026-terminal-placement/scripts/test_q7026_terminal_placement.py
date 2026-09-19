#!/usr/bin/env python3
"""Contract test for terminal and contact placement before crimping (offline)."""

import copy
import unittest

from q7026_terminal_placement_logic import (
    PLACEMENT_ACCEPT,
    PLACEMENT_REJECT,
    PLACEMENT_REPOSITION,
    assess_placement,
    assess_placement_batch,
    evaluate_bottoming,
    evaluate_entrapment,
    evaluate_insulation_gap,
    evaluate_seating,
    evaluate_stray_strands,
    evaluate_window_fill,
    lookup_contact,
    validate_contact_table,
)

TABLE = {
    "M39029-22": {
        "gap_min_mm": 0.3,
        "gap_max_mm": 1.1,
        "barrel_depth_mm": 3.0,
        "bottoming_tolerance_mm": 0.2,
        "window_fill_min": 0.8,
        "strand_count": 19,
        "max_stray_strands": 0,
        "max_seating_error_deg": 2.0,
    },
    "M39029-20": {
        "gap_min_mm": 0.4,
        "gap_max_mm": 1.3,
        "barrel_depth_mm": 3.6,
        "bottoming_tolerance_mm": 0.2,
        "window_fill_min": 0.8,
        "strand_count": 19,
        "max_stray_strands": 1,
        "max_seating_error_deg": 2.0,
    },
}

GOOD = {
    "identifier": "P-001",
    "contact": "M39029-22",
    "gap_mm": 0.7,
    "insertion_depth_mm": 3.0,
    "exposed_length_mm": 4.2,
    "window_present": True,
    "window_fill": 1.0,
    "strands_in_barrel": 19,
    "strands_outside": 0,
    "insulation_under_conductor_grip": False,
    "conductor_under_insulation_grip": True,
    "seating_error_deg": 0.0,
    "seated_in_nest": True,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD)
    case.update(overrides)
    return case


def _entry(part="M39029-22"):
    return lookup_contact(validate_contact_table(TABLE), part)


class ContactTableTests(unittest.TestCase):
    def test_valid_table_normalises(self):
        table = validate_contact_table(TABLE)
        self.assertEqual(sorted(table), ["M39029-20", "M39029-22"])
        self.assertAlmostEqual(table["M39029-22"]["gap_max_mm"], 1.1, places=9)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_table({})

    def test_inverted_gap_band_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["gap_max_mm"] = 0.1
        with self.assertRaises(ValueError):
            validate_contact_table(bad)

    def test_bottoming_tolerance_swallowing_the_bore_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["bottoming_tolerance_mm"] = 3.0
        with self.assertRaises(ValueError):
            validate_contact_table(bad)

    def test_stray_allowance_reaching_strand_count_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["max_stray_strands"] = 19
        with self.assertRaises(ValueError):
            validate_contact_table(bad)

    def test_untabulated_contact_is_not_derived(self):
        with self.assertRaises(ValueError):
            lookup_contact(validate_contact_table(TABLE), "M39029-16")


class InsulationGapTests(unittest.TestCase):
    def test_gap_inside_band_accepts(self):
        result = evaluate_insulation_gap(0.7, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)

    def test_gap_exactly_on_the_minimum_is_in_band(self):
        # The same representation error that puts 0.1 + 0.2 above 0.3
        # reaches a gap measured off a converted scale.
        edge = 0.3 + (0.1 + 0.2 - 0.3)
        result = evaluate_insulation_gap(edge, _entry())
        self.assertFalse(result["below_minimum"])
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)

    def test_gap_exactly_on_the_maximum_is_in_band(self):
        result = evaluate_insulation_gap(1.1, _entry())
        self.assertFalse(result["above_maximum"])

    def test_tight_gap_is_reposition(self):
        result = evaluate_insulation_gap(0.05, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)
        self.assertTrue(any("under the conductor grip" in f for f in result["findings"]))

    def test_wide_gap_is_reposition(self):
        result = evaluate_insulation_gap(2.0, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)
        self.assertTrue(result["above_maximum"])

    def test_band_position_is_reported(self):
        result = evaluate_insulation_gap(0.7, _entry())
        self.assertAlmostEqual(result["band_position"], 0.5, places=9)

    def test_negative_gap_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_insulation_gap(-0.1, _entry())


class BottomingTests(unittest.TestCase):
    def test_bottomed_conductor_accepts(self):
        result = evaluate_bottoming(3.0, 4.2, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)
        self.assertTrue(result["bottomed"])

    def test_depth_exactly_on_the_required_value_counts_as_bottomed(self):
        entry = _entry()
        required = entry["barrel_depth_mm"] - entry["bottoming_tolerance_mm"]
        result = evaluate_bottoming(required, 4.2, entry)
        self.assertTrue(result["bottomed"])
        self.assertAlmostEqual(result["shortfall_mm"], 0.0, places=9)

    def test_short_insertion_with_enough_conductor_is_reposition(self):
        result = evaluate_bottoming(1.5, 4.2, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)
        self.assertAlmostEqual(result["shortfall_mm"], 1.3, places=9)

    def test_conductor_too_short_to_ever_bottom_is_reject(self):
        result = evaluate_bottoming(1.5, 1.8, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_REJECT)
        self.assertTrue(any("back to preparation" in f for f in result["findings"]))

    def test_insertion_deeper_than_the_exposed_conductor_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_bottoming(5.0, 4.2, _entry())

    def test_non_numeric_depth_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_bottoming("3 mm", 4.2, _entry())


class WindowFillTests(unittest.TestCase):
    def test_full_window_accepts(self):
        result = evaluate_window_fill(1.0, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)

    def test_fill_exactly_on_the_requirement_accepts(self):
        result = evaluate_window_fill(0.8, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)

    def test_part_filled_window_is_reposition(self):
        result = evaluate_window_fill(0.3, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)

    def test_contact_without_a_window_says_so(self):
        result = evaluate_window_fill(None, _entry(), window_present=False)
        self.assertIsNone(result["fill_fraction"])
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)
        self.assertTrue(any("no inspection window" in f for f in result["findings"]))

    def test_fill_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_window_fill(1.4, _entry())


class StrayStrandTests(unittest.TestCase):
    def test_every_strand_in_the_barrel_accepts(self):
        result = evaluate_stray_strands(19, 0, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)
        self.assertAlmostEqual(result["captured_fraction"], 1.0, places=9)

    def test_stray_above_a_zero_allowance_rejects(self):
        result = evaluate_stray_strands(18, 1, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_REJECT)

    def test_stray_within_allowance_is_reposition(self):
        result = evaluate_stray_strands(18, 1, _entry("M39029-20"))
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)

    def test_strand_bookkeeping_must_balance(self):
        with self.assertRaises(ValueError):
            evaluate_stray_strands(17, 1, _entry())

    def test_non_integer_stray_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_stray_strands(19, 0.0, _entry())


class EntrapmentAndSeatingTests(unittest.TestCase):
    def test_clean_grips_accept(self):
        result = evaluate_entrapment()
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)

    def test_insulation_under_the_conductor_grip_is_reposition(self):
        result = evaluate_entrapment(insulation_under_conductor_grip=True)
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)

    def test_insulation_grip_on_bare_conductor_is_reposition(self):
        result = evaluate_entrapment(conductor_under_insulation_grip=False)
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)

    def test_square_seating_accepts(self):
        result = evaluate_seating(0.5, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)
        self.assertTrue(result["square"])

    def test_seating_error_exactly_on_the_limit_is_square(self):
        result = evaluate_seating(2.0, _entry())
        self.assertTrue(result["square"])

    def test_off_axis_contact_is_reposition(self):
        result = evaluate_seating(5.0, _entry())
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)

    def test_unseated_contact_is_reposition(self):
        result = evaluate_seating(0.0, _entry(), seated_in_nest=False)
        self.assertEqual(result["disposition"], PLACEMENT_REPOSITION)

    def test_non_boolean_seated_flag_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_seating(0.0, _entry(), seated_in_nest="yes")


class PlacementTests(unittest.TestCase):
    def test_good_placement_accepts(self):
        result = assess_placement(_case(), TABLE)
        self.assertEqual(result["disposition"], PLACEMENT_ACCEPT)
        self.assertEqual(result["driving_checks"], [])

    def test_reject_outranks_reposition(self):
        result = assess_placement(_case(gap_mm=2.0, strands_outside=1, strands_in_barrel=18), TABLE)
        self.assertEqual(result["disposition"], PLACEMENT_REJECT)
        self.assertEqual(result["driving_checks"], ["stray_strands"])

    def test_two_checks_at_the_worst_level_are_both_named(self):
        result = assess_placement(_case(gap_mm=2.0, window_fill=0.2), TABLE)
        self.assertEqual(result["driving_checks"], ["insulation_gap", "window_fill"])

    def test_findings_are_prefixed_by_check(self):
        result = assess_placement(_case(gap_mm=2.0), TABLE)
        self.assertTrue(any(f.startswith("insulation_gap:") for f in result["findings"]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_placement("a seated contact", TABLE)


class BatchTests(unittest.TestCase):
    def test_clean_batch_is_ready_to_crimp(self):
        batch = {"contact_table": TABLE, "placements": [_case(), _case(identifier="P-002")]}
        result = assess_placement_batch(batch)
        self.assertTrue(result["ready_to_crimp"])
        self.assertEqual(result["accepted"], 2)

    def test_unrecorded_placements_block_readiness(self):
        batch = {
            "contact_table": TABLE,
            "placements": [_case()],
            "declared_placement_count": 3,
        }
        result = assess_placement_batch(batch)
        self.assertFalse(result["ready_to_crimp"])
        self.assertEqual(result["unrecorded_placement_count"], 2)

    def test_not_accepted_placements_are_named(self):
        batch = {
            "contact_table": TABLE,
            "placements": [_case(), _case(identifier="P-007", gap_mm=2.4)],
        }
        result = assess_placement_batch(batch)
        self.assertEqual(result["not_accepted"], ["P-007"])
        self.assertEqual(result["reposition"], 1)

    def test_more_records_than_declared_rejected(self):
        batch = {
            "contact_table": TABLE,
            "placements": [_case(), _case()],
            "declared_placement_count": 1,
        }
        with self.assertRaises(ValueError):
            assess_placement_batch(batch)

    def test_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            assess_placement_batch({"contact_table": TABLE, "placements": []})


if __name__ == "__main__":
    unittest.main()
