#!/usr/bin/env python3
"""Gate 3 contract test for q6005-active-chip-user-lot-testing.

Offline, deterministic, stdlib unittest. Exercises the clause 8.3.3
logic: the lot-size sampling schedule, full-inspection collapse, sample
disposition against the acceptance number, the exact hypergeometric
acceptance probability, receiving-log normalization and the
reconciliation that catches an untested delivery or a reused lot
identifier.
"""

import unittest

from q6005_active_chip_user_lot_testing_logic import (
    SAMPLING_SCHEDULE,
    acceptance_probability,
    assess_user_lot_testing,
    disposition_sample,
    evaluate_delivery,
    format_user_lot_report,
    normalize_receiving_log,
    sampling_plan_for_lot,
    validate_delivery,
)


def delivery(**kw):
    entry = {
        "delivery_id": "dn-001",
        "lot_id": "lot-a",
        "lot_size": 100,
        "nonconforming_found": 0,
    }
    entry.update(kw)
    return entry


class TestSamplingSchedule(unittest.TestCase):
    def test_mid_band_lot_gets_its_band_plan(self):
        plan = sampling_plan_for_lot(100)
        self.assertEqual(plan["sample_size"], 32)
        self.assertEqual(plan["acceptance_number"], 1)
        self.assertFalse(plan["full_inspection"])

    def test_small_batch_collapses_to_full_inspection(self):
        plan = sampling_plan_for_lot(5)
        self.assertEqual(plan["sample_size"], 5)
        self.assertTrue(plan["full_inspection"])

    def test_band_boundary_lot_stays_in_the_lower_band(self):
        self.assertEqual(sampling_plan_for_lot(150)["sample_size"], 32)
        self.assertEqual(sampling_plan_for_lot(151)["sample_size"], 50)

    def test_very_large_lot_uses_the_open_band(self):
        plan = sampling_plan_for_lot(20000)
        self.assertEqual(plan["sample_size"], 125)
        self.assertEqual(plan["acceptance_number"], 5)

    def test_sample_size_never_shrinks_with_lot_size(self):
        sizes = [sampling_plan_for_lot(n)["sample_size"] for n in (8, 25, 50, 150, 500)]
        self.assertEqual(sizes, sorted(sizes))

    def test_empty_delivery_raises(self):
        with self.assertRaises(ValueError):
            sampling_plan_for_lot(0)

    def test_non_integer_lot_size_raises(self):
        with self.assertRaises(ValueError):
            sampling_plan_for_lot(100.5)

    def test_boolean_lot_size_raises(self):
        with self.assertRaises(ValueError):
            sampling_plan_for_lot(True)

    def test_schedule_is_ordered_by_upper_bound(self):
        bounds = [band[0] for band in SAMPLING_SCHEDULE]
        self.assertEqual(bounds, sorted(bounds))


class TestSampleDisposition(unittest.TestCase):
    def test_count_on_the_acceptance_number_is_accepted(self):
        result = disposition_sample(100, 1)
        self.assertTrue(result["accepted"])

    def test_count_above_the_acceptance_number_is_rejected(self):
        result = disposition_sample(100, 2)
        self.assertFalse(result["accepted"])

    def test_short_sample_cannot_accept_a_batch(self):
        result = disposition_sample(100, 0, sample_size=10)
        self.assertTrue(result["short_sample"])
        self.assertFalse(result["accepted"])

    def test_full_inspection_of_a_small_batch_accepts_a_clean_result(self):
        result = disposition_sample(5, 0)
        self.assertTrue(result["full_inspection"])
        self.assertTrue(result["accepted"])

    def test_sample_larger_than_the_batch_raises(self):
        with self.assertRaises(ValueError):
            disposition_sample(20, 0, sample_size=40)

    def test_more_nonconforming_than_inspected_raises(self):
        with self.assertRaises(ValueError):
            disposition_sample(100, 40)

    def test_negative_nonconforming_count_raises(self):
        with self.assertRaises(ValueError):
            disposition_sample(100, -1)


class TestAcceptanceProbability(unittest.TestCase):
    def test_defect_free_batch_is_always_accepted(self):
        self.assertAlmostEqual(acceptance_probability(10, 5, 0, 0), 1.0, places=9)

    def test_full_inspection_never_accepts_a_defective_batch(self):
        self.assertAlmostEqual(acceptance_probability(10, 10, 1, 0), 0.0, places=9)

    def test_exact_hypergeometric_value(self):
        self.assertAlmostEqual(acceptance_probability(4, 2, 2, 0), 1.0 / 6.0, places=9)

    def test_probability_falls_as_the_defect_population_grows(self):
        light = acceptance_probability(200, 32, 4, 1)
        heavy = acceptance_probability(200, 32, 40, 1)
        self.assertGreater(light, heavy)

    def test_probability_is_bounded(self):
        value = acceptance_probability(200, 32, 10, 1)
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 1.0)

    def test_defect_population_larger_than_the_lot_raises(self):
        with self.assertRaises(ValueError):
            acceptance_probability(50, 20, 60, 1)

    def test_sample_larger_than_the_lot_raises(self):
        with self.assertRaises(ValueError):
            acceptance_probability(50, 80, 1, 1)


class TestReceivingLogNormalization(unittest.TestCase):
    def test_valid_entry_normalizes(self):
        item = validate_delivery(delivery())
        self.assertEqual(item["lot_id"], "lot-a")
        self.assertTrue(item["tested"])

    def test_untested_entry_is_marked_untested(self):
        item = validate_delivery(delivery(nonconforming_found=None))
        self.assertFalse(item["tested"])

    def test_blank_lot_id_raises(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(lot_id="  "))

    def test_missing_delivery_id_raises(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(delivery_id=None))

    def test_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_delivery(("dn-001", 100))

    def test_repeated_delivery_identifier_raises(self):
        with self.assertRaises(ValueError):
            normalize_receiving_log([delivery(), delivery()])

    def test_empty_log_raises(self):
        with self.assertRaises(ValueError):
            normalize_receiving_log([])


class TestDeliveryEvaluation(unittest.TestCase):
    def test_untested_delivery_is_never_accepted(self):
        outcome = evaluate_delivery(validate_delivery(delivery(nonconforming_found=None)))
        self.assertFalse(outcome["accepted"])
        self.assertTrue(any("no user-lot test" in r for r in outcome["reasons"]))

    def test_clean_delivery_has_no_reasons(self):
        outcome = evaluate_delivery(validate_delivery(delivery()))
        self.assertTrue(outcome["accepted"])
        self.assertEqual(outcome["reasons"], [])


class TestLogAssessment(unittest.TestCase):
    def test_clean_log_conforms(self):
        report = assess_user_lot_testing(
            [
                delivery(delivery_id="dn-001", lot_id="lot-a"),
                delivery(delivery_id="dn-002", lot_id="lot-b"),
            ]
        )
        self.assertTrue(report["conforming"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["accepted_deliveries"], ["dn-001", "dn-002"])

    def test_untested_delivery_is_a_finding(self):
        report = assess_user_lot_testing(
            [
                delivery(delivery_id="dn-001", lot_id="lot-a"),
                delivery(delivery_id="dn-002", lot_id="lot-b", nonconforming_found=None),
            ]
        )
        self.assertFalse(report["conforming"])
        self.assertEqual(report["untested_deliveries"], ["dn-002"])

    def test_reused_lot_identifier_is_a_finding(self):
        report = assess_user_lot_testing(
            [
                delivery(delivery_id="dn-001", lot_id="lot-a"),
                delivery(delivery_id="dn-002", lot_id="lot-a"),
            ]
        )
        self.assertFalse(report["conforming"])
        self.assertEqual(report["reused_lot_ids"], ["lot-a"])

    def test_overcount_delivery_is_rejected(self):
        report = assess_user_lot_testing(
            [delivery(delivery_id="dn-001", lot_id="lot-a", nonconforming_found=3)]
        )
        self.assertFalse(report["conforming"])
        self.assertEqual(report["accepted_deliveries"], [])

    def test_outcomes_are_sorted_by_delivery(self):
        report = assess_user_lot_testing(
            [
                delivery(delivery_id="dn-009", lot_id="lot-b"),
                delivery(delivery_id="dn-002", lot_id="lot-a"),
            ]
        )
        ids = [o["delivery_id"] for o in report["outcomes"]]
        self.assertEqual(ids, sorted(ids))


class TestReportRendering(unittest.TestCase):
    def test_report_is_deterministic(self):
        log = [delivery(delivery_id="dn-001", lot_id="lot-a")]
        first = format_user_lot_report(assess_user_lot_testing(log))
        second = format_user_lot_report(assess_user_lot_testing(log))
        self.assertEqual(first, second)
        self.assertIn("CONFORMING", first)

    def test_report_text_lists_findings(self):
        text = format_user_lot_report(
            assess_user_lot_testing(
                [delivery(delivery_id="dn-001", lot_id="lot-a", nonconforming_found=5)]
            )
        )
        self.assertIn("NOT CONFORMING", text)
        self.assertIn("FINDING:", text)


if __name__ == "__main__":
    unittest.main()
