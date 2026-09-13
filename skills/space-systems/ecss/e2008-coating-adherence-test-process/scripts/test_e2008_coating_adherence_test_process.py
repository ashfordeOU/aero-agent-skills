"""Contract tests for the clause 6.4.3.9.2 coating adherence process logic."""

import unittest

from e2008_coating_adherence_test_process_logic import (
    DEFAULT_MAX_REMOVED_FRACTION,
    DEFAULT_UNTESTED_ALLOWANCE,
    SAMPLE_ACCEPTED,
    SAMPLE_COATING_REMOVED,
    SAMPLE_FACE_NOT_COVERED,
    SUBGROUP_ACCEPTED,
    SUBGROUP_REJECTED,
    SUBGROUP_UNDERSIZED,
    assess_sample_face,
    assess_subgroup_adherence,
    coverage_fraction,
    face_area,
    removed_fraction,
    union_area,
    validate_face,
    validate_zone,
    validate_zones,
    zone_area,
)

# A representative coverglass face: 40 mm by 60 mm, tiled exactly by 20 mm
# squares (six zones) or by 10 mm squares (twenty-four zones).
FACE = {"width_mm": 40.0, "height_mm": 60.0}
FACE_AREA_MM2 = 2400.0


def _zones(cols=2, rows=3, w=20.0, h=20.0, skip=(), removed=None):
    """Tile the face with applied zones, optionally skipping or damaging some."""
    removed = removed or {}
    zones = []
    for i in range(cols):
        for j in range(rows):
            if (i, j) in skip:
                continue
            zones.append(
                {
                    "x_mm": i * w,
                    "y_mm": j * h,
                    "width_mm": w,
                    "height_mm": h,
                    "removed_area_mm2": removed.get((i, j), 0.0),
                }
            )
    return zones


def _sample(sample_id="SCA-01", **overrides):
    sample = {
        "sample_id": sample_id,
        "face": dict(FACE),
        "applied_zones": _zones(),
    }
    sample.update(overrides)
    return sample


def _spec(count=4, **overrides):
    spec = {"samples": [_sample("SCA-%02d" % (i + 1)) for i in range(count)]}
    spec.update(overrides)
    return spec


class FaceValidationTests(unittest.TestCase):
    def test_face_is_normalized_to_floats(self):
        face = validate_face({"width_mm": 40, "height_mm": 60})
        self.assertAlmostEqual(face["width_mm"], 40.0, places=9)

    def test_face_area_is_the_product(self):
        self.assertAlmostEqual(face_area(FACE), FACE_AREA_MM2, places=9)

    def test_zero_dimension_face_rejected(self):
        with self.assertRaises(ValueError):
            validate_face({"width_mm": 0.0, "height_mm": 60.0})

    def test_missing_face_dimension_rejected(self):
        with self.assertRaises(ValueError):
            validate_face({"width_mm": 40.0})

    def test_non_mapping_face_rejected(self):
        with self.assertRaises(ValueError):
            validate_face([40.0, 60.0])


class ZoneValidationTests(unittest.TestCase):
    def test_zone_is_normalized_to_floats(self):
        zone = validate_zone(_zones()[0], 0, FACE)
        self.assertAlmostEqual(zone["width_mm"], 20.0, places=9)
        self.assertEqual(zone["index"], 0)

    def test_zone_running_off_the_width_rejected(self):
        zone = dict(_zones()[0], x_mm=30.0)
        with self.assertRaises(ValueError):
            validate_zone(zone, 0, FACE)

    def test_zone_running_off_the_height_rejected(self):
        zone = dict(_zones()[0], y_mm=50.0)
        with self.assertRaises(ValueError):
            validate_zone(zone, 0, FACE)

    def test_zone_ending_exactly_on_the_edge_is_accepted(self):
        zone = dict(_zones()[0], x_mm=20.0, y_mm=40.0)
        self.assertAlmostEqual(zone["x_mm"] + zone["width_mm"], FACE["width_mm"], places=9)
        self.assertIsInstance(validate_zone(zone, 0, FACE), dict)

    def test_negative_origin_rejected(self):
        zone = dict(_zones()[0], x_mm=-1.0)
        with self.assertRaises(ValueError):
            validate_zone(zone, 0, FACE)

    def test_zero_width_zone_rejected(self):
        zone = dict(_zones()[0], width_mm=0.0)
        with self.assertRaises(ValueError):
            validate_zone(zone, 0, FACE)

    def test_removed_area_above_the_zone_rejected(self):
        zone = dict(_zones()[0], removed_area_mm2=500.0)
        with self.assertRaises(ValueError):
            validate_zone(zone, 0, FACE)

    def test_removed_area_equal_to_the_zone_is_accepted(self):
        zone = dict(_zones()[0], removed_area_mm2=400.0)
        self.assertAlmostEqual(zone_area(zone), 400.0, places=9)
        self.assertIsInstance(validate_zone(zone, 0, FACE), dict)

    def test_negative_removed_area_rejected(self):
        zone = dict(_zones()[0], removed_area_mm2=-1.0)
        with self.assertRaises(ValueError):
            validate_zone(zone, 0, FACE)

    def test_empty_zone_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_zones([], FACE)

    def test_non_numeric_zone_field_rejected(self):
        zone = dict(_zones()[0], width_mm="20")
        with self.assertRaises(ValueError):
            validate_zone(zone, 0, FACE)


class CoverageTests(unittest.TestCase):
    def test_full_tiling_covers_the_whole_face(self):
        self.assertAlmostEqual(union_area(_zones(), FACE), FACE_AREA_MM2, places=9)
        self.assertAlmostEqual(coverage_fraction(_zones(), FACE), 1.0, places=9)

    def test_a_missing_tile_leaves_the_face_unread(self):
        zones = _zones(skip=((1, 2),))
        self.assertAlmostEqual(union_area(zones, FACE), 2000.0, places=9)

    def test_overlapping_applications_are_counted_once(self):
        zones = _zones() + [dict(_zones()[0])]
        self.assertAlmostEqual(union_area(zones, FACE), FACE_AREA_MM2, places=9)

    def test_a_single_zone_covers_its_own_area(self):
        self.assertAlmostEqual(union_area([_zones()[0]], FACE), 400.0, places=9)

    def test_partial_overlap_is_added_once(self):
        zones = [
            {"x_mm": 0.0, "y_mm": 0.0, "width_mm": 20.0, "height_mm": 20.0,
             "removed_area_mm2": 0.0},
            {"x_mm": 10.0, "y_mm": 0.0, "width_mm": 20.0, "height_mm": 20.0,
             "removed_area_mm2": 0.0},
        ]
        self.assertAlmostEqual(union_area(zones, FACE), 600.0, places=9)

    def test_fine_tiling_also_covers_the_whole_face(self):
        zones = _zones(cols=4, rows=6, w=10.0, h=10.0)
        self.assertEqual(len(zones), 24)
        self.assertAlmostEqual(coverage_fraction(zones, FACE), 1.0, places=9)

    def test_removed_fraction_is_relative_to_the_whole_face(self):
        zones = _zones(removed={(0, 0): 120.0})
        self.assertAlmostEqual(removed_fraction(zones, FACE), 0.05, places=9)

    def test_undamaged_face_removes_nothing(self):
        self.assertAlmostEqual(removed_fraction(_zones(), FACE), 0.0, places=9)


class SampleAssessmentTests(unittest.TestCase):
    def test_fully_covered_undamaged_sample_is_accepted(self):
        result = assess_sample_face(_sample())
        self.assertEqual(result["verdict"], SAMPLE_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_unread_corner_is_a_coverage_finding(self):
        result = assess_sample_face(_sample(applied_zones=_zones(skip=((1, 2),))))
        self.assertEqual(result["verdict"], SAMPLE_FACE_NOT_COVERED)
        self.assertAlmostEqual(result["untested_area_mm2"], 400.0, places=9)

    def test_coverage_landing_on_the_floor_is_accepted(self):
        # Eighteen of twenty-four fine tiles is exactly three quarters of the
        # face, which is exactly the floor a quarter allowance sets.
        skip = tuple((3, j) for j in range(6))
        zones = _zones(cols=4, rows=6, w=10.0, h=10.0, skip=skip)
        result = assess_sample_face(
            _sample(applied_zones=zones), 0, untested_allowance=0.25
        )
        self.assertAlmostEqual(result["coverage_fraction"], 0.75, places=9)
        self.assertAlmostEqual(result["coverage_floor"], 0.75, places=9)
        self.assertEqual(result["verdict"], SAMPLE_ACCEPTED)

    def test_removal_landing_on_the_limit_is_accepted(self):
        result = assess_sample_face(_sample(applied_zones=_zones(removed={(0, 0): 120.0})))
        self.assertAlmostEqual(result["removed_fraction"], DEFAULT_MAX_REMOVED_FRACTION,
                               places=9)
        self.assertEqual(result["verdict"], SAMPLE_ACCEPTED)

    def test_removal_over_the_limit_sentences_the_sample(self):
        result = assess_sample_face(_sample(applied_zones=_zones(removed={(0, 0): 240.0})))
        self.assertEqual(result["verdict"], SAMPLE_COATING_REMOVED)
        self.assertEqual(len(result["findings"]), 1)

    def test_coverage_shortfall_outranks_a_removal_shortfall(self):
        zones = _zones(skip=((1, 2),), removed={(0, 0): 240.0})
        result = assess_sample_face(_sample(applied_zones=zones))
        self.assertEqual(result["verdict"], SAMPLE_FACE_NOT_COVERED)
        self.assertEqual(len(result["findings"]), 2)

    def test_applied_area_exceeds_tested_area_when_zones_overlap(self):
        zones = _zones() + [dict(_zones()[0])]
        result = assess_sample_face(_sample(applied_zones=zones))
        self.assertAlmostEqual(result["applied_area_mm2"], 2800.0, places=9)
        self.assertAlmostEqual(result["tested_area_mm2"], FACE_AREA_MM2, places=9)

    def test_default_allowance_sets_the_floor(self):
        result = assess_sample_face(_sample())
        self.assertAlmostEqual(result["coverage_floor"],
                               1.0 - DEFAULT_UNTESTED_ALLOWANCE, places=9)

    def test_blank_sample_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_sample_face(_sample(sample_id="  "))

    def test_missing_zones_key_rejected(self):
        sample = _sample()
        del sample["applied_zones"]
        with self.assertRaises(ValueError):
            assess_sample_face(sample)

    def test_allowance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_sample_face(_sample(), 0, untested_allowance=1.0)

    def test_removal_limit_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_sample_face(_sample(), 0, max_removed_fraction=1.5)


class SubgroupAssessmentTests(unittest.TestCase):
    def test_nominal_subgroup_is_accepted(self):
        result = assess_subgroup_adherence(_spec())
        self.assertEqual(result["verdict"], SUBGROUP_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_one_unread_sample_holds_the_subgroup(self):
        spec = _spec()
        spec["samples"][2]["applied_zones"] = _zones(skip=((0, 1),))
        result = assess_subgroup_adherence(spec)
        self.assertEqual(result["verdict"], SUBGROUP_REJECTED)
        self.assertEqual(result["samples"][2]["verdict"], SAMPLE_FACE_NOT_COVERED)

    def test_undersized_subgroup_is_its_own_verdict(self):
        result = assess_subgroup_adherence(_spec(count=2))
        self.assertEqual(result["verdict"], SUBGROUP_UNDERSIZED)

    def test_declared_sample_floor_is_honoured(self):
        result = assess_subgroup_adherence(_spec(count=2, min_subgroup_samples=2))
        self.assertEqual(result["verdict"], SUBGROUP_ACCEPTED)

    def test_worst_sample_is_reported(self):
        spec = _spec()
        spec["samples"][1]["applied_zones"] = _zones(removed={(0, 0): 240.0})
        result = assess_subgroup_adherence(spec)
        self.assertAlmostEqual(result["worst_removed_fraction"], 0.1, places=9)
        self.assertAlmostEqual(result["worst_coverage_fraction"], 1.0, places=9)

    def test_duplicate_sample_id_rejected(self):
        spec = _spec()
        spec["samples"][1]["sample_id"] = spec["samples"][0]["sample_id"]
        with self.assertRaises(ValueError):
            assess_subgroup_adherence(spec)

    def test_declared_removal_limit_changes_the_sentence(self):
        spec = _spec(max_removed_fraction=0.2)
        spec["samples"][1]["applied_zones"] = _zones(removed={(0, 0): 240.0})
        result = assess_subgroup_adherence(spec)
        self.assertEqual(result["verdict"], SUBGROUP_ACCEPTED)

    def test_empty_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_adherence({"samples": []})

    def test_non_integer_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_adherence(_spec(min_subgroup_samples=2.5))

    def test_missing_samples_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_adherence({"min_subgroup_samples": 4})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_adherence(["samples"])


if __name__ == "__main__":
    unittest.main()
