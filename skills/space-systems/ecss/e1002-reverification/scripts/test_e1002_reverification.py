#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §5.4.3 re-verification trigger
and scope assessment.

Exercises scripts/e1002_reverification_logic.py (stdlib unittest,
offline). Contract: a trigger_type categorizes into exactly one of
design_change, storage, re_flight, or anomaly, and an unrecognized
trigger raises; each trigger maps to a minimum scope level, and that
scope level enumerates required activities; missing_activities returns
the gap between required and documented activities; assess_reverification_item
integrates trigger, scope, and coverage into a findings record;
is_reverification_complete returns True only when no unclosed incomplete
scope findings remain.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_reverification_logic as rv  # noqa: E402


class CategorizeTriggerTest(unittest.TestCase):
    def test_design_change_minor_is_design_change(self):
        self.assertEqual(rv.categorize_trigger("design_change_minor"), "design_change")

    def test_design_change_major_is_design_change(self):
        self.assertEqual(rv.categorize_trigger("design_change_major"), "design_change")

    def test_storage_within_limit_is_storage(self):
        self.assertEqual(rv.categorize_trigger("storage_within_limit"), "storage")

    def test_storage_beyond_limit_is_storage(self):
        self.assertEqual(rv.categorize_trigger("storage_beyond_limit"), "storage")

    def test_re_flight_is_re_flight(self):
        self.assertEqual(rv.categorize_trigger("re_flight"), "re_flight")

    def test_anomaly_test_is_anomaly(self):
        self.assertEqual(rv.categorize_trigger("anomaly_test"), "anomaly")

    def test_anomaly_operation_is_anomaly(self):
        self.assertEqual(rv.categorize_trigger("anomaly_operation"), "anomaly")

    def test_anomaly_storage_is_anomaly(self):
        self.assertEqual(rv.categorize_trigger("anomaly_storage"), "anomaly")

    def test_unknown_trigger_raises(self):
        with self.assertRaises(ValueError):
            rv.categorize_trigger("spontaneous_combustion")


class ScopeLevelForTriggerTest(unittest.TestCase):
    def test_minor_change_yields_delta(self):
        self.assertEqual(rv.scope_level_for_trigger("design_change_minor"), "delta")

    def test_major_change_yields_full(self):
        self.assertEqual(rv.scope_level_for_trigger("design_change_major"), "full")

    def test_storage_within_limit_yields_inspection_only(self):
        self.assertEqual(
            rv.scope_level_for_trigger("storage_within_limit"), "inspection_only"
        )

    def test_storage_beyond_limit_yields_limited(self):
        self.assertEqual(rv.scope_level_for_trigger("storage_beyond_limit"), "limited")

    def test_re_flight_yields_delta_with_similarity(self):
        self.assertEqual(
            rv.scope_level_for_trigger("re_flight"), "delta_with_similarity"
        )

    def test_anomaly_test_yields_anomaly_scope(self):
        self.assertEqual(rv.scope_level_for_trigger("anomaly_test"), "anomaly")

    def test_anomaly_operation_yields_anomaly_scope(self):
        self.assertEqual(rv.scope_level_for_trigger("anomaly_operation"), "anomaly")

    def test_unknown_trigger_raises(self):
        with self.assertRaises(ValueError):
            rv.scope_level_for_trigger("warp_drive_failure")


class RequiredActivitiesTest(unittest.TestCase):
    def test_inspection_only_contains_inspection_and_review(self):
        acts = rv.required_activities("inspection_only")
        self.assertIn("inspection", acts)
        self.assertIn("documentation_review", acts)

    def test_inspection_only_excludes_environmental_test(self):
        acts = rv.required_activities("inspection_only")
        self.assertNotIn("environmental_test", acts)

    def test_full_scope_includes_structural_analysis(self):
        acts = rv.required_activities("full")
        self.assertIn("structural_analysis", acts)

    def test_full_scope_includes_thermal_analysis(self):
        acts = rv.required_activities("full")
        self.assertIn("thermal_analysis", acts)

    def test_full_scope_includes_environmental_test(self):
        acts = rv.required_activities("full")
        self.assertIn("environmental_test", acts)

    def test_delta_with_similarity_includes_similarity_assessment(self):
        acts = rv.required_activities("delta_with_similarity")
        self.assertIn("similarity_assessment", acts)

    def test_anomaly_scope_includes_anomaly_investigation(self):
        acts = rv.required_activities("anomaly")
        self.assertIn("anomaly_investigation", acts)

    def test_delta_scope_includes_delta_qualification(self):
        acts = rv.required_activities("delta")
        self.assertIn("delta_qualification", acts)

    def test_unrecognized_scope_raises(self):
        with self.assertRaises(ValueError):
            rv.required_activities("turbo_scope")


class MissingActivitiesTest(unittest.TestCase):
    def test_all_documented_returns_empty(self):
        documented = ["inspection", "documentation_review"]
        self.assertEqual(rv.missing_activities("inspection_only", documented), [])

    def test_missing_one_activity_returned(self):
        documented = ["inspection"]
        missing = rv.missing_activities("inspection_only", documented)
        self.assertIn("documentation_review", missing)

    def test_extra_documented_activities_not_penalized(self):
        documented = [
            "inspection",
            "documentation_review",
            "structural_analysis",
            "bonus_step",
        ]
        self.assertEqual(rv.missing_activities("inspection_only", documented), [])

    def test_empty_documented_returns_all_required(self):
        missing = rv.missing_activities("inspection_only", [])
        self.assertIn("inspection", missing)
        self.assertIn("documentation_review", missing)

    def test_result_is_sorted(self):
        missing = rv.missing_activities("inspection_only", [])
        self.assertEqual(missing, sorted(missing))

    def test_unrecognized_scope_raises(self):
        with self.assertRaises(ValueError):
            rv.missing_activities("unknown_scope", ["inspection"])


class AssessReverificationItemTest(unittest.TestCase):
    def _make_item(self, trigger_type, activities, waiver=False, item_id="unit-1"):
        return {
            "item_id": item_id,
            "trigger_type": trigger_type,
            "documented_activities": activities,
            "waiver_on_record": waiver,
        }

    def test_complete_inspection_only_scope_no_findings(self):
        item = self._make_item(
            "storage_within_limit", ["inspection", "documentation_review"]
        )
        result = rv.assess_reverification_item(item)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["findings"], [])

    def test_incomplete_scope_raises_incomplete_finding(self):
        item = self._make_item("design_change_minor", ["inspection"])
        result = rv.assess_reverification_item(item)
        self.assertTrue(result["missing"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(
            result["findings"][0]["issue"], "incomplete_reverification_scope"
        )

    def test_waiver_converts_incomplete_to_waiver_finding(self):
        item = self._make_item("design_change_minor", ["inspection"], waiver=True)
        result = rv.assess_reverification_item(item)
        self.assertTrue(result["missing"])
        self.assertEqual(result["findings"][0]["issue"], "scope_reduced_by_waiver")

    def test_complete_re_flight_scope_no_findings(self):
        activities = [
            "inspection",
            "similarity_assessment",
            "functional_test",
            "documentation_review",
        ]
        item = self._make_item("re_flight", activities)
        result = rv.assess_reverification_item(item)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["findings"], [])

    def test_trigger_category_in_result(self):
        item = self._make_item(
            "anomaly_operation",
            ["anomaly_investigation", "inspection", "functional_test", "documentation_review"],
        )
        result = rv.assess_reverification_item(item)
        self.assertEqual(result["trigger_category"], "anomaly")

    def test_scope_level_in_result(self):
        item = self._make_item(
            "anomaly_operation",
            ["anomaly_investigation", "inspection", "functional_test", "documentation_review"],
        )
        result = rv.assess_reverification_item(item)
        self.assertEqual(result["scope_level"], "anomaly")

    def test_unknown_trigger_raises(self):
        item = self._make_item("mystery_event", [])
        with self.assertRaises(ValueError):
            rv.assess_reverification_item(item)

    def test_incomplete_finding_lists_missing_activities(self):
        item = self._make_item("design_change_minor", ["inspection"])
        result = rv.assess_reverification_item(item)
        finding = result["findings"][0]
        self.assertIn("missing_activities", finding)
        self.assertIn("delta_qualification", finding["missing_activities"])


class IsReverificationCompleteTest(unittest.TestCase):
    def test_no_findings_is_complete(self):
        assessment = {
            "item_id": "unit-1",
            "trigger_category": "storage",
            "scope_level": "inspection_only",
            "missing": [],
            "findings": [],
        }
        self.assertTrue(rv.is_reverification_complete(assessment))

    def test_incomplete_scope_finding_is_not_complete(self):
        assessment = {
            "item_id": "unit-1",
            "trigger_category": "design_change",
            "scope_level": "delta",
            "missing": ["delta_qualification"],
            "findings": [
                {
                    "issue": "incomplete_reverification_scope",
                    "item": "unit-1",
                    "scope_level": "delta",
                    "missing_activities": ["delta_qualification"],
                }
            ],
        }
        self.assertFalse(rv.is_reverification_complete(assessment))

    def test_waiver_finding_is_complete(self):
        assessment = {
            "item_id": "unit-2",
            "trigger_category": "design_change",
            "scope_level": "delta",
            "missing": ["delta_qualification"],
            "findings": [
                {
                    "issue": "scope_reduced_by_waiver",
                    "item": "unit-2",
                    "scope_level": "delta",
                    "waived_activities": ["delta_qualification"],
                }
            ],
        }
        self.assertTrue(rv.is_reverification_complete(assessment))

    def test_empty_findings_list_is_complete(self):
        assessment = {"findings": []}
        self.assertTrue(rv.is_reverification_complete(assessment))


if __name__ == "__main__":
    unittest.main()
