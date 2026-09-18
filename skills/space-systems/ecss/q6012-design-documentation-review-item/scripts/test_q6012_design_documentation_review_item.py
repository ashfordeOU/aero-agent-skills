#!/usr/bin/env python3
"""Contract test for the microwave die design documentation review item (offline)."""

import copy
import unittest

from q6012_design_documentation_review_item_logic import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_INCOMPLETE,
    CURRENCY_CURRENT,
    CURRENCY_NOT_RELEASED,
    CURRENCY_STALE,
    REQUIRED_DOCUMENT_TYPES,
    TRACE_BROKEN,
    TRACE_ORPHAN,
    TRACE_RESOLVED,
    VERDICT_ACTIONED,
    VERDICT_CLOSED,
    VERDICT_REJECTED,
    assess_completeness,
    assess_currency,
    assess_traceability,
    canonical_document_id,
    latest_issues,
    normalize_documents,
    review_design_documentation_item,
    trace_chain,
)

REFERENCE_DOCUMENTS = [
    {
        "document_id": "DS-001",
        "document_type": "die-detail-specification",
        "issue": 1,
        "issued_day": 90.0,
        "status": "document-superseded",
        "parent_id": None,
    },
    {
        "document_id": "DS-001",
        "document_type": "die-detail-specification",
        "issue": 2,
        "issued_day": 120.0,
        "status": "document-released",
        "parent_id": None,
    },
    {
        "document_id": "LD-010",
        "document_type": "die-layout-drawing",
        "issue": 1,
        "issued_day": 130.0,
        "status": "document-released",
        "parent_id": "DS-001",
    },
    {
        "document_id": "PI-020",
        "document_type": "die-process-identification",
        "issue": 1,
        "issued_day": 125.0,
        "status": "document-released",
        "parent_id": "DS-001",
    },
    {
        "document_id": "TP-030",
        "document_type": "die-electrical-test-plan",
        "issue": 2,
        "issued_day": 110.0,
        "status": "document-superseded",
        "parent_id": "DS-001",
    },
    {
        "document_id": "TP-030",
        "document_type": "die-electrical-test-plan",
        "issue": 3,
        "issued_day": 140.0,
        "status": "document-released",
        "parent_id": "DS-001",
    },
    {
        "document_id": "QR-040",
        "document_type": "die-qualification-report",
        "issue": 1,
        "issued_day": 150.0,
        "status": "document-released",
        "parent_id": "TP-030",
    },
    {
        "document_id": "SD-050",
        "document_type": "die-summary-design-sheet",
        "issue": 1,
        "issued_day": 145.0,
        "status": "document-released",
        "parent_id": "DS-001",
    },
]

REFERENCE_CASE = {
    "documents": REFERENCE_DOCUMENTS,
    "baseline_freeze_day": 100.0,
}


def _edit(target_id, target_issue, **fields):
    """Reference documents with one named issue overridden."""
    rows = copy.deepcopy(REFERENCE_DOCUMENTS)
    for row in rows:
        if row["document_id"] == target_id and row["issue"] == target_issue:
            row.update(fields)
            return rows
    raise AssertionError("no such reference row")


def _drop(target_id):
    """Reference documents with every issue of one document removed."""
    return [
        row for row in copy.deepcopy(REFERENCE_DOCUMENTS)
        if row["document_id"] != target_id
    ]


def _case(**overrides):
    case = copy.deepcopy(REFERENCE_CASE)
    case.update(overrides)
    return case


class CanonicalIdentifierTests(unittest.TestCase):
    def test_case_is_folded_to_one_spelling(self):
        self.assertEqual(canonical_document_id("ds-001"), "DS-001")

    def test_inner_and_outer_space_is_collapsed(self):
        self.assertEqual(canonical_document_id("  DS   001 "), "DS 001")

    def test_two_spellings_reach_the_same_identifier(self):
        self.assertEqual(
            canonical_document_id(" ds  001"), canonical_document_id("DS 001")
        )

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            canonical_document_id("   ")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            canonical_document_id(1001)


class NormalizeDocumentTests(unittest.TestCase):
    def test_rows_come_back_ordered_by_identifier_and_issue(self):
        rows = normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS))
        keys = [(row["document_id"], row["issue"]) for row in rows]
        self.assertEqual(keys, sorted(keys))

    def test_identifiers_are_canonicalized_on_the_way_in(self):
        rows = normalize_documents(
            _edit("SD-050", 1, document_id=" sd  050 ")
        )
        self.assertIn("SD 050", {row["document_id"] for row in rows})

    def test_parent_identifiers_are_canonicalized_too(self):
        rows = normalize_documents(_edit("LD-010", 1, parent_id="ds-001"))
        layout = [row for row in rows if row["document_id"] == "LD-010"][0]
        self.assertEqual(layout["parent_id"], "DS-001")

    def test_empty_record_rejected(self):
        with self.assertRaises(ValueError):
            normalize_documents([])

    def test_same_document_at_the_same_issue_twice_rejected(self):
        rows = copy.deepcopy(REFERENCE_DOCUMENTS)
        rows.append(copy.deepcopy(REFERENCE_DOCUMENTS[1]))
        with self.assertRaises(ValueError):
            normalize_documents(rows)

    def test_duplicate_hidden_by_spelling_is_still_rejected(self):
        rows = copy.deepcopy(REFERENCE_DOCUMENTS)
        twin = copy.deepcopy(REFERENCE_DOCUMENTS[1])
        twin["document_id"] = "ds-001"
        rows.append(twin)
        with self.assertRaises(ValueError):
            normalize_documents(rows)

    def test_one_identifier_under_two_types_rejected(self):
        rows = _edit("TP-030", 2, document_type="die-layout-drawing")
        with self.assertRaises(ValueError):
            normalize_documents(rows)

    def test_document_deriving_from_itself_rejected(self):
        rows = _edit("LD-010", 1, parent_id="LD-010")
        with self.assertRaises(ValueError):
            normalize_documents(rows)

    def test_issue_zero_rejected(self):
        with self.assertRaises(ValueError):
            normalize_documents(_edit("LD-010", 1, issue=0))

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            normalize_documents(_edit("LD-010", 1, status="probably-fine"))

    def test_unknown_field_rejected(self):
        rows = copy.deepcopy(REFERENCE_DOCUMENTS)
        rows[0]["author"] = "the drawing office"
        with self.assertRaises(ValueError):
            normalize_documents(rows)

    def test_document_type_outside_the_programme_set_rejected(self):
        rows = _edit("SD-050", 1, document_type="die-marketing-sheet")
        with self.assertRaises(ValueError):
            normalize_documents(rows)

    def test_negative_issue_day_rejected(self):
        with self.assertRaises(ValueError):
            normalize_documents(_edit("LD-010", 1, issued_day=-5.0))


class LatestIssueTests(unittest.TestCase):
    def test_the_highest_issue_controls(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        self.assertEqual(latest["DS-001"]["issue"], 2)
        self.assertEqual(latest["TP-030"]["issue"], 3)

    def test_every_identifier_has_exactly_one_controlling_issue(self):
        documents = normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS))
        latest = latest_issues(documents)
        self.assertEqual(len(latest), 6)


class CompletenessTests(unittest.TestCase):
    def test_a_full_record_is_complete(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        result = assess_completeness(latest)
        self.assertEqual(result["status"], COMPLETENESS_COMPLETE)
        self.assertEqual(result["absent_types"], ())
        self.assertAlmostEqual(result["coverage_share"], 1.0, places=9)

    def test_a_missing_required_type_is_a_hole(self):
        latest = latest_issues(normalize_documents(_drop("SD-050")))
        result = assess_completeness(latest)
        self.assertEqual(result["status"], COMPLETENESS_INCOMPLETE)
        self.assertEqual(result["absent_types"], ("die-summary-design-sheet",))

    def test_coverage_share_is_counted_over_the_required_types(self):
        latest = latest_issues(normalize_documents(_drop("SD-050")))
        result = assess_completeness(latest)
        expected = float(len(REQUIRED_DOCUMENT_TYPES) - 1) / float(
            len(REQUIRED_DOCUMENT_TYPES)
        )
        self.assertAlmostEqual(result["coverage_share"], expected, places=9)

    def test_an_empty_required_set_rejected(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        with self.assertRaises(ValueError):
            assess_completeness(latest, [])

    def test_non_mapping_latest_rejected(self):
        with self.assertRaises(ValueError):
            assess_completeness(["DS-001"])


class CurrencyTests(unittest.TestCase):
    def test_a_released_and_recent_record_is_current(self):
        documents = normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS))
        result = assess_currency(documents, latest_issues(documents), 100.0)
        self.assertEqual(result["status"], CURRENCY_CURRENT)
        self.assertEqual(result["findings"], [])

    def test_a_draft_controlling_issue_leaves_the_record_unreleased(self):
        documents = normalize_documents(_edit("LD-010", 1, status="document-draft"))
        result = assess_currency(documents, latest_issues(documents), 100.0)
        self.assertEqual(result["status"], CURRENCY_NOT_RELEASED)
        self.assertEqual(result["not_released"], ("LD-010",))

    def test_a_withdrawn_controlling_issue_leaves_the_record_unreleased(self):
        documents = normalize_documents(_edit("QR-040", 1, status="document-withdrawn"))
        result = assess_currency(documents, latest_issues(documents), 100.0)
        self.assertEqual(result["status"], CURRENCY_NOT_RELEASED)

    def test_an_issue_predating_the_baseline_is_stale(self):
        documents = normalize_documents(_edit("PI-020", 1, issued_day=90.0))
        result = assess_currency(documents, latest_issues(documents), 100.0)
        self.assertEqual(result["status"], CURRENCY_STALE)
        self.assertEqual(result["stale"], ("PI-020",))

    def test_an_issue_exactly_on_the_freeze_day_is_not_stale(self):
        documents = normalize_documents(_edit("PI-020", 1, issued_day=100.0))
        result = assess_currency(documents, latest_issues(documents), 100.0)
        self.assertEqual(result["status"], CURRENCY_CURRENT)

    def test_a_freeze_day_that_is_inexact_does_not_make_a_record_stale(self):
        # 0.1 + 0.2 lands just above 0.3, so a strict comparison would call a
        # document issued on the freeze day stale on one platform and current
        # on another.
        documents = normalize_documents(
            [
                {
                    "document_id": "DS-001",
                    "document_type": "die-detail-specification",
                    "issue": 1,
                    "issued_day": 0.3,
                    "status": "document-released",
                    "parent_id": None,
                }
            ],
            ["die-detail-specification"],
        )
        result = assess_currency(documents, latest_issues(documents), 0.1 + 0.2)
        self.assertEqual(result["status"], CURRENCY_CURRENT)
        self.assertEqual(result["stale"], ())

    def test_an_earlier_issue_still_marked_released_is_reported(self):
        documents = normalize_documents(_edit("TP-030", 2, status="document-released"))
        result = assess_currency(documents, latest_issues(documents), 100.0)
        self.assertEqual(result["status"], CURRENCY_STALE)
        self.assertEqual(result["lingering_released_issues"], (("TP-030", 2),))

    def test_a_superseded_earlier_issue_is_not_a_finding(self):
        documents = normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS))
        result = assess_currency(documents, latest_issues(documents), 100.0)
        self.assertEqual(result["lingering_released_issues"], ())

    def test_negative_freeze_day_rejected(self):
        documents = normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS))
        with self.assertRaises(ValueError):
            assess_currency(documents, latest_issues(documents), -1.0)


class TraceabilityTests(unittest.TestCase):
    def test_a_chain_walks_up_to_the_root(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        result = trace_chain(latest, "QR-040")
        self.assertEqual(result["resolution"], "root")
        self.assertEqual(result["chain"], ("QR-040", "TP-030", "DS-001"))

    def test_a_chain_is_found_through_a_loose_spelling(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        self.assertEqual(
            trace_chain(latest, " qr-040 ")["chain"],
            trace_chain(latest, "QR-040")["chain"],
        )

    def test_a_document_outside_the_record_has_no_chain(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        with self.assertRaises(ValueError):
            trace_chain(latest, "XX-999")

    def test_a_full_record_resolves_every_trace(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        result = assess_traceability(latest)
        self.assertEqual(result["status"], TRACE_RESOLVED)
        self.assertEqual(result["findings"], [])

    def test_a_reference_to_a_document_not_in_the_record_breaks_the_trace(self):
        latest = latest_issues(normalize_documents(_edit("QR-040", 1, parent_id="TP-999")))
        result = assess_traceability(latest)
        self.assertEqual(result["status"], TRACE_BROKEN)
        self.assertEqual(result["dangling"], (("QR-040", "TP-999"),))

    def test_a_chain_that_returns_to_its_start_breaks_the_trace(self):
        rows = _edit("DS-001", 2, parent_id="LD-010")
        latest = latest_issues(normalize_documents(rows))
        result = assess_traceability(latest)
        self.assertEqual(result["status"], TRACE_BROKEN)
        self.assertIn("DS-001", result["cyclic"])

    def test_a_document_with_no_parent_that_is_not_the_root_is_an_orphan(self):
        latest = latest_issues(normalize_documents(_edit("LD-010", 1, parent_id=None)))
        result = assess_traceability(latest)
        self.assertEqual(result["status"], TRACE_ORPHAN)
        self.assertEqual(result["orphans"], ("LD-010",))

    def test_the_root_document_is_not_an_orphan(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        result = assess_traceability(latest)
        self.assertEqual(result["orphans"], ())

    def test_chain_depth_is_reported_per_document(self):
        latest = latest_issues(normalize_documents(copy.deepcopy(REFERENCE_DOCUMENTS)))
        result = assess_traceability(latest)
        self.assertEqual(result["depths"]["DS-001"], 1)
        self.assertEqual(result["depths"]["QR-040"], 3)

    def test_non_mapping_latest_rejected_by_traceability(self):
        with self.assertRaises(ValueError):
            assess_traceability(["DS-001"])


class ReviewItemTests(unittest.TestCase):
    def test_reference_record_closes_the_item(self):
        result = review_design_documentation_item(REFERENCE_CASE)
        self.assertEqual(result["verdict"], VERDICT_CLOSED)
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["findings"], [])

    def test_a_missing_required_document_rejects_the_item(self):
        result = review_design_documentation_item(_case(documents=_drop("SD-050")))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["completeness"]["status"], COMPLETENESS_INCOMPLETE)

    def test_a_draft_controlling_issue_rejects_the_item(self):
        result = review_design_documentation_item(
            _case(documents=_edit("LD-010", 1, status="document-draft"))
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["currency"]["status"], CURRENCY_NOT_RELEASED)

    def test_a_stale_issue_leaves_an_action(self):
        result = review_design_documentation_item(
            _case(documents=_edit("PI-020", 1, issued_day=90.0))
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("baseline" in action for action in result["actions"]))

    def test_a_broken_trace_rejects_the_item(self):
        result = review_design_documentation_item(
            _case(documents=_edit("QR-040", 1, parent_id="TP-999"))
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["traceability"]["status"], TRACE_BROKEN)

    def test_an_orphan_document_leaves_an_action(self):
        result = review_design_documentation_item(
            _case(documents=_edit("LD-010", 1, parent_id=None))
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("orphan" in action for action in result["actions"]))

    def test_a_lingering_released_issue_leaves_an_action(self):
        result = review_design_documentation_item(
            _case(documents=_edit("TP-030", 2, status="document-released"))
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)

    def test_several_findings_are_reported_together(self):
        rows = _drop("SD-050")
        for row in rows:
            if row["document_id"] == "QR-040":
                row["parent_id"] = "TP-999"
        result = review_design_documentation_item(_case(documents=rows))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_a_programme_required_set_can_be_narrowed(self):
        result = review_design_documentation_item(
            {
                "documents": [
                    {
                        "document_id": "DS-001",
                        "document_type": "die-detail-specification",
                        "issue": 1,
                        "issued_day": 120.0,
                        "status": "document-released",
                        "parent_id": None,
                    }
                ],
                "baseline_freeze_day": 100.0,
                "required_types": ["die-detail-specification"],
            }
        )
        self.assertEqual(result["verdict"], VERDICT_CLOSED)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            review_design_documentation_item("DS-001")

    def test_missing_baseline_freeze_day_rejected(self):
        case = _case()
        del case["baseline_freeze_day"]
        with self.assertRaises(ValueError):
            review_design_documentation_item(case)

    def test_missing_documents_rejected(self):
        with self.assertRaises(ValueError):
            review_design_documentation_item({"baseline_freeze_day": 100.0})


if __name__ == "__main__":
    unittest.main()
