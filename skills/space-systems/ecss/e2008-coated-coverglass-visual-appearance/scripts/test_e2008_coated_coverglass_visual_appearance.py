#!/usr/bin/env python3
"""Contract test for the coated coverglass appearance screen (offline)."""

import copy
import unittest

from e2008_coated_coverglass_visual_appearance_logic import (
    ACCEPT,
    DEFAULT_APPEARANCE_ALLOWANCES,
    INSPECTION_INCOMPLETE,
    PINHOLE,
    REJECT,
    REWORK,
    SPATTER,
    VOID,
    active_aperture,
    assess_coated_coverglass,
    coating_uniformity_spread,
    defect_projected_area_mm2,
    inspect_coated_coverglass_appearance,
    screen_coated_defects,
    validate_appearance_allowances,
    validate_coated_area,
)

EVEN_READINGS = [95.0, 95.5, 96.0, 95.2, 95.8]


def _geometry(**overrides):
    record = {
        "coating_id": "AR-7",
        "coated_width_mm": 40.0,
        "coated_height_mm": 20.0,
        "edge_exclusion_mm": 0.5,
    }
    record.update(overrides)
    return record


def _unit_geometry(**overrides):
    """A face whose active aperture is exactly one square centimetre."""
    record = {
        "coating_id": "AR-7",
        "coated_width_mm": 12.0,
        "coated_height_mm": 12.0,
        "edge_exclusion_mm": 1.0,
    }
    record.update(overrides)
    return record


def _defect(category=PINHOLE, diameter_mm=0.05, distance_from_edge_mm=5.0):
    return {
        "category": category,
        "diameter_mm": diameter_mm,
        "distance_from_edge_mm": distance_from_edge_mm,
    }


def _coverglass(coverglass_id="CG-001", **overrides):
    record = {
        "coverglass_id": coverglass_id,
        "coating_id": "AR-7",
        "appearance_readings": list(EVEN_READINGS),
        "defects": [],
    }
    record.update(overrides)
    return record


def _lot(how_many, declared=None):
    return {
        "lot_id": "CGL-44",
        "declared_coverglass_count": declared if declared is not None else how_many,
        "coverglasses": [_coverglass("CG-%03d" % n) for n in range(1, how_many + 1)],
    }


class AllowanceValidationTests(unittest.TestCase):
    def test_default_allowances_validate(self):
        self.assertIs(
            validate_appearance_allowances(DEFAULT_APPEARANCE_ALLOWANCES),
            DEFAULT_APPEARANCE_ALLOWANCES,
        )

    def test_non_mapping_allowances_refused(self):
        with self.assertRaises(ValueError):
            validate_appearance_allowances(0.1)

    def test_missing_fraction_refused(self):
        broken = copy.deepcopy(DEFAULT_APPEARANCE_ALLOWANCES)
        del broken["max_obscured_area_fraction"]
        with self.assertRaises(ValueError):
            validate_appearance_allowances(broken)

    def test_spread_allowance_above_one_refused(self):
        broken = copy.deepcopy(DEFAULT_APPEARANCE_ALLOWANCES)
        broken["max_uniformity_spread"] = 1.4
        with self.assertRaises(ValueError):
            validate_appearance_allowances(broken)

    def test_non_positive_defect_diameter_allowance_refused(self):
        broken = copy.deepcopy(DEFAULT_APPEARANCE_ALLOWANCES)
        broken["max_defect_diameter_mm"] = 0.0
        with self.assertRaises(ValueError):
            validate_appearance_allowances(broken)

    def test_a_single_appearance_reading_refused(self):
        broken = copy.deepcopy(DEFAULT_APPEARANCE_ALLOWANCES)
        broken["min_appearance_readings"] = 1
        with self.assertRaises(ValueError):
            validate_appearance_allowances(broken)

    def test_rework_margin_below_one_refused(self):
        broken = copy.deepcopy(DEFAULT_APPEARANCE_ALLOWANCES)
        broken["rework_margin_factor"] = 0.5
        with self.assertRaises(ValueError):
            validate_appearance_allowances(broken)


class CoatedAreaTests(unittest.TestCase):
    def test_a_valid_geometry_returns_itself(self):
        geometry = _geometry()
        self.assertIs(validate_coated_area(geometry), geometry)

    def test_geometry_without_a_coating_id_refused(self):
        with self.assertRaises(ValueError):
            validate_coated_area(_geometry(coating_id="  "))

    def test_non_positive_coated_width_refused(self):
        with self.assertRaises(ValueError):
            validate_coated_area(_geometry(coated_width_mm=0.0))

    def test_negative_edge_exclusion_refused(self):
        with self.assertRaises(ValueError):
            validate_coated_area(_geometry(edge_exclusion_mm=-0.1))

    def test_an_exclusion_band_that_consumes_the_face_refused(self):
        with self.assertRaises(ValueError):
            validate_coated_area(_geometry(edge_exclusion_mm=10.0))

    def test_the_aperture_is_the_face_less_the_band_on_every_side(self):
        aperture = active_aperture(_geometry())
        self.assertAlmostEqual(aperture["active_width_mm"], 39.0, places=9)
        self.assertAlmostEqual(aperture["active_height_mm"], 19.0, places=9)
        self.assertAlmostEqual(aperture["active_area_mm2"], 741.0, places=9)
        self.assertAlmostEqual(aperture["coated_area_mm2"], 800.0, places=9)

    def test_the_unit_geometry_is_one_square_centimetre_of_aperture(self):
        aperture = active_aperture(_unit_geometry())
        self.assertAlmostEqual(aperture["active_area_mm2"], 100.0, places=9)


class UniformityTests(unittest.TestCase):
    def test_an_even_face_reads_a_small_spread(self):
        spread = coating_uniformity_spread(EVEN_READINGS)
        self.assertEqual(spread["reading_count"], 5)
        self.assertAlmostEqual(spread["mean"], 95.5, places=9)
        self.assertAlmostEqual(spread["spread"], 1.0 / 95.5, places=12)

    def test_a_short_sample_is_refused_rather_than_averaged(self):
        with self.assertRaises(ValueError):
            coating_uniformity_spread([95.0, 95.5])

    def test_readings_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            coating_uniformity_spread("95 95 96 95 96")

    def test_a_non_positive_reading_refused(self):
        with self.assertRaises(ValueError):
            coating_uniformity_spread([95.0, 95.5, 0.0, 95.2, 95.8])

    def test_a_boolean_reading_refused(self):
        with self.assertRaises(ValueError):
            coating_uniformity_spread([95.0, 95.5, True, 95.2, 95.8])

    def test_a_spread_that_lands_on_its_limit_is_still_even(self):
        readings = [95.0, 105.0, 100.0, 100.0, 100.0]
        spread = coating_uniformity_spread(readings)
        self.assertAlmostEqual(spread["mean"], 100.0, places=9)
        self.assertAlmostEqual(
            spread["spread"], DEFAULT_APPEARANCE_ALLOWANCES["max_uniformity_spread"],
            places=9,
        )
        result = assess_coated_coverglass(
            _coverglass(appearance_readings=readings), _geometry()
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_an_uneven_face_is_returned_for_rework(self):
        readings = [92.0, 108.0, 100.0, 100.0, 100.0]
        result = assess_coated_coverglass(
            _coverglass(appearance_readings=readings), _geometry()
        )
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(any("across the face" in f for f in result["findings"]))

    def test_a_badly_uneven_face_is_rejected(self):
        readings = [20.0, 130.0, 100.0, 100.0, 100.0]
        result = assess_coated_coverglass(
            _coverglass(appearance_readings=readings), _geometry()
        )
        self.assertEqual(result["verdict"], REJECT)


class DefectScreenTests(unittest.TestCase):
    def test_a_pinhole_projects_a_circle(self):
        area = defect_projected_area_mm2(_defect(PINHOLE, 0.2))
        self.assertAlmostEqual(area, 3.141592653589793 * 0.04 / 4.0, places=12)

    def test_an_unknown_defect_category_refused(self):
        with self.assertRaises(ValueError):
            defect_projected_area_mm2(_defect("smudge", 0.1))

    def test_a_defect_without_a_diameter_refused(self):
        with self.assertRaises(ValueError):
            defect_projected_area_mm2({"category": VOID})

    def test_a_non_mapping_defect_refused(self):
        with self.assertRaises(ValueError):
            defect_projected_area_mm2("pinhole")

    def test_defects_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            screen_coated_defects("two pinholes", _geometry())

    def test_the_three_categories_are_counted_apart(self):
        screen = screen_coated_defects(
            [_defect(PINHOLE), _defect(VOID), _defect(SPATTER), _defect(SPATTER)],
            _geometry(),
        )
        self.assertEqual(screen["category_counts"][PINHOLE], 1)
        self.assertEqual(screen["category_counts"][VOID], 1)
        self.assertEqual(screen["category_counts"][SPATTER], 2)
        self.assertEqual(screen["graded_count"], 4)

    def test_a_defect_in_the_edge_band_is_reported_not_graded(self):
        screen = screen_coated_defects(
            [_defect(PINHOLE, 0.05, 0.2), _defect(VOID, 0.05, 5.0)], _geometry()
        )
        self.assertEqual(screen["graded_count"], 1)
        self.assertEqual(screen["edge_band_count"], 1)
        self.assertEqual(screen["category_counts"][PINHOLE], 0)

    def test_a_defect_on_the_band_edge_is_inside_the_aperture(self):
        screen = screen_coated_defects(
            [_defect(SPATTER, 0.05, 0.5)], _geometry()
        )
        self.assertEqual(screen["graded_count"], 1)
        self.assertEqual(screen["edge_band_count"], 0)

    def test_the_density_is_taken_over_the_aperture_not_the_face(self):
        screen = screen_coated_defects(
            [_defect(PINHOLE), _defect(VOID)], _unit_geometry()
        )
        self.assertAlmostEqual(screen["defect_density_per_cm2"], 2.0, places=9)

    def test_a_density_that_lands_on_its_limit_is_accepted(self):
        record = _coverglass(defects=[_defect(PINHOLE), _defect(VOID)])
        result = assess_coated_coverglass(record, _unit_geometry())
        self.assertAlmostEqual(
            result["defects"]["defect_density_per_cm2"],
            DEFAULT_APPEARANCE_ALLOWANCES["max_defect_density_per_cm2"],
            places=9,
        )
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_crowded_aperture_is_returned_for_rework(self):
        record = _coverglass(defects=[_defect(SPATTER) for _ in range(3)])
        result = assess_coated_coverglass(record, _unit_geometry())
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(
            any("per square centimetre" in f for f in result["findings"])
        )

    def test_a_defect_that_lands_on_the_size_limit_is_accepted(self):
        limit = DEFAULT_APPEARANCE_ALLOWANCES["max_defect_diameter_mm"]
        record = _coverglass(defects=[_defect(VOID, limit)])
        result = assess_coated_coverglass(record, _geometry())
        self.assertAlmostEqual(result["defects"]["largest_diameter_mm"], limit, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_an_oversize_spatter_blob_is_rejected(self):
        record = _coverglass(defects=[_defect(SPATTER, 1.2)])
        result = assess_coated_coverglass(record, _geometry())
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("across, past the" in f for f in result["findings"]))

    def test_many_small_defects_fail_on_obscured_area_alone(self):
        allowances = copy.deepcopy(DEFAULT_APPEARANCE_ALLOWANCES)
        allowances["max_defect_density_per_cm2"] = 50.0
        record = _coverglass(defects=[_defect(PINHOLE, 0.2) for _ in range(16)])
        result = assess_coated_coverglass(record, _unit_geometry(), allowances)
        self.assertNotEqual(result["verdict"], ACCEPT)
        self.assertTrue(any("obscure" in f for f in result["findings"]))


class CoverglassAssessmentTests(unittest.TestCase):
    def test_a_clean_even_face_is_accepted(self):
        result = assess_coated_coverglass(_coverglass(), _geometry())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["appearance_sampled"])
        self.assertEqual(result["findings"], [])

    def test_a_face_coated_with_another_coating_refused(self):
        with self.assertRaises(ValueError):
            assess_coated_coverglass(_coverglass(coating_id="ITO-2"), _geometry())

    def test_a_record_without_an_id_refused(self):
        with self.assertRaises(ValueError):
            assess_coated_coverglass(_coverglass(coverglass_id=""), _geometry())

    def test_a_non_mapping_record_refused(self):
        with self.assertRaises(ValueError):
            assess_coated_coverglass("CG-001", _geometry())

    def test_an_unread_face_is_ungraded_rather_than_even(self):
        result = assess_coated_coverglass(
            _coverglass(appearance_readings=None), _geometry()
        )
        self.assertFalse(result["appearance_sampled"])
        self.assertIsNone(result["uniformity_spread"])
        self.assertTrue(
            any("no appearance sample" in f for f in result["findings"])
        )

    def test_an_unread_face_still_has_its_point_defects_graded(self):
        result = assess_coated_coverglass(
            _coverglass(appearance_readings=None, defects=[_defect(SPATTER, 1.2)]),
            _geometry(),
        )
        self.assertEqual(result["verdict"], REJECT)


class LotRollupTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted_and_complete(self):
        result = inspect_coated_coverglass_appearance(_lot(40), _geometry())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["affected_count"], 0)
        self.assertEqual(result["not_accepted_ids"], [])

    def test_one_bad_face_inside_the_lot_allowance_still_names_itself(self):
        lot = _lot(40)
        lot["coverglasses"][2]["defects"] = [_defect(SPATTER, 1.2)]
        result = inspect_coated_coverglass_appearance(lot, _geometry())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["CG-003"])
        self.assertEqual(result["affected_count"], 1)

    def test_too_many_affected_faces_take_the_lot_out(self):
        lot = _lot(20)
        for record in lot["coverglasses"][:6]:
            record["defects"] = [_defect(SPATTER, 1.2)]
        result = inspect_coated_coverglass_appearance(lot, _geometry())
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("lot allowance" in f or "rework margin" in f
                            for f in result["findings"]))

    def test_the_remaining_lot_allowance_is_reported(self):
        result = inspect_coated_coverglass_appearance(_lot(20), _geometry())
        self.assertAlmostEqual(result["affected_allowance"], 1.0, places=9)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 1.0, places=9)

    def test_an_unread_face_leaves_the_lot_open(self):
        lot = _lot(10)
        lot["coverglasses"][4]["appearance_readings"] = []
        result = inspect_coated_coverglass_appearance(lot, _geometry())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["unsampled_coverglass_ids"], ["CG-005"])
        self.assertFalse(result["inspection_complete"])

    def test_a_short_record_set_leaves_the_lot_open(self):
        result = inspect_coated_coverglass_appearance(_lot(8, declared=10), _geometry())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)
        self.assertTrue(any("wrong population" in f for f in result["findings"]))

    def test_more_records_than_declared_refused(self):
        with self.assertRaises(ValueError):
            inspect_coated_coverglass_appearance(_lot(6, declared=5), _geometry())

    def test_duplicate_coverglass_ids_refused(self):
        lot = _lot(4)
        lot["coverglasses"][3]["coverglass_id"] = "CG-001"
        with self.assertRaises(ValueError):
            inspect_coated_coverglass_appearance(lot, _geometry())

    def test_a_non_mapping_lot_refused(self):
        with self.assertRaises(ValueError):
            inspect_coated_coverglass_appearance("CGL-44", _geometry())

    def test_coverglasses_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            inspect_coated_coverglass_appearance(
                {
                    "lot_id": "CGL-44",
                    "declared_coverglass_count": 3,
                    "coverglasses": "three",
                },
                _geometry(),
            )

    def test_a_non_integer_declared_count_refused(self):
        lot = _lot(3)
        lot["declared_coverglass_count"] = "three"
        with self.assertRaises(ValueError):
            inspect_coated_coverglass_appearance(lot, _geometry())

    def test_the_report_carries_the_coating_it_answered_to(self):
        result = inspect_coated_coverglass_appearance(_lot(5), _geometry())
        self.assertEqual(result["coating_id"], "AR-7")
        self.assertEqual(result["declared_coverglass_count"], 5)
        self.assertEqual(result["inspected_count"], 5)


if __name__ == "__main__":
    unittest.main()
