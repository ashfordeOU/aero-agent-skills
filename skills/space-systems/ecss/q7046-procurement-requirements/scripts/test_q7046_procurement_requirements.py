"""Contract tests for the ECSS-Q-ST-70-46C fastener procurement screen."""

import unittest
from datetime import date

from q7046_procurement_requirements_logic import (
    REQUIRED_CERTIFICATES,
    REQUIRED_PURCHASE_DATA,
    assess_procurement_package,
    certificate_check,
    certificate_set_check,
    disposition_for,
    parse_iso_date,
    purchase_data_completeness,
    qualification_days_remaining,
    source_check,
    validate_order,
)

ORDER = {
    "category": "hex-head-bolt-a286",
    "lot_id": "LOT-4471",
    "quantity": 500,
    "delivery_date": "2026-05-12",
}

SOURCE = {
    "name": "Fastener Works",
    "qualification_status": "qualified",
    "qualified_categories": ["hex-head-bolt-a286", "socket-screw-a286"],
    "qualification_expiry": "2027-01-31",
}


def full_purchase_data():
    return dict((item, "stated") for item in REQUIRED_PURCHASE_DATA)


def full_certificates():
    return [
        {
            "kind": kind,
            "lot_id": "LOT-4471",
            "issue_date": "2026-05-02",
            "signatory": "Quality Manager",
        }
        for kind in REQUIRED_CERTIFICATES
    ]


def package(**overrides):
    base = {
        "order": dict(ORDER),
        "source": dict(SOURCE),
        "purchase_data": full_purchase_data(),
        "certificates": full_certificates(),
    }
    base.update(overrides)
    return base


class DateTests(unittest.TestCase):
    def test_iso_string_parses(self):
        self.assertEqual(parse_iso_date("2026-05-12"), date(2026, 5, 12))

    def test_date_object_passes_through(self):
        self.assertEqual(parse_iso_date(date(2026, 1, 1)), date(2026, 1, 1))

    def test_malformed_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("12/05/2026")

    def test_impossible_calendar_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-02-30")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date(20260512)


class OrderValidationTests(unittest.TestCase):
    def test_valid_order_normalises_fields(self):
        view = validate_order(dict(ORDER, lot_id="  LOT-4471 "))
        self.assertEqual(view["lot_id"], "LOT-4471")
        self.assertEqual(view["delivery_date"], date(2026, 5, 12))

    def test_missing_key_rejected(self):
        bad = dict(ORDER)
        del bad["lot_id"]
        with self.assertRaises(ValueError):
            validate_order(bad)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(dict(ORDER, quantity=0))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(dict(ORDER, quantity=True))

    def test_blank_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(dict(ORDER, category="   "))

    def test_non_mapping_order_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(["hex-head-bolt-a286"])


class PurchaseDataTests(unittest.TestCase):
    def test_full_set_is_complete(self):
        result = purchase_data_completeness(full_purchase_data())
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["completeness_ratio"], 1.0, places=9)
        self.assertEqual(result["missing"], [])

    def test_one_omission_lowers_the_ratio(self):
        data = full_purchase_data()
        del data["property_class"]
        result = purchase_data_completeness(data)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing"], ["property_class"])
        expected = float(len(REQUIRED_PURCHASE_DATA) - 1) / float(len(REQUIRED_PURCHASE_DATA))
        self.assertAlmostEqual(result["completeness_ratio"], expected, places=9)

    def test_blank_value_counts_as_missing(self):
        data = full_purchase_data()
        data["lot_identification"] = "   "
        self.assertIn("lot_identification", purchase_data_completeness(data)["missing"])

    def test_extra_item_is_reported_not_counted(self):
        data = full_purchase_data()
        data["buyer_note"] = "expedite"
        result = purchase_data_completeness(data)
        self.assertEqual(result["unrecognised"], ["buyer_note"])
        self.assertTrue(result["complete"])

    def test_empty_data_gives_zero_ratio(self):
        result = purchase_data_completeness({})
        self.assertAlmostEqual(result["completeness_ratio"], 0.0, places=9)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            purchase_data_completeness(["part_designation"])

    def test_empty_required_list_rejected(self):
        with self.assertRaises(ValueError):
            purchase_data_completeness({}, required=())


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.view = validate_order(ORDER)

    def test_live_qualification_is_acceptable(self):
        result = source_check(SOURCE, self.view)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["reasons"], [])

    def test_days_remaining_is_the_calendar_difference(self):
        days = qualification_days_remaining(SOURCE, "2027-01-01")
        self.assertEqual(days, 30)

    def test_expired_qualification_is_refused(self):
        expired = dict(SOURCE, qualification_expiry="2026-01-01")
        result = source_check(expired, self.view)
        self.assertFalse(result["acceptable"])
        self.assertIn("expired", result["reasons"][0])

    def test_scope_not_covering_the_category_is_refused(self):
        narrow = dict(SOURCE, qualified_categories=["socket-screw-a286"])
        result = source_check(narrow, self.view)
        self.assertFalse(result["covers_category"])
        self.assertFalse(result["acceptable"])

    def test_suspended_source_is_refused(self):
        result = source_check(dict(SOURCE, qualification_status="suspended"), self.view)
        self.assertFalse(result["acceptable"])

    def test_conditional_source_is_flagged_but_acceptable(self):
        result = source_check(dict(SOURCE, qualification_status="conditional"), self.view)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["conditional"])

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            source_check(dict(SOURCE, qualification_status="pending"), self.view)

    def test_missing_source_key_rejected(self):
        bad = dict(SOURCE)
        del bad["qualified_categories"]
        with self.assertRaises(ValueError):
            source_check(bad, self.view)


class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.view = validate_order(ORDER)

    def test_consistent_certificate_is_acceptable(self):
        result = certificate_check(full_certificates()[0], self.view)
        self.assertTrue(result["acceptable"])

    def test_wrong_lot_is_refused(self):
        cert = dict(full_certificates()[0], lot_id="LOT-9999")
        self.assertFalse(certificate_check(cert, self.view)["acceptable"])

    def test_certificate_dated_after_delivery_is_refused(self):
        cert = dict(full_certificates()[0], issue_date="2026-06-01")
        self.assertFalse(certificate_check(cert, self.view)["acceptable"])

    def test_certificate_dated_on_delivery_day_is_accepted(self):
        cert = dict(full_certificates()[0], issue_date="2026-05-12")
        self.assertTrue(certificate_check(cert, self.view)["acceptable"])

    def test_unsigned_certificate_is_refused(self):
        cert = dict(full_certificates()[0], signatory="")
        self.assertFalse(certificate_check(cert, self.view)["acceptable"])

    def test_missing_certificate_kind_is_reported(self):
        certs = full_certificates()[:-1]
        result = certificate_set_check(certs, self.view)
        self.assertEqual(result["missing_kinds"], ["mechanical_test_report"])
        self.assertFalse(result["acceptable"])

    def test_full_pack_is_acceptable(self):
        self.assertTrue(certificate_set_check(full_certificates(), self.view)["acceptable"])

    def test_non_sequence_pack_rejected(self):
        with self.assertRaises(ValueError):
            certificate_set_check({"kind": "material_certificate"}, self.view)

    def test_certificate_missing_key_rejected(self):
        cert = dict(full_certificates()[0])
        del cert["issue_date"]
        with self.assertRaises(ValueError):
            certificate_check(cert, self.view)


class DispositionTests(unittest.TestCase):
    def test_all_clean_releases(self):
        self.assertEqual(
            disposition_for(
                {"acceptable": True, "conditional": False},
                {"complete": True},
                {"acceptable": True},
            ),
            "release",
        )

    def test_bad_source_rejects(self):
        self.assertEqual(
            disposition_for({"acceptable": False}, {"complete": True}, {"acceptable": True}),
            "reject",
        )

    def test_incomplete_data_holds(self):
        self.assertEqual(
            disposition_for(
                {"acceptable": True, "conditional": False},
                {"complete": False},
                {"acceptable": True},
            ),
            "hold",
        )

    def test_conditional_source_holds(self):
        self.assertEqual(
            disposition_for(
                {"acceptable": True, "conditional": True},
                {"complete": True},
                {"acceptable": True},
            ),
            "hold",
        )

    def test_non_mapping_result_rejected(self):
        with self.assertRaises(ValueError):
            disposition_for(None, {"complete": True}, {"acceptable": True})


class AssessmentTests(unittest.TestCase):
    def test_clean_package_releases_with_no_findings(self):
        result = assess_procurement_package(package())
        self.assertEqual(result["disposition"], "release")
        self.assertEqual(result["findings"], [])

    def test_unqualified_source_rejects_the_package(self):
        bad = package(source=dict(SOURCE, qualification_status="none"))
        result = assess_procurement_package(bad)
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(result["findings"])

    def test_missing_purchase_data_item_holds_the_package(self):
        data = full_purchase_data()
        del data["surface_treatment"]
        result = assess_procurement_package(package(purchase_data=data))
        self.assertEqual(result["disposition"], "hold")
        self.assertIn("purchase data omits 'surface_treatment'", result["findings"])

    def test_missing_certificate_holds_the_package(self):
        result = assess_procurement_package(package(certificates=full_certificates()[:1]))
        self.assertEqual(result["disposition"], "hold")

    def test_findings_accumulate_across_all_three_checks(self):
        data = full_purchase_data()
        del data["inspection_level"]
        bad = package(
            source=dict(SOURCE, qualified_categories=["washer-a286"]),
            purchase_data=data,
            certificates=[],
        )
        result = assess_procurement_package(bad)
        self.assertEqual(result["disposition"], "reject")
        self.assertGreaterEqual(len(result["findings"]), 5)

    def test_missing_package_key_rejected(self):
        bad = package()
        del bad["certificates"]
        with self.assertRaises(ValueError):
            assess_procurement_package(bad)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_package("order")


if __name__ == "__main__":
    unittest.main()
