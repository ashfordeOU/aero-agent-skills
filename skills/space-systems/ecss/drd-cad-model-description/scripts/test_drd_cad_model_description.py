#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C Annex A CAD model and drawing
description delivery validation.

Exercises scripts/drd_cad_model_description_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 — an accepted exchange
or native CAD format passes and an unrecognised format raises; a coordinate
system dict is valid when all four required fields are present with a
recognised handedness, and flags each missing or invalid field; a drawing
title block is valid when all six required fields are non-empty, and flags
each missing field; mass properties are valid when all seven fields are
present and the non-negative fields hold non-negative values, and flags
missing fields and negative values; a recognised maturity level passes and
an unrecognised level raises; an interface definition is valid when all
three required fields are present with a recognised type, and flags each
gap; the model tree check flags a component without an id and a component
whose id duplicates an earlier entry; the aggregate delivery review raises
on a bad format or bad maturity and returns per-category finding lists
otherwise; the delivery is compliant only when every category list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import drd_cad_model_description_logic as cad  # noqa: E402


def _valid_record():
    return {
        "model_format": "step_ap214",
        "coordinate_system": {
            "origin": [0.0, 0.0, 0.0],
            "x_axis": [1.0, 0.0, 0.0],
            "y_axis": [0.0, 1.0, 0.0],
            "handedness": "right",
        },
        "title_block": {
            "document_number": "STR-CAD-001",
            "title": "Primary Structure Assembly",
            "revision": "B",
            "release_date": "2026-09-01",
            "originator": "J. Smith",
            "approval_authority": "Chief Engineer",
        },
        "mass_properties": {
            "mass_kg": 42.5,
            "cog_x_m": 0.1,
            "cog_y_m": -0.05,
            "cog_z_m": 0.3,
            "ixx_kg_m2": 1.2,
            "iyy_kg_m2": 0.8,
            "izz_kg_m2": 1.5,
        },
        "maturity_level": "released",
        "interfaces": [
            {
                "interface_id": "ICD-001",
                "interface_type": "mechanical",
                "mating_component": "spacecraft-bus",
            }
        ],
        "model_tree_components": [
            {"id": "COMP-001", "description": "Main bracket"},
            {"id": "COMP-002", "description": "Side panel"},
        ],
    }


class ValidateModelFormatTest(unittest.TestCase):
    def test_step_ap214_accepted(self):
        self.assertEqual(cad.validate_model_format("step_ap214"), "accepted")

    def test_step_ap242_accepted(self):
        self.assertEqual(cad.validate_model_format("step_ap242"), "accepted")

    def test_catia_v5_accepted(self):
        self.assertEqual(cad.validate_model_format("catia_v5"), "accepted")

    def test_solidworks_accepted(self):
        self.assertEqual(cad.validate_model_format("solidworks"), "accepted")

    def test_unrecognised_format_raises(self):
        with self.assertRaises(ValueError):
            cad.validate_model_format("autocad_dwg")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            cad.validate_model_format("")


class ValidateCoordinateSystemTest(unittest.TestCase):
    def test_complete_right_handed_no_findings(self):
        cs = {
            "origin": [0, 0, 0],
            "x_axis": [1, 0, 0],
            "y_axis": [0, 1, 0],
            "handedness": "right",
        }
        self.assertEqual(cad.validate_coordinate_system(cs), [])

    def test_left_handed_accepted(self):
        cs = {
            "origin": [0, 0, 0],
            "x_axis": [1, 0, 0],
            "y_axis": [0, 1, 0],
            "handedness": "left",
        }
        self.assertEqual(cad.validate_coordinate_system(cs), [])

    def test_missing_handedness_flagged(self):
        cs = {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0]}
        findings = cad.validate_coordinate_system(cs)
        issues = [f["issue"] for f in findings]
        self.assertIn("missing_coordinate_system_field", issues)
        fields = [f["field"] for f in findings if f["issue"] == "missing_coordinate_system_field"]
        self.assertIn("handedness", fields)

    def test_invalid_handedness_flagged(self):
        cs = {
            "origin": [0, 0, 0],
            "x_axis": [1, 0, 0],
            "y_axis": [0, 1, 0],
            "handedness": "ambidextrous",
        }
        findings = cad.validate_coordinate_system(cs)
        issues = [f["issue"] for f in findings]
        self.assertIn("invalid_handedness_value", issues)

    def test_multiple_missing_fields_all_flagged(self):
        findings = cad.validate_coordinate_system({})
        self.assertEqual(len(findings), 4)


class ValidateTitleBlockTest(unittest.TestCase):
    def test_complete_title_block_no_findings(self):
        tb = {
            "document_number": "X-001",
            "title": "Assembly",
            "revision": "A",
            "release_date": "2026-01-01",
            "originator": "Engineer",
            "approval_authority": "PM",
        }
        self.assertEqual(cad.validate_title_block(tb), [])

    def test_missing_approval_authority_flagged(self):
        tb = {
            "document_number": "X-001",
            "title": "Assembly",
            "revision": "A",
            "release_date": "2026-01-01",
            "originator": "Engineer",
        }
        findings = cad.validate_title_block(tb)
        fields = [f["field"] for f in findings]
        self.assertIn("approval_authority", fields)

    def test_empty_title_block_flags_all_fields(self):
        findings = cad.validate_title_block({})
        self.assertEqual(len(findings), 6)


class ValidateMassPropertiesTest(unittest.TestCase):
    def test_complete_valid_no_findings(self):
        mp = {
            "mass_kg": 10.0,
            "cog_x_m": 0.0,
            "cog_y_m": -0.1,
            "cog_z_m": 0.2,
            "ixx_kg_m2": 1.0,
            "iyy_kg_m2": 2.0,
            "izz_kg_m2": 3.0,
        }
        self.assertEqual(cad.validate_mass_properties(mp), [])

    def test_negative_mass_flagged(self):
        mp = {
            "mass_kg": -1.0,
            "cog_x_m": 0.0,
            "cog_y_m": 0.0,
            "cog_z_m": 0.0,
            "ixx_kg_m2": 1.0,
            "iyy_kg_m2": 1.0,
            "izz_kg_m2": 1.0,
        }
        findings = cad.validate_mass_properties(mp)
        issues = [f["issue"] for f in findings]
        self.assertIn("negative_mass_property_value", issues)

    def test_negative_inertia_flagged(self):
        mp = {
            "mass_kg": 5.0,
            "cog_x_m": 0.0,
            "cog_y_m": 0.0,
            "cog_z_m": 0.0,
            "ixx_kg_m2": -0.1,
            "iyy_kg_m2": 1.0,
            "izz_kg_m2": 1.0,
        }
        findings = cad.validate_mass_properties(mp)
        fields = [f.get("field") for f in findings if f["issue"] == "negative_mass_property_value"]
        self.assertIn("ixx_kg_m2", fields)

    def test_negative_cog_not_flagged(self):
        mp = {
            "mass_kg": 5.0,
            "cog_x_m": -1.5,
            "cog_y_m": -0.3,
            "cog_z_m": -2.0,
            "ixx_kg_m2": 1.0,
            "iyy_kg_m2": 1.0,
            "izz_kg_m2": 1.0,
        }
        self.assertEqual(cad.validate_mass_properties(mp), [])

    def test_missing_field_flagged(self):
        mp = {
            "mass_kg": 5.0,
            "cog_x_m": 0.0,
            "cog_y_m": 0.0,
            "cog_z_m": 0.0,
            "ixx_kg_m2": 1.0,
            "iyy_kg_m2": 1.0,
        }
        findings = cad.validate_mass_properties(mp)
        fields = [f["field"] for f in findings if f["issue"] == "missing_mass_property_field"]
        self.assertIn("izz_kg_m2", fields)

    def test_empty_record_flags_all_fields(self):
        findings = cad.validate_mass_properties({})
        self.assertEqual(len(findings), 7)


class ValidateMaturityLevelTest(unittest.TestCase):
    def test_released_accepted(self):
        self.assertEqual(cad.validate_maturity_level("released"), "released")

    def test_preliminary_accepted(self):
        self.assertEqual(cad.validate_maturity_level("preliminary"), "preliminary")

    def test_development_accepted(self):
        self.assertEqual(cad.validate_maturity_level("development"), "development")

    def test_superseded_accepted(self):
        self.assertEqual(cad.validate_maturity_level("superseded"), "superseded")

    def test_unrecognised_level_raises(self):
        with self.assertRaises(ValueError):
            cad.validate_maturity_level("draft")


class ValidateInterfaceDefinitionTest(unittest.TestCase):
    def test_complete_mechanical_interface_no_findings(self):
        iface = {
            "interface_id": "ICD-001",
            "interface_type": "mechanical",
            "mating_component": "bus-panel",
        }
        self.assertEqual(cad.validate_interface_definition(iface), [])

    def test_missing_mating_component_flagged(self):
        iface = {"interface_id": "ICD-001", "interface_type": "thermal"}
        findings = cad.validate_interface_definition(iface)
        fields = [f["field"] for f in findings]
        self.assertIn("mating_component", fields)

    def test_invalid_interface_type_flagged(self):
        iface = {
            "interface_id": "ICD-002",
            "interface_type": "acoustic",
            "mating_component": "panel-2",
        }
        findings = cad.validate_interface_definition(iface)
        issues = [f["issue"] for f in findings]
        self.assertIn("invalid_interface_type", issues)

    def test_empty_interface_flags_all_required_fields(self):
        findings = cad.validate_interface_definition({})
        self.assertEqual(len(findings), 3)


class ValidateModelTreeTest(unittest.TestCase):
    def test_unique_ids_no_findings(self):
        components = [
            {"id": "A-001", "description": "Bracket"},
            {"id": "A-002", "description": "Panel"},
        ]
        self.assertEqual(cad.validate_model_tree(components), [])

    def test_missing_id_flagged(self):
        components = [{"description": "Bracket"}]
        findings = cad.validate_model_tree(components)
        issues = [f["issue"] for f in findings]
        self.assertIn("component_missing_id", issues)

    def test_duplicate_id_flagged(self):
        components = [
            {"id": "A-001", "description": "Bracket"},
            {"id": "A-001", "description": "Copy of Bracket"},
        ]
        findings = cad.validate_model_tree(components)
        issues = [f["issue"] for f in findings]
        self.assertIn("duplicate_component_id", issues)

    def test_empty_tree_no_findings(self):
        self.assertEqual(cad.validate_model_tree([]), [])


class CadDeliveryReviewTest(unittest.TestCase):
    def test_fully_compliant_delivery(self):
        review = cad.cad_delivery_review(_valid_record())
        self.assertEqual(review, {
            "coordinate_system": [],
            "title_block": [],
            "mass_properties": [],
            "interfaces": [],
            "model_tree": [],
        })
        self.assertTrue(cad.is_delivery_compliant(review))

    def test_bad_format_raises(self):
        rec = _valid_record()
        rec["model_format"] = "pdf"
        with self.assertRaises(ValueError):
            cad.cad_delivery_review(rec)

    def test_bad_maturity_raises(self):
        rec = _valid_record()
        rec["maturity_level"] = "approved"
        with self.assertRaises(ValueError):
            cad.cad_delivery_review(rec)

    def test_title_block_finding_surfaced(self):
        rec = _valid_record()
        del rec["title_block"]["approval_authority"]
        review = cad.cad_delivery_review(rec)
        self.assertTrue(review["title_block"])
        self.assertFalse(cad.is_delivery_compliant(review))

    def test_mass_property_finding_surfaced(self):
        rec = _valid_record()
        rec["mass_properties"]["mass_kg"] = -5.0
        review = cad.cad_delivery_review(rec)
        self.assertTrue(review["mass_properties"])
        self.assertFalse(cad.is_delivery_compliant(review))

    def test_interface_finding_surfaced(self):
        rec = _valid_record()
        rec["interfaces"].append({"interface_id": "ICD-002"})
        review = cad.cad_delivery_review(rec)
        self.assertTrue(review["interfaces"])
        self.assertFalse(cad.is_delivery_compliant(review))

    def test_model_tree_finding_surfaced(self):
        rec = _valid_record()
        rec["model_tree_components"].append({"description": "Orphan part"})
        review = cad.cad_delivery_review(rec)
        self.assertTrue(review["model_tree"])
        self.assertFalse(cad.is_delivery_compliant(review))

    def test_coordinate_system_finding_surfaced(self):
        rec = _valid_record()
        del rec["coordinate_system"]["handedness"]
        review = cad.cad_delivery_review(rec)
        self.assertTrue(review["coordinate_system"])
        self.assertFalse(cad.is_delivery_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
