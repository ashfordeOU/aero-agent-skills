#!/usr/bin/env python3
"""Contract test for the bare cell antireflective coating limits (offline)."""

import copy
import unittest

from e2008_bare_cell_ar_coating_limits_logic import (
    ACCEPT,
    AR_COATING_DEFECT_KINDS,
    COATING_ACCEPTED,
    COATING_REFERRED,
    COATING_REJECTED,
    COATING_SPATTER,
    COATING_VOID,
    DEFAULT_AR_COATING_CRITERIA,
    REFER,
    REJECT,
    UNCOATED_PATCH,
    assess_ar_coating,
    assess_coating_defect,
    coatable_area,
    estimate_current_loss_fraction,
    validate_ar_coating_criteria,
)

GEOMETRY = {
    "cell_length_mm": 40.0,
    "cell_width_mm": 40.0,
    "contact_area_mm2": 100.0,
}

COATABLE_MM2 = 1500.0

RESOLVED = coatable_area(GEOMETRY)


def _patch(**overrides):
    defect = {
        "id": "P1",
        "kind": UNCOATED_PATCH,
        "area_mm2": 0.8,
        "max_dimension_mm": 1.5,
        "touches_cell_edge": False,
    }
    defect.update(overrides)
    return defect


def _void(**overrides):
    defect = {
        "id": "V1",
        "kind": COATING_VOID,
        "area_mm2": 0.1,
        "max_dimension_mm": 0.4,
        "touches_cell_edge": False,
    }
    defect.update(overrides)
    return defect


def _spatter(**overrides):
    defect = {
        "id": "S1",
        "kind": COATING_SPATTER,
        "area_mm2": 0.1,
        "max_dimension_mm": 0.5,
        "on_attachment_pad": False,
    }
    defect.update(overrides)
    return defect


def _cell(defects=None, **overrides):
    cell = {
        "cell_id": "BC-AR-001",
        "geometry": copy.deepcopy(GEOMETRY),
        "coating_defects": copy.deepcopy(defects) if defects else [],
    }
    cell.update(overrides)
    return cell


def _patch_run(total_area_mm2, each_mm2=1.0):
    """A run of individually acceptable patches summing to a target area."""
    defects = []
    remaining = total_area_mm2
    index = 0
    while remaining > 1e-9:
        area = each_mm2 if remaining >= each_mm2 else remaining
        defects.append(
            _patch(id="P%d" % index, area_mm2=area, max_dimension_mm=1.5)
        )
        remaining -= area
        index += 1
    return defects


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_ar_coating_criteria(DEFAULT_AR_COATING_CRITERIA),
            DEFAULT_AR_COATING_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_ar_coating_criteria("default")

    def test_missing_limit_rejected(self):
        broken = dict(DEFAULT_AR_COATING_CRITERIA)
        del broken["max_void_dimension_mm"]
        with self.assertRaises(ValueError):
            validate_ar_coating_criteria(broken)

    def test_fraction_above_one_rejected(self):
        broken = dict(DEFAULT_AR_COATING_CRITERIA, max_uncoated_area_fraction=1.5)
        with self.assertRaises(ValueError):
            validate_ar_coating_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = dict(DEFAULT_AR_COATING_CRITERIA, void_review_factor=0.5)
        with self.assertRaises(ValueError):
            validate_ar_coating_criteria(broken)

    def test_coating_that_does_not_lower_reflectance_rejected(self):
        broken = dict(
            DEFAULT_AR_COATING_CRITERIA,
            coated_reflectance=0.4,
            uncoated_reflectance=0.33,
        )
        with self.assertRaises(ValueError):
            validate_ar_coating_criteria(broken)

    def test_non_boolean_edge_policy_rejected(self):
        broken = dict(DEFAULT_AR_COATING_CRITERIA, edge_void_rejects="yes")
        with self.assertRaises(ValueError):
            validate_ar_coating_criteria(broken)


class CoatableAreaTests(unittest.TestCase):
    def test_contacts_are_removed_from_the_coatable_face(self):
        self.assertAlmostEqual(RESOLVED["cell_area_mm2"], 1600.0, places=9)
        self.assertAlmostEqual(RESOLVED["coatable_area_mm2"], COATABLE_MM2, places=9)

    def test_cell_with_no_contacts_is_entirely_coatable(self):
        resolved = coatable_area(dict(GEOMETRY, contact_area_mm2=0.0))
        self.assertAlmostEqual(resolved["coatable_area_mm2"], 1600.0, places=9)

    def test_contacts_covering_the_whole_face_rejected(self):
        with self.assertRaises(ValueError):
            coatable_area(dict(GEOMETRY, contact_area_mm2=1600.0))

    def test_negative_contact_area_rejected(self):
        with self.assertRaises(ValueError):
            coatable_area(dict(GEOMETRY, contact_area_mm2=-1.0))

    def test_non_mapping_geometry_rejected(self):
        with self.assertRaises(ValueError):
            coatable_area("40x40")


class OpticalArmTests(unittest.TestCase):
    def test_fully_coated_face_costs_nothing(self):
        self.assertAlmostEqual(estimate_current_loss_fraction(0.0), 0.0, places=12)

    def test_loss_at_the_area_ceiling_is_the_reflectance_step(self):
        self.assertAlmostEqual(
            estimate_current_loss_fraction(0.01), 0.0031632653061224, places=12
        )

    def test_loss_grows_with_the_uncoated_share(self):
        self.assertGreater(
            estimate_current_loss_fraction(0.02),
            estimate_current_loss_fraction(0.01) + 1e-6,
        )

    def test_loss_follows_the_declared_reflectance_step(self):
        gentle = dict(DEFAULT_AR_COATING_CRITERIA, uncoated_reflectance=0.10)
        self.assertGreater(
            estimate_current_loss_fraction(0.01),
            estimate_current_loss_fraction(0.01, gentle) + 1e-6,
        )

    def test_uncoated_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            estimate_current_loss_fraction(1.4)


class DefectDispositionTests(unittest.TestCase):
    def test_small_patch_accepted(self):
        result = assess_coating_defect(_patch(), RESOLVED)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_patch_exactly_on_the_limit_still_accepts(self):
        result = assess_coating_defect(_patch(area_mm2=1.0), RESOLVED)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_patch_in_the_review_band_is_referred(self):
        result = assess_coating_defect(
            _patch(area_mm2=1.5, max_dimension_mm=2.0), RESOLVED
        )
        self.assertEqual(result["disposition"], REFER)

    def test_large_patch_rejects(self):
        result = assess_coating_defect(
            _patch(area_mm2=3.0, max_dimension_mm=2.5), RESOLVED
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_small_void_accepted(self):
        result = assess_coating_defect(_void(), RESOLVED)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_void_is_graded_on_dimension_not_on_area(self):
        wide_thin = assess_coating_defect(
            _void(area_mm2=0.1, max_dimension_mm=0.8), RESOLVED
        )
        self.assertEqual(wide_thin["disposition"], REFER)

    def test_void_past_the_review_band_rejects(self):
        result = assess_coating_defect(
            _void(area_mm2=0.1, max_dimension_mm=1.2), RESOLVED
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_void_reaching_the_cell_edge_rejects(self):
        result = assess_coating_defect(_void(touches_cell_edge=True), RESOLVED)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(any("free edge" in reason for reason in result["reasons"]))

    def test_edge_void_policy_can_carry_it_to_review_instead(self):
        policy = dict(DEFAULT_AR_COATING_CRITERIA, edge_void_rejects=False)
        result = assess_coating_defect(_void(touches_cell_edge=True), RESOLVED, policy)
        self.assertEqual(result["disposition"], REFER)

    def test_spatter_away_from_a_pad_is_bounded_on_area(self):
        self.assertEqual(assess_coating_defect(_spatter(), RESOLVED)["disposition"], ACCEPT)
        referred = assess_coating_defect(
            _spatter(area_mm2=0.4, max_dimension_mm=0.9), RESOLVED
        )
        self.assertEqual(referred["disposition"], REFER)

    def test_large_spatter_rejects(self):
        result = assess_coating_defect(
            _spatter(area_mm2=0.7, max_dimension_mm=1.2), RESOLVED
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_spatter_on_an_attachment_pad_always_rejects(self):
        result = assess_coating_defect(
            _spatter(area_mm2=0.05, max_dimension_mm=0.3, on_attachment_pad=True),
            RESOLVED,
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_spatter_takes_no_coated_area_away(self):
        result = assess_coating_defect(_spatter(), RESOLVED)
        self.assertAlmostEqual(result["uncoated_area_mm2"], 0.0, places=9)
        self.assertAlmostEqual(result["spatter_area_mm2"], 0.1, places=9)

    def test_patch_takes_coated_area_away_and_adds_no_spatter(self):
        result = assess_coating_defect(_patch(), RESOLVED)
        self.assertAlmostEqual(result["uncoated_area_mm2"], 0.8, places=9)
        self.assertAlmostEqual(result["spatter_area_mm2"], 0.0, places=9)

    def test_unknown_defect_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_defect(_patch(kind="scratch"), RESOLVED)

    def test_area_that_cannot_fit_its_largest_dimension_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_defect(
                _patch(area_mm2=5.0, max_dimension_mm=1.0), RESOLVED
            )

    def test_defect_larger_than_the_coatable_face_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_defect(
                _patch(area_mm2=2000.0, max_dimension_mm=60.0), RESOLVED
            )

    def test_spatter_without_a_pad_flag_rejected(self):
        defect = _spatter()
        del defect["on_attachment_pad"]
        with self.assertRaises(ValueError):
            assess_coating_defect(defect, RESOLVED)

    def test_every_named_defect_kind_is_dispositionable(self):
        for kind in AR_COATING_DEFECT_KINDS:
            defect = {
                "id": kind,
                "kind": kind,
                "area_mm2": 0.1,
                "max_dimension_mm": 0.4,
                "touches_cell_edge": False,
                "on_attachment_pad": False,
            }
            result = assess_coating_defect(defect, RESOLVED)
            self.assertIn(result["disposition"], (ACCEPT, REFER, REJECT))


class CellRollupTests(unittest.TestCase):
    def test_clean_cell_is_accepted(self):
        result = assess_ar_coating(_cell([_patch(), _void(), _spatter()]))
        self.assertEqual(result["verdict"], COATING_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["not_accepted_ids"], [])

    def test_uncoated_fraction_is_taken_against_the_coatable_face(self):
        result = assess_ar_coating(_cell(_patch_run(10.0)))
        self.assertAlmostEqual(result["uncoated_area_mm2"], 10.0, places=9)
        self.assertAlmostEqual(
            result["uncoated_fraction"], 10.0 / COATABLE_MM2, places=12
        )
        self.assertEqual(result["verdict"], COATING_ACCEPTED)

    def test_optical_arm_catches_what_the_area_ceiling_passes(self):
        result = assess_ar_coating(_cell(_patch_run(13.5)))
        for defect in result["defects"]:
            self.assertEqual(defect["disposition"], ACCEPT)
        self.assertLess(
            result["uncoated_fraction"],
            DEFAULT_AR_COATING_CRITERIA["max_uncoated_area_fraction"],
        )
        self.assertGreater(
            result["estimated_current_loss_fraction"],
            DEFAULT_AR_COATING_CRITERIA["max_current_loss_fraction"],
        )
        self.assertEqual(result["verdict"], COATING_REFERRED)

    def test_area_ceiling_is_reported_in_its_own_words(self):
        result = assess_ar_coating(_cell(_patch_run(16.0)))
        self.assertTrue(any("no coating" in finding for finding in result["findings"]))
        self.assertEqual(result["verdict"], COATING_REFERRED)

    def test_worst_defect_sets_the_cell_verdict(self):
        result = assess_ar_coating(
            _cell([_patch(), _void(id="V2", touches_cell_edge=True)])
        )
        self.assertEqual(result["verdict"], COATING_REJECTED)
        self.assertEqual(result["not_accepted_ids"], ["V2"])

    def test_spatter_obscuration_allowance_is_enforced(self):
        criteria = dict(DEFAULT_AR_COATING_CRITERIA, max_spatter_area_fraction=1e-4)
        result = assess_ar_coating(
            _cell([_spatter(area_mm2=0.2, max_dimension_mm=0.6)]), criteria
        )
        self.assertEqual(result["defects"][0]["disposition"], ACCEPT)
        self.assertEqual(result["verdict"], COATING_REFERRED)

    def test_too_many_voids_on_one_cell_is_referred(self):
        voids = [_void(id="V%d" % index) for index in range(7)]
        result = assess_ar_coating(_cell(voids))
        self.assertEqual(result["defect_counts"][COATING_VOID], 7)
        self.assertEqual(result["verdict"], COATING_REFERRED)

    def test_too_many_spatter_spots_is_referred(self):
        spots = [_spatter(id="S%d" % index) for index in range(5)]
        result = assess_ar_coating(_cell(spots))
        self.assertEqual(result["defect_counts"][COATING_SPATTER], 5)
        self.assertEqual(result["verdict"], COATING_REFERRED)

    def test_defect_counts_separate_the_three_kinds(self):
        result = assess_ar_coating(_cell([_patch(), _void(), _spatter()]))
        self.assertEqual(
            result["defect_counts"],
            {UNCOATED_PATCH: 1, COATING_VOID: 1, COATING_SPATTER: 1},
        )

    def test_duplicate_defect_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_ar_coating(_cell([_patch(id="D"), _void(id="D")]))

    def test_cell_without_an_id_rejected(self):
        cell = _cell([_patch()])
        cell["cell_id"] = " "
        with self.assertRaises(ValueError):
            assess_ar_coating(cell)

    def test_non_list_defect_collection_rejected(self):
        cell = _cell()
        cell["coating_defects"] = _patch()
        with self.assertRaises(ValueError):
            assess_ar_coating(cell)

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_ar_coating("BC-AR-001")

    def test_input_is_not_mutated_by_the_screen(self):
        cell = _cell([_patch(), _void(), _spatter()])
        before = copy.deepcopy(cell)
        assess_ar_coating(cell)
        self.assertEqual(cell, before)


if __name__ == "__main__":
    unittest.main()
