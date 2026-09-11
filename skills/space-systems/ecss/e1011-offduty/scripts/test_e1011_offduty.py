"""test_e1011_offduty.py — stdlib unittest for e1011_offduty_logic (offline, deterministic)."""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from e1011_offduty_logic import (
    evaluate_station,
    evaluate_station_set,
    validate_station_type,
)


class TestValidateStationType(unittest.TestCase):

    def test_sleep_accepted(self):
        validate_station_type("sleep")  # must not raise

    def test_hygiene_accepted(self):
        validate_station_type("hygiene")  # must not raise

    def test_recreation_accepted(self):
        validate_station_type("recreation")  # must not raise

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            validate_station_type("cafeteria")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            validate_station_type("")

    def test_case_sensitive_rejection(self):
        with self.assertRaises(ValueError):
            validate_station_type("Sleep")


class TestSleepStation(unittest.TestCase):

    def _good(self):
        return {
            "acoustic_attenuation_dB": 45,
            "lighting_lux_min": 0,
            "lighting_lux_max": 100,
            "temperature_c_min": 20,
            "temperature_c_max": 25,
            "volume_m3": 3.5,
            "restraint_system": True,
            "privacy_screen": True,
        }

    def test_fully_compliant_sleep_station(self):
        result = evaluate_station("sleep", self._good())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing"], [])

    def test_station_type_echoed(self):
        result = evaluate_station("sleep", self._good())
        self.assertEqual(result["station_type"], "sleep")

    def test_low_acoustic_attenuation_fails(self):
        p = self._good()
        p["acoustic_attenuation_dB"] = 30  # below min 40
        result = evaluate_station("sleep", p)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("acoustic_attenuation_dB" in f for f in result["findings"]))

    def test_lighting_max_too_high_fails(self):
        p = self._good()
        p["lighting_lux_max"] = 250  # above max 200
        result = evaluate_station("sleep", p)
        self.assertFalse(result["compliant"])

    def test_volume_below_minimum_fails(self):
        p = self._good()
        p["volume_m3"] = 1.8  # below min 2.0
        result = evaluate_station("sleep", p)
        self.assertFalse(result["compliant"])

    def test_restraint_system_false_fails(self):
        p = self._good()
        p["restraint_system"] = False
        result = evaluate_station("sleep", p)
        self.assertFalse(result["compliant"])

    def test_restraint_system_missing_flagged(self):
        p = self._good()
        del p["restraint_system"]
        result = evaluate_station("sleep", p)
        self.assertFalse(result["compliant"])
        self.assertIn("restraint_system", result["missing"])

    def test_privacy_screen_missing_flagged(self):
        p = self._good()
        del p["privacy_screen"]
        result = evaluate_station("sleep", p)
        self.assertIn("privacy_screen", result["missing"])

    def test_temperature_too_cold_fails(self):
        p = self._good()
        p["temperature_c_min"] = 15  # below min 18
        result = evaluate_station("sleep", p)
        self.assertFalse(result["compliant"])

    def test_lighting_min_nonzero_fails(self):
        p = self._good()
        p["lighting_lux_min"] = 5  # must be capable of reaching 0 lux
        result = evaluate_station("sleep", p)
        self.assertFalse(result["compliant"])


class TestHygieneStation(unittest.TestCase):

    def _good(self):
        return {
            "water_flow_ml_per_min": 80,
            "waste_containment": True,
            "accessibility_rating": 4,
            "handhold_count": 3,
        }

    def test_fully_compliant_hygiene_station(self):
        result = evaluate_station("hygiene", self._good())
        self.assertTrue(result["compliant"])

    def test_low_water_flow_fails(self):
        p = self._good()
        p["water_flow_ml_per_min"] = 40  # below min 50
        result = evaluate_station("hygiene", p)
        self.assertFalse(result["compliant"])

    def test_waste_containment_false_fails(self):
        p = self._good()
        p["waste_containment"] = False
        result = evaluate_station("hygiene", p)
        self.assertFalse(result["compliant"])

    def test_accessibility_below_min_fails(self):
        p = self._good()
        p["accessibility_rating"] = 2  # below min 3
        result = evaluate_station("hygiene", p)
        self.assertFalse(result["compliant"])

    def test_insufficient_handholds_fails(self):
        p = self._good()
        p["handhold_count"] = 1  # below min 2
        result = evaluate_station("hygiene", p)
        self.assertFalse(result["compliant"])

    def test_missing_waste_containment_in_missing_list(self):
        p = self._good()
        del p["waste_containment"]
        result = evaluate_station("hygiene", p)
        self.assertIn("waste_containment", result["missing"])


class TestRecreationStation(unittest.TestCase):

    def _good(self):
        return {
            "comm_link_available": True,
            "exercise_volume_m3": 12.0,
            "lighting_lux": 500,
        }

    def test_fully_compliant_recreation_station(self):
        result = evaluate_station("recreation", self._good())
        self.assertTrue(result["compliant"])

    def test_comm_link_false_fails(self):
        p = self._good()
        p["comm_link_available"] = False
        result = evaluate_station("recreation", p)
        self.assertFalse(result["compliant"])

    def test_exercise_volume_too_small_fails(self):
        p = self._good()
        p["exercise_volume_m3"] = 8.0  # below min 10.0
        result = evaluate_station("recreation", p)
        self.assertFalse(result["compliant"])

    def test_dim_lighting_fails(self):
        p = self._good()
        p["lighting_lux"] = 200  # below min 300
        result = evaluate_station("recreation", p)
        self.assertFalse(result["compliant"])

    def test_comm_link_missing_flagged(self):
        p = self._good()
        del p["comm_link_available"]
        result = evaluate_station("recreation", p)
        self.assertIn("comm_link_available", result["missing"])


class TestEvaluateStationSet(unittest.TestCase):

    def _sleep_ok(self):
        return {"station_type": "sleep", "params": {
            "acoustic_attenuation_dB": 45, "lighting_lux_min": 0,
            "lighting_lux_max": 100, "temperature_c_min": 20,
            "temperature_c_max": 25, "volume_m3": 3.5,
            "restraint_system": True, "privacy_screen": True,
        }}

    def _hygiene_ok(self):
        return {"station_type": "hygiene", "params": {
            "water_flow_ml_per_min": 80, "waste_containment": True,
            "accessibility_rating": 4, "handhold_count": 3,
        }}

    def _recreation_ok(self):
        return {"station_type": "recreation", "params": {
            "comm_link_available": True, "exercise_volume_m3": 15.0,
            "lighting_lux": 400,
        }}

    def test_all_three_stations_compliant(self):
        agg = evaluate_station_set([self._sleep_ok(), self._hygiene_ok(), self._recreation_ok()])
        self.assertTrue(agg["all_compliant"])
        self.assertEqual(agg["total"], 3)
        self.assertEqual(agg["compliant_count"], 3)

    def test_partial_compliance_counted_correctly(self):
        failing_sleep = {"station_type": "sleep", "params": {
            "acoustic_attenuation_dB": 20,  # fails
            "lighting_lux_min": 0, "lighting_lux_max": 100,
            "temperature_c_min": 20, "temperature_c_max": 25,
            "volume_m3": 3.5, "restraint_system": True, "privacy_screen": True,
        }}
        agg = evaluate_station_set([failing_sleep, self._recreation_ok()])
        self.assertFalse(agg["all_compliant"])
        self.assertEqual(agg["compliant_count"], 1)
        self.assertEqual(agg["total"], 2)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            evaluate_station_set([])

    def test_entry_missing_station_type_raises(self):
        with self.assertRaises(ValueError):
            evaluate_station_set([{"params": {}}])

    def test_entry_missing_params_raises(self):
        with self.assertRaises(ValueError):
            evaluate_station_set([{"station_type": "sleep"}])

    def test_results_list_length_matches_input(self):
        agg = evaluate_station_set([self._sleep_ok(), self._hygiene_ok()])
        self.assertEqual(len(agg["results"]), 2)

    def test_single_station_set(self):
        agg = evaluate_station_set([self._hygiene_ok()])
        self.assertEqual(agg["total"], 1)
        self.assertTrue(agg["all_compliant"])


if __name__ == "__main__":
    unittest.main()
