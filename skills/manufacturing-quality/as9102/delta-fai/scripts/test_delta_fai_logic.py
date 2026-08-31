#!/usr/bin/env python3
"""Gate 3 contract test: delta first article inspection.

Exercises scripts/delta_fai_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3: change classification
(part number or material -> full new FAI; process, tooling, drawing
revision, location, supplier -> delta FAI; none -> no FAI), delta FAI
scope (forms 1/2/3 per change type plus the affected characteristics
and a note), and the full-new-FAI convenience check; invalid inputs
raise ValueError. The physically meaningful invariant: every delta
scope keeps form 1 (part accountability) in scope.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import delta_fai_logic as dfl  # noqa: E402


class ClassifyTest(unittest.TestCase):
    def test_rule_table_happy_path(self):
        for ctype, rule in dfl.CHANGE_RULES.items():
            self.assertEqual(
                dfl.classify_change({"change_type": ctype}), rule, ctype
            )

    def test_part_number_and_material_are_full_new_fai(self):
        self.assertEqual(
            dfl.classify_change({"change_type": "part-number"}), "full-new-fai"
        )
        self.assertEqual(
            dfl.classify_change({"change_type": "material"}), "full-new-fai"
        )

    def test_delta_types_are_delta_fai(self):
        for ctype in sorted(dfl.DELTA_TYPES):
            self.assertEqual(
                dfl.classify_change({"change_type": ctype}), "delta-fai", ctype
            )

    def test_none_is_no_fai(self):
        self.assertEqual(dfl.classify_change({"change_type": "none"}), "no-fai")

    def test_description_is_ignored_by_classification(self):
        change = {"change_type": "process", "description": "new broach"}
        self.assertEqual(dfl.classify_change(change), "delta-fai")

    def test_unknown_change_type_raises(self):
        with self.assertRaises(ValueError):
            dfl.classify_change({"change_type": "electrical"})

    def test_missing_change_type_raises(self):
        with self.assertRaises(ValueError):
            dfl.classify_change({})

    def test_non_dict_change_raises(self):
        with self.assertRaises(ValueError):
            dfl.classify_change("process")


class VerifyFullFaiTest(unittest.TestCase):
    def test_part_number_needs_full_new_fai(self):
        self.assertTrue(
            dfl.verify_full_fai_needed({"change_type": "part-number"})
        )

    def test_material_needs_full_new_fai(self):
        self.assertTrue(dfl.verify_full_fai_needed({"change_type": "material"}))

    def test_process_does_not_need_full_new_fai(self):
        self.assertFalse(dfl.verify_full_fai_needed({"change_type": "process"}))

    def test_none_does_not_need_full_new_fai(self):
        self.assertFalse(dfl.verify_full_fai_needed({"change_type": "none"}))

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            dfl.verify_full_fai_needed({"change_type": "electrical"})


class ScopeTest(unittest.TestCase):
    def test_process_scope_forms_1_and_2(self):
        result = dfl.scope_delta_fai(
            {"change_type": "process", "description": "new machining method"},
            ["hole diameter", "surface finish"],
        )
        self.assertEqual(result["forms"], [1, 2])
        self.assertEqual(
            result["characteristics"], ["hole diameter", "surface finish"]
        )
        self.assertIsInstance(result["note"], str)
        self.assertTrue(result["note"])

    def test_material_scope_forms_1_and_2_with_full_fai_note(self):
        result = dfl.scope_delta_fai(
            {"change_type": "material"}, ["hardness", "tensile strength"]
        )
        self.assertEqual(result["forms"], [1, 2])
        self.assertIn("full new FAI", result["note"])

    def test_tooling_scope_forms_1_and_3(self):
        result = dfl.scope_delta_fai(
            {"change_type": "tooling"}, ["bore diameter"]
        )
        self.assertEqual(result["forms"], [1, 3])

    def test_drawing_revision_scope_forms_1_and_3(self):
        result = dfl.scope_delta_fai(
            {"change_type": "drawing-revision"}, ["outer radius"]
        )
        self.assertEqual(result["forms"], [1, 3])

    def test_location_scope_form_1_only(self):
        result = dfl.scope_delta_fai(
            {"change_type": "location"}, ["wall thickness"]
        )
        self.assertEqual(result["forms"], [1])

    def test_supplier_scope_form_1_only(self):
        result = dfl.scope_delta_fai(
            {"change_type": "supplier"}, ["material grade"]
        )
        self.assertEqual(result["forms"], [1])

    def test_tuple_characteristics_accepted(self):
        result = dfl.scope_delta_fai(
            {"change_type": "supplier"}, ("material grade",)
        )
        self.assertEqual(result["characteristics"], ["material grade"])

    def test_empty_characteristics_ok(self):
        result = dfl.scope_delta_fai({"change_type": "location"}, [])
        self.assertEqual(result["characteristics"], [])
        self.assertEqual(result["forms"], [1])

    def test_characteristics_copied_not_shared(self):
        chars = ["a", "b"]
        result = dfl.scope_delta_fai({"change_type": "process"}, chars)
        chars.append("c")
        self.assertEqual(result["characteristics"], ["a", "b"])

    def test_part_number_has_no_delta_scope(self):
        with self.assertRaises(ValueError):
            dfl.scope_delta_fai({"change_type": "part-number"}, ["a"])

    def test_none_has_no_delta_scope(self):
        with self.assertRaises(ValueError):
            dfl.scope_delta_fai({"change_type": "none"}, ["a"])

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            dfl.scope_delta_fai({"change_type": "electrical"}, ["a"])

    def test_non_list_characteristics_raises(self):
        with self.assertRaises(ValueError):
            dfl.scope_delta_fai({"change_type": "process"}, "hole diameter")


class InvariantTest(unittest.TestCase):
    def test_form_1_in_every_delta_scope(self):
        """Physically meaningful invariant: part accountability (form 1)
        stays in scope for every delta FAI, because the changed article
        must still be identified on form 1."""
        for ctype in dfl.FORM_SCOPE:
            result = dfl.scope_delta_fai({"change_type": ctype}, ["x"])
            self.assertIn(1, result["forms"], ctype)

    def test_every_delta_rule_has_a_scope(self):
        self.assertEqual(set(dfl.FORM_SCOPE.keys()), set(dfl.DELTA_TYPES) | {"material"})

    def test_full_fai_types_have_no_scope(self):
        for ctype in ("part-number", "none"):
            self.assertNotIn(ctype, dfl.FORM_SCOPE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
