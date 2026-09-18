"""Contract tests for the clause 5.8.9 GSE maintenance and readiness logic."""

import unittest

from q20_gse_maintenance_logic import (
    INTERVAL_BASES,
    INTERVENTION_REVERIFICATIONS,
    assess_gse_maintenance,
    maintenance_findings,
    normalize_token,
    readiness_verdict,
    required_reverifications,
    reverification_findings,
    task_status,
    validate_task,
)

TASKS = [
    {"id": "PM-01", "basis": "calendar-days", "interval": 365.0, "since_last": 120.0},
    {"id": "PM-02", "basis": "operating-hours", "interval": 500.0, "since_last": 210.0},
    {
        "id": "PM-03",
        "basis": "calendar-days",
        "interval": 180.0,
        "since_last": 40.0,
        "safety_critical": True,
    },
]


def _spec(**overrides):
    spec = {
        "tasks": [dict(t) for t in TASKS],
        "interventions": [],
        "completed_reverifications": [],
        "readiness_record_current": True,
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_case_and_separator_folded(self):
        self.assertEqual(normalize_token("Operating_Hours"), "operating-hours")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("")


class ValidateTaskTests(unittest.TestCase):
    def test_valid_task_is_normalized(self):
        record = validate_task(TASKS[0])
        self.assertEqual(record["id"], "pm-01")
        self.assertEqual(record["basis"], "calendar-days")

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(dict(TASKS[0], basis="whenever"))

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(dict(TASKS[0], interval=0.0))

    def test_negative_elapsed_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(dict(TASKS[0], since_last=-5.0))

    def test_missing_field_rejected(self):
        task = dict(TASKS[0])
        del task["interval"]
        with self.assertRaises(ValueError):
            validate_task(task)

    def test_basis_vocabulary_is_closed(self):
        self.assertEqual(set(INTERVAL_BASES), {"calendar-days", "operating-hours"})


class TaskStatusTests(unittest.TestCase):
    def test_task_inside_its_interval_reports_the_consumed_fraction(self):
        status = task_status(dict(TASKS[1]))
        self.assertEqual(status["state"], "within-interval")
        self.assertAlmostEqual(status["consumed_fraction"], 0.42, places=9)

    def test_task_exactly_on_its_interval_is_due_not_overdue(self):
        status = task_status(dict(TASKS[0], since_last=365.0))
        self.assertEqual(status["state"], "due")
        self.assertAlmostEqual(status["overdue_by"], 0.0, places=9)
        self.assertAlmostEqual(status["consumed_fraction"], 1.0, places=9)

    def test_task_past_its_interval_reports_how_far(self):
        status = task_status(dict(TASKS[0], since_last=400.0))
        self.assertEqual(status["state"], "overdue")
        self.assertAlmostEqual(status["overdue_by"], 35.0, places=9)

    def test_a_fresh_task_has_consumed_nothing(self):
        status = task_status(dict(TASKS[0], since_last=0.0))
        self.assertAlmostEqual(status["consumed_fraction"], 0.0, places=9)

    def test_safety_criticality_is_carried_through(self):
        self.assertTrue(task_status(dict(TASKS[2]))["safety_critical"])


class MaintenanceFindingTests(unittest.TestCase):
    def test_schedule_inside_its_intervals_is_clean(self):
        self.assertEqual(maintenance_findings(TASKS)["findings"], [])

    def test_overdue_task_is_named_with_its_basis(self):
        tasks = [dict(TASKS[1], since_last=610.0)]
        findings = maintenance_findings(tasks)["findings"]
        self.assertEqual(len(findings), 1)
        self.assertIn("operating-hours", findings[0])

    def test_safety_critical_task_on_its_interval_is_a_finding(self):
        tasks = [dict(TASKS[2], since_last=180.0)]
        findings = maintenance_findings(tasks)["findings"]
        self.assertTrue(any("reached its interval" in f for f in findings))

    def test_ordinary_task_on_its_interval_is_not_yet_a_finding(self):
        tasks = [dict(TASKS[0], since_last=365.0)]
        self.assertEqual(maintenance_findings(tasks)["findings"], [])

    def test_duplicate_task_identifier_rejected(self):
        with self.assertRaises(ValueError):
            maintenance_findings([dict(TASKS[0]), dict(TASKS[0])])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            maintenance_findings(TASKS[0])

    def test_every_task_gets_a_status(self):
        self.assertEqual(len(maintenance_findings(TASKS)["statuses"]), 3)


class ReverificationTests(unittest.TestCase):
    def test_no_intervention_owes_nothing(self):
        self.assertEqual(required_reverifications([]), [])

    def test_measuring_chain_work_owes_recalibration(self):
        self.assertEqual(required_reverifications(["measuring-chain"]), ["recalibration"])

    def test_load_path_work_owes_a_proof_reverification(self):
        self.assertIn("proof-load-reverification", required_reverifications(["load-path"]))

    def test_two_interventions_on_one_part_owe_one_reverification(self):
        self.assertEqual(
            required_reverifications(["control-software", "Control Software"]),
            ["functional-re-test"],
        )

    def test_unknown_intervention_rejected(self):
        with self.assertRaises(ValueError):
            required_reverifications(["paintwork"])

    def test_outstanding_reverification_named(self):
        findings = reverification_findings(["recalibration", "functional-re-test"], ["recalibration"])
        self.assertEqual(len(findings), 1)
        self.assertIn("functional-re-test", findings[0])

    def test_completed_reverification_clears_the_finding(self):
        self.assertEqual(reverification_findings(["recalibration"], ["Recalibration"]), [])

    def test_reverification_map_covers_every_maintained_part(self):
        self.assertGreaterEqual(len(INTERVENTION_REVERIFICATIONS), 5)

    def test_non_sequence_completed_rejected(self):
        with self.assertRaises(ValueError):
            reverification_findings(["recalibration"], "recalibration")


class ReadinessVerdictTests(unittest.TestCase):
    def test_clean_equipment_with_a_current_record_is_ready(self):
        self.assertEqual(readiness_verdict([], True), "ready")

    def test_clean_equipment_without_a_current_record_waits_on_the_record(self):
        self.assertEqual(readiness_verdict([], False), "ready-pending-record")

    def test_any_finding_makes_the_equipment_not_ready(self):
        self.assertEqual(readiness_verdict(["overdue"], True), "not-ready")

    def test_non_boolean_record_state_rejected(self):
        with self.assertRaises(ValueError):
            readiness_verdict([], "yes")


class AssessGseMaintenanceTests(unittest.TestCase):
    def test_maintained_equipment_is_ready(self):
        result = assess_gse_maintenance(_spec())
        self.assertEqual(result["verdict"], "ready")
        self.assertEqual(result["findings"], [])

    def test_overdue_task_makes_the_equipment_not_ready(self):
        spec = _spec()
        spec["tasks"][0]["since_last"] = 500.0
        result = assess_gse_maintenance(spec)
        self.assertEqual(result["verdict"], "not-ready")

    def test_outstanding_recalibration_makes_the_equipment_not_ready(self):
        spec = _spec(interventions=["measuring-chain"])
        result = assess_gse_maintenance(spec)
        self.assertEqual(result["verdict"], "not-ready")
        self.assertEqual(result["required_reverifications"], ["recalibration"])

    def test_completed_reverification_returns_the_equipment_to_service(self):
        spec = _spec(
            interventions=["measuring-chain", "load-path"],
            completed_reverifications=["recalibration", "proof-load-reverification"],
        )
        self.assertEqual(assess_gse_maintenance(spec)["verdict"], "ready")

    def test_stale_readiness_record_holds_an_otherwise_clean_item(self):
        result = assess_gse_maintenance(_spec(readiness_record_current=False))
        self.assertEqual(result["verdict"], "ready-pending-record")

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["interventions"]
        with self.assertRaises(ValueError):
            assess_gse_maintenance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_maintenance(["tasks"])

    def test_findings_accumulate_across_every_check(self):
        spec = _spec(
            interventions=["measuring-chain", "load-path", "pressure-boundary"],
            readiness_record_current=False,
        )
        spec["tasks"][0]["since_last"] = 500.0
        spec["tasks"][2]["since_last"] = 180.0
        result = assess_gse_maintenance(spec)
        self.assertEqual(result["verdict"], "not-ready")
        self.assertGreaterEqual(len(result["findings"]), 5)


if __name__ == "__main__":
    unittest.main()
