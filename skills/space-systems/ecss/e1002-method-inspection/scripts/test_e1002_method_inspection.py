#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.2.5 inspection
method.

Exercises scripts/e1002_method_inspection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a checklist item
technique classifies as exactly visual or measurement and an
unrecognized technique raises; inspection is applicable only when no
special test equipment and no functional operation is required;
a visual item passes only when it conforms to the reference and a
non-bool flag raises; a measurement item passes only within its
tolerance band and a negative tolerance raises; a verification plan
entry missing a required field is flagged and its checklist is left
unevaluated; per-item statuses roll up to fail-over-pending-over-pass,
and an empty list or an unrecognized status raises; the full review
short-circuits to not-applicable or pending before evaluating a
malformed checklist item.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_method_inspection_logic as insp  # noqa: E402


class ClassifyInspectionTechniqueTest(unittest.TestCase):
    def test_visual_is_recognized(self):
        self.assertEqual(insp.classify_inspection_technique("visual"), "visual")

    def test_measurement_is_recognized(self):
        self.assertEqual(
            insp.classify_inspection_technique("measurement"), "measurement"
        )

    def test_unknown_technique_raises(self):
        with self.assertRaises(ValueError):
            insp.classify_inspection_technique("olfactory")


class InspectionMethodApplicableTest(unittest.TestCase):
    def test_neither_condition_is_applicable(self):
        self.assertTrue(insp.is_inspection_method_applicable(False, False))

    def test_special_equipment_not_applicable(self):
        self.assertFalse(insp.is_inspection_method_applicable(True, False))

    def test_functional_operation_not_applicable(self):
        self.assertFalse(insp.is_inspection_method_applicable(False, True))

    def test_both_conditions_not_applicable(self):
        self.assertFalse(insp.is_inspection_method_applicable(True, True))


class EvaluateVisualItemTest(unittest.TestCase):
    def test_conforms_passes(self):
        self.assertEqual(insp.evaluate_visual_item(True), "pass")

    def test_does_not_conform_fails(self):
        self.assertEqual(insp.evaluate_visual_item(False), "fail")

    def test_non_bool_raises(self):
        with self.assertRaises(ValueError):
            insp.evaluate_visual_item("yes")


class EvaluateMeasurementItemTest(unittest.TestCase):
    def test_within_tolerance_passes(self):
        self.assertEqual(insp.evaluate_measurement_item(10.2, 10.0, 0.5), "pass")

    def test_at_upper_bound_passes(self):
        self.assertEqual(insp.evaluate_measurement_item(10.5, 10.0, 0.5), "pass")

    def test_at_lower_bound_passes(self):
        self.assertEqual(insp.evaluate_measurement_item(9.5, 10.0, 0.5), "pass")

    def test_outside_tolerance_fails(self):
        self.assertEqual(insp.evaluate_measurement_item(11.0, 10.0, 0.5), "fail")

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            insp.evaluate_measurement_item(10.0, 10.0, -0.1)


class EvaluateChecklistItemTest(unittest.TestCase):
    def test_visual_item_dispatch(self):
        item = {"technique": "visual", "conforms_to_reference": True}
        self.assertEqual(insp.evaluate_checklist_item(item), "pass")

    def test_measurement_item_dispatch(self):
        item = {
            "technique": "measurement",
            "measured_value": 100.0,
            "nominal_value": 100.0,
            "tolerance": 1.0,
        }
        self.assertEqual(insp.evaluate_checklist_item(item), "pass")

    def test_unrecognized_technique_raises(self):
        with self.assertRaises(ValueError):
            insp.evaluate_checklist_item({"technique": "thermal_scan"})

    def test_missing_required_key_raises(self):
        with self.assertRaises(KeyError):
            insp.evaluate_checklist_item({"technique": "visual"})


class PlanCompletenessViolationsTest(unittest.TestCase):
    def _complete_entry(self):
        return {
            "requirement_id": "REQ-1",
            "technique": "visual",
            "acceptance_criteria": "no visible damage",
            "checklist": [{"technique": "visual", "conforms_to_reference": True}],
        }

    def test_complete_entry_has_no_violations(self):
        self.assertEqual(insp.plan_completeness_violations(self._complete_entry()), [])

    def test_missing_field_is_flagged(self):
        entry = self._complete_entry()
        del entry["acceptance_criteria"]
        violations = insp.plan_completeness_violations(entry)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["field"], "acceptance_criteria")

    def test_multiple_missing_fields_each_flagged(self):
        entry = {"requirement_id": "REQ-2"}
        violations = insp.plan_completeness_violations(entry)
        fields = {v["field"] for v in violations}
        self.assertEqual(fields, {"technique", "acceptance_criteria", "checklist"})

    def test_empty_checklist_is_flagged(self):
        entry = self._complete_entry()
        entry["checklist"] = []
        violations = insp.plan_completeness_violations(entry)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["field"], "checklist")


class RollupStatusTest(unittest.TestCase):
    def test_all_pass_is_pass(self):
        self.assertEqual(insp.rollup_status(["pass", "pass"]), "pass")

    def test_any_fail_is_fail(self):
        self.assertEqual(insp.rollup_status(["pass", "fail", "pending"]), "fail")

    def test_pending_without_fail_is_pending(self):
        self.assertEqual(insp.rollup_status(["pass", "pending"]), "pending")

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            insp.rollup_status([])

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            insp.rollup_status(["pass", "maybe"])


class InspectionReviewTest(unittest.TestCase):
    def test_fully_passing_review(self):
        entry = {
            "requirement_id": "REQ-10",
            "technique": "measurement",
            "acceptance_criteria": "bracket gap within tolerance",
            "requires_special_equipment": False,
            "requires_functional_operation": False,
            "checklist": [
                {
                    "technique": "measurement",
                    "measured_value": 5.0,
                    "nominal_value": 5.0,
                    "tolerance": 0.2,
                },
                {"technique": "visual", "conforms_to_reference": True},
            ],
        }
        review = insp.inspection_review(entry)
        self.assertTrue(review["applicability"])
        self.assertEqual(review["plan_violations"], [])
        self.assertEqual(review["status"], "pass")
        self.assertTrue(insp.is_inspection_compliant(review))

    def test_not_applicable_when_special_equipment_required(self):
        entry = {
            "requirement_id": "REQ-11",
            "technique": "measurement",
            "acceptance_criteria": "vibration response",
            "requires_special_equipment": True,
            "requires_functional_operation": False,
            "checklist": [{"technique": "thermal_scan"}],
        }
        review = insp.inspection_review(entry)
        self.assertFalse(review["applicability"])
        self.assertEqual(review["status"], insp.NOT_APPLICABLE)
        self.assertEqual(review["item_statuses"], [])

    def test_incomplete_plan_is_pending_without_evaluating_checklist(self):
        entry = {
            "requirement_id": "REQ-12",
            "technique": "visual",
            "requires_special_equipment": False,
            "requires_functional_operation": False,
            "checklist": [{"technique": "unobtainium_scan"}],
        }
        review = insp.inspection_review(entry)
        self.assertTrue(review["applicability"])
        self.assertTrue(review["plan_violations"])
        self.assertEqual(review["status"], "pending")
        self.assertEqual(review["item_statuses"], [])

    def test_failing_measurement_item_fails_review(self):
        entry = {
            "requirement_id": "REQ-13",
            "technique": "measurement",
            "acceptance_criteria": "fastener torque within tolerance",
            "requires_special_equipment": False,
            "requires_functional_operation": False,
            "checklist": [
                {
                    "technique": "measurement",
                    "measured_value": 12.0,
                    "nominal_value": 10.0,
                    "tolerance": 0.5,
                }
            ],
        }
        review = insp.inspection_review(entry)
        self.assertEqual(review["status"], "fail")
        self.assertFalse(insp.is_inspection_compliant(review))

    def test_review_raises_on_malformed_checklist_item_once_applicable_and_complete(
        self,
    ):
        entry = {
            "requirement_id": "REQ-14",
            "technique": "visual",
            "acceptance_criteria": "surface finish",
            "requires_special_equipment": False,
            "requires_functional_operation": False,
            "checklist": [{"technique": "spectral_analysis"}],
        }
        with self.assertRaises(ValueError):
            insp.inspection_review(entry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
