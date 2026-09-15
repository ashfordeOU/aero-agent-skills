"""Contract tests for the clause 4.3.7 Class 1 incoming inspection logic.

The cases follow the delivery across the goods-in bench: the build week the
date code names, the age that puts a solderability re-test on the lot, the
bench count against the note, the packaging that arrived around the pieces,
the evidence pack that travelled with them, and the bonded-store-or-quarantine
decision that comes out of all of it.
"""

import unittest

from q60_class_1_incoming_inspection_logic import (
    DEFAULT_SOLDERABILITY_MONTHS,
    DRY_INDICATORS,
    MINIMUM_VISUAL_SAMPLE,
    REQUIRED_DOCUMENTS,
    assess_incoming_inspection,
    date_code_week_start,
    documentation_findings,
    packaging_findings,
    parse_day,
    part_age_months,
    reconcile_quantity,
    solderability_retest_due,
    visual_sample_size,
)


def _packaging(**overrides):
    record = {"seal_intact": True, "esd_bag_intact": True, "humidity_indicator": "blue"}
    record.update(overrides)
    return record


def _spec(**overrides):
    spec = {
        "date_code": "2514",
        "receipt_day": "2025-09-01",
        "declared": 400,
        "counted": 400,
        "damaged": 0,
        "packaging": _packaging(),
        "documents": list(REQUIRED_DOCUMENTS),
    }
    spec.update(overrides)
    return spec


class DateCodeTests(unittest.TestCase):
    def test_build_week_starts_on_a_monday(self):
        self.assertEqual(date_code_week_start("2514").weekday(), 0)

    def test_week_one_resolves_to_the_iso_first_week(self):
        first = date_code_week_start("2501")
        self.assertEqual(first.isocalendar()[1], 1)
        self.assertEqual(first.isocalendar()[0], 2025)

    def test_week_a_year_does_not_have_is_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("2553")

    def test_week_a_year_does_have_resolves(self):
        self.assertEqual(date_code_week_start("2053").year, 2020)

    def test_week_zero_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("2500")

    def test_non_digit_code_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("25W4")

    def test_partial_century_base_refused(self):
        with self.assertRaises(ValueError):
            date_code_week_start("2514", century_base=2010)

    def test_parse_day_rejects_a_non_iso_day(self):
        with self.assertRaises(ValueError):
            parse_day("receipt_day", "01/09/2025")


class AgeTests(unittest.TestCase):
    def test_whole_months_counted_from_the_build_week(self):
        # Week 14 of 2025 starts 2025-03-31; 1 September has not reached the
        # 31st of its month, so the sixth month is not yet complete.
        self.assertEqual(part_age_months("2514", "2025-09-01"), 5)

    def test_receipt_before_the_build_week_refused(self):
        with self.assertRaises(ValueError):
            part_age_months("2514", "2025-01-01")

    def test_fresh_lot_owes_no_retest(self):
        record = solderability_retest_due("2514", "2025-09-01", 24)
        self.assertFalse(record["retest_due"])
        self.assertEqual(record["threshold_months"], 24)

    def test_aged_lot_owes_a_retest(self):
        record = solderability_retest_due("2014", "2025-09-01", 24)
        self.assertTrue(record["retest_due"])

    def test_age_exactly_at_the_threshold_owes_no_retest(self):
        record = solderability_retest_due("2314", "2025-04-03", 24)
        self.assertEqual(record["age_months"], 24)
        self.assertFalse(record["retest_due"])

    def test_zero_threshold_refused(self):
        with self.assertRaises(ValueError):
            solderability_retest_due("2514", "2025-09-01", 0)

    def test_default_threshold_is_a_whole_number_of_months(self):
        self.assertIsInstance(DEFAULT_SOLDERABILITY_MONTHS, int)


class QuantityTests(unittest.TestCase):
    def test_matching_count_reconciles(self):
        record = reconcile_quantity(400, 400, 0)
        self.assertTrue(record["reconciled"])
        self.assertEqual(record["accepted"], 400)
        self.assertEqual(record["discrepancy"], 0)

    def test_short_delivery_reports_a_negative_discrepancy(self):
        record = reconcile_quantity(400, 397)
        self.assertEqual(record["discrepancy"], -3)
        self.assertFalse(record["reconciled"])

    def test_over_delivery_reports_a_positive_discrepancy(self):
        record = reconcile_quantity(400, 402)
        self.assertEqual(record["discrepancy"], 2)

    def test_damaged_pieces_leave_the_accepted_count(self):
        record = reconcile_quantity(400, 400, 6)
        self.assertEqual(record["accepted"], 394)
        self.assertFalse(record["reconciled"])

    def test_more_damage_than_pieces_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantity(400, 10, 11)

    def test_zero_declared_quantity_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantity(0, 0)

    def test_non_integer_count_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantity(400, 400.0)


class VisualSampleTests(unittest.TestCase):
    def test_square_delivery_draws_the_root_plus_one(self):
        self.assertEqual(visual_sample_size(400, minimum_sample=1), 21)

    def test_non_square_delivery_uses_the_integer_root(self):
        self.assertEqual(visual_sample_size(399, minimum_sample=1), 20)

    def test_declared_floor_raises_a_small_draw(self):
        self.assertEqual(visual_sample_size(4, minimum_sample=3), 3)

    def test_draw_never_exceeds_the_delivery(self):
        self.assertEqual(visual_sample_size(2, minimum_sample=5), 2)

    def test_zero_delivery_refused(self):
        with self.assertRaises(ValueError):
            visual_sample_size(0)

    def test_default_floor_is_positive(self):
        self.assertGreaterEqual(MINIMUM_VISUAL_SAMPLE, 1)


class DocumentationTests(unittest.TestCase):
    def test_full_pack_is_complete(self):
        record = documentation_findings(list(REQUIRED_DOCUMENTS))
        self.assertTrue(record["complete"])
        self.assertEqual(record["missing"], [])

    def test_missing_document_is_named(self):
        pack = [name for name in REQUIRED_DOCUMENTS if name != "buy-off-record"]
        record = documentation_findings(pack)
        self.assertFalse(record["complete"])
        self.assertIn("buy-off-record", record["missing"])

    def test_document_names_match_without_regard_to_case(self):
        record = documentation_findings([name.upper() for name in REQUIRED_DOCUMENTS])
        self.assertTrue(record["complete"])

    def test_extra_documents_do_not_close_a_gap(self):
        record = documentation_findings(["packing-list", "certificate-of-conformity"])
        self.assertFalse(record["complete"])
        self.assertEqual(len(record["missing"]), 3)

    def test_non_sequence_pack_refused(self):
        with self.assertRaises(ValueError):
            documentation_findings("certificate-of-conformity")

    def test_empty_required_list_refused(self):
        with self.assertRaises(ValueError):
            documentation_findings([], required=())


class PackagingTests(unittest.TestCase):
    def test_sound_packaging_raises_nothing(self):
        record = packaging_findings(_packaging())
        self.assertTrue(record["sound"])
        self.assertEqual(record["findings"], [])

    def test_broken_seal_raises_a_finding(self):
        record = packaging_findings(_packaging(seal_intact=False))
        self.assertFalse(record["sound"])
        self.assertIn("seal arrived broken", record["findings"][0])

    def test_open_static_bag_raises_a_finding(self):
        record = packaging_findings(_packaging(esd_bag_intact=False))
        self.assertFalse(record["sound"])

    def test_changed_humidity_indicator_raises_a_finding(self):
        record = packaging_findings(_packaging(humidity_indicator="pink"))
        self.assertFalse(record["dry"])
        self.assertTrue(any("damp" in item for item in record["findings"]))

    def test_dry_readings_are_named_not_guessed(self):
        self.assertIn("blue", DRY_INDICATORS)

    def test_non_boolean_seal_refused(self):
        with self.assertRaises(ValueError):
            packaging_findings(_packaging(seal_intact="yes"))

    def test_missing_packaging_key_refused(self):
        record = _packaging()
        del record["humidity_indicator"]
        with self.assertRaises(ValueError):
            packaging_findings(record)


class ArrivalDecisionTests(unittest.TestCase):
    def test_clean_arrival_goes_into_bonded_store(self):
        result = assess_incoming_inspection(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-into-bonded-store")
        self.assertEqual(result["accepted_pieces"], 400)
        self.assertEqual(result["findings"], [])

    def test_visual_sample_sized_from_the_accepted_pieces(self):
        result = assess_incoming_inspection(_spec())
        self.assertEqual(result["visual_sample_size"], 21)

    def test_count_discrepancy_quarantines(self):
        result = assess_incoming_inspection(_spec(counted=397))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "quarantine")
        self.assertTrue(any("disagrees with the delivery note" in item for item in result["findings"]))

    def test_transit_damage_quarantines_and_is_counted(self):
        result = assess_incoming_inspection(_spec(damaged=6))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["quantity"]["accepted"], 394)

    def test_damp_indicator_quarantines(self):
        result = assess_incoming_inspection(_spec(packaging=_packaging(humidity_indicator="pink")))
        self.assertFalse(result["accepted"])

    def test_missing_evidence_quarantines(self):
        result = assess_incoming_inspection(_spec(documents=["certificate-of-conformity"]))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("evidence pack is missing" in item for item in result["findings"]))

    def test_aged_lot_quarantines_for_solderability(self):
        result = assess_incoming_inspection(_spec(date_code="2014"))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("solderability re-test is due" in item for item in result["findings"]))

    def test_nothing_usable_arrived_draws_no_sample(self):
        result = assess_incoming_inspection(_spec(declared=10, counted=10, damaged=10))
        self.assertEqual(result["visual_sample_size"], 0)
        self.assertFalse(result["accepted"])

    def test_every_failing_check_is_reported_not_the_first(self):
        result = assess_incoming_inspection(
            _spec(
                counted=397,
                packaging=_packaging(seal_intact=False, humidity_indicator="pink"),
                documents=["certificate-of-conformity"],
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 5)

    def test_missing_spec_key_refused(self):
        spec = _spec()
        del spec["packaging"]
        with self.assertRaises(ValueError):
            assess_incoming_inspection(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_incoming_inspection(["date_code"])

    def test_pieces_are_grouped_by_the_accepted_count_not_the_note(self):
        result = assess_incoming_inspection(_spec(counted=400, damaged=4))
        self.assertEqual(result["quantity"]["accepted"], 396)
        self.assertEqual(result["accepted_pieces"], 0)


if __name__ == "__main__":
    unittest.main()
