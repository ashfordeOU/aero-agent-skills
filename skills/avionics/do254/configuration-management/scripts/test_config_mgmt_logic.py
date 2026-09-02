#!/usr/bin/env python3
"""Gate 3 contract test for DO-254 configuration management logic.

Exercises scripts/config_mgmt_logic.py: change class determination,
CM action mapping per class, and HCI line formatting. Stdlib
unittest only, offline. Run: python3 test_config_mgmt_logic.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config_mgmt_logic as cm


class ChangeClassTest(unittest.TestCase):
    def test_class1_functional_change(self):
        r = cm.change_class(
            {"hardware_class": "simple", "safety_effect": "none", "functional_change": True}
        )
        self.assertEqual(r["class"], 1)

    def test_class1_safety_effect_minor(self):
        r = cm.change_class(
            {"hardware_class": "simple", "safety_effect": "minor", "functional_change": False}
        )
        self.assertEqual(r["class"], 1)

    def test_class1_complex_hardware(self):
        r = cm.change_class(
            {"hardware_class": "complex", "safety_effect": "none", "functional_change": False}
        )
        self.assertEqual(r["class"], 1)

    def test_class2_all_benign(self):
        r = cm.change_class(
            {"hardware_class": "simple", "safety_effect": "none", "functional_change": False}
        )
        self.assertEqual(r["class"], 2)

    def test_class1_hazardous_safety_dominates(self):
        # Physically meaningful check: a hazardous safety effect forces
        # class 1 even on simple hardware with no functional change,
        # because safety significance drives full control in DO-254 CM.
        r = cm.change_class(
            {"hardware_class": "simple", "safety_effect": "hazardous", "functional_change": False}
        )
        self.assertEqual(r["class"], 1)

    def test_invalid_hardware_class_raises(self):
        with self.assertRaises(ValueError):
            cm.change_class(
                {"hardware_class": "medium", "safety_effect": "none", "functional_change": False}
            )

    def test_invalid_safety_effect_raises(self):
        with self.assertRaises(ValueError):
            cm.change_class(
                {"hardware_class": "simple", "safety_effect": "severe", "functional_change": False}
            )

    def test_non_bool_functional_change_raises(self):
        with self.assertRaises(ValueError):
            cm.change_class(
                {"hardware_class": "simple", "safety_effect": "none", "functional_change": "yes"}
            )

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            cm.change_class({"hardware_class": "simple", "safety_effect": "none"})


class CmActionsTest(unittest.TestCase):
    def test_class1_full_control_set(self):
        a = cm.cm_actions(1)
        self.assertTrue(a["baseline_update"])
        self.assertTrue(a["ecr_required"])
        self.assertTrue(a["reverification_required"])
        self.assertTrue(a["independent_review"])

    def test_class2_lighter_control_set(self):
        a = cm.cm_actions(2)
        self.assertTrue(a["baseline_update"])
        self.assertTrue(a["ecr_required"])
        self.assertFalse(a["reverification_required"])
        self.assertFalse(a["independent_review"])

    def test_class1_classification_maps_to_full_actions(self):
        # Consistency: a class-1 verdict from change_class always maps
        # to the full control set via cm_actions.
        r = cm.change_class(
            {"hardware_class": "complex", "safety_effect": "none", "functional_change": False}
        )
        a = cm.cm_actions(r["class"])
        self.assertTrue(a["reverification_required"])
        self.assertTrue(a["independent_review"])

    def test_invalid_class_raises(self):
        with self.assertRaises(ValueError):
            cm.cm_actions(3)


class HciEntryTest(unittest.TestCase):
    def test_entry_format(self):
        self.assertEqual(
            cm.hci_entry("AFDX switch", "rev C", "baseline 3.1"), "AFDX switch rev C baseline 3.1"
        )

    def test_whitespace_stripped(self):
        self.assertEqual(
            cm.hci_entry("  AFDX switch ", " rev C ", " baseline 3.1 "),
            "AFDX switch rev C baseline 3.1",
        )

    def test_empty_item_raises(self):
        with self.assertRaises(ValueError):
            cm.hci_entry("", "rev C", "baseline 3.1")

    def test_empty_revision_raises(self):
        with self.assertRaises(ValueError):
            cm.hci_entry("AFDX switch", "", "baseline 3.1")

    def test_empty_baseline_raises(self):
        with self.assertRaises(ValueError):
            cm.hci_entry("AFDX switch", "rev C", "")


if __name__ == "__main__":
    unittest.main()
