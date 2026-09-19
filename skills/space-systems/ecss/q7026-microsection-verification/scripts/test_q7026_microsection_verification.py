#!/usr/bin/env python3
"""Contract test for crimp microsection examination (offline)."""

import copy
import unittest

from q7026_microsection_verification_logic import (
    COMPRESSION_IN_BAND,
    COMPRESSION_OVER,
    COMPRESSION_UNDER,
    MICRO_ACCEPT,
    MICRO_REJECT,
    MICRO_REVIEW,
    compression_ratio,
    evaluate_compression,
    evaluate_section_frequency,
    evaluate_section_plane,
    evaluate_strand_deformation,
    evaluate_voids,
    evaluate_wall_thinning,
    examine_microsection,
    lookup_microsection_limits,
    required_section_count,
    validate_microsection_limits,
    verify_microsection_programme,
)

TABLE = {
    "M39029-22": {
        "compression_ratio_min": 0.70,
        "compression_ratio_max": 0.85,
        "max_void_count": 2,
        "max_void_area_fraction": 0.02,
        "min_deformed_strand_fraction": 0.9,
        "min_wall_fraction": 0.6,
        "crimp_zone_min_mm": 0.8,
        "crimp_zone_max_mm": 2.4,
        "strand_count": 19,
    },
    "M39029-20": {
        "compression_ratio_min": 0.72,
        "compression_ratio_max": 0.88,
        "max_void_count": 3,
        "max_void_area_fraction": 0.03,
        "min_deformed_strand_fraction": 0.9,
        "min_wall_fraction": 0.6,
        "crimp_zone_min_mm": 1.0,
        "crimp_zone_max_mm": 2.8,
        "strand_count": 19,
    },
}

GOOD = {
    "identifier": "MS-001",
    "contact": "M39029-22",
    "plane_mm": 1.6,
    "deformed_area_mm2": 0.78,
    "undeformed_area_mm2": 1.00,
    "void_count": 1,
    "void_area_mm2": 0.004,
    "bore_area_mm2": 1.40,
    "deformed_strands": 19,
    "min_wall_mm": 0.18,
    "nominal_wall_mm": 0.25,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD)
    case.update(overrides)
    return case


def _entry(part="M39029-22"):
    return lookup_microsection_limits(validate_microsection_limits(TABLE), part)


class LimitsTableTests(unittest.TestCase):
    def test_valid_table_normalises(self):
        table = validate_microsection_limits(TABLE)
        self.assertEqual(sorted(table), ["M39029-20", "M39029-22"])
        self.assertAlmostEqual(table["M39029-22"]["compression_ratio_max"], 0.85, places=9)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_microsection_limits({})

    def test_inverted_compression_band_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["compression_ratio_max"] = 0.5
        with self.assertRaises(ValueError):
            validate_microsection_limits(bad)

    def test_compression_band_starting_at_zero_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["compression_ratio_min"] = 0.0
        with self.assertRaises(ValueError):
            validate_microsection_limits(bad)

    def test_zero_wall_limit_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["min_wall_fraction"] = 0.0
        with self.assertRaises(ValueError):
            validate_microsection_limits(bad)

    def test_crimp_zone_with_no_width_rejected(self):
        bad = copy.deepcopy(TABLE)
        bad["M39029-22"]["crimp_zone_max_mm"] = 0.8
        with self.assertRaises(ValueError):
            validate_microsection_limits(bad)

    def test_untabulated_contact_is_not_derived(self):
        with self.assertRaises(ValueError):
            lookup_microsection_limits(validate_microsection_limits(TABLE), "M39029-12")


class CompressionRatioTests(unittest.TestCase):
    def test_ratio_is_the_area_quotient(self):
        self.assertAlmostEqual(compression_ratio(0.78, 1.00), 0.78, places=9)

    def test_deformed_area_may_equal_the_undeformed_area(self):
        self.assertAlmostEqual(compression_ratio(1.00, 1.00), 1.0, places=9)

    def test_deformed_area_above_the_undeformed_area_rejected(self):
        with self.assertRaises(ValueError):
            compression_ratio(1.20, 1.00)

    def test_zero_undeformed_area_rejected(self):
        with self.assertRaises(ValueError):
            compression_ratio(0.78, 0.0)

    def test_ratio_inside_band_accepts(self):
        result = evaluate_compression(0.78, _entry())
        self.assertEqual(result["state"], COMPRESSION_IN_BAND)
        self.assertEqual(result["disposition"], MICRO_ACCEPT)

    def test_ratio_exactly_on_the_floor_is_in_band(self):
        # The area quotient routinely lands a few units in the last
        # place either side of a specified band edge.
        edge = 0.70 + (0.1 + 0.2 - 0.3)
        result = evaluate_compression(edge, _entry())
        self.assertEqual(result["state"], COMPRESSION_IN_BAND)

    def test_ratio_exactly_on_the_ceiling_is_in_band(self):
        result = evaluate_compression(0.85, _entry())
        self.assertEqual(result["state"], COMPRESSION_IN_BAND)

    def test_ratio_below_the_floor_is_over_compressed(self):
        result = evaluate_compression(0.55, _entry())
        self.assertEqual(result["state"], COMPRESSION_OVER)
        self.assertEqual(result["disposition"], MICRO_REJECT)

    def test_ratio_above_the_ceiling_is_under_compressed(self):
        result = evaluate_compression(0.95, _entry())
        self.assertEqual(result["state"], COMPRESSION_UNDER)

    def test_compression_percent_is_reported(self):
        result = evaluate_compression(0.78, _entry())
        self.assertAlmostEqual(result["compression_percent"], 22.0, places=9)

    def test_unread_ratio_is_review(self):
        result = evaluate_compression(None, _entry())
        self.assertEqual(result["disposition"], MICRO_REVIEW)
        self.assertFalse(result["read"])


class VoidTests(unittest.TestCase):
    def test_voids_within_both_allowances_accept(self):
        result = evaluate_voids(_entry(), void_count=1, void_area_mm2=0.004, bore_area_mm2=1.4)
        self.assertEqual(result["disposition"], MICRO_ACCEPT)

    def test_void_count_over_the_allowance_rejects(self):
        result = evaluate_voids(_entry(), void_count=5, void_area_mm2=0.004, bore_area_mm2=1.4)
        self.assertEqual(result["disposition"], MICRO_REJECT)

    def test_void_area_over_the_allowance_rejects(self):
        result = evaluate_voids(_entry(), void_count=1, void_area_mm2=0.2, bore_area_mm2=1.4)
        self.assertEqual(result["disposition"], MICRO_REJECT)

    def test_counted_but_unsized_voids_are_review(self):
        result = evaluate_voids(_entry(), void_count=1)
        self.assertEqual(result["disposition"], MICRO_REVIEW)

    def test_no_voids_and_no_sizing_still_accepts(self):
        result = evaluate_voids(_entry(), void_count=0)
        self.assertEqual(result["disposition"], MICRO_ACCEPT)

    def test_unread_voids_are_review(self):
        result = evaluate_voids(_entry())
        self.assertEqual(result["disposition"], MICRO_REVIEW)
        self.assertFalse(result["read"])

    def test_void_area_larger_than_the_bore_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_voids(_entry(), void_count=1, void_area_mm2=2.0, bore_area_mm2=1.4)


class StrandDeformationTests(unittest.TestCase):
    def test_every_strand_deformed_accepts(self):
        result = evaluate_strand_deformation(_entry(), deformed_strands=19)
        self.assertEqual(result["disposition"], MICRO_ACCEPT)
        self.assertAlmostEqual(result["deformed_fraction"], 1.0, places=9)

    def test_undeformed_core_rejects(self):
        result = evaluate_strand_deformation(_entry(), deformed_strands=12)
        self.assertEqual(result["disposition"], MICRO_REJECT)
        self.assertTrue(any("carry no weld" in f for f in result["findings"]))

    def test_unread_deformation_is_review(self):
        result = evaluate_strand_deformation(_entry())
        self.assertEqual(result["disposition"], MICRO_REVIEW)

    def test_more_deformed_strands_than_the_contact_carries_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_strand_deformation(_entry(), deformed_strands=25)


class WallThinningTests(unittest.TestCase):
    def test_wall_above_the_limit_accepts(self):
        result = evaluate_wall_thinning(_entry(), min_wall_mm=0.18, nominal_wall_mm=0.25)
        self.assertEqual(result["disposition"], MICRO_ACCEPT)

    def test_wall_exactly_on_the_limit_accepts(self):
        result = evaluate_wall_thinning(_entry(), min_wall_mm=0.15, nominal_wall_mm=0.25)
        self.assertEqual(result["disposition"], MICRO_ACCEPT)
        self.assertAlmostEqual(result["wall_fraction"], 0.6, places=9)

    def test_wall_below_the_limit_rejects(self):
        result = evaluate_wall_thinning(_entry(), min_wall_mm=0.10, nominal_wall_mm=0.25)
        self.assertEqual(result["disposition"], MICRO_REJECT)

    def test_unread_wall_is_review(self):
        result = evaluate_wall_thinning(_entry())
        self.assertEqual(result["disposition"], MICRO_REVIEW)

    def test_wall_thicker_than_nominal_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_wall_thinning(_entry(), min_wall_mm=0.40, nominal_wall_mm=0.25)


class SectionPlaneTests(unittest.TestCase):
    def test_plane_inside_the_zone_accepts(self):
        result = evaluate_section_plane(1.6, _entry())
        self.assertTrue(result["inside_zone"])
        self.assertEqual(result["disposition"], MICRO_ACCEPT)

    def test_plane_exactly_on_the_zone_edge_is_inside(self):
        result = evaluate_section_plane(0.8, _entry())
        self.assertTrue(result["inside_zone"])

    def test_plane_outside_the_zone_is_invalid_not_failing(self):
        result = evaluate_section_plane(3.5, _entry())
        self.assertFalse(result["inside_zone"])
        self.assertEqual(result["disposition"], MICRO_REVIEW)
        self.assertTrue(any("invalid rather than failing" in f for f in result["findings"]))

    def test_unrecorded_plane_is_review(self):
        result = evaluate_section_plane(None, _entry())
        self.assertEqual(result["disposition"], MICRO_REVIEW)
        self.assertFalse(result["read"])


class FrequencyTests(unittest.TestCase):
    def test_one_section_per_interval(self):
        self.assertEqual(required_section_count(100, 50), 2)

    def test_a_part_interval_still_needs_a_section(self):
        self.assertEqual(required_section_count(101, 50), 3)

    def test_setup_changes_add_sections(self):
        self.assertEqual(required_section_count(100, 50, setup_changes=2), 4)

    def test_sufficient_sections_accept(self):
        result = evaluate_section_frequency(100, 50, 2)
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["disposition"], MICRO_ACCEPT)

    def test_short_programme_is_review(self):
        result = evaluate_section_frequency(100, 50, 1, setup_changes=1)
        self.assertEqual(result["disposition"], MICRO_REVIEW)
        self.assertEqual(result["shortfall"], 2)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            required_section_count(100, 0)


class ExamineTests(unittest.TestCase):
    def test_good_section_accepts(self):
        result = examine_microsection(_case(), TABLE)
        self.assertEqual(result["disposition"], MICRO_ACCEPT)
        self.assertTrue(result["section_valid"])
        self.assertEqual(result["unread_characteristics"], [])

    def test_ratio_is_derived_from_the_areas(self):
        result = examine_microsection(_case(), TABLE)
        self.assertAlmostEqual(result["compression"]["ratio"], 0.78, places=9)

    def test_an_explicit_ratio_overrides_the_areas(self):
        result = examine_microsection(_case(compression_ratio=0.60), TABLE)
        self.assertEqual(result["compression"]["disposition"], MICRO_REJECT)

    def test_an_invalid_plane_suppresses_the_other_dispositions(self):
        result = examine_microsection(_case(plane_mm=3.5, compression_ratio=0.40), TABLE)
        self.assertFalse(result["section_valid"])
        self.assertEqual(result["disposition"], MICRO_REVIEW)
        self.assertEqual(result["driving_checks"], ["section_plane"])

    def test_unread_characteristics_are_listed(self):
        result = examine_microsection(_case(min_wall_mm=None), TABLE)
        self.assertEqual(result["unread_characteristics"], ["wall_thinning"])
        self.assertEqual(result["disposition"], MICRO_REVIEW)

    def test_findings_are_prefixed_by_check(self):
        result = examine_microsection(_case(compression_ratio=0.40), TABLE)
        self.assertTrue(any(f.startswith("compression:") for f in result["findings"]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            examine_microsection("a polished section", TABLE)


class ProgrammeTests(unittest.TestCase):
    def test_complete_programme_accepts(self):
        programme = {
            "limits_table": TABLE,
            "lot_size": 100,
            "section_interval": 50,
            "sections": [_case(), _case(identifier="MS-002")],
        }
        result = verify_microsection_programme(programme)
        self.assertEqual(result["disposition"], MICRO_ACCEPT)
        self.assertEqual(result["valid_section_count"], 2)

    def test_invalid_sections_do_not_count_toward_the_frequency(self):
        programme = {
            "limits_table": TABLE,
            "lot_size": 100,
            "section_interval": 50,
            "sections": [_case(), _case(identifier="MS-002", plane_mm=3.5)],
        }
        result = verify_microsection_programme(programme)
        self.assertEqual(result["invalid_section_count"], 1)
        self.assertFalse(result["frequency"]["sufficient"])
        self.assertEqual(result["disposition"], MICRO_REVIEW)

    def test_a_rejected_section_drives_the_programme(self):
        programme = {
            "limits_table": TABLE,
            "lot_size": 100,
            "section_interval": 50,
            "sections": [_case(), _case(identifier="MS-003", compression_ratio=0.40)],
        }
        result = verify_microsection_programme(programme)
        self.assertEqual(result["disposition"], MICRO_REJECT)
        self.assertEqual(result["not_accepted"], ["MS-003"])

    def test_compression_range_is_reported_over_valid_sections(self):
        programme = {
            "limits_table": TABLE,
            "lot_size": 100,
            "section_interval": 50,
            "sections": [_case(), _case(identifier="MS-002", compression_ratio=0.84)],
        }
        result = verify_microsection_programme(programme)
        self.assertAlmostEqual(result["min_compression_ratio"], 0.78, places=9)
        self.assertAlmostEqual(result["max_compression_ratio"], 0.84, places=9)

    def test_empty_programme_rejected(self):
        with self.assertRaises(ValueError):
            verify_microsection_programme(
                {"limits_table": TABLE, "lot_size": 10, "section_interval": 5, "sections": []}
            )

    def test_non_mapping_programme_rejected(self):
        with self.assertRaises(ValueError):
            verify_microsection_programme("a set of sections")


if __name__ == "__main__":
    unittest.main()
