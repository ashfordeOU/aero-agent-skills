import unittest

from e1002_method_test_logic import (
    TestConditions,
    TestVerificationRecord,
    evaluate_applicability,
    evaluate_delegation,
    close_out,
    build_verification_summary,
)


def full_conditions(**overrides):
    base = dict(
        physically_measurable=True,
        test_article_available=True,
        environment_reproducible=True,
        pass_fail_criteria_defined=True,
    )
    base.update(overrides)
    return TestConditions(**base)


class ApplicabilityTests(unittest.TestCase):
    def test_all_conditions_met_is_applicable(self):
        applicable, unmet = evaluate_applicability(full_conditions())
        self.assertTrue(applicable)
        self.assertEqual(unmet, [])

    def test_missing_physically_measurable_is_unmet(self):
        applicable, unmet = evaluate_applicability(
            full_conditions(physically_measurable=False)
        )
        self.assertFalse(applicable)
        self.assertIn("physically_measurable", unmet)

    def test_missing_test_article_is_unmet(self):
        applicable, unmet = evaluate_applicability(
            full_conditions(test_article_available=False)
        )
        self.assertFalse(applicable)
        self.assertIn("test_article_available", unmet)

    def test_missing_environment_reproducible_is_unmet(self):
        applicable, unmet = evaluate_applicability(
            full_conditions(environment_reproducible=False)
        )
        self.assertFalse(applicable)
        self.assertIn("environment_reproducible", unmet)

    def test_missing_pass_fail_criteria_is_unmet(self):
        applicable, unmet = evaluate_applicability(
            full_conditions(pass_fail_criteria_defined=False)
        )
        self.assertFalse(applicable)
        self.assertIn("pass_fail_criteria_defined", unmet)

    def test_all_conditions_unmet_lists_all_four(self):
        applicable, unmet = evaluate_applicability(
            full_conditions(
                physically_measurable=False,
                test_article_available=False,
                environment_reproducible=False,
                pass_fail_criteria_defined=False,
            )
        )
        self.assertFalse(applicable)
        self.assertEqual(len(unmet), 4)


class RecordValidationTests(unittest.TestCase):
    def test_blank_requirement_id_rejected(self):
        with self.assertRaises(ValueError):
            TestVerificationRecord(requirement_id="  ", conditions=full_conditions())

    def test_bad_conditions_type_rejected(self):
        with self.assertRaises(TypeError):
            TestVerificationRecord(requirement_id="REQ-1", conditions={"a": 1})

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            TestVerificationRecord(
                requirement_id="REQ-1", conditions=full_conditions(), status="done"
            )


class DelegationTests(unittest.TestCase):
    def test_reference_present_no_embedded_procedure_is_compliant(self):
        record = TestVerificationRecord(
            requirement_id="REQ-1",
            conditions=full_conditions(),
            test_specification_ref="TS-100",
        )
        self.assertEqual(evaluate_delegation(record), [])

    def test_missing_reference_is_violation(self):
        record = TestVerificationRecord(
            requirement_id="REQ-2", conditions=full_conditions()
        )
        violations = evaluate_delegation(record)
        self.assertEqual(len(violations), 1)
        self.assertIn("missing", violations[0])

    def test_embedded_procedure_is_violation_even_with_reference(self):
        record = TestVerificationRecord(
            requirement_id="REQ-3",
            conditions=full_conditions(),
            test_specification_ref="TS-100",
            procedure_embedded=True,
        )
        violations = evaluate_delegation(record)
        self.assertEqual(len(violations), 1)
        self.assertIn("embedded", violations[0])

    def test_missing_reference_and_embedded_procedure_both_flagged(self):
        record = TestVerificationRecord(
            requirement_id="REQ-4",
            conditions=full_conditions(),
            procedure_embedded=True,
        )
        violations = evaluate_delegation(record)
        self.assertEqual(len(violations), 2)


class CloseOutTests(unittest.TestCase):
    def setUp(self):
        self.applicable_record = TestVerificationRecord(
            requirement_id="REQ-1",
            conditions=full_conditions(),
            test_specification_ref="TS-100",
        )
        self.not_applicable_record = TestVerificationRecord(
            requirement_id="REQ-2",
            conditions=full_conditions(environment_reproducible=False),
        )

    def test_passed_requires_evidence_ref(self):
        with self.assertRaises(ValueError):
            close_out(self.applicable_record, "passed")

    def test_passed_with_evidence_ref_succeeds(self):
        closed = close_out(self.applicable_record, "passed", evidence_ref="TR-1")
        self.assertEqual(closed.status, "passed")
        self.assertEqual(closed.evidence_ref, "TR-1")

    def test_failed_requires_evidence_ref(self):
        with self.assertRaises(ValueError):
            close_out(self.applicable_record, "failed")

    def test_waived_requires_waiver_ref(self):
        with self.assertRaises(ValueError):
            close_out(self.applicable_record, "waived")

    def test_waived_with_waiver_ref_succeeds(self):
        closed = close_out(self.applicable_record, "waived", waiver_ref="WV-1")
        self.assertEqual(closed.status, "waived")
        self.assertEqual(closed.waiver_ref, "WV-1")

    def test_cannot_close_terminal_status_when_not_applicable(self):
        with self.assertRaises(ValueError):
            close_out(self.not_applicable_record, "passed", evidence_ref="TR-1")

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            close_out(self.applicable_record, "cancelled")

    def test_close_out_does_not_mutate_input_record(self):
        close_out(self.applicable_record, "passed", evidence_ref="TR-1")
        self.assertEqual(self.applicable_record.status, "pending")

    def test_reopen_to_pending_clears_references(self):
        closed = close_out(self.applicable_record, "passed", evidence_ref="TR-1")
        reopened = close_out(closed, "pending")
        self.assertEqual(reopened.status, "pending")
        self.assertIsNone(reopened.evidence_ref)


class SummaryTests(unittest.TestCase):
    def test_empty_records_rejected(self):
        with self.assertRaises(ValueError):
            build_verification_summary([])

    def test_duplicate_requirement_id_rejected(self):
        records = [
            TestVerificationRecord(requirement_id="REQ-1", conditions=full_conditions()),
            TestVerificationRecord(requirement_id="REQ-1", conditions=full_conditions()),
        ]
        with self.assertRaises(ValueError):
            build_verification_summary(records)

    def test_fully_ready_set(self):
        record = close_out(
            TestVerificationRecord(
                requirement_id="REQ-1",
                conditions=full_conditions(),
                test_specification_ref="TS-100",
            ),
            "passed",
            evidence_ref="TR-1",
        )
        summary = build_verification_summary([record])
        self.assertTrue(summary["ready"])
        self.assertEqual(summary["applicable_count"], 1)
        self.assertEqual(summary["not_applicable"], [])
        self.assertEqual(summary["delegation_violations"], [])

    def test_pending_record_blocks_ready(self):
        record = TestVerificationRecord(
            requirement_id="REQ-1",
            conditions=full_conditions(),
            test_specification_ref="TS-100",
        )
        summary = build_verification_summary([record])
        self.assertFalse(summary["ready"])
        self.assertEqual(summary["status_counts"]["pending"], 1)

    def test_not_applicable_record_blocks_ready_and_is_listed(self):
        record = TestVerificationRecord(
            requirement_id="REQ-2",
            conditions=full_conditions(test_article_available=False),
        )
        summary = build_verification_summary([record])
        self.assertFalse(summary["ready"])
        self.assertEqual(len(summary["not_applicable"]), 1)
        self.assertEqual(summary["not_applicable"][0][0], "REQ-2")

    def test_delegation_violation_blocks_ready(self):
        record = TestVerificationRecord(
            requirement_id="REQ-3",
            conditions=full_conditions(),
        )
        summary = build_verification_summary([record])
        self.assertFalse(summary["ready"])
        self.assertGreaterEqual(len(summary["delegation_violations"]), 1)

    def test_mixed_set_counts_correctly(self):
        ready_record = close_out(
            TestVerificationRecord(
                requirement_id="REQ-1",
                conditions=full_conditions(),
                test_specification_ref="TS-100",
            ),
            "passed",
            evidence_ref="TR-1",
        )
        not_applicable_record = TestVerificationRecord(
            requirement_id="REQ-2",
            conditions=full_conditions(physically_measurable=False),
        )
        pending_record = TestVerificationRecord(
            requirement_id="REQ-3",
            conditions=full_conditions(),
            test_specification_ref="TS-101",
        )
        summary = build_verification_summary(
            [ready_record, not_applicable_record, pending_record]
        )
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["applicable_count"], 2)
        self.assertEqual(len(summary["not_applicable"]), 1)
        self.assertFalse(summary["ready"])


if __name__ == "__main__":
    unittest.main()
