"""Contract tests for the clause 8.2.1 passive chip general-provisions logic."""

import unittest

from q6005_passive_chip_general_provisions_logic import (
    AGE_TOLERANCE_MONTHS,
    REQUIRED_DOCUMENTS,
    assess_age,
    assess_documents,
    assess_examination,
    assess_general_provisions,
    assess_packaging,
    assess_source,
    date_code_age_months,
    parse_date_code,
    sample_size,
)


def delivery(**overrides):
    record = {
        "source_kind": "approved-manufacturer",
        "traceability_chain": True,
        "lot_size": 400,
        "examined": 32,
        "date_code": "2401",
        "delivery_code": "2501",
        "age_limit_months": 24.0,
        "carrier": "waffle-pack",
        "static_protected": True,
        "moisture_sensitive": False,
        "dry_packed": False,
        "documents": list(REQUIRED_DOCUMENTS),
    }
    record.update(overrides)
    return record


class DateCodeTests(unittest.TestCase):
    def test_string_code_splits_into_year_and_week(self):
        self.assertEqual(parse_date_code("2412"), (24, 12))

    def test_integer_code_is_zero_padded(self):
        self.assertEqual(parse_date_code(203), (2, 3))

    def test_week_fifty_three_is_allowed(self):
        self.assertEqual(parse_date_code("2453"), (24, 53))

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2400")

    def test_week_fifty_four_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2454")

    def test_short_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("241")

    def test_non_numeric_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("24Q1")

    def test_float_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code(24.12)


class AgeTests(unittest.TestCase):
    def test_one_year_gap_is_twelve_months(self):
        self.assertAlmostEqual(date_code_age_months("2401", "2501"), 12.0, places=9)

    def test_half_year_gap_is_six_months(self):
        self.assertAlmostEqual(date_code_age_months("2401", "2427"), 6.0, places=9)

    def test_same_week_is_zero_months(self):
        self.assertAlmostEqual(date_code_age_months("2412", "2412"), 0.0, places=9)

    def test_century_wrap_is_handled(self):
        self.assertAlmostEqual(date_code_age_months("9801", "0201"), 48.0, places=9)

    def test_delivery_before_manufacture_rejected(self):
        with self.assertRaises(ValueError):
            date_code_age_months("2501", "2401")

    def test_age_on_the_limit_is_within(self):
        result = assess_age("2401", "2501", 12.0)
        self.assertAlmostEqual(result["age_months"], result["limit_months"], places=9)
        self.assertTrue(result["within_limit"])

    def test_age_past_the_limit_is_flagged(self):
        result = assess_age("2201", "2501", 24.0)
        self.assertFalse(result["within_limit"])
        self.assertIn("month limit", result["finding"])

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_age("2401", "2501", 0.0)

    def test_tolerance_stays_far_below_a_week(self):
        self.assertLess(AGE_TOLERANCE_MONTHS, 1e-6)


class SampleSizeTests(unittest.TestCase):
    def test_small_lot_is_examined_completely(self):
        self.assertEqual(sample_size(12), 12)

    def test_band_boundary_uses_the_lower_band(self):
        self.assertEqual(sample_size(15), 15)
        self.assertEqual(sample_size(16), 13)

    def test_mid_band_lot_takes_the_band_sample(self):
        self.assertEqual(sample_size(400), 32)

    def test_largest_band_is_capped(self):
        self.assertEqual(sample_size(50000), 80)

    def test_sample_never_exceeds_the_lot(self):
        for size in (1, 5, 16, 51, 151, 501, 1201):
            self.assertLessEqual(sample_size(size), size)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(0)

    def test_non_integer_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(400.0)


class ExaminationTests(unittest.TestCase):
    def test_plan_met_exactly_is_sufficient(self):
        result = assess_examination(400, 32)
        self.assertTrue(result["sufficient"])
        self.assertIsNone(result["finding"])

    def test_more_than_the_plan_is_sufficient(self):
        self.assertTrue(assess_examination(400, 60)["sufficient"])

    def test_short_sample_is_flagged(self):
        result = assess_examination(400, 20)
        self.assertFalse(result["sufficient"])
        self.assertIn("the plan for a lot of 400 is 32", result["finding"])

    def test_examining_more_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_examination(400, 401)

    def test_negative_examined_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_examination(400, -1)


class SourceTests(unittest.TestCase):
    def test_approved_manufacturer_is_acceptable(self):
        self.assertTrue(assess_source("approved-manufacturer")["acceptable"])

    def test_approved_distributor_with_a_chain_is_acceptable(self):
        self.assertTrue(assess_source("approved-distributor", True)["acceptable"])

    def test_approved_distributor_without_a_chain_is_not(self):
        result = assess_source("approved-distributor", False)
        self.assertFalse(result["acceptable"])
        self.assertIn("traceability chain", result["finding"])

    def test_open_market_supply_is_not_acceptable(self):
        self.assertFalse(assess_source("open-market")["acceptable"])

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            assess_source("a-friend-had-some")

    def test_non_boolean_chain_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_source("approved-distributor", "yes")


class PackagingTests(unittest.TestCase):
    def test_waffle_pack_with_static_protection_conforms(self):
        result = assess_packaging("waffle-pack", True, False, False)
        self.assertTrue(result["conforming"])

    def test_bulk_carriage_is_flagged(self):
        result = assess_packaging("bulk-bag", True, False, False)
        self.assertFalse(result["conforming"])
        self.assertIn("bare chips apart", result["finding"])

    def test_missing_static_protection_is_flagged(self):
        self.assertFalse(assess_packaging("waffle-pack", False, False, False)["conforming"])

    def test_moisture_sensitive_without_dry_pack_is_flagged(self):
        result = assess_packaging("tape-and-reel", True, True, False)
        self.assertIn("dry pack", result["finding"])

    def test_moisture_sensitive_with_dry_pack_conforms(self):
        self.assertTrue(assess_packaging("tape-and-reel", True, True, True)["conforming"])

    def test_two_faults_are_both_reported(self):
        result = assess_packaging("bulk-bag", False, True, False)
        self.assertEqual(len(result["findings"]), 3)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_packaging("waffle-pack", 1, False, False)


class DocumentTests(unittest.TestCase):
    def test_complete_document_set_is_clean(self):
        result = assess_documents(list(REQUIRED_DOCUMENTS))
        self.assertTrue(result["complete"])

    def test_absent_document_is_named(self):
        result = assess_documents(["certificate-of-conformity", "inspection-data"])
        self.assertEqual(result["missing"], ("lot-traceability-record",))

    def test_document_names_are_normalized(self):
        result = assess_documents([name.upper().replace("-", "_") for name in REQUIRED_DOCUMENTS])
        self.assertTrue(result["complete"])

    def test_non_sequence_document_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_documents("certificate-of-conformity")


class GeneralProvisionTests(unittest.TestCase):
    def test_clean_delivery_is_acceptable(self):
        result = assess_general_provisions(delivery())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], ())

    def test_open_market_supply_rejects_the_delivery(self):
        result = assess_general_provisions(delivery(source_kind="open-market"))
        self.assertEqual(result["disposition"], "reject")

    def test_short_examination_is_conditional(self):
        result = assess_general_provisions(delivery(examined=10))
        self.assertEqual(result["disposition"], "conditional")

    def test_aged_lot_is_conditional(self):
        result = assess_general_provisions(delivery(date_code="2001"))
        self.assertEqual(result["disposition"], "conditional")

    def test_packaging_fault_rejects_the_delivery(self):
        result = assess_general_provisions(delivery(carrier="bulk-bag"))
        self.assertEqual(result["disposition"], "reject")

    def test_missing_document_is_conditional(self):
        result = assess_general_provisions(delivery(documents=["inspection-data"]))
        self.assertEqual(result["disposition"], "conditional")
        self.assertIn("certificate-of-conformity", result["governing_finding"])

    def test_source_finding_governs_over_a_later_one(self):
        result = assess_general_provisions(delivery(source_kind="open-market", examined=1))
        self.assertIn("open-market", result["governing_finding"])

    def test_missing_key_rejected(self):
        record = delivery()
        del record["carrier"]
        with self.assertRaises(ValueError):
            assess_general_provisions(record)

    def test_non_mapping_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_general_provisions(["approved-manufacturer"])


if __name__ == "__main__":
    unittest.main()
