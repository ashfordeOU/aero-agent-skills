"""Contract tests for the clause 4.3.7 incoming inspection logic.

The cases follow the receiving workflow one step at a time: purchase-order
reconciliation, the sample-sizing step, the visual accept-number gate, the
dry-pack checklist of seal, humidity card and floor life, the document
review, and the disposition that stops a delivery at the dock. Each step is
exercised on both sides of its limit.
"""

import math
import unittest

from q6013_class_1_incoming_inspection_logic import (
    MSL_FLOOR_LIFE_HOURS,
    REQUIRED_DOCUMENTS,
    assess_incoming_inspection,
    floor_life_status,
    humidity_indicator_verdict,
    missing_documents,
    quantity_discrepancy,
    reconcile_part_number,
    visual_sample_size,
    visual_verdict,
)

FULL_DOCS = {item: True for item in REQUIRED_DOCUMENTS}


def _spec(**overrides):
    spec = {
        "ordered_part_number": "XC7A35T-2FGG484I",
        "received_part_number": "XC7A35T-2FGG484I",
        "ordered_quantity": 100,
        "received_quantity": 100,
        "date_code_ordered": "2537",
        "date_code_received": "2537",
        "bag_seal_intact": True,
        "humidity_reading_percent": 5.0,
        "humidity_limit_percent": 10.0,
        "msl": "3",
        "exposed_hours": 12.0,
        "documents": dict(FULL_DOCS),
        "visual_defects": 0,
    }
    spec.update(overrides)
    return spec


class ReconciliationTests(unittest.TestCase):
    def test_identical_part_numbers_match(self):
        self.assertTrue(reconcile_part_number("AD8someX", "AD8someX")["matches"])

    def test_case_and_space_differences_still_match(self):
        self.assertTrue(reconcile_part_number(" ad8somex ", "AD8SOMEX")["matches"])

    def test_substituted_part_number_does_not_match(self):
        self.assertFalse(reconcile_part_number("AD8someX", "AD8someY")["matches"])

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_part_number("   ", "AD8someX")

    def test_exact_quantity_matches(self):
        result = quantity_discrepancy(100, 100)
        self.assertTrue(result["matches"])
        self.assertEqual(result["shortfall"], 0)
        self.assertEqual(result["overage"], 0)

    def test_short_delivery_reported(self):
        self.assertEqual(quantity_discrepancy(100, 96)["shortfall"], 4)

    def test_over_delivery_reported(self):
        self.assertEqual(quantity_discrepancy(100, 104)["overage"], 4)

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            quantity_discrepancy(100, -1)

    def test_zero_ordered_quantity_rejected(self):
        with self.assertRaises(ValueError):
            quantity_discrepancy(0, 10)


class SampleSizeTests(unittest.TestCase):
    def test_perfect_square_lot_gives_its_exact_root(self):
        self.assertEqual(visual_sample_size(100), 10)

    def test_non_square_lot_rounds_the_root_up(self):
        self.assertEqual(visual_sample_size(101), 11)

    def test_small_lot_raised_to_the_floor(self):
        self.assertEqual(visual_sample_size(9, floor=5), 5)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(visual_sample_size(3, floor=5), 3)

    def test_large_lot_limited_by_the_cap(self):
        self.assertEqual(visual_sample_size(1000000, cap=125), 125)

    def test_cap_below_floor_rejected(self):
        with self.assertRaises(ValueError):
            visual_sample_size(100, floor=10, cap=5)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            visual_sample_size(0)

    def test_sample_size_is_reproducible_for_the_same_lot(self):
        self.assertEqual(visual_sample_size(275), visual_sample_size(275))


class VisualTests(unittest.TestCase):
    def test_clean_sample_accepts(self):
        self.assertTrue(visual_verdict(10, 0)["accepted"])

    def test_one_defect_against_accept_on_zero_rejects(self):
        self.assertFalse(visual_verdict(10, 1)["accepted"])

    def test_defects_equal_to_accept_number_accept(self):
        self.assertTrue(visual_verdict(20, 2, accept_number=2)["accepted"])

    def test_defect_fraction_reported(self):
        self.assertAlmostEqual(visual_verdict(20, 1, accept_number=2)["defect_fraction"], 0.05, places=9)

    def test_more_defects_than_units_rejected(self):
        with self.assertRaises(ValueError):
            visual_verdict(5, 6)


class MoistureBarrierTests(unittest.TestCase):
    def test_reading_below_limit_within(self):
        self.assertTrue(humidity_indicator_verdict(5.0, 10.0)["within_limit"])

    def test_reading_exactly_on_limit_within(self):
        result = humidity_indicator_verdict(10.0, 10.0)
        self.assertAlmostEqual(result["margin_percent"], 0.0, places=9)
        self.assertTrue(result["within_limit"])

    def test_reading_above_limit_outside(self):
        self.assertFalse(humidity_indicator_verdict(20.0, 10.0)["within_limit"])

    def test_reading_outside_percentage_range_rejected(self):
        with self.assertRaises(ValueError):
            humidity_indicator_verdict(120.0, 10.0)

    def test_level_one_has_unlimited_floor_life(self):
        result = floor_life_status("1", 100000.0)
        self.assertTrue(math.isinf(result["floor_life_hours"]))
        self.assertTrue(result["within_floor_life"])

    def test_exposure_inside_level_three_floor_life(self):
        result = floor_life_status("3", 100.0)
        self.assertAlmostEqual(result["remaining_hours"], MSL_FLOOR_LIFE_HOURS["3"] - 100.0, places=9)
        self.assertTrue(result["within_floor_life"])

    def test_exposure_exactly_on_the_floor_life_still_within(self):
        result = floor_life_status("4", MSL_FLOOR_LIFE_HOURS["4"])
        self.assertAlmostEqual(result["remaining_hours"], 0.0, places=9)
        self.assertTrue(result["within_floor_life"])

    def test_exposure_past_the_floor_life_outside(self):
        self.assertFalse(floor_life_status("5a", 30.0)["within_floor_life"])

    def test_level_six_has_no_floor_life(self):
        self.assertFalse(floor_life_status("6", 1.0)["within_floor_life"])

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_status("7", 1.0)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_status("3", -1.0)


class DocumentTests(unittest.TestCase):
    def test_full_document_set_has_nothing_missing(self):
        self.assertEqual(missing_documents(FULL_DOCS), [])

    def test_absent_document_reported(self):
        docs = dict(FULL_DOCS)
        del docs["screening-data"]
        self.assertEqual(missing_documents(docs), ["screening-data"])

    def test_document_marked_not_received_reported(self):
        docs = dict(FULL_DOCS)
        docs["certificate-of-conformity"] = False
        self.assertIn("certificate-of-conformity", missing_documents(docs))

    def test_non_boolean_document_value_rejected(self):
        with self.assertRaises(ValueError):
            missing_documents({"screening-data": "later"})


class AssessmentTests(unittest.TestCase):
    def test_clean_delivery_released_to_bonded_store(self):
        result = assess_incoming_inspection(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "release-to-bonded-store")
        self.assertEqual(result["findings"], [])

    def test_substituted_part_number_quarantines(self):
        result = assess_incoming_inspection(_spec(received_part_number="XC7A35T-1FGG484I"))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "quarantine")

    def test_wrong_date_code_quarantines(self):
        result = assess_incoming_inspection(_spec(date_code_received="2601"))
        self.assertFalse(result["accepted"])
        self.assertFalse(result["date_code_matches"])

    def test_short_delivery_quarantines(self):
        result = assess_incoming_inspection(_spec(received_quantity=90))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["quantity"]["shortfall"], 10)

    def test_broken_bag_seal_quarantines(self):
        result = assess_incoming_inspection(_spec(bag_seal_intact=False))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("seal" in item for item in result["findings"]))

    def test_expired_floor_life_quarantines(self):
        result = assess_incoming_inspection(_spec(msl="4", exposed_hours=200.0))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("floor life" in item for item in result["findings"]))

    def test_visual_defect_quarantines_under_accept_on_zero(self):
        result = assess_incoming_inspection(_spec(visual_defects=1))
        self.assertFalse(result["accepted"])

    def test_sample_size_follows_the_received_quantity(self):
        result = assess_incoming_inspection(_spec(ordered_quantity=400, received_quantity=400))
        self.assertEqual(result["visual"]["sample_size"], 20)

    def test_missing_document_quarantines(self):
        docs = dict(FULL_DOCS)
        del docs["lot-acceptance-data"]
        result = assess_incoming_inspection(_spec(documents=docs))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["missing_documents"], ["lot-acceptance-data"])

    def test_every_reason_is_named_not_just_the_first(self):
        docs = dict(FULL_DOCS)
        del docs["screening-data"]
        result = assess_incoming_inspection(
            _spec(bag_seal_intact=False, received_quantity=95, documents=docs)
        )
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["msl"]
        with self.assertRaises(ValueError):
            assess_incoming_inspection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_incoming_inspection(["not", "a", "mapping"])

    def test_empty_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_incoming_inspection(_spec(received_quantity=0))


if __name__ == "__main__":
    unittest.main()
