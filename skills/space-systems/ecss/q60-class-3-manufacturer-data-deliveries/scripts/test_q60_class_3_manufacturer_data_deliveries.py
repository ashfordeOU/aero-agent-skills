"""Contract tests for the clause 6.3.11 delivered manufacturer data logic."""

import unittest

from q60_class_3_manufacturer_data_deliveries_logic import (
    CORE_DOCUMENT_TYPES,
    DELIVERY_VERDICTS,
    DOCUMENT_TYPES,
    REQUIRED_DOCUMENT_FIELDS,
    REQUIRED_SUBLOT_FIELDS,
    assess_data_delivery,
    conditional_document_types,
    coverage_by_type,
    delivery_verdict,
    document_admissibility,
    parse_iso_date,
    quantity_coverage,
    releasable_sublots,
    required_document_types,
)

RECEIPT = "2026-05-20"
ORDERED_REVISION = "C"


def sublots():
    return [
        {
            "sublot_id": "SL-1",
            "part_number": "rh1020-ccg84b",
            "quantity": 40,
            "manufactured_on": "2026-01-05",
        },
        {
            "sublot_id": "SL-2",
            "part_number": "rh1020-ccg84b",
            "quantity": 10,
            "manufactured_on": "2026-02-09",
        },
    ]


def coc(**overrides):
    record = {
        "doc_type": "certificate-of-conformity",
        "doc_id": "CoC-4410",
        "issue": "1",
        "issue_date": "2026-05-04",
        "covers": ["SL-1", "SL-2"],
        "signed_by": "Quality Manager",
        "spec_revision": "C",
    }
    record.update(overrides)
    return record


def screening(**overrides):
    record = {
        "doc_type": "screening-test-data",
        "doc_id": "SCR-2231",
        "issue": "2",
        "issue_date": "2026-05-06",
        "covers": ["SL-1", "SL-2"],
    }
    record.update(overrides)
    return record


def documents():
    return [coc(), screening()]


class ParseTests(unittest.TestCase):
    def test_an_iso_date_parses(self):
        self.assertEqual(parse_iso_date("2026-05-20").month, 5)

    def test_a_malformed_date_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("20/05/2026")

    def test_a_non_string_date_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date(20260520)


class OwedSetTests(unittest.TestCase):
    def test_a_plain_part_owes_only_the_core_items(self):
        self.assertEqual(required_document_types({}), CORE_DOCUMENT_TYPES)

    def test_a_radiation_sensitive_part_brings_in_its_report(self):
        owed = required_document_types({"radiation_sensitive": True})
        self.assertIn("radiation-test-report", owed)

    def test_a_false_attribute_brings_nothing_in(self):
        self.assertEqual(conditional_document_types({"radiation_sensitive": False}), ())

    def test_several_attributes_stack(self):
        owed = required_document_types(
            {"radiation_sensitive": True, "die_level_traceability": True}
        )
        self.assertEqual(len(owed), 4)

    def test_an_unknown_attribute_is_rejected(self):
        with self.assertRaises(ValueError):
            conditional_document_types({"gold_plated": True})

    def test_a_non_boolean_attribute_is_rejected(self):
        with self.assertRaises(ValueError):
            conditional_document_types({"radiation_sensitive": "yes"})

    def test_every_owed_item_is_a_recognised_document_type(self):
        owed = required_document_types(
            {
                "lot_acceptance_required": True,
                "destructive_analysis_required": True,
                "radiation_sensitive": True,
                "die_level_traceability": True,
            }
        )
        for item in owed:
            self.assertIn(item, DOCUMENT_TYPES)


class AdmissibilityTests(unittest.TestCase):
    def check(self, document):
        return document_admissibility(document, ORDERED_REVISION, RECEIPT, "2026-01-05")

    def test_a_complete_certificate_is_admissible(self):
        self.assertTrue(self.check(coc())["admissible"])

    def test_a_certificate_on_the_wrong_revision_is_not(self):
        verdict = self.check(coc(spec_revision="B"))
        self.assertFalse(verdict["admissible"])
        self.assertTrue(any("ordered revision" in r for r in verdict["reasons"]))

    def test_an_unsigned_certificate_is_not(self):
        verdict = self.check(coc(signed_by="   "))
        self.assertFalse(verdict["admissible"])
        self.assertTrue(any("signature" in r for r in verdict["reasons"]))

    def test_a_document_issued_after_the_delivery_arrived_is_not(self):
        verdict = self.check(coc(issue_date="2026-06-01"))
        self.assertFalse(verdict["admissible"])

    def test_a_document_predating_the_parts_it_certifies_is_not(self):
        verdict = self.check(coc(issue_date="2025-11-01"))
        self.assertFalse(verdict["admissible"])

    def test_a_certificate_naming_no_revision_is_not(self):
        self.assertFalse(self.check(coc(spec_revision=""))["admissible"])

    def test_screening_data_needs_no_signature(self):
        self.assertTrue(self.check(screening())["admissible"])

    def test_an_unknown_document_type_is_rejected(self):
        with self.assertRaises(ValueError):
            self.check(coc(doc_type="shipping-note"))

    def test_a_document_naming_no_sub_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            self.check(coc(covers=[]))

    def test_every_required_document_field_is_enforced(self):
        for field in REQUIRED_DOCUMENT_FIELDS:
            record = coc()
            record[field] = ""
            with self.assertRaises(ValueError):
                self.check(record)


class CoverageTests(unittest.TestCase):
    def test_covering_every_sub_lot_is_complete_coverage(self):
        entry = quantity_coverage(sublots(), {"SL-1", "SL-2"})
        self.assertTrue(entry["complete"])
        self.assertAlmostEqual(entry["coverage"], 1.0, places=9)

    def test_coverage_is_weighted_by_quantity_not_by_sub_lot_count(self):
        entry = quantity_coverage(sublots(), {"SL-2"})
        self.assertFalse(entry["complete"])
        self.assertEqual(entry["quantity_covered"], 10)
        self.assertAlmostEqual(entry["coverage"], 0.2, places=9)

    def test_covering_nothing_is_zero_coverage(self):
        entry = quantity_coverage(sublots(), set())
        self.assertAlmostEqual(entry["coverage"], 0.0, places=9)

    def test_a_zero_quantity_sub_lot_is_rejected(self):
        records = sublots()
        records[0]["quantity"] = 0
        with self.assertRaises(ValueError):
            quantity_coverage(records, {"SL-1"})

    def test_an_empty_shipment_is_rejected(self):
        with self.assertRaises(ValueError):
            quantity_coverage([], set())

    def test_an_inadmissible_document_contributes_no_coverage(self):
        mapped = coverage_by_type(
            sublots(),
            [coc(spec_revision="B"), screening()],
            CORE_DOCUMENT_TYPES,
            ORDERED_REVISION,
            RECEIPT,
            "2026-01-05",
        )
        entry = mapped["coverage"]["certificate-of-conformity"]
        self.assertEqual(entry["quantity_covered"], 0)
        self.assertEqual(len(mapped["inadmissible"]), 1)

    def test_a_document_naming_an_unshipped_sub_lot_is_reported(self):
        mapped = coverage_by_type(
            sublots(),
            [coc(covers=["SL-1", "SL-9"]), screening()],
            CORE_DOCUMENT_TYPES,
            ORDERED_REVISION,
            RECEIPT,
            "2026-01-05",
        )
        self.assertEqual(mapped["unknown_references"], (("CoC-4410", "SL-9"),))

    def test_only_sub_lots_every_core_item_reaches_are_releasable(self):
        mapped = coverage_by_type(
            sublots(),
            [coc(covers=["SL-1"]), screening()],
            CORE_DOCUMENT_TYPES,
            ORDERED_REVISION,
            RECEIPT,
            "2026-01-05",
        )
        self.assertEqual(releasable_sublots(sublots(), mapped["coverage"]), ("SL-1",))


class VerdictTests(unittest.TestCase):
    def test_a_whole_package_is_accepted(self):
        self.assertEqual(delivery_verdict(True, True, True, 0), "accept")

    def test_a_conditional_gap_is_accepted_pending_data(self):
        self.assertEqual(delivery_verdict(True, True, False, 0), "accept-pending-data")

    def test_a_partial_core_reach_is_a_partial_acceptance(self):
        self.assertEqual(delivery_verdict(False, True, True, 0), "partial-acceptance")

    def test_a_core_item_reaching_nothing_stays_at_the_dock(self):
        self.assertEqual(delivery_verdict(False, False, True, 2), "reject-at-dock")

    def test_every_verdict_returned_is_a_known_verdict(self):
        for core_complete in (True, False):
            for core_any in (True, False):
                for conditional in (True, False):
                    self.assertIn(
                        delivery_verdict(core_complete, core_any, conditional, 0),
                        DELIVERY_VERDICTS,
                    )

    def test_a_non_boolean_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            delivery_verdict(1, True, True, 0)

    def test_a_negative_inadmissible_count_is_rejected(self):
        with self.assertRaises(ValueError):
            delivery_verdict(True, True, True, -1)


class AssessDeliveryTests(unittest.TestCase):
    def test_a_complete_delivery_is_accepted_whole(self):
        result = assess_data_delivery(sublots(), documents(), ORDERED_REVISION, RECEIPT)
        self.assertEqual(result["verdict"], "accept")
        self.assertTrue(result["package_complete"])
        self.assertEqual(result["quantity_released"], 50)

    def test_the_release_fraction_follows_the_quantity_released(self):
        result = assess_data_delivery(sublots(), documents(), ORDERED_REVISION, RECEIPT)
        self.assertAlmostEqual(result["release_fraction"], 1.0, places=9)

    def test_a_certificate_reaching_one_sub_lot_gives_a_partial_acceptance(self):
        docs = [coc(covers=["SL-1"]), screening()]
        result = assess_data_delivery(sublots(), docs, ORDERED_REVISION, RECEIPT)
        self.assertEqual(result["verdict"], "partial-acceptance")
        self.assertEqual(result["releasable_sublots"], ("SL-1",))
        self.assertAlmostEqual(result["release_fraction"], 0.8, places=9)

    def test_a_wrong_revision_certificate_leaves_the_delivery_at_the_dock(self):
        docs = [coc(spec_revision="B"), screening()]
        result = assess_data_delivery(sublots(), docs, ORDERED_REVISION, RECEIPT)
        self.assertEqual(result["verdict"], "reject-at-dock")
        self.assertEqual(result["quantity_released"], 0)

    def test_a_missing_conditional_report_is_accepted_pending_data(self):
        result = assess_data_delivery(
            sublots(),
            documents(),
            ORDERED_REVISION,
            RECEIPT,
            {"radiation_sensitive": True},
        )
        self.assertEqual(result["verdict"], "accept-pending-data")
        self.assertIn("radiation-test-report", result["owed_document_types"])

    def test_the_conditional_report_when_delivered_completes_the_package(self):
        docs = documents() + [
            {
                "doc_type": "radiation-test-report",
                "doc_id": "RAD-77",
                "issue": "1",
                "issue_date": "2026-05-10",
                "covers": ["SL-1", "SL-2"],
            }
        ]
        result = assess_data_delivery(
            sublots(), docs, ORDERED_REVISION, RECEIPT, {"radiation_sensitive": True}
        )
        self.assertEqual(result["verdict"], "accept")

    def test_an_unshipped_sub_lot_reference_becomes_a_finding(self):
        docs = [coc(covers=["SL-1", "SL-2", "SL-9"]), screening()]
        result = assess_data_delivery(sublots(), docs, ORDERED_REVISION, RECEIPT)
        self.assertTrue(any("was not shipped" in note for note in result["findings"]))

    def test_a_duplicate_sub_lot_is_rejected(self):
        records = sublots()
        records[1]["sublot_id"] = "SL-1"
        with self.assertRaises(ValueError):
            assess_data_delivery(records, documents(), ORDERED_REVISION, RECEIPT)

    def test_an_empty_shipment_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_delivery([], documents(), ORDERED_REVISION, RECEIPT)

    def test_a_blank_ordered_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_delivery(sublots(), documents(), "  ", RECEIPT)

    def test_every_required_sub_lot_field_is_enforced(self):
        for field in REQUIRED_SUBLOT_FIELDS:
            records = sublots()
            records[0][field] = ""
            with self.assertRaises(ValueError):
                assess_data_delivery(records, documents(), ORDERED_REVISION, RECEIPT)

    def test_a_shipment_received_before_it_was_made_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_delivery(sublots(), documents(), ORDERED_REVISION, "2025-06-01")

    def test_a_delivery_with_no_documents_at_all_stays_at_the_dock(self):
        result = assess_data_delivery(sublots(), [], ORDERED_REVISION, RECEIPT)
        self.assertEqual(result["verdict"], "reject-at-dock")
        self.assertEqual(result["releasable_sublots"], ())


if __name__ == "__main__":
    unittest.main()
