"""Contract tests for the board-repair record audit logic."""

import unittest
from datetime import date

from q7028_repair_records_logic import (
    APPROVED_METHODS,
    BOARD_SIDES,
    CHECK_GROUPS,
    REQUIRED_HEADER_FIELDS,
    RETENTION_YEARS,
    audit_repair_record,
    chronology_findings,
    location_findings,
    material_findings,
    method_findings,
    missing_header_fields,
    parse_record_date,
    required_verifications,
    retention_findings,
    verification_findings,
)


def base_record(**overrides):
    """A complete jumper-wire repair record on a single board."""
    record = {
        "assembly-part-number": "PCA-4471-02",
        "assembly-serial-number": "SN-0113",
        "repair-authorization": "NCR-2026-0188 disposition repair",
        "operator-identity": "operator-7731",
        "procedure-reference": "RP-JUMPER-004",
        "procedure_revision": "C",
        "repair-date": "2026-04-14",
        "authorization_date": "2026-04-10",
        "verification_date": "2026-04-15",
        "location": {"side": "top", "reference-designator": "U7-3", "grid": ("D", "6")},
        "repair_method": "jumper-wire",
        "materials": [
            {
                "designation": "insulated-jumper-wire-awg30",
                "batch": "LOT-88213",
                "expiry-date": "2027-01-31",
            },
            {
                "designation": "staking-adhesive",
                "batch": "LOT-40021",
                "expiry-date": "2026-11-30",
            },
        ],
        "verifications": ["visual", "electrical-continuity", "ionic-cleanliness"],
        "retention_years": 12,
    }
    record.update(overrides)
    return record


class DateTests(unittest.TestCase):
    def test_an_iso_string_parses(self):
        self.assertEqual(parse_record_date("2026-04-14", "d"), date(2026, 4, 14))

    def test_a_date_object_passes_through(self):
        self.assertEqual(parse_record_date(date(2026, 4, 14), "d"), date(2026, 4, 14))

    def test_a_non_iso_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_record_date("14/04/2026", "d")

    def test_a_number_is_not_a_date(self):
        with self.assertRaises(ValueError):
            parse_record_date(20260414, "d")


class HeaderTests(unittest.TestCase):
    def test_a_complete_header_reports_nothing(self):
        self.assertEqual(missing_header_fields(base_record()), [])

    def test_an_absent_field_is_reported(self):
        record = base_record()
        del record["assembly-serial-number"]
        self.assertIn("assembly-serial-number", missing_header_fields(record))

    def test_a_blank_field_counts_as_missing(self):
        record = base_record(**{"operator-identity": "   "})
        self.assertIn("operator-identity", missing_header_fields(record))

    def test_every_required_field_is_checked(self):
        self.assertEqual(len(missing_header_fields({})), len(REQUIRED_HEADER_FIELDS))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            missing_header_fields("PCA-4471-02")


class LocationTests(unittest.TestCase):
    def test_a_side_and_a_designator_locate_the_work(self):
        self.assertEqual(
            location_findings({"side": "top", "reference-designator": "U7-3"}), []
        )

    def test_a_side_and_a_grid_locate_the_work(self):
        self.assertEqual(location_findings({"side": "bottom", "grid": ("D", "6")}), [])

    def test_prose_alone_does_not_locate_the_work(self):
        findings = location_findings({"side": "top", "description": "near the connector"})
        self.assertTrue(any("neither a reference designator" in f for f in findings))

    def test_a_missing_side_is_reported(self):
        findings = location_findings({"reference-designator": "U7-3"})
        self.assertTrue(any("which side" in f for f in findings))

    def test_an_unknown_side_is_reported(self):
        findings = location_findings({"side": "edge", "reference-designator": "U7-3"})
        self.assertTrue(any("is not one of" in f for f in findings))
        self.assertEqual(len(BOARD_SIDES), 2)

    def test_a_malformed_grid_is_reported(self):
        findings = location_findings({"side": "top", "grid": ("D",)})
        self.assertTrue(any("(column, row)" in f for f in findings))

    def test_no_location_at_all_is_reported(self):
        self.assertEqual(location_findings(None), ["no repair location recorded"])


class MethodTests(unittest.TestCase):
    def test_an_approved_method_with_a_revision_is_clean(self):
        self.assertEqual(method_findings("jumper-wire", "C"), [])

    def test_an_unapproved_method_is_reported(self):
        findings = method_findings("conductive-paint", "A")
        self.assertTrue(any("not in the approved set" in f for f in findings))

    def test_a_missing_revision_is_reported(self):
        findings = method_findings("jumper-wire", None)
        self.assertTrue(any("revision is not recorded" in f for f in findings))

    def test_a_blank_revision_is_reported(self):
        self.assertTrue(method_findings("jumper-wire", "  "))

    def test_required_verifications_differ_by_method(self):
        self.assertNotEqual(
            set(required_verifications("jumper-wire")),
            set(required_verifications("eyelet-insertion")),
        )

    def test_every_approved_method_requires_a_visual_check(self):
        for method in APPROVED_METHODS:
            self.assertIn("visual", required_verifications(method))

    def test_required_verifications_of_an_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            required_verifications("conductive-paint")


class MaterialTests(unittest.TestCase):
    def test_a_complete_material_list_is_clean(self):
        self.assertEqual(material_findings(base_record()["materials"], "2026-04-14"), [])

    def test_an_empty_material_list_is_reported(self):
        self.assertTrue(any("no materials" in f for f in material_findings([], "2026-04-14")))

    def test_a_material_with_no_batch_is_reported(self):
        materials = [{"designation": "flux", "expiry-date": "2027-01-01"}]
        findings = material_findings(materials, "2026-04-14")
        self.assertTrue(any("no batch recorded" in f for f in findings))

    def test_a_material_expired_before_the_repair_is_reported(self):
        materials = [
            {"designation": "adhesive", "batch": "LOT-1", "expiry-date": "2026-01-31"}
        ]
        findings = material_findings(materials, "2026-04-14")
        self.assertTrue(any("expired on" in f for f in findings))

    def test_a_material_expiring_on_the_day_of_use_is_still_in_date(self):
        materials = [
            {"designation": "adhesive", "batch": "LOT-1", "expiry-date": "2026-04-14"}
        ]
        self.assertEqual(material_findings(materials, "2026-04-14"), [])

    def test_a_mapping_of_materials_rejected(self):
        with self.assertRaises(ValueError):
            material_findings({"adhesive": "LOT-1"}, "2026-04-14")


class VerificationTests(unittest.TestCase):
    def test_the_full_required_set_is_clean(self):
        self.assertEqual(
            verification_findings("jumper-wire", list(required_verifications("jumper-wire"))), []
        )

    def test_a_missing_verification_is_reported(self):
        findings = verification_findings("jumper-wire", ["visual", "electrical-continuity"])
        self.assertTrue(any("ionic-cleanliness" in f for f in findings))

    def test_a_verification_from_another_method_is_reported(self):
        findings = verification_findings(
            "jumper-wire", list(required_verifications("jumper-wire")) + ["radiographic"]
        )
        self.assertTrue(any("radiographic" in f for f in findings))

    def test_a_bare_string_is_not_a_verification_list(self):
        with self.assertRaises(ValueError):
            verification_findings("jumper-wire", "visual")


class ChronologyAndRetentionTests(unittest.TestCase):
    def test_dates_in_order_are_clean(self):
        self.assertEqual(
            chronology_findings("2026-04-10", "2026-04-14", "2026-04-15"), []
        )

    def test_same_day_authorization_repair_and_verification_are_clean(self):
        self.assertEqual(
            chronology_findings("2026-04-14", "2026-04-14", "2026-04-14"), []
        )

    def test_a_repair_before_its_authorization_is_reported(self):
        findings = chronology_findings("2026-04-20", "2026-04-14", "2026-04-22")
        self.assertTrue(any("precedes its authorization" in f for f in findings))

    def test_a_verification_before_the_repair_is_reported(self):
        findings = chronology_findings("2026-04-10", "2026-04-14", "2026-04-12")
        self.assertTrue(any("precedes the repair" in f for f in findings))

    def test_retention_at_the_required_period_is_clean(self):
        self.assertEqual(retention_findings(RETENTION_YEARS), [])

    def test_short_retention_is_reported(self):
        self.assertTrue(retention_findings(2))

    def test_negative_retention_rejected(self):
        with self.assertRaises(ValueError):
            retention_findings(-1)


class AuditTests(unittest.TestCase):
    def test_a_complete_record_audits_clean(self):
        result = audit_repair_record(base_record())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_a_clean_record_scores_one(self):
        result = audit_repair_record(base_record())
        self.assertAlmostEqual(result["completeness_score"], 1.0, places=9)
        self.assertEqual(result["clean_groups"], len(CHECK_GROUPS))

    def test_findings_are_grouped_by_the_part_of_the_record(self):
        record = base_record(location={"side": "top"})
        result = audit_repair_record(record)
        self.assertTrue(result["grouped_findings"]["location"])
        self.assertEqual(result["grouped_findings"]["header"], [])

    def test_a_missing_method_blocks_the_verification_group_too(self):
        record = base_record()
        del record["repair_method"]
        result = audit_repair_record(record)
        self.assertTrue(result["grouped_findings"]["method"])
        self.assertTrue(result["grouped_findings"]["verification"])

    def test_an_expired_material_reaches_the_audit(self):
        record = base_record(
            materials=[
                {"designation": "adhesive", "batch": "LOT-1", "expiry-date": "2026-01-01"}
            ]
        )
        result = audit_repair_record(record)
        self.assertFalse(result["complete"])
        self.assertTrue(any("expired on" in f for f in result["findings"]))

    def test_a_short_retention_reaches_the_audit(self):
        result = audit_repair_record(base_record(retention_years=1))
        self.assertTrue(result["grouped_findings"]["retention"])

    def test_the_score_falls_as_groups_fail(self):
        good = audit_repair_record(base_record())["completeness_score"]
        bad = audit_repair_record(base_record(retention_years=1))["completeness_score"]
        self.assertLess(bad, good)

    def test_an_empty_record_fails_every_group(self):
        result = audit_repair_record({})
        self.assertEqual(result["clean_groups"], 0)
        self.assertAlmostEqual(result["completeness_score"], 0.0, places=9)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            audit_repair_record(["PCA-4471-02"])


if __name__ == "__main__":
    unittest.main()
