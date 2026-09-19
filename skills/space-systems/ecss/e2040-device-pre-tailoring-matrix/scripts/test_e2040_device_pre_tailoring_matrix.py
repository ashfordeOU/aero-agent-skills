#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-pre-tailoring-matrix.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_pre_tailoring_matrix.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_pre_tailoring_matrix_logic import (  # noqa: E402
    APPLICABLE,
    MODIFIED,
    NOT_APPLICABLE,
    applicable_requirements,
    apply_tailoring,
    build_matrix,
    coverage_summary,
    empty_categories,
    evaluate_pre_tailoring_matrix,
    matrix_gaps,
    missing_modification_notes,
    normalize_categories,
    normalize_disposition,
    orphan_requirements,
    validate_requirement,
)

CATEGORIES = ["standard-device", "custom-device", "heritage-device"]


def row(req_id, standard, custom, heritage, notes=None):
    entry = {
        "id": req_id,
        "title": "requirement %s" % req_id,
        "dispositions": {
            "standard-device": standard,
            "custom-device": custom,
            "heritage-device": heritage,
        },
    }
    if notes:
        entry["notes"] = notes
    return entry


def base_spec():
    return {
        "categories": list(CATEGORIES),
        "requirements": [
            row("R-6.1", "applicable", "applicable", "applicable"),
            row("R-6.2", "applicable", "applicable", "not-applicable"),
            row(
                "R-6.3",
                "not-applicable",
                "modified",
                "not-applicable",
                notes={"custom-device": "reduced to a datasheet review"},
            ),
            row("R-6.4", "applicable", "applicable", "applicable"),
        ],
    }


def codes(result):
    return sorted(f["code"] for f in result["findings"])


class TestDispositionNormalisation(unittest.TestCase):
    def test_canonical_value_passes_through(self):
        self.assertEqual(normalize_disposition("applicable"), APPLICABLE)

    def test_short_form_folds(self):
        self.assertEqual(normalize_disposition("N/A"), NOT_APPLICABLE)

    def test_spacing_and_case_are_tolerated(self):
        self.assertEqual(normalize_disposition("  Not   Applicable "), NOT_APPLICABLE)

    def test_tailored_folds_to_modified(self):
        self.assertEqual(normalize_disposition("tailored"), MODIFIED)

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_disposition("maybe")

    def test_non_string_disposition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_disposition(1)


class TestCategories(unittest.TestCase):
    def test_declared_order_is_kept(self):
        self.assertEqual(normalize_categories(CATEGORIES), CATEGORIES)

    def test_names_are_trimmed(self):
        self.assertEqual(normalize_categories([" a ", "b"]), ["a", "b"])

    def test_duplicate_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_categories(["a", "a"])

    def test_empty_category_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_categories([])

    def test_blank_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_categories(["  "])


class TestRowValidation(unittest.TestCase):
    def test_a_good_row_resolves(self):
        req_id, title, cells, notes = validate_requirement(
            row("R-1", "applicable", "no", "m", notes={"heritage-device": "note"}),
            CATEGORIES,
        )
        self.assertEqual(req_id, "R-1")
        self.assertEqual(cells["custom-device"], NOT_APPLICABLE)
        self.assertEqual(cells["heritage-device"], MODIFIED)
        self.assertEqual(title, "requirement R-1")
        self.assertIn("heritage-device", notes)

    def test_row_naming_an_undeclared_category_rejected(self):
        bad = row("R-1", "applicable", "applicable", "applicable")
        bad["dispositions"]["mystery-device"] = "applicable"
        with self.assertRaises(ValueError):
            validate_requirement(bad, CATEGORIES)

    def test_row_without_an_id_rejected(self):
        bad = row("R-1", "applicable", "applicable", "applicable")
        del bad["id"]
        with self.assertRaises(ValueError):
            validate_requirement(bad, CATEGORIES)

    def test_unknown_row_key_rejected(self):
        bad = row("R-1", "applicable", "applicable", "applicable")
        bad["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_requirement(bad, CATEGORIES)

    def test_duplicate_row_id_rejected(self):
        with self.assertRaises(ValueError):
            build_matrix(
                CATEGORIES,
                [
                    row("R-1", "applicable", "applicable", "applicable"),
                    row("R-1", "applicable", "applicable", "applicable"),
                ],
            )

    def test_empty_requirement_list_rejected(self):
        with self.assertRaises(ValueError):
            build_matrix(CATEGORIES, [])


class TestMatrixReading(unittest.TestCase):
    def setUp(self):
        spec = base_spec()
        self.matrix = build_matrix(spec["categories"], spec["requirements"])

    def test_applicable_set_includes_modified_rows(self):
        self.assertEqual(
            applicable_requirements(self.matrix, "custom-device"),
            ["R-6.1", "R-6.2", "R-6.3", "R-6.4"],
        )

    def test_not_applicable_rows_are_dropped(self):
        self.assertEqual(
            applicable_requirements(self.matrix, "heritage-device"),
            ["R-6.1", "R-6.4"],
        )

    def test_unknown_category_rejected_on_read(self):
        with self.assertRaises(ValueError):
            applicable_requirements(self.matrix, "mystery-device")

    def test_coverage_fraction_is_reported(self):
        summary = coverage_summary(self.matrix)
        self.assertAlmostEqual(
            summary["heritage-device"]["applicable_fraction"], 0.5, places=12
        )

    def test_modified_cells_are_counted_separately(self):
        summary = coverage_summary(self.matrix)
        self.assertEqual(summary["custom-device"]["modified"], 1)

    def test_a_complete_matrix_has_no_gaps(self):
        self.assertEqual(matrix_gaps(self.matrix), [])

    def test_a_missing_cell_is_a_gap(self):
        spec = base_spec()
        del spec["requirements"][0]["dispositions"]["custom-device"]
        matrix = build_matrix(spec["categories"], spec["requirements"])
        self.assertEqual(matrix_gaps(matrix), [("R-6.1", "custom-device")])

    def test_modified_cell_needs_a_note(self):
        spec = base_spec()
        del spec["requirements"][2]["notes"]
        matrix = build_matrix(spec["categories"], spec["requirements"])
        self.assertEqual(missing_modification_notes(matrix), [("R-6.3", "custom-device")])

    def test_orphan_row_is_found(self):
        spec = base_spec()
        spec["requirements"].append(
            row("R-6.9", "not-applicable", "not-applicable", "not-applicable")
        )
        matrix = build_matrix(spec["categories"], spec["requirements"])
        self.assertEqual(orphan_requirements(matrix), ["R-6.9"])

    def test_empty_column_is_found(self):
        spec = base_spec()
        spec["categories"].append("ground-support-device")
        for entry in spec["requirements"]:
            entry["dispositions"]["ground-support-device"] = "not-applicable"
        matrix = build_matrix(spec["categories"], spec["requirements"])
        self.assertEqual(empty_categories(matrix), ["ground-support-device"])


class TestTailoringDelta(unittest.TestCase):
    def setUp(self):
        spec = base_spec()
        self.matrix = build_matrix(spec["categories"], spec["requirements"])

    def test_no_delta_leaves_the_baseline(self):
        delta = apply_tailoring(self.matrix, "heritage-device", [])
        self.assertEqual(delta["resulting_applicable"], ["R-6.1", "R-6.4"])
        self.assertEqual(delta["added"], [])
        self.assertEqual(delta["removed"], [])

    def test_a_justified_removal_is_recorded(self):
        delta = apply_tailoring(
            self.matrix,
            "heritage-device",
            [
                {
                    "requirement_id": "R-6.4",
                    "disposition": "not-applicable",
                    "justification": "covered by the heritage qualification file",
                }
            ],
        )
        self.assertEqual(delta["removed"], ["R-6.4"])
        self.assertEqual(delta["unjustified_removals"], [])

    def test_an_unjustified_removal_is_caught(self):
        delta = apply_tailoring(
            self.matrix,
            "heritage-device",
            [{"requirement_id": "R-6.4", "disposition": "not-applicable"}],
        )
        self.assertEqual(delta["unjustified_removals"], ["R-6.4"])

    def test_a_delta_can_add_a_requirement_back(self):
        delta = apply_tailoring(
            self.matrix,
            "heritage-device",
            [{"requirement_id": "R-6.2", "disposition": "applicable"}],
        )
        self.assertEqual(delta["added"], ["R-6.2"])

    def test_reduction_fraction_is_reported(self):
        delta = apply_tailoring(
            self.matrix,
            "heritage-device",
            [
                {
                    "requirement_id": "R-6.4",
                    "disposition": "n/a",
                    "justification": "heritage",
                }
            ],
        )
        self.assertAlmostEqual(delta["reduction_fraction"], 0.5, places=12)

    def test_delta_naming_an_unknown_requirement_rejected(self):
        with self.assertRaises(ValueError):
            apply_tailoring(
                self.matrix,
                "heritage-device",
                [{"requirement_id": "R-9.9", "disposition": "applicable"}],
            )

    def test_delta_with_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            apply_tailoring(
                self.matrix,
                "heritage-device",
                [
                    {
                        "requirement_id": "R-6.4",
                        "disposition": "applicable",
                        "reason": "x",
                    }
                ],
            )

    def test_non_list_delta_rejected(self):
        with self.assertRaises(ValueError):
            apply_tailoring(self.matrix, "heritage-device", {"R-6.4": "applicable"})


class TestEvaluateMatrix(unittest.TestCase):
    def test_a_complete_matrix_is_usable(self):
        result = evaluate_pre_tailoring_matrix(base_spec())
        self.assertTrue(result["usable"])
        self.assertEqual(result["findings"], [])

    def test_every_category_gets_an_applicable_set(self):
        result = evaluate_pre_tailoring_matrix(base_spec())
        self.assertEqual(sorted(result["applicable_by_category"]), sorted(CATEGORIES))

    def test_unset_cell_is_reported_not_read_as_not_applicable(self):
        spec = base_spec()
        del spec["requirements"][1]["dispositions"]["standard-device"]
        result = evaluate_pre_tailoring_matrix(spec)
        self.assertIn("matrix-cell-unset", codes(result))
        self.assertFalse(result["usable"])

    def test_modified_without_note_is_reported(self):
        spec = base_spec()
        del spec["requirements"][2]["notes"]
        result = evaluate_pre_tailoring_matrix(spec)
        self.assertIn("modified-cell-without-note", codes(result))

    def test_orphan_row_is_reported(self):
        spec = base_spec()
        spec["requirements"].append(row("R-6.9", "no", "no", "no"))
        result = evaluate_pre_tailoring_matrix(spec)
        self.assertIn("requirement-applicable-to-no-category", codes(result))

    def test_unjustified_removal_is_reported(self):
        spec = base_spec()
        spec["tailoring"] = {
            "standard-device": [
                {"requirement_id": "R-6.1", "disposition": "not-applicable"}
            ]
        }
        result = evaluate_pre_tailoring_matrix(spec)
        self.assertIn("unjustified-tailoring-removal", codes(result))

    def test_justified_removal_keeps_the_matrix_usable(self):
        spec = base_spec()
        spec["tailoring"] = {
            "standard-device": [
                {
                    "requirement_id": "R-6.1",
                    "disposition": "not-applicable",
                    "justification": "the device carries no such interface",
                }
            ]
        }
        result = evaluate_pre_tailoring_matrix(spec)
        self.assertTrue(result["usable"])
        self.assertEqual(
            result["tailoring_delta"]["standard-device"]["removed"], ["R-6.1"]
        )

    def test_tailoring_on_an_undeclared_category_rejected(self):
        spec = base_spec()
        spec["tailoring"] = {"mystery-device": []}
        with self.assertRaises(ValueError):
            evaluate_pre_tailoring_matrix(spec)

    def test_unknown_spec_key_rejected(self):
        spec = base_spec()
        spec["issue"] = "1"
        with self.assertRaises(ValueError):
            evaluate_pre_tailoring_matrix(spec)

    def test_missing_categories_rejected(self):
        spec = base_spec()
        del spec["categories"]
        with self.assertRaises(ValueError):
            evaluate_pre_tailoring_matrix(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pre_tailoring_matrix([("categories", CATEGORIES)])


if __name__ == "__main__":
    unittest.main()
