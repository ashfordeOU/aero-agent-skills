"""Contract tests for the clause 5.5.1 class 2 quality assurance overview."""

import datetime
import unittest

from q6013_class_2_quality_assurance_overview_logic import (
    BOUND_TOLERANCE,
    DISCRETIONARY_DUTIES,
    MANDATORY_DUTIES,
    QA_DUTIES,
    assess_class_two_quality_assurance,
    coverage_figures,
    dispose_duties,
    duty_state,
    independence_state,
    plan_reference_state,
    quality_assurance_verdict,
    validate_policy,
    waiver_admissible,
)


def _full_duties(**over):
    duties = []
    for name in sorted(QA_DUTIES):
        duties.append(
            {
                "duty": name,
                "owner": "product-assurance-unit",
                "procedure_ref": "PA-PROC-%s" % name[:4].upper(),
                "evidence_ref": "PA-REC-%s" % name[:4].upper(),
            }
        )
    for name, replacement in over.items():
        key = name.replace("_", "-")
        for index, entry in enumerate(duties):
            if entry["duty"] == key:
                if replacement is None:
                    duties.pop(index)
                else:
                    duties[index] = replacement
                break
    return duties


def _record(**over):
    base = {
        "programme": "class-two-commercial-eee-programme",
        "duties": _full_duties(),
        "reports_to": "product-assurance",
        "review_date": "2025-06-02",
        "quality_plan_ref": "PA-PLAN-0021",
        "plan_issue_date": "2024-06-02",
    }
    base.update(over)
    return base


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        policy = validate_policy()
        self.assertAlmostEqual(policy["plain_floor"], 1.0, places=9)
        self.assertAlmostEqual(policy["evidenced_floor"], 0.75, places=9)

    def test_policy_override_is_taken(self):
        policy = validate_policy({"evidenced_floor": 0.5})
        self.assertAlmostEqual(policy["evidenced_floor"], 0.5, places=9)

    def test_evidenced_floor_above_plain_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"plain_floor": 0.6, "evidenced_floor": 0.9})

    def test_equal_floors_are_accepted(self):
        policy = validate_policy({"plain_floor": 0.8, "evidenced_floor": 0.8})
        self.assertAlmostEqual(policy["evidenced_floor"], 0.8, places=9)

    def test_fraction_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"plain_floor": 1.4})

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"plane_floor": 1.0})

    def test_non_positive_revalidation_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"plan_revalidation_days": 0})

    def test_non_boolean_route_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"escalation_route_required": "yes"})


class WaiverTests(unittest.TestCase):
    def test_mandatory_duty_cannot_be_waived(self):
        verdict = waiver_admissible(
            MANDATORY_DUTIES[0], {"rationale": "cost", "approval": "PA-1"}
        )
        self.assertFalse(verdict["admissible"])

    def test_discretionary_duty_waivable_when_recorded(self):
        verdict = waiver_admissible(
            DISCRETIONARY_DUTIES[0],
            {"rationale": "catalogue part from a surveyed source", "approval": "PA-2"},
        )
        self.assertTrue(verdict["admissible"])

    def test_waiver_without_rationale_refused(self):
        verdict = waiver_admissible(DISCRETIONARY_DUTIES[0], {"approval": "PA-2"})
        self.assertFalse(verdict["admissible"])

    def test_waiver_without_approval_refused(self):
        verdict = waiver_admissible(DISCRETIONARY_DUTIES[0], {"rationale": "r"})
        self.assertFalse(verdict["admissible"])

    def test_absent_waiver_is_not_admissible(self):
        self.assertFalse(waiver_admissible(DISCRETIONARY_DUTIES[0], None)["admissible"])

    def test_unknown_duty_rejected(self):
        with self.assertRaises(ValueError):
            waiver_admissible("shipping-paperwork", None)


class DutyStateTests(unittest.TestCase):
    def test_complete_record_is_established(self):
        state = duty_state(
            {
                "duty": "nonconformance-processing",
                "owner": "pa",
                "procedure_ref": "p",
                "evidence_ref": "e",
            }
        )
        self.assertEqual(state["state"], "established")

    def test_missing_owner_reads_unowned(self):
        state = duty_state(
            {"duty": "nonconformance-processing", "procedure_ref": "p", "evidence_ref": "e"}
        )
        self.assertEqual(state["state"], "unowned")

    def test_missing_procedure_reads_procedure_missing(self):
        state = duty_state(
            {"duty": "nonconformance-processing", "owner": "pa", "evidence_ref": "e"}
        )
        self.assertEqual(state["state"], "procedure-missing")

    def test_missing_evidence_reads_evidence_missing(self):
        state = duty_state(
            {"duty": "nonconformance-processing", "owner": "pa", "procedure_ref": "p"}
        )
        self.assertEqual(state["state"], "evidence-missing")

    def test_blank_reference_counts_as_absent(self):
        state = duty_state(
            {
                "duty": "nonconformance-processing",
                "owner": "pa",
                "procedure_ref": "   ",
                "evidence_ref": "e",
            }
        )
        self.assertEqual(state["state"], "procedure-missing")

    def test_admissible_waiver_reads_waived(self):
        state = duty_state(
            {
                "duty": DISCRETIONARY_DUTIES[0],
                "waiver": {"rationale": "surveyed source", "approval": "PA-2"},
            }
        )
        self.assertEqual(state["state"], "waived")

    def test_inadmissible_waiver_on_a_mandatory_duty_reads_unowned(self):
        state = duty_state(
            {
                "duty": MANDATORY_DUTIES[0],
                "waiver": {"rationale": "cost", "approval": "PA-2"},
            }
        )
        self.assertEqual(state["state"], "unowned")

    def test_duty_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            duty_state(["nonconformance-processing"])


class DispositionTests(unittest.TestCase):
    def test_every_catalogue_duty_appears(self):
        report = dispose_duties([])
        self.assertEqual(len(report), len(QA_DUTIES))
        self.assertTrue(all(item["state"] == "unowned" for item in report))

    def test_undeclared_duty_is_reported_not_dropped(self):
        report = dispose_duties(_full_duties(supplier_surveillance=None))
        states = {item["duty"]: item["state"] for item in report}
        self.assertEqual(states["supplier-surveillance"], "unowned")

    def test_duplicate_duty_rejected(self):
        duties = _full_duties()
        duties.append(duties[0])
        with self.assertRaises(ValueError):
            dispose_duties(duties)

    def test_declared_duties_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            dispose_duties({"duty": "nonconformance-processing"})


class CoverageTests(unittest.TestCase):
    def test_full_catalogue_reaches_both_figures(self):
        figures = coverage_figures(dispose_duties(_full_duties()))
        self.assertAlmostEqual(figures["plain_coverage"], 1.0, places=9)
        self.assertAlmostEqual(figures["evidenced_coverage"], 1.0, places=9)

    def test_a_waived_duty_lifts_plain_but_not_evidenced(self):
        duties = _full_duties(
            supplier_surveillance={
                "duty": "supplier-surveillance",
                "waiver": {"rationale": "surveyed source", "approval": "PA-2"},
            }
        )
        figures = coverage_figures(dispose_duties(duties))
        self.assertAlmostEqual(figures["plain_coverage"], 1.0, places=9)
        self.assertAlmostEqual(
            figures["evidenced_coverage"], (len(QA_DUTIES) - 1) / len(QA_DUTIES), places=9
        )

    def test_empty_report_rejected(self):
        with self.assertRaises(ValueError):
            coverage_figures([])

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            coverage_figures([{"duty": "d", "state": "pending"}])


class PlanTests(unittest.TestCase):
    def test_absent_plan_is_reported_overdue(self):
        state = plan_reference_state(None, "2024-01-01", "2025-01-01", 730)
        self.assertFalse(state["present"])
        self.assertTrue(state["revalidation_overdue"])

    def test_fresh_plan_is_inside_the_interval(self):
        state = plan_reference_state("PA-PLAN-1", "2024-06-02", "2025-06-02", 730)
        self.assertTrue(state["present"])
        self.assertFalse(state["revalidation_overdue"])

    def test_plan_exactly_on_the_interval_is_still_valid(self):
        state = plan_reference_state("PA-PLAN-1", "2023-01-01", "2023-01-11", 10)
        self.assertEqual(state["age_days"], 10)
        self.assertFalse(state["revalidation_overdue"])

    def test_plan_past_the_interval_is_overdue(self):
        state = plan_reference_state("PA-PLAN-1", "2023-01-01", "2023-01-12", 10)
        self.assertTrue(state["revalidation_overdue"])

    def test_date_objects_accepted(self):
        state = plan_reference_state(
            "PA-PLAN-1", datetime.date(2024, 1, 1), datetime.date(2024, 1, 2), 10
        )
        self.assertEqual(state["age_days"], 1)

    def test_review_before_issue_rejected(self):
        with self.assertRaises(ValueError):
            plan_reference_state("PA-PLAN-1", "2025-01-01", "2024-01-01", 730)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            plan_reference_state("PA-PLAN-1", "01/01/2024", "2025-01-01", 730)


class IndependenceTests(unittest.TestCase):
    def test_a_separate_line_is_not_embedded(self):
        state = independence_state("product-assurance", None)
        self.assertFalse(state["embedded"])
        self.assertTrue(state["satisfied"])

    def test_embedding_without_a_route_is_unsatisfied(self):
        state = independence_state("design", None)
        self.assertTrue(state["embedded"])
        self.assertFalse(state["satisfied"])

    def test_embedding_with_a_route_is_satisfied(self):
        state = independence_state("design", "customer-pa-escalation-annex-c")
        self.assertTrue(state["satisfied"])

    def test_route_not_required_by_policy_leaves_embedding_satisfied(self):
        state = independence_state("production", None, route_required=False)
        self.assertTrue(state["satisfied"])

    def test_blank_reporting_line_rejected(self):
        with self.assertRaises(ValueError):
            independence_state("  ", None)

    def test_non_boolean_route_requirement_rejected(self):
        with self.assertRaises(ValueError):
            independence_state("design", None, route_required="yes")


class VerdictTests(unittest.TestCase):
    def test_verdict_state_must_be_complete(self):
        with self.assertRaises(ValueError):
            quality_assurance_verdict({"plan": {"present": True}})

    def test_verdict_state_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            quality_assurance_verdict(["plan"])


class AssessmentTests(unittest.TestCase):
    def test_a_complete_arrangement_meets_the_class(self):
        result = assess_class_two_quality_assurance(_record())
        self.assertTrue(result["meets_class_two"])
        self.assertEqual(result["gaps"], [])

    def test_no_plan_closes_on_not_established(self):
        result = assess_class_two_quality_assurance(_record(quality_plan_ref=None))
        self.assertEqual(result["verdict"], "quality-assurance-not-established")

    def test_waiving_a_mandatory_duty_is_named(self):
        duties = _full_duties(
            nonconformance_processing={
                "duty": "nonconformance-processing",
                "waiver": {"rationale": "low part count", "approval": "PA-9"},
            }
        )
        result = assess_class_two_quality_assurance(_record(duties=duties))
        self.assertEqual(result["verdict"], "mandatory-duty-waived")
        self.assertIn("nonconformance-processing", result["mandatory_waived"])

    def test_an_unowned_mandatory_duty_closes_on_unassigned(self):
        duties = _full_duties(traceability_and_lot_identity=None)
        result = assess_class_two_quality_assurance(_record(duties=duties))
        self.assertEqual(result["verdict"], "mandatory-duty-unassigned")
        self.assertIn("traceability-and-lot-identity", result["mandatory_unassigned"])

    def test_a_discretionary_gap_shows_as_coverage_short(self):
        duties = _full_duties(supplier_surveillance=None, process_and_handling_audit=None)
        result = assess_class_two_quality_assurance(_record(duties=duties))
        self.assertEqual(result["verdict"], "duty-coverage-short")
        self.assertAlmostEqual(
            result["plain_coverage"], (len(QA_DUTIES) - 2) / len(QA_DUTIES), places=9
        )

    def test_a_recorded_waiver_keeps_plain_coverage_whole(self):
        duties = _full_duties(
            supplier_surveillance={
                "duty": "supplier-surveillance",
                "waiver": {"rationale": "surveyed source", "approval": "PA-2"},
            }
        )
        result = assess_class_two_quality_assurance(
            _record(duties=duties, policy={"evidenced_floor": 0.75})
        )
        self.assertAlmostEqual(result["plain_coverage"], 1.0, places=9)
        self.assertTrue(result["meets_class_two"])

    def test_evidenced_floor_exactly_met_is_not_short(self):
        duties = _full_duties(
            supplier_surveillance={
                "duty": "supplier-surveillance",
                "waiver": {"rationale": "surveyed source", "approval": "PA-2"},
            },
            process_and_handling_audit={
                "duty": "process-and-handling-audit",
                "waiver": {"rationale": "single build site", "approval": "PA-3"},
            },
        )
        result = assess_class_two_quality_assurance(_record(duties=duties))
        self.assertAlmostEqual(result["evidenced_coverage"], 0.75, places=9)
        self.assertTrue(result["meets_class_two"])

    def test_embedded_function_without_a_route_is_named(self):
        result = assess_class_two_quality_assurance(_record(reports_to="design"))
        self.assertEqual(result["verdict"], "escalation-route-not-declared")

    def test_embedded_function_with_a_route_passes(self):
        result = assess_class_two_quality_assurance(
            _record(reports_to="design", escalation_route="customer-pa-annex-c")
        )
        self.assertTrue(result["meets_class_two"])

    def test_stale_plan_is_named(self):
        result = assess_class_two_quality_assurance(
            _record(plan_issue_date="2020-01-01")
        )
        self.assertEqual(result["verdict"], "plan-revalidation-overdue")

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)

    def test_missing_record_key_rejected(self):
        record = _record()
        del record["reports_to"]
        with self.assertRaises(ValueError):
            assess_class_two_quality_assurance(record)

    def test_blank_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_two_quality_assurance(_record(programme="  "))

    def test_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_class_two_quality_assurance([_record()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
