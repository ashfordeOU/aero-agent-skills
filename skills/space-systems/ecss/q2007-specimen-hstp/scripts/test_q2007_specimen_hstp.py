#!/usr/bin/env python3
"""Gate 3 contract test for q2007-specimen-hstp.

stdlib unittest, offline, deterministic. Run:
    python3 test_q2007_specimen_hstp.py
"""

import unittest

from q2007_specimen_hstp_logic import (
    CLEANLINESS,
    HSTP_COMPLIANT,
    HSTP_DEFICIENT,
    HUMIDITY,
    TEMPERATURE,
    assess_hstp,
    environment_excursions,
    handling_findings,
    preservation_expiry_day,
    preservation_is_valid,
    sample_excursions,
    time_outside_limits_s,
    transport_findings,
    validate_limits,
    validate_storage_log,
)

LIMITS = {
    "temperature_min_c": 15.0,
    "temperature_max_c": 25.0,
    "humidity_max_pct": 55.0,
    "cleanliness_class_max": 8.0,
    "max_shock_g": 3.0,
    "max_tilt_deg": 15.0,
    "shelf_life_days": 180.0,
}


def good_log():
    return [
        {"time_s": 0.0, TEMPERATURE: 20.0, HUMIDITY: 40.0, CLEANLINESS: 7.0},
        {"time_s": 3600.0, TEMPERATURE: 21.0, HUMIDITY: 42.0, CLEANLINESS: 7.0},
        {"time_s": 7200.0, TEMPERATURE: 20.5, HUMIDITY: 41.0, CLEANLINESS: 7.0},
    ]


def good_move(**over):
    record = {
        "peak_shock_g": 1.2,
        "peak_tilt_deg": 4.0,
        "monitors_fitted": True,
        "seal_intact": True,
    }
    record.update(over)
    return record


def good_item(**over):
    record = {
        "mass_kg": 12.0,
        "lifting_equipment_used": False,
        "lifting_certificate_valid": False,
        "declared_lift_points_used": True,
        "electrostatic_sensitive": True,
        "electrostatic_protection_applied": True,
    }
    record.update(over)
    return record


def good_plan(**over):
    record = {
        "limits": dict(LIMITS),
        "storage_log": good_log(),
        "preservation_applied_day": 10.0,
        "planned_use_day": 40.0,
        "internal_moves": [good_move()],
        "item": good_item(),
    }
    record.update(over)
    return record


class TestLimitValidation(unittest.TestCase):
    def test_good_limits_normalize(self):
        bounds = validate_limits(LIMITS)
        self.assertAlmostEqual(bounds["humidity_max_pct"], 55.0, places=9)

    def test_inverted_temperature_band_is_rejected(self):
        bad = dict(LIMITS, temperature_min_c=30.0)
        with self.assertRaises(ValueError):
            validate_limits(bad)

    def test_humidity_over_one_hundred_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits(dict(LIMITS, humidity_max_pct=120.0))

    def test_zero_shelf_life_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits(dict(LIMITS, shelf_life_days=0.0))

    def test_negative_tilt_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits(dict(LIMITS, max_tilt_deg=-1.0))


class TestStorageLog(unittest.TestCase):
    def test_good_log_normalizes_in_order(self):
        log = validate_storage_log(good_log())
        self.assertEqual([s["time_s"] for s in log], [0.0, 3600.0, 7200.0])

    def test_out_of_order_readings_are_rejected(self):
        log = good_log()
        log[2]["time_s"] = 1800.0
        with self.assertRaises(ValueError):
            validate_storage_log(log)

    def test_an_empty_log_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_storage_log([])

    def test_a_reading_missing_humidity_is_rejected(self):
        log = good_log()
        del log[1][HUMIDITY]
        with self.assertRaises(ValueError):
            validate_storage_log(log)


class TestExcursions(unittest.TestCase):
    def test_a_reading_inside_every_limit_is_clean(self):
        self.assertEqual(sample_excursions(good_log()[0], LIMITS), [])

    def test_a_reading_exactly_on_the_temperature_ceiling_is_clean(self):
        sample = dict(good_log()[0])
        sample[TEMPERATURE] = 25.0
        self.assertEqual(sample_excursions(sample, LIMITS), [])

    def test_a_reading_exactly_on_the_humidity_ceiling_is_clean(self):
        sample = dict(good_log()[0])
        sample[HUMIDITY] = 55.0
        self.assertEqual(sample_excursions(sample, LIMITS), [])

    def test_a_cold_reading_is_a_temperature_excursion(self):
        sample = dict(good_log()[0])
        sample[TEMPERATURE] = 10.0
        self.assertEqual(sample_excursions(sample, LIMITS), [TEMPERATURE])

    def test_a_damp_dirty_reading_reports_both_limits(self):
        sample = dict(good_log()[0])
        sample[HUMIDITY] = 70.0
        sample[CLEANLINESS] = 9.0
        self.assertEqual(sample_excursions(sample, LIMITS), [HUMIDITY, CLEANLINESS])

    def test_a_clean_log_has_no_excursions(self):
        self.assertEqual(environment_excursions(good_log(), LIMITS), [])

    def test_an_excursion_is_reported_with_its_time(self):
        log = good_log()
        log[1][HUMIDITY] = 80.0
        found = environment_excursions(log, LIMITS)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["time_s"], 3600.0, places=9)


class TestTimeOutside(unittest.TestCase):
    def test_a_clean_log_spends_no_time_outside(self):
        self.assertAlmostEqual(time_outside_limits_s(good_log(), LIMITS), 0.0, places=9)

    def test_one_bad_reading_counts_the_interval_that_follows_it(self):
        log = good_log()
        log[0][HUMIDITY] = 80.0
        self.assertAlmostEqual(
            time_outside_limits_s(log, LIMITS), 3600.0, places=9
        )

    def test_two_consecutive_bad_readings_count_both_intervals(self):
        log = good_log()
        log[0][HUMIDITY] = 80.0
        log[1][HUMIDITY] = 80.0
        self.assertAlmostEqual(
            time_outside_limits_s(log, LIMITS), 7200.0, places=9
        )

    def test_a_single_reading_log_has_no_duration(self):
        self.assertAlmostEqual(
            time_outside_limits_s(good_log()[:1], LIMITS), 0.0, places=9
        )


class TestPreservation(unittest.TestCase):
    def test_expiry_runs_from_the_day_it_was_applied(self):
        self.assertAlmostEqual(preservation_expiry_day(10.0, 180.0), 190.0, places=9)

    def test_use_inside_the_shelf_life_is_valid(self):
        self.assertTrue(preservation_is_valid(40.0, 10.0, 180.0))

    def test_use_exactly_on_the_expiry_day_is_valid(self):
        self.assertTrue(preservation_is_valid(190.0, 10.0, 180.0))

    def test_use_after_the_expiry_day_is_not_valid(self):
        self.assertFalse(preservation_is_valid(200.0, 10.0, 180.0))

    def test_use_before_the_preservation_was_applied_is_rejected(self):
        with self.assertRaises(ValueError):
            preservation_is_valid(5.0, 10.0, 180.0)


class TestTransport(unittest.TestCase):
    def test_a_monitored_gentle_move_has_no_findings(self):
        self.assertEqual(transport_findings(good_move(), LIMITS), [])

    def test_a_move_exactly_on_the_shock_limit_has_no_findings(self):
        self.assertEqual(transport_findings(good_move(peak_shock_g=3.0), LIMITS), [])

    def test_a_move_over_the_shock_limit_is_a_finding(self):
        self.assertEqual(len(transport_findings(good_move(peak_shock_g=6.0), LIMITS)), 1)

    def test_an_unmonitored_move_is_a_finding_on_its_own(self):
        self.assertEqual(
            len(transport_findings(good_move(monitors_fitted=False), LIMITS)), 1
        )

    def test_a_broken_seal_is_a_finding(self):
        self.assertEqual(
            len(transport_findings(good_move(seal_intact=False), LIMITS)), 1
        )

    def test_a_negative_shock_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            transport_findings(good_move(peak_shock_g=-1.0), LIMITS)


class TestHandling(unittest.TestCase):
    def test_a_correctly_handled_item_has_no_findings(self):
        self.assertEqual(handling_findings(good_item()), [])

    def test_a_heavy_item_lifted_by_hand_is_a_finding(self):
        self.assertEqual(len(handling_findings(good_item(mass_kg=40.0))), 1)

    def test_an_item_exactly_on_the_hand_limit_is_not_a_finding(self):
        self.assertEqual(handling_findings(good_item(mass_kg=25.0)), [])

    def test_lifting_equipment_without_a_certificate_is_a_finding(self):
        self.assertEqual(
            len(handling_findings(good_item(mass_kg=40.0, lifting_equipment_used=True))),
            1,
        )

    def test_ignoring_the_declared_lift_points_is_a_finding(self):
        self.assertEqual(
            len(handling_findings(good_item(declared_lift_points_used=False))), 1
        )

    def test_an_unprotected_sensitive_item_is_a_finding(self):
        self.assertEqual(
            len(handling_findings(good_item(electrostatic_protection_applied=False))), 1
        )

    def test_a_zero_mass_item_is_rejected(self):
        with self.assertRaises(ValueError):
            handling_findings(good_item(mass_kg=0.0))


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_stay_is_compliant(self):
        report = assess_hstp(good_plan())
        self.assertEqual(report["verdict"], HSTP_COMPLIANT)
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["time_outside_limits_s"], 0.0, places=9)

    def test_a_storage_excursion_is_a_finding(self):
        log = good_log()
        log[1][TEMPERATURE] = 31.0
        report = assess_hstp(good_plan(storage_log=log))
        self.assertEqual(report["verdict"], HSTP_DEFICIENT)
        self.assertEqual(len(report["excursions"]), 1)

    def test_expired_preservation_is_a_finding(self):
        report = assess_hstp(good_plan(planned_use_day=400.0))
        self.assertFalse(report["preservation_is_valid"])
        self.assertAlmostEqual(report["preservation_expiry_day"], 190.0, places=9)

    def test_a_rough_move_is_reported_against_its_leg(self):
        report = assess_hstp(
            good_plan(internal_moves=[good_move(), good_move(peak_shock_g=9.0)])
        )
        self.assertEqual(len(report["transport_findings"]), 1)
        self.assertIn("internal move 2", report["transport_findings"][0])

    def test_no_recorded_move_is_a_limitation_not_a_finding(self):
        report = assess_hstp(good_plan(internal_moves=[]))
        self.assertEqual(report["verdict"], HSTP_COMPLIANT)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_handling_breach_reaches_the_verdict(self):
        report = assess_hstp(good_plan(item=good_item(mass_kg=60.0)))
        self.assertEqual(report["verdict"], HSTP_DEFICIENT)
        self.assertEqual(len(report["handling_findings"]), 1)

    def test_assessment_propagates_a_limit_error(self):
        with self.assertRaises(ValueError):
            assess_hstp(good_plan(limits=dict(LIMITS, max_shock_g=0.0)))


if __name__ == "__main__":
    unittest.main()
