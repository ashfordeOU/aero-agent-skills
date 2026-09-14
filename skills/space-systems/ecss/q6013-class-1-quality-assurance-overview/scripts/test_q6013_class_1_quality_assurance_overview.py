"""Contract tests for the clause 4.5.1 quality-assurance duty logic."""

import unittest

from q6013_class_1_quality_assurance_overview_logic import (
    DUTY_WEIGHTS,
    INDEPENDENCE_REQUIRED,
    SCORE_TOLERANCE,
    assess_quality_assurance_duties,
    coverage_score,
    duty_findings,
    duty_is_covered,
    duty_weight,
    owner_is_independent,
    readiness_verdict,
    validate_duty_assignment,
)

TOTAL_WEIGHT = sum(DUTY_WEIGHTS.values())
EXECUTOR = "design-authority"


def _assignment(duty, **over):
    base = {
        "duty": duty,
        "state": "assigned",
        "evidence": "recorded",
        "owner": "K. Ilves",
        "owner_organisation": "quality-assurance",
    }
    base.update(over)
    return base


def _programme(**over):
    programme = {
        "assignments": [_assignment(duty) for duty in sorted(DUTY_WEIGHTS)],
        "executing_organisation": EXECUTOR,
        "required_score": 1.0,
    }
    programme.update(over)
    return programme


class DutyWeightTests(unittest.TestCase):
    def test_known_duty_returns_its_weight(self):
        self.assertAlmostEqual(
            duty_weight("lot-acceptance-review"),
            DUTY_WEIGHTS["lot-acceptance-review"],
            places=9,
        )

    def test_unknown_duty_rejected(self):
        with self.assertRaises(ValueError):
            duty_weight("coffee-rota")

    def test_blank_duty_rejected(self):
        with self.assertRaises(ValueError):
            duty_weight("   ")

    def test_non_positive_weight_rejected(self):
        with self.assertRaises(ValueError):
            duty_weight("x", {"x": 0.0})

    def test_empty_weight_table_rejected(self):
        with self.assertRaises(ValueError):
            duty_weight("x", {})


class AssignmentValidationTests(unittest.TestCase):
    def test_assigned_duty_is_normalised(self):
        record = validate_duty_assignment(_assignment("nonconformance-disposition"))
        self.assertEqual(record["owner_organisation"], "quality-assurance")
        self.assertEqual(record["evidence"], "recorded")

    def test_assigned_duty_needs_an_owner(self):
        with self.assertRaises(ValueError):
            validate_duty_assignment(_assignment("lot-acceptance-review", owner=""))

    def test_unknown_owner_organisation_rejected(self):
        with self.assertRaises(ValueError):
            validate_duty_assignment(
                _assignment("lot-acceptance-review", owner_organisation="marketing")
            )

    def test_deferred_duty_needs_an_authorisation_reference(self):
        with self.assertRaises(ValueError):
            validate_duty_assignment(
                {"duty": "alert-and-advisory-handling", "state": "deferred"}
            )

    def test_deferred_duty_keeps_its_authorisation(self):
        record = validate_duty_assignment(
            {
                "duty": "alert-and-advisory-handling",
                "state": "deferred",
                "authorisation_reference": "PCB-2025-07",
            }
        )
        self.assertEqual(record["authorisation_reference"], "PCB-2025-07")
        self.assertIsNone(record["owner"])

    def test_unassigned_duty_carries_no_owner(self):
        record = validate_duty_assignment(
            {"duty": "parts-control-board-reporting", "state": "unassigned"}
        )
        self.assertIsNone(record["owner"])

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_duty_assignment(_assignment("lot-acceptance-review", state="pending"))

    def test_unknown_evidence_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_duty_assignment(_assignment("lot-acceptance-review", evidence="maybe"))

    def test_assignment_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_duty_assignment(["lot-acceptance-review"])


class IndependenceTests(unittest.TestCase):
    def test_duty_outside_the_independence_set_is_always_independent(self):
        self.assertTrue(
            owner_is_independent(
                "parts-control-board-reporting", "design-authority", "design-authority"
            )
        )

    def test_owner_inside_the_executing_organisation_is_not_independent(self):
        self.assertFalse(
            owner_is_independent("lot-acceptance-review", "design-authority", "design-authority")
        )

    def test_owner_outside_the_executing_organisation_is_independent(self):
        self.assertTrue(
            owner_is_independent("lot-acceptance-review", "quality-assurance", "design-authority")
        )

    def test_every_independence_duty_is_an_owed_duty(self):
        for duty in INDEPENDENCE_REQUIRED:
            self.assertIn(duty, DUTY_WEIGHTS)

    def test_unknown_organisation_rejected(self):
        with self.assertRaises(ValueError):
            owner_is_independent("lot-acceptance-review", "legal", "design-authority")


class CoverageTests(unittest.TestCase):
    def test_a_recorded_independent_duty_counts(self):
        record = validate_duty_assignment(_assignment("lot-acceptance-review"))
        self.assertTrue(duty_is_covered(record, EXECUTOR))

    def test_a_duty_without_evidence_does_not_count(self):
        record = validate_duty_assignment(
            _assignment("lot-acceptance-review", evidence="absent")
        )
        self.assertFalse(duty_is_covered(record, EXECUTOR))

    def test_a_non_independent_owner_does_not_count(self):
        record = validate_duty_assignment(
            _assignment("lot-acceptance-review", owner_organisation="design-authority")
        )
        self.assertFalse(duty_is_covered(record, EXECUTOR))

    def test_full_allocation_scores_one(self):
        records = [
            validate_duty_assignment(_assignment(duty)) for duty in sorted(DUTY_WEIGHTS)
        ]
        self.assertAlmostEqual(coverage_score(records, EXECUTOR), 1.0, places=9)

    def test_empty_allocation_scores_zero(self):
        self.assertAlmostEqual(coverage_score([], EXECUTOR), 0.0, places=9)

    def test_one_dropped_duty_removes_exactly_its_weight(self):
        duties = [d for d in sorted(DUTY_WEIGHTS) if d != "parts-control-board-reporting"]
        records = [validate_duty_assignment(_assignment(d)) for d in duties]
        expected = (TOTAL_WEIGHT - DUTY_WEIGHTS["parts-control-board-reporting"]) / TOTAL_WEIGHT
        self.assertAlmostEqual(coverage_score(records, EXECUTOR), expected, places=9)

    def test_a_duty_listed_twice_is_counted_once(self):
        records = [
            validate_duty_assignment(_assignment("lot-acceptance-review")),
            validate_duty_assignment(_assignment("lot-acceptance-review")),
        ]
        expected = DUTY_WEIGHTS["lot-acceptance-review"] / TOTAL_WEIGHT
        self.assertAlmostEqual(coverage_score(records, EXECUTOR), expected, places=9)

    def test_records_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            coverage_score("all of them", EXECUTOR)


class DutyFindingTests(unittest.TestCase):
    def test_covered_duty_raises_nothing(self):
        record = validate_duty_assignment(_assignment("lot-acceptance-review"))
        self.assertEqual(duty_findings(record, EXECUTOR), [])

    def test_unassigned_duty_is_critical(self):
        record = validate_duty_assignment(
            {"duty": "lot-acceptance-review", "state": "unassigned"}
        )
        self.assertEqual([f["severity"] for f in duty_findings(record, EXECUTOR)], ["critical"])

    def test_non_independent_owner_is_critical(self):
        record = validate_duty_assignment(
            _assignment("nonconformance-disposition", owner_organisation="design-authority")
        )
        self.assertEqual([f["severity"] for f in duty_findings(record, EXECUTOR)], ["critical"])

    def test_owner_without_evidence_is_major(self):
        record = validate_duty_assignment(
            _assignment("alert-and-advisory-handling", evidence="absent")
        )
        self.assertEqual([f["severity"] for f in duty_findings(record, EXECUTOR)], ["major"])

    def test_planned_evidence_is_minor(self):
        record = validate_duty_assignment(
            _assignment("alert-and-advisory-handling", evidence="planned")
        )
        self.assertEqual([f["severity"] for f in duty_findings(record, EXECUTOR)], ["minor"])

    def test_deferred_duty_is_minor_and_names_its_authorisation(self):
        record = validate_duty_assignment(
            {
                "duty": "alert-and-advisory-handling",
                "state": "deferred",
                "authorisation_reference": "PCB-2025-07",
            }
        )
        findings = duty_findings(record, EXECUTOR)
        self.assertEqual(findings[0]["severity"], "minor")
        self.assertIn("PCB-2025-07", findings[0]["message"])


class ReadinessVerdictTests(unittest.TestCase):
    def test_full_score_and_no_findings_is_ready(self):
        self.assertEqual(readiness_verdict(1.0, [], 1.0), "ready")

    def test_minor_finding_keeps_the_programme_with_actions(self):
        self.assertEqual(
            readiness_verdict(1.0, [{"severity": "minor", "duty": "d", "message": "m"}], 1.0),
            "ready-with-actions",
        )

    def test_critical_finding_is_not_ready(self):
        self.assertEqual(
            readiness_verdict(
                1.0, [{"severity": "critical", "duty": "d", "message": "m"}], 1.0
            ),
            "not-ready",
        )

    def test_score_exactly_at_the_required_value_meets_it(self):
        duties = [d for d in sorted(DUTY_WEIGHTS) if d != "parts-control-board-reporting"]
        records = [validate_duty_assignment(_assignment(d)) for d in duties]
        required = (TOTAL_WEIGHT - DUTY_WEIGHTS["parts-control-board-reporting"]) / TOTAL_WEIGHT
        achieved = coverage_score(records, EXECUTOR)
        self.assertAlmostEqual(achieved, required, places=9)
        self.assertEqual(readiness_verdict(achieved, [], required), "ready")

    def test_score_below_the_required_value_is_not_ready(self):
        self.assertEqual(readiness_verdict(0.5, [], 0.9), "not-ready")

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(SCORE_TOLERANCE, 1e-9, places=12)

    def test_score_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            readiness_verdict(1.4, [], 1.0)

    def test_zero_required_score_rejected(self):
        with self.assertRaises(ValueError):
            readiness_verdict(1.0, [], 0.0)


class AssessmentTests(unittest.TestCase):
    def test_complete_allocation_is_ready(self):
        result = assess_quality_assurance_duties(_programme())
        self.assertTrue(result["ready"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_score"], 1.0, places=9)

    def test_duty_absent_from_the_matrix_is_reported(self):
        programme = _programme()
        programme["assignments"] = [
            a for a in programme["assignments"] if a["duty"] != "lot-traceability-maintenance"
        ]
        result = assess_quality_assurance_duties(programme)
        self.assertEqual(result["verdict"], "not-ready")
        duties = [f["duty"] for f in result["findings"]]
        self.assertIn("lot-traceability-maintenance", duties)

    def test_self_assured_duty_is_not_ready(self):
        duty = INDEPENDENCE_REQUIRED[0]
        programme = _programme()
        programme["assignments"] = [
            a for a in programme["assignments"] if a["duty"] != duty
        ] + [_assignment(duty, owner_organisation=EXECUTOR)]
        result = assess_quality_assurance_duties(programme)
        self.assertEqual(result["verdict"], "not-ready")
        critical = [f for f in result["findings"] if f["severity"] == "critical"]
        self.assertEqual([f["duty"] for f in critical], [duty])

    def test_a_duty_outside_the_independence_set_may_sit_with_the_executor(self):
        duty = "parts-control-board-reporting"
        self.assertNotIn(duty, INDEPENDENCE_REQUIRED)
        programme = _programme()
        programme["assignments"] = [
            a for a in programme["assignments"] if a["duty"] != duty
        ] + [_assignment(duty, owner_organisation=EXECUTOR)]
        result = assess_quality_assurance_duties(programme)
        self.assertEqual(result["verdict"], "ready")

    def test_deferred_duty_lowers_the_score_to_its_exact_complement(self):
        programme = _programme(required_score=1.0)
        programme["assignments"] = [
            a for a in programme["assignments"] if a["duty"] != "parts-control-board-reporting"
        ] + [
            {
                "duty": "parts-control-board-reporting",
                "state": "deferred",
                "authorisation_reference": "PCB-2025-07",
            }
        ]
        result = assess_quality_assurance_duties(programme)
        expected = (TOTAL_WEIGHT - DUTY_WEIGHTS["parts-control-board-reporting"]) / TOTAL_WEIGHT
        self.assertAlmostEqual(result["coverage_score"], expected, places=9)
        self.assertEqual(result["verdict"], "not-ready")

    def test_a_deferred_duty_passes_when_the_required_score_allows_it(self):
        expected = (TOTAL_WEIGHT - DUTY_WEIGHTS["parts-control-board-reporting"]) / TOTAL_WEIGHT
        programme = _programme(required_score=expected)
        programme["assignments"] = [
            a for a in programme["assignments"] if a["duty"] != "parts-control-board-reporting"
        ] + [
            {
                "duty": "parts-control-board-reporting",
                "state": "deferred",
                "authorisation_reference": "PCB-2025-07",
            }
        ]
        result = assess_quality_assurance_duties(programme)
        self.assertAlmostEqual(result["coverage_score"], expected, places=9)
        self.assertEqual(result["verdict"], "ready-with-actions")

    def test_findings_are_ranked_critical_first(self):
        programme = _programme()
        programme["assignments"][1] = {
            "duty": sorted(DUTY_WEIGHTS)[1],
            "state": "unassigned",
        }
        programme["assignments"][2] = _assignment(sorted(DUTY_WEIGHTS)[2], evidence="planned")
        result = assess_quality_assurance_duties(programme)
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "minor")

    def test_unknown_executing_organisation_rejected(self):
        with self.assertRaises(ValueError):
            assess_quality_assurance_duties(_programme(executing_organisation="legal"))

    def test_missing_programme_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_quality_assurance_duties({"assignments": []})

    def test_programme_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_quality_assurance_duties([_programme()])

    def test_duty_outside_the_owed_set_rejected(self):
        programme = _programme()
        programme["assignments"].append(_assignment("coffee-rota"))
        with self.assertRaises(ValueError):
            assess_quality_assurance_duties(programme)


if __name__ == "__main__":
    unittest.main(verbosity=1)
