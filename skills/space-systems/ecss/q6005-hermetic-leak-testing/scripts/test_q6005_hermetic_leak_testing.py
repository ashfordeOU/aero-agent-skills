"""Contract test for the hermetic-leak-testing leaf (stdlib unittest)."""

import math
import unittest

from q6005_hermetic_leak_testing_logic import (
    FAIL,
    FINE_TEST_BLIND_THRESHOLD,
    LARGE_CAVITY_REJECT_LIMIT,
    MAX_DWELL_HOURS,
    MIN_BOMB_PRESSURE_TIME_ATM_HOURS,
    MOLECULAR_WEIGHT_AIR,
    PASS,
    TRACER_MOLECULAR_WEIGHT,
    AmbiguousReading,
    assess_seal,
    assess_seal_batch,
    bomb_pressure_time_product,
    check_conditions,
    check_fine_leak,
    check_gross_leak,
    dwell_retention_fraction,
    fine_test_is_blind,
    limit_is_saturated,
    measured_tracer_rate,
    molecular_weight_ratio,
    recovered_leak_rate,
    reject_limit_for_volume,
    solvable_reading_ceiling,
    solve_true_leak_rate,
    tracer_molecular_weight,
    validate_seal,
)

CLEAN_READING = measured_tracer_rate(5.0e-8, 0.05, 5.0, 24.0, 0.5)
LEAKY_READING = measured_tracer_rate(4.0e-7, 0.05, 5.0, 24.0, 0.5)
OPEN_READING = measured_tracer_rate(5.0e-5, 0.05, 5.0, 24.0, 0.0)


def seal(unit_id="U-1", **kw):
    record = {
        "id": unit_id,
        "tracer": "helium",
        "test_order": "fine-then-gross",
        "cavity_volume_cm3": 0.05,
        "bomb_pressure_atm": 5.0,
        "bomb_time_h": 24.0,
        "dwell_time_h": 0.5,
        "measured_tracer_rate": CLEAN_READING,
        "gross_test_performed": True,
        "gross_test_bubbles_observed": False,
    }
    record.update(kw)
    return record


class TestRejectLimit(unittest.TestCase):
    def test_a_small_cavity_takes_the_tightest_limit(self):
        self.assertAlmostEqual(reject_limit_for_volume(0.005), 5.0e-8, places=15)

    def test_band_boundary_stays_in_the_lower_band(self):
        self.assertAlmostEqual(reject_limit_for_volume(0.01), 5.0e-8, places=15)
        self.assertAlmostEqual(reject_limit_for_volume(0.011), 1.0e-7, places=15)

    def test_a_large_cavity_saturates_the_loosest_limit(self):
        self.assertAlmostEqual(
            reject_limit_for_volume(2.0), LARGE_CAVITY_REJECT_LIMIT, places=15
        )
        self.assertTrue(limit_is_saturated(2.0))
        self.assertFalse(limit_is_saturated(0.005))

    def test_zero_volume_raises(self):
        with self.assertRaises(ValueError):
            reject_limit_for_volume(0.0)

    def test_boolean_volume_raises(self):
        with self.assertRaises(ValueError):
            reject_limit_for_volume(True)


class TestTracer(unittest.TestCase):
    def test_helium_is_lighter_than_air(self):
        self.assertLess(
            tracer_molecular_weight("helium"), MOLECULAR_WEIGHT_AIR
        )

    def test_the_ratio_is_the_square_root_of_the_weights(self):
        self.assertAlmostEqual(
            molecular_weight_ratio("helium"),
            math.sqrt(MOLECULAR_WEIGHT_AIR / 4.0),
            places=12,
        )

    def test_a_heavier_tracer_gives_a_smaller_ratio(self):
        self.assertLess(
            molecular_weight_ratio("krypton-85"), molecular_weight_ratio("helium")
        )

    def test_every_tracer_is_tabulated(self):
        for name in TRACER_MOLECULAR_WEIGHT:
            self.assertGreater(tracer_molecular_weight(name), 0.0)

    def test_unknown_tracer_raises(self):
        with self.assertRaises(ValueError):
            tracer_molecular_weight("argon")


class TestFixedMethodReading(unittest.TestCase):
    def test_a_longer_bomb_charges_the_cavity_further(self):
        short = measured_tracer_rate(5.0e-8, 0.05, 5.0, 2.0, 0.0)
        long_bomb = measured_tracer_rate(5.0e-8, 0.05, 5.0, 24.0, 0.0)
        self.assertLess(short, long_bomb)

    def test_a_higher_bomb_pressure_scales_the_reading(self):
        low = measured_tracer_rate(5.0e-8, 0.05, 2.0, 24.0, 0.0)
        high = measured_tracer_rate(5.0e-8, 0.05, 5.0, 24.0, 0.0)
        self.assertAlmostEqual(high / low, 2.5, places=9)

    def test_a_longer_dwell_lowers_the_reading(self):
        prompt = measured_tracer_rate(5.0e-7, 0.05, 5.0, 24.0, 0.0)
        late = measured_tracer_rate(5.0e-7, 0.05, 5.0, 24.0, 1.0)
        self.assertLess(late, prompt)

    def test_zero_dwell_retains_everything(self):
        self.assertAlmostEqual(
            dwell_retention_fraction(5.0e-7, 0.05, 0.0), 1.0, places=12
        )

    def test_retention_follows_the_exponential_decay(self):
        expected = math.exp(
            -5.0e-7 * molecular_weight_ratio("helium") * 3600.0 / 0.05
        )
        self.assertAlmostEqual(
            dwell_retention_fraction(5.0e-7, 0.05, 1.0), expected, places=12
        )

    def test_negative_dwell_raises(self):
        with self.assertRaises(ValueError):
            measured_tracer_rate(5.0e-8, 0.05, 5.0, 24.0, -1.0)

    def test_zero_bomb_time_raises(self):
        with self.assertRaises(ValueError):
            measured_tracer_rate(5.0e-8, 0.05, 5.0, 0.0, 0.5)


class TestRecovery(unittest.TestCase):
    def test_the_solver_inverts_the_relation(self):
        reading = measured_tracer_rate(7.5e-8, 0.05, 5.0, 24.0, 0.5)
        self.assertAlmostEqual(
            solve_true_leak_rate(reading, 0.05, 5.0, 24.0, 0.5) / 7.5e-8,
            1.0,
            places=9,
        )

    def test_recovery_works_for_a_heavier_tracer(self):
        reading = measured_tracer_rate(
            6.0e-8, 0.05, 5.0, 24.0, 0.25, "krypton-85"
        )
        self.assertAlmostEqual(
            solve_true_leak_rate(reading, 0.05, 5.0, 24.0, 0.25, "krypton-85")
            / 6.0e-8,
            1.0,
            places=9,
        )

    def test_the_ceiling_names_a_turning_point(self):
        peak_leak, peak_reading = solvable_reading_ceiling(0.005, 5.0, 24.0, 1.0)
        self.assertGreater(peak_leak, 0.0)
        self.assertGreater(
            peak_reading, measured_tracer_rate(peak_leak * 10.0, 0.005, 5.0, 24.0, 1.0)
        )

    def test_a_reading_above_the_ceiling_is_refused(self):
        _, peak_reading = solvable_reading_ceiling(0.005, 5.0, 24.0, 1.0)
        with self.assertRaises(AmbiguousReading):
            solve_true_leak_rate(peak_reading * 10.0, 0.005, 5.0, 24.0, 1.0)

    def test_an_ambiguous_reading_is_reported_absent_not_zero(self):
        _, peak_reading = solvable_reading_ceiling(0.005, 5.0, 24.0, 1.0)
        record = seal(
            "U-1",
            cavity_volume_cm3=0.005,
            dwell_time_h=1.0,
            measured_tracer_rate=peak_reading * 10.0,
        )
        self.assertIsNone(recovered_leak_rate(record))

    def test_a_resolvable_reading_returns_a_rate(self):
        self.assertIsNotNone(recovered_leak_rate(seal()))

    def test_zero_measured_rate_raises(self):
        with self.assertRaises(ValueError):
            solve_true_leak_rate(0.0, 0.05, 5.0, 24.0, 0.5)


class TestBlindness(unittest.TestCase):
    def test_a_hole_above_the_threshold_is_blind_to_the_fine_test(self):
        self.assertTrue(fine_test_is_blind(FINE_TEST_BLIND_THRESHOLD * 10.0))

    def test_a_tight_seal_is_not_blind(self):
        self.assertFalse(fine_test_is_blind(5.0e-8))

    def test_exactly_on_the_threshold_is_not_yet_blind(self):
        self.assertFalse(fine_test_is_blind(FINE_TEST_BLIND_THRESHOLD))

    def test_zero_leak_rate_raises(self):
        with self.assertRaises(ValueError):
            fine_test_is_blind(0.0)


class TestValidation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_seal(["U-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_seal(seal(""))

    def test_unknown_test_order_raises(self):
        with self.assertRaises(ValueError):
            validate_seal(seal("U-1", test_order="whenever"))

    def test_non_boolean_gross_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_seal(seal("U-1", gross_test_performed="yes"))

    def test_dwell_defaults_to_zero(self):
        norm = validate_seal(
            {
                "id": "U-9",
                "cavity_volume_cm3": 0.05,
                "bomb_pressure_atm": 5.0,
                "bomb_time_h": 24.0,
                "measured_tracer_rate": CLEAN_READING,
            }
        )
        self.assertAlmostEqual(norm["dwell_time_h"], 0.0, places=12)
        self.assertEqual(norm["tracer"], "helium")


class TestConditionFindings(unittest.TestCase):
    def test_the_product_is_pressure_times_time(self):
        self.assertAlmostEqual(
            bomb_pressure_time_product(5.0, 24.0), 120.0, places=9
        )

    def test_an_undercharged_bomb_is_a_finding(self):
        self.assertIn(
            "bomb-pressure-time-product-below-the-minimum",
            check_conditions(seal("U-1", bomb_pressure_atm=2.0, bomb_time_h=2.0)),
        )

    def test_a_product_exactly_on_the_minimum_is_accepted(self):
        record = seal("U-1", bomb_pressure_atm=1.0, bomb_time_h=MIN_BOMB_PRESSURE_TIME_ATM_HOURS)
        self.assertNotIn(
            "bomb-pressure-time-product-below-the-minimum",
            check_conditions(record),
        )

    def test_a_long_dwell_is_a_finding(self):
        self.assertIn(
            "dwell-exceeds-the-measurement-window",
            check_conditions(seal("U-1", dwell_time_h=MAX_DWELL_HOURS + 2.0)),
        )

    def test_a_dwell_exactly_on_the_window_is_accepted(self):
        self.assertEqual(check_conditions(seal("U-1", dwell_time_h=MAX_DWELL_HOURS)), [])


class TestFineLeakFindings(unittest.TestCase):
    def test_a_tight_seal_carries_no_finding(self):
        self.assertEqual(check_fine_leak(seal()), [])

    def test_a_rate_above_the_cavity_limit_is_a_finding(self):
        self.assertIn(
            "equivalent-leak-rate-above-the-cavity-limit",
            check_fine_leak(seal("U-1", measured_tracer_rate=LEAKY_READING)),
        )

    def test_the_same_reading_passes_in_a_larger_cavity(self):
        big = seal(
            "U-1",
            cavity_volume_cm3=2.0,
            measured_tracer_rate=measured_tracer_rate(4.0e-7, 2.0, 5.0, 24.0, 0.5),
        )
        self.assertEqual(check_fine_leak(big), [])

    def test_an_unresolved_reading_is_its_own_finding(self):
        _, peak_reading = solvable_reading_ceiling(0.005, 5.0, 24.0, 1.0)
        record = seal(
            "U-1",
            cavity_volume_cm3=0.005,
            dwell_time_h=1.0,
            measured_tracer_rate=peak_reading * 10.0,
        )
        self.assertIn(
            "reading-above-what-the-conditions-can-resolve", check_fine_leak(record)
        )


class TestGrossLeakFindings(unittest.TestCase):
    def test_a_completed_sequence_carries_no_finding(self):
        self.assertEqual(check_gross_leak(seal()), [])

    def test_a_missing_gross_test_is_a_finding(self):
        self.assertIn(
            "gross-leak-test-not-performed",
            check_gross_leak(seal("U-1", gross_test_performed=False)),
        )

    def test_the_wrong_order_is_a_finding(self):
        self.assertIn(
            "gross-leak-test-run-before-the-fine-leak-test",
            check_gross_leak(seal("U-1", test_order="gross-then-fine")),
        )

    def test_bubbles_are_a_finding(self):
        self.assertIn(
            "gross-leak-indication-observed",
            check_gross_leak(seal("U-1", gross_test_bubbles_observed=True)),
        )

    def test_a_blind_fine_test_without_a_gross_test_is_a_finding(self):
        record = seal(
            "U-1",
            dwell_time_h=0.0,
            measured_tracer_rate=OPEN_READING,
            gross_test_performed=False,
        )
        self.assertIn(
            "fine-test-blind-to-a-hole-this-large", check_gross_leak(record)
        )


class TestAssessSeal(unittest.TestCase):
    def test_a_sound_seal_is_accepted(self):
        result = assess_seal(seal())
        self.assertEqual(result["disposition"], PASS)
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["fine_test_blind"])

    def test_any_finding_rejects_the_seal(self):
        result = assess_seal(seal("U-1", gross_test_bubbles_observed=True))
        self.assertEqual(result["disposition"], FAIL)

    def test_the_report_carries_the_recovered_rate_and_the_limit(self):
        result = assess_seal(seal())
        self.assertAlmostEqual(
            result["equivalent_leak_rate"] / 5.0e-8, 1.0, places=9
        )
        self.assertAlmostEqual(result["reject_limit"], 1.0e-7, places=15)

    def test_an_unresolved_unit_reports_no_rate_rather_than_zero(self):
        _, peak_reading = solvable_reading_ceiling(0.005, 5.0, 24.0, 1.0)
        result = assess_seal(
            seal(
                "U-1",
                cavity_volume_cm3=0.005,
                dwell_time_h=1.0,
                measured_tracer_rate=peak_reading * 10.0,
            )
        )
        self.assertIsNone(result["equivalent_leak_rate"])
        self.assertIsNone(result["dwell_retention_fraction"])
        self.assertTrue(result["fine_test_blind"])


class TestBatch(unittest.TestCase):
    def test_a_clean_batch_is_accepted(self):
        report = assess_seal_batch([seal("U-1"), seal("U-2")])
        self.assertTrue(report["batch_accepted"])
        self.assertEqual(report["rejected_ids"], [])
        self.assertEqual(report["unresolved_ids"], [])

    def test_one_leaky_unit_fails_the_batch(self):
        report = assess_seal_batch(
            [seal("U-1"), seal("U-2", measured_tracer_rate=LEAKY_READING)]
        )
        self.assertFalse(report["batch_accepted"])
        self.assertEqual(report["rejected_ids"], ["U-2"])
        self.assertEqual(report["accepted_ids"], ["U-1"])

    def test_the_worst_rate_is_reported(self):
        report = assess_seal_batch(
            [seal("U-1"), seal("U-2", measured_tracer_rate=LEAKY_READING)]
        )
        self.assertAlmostEqual(
            report["worst_equivalent_leak_rate"] / 4.0e-7, 1.0, places=9
        )

    def test_duplicate_unit_id_raises(self):
        with self.assertRaises(ValueError):
            assess_seal_batch([seal("U-1"), seal("U-1")])

    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_seal_batch([])

    def test_non_list_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_seal_batch(seal())


if __name__ == "__main__":
    unittest.main()
