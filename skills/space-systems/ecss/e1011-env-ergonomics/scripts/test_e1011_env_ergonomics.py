"""
Offline deterministic tests for e1011_env_ergonomics_logic.py.

Run: python3 test_e1011_env_ergonomics.py
Expected: OK
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_env_ergonomics_logic import (
    check_noise,
    check_alarm_audibility,
    check_vibration,
    check_lighting,
    check_atmosphere,
    check_temperature,
    check_eva_suit,
    assess_habitat,
    NOISE_LIMIT_HABITABLE_DBA,
    NOISE_LIMIT_SLEEP_DBA,
    NOISE_LIMIT_INTERMITTENT_DBA,
    VIBRATION_LIMIT_8H_MS2,
    LIGHTING_MIN_TASK_LUX,
    ATMO_TOTAL_PRESSURE_MIN_KPA,
    ATMO_TOTAL_PRESSURE_MAX_KPA,
    ATMO_PO2_MIN_KPA,
    ATMO_PO2_MAX_KPA,
    ATMO_PCO2_MAX_KPA,
    TEMP_OPERATIVE_MIN_C,
    TEMP_OPERATIVE_MAX_C,
    EVA_SUIT_PRESSURE_MIN_KPA,
    EVA_SUIT_PCO2_MAX_KPA,
)


class TestNoise(unittest.TestCase):

    def test_continuous_noise_within_limit_is_compliant(self):
        result = check_noise(50.0, "continuous")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_continuous_noise_at_limit_is_compliant(self):
        result = check_noise(NOISE_LIMIT_HABITABLE_DBA, "continuous")
        self.assertTrue(result["compliant"])

    def test_continuous_noise_above_limit_raises_finding(self):
        result = check_noise(60.0, "continuous")
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("60.0 dB(A)", result["findings"][0])

    def test_sleep_noise_within_limit_is_compliant(self):
        result = check_noise(45.0, "sleep")
        self.assertTrue(result["compliant"])

    def test_sleep_noise_above_limit_raises_finding(self):
        result = check_noise(55.0, "sleep")
        self.assertFalse(result["compliant"])
        self.assertIn(str(NOISE_LIMIT_SLEEP_DBA), result["findings"][0])

    def test_intermittent_noise_within_limit_is_compliant(self):
        result = check_noise(80.0, "intermittent")
        self.assertTrue(result["compliant"])

    def test_intermittent_noise_above_limit_raises_finding(self):
        result = check_noise(90.0, "intermittent")
        self.assertFalse(result["compliant"])

    def test_invalid_exposure_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_noise(50.0, "outdoor")

    def test_non_numeric_spl_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_noise("loud", "continuous")


class TestAlarmAudibility(unittest.TestCase):

    def test_sufficient_alarm_margin_is_compliant(self):
        result = check_alarm_audibility(70.0, 55.0)  # 15 dB margin
        self.assertTrue(result["compliant"])

    def test_insufficient_alarm_margin_raises_finding(self):
        result = check_alarm_audibility(60.0, 55.0)  # 5 dB margin
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_alarm_exactly_at_required_margin_is_compliant(self):
        result = check_alarm_audibility(65.0, 55.0)  # exactly 10 dB
        self.assertTrue(result["compliant"])


class TestVibration(unittest.TestCase):

    def test_vibration_within_8h_limit_is_compliant(self):
        result = check_vibration(0.3, 8.0)
        self.assertTrue(result["compliant"])

    def test_vibration_above_8h_limit_raises_finding(self):
        result = check_vibration(0.6, 8.0)
        self.assertFalse(result["compliant"])
        self.assertIn("0.600 m/s²", result["findings"][0])

    def test_short_duration_applies_higher_limit(self):
        # 0.8 m/s² is above the 8h limit (0.5) but below the short limit (1.0)
        result = check_vibration(0.8, 0.5)
        self.assertTrue(result["compliant"])

    def test_invalid_axis_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_vibration(0.3, 8.0, axis="w")

    def test_negative_rms_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_vibration(-0.1, 8.0)

    def test_out_of_range_duration_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_vibration(0.3, 25.0)


class TestLighting(unittest.TestCase):

    def test_task_area_within_range_is_compliant(self):
        result = check_lighting(400, "task")
        self.assertTrue(result["compliant"])

    def test_task_area_below_minimum_raises_finding(self):
        result = check_lighting(200, "task")
        self.assertFalse(result["compliant"])
        self.assertIn("below minimum", result["findings"][0])

    def test_task_area_above_maximum_raises_finding(self):
        result = check_lighting(600, "task")
        self.assertFalse(result["compliant"])
        self.assertIn("exceeds", result["findings"][0])

    def test_emergency_above_minimum_is_compliant(self):
        result = check_lighting(20, "emergency")
        self.assertTrue(result["compliant"])

    def test_emergency_below_minimum_raises_finding(self):
        result = check_lighting(5, "emergency")
        self.assertFalse(result["compliant"])

    def test_sleep_area_darkness_is_compliant(self):
        result = check_lighting(0, "sleep")
        self.assertTrue(result["compliant"])

    def test_sleep_area_too_bright_raises_finding(self):
        result = check_lighting(100, "sleep")
        self.assertFalse(result["compliant"])

    def test_invalid_area_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_lighting(300, "corridor")


class TestAtmosphere(unittest.TestCase):

    def test_nominal_atmosphere_is_compliant(self):
        result = check_atmosphere(101.3, 21.2, 0.40, 50.0)
        self.assertTrue(result["compliant"])

    def test_low_total_pressure_raises_finding(self):
        result = check_atmosphere(65.0, 21.2, 0.40, 50.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("Total pressure" in f for f in result["findings"])
        )

    def test_low_o2_raises_finding(self):
        result = check_atmosphere(101.3, 15.0, 0.40, 50.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("O₂" in f for f in result["findings"]))

    def test_high_o2_raises_finding(self):
        result = check_atmosphere(101.3, 25.0, 0.40, 50.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("fire risk" in f for f in result["findings"]))

    def test_co2_above_limit_raises_finding(self):
        result = check_atmosphere(101.3, 21.2, 0.80, 50.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("CO₂" in f for f in result["findings"]))

    def test_humidity_too_low_raises_finding(self):
        result = check_atmosphere(101.3, 21.2, 0.40, 20.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("humidity" in f.lower() for f in result["findings"]))

    def test_humidity_too_high_raises_finding(self):
        result = check_atmosphere(101.3, 21.2, 0.40, 80.0)
        self.assertFalse(result["compliant"])

    def test_multiple_atmosphere_findings_accumulated(self):
        result = check_atmosphere(65.0, 15.0, 0.80, 20.0)
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 3)


class TestTemperature(unittest.TestCase):

    def test_nominal_temperature_is_compliant(self):
        result = check_temperature(22.0, 5.0, 0.10)
        self.assertTrue(result["compliant"])

    def test_temperature_too_cold_raises_finding(self):
        result = check_temperature(15.0, 5.0, 0.10)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("below minimum" in f for f in result["findings"]))

    def test_temperature_too_hot_raises_finding(self):
        result = check_temperature(30.0, 5.0, 0.10)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds maximum" in f for f in result["findings"]))

    def test_radiant_asymmetry_above_limit_raises_finding(self):
        result = check_temperature(22.0, 12.0, 0.10)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("asymmetry" in f for f in result["findings"]))

    def test_high_air_velocity_raises_finding(self):
        result = check_temperature(22.0, 5.0, 0.30)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("velocity" in f for f in result["findings"]))

    def test_negative_asymmetry_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_temperature(22.0, -1.0, 0.10)


class TestEvaSuit(unittest.TestCase):

    def test_nominal_eva_suit_is_compliant(self):
        # 29.6 kPa pure O₂ suit — typical US EMU/Orlan analogue
        result = check_eva_suit(29.6, 1.0, 0.40)
        self.assertTrue(result["compliant"])

    def test_suit_pressure_too_low_raises_finding(self):
        result = check_eva_suit(20.0, 1.0, 0.40)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Suit pressure" in f for f in result["findings"]))

    def test_o2_fraction_below_minimum_raises_finding(self):
        result = check_eva_suit(29.6, 0.10, 0.40)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("O₂ fraction" in f for f in result["findings"]))

    def test_co2_above_limit_raises_finding(self):
        result = check_eva_suit(29.6, 1.0, 1.5)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("CO₂" in f for f in result["findings"]))

    def test_invalid_o2_fraction_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_eva_suit(29.6, 1.5, 0.40)

    def test_negative_co2_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_eva_suit(29.6, 1.0, -0.1)


class TestAssessHabitat(unittest.TestCase):

    def _nominal_kwargs(self):
        return dict(
            noise_spl_db_a=50.0,
            noise_exposure_type="continuous",
            vibration_rms_ms2=0.3,
            vibration_duration_h=8.0,
            lighting_lux=400,
            lighting_area_type="task",
            total_pressure_kpa=101.3,
            o2_partial_kpa=21.2,
            co2_partial_kpa=0.40,
            humidity_pct=50.0,
            operative_temp_c=22.0,
            radiant_asymmetry_delta_c=5.0,
            air_velocity_ms=0.10,
        )

    def test_nominal_habitat_is_compliant(self):
        result = assess_habitat(**self._nominal_kwargs())
        self.assertTrue(result["compliant"])
        for domain, dr in result["domain_results"].items():
            self.assertTrue(dr["compliant"], f"Domain '{domain}' not compliant")

    def test_single_noise_violation_fails_habitat(self):
        kwargs = self._nominal_kwargs()
        kwargs["noise_spl_db_a"] = 65.0
        result = assess_habitat(**kwargs)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["domain_results"]["noise"]["compliant"])
        # other domains should still pass
        self.assertTrue(result["domain_results"]["atmosphere"]["compliant"])

    def test_single_temperature_violation_fails_habitat(self):
        kwargs = self._nominal_kwargs()
        kwargs["operative_temp_c"] = 30.0
        result = assess_habitat(**kwargs)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["domain_results"]["temperature"]["compliant"])

    def test_domain_results_keys_present(self):
        result = assess_habitat(**self._nominal_kwargs())
        expected_keys = {"noise", "vibration", "lighting", "atmosphere", "temperature"}
        self.assertEqual(set(result["domain_results"].keys()), expected_keys)


if __name__ == "__main__":
    unittest.main()
