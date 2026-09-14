#!/usr/bin/env python3
"""Contract test for the blocking diode data package check, clause 12.8 (offline)."""

import unittest

from e2008_blocking_diode_data_documentation_logic import (
    APPROVAL_STATES,
    BATCH_CONDITIONAL_FAMILIES,
    BATCH_REQUIRED_FAMILIES,
    FAMILY_MISSING,
    FAMILY_NOT_APPROVED,
    FAMILY_PRESENT,
    KNOWN_FAMILIES,
    PACKAGE_HELD,
    PACKAGE_RELEASABLE,
    QUALIFICATION_APPROVAL_FAMILY,
    QUALIFICATION_FAMILIES,
    SCREENING_FAMILY,
    evaluate_batch_file,
    evaluate_data_package,
    evaluate_qualification_tier,
    governing_record,
    grade_family,
    group_records,
    normalize_approval_state,
    normalize_family,
    parse_package_date,
    reconcile_batch_set,
    reconcile_screening_serials,
    resolve_batch_families,
    validate_record,
    verify_date_order,
)

APPROVAL_REF = "qa-2026-0001"


def _rec(family, issue=1, reference=None, state="approved", date="2026-01-10"):
    if state != "approved" and date == "2026-01-10":
        date = None
    return {
        "family": family,
        "reference": reference or ("%s-i%d" % (family, issue)),
        "issue": issue,
        "approval_state": state,
        "approval_date": date,
    }


def _qualification(drop=(), replace=None):
    drop = set(drop)
    replace = replace or {}
    out = []
    for family in QUALIFICATION_FAMILIES:
        if family in drop:
            continue
        if family in replace:
            out.extend(replace[family])
            continue
        reference = APPROVAL_REF if family == QUALIFICATION_APPROVAL_FAMILY else None
        out.append(_rec(family, reference=reference))
    return out


def _context(**flags):
    base = {
        "nonconformance_raised": False,
        "waiver_granted": False,
        "rework_performed": False,
    }
    base.update(flags)
    return base


def _batch(
    batch_id="bat-01",
    serials=None,
    screened=None,
    drop=(),
    extra_records=(),
    context=None,
    cited=APPROVAL_REF,
    manufacture="2026-02-01",
    screening="2026-02-05",
    delivery="2026-02-20",
):
    serials = list(serials) if serials is not None else ["sn-1", "sn-2", "sn-3", "sn-4"]
    screened = list(screened) if screened is not None else list(serials)
    drop = set(drop)
    context = _context() if context is None else context
    records = [
        _rec(family, date="2026-02-05")
        for family in BATCH_REQUIRED_FAMILIES
        if family not in drop
    ]
    for flag, family in sorted(BATCH_CONDITIONAL_FAMILIES.items()):
        if context.get(flag) and family not in drop:
            records.append(_rec(family, date="2026-02-05"))
    records.extend(extra_records)
    return {
        "batch_id": batch_id,
        "context": context,
        "records": records,
        "delivered_serials": serials,
        "screened_serials": screened,
        "cited_approval_reference": cited,
        "manufacture_date": manufacture,
        "screening_date": screening,
        "delivery_date": delivery,
    }


def _spec(**overrides):
    spec = {
        "package_id": "pkg-12-8-0042",
        "qualification_records": _qualification(),
        "declared_batch_ids": ["bat-01"],
        "batch_files": [_batch()],
    }
    spec.update(overrides)
    return spec


class FamilyCatalogueTests(unittest.TestCase):
    def test_approval_statement_sits_in_the_qualification_tier(self):
        self.assertIn(QUALIFICATION_APPROVAL_FAMILY, QUALIFICATION_FAMILIES)

    def test_screening_record_is_a_batch_family(self):
        self.assertIn(SCREENING_FAMILY, BATCH_REQUIRED_FAMILIES)

    def test_the_two_tiers_share_no_family(self):
        self.assertFalse(
            set(QUALIFICATION_FAMILIES) & set(BATCH_REQUIRED_FAMILIES)
        )

    def test_conditional_families_are_not_owed_unconditionally(self):
        for family in BATCH_CONDITIONAL_FAMILIES.values():
            self.assertNotIn(family, BATCH_REQUIRED_FAMILIES)
            self.assertIn(family, KNOWN_FAMILIES)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("batch-vibes-record")

    def test_family_is_trimmed_and_lowercased(self):
        self.assertEqual(
            normalize_family("  BATCH-Identification-Record "),
            "batch-identification-record",
        )


class RecordValidationTests(unittest.TestCase):
    def test_only_approved_counts_as_evidence(self):
        self.assertIn("approved", APPROVAL_STATES)
        record = validate_record(_rec(SCREENING_FAMILY, state="in-review"))
        self.assertFalse(record["approved"])

    def test_unknown_approval_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval_state("probably-fine")

    def test_approved_record_without_a_date_rejected(self):
        bad = _rec(SCREENING_FAMILY)
        bad["approval_date"] = None
        with self.assertRaises(ValueError):
            validate_record(bad)

    def test_draft_record_may_carry_no_date(self):
        record = validate_record(_rec(SCREENING_FAMILY, state="draft"))
        self.assertIsNone(record["approval_date"])

    def test_zero_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_rec(SCREENING_FAMILY, issue=0))

    def test_boolean_issue_rejected(self):
        bad = _rec(SCREENING_FAMILY)
        bad["issue"] = True
        with self.assertRaises(ValueError):
            validate_record(bad)

    def test_record_missing_a_key_rejected(self):
        bad = _rec(SCREENING_FAMILY)
        del bad["reference"]
        with self.assertRaises(ValueError):
            validate_record(bad)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_record("looks fine to me")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_package_date("05/02/2026", "screening_date")

    def test_iso_date_parsed(self):
        self.assertEqual(parse_package_date("2026-02-05", "d").month, 2)


class GoverningIssueTests(unittest.TestCase):
    def test_highest_issue_governs(self):
        grouped = group_records(
            [_rec(SCREENING_FAMILY, issue=1), _rec(SCREENING_FAMILY, issue=3)]
        )
        self.assertEqual(grouped[SCREENING_FAMILY]["governing"]["issue"], 3)

    def test_lower_issues_are_superseded_not_missing(self):
        grouped = group_records(
            [_rec(SCREENING_FAMILY, issue=1), _rec(SCREENING_FAMILY, issue=3)]
        )
        entry = grouped[SCREENING_FAMILY]
        self.assertEqual(entry["issue_count"], 2)
        self.assertEqual(len(entry["superseded"]), 1)
        self.assertEqual(entry["superseded"][0]["issue"], 1)

    def test_governing_record_needs_a_record(self):
        with self.assertRaises(ValueError):
            governing_record([])

    def test_superseding_draft_does_not_inherit_approval(self):
        grouped = group_records(
            [
                _rec(SCREENING_FAMILY, issue=1),
                _rec(SCREENING_FAMILY, issue=2, state="draft"),
            ]
        )
        graded = grade_family(SCREENING_FAMILY, grouped)
        self.assertEqual(graded["status"], FAMILY_NOT_APPROVED)


class FamilyGradingTests(unittest.TestCase):
    def test_absent_family_graded_missing(self):
        graded = grade_family(SCREENING_FAMILY, {})
        self.assertEqual(graded["status"], FAMILY_MISSING)
        self.assertIsNotNone(graded["finding"])

    def test_in_review_family_graded_not_approved(self):
        grouped = group_records([_rec(SCREENING_FAMILY, state="in-review")])
        self.assertEqual(
            grade_family(SCREENING_FAMILY, grouped)["status"], FAMILY_NOT_APPROVED
        )

    def test_approved_family_has_no_finding(self):
        grouped = group_records([_rec(SCREENING_FAMILY)])
        graded = grade_family(SCREENING_FAMILY, grouped)
        self.assertEqual(graded["status"], FAMILY_PRESENT)
        self.assertIsNone(graded["finding"])


class QualificationTierTests(unittest.TestCase):
    def test_complete_tier_names_the_governing_approval(self):
        tier = evaluate_qualification_tier(_qualification())
        self.assertTrue(tier["accepted"])
        self.assertEqual(tier["governing_approval"]["reference"], APPROVAL_REF)

    def test_missing_family_blocks_the_tier(self):
        tier = evaluate_qualification_tier(
            _qualification(drop=("diode-design-and-construction-data",))
        )
        self.assertFalse(tier["accepted"])

    def test_draft_approval_statement_yields_no_governing_approval(self):
        tier = evaluate_qualification_tier(
            _qualification(
                replace={
                    QUALIFICATION_APPROVAL_FAMILY: [
                        _rec(
                            QUALIFICATION_APPROVAL_FAMILY,
                            reference=APPROVAL_REF,
                            state="draft",
                        )
                    ]
                }
            )
        )
        self.assertIsNone(tier["governing_approval"])
        self.assertFalse(tier["accepted"])


class BatchContextTests(unittest.TestCase):
    def test_absent_flag_rejected_rather_than_defaulted(self):
        context = _context()
        del context["waiver_granted"]
        with self.assertRaises(ValueError):
            resolve_batch_families(context)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            resolve_batch_families(_context(rework_performed="a bit"))

    def test_clean_context_owes_only_the_required_families(self):
        self.assertEqual(
            resolve_batch_families(_context()), tuple(BATCH_REQUIRED_FAMILIES)
        )

    def test_raised_nonconformance_adds_a_family(self):
        owed = resolve_batch_families(_context(nonconformance_raised=True))
        self.assertIn(
            BATCH_CONDITIONAL_FAMILIES["nonconformance_raised"], owed
        )


class SerialCoverageTests(unittest.TestCase):
    def test_uncovered_serials_named(self):
        result = reconcile_screening_serials(["a", "b", "c"], ["a"])
        self.assertEqual(result["uncovered_serials"], ("b", "c"))
        self.assertFalse(result["accepted"])

    def test_foreign_screening_rows_named(self):
        result = reconcile_screening_serials(["a", "b"], ["a", "b", "z"])
        self.assertEqual(result["foreign_serials"], ("z",))
        self.assertFalse(result["accepted"])

    def test_full_coverage_is_one(self):
        result = reconcile_screening_serials(["a", "b"], ["b", "a"])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)
        self.assertTrue(result["accepted"])

    def test_partial_coverage_fraction_is_exact(self):
        delivered = ["sn-%03d" % n for n in range(400)]
        result = reconcile_screening_serials(delivered, delivered[:40])
        self.assertAlmostEqual(result["coverage_fraction"], 0.1, places=9)
        self.assertEqual(result["covered_count"], 40)

    def test_repeated_delivered_serial_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_screening_serials(["a", "a"], ["a"])

    def test_empty_delivered_list_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_screening_serials([], [])


class DateOrderTests(unittest.TestCase):
    def test_screening_before_manufacture_is_a_finding(self):
        result = verify_date_order("2026-02-10", "2026-02-01", "2026-02-20")
        self.assertFalse(result["accepted"])

    def test_delivery_before_screening_is_a_finding(self):
        result = verify_date_order("2026-02-01", "2026-02-20", "2026-02-10")
        self.assertFalse(result["accepted"])

    def test_same_day_screening_and_delivery_accepted(self):
        result = verify_date_order("2026-02-01", "2026-02-05", "2026-02-05")
        self.assertTrue(result["accepted"])

    def test_ordered_dates_accepted(self):
        result = verify_date_order("2026-02-01", "2026-02-05", "2026-02-20")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["delivery_date"].day, 20)


class BatchFileTests(unittest.TestCase):
    def test_clean_batch_accepted(self):
        tier = evaluate_qualification_tier(_qualification())
        result = evaluate_batch_file(_batch(), tier["governing_approval"])
        self.assertTrue(result["accepted"])
        self.assertTrue(result["citation_matches_governing"])

    def test_absent_citation_is_a_finding(self):
        tier = evaluate_qualification_tier(_qualification())
        result = evaluate_batch_file(_batch(cited=None), tier["governing_approval"])
        self.assertFalse(result["accepted"])

    def test_citation_of_a_real_but_superseded_approval_is_a_finding(self):
        tier = evaluate_qualification_tier(_qualification())
        result = evaluate_batch_file(
            _batch(cited="qa-2019-0007"), tier["governing_approval"]
        )
        self.assertFalse(result["accepted"])
        self.assertFalse(result["citation_matches_governing"])

    def test_unowed_family_submission_is_a_finding(self):
        tier = evaluate_qualification_tier(_qualification())
        extra = [_rec(BATCH_CONDITIONAL_FAMILIES["waiver_granted"], date="2026-02-05")]
        result = evaluate_batch_file(
            _batch(extra_records=extra), tier["governing_approval"]
        )
        self.assertIn(
            BATCH_CONDITIONAL_FAMILIES["waiver_granted"], result["unowed_families"]
        )
        self.assertFalse(result["accepted"])

    def test_missing_batch_family_blocks_the_batch(self):
        tier = evaluate_qualification_tier(_qualification())
        result = evaluate_batch_file(
            _batch(drop=(SCREENING_FAMILY,)), tier["governing_approval"]
        )
        self.assertFalse(result["accepted"])

    def test_batch_missing_a_key_rejected(self):
        batch = _batch()
        del batch["screened_serials"]
        with self.assertRaises(ValueError):
            evaluate_batch_file(batch, None)


class BatchSetReconciliationTests(unittest.TestCase):
    def test_declared_batch_without_a_file_is_missing(self):
        result = reconcile_batch_set(["bat-01", "bat-02"], ["bat-01"])
        self.assertEqual(result["missing_batch_ids"], ("bat-02",))
        self.assertFalse(result["accepted"])

    def test_undeclared_file_is_a_finding(self):
        result = reconcile_batch_set(["bat-01"], ["bat-01", "bat-09"])
        self.assertEqual(result["undeclared_batch_ids"], ("bat-09",))
        self.assertFalse(result["accepted"])

    def test_matched_sets_accepted(self):
        self.assertTrue(reconcile_batch_set(["bat-01"], ["bat-01"])["accepted"])

    def test_repeated_declared_batch_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_batch_set(["bat-01", "bat-01"], ["bat-01"])

    def test_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_batch_set([], [])


class PackageTests(unittest.TestCase):
    def test_clean_package_releasable(self):
        result = evaluate_data_package(_spec())
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)
        self.assertEqual(result["findings"], [])

    def test_family_sweep_passes_while_three_batches_have_no_file(self):
        spec = _spec(declared_batch_ids=["bat-01", "bat-02", "bat-03", "bat-04"])
        result = evaluate_data_package(spec)
        self.assertEqual(result["verdict"], PACKAGE_HELD)
        self.assertEqual(
            result["batch_reconciliation"]["missing_batch_ids"],
            ("bat-02", "bat-03", "bat-04"),
        )

    def test_one_blocking_batch_is_named(self):
        spec = _spec(
            declared_batch_ids=["bat-01", "bat-02"],
            batch_files=[_batch(), _batch(batch_id="bat-02", cited=None)],
        )
        result = evaluate_data_package(spec)
        self.assertEqual(result["blocking_batch_ids"], ("bat-02",))

    def test_package_coverage_fraction_spans_the_batches(self):
        spec = _spec(
            declared_batch_ids=["bat-01", "bat-02"],
            batch_files=[
                _batch(serials=["a", "b"], screened=["a", "b"]),
                _batch(batch_id="bat-02", serials=["c", "d"], screened=["c"]),
            ],
        )
        result = evaluate_data_package(spec)
        self.assertEqual(result["delivered_serial_total"], 4)
        self.assertAlmostEqual(result["package_coverage_fraction"], 0.75, places=9)

    def test_two_files_for_one_batch_rejected(self):
        spec = _spec(batch_files=[_batch(), _batch()])
        with self.assertRaises(ValueError):
            evaluate_data_package(spec)

    def test_package_with_no_batch_file_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_data_package(_spec(batch_files=[]))

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["declared_batch_ids"]
        with self.assertRaises(ValueError):
            evaluate_data_package(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_data_package("the paperwork is fine")


if __name__ == "__main__":
    unittest.main()
