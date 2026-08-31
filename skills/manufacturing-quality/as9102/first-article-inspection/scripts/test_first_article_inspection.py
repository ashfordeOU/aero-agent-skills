#!/usr/bin/env python3
"""Gate 3 contract test: AS9102 first article inspection.

Exercises scripts/first_article_inspection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 — an FAI is
complete only when forms 1, 2, and 3 are present and acceptable and
all nonconformances are closed (missing elements listed); delta FAI
is required when a change matches a trigger keyword; characteristic
accountability passes when the measured count covers the total;
invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import first_article_inspection_logic as fai  # noqa: E402


class FormNamesTest(unittest.TestCase):
    def test_form_names(self):
        self.assertEqual(
            fai.FORM_NAMES,
            {
                1: "part accountability",
                2: "material and special processes",
                3: "characteristic accountability",
            },
        )


class CompletenessTest(unittest.TestCase):
    def test_all_forms_ok_complete(self):
        self.assertEqual(
            fai.completeness({1, 2, 3}, True, True, True, True), (True, [])
        )

    def test_list_input_accepted(self):
        self.assertEqual(
            fai.completeness([1, 2, 3], True, True, True, True), (True, [])
        )

    def test_missing_form_2(self):
        complete, missing = fai.completeness({1, 3}, True, True, True, True)
        self.assertFalse(complete)
        self.assertIn("missing form 2", missing)

    def test_form_1_not_ok(self):
        complete, missing = fai.completeness({1, 2, 3}, False, True, True, True)
        self.assertFalse(complete)
        self.assertIn("form 1 not ok", missing)

    def test_open_nonconformances(self):
        complete, missing = fai.completeness({1, 2, 3}, True, True, True, False)
        self.assertFalse(complete)
        self.assertIn("open nonconformances", missing)


class StatusTest(unittest.TestCase):
    def test_status_complete(self):
        self.assertEqual(
            fai.fai_status({1, 2, 3}, True, True, True, True), "complete"
        )

    def test_status_not_complete(self):
        self.assertEqual(
            fai.fai_status({1, 2}, True, True, True, True), "not complete"
        )


class DeltaFaiTest(unittest.TestCase):
    def test_design_change_triggers(self):
        self.assertTrue(fai.delta_fai_required(["design change"]))

    def test_full_trigger_phrase_triggers(self):
        self.assertTrue(
            fai.delta_fai_required(["design change affecting form fit or function"])
        )

    def test_manufacturing_source_change_triggers(self):
        self.assertTrue(fai.delta_fai_required(["manufacturing source change"]))

    def test_two_year_lapse_triggers(self):
        self.assertTrue(fai.delta_fai_required(["two year lapse"]))

    def test_unrelated_change_does_not_trigger(self):
        self.assertFalse(fai.delta_fai_required(["unrelated change"]))

    def test_empty_change_list_does_not_trigger(self):
        self.assertFalse(fai.delta_fai_required([]))


class AccountingTest(unittest.TestCase):
    def test_measured_equals_total_passes(self):
        self.assertTrue(fai.characteristics_accounted(50, 50))

    def test_measured_above_total_passes(self):
        self.assertTrue(fai.characteristics_accounted(51, 50))

    def test_measured_below_total_fails(self):
        self.assertFalse(fai.characteristics_accounted(49, 50))

    def test_zero_total_raises(self):
        with self.assertRaises(ValueError):
            fai.characteristics_accounted(0, 0)

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            fai.characteristics_accounted(-1, 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
