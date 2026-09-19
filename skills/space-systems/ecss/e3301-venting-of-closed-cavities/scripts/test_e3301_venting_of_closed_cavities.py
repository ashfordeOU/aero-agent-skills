"""Contract tests for the clause 4.7.5.4.11 cavity-venting logic."""

import math
import unittest

from e3301_venting_of_closed_cavities_logic import (
    CHANNEL_LOSS_FACTOR,
    DEFAULT_DISCHARGE_COEFFICIENT,
    DEFAULT_GAS_TEMPERATURE_K,
    GAMMA_AIR,
    MIN_VENT_AREA_PER_LITRE_MM2,
    MIN_VENT_DIAMETER_MM,
    PRESSURE_TOLERANCE_PA,
    R_SPECIFIC_AIR,
    assess_cavity,
    assess_venting,
    contamination_findings,
    critical_discharge_velocity_m_s,
    effective_vent_area_mm2,
    geometric_vent_area_mm2,
    peak_differential_pressure_pa,
    validate_positive,
    vent_area_per_litre_mm2,
    venting_time_constant_s,
)


def cavity(**overrides):
    record = {
        "name": "actuator housing",
        "volume_litre": 0.8,
        "vent_diameter_mm": 5.0,
        "vent_count": 4,
        "vent_length_mm": 6.0,
        "allowable_differential_pa": 3000.0,
        "depressurization_rate_pa_per_s": 5000.0,
    }
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertAlmostEqual(validate_positive("x", 6), 6.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", -1.0, allow_zero=True)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("inf"))


class DischargeVelocityTests(unittest.TestCase):
    def test_matches_the_closed_form_for_air(self):
        expected = math.sqrt(GAMMA_AIR * R_SPECIFIC_AIR * DEFAULT_GAS_TEMPERATURE_K) * (
            2.0 / (GAMMA_AIR + 1.0)
        ) ** ((GAMMA_AIR + 1.0) / (2.0 * (GAMMA_AIR - 1.0)))
        self.assertAlmostEqual(critical_discharge_velocity_m_s(), expected, places=9)

    def test_velocity_is_below_the_speed_of_sound(self):
        sonic = math.sqrt(GAMMA_AIR * R_SPECIFIC_AIR * DEFAULT_GAS_TEMPERATURE_K)
        self.assertLess(critical_discharge_velocity_m_s(), sonic)

    def test_hotter_gas_vents_faster(self):
        self.assertGreater(
            critical_discharge_velocity_m_s(400.0), critical_discharge_velocity_m_s(200.0)
        )

    def test_gamma_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            critical_discharge_velocity_m_s(293.15, 1.0)

    def test_zero_temperature_rejected(self):
        with self.assertRaises(ValueError):
            critical_discharge_velocity_m_s(0.0)


class VentAreaTests(unittest.TestCase):
    def test_geometric_area_matches_the_circle_formula(self):
        self.assertAlmostEqual(
            geometric_vent_area_mm2(4.0, 3), 3 * math.pi * 4.0, places=9
        )

    def test_no_holes_gives_no_area(self):
        self.assertAlmostEqual(geometric_vent_area_mm2(4.0, 0), 0.0)

    def test_negative_hole_count_rejected(self):
        with self.assertRaises(ValueError):
            geometric_vent_area_mm2(4.0, -1)

    def test_discharge_coefficient_reduces_the_area(self):
        self.assertAlmostEqual(
            effective_vent_area_mm2(4.0, 3, 0.0, 0.62),
            geometric_vent_area_mm2(4.0, 3) * 0.62,
            places=9,
        )

    def test_default_discharge_coefficient_value(self):
        self.assertAlmostEqual(DEFAULT_DISCHARGE_COEFFICIENT, 0.62)

    def test_deep_channel_reduces_the_area_further(self):
        shallow = effective_vent_area_mm2(4.0, 3, 0.0)
        deep = effective_vent_area_mm2(4.0, 3, 20.0)
        self.assertLess(deep, shallow)

    def test_channel_loss_matches_the_closed_form(self):
        value = effective_vent_area_mm2(4.0, 1, 8.0, 1.0)
        expected = geometric_vent_area_mm2(4.0, 1) / math.sqrt(
            1.0 + CHANNEL_LOSS_FACTOR * 8.0 / 4.0
        )
        self.assertAlmostEqual(value, expected, places=9)

    def test_discharge_coefficient_above_one_rejected(self):
        with self.assertRaises(ValueError):
            effective_vent_area_mm2(4.0, 3, 0.0, 1.4)


class TimeConstantTests(unittest.TestCase):
    def test_time_constant_matches_the_closed_form(self):
        tau = venting_time_constant_s(1.0, 40.0)
        expected = 1.0e-3 / (40.0e-6 * critical_discharge_velocity_m_s())
        self.assertAlmostEqual(tau, expected, places=12)

    def test_larger_cavity_vents_more_slowly(self):
        self.assertGreater(
            venting_time_constant_s(2.0, 40.0), venting_time_constant_s(1.0, 40.0)
        )

    def test_more_vent_area_vents_faster(self):
        self.assertLess(
            venting_time_constant_s(1.0, 80.0), venting_time_constant_s(1.0, 40.0)
        )

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            venting_time_constant_s(1.0, 0.0)

    def test_differential_is_the_lag_times_the_rate(self):
        self.assertAlmostEqual(
            peak_differential_pressure_pa(0.25, 5000.0), 1250.0, places=9
        )

    def test_zero_depressurization_rate_rejected(self):
        with self.assertRaises(ValueError):
            peak_differential_pressure_pa(0.25, 0.0)

    def test_area_per_litre_matches_the_ratio(self):
        self.assertAlmostEqual(vent_area_per_litre_mm2(40.0, 0.5), 80.0, places=9)


class ContaminationTests(unittest.TestCase):
    def test_generous_through_vent_reports_nothing(self):
        self.assertEqual(contamination_findings("housing", 4.0), [])

    def test_small_hole_is_reported(self):
        findings = contamination_findings("housing", 0.4)
        self.assertTrue(any("resists blockage" in f for f in findings))

    def test_hole_exactly_at_the_floor_is_accepted(self):
        self.assertEqual(contamination_findings("housing", MIN_VENT_DIAMETER_MM), [])

    def test_blind_pocket_is_reported(self):
        findings = contamination_findings("housing", 4.0, blind_pocket=True)
        self.assertTrue(any("blind pocket" in f for f in findings))

    def test_sensitive_discharge_without_a_screen_is_reported(self):
        findings = contamination_findings(
            "housing", 4.0, discharges_at_sensitive_surface=True
        )
        self.assertTrue(any("sensitive surface" in f for f in findings))

    def test_screen_clears_the_sensitive_discharge(self):
        findings = contamination_findings(
            "housing", 4.0, discharges_at_sensitive_surface=True, screened=True
        )
        self.assertEqual(findings, [])


class CavityTests(unittest.TestCase):
    def test_well_vented_cavity_is_compliant(self):
        result = assess_cavity(cavity())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_unvented_cavity_is_reported_before_any_arithmetic(self):
        result = assess_cavity(cavity(vent_count=0, vent_diameter_mm=0.0))
        self.assertFalse(result["vented"])
        self.assertIsNone(result["time_constant_s"])
        self.assertTrue(any("unvented" in f for f in result["findings"]))

    def test_undersized_vent_fails_the_area_screen(self):
        result = assess_cavity(cavity(vent_diameter_mm=2.0, vent_count=1))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("per litre" in f for f in result["findings"]))

    def test_steep_depressurization_fails_the_pressure_check(self):
        result = assess_cavity(
            cavity(depressurization_rate_pa_per_s=120000.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("lags ambient" in f for f in result["findings"]))

    def test_differential_exactly_at_the_allowable_is_accepted(self):
        record = cavity()
        probe = assess_cavity(record)
        record["allowable_differential_pa"] = probe["peak_differential_pa"]
        result = assess_cavity(record)
        self.assertAlmostEqual(
            result["peak_differential_pa"], result["allowable_differential_pa"], places=9
        )
        self.assertLessEqual(
            abs(result["peak_differential_pa"] - result["allowable_differential_pa"]),
            PRESSURE_TOLERANCE_PA,
        )
        self.assertTrue(result["compliant"])

    def test_contamination_finding_fails_an_otherwise_sound_cavity(self):
        result = assess_cavity(cavity(blind_pocket=True))
        self.assertFalse(result["compliant"])

    def test_unnamed_cavity_rejected(self):
        with self.assertRaises(ValueError):
            assess_cavity(cavity(name="  "))

    def test_non_integer_vent_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_cavity(cavity(vent_count=2.5))

    def test_missing_key_rejected(self):
        record = cavity()
        del record["allowable_differential_pa"]
        with self.assertRaises(ValueError):
            assess_cavity(record)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_cavity(["name"])


class AssessmentTests(unittest.TestCase):
    def test_sound_set_reports_no_findings(self):
        result = assess_venting({"cavities": [cavity()]})
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_unvented_cavity_is_counted(self):
        result = assess_venting(
            {"cavities": [cavity(), cavity(name="cartridge", vent_count=0)]}
        )
        self.assertEqual(result["unvented_count"], 1)
        self.assertFalse(result["compliant"])

    def test_governing_cavity_is_the_largest_differential(self):
        worse = cavity(name="gearbox", volume_litre=2.5)
        result = assess_venting({"cavities": [cavity(), worse]})
        self.assertEqual(result["governing_cavity"], "gearbox")

    def test_governing_cavity_skips_the_unvented_ones(self):
        result = assess_venting(
            {"cavities": [cavity(), cavity(name="cartridge", vent_count=0)]}
        )
        self.assertEqual(result["governing_cavity"], "actuator housing")

    def test_all_unvented_leaves_no_governing_cavity(self):
        result = assess_venting({"cavities": [cavity(vent_count=0)]})
        self.assertIsNone(result["governing_cavity"])
        self.assertIsNone(result["governing_differential_pa"])

    def test_cavity_count_is_reported(self):
        result = assess_venting(
            {"cavities": [cavity(), cavity(name="gearbox")]}
        )
        self.assertEqual(result["cavity_count"], 2)

    def test_duplicate_cavity_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_venting({"cavities": [cavity(), cavity()]})

    def test_empty_cavity_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_venting({"cavities": []})

    def test_missing_cavities_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_venting({})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_venting(["cavities"])

    def test_area_screen_floor_value(self):
        self.assertAlmostEqual(MIN_VENT_AREA_PER_LITRE_MM2, 39.37)

    def test_deep_vent_channel_raises_the_differential(self):
        shallow = assess_venting({"cavities": [cavity(vent_length_mm=1.0)]})
        deep = assess_venting({"cavities": [cavity(vent_length_mm=40.0)]})
        self.assertGreater(
            deep["governing_differential_pa"], shallow["governing_differential_pa"]
        )


if __name__ == "__main__":
    unittest.main()
