"""Contract tests for the ambient-temperature metallic test logic."""

import unittest

from q7045_ambient_temperature_testing_logic import (
    ELASTIC_STRESS_RATE_WINDOW_MPA_S,
    MIN_LOAD_CELL_UTILISATION,
    PLASTIC_STRAIN_RATE_WINDOW_PER_S,
    SECONDS_PER_MINUTE,
    assess_ambient_test,
    calibration_valid,
    extensometer_suitable,
    load_cell_utilisation,
    peak_load_kn,
    rate_within_window,
    required_extensometer_class,
    strain_rate_per_s,
    stress_rate_mpa_s,
)

MODULUS_MPA = 70000.0
PARALLEL_LENGTH_MM = 60.0
# 1.5e-4 /s: inside the plastic window and 10.5 MPa/s inside the elastic one.
NOMINAL_SPEED_MM_MIN = 1.5e-4 * PARALLEL_LENGTH_MM * SECONDS_PER_MINUTE


def setup(**overrides):
    """A 10 mm round aluminium piece pulled for proof strength at room temperature."""
    spec = {
        "crosshead_speed_mm_min": NOMINAL_SPEED_MM_MIN,
        "parallel_length_mm": PARALLEL_LENGTH_MM,
        "modulus_mpa": MODULUS_MPA,
        "area_mm2": 78.54,
        "expected_strength_mpa": 480.0,
        "load_cell_range_kn": 100.0,
        "test_date": "2026-09-18",
        "calibration_due_date": "2027-03-01",
        "measured_quantity": "proof-strength",
        "extensometer_class": 1,
        "extensometer_gauge_length_mm": 50.0,
        "reported_gauge_length_mm": 50.0,
    }
    spec.update(overrides)
    return spec


class RateConversionTests(unittest.TestCase):
    def test_crosshead_speed_converts_to_strain_rate(self):
        self.assertAlmostEqual(
            strain_rate_per_s(0.6, 60.0), 0.6 / 60.0 / 60.0, places=12
        )

    def test_a_shorter_piece_sees_a_faster_rate_at_the_same_speed(self):
        self.assertGreater(strain_rate_per_s(0.6, 30.0), strain_rate_per_s(0.6, 60.0))

    def test_strain_rate_scales_with_the_modulus_into_a_stress_rate(self):
        self.assertAlmostEqual(stress_rate_mpa_s(1.0e-4, 70000.0), 7.0, places=9)

    def test_zero_parallel_length_rejected(self):
        with self.assertRaises(ValueError):
            strain_rate_per_s(0.6, 0.0)

    def test_negative_speed_rejected(self):
        with self.assertRaises(ValueError):
            strain_rate_per_s(-0.6, 60.0)

    def test_non_numeric_modulus_rejected(self):
        with self.assertRaises(ValueError):
            stress_rate_mpa_s(1.0e-4, "70000")


class RateWindowTests(unittest.TestCase):
    def test_a_rate_inside_the_window_passes(self):
        self.assertTrue(rate_within_window(10.0, ELASTIC_STRESS_RATE_WINDOW_MPA_S)["within"])

    def test_a_rate_exactly_on_the_lower_bound_passes(self):
        low = ELASTIC_STRESS_RATE_WINDOW_MPA_S[0]
        result = rate_within_window(low, ELASTIC_STRESS_RATE_WINDOW_MPA_S)
        self.assertAlmostEqual(result["rate"], low, places=9)
        self.assertTrue(result["within"])

    def test_a_rate_exactly_on_the_upper_bound_passes(self):
        high = ELASTIC_STRESS_RATE_WINDOW_MPA_S[1]
        result = rate_within_window(high, ELASTIC_STRESS_RATE_WINDOW_MPA_S)
        self.assertAlmostEqual(result["rate"], high, places=9)
        self.assertTrue(result["within"])

    def test_a_fast_rate_is_reported_as_too_fast(self):
        result = rate_within_window(200.0, ELASTIC_STRESS_RATE_WINDOW_MPA_S)
        self.assertTrue(result["too_fast"])
        self.assertFalse(result["too_slow"])

    def test_a_slow_rate_is_reported_as_too_slow(self):
        result = rate_within_window(0.2, ELASTIC_STRESS_RATE_WINDOW_MPA_S)
        self.assertTrue(result["too_slow"])

    def test_an_inverted_window_is_rejected(self):
        with self.assertRaises(ValueError):
            rate_within_window(10.0, (20.0, 2.0))


class LoadCellTests(unittest.TestCase):
    def test_peak_load_follows_section_and_strength(self):
        self.assertAlmostEqual(peak_load_kn(100.0, 500.0), 50.0, places=9)

    def test_a_well_matched_cell_is_accepted(self):
        self.assertTrue(load_cell_utilisation(50.0, 100.0)["ok"])

    def test_a_peak_exactly_at_the_usable_floor_is_accepted(self):
        result = load_cell_utilisation(10.0, 100.0)
        self.assertAlmostEqual(result["fraction"], MIN_LOAD_CELL_UTILISATION, places=9)
        self.assertFalse(result["too_low"])

    def test_an_oversized_cell_buries_the_reading(self):
        result = load_cell_utilisation(5.0, 1000.0)
        self.assertTrue(result["too_low"])
        self.assertFalse(result["ok"])

    def test_a_peak_over_the_cell_range_is_reported(self):
        self.assertTrue(load_cell_utilisation(150.0, 100.0)["over_range"])

    def test_zero_cell_range_rejected(self):
        with self.assertRaises(ValueError):
            load_cell_utilisation(50.0, 0.0)


class CalibrationTests(unittest.TestCase):
    def test_a_calibration_due_after_the_test_is_valid(self):
        self.assertTrue(calibration_valid("2026-09-18", "2027-03-01"))

    def test_a_calibration_due_on_the_test_date_is_still_valid(self):
        self.assertTrue(calibration_valid("2026-09-18", "2026-09-18"))

    def test_an_expired_calibration_is_not_valid(self):
        self.assertFalse(calibration_valid("2026-09-18", "2026-03-01"))

    def test_a_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            calibration_valid("18/09/2026", "2027-03-01")


class ExtensometerTests(unittest.TestCase):
    def test_a_proof_strength_needs_the_tighter_class(self):
        self.assertEqual(required_extensometer_class("proof-strength"), 1)

    def test_an_elongation_after_fracture_does_not(self):
        self.assertEqual(required_extensometer_class("elongation-after-fracture"), 2)

    def test_an_unknown_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            required_extensometer_class("toughness-feel")

    def test_a_class_one_device_serves_a_class_two_need(self):
        result = extensometer_suitable("elongation-after-fracture", 1, 50.0, 50.0)
        self.assertTrue(result["ok"])

    def test_a_class_two_device_does_not_serve_a_proof_strength(self):
        result = extensometer_suitable("proof-strength", 2, 50.0, 50.0)
        self.assertFalse(result["ok"])
        self.assertTrue(any("looser" in f for f in result["findings"]))

    def test_a_gauge_length_mismatch_is_a_finding(self):
        result = extensometer_suitable("proof-strength", 1, 25.0, 50.0)
        self.assertTrue(any("reported on" in f for f in result["findings"]))

    def test_a_mismatch_inside_the_match_tolerance_is_accepted(self):
        result = extensometer_suitable("proof-strength", 1, 50.05, 50.0)
        self.assertTrue(result["ok"])

    def test_a_non_integer_device_class_rejected(self):
        with self.assertRaises(ValueError):
            extensometer_suitable("proof-strength", 1.5, 50.0, 50.0)


class AssessmentTests(unittest.TestCase):
    def test_a_correctly_set_up_run_is_valid(self):
        result = assess_ambient_test(setup())
        self.assertEqual(result["status"], "run-valid")
        self.assertEqual(result["findings"], [])

    def test_the_nominal_setup_sits_inside_both_windows(self):
        result = assess_ambient_test(setup())
        self.assertTrue(result["elastic_rate"]["within"])
        self.assertTrue(result["plastic_rate"]["within"])

    def test_a_fast_pull_is_reported_as_inflating_the_strength(self):
        result = assess_ambient_test(
            setup(crosshead_speed_mm_min=NOMINAL_SPEED_MM_MIN * 100.0)
        )
        self.assertTrue(any("inflates" in f for f in result["findings"]))

    def test_the_same_speed_on_a_shorter_piece_can_leave_the_window(self):
        slow = assess_ambient_test(setup(parallel_length_mm=PARALLEL_LENGTH_MM))
        fast = assess_ambient_test(setup(parallel_length_mm=1.0))
        self.assertTrue(slow["elastic_rate"]["within"])
        self.assertFalse(fast["elastic_rate"]["within"])

    def test_elastic_and_plastic_verdicts_are_kept_separate(self):
        # 3.0e-4 /s: past the plastic window top but 21 MPa/s, also past the
        # elastic top, so both verdicts are computed and reported on their own.
        result = assess_ambient_test(
            setup(crosshead_speed_mm_min=3.0e-4 * PARALLEL_LENGTH_MM * SECONDS_PER_MINUTE)
        )
        self.assertIn("elastic_rate", result)
        self.assertIn("plastic_rate", result)
        self.assertTrue(result["elastic_rate"]["too_fast"])

    def test_an_oversized_load_cell_is_a_finding(self):
        result = assess_ambient_test(setup(load_cell_range_kn=5000.0))
        self.assertTrue(any("smaller cell" in f for f in result["findings"]))

    def test_an_expired_calibration_is_a_finding(self):
        result = assess_ambient_test(setup(calibration_due_date="2026-01-01"))
        self.assertTrue(any("calibration expired" in f for f in result["findings"]))

    def test_a_looser_extensometer_for_a_proof_strength_is_a_finding(self):
        result = assess_ambient_test(setup(extensometer_class=2))
        self.assertTrue(any("looser" in f for f in result["findings"]))

    def test_an_extensometer_gauge_length_mismatch_is_a_finding(self):
        result = assess_ambient_test(setup(extensometer_gauge_length_mm=25.0))
        self.assertTrue(any("reported on" in f for f in result["findings"]))

    def test_peak_load_travels_with_the_result(self):
        result = assess_ambient_test(setup())
        self.assertAlmostEqual(result["peak_load_kn"], 78.54 * 480.0 / 1000.0, places=9)

    def test_missing_spec_key_rejected(self):
        spec = setup()
        del spec["modulus_mpa"]
        with self.assertRaises(ValueError):
            assess_ambient_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_ambient_test("tensile")

    def test_plastic_window_default_is_narrower_at_the_top_than_a_hundredfold(self):
        low, high = PLASTIC_STRAIN_RATE_WINDOW_PER_S
        self.assertGreater(high, low)


if __name__ == "__main__":
    unittest.main()
