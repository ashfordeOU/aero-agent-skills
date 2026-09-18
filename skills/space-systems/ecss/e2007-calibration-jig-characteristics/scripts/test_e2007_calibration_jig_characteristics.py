#!/usr/bin/env python3
"""Contract test for the calibration jig characteristics leaf."""

import math
import unittest

from e2007_calibration_jig_characteristics_logic import (
    IMPEDANCE_TOLERANCE_FRACTION,
    MAX_INSERTION_LOSS_DB,
    MAX_STANDING_WAVE_RATIO,
    MIN_RADIAL_CLEARANCE_M,
    MIN_SCREENING_ATTENUATION_DB,
    NOMINAL_IMPEDANCE_OHM,
    assess_calibration_jig_set,
    check_impedance_match,
    check_insertion_loss,
    check_radial_clearance,
    check_screening_attenuation,
    check_usable_span,
    coaxial_characteristic_impedance,
    evaluate_calibration_jig,
    injected_current_a,
    insertion_loss_db,
    radial_clearance_m,
    standing_wave_ratio,
    transfer_impedance_db_ohm,
)

SPAN_LOWER_HZ = 1.0e4
SPAN_UPPER_HZ = 4.0e8


def good_jig(**overrides):
    jig = {
        "id": "JIG-A",
        "bore_diameter_m": 0.0046,
        "conductor_diameter_m": 0.002,
        "insertion_loss_db": 0.2,
        "screening_attenuation_db": 60.0,
        "usable_lower_hz": 1.0e3,
        "usable_upper_hz": 1.0e9,
    }
    jig.update(overrides)
    return jig


class TestCharacteristicImpedance(unittest.TestCase):
    def test_air_filled_geometry_lands_near_the_reference(self):
        impedance = coaxial_characteristic_impedance(0.0046, 0.002)
        self.assertAlmostEqual(impedance, 49.937, places=2)

    def test_dielectric_lowers_the_impedance_by_its_root(self):
        air = coaxial_characteristic_impedance(0.0046, 0.002)
        filled = coaxial_characteristic_impedance(0.0046, 0.002, 2.1)
        self.assertAlmostEqual(filled * math.sqrt(2.1), air, places=9)

    def test_wider_bore_raises_the_impedance(self):
        narrow = coaxial_characteristic_impedance(0.0046, 0.002)
        wide = coaxial_characteristic_impedance(0.0060, 0.002)
        self.assertGreater(wide, narrow + 1.0)

    def test_bore_not_exceeding_conductor_raises(self):
        with self.assertRaises(ValueError):
            coaxial_characteristic_impedance(0.002, 0.002)

    def test_permittivity_below_unity_raises(self):
        with self.assertRaises(ValueError):
            coaxial_characteristic_impedance(0.0046, 0.002, 0.5)

    def test_non_numeric_bore_raises(self):
        with self.assertRaises(ValueError):
            coaxial_characteristic_impedance("0.0046", 0.002)

    def test_infinite_bore_raises(self):
        with self.assertRaises(ValueError):
            coaxial_characteristic_impedance(float("inf"), 0.002)


class TestStandingWaveRatio(unittest.TestCase):
    def test_matched_fixture_gives_unity(self):
        self.assertAlmostEqual(standing_wave_ratio(50.0, 50.0), 1.0, places=12)

    def test_ratio_is_symmetric_about_the_reference(self):
        self.assertAlmostEqual(
            standing_wave_ratio(100.0, 50.0), standing_wave_ratio(25.0, 50.0), places=12
        )

    def test_zero_impedance_raises(self):
        with self.assertRaises(ValueError):
            standing_wave_ratio(0.0)

    def test_negative_reference_raises(self):
        with self.assertRaises(ValueError):
            standing_wave_ratio(50.0, -50.0)


class TestImpedanceMatch(unittest.TestCase):
    def test_reference_impedance_is_within(self):
        result = check_impedance_match(NOMINAL_IMPEDANCE_OHM)
        self.assertTrue(result["within"])
        self.assertTrue(result["ratio_within"])

    def test_allowed_band_is_a_fraction_of_the_reference(self):
        result = check_impedance_match(NOMINAL_IMPEDANCE_OHM)
        self.assertAlmostEqual(
            result["allowed_ohm"],
            NOMINAL_IMPEDANCE_OHM * IMPEDANCE_TOLERANCE_FRACTION,
            places=9,
        )

    def test_exact_boundary_is_within(self):
        edge = NOMINAL_IMPEDANCE_OHM * (1.0 + IMPEDANCE_TOLERANCE_FRACTION)
        result = check_impedance_match(edge)
        self.assertAlmostEqual(result["deviation_ohm"], result["allowed_ohm"], places=9)
        self.assertTrue(result["within"])

    def test_impedance_can_fail_while_the_ratio_still_passes(self):
        result = check_impedance_match(55.0)
        self.assertFalse(result["within"])
        self.assertTrue(result["ratio_within"])

    def test_large_mismatch_fails_both(self):
        result = check_impedance_match(70.0)
        self.assertFalse(result["within"])
        self.assertFalse(result["ratio_within"])
        self.assertGreater(result["standing_wave_ratio"], MAX_STANDING_WAVE_RATIO)

    def test_percent_is_signed(self):
        self.assertLess(check_impedance_match(45.0)["percent"], 0.0)
        self.assertGreater(check_impedance_match(51.0)["percent"], 0.0)

    def test_ratio_limit_below_unity_raises(self):
        with self.assertRaises(ValueError):
            check_impedance_match(50.0, max_ratio=0.5)


class TestRadialClearance(unittest.TestCase):
    def test_clearance_is_half_the_diameter_difference(self):
        self.assertAlmostEqual(radial_clearance_m(0.006, 0.002), 0.002, places=12)

    def test_generous_bore_passes(self):
        self.assertTrue(check_radial_clearance(0.006, 0.002)["within"])

    def test_exact_minimum_clearance_is_accepted(self):
        bore = 0.002 + 2.0 * MIN_RADIAL_CLEARANCE_M
        result = check_radial_clearance(bore, 0.002)
        self.assertAlmostEqual(result["clearance_m"], MIN_RADIAL_CLEARANCE_M, places=9)
        self.assertTrue(result["within"])

    def test_tight_bore_fails(self):
        self.assertFalse(check_radial_clearance(0.0024, 0.002)["within"])

    def test_conductor_filling_the_bore_raises(self):
        with self.assertRaises(ValueError):
            radial_clearance_m(0.002, 0.003)


class TestLossAndScreening(unittest.TestCase):
    def test_low_loss_passes(self):
        self.assertTrue(check_insertion_loss(0.1)["within"])

    def test_exact_loss_limit_is_accepted(self):
        result = check_insertion_loss(MAX_INSERTION_LOSS_DB)
        self.assertAlmostEqual(result["margin_db"], 0.0, places=9)
        self.assertTrue(result["within"])

    def test_excess_loss_fails(self):
        self.assertFalse(check_insertion_loss(1.5)["within"])

    def test_negative_loss_raises(self):
        with self.assertRaises(ValueError):
            check_insertion_loss(-0.1)

    def test_screening_above_the_floor_passes(self):
        self.assertTrue(check_screening_attenuation(55.0)["within"])

    def test_exact_screening_floor_is_accepted(self):
        result = check_screening_attenuation(MIN_SCREENING_ATTENUATION_DB)
        self.assertAlmostEqual(result["margin_db"], 0.0, places=9)
        self.assertTrue(result["within"])

    def test_thin_screening_fails(self):
        self.assertFalse(check_screening_attenuation(20.0)["within"])

    def test_loss_from_power_ratio(self):
        self.assertAlmostEqual(insertion_loss_db(1.0, 0.1), 10.0, places=9)

    def test_lossless_path_reads_zero(self):
        self.assertAlmostEqual(insertion_loss_db(2.0, 2.0), 0.0, places=12)

    def test_gain_from_a_passive_fixture_raises(self):
        with self.assertRaises(ValueError):
            insertion_loss_db(1.0, 2.0)


class TestUsableSpan(unittest.TestCase):
    def test_covering_fixture_passes(self):
        result = check_usable_span(1.0e3, 1.0e9, SPAN_LOWER_HZ, SPAN_UPPER_HZ)
        self.assertTrue(result["within"])
        self.assertAlmostEqual(result["low_shortfall_hz"], 0.0, places=9)

    def test_exactly_coincident_span_is_accepted(self):
        result = check_usable_span(
            SPAN_LOWER_HZ, SPAN_UPPER_HZ, SPAN_LOWER_HZ, SPAN_UPPER_HZ
        )
        self.assertTrue(result["within"])

    def test_short_top_end_is_a_shortfall(self):
        result = check_usable_span(1.0e3, 1.0e8, SPAN_LOWER_HZ, SPAN_UPPER_HZ)
        self.assertFalse(result["within"])
        self.assertAlmostEqual(result["high_shortfall_hz"], 3.0e8, places=3)

    def test_high_lower_edge_is_a_shortfall(self):
        result = check_usable_span(1.0e5, 1.0e9, SPAN_LOWER_HZ, SPAN_UPPER_HZ)
        self.assertFalse(result["within"])
        self.assertGreater(result["low_shortfall_hz"], 0.0)

    def test_descending_usable_span_raises(self):
        with self.assertRaises(ValueError):
            check_usable_span(1.0e9, 1.0e3, SPAN_LOWER_HZ, SPAN_UPPER_HZ)

    def test_descending_required_span_raises(self):
        with self.assertRaises(ValueError):
            check_usable_span(1.0e3, 1.0e9, SPAN_UPPER_HZ, SPAN_LOWER_HZ)


class TestCurrentAndTransferImpedance(unittest.TestCase):
    def test_current_from_applied_power(self):
        self.assertAlmostEqual(injected_current_a(50.0, 50.0), 1.0, places=12)

    def test_zero_power_drives_no_current(self):
        self.assertAlmostEqual(injected_current_a(0.0), 0.0, places=12)

    def test_negative_power_raises(self):
        with self.assertRaises(ValueError):
            injected_current_a(-1.0)

    def test_zero_impedance_raises(self):
        with self.assertRaises(ValueError):
            injected_current_a(1.0, 0.0)

    def test_transfer_impedance_of_one_ohm_reads_zero_db(self):
        self.assertAlmostEqual(transfer_impedance_db_ohm(1.0, 1.0), 0.0, places=9)

    def test_transfer_impedance_decade(self):
        self.assertAlmostEqual(transfer_impedance_db_ohm(10.0, 1.0), 20.0, places=9)

    def test_transfer_impedance_needs_a_current(self):
        with self.assertRaises(ValueError):
            transfer_impedance_db_ohm(1.0, 0.0)


class TestEvaluateCalibrationJig(unittest.TestCase):
    def test_good_fixture_is_fit_for_use(self):
        record = evaluate_calibration_jig(good_jig(), SPAN_LOWER_HZ, SPAN_UPPER_HZ)
        self.assertTrue(record["fit_for_use"])
        self.assertEqual(record["findings"], [])

    def test_realised_impedance_is_reported(self):
        record = evaluate_calibration_jig(good_jig(), SPAN_LOWER_HZ, SPAN_UPPER_HZ)
        self.assertAlmostEqual(record["characteristic_impedance_ohm"], 49.937, places=2)

    def test_wide_bore_raises_an_impedance_finding(self):
        record = evaluate_calibration_jig(
            good_jig(bore_diameter_m=0.0080), SPAN_LOWER_HZ, SPAN_UPPER_HZ
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("impedance-out-of-band", codes)

    def test_tight_bore_raises_a_clearance_finding(self):
        record = evaluate_calibration_jig(
            good_jig(bore_diameter_m=0.0021), SPAN_LOWER_HZ, SPAN_UPPER_HZ
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("radial-clearance-too-small", codes)

    def test_lossy_fixture_raises_a_loss_finding(self):
        record = evaluate_calibration_jig(
            good_jig(insertion_loss_db=2.0), SPAN_LOWER_HZ, SPAN_UPPER_HZ
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("insertion-loss-too-high", codes)

    def test_leaky_enclosure_raises_a_screening_finding(self):
        record = evaluate_calibration_jig(
            good_jig(screening_attenuation_db=10.0), SPAN_LOWER_HZ, SPAN_UPPER_HZ
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("screening-too-low", codes)

    def test_short_fixture_span_raises_a_span_finding(self):
        record = evaluate_calibration_jig(
            good_jig(usable_upper_hz=1.0e6), SPAN_LOWER_HZ, SPAN_UPPER_HZ
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("span-does-not-cover", codes)

    def test_unknown_key_raises(self):
        jig = good_jig()
        jig["coating"] = "tin"
        with self.assertRaises(ValueError):
            evaluate_calibration_jig(jig, SPAN_LOWER_HZ, SPAN_UPPER_HZ)

    def test_missing_key_raises(self):
        jig = good_jig()
        del jig["screening_attenuation_db"]
        with self.assertRaises(ValueError):
            evaluate_calibration_jig(jig, SPAN_LOWER_HZ, SPAN_UPPER_HZ)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_calibration_jig(good_jig(id="   "), SPAN_LOWER_HZ, SPAN_UPPER_HZ)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            evaluate_calibration_jig(["JIG-A"], SPAN_LOWER_HZ, SPAN_UPPER_HZ)

    def test_findings_carry_code_subject_and_detail(self):
        record = evaluate_calibration_jig(
            good_jig(insertion_loss_db=3.0), SPAN_LOWER_HZ, SPAN_UPPER_HZ
        )
        for finding in record["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


class TestAssessCalibrationJigSet(unittest.TestCase):
    def test_all_good_set_is_fit_for_use(self):
        report = assess_calibration_jig_set(
            [good_jig(id="JIG-A"), good_jig(id="JIG-B")],
            SPAN_LOWER_HZ,
            SPAN_UPPER_HZ,
        )
        self.assertEqual(report["verdict"], "fit-for-use")
        self.assertAlmostEqual(report["usable_fraction"], 1.0, places=12)

    def test_mixed_set_is_partially_usable(self):
        report = assess_calibration_jig_set(
            [good_jig(id="JIG-A"), good_jig(id="JIG-B", insertion_loss_db=4.0)],
            SPAN_LOWER_HZ,
            SPAN_UPPER_HZ,
        )
        self.assertEqual(report["verdict"], "partially-usable")
        self.assertEqual(report["usable_ids"], ["JIG-A"])

    def test_wholly_bad_set_is_not_usable(self):
        report = assess_calibration_jig_set(
            [good_jig(id="JIG-A", insertion_loss_db=4.0)], SPAN_LOWER_HZ, SPAN_UPPER_HZ
        )
        self.assertEqual(report["verdict"], "not-usable")
        self.assertFalse(report["accepted"])
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("no-usable-fixture", codes)

    def test_repeated_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_calibration_jig_set(
                [good_jig(), good_jig()], SPAN_LOWER_HZ, SPAN_UPPER_HZ
            )

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_calibration_jig_set([], SPAN_LOWER_HZ, SPAN_UPPER_HZ)

    def test_string_set_raises(self):
        with self.assertRaises(ValueError):
            assess_calibration_jig_set("JIG-A", SPAN_LOWER_HZ, SPAN_UPPER_HZ)

    def test_fixture_count_is_reported(self):
        report = assess_calibration_jig_set(
            [good_jig(id="JIG-A"), good_jig(id="JIG-B"), good_jig(id="JIG-C")],
            SPAN_LOWER_HZ,
            SPAN_UPPER_HZ,
        )
        self.assertEqual(report["fixture_count"], 3)


if __name__ == "__main__":
    unittest.main()
