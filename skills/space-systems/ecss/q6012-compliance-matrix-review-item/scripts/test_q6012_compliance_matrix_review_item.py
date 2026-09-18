#!/usr/bin/env python3
"""Contract test for the compliance matrix review item (offline)."""

import copy
import unittest

from q6012_compliance_matrix_review_item_logic import (
    CONFORMANCE_STATUSES,
    VERDICT_ACCEPTED,
    VERDICT_ACTIONED,
    VERDICT_REJECTED,
    build_matrix,
    conformance_counts,
    coverage_report,
    evidence_gaps,
    full_conformance_fraction,
    normalize_requirement_id,
    normalize_status,
    review_compliance_matrix,
    unjustified_exclusions,
    unwaived_departures,
    validate_matrix_row,
)

APPLICABLE = ["MMD-001", "MMD-002", "MMD-003", "MMD-004"]

ROWS = [
    {
        "requirement_id": "MMD-001",
        "status": "compliant",
        "evidence_ref": "S-parameter report SR-11",
    },
    {
        "requirement_id": "MMD-002",
        "status": "compliant",
        "evidence_ref": "load-pull report LP-04",
    },
    {
        "requirement_id": "MMD-003",
        "status": "not-applicable",
        "justification": "the die carries no on-chip bias regulator",
    },
    {
        "requirement_id": "MMD-004",
        "status": "compliant",
        "evidence_ref": "thermal model TM-02",
    },
]


def _rows(*overrides):
    rows = copy.deepcopy(ROWS)
    for requirement_id, changes in overrides:
        for row in rows:
            if row["requirement_id"] == requirement_id:
                row.update(changes)
                for key in [k for k, v in row.items() if v is None]:
                    del row[key]
    return rows


def _case(**overrides):
    case = {
        "applicable_requirement_ids": list(APPLICABLE),
        "rows": copy.deepcopy(ROWS),
    }
    case.update(overrides)
    return case


class NormalizationTests(unittest.TestCase):
    def test_requirement_id_is_upper_cased_and_squeezed(self):
        self.assertEqual(normalize_requirement_id("  mmd-001  "), "MMD-001")

    def test_internal_whitespace_in_an_identifier_is_squeezed(self):
        self.assertEqual(normalize_requirement_id("MMD   001"), "MMD 001")

    def test_blank_requirement_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_requirement_id("   ")

    def test_non_string_requirement_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_requirement_id(1)

    def test_status_accepts_a_loose_spelling(self):
        self.assertEqual(normalize_status("Partially Compliant"), "partially-compliant")

    def test_status_accepts_an_underscored_spelling(self):
        self.assertEqual(normalize_status("NOT_APPLICABLE"), "not-applicable")

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            normalize_status("mostly fine")

    def test_every_declared_status_normalizes_to_itself(self):
        for status in CONFORMANCE_STATUSES:
            self.assertEqual(normalize_status(status), status)


class RowValidationTests(unittest.TestCase):
    def test_a_complete_row_normalizes(self):
        row = validate_matrix_row(ROWS[0])
        self.assertEqual(row["requirement_id"], "MMD-001")
        self.assertEqual(row["status"], "compliant")
        self.assertEqual(row["evidence_ref"], "S-parameter report SR-11")
        self.assertIsNone(row["departure_ref"])

    def test_a_blank_evidence_reference_reads_as_absent(self):
        row = validate_matrix_row(
            {"requirement_id": "MMD-001", "status": "compliant", "evidence_ref": "  "}
        )
        self.assertIsNone(row["evidence_ref"])

    def test_a_row_with_an_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix_row(
                {"requirement_id": "MMD-001", "status": "compliant", "owner": "RF"}
            )

    def test_a_non_mapping_row_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix_row("MMD-001 compliant")

    def test_a_non_string_evidence_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix_row(
                {"requirement_id": "MMD-001", "status": "compliant", "evidence_ref": 11}
            )


class MatrixBuildTests(unittest.TestCase):
    def test_the_reference_matrix_builds(self):
        matrix = build_matrix(ROWS)
        self.assertEqual(len(matrix), 4)
        self.assertIn("MMD-003", matrix)

    def test_a_requirement_stated_twice_rejected(self):
        rows = copy.deepcopy(ROWS)
        rows.append({"requirement_id": "mmd-001", "status": "non-compliant"})
        with self.assertRaises(ValueError):
            build_matrix(rows)

    def test_an_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            build_matrix([])

    def test_a_non_list_of_rows_rejected(self):
        with self.assertRaises(ValueError):
            build_matrix(ROWS[0])


class CoverageTests(unittest.TestCase):
    def test_the_reference_matrix_covers_every_requirement(self):
        report = coverage_report(APPLICABLE, ROWS)
        self.assertEqual(report["uncovered"], [])
        self.assertEqual(report["orphan"], [])
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=9)

    def test_a_requirement_with_no_row_is_uncovered(self):
        report = coverage_report(APPLICABLE + ["MMD-005"], ROWS)
        self.assertEqual(report["uncovered"], ["MMD-005"])
        self.assertAlmostEqual(report["coverage_fraction"], 0.8, places=9)

    def test_a_row_against_no_applicable_requirement_is_an_orphan(self):
        rows = copy.deepcopy(ROWS)
        rows.append(
            {
                "requirement_id": "MMD-099",
                "status": "compliant",
                "evidence_ref": "legacy report LG-01",
            }
        )
        report = coverage_report(APPLICABLE, rows)
        self.assertEqual(report["orphan"], ["MMD-099"])

    def test_coverage_is_counted_on_the_canonical_identifier(self):
        rows = copy.deepcopy(ROWS)
        rows[0]["requirement_id"] = " mmd-001 "
        report = coverage_report(APPLICABLE, rows)
        self.assertEqual(report["uncovered"], [])

    def test_a_requirement_listed_twice_as_applicable_rejected(self):
        with self.assertRaises(ValueError):
            coverage_report(APPLICABLE + ["MMD-002"], ROWS)

    def test_an_empty_applicable_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_report([], ROWS)

    def test_a_non_list_applicable_set_rejected(self):
        with self.assertRaises(ValueError):
            coverage_report("MMD-001", ROWS)


class RowDutyTests(unittest.TestCase):
    def test_the_reference_matrix_has_no_evidence_gap(self):
        self.assertEqual(evidence_gaps(ROWS), [])

    def test_conformance_without_evidence_is_a_gap(self):
        rows = _rows(("MMD-002", {"evidence_ref": None}))
        self.assertEqual(evidence_gaps(rows), ["MMD-002"])

    def test_a_partial_row_without_evidence_is_a_gap(self):
        rows = _rows(
            (
                "MMD-002",
                {
                    "status": "partially-compliant",
                    "evidence_ref": None,
                    "departure_ref": "WVR-07",
                },
            )
        )
        self.assertEqual(evidence_gaps(rows), ["MMD-002"])

    def test_an_excluded_row_owes_no_evidence(self):
        self.assertNotIn("MMD-003", evidence_gaps(ROWS))

    def test_a_non_conformance_without_a_waiver_is_unwaived(self):
        rows = _rows(("MMD-004", {"status": "non-compliant", "evidence_ref": None}))
        self.assertEqual(unwaived_departures(rows), ["MMD-004"])

    def test_a_non_conformance_with_a_waiver_is_not_unwaived(self):
        rows = _rows(
            (
                "MMD-004",
                {
                    "status": "non-compliant",
                    "evidence_ref": None,
                    "departure_ref": "WVR-12",
                },
            )
        )
        self.assertEqual(unwaived_departures(rows), [])

    def test_an_exclusion_without_a_justification_is_reported(self):
        rows = _rows(("MMD-003", {"justification": None}))
        self.assertEqual(unjustified_exclusions(rows), ["MMD-003"])

    def test_the_reference_exclusion_is_justified(self):
        self.assertEqual(unjustified_exclusions(ROWS), [])


class CountingTests(unittest.TestCase):
    def test_counts_cover_every_status(self):
        counts = conformance_counts(ROWS)
        for status in CONFORMANCE_STATUSES:
            self.assertIn(status, counts)

    def test_the_reference_matrix_counts_three_conformant_rows(self):
        self.assertEqual(conformance_counts(ROWS)["compliant"], 3)

    def test_excluded_rows_leave_the_conformance_fraction(self):
        self.assertAlmostEqual(full_conformance_fraction(ROWS), 1.0, places=9)

    def test_a_partial_row_lowers_the_conformance_fraction(self):
        rows = _rows(
            ("MMD-002", {"status": "partially-compliant", "departure_ref": "WVR-07"})
        )
        self.assertAlmostEqual(full_conformance_fraction(rows), 2.0 / 3.0, places=9)

    def test_a_matrix_of_only_exclusions_rejected(self):
        rows = [
            {
                "requirement_id": "MMD-00%d" % n,
                "status": "not-applicable",
                "justification": "out of scope",
            }
            for n in (1, 2)
        ]
        with self.assertRaises(ValueError):
            full_conformance_fraction(rows)


class ReviewTests(unittest.TestCase):
    def test_the_reference_matrix_is_accepted(self):
        result = review_compliance_matrix(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["actions"], [])

    def test_an_uncovered_requirement_rejects_the_matrix(self):
        result = review_compliance_matrix(
            _case(applicable_requirement_ids=APPLICABLE + ["MMD-005"])
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(any("MMD-005" in f for f in result["findings"]))

    def test_an_evidence_gap_rejects_the_matrix(self):
        result = review_compliance_matrix(
            _case(rows=_rows(("MMD-002", {"evidence_ref": None})))
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["evidence_gaps"], ["MMD-002"])

    def test_an_unwaived_departure_rejects_the_matrix(self):
        result = review_compliance_matrix(
            _case(
                rows=_rows(
                    ("MMD-004", {"status": "non-compliant", "evidence_ref": None})
                )
            )
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["unwaived_departures"], ["MMD-004"])

    def test_a_waived_partial_row_leaves_an_action_not_a_rejection(self):
        result = review_compliance_matrix(
            _case(
                rows=_rows(
                    (
                        "MMD-002",
                        {"status": "partially-compliant", "departure_ref": "WVR-07"},
                    )
                )
            )
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("open work list" in a for a in result["actions"]))

    def test_an_orphan_row_leaves_an_action(self):
        rows = copy.deepcopy(ROWS)
        rows.append(
            {
                "requirement_id": "MMD-099",
                "status": "compliant",
                "evidence_ref": "legacy report LG-01",
            }
        )
        result = review_compliance_matrix(_case(rows=rows))
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertTrue(any("MMD-099" in a for a in result["actions"]))

    def test_an_unjustified_exclusion_leaves_an_action(self):
        result = review_compliance_matrix(
            _case(rows=_rows(("MMD-003", {"justification": None})))
        )
        self.assertEqual(result["verdict"], VERDICT_ACTIONED)
        self.assertEqual(result["unjustified_exclusions"], ["MMD-003"])

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            review_compliance_matrix("MMD-001")

    def test_a_case_without_rows_rejected(self):
        case = _case()
        del case["rows"]
        with self.assertRaises(ValueError):
            review_compliance_matrix(case)

    def test_a_duplicated_row_rejects_the_review(self):
        rows = copy.deepcopy(ROWS)
        rows.append({"requirement_id": "MMD-001", "status": "non-compliant"})
        with self.assertRaises(ValueError):
            review_compliance_matrix(_case(rows=rows))


if __name__ == "__main__":
    unittest.main()
