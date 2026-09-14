"""Contract tests for the clause 5.3.5 delivery lot acceptance logic.

The cases follow the workflow one step at a time: date-code parsing, the
validity-window arithmetic a prior acceptance rests on, the issue a
manufacturer data package needs before it is credited, the purchaser test
gate, the subgroup coverage a code has to reach across its evidence sources,
and the per-code verdicts a delivery is released on. Each limit is exercised
on both sides.
"""

import unittest

from q6013_class_2_lot_acceptance_logic import (
    ACCEPTANCE_TOLERANCE,
    CREDIT_SOURCES,
    DEFAULT_VALIDITY_MONTHS,
    MARGINAL_FRACTION,
    REQUIRED_SUBGROUPS,
    assess_delivery_lot_acceptance,
    date_code_verdict,
    manufacturer_data_credit,
    months_between,
    prior_acceptance_credit,
    purchaser_test_verdict,
    validate_date_code,
)


def _tested(name, sample_size=20, failures=0, **extra):
    record = {"name": name, "sample_size": sample_size, "failures": failures}
    record.update(extra)
    return record


def _entry(code="2537", **overrides):
    entry = {
        "date_code": code,
        "subgroups": [
            _tested("electrical-end-points", 20, 0, accept_number=1),
            _tested("environmental-stress", 10, 0, accept_number=1),
            _tested("endurance-life", 5, 0, accept_number=0),
        ],
    }
    entry.update(overrides)
    return entry


def _prior(**overrides):
    record = {
        "accepted_month": "2025-03",
        "manufacturing_site": "site-alpha",
        "assembly_location": "plant-one",
        "lot_manufacturing_site": "site-alpha",
        "lot_assembly_location": "plant-one",
        "covers": ["endurance-life"],
    }
    record.update(overrides)
    return record


def _spec(**overrides):
    spec = {
        "date_codes": [_entry("2537"), _entry("2538")],
        "assessment_month": "2026-03",
        "allowable_percent": 10.0,
    }
    spec.update(overrides)
    return spec


class DateCodeTests(unittest.TestCase):
    def test_parses_year_and_week(self):
        self.assertEqual(validate_date_code("2537"), (25, 37))

    def test_week_fifty_three_admissible(self):
        self.assertEqual(validate_date_code("2453"), (24, 53))

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code("2500")

    def test_non_numeric_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code("25W7")

    def test_non_string_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code(2537)

    def test_required_subgroups_and_sources_are_distinct(self):
        self.assertEqual(len(set(REQUIRED_SUBGROUPS)), len(REQUIRED_SUBGROUPS))
        self.assertEqual(len(set(CREDIT_SOURCES)), len(CREDIT_SOURCES))


class MonthArithmeticTests(unittest.TestCase):
    def test_whole_months_across_a_year_end(self):
        self.assertEqual(months_between("2025-11", "2026-03"), 4)

    def test_same_month_is_zero(self):
        self.assertEqual(months_between("2026-03", "2026-03"), 0)

    def test_backwards_span_is_negative(self):
        self.assertEqual(months_between("2026-05", "2026-03"), -2)

    def test_malformed_month_rejected(self):
        with self.assertRaises(ValueError):
            months_between("2026-3", "2026-05")

    def test_month_thirteen_rejected(self):
        with self.assertRaises(ValueError):
            months_between("2026-13", "2027-01")


class ManufacturerDataTests(unittest.TestCase):
    def test_reference_with_issue_is_credited(self):
        credit = manufacturer_data_credit(
            {"document_reference": "LAT-RPT-88", "issue": "2", "covers": ["environmental-stress"]}
        )
        self.assertEqual(credit["credited"], ["environmental-stress"])
        self.assertEqual(credit["reasons"], [])

    def test_reference_without_issue_is_not_credited(self):
        credit = manufacturer_data_credit(
            {"document_reference": "LAT-RPT-88", "covers": ["environmental-stress"]}
        )
        self.assertEqual(credit["credited"], [])
        self.assertTrue(any("carries no issue" in r for r in credit["reasons"]))

    def test_no_reference_is_not_credited(self):
        credit = manufacturer_data_credit({"issue": "2", "covers": ["environmental-stress"]})
        self.assertEqual(credit["credited"], [])

    def test_credit_covers_only_the_named_subgroups(self):
        credit = manufacturer_data_credit(
            {"document_reference": "LAT-RPT-88", "issue": "2", "covers": ["environmental-stress"]}
        )
        self.assertNotIn("endurance-life", credit["credited"])

    def test_subgroup_outside_the_required_set_rejected(self):
        with self.assertRaises(ValueError):
            manufacturer_data_credit(
                {"document_reference": "LAT-RPT-88", "issue": "2", "covers": ["solderability"]}
            )

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            manufacturer_data_credit("LAT-RPT-88")


class PriorAcceptanceTests(unittest.TestCase):
    def test_recent_same_site_acceptance_is_credited(self):
        credit = prior_acceptance_credit(_prior(), "2026-03")
        self.assertEqual(credit["credited"], ["endurance-life"])
        self.assertTrue(credit["in_window"])

    def test_acceptance_exactly_on_the_window_edge_is_credited(self):
        credit = prior_acceptance_credit(_prior(accepted_month="2024-03"), "2026-03", 24)
        self.assertEqual(credit["age_months"], 24)
        self.assertTrue(credit["in_window"])

    def test_acceptance_one_month_past_the_window_is_not(self):
        credit = prior_acceptance_credit(_prior(accepted_month="2024-02"), "2026-03", 24)
        self.assertFalse(credit["in_window"])
        self.assertEqual(credit["credited"], [])

    def test_different_assembly_location_voids_the_credit(self):
        credit = prior_acceptance_credit(_prior(assembly_location="plant-two"), "2026-03")
        self.assertFalse(credit["same_assembly_location"])
        self.assertEqual(credit["credited"], [])

    def test_different_manufacturing_site_voids_the_credit(self):
        credit = prior_acceptance_credit(_prior(manufacturing_site="site-beta"), "2026-03")
        self.assertEqual(credit["credited"], [])

    def test_acceptance_dated_after_the_assessment_rejected(self):
        with self.assertRaises(ValueError):
            prior_acceptance_credit(_prior(accepted_month="2026-09"), "2026-03")

    def test_missing_site_key_rejected(self):
        record = _prior()
        del record["manufacturing_site"]
        with self.assertRaises(ValueError):
            prior_acceptance_credit(record, "2026-03")

    def test_default_validity_window_is_two_years(self):
        self.assertEqual(DEFAULT_VALIDITY_MONTHS, 24)


class PurchaserTestTests(unittest.TestCase):
    def test_zero_failures_accepts(self):
        record = purchaser_test_verdict(_tested("electrical-end-points", 20, 0, accept_number=1), 10.0)
        self.assertTrue(record["accepted"])
        self.assertFalse(record["marginal"])

    def test_failures_over_accept_number_reject(self):
        record = purchaser_test_verdict(_tested("endurance-life", 20, 2, accept_number=1), 50.0)
        self.assertFalse(record["within_accept_number"])
        self.assertFalse(record["accepted"])

    def test_percent_defective_equal_to_allowance_accepts(self):
        record = purchaser_test_verdict(
            _tested("environmental-stress", 20, 2, accept_number=5), 10.0
        )
        self.assertAlmostEqual(record["percent_defective"], 10.0, places=9)
        self.assertTrue(record["within_allowance"])
        self.assertTrue(record["accepted"])

    def test_percent_defective_over_allowance_rejects(self):
        record = purchaser_test_verdict(
            _tested("environmental-stress", 20, 3, accept_number=5), 10.0
        )
        self.assertFalse(record["within_allowance"])

    def test_marginal_flag_raised_near_the_allowance(self):
        record = purchaser_test_verdict(
            _tested("environmental-stress", 25, 2, accept_number=5), 10.0
        )
        self.assertAlmostEqual(record["percent_defective"], 8.0, places=9)
        self.assertGreaterEqual(record["percent_defective"], MARGINAL_FRACTION * 10.0)
        self.assertTrue(record["marginal"])

    def test_more_failures_than_units_rejected(self):
        with self.assertRaises(ValueError):
            purchaser_test_verdict(_tested("endurance-life", 5, 6), 10.0)

    def test_zero_sample_rejected(self):
        with self.assertRaises(ValueError):
            purchaser_test_verdict(_tested("endurance-life", 0, 0), 10.0)

    def test_allowance_outside_percentage_range_rejected(self):
        with self.assertRaises(ValueError):
            purchaser_test_verdict(_tested("endurance-life", 5, 0), 140.0)


class DateCodeVerdictTests(unittest.TestCase):
    def test_fully_tested_code_released(self):
        record = date_code_verdict(_entry(), "2026-03", 10.0)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["disposition"], "release-date-code")
        self.assertEqual(record["uncovered_subgroups"], [])

    def test_uncovered_subgroup_holds_the_code(self):
        entry = _entry(subgroups=[_tested("electrical-end-points", 20, 0, accept_number=1)])
        record = date_code_verdict(entry, "2026-03", 10.0)
        self.assertFalse(record["accepted"])
        self.assertEqual(
            record["uncovered_subgroups"], ["environmental-stress", "endurance-life"]
        )

    def test_mixed_evidence_sources_can_cover_a_code(self):
        entry = _entry(
            subgroups=[_tested("electrical-end-points", 20, 0, accept_number=1)],
            manufacturer_data={
                "document_reference": "LAT-RPT-88",
                "issue": "2",
                "covers": ["environmental-stress"],
            },
            prior_acceptance=_prior(),
        )
        record = date_code_verdict(entry, "2026-03", 10.0)
        self.assertTrue(record["accepted"])
        self.assertEqual(record["coverage"]["environmental-stress"], "manufacturer-data")
        self.assertEqual(record["coverage"]["endurance-life"], "prior-acceptance")

    def test_stale_prior_acceptance_leaves_its_subgroup_uncovered(self):
        entry = _entry(
            subgroups=[
                _tested("electrical-end-points", 20, 0, accept_number=1),
                _tested("environmental-stress", 10, 0, accept_number=1),
            ],
            prior_acceptance=_prior(accepted_month="2020-01"),
        )
        record = date_code_verdict(entry, "2026-03", 10.0)
        self.assertEqual(record["uncovered_subgroups"], ["endurance-life"])
        self.assertFalse(record["accepted"])

    def test_purchaser_test_outranks_a_data_credit_for_the_same_subgroup(self):
        entry = _entry(
            manufacturer_data={
                "document_reference": "LAT-RPT-88",
                "issue": "2",
                "covers": ["endurance-life"],
            }
        )
        record = date_code_verdict(entry, "2026-03", 10.0)
        self.assertEqual(record["coverage"]["endurance-life"], "purchaser-test")

    def test_repeated_subgroup_in_one_code_rejected(self):
        entry = _entry(
            subgroups=[
                _tested("electrical-end-points", 20, 0),
                _tested("electrical-end-points", 10, 0),
            ]
        )
        with self.assertRaises(ValueError):
            date_code_verdict(entry, "2026-03", 10.0)

    def test_missing_date_code_key_rejected(self):
        with self.assertRaises(ValueError):
            date_code_verdict({"subgroups": []}, "2026-03", 10.0)


class DeliveryTests(unittest.TestCase):
    def test_clean_delivery_released(self):
        result = assess_delivery_lot_acceptance(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "release-delivery")
        self.assertEqual(result["code_count"], 2)
        self.assertEqual(result["findings"], [])

    def test_two_date_codes_take_two_verdicts_not_one(self):
        bad = _entry("2538")
        bad["subgroups"] = [
            _tested("electrical-end-points", 20, 0, accept_number=1),
            _tested("environmental-stress", 10, 0, accept_number=1),
            _tested("endurance-life", 5, 3, accept_number=0),
        ]
        result = assess_delivery_lot_acceptance(_spec(date_codes=[_entry("2537"), bad]))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["held_date_codes"], ["2538"])
        self.assertTrue(result["date_codes"][0]["accepted"])

    def test_a_good_week_does_not_carry_a_bad_one(self):
        bad = _entry("2538", subgroups=[_tested("electrical-end-points", 20, 0, accept_number=1)])
        result = assess_delivery_lot_acceptance(_spec(date_codes=[_entry("2537"), bad]))
        self.assertEqual(result["disposition"], "hold-delivery")

    def test_repeated_date_code_in_a_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_lot_acceptance(_spec(date_codes=[_entry("2537"), _entry("2537")]))

    def test_empty_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_lot_acceptance(_spec(date_codes=[]))

    def test_missing_required_key_rejected(self):
        spec = _spec()
        del spec["allowable_percent"]
        with self.assertRaises(ValueError):
            assess_delivery_lot_acceptance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_lot_acceptance(["not", "a", "mapping"])

    def test_custom_validity_window_applied_to_every_code(self):
        entry = _entry(
            "2537",
            subgroups=[
                _tested("electrical-end-points", 20, 0, accept_number=1),
                _tested("environmental-stress", 10, 0, accept_number=1),
            ],
            prior_acceptance=_prior(accepted_month="2025-03"),
        )
        result = assess_delivery_lot_acceptance(
            _spec(date_codes=[entry], validity_months=6)
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("validity window" in f for f in result["findings"]))

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(ACCEPTANCE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
