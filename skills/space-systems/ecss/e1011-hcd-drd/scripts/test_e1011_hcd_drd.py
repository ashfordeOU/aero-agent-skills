#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C Annex A HCD process plan DRD
validation.

Exercises scripts/e1011_hcd_drd_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — every mandatory section
that is absent is flagged; every required field that is empty or missing
within a present section is flagged; each activity without a milestone
or responsible practitioner is flagged; each evaluation event with a
type other than formative or summative is flagged and each event without
success criteria is flagged; each HFE practitioner without a competency
statement is flagged; each traceability mapping without an activity ID
or requirement ID is flagged; the aggregated result is compliant only
when every violation list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_hcd_drd_logic as hcd  # noqa: E402


def _minimal_compliant_plan():
    return {
        "scope": {
            "document_title": "HCD Process Plan — Mission Alpha",
            "applicable_standard": "ECSS-E-ST-10-11C",
        },
        "context_of_use": {
            "mission_phases": ["pre-launch", "operations", "contingency"],
            "crew_roles": ["commander", "systems-engineer"],
            "environment_description": "Low Earth Orbit, microgravity, confined quarters",
        },
        "stakeholder_inventory": {
            "users": ["flight crew"],
            "operators": ["ground control"],
        },
        "activity_schedule": {
            "activities": [
                {
                    "name": "context-of-use-analysis",
                    "milestone": "PDR",
                    "responsible_practitioner": "Dr. Smith",
                },
            ],
        },
        "evaluation_plan": {
            "events": [
                {
                    "name": "formative-eval-1",
                    "type": "formative",
                    "success_criteria": "SUS score >= 70",
                },
                {
                    "name": "summative-eval-1",
                    "type": "summative",
                    "success_criteria": "All critical tasks completed within time limit",
                },
            ],
        },
        "hfe_staffing": {
            "practitioners": [
                {
                    "name": "Dr. Smith",
                    "competency": "Chartered Ergonomist, 10 years spaceflight HFE",
                },
            ],
        },
        "requirements_traceability": {
            "mappings": [
                {
                    "activity_id": "context-of-use-analysis",
                    "requirement_id": "HFE-REQ-001",
                },
            ],
        },
    }


class MandatorySectionsTest(unittest.TestCase):
    def test_all_sections_present_returns_no_violations(self):
        plan = _minimal_compliant_plan()
        self.assertEqual(hcd.check_mandatory_sections(plan), [])

    def test_missing_one_section_flagged(self):
        plan = _minimal_compliant_plan()
        del plan["evaluation_plan"]
        violations = hcd.check_mandatory_sections(plan)
        issues = [v["section"] for v in violations]
        self.assertIn("evaluation_plan", issues)

    def test_missing_multiple_sections_all_flagged(self):
        plan = _minimal_compliant_plan()
        del plan["hfe_staffing"]
        del plan["requirements_traceability"]
        violations = hcd.check_mandatory_sections(plan)
        sections = {v["section"] for v in violations}
        self.assertIn("hfe_staffing", sections)
        self.assertIn("requirements_traceability", sections)

    def test_empty_plan_flags_all_mandatory_sections(self):
        violations = hcd.check_mandatory_sections({})
        self.assertEqual(len(violations), len(hcd.MANDATORY_SECTIONS))

    def test_non_dict_plan_raises_type_error(self):
        with self.assertRaises(TypeError):
            hcd.check_mandatory_sections("not-a-dict")


class SectionFieldsTest(unittest.TestCase):
    def test_complete_scope_section_passes(self):
        data = {
            "document_title": "HCD Plan",
            "applicable_standard": "ECSS-E-ST-10-11C",
        }
        self.assertEqual(hcd.check_section_fields("scope", data), [])

    def test_scope_missing_document_title_flagged(self):
        data = {"applicable_standard": "ECSS-E-ST-10-11C"}
        violations = hcd.check_section_fields("scope", data)
        fields = [v["field"] for v in violations]
        self.assertIn("document_title", fields)

    def test_context_of_use_missing_crew_roles_flagged(self):
        data = {
            "mission_phases": ["ops"],
            "environment_description": "LEO",
        }
        violations = hcd.check_section_fields("context_of_use", data)
        fields = [v["field"] for v in violations]
        self.assertIn("crew_roles", fields)

    def test_unrecognized_section_raises_value_error(self):
        with self.assertRaises(ValueError):
            hcd.check_section_fields("nonexistent_section", {})


class ActivityScheduleTest(unittest.TestCase):
    def test_activity_with_milestone_and_practitioner_passes(self):
        activities = [
            {
                "name": "context-analysis",
                "milestone": "PDR",
                "responsible_practitioner": "Dr. Jones",
            }
        ]
        self.assertEqual(hcd.check_activity_schedule(activities), [])

    def test_activity_missing_milestone_flagged(self):
        activities = [
            {"name": "task-analysis", "responsible_practitioner": "Dr. Jones"}
        ]
        violations = hcd.check_activity_schedule(activities)
        issues = [v["issue"] for v in violations]
        self.assertIn("activity_missing_milestone", issues)

    def test_activity_missing_practitioner_flagged(self):
        activities = [{"name": "user-req-elicitation", "milestone": "SRR"}]
        violations = hcd.check_activity_schedule(activities)
        issues = [v["issue"] for v in violations]
        self.assertIn("activity_missing_responsible_practitioner", issues)

    def test_empty_activity_list_passes(self):
        self.assertEqual(hcd.check_activity_schedule([]), [])


class EvaluationEventsTest(unittest.TestCase):
    def test_formative_event_with_criteria_passes(self):
        events = [
            {
                "name": "formative-1",
                "type": "formative",
                "success_criteria": "SUS >= 68",
            }
        ]
        self.assertEqual(hcd.check_evaluation_events(events), [])

    def test_summative_event_with_criteria_passes(self):
        events = [
            {
                "name": "summative-1",
                "type": "summative",
                "success_criteria": "Zero critical errors",
            }
        ]
        self.assertEqual(hcd.check_evaluation_events(events), [])

    def test_event_with_unrecognized_type_flagged(self):
        events = [
            {
                "name": "mystery-eval",
                "type": "exploratory",
                "success_criteria": "TBD",
            }
        ]
        violations = hcd.check_evaluation_events(events)
        issues = [v["issue"] for v in violations]
        self.assertIn("evaluation_event_invalid_type", issues)

    def test_event_missing_success_criteria_flagged(self):
        events = [{"name": "formative-2", "type": "formative"}]
        violations = hcd.check_evaluation_events(events)
        issues = [v["issue"] for v in violations]
        self.assertIn("evaluation_event_missing_success_criteria", issues)

    def test_event_with_none_type_flagged(self):
        events = [{"name": "unconfigured-eval", "type": None, "success_criteria": "Pass"}]
        violations = hcd.check_evaluation_events(events)
        issues = [v["issue"] for v in violations]
        self.assertIn("evaluation_event_invalid_type", issues)


class HfeStaffingTest(unittest.TestCase):
    def test_practitioner_with_competency_passes(self):
        practitioners = [
            {"name": "Dr. Adams", "competency": "CIEHF member, 8 years space HFE"}
        ]
        self.assertEqual(hcd.check_hfe_staffing(practitioners), [])

    def test_practitioner_missing_competency_flagged(self):
        practitioners = [{"name": "J. Doe"}]
        violations = hcd.check_hfe_staffing(practitioners)
        issues = [v["issue"] for v in violations]
        self.assertIn("hfe_practitioner_missing_competency", issues)

    def test_practitioner_with_empty_competency_flagged(self):
        practitioners = [{"name": "J. Doe", "competency": ""}]
        violations = hcd.check_hfe_staffing(practitioners)
        issues = [v["issue"] for v in violations]
        self.assertIn("hfe_practitioner_missing_competency", issues)


class TraceabilityMappingsTest(unittest.TestCase):
    def test_complete_mapping_passes(self):
        mappings = [
            {"activity_id": "context-analysis", "requirement_id": "HFE-REQ-001"}
        ]
        self.assertEqual(hcd.check_traceability_mappings(mappings), [])

    def test_mapping_missing_requirement_id_flagged(self):
        mappings = [{"activity_id": "context-analysis"}]
        violations = hcd.check_traceability_mappings(mappings)
        issues = [v["issue"] for v in violations]
        self.assertIn("traceability_mapping_missing_requirement_id", issues)

    def test_mapping_missing_activity_id_flagged(self):
        mappings = [{"requirement_id": "HFE-REQ-002"}]
        violations = hcd.check_traceability_mappings(mappings)
        issues = [v["issue"] for v in violations]
        self.assertIn("traceability_mapping_missing_activity_id", issues)


class FullValidationTest(unittest.TestCase):
    def test_fully_compliant_plan_is_compliant(self):
        plan = _minimal_compliant_plan()
        result = hcd.validate_hcd_plan(plan)
        self.assertTrue(hcd.is_plan_compliant(result))

    def test_plan_missing_section_is_not_compliant(self):
        plan = _minimal_compliant_plan()
        del plan["context_of_use"]
        result = hcd.validate_hcd_plan(plan)
        self.assertFalse(hcd.is_plan_compliant(result))
        self.assertTrue(result["missing_sections"])

    def test_plan_with_bad_activity_is_not_compliant(self):
        plan = _minimal_compliant_plan()
        plan["activity_schedule"]["activities"][0].pop("milestone")
        result = hcd.validate_hcd_plan(plan)
        self.assertFalse(hcd.is_plan_compliant(result))
        self.assertTrue(result["activity_violations"])

    def test_plan_with_invalid_eval_type_is_not_compliant(self):
        plan = _minimal_compliant_plan()
        plan["evaluation_plan"]["events"][0]["type"] = "heuristic"
        result = hcd.validate_hcd_plan(plan)
        self.assertFalse(hcd.is_plan_compliant(result))
        self.assertTrue(result["evaluation_violations"])

    def test_plan_with_unstaffed_practitioner_is_not_compliant(self):
        plan = _minimal_compliant_plan()
        plan["hfe_staffing"]["practitioners"][0].pop("competency")
        result = hcd.validate_hcd_plan(plan)
        self.assertFalse(hcd.is_plan_compliant(result))
        self.assertTrue(result["staffing_violations"])

    def test_plan_with_incomplete_traceability_is_not_compliant(self):
        plan = _minimal_compliant_plan()
        plan["requirements_traceability"]["mappings"][0].pop("requirement_id")
        result = hcd.validate_hcd_plan(plan)
        self.assertFalse(hcd.is_plan_compliant(result))
        self.assertTrue(result["traceability_violations"])

    def test_validate_raises_on_non_dict_plan(self):
        with self.assertRaises(TypeError):
            hcd.validate_hcd_plan(42)


if __name__ == "__main__":
    unittest.main(verbosity=2)
