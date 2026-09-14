#!/usr/bin/env python3
"""Contract test for the cell assembly data documentation package (offline).

Walks the clause workflow step by step: the two-tier family catalogues,
the context-driven resolution of the families a lot owes, the record
validation with its approval-state and approval-date rules, the
highest-revision governing rule with superseded revisions retained, the
qualification tier and the approval it names, the lot-set reconciliation
in both directions, the cross-tier citation and build-date rules, and the
aggregated package verdict. This is the gate 3 review evidence for the
leaf.
"""

import datetime
import unittest

from e2008_sca_data_documentation_package_logic import (
    APPROVAL_STATES,
    LOT_ACCEPTED,
    LOT_FAMILIES,
    LOT_REJECTED,
    PACKAGE_ACCEPTED,
    PACKAGE_REJECTED,
    QUALIFICATION_FAMILIES,
    assess_lot_file,
    conditional_lot_families,
    evaluate_documentation_package,
    governing_records,
    mandatory_lot_families,
    normalize_approval_state,
    normalize_family,
    parse_date,
    reconcile_lot_files,
    required_lot_families,
    resolve_qualification_tier,
    validate_lot_context,
    validate_record,
    validate_records,
)

APPROVAL_DATE = "2026-03-01"
CLEAN_CONTEXT = {"nonconformances_raised": False, "waivers_granted": False}


def _record(family, reference, revision=1, state="approved", date=APPROVAL_DATE):
    entry = {
        "family": family,
        "reference": reference,
        "revision": revision,
        "approval_state": state,
    }
    if state == "approved":
        entry["approval_date"] = date
    return entry


def _qualification_records(**overrides):
    records = []
    for index, family in enumerate(QUALIFICATION_FAMILIES):
        records.append(_record(family, "QR-%03d" % index))
    if overrides:
        by_family = {r["family"]: r for r in records}
        for family, patch in overrides.items():
            by_family[family].update(patch)
    return records


def _lot_records(families=None):
    families = families if families is not None else mandatory_lot_families()
    return [
        _record(family, "LR-%02d" % index) for index, family in enumerate(families)
    ]


def _lot(lot_id="LOT-A", **overrides):
    lot = {
        "lot_id": lot_id,
        "context": dict(CLEAN_CONTEXT),
        "records": _lot_records(),
        "cited_approval_reference": "QR-001",
        "manufacture_completed": "2026-05-10",
    }
    lot.update(overrides)
    return lot


def _tier(**overrides):
    return resolve_qualification_tier(_qualification_records(**overrides))


class CatalogueTests(unittest.TestCase):
    def test_the_two_tiers_share_no_family(self):
        self.assertEqual(
            set(QUALIFICATION_FAMILIES) & set(LOT_FAMILIES), set()
        )

    def test_qualification_approval_statement_is_in_the_tier(self):
        self.assertIn("qualification-approval-statement", QUALIFICATION_FAMILIES)

    def test_lot_families_split_into_mandatory_and_conditional(self):
        self.assertEqual(
            len(mandatory_lot_families()) + len(conditional_lot_families()),
            len(LOT_FAMILIES),
        )
        self.assertTrue(conditional_lot_families())

    def test_only_one_approval_state_is_an_approval(self):
        self.assertIn("approved", APPROVAL_STATES)
        self.assertEqual(normalize_approval_state("  Approved "), "approved")

    def test_unrecognized_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("shipping-label")

    def test_family_outside_the_named_tier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("certificate-of-conformity", QUALIFICATION_FAMILIES)

    def test_unrecognized_approval_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval_state("signed-off-ish")


class ContextTests(unittest.TestCase):
    def test_clean_lot_owes_only_the_mandatory_families(self):
        self.assertEqual(required_lot_families(CLEAN_CONTEXT), mandatory_lot_families())

    def test_raised_nonconformance_adds_its_family(self):
        context = dict(CLEAN_CONTEXT)
        context["nonconformances_raised"] = True
        self.assertIn("nonconformance-records", required_lot_families(context))

    def test_granted_waiver_adds_its_family(self):
        context = dict(CLEAN_CONTEXT)
        context["waivers_granted"] = True
        self.assertIn("waiver-and-deviation-records", required_lot_families(context))

    def test_unstated_flag_is_not_a_false_flag(self):
        with self.assertRaises(ValueError):
            validate_lot_context({"nonconformances_raised": False})

    def test_unrecognized_flag_rejected(self):
        context = dict(CLEAN_CONTEXT)
        context["shipped_in_a_hurry"] = True
        with self.assertRaises(ValueError):
            validate_lot_context(context)

    def test_non_boolean_flag_rejected(self):
        context = dict(CLEAN_CONTEXT)
        context["waivers_granted"] = "yes"
        with self.assertRaises(ValueError):
            validate_lot_context(context)


class RecordTests(unittest.TestCase):
    def test_approved_record_keeps_its_parsed_date(self):
        entry = validate_record(_record("lot-inspection-report", "LR-9"))
        self.assertEqual(entry["approval_date"], datetime.date(2026, 3, 1))

    def test_approved_record_without_a_date_rejected(self):
        record = _record("lot-inspection-report", "LR-9")
        del record["approval_date"]
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_draft_record_carrying_a_date_rejected(self):
        record = _record("lot-inspection-report", "LR-9", state="draft")
        record["approval_date"] = APPROVAL_DATE
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_float_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record("lot-inspection-report", "LR-9", revision=1.0))

    def test_blank_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record("lot-inspection-report", "  "))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("01/03/2026", "approval_date")

    def test_same_revision_submitted_twice_rejected(self):
        record = _record("lot-inspection-report", "LR-9")
        with self.assertRaises(ValueError):
            validate_records([record, dict(record)])

    def test_highest_revision_governs_and_lower_ones_are_superseded(self):
        governing = governing_records(
            [
                _record("lot-inspection-report", "LR-9", revision=1),
                _record("lot-inspection-report", "LR-9", revision=4),
                _record("lot-inspection-report", "LR-9", revision=2),
            ]
        )
        entry = governing["lot-inspection-report"]
        self.assertEqual(entry["revision"], 4)
        self.assertEqual(entry["superseded_revisions"], (1, 2))


class QualificationTierTests(unittest.TestCase):
    def test_complete_approved_tier_is_accepted(self):
        tier = _tier()
        self.assertTrue(tier["accepted"])
        self.assertEqual(tier["findings"], [])
        self.assertEqual(len(tier["families"]), len(QUALIFICATION_FAMILIES))

    def test_tier_names_the_governing_approval(self):
        tier = _tier()
        self.assertEqual(tier["governing_approval_reference"], "QR-001")
        self.assertEqual(
            tier["governing_approval_date"], datetime.date(2026, 3, 1)
        )

    def test_missing_tier_family_is_a_finding(self):
        records = [
            r
            for r in _qualification_records()
            if r["family"] != "process-identification-document"
        ]
        tier = resolve_qualification_tier(records)
        self.assertFalse(tier["accepted"])
        self.assertTrue(
            any("process-identification-document" in f for f in tier["findings"])
        )

    def test_draft_tier_record_is_a_finding(self):
        tier = _tier(
            **{
                "qualification-test-report": {
                    "approval_state": "draft",
                    "approval_date": None,
                }
            }
        )
        self.assertFalse(tier["accepted"])

    def test_unapproved_approval_statement_leaves_no_governing_reference(self):
        tier = _tier(
            **{
                "qualification-approval-statement": {
                    "approval_state": "withdrawn",
                    "approval_date": None,
                }
            }
        )
        self.assertIsNone(tier["governing_approval_reference"])

    def test_a_lot_family_in_the_tier_is_rejected(self):
        records = _qualification_records()
        records.append(_record("certificate-of-conformity", "LR-x"))
        with self.assertRaises(ValueError):
            resolve_qualification_tier(records)


class LotFileTests(unittest.TestCase):
    def test_complete_lot_file_is_accepted(self):
        result = assess_lot_file(_lot(), _tier())
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertTrue(result["citation_matches_governing"])
        self.assertFalse(result["built_before_approval"])

    def test_missing_lot_family_is_named(self):
        records = [
            r
            for r in _lot_records()
            if r["family"] != "certificate-of-conformity"
        ]
        result = assess_lot_file(_lot(records=records), _tier())
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertEqual(result["missing_families"], ("certificate-of-conformity",))

    def test_owed_conditional_family_is_enforced(self):
        context = dict(CLEAN_CONTEXT)
        context["nonconformances_raised"] = True
        result = assess_lot_file(_lot(context=context), _tier())
        self.assertIn("nonconformance-records", result["missing_families"])

    def test_surplus_family_contradicts_the_lot_context(self):
        records = _lot_records() + [_record("waiver-and-deviation-records", "LR-w")]
        result = assess_lot_file(_lot(records=records), _tier())
        self.assertEqual(
            result["unexpected_families"], ("waiver-and-deviation-records",)
        )
        self.assertEqual(result["verdict"], LOT_REJECTED)

    def test_lot_citing_a_superseded_approval_is_rejected(self):
        result = assess_lot_file(
            _lot(cited_approval_reference="QR-OLD"), _tier()
        )
        self.assertFalse(result["citation_matches_governing"])
        self.assertTrue(any("QR-OLD" in f for f in result["findings"]))

    def test_lot_citing_nothing_is_rejected(self):
        result = assess_lot_file(_lot(cited_approval_reference=None), _tier())
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertFalse(result["citation_matches_governing"])

    def test_lot_built_before_the_approval_is_a_finding(self):
        result = assess_lot_file(
            _lot(manufacture_completed="2026-01-15"), _tier()
        )
        self.assertTrue(result["built_before_approval"])
        self.assertEqual(result["verdict"], LOT_REJECTED)

    def test_lot_built_on_the_approval_date_is_not_a_finding(self):
        result = assess_lot_file(
            _lot(manufacture_completed=APPROVAL_DATE), _tier()
        )
        self.assertFalse(result["built_before_approval"])
        self.assertEqual(result["verdict"], LOT_ACCEPTED)

    def test_draft_lot_record_is_a_finding(self):
        records = _lot_records()
        records[0] = _record(records[0]["family"], "LR-00", state="in-review")
        result = assess_lot_file(_lot(records=records), _tier())
        self.assertEqual(result["verdict"], LOT_REJECTED)

    def test_lot_missing_a_required_key_rejected(self):
        lot = _lot()
        del lot["records"]
        with self.assertRaises(ValueError):
            assess_lot_file(lot, _tier())


class ReconciliationTests(unittest.TestCase):
    def test_matching_sets_reconcile_clean(self):
        result = reconcile_lot_files(["A", "B"], ["B", "A"])
        self.assertEqual(result["missing_lots"], ())
        self.assertEqual(result["unexpected_lots"], ())

    def test_declared_lot_with_no_file_is_missing(self):
        result = reconcile_lot_files(["A", "B", "C"], ["A", "B"])
        self.assertEqual(result["missing_lots"], ("C",))

    def test_file_for_an_undeclared_lot_is_unexpected(self):
        result = reconcile_lot_files(["A"], ["A", "Z"])
        self.assertEqual(result["unexpected_lots"], ("Z",))

    def test_lot_declared_twice_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lot_files(["A", "A"], ["A"])

    def test_two_files_for_one_lot_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lot_files(["A"], ["A", "A"])

    def test_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lot_files([], [])


class PackageTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "delivery_id": "DEL-2026-04",
            "declared_lots": ["LOT-A", "LOT-B"],
            "qualification_records": _qualification_records(),
            "lot_files": [_lot("LOT-A"), _lot("LOT-B")],
        }
        spec.update(overrides)
        return spec

    def test_complete_package_is_accepted(self):
        result = evaluate_documentation_package(self._spec())
        self.assertEqual(result["verdict"], PACKAGE_ACCEPTED)
        self.assertEqual(result["accepted_lot_count"], 2)
        self.assertEqual(result["findings"], [])

    def test_an_immaculate_lot_file_does_not_cover_a_missing_lot(self):
        result = evaluate_documentation_package(
            self._spec(lot_files=[_lot("LOT-A")])
        )
        self.assertEqual(result["verdict"], PACKAGE_REJECTED)
        self.assertEqual(result["reconciliation"]["missing_lots"], ("LOT-B",))
        self.assertEqual(result["accepted_lot_count"], 1)

    def test_a_broken_tier_rejects_the_package_even_with_sound_lots(self):
        records = [
            r
            for r in _qualification_records()
            if r["family"] != "qualification-test-report"
        ]
        result = evaluate_documentation_package(
            self._spec(qualification_records=records)
        )
        self.assertEqual(result["verdict"], PACKAGE_REJECTED)
        self.assertFalse(result["qualification_tier"]["accepted"])

    def test_findings_carry_both_tiers(self):
        records = [
            r
            for r in _qualification_records()
            if r["family"] != "qualification-test-report"
        ]
        result = evaluate_documentation_package(
            self._spec(
                qualification_records=records,
                lot_files=[_lot("LOT-A"), _lot("LOT-B", cited_approval_reference="QR-OLD")],
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["declared_lots"]
        with self.assertRaises(ValueError):
            evaluate_documentation_package(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_documentation_package("the paperwork is all there")


if __name__ == "__main__":
    unittest.main()
