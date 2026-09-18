"""Contract test for the CVCM measurement leaf (stdlib unittest)."""

import unittest

from q7002_cvcm_measurement_logic import (
    BELOW_FLOOR,
    COLLECTOR_LOSS_NOISE_G,
    PLATE_LOST_MASS,
    QUANTIFICATION_FLOOR_G,
    QUANTIFIED,
    REPLICATE_SPREAD_LIMIT_PCT,
    REQUIRED_REPLICATES,
    assess_cvcm_run,
    assess_specimen,
    collector_gain_g,
    cvcm_percent,
    gain_status,
    mean_percent,
    quantification_floor_percent,
    replicate_spread_percent,
    validate_specimen,
)


def specimen(sid="S-1", initial=0.2, before=1.0, gain=2.0e-4):
    return {
        "id": sid,
        "initial_mass_g": initial,
        "collector_before_g": before,
        "collector_after_g": before + gain,
    }


class TestValidateSpecimen(unittest.TestCase):
    def test_valid_record_is_normalized(self):
        norm = validate_specimen(specimen())
        self.assertEqual(norm["id"], "S-1")
        self.assertAlmostEqual(norm["initial_mass_g"], 0.2, places=9)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_specimen(["S-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(""))

    def test_missing_initial_mass_raises(self):
        record = specimen()
        del record["initial_mass_g"]
        with self.assertRaises(ValueError):
            validate_specimen(record)

    def test_boolean_mass_is_not_numeric(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(initial=True))

    def test_zero_initial_mass_raises(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(initial=0.0))

    def test_mass_outside_holder_window_raises(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(initial=5.0))

    def test_negative_collector_mass_raises(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(before=-1.0))


class TestCollectorGain(unittest.TestCase):
    def test_gain_is_the_plate_difference(self):
        self.assertAlmostEqual(collector_gain_g(1.0, 1.0002), 2.0e-4, places=12)

    def test_a_lighter_plate_gives_a_negative_gain(self):
        self.assertLess(collector_gain_g(1.0, 0.9999), 0.0)

    def test_non_numeric_gain_input_raises(self):
        with self.assertRaises(ValueError):
            collector_gain_g("1.0", 1.0002)


class TestCvcmPercent(unittest.TestCase):
    def test_cvcm_normalizes_by_the_initial_specimen_mass(self):
        self.assertAlmostEqual(cvcm_percent(1.0, 1.0002, 0.2), 0.1, places=9)

    def test_doubling_the_specimen_halves_the_percentage(self):
        one = cvcm_percent(1.0, 1.0002, 0.2)
        two = cvcm_percent(1.0, 1.0002, 0.4)
        self.assertAlmostEqual(one, 2.0 * two, places=9)

    def test_zero_specimen_mass_raises(self):
        with self.assertRaises(ValueError):
            cvcm_percent(1.0, 1.0002, 0.0)

    def test_quantification_floor_scales_with_specimen_mass(self):
        floor = quantification_floor_percent(0.2)
        self.assertAlmostEqual(floor, QUANTIFICATION_FLOOR_G / 0.2 * 100.0, places=12)


class TestGainStatus(unittest.TestCase):
    def test_a_clear_deposit_is_quantified(self):
        self.assertEqual(gain_status(2.0e-4), QUANTIFIED)

    def test_a_gain_on_the_floor_is_quantified(self):
        self.assertEqual(gain_status(QUANTIFICATION_FLOOR_G), QUANTIFIED)

    def test_a_gain_under_the_floor_is_not_quantified(self):
        self.assertEqual(gain_status(QUANTIFICATION_FLOOR_G / 2.0), BELOW_FLOOR)

    def test_a_small_loss_is_scatter_not_a_plate_defect(self):
        self.assertEqual(gain_status(-COLLECTOR_LOSS_NOISE_G), BELOW_FLOOR)

    def test_a_loss_past_the_noise_band_is_a_plate_defect(self):
        self.assertEqual(gain_status(-10.0 * COLLECTOR_LOSS_NOISE_G), PLATE_LOST_MASS)


class TestAssessSpecimen(unittest.TestCase):
    def test_a_normal_specimen_is_usable(self):
        result = assess_specimen(specimen())
        self.assertTrue(result["usable"])
        self.assertEqual(result["gain_status"], QUANTIFIED)
        self.assertAlmostEqual(result["reported_cvcm_percent"], 0.1, places=9)

    def test_a_sub_floor_specimen_reports_no_value(self):
        result = assess_specimen(specimen(gain=QUANTIFICATION_FLOOR_G / 4.0))
        self.assertEqual(result["gain_status"], BELOW_FLOOR)
        self.assertIsNone(result["reported_cvcm_percent"])
        self.assertTrue(result["usable"])

    def test_a_plate_that_lost_mass_is_a_finding(self):
        result = assess_specimen(specimen(gain=-1.0e-4))
        self.assertFalse(result["usable"])
        self.assertIn(
            "collector-plate-lost-mass-beyond-weighing-noise", result["findings"]
        )


class TestReplicateStatistics(unittest.TestCase):
    def test_spread_is_max_minus_min(self):
        self.assertAlmostEqual(
            replicate_spread_percent([0.10, 0.12, 0.11]), 0.02, places=9
        )

    def test_mean_of_equal_values_is_that_value(self):
        self.assertAlmostEqual(mean_percent([0.10, 0.10, 0.10]), 0.10, places=12)

    def test_empty_replicates_raise(self):
        with self.assertRaises(ValueError):
            replicate_spread_percent([])

    def test_non_sequence_mean_input_raises(self):
        with self.assertRaises(ValueError):
            mean_percent(0.10)


class TestAssessRun(unittest.TestCase):
    def _run(self, gains):
        return assess_cvcm_run(
            [specimen("S-%d" % i, gain=g) for i, g in enumerate(gains, start=1)]
        )

    def test_three_tight_replicates_are_acceptable(self):
        report = self._run([2.0e-4, 2.02e-4, 1.98e-4])
        self.assertTrue(report["acceptable"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["mean_cvcm_percent"], 0.1, places=9)

    def test_too_few_replicates_is_a_finding(self):
        report = self._run([2.0e-4, 2.0e-4])
        self.assertFalse(report["acceptable"])
        self.assertIn(
            "fewer-replicates-than-the-method-requires", report["findings"]
        )
        self.assertLess(len(report["specimens"]), REQUIRED_REPLICATES)

    def test_a_spread_on_the_band_edge_still_passes(self):
        # 0.10 / 0.11 / 0.12 percent spans exactly the reproducibility band.
        report = self._run([2.0e-4, 2.2e-4, 2.4e-4])
        self.assertAlmostEqual(
            report["replicate_spread_percent"], REPLICATE_SPREAD_LIMIT_PCT, places=9
        )
        self.assertTrue(report["acceptable"])

    def test_a_wide_spread_is_a_finding(self):
        report = self._run([2.0e-4, 2.0e-4, 8.0e-4])
        self.assertFalse(report["acceptable"])
        self.assertIn(
            "replicate-spread-beyond-the-reproducibility-band", report["findings"]
        )

    def test_a_run_with_a_damaged_plate_is_flagged_twice(self):
        report = self._run([2.0e-4, 2.0e-4, -1.0e-4])
        self.assertIn("run-contains-a-plate-that-lost-mass", report["findings"])
        self.assertFalse(report["acceptable"])

    def test_an_all_sub_floor_run_reports_a_sub_floor_status(self):
        floor_quarter = QUANTIFICATION_FLOOR_G / 4.0
        report = self._run([floor_quarter, floor_quarter, floor_quarter])
        self.assertEqual(report["gain_status"], BELOW_FLOOR)
        self.assertTrue(report["acceptable"])

    def test_a_run_of_only_damaged_plates_has_no_mean(self):
        report = self._run([-1.0e-4, -1.0e-4, -1.0e-4])
        self.assertIsNone(report["mean_cvcm_percent"])
        self.assertIn("no-usable-replicate-in-the-run", report["findings"])

    def test_duplicate_specimen_id_raises(self):
        with self.assertRaises(ValueError):
            assess_cvcm_run([specimen("S-1"), specimen("S-1"), specimen("S-1")])

    def test_empty_run_raises(self):
        with self.assertRaises(ValueError):
            assess_cvcm_run([])

    def test_non_list_run_raises(self):
        with self.assertRaises(ValueError):
            assess_cvcm_run(specimen())


if __name__ == "__main__":
    unittest.main()
