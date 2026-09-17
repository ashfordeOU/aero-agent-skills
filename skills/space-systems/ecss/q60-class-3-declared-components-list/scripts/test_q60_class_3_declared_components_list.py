"""Contract tests for the clause 6.1.4 Class 3 declared components list logic."""

import unittest

from q60_class_3_declared_components_list_logic import (
    CLASS_3_CATEGORY,
    CONTAINER_FORMATS,
    COVERAGE_TOLERANCE,
    MANDATORY_ISSUE_FIELDS,
    assess_class_3_declared_components_list,
    build_standard_alignment,
    container_revisable,
    coverage_by_part_count,
    editability_decision,
    evaluate_issue,
    issue_completeness,
    obliged_class_3_items,
    validate_identifier,
)

ITEM = "HARN-BOX-3A"
OTHER = "STAR-TRK-1"


def item(**overrides):
    """Return one Class 3 equipment item with optional overrides."""
    base = {
        "item_id": ITEM,
        "product_category": "class-3",
        "build_standard": 4,
        "installed_part_count": 90,
    }
    base.update(overrides)
    return base


def issue(**overrides):
    """Return one acceptable issued list with optional overrides."""
    base = {
        "issue_id": "L-001",
        "item_id": ITEM,
        "container_format": "csv",
        "schema_declared": True,
        "issued_build_standard": 4,
        "declared_line_count": 90,
    }
    base.update(overrides)
    return base


def index(*entries):
    return {entry["item_id"]: entry for entry in entries}


class IdentifierTests(unittest.TestCase):
    def test_surrounding_space_is_stripped(self):
        self.assertEqual(validate_identifier("  HARN-BOX-3A "), ITEM)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(17)


class ContainerTests(unittest.TestCase):
    def test_spreadsheet_container_is_revisable(self):
        self.assertTrue(container_revisable("xlsx"))

    def test_flattened_print_is_not_revisable(self):
        self.assertFalse(container_revisable("pdf-flat"))

    def test_scan_is_not_revisable(self):
        self.assertFalse(container_revisable("pdf-scan"))

    def test_lookup_ignores_case(self):
        self.assertTrue(container_revisable("CSV"))

    def test_unknown_container_rejected(self):
        with self.assertRaises(ValueError):
            container_revisable("whatever-arrived")

    def test_every_known_container_answers_a_boolean(self):
        for fmt in CONTAINER_FORMATS:
            self.assertIsInstance(container_revisable(fmt), bool)


class EditabilityTests(unittest.TestCase):
    def test_revisable_container_with_schema_is_editable(self):
        self.assertEqual(editability_decision("ods", True), "editable")

    def test_unrevisable_container_reported_first(self):
        self.assertEqual(
            editability_decision("pdf-flat", False), "container-not-revisable"
        )

    def test_revisable_container_without_schema_is_not_editable(self):
        self.assertEqual(editability_decision("xlsx", False), "schema-not-declared")

    def test_non_boolean_schema_flag_rejected(self):
        with self.assertRaises(ValueError):
            editability_decision("csv", "yes")


class CompletenessTests(unittest.TestCase):
    def test_complete_issue_scores_one(self):
        missing, fraction = issue_completeness(issue())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_absent_field_is_named(self):
        incomplete = issue()
        del incomplete["container_format"]
        missing, fraction = issue_completeness(incomplete)
        self.assertEqual(missing, ("container_format",))
        expected = (len(MANDATORY_ISSUE_FIELDS) - 1) / len(MANDATORY_ISSUE_FIELDS)
        self.assertAlmostEqual(fraction, expected, places=9)

    def test_blank_string_counts_as_missing(self):
        missing, _ = issue_completeness(issue(item_id="  "))
        self.assertEqual(missing, ("item_id",))

    def test_none_counts_as_missing(self):
        missing, _ = issue_completeness(issue(declared_line_count=None))
        self.assertEqual(missing, ("declared_line_count",))

    def test_non_mapping_issue_rejected(self):
        with self.assertRaises(ValueError):
            issue_completeness(["L-001"])


class BuildStandardTests(unittest.TestCase):
    def test_same_standard_is_aligned(self):
        self.assertEqual(build_standard_alignment(4, 4), "aligned")

    def test_older_issue_is_behind_the_build(self):
        self.assertEqual(build_standard_alignment(2, 4), "behind-build")

    def test_newer_issue_is_ahead_of_the_build(self):
        self.assertEqual(build_standard_alignment(6, 4), "ahead-of-build")

    def test_negative_standard_rejected(self):
        with self.assertRaises(ValueError):
            build_standard_alignment(-1, 4)

    def test_boolean_standard_rejected(self):
        with self.assertRaises(ValueError):
            build_standard_alignment(True, 4)


class ObligedItemTests(unittest.TestCase):
    def test_only_class_3_items_are_obliged(self):
        obliged = obliged_class_3_items(
            [item(), item(item_id=OTHER, product_category="class-1")]
        )
        self.assertEqual(obliged, (ITEM,))

    def test_category_matching_ignores_case(self):
        self.assertEqual(obliged_class_3_items([item(product_category="CLASS-3")]), (ITEM,))

    def test_repeated_item_identifier_rejected(self):
        with self.assertRaises(ValueError):
            obliged_class_3_items([item(), item()])

    def test_zero_installed_part_count_rejected(self):
        with self.assertRaises(ValueError):
            obliged_class_3_items([item(installed_part_count=0)])

    def test_build_without_a_class_3_item_rejected(self):
        with self.assertRaises(ValueError):
            obliged_class_3_items([item(product_category="class-2")])

    def test_empty_build_rejected(self):
        with self.assertRaises(ValueError):
            obliged_class_3_items([])

    def test_obliged_category_constant_is_class_three(self):
        self.assertEqual(CLASS_3_CATEGORY, "class-3")


class EvaluateIssueTests(unittest.TestCase):
    def setUp(self):
        self.index = index(item())

    def test_clean_issue_is_accepted(self):
        record = evaluate_issue(issue(), self.index)
        self.assertEqual(record["disposition"], "accepted")
        self.assertTrue(record["accepted"])

    def test_incomplete_record_is_not_reported_as_a_format_failure(self):
        broken = issue()
        del broken["schema_declared"]
        record = evaluate_issue(broken, self.index)
        self.assertEqual(record["disposition"], "issue-record-incomplete")
        self.assertIsNone(record["editability"])

    def test_issue_for_an_item_outside_the_build(self):
        record = evaluate_issue(issue(item_id="NOT-IN-BUILD"), self.index)
        self.assertEqual(record["disposition"], "unknown-equipment-item")

    def test_issue_for_another_category_is_outside_the_obligation(self):
        idx = index(item(), item(item_id=OTHER, product_category="class-1"))
        record = evaluate_issue(issue(item_id=OTHER), idx)
        self.assertEqual(record["disposition"], "outside-class-3-obligation")

    def test_unrevisable_container_is_rejected_even_with_right_content(self):
        record = evaluate_issue(issue(container_format="pdf-flat"), self.index)
        self.assertEqual(record["disposition"], "container-not-revisable")

    def test_missing_schema_is_its_own_finding(self):
        record = evaluate_issue(issue(schema_declared=False), self.index)
        self.assertEqual(record["disposition"], "schema-not-declared")

    def test_issue_ahead_of_the_build_is_kept_separate(self):
        record = evaluate_issue(issue(issued_build_standard=7), self.index)
        self.assertEqual(record["disposition"], "build-standard-ahead")

    def test_issue_behind_the_build_is_kept_separate(self):
        record = evaluate_issue(issue(issued_build_standard=1), self.index)
        self.assertEqual(record["disposition"], "build-standard-behind")

    def test_short_line_count_is_a_scope_finding(self):
        record = evaluate_issue(issue(declared_line_count=12), self.index)
        self.assertEqual(record["disposition"], "line-count-below-installed-parts")

    def test_longer_line_count_is_not_a_defect(self):
        record = evaluate_issue(issue(declared_line_count=140), self.index)
        self.assertEqual(record["disposition"], "accepted")

    def test_repeat_issue_for_a_closed_item(self):
        record = evaluate_issue(issue(), self.index, closed_items={ITEM})
        self.assertEqual(record["disposition"], "repeat-issue-for-closed-item")

    def test_empty_item_index_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_issue(issue(), {})


class CoverageTests(unittest.TestCase):
    def test_single_accepted_item_covers_the_build(self):
        idx = index(item())
        records = [evaluate_issue(issue(), idx)]
        self.assertAlmostEqual(
            coverage_by_part_count(records, idx, (ITEM,)), 1.0, places=9
        )

    def test_coverage_weights_by_installed_part_count(self):
        big = item(item_id="BIG", installed_part_count=300)
        small = item(item_id="SMALL", installed_part_count=100)
        idx = index(big, small)
        records = [evaluate_issue(issue(item_id="SMALL", declared_line_count=100), idx)]
        self.assertAlmostEqual(
            coverage_by_part_count(records, idx, ("BIG", "SMALL")), 0.25, places=9
        )

    def test_records_without_a_disposition_rejected(self):
        idx = index(item())
        with self.assertRaises(ValueError):
            coverage_by_part_count([{"item_id": ITEM}], idx, (ITEM,))

    def test_empty_obliged_set_rejected(self):
        idx = index(item())
        with self.assertRaises(ValueError):
            coverage_by_part_count([], idx, ())


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {"items": [item()], "issues": [issue()]}
        base.update(overrides)
        return base

    def test_clean_build_is_issuable(self):
        result = assess_class_3_declared_components_list(self._spec())
        self.assertTrue(result["issuable"])
        self.assertEqual(result["verdict"], "issue")
        self.assertEqual(result["findings"], [])

    def test_item_with_no_list_is_reported(self):
        spec = self._spec(items=[item(), item(item_id="SECOND")], issues=[issue()])
        result = assess_class_3_declared_components_list(spec)
        self.assertEqual(result["items_without_a_list"], ("SECOND",))
        self.assertEqual(result["verdict"], "hold")

    def test_programme_wide_sheet_does_not_close_every_item(self):
        spec = self._spec(
            items=[item(), item(item_id="SECOND", installed_part_count=10)],
            issues=[issue(declared_line_count=100)],
        )
        result = assess_class_3_declared_components_list(spec)
        self.assertIn("SECOND", result["items_without_a_list"])

    def test_other_category_items_leave_the_denominator_alone(self):
        spec = self._spec(
            items=[item(), item(item_id=OTHER, product_category="class-1")],
            issues=[issue()],
        )
        result = assess_class_3_declared_components_list(spec)
        self.assertAlmostEqual(result["part_count_coverage"], 1.0, places=9)

    def test_corrected_resubmission_after_a_rejection_is_assessed_on_its_merits(self):
        spec = self._spec(
            issues=[
                issue(issue_id="L-001", container_format="pdf-flat"),
                issue(issue_id="L-002"),
            ]
        )
        result = assess_class_3_declared_components_list(spec)
        dispositions = [record["disposition"] for record in result["records"]]
        self.assertEqual(dispositions, ["container-not-revisable", "accepted"])

    def test_second_list_after_an_accepted_one_is_a_repeat(self):
        spec = self._spec(
            issues=[issue(issue_id="L-001"), issue(issue_id="L-002")]
        )
        result = assess_class_3_declared_components_list(spec)
        self.assertEqual(
            result["records"][1]["disposition"], "repeat-issue-for-closed-item"
        )

    def test_findings_are_ranked_worst_first(self):
        incomplete = issue(issue_id="L-000")
        del incomplete["container_format"]
        spec = self._spec(
            items=[item(), item(item_id="SECOND")],
            issues=[issue(issue_id="L-003", declared_line_count=2), incomplete],
        )
        result = assess_class_3_declared_components_list(spec)
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_exactly_met_coverage_passes_at_the_boundary(self):
        big = item(item_id="BIG", installed_part_count=300)
        small = item(item_id="SMALL", installed_part_count=100)
        spec = {
            "items": [big, small],
            "issues": [issue(item_id="BIG", declared_line_count=300)],
            "required_coverage": 0.75,
        }
        result = assess_class_3_declared_components_list(spec)
        self.assertAlmostEqual(result["part_count_coverage"], 0.75, places=9)
        self.assertAlmostEqual(result["required_coverage"], 0.75, places=9)

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_missing_issues_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_declared_components_list({"items": [item()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_declared_components_list(["items"])

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_declared_components_list(self._spec(required_coverage=1.4))

    def test_boolean_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_declared_components_list(self._spec(required_coverage=True))

    def test_non_sequence_issues_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_declared_components_list(self._spec(issues="L-001"))


if __name__ == "__main__":
    unittest.main()
