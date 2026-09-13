"""Contract tests for the clause 5.7 coupon data-package acceptance logic."""

import datetime
import unittest

from e2008_pva_data_documentation_package_logic import (
    APPROVAL_STATES,
    CONDITIONAL_FAMILIES,
    MANDATORY_FAMILIES,
    RECORD_FAMILIES,
    evaluate_package,
    governing_records,
    normalize_approval_state,
    normalize_family,
    parse_date,
    required_families,
    validate_context,
    validate_record,
)

DELIVERY = "2026-04-20"
APPROVED_ON = "2026-04-10"

CLEAN_CONTEXT = {"nonconformances_raised": False, "waivers_granted": False}


def _record(family="inspection-records", reference=None, revision=2,
            approval_state="approved", approval_date=APPROVED_ON):
    entry = {
        "family": family,
        "reference": reference or ("DOC-" + family[:6].upper()),
        "revision": revision,
        "approval_state": approval_state,
    }
    if approval_state == "approved":
        entry["approval_date"] = approval_date
    return entry


def _clean_records():
    return [_record(family=family) for family in MANDATORY_FAMILIES]


class FamilyCatalogueTests(unittest.TestCase):
    def test_recognized_family_is_returned(self):
        self.assertEqual(
            normalize_family("inspection-records"), "inspection-records"
        )

    def test_case_and_space_are_absorbed(self):
        self.assertEqual(
            normalize_family("  Parts-And-Materials-List "), "parts-and-materials-list"
        )

    def test_unrecognized_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family("some-other-paperwork")

    def test_non_string_family_rejected(self):
        with self.assertRaises(ValueError):
            normalize_family(3)

    def test_mandatory_and_conditional_families_partition_the_catalogue(self):
        self.assertEqual(
            len(MANDATORY_FAMILIES) + len(CONDITIONAL_FAMILIES), len(RECORD_FAMILIES)
        )

    def test_qualification_approval_statement_is_always_owed(self):
        self.assertIn("qualification-approval-statement", MANDATORY_FAMILIES)

    def test_nonconformance_records_are_conditional(self):
        self.assertIn("nonconformance-records", CONDITIONAL_FAMILIES)

    def test_only_one_approval_state_is_an_approval(self):
        self.assertIn("approved", APPROVAL_STATES)
        self.assertNotIn("approved", [s for s in APPROVAL_STATES if s != "approved"])


class ContextTests(unittest.TestCase):
    def test_clean_context_owes_only_the_mandatory_families(self):
        self.assertEqual(required_families(CLEAN_CONTEXT), MANDATORY_FAMILIES)

    def test_a_raised_nonconformance_adds_its_family(self):
        context = dict(CLEAN_CONTEXT, nonconformances_raised=True)
        self.assertIn("nonconformance-records", required_families(context))

    def test_a_granted_waiver_adds_its_family(self):
        context = dict(CLEAN_CONTEXT, waivers_granted=True)
        self.assertIn("waiver-and-deviation-records", required_families(context))

    def test_unstated_flag_rejected_rather_than_read_as_false(self):
        with self.assertRaises(ValueError):
            validate_context({"nonconformances_raised": False})

    def test_unrecognized_context_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_context(dict(CLEAN_CONTEXT, everything_fine=True))

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_context(dict(CLEAN_CONTEXT, waivers_granted="no"))

    def test_non_mapping_context_rejected(self):
        with self.assertRaises(ValueError):
            validate_context(["nonconformances_raised"])


class RecordValidationTests(unittest.TestCase):
    def test_valid_record_keeps_its_revision(self):
        self.assertEqual(validate_record(_record(revision=4))["revision"], 4)

    def test_reference_is_trimmed(self):
        self.assertEqual(
            validate_record(_record(reference="  DOC-9 "))["reference"], "DOC-9"
        )

    def test_approval_date_is_parsed(self):
        entry = validate_record(_record())
        self.assertEqual(entry["approval_date"], datetime.date(2026, 4, 10))

    def test_approved_record_without_a_date_rejected(self):
        record = _record()
        del record["approval_date"]
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_draft_record_carrying_an_approval_date_rejected(self):
        record = _record(approval_state="draft")
        record["approval_date"] = APPROVED_ON
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_missing_key_rejected(self):
        record = _record()
        del record["revision"]
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_float_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(revision=2.5))

    def test_boolean_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(revision=True))

    def test_negative_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(revision=-1))

    def test_unrecognized_approval_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval_state("signed-off-ish")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("20 April 2026", "approval_date")

    def test_date_object_passes_through(self):
        self.assertEqual(parse_date(datetime.date(2026, 1, 2)),
                         datetime.date(2026, 1, 2))


class GoverningRecordTests(unittest.TestCase):
    def test_highest_revision_governs_its_family(self):
        records = [_record(revision=1), _record(revision=3, reference="DOC-B")]
        governing = governing_records(records)["inspection-records"]
        self.assertEqual(governing["revision"], 3)

    def test_lower_revisions_are_kept_as_superseded(self):
        records = [_record(revision=1), _record(revision=3, reference="DOC-B")]
        governing = governing_records(records)["inspection-records"]
        self.assertEqual(governing["superseded_revisions"], (1,))

    def test_one_entry_per_family(self):
        self.assertEqual(
            len(governing_records(_clean_records())), len(MANDATORY_FAMILIES)
        )

    def test_repeated_revision_of_one_reference_rejected(self):
        with self.assertRaises(ValueError):
            governing_records([_record(revision=2), _record(revision=2)])

    def test_non_sequence_record_set_rejected(self):
        with self.assertRaises(ValueError):
            governing_records({"family": "inspection-records"})


class PackageAcceptanceTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "coupon_id": "pv-014",
            "delivery_date": DELIVERY,
            "records": _clean_records(),
            "context": dict(CLEAN_CONTEXT),
        }
        spec.update(overrides)
        return spec

    def test_a_complete_approved_package_is_accepted(self):
        result = evaluate_package(self._spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["accepted_family_count"], len(MANDATORY_FAMILIES))

    def test_a_missing_family_is_a_finding(self):
        records = [r for r in _clean_records()
                   if r["family"] != "manufacturing-process-records"]
        result = evaluate_package(self._spec(records=records))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["missing_families"], ("manufacturing-process-records",))

    def test_a_draft_record_is_a_finding(self):
        records = _clean_records()
        records[0] = _record(family=records[0]["family"], approval_state="draft")
        result = evaluate_package(self._spec(records=records))
        self.assertFalse(result["accepted"])
        self.assertIn("rather than approved", result["findings"][0])

    def test_a_record_still_in_review_is_a_finding(self):
        records = _clean_records()
        records[1] = _record(family=records[1]["family"], approval_state="in-review")
        self.assertFalse(evaluate_package(self._spec(records=records))["accepted"])

    def test_a_revision_below_the_applicable_one_is_a_finding(self):
        result = evaluate_package(self._spec(
            applicable_revisions={"inspection-records": 5}
        ))
        self.assertFalse(result["accepted"])
        self.assertIn("below the revision", result["findings"][0])

    def test_a_revision_exactly_at_the_applicable_one_is_accepted(self):
        result = evaluate_package(self._spec(
            applicable_revisions={"inspection-records": 2}
        ))
        self.assertTrue(result["accepted"])

    def test_an_approval_dated_after_delivery_is_a_finding(self):
        records = _clean_records()
        records[2] = _record(family=records[2]["family"], approval_date="2026-06-01")
        result = evaluate_package(self._spec(records=records))
        self.assertFalse(result["accepted"])
        self.assertIn("after coupon", result["findings"][0])

    def test_an_approval_dated_on_the_delivery_day_is_accepted(self):
        records = _clean_records()
        records[2] = _record(family=records[2]["family"], approval_date=DELIVERY)
        self.assertTrue(evaluate_package(self._spec(records=records))["accepted"])

    def test_a_raised_nonconformance_makes_its_family_owed(self):
        context = dict(CLEAN_CONTEXT, nonconformances_raised=True)
        result = evaluate_package(self._spec(context=context))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["missing_families"], ("nonconformance-records",))

    def test_the_owed_nonconformance_family_can_be_supplied(self):
        context = dict(CLEAN_CONTEXT, nonconformances_raised=True)
        records = _clean_records() + [_record(family="nonconformance-records")]
        self.assertTrue(
            evaluate_package(self._spec(context=context, records=records))["accepted"]
        )

    def test_a_family_the_context_denies_is_a_finding(self):
        records = _clean_records() + [_record(family="waiver-and-deviation-records")]
        result = evaluate_package(self._spec(records=records))
        self.assertFalse(result["accepted"])
        self.assertEqual(
            result["unexpected_families"], ("waiver-and-deviation-records",)
        )

    def test_superseded_revisions_travel_with_the_family_record(self):
        records = _clean_records() + [
            _record(family="inspection-records", reference="DOC-OLD", revision=1)
        ]
        result = evaluate_package(self._spec(records=records))
        entry = [r for r in result["families"]
                 if r["family"] == "inspection-records"][0]
        self.assertEqual(entry["superseded_revisions"], (1,))
        self.assertTrue(result["accepted"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["context"]
        with self.assertRaises(ValueError):
            evaluate_package(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_package(["pv-014"])

    def test_blank_coupon_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_package(self._spec(coupon_id="  "))

    def test_unrecognized_applicable_revision_family_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_package(self._spec(applicable_revisions={"minutes": 1}))

    def test_malformed_delivery_date_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_package(self._spec(delivery_date="last Tuesday"))


if __name__ == "__main__":
    unittest.main()
