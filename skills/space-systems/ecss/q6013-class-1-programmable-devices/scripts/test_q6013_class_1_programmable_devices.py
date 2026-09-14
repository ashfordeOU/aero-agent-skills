"""Contract tests for the clause 4.6.4 programmable-device control logic."""

import math
import unittest

from q6013_class_1_programmable_devices_logic import (
    BOLTZMANN_EV_PER_K,
    HOURS_TOLERANCE,
    acceleration_factor,
    assess_programmable_device_control,
    calibration_status,
    post_programming_screen_plan,
    programming_site_category,
    readback_verification,
    retention_bake_hours,
    screen_sample_size,
)


def clean_spec(**overrides):
    """A flash-device programming record that should accept outright."""
    required_bake = retention_bake_hours(87600.0, 25.0, 125.0, 0.6)
    spec = {
        "programming_site": "approved-programming-centre",
        "days_since_calibration": 120.0,
        "calibration_interval_days": 365.0,
        "bits_programmed": 4194304,
        "bits_mismatched": 0,
        "technology": "flash",
        "lot_size": 40,
        "required_retention_hours": 87600.0,
        "use_temp_c": 25.0,
        "bake_temp_c": 125.0,
        "activation_energy_ev": 0.6,
        "bake_hours_performed": required_bake + 24.0,
        "screens_performed": [
            "programming-readback",
            "retention-bake",
            "thermal-cycling",
            "electrical-endpoint",
        ],
        "lot_identifier": "LOT-4471-A",
        "programming_record_id": "PRG-2026-0912",
    }
    spec.update(overrides)
    return spec


class SiteCategoryTests(unittest.TestCase):
    def test_component_manufacturer_is_under_control(self):
        result = programming_site_category("component-manufacturer")
        self.assertTrue(result["under_procurement_control"])

    def test_approved_centre_is_under_control(self):
        result = programming_site_category("  Approved-Programming-Centre ")
        self.assertEqual(result["category"], "approved-programming-centre")
        self.assertTrue(result["under_procurement_control"])

    def test_uncontrolled_facility_is_not_under_control(self):
        result = programming_site_category("uncontrolled-facility")
        self.assertFalse(result["under_procurement_control"])

    def test_unknown_site_rejected(self):
        with self.assertRaises(ValueError):
            programming_site_category("a-bench-in-the-lab")

    def test_empty_site_rejected(self):
        with self.assertRaises(ValueError):
            programming_site_category("   ")


class CalibrationTests(unittest.TestCase):
    def test_in_interval_equipment_is_valid(self):
        status = calibration_status(90.0, 365.0)
        self.assertTrue(status["valid"])
        self.assertAlmostEqual(status["days_remaining"], 275.0, places=9)

    def test_expired_equipment_is_not_valid(self):
        self.assertFalse(calibration_status(400.0, 365.0)["valid"])

    def test_exactly_at_the_interval_is_still_valid(self):
        status = calibration_status(365.0, 365.0)
        self.assertTrue(status["valid"])
        self.assertAlmostEqual(status["days_remaining"], 0.0, places=9)

    def test_negative_elapsed_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(-1.0, 365.0)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(10.0, 0.0)


class ReadbackTests(unittest.TestCase):
    def test_clean_readback_is_verified(self):
        result = readback_verification(1024, 0)
        self.assertTrue(result["verified"])
        self.assertAlmostEqual(result["mismatch_fraction"], 0.0, places=9)

    def test_single_mismatched_bit_fails_the_readback(self):
        result = readback_verification(1024, 1)
        self.assertFalse(result["verified"])
        self.assertAlmostEqual(result["mismatch_fraction"], 1.0 / 1024.0, places=12)

    def test_mismatch_above_programmed_rejected(self):
        with self.assertRaises(ValueError):
            readback_verification(100, 101)

    def test_zero_bits_programmed_rejected(self):
        with self.assertRaises(ValueError):
            readback_verification(0, 0)

    def test_float_bit_count_rejected(self):
        with self.assertRaises(ValueError):
            readback_verification(1024.0, 0)


class AccelerationTests(unittest.TestCase):
    def test_equal_temperatures_give_unity(self):
        self.assertAlmostEqual(acceleration_factor(85.0, 85.0, 0.6), 1.0, places=9)

    def test_factor_matches_the_closed_form(self):
        expected = math.exp(
            (0.6 / BOLTZMANN_EV_PER_K) * (1.0 / 298.15 - 1.0 / 398.15)
        )
        self.assertAlmostEqual(acceleration_factor(25.0, 125.0, 0.6), expected, places=6)

    def test_higher_activation_energy_accelerates_more(self):
        low = acceleration_factor(25.0, 125.0, 0.4)
        high = acceleration_factor(25.0, 125.0, 0.9)
        self.assertGreater(high, low * 10.0)

    def test_bake_shorter_than_the_retention_requirement(self):
        hours = retention_bake_hours(87600.0, 25.0, 125.0, 0.6)
        self.assertLess(hours, 87600.0)
        self.assertGreater(hours, 0.0)

    def test_bake_at_use_temperature_equals_the_requirement(self):
        hours = retention_bake_hours(500.0, 55.0, 55.0, 0.7)
        self.assertAlmostEqual(hours, 500.0, places=9)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(-300.0, 125.0, 0.6)

    def test_non_positive_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(25.0, 125.0, 0.0)

    def test_non_positive_retention_rejected(self):
        with self.assertRaises(ValueError):
            retention_bake_hours(0.0, 25.0, 125.0, 0.6)


class ScreenPlanTests(unittest.TestCase):
    def test_antifuse_plan_has_no_retention_bake(self):
        plan = post_programming_screen_plan("antifuse")
        self.assertIn("thermal-cycling", plan)
        self.assertNotIn("retention-bake", plan)

    def test_flash_plan_carries_both_bake_and_cycling(self):
        plan = post_programming_screen_plan("flash")
        self.assertIn("retention-bake", plan)
        self.assertIn("thermal-cycling", plan)

    def test_readback_leads_every_plan(self):
        for technology in ("antifuse", "fuse-link", "floating-gate-otp", "eeprom", "flash"):
            self.assertEqual(post_programming_screen_plan(technology)[0],
                             "programming-readback")

    def test_radiation_sample_appends_a_screen(self):
        base = post_programming_screen_plan("eeprom")
        with_rad = post_programming_screen_plan("eeprom", True)
        self.assertEqual(len(with_rad), len(base) + 1)
        self.assertEqual(with_rad[-1], "radiation-lot-sample")

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            post_programming_screen_plan("core-rope")

    def test_non_boolean_radiation_flag_rejected(self):
        with self.assertRaises(ValueError):
            post_programming_screen_plan("eeprom", "yes")


class SampleSizeTests(unittest.TestCase):
    def test_non_destructive_screen_covers_the_whole_lot(self):
        self.assertEqual(screen_sample_size(40, "programming-readback"), 40)

    def test_destructive_screen_is_sampled(self):
        self.assertEqual(screen_sample_size(40, "retention-bake"), 4)

    def test_destructive_sample_has_a_floor(self):
        self.assertEqual(screen_sample_size(5, "retention-bake"), 2)

    def test_sample_never_exceeds_a_tiny_lot(self):
        self.assertEqual(screen_sample_size(1, "retention-bake"), 1)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            screen_sample_size(0, "programming-readback")


class AssessmentTests(unittest.TestCase):
    def test_clean_record_accepts(self):
        result = assess_programmable_device_control(clean_spec())
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["findings"], [])

    def test_uncontrolled_site_rejects(self):
        result = assess_programmable_device_control(
            clean_spec(programming_site="uncontrolled-facility")
        )
        self.assertEqual(result["disposition"], "reject")

    def test_mismatched_bit_rejects(self):
        result = assess_programmable_device_control(clean_spec(bits_mismatched=1))
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(any("readback" in f for f in result["findings"]))

    def test_expired_calibration_with_reverification_is_a_deviation(self):
        result = assess_programmable_device_control(
            clean_spec(
                days_since_calibration=400.0,
                reverified_on_calibrated_equipment=True,
            )
        )
        self.assertEqual(result["disposition"], "accept-with-deviation")

    def test_expired_calibration_without_reverification_rejects(self):
        result = assess_programmable_device_control(
            clean_spec(days_since_calibration=400.0)
        )
        self.assertEqual(result["disposition"], "reject")

    def test_missing_screen_rejects(self):
        result = assess_programmable_device_control(
            clean_spec(screens_performed=["programming-readback", "electrical-endpoint"])
        )
        self.assertEqual(result["disposition"], "reject")
        self.assertIn("retention-bake", result["missing_screens"])

    def test_waived_screen_is_a_deviation(self):
        result = assess_programmable_device_control(
            clean_spec(
                screens_performed=[
                    "programming-readback",
                    "retention-bake",
                    "electrical-endpoint",
                ],
                documented_deviations=["thermal-cycling"],
            )
        )
        self.assertEqual(result["disposition"], "accept-with-deviation")

    def test_short_bake_rejects(self):
        spec = clean_spec()
        spec["bake_hours_performed"] = spec["bake_hours_performed"] - 100.0
        result = assess_programmable_device_control(spec)
        self.assertEqual(result["disposition"], "reject")

    def test_bake_exactly_at_the_requirement_accepts(self):
        required = retention_bake_hours(87600.0, 25.0, 125.0, 0.6)
        result = assess_programmable_device_control(
            clean_spec(bake_hours_performed=required)
        )
        self.assertAlmostEqual(result["required_bake_hours"], required, places=9)
        self.assertEqual(result["disposition"], "accept")

    def test_missing_traceability_rejects(self):
        spec = clean_spec()
        del spec["lot_identifier"]
        result = assess_programmable_device_control(spec)
        self.assertEqual(result["disposition"], "reject")
        self.assertTrue(any("traceability" in f for f in result["findings"]))

    def test_sample_map_covers_every_planned_screen(self):
        result = assess_programmable_device_control(clean_spec())
        self.assertEqual(set(result["screen_samples"]), set(result["screen_plan"]))

    def test_missing_key_rejected(self):
        spec = clean_spec()
        del spec["technology"]
        with self.assertRaises(ValueError):
            assess_programmable_device_control(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_programmable_device_control(["programming_site"])

    def test_non_sequence_screens_rejected(self):
        with self.assertRaises(ValueError):
            assess_programmable_device_control(clean_spec(screens_performed="all"))

    def test_hours_tolerance_is_tight(self):
        self.assertLessEqual(HOURS_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
