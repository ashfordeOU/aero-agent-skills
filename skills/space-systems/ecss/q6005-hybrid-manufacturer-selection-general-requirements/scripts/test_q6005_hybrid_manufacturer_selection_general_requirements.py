"""Contract tests for the clause 5.1 hybrid manufacturer selection baseline."""

import datetime
import unittest

from q6005_hybrid_manufacturer_selection_general_requirements_logic import (
    ACCEPTABLE_STANDINGS,
    CATEGORIES,
    CATEGORY_APPROVED_LINE,
    CATEGORY_NO_APPROVED_LINE,
    EVIDENCE_KINDS,
    REQUIRED_EVIDENCE,
    ROUTE_APPROVED_LINE,
    ROUTE_FULL_VALIDATION,
    ROUTES,
    assess_manufacturer_selection,
    days_of_cover,
    evidence_by_kind,
    evidence_state,
    missing_evidence,
    normalize_category,
    normalize_evidence_kind,
    normalize_standing,
    parse_date,
    required_evidence,
    route_for_category,
    validate_evidence,
)

TODAY = "2026-09-18"


def evidence(kind, valid_until="2028-01-31", issued="2024-01-31", standing="valid"):
    return {
        "kind": kind,
        "issued": issued,
        "valid_until": valid_until,
        "standing": standing,
        "reference": "doc-%s" % kind[:6],
    }


def full_pack(route):
    return [evidence(kind) for kind in REQUIRED_EVIDENCE[route]]


class CategoryAndRouteTests(unittest.TestCase):
    def test_approved_line_alias_resolves(self):
        self.assertEqual(normalize_category("Category-1"), CATEGORY_APPROVED_LINE)

    def test_non_approved_alias_resolves(self):
        self.assertEqual(normalize_category("non approved line"), CATEGORY_NO_APPROVED_LINE)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("qualified-vendor")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category(2)

    def test_approved_line_category_takes_the_shorter_route(self):
        self.assertEqual(route_for_category(CATEGORY_APPROVED_LINE), ROUTE_APPROVED_LINE)

    def test_non_approved_category_takes_the_full_route(self):
        self.assertEqual(
            route_for_category(CATEGORY_NO_APPROVED_LINE), ROUTE_FULL_VALIDATION
        )

    def test_every_category_maps_to_a_known_route(self):
        for category in CATEGORIES:
            self.assertIn(route_for_category(category), ROUTES)

    def test_full_route_is_a_superset_of_the_shorter_route(self):
        short = set(required_evidence(ROUTE_APPROVED_LINE))
        long = set(required_evidence(ROUTE_FULL_VALIDATION))
        self.assertTrue(short.issubset(long))
        self.assertEqual(len(long) - len(short), 2)

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            required_evidence("fast-track")


class EvidenceNormalisationTests(unittest.TestCase):
    def test_kind_is_canonicalised(self):
        self.assertEqual(
            normalize_evidence_kind("Quality_Management_Certification"),
            "quality-management-certification",
        )

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_evidence_kind("marketing-brochure")

    def test_every_required_kind_is_a_known_kind(self):
        for kinds in REQUIRED_EVIDENCE.values():
            for kind in kinds:
                self.assertIn(kind, EVIDENCE_KINDS)

    def test_only_valid_standing_is_acceptable(self):
        self.assertEqual(ACCEPTABLE_STANDINGS, ("valid",))

    def test_standing_is_canonicalised(self):
        self.assertEqual(normalize_standing(" Suspended "), "suspended")

    def test_unknown_standing_rejected(self):
        with self.assertRaises(ValueError):
            normalize_standing("pending")

    def test_iso_date_is_parsed(self):
        self.assertEqual(parse_date("2026-09-18"), datetime.date(2026, 9, 18))

    def test_date_object_passes_through(self):
        d = datetime.date(2027, 3, 1)
        self.assertEqual(parse_date(d), d)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("18/09/2026")

    def test_impossible_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("2026-02-30")

    def test_record_missing_expiry_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence({"kind": "manufacturer-audit-report", "issued": TODAY})

    def test_expiry_before_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(
                evidence("manufacturer-audit-report", valid_until="2023-01-01")
            )

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(["manufacturer-audit-report"])

    def test_non_string_reference_rejected(self):
        record = evidence("manufacturer-audit-report")
        record["reference"] = 17
        with self.assertRaises(ValueError):
            validate_evidence(record)


class EvidenceStateTests(unittest.TestCase):
    def test_in_date_evidence_is_valid(self):
        self.assertEqual(evidence_state(evidence("process-identification-document"), TODAY), "valid")

    def test_expired_evidence_is_lapsed(self):
        record = evidence("process-identification-document", valid_until="2025-12-31")
        self.assertEqual(evidence_state(record, TODAY), "lapsed")

    def test_evidence_is_still_valid_on_its_expiry_date(self):
        record = evidence("process-identification-document", valid_until=TODAY)
        self.assertEqual(evidence_state(record, TODAY), "valid")

    def test_suspended_evidence_reports_its_standing(self):
        record = evidence("quality-management-certification", standing="suspended")
        self.assertEqual(evidence_state(record, TODAY), "suspended")

    def test_withdrawn_evidence_reports_its_standing(self):
        record = evidence("quality-management-certification", standing="withdrawn")
        self.assertEqual(evidence_state(record, TODAY), "withdrawn")

    def test_suspension_outranks_a_future_expiry(self):
        record = evidence(
            "quality-management-certification", valid_until="2030-01-01", standing="suspended"
        )
        self.assertNotEqual(evidence_state(record, TODAY), "valid")

    def test_assessment_before_issue_rejected(self):
        record = evidence("manufacturer-audit-report", issued="2026-01-01")
        with self.assertRaises(ValueError):
            evidence_state(record, "2025-06-01")

    def test_days_of_cover_is_zero_on_the_expiry_date(self):
        record = evidence("process-identification-document", valid_until=TODAY)
        self.assertEqual(days_of_cover(record, TODAY), 0)

    def test_days_of_cover_counts_whole_days(self):
        record = evidence("process-identification-document", valid_until="2026-09-28")
        self.assertEqual(days_of_cover(record, TODAY), 10)

    def test_days_of_cover_is_negative_once_lapsed(self):
        record = evidence("process-identification-document", valid_until="2026-09-08")
        self.assertEqual(days_of_cover(record, TODAY), -10)


class GroupingTests(unittest.TestCase):
    def test_longest_cover_wins_between_two_valid_copies(self):
        records = [
            evidence("quality-management-certification", valid_until="2027-01-01"),
            evidence("quality-management-certification", valid_until="2029-01-01"),
        ]
        grouped = evidence_by_kind(records, TODAY)
        self.assertEqual(
            grouped["quality-management-certification"]["valid_until"],
            datetime.date(2029, 1, 1),
        )

    def test_a_valid_copy_beats_a_suspended_one_with_longer_cover(self):
        records = [
            evidence("quality-management-certification", valid_until="2032-01-01", standing="suspended"),
            evidence("quality-management-certification", valid_until="2027-01-01"),
        ]
        grouped = evidence_by_kind(records, TODAY)
        self.assertEqual(grouped["quality-management-certification"]["state"], "valid")

    def test_grouping_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            evidence_by_kind({"kind": "manufacturer-audit-report"}, TODAY)

    def test_missing_evidence_lists_every_unmet_kind(self):
        gaps = missing_evidence(ROUTE_FULL_VALIDATION, [], TODAY)
        self.assertEqual(tuple(gaps), REQUIRED_EVIDENCE[ROUTE_FULL_VALIDATION])

    def test_a_complete_pack_leaves_no_gap(self):
        self.assertEqual(
            missing_evidence(ROUTE_APPROVED_LINE, full_pack(ROUTE_APPROVED_LINE), TODAY), []
        )

    def test_a_lapsed_copy_still_counts_as_a_gap(self):
        pack = full_pack(ROUTE_APPROVED_LINE)
        pack[0] = evidence(pack[0]["kind"], valid_until="2025-01-01")
        self.assertEqual(missing_evidence(ROUTE_APPROVED_LINE, pack, TODAY), [pack[0]["kind"]])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "category": CATEGORY_APPROVED_LINE,
            "evidence": full_pack(ROUTE_APPROVED_LINE),
            "assessment_date": TODAY,
        }
        spec.update(overrides)
        return spec

    def test_complete_shorter_route_is_selectable(self):
        result = assess_manufacturer_selection(self._spec())
        self.assertTrue(result["selectable"])
        self.assertEqual(result["findings"], [])

    def test_shorter_pack_does_not_satisfy_the_full_route(self):
        result = assess_manufacturer_selection(
            self._spec(category=CATEGORY_NO_APPROVED_LINE)
        )
        self.assertFalse(result["selectable"])
        self.assertEqual(len(result["missing_evidence"]), 2)

    def test_full_pack_satisfies_the_full_route(self):
        result = assess_manufacturer_selection(
            self._spec(
                category=CATEGORY_NO_APPROVED_LINE,
                evidence=full_pack(ROUTE_FULL_VALIDATION),
            )
        )
        self.assertTrue(result["selectable"])

    def test_lapsed_element_is_reported_separately_from_a_missing_one(self):
        pack = full_pack(ROUTE_APPROVED_LINE)
        pack[1] = evidence(pack[1]["kind"], valid_until="2026-01-01")
        result = assess_manufacturer_selection(self._spec(evidence=pack))
        self.assertEqual(result["lapsed_evidence"], (pack[1]["kind"],))
        self.assertEqual(result["missing_evidence"], ())

    def test_suspended_element_is_unusable(self):
        pack = full_pack(ROUTE_APPROVED_LINE)
        pack[2] = evidence(pack[2]["kind"], standing="suspended")
        result = assess_manufacturer_selection(self._spec(evidence=pack))
        self.assertEqual(result["unusable_evidence"], (pack[2]["kind"],))
        self.assertFalse(result["selectable"])

    def test_cover_shortfall_is_flagged_even_though_the_pack_is_current(self):
        pack = full_pack(ROUTE_APPROVED_LINE)
        pack[0] = evidence(pack[0]["kind"], valid_until="2026-12-31")
        result = assess_manufacturer_selection(
            self._spec(evidence=pack, cover_until="2027-06-30")
        )
        self.assertEqual(result["short_cover_evidence"], (pack[0]["kind"],))
        self.assertFalse(result["selectable"])

    def test_cover_met_exactly_on_the_expiry_date_is_accepted(self):
        result = assess_manufacturer_selection(self._spec(cover_until="2028-01-31"))
        self.assertTrue(result["selectable"])

    def test_cover_until_before_the_assessment_date_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer_selection(self._spec(cover_until="2026-01-01"))

    def test_heritage_claim_does_not_close_an_open_route(self):
        result = assess_manufacturer_selection(
            self._spec(evidence=[], substitute_claims=["flight-heritage"])
        )
        self.assertFalse(result["selectable"])
        self.assertTrue(any("heritage does not" in f for f in result["findings"]))

    def test_heritage_claim_on_a_complete_pack_raises_no_finding(self):
        result = assess_manufacturer_selection(
            self._spec(substitute_claims=["long-standing-supply"])
        )
        self.assertTrue(result["selectable"])

    def test_unknown_substitute_claim_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer_selection(self._spec(substitute_claims=["cheapest-quote"]))

    def test_non_sequence_substitute_claims_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer_selection(self._spec(substitute_claims="flight-heritage"))

    def test_surplus_evidence_is_reported_without_penalty(self):
        pack = full_pack(ROUTE_APPROVED_LINE) + [evidence("manufacturer-audit-report")]
        result = assess_manufacturer_selection(self._spec(evidence=pack))
        self.assertEqual(result["surplus_evidence"], ("manufacturer-audit-report",))
        self.assertTrue(result["selectable"])

    def test_route_is_reported_with_the_category(self):
        result = assess_manufacturer_selection(self._spec())
        self.assertEqual(result["route"], ROUTE_APPROVED_LINE)
        self.assertEqual(result["category"], CATEGORY_APPROVED_LINE)

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["assessment_date"]
        with self.assertRaises(ValueError):
            assess_manufacturer_selection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_manufacturer_selection("approved-line")

    def test_empty_pack_reports_every_required_kind(self):
        result = assess_manufacturer_selection(self._spec(evidence=[]))
        self.assertEqual(result["missing_evidence"], REQUIRED_EVIDENCE[ROUTE_APPROVED_LINE])


if __name__ == "__main__":
    unittest.main()
