#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.4.5 in-orbit
verification.

Exercises scripts/e1002_in_orbit_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a requirement needs the
in-orbit stage only when flagged onorbit_environment_dependent;
closure follows the commissioning-evidence outcome (fail beats
not_run beats pass, no covering record leaves it open); the matrix
covers every requirement with no duplicates; an in-orbit anomaly
reopens a currently-verified affected requirement to
reverification_required or reverified, and leaves everything else
unchanged.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_in_orbit_logic as io  # noqa: E402


class RequiresInOrbitStageTest(unittest.TestCase):
    def test_true_when_flagged(self):
        self.assertTrue(io.requires_in_orbit_stage({"onorbit_environment_dependent": True}))

    def test_false_when_not_flagged(self):
        self.assertFalse(io.requires_in_orbit_stage({"onorbit_environment_dependent": False}))


class EvidenceForRequirementTest(unittest.TestCase):
    RECORDS = [
        {"activity_id": "COM-01", "requirement_ids": ["REQ-001"], "result": "pass"},
        {"activity_id": "COM-02", "requirement_ids": ["REQ-001", "REQ-002"], "result": "fail"},
        {"activity_id": "COM-03", "requirement_ids": ["REQ-003"], "result": "not_run"},
    ]

    def test_collects_in_record_order(self):
        self.assertEqual(io.evidence_for_requirement("REQ-001", self.RECORDS), ["pass", "fail"])

    def test_empty_when_uncovered(self):
        self.assertEqual(io.evidence_for_requirement("REQ-999", self.RECORDS), [])


class CommissioningOutcomeTest(unittest.TestCase):
    def test_all_pass_is_pass(self):
        records = [{"activity_id": "A", "requirement_ids": ["REQ-001"], "result": "pass"}]
        self.assertEqual(io.commissioning_outcome("REQ-001", records), "pass")

    def test_any_fail_wins_over_pass(self):
        records = [
            {"activity_id": "A", "requirement_ids": ["REQ-001"], "result": "pass"},
            {"activity_id": "B", "requirement_ids": ["REQ-001"], "result": "fail"},
        ]
        self.assertEqual(io.commissioning_outcome("REQ-001", records), "fail")

    def test_not_run_wins_over_pass_when_no_fail(self):
        records = [
            {"activity_id": "A", "requirement_ids": ["REQ-001"], "result": "pass"},
            {"activity_id": "B", "requirement_ids": ["REQ-001"], "result": "not_run"},
        ]
        self.assertEqual(io.commissioning_outcome("REQ-001", records), "not_run")

    def test_no_evidence(self):
        self.assertEqual(io.commissioning_outcome("REQ-001", []), "no_commissioning_evidence")

    def test_unknown_result_raises(self):
        records = [{"activity_id": "A", "requirement_ids": ["REQ-001"], "result": "partial"}]
        with self.assertRaises(ValueError):
            io.commissioning_outcome("REQ-001", records)


class CloseInOrbitVerificationTest(unittest.TestCase):
    def test_not_applicable_when_not_flagged(self):
        requirement = {"id": "REQ-001", "onorbit_environment_dependent": False}
        self.assertEqual(
            io.close_in_orbit_verification(requirement, []),
            {"id": "REQ-001", "status": "not_applicable"},
        )

    def test_verified_on_passing_evidence(self):
        requirement = {"id": "REQ-001", "onorbit_environment_dependent": True}
        records = [{"activity_id": "A", "requirement_ids": ["REQ-001"], "result": "pass"}]
        self.assertEqual(
            io.close_in_orbit_verification(requirement, records),
            {"id": "REQ-001", "status": "verified"},
        )

    def test_open_when_uncovered(self):
        requirement = {"id": "REQ-001", "onorbit_environment_dependent": True}
        self.assertEqual(
            io.close_in_orbit_verification(requirement, []),
            {"id": "REQ-001", "status": "open"},
        )

    def test_failed_on_failing_evidence(self):
        requirement = {"id": "REQ-001", "onorbit_environment_dependent": True}
        records = [{"activity_id": "A", "requirement_ids": ["REQ-001"], "result": "fail"}]
        self.assertEqual(
            io.close_in_orbit_verification(requirement, records),
            {"id": "REQ-001", "status": "failed"},
        )

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            io.close_in_orbit_verification({"onorbit_environment_dependent": True}, [])


class BuildInOrbitMatrixTest(unittest.TestCase):
    REQUIREMENTS = [
        {"id": "REQ-001", "onorbit_environment_dependent": True},
        {"id": "REQ-002", "onorbit_environment_dependent": False},
    ]
    RECORDS = [{"activity_id": "A", "requirement_ids": ["REQ-001"], "result": "pass"}]

    def test_matrix_order_and_content(self):
        matrix = io.build_in_orbit_matrix(self.REQUIREMENTS, self.RECORDS)
        self.assertEqual(
            matrix,
            [
                {"id": "REQ-001", "status": "verified"},
                {"id": "REQ-002", "status": "not_applicable"},
            ],
        )

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            io.build_in_orbit_matrix(self.REQUIREMENTS + [self.REQUIREMENTS[0]], self.RECORDS)


class ApplyAnomalyReverificationTest(unittest.TestCase):
    MATRIX = [
        {"id": "REQ-001", "status": "verified"},
        {"id": "REQ-002", "status": "open"},
        {"id": "REQ-003", "status": "verified"},
    ]

    def test_verified_affected_requires_reverification(self):
        anomaly = {"affected_ids": ["REQ-001"], "corrective_action_verified": False}
        result = io.apply_anomaly_reverification(self.MATRIX, anomaly)
        self.assertEqual(result[0], {"id": "REQ-001", "status": "reverification_required"})

    def test_verified_affected_with_corrective_action_is_reverified(self):
        anomaly = {"affected_ids": ["REQ-001"], "corrective_action_verified": True}
        result = io.apply_anomaly_reverification(self.MATRIX, anomaly)
        self.assertEqual(result[0], {"id": "REQ-001", "status": "reverified"})

    def test_non_verified_affected_entry_unchanged(self):
        anomaly = {"affected_ids": ["REQ-002"], "corrective_action_verified": True}
        result = io.apply_anomaly_reverification(self.MATRIX, anomaly)
        self.assertEqual(result[1], {"id": "REQ-002", "status": "open"})

    def test_unaffected_entries_unchanged(self):
        anomaly = {"affected_ids": ["REQ-001"], "corrective_action_verified": True}
        result = io.apply_anomaly_reverification(self.MATRIX, anomaly)
        self.assertEqual(result[2], {"id": "REQ-003", "status": "verified"})

    def test_does_not_mutate_input(self):
        before = [dict(e) for e in self.MATRIX]
        io.apply_anomaly_reverification(self.MATRIX, {"affected_ids": ["REQ-001"], "corrective_action_verified": True})
        self.assertEqual(self.MATRIX, before)

    def test_unknown_affected_id_raises(self):
        anomaly = {"affected_ids": ["REQ-999"], "corrective_action_verified": True}
        with self.assertRaises(ValueError):
            io.apply_anomaly_reverification(self.MATRIX, anomaly)


class OpenInOrbitItemsTest(unittest.TestCase):
    def test_lists_unclosed_statuses_in_order(self):
        matrix = [
            {"id": "REQ-001", "status": "verified"},
            {"id": "REQ-002", "status": "open"},
            {"id": "REQ-003", "status": "failed"},
            {"id": "REQ-004", "status": "reverification_required"},
            {"id": "REQ-005", "status": "reverified"},
            {"id": "REQ-006", "status": "not_applicable"},
        ]
        self.assertEqual(
            io.open_in_orbit_items(matrix),
            ["REQ-002", "REQ-003", "REQ-004"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
