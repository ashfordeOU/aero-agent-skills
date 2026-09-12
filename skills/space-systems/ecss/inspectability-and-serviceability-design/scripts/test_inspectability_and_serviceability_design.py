#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clauses 4.5.1-4.5.4
inspectability and serviceability design assessment.

Exercises scripts/inspectability_and_serviceability_design_logic.py
(stdlib unittest, offline). Contract: an inspection method is
categorized as direct (visual) or tool-aided (all others) and an
unrecognized method raises; a primary or secondary joint with no
access path is flagged and one with insufficient clearance is flagged
separately; a non-structural joint has no requirement; a replaceable
part with undefined tolerances or adjustment required is flagged and
a non-replaceable part is not; a maintenance action with insufficient
clearance, missing tooling, or missing procedure is each flagged
independently; an unknown action type raises; a galling-risk material
pair is detected regardless of argument order; a dismount joint with
insufficient cycle rating is flagged and one with a galling-risk pair
and no treatment is flagged; a fully compliant item passes the
combined serviceability review and is_serviceability_compliant returns
True, while any finding returns False.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inspectability_and_serviceability_design_logic as sd  # noqa: E402


class CategorizeAccessMethodTest(unittest.TestCase):
    def test_visual_is_direct(self):
        self.assertEqual(sd.categorize_access_method("visual"), "direct")

    def test_borescope_is_tool_aided(self):
        self.assertEqual(sd.categorize_access_method("borescope"), "tool_aided")

    def test_ultrasonic_probe_is_tool_aided(self):
        self.assertEqual(sd.categorize_access_method("ultrasonic_probe"), "tool_aided")

    def test_eddy_current_is_tool_aided(self):
        self.assertEqual(sd.categorize_access_method("eddy_current"), "tool_aided")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            sd.categorize_access_method("xray_tomography")


class CheckInspectabilityTest(unittest.TestCase):
    def test_primary_joint_no_access_flagged(self):
        violations = sd.check_inspectability("J-001", "primary", None, 0.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "no_inspection_access")
        self.assertEqual(violations[0]["joint"], "J-001")

    def test_secondary_joint_no_access_flagged(self):
        violations = sd.check_inspectability("J-002", "secondary", None, 0.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "no_inspection_access")

    def test_non_structural_joint_no_requirement(self):
        self.assertEqual(
            sd.check_inspectability("J-003", "non_structural", None, 0.0), []
        )

    def test_primary_joint_insufficient_visual_clearance(self):
        violations = sd.check_inspectability("J-004", "primary", "visual", 30.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "insufficient_inspection_clearance")
        self.assertEqual(violations[0]["required_mm"], 50.0)
        self.assertEqual(violations[0]["clearance_mm"], 30.0)

    def test_primary_joint_adequate_visual_clearance(self):
        self.assertEqual(
            sd.check_inspectability("J-005", "primary", "visual", 50.0), []
        )

    def test_borescope_minimum_clearance_passes(self):
        self.assertEqual(
            sd.check_inspectability("J-006", "secondary", "borescope", 15.0), []
        )

    def test_borescope_below_minimum_flagged(self):
        violations = sd.check_inspectability("J-007", "secondary", "borescope", 10.0)
        self.assertEqual(violations[0]["issue"], "insufficient_inspection_clearance")

    def test_unknown_criticality_raises(self):
        with self.assertRaises(ValueError):
            sd.check_inspectability("J-008", "critical_extreme", "visual", 60.0)

    def test_negative_clearance_raises(self):
        with self.assertRaises(ValueError):
            sd.check_inspectability("J-009", "primary", "visual", -1.0)


class CheckInterchangeabilityTest(unittest.TestCase):
    def test_non_replaceable_part_no_violation(self):
        self.assertEqual(
            sd.check_interchangeability("P-001", False, False, False), []
        )

    def test_replaceable_part_tolerances_not_defined_flagged(self):
        violations = sd.check_interchangeability("P-002", True, False, False)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "interface_tolerances_not_defined")
        self.assertEqual(violations[0]["part"], "P-002")

    def test_replaceable_part_adjustment_required_flagged(self):
        violations = sd.check_interchangeability("P-003", True, True, True)
        issues = [v["issue"] for v in violations]
        self.assertIn("manual_adjustment_required", issues)

    def test_replaceable_part_both_failures_reported(self):
        violations = sd.check_interchangeability("P-004", True, False, True)
        self.assertEqual(len(violations), 2)
        issues = {v["issue"] for v in violations}
        self.assertEqual(
            issues,
            {"interface_tolerances_not_defined", "manual_adjustment_required"},
        )

    def test_replaceable_part_fully_compliant(self):
        self.assertEqual(
            sd.check_interchangeability("P-005", True, True, False), []
        )


class CheckMaintainabilityTest(unittest.TestCase):
    def test_replacement_action_insufficient_clearance(self):
        violations = sd.check_maintainability(
            "MA-001", "replacement", 80.0, True, True
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "insufficient_maintenance_clearance")
        self.assertEqual(violations[0]["required_mm"], 100.0)

    def test_action_missing_tooling_flagged(self):
        violations = sd.check_maintainability(
            "MA-002", "lubrication", 40.0, False, True
        )
        issues = [v["issue"] for v in violations]
        self.assertIn("tooling_not_defined", issues)

    def test_action_missing_procedure_flagged(self):
        violations = sd.check_maintainability(
            "MA-003", "adjustment", 60.0, True, False
        )
        issues = [v["issue"] for v in violations]
        self.assertIn("procedure_not_defined", issues)

    def test_action_fully_compliant(self):
        self.assertEqual(
            sd.check_maintainability("MA-004", "inspection", 60.0, True, True), []
        )

    def test_unknown_action_type_raises(self):
        with self.assertRaises(ValueError):
            sd.check_maintainability("MA-005", "overhaul", 100.0, True, True)

    def test_negative_clearance_raises(self):
        with self.assertRaises(ValueError):
            sd.check_maintainability("MA-006", "repair", -5.0, True, True)

    def test_all_three_failures_independent(self):
        violations = sd.check_maintainability(
            "MA-007", "repair", 20.0, False, False
        )
        issues = {v["issue"] for v in violations}
        self.assertEqual(
            issues,
            {
                "insufficient_maintenance_clearance",
                "tooling_not_defined",
                "procedure_not_defined",
            },
        )


class IsGallingRiskPairTest(unittest.TestCase):
    def test_same_titanium_is_risk(self):
        self.assertTrue(sd.is_galling_risk_pair("titanium", "titanium"))

    def test_same_stainless_steel_is_risk(self):
        self.assertTrue(sd.is_galling_risk_pair("stainless_steel", "stainless_steel"))

    def test_inconel_stainless_steel_is_risk(self):
        self.assertTrue(sd.is_galling_risk_pair("inconel", "stainless_steel"))

    def test_inconel_stainless_steel_reversed_is_risk(self):
        self.assertTrue(sd.is_galling_risk_pair("stainless_steel", "inconel"))

    def test_titanium_aluminum_not_risk(self):
        self.assertFalse(sd.is_galling_risk_pair("titanium", "aluminum"))

    def test_case_insensitive(self):
        self.assertTrue(sd.is_galling_risk_pair("Titanium", "TITANIUM"))


class CheckDismountabilityTest(unittest.TestCase):
    def test_insufficient_cycles_flagged(self):
        violations = sd.check_dismountability(
            "DJ-001", 3, 10, "aluminum", "steel", "dry_film_lubricant"
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "insufficient_dismount_cycles")
        self.assertEqual(violations[0]["design_cycles"], 3)
        self.assertEqual(violations[0]["required_cycles"], 10)

    def test_missing_anti_galling_treatment_flagged(self):
        violations = sd.check_dismountability(
            "DJ-002", 20, 10, "titanium", "titanium", None
        )
        issues = [v["issue"] for v in violations]
        self.assertIn("missing_anti_galling_treatment", issues)

    def test_galling_risk_with_treatment_no_violation(self):
        violations = sd.check_dismountability(
            "DJ-003", 20, 10, "stainless_steel", "stainless_steel", "silver_plating"
        )
        self.assertEqual(violations, [])

    def test_no_galling_risk_no_treatment_no_violation(self):
        violations = sd.check_dismountability(
            "DJ-004", 20, 10, "titanium", "composite", None
        )
        self.assertEqual(violations, [])

    def test_negative_design_cycles_raises(self):
        with self.assertRaises(ValueError):
            sd.check_dismountability("DJ-005", -1, 5, "aluminum", "aluminum", None)

    def test_negative_required_cycles_raises(self):
        with self.assertRaises(ValueError):
            sd.check_dismountability("DJ-006", 5, -1, "aluminum", "aluminum", None)

    def test_both_failures_reported_independently(self):
        violations = sd.check_dismountability(
            "DJ-007", 2, 10, "titanium", "titanium", None
        )
        issues = {v["issue"] for v in violations}
        self.assertEqual(
            issues,
            {"insufficient_dismount_cycles", "missing_anti_galling_treatment"},
        )


class ServiceabilityReviewTest(unittest.TestCase):
    def _compliant_item(self):
        return {
            "item_id": "ITEM-001",
            "criticality": "primary",
            "inspection_method": "visual",
            "inspection_clearance_mm": 60.0,
            "replaceable": True,
            "tolerance_defined": True,
            "adjustment_required": False,
            "maintenance_actions": [
                {
                    "action_id": "MA-A",
                    "action_type": "replacement",
                    "access_clearance_mm": 120.0,
                    "tooling_defined": True,
                    "procedure_defined": True,
                }
            ],
            "dismount_joints": [
                {
                    "joint_id": "DJ-A",
                    "design_cycles": 25,
                    "required_cycles": 10,
                    "material_a": "aluminum",
                    "material_b": "aluminum",
                    "anti_galling_treatment": "anodize_coating",
                }
            ],
        }

    def test_fully_compliant_item_passes(self):
        review = sd.serviceability_review(self._compliant_item())
        self.assertEqual(
            review,
            {
                "inspectability": [],
                "interchangeability": [],
                "maintainability": [],
                "dismountability": [],
            },
        )
        self.assertTrue(sd.is_serviceability_compliant(review))

    def test_non_structural_item_no_inspectability_finding(self):
        item = self._compliant_item()
        item["criticality"] = "non_structural"
        item["inspection_method"] = None
        item["inspection_clearance_mm"] = 0.0
        review = sd.serviceability_review(item)
        self.assertEqual(review["inspectability"], [])

    def test_primary_joint_no_access_surfaced_in_review(self):
        item = self._compliant_item()
        item["inspection_method"] = None
        review = sd.serviceability_review(item)
        self.assertTrue(review["inspectability"])
        self.assertFalse(sd.is_serviceability_compliant(review))

    def test_replaceable_part_missing_tolerance_surfaced(self):
        item = self._compliant_item()
        item["tolerance_defined"] = False
        review = sd.serviceability_review(item)
        self.assertTrue(review["interchangeability"])

    def test_maintenance_missing_procedure_surfaced(self):
        item = self._compliant_item()
        item["maintenance_actions"][0]["procedure_defined"] = False
        review = sd.serviceability_review(item)
        self.assertTrue(review["maintainability"])

    def test_dismount_insufficient_cycles_surfaced(self):
        item = self._compliant_item()
        item["dismount_joints"][0]["design_cycles"] = 2
        review = sd.serviceability_review(item)
        self.assertTrue(review["dismountability"])

    def test_all_categories_independent(self):
        item = self._compliant_item()
        item["inspection_method"] = None
        item["tolerance_defined"] = False
        item["maintenance_actions"][0]["tooling_defined"] = False
        item["dismount_joints"][0]["design_cycles"] = 0
        item["dismount_joints"][0]["anti_galling_treatment"] = None
        review = sd.serviceability_review(item)
        self.assertTrue(review["inspectability"])
        self.assertTrue(review["interchangeability"])
        self.assertTrue(review["maintainability"])
        self.assertTrue(review["dismountability"])
        self.assertFalse(sd.is_serviceability_compliant(review))

    def test_empty_maintenance_and_dismount_lists(self):
        item = {
            "item_id": "ITEM-002",
            "criticality": "secondary",
            "inspection_method": "borescope",
            "inspection_clearance_mm": 20.0,
            "replaceable": False,
            "tolerance_defined": False,
            "adjustment_required": False,
            "maintenance_actions": [],
            "dismount_joints": [],
        }
        review = sd.serviceability_review(item)
        self.assertEqual(review["maintainability"], [])
        self.assertEqual(review["dismountability"], [])
        self.assertTrue(sd.is_serviceability_compliant(review))


if __name__ == "__main__":
    unittest.main()
