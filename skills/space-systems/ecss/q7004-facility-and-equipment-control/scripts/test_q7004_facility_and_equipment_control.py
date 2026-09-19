#!/usr/bin/env python3
"""Contract test for facility, fixture and instrument control (offline)."""

import copy
import unittest

from q7004_facility_and_equipment_control_logic import (
    CHAMBER_CONTROLLER,
    CONTROLLING_SENSOR,
    DEFAULT_FACILITY_POLICY,
    DUE_SOON,
    EXPIRED,
    MONITORING_SENSOR,
    NOT_READY,
    READY,
    VALID,
    assess_instrument,
    calibration_status,
    envelope_check,
    fixture_check,
    instrument_is_adequate,
    test_accuracy_ratio,
    validate_facility_policy,
    verify_facility_control,
)

TEST_DAY = 1000

GOOD_SENSOR = {
    "tag": "TC-01",
    "role": CONTROLLING_SENSOR,
    "calibrated_on_day": 800,
    "interval_days": 365,
    "required_tolerance_k": 2.0,
    "uncertainty_k": 0.25,
}

BASE_CASE = {
    "facility_id": "chamber-2",
    "test_day": TEST_DAY,
    "instruments": [
        GOOD_SENSOR,
        dict(GOOD_SENSOR, tag="TC-02", role=MONITORING_SENSOR),
        dict(GOOD_SENSOR, tag="CH-01", role=CHAMBER_CONTROLLER),
    ],
    "required_min_k": 213.15,
    "required_max_k": 373.15,
    "capability_min_k": 193.15,
    "capability_max_k": 423.15,
    "fixture_mass_kg": 4.0,
    "item_mass_kg": 6.0,
    "attachment_conforms": True,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_facility_policy(DEFAULT_FACILITY_POLICY), DEFAULT_FACILITY_POLICY
        )

    def test_a_policy_allowing_a_ratio_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_FACILITY_POLICY)
        broken["min_test_accuracy_ratio"] = 0.5
        with self.assertRaises(ValueError):
            validate_facility_policy(broken)

    def test_a_policy_with_no_envelope_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_FACILITY_POLICY)
        broken["envelope_margin_k"] = 0.0
        with self.assertRaises(ValueError):
            validate_facility_policy(broken)

    def test_a_policy_with_a_fractional_sensor_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_FACILITY_POLICY)
        broken["min_temperature_sensors"] = 1.5
        with self.assertRaises(ValueError):
            validate_facility_policy(broken)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility_policy("four to one and calibrated")


class CalibrationTests(unittest.TestCase):
    def test_an_instrument_well_inside_its_interval_is_valid(self):
        status = calibration_status(800, 365, TEST_DAY)
        self.assertEqual(status["status"], VALID)
        self.assertEqual(status["days_remaining"], 165)

    def test_an_instrument_near_its_due_day_is_due_soon(self):
        status = calibration_status(800, 210, TEST_DAY)
        self.assertEqual(status["status"], DUE_SOON)
        self.assertTrue(status["is_valid"])

    def test_an_instrument_on_its_due_day_is_still_valid(self):
        status = calibration_status(800, 200, TEST_DAY)
        self.assertEqual(status["days_remaining"], 0)
        self.assertTrue(status["is_valid"])

    def test_an_instrument_past_its_due_day_is_expired(self):
        status = calibration_status(800, 100, TEST_DAY)
        self.assertEqual(status["status"], EXPIRED)
        self.assertFalse(status["is_valid"])

    def test_a_test_day_before_the_calibration_day_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(1200, 365, TEST_DAY)

    def test_a_zero_calibration_interval_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(800, 0, TEST_DAY)

    def test_a_non_integer_day_rejected(self):
        with self.assertRaises(ValueError):
            calibration_status(800.5, 365, TEST_DAY)


class AccuracyRatioTests(unittest.TestCase):
    def test_the_ratio_is_tolerance_over_uncertainty(self):
        self.assertAlmostEqual(test_accuracy_ratio(2.0, 0.25), 8.0, places=9)

    def test_a_ratio_on_the_minimum_is_adequate(self):
        minimum = DEFAULT_FACILITY_POLICY["min_test_accuracy_ratio"]
        self.assertTrue(instrument_is_adequate(minimum))

    def test_a_ratio_built_to_land_on_the_minimum_is_adequate(self):
        minimum = DEFAULT_FACILITY_POLICY["min_test_accuracy_ratio"]
        ratio = test_accuracy_ratio(minimum * 0.3, 0.3)
        self.assertAlmostEqual(ratio, minimum, places=9)
        self.assertTrue(instrument_is_adequate(ratio))

    def test_a_ratio_below_the_minimum_is_not_adequate(self):
        self.assertFalse(instrument_is_adequate(2.0))

    def test_a_zero_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            test_accuracy_ratio(2.0, 0.0)

    def test_a_non_numeric_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            test_accuracy_ratio("two kelvin", 0.25)


class InstrumentTests(unittest.TestCase):
    def test_a_good_instrument_is_usable(self):
        instrument = assess_instrument(GOOD_SENSOR, TEST_DAY)
        self.assertTrue(instrument["is_usable"])
        self.assertEqual(instrument["reasons"], [])

    def test_an_expired_instrument_is_not_usable(self):
        instrument = assess_instrument(
            dict(GOOD_SENSOR, interval_days=100), TEST_DAY
        )
        self.assertFalse(instrument["is_usable"])
        self.assertTrue(any("past its calibration" in r for r in instrument["reasons"]))

    def test_a_blunt_instrument_is_not_usable(self):
        instrument = assess_instrument(dict(GOOD_SENSOR, uncertainty_k=1.0), TEST_DAY)
        self.assertFalse(instrument["is_usable"])
        self.assertTrue(any("accuracy ratio" in r for r in instrument["reasons"]))

    def test_a_due_soon_instrument_is_usable_but_flagged(self):
        instrument = assess_instrument(
            dict(GOOD_SENSOR, interval_days=210), TEST_DAY
        )
        self.assertTrue(instrument["is_usable"])
        self.assertTrue(any("falls due" in r for r in instrument["reasons"]))

    def test_an_untagged_instrument_rejected(self):
        with self.assertRaises(ValueError):
            assess_instrument(dict(GOOD_SENSOR, tag="  "), TEST_DAY)

    def test_an_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_instrument(dict(GOOD_SENSOR, role="thermostat"), TEST_DAY)


class EnvelopeTests(unittest.TestCase):
    def test_a_roomy_chamber_is_adequate(self):
        envelope = envelope_check(213.15, 373.15, 193.15, 423.15)
        self.assertTrue(envelope["is_adequate"])
        self.assertAlmostEqual(envelope["cold_margin_k"], 20.0, places=9)

    def test_a_chamber_with_exactly_the_policy_margin_is_adequate(self):
        margin = DEFAULT_FACILITY_POLICY["envelope_margin_k"]
        envelope = envelope_check(
            213.15, 373.15, 213.15 - margin, 373.15 + margin
        )
        self.assertAlmostEqual(envelope["hot_margin_k"], margin, places=9)
        self.assertTrue(envelope["is_adequate"])

    def test_a_chamber_that_only_just_reaches_the_extreme_is_not_adequate(self):
        envelope = envelope_check(213.15, 373.15, 213.15, 373.15)
        self.assertFalse(envelope["is_adequate"])
        self.assertEqual(len(envelope["reasons"]), 2)

    def test_a_hot_shortfall_is_named_on_its_own(self):
        envelope = envelope_check(213.15, 373.15, 193.15, 374.15)
        self.assertFalse(envelope["is_adequate"])
        self.assertTrue(any("hot end" in r for r in envelope["reasons"]))

    def test_inverted_required_limits_rejected(self):
        with self.assertRaises(ValueError):
            envelope_check(373.15, 213.15, 193.15, 423.15)

    def test_inverted_capability_limits_rejected(self):
        with self.assertRaises(ValueError):
            envelope_check(213.15, 373.15, 423.15, 193.15)


class FixtureTests(unittest.TestCase):
    def test_a_light_conforming_fixture_is_adequate(self):
        fixture = fixture_check(4.0, 6.0, True)
        self.assertTrue(fixture["is_adequate"])

    def test_a_fixture_on_the_mass_ratio_limit_is_adequate(self):
        limit = DEFAULT_FACILITY_POLICY["max_fixture_to_item_mass_ratio"]
        fixture = fixture_check(limit * 6.0, 6.0, True)
        self.assertAlmostEqual(fixture["mass_ratio"], limit, places=9)
        self.assertTrue(fixture["is_adequate"])

    def test_a_heavy_fixture_drives_the_item(self):
        fixture = fixture_check(30.0, 6.0, True)
        self.assertFalse(fixture["is_adequate"])
        self.assertTrue(any("fixture's" in r for r in fixture["reasons"]))

    def test_a_non_conforming_attachment_is_not_adequate(self):
        fixture = fixture_check(4.0, 6.0, False)
        self.assertFalse(fixture["is_adequate"])
        self.assertTrue(any("attachment" in r for r in fixture["reasons"]))

    def test_a_zero_item_mass_rejected(self):
        with self.assertRaises(ValueError):
            fixture_check(4.0, 0.0, True)

    def test_a_non_boolean_attachment_flag_rejected(self):
        with self.assertRaises(ValueError):
            fixture_check(4.0, 6.0, "conforms")


class ReadinessTests(unittest.TestCase):
    def test_a_controlled_facility_is_ready(self):
        readiness = verify_facility_control(BASE_CASE)
        self.assertEqual(readiness["verdict"], READY)
        self.assertEqual(readiness["findings"], [])
        self.assertEqual(readiness["unusable_instrument_count"], 0)

    def test_one_expired_instrument_stops_the_test(self):
        case = _case(BASE_CASE)
        case["instruments"][1] = dict(case["instruments"][1], interval_days=100)
        readiness = verify_facility_control(case)
        self.assertEqual(readiness["verdict"], NOT_READY)
        self.assertEqual(readiness["unusable_instrument_count"], 1)

    def test_a_tight_chamber_stops_the_test(self):
        readiness = verify_facility_control(
            _case(BASE_CASE, capability_max_k=373.15)
        )
        self.assertEqual(readiness["verdict"], NOT_READY)
        self.assertFalse(readiness["envelope"]["is_adequate"])

    def test_a_heavy_fixture_stops_the_test(self):
        readiness = verify_facility_control(_case(BASE_CASE, fixture_mass_kg=40.0))
        self.assertEqual(readiness["verdict"], NOT_READY)
        self.assertFalse(readiness["fixture"]["is_adequate"])

    def test_a_single_sensor_setup_stops_the_test(self):
        readiness = verify_facility_control(
            _case(BASE_CASE, instruments=[GOOD_SENSOR])
        )
        self.assertEqual(readiness["verdict"], NOT_READY)
        self.assertTrue(any("nothing to be checked" in f for f in readiness["findings"]))

    def test_a_setup_without_a_controlling_sensor_stops_the_test(self):
        case = _case(
            BASE_CASE,
            instruments=[
                dict(GOOD_SENSOR, tag="TC-01", role=MONITORING_SENSOR),
                dict(GOOD_SENSOR, tag="TC-02", role=MONITORING_SENSOR),
            ],
        )
        readiness = verify_facility_control(case)
        self.assertEqual(readiness["verdict"], NOT_READY)
        self.assertTrue(
            any("no controlling sensor" in f for f in readiness["findings"])
        )

    def test_a_duplicated_instrument_tag_rejected(self):
        case = _case(BASE_CASE)
        case["instruments"][1] = dict(case["instruments"][1], tag="TC-01")
        with self.assertRaises(ValueError):
            verify_facility_control(case)

    def test_every_readiness_statement_carries_the_traceability_duty(self):
        readiness = verify_facility_control(BASE_CASE)
        self.assertTrue(any("not evidence" in d for d in readiness["duties"]))

    def test_a_due_soon_instrument_adds_the_campaign_end_duty(self):
        case = _case(BASE_CASE)
        case["instruments"][0] = dict(case["instruments"][0], interval_days=210)
        readiness = verify_facility_control(case)
        self.assertTrue(any("campaign end day" in d for d in readiness["duties"]))

    def test_an_empty_instrument_list_rejected(self):
        with self.assertRaises(ValueError):
            verify_facility_control(_case(BASE_CASE, instruments=[]))

    def test_a_blank_facility_id_rejected(self):
        with self.assertRaises(ValueError):
            verify_facility_control(_case(BASE_CASE, facility_id=" "))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            verify_facility_control("chamber two, calibrated last spring")


if __name__ == "__main__":
    unittest.main()
