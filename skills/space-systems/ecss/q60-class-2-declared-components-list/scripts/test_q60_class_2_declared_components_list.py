"""Contract tests for the clause 5.1.4 Class 2 declared components list logic.

Each test class follows one step of the SKILL.md workflow: the input
validation, the per-record disposition, the coverage gate and the closing
verdict. Offline, stdlib unittest; run it as the review checklist before
the leaf is issued.
"""

import unittest

from q60_class_2_declared_components_list_logic import (
    COVERAGE_TOLERANCE,
    FILE_FORMS,
    MANDATORY_ISSUE_ATTRIBUTES,
    MANDATORY_LINE_FIELDS,
    OBLIGED_RELIABILITY_CLASS,
    assess_declared_components_list,
    evaluate_issue,
    form_is_editable,
    issue_line_completeness,
    item_issue_coverage,
    line_completeness,
    obliged_items,
    revision_alignment,
    update_latency,
    validate_item_id,
)

ITEM = "RIU-B"


def line(number="RES-1K-0805", **overrides):
    """Return one fully populated list line."""
    base = {
        "part_number": number,
        "manufacturer": "Vendor GmbH",
        "procurement_specification": "PSPEC-0042",
        "quality_level": "level-2",
        "quantity": 8,
    }
    base.update(overrides)
    return base


def item(**overrides):
    """Return one Class 2 equipment item."""
    base = {
        "item_id": ITEM,
        "reliability_class": "class-2",
        "build_revision": 4,
        "installed_part_count": 2,
    }
    base.update(overrides)
    return base


def issue(**overrides):
    """Return one acceptable issued list for the Class 2 item."""
    base = {
        "issue_id": "DCL-001",
        "item_id": ITEM,
        "file_form": "source-spreadsheet",
        "issued_revision": 4,
        "lines": [line(), line("CAP-10N-0603")],
    }
    base.update(overrides)
    return base


def index(*items):
    return {entry["item_id"]: entry for entry in items}


class ValidateItemTests(unittest.TestCase):
    def test_identifier_is_stripped(self):
        self.assertEqual(validate_item_id("  RIU-B "), ITEM)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_item_id("   ")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_item_id(11)

    def test_class_two_item_is_obliged(self):
        self.assertEqual(obliged_items([item()]), (ITEM,))

    def test_other_class_item_is_not_obliged(self):
        with self.assertRaises(ValueError):
            obliged_items([item(reliability_class="class-3")])

    def test_duplicate_item_rejected(self):
        with self.assertRaises(ValueError):
            obliged_items([item(), item()])

    def test_zero_installed_part_count_rejected(self):
        with self.assertRaises(ValueError):
            obliged_items([item(installed_part_count=0)])

    def test_obliged_class_is_the_one_the_module_names(self):
        self.assertEqual(OBLIGED_RELIABILITY_CLASS, "class-2")


class FileFormTests(unittest.TestCase):
    def test_source_spreadsheet_is_editable(self):
        self.assertTrue(form_is_editable("source-spreadsheet"))

    def test_flattened_print_is_not_editable(self):
        self.assertFalse(form_is_editable("flattened-print"))

    def test_locked_document_is_not_editable(self):
        self.assertFalse(form_is_editable("locked-document"))

    def test_lookup_is_case_insensitive(self):
        self.assertTrue(form_is_editable("Database-Export"))

    def test_unknown_form_rejected(self):
        with self.assertRaises(ValueError):
            form_is_editable("whatever-the-supplier-emailed")

    def test_every_known_form_answers_a_boolean(self):
        for form in FILE_FORMS:
            self.assertIsInstance(form_is_editable(form), bool)


class LineCompletenessTests(unittest.TestCase):
    def test_full_line_scores_one(self):
        missing, fraction = line_completeness(line())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_blank_manufacturer_counts_as_missing(self):
        missing, fraction = line_completeness(line(manufacturer="  "))
        self.assertIn("manufacturer", missing)
        self.assertAlmostEqual(
            fraction,
            (len(MANDATORY_LINE_FIELDS) - 1) / len(MANDATORY_LINE_FIELDS),
            places=9,
        )

    def test_zero_quantity_counts_as_missing(self):
        missing, _ = line_completeness(line(quantity=0))
        self.assertIn("quantity", missing)

    def test_absent_field_counts_as_missing(self):
        entry = line()
        del entry["quality_level"]
        missing, _ = line_completeness(entry)
        self.assertIn("quality_level", missing)

    def test_non_mapping_line_rejected(self):
        with self.assertRaises(ValueError):
            line_completeness("RES-1K-0805")

    def test_issue_mean_is_the_mean_of_its_lines(self):
        mean, deficient = issue_line_completeness(
            [line(), line("CAP-10N-0603", manufacturer=None)]
        )
        expected = (1.0 + (len(MANDATORY_LINE_FIELDS) - 1) / len(MANDATORY_LINE_FIELDS)) / 2
        self.assertAlmostEqual(mean, expected, places=9)
        self.assertEqual(deficient, ("CAP-10N-0603",))

    def test_deficient_line_without_a_part_number_is_positioned(self):
        _, deficient = issue_line_completeness([line(number=None)])
        self.assertEqual(deficient, ("line 1",))

    def test_empty_line_set_rejected(self):
        with self.assertRaises(ValueError):
            issue_line_completeness([])


class RevisionTests(unittest.TestCase):
    def test_same_revision_is_aligned(self):
        self.assertEqual(revision_alignment(4, 4), "aligned")

    def test_older_issue_is_behind_the_build(self):
        self.assertEqual(revision_alignment(2, 4), "behind-build")

    def test_newer_issue_is_ahead_of_the_build(self):
        self.assertEqual(revision_alignment(6, 4), "ahead-of-build")

    def test_negative_revision_rejected(self):
        with self.assertRaises(ValueError):
            revision_alignment(-1, 4)


class EvaluateIssueTests(unittest.TestCase):
    def setUp(self):
        self.index = index(item())

    def test_clean_issue_is_accepted(self):
        record = evaluate_issue(issue(), self.index)
        self.assertEqual(record["disposition"], "accepted")
        self.assertTrue(record["editable"])

    def test_incomplete_record_stops_before_any_other_test(self):
        record = evaluate_issue(issue(file_form=None), self.index)
        self.assertEqual(record["disposition"], "record-incomplete")
        self.assertIn("file_form", record["missing_attributes"])

    def test_empty_line_set_is_an_incomplete_record(self):
        record = evaluate_issue(issue(lines=[]), self.index)
        self.assertEqual(record["disposition"], "record-incomplete")

    def test_unknown_item_is_named(self):
        record = evaluate_issue(issue(item_id="GHOST-UNIT"), self.index)
        self.assertEqual(record["disposition"], "unknown-item")

    def test_item_of_another_class_is_outside_the_obligation(self):
        other = index(item(reliability_class="class-3"))
        record = evaluate_issue(issue(), other)
        self.assertEqual(record["disposition"], "outside-obligation")

    def test_uneditable_form_is_refused(self):
        record = evaluate_issue(issue(file_form="image-scan"), self.index)
        self.assertEqual(record["disposition"], "form-not-editable")

    def test_issue_behind_the_build_is_refused(self):
        record = evaluate_issue(issue(issued_revision=2), self.index)
        self.assertEqual(record["disposition"], "revision-behind-build")

    def test_issue_ahead_of_the_build_is_refused(self):
        record = evaluate_issue(issue(issued_revision=9), self.index)
        self.assertEqual(record["disposition"], "revision-ahead-of-build")

    def test_short_line_count_is_refused(self):
        record = evaluate_issue(issue(lines=[line()]), self.index)
        self.assertEqual(record["disposition"], "line-count-short")

    def test_deficient_line_fields_are_refused_and_named(self):
        record = evaluate_issue(
            issue(lines=[line(), line("CAP-10N-0603", quality_level="")]), self.index
        )
        self.assertEqual(record["disposition"], "line-fields-incomplete")
        self.assertEqual(record["deficient_lines"], ("CAP-10N-0603",))

    def test_a_relaxed_line_requirement_admits_a_thin_line(self):
        record = evaluate_issue(
            issue(lines=[line(), line("CAP-10N-0603", quality_level="")]),
            self.index,
            required_line_completeness=0.85,
        )
        self.assertEqual(record["disposition"], "accepted")

    def test_second_issue_for_a_closed_item_is_a_duplicate(self):
        record = evaluate_issue(issue(), self.index, already_seen={ITEM})
        self.assertEqual(record["disposition"], "duplicate-item-issue")

    def test_empty_item_index_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_issue(issue(), {})

    def test_out_of_range_line_requirement_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_issue(issue(), self.index, required_line_completeness=2.0)

    def test_mandatory_issue_attributes_are_all_checked(self):
        for attribute in MANDATORY_ISSUE_ATTRIBUTES:
            entry = issue()
            del entry[attribute]
            record = evaluate_issue(entry, self.index)
            self.assertEqual(record["disposition"], "record-incomplete")


class UpdateLatencyTests(unittest.TestCase):
    def decision(self, reference="PCB-D-1", **overrides):
        base = {"decision_id": reference, "decision_day": 10, "incorporated_day": 20}
        base.update(overrides)
        return base

    def test_timely_incorporation_raises_nothing(self):
        latency = update_latency([self.decision()], 100, 30)
        self.assertEqual(latency["open_past_response"], ())
        self.assertEqual(latency["late_but_incorporated"], ())

    def test_late_incorporation_is_recorded_though_it_landed(self):
        latency = update_latency([self.decision(incorporated_day=90)], 100, 30)
        self.assertEqual(latency["late_but_incorporated"], (("PCB-D-1", 80),))

    def test_open_decision_is_aged_against_the_assessment_day(self):
        latency = update_latency([self.decision(incorporated_day=None)], 100, 30)
        self.assertEqual(latency["open_past_response"], (("PCB-D-1", 90),))

    def test_open_decision_inside_the_window_is_not_a_finding(self):
        latency = update_latency([self.decision(incorporated_day=None)], 20, 30)
        self.assertEqual(latency["open_past_response"], ())

    def test_slowest_incorporation_is_kept(self):
        latency = update_latency(
            [
                self.decision("PCB-D-1", incorporated_day=15),
                self.decision("PCB-D-2", incorporated_day=95),
            ],
            100,
            120,
        )
        self.assertEqual(latency["slowest_incorporation"], ("PCB-D-2", 85))

    def test_duplicate_decision_rejected(self):
        with self.assertRaises(ValueError):
            update_latency([self.decision(), self.decision()], 100, 30)

    def test_decision_after_the_assessment_day_rejected(self):
        with self.assertRaises(ValueError):
            update_latency([self.decision(decision_day=150)], 100, 30)

    def test_incorporation_before_the_decision_rejected(self):
        with self.assertRaises(ValueError):
            update_latency([self.decision(incorporated_day=5)], 100, 30)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.items = [item(), item(item_id="PSU-C", installed_part_count=6)]
        self.index = index(*self.items)
        self.obliged = obliged_items(self.items)

    def test_every_item_closed_covers_everything(self):
        records = [
            evaluate_issue(issue(), self.index),
            evaluate_issue(
                issue(
                    issue_id="DCL-002",
                    item_id="PSU-C",
                    lines=[line("R%d" % n) for n in range(6)],
                ),
                self.index,
            ),
        ]
        self.assertAlmostEqual(
            item_issue_coverage(records, self.index, self.obliged), 1.0, places=9
        )

    def test_coverage_is_part_count_weighted(self):
        records = [evaluate_issue(issue(), self.index)]
        self.assertAlmostEqual(
            item_issue_coverage(records, self.index, self.obliged), 2 / 8, places=9
        )

    def test_refused_issue_covers_nothing(self):
        records = [evaluate_issue(issue(file_form="paper-copy"), self.index)]
        self.assertAlmostEqual(
            item_issue_coverage(records, self.index, self.obliged), 0.0, places=9
        )

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            item_issue_coverage([{"no": "disposition"}], self.index, self.obliged)


class AssessmentTests(unittest.TestCase):
    def spec(self, **overrides):
        base = {
            "items": [item()],
            "issues": [issue()],
            "board_decisions": [],
            "assessment_day": 100,
            "update_response_days": 30,
            "required_line_completeness": 1.0,
            "required_item_coverage": 1.0,
        }
        base.update(overrides)
        return base

    def test_clean_build_is_issuable(self):
        result = assess_declared_components_list(self.spec())
        self.assertTrue(result["issuable"])
        self.assertEqual(result["verdict"], "lists issuable")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["item_coverage"], 1.0, places=9)

    def test_item_with_no_list_is_named(self):
        result = assess_declared_components_list(
            self.spec(
                items=[item(), item(item_id="PSU-C", installed_part_count=6)],
                required_item_coverage=0.0,
            )
        )
        self.assertEqual(result["items_without_a_list"], ("PSU-C",))
        self.assertFalse(result["issuable"])

    def test_open_board_decision_stops_the_verdict(self):
        result = assess_declared_components_list(
            self.spec(
                board_decisions=[
                    {
                        "decision_id": "PCB-D-7",
                        "decision_day": 10,
                        "incorporated_day": None,
                    }
                ]
            )
        )
        self.assertFalse(result["issuable"])
        self.assertEqual(
            result["update_latency"]["open_past_response"], (("PCB-D-7", 90),)
        )

    def test_a_refused_issue_then_a_corrected_one_closes_the_item(self):
        result = assess_declared_components_list(
            self.spec(
                issues=[
                    issue(issue_id="DCL-001", file_form="flattened-print"),
                    issue(issue_id="DCL-002"),
                ]
            )
        )
        self.assertAlmostEqual(result["item_coverage"], 1.0, places=9)
        self.assertEqual(result["findings"][0]["disposition"], "form-not-editable")

    def test_coverage_exactly_at_a_reduced_requirement_is_met(self):
        result = assess_declared_components_list(
            self.spec(
                items=[item(), item(item_id="PSU-C", installed_part_count=6)],
                required_item_coverage=2 / 8,
            )
        )
        self.assertAlmostEqual(
            result["item_coverage"], result["required_item_coverage"], places=9
        )

    def test_findings_are_ranked_most_severe_first(self):
        result = assess_declared_components_list(
            self.spec(
                issues=[
                    issue(issue_id="DCL-001", item_id="GHOST-UNIT"),
                    issue(issue_id="DCL-002", issued_revision=1),
                ],
                board_decisions=[
                    {
                        "decision_id": "PCB-D-7",
                        "decision_day": 10,
                        "incorporated_day": None,
                    }
                ],
            )
        )
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_duplicate_issue_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list(self.spec(issues=[issue(), issue()]))

    def test_missing_key_rejected(self):
        spec = self.spec()
        del spec["issues"]
        with self.assertRaises(ValueError):
            assess_declared_components_list(spec)

    def test_out_of_range_coverage_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list(self.spec(required_item_coverage=1.2))

    def test_negative_response_window_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list(self.spec(update_response_days=-1))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list("a list of parts")

    def test_tolerance_is_small_enough_to_be_representation_error(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
