"""Contract tests for the clause 4 hybrid procurement activity ordering."""

import unittest

from q6005_hybrid_procurement_activity_sequence_logic import (
    CATEGORIES,
    CATEGORY_APPROVED_LINE,
    CATEGORY_NO_APPROVED_LINE,
    COMMON_OPENING_STEPS,
    LINE_APPROVAL_STEPS,
    PROCUREMENT_SEQUENCE,
    applicable_steps,
    assess_procurement_sequence,
    completion_fraction,
    entry_step,
    next_step,
    normalize_category,
    normalize_step,
    not_applicable_findings,
    ordering_findings,
    prerequisites,
    remaining_steps,
    skipped_steps,
    step_position,
    validate_executed,
)

FULL_APPROVED = [
    "define-procurement-requirements",
    "select-manufacturer",
    "agree-procurement-specification",
    "qualify-part-type",
    "manufacture-under-inline-control",
    "lot-acceptance-testing",
    "accept-and-deliver-lot",
]

FULL_UNAPPROVED = [
    "define-procurement-requirements",
    "select-manufacturer",
    "evaluate-production-line",
    "approve-production-line",
    "agree-procurement-specification",
    "qualify-part-type",
    "manufacture-under-inline-control",
    "lot-acceptance-testing",
    "accept-and-deliver-lot",
]


class CategoryNormalisationTests(unittest.TestCase):
    def test_canonical_names_pass_through(self):
        self.assertEqual(normalize_category("approved-line"), CATEGORY_APPROVED_LINE)

    def test_numeric_alias_maps_to_the_approved_line_category(self):
        self.assertEqual(normalize_category("category-1"), CATEGORY_APPROVED_LINE)

    def test_numeric_alias_maps_to_the_non_approved_category(self):
        self.assertEqual(normalize_category("category-2"), CATEGORY_NO_APPROVED_LINE)

    def test_case_and_padding_are_tolerated(self):
        self.assertEqual(normalize_category("  Approved Line "), CATEGORY_APPROVED_LINE)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("preferred-supplier")

    def test_empty_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("   ")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category(1)

    def test_only_two_categories_exist(self):
        self.assertEqual(len(CATEGORIES), 2)


class StepNormalisationTests(unittest.TestCase):
    def test_underscores_and_spaces_are_folded(self):
        self.assertEqual(normalize_step("Qualify Part Type"), "qualify-part-type")

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step("negotiate-price")

    def test_non_string_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step(None)

    def test_sequence_has_no_repeated_activity(self):
        self.assertEqual(len(set(PROCUREMENT_SEQUENCE)), len(PROCUREMENT_SEQUENCE))


class RouteShapeTests(unittest.TestCase):
    def test_non_approved_route_is_the_whole_sequence(self):
        self.assertEqual(applicable_steps(CATEGORY_NO_APPROVED_LINE), PROCUREMENT_SEQUENCE)

    def test_approved_route_drops_the_line_approval_activities(self):
        route = applicable_steps(CATEGORY_APPROVED_LINE)
        for step in LINE_APPROVAL_STEPS:
            self.assertNotIn(step, route)

    def test_approved_route_is_two_activities_shorter(self):
        self.assertEqual(
            len(applicable_steps(CATEGORY_NO_APPROVED_LINE))
            - len(applicable_steps(CATEGORY_APPROVED_LINE)),
            len(LINE_APPROVAL_STEPS),
        )

    def test_both_routes_keep_the_common_opening_activities(self):
        for category in CATEGORIES:
            for step in COMMON_OPENING_STEPS:
                self.assertIn(step, applicable_steps(category))

    def test_skipped_steps_are_empty_for_the_non_approved_category(self):
        self.assertEqual(skipped_steps(CATEGORY_NO_APPROVED_LINE), ())

    def test_skipped_steps_name_the_line_activities_for_the_approved_category(self):
        self.assertEqual(skipped_steps(CATEGORY_APPROVED_LINE), LINE_APPROVAL_STEPS)

    def test_route_order_follows_the_master_sequence(self):
        route = applicable_steps(CATEGORY_APPROVED_LINE)
        positions = [PROCUREMENT_SEQUENCE.index(s) for s in route]
        self.assertEqual(positions, sorted(positions))


class EntryPointTests(unittest.TestCase):
    def test_approved_line_maker_enters_at_the_specification_agreement(self):
        self.assertEqual(entry_step(CATEGORY_APPROVED_LINE), "agree-procurement-specification")

    def test_non_approved_maker_enters_at_the_line_evaluation(self):
        self.assertEqual(entry_step(CATEGORY_NO_APPROVED_LINE), "evaluate-production-line")

    def test_entry_points_differ_between_the_two_categories(self):
        self.assertNotEqual(
            entry_step(CATEGORY_APPROVED_LINE), entry_step(CATEGORY_NO_APPROVED_LINE)
        )

    def test_entry_point_is_inside_its_own_route(self):
        for category in CATEGORIES:
            self.assertIn(entry_step(category), applicable_steps(category))

    def test_unknown_category_has_no_entry_point(self):
        with self.assertRaises(ValueError):
            entry_step("category-3")


class PrerequisiteTests(unittest.TestCase):
    def test_first_activity_has_no_prerequisite(self):
        self.assertEqual(prerequisites("define-procurement-requirements", CATEGORIES[0]), ())

    def test_prerequisites_of_the_last_activity_cover_the_rest_of_the_route(self):
        route = applicable_steps(CATEGORY_APPROVED_LINE)
        self.assertEqual(prerequisites(route[-1], CATEGORY_APPROVED_LINE), route[:-1])

    def test_line_approval_is_a_prerequisite_only_on_the_non_approved_route(self):
        deps = prerequisites("agree-procurement-specification", CATEGORY_NO_APPROVED_LINE)
        self.assertIn("approve-production-line", deps)
        self.assertNotIn(
            "approve-production-line",
            prerequisites("agree-procurement-specification", CATEGORY_APPROVED_LINE),
        )

    def test_position_is_zero_based_within_the_route(self):
        self.assertEqual(step_position("select-manufacturer", CATEGORY_APPROVED_LINE), 1)

    def test_position_of_a_skipped_activity_is_refused(self):
        with self.assertRaises(ValueError):
            step_position("approve-production-line", CATEGORY_APPROVED_LINE)


class ExecutedListTests(unittest.TestCase):
    def test_executed_list_is_canonicalised(self):
        self.assertEqual(
            validate_executed(["Define_Procurement_Requirements"]),
            ["define-procurement-requirements"],
        )

    def test_repeated_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_executed(["select-manufacturer", "select-manufacturer"])

    def test_non_sequence_executed_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_executed("select-manufacturer")

    def test_unknown_activity_in_the_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_executed(["select-manufacturer", "sign-nda"])


class FindingTests(unittest.TestCase):
    def test_clean_approved_route_has_no_ordering_finding(self):
        self.assertEqual(ordering_findings(CATEGORY_APPROVED_LINE, FULL_APPROVED), [])

    def test_clean_non_approved_route_has_no_ordering_finding(self):
        self.assertEqual(ordering_findings(CATEGORY_NO_APPROVED_LINE, FULL_UNAPPROVED), [])

    def test_swapped_pair_is_reported_as_out_of_turn(self):
        swapped = ["select-manufacturer", "define-procurement-requirements"]
        self.assertEqual(
            ordering_findings(CATEGORY_APPROVED_LINE, swapped),
            [("select-manufacturer", "define-procurement-requirements")],
        )

    def test_missing_prerequisite_is_reported(self):
        gapped = ["define-procurement-requirements", "agree-procurement-specification"]
        findings = ordering_findings(CATEGORY_APPROVED_LINE, gapped)
        self.assertIn(
            ("agree-procurement-specification", "select-manufacturer"), findings
        )

    def test_line_activity_on_the_approved_route_is_not_applicable(self):
        executed = FULL_APPROVED + ["evaluate-production-line"]
        self.assertEqual(
            not_applicable_findings(CATEGORY_APPROVED_LINE, executed),
            ["evaluate-production-line"],
        )

    def test_line_activity_on_the_non_approved_route_is_applicable(self):
        self.assertEqual(
            not_applicable_findings(CATEGORY_NO_APPROVED_LINE, FULL_UNAPPROVED), []
        )

    def test_not_applicable_activity_raises_no_ordering_noise(self):
        executed = FULL_APPROVED + ["evaluate-production-line"]
        self.assertEqual(ordering_findings(CATEGORY_APPROVED_LINE, executed), [])


class ProgressTests(unittest.TestCase):
    def test_remaining_steps_on_an_empty_list_is_the_whole_route(self):
        self.assertEqual(
            remaining_steps(CATEGORY_APPROVED_LINE, []),
            applicable_steps(CATEGORY_APPROVED_LINE),
        )

    def test_next_step_after_selection_is_the_entry_point(self):
        self.assertEqual(
            next_step(CATEGORY_APPROVED_LINE, list(COMMON_OPENING_STEPS)),
            entry_step(CATEGORY_APPROVED_LINE),
        )

    def test_next_step_for_the_non_approved_category_is_the_line_evaluation(self):
        self.assertEqual(
            next_step(CATEGORY_NO_APPROVED_LINE, list(COMMON_OPENING_STEPS)),
            "evaluate-production-line",
        )

    def test_next_step_is_none_when_the_route_is_complete(self):
        self.assertIsNone(next_step(CATEGORY_APPROVED_LINE, FULL_APPROVED))

    def test_completion_fraction_is_one_on_a_complete_route(self):
        self.assertAlmostEqual(
            completion_fraction(CATEGORY_APPROVED_LINE, FULL_APPROVED), 1.0, places=9
        )

    def test_completion_fraction_is_zero_on_an_empty_list(self):
        self.assertAlmostEqual(
            completion_fraction(CATEGORY_NO_APPROVED_LINE, []), 0.0, places=9
        )

    def test_completion_fraction_counts_only_applicable_activities(self):
        executed = list(COMMON_OPENING_STEPS) + ["evaluate-production-line"]
        self.assertAlmostEqual(
            completion_fraction(CATEGORY_APPROVED_LINE, executed), 2.0 / 7.0, places=9
        )

    def test_same_list_reads_further_along_on_the_shorter_route(self):
        executed = list(COMMON_OPENING_STEPS)
        short = completion_fraction(CATEGORY_APPROVED_LINE, executed)
        long = completion_fraction(CATEGORY_NO_APPROVED_LINE, executed)
        self.assertGreater(short, long)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "category": CATEGORY_APPROVED_LINE,
            "executed_steps": list(FULL_APPROVED),
        }
        spec.update(overrides)
        return spec

    def test_complete_approved_route_is_compliant(self):
        result = assess_procurement_sequence(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_report_carries_the_entry_point(self):
        result = assess_procurement_sequence(self._spec())
        self.assertEqual(result["entry_step"], "agree-procurement-specification")

    def test_report_names_the_skipped_line_activities(self):
        result = assess_procurement_sequence(self._spec())
        self.assertEqual(result["skipped_steps"], LINE_APPROVAL_STEPS)

    def test_line_activity_run_by_an_approved_maker_is_flagged(self):
        result = assess_procurement_sequence(
            self._spec(executed_steps=FULL_APPROVED + ["approve-production-line"])
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["not_applicable"], ("approve-production-line",))

    def test_non_approved_maker_skipping_the_line_work_is_flagged(self):
        result = assess_procurement_sequence(
            self._spec(category=CATEGORY_NO_APPROVED_LINE, executed_steps=FULL_APPROVED)
        )
        self.assertFalse(result["compliant"])
        unmet = set(pair[1] for pair in result["out_of_order"])
        self.assertEqual(unmet, set(LINE_APPROVAL_STEPS))
        self.assertEqual(result["remaining_steps"], LINE_APPROVAL_STEPS)

    def test_target_milestone_reports_outstanding_activities(self):
        result = assess_procurement_sequence(
            self._spec(
                executed_steps=list(COMMON_OPENING_STEPS),
                target_step="qualify-part-type",
            )
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_target_milestone_already_reached_is_clean(self):
        result = assess_procurement_sequence(
            self._spec(target_step="agree-procurement-specification")
        )
        self.assertTrue(result["compliant"])

    def test_target_outside_the_route_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_sequence(self._spec(target_step="approve-production-line"))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["executed_steps"]
        with self.assertRaises(ValueError):
            assess_procurement_sequence(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_sequence(["approved-line"])

    def test_completion_fraction_is_reported(self):
        result = assess_procurement_sequence(self._spec(executed_steps=[]))
        self.assertAlmostEqual(result["completion_fraction"], 0.0, places=9)


if __name__ == "__main__":
    unittest.main()
