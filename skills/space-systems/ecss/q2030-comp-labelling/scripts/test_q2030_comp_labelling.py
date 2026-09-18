#!/usr/bin/env python3
"""Contract test for the complementary labelling and marking leaf."""

import unittest

from q2030_comp_labelling_logic import (
    assess_label_set,
    character_height_adequate,
    durability_verdict,
    evaluate_label,
    find_duplicate_labels,
    minimum_character_height_mm,
    parse_label,
    placement_in_window,
    validate_label_content,
)

REQUIREMENTS = {
    "placement_window_mm": (10.0, 60.0),
    "required_abrasion_cycles": 10,
    "required_solvent_cycles": 3,
}


def good_label(**overrides):
    record = {
        "id": "L-1",
        "token": "ABC-W120-J7-004",
        "character_height_mm": 1.5,
        "view_distance_mm": 300.0,
        "distance_from_termination_mm": 25.0,
        "routed_through_bundle": True,
        "marked_both_ends": True,
        "abrasion_cycles_legible": 20,
        "solvent_cycles_legible": 5,
    }
    record.update(overrides)
    return record


class TestParseLabel(unittest.TestCase):
    def test_four_field_token_decomposes(self):
        fields = parse_label("ABC-W120-J7-004")
        self.assertEqual(fields["harness"], "W120")

    def test_every_field_is_returned(self):
        self.assertEqual(len(parse_label("ABC-W120-J7-004")), 4)

    def test_surrounding_whitespace_is_trimmed(self):
        self.assertEqual(parse_label("  ABC-W120-J7-004 ")["project"], "ABC")

    def test_token_with_too_few_fields_raises(self):
        with self.assertRaises(ValueError):
            parse_label("ABC-W120-J7")

    def test_token_with_too_many_fields_raises(self):
        with self.assertRaises(ValueError):
            parse_label("ABC-W120-J7-004-X")

    def test_empty_field_raises(self):
        with self.assertRaises(ValueError):
            parse_label("ABC--J7-004")

    def test_blank_token_raises(self):
        with self.assertRaises(ValueError):
            parse_label("   ")

    def test_non_string_token_raises(self):
        with self.assertRaises(ValueError):
            parse_label(120)


class TestValidateLabelContent(unittest.TestCase):
    def test_conforming_token_has_no_finding(self):
        self.assertEqual(validate_label_content("ABC-W120-J7-004")["findings"], [])

    def test_lowercase_project_code_is_a_finding(self):
        self.assertTrue(validate_label_content("abc-W120-J7-004")["findings"])

    def test_harness_field_without_its_prefix_is_a_finding(self):
        self.assertTrue(validate_label_content("ABC-120-J7-004")["findings"])

    def test_connector_field_with_a_wrong_prefix_is_a_finding(self):
        self.assertTrue(validate_label_content("ABC-W120-X7-004")["findings"])

    def test_non_numeric_serial_is_a_finding(self):
        self.assertTrue(validate_label_content("ABC-W120-J7-00A")["findings"])

    def test_plug_prefix_is_accepted(self):
        self.assertEqual(validate_label_content("ABC-W120-P7-004")["findings"], [])


class TestCharacterHeight(unittest.TestCase):
    def test_reference_distance_needs_the_reference_height(self):
        self.assertAlmostEqual(minimum_character_height_mm(300.0), 1.5, places=9)

    def test_double_distance_doubles_the_height(self):
        self.assertAlmostEqual(minimum_character_height_mm(600.0), 3.0, places=9)

    def test_half_distance_halves_the_height(self):
        self.assertAlmostEqual(minimum_character_height_mm(150.0), 0.75, places=9)

    def test_height_exactly_on_the_requirement_is_adequate(self):
        self.assertTrue(character_height_adequate(1.5, 300.0))

    def test_last_place_shortfall_is_still_adequate(self):
        self.assertTrue(character_height_adequate(1.5 - 1e-12, 300.0))

    def test_clearly_small_marking_is_not_adequate(self):
        self.assertFalse(character_height_adequate(0.8, 600.0))

    def test_zero_view_distance_raises(self):
        with self.assertRaises(ValueError):
            minimum_character_height_mm(0.0)


class TestPlacement(unittest.TestCase):
    def test_label_inside_the_window_passes(self):
        self.assertTrue(placement_in_window(25.0, (10.0, 60.0)))

    def test_label_on_the_lower_edge_passes(self):
        self.assertTrue(placement_in_window(10.0, (10.0, 60.0)))

    def test_label_on_the_upper_edge_passes(self):
        self.assertTrue(placement_in_window(60.0, (10.0, 60.0)))

    def test_label_crowding_the_termination_fails(self):
        self.assertFalse(placement_in_window(4.0, (10.0, 60.0)))

    def test_label_far_down_the_wire_fails(self):
        self.assertFalse(placement_in_window(200.0, (10.0, 60.0)))

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            placement_in_window(-1.0, (10.0, 60.0))

    def test_inverted_window_raises(self):
        with self.assertRaises(ValueError):
            placement_in_window(25.0, (60.0, 10.0))


class TestDurability(unittest.TestCase):
    def test_marking_beyond_both_requirements_is_durable(self):
        self.assertTrue(durability_verdict(20, 5, 10, 3)["durable"])

    def test_marking_exactly_on_both_requirements_is_durable(self):
        self.assertTrue(durability_verdict(10, 3, 10, 3)["durable"])

    def test_abrasion_shortfall_is_a_finding(self):
        verdict = durability_verdict(4, 5, 10, 3)
        self.assertFalse(verdict["durable"])
        self.assertEqual(verdict["abrasion_margin"], -6)

    def test_solvent_shortfall_is_a_finding(self):
        self.assertFalse(durability_verdict(20, 1, 10, 3)["durable"])

    def test_both_shortfalls_are_reported_separately(self):
        self.assertEqual(len(durability_verdict(1, 1, 10, 3)["findings"]), 2)

    def test_negative_cycle_count_raises(self):
        with self.assertRaises(ValueError):
            durability_verdict(-1, 5, 10, 3)

    def test_zero_requirement_raises(self):
        with self.assertRaises(ValueError):
            durability_verdict(20, 5, 0, 3)


class TestEvaluateLabel(unittest.TestCase):
    def test_conforming_label_has_no_finding(self):
        self.assertTrue(evaluate_label(good_label(), REQUIREMENTS)["conforming"])

    def test_malformed_token_is_a_finding(self):
        self.assertFalse(evaluate_label(good_label(token="abc-W120-J7-004"), REQUIREMENTS)["conforming"])

    def test_small_marking_at_a_long_read_distance_is_a_finding(self):
        record = good_label(character_height_mm=1.0, view_distance_mm=900.0)
        self.assertFalse(evaluate_label(record, REQUIREMENTS)["conforming"])

    def test_label_outside_the_placement_window_is_a_finding(self):
        self.assertFalse(evaluate_label(good_label(distance_from_termination_mm=3.0), REQUIREMENTS)["conforming"])

    def test_single_end_marking_of_a_bundled_wire_is_a_finding(self):
        self.assertFalse(evaluate_label(good_label(marked_both_ends=False), REQUIREMENTS)["conforming"])

    def test_unbundled_wire_need_not_be_marked_twice(self):
        record = good_label(routed_through_bundle=False, marked_both_ends=False)
        self.assertTrue(evaluate_label(record, REQUIREMENTS)["conforming"])

    def test_weak_durability_is_a_finding(self):
        self.assertFalse(evaluate_label(good_label(abrasion_cycles_legible=2), REQUIREMENTS)["conforming"])

    def test_missing_record_key_raises(self):
        record = good_label()
        del record["character_height_mm"]
        with self.assertRaises(ValueError):
            evaluate_label(record, REQUIREMENTS)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_label(good_label(id=" "), REQUIREMENTS)


class TestDuplicates(unittest.TestCase):
    def test_unique_tokens_report_no_duplicate(self):
        self.assertEqual(find_duplicate_labels(["A-1", "A-2"]), [])

    def test_repeated_token_is_reported(self):
        self.assertEqual(find_duplicate_labels(["A-1", "A-1", "A-2"]), ["A-1"])

    def test_whitespace_variants_count_as_the_same_token(self):
        self.assertEqual(find_duplicate_labels(["A-1", " A-1 "]), ["A-1"])

    def test_non_string_token_raises(self):
        with self.assertRaises(ValueError):
            find_duplicate_labels(["A-1", 2])


class TestAssessLabelSet(unittest.TestCase):
    def test_clean_set_is_compliant(self):
        report = assess_label_set(
            [good_label(id="L-1"), good_label(id="L-2", token="ABC-W120-J8-005")], REQUIREMENTS
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["conforming_count"], 2)

    def test_repeated_token_across_wires_fails_the_set(self):
        report = assess_label_set([good_label(id="L-1"), good_label(id="L-2")], REQUIREMENTS)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["duplicate_tokens"], ["ABC-W120-J7-004"])

    def test_one_bad_label_fails_the_set(self):
        report = assess_label_set(
            [good_label(id="L-1"), good_label(id="L-2", token="ABC-W120-J8-005", abrasion_cycles_legible=0)],
            REQUIREMENTS,
        )
        self.assertFalse(report["compliant"])

    def test_duplicate_record_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_label_set([good_label(id="L-1"), good_label(id="L-1", token="ABC-W120-J8-005")], REQUIREMENTS)

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_label_set([], REQUIREMENTS)

    def test_default_requirements_are_usable(self):
        self.assertTrue(assess_label_set([good_label()])["compliant"])


if __name__ == "__main__":
    unittest.main()
