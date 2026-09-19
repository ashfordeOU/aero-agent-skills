#!/usr/bin/env python3
"""Contract test for finished-crimp dimensional and visual acceptance (offline)."""

import copy
import unittest

from q7026_crimp_inspection_logic import (
    INSPECTION_ACCEPT,
    INSPECTION_REJECT,
    INSPECTION_REVIEW,
    evaluate_bell_mouth,
    evaluate_crimp_height,
    evaluate_crimp_width,
    evaluate_flash,
    evaluate_insulation_grip,
    evaluate_strand_visibility,
    inspect_crimp,
    lookup_limits,
    summarize_inspection,
    validate_limits_table,
)

TABLE = {
    "M39029-22": {
        "height_min_mm": 1.24,
        "height_max_mm": 1.36,
        "width_min_mm": 1.60,
        "width_max_mm": 1.80,
        "max_flash_mm": 0.08,
        "bell_mouth_required": True,
        "bell_mouth_min_mm": 0.10,
        "bell_mouth_max_mm": 0.40,
        "strand_count": 19,
    },
    "SPLICE-A": {
        "height_min_mm": 1.90,
        "height_max_mm": 2.10,
        "width_min_mm": 2.40,
        "width_max_mm": 2.70,
        "max_flash_mm": 0.10,
        "bell_mouth_required": False,
        "bell_mouth_min_mm": 0.10,
        "bell_mouth_max_mm": 0.40,
        "strand_count": 19,
    },
}

GOOD = {
    "identifier": "I-001",
    "contact": "M39029-22",
    "height_mm": 1.30,
    "width_mm": 1.70,
    "flash_mm": 0.02,
    "bell_mouth_present": True,
    "bell_mouth_mm": 0.25,
    "strands_visible": 19,
    "window_present": True,
    "insulation_grip_closed": True,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD)
    case.update(overrides)
    return case


def _entry(part="M39029-22"):
    return lookup_limits(validate_limits_table(TABLE), part)


class LimitsTableTests(unittest.TestCase):
    def test_valid_table_normalises(self):
        table = validate_limits_table(TABLE)
        self.assertEqual(sorted(table), ["M39029-22", "SPLICE-A"])
        self.assertAlmostEqual(table["M39029-22"]["height_max_mm"], 1.36, places=9)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits_table({})

    def test_inverted_height_band_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["height_max_mm"] = 1.0
        with self.assertRaises(ValueError):
            validate_limits_table(bad)

    def test_inverted_bell_mouth_band_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["bell_mouth_max_mm"] = 0.05
        with self.assertRaises(ValueError):
            validate_limits_table(bad)

    def test_zero_strand_count_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["strand_count"] = 0
        with self.assertRaises(ValueError):
            validate_limits_table(bad)

    def test_untabulated_contact_is_not_derived(self):
        with self.assertRaises(ValueError):
            lookup_limits(validate_limits_table(TABLE), "M39029-12")


class HeightAndWidthTests(unittest.TestCase):
    def test_height_inside_band_accepts(self):
        result = evaluate_crimp_height(1.30, _entry())
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)
        self.assertTrue(result["read"])

    def test_height_exactly_on_the_floor_is_in_band(self):
        # The representation error that puts 0.1 + 0.2 above 0.3 also
        # reaches a height converted from a dial reading.
        edge = 1.24 + (0.1 + 0.2 - 0.3)
        result = evaluate_crimp_height(edge, _entry())
        self.assertFalse(result["below_minimum"])
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)

    def test_height_exactly_on_the_ceiling_is_in_band(self):
        result = evaluate_crimp_height(1.36, _entry())
        self.assertFalse(result["above_maximum"])

    def test_height_below_the_floor_rejects(self):
        result = evaluate_crimp_height(1.05, _entry())
        self.assertEqual(result["disposition"], INSPECTION_REJECT)
        self.assertTrue(any("driven into the strands" in f for f in result["findings"]))

    def test_unmeasured_height_is_review_not_accept(self):
        result = evaluate_crimp_height(None, _entry())
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)
        self.assertFalse(result["read"])

    def test_width_outside_band_rejects(self):
        result = evaluate_crimp_width(2.20, _entry())
        self.assertEqual(result["disposition"], INSPECTION_REJECT)

    def test_unmeasured_width_is_review(self):
        result = evaluate_crimp_width(None, _entry())
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)

    def test_band_position_is_reported(self):
        result = evaluate_crimp_width(1.70, _entry())
        self.assertAlmostEqual(result["band_position"], 0.5, places=9)

    def test_zero_height_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_crimp_height(0.0, _entry())


class FlashTests(unittest.TestCase):
    def test_flash_within_limit_accepts(self):
        result = evaluate_flash(0.02, _entry())
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)

    def test_flash_exactly_on_the_limit_accepts(self):
        result = evaluate_flash(0.08, _entry())
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)

    def test_flash_over_the_limit_rejects(self):
        result = evaluate_flash(0.20, _entry())
        self.assertEqual(result["disposition"], INSPECTION_REJECT)

    def test_unmeasured_flash_is_review(self):
        result = evaluate_flash(None, _entry())
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)
        self.assertFalse(result["read"])

    def test_negative_flash_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_flash(-0.01, _entry())


class BellMouthTests(unittest.TestCase):
    def test_bell_mouth_inside_band_accepts(self):
        result = evaluate_bell_mouth(_entry(), present=True, length_mm=0.25)
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)

    def test_bell_mouth_exactly_on_the_minimum_accepts(self):
        result = evaluate_bell_mouth(_entry(), present=True, length_mm=0.10)
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)

    def test_absent_bell_mouth_rejects(self):
        result = evaluate_bell_mouth(_entry(), present=False)
        self.assertEqual(result["disposition"], INSPECTION_REJECT)
        self.assertTrue(any("sheared barrel edge" in f for f in result["findings"]))

    def test_over_long_bell_mouth_rejects(self):
        result = evaluate_bell_mouth(_entry(), present=True, length_mm=0.9)
        self.assertEqual(result["disposition"], INSPECTION_REJECT)

    def test_present_but_unmeasured_bell_mouth_is_review(self):
        result = evaluate_bell_mouth(_entry(), present=True, length_mm=None)
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)
        self.assertFalse(result["read"])

    def test_unread_bell_mouth_is_review(self):
        result = evaluate_bell_mouth(_entry(), present=None)
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)

    def test_contact_without_a_bell_mouth_requirement_accepts(self):
        result = evaluate_bell_mouth(_entry("SPLICE-A"), present=None)
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)
        self.assertFalse(result["required"])


class StrandVisibilityTests(unittest.TestCase):
    def test_every_strand_visible_accepts(self):
        result = evaluate_strand_visibility(_entry(), strands_visible=19)
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)
        self.assertAlmostEqual(result["visible_fraction"], 1.0, places=9)

    def test_missing_strands_reject_where_a_window_exists(self):
        result = evaluate_strand_visibility(_entry(), strands_visible=17)
        self.assertEqual(result["disposition"], INSPECTION_REJECT)
        self.assertEqual(result["missing"], 2)

    def test_missing_strands_without_a_window_are_review(self):
        result = evaluate_strand_visibility(
            _entry(), strands_visible=17, window_present=False
        )
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)

    def test_unread_visibility_is_review(self):
        result = evaluate_strand_visibility(_entry())
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)
        self.assertFalse(result["read"])

    def test_more_strands_than_the_contact_carries_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_strand_visibility(_entry(), strands_visible=25)

    def test_non_integer_strand_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_strand_visibility(_entry(), strands_visible=19.0)


class InsulationGripTests(unittest.TestCase):
    def test_grip_closed_on_insulation_accepts(self):
        self.assertEqual(
            evaluate_insulation_grip(True)["disposition"], INSPECTION_ACCEPT
        )

    def test_grip_not_closed_rejects(self):
        self.assertEqual(
            evaluate_insulation_grip(False)["disposition"], INSPECTION_REJECT
        )

    def test_unread_grip_is_review(self):
        result = evaluate_insulation_grip(None)
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)
        self.assertFalse(result["read"])


class InspectCrimpTests(unittest.TestCase):
    def test_fully_read_good_crimp_accepts(self):
        result = inspect_crimp(_case(), TABLE)
        self.assertEqual(result["disposition"], INSPECTION_ACCEPT)
        self.assertEqual(result["unread_characteristics"], [])

    def test_reject_outranks_review(self):
        result = inspect_crimp(_case(height_mm=1.05, flash_mm=None), TABLE)
        self.assertEqual(result["disposition"], INSPECTION_REJECT)
        self.assertEqual(result["driving_checks"], ["crimp_height"])

    def test_an_unread_characteristic_alone_blocks_acceptance(self):
        result = inspect_crimp(_case(width_mm=None), TABLE)
        self.assertEqual(result["disposition"], INSPECTION_REVIEW)
        self.assertEqual(result["unread_characteristics"], ["crimp_width"])

    def test_two_checks_at_the_worst_level_are_both_named(self):
        result = inspect_crimp(_case(height_mm=1.05, flash_mm=0.5), TABLE)
        self.assertEqual(result["driving_checks"], ["crimp_height", "flash"])

    def test_findings_are_prefixed_by_check(self):
        result = inspect_crimp(_case(flash_mm=0.5), TABLE)
        self.assertTrue(any(f.startswith("flash:") for f in result["findings"]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            inspect_crimp("a finished crimp", TABLE)


class SummaryTests(unittest.TestCase):
    def test_clean_population_rolls_up(self):
        lot = {"limits_table": TABLE, "crimps": [_case(), _case(identifier="I-002")]}
        result = summarize_inspection(lot)
        self.assertEqual(result["worst_disposition"], INSPECTION_ACCEPT)
        self.assertEqual(result["accepted"], 2)
        self.assertEqual(result["with_unread_characteristics"], [])

    def test_unread_characteristics_are_listed_by_identifier(self):
        lot = {
            "limits_table": TABLE,
            "crimps": [_case(), _case(identifier="I-009", bell_mouth_mm=None)],
        }
        result = summarize_inspection(lot)
        self.assertEqual(result["with_unread_characteristics"], ["I-009"])
        self.assertEqual(result["review"], 1)

    def test_uninspected_crimps_flag_the_record(self):
        lot = {"limits_table": TABLE, "crimps": [_case()], "declared_crimp_count": 6}
        result = summarize_inspection(lot)
        self.assertEqual(result["uninspected_crimp_count"], 5)
        self.assertFalse(result["record_complete"])

    def test_more_inspected_than_declared_rejected(self):
        lot = {
            "limits_table": TABLE,
            "crimps": [_case(), _case()],
            "declared_crimp_count": 1,
        }
        with self.assertRaises(ValueError):
            summarize_inspection(lot)

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            summarize_inspection({"limits_table": TABLE, "crimps": []})


if __name__ == "__main__":
    unittest.main()
