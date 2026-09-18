#!/usr/bin/env python3
"""Gate 3 contract test for q6005-material-and-part-lot-requirements.

Offline, stdlib unittest. Exercises the batch validation, shelf-life
arithmetic at receipt and at point of use, the storage-regime comparison, the
single manufacturing lot condition, the category-driven lot documentation
check and the three-way disposition of ECSS-Q-ST-60-05C clause 9.4 as
paraphrased in the logic module. The remaining-life fraction and the storage
window edges land exactly on their bounds in the ordinary case, so those are
asserted with assertAlmostEqual rather than a strict inequality that could
round either way between the build host and the CI runner.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_material_and_part_lot_requirements_logic import (  # noqa: E402
    CONDITIONAL_RELEASE,
    CORE_LOT_DOCUMENTS,
    DEFAULT_RESERVE_FRACTION,
    QUARANTINE,
    RELEASE,
    STORAGE_REGIMES,
    assess_batch,
    assess_goods_in,
    batch_age_days,
    lot_identity_state,
    missing_lot_documents,
    parse_date,
    required_lot_documents,
    shelf_life_state,
    storage_compliance,
    validate_batch,
)

BASE = datetime.date(2026, 1, 1)


def day(offset):
    """An ISO date a whole number of days after the reference day."""
    return (BASE + datetime.timedelta(days=offset)).isoformat()


def batch(category="adhesive", **overrides):
    record = {
        "batch_reference": "GRN-2026-%s-01" % category.upper(),
        "category": category,
        "lot_ids": ["MLOT-7741"],
        "manufacture_date": day(0),
        "receipt_date": day(30),
        "storage_regime": "refrigerated",
        "observed_min_c": 2.0,
        "observed_max_c": 8.0,
        "documents": list(required_lot_documents(category)),
        "shelf_life_days": 365,
        "days_to_use": 60,
    }
    record.update(overrides)
    if record.get("shelf_life_days") is None:
        record.pop("shelf_life_days", None)
        record["shelf_life_days"] = None
    return record


class DateAndAgeTests(unittest.TestCase):
    def test_age_is_the_whole_days_between_manufacture_and_receipt(self):
        self.assertEqual(batch_age_days(day(0), day(91)), 91)

    def test_a_batch_received_on_the_day_it_was_made_has_no_age(self):
        self.assertEqual(batch_age_days(day(10), day(10)), 0)

    def test_receipt_before_manufacture_is_refused(self):
        with self.assertRaises(ValueError):
            batch_age_days(day(30), day(29))

    def test_a_malformed_date_is_refused(self):
        with self.assertRaises(ValueError):
            parse_date("01/01/2026", "manufacture_date")

    def test_a_blank_date_is_refused(self):
        with self.assertRaises(ValueError):
            parse_date("  ", "receipt_date")


class ShelfLifeTests(unittest.TestCase):
    def test_a_fresh_batch_keeps_most_of_its_life(self):
        state = shelf_life_state(day(0), day(100), 400)
        self.assertEqual(state["remaining_days"], 300)
        self.assertAlmostEqual(state["remaining_fraction"], 0.75, places=9)
        self.assertTrue(state["in_date_at_receipt"])

    def test_a_batch_landing_exactly_on_the_reserve_still_holds_it(self):
        state = shelf_life_state(day(0), day(300), 400)
        self.assertAlmostEqual(state["remaining_fraction"], DEFAULT_RESERVE_FRACTION, places=9)

    def test_a_batch_whose_life_runs_out_on_arrival_is_out_of_date(self):
        state = shelf_life_state(day(0), day(400), 400)
        self.assertEqual(state["remaining_days"], 0)
        self.assertFalse(state["in_date_at_receipt"])

    def test_remaining_life_covering_the_planned_use_is_reported(self):
        state = shelf_life_state(day(0), day(100), 400, days_to_use=200)
        self.assertTrue(state["covers_planned_use"])

    def test_remaining_life_short_of_the_planned_use_is_reported(self):
        state = shelf_life_state(day(0), day(300), 400, days_to_use=200)
        self.assertFalse(state["covers_planned_use"])

    def test_life_exactly_reaching_the_planned_use_day_covers_it(self):
        state = shelf_life_state(day(0), day(300), 400, days_to_use=100)
        self.assertTrue(state["covers_planned_use"])

    def test_a_non_positive_shelf_life_is_refused(self):
        with self.assertRaises(ValueError):
            shelf_life_state(day(0), day(10), 0)

    def test_a_negative_time_to_use_is_refused(self):
        with self.assertRaises(ValueError):
            shelf_life_state(day(0), day(10), 400, days_to_use=-1)


class StorageRegimeTests(unittest.TestCase):
    def test_a_batch_held_inside_its_regime_complies(self):
        state = storage_compliance("refrigerated", 2.0, 8.0)
        self.assertTrue(state["within_regime"])
        self.assertEqual(state["findings"], [])

    def test_temperatures_landing_on_the_window_edges_still_comply(self):
        lower, upper = STORAGE_REGIMES["refrigerated"]
        state = storage_compliance("refrigerated", lower, upper)
        self.assertTrue(state["within_regime"])
        self.assertAlmostEqual(state["observed_c"][0], lower, places=9)
        self.assertAlmostEqual(state["observed_c"][1], upper, places=9)

    def test_a_warm_excursion_is_reported_with_the_ceiling_named(self):
        state = storage_compliance("refrigerated", 2.0, 19.0)
        self.assertFalse(state["within_regime"])
        self.assertTrue(any("ceiling" in f for f in state["findings"]))

    def test_a_cold_excursion_is_reported_with_the_floor_named(self):
        state = storage_compliance("ambient-controlled", 4.0, 22.0)
        self.assertTrue(any("floor" in f for f in state["findings"]))

    def test_both_ends_breached_are_both_named(self):
        state = storage_compliance("refrigerated", -20.0, 40.0)
        self.assertEqual(len(state["findings"]), 2)

    def test_an_unrecognised_regime_is_refused_rather_than_passed(self):
        with self.assertRaises(ValueError):
            storage_compliance("cool-ish", 2.0, 8.0)

    def test_an_inverted_observed_window_is_refused(self):
        with self.assertRaises(ValueError):
            storage_compliance("refrigerated", 9.0, 1.0)


class LotIdentityTests(unittest.TestCase):
    def test_one_manufacturing_lot_is_permitted(self):
        state = lot_identity_state(["MLOT-1"])
        self.assertTrue(state["single_lot"])
        self.assertTrue(state["permitted"])

    def test_a_repeated_identity_is_still_one_lot(self):
        state = lot_identity_state(["MLOT-1", "MLOT-1"])
        self.assertEqual(state["lot_count"], 1)

    def test_two_lots_are_not_permitted_by_default(self):
        state = lot_identity_state(["MLOT-1", "MLOT-2"])
        self.assertFalse(state["permitted"])

    def test_two_lots_are_permitted_when_the_order_allowed_them(self):
        state = lot_identity_state(["MLOT-1", "MLOT-2"], multiple_lots_permitted=True)
        self.assertTrue(state["permitted"])
        self.assertFalse(state["single_lot"])

    def test_a_placeholder_identity_is_refused(self):
        with self.assertRaises(ValueError):
            lot_identity_state(["TBD"])

    def test_an_empty_identity_list_is_refused(self):
        with self.assertRaises(ValueError):
            lot_identity_state([])


class LotDocumentationTests(unittest.TestCase):
    def test_every_category_owes_the_core_documents(self):
        for category in ("adhesive", "bonding-wire", "piece-part"):
            for document in CORE_LOT_DOCUMENTS:
                self.assertIn(document, required_lot_documents(category), category)

    def test_a_category_adds_its_own_documents(self):
        self.assertIn("breaking-load-record", required_lot_documents("bonding-wire"))
        self.assertNotIn("breaking-load-record", required_lot_documents("adhesive"))

    def test_a_complete_set_leaves_nothing_missing(self):
        self.assertEqual(
            missing_lot_documents(list(required_lot_documents("adhesive")), "adhesive"), []
        )

    def test_names_are_matched_case_and_separator_insensitively(self):
        provided = [d.replace("-", " ").upper() for d in required_lot_documents("preform")]
        self.assertEqual(missing_lot_documents(provided, "preform"), [])

    def test_an_absent_document_is_reported(self):
        provided = [d for d in required_lot_documents("adhesive") if d != "certificate-of-analysis"]
        self.assertEqual(
            missing_lot_documents(provided, "adhesive"), ["certificate-of-analysis"]
        )

    def test_a_string_is_not_a_document_list(self):
        with self.assertRaises(ValueError):
            missing_lot_documents("certificate-of-conformity", "adhesive")


class BatchValidationTests(unittest.TestCase):
    def test_a_missing_required_key_is_refused(self):
        for key in ("batch_reference", "category", "lot_ids", "manufacture_date",
                    "receipt_date", "storage_regime", "documents"):
            record = batch()
            del record[key]
            with self.assertRaises(ValueError):
                validate_batch(record)

    def test_a_limited_life_batch_without_a_shelf_life_is_refused(self):
        with self.assertRaises(ValueError):
            validate_batch(batch(shelf_life_days=None))

    def test_a_non_limited_life_batch_needs_no_shelf_life(self):
        record = validate_batch(batch("bonding-wire", shelf_life_days=None))
        self.assertFalse(record["limited_life"])
        self.assertIsNone(record["shelf_life_days"])

    def test_an_unrecognised_category_is_refused(self):
        with self.assertRaises(ValueError):
            validate_batch(batch(category="solder-paste"))


class DispositionTests(unittest.TestCase):
    def test_a_clean_batch_is_released(self):
        verdict = assess_batch(batch())
        self.assertEqual(verdict["disposition"], RELEASE)
        self.assertEqual(verdict["quarantine_findings"], [])
        self.assertEqual(verdict["restrictions"], [])
        self.assertTrue(verdict["usable"])

    def test_a_storage_excursion_quarantines_the_batch(self):
        verdict = assess_batch(batch(observed_max_c=24.0))
        self.assertEqual(verdict["disposition"], QUARANTINE)
        self.assertFalse(verdict["usable"])

    def test_a_missing_document_quarantines_the_batch(self):
        documents = [d for d in required_lot_documents("adhesive") if d != "certificate-of-conformity"]
        verdict = assess_batch(batch(documents=documents))
        self.assertEqual(verdict["disposition"], QUARANTINE)
        self.assertEqual(verdict["missing_documents"], ["certificate-of-conformity"])

    def test_an_out_of_date_batch_is_quarantined_with_the_overrun_named(self):
        verdict = assess_batch(batch(receipt_date=day(400), shelf_life_days=365))
        self.assertEqual(verdict["disposition"], QUARANTINE)
        self.assertTrue(any("past its shelf life" in f for f in verdict["quarantine_findings"]))

    def test_a_split_batch_is_quarantined_when_one_lot_was_required(self):
        verdict = assess_batch(batch(lot_ids=["MLOT-1", "MLOT-2"]))
        self.assertEqual(verdict["disposition"], QUARANTINE)

    def test_a_permitted_split_batch_is_released_with_a_segregation_restriction(self):
        verdict = assess_batch(
            batch(lot_ids=["MLOT-1", "MLOT-2"], multiple_lots_permitted=True)
        )
        self.assertEqual(verdict["disposition"], CONDITIONAL_RELEASE)
        self.assertTrue(any("segregated" in r for r in verdict["restrictions"]))

    def test_life_short_of_the_planned_use_restricts_rather_than_quarantines(self):
        verdict = assess_batch(batch(receipt_date=day(330), days_to_use=60))
        self.assertEqual(verdict["disposition"], CONDITIONAL_RELEASE)
        self.assertTrue(verdict["usable"])
        self.assertTrue(any("to planned use" in r for r in verdict["restrictions"]))

    def test_a_batch_on_the_reserve_fraction_is_released_unrestricted(self):
        verdict = assess_batch(batch(manufacture_date=day(0), receipt_date=day(300),
                                     shelf_life_days=400, days_to_use=100))
        self.assertEqual(verdict["disposition"], RELEASE)
        self.assertAlmostEqual(
            verdict["shelf_life"]["remaining_fraction"], DEFAULT_RESERVE_FRACTION, places=9
        )

    def test_a_batch_below_the_reserve_fraction_is_restricted(self):
        verdict = assess_batch(batch(receipt_date=day(310), shelf_life_days=400,
                                     days_to_use=10))
        self.assertEqual(verdict["disposition"], CONDITIONAL_RELEASE)
        self.assertTrue(any("declared shelf life is left" in r for r in verdict["restrictions"]))

    def test_a_project_reserve_can_be_raised(self):
        verdict = assess_batch(batch(receipt_date=day(100), shelf_life_days=400,
                                     days_to_use=10), reserve_fraction=0.9)
        self.assertEqual(verdict["disposition"], CONDITIONAL_RELEASE)

    def test_an_out_of_range_reserve_is_refused(self):
        with self.assertRaises(ValueError):
            assess_batch(batch(), reserve_fraction=1.4)

    def test_several_conditions_failing_are_all_named(self):
        verdict = assess_batch(
            batch(observed_max_c=30.0, lot_ids=["MLOT-1", "MLOT-2"],
                  documents=list(CORE_LOT_DOCUMENTS))
        )
        self.assertEqual(verdict["disposition"], QUARANTINE)
        self.assertGreaterEqual(len(verdict["quarantine_findings"]), 3)

    def test_a_non_limited_life_batch_carries_no_shelf_life_report(self):
        verdict = assess_batch(batch("piece-part", shelf_life_days=None))
        self.assertIsNone(verdict["shelf_life"])
        self.assertEqual(verdict["disposition"], RELEASE)


class GoodsInRollupTests(unittest.TestCase):
    def test_an_all_clean_delivery_releases_unrestricted(self):
        result = assess_goods_in([batch("adhesive"), batch("bonding-wire", shelf_life_days=None)])
        self.assertTrue(result["all_released_unrestricted"])
        self.assertEqual(result["batch_count"], 2)
        self.assertAlmostEqual(result["released_fraction"], 1.0, places=9)

    def test_one_quarantined_batch_lowers_the_released_fraction(self):
        result = assess_goods_in(
            [batch("adhesive"), batch("preform", shelf_life_days=None, observed_max_c=60.0)]
        )
        self.assertEqual(result["quarantined"], ["GRN-2026-PREFORM-01"])
        self.assertAlmostEqual(result["released_fraction"], 0.5, places=9)

    def test_a_restricted_batch_is_listed_separately_from_a_released_one(self):
        result = assess_goods_in(
            [batch("adhesive"), batch("sealing-material", receipt_date=day(340),
                                      days_to_use=60)]
        )
        self.assertEqual(result["released"], ["GRN-2026-ADHESIVE-01"])
        self.assertEqual(result["restricted"], ["GRN-2026-SEALING-MATERIAL-01"])

    def test_duplicate_batch_references_are_refused(self):
        with self.assertRaises(ValueError):
            assess_goods_in([batch("adhesive"), batch("adhesive")])

    def test_an_empty_delivery_is_refused(self):
        with self.assertRaises(ValueError):
            assess_goods_in([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
