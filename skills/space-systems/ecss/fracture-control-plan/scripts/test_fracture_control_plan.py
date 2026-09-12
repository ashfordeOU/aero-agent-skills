import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fracture_control_plan_logic import (
    categorize_part,
    check_fc_item_completeness,
    check_plan_sections,
    check_plan_approval,
    is_update_required,
    validate_fracture_control_plan,
    FC,
    NFC,
    REQUIRED_PLAN_SECTIONS,
    MANDATORY_UPDATE_TRIGGERS,
)


class TestCategorization(unittest.TestCase):

    def test_catastrophic_consequence_yields_fc(self):
        result = categorize_part("SPAR-001", "catastrophic")
        self.assertEqual(result["designation"], FC)

    def test_critical_consequence_yields_fc(self):
        result = categorize_part("FRAME-002", "critical")
        self.assertEqual(result["designation"], FC)

    def test_marginal_consequence_yields_nfc(self):
        result = categorize_part("BRACKET-007", "marginal")
        self.assertEqual(result["designation"], NFC)

    def test_negligible_consequence_yields_nfc(self):
        result = categorize_part("CLIP-012", "negligible")
        self.assertEqual(result["designation"], NFC)

    def test_invalid_consequence_raises(self):
        with self.assertRaises(ValueError):
            categorize_part("PART-X", "unknown_level")

    def test_empty_part_id_raises(self):
        with self.assertRaises(ValueError):
            categorize_part("", "catastrophic")

    def test_whitespace_part_id_raises(self):
        with self.assertRaises(ValueError):
            categorize_part("   ", "critical")

    def test_categorize_returns_all_fields(self):
        result = categorize_part("RIB-003", "catastrophic")
        self.assertEqual(result["failure_consequence"], "catastrophic")
        self.assertEqual(result["part_id"], "RIB-003")
        self.assertEqual(result["designation"], FC)


class TestFCItemCompleteness(unittest.TestCase):

    def _valid_fc_item(self):
        return {
            "part_id": "SPAR-001",
            "nde_method": "ultrasonic",
            "nde_detection_limit_mm": 0.5,
            "life_approach": "safe_life",
            "verification_method": "analysis_and_test",
            "design_life_cycles": 10000,
        }

    def test_valid_fc_item_passes(self):
        result = check_fc_item_completeness(self._valid_fc_item())
        self.assertTrue(result["pass"])
        self.assertEqual(result["findings"], [])

    def test_missing_nde_method_fails(self):
        item = self._valid_fc_item()
        del item["nde_method"]
        result = check_fc_item_completeness(item)
        self.assertFalse(result["pass"])
        self.assertTrue(any("nde_method" in f for f in result["findings"]))

    def test_invalid_nde_method_fails(self):
        item = self._valid_fc_item()
        item["nde_method"] = "visual_only"
        result = check_fc_item_completeness(item)
        self.assertFalse(result["pass"])

    def test_missing_life_approach_fails(self):
        item = self._valid_fc_item()
        del item["life_approach"]
        result = check_fc_item_completeness(item)
        self.assertFalse(result["pass"])
        self.assertTrue(any("life_approach" in f for f in result["findings"]))

    def test_missing_verification_method_fails(self):
        item = self._valid_fc_item()
        del item["verification_method"]
        result = check_fc_item_completeness(item)
        self.assertFalse(result["pass"])

    def test_zero_detection_limit_fails(self):
        item = self._valid_fc_item()
        item["nde_detection_limit_mm"] = 0.0
        result = check_fc_item_completeness(item)
        self.assertFalse(result["pass"])

    def test_negative_detection_limit_fails(self):
        item = self._valid_fc_item()
        item["nde_detection_limit_mm"] = -1.0
        result = check_fc_item_completeness(item)
        self.assertFalse(result["pass"])

    def test_negative_design_life_fails(self):
        item = self._valid_fc_item()
        item["design_life_cycles"] = -500
        result = check_fc_item_completeness(item)
        self.assertFalse(result["pass"])

    def test_fail_safe_approach_valid(self):
        item = self._valid_fc_item()
        item["life_approach"] = "fail_safe"
        result = check_fc_item_completeness(item)
        self.assertTrue(result["pass"])

    def test_damage_tolerant_approach_valid(self):
        item = self._valid_fc_item()
        item["life_approach"] = "damage_tolerant"
        result = check_fc_item_completeness(item)
        self.assertTrue(result["pass"])

    def test_analysis_only_verification_valid(self):
        item = self._valid_fc_item()
        item["verification_method"] = "analysis"
        result = check_fc_item_completeness(item)
        self.assertTrue(result["pass"])

    def test_test_only_verification_valid(self):
        item = self._valid_fc_item()
        item["verification_method"] = "test"
        result = check_fc_item_completeness(item)
        self.assertTrue(result["pass"])

    def test_multiple_missing_fields_reported(self):
        result = check_fc_item_completeness({"part_id": "X-001"})
        self.assertFalse(result["pass"])
        self.assertGreater(len(result["findings"]), 1)


class TestPlanSections(unittest.TestCase):

    def test_all_sections_present_passes(self):
        result = check_plan_sections(list(REQUIRED_PLAN_SECTIONS))
        self.assertTrue(result["pass"])
        self.assertEqual(result["missing"], [])

    def test_missing_nde_requirements_fails(self):
        sections = [s for s in REQUIRED_PLAN_SECTIONS if s != "nde_requirements"]
        result = check_plan_sections(sections)
        self.assertFalse(result["pass"])
        self.assertIn("nde_requirements", result["missing"])

    def test_missing_part_inventory_fails(self):
        sections = [s for s in REQUIRED_PLAN_SECTIONS if s != "part_inventory"]
        result = check_plan_sections(sections)
        self.assertFalse(result["pass"])
        self.assertIn("part_inventory", result["missing"])

    def test_empty_sections_list_fails(self):
        result = check_plan_sections([])
        self.assertFalse(result["pass"])
        self.assertEqual(len(result["missing"]), len(REQUIRED_PLAN_SECTIONS))

    def test_extra_sections_do_not_cause_failure(self):
        sections = list(REQUIRED_PLAN_SECTIONS) + ["additional_notes", "appendix_a"]
        result = check_plan_sections(sections)
        self.assertTrue(result["pass"])

    def test_missing_sections_returned_sorted(self):
        result = check_plan_sections([])
        self.assertEqual(result["missing"], sorted(result["missing"]))


class TestPlanApproval(unittest.TestCase):

    def _full_approval(self):
        return {
            "project_engineer_signed": True,
            "fracture_control_authority_signed": True,
            "customer_accepted": True,
        }

    def test_all_signed_passes(self):
        result = check_plan_approval(self._full_approval())
        self.assertTrue(result["pass"])
        self.assertEqual(result["unsigned_roles"], [])

    def test_unsigned_fc_authority_fails(self):
        rec = self._full_approval()
        rec["fracture_control_authority_signed"] = False
        result = check_plan_approval(rec)
        self.assertFalse(result["pass"])
        self.assertIn("fracture_control_authority", result["unsigned_roles"])

    def test_customer_not_accepted_fails(self):
        rec = self._full_approval()
        rec["customer_accepted"] = False
        result = check_plan_approval(rec)
        self.assertFalse(result["pass"])
        self.assertIn("customer", result["unsigned_roles"])

    def test_project_engineer_unsigned_fails(self):
        rec = self._full_approval()
        rec["project_engineer_signed"] = False
        result = check_plan_approval(rec)
        self.assertFalse(result["pass"])
        self.assertIn("project_engineer", result["unsigned_roles"])

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            check_plan_approval({"project_engineer_signed": True})

    def test_all_unsigned_reports_three_roles(self):
        rec = {
            "project_engineer_signed": False,
            "fracture_control_authority_signed": False,
            "customer_accepted": False,
        }
        result = check_plan_approval(rec)
        self.assertFalse(result["pass"])
        self.assertEqual(len(result["unsigned_roles"]), 3)


class TestUpdateTriggers(unittest.TestCase):

    def test_design_change_requires_update(self):
        self.assertTrue(is_update_required("design_change")["update_required"])

    def test_material_change_requires_update(self):
        self.assertTrue(is_update_required("material_change")["update_required"])

    def test_load_increase_requires_update(self):
        self.assertTrue(is_update_required("load_increase")["update_required"])

    def test_new_fc_finding_requires_update(self):
        self.assertTrue(is_update_required("new_fc_finding")["update_required"])

    def test_inspection_finding_requires_update(self):
        self.assertTrue(is_update_required("inspection_finding")["update_required"])

    def test_cosmetic_change_does_not_require_update(self):
        self.assertFalse(is_update_required("cosmetic_label_change")["update_required"])

    def test_unknown_change_does_not_require_update(self):
        self.assertFalse(is_update_required("vendor_contact_update")["update_required"])

    def test_result_contains_reason_string(self):
        result = is_update_required("design_change")
        self.assertIn("reason", result)
        self.assertIsInstance(result["reason"], str)
        self.assertGreater(len(result["reason"]), 0)

    def test_all_mandatory_triggers_require_update(self):
        for trigger in MANDATORY_UPDATE_TRIGGERS:
            with self.subTest(trigger=trigger):
                self.assertTrue(is_update_required(trigger)["update_required"])


class TestFullPlanValidation(unittest.TestCase):

    def _valid_plan(self):
        return {
            "sections": list(REQUIRED_PLAN_SECTIONS),
            "approval": {
                "project_engineer_signed": True,
                "fracture_control_authority_signed": True,
                "customer_accepted": True,
            },
            "fc_items": [
                {
                    "part_id": "SPAR-001",
                    "nde_method": "ultrasonic",
                    "nde_detection_limit_mm": 0.5,
                    "life_approach": "safe_life",
                    "verification_method": "analysis_and_test",
                    "design_life_cycles": 10000,
                }
            ],
        }

    def test_valid_plan_passes_overall(self):
        result = validate_fracture_control_plan(self._valid_plan())
        self.assertTrue(result["overall_pass"])

    def test_plan_with_missing_section_fails_overall(self):
        plan = self._valid_plan()
        plan["sections"] = [s for s in REQUIRED_PLAN_SECTIONS if s != "nde_requirements"]
        result = validate_fracture_control_plan(plan)
        self.assertFalse(result["overall_pass"])

    def test_plan_with_incomplete_fc_item_fails_overall(self):
        plan = self._valid_plan()
        del plan["fc_items"][0]["nde_method"]
        result = validate_fracture_control_plan(plan)
        self.assertFalse(result["overall_pass"])

    def test_plan_with_unapproved_customer_fails_overall(self):
        plan = self._valid_plan()
        plan["approval"]["customer_accepted"] = False
        result = validate_fracture_control_plan(plan)
        self.assertFalse(result["overall_pass"])

    def test_non_dict_plan_raises(self):
        with self.assertRaises(ValueError):
            validate_fracture_control_plan("not a dict")

    def test_result_has_all_expected_keys(self):
        result = validate_fracture_control_plan(self._valid_plan())
        for key in ("overall_pass", "section_check", "approval_check", "fc_item_checks"):
            self.assertIn(key, result)

    def test_plan_with_no_fc_items_passes_if_rest_valid(self):
        plan = self._valid_plan()
        plan["fc_items"] = []
        result = validate_fracture_control_plan(plan)
        self.assertTrue(result["overall_pass"])

    def test_fc_item_checks_list_length_matches_items(self):
        plan = self._valid_plan()
        plan["fc_items"].append({
            "part_id": "FRAME-002",
            "nde_method": "radiography",
            "nde_detection_limit_mm": 1.0,
            "life_approach": "fail_safe",
            "verification_method": "test",
            "design_life_cycles": 5000,
        })
        result = validate_fracture_control_plan(plan)
        self.assertEqual(len(result["fc_item_checks"]), 2)
        self.assertTrue(result["overall_pass"])


if __name__ == "__main__":
    unittest.main()
