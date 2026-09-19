"""Contract test for the device-implementation-phase-review leaf (stdlib unittest)."""

import unittest

from e2040_device_implementation_phase_review_logic import (
    BLOCKING_SEVERITIES,
    CATEGORIES,
    DELIVERABLE_APPLICABILITY,
    DISPOSITIONS,
    MATURITY_ORDER,
    REQUIRED_MATURITY,
    SEVERITY_WEIGHT,
    assess_actions,
    assess_deliverables,
    assess_implementation_phase_review,
    assess_nonconformances,
    owed_deliverables,
    review_disposition,
    validate_action,
    validate_category,
    validate_deliverable,
    validate_nonconformance,
)


def deliverable(name, **kw):
    record = {
        "name": name,
        "maturity": REQUIRED_MATURITY[name],
        "customer_approved": True,
    }
    record.update(kw)
    return record


def full_set(category="A", **overrides):
    records = [deliverable(name) for name in owed_deliverables(category)]
    for name, changes in overrides.items():
        target = name.replace("_", "-")
        for record in records:
            if record["name"] == target:
                record.update(changes)
    return records


def action(aid="ACT-1", **kw):
    record = {
        "id": aid,
        "severity": "minor",
        "status": "open",
        "days_to_due": 14,
        "owner": "device supplier",
    }
    record.update(kw)
    return record


def nonconformance(nid="NCR-1", **kw):
    record = {"id": nid, "severity": "minor", "disposition": "open"}
    record.update(kw)
    return record


class TestValidateCategory(unittest.TestCase):
    def test_lower_case_category_is_accepted(self):
        self.assertEqual(validate_category("b"), "B")

    def test_every_declared_category_round_trips(self):
        for cat in CATEGORIES:
            self.assertEqual(validate_category(cat), cat)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            validate_category("E")

    def test_non_string_category_raises(self):
        with self.assertRaises(ValueError):
            validate_category(2)


class TestOwedDeliverables(unittest.TestCase):
    def test_category_a_owes_every_output(self):
        self.assertEqual(len(owed_deliverables("A")), len(DELIVERABLE_APPLICABILITY))

    def test_category_d_owes_fewer_than_category_a(self):
        self.assertLess(len(owed_deliverables("D")), len(owed_deliverables("A")))

    def test_category_d_does_not_owe_the_part_evaluation_specification(self):
        self.assertNotIn("escc-detail-specification", owed_deliverables("D"))

    def test_every_category_owes_the_production_test_report(self):
        for cat in CATEGORIES:
            self.assertIn("production-test-report", owed_deliverables(cat))


class TestValidateDeliverable(unittest.TestCase):
    def test_name_is_lower_cased(self):
        record = validate_deliverable(
            {"name": "Production-Test-Report", "maturity": "final", "customer_approved": True}
        )
        self.assertEqual(record["name"], "production-test-report")

    def test_unknown_deliverable_raises(self):
        with self.assertRaises(ValueError):
            validate_deliverable({"name": "lunch-menu", "maturity": "final"})

    def test_unknown_maturity_raises(self):
        with self.assertRaises(ValueError):
            validate_deliverable({"name": "production-test-report", "maturity": "nearly"})

    def test_non_boolean_approval_raises(self):
        with self.assertRaises(ValueError):
            validate_deliverable(
                {"name": "production-test-report", "maturity": "final", "customer_approved": 1}
            )

    def test_approval_defaults_to_false(self):
        record = validate_deliverable({"name": "production-test-report", "maturity": "final"})
        self.assertFalse(record["customer_approved"])


class TestAssessDeliverables(unittest.TestCase):
    def test_complete_set_is_fraction_one(self):
        report = assess_deliverables(full_set("A"), "A")
        self.assertAlmostEqual(report["deliverable_fraction"], 1.0, places=9)
        self.assertEqual(report["missing"], [])

    def test_missing_output_is_named(self):
        records = [d for d in full_set("A") if d["name"] != "production-test-report"]
        report = assess_deliverables(records, "A")
        self.assertEqual(report["missing"], ["production-test-report"])

    def test_immature_output_is_named(self):
        report = assess_deliverables(
            full_set("A", production_test_report={"maturity": "draft"}), "A"
        )
        self.assertEqual(report["immature"], ["production-test-report"])

    def test_maturity_above_the_requirement_is_accepted(self):
        report = assess_deliverables(
            full_set("A", escc_detail_specification={"maturity": "final"}), "A"
        )
        self.assertEqual(report["immature"], [])

    def test_unapproved_output_is_named(self):
        report = assess_deliverables(
            full_set("A", device_data_sheet={"customer_approved": False}), "A"
        )
        self.assertEqual(report["unapproved"], ["device-data-sheet"])

    def test_output_not_owed_by_the_category_is_reported(self):
        records = full_set("D") + [deliverable("escc-detail-specification")]
        report = assess_deliverables(records, "D")
        self.assertEqual(report["submitted_but_not_owed"], ["escc-detail-specification"])

    def test_duplicate_deliverable_raises(self):
        records = full_set("D") + [deliverable("production-test-report")]
        with self.assertRaises(ValueError):
            assess_deliverables(records, "D")

    def test_non_sequence_deliverables_raises(self):
        with self.assertRaises(ValueError):
            assess_deliverables({"name": "production-test-report"}, "A")


class TestAssessActions(unittest.TestCase):
    def test_no_actions_is_zero_load(self):
        report = assess_actions([])
        self.assertEqual(report["weighted_load"], 0)
        self.assertEqual(report["blocking_ids"], [])

    def test_closed_action_carries_no_load(self):
        report = assess_actions([action("ACT-1", status="closed", owner=None)])
        self.assertEqual(report["weighted_load"], 0)
        self.assertEqual(report["open_ids"], [])

    def test_open_minor_action_is_not_blocking(self):
        report = assess_actions([action("ACT-1")])
        self.assertEqual(report["blocking_ids"], [])
        self.assertEqual(report["weighted_load"], SEVERITY_WEIGHT["minor"])

    def test_open_major_action_is_blocking(self):
        report = assess_actions([action("ACT-1", severity="major")])
        self.assertEqual(report["blocking_ids"], ["ACT-1"])

    def test_overdue_minor_action_escalates_to_blocking(self):
        report = assess_actions([action("ACT-1", days_to_due=-3)])
        self.assertEqual(report["overdue_ids"], ["ACT-1"])
        self.assertEqual(report["blocking_ids"], ["ACT-1"])
        self.assertEqual(report["weighted_load"], SEVERITY_WEIGHT["major"])

    def test_overdue_critical_action_keeps_its_own_weight(self):
        report = assess_actions([action("ACT-1", severity="critical", days_to_due=-1)])
        self.assertEqual(report["weighted_load"], SEVERITY_WEIGHT["critical"])

    def test_open_action_without_owner_raises(self):
        with self.assertRaises(ValueError):
            validate_action(action("ACT-1", owner=None))

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_action(action("ACT-1", severity="annoying"))

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_action(action("ACT-1", status="pending"))

    def test_non_integer_due_offset_raises(self):
        with self.assertRaises(ValueError):
            validate_action(action("ACT-1", days_to_due=1.5))

    def test_duplicate_action_id_raises(self):
        with self.assertRaises(ValueError):
            assess_actions([action("ACT-1"), action("ACT-1")])


class TestAssessNonconformances(unittest.TestCase):
    def test_accepted_nonconformance_is_not_open(self):
        report = assess_nonconformances([nonconformance("NCR-1", disposition="accepted")])
        self.assertEqual(report["open_ids"], [])

    def test_open_major_nonconformance_is_blocking(self):
        report = assess_nonconformances([nonconformance("NCR-1", severity="major")])
        self.assertEqual(report["blocking_ids"], ["NCR-1"])

    def test_open_minor_nonconformance_is_not_blocking(self):
        report = assess_nonconformances([nonconformance("NCR-1")])
        self.assertEqual(report["blocking_ids"], [])
        self.assertEqual(report["open_ids"], ["NCR-1"])

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            validate_nonconformance(nonconformance("NCR-1", disposition="ignored"))

    def test_duplicate_nonconformance_id_raises(self):
        with self.assertRaises(ValueError):
            assess_nonconformances([nonconformance("NCR-1"), nonconformance("NCR-1")])


class TestReviewDisposition(unittest.TestCase):
    def test_clean_review_proceeds(self):
        verdict = review_disposition(
            assess_deliverables(full_set("A"), "A"), assess_actions([]), assess_nonconformances([])
        )
        self.assertEqual(verdict, "proceed")

    def test_open_minor_action_gives_proceed_with_actions(self):
        verdict = review_disposition(
            assess_deliverables(full_set("A"), "A"),
            assess_actions([action("ACT-1")]),
            assess_nonconformances([]),
        )
        self.assertEqual(verdict, "proceed-with-actions")

    def test_missing_output_holds_the_gate(self):
        records = [d for d in full_set("A") if d["name"] != "device-validation-plan"]
        verdict = review_disposition(
            assess_deliverables(records, "A"), assess_actions([]), assess_nonconformances([])
        )
        self.assertEqual(verdict, "hold")

    def test_every_verdict_is_a_declared_disposition(self):
        verdict = review_disposition(
            assess_deliverables(full_set("A"), "A"), assess_actions([]), assess_nonconformances([])
        )
        self.assertIn(verdict, DISPOSITIONS)

    def test_malformed_action_report_raises(self):
        with self.assertRaises(ValueError):
            review_disposition(
                assess_deliverables(full_set("A"), "A"), {"open_ids": []}, assess_nonconformances([])
            )


class TestAssessment(unittest.TestCase):
    def test_clean_category_d_review_proceeds(self):
        report = assess_implementation_phase_review(
            {"category": "D", "deliverables": full_set("D")}
        )
        self.assertEqual(report["disposition"], "proceed")
        self.assertTrue(report["may_proceed"])
        self.assertEqual(report["findings"], [])

    def test_overdue_minor_action_holds_the_gate(self):
        report = assess_implementation_phase_review(
            {
                "category": "D",
                "deliverables": full_set("D"),
                "actions": [action("ACT-1", days_to_due=-2)],
            }
        )
        self.assertEqual(report["disposition"], "hold")
        self.assertFalse(report["may_proceed"])

    def test_open_minor_nonconformance_still_proceeds_with_actions(self):
        report = assess_implementation_phase_review(
            {
                "category": "D",
                "deliverables": full_set("D"),
                "nonconformances": [nonconformance("NCR-1")],
            }
        )
        self.assertEqual(report["disposition"], "proceed-with-actions")

    def test_category_a_set_offered_for_category_d_raises_a_finding(self):
        report = assess_implementation_phase_review(
            {"category": "D", "deliverables": full_set("A")}
        )
        self.assertTrue(
            any("does not owe" in finding for finding in report["findings"])
        )

    def test_missing_spec_key_raises(self):
        with self.assertRaises(ValueError):
            assess_implementation_phase_review({"category": "A"})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_implementation_phase_review(["A"])

    def test_blocking_severities_are_a_subset_of_the_weight_table(self):
        for severity in BLOCKING_SEVERITIES:
            self.assertIn(severity, SEVERITY_WEIGHT)

    def test_maturity_ladder_covers_every_required_maturity(self):
        for maturity in REQUIRED_MATURITY.values():
            self.assertIn(maturity, MATURITY_ORDER)


if __name__ == "__main__":
    unittest.main()
