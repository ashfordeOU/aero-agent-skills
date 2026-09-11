import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1011_habitable_env_logic import (
    check_atmospheric_parameters,
    check_habitable_volume,
    check_layout,
    check_hygiene_provisions,
    evaluate_habitability,
    O2_PARTIAL_PRESSURE_MIN_KPA,
    O2_PARTIAL_PRESSURE_MAX_KPA,
    CO2_PARTIAL_PRESSURE_MAX_KPA,
    TOTAL_PRESSURE_MIN_KPA,
    TOTAL_PRESSURE_MAX_KPA,
    TEMPERATURE_MIN_C,
    TEMPERATURE_MAX_C,
    HUMIDITY_MIN_PCT,
    HUMIDITY_MAX_PCT,
    MIN_VOLUME_PER_CREW_M3,
    REQUIRED_HYGIENE_PROVISIONS,
)

VALID_ATM = {
    "o2_kpa": 21.0,
    "co2_kpa": 0.3,
    "total_pressure_kpa": 101.3,
    "temperature_c": 22.0,
    "humidity_pct": 50.0,
}


class TestAtmosphericParameters(unittest.TestCase):

    def test_nominal_parameters_produce_no_findings(self):
        self.assertEqual([], check_atmospheric_parameters(VALID_ATM))

    def test_low_o2_is_flagged(self):
        params = {**VALID_ATM, "o2_kpa": O2_PARTIAL_PRESSURE_MIN_KPA - 0.1}
        findings = check_atmospheric_parameters(params)
        self.assertTrue(any("O2" in f for f in findings))

    def test_high_o2_is_flagged(self):
        params = {**VALID_ATM, "o2_kpa": O2_PARTIAL_PRESSURE_MAX_KPA + 0.1}
        findings = check_atmospheric_parameters(params)
        self.assertTrue(any("O2" in f for f in findings))

    def test_o2_at_lower_bound_is_compliant(self):
        params = {**VALID_ATM, "o2_kpa": O2_PARTIAL_PRESSURE_MIN_KPA}
        self.assertEqual([], check_atmospheric_parameters(params))

    def test_o2_at_upper_bound_is_compliant(self):
        params = {**VALID_ATM, "o2_kpa": O2_PARTIAL_PRESSURE_MAX_KPA}
        self.assertEqual([], check_atmospheric_parameters(params))

    def test_co2_above_limit_is_flagged(self):
        params = {**VALID_ATM, "co2_kpa": CO2_PARTIAL_PRESSURE_MAX_KPA + 0.1}
        findings = check_atmospheric_parameters(params)
        self.assertTrue(any("CO2" in f for f in findings))

    def test_co2_at_limit_is_compliant(self):
        params = {**VALID_ATM, "co2_kpa": CO2_PARTIAL_PRESSURE_MAX_KPA}
        self.assertEqual([], check_atmospheric_parameters(params))

    def test_low_total_pressure_is_flagged(self):
        params = {**VALID_ATM, "total_pressure_kpa": TOTAL_PRESSURE_MIN_KPA - 1.0}
        findings = check_atmospheric_parameters(params)
        self.assertTrue(any("pressure" in f.lower() for f in findings))

    def test_high_temperature_is_flagged(self):
        params = {**VALID_ATM, "temperature_c": TEMPERATURE_MAX_C + 1.0}
        findings = check_atmospheric_parameters(params)
        self.assertTrue(any("Temperature" in f for f in findings))

    def test_low_humidity_is_flagged(self):
        params = {**VALID_ATM, "humidity_pct": HUMIDITY_MIN_PCT - 1.0}
        findings = check_atmospheric_parameters(params)
        self.assertTrue(any("humidity" in f.lower() for f in findings))

    def test_high_humidity_is_flagged(self):
        params = {**VALID_ATM, "humidity_pct": HUMIDITY_MAX_PCT + 1.0}
        findings = check_atmospheric_parameters(params)
        self.assertTrue(any("humidity" in f.lower() for f in findings))

    def test_missing_key_raises_value_error(self):
        params = {k: v for k, v in VALID_ATM.items() if k != "co2_kpa"}
        with self.assertRaises(ValueError):
            check_atmospheric_parameters(params)

    def test_multiple_violations_each_reported_independently(self):
        params = {
            "o2_kpa": 10.0,
            "co2_kpa": 1.0,
            "total_pressure_kpa": 50.0,
            "temperature_c": 35.0,
            "humidity_pct": 90.0,
        }
        findings = check_atmospheric_parameters(params)
        self.assertGreaterEqual(len(findings), 4)

    def test_single_out_of_band_does_not_suppress_others(self):
        params = {**VALID_ATM, "o2_kpa": 10.0, "co2_kpa": 1.0}
        findings = check_atmospheric_parameters(params)
        self.assertGreaterEqual(len(findings), 2)


class TestHabitableVolume(unittest.TestCase):

    def test_adequate_volume_produces_no_finding(self):
        volume = MIN_VOLUME_PER_CREW_M3 * 3 + 1.0
        self.assertEqual([], check_habitable_volume(volume, 3))

    def test_volume_below_minimum_per_person_is_flagged(self):
        findings = check_habitable_volume(10.0, 2)
        self.assertEqual(1, len(findings))

    def test_exact_minimum_per_person_is_compliant(self):
        volume = MIN_VOLUME_PER_CREW_M3 * 4
        self.assertEqual([], check_habitable_volume(volume, 4))

    def test_single_crew_member_below_threshold_is_flagged(self):
        findings = check_habitable_volume(MIN_VOLUME_PER_CREW_M3 - 0.1, 1)
        self.assertEqual(1, len(findings))

    def test_zero_crew_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_habitable_volume(50.0, 0)

    def test_negative_volume_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_habitable_volume(-1.0, 2)


class TestLayoutCheck(unittest.TestCase):

    def test_adequate_layout_produces_no_findings(self):
        self.assertEqual([], check_layout(2, 4, 4))

    def test_zero_egress_paths_is_flagged(self):
        findings = check_layout(0, 3, 3)
        self.assertTrue(any("gress" in f.lower() for f in findings))

    def test_insufficient_workstations_is_flagged(self):
        findings = check_layout(1, 1, 3)
        self.assertTrue(any("workstation" in f.lower() for f in findings))

    def test_zero_crew_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_layout(2, 2, 0)

    def test_one_egress_path_meets_minimum(self):
        self.assertEqual([], check_layout(1, 2, 2))

    def test_both_shortfalls_reported_together(self):
        findings = check_layout(0, 0, 2)
        self.assertEqual(2, len(findings))


class TestHygieneProvisions(unittest.TestCase):

    def test_all_provisions_allocated_produces_no_findings(self):
        self.assertEqual([], check_hygiene_provisions(REQUIRED_HYGIENE_PROVISIONS))

    def test_missing_single_provision_flagged(self):
        partial = set(REQUIRED_HYGIENE_PROVISIONS) - {"waste_management"}
        findings = check_hygiene_provisions(partial)
        self.assertEqual(1, len(findings))
        self.assertIn("waste_management", findings[0])

    def test_all_provisions_missing_each_flagged(self):
        findings = check_hygiene_provisions(set())
        self.assertEqual(len(REQUIRED_HYGIENE_PROVISIONS), len(findings))

    def test_extra_provision_does_not_cause_finding(self):
        extended = set(REQUIRED_HYGIENE_PROVISIONS) | {"exercise_equipment"}
        self.assertEqual([], check_hygiene_provisions(extended))


class TestEvaluateHabitability(unittest.TestCase):

    def test_fully_compliant_compartment(self):
        result = evaluate_habitability(
            compartment_id="HAB-01",
            total_volume_m3=60.0,
            crew_count=4,
            atm_params=VALID_ATM,
            egress_path_count=2,
            workstation_count=4,
            hygiene_provisions=REQUIRED_HYGIENE_PROVISIONS,
        )
        self.assertTrue(result["compliant"])
        self.assertEqual([], result["findings"])
        self.assertEqual("HAB-01", result["compartment_id"])

    def test_non_compliant_compartment_returns_findings_and_false(self):
        bad_atm = {**VALID_ATM, "o2_kpa": 10.0, "co2_kpa": 1.5}
        result = evaluate_habitability(
            compartment_id="HAB-02",
            total_volume_m3=5.0,
            crew_count=3,
            atm_params=bad_atm,
            egress_path_count=0,
            workstation_count=0,
            hygiene_provisions=set(),
        )
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_compartment_id_preserved_in_result(self):
        result = evaluate_habitability(
            compartment_id="NODE-3",
            total_volume_m3=25.0,
            crew_count=2,
            atm_params=VALID_ATM,
            egress_path_count=1,
            workstation_count=2,
            hygiene_provisions=REQUIRED_HYGIENE_PROVISIONS,
        )
        self.assertEqual("NODE-3", result["compartment_id"])


if __name__ == "__main__":
    unittest.main()
