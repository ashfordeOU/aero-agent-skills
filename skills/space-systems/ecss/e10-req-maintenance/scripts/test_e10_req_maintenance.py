#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.2.3.8 requirement
maintenance under configuration control.

Exercises scripts/e10_req_maintenance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a lifecycle
state transition is allowed only per the fixed transition table and an
unrecognized state or disallowed transition raises; a baselined
requirement under modification requires an approved change request or
is flagged; the derived-requirement and verification-item impact
lookups return the recorded links for a requirement (empty when none
are recorded); a change with real impact but no recorded assessment is
flagged, while a change with no impact needs no assessment; a
baselined requirement under modification without a maintenance record
is flagged; and the aggregated review is compliant only when all three
categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_maintenance_logic as rm  # noqa: E402


class ValidateStateTransitionTest(unittest.TestCase):
    def test_draft_to_proposed_allowed(self):
        self.assertTrue(rm.validate_state_transition("draft", "proposed"))

    def test_draft_to_obsolete_allowed(self):
        self.assertTrue(rm.validate_state_transition("draft", "obsolete"))

    def test_proposed_to_baselined_allowed(self):
        self.assertTrue(rm.validate_state_transition("proposed", "baselined"))

    def test_proposed_to_draft_allowed(self):
        self.assertTrue(rm.validate_state_transition("proposed", "draft"))

    def test_baselined_to_obsolete_allowed(self):
        self.assertTrue(rm.validate_state_transition("baselined", "obsolete"))

    def test_draft_to_baselined_disallowed(self):
        with self.assertRaises(ValueError):
            rm.validate_state_transition("draft", "baselined")

    def test_obsolete_to_anything_disallowed(self):
        with self.assertRaises(ValueError):
            rm.validate_state_transition("obsolete", "draft")

    def test_unknown_current_state_raises(self):
        with self.assertRaises(ValueError):
            rm.validate_state_transition("archived", "obsolete")

    def test_unknown_target_state_raises(self):
        with self.assertRaises(ValueError):
            rm.validate_state_transition("draft", "archived")


class RequiresChangeControlTest(unittest.TestCase):
    def test_baselined_requires_control(self):
        self.assertTrue(rm.requires_change_control("baselined"))

    def test_draft_does_not_require_control(self):
        self.assertFalse(rm.requires_change_control("draft"))

    def test_proposed_does_not_require_control(self):
        self.assertFalse(rm.requires_change_control("proposed"))

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            rm.requires_change_control("archived")


class ConfigurationControlViolationsTest(unittest.TestCase):
    def test_baselined_modified_without_change_request_flagged(self):
        violations = rm.configuration_control_violations(
            "REQ-1", "baselined", True, False
        )
        self.assertEqual(
            violations,
            [
                {
                    "issue": "change_without_configuration_control",
                    "requirement": "REQ-1",
                    "state": "baselined",
                }
            ],
        )

    def test_baselined_modified_with_change_request_clean(self):
        self.assertEqual(
            rm.configuration_control_violations("REQ-1", "baselined", True, True), []
        )

    def test_baselined_not_modified_clean(self):
        self.assertEqual(
            rm.configuration_control_violations("REQ-1", "baselined", False, False), []
        )

    def test_draft_modified_without_change_request_clean(self):
        self.assertEqual(
            rm.configuration_control_violations("REQ-1", "draft", True, False), []
        )


class ImpactLookupTest(unittest.TestCase):
    def test_derived_requirement_impact_found(self):
        trace_links = {"REQ-1": ["REQ-1.1", "REQ-1.2"]}
        self.assertEqual(
            rm.derived_requirement_impact("REQ-1", trace_links),
            ["REQ-1.1", "REQ-1.2"],
        )

    def test_derived_requirement_impact_none_recorded(self):
        self.assertEqual(rm.derived_requirement_impact("REQ-1", {}), [])

    def test_verification_impact_found(self):
        verification_links = {"REQ-1": ["VER-2", "VER-1"]}
        self.assertEqual(
            rm.verification_impact("REQ-1", verification_links), ["VER-1", "VER-2"]
        )

    def test_verification_impact_none_recorded(self):
        self.assertEqual(rm.verification_impact("REQ-1", {}), [])

    def test_change_impact_assessment_combines_both(self):
        trace_links = {"REQ-1": ["REQ-1.1"]}
        verification_links = {"REQ-1": ["VER-1"]}
        impact = rm.change_impact_assessment("REQ-1", trace_links, verification_links)
        self.assertEqual(
            impact,
            {"derived_requirements": ["REQ-1.1"], "verification_items": ["VER-1"]},
        )


class ImpactAssessmentViolationsTest(unittest.TestCase):
    def test_impact_without_assessment_flagged(self):
        impact = {"derived_requirements": ["REQ-1.1"], "verification_items": []}
        violations = rm.impact_assessment_violations("REQ-1", impact, False)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_change_impact_assessment")

    def test_impact_with_assessment_clean(self):
        impact = {"derived_requirements": ["REQ-1.1"], "verification_items": []}
        self.assertEqual(rm.impact_assessment_violations("REQ-1", impact, True), [])

    def test_no_impact_no_assessment_needed(self):
        impact = {"derived_requirements": [], "verification_items": []}
        self.assertEqual(rm.impact_assessment_violations("REQ-1", impact, False), [])

    def test_verification_only_impact_flagged(self):
        impact = {"derived_requirements": [], "verification_items": ["VER-1"]}
        violations = rm.impact_assessment_violations("REQ-1", impact, False)
        self.assertEqual(len(violations), 1)


class MaintenanceRecordViolationsTest(unittest.TestCase):
    def test_baselined_modified_without_record_flagged(self):
        violations = rm.maintenance_record_violations("REQ-1", "baselined", True, False)
        self.assertEqual(
            violations,
            [{"issue": "missing_maintenance_record", "requirement": "REQ-1"}],
        )

    def test_baselined_modified_with_record_clean(self):
        self.assertEqual(
            rm.maintenance_record_violations("REQ-1", "baselined", True, True), []
        )

    def test_draft_modified_without_record_clean(self):
        self.assertEqual(
            rm.maintenance_record_violations("REQ-1", "draft", True, False), []
        )

    def test_baselined_not_modified_clean(self):
        self.assertEqual(
            rm.maintenance_record_violations("REQ-1", "baselined", False, False), []
        )


class RequirementMaintenanceReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        change = {
            "requirement_id": "REQ-1",
            "state": "baselined",
            "is_being_modified": True,
            "has_approved_change_request": True,
            "has_maintenance_record": True,
            "assessment_recorded": True,
            "trace_links": {"REQ-1": ["REQ-1.1"]},
            "verification_links": {"REQ-1": ["VER-1"]},
        }
        review = rm.requirement_maintenance_review(change)
        self.assertEqual(
            review,
            {"configuration_control": [], "impact_assessment": [], "maintenance_record": []},
        )
        self.assertTrue(rm.is_maintenance_compliant(review))

    def test_review_surfaces_each_category_independently(self):
        change = {
            "requirement_id": "REQ-2",
            "state": "baselined",
            "is_being_modified": True,
            "has_approved_change_request": False,
            "has_maintenance_record": False,
            "assessment_recorded": False,
            "trace_links": {"REQ-2": ["REQ-2.1"]},
            "verification_links": {},
        }
        review = rm.requirement_maintenance_review(change)
        self.assertTrue(review["configuration_control"])
        self.assertTrue(review["impact_assessment"])
        self.assertTrue(review["maintenance_record"])
        self.assertFalse(rm.is_maintenance_compliant(review))

    def test_review_no_impact_requires_no_assessment(self):
        change = {
            "requirement_id": "REQ-3",
            "state": "baselined",
            "is_being_modified": True,
            "has_approved_change_request": True,
            "has_maintenance_record": True,
            "assessment_recorded": False,
            "trace_links": {},
            "verification_links": {},
        }
        review = rm.requirement_maintenance_review(change)
        self.assertEqual(review["impact_assessment"], [])
        self.assertTrue(rm.is_maintenance_compliant(review))

    def test_review_draft_requirement_skips_configuration_control(self):
        change = {
            "requirement_id": "REQ-4",
            "state": "draft",
            "is_being_modified": True,
            "has_approved_change_request": False,
            "has_maintenance_record": False,
            "assessment_recorded": False,
            "trace_links": {},
            "verification_links": {},
        }
        review = rm.requirement_maintenance_review(change)
        self.assertEqual(review["configuration_control"], [])
        self.assertEqual(review["maintenance_record"], [])
        self.assertTrue(rm.is_maintenance_compliant(review))

    def test_review_raises_on_unknown_state(self):
        change = {
            "requirement_id": "REQ-5",
            "state": "archived",
            "is_being_modified": True,
        }
        with self.assertRaises(ValueError):
            rm.requirement_maintenance_review(change)


if __name__ == "__main__":
    unittest.main(verbosity=2)
