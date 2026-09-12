#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-24C §5.8.3 EICD at space segment
element level.

Exercises scripts/e1024_eicd_element_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 — an interface type
is categorized as element_to_element or element_to_launcher and an
unrecognized type raises; required EICD fields that are absent or empty
are reported as missing; physical medium families with no characteristic
entry are reported as uncovered; characteristics carrying no linked
verification provision are reported as unlinked; and the aggregate EICD
review is compliant only when all four finding categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1024_eicd_element_logic as ei  # noqa: E402


def _minimal_compliant_eicd():
    """Return a minimal EICD dict that passes all §5.8.3 checks."""
    return {
        "interface_id": "IF-SAT-001",
        "interface_type": "element_to_element",
        "provider_element_id": "AOCS",
        "consumer_element_id": "THERMAL",
        "characteristics": [
            {"char_id": "C-MECH-01", "family": "mechanical"},
            {"char_id": "C-ELEC-01", "family": "electrical"},
            {"char_id": "C-THERM-01", "family": "thermal"},
            {"char_id": "C-DATA-01", "family": "data"},
            {"char_id": "C-RF-01", "family": "rf"},
        ],
        "requirement_refs": ["REQ-SAT-ICD-001"],
        "verification_provisions": [
            {"char_id": "C-MECH-01", "method": "test"},
            {"char_id": "C-ELEC-01", "method": "analysis"},
            {"char_id": "C-THERM-01", "method": "analysis"},
            {"char_id": "C-DATA-01", "method": "test"},
            {"char_id": "C-RF-01", "method": "inspection"},
        ],
        "required_families": {"mechanical", "electrical", "thermal", "data", "rf"},
    }


class CategorizeInterfaceTest(unittest.TestCase):
    def test_element_to_element_accepted(self):
        self.assertEqual(
            ei.categorize_interface("element_to_element"), "element_to_element"
        )

    def test_element_to_launcher_accepted(self):
        self.assertEqual(
            ei.categorize_interface("element_to_launcher"), "element_to_launcher"
        )

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            ei.categorize_interface("spacecraft_to_ground")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            ei.categorize_interface("")

    def test_none_raises(self):
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            ei.categorize_interface(None)


class EicdCompletenessTest(unittest.TestCase):
    def test_complete_eicd_no_missing_fields(self):
        eicd = _minimal_compliant_eicd()
        self.assertEqual(ei.check_eicd_completeness(eicd), [])

    def test_missing_interface_id_flagged(self):
        eicd = _minimal_compliant_eicd()
        del eicd["interface_id"]
        self.assertIn("interface_id", ei.check_eicd_completeness(eicd))

    def test_empty_characteristics_flagged(self):
        eicd = _minimal_compliant_eicd()
        eicd["characteristics"] = []
        self.assertIn("characteristics", ei.check_eicd_completeness(eicd))

    def test_missing_requirement_refs_flagged(self):
        eicd = _minimal_compliant_eicd()
        eicd["requirement_refs"] = []
        self.assertIn("requirement_refs", ei.check_eicd_completeness(eicd))

    def test_missing_provider_element_id_flagged(self):
        eicd = _minimal_compliant_eicd()
        eicd["provider_element_id"] = ""
        self.assertIn("provider_element_id", ei.check_eicd_completeness(eicd))


class CharacteristicFamiliesTest(unittest.TestCase):
    def test_all_families_covered_returns_empty_set(self):
        chars = [
            {"char_id": "C-M", "family": "mechanical"},
            {"char_id": "C-E", "family": "electrical"},
            {"char_id": "C-T", "family": "thermal"},
            {"char_id": "C-D", "family": "data"},
            {"char_id": "C-R", "family": "rf"},
        ]
        uncovered = ei.check_characteristic_families(chars, {"mechanical", "electrical", "thermal", "data", "rf"})
        self.assertEqual(uncovered, set())

    def test_missing_thermal_family_flagged(self):
        chars = [
            {"char_id": "C-M", "family": "mechanical"},
            {"char_id": "C-E", "family": "electrical"},
        ]
        uncovered = ei.check_characteristic_families(chars, {"mechanical", "electrical", "thermal"})
        self.assertIn("thermal", uncovered)

    def test_empty_characteristics_all_families_uncovered(self):
        uncovered = ei.check_characteristic_families([], {"mechanical", "data"})
        self.assertEqual(uncovered, {"mechanical", "data"})

    def test_unknown_family_in_char_ignored(self):
        chars = [{"char_id": "C-X", "family": "acoustic"}]
        uncovered = ei.check_characteristic_families(chars, {"mechanical"})
        self.assertIn("mechanical", uncovered)


class VerificationLinkageTest(unittest.TestCase):
    def test_all_chars_linked_returns_empty_list(self):
        chars = [{"char_id": "C-01"}, {"char_id": "C-02"}]
        provisions = [{"char_id": "C-01", "method": "test"}, {"char_id": "C-02", "method": "analysis"}]
        self.assertEqual(ei.check_verification_linkage(chars, provisions), [])

    def test_unlinked_characteristic_flagged(self):
        chars = [{"char_id": "C-01"}, {"char_id": "C-02"}]
        provisions = [{"char_id": "C-01", "method": "test"}]
        unlinked = ei.check_verification_linkage(chars, provisions)
        self.assertIn("C-02", unlinked)

    def test_char_without_char_id_skipped(self):
        chars = [{"family": "mechanical"}]
        provisions = []
        self.assertEqual(ei.check_verification_linkage(chars, provisions), [])

    def test_provision_without_char_id_ignored(self):
        chars = [{"char_id": "C-01"}]
        provisions = [{"method": "test"}]
        unlinked = ei.check_verification_linkage(chars, provisions)
        self.assertIn("C-01", unlinked)


class EicdElementReviewTest(unittest.TestCase):
    def test_fully_compliant_review_all_empty(self):
        eicd = _minimal_compliant_eicd()
        review = ei.eicd_element_review(eicd)
        self.assertEqual(review["missing_fields"], [])
        self.assertFalse(review["uncategorized_type"])
        self.assertEqual(review["uncovered_families"], [])
        self.assertEqual(review["unlinked_characteristics"], [])
        self.assertTrue(ei.is_eicd_compliant(review))

    def test_bad_interface_type_flags_uncategorized(self):
        eicd = _minimal_compliant_eicd()
        eicd["interface_type"] = "ground_to_orbit"
        review = ei.eicd_element_review(eicd)
        self.assertTrue(review["uncategorized_type"])
        self.assertFalse(ei.is_eicd_compliant(review))

    def test_missing_field_surfaces_in_review(self):
        eicd = _minimal_compliant_eicd()
        del eicd["consumer_element_id"]
        review = ei.eicd_element_review(eicd)
        self.assertIn("consumer_element_id", review["missing_fields"])
        self.assertFalse(ei.is_eicd_compliant(review))

    def test_uncovered_family_surfaces_in_review(self):
        eicd = _minimal_compliant_eicd()
        eicd["characteristics"] = [c for c in eicd["characteristics"] if c["family"] != "rf"]
        eicd["verification_provisions"] = [vp for vp in eicd["verification_provisions"] if vp["char_id"] != "C-RF-01"]
        review = ei.eicd_element_review(eicd)
        self.assertIn("rf", review["uncovered_families"])
        self.assertFalse(ei.is_eicd_compliant(review))

    def test_element_to_launcher_type_accepted(self):
        eicd = _minimal_compliant_eicd()
        eicd["interface_type"] = "element_to_launcher"
        eicd["consumer_element_id"] = "LAUNCHER-LV"
        review = ei.eicd_element_review(eicd)
        self.assertFalse(review["uncategorized_type"])

    def test_is_eicd_compliant_false_on_unlinked_chars(self):
        eicd = _minimal_compliant_eicd()
        eicd["verification_provisions"] = [{"char_id": "C-MECH-01", "method": "test"}]
        review = ei.eicd_element_review(eicd)
        self.assertTrue(review["unlinked_characteristics"])
        self.assertFalse(ei.is_eicd_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
