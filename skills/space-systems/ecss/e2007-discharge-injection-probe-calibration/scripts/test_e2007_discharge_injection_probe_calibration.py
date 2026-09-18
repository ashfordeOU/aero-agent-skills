"""Contract tests for the clause 5.4.13.3 injection-probe calibration logic."""

import unittest

from e2007_discharge_injection_probe_calibration_logic import (
    DEFAULT_MAX_RELATIVE_SPREAD,
    DEFAULT_MAX_TERMINATION_REFLECTION,
    LOSS_TOLERANCE_DB,
    MIN_CALIBRATION_PULSES,
    assess_calibration,
    drive_setting_v,
    injection_loss_db,
    monitor_bandwidth_hz,
    pulse_statistics,
    termination_reflection,
    validate_fixture,
    validity_remaining_days,
)


def make_fixture(**overrides):
    """Return a matched 50 ohm calibration fixture."""
    fixture = {
        "impedance_ohm": 50.0,
        "source_termination_ohm": 50.0,
        "load_termination_ohm": 50.0,
    }
    fixture.update(overrides)
    return fixture


def make_spec(**overrides):
    """Return a ready calibration arrangement."""
    spec = {
        "fixture": make_fixture(),
        "calibration_drive_v": 500.0,
        "measured_currents_a": [5.0, 5.1, 4.95, 5.02],
        "target_current_a": 10.0,
        "generator_max_v": 2000.0,
        "pulse_rise_time_s": 5.0e-9,
        "monitor_bandwidth_hz": 2.5e8,
        "calibration_age_days": 120,
        "calibration_interval_days": 365,
    }
    spec.update(overrides)
    return spec


class TerminationTests(unittest.TestCase):
    def test_matched_termination_reflects_nothing(self):
        self.assertAlmostEqual(termination_reflection(50.0, 50.0), 0.0, places=12)

    def test_open_side_termination_reflects_a_known_fraction(self):
        self.assertAlmostEqual(termination_reflection(75.0, 50.0), 0.2, places=12)

    def test_reflection_magnitude_is_sign_free(self):
        self.assertAlmostEqual(
            termination_reflection(25.0, 50.0),
            termination_reflection(100.0, 50.0),
            places=12,
        )

    def test_zero_termination_rejected(self):
        with self.assertRaises(ValueError):
            termination_reflection(0.0, 50.0)

    def test_non_numeric_impedance_rejected(self):
        with self.assertRaises(ValueError):
            termination_reflection(50.0, "50")


class FixtureTests(unittest.TestCase):
    def test_matched_fixture_is_clean(self):
        graded = validate_fixture(make_fixture())
        self.assertTrue(graded["matched"])
        self.assertEqual(graded["findings"], [])
        self.assertAlmostEqual(graded["impedance_ohm"], 50.0, places=12)

    def test_default_reflection_limit_is_the_published_one(self):
        graded = validate_fixture(make_fixture())
        self.assertAlmostEqual(
            graded["max_termination_reflection"], DEFAULT_MAX_TERMINATION_REFLECTION, places=12
        )

    def test_mismatched_load_termination_is_a_finding(self):
        graded = validate_fixture(make_fixture(load_termination_ohm=75.0))
        self.assertFalse(graded["matched"])
        self.assertEqual(len(graded["findings"]), 1)
        self.assertIn("load termination", graded["findings"][0])

    def test_both_terminations_can_fail_together(self):
        graded = validate_fixture(
            make_fixture(source_termination_ohm=75.0, load_termination_ohm=25.0)
        )
        self.assertEqual(len(graded["findings"]), 2)

    def test_slightly_off_termination_inside_the_limit_passes(self):
        graded = validate_fixture(make_fixture(load_termination_ohm=52.0))
        self.assertTrue(graded["matched"])

    def test_missing_fixture_key_rejected(self):
        fixture = make_fixture()
        del fixture["source_termination_ohm"]
        with self.assertRaises(ValueError):
            validate_fixture(fixture)

    def test_non_mapping_fixture_rejected(self):
        with self.assertRaises(ValueError):
            validate_fixture([50.0, 50.0, 50.0])

    def test_out_of_range_reflection_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_fixture(make_fixture(max_termination_reflection=1.5))


class PulseStatisticsTests(unittest.TestCase):
    def test_mean_of_identical_pulses_is_that_value(self):
        stats = pulse_statistics([4.0, 4.0, 4.0, 4.0])
        self.assertAlmostEqual(stats["mean_a"], 4.0, places=12)
        self.assertAlmostEqual(stats["relative_spread"], 0.0, places=12)
        self.assertTrue(stats["repeatable"])

    def test_extremes_are_reported(self):
        stats = pulse_statistics([4.0, 5.0, 6.0])
        self.assertAlmostEqual(stats["min_a"], 4.0, places=12)
        self.assertAlmostEqual(stats["max_a"], 6.0, places=12)
        self.assertAlmostEqual(stats["mean_a"], 5.0, places=12)

    def test_relative_spread_is_the_range_over_the_mean(self):
        stats = pulse_statistics([4.0, 5.0, 6.0])
        self.assertAlmostEqual(stats["relative_spread"], 0.4, places=12)
        self.assertFalse(stats["repeatable"])

    def test_default_spread_limit_is_the_published_one(self):
        stats = pulse_statistics([5.0, 5.0, 5.0])
        self.assertAlmostEqual(
            stats["max_relative_spread"], DEFAULT_MAX_RELATIVE_SPREAD, places=12
        )

    def test_too_few_pulses_rejected(self):
        with self.assertRaises(ValueError):
            pulse_statistics([5.0] * (MIN_CALIBRATION_PULSES - 1))

    def test_zero_current_pulse_rejected(self):
        with self.assertRaises(ValueError):
            pulse_statistics([5.0, 0.0, 5.0])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            pulse_statistics(5.0)

    def test_out_of_range_spread_limit_rejected(self):
        with self.assertRaises(ValueError):
            pulse_statistics([5.0, 5.0, 5.0], max_relative_spread=0.0)


class InjectionLossTests(unittest.TestCase):
    def test_unity_transfer_is_zero_db(self):
        self.assertAlmostEqual(injection_loss_db(500.0, 10.0, 50.0), 0.0, places=9)

    def test_halved_transfer_is_six_db(self):
        self.assertAlmostEqual(injection_loss_db(500.0, 5.0, 50.0), 6.020599913, places=6)

    def test_loss_rises_as_the_fixture_current_falls(self):
        low = injection_loss_db(500.0, 10.0, 50.0)
        high = injection_loss_db(500.0, 1.0, 50.0)
        self.assertAlmostEqual(high - low, 20.0, places=9)

    def test_zero_measured_current_rejected(self):
        with self.assertRaises(ValueError):
            injection_loss_db(500.0, 0.0, 50.0)

    def test_negative_drive_rejected(self):
        with self.assertRaises(ValueError):
            injection_loss_db(-500.0, 5.0, 50.0)


class DriveSettingTests(unittest.TestCase):
    def test_lossless_probe_needs_current_times_impedance(self):
        self.assertAlmostEqual(drive_setting_v(10.0, 0.0, 50.0), 500.0, places=9)

    def test_twenty_db_loss_demands_ten_times_the_drive(self):
        self.assertAlmostEqual(drive_setting_v(10.0, 20.0, 50.0), 5000.0, places=6)

    def test_setting_round_trips_the_measured_loss(self):
        loss = injection_loss_db(500.0, 5.0, 50.0)
        self.assertAlmostEqual(drive_setting_v(5.0, loss, 50.0), 500.0, places=6)

    def test_setting_scales_with_the_target_current(self):
        single = drive_setting_v(5.0, 6.0, 50.0)
        double = drive_setting_v(10.0, 6.0, 50.0)
        self.assertAlmostEqual(double / single, 2.0, places=9)

    def test_non_finite_loss_rejected(self):
        with self.assertRaises(ValueError):
            drive_setting_v(10.0, float("nan"), 50.0)

    def test_zero_target_current_rejected(self):
        with self.assertRaises(ValueError):
            drive_setting_v(0.0, 6.0, 50.0)


class BandwidthAndValidityTests(unittest.TestCase):
    def test_monitor_bandwidth_follows_the_edge(self):
        self.assertAlmostEqual(monitor_bandwidth_hz(3.5e-9) / 1.0e8, 1.0, places=9)

    def test_zero_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            monitor_bandwidth_hz(0.0)

    def test_fresh_calibration_has_the_whole_interval_left(self):
        self.assertEqual(validity_remaining_days(0, 365), 365)

    def test_expired_calibration_is_negative(self):
        self.assertEqual(validity_remaining_days(400, 365), -35)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            validity_remaining_days(-1, 365)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            validity_remaining_days(10, 0)

    def test_boolean_age_rejected(self):
        with self.assertRaises(ValueError):
            validity_remaining_days(True, 365)


class AssessCalibrationTests(unittest.TestCase):
    def test_ready_arrangement_has_no_finding(self):
        result = assess_calibration(make_spec())
        self.assertTrue(result["arrangement_ready"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["limitations"], [])

    def test_drive_setting_reproduces_the_target_current(self):
        result = assess_calibration(make_spec())
        mean = result["pulse_statistics"]["mean_a"]
        implied = drive_setting_v(mean, result["injection_loss_db"], 50.0)
        self.assertAlmostEqual(implied, 500.0, places=6)
        self.assertAlmostEqual(
            result["drive_setting_v"] / implied, 10.0 / mean, places=9
        )

    def test_unmatched_fixture_blocks_the_arrangement(self):
        result = assess_calibration(
            make_spec(fixture=make_fixture(load_termination_ohm=100.0))
        )
        self.assertFalse(result["arrangement_ready"])
        self.assertIn("load termination", result["findings"][0])

    def test_scattered_pulses_block_the_arrangement(self):
        result = assess_calibration(make_spec(measured_currents_a=[3.0, 5.0, 7.0]))
        self.assertFalse(result["arrangement_ready"])
        self.assertFalse(result["pulse_statistics"]["repeatable"])

    def test_target_beyond_the_generator_is_a_finding(self):
        result = assess_calibration(make_spec(generator_max_v=600.0))
        self.assertFalse(result["arrangement_ready"])
        self.assertIn("exceeds", result["findings"][0])

    def test_slow_monitor_is_a_finding(self):
        result = assess_calibration(make_spec(monitor_bandwidth_hz=1.0e7))
        self.assertFalse(result["arrangement_ready"])
        self.assertIn("cannot resolve", result["findings"][0])

    def test_expired_fixture_calibration_is_a_finding(self):
        result = assess_calibration(make_spec(calibration_age_days=400))
        self.assertFalse(result["arrangement_ready"])
        self.assertEqual(result["validity_remaining_days"], -35)

    def test_nearly_expired_calibration_is_a_limitation(self):
        result = assess_calibration(make_spec(calibration_age_days=350))
        self.assertTrue(result["arrangement_ready"])
        self.assertIn("days left", result["limitations"][0])

    def test_drive_near_the_top_of_the_range_is_a_limitation(self):
        result = assess_calibration(make_spec(generator_max_v=1050.0))
        self.assertTrue(result["arrangement_ready"])
        self.assertIn("generator range", result["limitations"][-1])

    def test_loss_tolerance_is_representation_sized(self):
        self.assertLess(LOSS_TOLERANCE_DB, 1.0e-6)

    def test_missing_key_rejected(self):
        spec = make_spec()
        del spec["target_current_a"]
        with self.assertRaises(ValueError):
            assess_calibration(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_calibration(["fixture"])

    def test_required_bandwidth_is_reported_alongside_the_declared_one(self):
        result = assess_calibration(make_spec())
        self.assertAlmostEqual(result["required_monitor_bandwidth_hz"] / 7.0e7, 1.0, places=9)
        self.assertAlmostEqual(result["declared_monitor_bandwidth_hz"] / 2.5e8, 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
