#!/usr/bin/env python3
"""Contract test for the bare-cell supplier data package, clause 7.7 (offline)."""

import datetime
import unittest

from e2008_bare_cell_data_documentation_logic import (
    APPROVAL_STATES,
    LOT_DATA_FAMILIES,
    LOT_FILE_ACCEPTED,
    LOT_FILE_REJECTED,
    PACKAGE_RELEASABLE,
    PACKAGE_WITHHELD,
    QUALIFICATION_FAMILIES,
    assess_lot_data_file,
    conditional_lot_families,
    evaluate_data_package,
    governing_records,
    mandatory_lot_families,
    normalize_approval_state,
    normalize_family,
    parse_date,
    reconcile_cell_rows,
    reconcile_lot_files,
    required_lot_families,
    resolve_qualification_tier,
    validate_lot_context,
    validate_record,
    validate_records,
)

APPROVAL_REF = "qa-approval-2026-004"
QUIET_CONTEXT = {"nonconformances_raised": False, "waivers_granted": False}
CELLS_A = ["cell-a-001", "cell-a-002", "cell-a-003", "cell-a-004"]
CELLS_B = ["cell-b-001", "cell-b-002"]


def _record(family, reference=None, issue=1, state="approved", date="2026-05-01"):
    entry = {
        "family": family,
        "reference": reference or ("doc-%s" % family),
        "issue": issue,
        "approval_state": state,
    }
    if state == "approved":
        entry["approval_date"] = date
    return entry


def _qual_records(**overrides):
    records = []
    for family in QUALIFICATION_FAMILIES:
        reference = APPROVAL_REF if family.endswith("approval-statement") else None
        records.append(_record(family, reference=reference, **overrides))
    return records


def _lot(lot_id="lot-a", cells=None, rows=None, context=None, **overrides):
    cells = list(CELLS_A if cells is None else cells)
    lot = {
        "lot_id": lot_id,
        "context": dict(QUIET_CONTEXT if context is None else context),
        "records": [_record(f) for f in mandatory_lot_families()],
        "delivered_cell_ids": cells,
        "measured_data_rows": list(cells if rows is None else rows),
        "cited_approval_reference": APPROVAL_REF,
    }
    lot.update(overrides)
    return lot


def _package(**overrides):
    spec = {
        "delivery_id": "dlv-2026-11",
        "declared_lots": ["lot-a", "lot-b"],
        "qualification_records": _qual_records(),
        "lot_files": [_lot("lot-a"), _lot("lot-b", cells=CELLS_B)],
    }
    spec.update(overrides)
    return spec


class CatalogueTests(unittest.TestCase):
    def test_qualification_tier_names_the_approval_statement(self):
        self.assertIn(
            "bare-cell-qualification-approval-statement", QUALIFICATION_FAMILIES
        )

    def test_measured_data_table_is_owed_by_every_lot(self):
        self.assertIn("bare-cell-measured-electrical-data-table", mandatory_lot_families())

    def test_conditional_families_are_event_driven_only(self):
        self.assertEqual(
            set(conditional_lot_families()),
            {
                "bare-cell-nonconformance-records",
                "bare-cell-waiver-and-deviation-records",
            },
        )

    def test_tiers_do_not_share_a_family(self):
        self.assertFalse(set(QUALIFICATION_FAMILIES) & set(LOT_DATA_FAMILIES))

    def test_only_approved_is_an_approval_state(self):
        self.assertEqual(APPROVAL_STATES[0], "approved")
        self.assertIn("draft", APPROVAL_STATES)


class NormalizationTests(unittest.TestCase):
    def test_family_is_trimmed_and_lowercased(self):
        self.assertEqual(
            normalize_family("  Bare-Cell-Certificate-Of-Conformity "),
            "bare-cell-certificate-of-conformity",
        )

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("bare-cell-holiday-photos")

    def test_family_outside_the_allowed_tier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family(
                "bare-cell-certificate-of-conformity", QUALIFICATION_FAMILIES
            )

    def test_unknown_approval_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval_state("signed-off-verbally")

    def test_iso_date_parsed_and_bad_date_refused(self):
        self.assertEqual(parse_date("2026-05-01"), datetime.date(2026, 5, 1))
        with self.assertRaises(ValueError):
            parse_date("01/05/2026")


class RecordValidationTests(unittest.TestCase):
    def test_approved_record_without_a_date_rejected(self):
        broken = _record("bare-cell-lot-acceptance-test-report")
        del broken["approval_date"]
        with self.assertRaises(ValueError):
            validate_record(broken, tuple(LOT_DATA_FAMILIES))

    def test_draft_record_carrying_an_approval_date_rejected(self):
        broken = _record("bare-cell-certificate-of-conformity", state="draft")
        broken["approval_date"] = "2026-05-01"
        with self.assertRaises(ValueError):
            validate_record(broken, tuple(LOT_DATA_FAMILIES))

    def test_negative_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(
                _record("bare-cell-certificate-of-conformity", issue=-1),
                tuple(LOT_DATA_FAMILIES),
            )

    def test_boolean_issue_rejected(self):
        broken = _record("bare-cell-certificate-of-conformity")
        broken["issue"] = True
        with self.assertRaises(ValueError):
            validate_record(broken, tuple(LOT_DATA_FAMILIES))

    def test_same_issue_submitted_twice_rejected(self):
        duplicate = [
            _record("bare-cell-certificate-of-conformity"),
            _record("bare-cell-certificate-of-conformity"),
        ]
        with self.assertRaises(ValueError):
            validate_records(duplicate, tuple(LOT_DATA_FAMILIES))


class GoverningIssueTests(unittest.TestCase):
    def test_highest_issue_governs_and_lower_ones_are_superseded(self):
        records = [
            _record("bare-cell-certificate-of-conformity", reference="coc-a", issue=1),
            _record("bare-cell-certificate-of-conformity", reference="coc-b", issue=3),
        ]
        governing = governing_records(records, tuple(LOT_DATA_FAMILIES))
        entry = governing["bare-cell-certificate-of-conformity"]
        self.assertEqual(entry["issue"], 3)
        self.assertEqual(entry["superseded_issues"], (1,))

    def test_a_superseding_draft_does_not_inherit_the_approval_below_it(self):
        records = [
            _record("bare-cell-certificate-of-conformity", reference="coc-a", issue=1),
            _record(
                "bare-cell-certificate-of-conformity",
                reference="coc-b",
                issue=2,
                state="draft",
            ),
        ]
        governing = governing_records(records, tuple(LOT_DATA_FAMILIES))
        self.assertEqual(
            governing["bare-cell-certificate-of-conformity"]["approval_state"], "draft"
        )


class LotContextTests(unittest.TestCase):
    def test_unstated_flag_is_not_a_false_flag(self):
        with self.assertRaises(ValueError):
            validate_lot_context({"nonconformances_raised": False})

    def test_unknown_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_context(dict(QUIET_CONTEXT, rain_on_delivery_day=True))

    def test_raised_nonconformance_pulls_in_its_family(self):
        owed = required_lot_families(
            {"nonconformances_raised": True, "waivers_granted": False}
        )
        self.assertIn("bare-cell-nonconformance-records", owed)
        self.assertNotIn("bare-cell-waiver-and-deviation-records", owed)


class CellRowReconciliationTests(unittest.TestCase):
    def test_a_full_table_covers_every_delivered_cell(self):
        result = reconcile_cell_rows(CELLS_A, CELLS_A, "lot-a")
        self.assertTrue(result["fully_covered"])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_a_present_table_can_still_miss_most_of_the_lot(self):
        result = reconcile_cell_rows(CELLS_A, CELLS_A[:1], "lot-a")
        self.assertEqual(len(result["uncovered_cells"]), 3)
        self.assertAlmostEqual(result["coverage_fraction"], 0.25, places=9)
        self.assertFalse(result["fully_covered"])

    def test_a_row_for_a_cell_the_lot_never_held_is_foreign_data(self):
        result = reconcile_cell_rows(CELLS_A, CELLS_A + ["cell-z-999"], "lot-a")
        self.assertEqual(result["foreign_rows"], ("cell-z-999",))
        self.assertFalse(result["fully_covered"])

    def test_duplicate_row_for_one_cell_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_cell_rows(CELLS_A, CELLS_A + [CELLS_A[0]], "lot-a")

    def test_empty_delivered_cell_list_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_cell_rows([], [], "lot-a")


class LotFileReconciliationTests(unittest.TestCase):
    def test_declared_lot_without_a_file_is_missing(self):
        result = reconcile_lot_files(["lot-a", "lot-b"], ["lot-a"])
        self.assertEqual(result["missing_lots"], ("lot-b",))

    def test_file_for_an_undeclared_lot_is_a_contradiction(self):
        result = reconcile_lot_files(["lot-a"], ["lot-a", "lot-c"])
        self.assertEqual(result["undeclared_lots"], ("lot-c",))

    def test_lot_declared_twice_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lot_files(["lot-a", "lot-a"], ["lot-a"])


class QualificationTierTests(unittest.TestCase):
    def test_complete_tier_names_its_governing_approval(self):
        tier = resolve_qualification_tier(_qual_records())
        self.assertTrue(tier["accepted"])
        self.assertEqual(tier["governing_approval_reference"], APPROVAL_REF)
        self.assertEqual(tier["governing_approval_date"], datetime.date(2026, 5, 1))

    def test_missing_family_blocks_the_tier(self):
        tier = resolve_qualification_tier(_qual_records()[:-1])
        self.assertFalse(tier["accepted"])
        self.assertTrue(any("declared-materials" in f for f in tier["findings"]))

    def test_a_draft_approval_statement_names_no_governing_approval(self):
        records = [
            _record(f, reference=APPROVAL_REF if f.endswith("statement") else None,
                    state="draft" if f.endswith("statement") else "approved")
            for f in QUALIFICATION_FAMILIES
        ]
        tier = resolve_qualification_tier(records)
        self.assertIsNone(tier["governing_approval_reference"])
        self.assertFalse(tier["accepted"])


class LotDataFileTests(unittest.TestCase):
    def setUp(self):
        self.tier = resolve_qualification_tier(_qual_records())

    def test_a_complete_lot_file_is_accepted(self):
        result = assess_lot_data_file(_lot(), self.tier)
        self.assertEqual(result["verdict"], LOT_FILE_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_family_complete_lot_with_a_thin_data_table_is_rejected(self):
        result = assess_lot_data_file(_lot(rows=CELLS_A[:2]), self.tier)
        self.assertEqual(result["verdict"], LOT_FILE_REJECTED)
        self.assertAlmostEqual(
            result["cell_coverage"]["coverage_fraction"], 0.5, places=9
        )

    def test_superseded_citation_blocks_the_lot(self):
        result = assess_lot_data_file(
            _lot(cited_approval_reference="qa-approval-2024-001"), self.tier
        )
        self.assertFalse(result["citation_matches_governing"])
        self.assertEqual(result["verdict"], LOT_FILE_REJECTED)

    def test_absent_citation_blocks_the_lot(self):
        lot = _lot()
        lot["cited_approval_reference"] = None
        result = assess_lot_data_file(lot, self.tier)
        self.assertFalse(result["citation_matches_governing"])

    def test_family_not_owed_by_the_context_is_a_finding(self):
        lot = _lot()
        lot["records"] = lot["records"] + [_record("bare-cell-waiver-and-deviation-records")]
        result = assess_lot_data_file(lot, self.tier)
        self.assertEqual(
            result["undeclared_families"], ("bare-cell-waiver-and-deviation-records",)
        )

    def test_lot_missing_a_required_key_rejected(self):
        lot = _lot()
        del lot["measured_data_rows"]
        with self.assertRaises(ValueError):
            assess_lot_data_file(lot, self.tier)

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_data_file(["lot-a"], self.tier)


class PackageTests(unittest.TestCase):
    def test_a_clean_package_is_releasable(self):
        result = evaluate_data_package(_package())
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)
        self.assertEqual(result["accepted_lot_count"], 2)
        self.assertAlmostEqual(result["package_cell_coverage_fraction"], 1.0, places=9)

    def test_one_immaculate_lot_file_does_not_cover_a_two_lot_delivery(self):
        result = evaluate_data_package(_package(lot_files=[_lot("lot-a")]))
        self.assertEqual(result["verdict"], PACKAGE_WITHHELD)
        self.assertIn("lot-b", result["reconciliation"]["missing_lots"])

    def test_undeclared_lot_file_withholds_the_package(self):
        spec = _package()
        spec["lot_files"] = spec["lot_files"] + [_lot("lot-c", cells=["cell-c-001"])]
        result = evaluate_data_package(spec)
        self.assertEqual(result["reconciliation"]["undeclared_lots"], ("lot-c",))
        self.assertEqual(result["verdict"], PACKAGE_WITHHELD)

    def test_package_cell_coverage_aggregates_across_lots(self):
        spec = _package(
            lot_files=[_lot("lot-a", rows=CELLS_A[:2]), _lot("lot-b", cells=CELLS_B)]
        )
        result = evaluate_data_package(spec)
        self.assertEqual(result["delivered_cell_count"], 6)
        self.assertEqual(result["covered_cell_count"], 4)
        self.assertAlmostEqual(
            result["package_cell_coverage_fraction"], 4.0 / 6.0, places=9
        )

    def test_package_carries_every_lot_finding(self):
        spec = _package(
            lot_files=[_lot("lot-a", rows=[]), _lot("lot-b", cells=CELLS_B)]
        )
        result = evaluate_data_package(spec)
        self.assertTrue(any("cell-a-001" in f for f in result["findings"]))

    def test_spec_missing_a_key_rejected(self):
        spec = _package()
        del spec["declared_lots"]
        with self.assertRaises(ValueError):
            evaluate_data_package(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_data_package("release it")


if __name__ == "__main__":
    unittest.main()
