#!/usr/bin/env python3
"""Gate 3 contract test for e2001-test-bed-validation (offline, stdlib)."""

import unittest

from e2001_test_bed_validation_logic import (
    DB_ABS_TOL,
    REL_TOL,
    REQUIRED_STEP_ORDER,
    STEP_ONE,
    STEP_TWO,
    check_bed_headroom,
    check_channel_agreement,
    check_step_order,
    check_validation_currency,
    evaluate_bed_validation,
    power_ratio_db,
    reference_deviation_db,
    scan_sweep_for_events,
    validate_step_one,
    validate_step_two,
)

MAX_APPLIED = 100.0


def quiet_sweep():
    return [
        {"power_w": 25.0, "channel": "forward-reverse-nulling", "event_detected": False},
        {"power_w": 50.0, "channel": "forward-reverse-nulling", "event_detected": False},
        {"power_w": 100.0, "channel": "forward-reverse-nulling", "event_detected": False},
        {"power_w": 25.0, "channel": "electron-probe", "event_detected": False},
        {"power_w": 50.0, "channel": "electron-probe", "event_detected": False},
        {"power_w": 100.0, "channel": "electron-probe", "event_detected": False},
    ]


def good_record(**overrides):
    record = {
        "steps": [STEP_ONE, STEP_TWO],
        "sweep_points": quiet_sweep(),
        "max_applied_power_w": MAX_APPLIED,
        "bed_onset_power_w": 400.0,
        "required_headroom_db": 3.0,
        "measured_onset_w": 52.0,
        "certified_onset_w": 50.0,
        "tolerance_db": 1.0,
        "registered_channels": ["forward-reverse-nulling", "electron-probe"],
        "required_channels": ["forward-reverse-nulling", "electron-probe"],
        "validation_date": "2026-05-01",
        "run_date": "2026-05-20",
        "validity_days": 90,
        "reconfiguration_dates": [],
    }
    record.update(overrides)
    return record


class TestPowerRatio(unittest.TestCase):
    def test_doubling_is_about_three_db(self):
        self.assertAlmostEqual(power_ratio_db(200.0, 100.0), 3.0103, places=4)

    def test_equal_powers_give_zero_db(self):
        self.assertAlmostEqual(power_ratio_db(75.0, 75.0), 0.0, places=12)

    def test_halving_is_negative(self):
        self.assertAlmostEqual(power_ratio_db(50.0, 100.0), -3.0103, places=4)

    def test_decade_is_ten_db(self):
        self.assertAlmostEqual(power_ratio_db(1000.0, 100.0), 10.0, places=9)

    def test_zero_power_raises(self):
        with self.assertRaises(ValueError):
            power_ratio_db(0.0, 100.0)

    def test_negative_reference_raises(self):
        with self.assertRaises(ValueError):
            power_ratio_db(100.0, -1.0)

    def test_boolean_power_raises(self):
        with self.assertRaises(ValueError):
            power_ratio_db(True, 100.0)

    def test_non_finite_power_raises(self):
        with self.assertRaises(ValueError):
            power_ratio_db(float("inf"), 100.0)


class TestStepOrder(unittest.TestCase):
    def test_correct_order_is_accepted(self):
        self.assertEqual(check_step_order([STEP_ONE, STEP_TWO]), list(REQUIRED_STEP_ORDER))

    def test_reversed_order_raises(self):
        with self.assertRaises(ValueError):
            check_step_order([STEP_TWO, STEP_ONE])

    def test_missing_step_raises(self):
        with self.assertRaises(ValueError):
            check_step_order([STEP_ONE])

    def test_repeated_step_raises(self):
        with self.assertRaises(ValueError):
            check_step_order([STEP_ONE, STEP_ONE])

    def test_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            check_step_order([STEP_ONE, "coffee-break"])

    def test_blank_step_raises(self):
        with self.assertRaises(ValueError):
            check_step_order([STEP_ONE, "  "])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            check_step_order(STEP_ONE)


class TestSweepScan(unittest.TestCase):
    def test_quiet_sweep_fires_nothing(self):
        scan = scan_sweep_for_events(quiet_sweep(), MAX_APPLIED)
        self.assertEqual(scan["fired"], [])
        self.assertTrue(scan["reached_max_applied_power"])

    def test_event_below_the_ceiling_is_captured(self):
        points = quiet_sweep()
        points[1]["event_detected"] = True
        scan = scan_sweep_for_events(points, MAX_APPLIED)
        self.assertEqual(len(scan["fired"]), 1)
        self.assertAlmostEqual(scan["fired"][0]["power_w"], 50.0, places=9)

    def test_event_above_the_ceiling_is_ignored(self):
        points = quiet_sweep() + [
            {"power_w": 250.0, "channel": "electron-probe", "event_detected": True}
        ]
        scan = scan_sweep_for_events(points, MAX_APPLIED)
        self.assertEqual(scan["fired"], [])

    def test_sweep_stopping_early_is_not_covered(self):
        points = [p for p in quiet_sweep() if p["power_w"] < 100.0]
        scan = scan_sweep_for_events(points, MAX_APPLIED)
        self.assertFalse(scan["reached_max_applied_power"])
        self.assertAlmostEqual(scan["highest_swept_power_w"], 50.0, places=9)

    def test_empty_sweep_raises(self):
        with self.assertRaises(ValueError):
            scan_sweep_for_events([], MAX_APPLIED)

    def test_sweep_point_without_channel_raises(self):
        with self.assertRaises(ValueError):
            scan_sweep_for_events(
                [{"power_w": 10.0, "channel": "", "event_detected": False}], MAX_APPLIED
            )

    def test_sweep_point_with_non_boolean_flag_raises(self):
        with self.assertRaises(ValueError):
            scan_sweep_for_events(
                [{"power_w": 10.0, "channel": "probe", "event_detected": "no"}],
                MAX_APPLIED,
            )

    def test_sweep_point_with_zero_power_raises(self):
        with self.assertRaises(ValueError):
            scan_sweep_for_events(
                [{"power_w": 0.0, "channel": "probe", "event_detected": False}],
                MAX_APPLIED,
            )


class TestBedHeadroom(unittest.TestCase):
    def test_generous_headroom_is_compliant(self):
        result = check_bed_headroom(400.0, 100.0, 3.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["headroom_db"], 6.0206, places=4)

    def test_insufficient_headroom_is_a_finding(self):
        result = check_bed_headroom(120.0, 100.0, 3.0)
        self.assertFalse(result["compliant"])
        self.assertIn("below the required", result["findings"][0])

    def test_headroom_landing_ulps_under_the_requirement_still_passes(self):
        # The log-domain round trip of an exactly-3 dB ratio lands a few ULPs
        # below 3.0; the bed is physically at the requirement.
        onset = 10.0 * (10.0 ** 0.3)
        actual = power_ratio_db(onset, 10.0)
        self.assertLess(actual, 3.0)
        self.assertTrue(check_bed_headroom(onset, 10.0, 3.0)["compliant"])

    def test_zero_required_headroom_is_met_by_equal_powers(self):
        result = check_bed_headroom(100.0, 100.0, 0.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["headroom_db"], 0.0, places=12)

    def test_negative_required_headroom_raises(self):
        with self.assertRaises(ValueError):
            check_bed_headroom(400.0, 100.0, -1.0)

    def test_non_numeric_required_headroom_raises(self):
        with self.assertRaises(ValueError):
            check_bed_headroom(400.0, 100.0, "3 dB")


class TestStepOne(unittest.TestCase):
    def test_quiet_bed_with_headroom_is_compliant(self):
        result = validate_step_one(quiet_sweep(), MAX_APPLIED, 400.0, 3.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["step"], STEP_ONE)

    def test_event_in_the_bed_names_the_channel(self):
        points = quiet_sweep()
        points[4]["event_detected"] = True
        result = validate_step_one(points, MAX_APPLIED, 400.0, 3.0)
        self.assertFalse(result["compliant"])
        self.assertIn("electron-probe", result["findings"][0])

    def test_unestablished_bed_onset_is_a_finding(self):
        result = validate_step_one(quiet_sweep(), MAX_APPLIED, None, 3.0)
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["headroom"])
        self.assertTrue(any("headroom cannot be shown" in f for f in result["findings"]))

    def test_truncated_sweep_is_a_finding(self):
        points = [p for p in quiet_sweep() if p["power_w"] < 100.0]
        result = validate_step_one(points, MAX_APPLIED, 400.0, 3.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("never reached" in f for f in result["findings"]))


class TestStepTwo(unittest.TestCase):
    def test_onset_inside_the_band_is_compliant(self):
        result = validate_step_two(
            52.0, 50.0, 1.0, ["a", "b"], ["a", "b"]
        )
        self.assertTrue(result["compliant"])
        self.assertTrue(result["inside_band"])

    def test_onset_outside_the_band_reports_late_detection(self):
        result = validate_step_two(80.0, 50.0, 1.0, ["a"], ["a"])
        self.assertFalse(result["compliant"])
        self.assertIn("late detection", result["findings"][0])

    def test_onset_outside_the_band_reports_early_detection(self):
        result = validate_step_two(30.0, 50.0, 1.0, ["a"], ["a"])
        self.assertFalse(result["compliant"])
        self.assertIn("early detection", result["findings"][0])

    def test_deviation_sign_follows_the_measured_onset(self):
        self.assertGreater(reference_deviation_db(60.0, 50.0), 0.0)
        self.assertLess(reference_deviation_db(40.0, 50.0), 0.0)

    def test_band_edge_landing_ulps_outside_is_still_inside(self):
        # An exactly 1.5 dB offset round-trips to 1.5000000000000002 dB.
        measured = 75.0 * (10.0 ** 0.15)
        self.assertGreater(abs(reference_deviation_db(measured, 75.0)), 1.5)
        result = validate_step_two(measured, 75.0, 1.5, ["a"], ["a"])
        self.assertTrue(result["inside_band"])
        self.assertTrue(result["compliant"])

    def test_silent_channel_is_a_finding_even_inside_the_band(self):
        result = validate_step_two(52.0, 50.0, 1.0, ["a"], ["a", "b"])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["channels"]["silent_channels"], ["b"])

    def test_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_step_two(52.0, 50.0, 0.0, ["a"], ["a"])

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_step_two(52.0, 50.0, -1.0, ["a"], ["a"])

    def test_zero_certified_onset_raises(self):
        with self.assertRaises(ValueError):
            validate_step_two(52.0, 0.0, 1.0, ["a"], ["a"])


class TestChannelAgreement(unittest.TestCase):
    def test_all_channels_registered_is_compliant(self):
        result = check_channel_agreement(["a", "b"], ["a", "b"])
        self.assertTrue(result["compliant"])

    def test_extra_registered_channel_is_harmless(self):
        result = check_channel_agreement(["a", "b", "c"], ["a", "b"])
        self.assertTrue(result["compliant"])

    def test_each_silent_channel_gets_its_own_finding(self):
        result = check_channel_agreement([], ["a", "b"])
        self.assertEqual(len(result["findings"]), 2)

    def test_empty_required_channels_raises(self):
        with self.assertRaises(ValueError):
            check_channel_agreement(["a"], [])

    def test_non_sequence_registered_channels_raises(self):
        with self.assertRaises(ValueError):
            check_channel_agreement(None, ["a"])


class TestValidationCurrency(unittest.TestCase):
    def test_recent_validation_is_current(self):
        result = check_validation_currency("2026-05-01", "2026-05-20", 90)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["age_days"], 19)

    def test_validation_on_the_window_edge_is_current(self):
        result = check_validation_currency("2026-01-01", "2026-04-01", 90)
        self.assertEqual(result["age_days"], 90)
        self.assertTrue(result["compliant"])

    def test_validation_past_the_window_is_a_finding(self):
        result = check_validation_currency("2026-01-01", "2026-04-02", 90)
        self.assertFalse(result["compliant"])
        self.assertIn("validity window", result["findings"][0])

    def test_reconfiguration_after_validation_supersedes_it(self):
        result = check_validation_currency(
            "2026-05-01", "2026-05-20", 90, ["2026-05-10"]
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["superseding_changes"], ["2026-05-10"])

    def test_reconfiguration_before_validation_is_harmless(self):
        result = check_validation_currency(
            "2026-05-01", "2026-05-20", 90, ["2026-04-10"]
        )
        self.assertTrue(result["compliant"])

    def test_run_before_validation_raises(self):
        with self.assertRaises(ValueError):
            check_validation_currency("2026-05-20", "2026-05-01", 90)

    def test_zero_validity_days_raises(self):
        with self.assertRaises(ValueError):
            check_validation_currency("2026-05-01", "2026-05-20", 0)

    def test_boolean_validity_days_raises(self):
        with self.assertRaises(ValueError):
            check_validation_currency("2026-05-01", "2026-05-20", True)

    def test_malformed_reconfiguration_date_raises(self):
        with self.assertRaises(ValueError):
            check_validation_currency("2026-05-01", "2026-05-20", 90, ["10-05-2026"])


class TestAggregate(unittest.TestCase):
    def test_good_record_is_validated(self):
        result = evaluate_bed_validation(good_record())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "BED-VALIDATED")

    def test_step_order_is_reported(self):
        result = evaluate_bed_validation(good_record())
        self.assertEqual(result["step_order"], list(REQUIRED_STEP_ORDER))

    def test_bed_event_makes_the_bed_not_validated(self):
        points = quiet_sweep()
        points[0]["event_detected"] = True
        result = evaluate_bed_validation(good_record(sweep_points=points))
        self.assertEqual(result["verdict"], "BED-NOT-VALIDATED")
        self.assertTrue(any(f.startswith("step-one:") for f in result["findings"]))

    def test_blind_channel_is_reported_under_step_two(self):
        record = good_record(registered_channels=["forward-reverse-nulling"])
        result = evaluate_bed_validation(record)
        self.assertTrue(any(f.startswith("step-two:") for f in result["findings"]))

    def test_stale_validation_is_reported_under_currency(self):
        record = good_record(validation_date="2025-01-01")
        result = evaluate_bed_validation(record)
        self.assertTrue(any(f.startswith("currency:") for f in result["findings"]))

    def test_reversed_steps_raise_before_scoring(self):
        with self.assertRaises(ValueError):
            evaluate_bed_validation(good_record(steps=[STEP_TWO, STEP_ONE]))

    def test_missing_key_raises(self):
        record = good_record()
        del record["tolerance_db"]
        with self.assertRaises(ValueError):
            evaluate_bed_validation(record)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            evaluate_bed_validation([STEP_ONE, STEP_TWO])

    def test_tolerances_are_small_and_positive(self):
        self.assertLess(REL_TOL, 1e-6)
        self.assertGreater(REL_TOL, 0.0)
        self.assertLess(DB_ABS_TOL, 1e-6)
        self.assertGreater(DB_ABS_TOL, 0.0)


if __name__ == "__main__":
    unittest.main()
