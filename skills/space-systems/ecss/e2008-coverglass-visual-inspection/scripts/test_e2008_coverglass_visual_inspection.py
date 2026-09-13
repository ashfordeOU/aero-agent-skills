#!/usr/bin/env python3
"""Contract test for the coverglass visual inspection screen (offline)."""

import copy
import unittest

from e2008_coverglass_visual_inspection_logic import (
    ACCEPT,
    CLEAN,
    COVERGLASS_DEFECT_KINDS,
    DEFAULT_COVERGLASS_CRITERIA,
    INSPECTION_INCOMPLETE,
    REFER,
    REJECT,
    active_area_coverage,
    assess_defect,
    inspect_coverglass,
    inspect_coverglass_set,
    validate_coverglass_criteria,
)

MARGIN_MM = 1.0

BARE_COVERGLASS = {
    "coverglass_id": "CG-001",
    "cell_length_mm": 40.0,
    "cell_width_mm": 40.0,
    "coverglass_length_mm": 42.0,
    "coverglass_width_mm": 42.0,
    "offset_x_mm": 0.0,
    "offset_y_mm": 0.0,
    "defects": [],
}


def _coverglass(defects=None, **overrides):
    record = copy.deepcopy(BARE_COVERGLASS)
    record["defects"] = copy.deepcopy(defects) if defects else []
    record.update(overrides)
    return record


def _chip(**overrides):
    defect = {
        "id": "D1",
        "kind": "edge-chip",
        "inward_extent_mm": 0.4,
        "area_mm2": 0.3,
    }
    defect.update(overrides)
    return defect


def _assembly(records, declared=None, **overrides):
    assembly = {
        "assembly_id": "SCA-01",
        "declared_coverglass_count": declared if declared is not None else len(records),
        "coverglasses": records,
    }
    assembly.update(overrides)
    return assembly


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_coverglass_criteria(DEFAULT_COVERGLASS_CRITERIA),
            DEFAULT_COVERGLASS_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverglass_criteria("default")

    def test_missing_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_CRITERIA)
        del broken["max_scratch_width_mm"]
        with self.assertRaises(ValueError):
            validate_coverglass_criteria(broken)

    def test_chip_allowance_beyond_the_overhang_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_CRITERIA)
        broken["chip_inward_fraction_of_margin"] = 1.4
        with self.assertRaises(ValueError):
            validate_coverglass_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_CRITERIA)
        broken["cavity_review_factor"] = 0.5
        with self.assertRaises(ValueError):
            validate_coverglass_criteria(broken)

    def test_non_integer_defect_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_CRITERIA)
        broken["max_accepted_defects_per_coverglass"] = 2.5
        with self.assertRaises(ValueError):
            validate_coverglass_criteria(broken)


class CoverageTests(unittest.TestCase):
    def test_centred_coverglass_covers_the_whole_active_area(self):
        coverage = active_area_coverage(40.0, 40.0, 42.0, 42.0)
        self.assertAlmostEqual(coverage["exposed_area_mm2"], 0.0, places=9)
        self.assertAlmostEqual(coverage["edge_margin_mm"], 1.0, places=9)
        self.assertAlmostEqual(coverage["covered_area_mm2"], 1600.0, places=9)

    def test_offset_eats_the_margin_on_one_side(self):
        coverage = active_area_coverage(40.0, 40.0, 42.0, 42.0, offset_x_mm=0.5)
        self.assertAlmostEqual(coverage["edge_margin_mm"], 0.5, places=9)
        self.assertAlmostEqual(coverage["exposed_area_mm2"], 0.0, places=9)

    def test_offset_past_the_overhang_exposes_the_cell(self):
        coverage = active_area_coverage(40.0, 40.0, 42.0, 42.0, offset_x_mm=1.5)
        self.assertLess(coverage["edge_margin_mm"], 0.0)
        self.assertAlmostEqual(coverage["exposed_area_mm2"], 20.0, places=9)
        self.assertAlmostEqual(coverage["exposed_fraction"], 0.0125, places=9)

    def test_undersized_coverglass_exposes_two_strips(self):
        coverage = active_area_coverage(40.0, 40.0, 38.0, 42.0)
        self.assertAlmostEqual(coverage["covered_area_mm2"], 1520.0, places=9)
        self.assertAlmostEqual(coverage["exposed_fraction"], 0.05, places=9)

    def test_zero_cell_dimension_rejected(self):
        with self.assertRaises(ValueError):
            active_area_coverage(0.0, 40.0, 42.0, 42.0)

    def test_non_numeric_offset_rejected(self):
        with self.assertRaises(ValueError):
            active_area_coverage(40.0, 40.0, 42.0, 42.0, offset_x_mm="0.5 mm")


class DefectTests(unittest.TestCase):
    def test_every_kind_is_dispositionable(self):
        self.assertEqual(len(COVERGLASS_DEFECT_KINDS), 6)

    def test_chip_inside_the_allowance_is_accepted(self):
        result = assess_defect(_chip(inward_extent_mm=0.5), MARGIN_MM)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_chip_past_the_allowance_goes_to_review(self):
        result = assess_defect(_chip(inward_extent_mm=0.8), MARGIN_MM)
        self.assertEqual(result["disposition"], REFER)

    def test_chip_past_the_overhang_rejects(self):
        result = assess_defect(_chip(inward_extent_mm=1.2), MARGIN_MM)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(any("active area" in reason for reason in result["reasons"]))

    def test_any_chip_rejects_when_no_overhang_is_left(self):
        result = assess_defect(_chip(inward_extent_mm=0.05), -0.2)
        self.assertEqual(result["disposition"], REJECT)

    def test_chip_without_an_extent_rejected(self):
        defect = _chip()
        del defect["inward_extent_mm"]
        with self.assertRaises(ValueError):
            assess_defect(defect, MARGIN_MM)

    def test_crack_always_rejects(self):
        result = assess_defect(
            {"id": "D2", "kind": "crack", "area_mm2": 0.1}, MARGIN_MM
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_scratch_on_both_limits_is_accepted(self):
        result = assess_defect(
            {
                "id": "D3",
                "kind": "surface-scratch",
                "length_mm": 3.0,
                "width_mm": 0.05,
                "area_mm2": 0.15,
            },
            MARGIN_MM,
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_wide_scratch_rejects_before_length_is_considered(self):
        result = assess_defect(
            {
                "id": "D4",
                "kind": "surface-scratch",
                "length_mm": 1.0,
                "width_mm": 0.2,
                "area_mm2": 0.2,
            },
            MARGIN_MM,
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(any("stress raiser" in reason for reason in result["reasons"]))

    def test_long_narrow_scratch_goes_to_review(self):
        result = assess_defect(
            {
                "id": "D5",
                "kind": "surface-scratch",
                "length_mm": 5.0,
                "width_mm": 0.02,
                "area_mm2": 0.1,
            },
            MARGIN_MM,
        )
        self.assertEqual(result["disposition"], REFER)

    def test_inclusion_bands_run_accept_review_reject(self):
        small = assess_defect(
            {
                "id": "D6",
                "kind": "cavity-or-inclusion",
                "max_dimension_mm": 0.5,
                "area_mm2": 0.2,
            },
            MARGIN_MM,
        )
        mid = assess_defect(
            {
                "id": "D7",
                "kind": "cavity-or-inclusion",
                "max_dimension_mm": 1.0,
                "area_mm2": 0.8,
            },
            MARGIN_MM,
        )
        big = assess_defect(
            {
                "id": "D8",
                "kind": "cavity-or-inclusion",
                "max_dimension_mm": 1.4,
                "area_mm2": 1.5,
            },
            MARGIN_MM,
        )
        self.assertEqual(small["disposition"], ACCEPT)
        self.assertEqual(mid["disposition"], REFER)
        self.assertEqual(big["disposition"], REJECT)

    def test_blemish_on_the_review_limit_is_still_reviewable(self):
        result = assess_defect(
            {"id": "D9", "kind": "coating-blemish", "area_mm2": 6.0}, MARGIN_MM
        )
        self.assertEqual(result["disposition"], REFER)

    def test_removable_deposit_is_cleaned_and_reinspected(self):
        result = assess_defect(
            {
                "id": "D10",
                "kind": "surface-contamination",
                "removable": True,
                "area_mm2": 4.0,
            },
            MARGIN_MM,
        )
        self.assertEqual(result["disposition"], CLEAN)
        self.assertAlmostEqual(result["counted_area_mm2"], 0.0, places=9)

    def test_fixed_deposit_stays_in_the_optical_path(self):
        result = assess_defect(
            {
                "id": "D11",
                "kind": "surface-contamination",
                "removable": False,
                "area_mm2": 4.0,
            },
            MARGIN_MM,
        )
        self.assertEqual(result["disposition"], REFER)
        self.assertAlmostEqual(result["counted_area_mm2"], 4.0, places=9)

    def test_non_boolean_removability_rejected(self):
        with self.assertRaises(ValueError):
            assess_defect(
                {
                    "id": "D12",
                    "kind": "surface-contamination",
                    "removable": "yes",
                    "area_mm2": 1.0,
                },
                MARGIN_MM,
            )

    def test_unknown_defect_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_defect({"id": "D13", "kind": "smudge", "area_mm2": 1.0}, MARGIN_MM)

    def test_negative_defect_area_rejected(self):
        with self.assertRaises(ValueError):
            assess_defect(_chip(area_mm2=-1.0), MARGIN_MM)


class CoverglassScreenTests(unittest.TestCase):
    def test_clean_coverglass_is_accepted(self):
        result = inspect_coverglass(_coverglass())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["defect_area_fraction"], 0.0, places=9)

    def test_worst_defect_governs_the_coverglass(self):
        result = inspect_coverglass(
            _coverglass([_chip(id="D1"), _chip(id="D2", inward_extent_mm=1.4)])
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_exposed_active_area_rejects_the_coverglass(self):
        result = inspect_coverglass(_coverglass(offset_x_mm=1.5))
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("uncovered" in finding for finding in result["findings"]))

    def test_exposure_exactly_on_the_allowance_is_not_a_reject(self):
        result = inspect_coverglass(_coverglass(offset_x_mm=1.2))
        self.assertAlmostEqual(result["exposed_active_fraction"], 0.005, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_accepted_defects_still_add_up_to_a_review(self):
        defects = [
            _chip(id="D%d" % n, inward_extent_mm=0.4, area_mm2=5.0)
            for n in range(4)
        ]
        result = inspect_coverglass(_coverglass(defects))
        self.assertEqual(result["accepted_defect_count"], 4)
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(any("cumulative" in finding for finding in result["findings"]))

    def test_too_many_accepted_defects_go_to_review(self):
        defects = [
            _chip(id="D%d" % n, inward_extent_mm=0.2, area_mm2=0.1)
            for n in range(5)
        ]
        result = inspect_coverglass(_coverglass(defects))
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(any("allowed on one" in finding for finding in result["findings"]))

    def test_duplicate_defect_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass(_coverglass([_chip(id="D1"), _chip(id="D1")]))

    def test_defect_area_beyond_the_glass_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass(
                _coverglass([_chip(id="D1", inward_extent_mm=0.2, area_mm2=5000.0)])
            )

    def test_coverglass_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass(_coverglass(coverglass_id=" "))

    def test_non_list_defect_survey_rejected(self):
        record = _coverglass()
        record["defects"] = "none"
        with self.assertRaises(ValueError):
            inspect_coverglass(record)


class AssemblyScreenTests(unittest.TestCase):
    def test_every_coverglass_clean_closes_the_assembly(self):
        records = [_coverglass(coverglass_id="CG-%d" % n) for n in range(3)]
        result = inspect_coverglass_set(_assembly(records))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["not_accepted_ids"], [])
        self.assertEqual(result["disposition_counts"][ACCEPT], 3)

    def test_a_missing_record_blocks_closure_even_when_all_screened_pass(self):
        records = [_coverglass(coverglass_id="CG-%d" % n) for n in range(2)]
        result = inspect_coverglass_set(_assembly(records, declared=3))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertFalse(result["inspection_complete"])
        self.assertEqual(result["missing_record_count"], 1)
        self.assertTrue(any("every one" in finding for finding in result["findings"]))

    def test_one_bad_coverglass_names_itself(self):
        records = [
            _coverglass(coverglass_id="CG-0"),
            _coverglass(
                [_chip(id="D1", inward_extent_mm=1.4)], coverglass_id="CG-1"
            ),
        ]
        result = inspect_coverglass_set(_assembly(records))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["CG-1"])

    def test_more_records_than_declared_rejected(self):
        records = [_coverglass(coverglass_id="CG-%d" % n) for n in range(3)]
        with self.assertRaises(ValueError):
            inspect_coverglass_set(_assembly(records, declared=2))

    def test_duplicate_coverglass_ids_rejected(self):
        records = [_coverglass(coverglass_id="CG-0") for _ in range(2)]
        with self.assertRaises(ValueError):
            inspect_coverglass_set(_assembly(records))

    def test_non_integer_declared_count_rejected(self):
        records = [_coverglass(coverglass_id="CG-0")]
        with self.assertRaises(ValueError):
            inspect_coverglass_set(_assembly(records, declared="three"))

    def test_non_mapping_assembly_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_set("SCA-01")


if __name__ == "__main__":
    unittest.main()
