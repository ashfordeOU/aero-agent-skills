"""Contract tests for the ECSS-Q-ST-70-21C facility and equipment control logic."""

import unittest

from q7021_equipment_and_facility_control_logic import (
    CONCENTRATION_TOLERANCE_PCT,
    IGNITION_WINDOWS,
    assess_facility,
    blended_oxygen_fraction,
    calibration_review,
    calibration_status,
    ignition_source_check,
    leak_rate_check,
    oxygen_concentration_check,
    parse_iso_date,
)

CALIBRATIONS = {
    "oxygen-analyser": "2026-12-01",
    "flow-controller": "2026-11-15",
    "chamber-thermocouple": "2027-02-01",
}


def spec(**over):
    base = {
        "test_date": "2026-05-20",
        "oxygen_flow_lpm": 3.0,
        "oxygen_purity": 1.0,
        "diluent_flow_lpm": 7.0,
        "diluent_oxygen_impurity": 0.0,
        "target_oxygen_pct": 30.0,
        "calibrations": dict(CALIBRATIONS),
        "flame_height_mm": 20.0,
        "application_time_s": 15.0,
        "leak_rate": 0.2,
        "leak_rate_limit": 1.0,
    }
    base.update(over)
    return base


class BlendTests(unittest.TestCase):
    def test_a_pure_blend_delivers_the_flow_ratio(self):
        self.assertAlmostEqual(blended_oxygen_fraction(3.0, 1.0, 7.0, 0.0), 0.30, places=9)

    def test_an_impure_oxygen_line_lowers_the_delivered_fraction(self):
        self.assertAlmostEqual(blended_oxygen_fraction(3.0, 0.99, 7.0, 0.0),
                               0.297, places=9)

    def test_oxygen_carried_in_the_diluent_raises_the_delivered_fraction(self):
        self.assertAlmostEqual(blended_oxygen_fraction(3.0, 1.0, 7.0, 0.01),
                               0.307, places=9)

    def test_a_pure_oxygen_supply_with_no_diluent_delivers_all_of_it(self):
        self.assertAlmostEqual(blended_oxygen_fraction(5.0, 1.0, 0.0, 0.0), 1.0, places=9)

    def test_no_flow_at_all_rejected(self):
        with self.assertRaises(ValueError):
            blended_oxygen_fraction(0.0, 1.0, 0.0, 0.0)

    def test_a_negative_flow_rejected(self):
        with self.assertRaises(ValueError):
            blended_oxygen_fraction(-1.0, 1.0, 7.0, 0.0)

    def test_a_purity_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            blended_oxygen_fraction(3.0, 1.4, 7.0, 0.0)

    def test_a_non_numeric_flow_rejected(self):
        with self.assertRaises(ValueError):
            blended_oxygen_fraction("3", 1.0, 7.0, 0.0)


class ConcentrationCheckTests(unittest.TestCase):
    def test_an_on_target_blend_is_inside_tolerance(self):
        result = oxygen_concentration_check(0.30, 30.0)
        self.assertTrue(result["inside_tolerance"])
        self.assertAlmostEqual(result["deviation_pct"], 0.0, places=9)

    def test_a_deviation_exactly_on_the_tolerance_is_inside_it(self):
        result = oxygen_concentration_check(0.305, 30.0, 0.5)
        self.assertTrue(result["inside_tolerance"])
        self.assertAlmostEqual(result["deviation_pct"], 0.5, places=9)

    def test_a_deviation_past_the_tolerance_is_outside_it(self):
        self.assertFalse(oxygen_concentration_check(0.31, 30.0, 0.5)["inside_tolerance"])

    def test_the_tolerance_is_two_sided(self):
        self.assertFalse(oxygen_concentration_check(0.29, 30.0, 0.5)["inside_tolerance"])

    def test_a_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            oxygen_concentration_check(1.4, 30.0)

    def test_a_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            oxygen_concentration_check(0.30, 30.0, -0.1)

    def test_the_default_tolerance_is_declared(self):
        self.assertAlmostEqual(CONCENTRATION_TOLERANCE_PCT, 0.5, places=9)


class CalibrationTests(unittest.TestCase):
    def test_a_far_due_date_is_in_date(self):
        self.assertEqual(calibration_status("2026-12-01", "2026-05-20", 30), "in-date")

    def test_a_due_date_before_the_test_is_expired(self):
        self.assertEqual(calibration_status("2026-05-01", "2026-05-20", 30), "expired")

    def test_a_due_date_on_the_test_date_is_still_valid(self):
        self.assertEqual(calibration_status("2026-05-20", "2026-05-20", 30), "due-soon")

    def test_a_due_date_inside_the_warning_window_is_due_soon(self):
        self.assertEqual(calibration_status("2026-06-10", "2026-05-20", 30), "due-soon")

    def test_a_due_date_just_past_the_warning_window_is_in_date(self):
        self.assertEqual(calibration_status("2026-06-20", "2026-05-20", 30), "in-date")

    def test_calibration_is_graded_against_the_test_date_not_today(self):
        self.assertEqual(calibration_status("2026-06-01", "2026-09-01", 30), "expired")

    def test_a_negative_warning_window_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status("2026-12-01", "2026-05-20", -1)

    def test_a_free_text_due_date_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status("December 2026", "2026-05-20", 30)

    def test_the_review_returns_items_in_name_order(self):
        records = calibration_review(CALIBRATIONS, "2026-05-20")
        self.assertEqual([r["item"] for r in records],
                         ["chamber-thermocouple", "flow-controller", "oxygen-analyser"])

    def test_an_empty_calibration_set_rejected(self):
        with self.assertRaises(ValueError):
            calibration_review({}, "2026-05-20")


class IgnitionAndLeakTests(unittest.TestCase):
    def test_a_centred_igniter_is_calibrated(self):
        self.assertTrue(ignition_source_check(20.0, 15.0)["calibrated"])

    def test_a_value_exactly_on_a_window_edge_is_inside_it(self):
        result = ignition_source_check(IGNITION_WINDOWS["flame_height_mm"][1], 15.0)
        self.assertTrue(result["calibrated"])

    def test_a_short_flame_is_a_finding(self):
        result = ignition_source_check(12.0, 15.0)
        self.assertFalse(result["calibrated"])
        self.assertEqual(len(result["findings"]), 1)

    def test_both_parameters_can_fail_at_once(self):
        self.assertEqual(len(ignition_source_check(12.0, 30.0)["findings"]), 2)

    def test_an_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            ignition_source_check(20.0, 15.0,
                                  {"flame_height_mm": (22.0, 18.0),
                                   "application_time_s": (14.0, 16.0)})

    def test_a_missing_window_rejected(self):
        with self.assertRaises(ValueError):
            ignition_source_check(20.0, 15.0, {"flame_height_mm": (18.0, 22.0)})

    def test_a_negative_flame_height_rejected(self):
        with self.assertRaises(ValueError):
            ignition_source_check(-1.0, 15.0)

    def test_a_leak_rate_under_its_limit_passes(self):
        result = leak_rate_check(0.2, 1.0)
        self.assertTrue(result["inside_limit"])
        self.assertAlmostEqual(result["margin"], 0.8, places=9)

    def test_a_leak_rate_exactly_on_its_limit_passes(self):
        result = leak_rate_check(1.0, 1.0)
        self.assertTrue(result["inside_limit"])
        self.assertAlmostEqual(result["margin"], 0.0, places=9)

    def test_a_leak_rate_past_its_limit_fails(self):
        self.assertFalse(leak_rate_check(1.4, 1.0)["inside_limit"])


class AssessFacilityTests(unittest.TestCase):
    def test_a_sound_facility_is_ready(self):
        result = assess_facility(spec())
        self.assertTrue(result["ready"])
        self.assertEqual(result["blocking"], [])

    def test_diluent_impurity_can_push_a_set_point_blend_off_target(self):
        result = assess_facility(spec(diluent_oxygen_impurity=0.02))
        self.assertFalse(result["ready"])
        self.assertTrue(any("oxygen concentration" in f for f in result["blocking"]))

    def test_an_expired_calibration_blocks_the_run(self):
        result = assess_facility(spec(calibrations=dict(CALIBRATIONS,
                                                        **{"oxygen-analyser": "2026-04-01"})))
        self.assertFalse(result["ready"])
        self.assertTrue(any("expired" in f for f in result["blocking"]))

    def test_a_calibration_falling_due_inside_the_campaign_is_advisory(self):
        result = assess_facility(spec(calibrations=dict(CALIBRATIONS,
                                                        **{"flow-controller": "2026-06-05"})))
        self.assertTrue(result["ready"])
        self.assertTrue(result["advisory"])

    def test_an_uncalibrated_igniter_blocks_the_run(self):
        result = assess_facility(spec(flame_height_mm=30.0))
        self.assertFalse(result["ready"])
        self.assertTrue(any("flame height" in f for f in result["blocking"]))

    def test_a_leaking_chamber_blocks_the_run(self):
        result = assess_facility(spec(leak_rate=2.0, leak_rate_limit=1.0))
        self.assertFalse(result["ready"])
        self.assertTrue(any("leak rate" in f for f in result["blocking"]))

    def test_several_blocking_findings_are_all_reported(self):
        result = assess_facility(spec(flame_height_mm=30.0, leak_rate=2.0,
                                      leak_rate_limit=1.0))
        self.assertGreaterEqual(len(result["blocking"]), 2)

    def test_the_delivered_concentration_is_reported_not_the_set_point(self):
        result = assess_facility(spec(oxygen_purity=0.995))
        self.assertLess(result["oxygen"]["delivered_pct"], 30.0)

    def test_missing_key_rejected(self):
        bad = spec()
        del bad["target_oxygen_pct"]
        with self.assertRaises(ValueError):
            assess_facility(bad)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_facility(["test_date", "2026-05-20"])

    def test_parse_iso_date_is_used_for_the_test_date(self):
        self.assertEqual(parse_iso_date("2026-05-20").isoformat(), "2026-05-20")


if __name__ == "__main__":
    unittest.main()
