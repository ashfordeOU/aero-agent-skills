"""
Offline unit tests for e1003_management_logic.py.

Run:  python3 test_e1003_management.py
Pass: prints "OK" (no network, no external deps).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_management_logic import (
    REQUIRED_READINESS_CONDITIONS,
    CAMPAIGN_PHASE_ORDER,
    assign_responsibility,
    check_readiness_conditions,
    validate_campaign_phases,
    build_campaign_plan,
    InvalidTestEventError,
    InvalidPhaseError,
    UnknownResponsibilityError,
)


ALL_CONDITIONS_MET = list(REQUIRED_READINESS_CONDITIONS)


# ---------------------------------------------------------------------------
# assign_responsibility tests
# ---------------------------------------------------------------------------

class TestAssignResponsibility(unittest.TestCase):

    def test_customer_led_acceptance(self):
        result = assign_responsibility({"test_id": "T01", "test_type": "acceptance"})
        self.assertEqual(result["responsibility"], "customer")
        self.assertEqual(result["source"], "rule")

    def test_customer_led_qualification_witness(self):
        result = assign_responsibility({"test_id": "T02", "test_type": "qualification_witness"})
        self.assertEqual(result["responsibility"], "customer")
        self.assertEqual(result["source"], "rule")

    def test_supplier_led_unit(self):
        result = assign_responsibility({"test_id": "T03", "test_type": "unit"})
        self.assertEqual(result["responsibility"], "supplier")
        self.assertEqual(result["source"], "rule")

    def test_supplier_led_environmental(self):
        result = assign_responsibility({"test_id": "T04", "test_type": "environmental"})
        self.assertEqual(result["responsibility"], "supplier")
        self.assertEqual(result["source"], "rule")

    def test_joint_system(self):
        result = assign_responsibility({"test_id": "T05", "test_type": "system"})
        self.assertEqual(result["responsibility"], "joint")
        self.assertEqual(result["source"], "rule")

    def test_joint_integration(self):
        result = assign_responsibility({"test_id": "T06", "test_type": "integration"})
        self.assertEqual(result["responsibility"], "joint")
        self.assertEqual(result["source"], "rule")

    def test_override_respected(self):
        result = assign_responsibility(
            {"test_id": "T07", "test_type": "unit", "override_responsibility": "joint"}
        )
        self.assertEqual(result["responsibility"], "joint")
        self.assertEqual(result["source"], "override")

    def test_invalid_override_raises(self):
        with self.assertRaises(UnknownResponsibilityError):
            assign_responsibility(
                {"test_id": "T08", "test_type": "unit", "override_responsibility": "prime"}
            )

    def test_unknown_test_type_raises(self):
        with self.assertRaises(InvalidTestEventError):
            assign_responsibility({"test_id": "T09", "test_type": "exotic_vibration"})

    def test_missing_test_id_raises(self):
        with self.assertRaises(InvalidTestEventError):
            assign_responsibility({"test_type": "unit"})

    def test_missing_test_type_raises(self):
        with self.assertRaises(InvalidTestEventError):
            assign_responsibility({"test_id": "T11"})

    def test_test_type_case_insensitive(self):
        result = assign_responsibility({"test_id": "T12", "test_type": "ACCEPTANCE"})
        self.assertEqual(result["responsibility"], "customer")

    def test_combined_operations_is_joint(self):
        result = assign_responsibility({"test_id": "T13", "test_type": "combined_operations"})
        self.assertEqual(result["responsibility"], "joint")


# ---------------------------------------------------------------------------
# check_readiness_conditions tests
# ---------------------------------------------------------------------------

class TestCheckReadinessConditions(unittest.TestCase):

    def test_all_conditions_met_is_ready(self):
        result = check_readiness_conditions(
            {"test_id": "R01", "conditions_met": ALL_CONDITIONS_MET}
        )
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["unmet"], [])

    def test_no_conditions_met_is_not_ready(self):
        result = check_readiness_conditions(
            {"test_id": "R02", "conditions_met": []}
        )
        self.assertEqual(result["status"], "not_ready")
        self.assertEqual(len(result["unmet"]), len(REQUIRED_READINESS_CONDITIONS))

    def test_partial_conditions_is_not_ready(self):
        partial = ALL_CONDITIONS_MET[:3]
        result = check_readiness_conditions(
            {"test_id": "R03", "conditions_met": partial}
        )
        self.assertEqual(result["status"], "not_ready")
        self.assertEqual(len(result["satisfied"]), 3)
        self.assertEqual(len(result["unmet"]), len(REQUIRED_READINESS_CONDITIONS) - 3)

    def test_single_missing_condition_blocks_authorisation(self):
        missing_one = [c for c in ALL_CONDITIONS_MET if c != "safety_clearance_granted"]
        result = check_readiness_conditions(
            {"test_id": "R04", "conditions_met": missing_one}
        )
        self.assertEqual(result["status"], "not_ready")
        self.assertIn("safety_clearance_granted", result["unmet"])

    def test_unknown_conditions_surfaced(self):
        conditions = ALL_CONDITIONS_MET + ["custom_lab_approval"]
        result = check_readiness_conditions(
            {"test_id": "R05", "conditions_met": conditions}
        )
        self.assertIn("custom_lab_approval", result["unknown_conditions"])
        self.assertEqual(result["status"], "ready")

    def test_missing_test_id_raises(self):
        with self.assertRaises(InvalidTestEventError):
            check_readiness_conditions({"conditions_met": ALL_CONDITIONS_MET})

    def test_missing_conditions_met_raises(self):
        with self.assertRaises(InvalidTestEventError):
            check_readiness_conditions({"test_id": "R07"})

    def test_satisfied_list_correct(self):
        two = ALL_CONDITIONS_MET[:2]
        result = check_readiness_conditions({"test_id": "R08", "conditions_met": two})
        self.assertEqual(result["satisfied"], two)


# ---------------------------------------------------------------------------
# validate_campaign_phases tests
# ---------------------------------------------------------------------------

class TestValidateCampaignPhases(unittest.TestCase):

    def test_full_canonical_sequence_is_valid(self):
        result = validate_campaign_phases(list(CAMPAIGN_PHASE_ORDER))
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["issues"], [])

    def test_tailored_subset_is_valid(self):
        # planning and execution only — preparation, readiness_review omitted
        result = validate_campaign_phases(["planning", "execution", "closeout"])
        self.assertEqual(result["status"], "valid")

    def test_out_of_order_detected(self):
        result = validate_campaign_phases(["execution", "planning"])
        self.assertEqual(result["status"], "out_of_order")
        self.assertTrue(len(result["issues"]) > 0)

    def test_unknown_phase_detected(self):
        result = validate_campaign_phases(["planning", "launch_day", "closeout"])
        self.assertEqual(result["status"], "unknown_phase")
        self.assertTrue(any("launch_day" in issue for issue in result["issues"]))

    def test_duplicate_phase_detected(self):
        result = validate_campaign_phases(["planning", "planning", "closeout"])
        self.assertEqual(result["status"], "duplicate_phase")

    def test_empty_list_is_valid(self):
        result = validate_campaign_phases([])
        self.assertEqual(result["status"], "valid")

    def test_non_list_raises(self):
        with self.assertRaises(InvalidPhaseError):
            validate_campaign_phases("planning,execution")

    def test_single_phase_is_valid(self):
        result = validate_campaign_phases(["readiness_review"])
        self.assertEqual(result["status"], "valid")

    def test_readiness_review_before_execution_required(self):
        # reversed order must fail
        result = validate_campaign_phases(["execution", "readiness_review"])
        self.assertEqual(result["status"], "out_of_order")


# ---------------------------------------------------------------------------
# build_campaign_plan tests
# ---------------------------------------------------------------------------

class TestBuildCampaignPlan(unittest.TestCase):

    def _event(self, test_id, test_type, conditions=None):
        return {
            "test_id": test_id,
            "test_type": test_type,
            "conditions_met": conditions if conditions is not None else ALL_CONDITIONS_MET,
        }

    def test_single_event_ready(self):
        plan = build_campaign_plan([self._event("P01", "unit")])
        self.assertTrue(plan["campaign_ready"])
        self.assertEqual(plan["event_count"], 1)
        self.assertEqual(plan["responsibility_tally"]["supplier"], 1)

    def test_mixed_events_all_ready(self):
        events = [
            self._event("P02", "acceptance"),
            self._event("P03", "unit"),
            self._event("P04", "system"),
        ]
        plan = build_campaign_plan(events)
        self.assertTrue(plan["campaign_ready"])
        self.assertEqual(plan["responsibility_tally"]["customer"], 1)
        self.assertEqual(plan["responsibility_tally"]["supplier"], 1)
        self.assertEqual(plan["responsibility_tally"]["joint"], 1)

    def test_one_unready_event_blocks_campaign(self):
        events = [
            self._event("P05", "unit"),
            self._event("P06", "acceptance", conditions=[]),
        ]
        plan = build_campaign_plan(events)
        self.assertFalse(plan["campaign_ready"])

    def test_empty_events_raises(self):
        with self.assertRaises(InvalidTestEventError):
            build_campaign_plan([])

    def test_event_count_correct(self):
        events = [self._event(f"P{i}", "unit") for i in range(5)]
        plan = build_campaign_plan(events)
        self.assertEqual(plan["event_count"], 5)

    def test_unmet_conditions_surfaced_per_event(self):
        events = [self._event("P10", "unit", conditions=[])]
        plan = build_campaign_plan(events)
        ev = plan["events"][0]
        self.assertEqual(ev["readiness_status"], "not_ready")
        self.assertEqual(len(ev["unmet_conditions"]), len(REQUIRED_READINESS_CONDITIONS))


if __name__ == "__main__":
    unittest.main()
