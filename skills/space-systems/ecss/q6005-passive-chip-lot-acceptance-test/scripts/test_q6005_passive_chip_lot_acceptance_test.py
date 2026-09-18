"""Contract test for the passive-chip-lot-acceptance-test leaf (stdlib unittest)."""

import unittest

from q6005_passive_chip_lot_acceptance_test_logic import (
    ACCEPT,
    FRACTION_TOLERANCE,
    LARGE_LOT_SAMPLE_SIZE,
    POISSON_90_MULTIPLIER,
    REJECT,
    TEST_DESTRUCTIVE,
    TEST_NON_DESTRUCTIVE,
    acceptance_number,
    allowable_fraction,
    assess_incoming_batch,
    assess_lot,
    check_defectives,
    check_resubmission,
    check_sampling,
    confidence_multiplier_span,
    defective_fraction,
    lot_tolerance_percent_defective,
    pieces_to_reserve,
    sample_size_for_lot,
    sample_size_is_saturated,
    test_category,
    validate_lot,
    worst_lot_tolerance,
)


def lot(lot_id="L-1", family="chip-resistor", **kw):
    record = {
        "id": lot_id,
        "chip_family": family,
        "test_kind": "electrical-parameter-measurement",
        "lot_size": 1000,
        "sample_drawn": 32,
        "defectives_found": 0,
    }
    record.update(kw)
    return record


class TestSampleSizing(unittest.TestCase):
    def test_small_lot_takes_the_first_band(self):
        self.assertEqual(sample_size_for_lot(40), 8)

    def test_band_boundary_stays_in_the_lower_band(self):
        self.assertEqual(sample_size_for_lot(150), 13)
        self.assertEqual(sample_size_for_lot(151), 20)

    def test_sample_never_exceeds_a_tiny_lot(self):
        self.assertEqual(sample_size_for_lot(5), 5)

    def test_very_large_lot_saturates_the_plan(self):
        self.assertEqual(sample_size_for_lot(90000), LARGE_LOT_SAMPLE_SIZE)
        self.assertTrue(sample_size_is_saturated(90000))
        self.assertFalse(sample_size_is_saturated(1000))

    def test_zero_lot_size_raises(self):
        with self.assertRaises(ValueError):
            sample_size_for_lot(0)

    def test_non_integer_lot_size_raises(self):
        with self.assertRaises(ValueError):
            sample_size_for_lot(120.0)

    def test_boolean_lot_size_raises(self):
        with self.assertRaises(ValueError):
            sample_size_for_lot(True)


class TestAcceptanceNumber(unittest.TestCase):
    def test_destructive_test_accepts_nothing(self):
        self.assertEqual(acceptance_number(50, "terminal-solderability"), 0)
        self.assertEqual(
            test_category("terminal-solderability"), TEST_DESTRUCTIVE
        )

    def test_non_destructive_number_grows_with_the_sample(self):
        self.assertEqual(
            acceptance_number(13, "electrical-parameter-measurement"), 0
        )
        self.assertEqual(
            acceptance_number(50, "electrical-parameter-measurement"), 2
        )
        self.assertEqual(
            test_category("electrical-parameter-measurement"),
            TEST_NON_DESTRUCTIVE,
        )

    def test_large_sample_takes_the_ceiling_number(self):
        self.assertEqual(
            acceptance_number(200, "visual-external-inspection"), 5
        )

    def test_unknown_test_kind_raises(self):
        with self.assertRaises(ValueError):
            acceptance_number(32, "taste-test")


class TestDefectiveFraction(unittest.TestCase):
    def test_fraction_is_the_plain_quotient(self):
        self.assertAlmostEqual(defective_fraction(1, 50), 0.02, places=9)

    def test_clean_sample_is_zero(self):
        self.assertAlmostEqual(defective_fraction(0, 32), 0.0, places=12)

    def test_more_defectives_than_sample_raises(self):
        with self.assertRaises(ValueError):
            defective_fraction(9, 8)

    def test_negative_defectives_raises(self):
        with self.assertRaises(ValueError):
            defective_fraction(-1, 32)


class TestLotTolerance(unittest.TestCase):
    def test_zero_acceptance_tolerance_is_the_poisson_quotient(self):
        self.assertAlmostEqual(
            lot_tolerance_percent_defective(50, 0),
            POISSON_90_MULTIPLIER[0] / 50,
            places=12,
        )

    def test_a_bigger_sample_buys_a_tighter_tolerance(self):
        tight = lot_tolerance_percent_defective(200, 0)
        loose = lot_tolerance_percent_defective(20, 0)
        self.assertLess(tight, loose)

    def test_untabulated_acceptance_number_raises(self):
        with self.assertRaises(ValueError):
            lot_tolerance_percent_defective(50, 9)

    def test_multiplier_span_is_reported(self):
        low, high, total = confidence_multiplier_span()
        self.assertEqual((low, high), (0, 5))
        self.assertGreater(total, 30.0)


class TestValidateLot(unittest.TestCase):
    def test_sample_defaults_to_the_plan_size(self):
        norm = validate_lot(
            {
                "id": "L-9",
                "chip_family": "chip-resistor",
                "test_kind": "visual-external-inspection",
                "lot_size": 1000,
            }
        )
        self.assertEqual(norm["sample_drawn"], 32)
        self.assertEqual(norm["defectives_found"], 0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(["L-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(""))

    def test_unknown_chip_family_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot("L-1", family="wirewound-power-resistor"))

    def test_unknown_test_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot("L-1", test_kind="smell-test"))

    def test_defectives_beyond_the_sample_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot("L-1", sample_drawn=8, defectives_found=9))

    def test_non_boolean_rescreen_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot("L-1", rescreened="yes"))

    def test_unknown_family_allowable_raises(self):
        with self.assertRaises(ValueError):
            allowable_fraction("moulded-film-capacitor")


class TestSamplingFindings(unittest.TestCase):
    def test_undersized_sample_is_a_finding(self):
        self.assertIn(
            "sample-smaller-than-the-plan-requires",
            check_sampling(lot("L-1", lot_size=1000, sample_drawn=20)),
        )

    def test_sample_bigger_than_the_lot_is_a_finding(self):
        findings = check_sampling(lot("L-1", lot_size=10, sample_drawn=20))
        self.assertIn("sample-larger-than-the-lot-it-was-drawn-from", findings)

    def test_destructive_test_eating_the_lot_is_a_finding(self):
        findings = check_sampling(
            lot(
                "L-1",
                lot_size=8,
                sample_drawn=8,
                test_kind="destructive-physical-analysis",
            )
        )
        self.assertIn("destructive-sample-consumes-the-whole-lot", findings)

    def test_correctly_drawn_sample_has_no_finding(self):
        self.assertEqual(check_sampling(lot()), [])


class TestResubmission(unittest.TestCase):
    def test_fresh_lot_carries_no_resubmission_finding(self):
        self.assertEqual(check_resubmission(lot()), [])

    def test_resubmission_without_rescreen_is_refused(self):
        self.assertIn(
            "rejected-lot-resubmitted-without-a-rescreen",
            check_resubmission(lot("L-1", previously_rejected=True)),
        )

    def test_rescreen_without_approval_is_refused(self):
        findings = check_resubmission(
            lot("L-1", previously_rejected=True, rescreened=True)
        )
        self.assertIn("rescreen-performed-without-an-approval-on-record", findings)

    def test_approved_rescreen_is_admissible(self):
        findings = check_resubmission(
            lot(
                "L-1",
                previously_rejected=True,
                rescreened=True,
                rescreen_approved=True,
            )
        )
        self.assertEqual(findings, [])


class TestDefectiveFindings(unittest.TestCase):
    def test_count_above_the_acceptance_number_is_a_finding(self):
        findings = check_defectives(
            lot("L-1", test_kind="terminal-solderability", defectives_found=1)
        )
        self.assertIn("defectives-above-the-acceptance-number", findings)

    def test_fraction_can_fail_while_the_count_passes(self):
        findings = check_defectives(
            lot(
                "L-1",
                family="ceramic-chip-capacitor",
                lot_size=10000,
                sample_drawn=80,
                defectives_found=2,
            )
        )
        self.assertNotIn("defectives-above-the-acceptance-number", findings)
        self.assertIn("defective-fraction-above-the-family-allowable", findings)

    def test_fraction_exactly_on_the_allowable_is_accepted(self):
        record = lot("L-1", sample_drawn=50, defectives_found=1)
        result = assess_lot(record)
        self.assertAlmostEqual(
            result["defective_fraction"], result["allowable_fraction"], places=9
        )
        self.assertNotIn(
            "defective-fraction-above-the-family-allowable", result["findings"]
        )

    def test_tolerance_is_far_under_any_real_defect_rate(self):
        self.assertAlmostEqual(FRACTION_TOLERANCE, 1.0e-12, places=18)


class TestAssessLot(unittest.TestCase):
    def test_clean_lot_is_accepted(self):
        result = assess_lot(lot())
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["sample_owed"], 32)

    def test_any_finding_rejects_the_lot(self):
        result = assess_lot(lot("L-1", sample_drawn=20))
        self.assertEqual(result["disposition"], REJECT)

    def test_report_carries_the_plan_basis(self):
        result = assess_lot(lot())
        self.assertAlmostEqual(
            result["lot_tolerance_fraction"],
            POISSON_90_MULTIPLIER[result["acceptance_number"]] / 32,
            places=12,
        )


class TestBatch(unittest.TestCase):
    def test_batch_of_clean_lots_is_accepted(self):
        report = assess_incoming_batch([lot("L-1"), lot("L-2")])
        self.assertTrue(report["batch_accepted"])
        self.assertEqual(report["rejected_ids"], [])
        self.assertEqual(report["pieces_sampled"], 64)
        self.assertEqual(report["pieces_consumed"], 0)

    def test_destructive_pieces_are_counted_as_consumed(self):
        report = assess_incoming_batch(
            [lot("L-1", test_kind="termination-adhesion-pull")]
        )
        self.assertEqual(report["pieces_consumed"], 32)

    def test_one_bad_lot_fails_the_batch(self):
        report = assess_incoming_batch(
            [lot("L-1"), lot("L-2", sample_drawn=20)]
        )
        self.assertFalse(report["batch_accepted"])
        self.assertEqual(report["rejected_ids"], ["L-2"])
        self.assertEqual(report["accepted_ids"], ["L-1"])

    def test_duplicate_lot_id_raises(self):
        with self.assertRaises(ValueError):
            assess_incoming_batch([lot("L-1"), lot("L-1")])

    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_incoming_batch([])

    def test_non_list_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_incoming_batch(lot())

    def test_worst_tolerance_names_the_smallest_sample(self):
        lot_id, value = worst_lot_tolerance(
            [lot("L-1"), lot("L-2", lot_size=40, sample_drawn=8)]
        )
        self.assertEqual(lot_id, "L-2")
        self.assertAlmostEqual(value, POISSON_90_MULTIPLIER[0] / 8, places=12)


class TestReservation(unittest.TestCase):
    def test_only_destructive_kinds_reserve_pieces(self):
        reserved = pieces_to_reserve(
            1000,
            ["visual-external-inspection", "terminal-solderability"],
        )
        self.assertEqual(reserved, 32)

    def test_two_destructive_kinds_reserve_two_samples(self):
        reserved = pieces_to_reserve(
            1000,
            ["terminal-solderability", "destructive-physical-analysis"],
        )
        self.assertEqual(reserved, 64)

    def test_reservation_beyond_the_lot_raises(self):
        with self.assertRaises(ValueError):
            pieces_to_reserve(
                10,
                ["terminal-solderability", "destructive-physical-analysis"],
            )

    def test_empty_test_list_raises(self):
        with self.assertRaises(ValueError):
            pieces_to_reserve(1000, [])


if __name__ == "__main__":
    unittest.main()
