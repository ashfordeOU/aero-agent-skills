import unittest

from e1002_process_logic import (
    assign_responsibility,
    check_documentation,
    evaluate_process_record,
    rollup_activity_status,
    validate_closure,
    validate_doc_type,
    validate_phase,
    validate_product_level,
    validate_status,
)


class ValidateProductLevelTests(unittest.TestCase):
    def test_accepts_known_level(self):
        self.assertEqual(validate_product_level("subsystem"), "subsystem")

    def test_rejects_unknown_level(self):
        with self.assertRaises(ValueError):
            validate_product_level("planet")


class ValidatePhaseTests(unittest.TestCase):
    def test_accepts_known_phase(self):
        self.assertEqual(validate_phase("closure"), "closure")

    def test_rejects_unknown_phase(self):
        with self.assertRaises(ValueError):
            validate_phase("kickoff")


class ValidateStatusTests(unittest.TestCase):
    def test_accepts_known_status(self):
        self.assertEqual(validate_status("waived"), "waived")

    def test_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            validate_status("cancelled")


class ValidateDocTypeTests(unittest.TestCase):
    def test_accepts_known_doc_type(self):
        self.assertEqual(
            validate_doc_type("verification-report"), "verification-report"
        )

    def test_rejects_unknown_doc_type(self):
        with self.assertRaises(ValueError):
            validate_doc_type("meeting-minutes")


class AssignResponsibilityTests(unittest.TestCase):
    def test_supplier_always_executes(self):
        result = assign_responsibility("equipment", safety_critical=False)
        self.assertEqual(result["executor"], "supplier")

    def test_customer_retained_level_defaults_to_customer_approval(self):
        result = assign_responsibility(
            "system", safety_critical=False, delegation_agreement=True
        )
        self.assertEqual(result["approver"], "customer")

    def test_equipment_level_delegated_to_supplier(self):
        result = assign_responsibility(
            "equipment", safety_critical=False, delegation_agreement=True
        )
        self.assertEqual(result["approver"], "supplier")

    def test_equipment_level_without_delegation_defaults_to_customer(self):
        result = assign_responsibility(
            "equipment", safety_critical=False, delegation_agreement=False
        )
        self.assertEqual(result["approver"], "customer")

    def test_safety_critical_overrides_delegation(self):
        result = assign_responsibility(
            "equipment", safety_critical=True, delegation_agreement=True
        )
        self.assertEqual(result["approver"], "customer")

    def test_rejects_unknown_level(self):
        with self.assertRaises(ValueError):
            assign_responsibility("module", safety_critical=False)


class CheckDocumentationTests(unittest.TestCase):
    def test_planning_missing_plan(self):
        missing = check_documentation("planning", [])
        self.assertEqual(missing, ["verification-plan"])

    def test_planning_complete(self):
        missing = check_documentation("planning", ["verification-plan"])
        self.assertEqual(missing, [])

    def test_closure_requires_both_documents(self):
        missing = check_documentation(
            "closure", ["verification-control-document"]
        )
        self.assertEqual(missing, ["verification-report"])

    def test_closure_complete(self):
        missing = check_documentation(
            "closure",
            ["verification-control-document", "verification-report"],
        )
        self.assertEqual(missing, [])

    def test_rejects_unknown_document_in_record(self):
        with self.assertRaises(ValueError):
            check_documentation("planning", ["meeting-minutes"])


class RollupActivityStatusTests(unittest.TestCase):
    def test_any_open_dominates(self):
        self.assertEqual(
            rollup_activity_status(["closed", "open", "in-progress"]), "open"
        )

    def test_in_progress_dominates_over_resolved(self):
        self.assertEqual(
            rollup_activity_status(["closed", "in-progress", "waived"]),
            "in-progress",
        )

    def test_all_resolved_is_closed(self):
        self.assertEqual(
            rollup_activity_status(["closed", "waived", "closed"]), "closed"
        )

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            rollup_activity_status([])


class ValidateClosureTests(unittest.TestCase):
    def test_unresolved_activity_is_always_valid(self):
        activity = {
            "status": "open",
            "product_level": "system",
            "safety_critical": False,
            "approved_by": None,
        }
        result = validate_closure(activity)
        self.assertTrue(result["valid"])

    def test_closed_with_correct_approver_is_valid(self):
        activity = {
            "status": "closed",
            "product_level": "equipment",
            "safety_critical": False,
            "delegation_agreement": True,
            "approved_by": "supplier",
        }
        result = validate_closure(activity)
        self.assertTrue(result["valid"])

    def test_closed_with_wrong_approver_is_invalid(self):
        activity = {
            "status": "closed",
            "product_level": "system",
            "safety_critical": False,
            "approved_by": "supplier",
        }
        result = validate_closure(activity)
        self.assertFalse(result["valid"])
        self.assertEqual(result["required_approver"], "customer")

    def test_waived_safety_critical_requires_customer(self):
        activity = {
            "status": "waived",
            "product_level": "equipment",
            "safety_critical": True,
            "delegation_agreement": True,
            "approved_by": "supplier",
        }
        result = validate_closure(activity)
        self.assertFalse(result["valid"])
        self.assertEqual(result["required_approver"], "customer")


class EvaluateProcessRecordTests(unittest.TestCase):
    def test_fully_compliant_record(self):
        record = {
            "product_level": "equipment",
            "phase": "closure",
            "docs_on_record": [
                "verification-control-document",
                "verification-report",
            ],
            "activities": [
                {
                    "status": "closed",
                    "product_level": "equipment",
                    "safety_critical": False,
                    "delegation_agreement": True,
                    "approved_by": "supplier",
                }
            ],
        }
        result = evaluate_process_record(record)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["missing_docs"], [])
        self.assertEqual(result["overall_status"], "closed")
        self.assertEqual(result["closure_findings"], [])

    def test_missing_docs_blocks_compliance(self):
        record = {
            "product_level": "system",
            "phase": "closure",
            "docs_on_record": ["verification-control-document"],
            "activities": [
                {
                    "status": "closed",
                    "product_level": "system",
                    "safety_critical": False,
                    "approved_by": "customer",
                }
            ],
        }
        result = evaluate_process_record(record)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["missing_docs"], ["verification-report"])

    def test_open_activity_blocks_compliance_even_with_docs(self):
        record = {
            "product_level": "segment",
            "phase": "closure",
            "docs_on_record": [
                "verification-control-document",
                "verification-report",
            ],
            "activities": [
                {
                    "status": "open",
                    "product_level": "segment",
                    "safety_critical": False,
                    "approved_by": None,
                }
            ],
        }
        result = evaluate_process_record(record)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["overall_status"], "open")

    def test_wrong_approver_surfaces_as_closure_finding(self):
        record = {
            "product_level": "element",
            "phase": "closure",
            "docs_on_record": [
                "verification-control-document",
                "verification-report",
            ],
            "activities": [
                {
                    "status": "closed",
                    "product_level": "element",
                    "safety_critical": False,
                    "approved_by": "supplier",
                },
                {
                    "status": "closed",
                    "product_level": "element",
                    "safety_critical": False,
                    "approved_by": "customer",
                },
            ],
        }
        result = evaluate_process_record(record)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["closure_findings"]), 1)
        self.assertEqual(result["closure_findings"][0]["index"], 0)


if __name__ == "__main__":
    unittest.main()
