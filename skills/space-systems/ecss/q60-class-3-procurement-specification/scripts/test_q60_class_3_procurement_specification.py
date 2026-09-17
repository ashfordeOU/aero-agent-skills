"""Contract test for the ECSS-Q-ST-60C clause 6.3.2 Class 3 specification leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_3_procurement_specification.py
"""

import datetime
import unittest

from q60_class_3_procurement_specification_logic import (
    BUYABLE_STATUS,
    COMPLETENESS_TOLERANCE,
    CONTROL_BEARING_KINDS,
    LINE_STATUSES,
    REQUIRED_SPECIFICATION_CONTENT,
    SPECIFICATION_KINDS,
    SPECIFICATION_STATUSES,
    TARGET_CATEGORY,
    assess_class_3_purchasing_specifications,
    assess_specified_line,
    compare_revisions,
    content_completeness,
    index_specifications,
    kind_findings,
    missing_content,
    parse_iso_date,
    revision_findings,
    revision_key,
    status_findings,
)

ORDER_DATE = datetime.date(2026, 3, 1)


def specification(**overrides):
    entry = {
        "document_id": "ps-1001",
        "part_type": "ldo-regulator-3v3",
        "kind": "project-purchasing-specification",
        "issue_identifier": "ps-1001-issue-b",
        "held_under_configuration_control": True,
        "status": "released",
        "released_on": "2026-01-15",
        "revision": "B",
        "content": list(REQUIRED_SPECIFICATION_CONTENT),
    }
    entry.update(overrides)
    return entry


def line(**overrides):
    entry = {"part_type": "ldo-regulator-3v3", "cited_revision": "B"}
    entry.update(overrides)
    return entry


def order(**overrides):
    entry = {
        "order_id": "po-4207",
        "declared_category": TARGET_CATEGORY,
        "order_date": "2026-03-01",
        "specifications": [specification()],
        "lines": [line()],
    }
    entry.update(overrides)
    return entry


class RevisionTests(unittest.TestCase):
    def test_the_same_revision_compares_equal(self):
        self.assertEqual(compare_revisions("B", "B"), 0)

    def test_a_later_letter_compares_later(self):
        self.assertEqual(compare_revisions("C", "B"), 1)

    def test_an_earlier_letter_compares_earlier(self):
        self.assertEqual(compare_revisions("A", "B"), -1)

    def test_a_numeric_suffix_sits_after_its_bare_letter(self):
        self.assertEqual(compare_revisions("B1", "B"), 1)

    def test_a_numeric_suffix_sits_before_the_next_letter(self):
        self.assertEqual(compare_revisions("B9", "C"), -1)

    def test_a_two_letter_revision_sits_after_every_single_letter(self):
        self.assertEqual(compare_revisions("AA", "Z"), 1)

    def test_revision_comparison_is_case_insensitive(self):
        self.assertEqual(compare_revisions("b", "B"), 0)

    def test_a_revision_that_is_not_a_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            revision_key("the-latest-one")

    def test_an_empty_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            revision_key("  ")


class ContentTests(unittest.TestCase):
    def test_a_complete_specification_leaves_no_content_missing(self):
        self.assertEqual(missing_content(list(REQUIRED_SPECIFICATION_CONTENT)), ())

    def test_a_complete_specification_scores_one(self):
        self.assertAlmostEqual(
            content_completeness(list(REQUIRED_SPECIFICATION_CONTENT)), 1.0, places=9
        )

    def test_an_empty_specification_scores_zero(self):
        self.assertAlmostEqual(content_completeness([]), 0.0, places=9)

    def test_half_the_content_scores_a_half(self):
        half = len(REQUIRED_SPECIFICATION_CONTENT) // 2
        self.assertAlmostEqual(
            content_completeness(list(REQUIRED_SPECIFICATION_CONTENT[:half])),
            0.5,
            places=9,
        )

    def test_each_absent_item_is_named_separately(self):
        absent = missing_content([REQUIRED_SPECIFICATION_CONTENT[0]])
        self.assertEqual(len(absent), len(REQUIRED_SPECIFICATION_CONTENT) - 1)

    def test_a_repeated_item_does_not_count_twice(self):
        supplied = [REQUIRED_SPECIFICATION_CONTENT[0], REQUIRED_SPECIFICATION_CONTENT[0]]
        self.assertEqual(
            len(missing_content(supplied)), len(REQUIRED_SPECIFICATION_CONTENT) - 1
        )

    def test_an_unknown_content_item_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_content(["whatever-the-supplier-sent"])

    def test_the_completeness_tolerance_is_small_enough_to_separate_a_bound(self):
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)


class DocumentKindTests(unittest.TestCase):
    def test_every_control_bearing_kind_is_a_published_kind(self):
        for kind in CONTROL_BEARING_KINDS:
            self.assertIn(kind, SPECIFICATION_KINDS)

    def test_a_project_specification_is_controlled_by_its_nature(self):
        self.assertEqual(kind_findings(specification()), ())

    def test_a_manufacturer_detail_specification_is_controlled_too(self):
        self.assertEqual(
            kind_findings(
                specification(kind="manufacturer-detail-specification")
            ),
            (),
        )

    def test_a_datasheet_under_control_with_an_issue_identifier_is_admitted(self):
        self.assertEqual(
            kind_findings(
                specification(
                    kind="catalogue-datasheet",
                    issue_identifier="ds-2024-06",
                    held_under_configuration_control=True,
                )
            ),
            (),
        )

    def test_a_datasheet_with_no_issue_identifier_is_uncontrolled(self):
        findings = kind_findings(
            specification(
                kind="catalogue-datasheet",
                issue_identifier="  ",
                held_under_configuration_control=True,
            )
        )
        self.assertEqual(
            findings[0]["finding"],
            "uncontrolled-datasheet-cited-as-a-purchasing-specification",
        )

    def test_a_datasheet_outside_configuration_control_is_uncontrolled(self):
        findings = kind_findings(
            specification(
                kind="catalogue-datasheet",
                held_under_configuration_control=False,
            )
        )
        self.assertEqual(len(findings), 1)

    def test_an_unknown_document_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            kind_findings(specification(kind="an-email-thread"))

    def test_a_datasheet_with_a_non_boolean_control_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            kind_findings(
                specification(
                    kind="catalogue-datasheet",
                    held_under_configuration_control="yes",
                )
            )


class IssueStatusTests(unittest.TestCase):
    def test_a_released_issue_raises_nothing(self):
        self.assertEqual(status_findings(specification(), ORDER_DATE), ())

    def test_the_buyable_status_is_one_of_the_published_statuses(self):
        self.assertIn(BUYABLE_STATUS, SPECIFICATION_STATUSES)

    def test_a_draft_issue_is_a_finding(self):
        findings = status_findings(specification(status="draft"), ORDER_DATE)
        self.assertEqual(
            findings[0]["finding"], "line-raised-against-a-specification-not-released"
        )

    def test_a_withdrawn_issue_is_a_finding(self):
        findings = status_findings(specification(status="withdrawn"), ORDER_DATE)
        self.assertEqual(len(findings), 1)

    def test_an_issue_released_after_the_order_date_is_a_finding(self):
        findings = status_findings(
            specification(released_on="2026-04-02"), ORDER_DATE
        )
        self.assertEqual(
            findings[0]["finding"], "specification-released-after-the-order-date"
        )

    def test_an_issue_released_on_the_order_date_is_accepted(self):
        self.assertEqual(
            status_findings(specification(released_on="2026-03-01"), ORDER_DATE), ()
        )

    def test_an_unknown_issue_status_is_rejected(self):
        with self.assertRaises(ValueError):
            status_findings(specification(status="nearly-done"), ORDER_DATE)

    def test_a_release_date_that_is_not_a_date_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("last spring", "released_on")


class CitedRevisionTests(unittest.TestCase):
    def test_citing_the_released_revision_raises_nothing(self):
        self.assertEqual(revision_findings("B", specification()), ())

    def test_citing_an_earlier_revision_is_a_superseded_citation(self):
        findings = revision_findings("A", specification())
        self.assertEqual(findings[0]["finding"], "order-cites-a-superseded-revision")

    def test_citing_a_later_revision_is_a_citation_of_nothing(self):
        findings = revision_findings("C", specification())
        self.assertEqual(
            findings[0]["finding"], "order-cites-a-revision-that-was-never-released"
        )

    def test_citing_a_numeric_sub_revision_of_the_released_letter_is_later(self):
        findings = revision_findings("B1", specification())
        self.assertEqual(
            findings[0]["finding"], "order-cites-a-revision-that-was-never-released"
        )


class LibraryTests(unittest.TestCase):
    def test_a_library_indexes_by_part_type(self):
        index = index_specifications([specification()])
        self.assertIn("ldo-regulator-3v3", index)

    def test_two_documents_claiming_one_part_type_are_rejected(self):
        with self.assertRaises(ValueError):
            index_specifications(
                [specification(), specification(document_id="ps-1002")]
            )

    def test_an_empty_library_is_rejected(self):
        with self.assertRaises(ValueError):
            index_specifications([])

    def test_a_document_with_no_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            index_specifications([specification(document_id="  ")])

    def test_a_bare_string_is_not_a_library(self):
        with self.assertRaises(ValueError):
            index_specifications("ps-1001")


class LineTests(unittest.TestCase):
    def test_a_line_bought_to_a_clean_specification_is_specified(self):
        record = assess_specified_line(
            line(), index_specifications([specification()]), ORDER_DATE
        )
        self.assertEqual(
            record["status"], "class-3-line-bought-to-a-controlled-specification"
        )
        self.assertTrue(record["specified"])
        self.assertEqual(record["findings"], [])

    def test_a_line_with_no_specification_at_all_is_named(self):
        record = assess_specified_line(
            line(part_type="unlisted-opto"),
            index_specifications([specification()]),
            ORDER_DATE,
        )
        self.assertEqual(record["status"], "class-3-line-has-no-specification")
        self.assertEqual(
            record["findings"][0]["finding"],
            "part-type-ordered-against-no-purchasing-specification",
        )

    def test_content_exactly_on_the_project_minimum_is_accepted(self):
        half = len(REQUIRED_SPECIFICATION_CONTENT) // 2
        partial = list(REQUIRED_SPECIFICATION_CONTENT[:half])
        self.assertAlmostEqual(content_completeness(partial), 0.5, places=9)
        record = assess_specified_line(
            line(),
            index_specifications([specification(content=partial)]),
            ORDER_DATE,
            minimum_completeness=0.5,
        )
        self.assertTrue(record["specified"])

    def test_content_below_the_project_minimum_names_every_absent_item(self):
        record = assess_specified_line(
            line(),
            index_specifications(
                [specification(content=[REQUIRED_SPECIFICATION_CONTENT[0]])]
            ),
            ORDER_DATE,
            minimum_completeness=1.0,
        )
        names = [f["finding"] for f in record["findings"]]
        self.assertEqual(
            names.count("purchasing-specification-content-missing"),
            len(REQUIRED_SPECIFICATION_CONTENT) - 1,
        )

    def test_every_defect_on_one_line_is_reported_at_once(self):
        record = assess_specified_line(
            line(cited_revision="A"),
            index_specifications(
                [
                    specification(
                        kind="catalogue-datasheet",
                        issue_identifier="  ",
                        held_under_configuration_control=False,
                        status="draft",
                    )
                ]
            ),
            ORDER_DATE,
        )
        names = [f["finding"] for f in record["findings"]]
        self.assertIn(
            "uncontrolled-datasheet-cited-as-a-purchasing-specification", names
        )
        self.assertIn("line-raised-against-a-specification-not-released", names)
        self.assertIn("order-cites-a-superseded-revision", names)

    def test_every_finding_carries_the_part_type_it_belongs_to(self):
        record = assess_specified_line(
            line(cited_revision="A"),
            index_specifications([specification()]),
            ORDER_DATE,
        )
        for finding in record["findings"]:
            self.assertEqual(finding["part_type"], "ldo-regulator-3v3")

    def test_every_status_name_is_one_the_module_publishes(self):
        index = index_specifications([specification()])
        self.assertIn(
            assess_specified_line(line(), index, ORDER_DATE)["status"], LINE_STATUSES
        )
        self.assertIn(
            assess_specified_line(
                line(part_type="unlisted-opto"), index, ORDER_DATE
            )["status"],
            LINE_STATUSES,
        )

    def test_a_minimum_completeness_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_specified_line(
                line(),
                index_specifications([specification()]),
                ORDER_DATE,
                minimum_completeness=1.5,
            )

    def test_a_non_mapping_line_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_specified_line(
                "ldo-regulator-3v3",
                index_specifications([specification()]),
                ORDER_DATE,
            )


class OrderTests(unittest.TestCase):
    def test_a_fully_documented_order_is_documented(self):
        report = assess_class_3_purchasing_specifications(order())
        self.assertTrue(report["order_documented"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["specified_fraction"], 1.0, places=9)

    def test_a_specification_held_for_a_type_nobody_ordered_is_reported(self):
        report = assess_class_3_purchasing_specifications(
            order(
                specifications=[
                    specification(),
                    specification(document_id="ps-1002", part_type="shunt-10m"),
                ]
            )
        )
        self.assertEqual(report["specifications_never_ordered"], ["shunt-10m"])
        self.assertFalse(report["order_documented"])

    def test_the_specified_fraction_counts_only_clean_lines(self):
        report = assess_class_3_purchasing_specifications(
            order(
                specifications=[
                    specification(),
                    specification(
                        document_id="ps-1002", part_type="shunt-10m", status="draft"
                    ),
                ],
                lines=[line(), line(part_type="shunt-10m")],
            )
        )
        self.assertAlmostEqual(report["specified_fraction"], 0.5, places=9)
        self.assertEqual(report["defective_part_types"], ["shunt-10m"])

    def test_an_order_declared_in_another_category_is_not_checked_here(self):
        report = assess_class_3_purchasing_specifications(
            order(declared_category="class-2")
        )
        self.assertIn(
            "declared-category-is-not-the-one-being-checked",
            [f["finding"] for f in report["findings"]],
        )

    def test_a_repeated_ordered_part_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_purchasing_specifications(order(lines=[line(), line()]))

    def test_an_order_with_no_lines_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_purchasing_specifications(order(lines=[]))

    def test_an_empty_order_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_purchasing_specifications(order(order_id="  "))

    def test_an_order_date_that_is_not_a_date_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_purchasing_specifications(order(order_date="whenever"))

    def test_a_non_sequence_line_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_purchasing_specifications(order(lines={"part_type": "x"}))


if __name__ == "__main__":
    unittest.main()
