"""Contract tests for the clause 6.5 class 3 quality assurance arrangement logic."""

import unittest

from q6013_class_3_component_quality_assurance_logic import (
    COVERAGE_TOLERANCE,
    GRADED_FUNCTIONS,
    QA_DUTY_CATALOGUE,
    RELIEF_AUTHORITY_ORDER,
    assess_quality_assurance,
    authority_rank,
    coverage_figures,
    dispose_duty,
    duty_catalogue,
    duty_weight,
    is_mandatory_duty,
    plan_age_months,
    plan_current,
    relief_admissible,
    reporting_line_embedded,
    required_relief_authority,
)


def duty_record(duty, **overrides):
    """Return a fully evidenced declaration for one duty."""
    record = {
        "duty": duty,
        "owner": "parts quality engineer",
        "procedure_reference": "QP-6500-%s" % duty,
        "evidence_reference": "QR-6500-%s" % duty,
    }
    record.update(overrides)
    return record


def base_policy(**overrides):
    policy = {
        "plain_coverage_floor": 0.9,
        "evidenced_coverage_floor": 0.6,
        "weighted_coverage_floor": 0.6,
        "plan_revalidation_months": 24,
        "require_escalation_route": True,
    }
    policy.update(overrides)
    return policy


def base_arrangement(**overrides):
    """Return an arrangement declaring every catalogue duty with full evidence."""
    arrangement = {
        "policy": base_policy(),
        "criticality": 3,
        "declared_duties": [duty_record(duty) for duty in duty_catalogue()],
        "reporting_line": "quality",
        "quality_plan_reference": "PA-PLAN-3",
        "quality_plan_issue_date": "2025-09-01",
        "escalation_route": None,
    }
    arrangement.update(overrides)
    return arrangement


class CatalogueTests(unittest.TestCase):
    def test_catalogue_is_stable_and_sorted(self):
        self.assertEqual(duty_catalogue(), tuple(sorted(QA_DUTY_CATALOGUE)))

    def test_alert_watch_stays_mandatory_at_the_lowest_class(self):
        self.assertTrue(is_mandatory_duty("alert-watch"))

    def test_audit_and_surveillance_is_discretionary(self):
        self.assertFalse(is_mandatory_duty("audit-and-surveillance"))

    def test_every_duty_carries_a_positive_weight(self):
        for duty in duty_catalogue():
            self.assertGreaterEqual(duty_weight(duty), 1)

    def test_unknown_duty_rejected(self):
        with self.assertRaises(ValueError):
            is_mandatory_duty("tea-rota")

    def test_non_string_duty_rejected(self):
        with self.assertRaises(ValueError):
            duty_weight(7)


class AuthorityTests(unittest.TestCase):
    def test_authority_order_increases(self):
        self.assertLess(authority_rank("project-manager"), authority_rank("customer"))

    def test_unknown_authority_rejected(self):
        with self.assertRaises(ValueError):
            authority_rank("the corridor")

    def test_mandatory_duty_is_not_relievable(self):
        self.assertEqual(
            required_relief_authority("nonconformance-processing", 3), "not-relievable"
        )

    def test_heavy_discretionary_duty_earns_the_customer(self):
        self.assertEqual(
            required_relief_authority("incoming-verification", 3), "customer"
        )

    def test_light_discretionary_duty_earns_the_quality_manager(self):
        self.assertEqual(
            required_relief_authority("training-and-certification", 4),
            "project-quality-manager",
        )

    def test_criticality_raises_the_authority_one_level(self):
        self.assertEqual(
            required_relief_authority("training-and-certification", 1),
            "project-manager",
        )

    def test_criticality_bump_is_capped_at_the_customer(self):
        self.assertEqual(
            required_relief_authority("incoming-verification", 1), "customer"
        )

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            required_relief_authority("audit-and-surveillance", 9)


class ReliefTests(unittest.TestCase):
    def test_relief_against_a_mandatory_duty_is_refused(self):
        verdict = relief_admissible("alert-watch", 3, "no staff", "customer")
        self.assertFalse(verdict["admissible"])

    def test_relief_without_a_rationale_is_refused(self):
        verdict = relief_admissible("audit-and-surveillance", 4, "   ", "customer")
        self.assertFalse(verdict["admissible"])

    def test_relief_below_the_required_authority_is_refused(self):
        verdict = relief_admissible(
            "incoming-verification", 4, "catalogue parts only", "project-manager"
        )
        self.assertFalse(verdict["admissible"])

    def test_relief_at_the_required_authority_is_admissible(self):
        verdict = relief_admissible(
            "incoming-verification", 4, "catalogue parts only", "customer"
        )
        self.assertTrue(verdict["admissible"])

    def test_relief_above_the_required_authority_is_admissible(self):
        verdict = relief_admissible(
            "training-and-certification", 4, "single operator", "customer"
        )
        self.assertTrue(verdict["admissible"])

    def test_every_refusal_is_reported_together(self):
        verdict = relief_admissible("records-retention", 3, "", "none")
        self.assertGreaterEqual(len(verdict["refusals"]), 2)


class DispositionTests(unittest.TestCase):
    def test_full_record_is_retained_and_evidenced(self):
        entry = dispose_duty(
            "traceability-records", duty_record("traceability-records"), 3
        )
        self.assertEqual(entry["status"], "retained")
        self.assertTrue(entry["evidenced"])

    def test_undeclared_duty_is_unassigned(self):
        entry = dispose_duty("traceability-records", None, 3)
        self.assertEqual(entry["status"], "unassigned")
        self.assertIn("never declared", entry["gap"])

    def test_missing_owner_is_reported_first(self):
        entry = dispose_duty(
            "traceability-records",
            duty_record("traceability-records", owner=None, procedure_reference=None),
            3,
        )
        self.assertIn("no owner", entry["gap"])

    def test_missing_procedure_leaves_the_duty_unassigned(self):
        entry = dispose_duty(
            "traceability-records",
            duty_record("traceability-records", procedure_reference="  "),
            3,
        )
        self.assertEqual(entry["status"], "unassigned")

    def test_missing_evidence_is_retained_but_not_evidenced(self):
        entry = dispose_duty(
            "traceability-records",
            duty_record("traceability-records", evidence_reference=None),
            3,
        )
        self.assertEqual(entry["status"], "retained")
        self.assertFalse(entry["evidenced"])

    def test_admissible_relief_is_relieved_and_not_evidenced(self):
        entry = dispose_duty(
            "audit-and-surveillance",
            {
                "duty": "audit-and-surveillance",
                "relief_requested": True,
                "relief_rationale": "no supplier access at this class",
                "relief_approval_authority": "project-quality-manager",
            },
            4,
        )
        self.assertEqual(entry["status"], "relieved")
        self.assertFalse(entry["evidenced"])

    def test_refused_relief_leaves_the_duty_unassigned(self):
        entry = dispose_duty(
            "audit-and-surveillance",
            {
                "duty": "audit-and-surveillance",
                "relief_requested": True,
                "relief_rationale": None,
                "relief_approval_authority": "project-quality-manager",
            },
            4,
        )
        self.assertEqual(entry["status"], "unassigned")

    def test_unknown_record_key_rejected(self):
        with self.assertRaises(ValueError):
            dispose_duty(
                "traceability-records",
                dict(duty_record("traceability-records"), budget="none"),
                3,
            )

    def test_non_boolean_relief_flag_rejected(self):
        with self.assertRaises(ValueError):
            dispose_duty(
                "traceability-records",
                duty_record("traceability-records", relief_requested="yes"),
                3,
            )


class CoverageTests(unittest.TestCase):
    def test_full_catalogue_reaches_one(self):
        result = assess_quality_assurance(base_arrangement(), "2026-09-14")
        self.assertAlmostEqual(result["coverage"]["plain_coverage"], 1.0, places=9)
        self.assertAlmostEqual(result["coverage"]["evidenced_coverage"], 1.0, places=9)

    def test_report_length_matches_the_catalogue(self):
        arrangement = base_arrangement(
            declared_duties=[duty_record("alert-watch")]
        )
        result = assess_quality_assurance(arrangement, "2026-09-14")
        self.assertEqual(len(result["duties"]), len(QA_DUTY_CATALOGUE))

    def test_weighted_coverage_differs_from_the_plain_count(self):
        dispositions = [
            {"status": "retained", "evidenced": True, "weight": 3},
            {"status": "retained", "evidenced": False, "weight": 1},
        ]
        figures = coverage_figures(dispositions)
        self.assertAlmostEqual(figures["evidenced_coverage"], 0.5, places=9)
        self.assertAlmostEqual(
            figures["weighted_evidenced_coverage"], 0.75, places=9
        )

    def test_coverage_landing_exactly_on_its_floor_is_met(self):
        arrangement = base_arrangement(
            policy=base_policy(
                plain_coverage_floor=1.0,
                evidenced_coverage_floor=1.0,
                weighted_coverage_floor=1.0,
            )
        )
        result = assess_quality_assurance(arrangement, "2026-09-14")
        self.assertTrue(result["evidenced_coverage_met"])
        self.assertAlmostEqual(
            result["coverage"]["weighted_evidenced_coverage"], 1.0, places=9
        )

    def test_tolerance_is_small_enough_to_matter(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_empty_disposition_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_figures([])

    def test_disposition_without_status_rejected(self):
        with self.assertRaises(ValueError):
            coverage_figures([{"evidenced": True, "weight": 1}])


class PlanTests(unittest.TestCase):
    def test_whole_months_elapsed(self):
        self.assertEqual(plan_age_months("2025-09-01", "2026-09-14"), 12)

    def test_part_month_does_not_count(self):
        self.assertEqual(plan_age_months("2025-09-20", "2026-09-14"), 11)

    def test_plan_exactly_at_its_interval_is_still_current(self):
        self.assertTrue(plan_current("2024-09-14", "2026-09-14", 24))

    def test_plan_past_its_interval_is_not_current(self):
        self.assertFalse(plan_current("2024-08-14", "2026-09-14", 24))

    def test_future_issue_date_rejected(self):
        with self.assertRaises(ValueError):
            plan_age_months("2027-01-01", "2026-09-14")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            plan_age_months("01/09/2025", "2026-09-14")

    def test_zero_revalidation_interval_rejected(self):
        with self.assertRaises(ValueError):
            plan_current("2025-09-01", "2026-09-14", 0)


class IndependenceTests(unittest.TestCase):
    def test_every_graded_function_reads_as_embedded(self):
        for function in GRADED_FUNCTIONS:
            self.assertTrue(reporting_line_embedded(function))

    def test_independent_line_is_not_embedded(self):
        self.assertFalse(reporting_line_embedded("quality"))

    def test_blank_reporting_line_rejected(self):
        with self.assertRaises(ValueError):
            reporting_line_embedded("   ")


class AssessmentTests(unittest.TestCase):
    def test_complete_arrangement_is_accepted(self):
        result = assess_quality_assurance(base_arrangement(), "2026-09-14")
        self.assertEqual(result["verdict"], "class-3-arrangement-met")
        self.assertTrue(result["acceptable"])

    def test_missing_plan_blocks_first(self):
        arrangement = base_arrangement(quality_plan_reference=None)
        result = assess_quality_assurance(arrangement, "2026-09-14")
        self.assertEqual(result["verdict"], "no-quality-plan")

    def test_relief_against_a_mandatory_duty_blocks(self):
        duties = [duty_record(duty) for duty in duty_catalogue() if duty != "alert-watch"]
        duties.append(
            {
                "duty": "alert-watch",
                "relief_requested": True,
                "relief_rationale": "no subscription budget",
                "relief_approval_authority": "customer",
            }
        )
        result = assess_quality_assurance(
            base_arrangement(declared_duties=duties), "2026-09-14"
        )
        self.assertEqual(result["verdict"], "mandatory-duty-relief-refused")

    def test_undeclared_mandatory_duty_blocks(self):
        duties = [
            duty_record(duty)
            for duty in duty_catalogue()
            if duty != "records-retention"
        ]
        result = assess_quality_assurance(
            base_arrangement(declared_duties=duties), "2026-09-14"
        )
        self.assertEqual(result["verdict"], "mandatory-duty-unassigned")

    def test_thin_evidence_shows_up_as_short_coverage(self):
        duties = [
            duty_record(duty, evidence_reference=None) for duty in duty_catalogue()
        ]
        result = assess_quality_assurance(
            base_arrangement(declared_duties=duties), "2026-09-14"
        )
        self.assertEqual(result["verdict"], "coverage-short")
        self.assertAlmostEqual(result["coverage"]["plain_coverage"], 1.0, places=9)

    def test_embedded_quality_function_needs_an_escalation_route(self):
        result = assess_quality_assurance(
            base_arrangement(reporting_line="production"), "2026-09-14"
        )
        self.assertEqual(result["verdict"], "no-escalation-route")

    def test_declared_escalation_route_clears_the_embedded_line(self):
        result = assess_quality_assurance(
            base_arrangement(
                reporting_line="production", escalation_route="programme manager"
            ),
            "2026-09-14",
        )
        self.assertEqual(result["verdict"], "class-3-arrangement-met")

    def test_overdue_plan_is_reported_last(self):
        result = assess_quality_assurance(
            base_arrangement(quality_plan_issue_date="2020-01-01"), "2026-09-14"
        )
        self.assertEqual(result["verdict"], "quality-plan-revalidation-overdue")

    def test_duplicate_duty_declaration_rejected(self):
        duties = [duty_record("alert-watch"), duty_record("alert-watch")]
        with self.assertRaises(ValueError):
            assess_quality_assurance(
                base_arrangement(declared_duties=duties), "2026-09-14"
            )

    def test_unknown_policy_key_rejected(self):
        policy = base_policy()
        policy["headcount"] = 3
        with self.assertRaises(ValueError):
            assess_quality_assurance(base_arrangement(policy=policy), "2026-09-14")

    def test_evidenced_floor_above_plain_floor_rejected(self):
        policy = base_policy(plain_coverage_floor=0.5, evidenced_coverage_floor=0.9)
        with self.assertRaises(ValueError):
            assess_quality_assurance(base_arrangement(policy=policy), "2026-09-14")

    def test_coverage_floor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_quality_assurance(
                base_arrangement(policy=base_policy(weighted_coverage_floor=1.4)),
                "2026-09-14",
            )

    def test_declared_duties_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_quality_assurance(
                base_arrangement(declared_duties=duty_record("alert-watch")),
                "2026-09-14",
            )

    def test_authority_levels_are_ordered_lowest_first(self):
        self.assertEqual(RELIEF_AUTHORITY_ORDER[0], "none")


if __name__ == "__main__":
    unittest.main()
