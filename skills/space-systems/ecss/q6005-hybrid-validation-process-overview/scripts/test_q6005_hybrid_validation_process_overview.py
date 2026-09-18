"""Contract tests for the clause 6.1 hybrid validation path logic."""

import unittest

from q6005_hybrid_validation_process_overview_logic import (
    MANDATORY_STAGES,
    STAGE_NAMES,
    VALIDATION_OBJECTIVES,
    VALIDATION_STAGES,
    assess_validation_path,
    completion_fraction,
    next_stage,
    objective_status,
    ordering_violations,
    planned_duration_days,
    scope_covers,
    stage_index,
    stage_record,
    validate_plan,
)

FULL_PLAN = list(STAGE_NAMES)

THROUGH_AUDIT = [
    "validation-request",
    "documentation-review",
    "manufacturer-audit",
]


def programme_with(**overrides):
    programme = {
        "manufacturer": "Thickfilm Hybrids SA",
        "plan": FULL_PLAN,
        "completed": THROUGH_AUDIT,
    }
    programme.update(overrides)
    return programme


class PathShapeTests(unittest.TestCase):
    def test_every_prerequisite_is_itself_a_stage(self):
        for stage in VALIDATION_STAGES:
            for prerequisite in stage["prerequisites"]:
                self.assertIn(prerequisite, STAGE_NAMES)

    def test_every_prerequisite_sits_earlier_on_the_path(self):
        for stage in VALIDATION_STAGES:
            for prerequisite in stage["prerequisites"]:
                self.assertLess(stage_index(prerequisite), stage_index(stage["name"]))

    def test_the_path_opens_with_a_stage_that_has_no_prerequisite(self):
        self.assertEqual(VALIDATION_STAGES[0]["prerequisites"], ())

    def test_surveillance_is_the_one_stage_outside_the_mandatory_set(self):
        self.assertNotIn("surveillance", MANDATORY_STAGES)
        self.assertEqual(len(MANDATORY_STAGES), len(STAGE_NAMES) - 1)

    def test_every_objective_is_evidenced_by_a_real_stage(self):
        for _, evidence in VALIDATION_OBJECTIVES:
            self.assertIn(evidence, STAGE_NAMES)


class StageLookupTests(unittest.TestCase):
    def test_case_and_separator_do_not_change_a_stage(self):
        self.assertEqual(stage_record("Manufacturer_Audit")["name"], "manufacturer-audit")

    def test_index_follows_the_path_order(self):
        self.assertLess(stage_index("documentation-review"), stage_index("evaluation-testing"))

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            stage_record("coffee-with-the-supplier")

    def test_blank_stage_rejected(self):
        with self.assertRaises(ValueError):
            stage_record("   ")

    def test_non_string_stage_rejected(self):
        with self.assertRaises(ValueError):
            stage_record(3)


class PlanValidationTests(unittest.TestCase):
    def test_full_path_validates(self):
        self.assertEqual(validate_plan(FULL_PLAN), list(STAGE_NAMES))

    def test_plan_is_normalized_on_the_way_through(self):
        self.assertEqual(
            validate_plan(["Validation Request", "documentation_review"]),
            ["validation-request", "documentation-review"],
        )

    def test_repeated_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(["validation-request", "validation-request"])

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([])

    def test_non_sequence_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan("validation-request")


class OrderingTests(unittest.TestCase):
    def test_the_full_path_has_no_violation(self):
        self.assertEqual(ordering_violations(FULL_PLAN), [])

    def test_a_stage_ahead_of_its_prerequisite_is_a_violation(self):
        plan = [
            "validation-request",
            "manufacturer-audit",
            "documentation-review",
        ]
        self.assertIn(("manufacturer-audit", "documentation-review"), ordering_violations(plan))

    def test_an_absent_prerequisite_is_a_violation(self):
        plan = ["validation-request", "evaluation-testing"]
        self.assertIn(("evaluation-testing", "validation-vehicle-build"), ordering_violations(plan))

    def test_a_partial_plan_in_order_has_no_violation(self):
        self.assertEqual(ordering_violations(THROUGH_AUDIT), [])


class NextStageTests(unittest.TestCase):
    def test_nothing_done_points_at_the_request(self):
        self.assertEqual(next_stage([]), "validation-request")

    def test_none_is_read_as_nothing_done(self):
        self.assertEqual(next_stage(None), "validation-request")

    def test_the_next_stage_respects_prerequisites(self):
        self.assertEqual(next_stage(THROUGH_AUDIT), "validation-vehicle-definition")

    def test_a_stage_with_two_prerequisites_waits_for_both(self):
        done = THROUGH_AUDIT + ["validation-vehicle-definition"]
        self.assertEqual(next_stage(done), "validation-vehicle-build")

    def test_a_completed_path_has_no_next_stage(self):
        self.assertIsNone(next_stage(FULL_PLAN))

    def test_unknown_completed_stage_rejected(self):
        with self.assertRaises(ValueError):
            next_stage(["validation-request", "a-nice-lunch"])


class CompletionTests(unittest.TestCase):
    def test_nothing_done_is_zero(self):
        self.assertAlmostEqual(completion_fraction([]), 0.0, places=9)

    def test_whole_path_is_one(self):
        self.assertAlmostEqual(completion_fraction(FULL_PLAN), 1.0, places=9)

    def test_partial_completion_is_the_stage_share(self):
        self.assertAlmostEqual(
            completion_fraction(THROUGH_AUDIT), 3 / float(len(STAGE_NAMES)), places=9
        )

    def test_repeated_completed_stage_counts_once(self):
        self.assertAlmostEqual(
            completion_fraction(THROUGH_AUDIT + ["manufacturer-audit"]),
            3 / float(len(STAGE_NAMES)),
            places=9,
        )

    def test_non_sequence_completed_rejected(self):
        with self.assertRaises(ValueError):
            completion_fraction("manufacturer-audit")


class ObjectiveTests(unittest.TestCase):
    def test_nothing_done_owes_every_objective(self):
        status = objective_status([])
        self.assertFalse(any(status.values()))

    def test_the_audit_confirms_the_process_documentation(self):
        status = objective_status(THROUGH_AUDIT)
        self.assertTrue(status["process-documentation-confirmed"])
        self.assertFalse(status["demonstrated-process-capability"])

    def test_a_completed_path_meets_every_objective(self):
        status = objective_status(FULL_PLAN)
        self.assertTrue(all(status.values()))

    def test_granting_without_surveillance_leaves_the_baseline_owed(self):
        done = [name for name in STAGE_NAMES if name != "surveillance"]
        self.assertFalse(objective_status(done)["surveillance-baseline-set"])


class DurationAndScopeTests(unittest.TestCase):
    def test_duration_sums_the_stages_named(self):
        self.assertEqual(
            planned_duration_days(THROUGH_AUDIT),
            sum(stage_record(name)["nominal_days"] for name in THROUGH_AUDIT),
        )

    def test_the_whole_path_costs_more_than_a_part_of_it(self):
        self.assertGreater(planned_duration_days(FULL_PLAN), planned_duration_days(THROUGH_AUDIT))

    def test_scope_match_ignores_case_and_separator(self):
        self.assertTrue(scope_covers(["Thickfilm Multilayer"], "thickfilm-multilayer"))

    def test_technology_outside_the_scope_is_not_covered(self):
        self.assertFalse(scope_covers(["thickfilm-multilayer"], "thinfilm-single-layer"))

    def test_empty_granted_scope_rejected(self):
        with self.assertRaises(ValueError):
            scope_covers([], "thickfilm-multilayer")

    def test_non_sequence_granted_scope_rejected(self):
        with self.assertRaises(ValueError):
            scope_covers("thickfilm-multilayer", "thickfilm-multilayer")


class AssessmentTests(unittest.TestCase):
    def test_a_coherent_programme_reports_no_finding(self):
        result = assess_validation_path(programme_with())
        self.assertTrue(result["coherent"])
        self.assertEqual(result["findings"], [])

    def test_the_purpose_is_reported_whatever_the_plan_says(self):
        result = assess_validation_path(programme_with())
        self.assertEqual(
            result["purpose"], tuple(objective for objective, _ in VALIDATION_OBJECTIVES)
        )

    def test_a_plan_missing_a_mandatory_stage_is_incoherent(self):
        plan = [name for name in STAGE_NAMES if name != "manufacturer-audit"]
        result = assess_validation_path(programme_with(plan=plan, completed=["validation-request"]))
        self.assertFalse(result["coherent"])
        self.assertEqual(result["missing_mandatory_stages"], ["manufacturer-audit"])

    def test_an_out_of_order_plan_is_reported_stage_by_prerequisite(self):
        plan = [
            "validation-request",
            "manufacturer-audit",
            "documentation-review",
            "validation-vehicle-definition",
            "validation-vehicle-build",
            "evaluation-testing",
            "validation-review",
            "validation-granted",
        ]
        result = assess_validation_path(programme_with(plan=plan, completed=["validation-request"]))
        self.assertIn(("manufacturer-audit", "documentation-review"), result["ordering_violations"])

    def test_the_next_stage_is_named_for_a_stalled_programme(self):
        result = assess_validation_path(programme_with())
        self.assertEqual(result["next_stage"], "validation-vehicle-definition")

    def test_outstanding_objectives_are_listed(self):
        result = assess_validation_path(programme_with())
        self.assertIn("demonstrated-process-capability", result["objectives_outstanding"])
        self.assertNotIn("process-documentation-confirmed", result["objectives_outstanding"])

    def test_a_build_outside_the_granted_scope_is_a_finding(self):
        result = assess_validation_path(
            programme_with(granted_scope=["thickfilm-multilayer"], requested_technology="thinfilm-single-layer")
        )
        self.assertFalse(result["coherent"])
        self.assertTrue(any("granted validation scope" in f for f in result["findings"]))

    def test_a_build_inside_the_granted_scope_is_not_a_finding(self):
        result = assess_validation_path(
            programme_with(granted_scope=["thickfilm-multilayer"], requested_technology="Thickfilm Multilayer")
        )
        self.assertTrue(result["coherent"])

    def test_completed_stage_outside_the_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_validation_path(
                programme_with(plan=THROUGH_AUDIT, completed=THROUGH_AUDIT + ["evaluation-testing"])
            )

    def test_missing_programme_key_rejected(self):
        programme = programme_with()
        del programme["plan"]
        with self.assertRaises(ValueError):
            assess_validation_path(programme)

    def test_non_mapping_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_validation_path(FULL_PLAN)

    def test_blank_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            assess_validation_path(programme_with(manufacturer="  "))

    def test_manufacturer_name_is_carried_through_trimmed(self):
        result = assess_validation_path(programme_with(manufacturer="  Thickfilm Hybrids SA  "))
        self.assertEqual(result["manufacturer"], "Thickfilm Hybrids SA")

    def test_completion_is_reported_as_a_share_of_the_whole_path(self):
        result = assess_validation_path(programme_with())
        self.assertAlmostEqual(result["completion"], 3 / float(len(STAGE_NAMES)), places=9)


if __name__ == "__main__":
    unittest.main()
