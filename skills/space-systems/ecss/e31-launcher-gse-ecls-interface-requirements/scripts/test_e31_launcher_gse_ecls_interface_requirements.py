"""Contract tests for the clause 4.3.7 to 4.3.9 external interface logic."""

import unittest

from e31_launcher_gse_ecls_interface_requirements_logic import (
    AIR_CP_J_PER_KGK,
    CONDENSATION_MARGIN_K,
    TOUCH_TEMPERATURE_LIMITS_C,
    air_temperature_rise_k,
    assess_crew_touch_surfaces,
    assess_external_interfaces,
    assess_gse_interface,
    assess_launcher_interface,
    condensation_clearance_k,
    envelope_clearance_m,
    gse_capacity_margin_fraction,
    gse_coolant_flow_kg_s,
    item_temperature_c,
    thermal_growth_m,
    touch_duration_band,
    touch_temperature_verdict,
    validate_positive,
)


def launcher(**overrides):
    """Return a representative fairing conditioned-air and envelope record."""
    record = {
        "inlet_temperature_c": 18.0,
        "mass_flow_kg_s": 0.9,
        "prelaunch_dissipation_w": 450.0,
        "non_operating_max_c": 40.0,
        "dew_point_c": 4.0,
        "coldest_surface_c": 15.0,
        "static_gap_m": 0.12,
        "expansion_coefficient_per_k": 23.0e-6,
        "ground_to_flight_swing_k": 60.0,
        "item_length_m": 2.4,
        "deflection_m": 0.015,
        "minimum_clearance_m": 0.05,
    }
    record.update(overrides)
    return record


def gse(**overrides):
    """Return a representative ground support cooling interface record."""
    record = {
        "test_load_w": 1800.0,
        "coolant_cp_j_per_kgk": 3600.0,
        "allowed_rise_k": 6.0,
        "capacity_w": 2600.0,
        "required_margin_fraction": 0.20,
    }
    record.update(overrides)
    return record


def crew_surface(**overrides):
    """Return a representative crew-reachable surface record."""
    record = {
        "name": "handrail-bracket",
        "surface_temperature_c": 32.0,
        "material_group": "metal",
        "contact_duration_s": 120.0,
    }
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertEqual(validate_positive("x", 4), 4.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("-inf"))


class FairingAirTests(unittest.TestCase):
    def test_rise_is_load_over_flow_times_cp(self):
        self.assertAlmostEqual(
            air_temperature_rise_k(450.0, 0.9), 450.0 / (0.9 * AIR_CP_J_PER_KGK),
            places=12,
        )

    def test_double_the_flow_halves_the_rise(self):
        single = air_temperature_rise_k(450.0, 0.9)
        double = air_temperature_rise_k(450.0, 1.8)
        self.assertAlmostEqual(single / double, 2.0, places=12)

    def test_zero_dissipation_gives_no_rise(self):
        self.assertAlmostEqual(air_temperature_rise_k(0.0, 0.9), 0.0, places=12)

    def test_zero_flow_rejected(self):
        with self.assertRaises(ValueError):
            air_temperature_rise_k(450.0, 0.0)

    def test_item_temperature_adds_the_rise(self):
        self.assertAlmostEqual(item_temperature_c(18.0, 2.5), 20.5, places=12)

    def test_negative_inlet_temperature_allowed(self):
        self.assertAlmostEqual(item_temperature_c(-15.0, 2.5), -12.5, places=12)

    def test_negative_rise_rejected(self):
        with self.assertRaises(ValueError):
            item_temperature_c(18.0, -2.5)


class CondensationTests(unittest.TestCase):
    def test_clearance_is_surface_less_dew_point(self):
        self.assertAlmostEqual(condensation_clearance_k(4.0, 15.0), 11.0, places=12)

    def test_surface_below_dew_point_gives_negative_clearance(self):
        self.assertAlmostEqual(condensation_clearance_k(12.0, 6.0), -6.0, places=12)

    def test_non_numeric_dew_point_rejected(self):
        with self.assertRaises(ValueError):
            condensation_clearance_k("4", 15.0)


class EnvelopeTests(unittest.TestCase):
    def test_growth_is_alpha_times_swing_times_length(self):
        self.assertAlmostEqual(
            thermal_growth_m(23.0e-6, 60.0, 2.4), 23.0e-6 * 60.0 * 2.4, places=15
        )

    def test_growth_is_unsigned_for_a_cooling_swing(self):
        warm = thermal_growth_m(23.0e-6, 60.0, 2.4)
        cold = thermal_growth_m(23.0e-6, -60.0, 2.4)
        self.assertAlmostEqual(warm, cold, places=15)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            thermal_growth_m(23.0e-6, 60.0, 0.0)

    def test_clearance_subtracts_growth_and_deflection(self):
        self.assertAlmostEqual(
            envelope_clearance_m(0.12, 0.004, 0.015), 0.12 - 0.019, places=12
        )

    def test_clearance_can_go_negative(self):
        self.assertLess(envelope_clearance_m(0.01, 0.02, 0.005), 0.0)

    def test_negative_deflection_rejected(self):
        with self.assertRaises(ValueError):
            envelope_clearance_m(0.12, 0.004, -0.01)


class GseTests(unittest.TestCase):
    def test_flow_is_load_over_cp_times_rise(self):
        self.assertAlmostEqual(
            gse_coolant_flow_kg_s(1800.0, 3600.0, 6.0), 1800.0 / (3600.0 * 6.0),
            places=12,
        )

    def test_tighter_rise_demands_more_flow(self):
        loose = gse_coolant_flow_kg_s(1800.0, 3600.0, 12.0)
        tight = gse_coolant_flow_kg_s(1800.0, 3600.0, 3.0)
        self.assertAlmostEqual(tight / loose, 4.0, places=12)

    def test_zero_allowed_rise_rejected(self):
        with self.assertRaises(ValueError):
            gse_coolant_flow_kg_s(1800.0, 3600.0, 0.0)

    def test_margin_is_spare_capacity_over_capacity(self):
        self.assertAlmostEqual(
            gse_capacity_margin_fraction(1800.0, 2600.0), 800.0 / 2600.0, places=12
        )

    def test_margin_is_negative_when_overloaded(self):
        self.assertLess(gse_capacity_margin_fraction(3000.0, 2600.0), 0.0)

    def test_zero_capacity_rejected(self):
        with self.assertRaises(ValueError):
            gse_capacity_margin_fraction(1800.0, 0.0)


class TouchTemperatureTests(unittest.TestCase):
    def test_one_second_contact_is_momentary(self):
        self.assertEqual(touch_duration_band(1.0), "momentary")

    def test_thirty_second_contact_is_short(self):
        self.assertEqual(touch_duration_band(30.0), "short")

    def test_two_minute_contact_is_prolonged(self):
        self.assertEqual(touch_duration_band(120.0), "prolonged")

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            touch_duration_band(0.0)

    def test_warm_metal_handrail_is_within_limits(self):
        self.assertEqual(
            touch_temperature_verdict(32.0, "metal", 120.0), "within-limits"
        )

    def test_hot_metal_is_a_hazard_for_prolonged_contact(self):
        self.assertEqual(
            touch_temperature_verdict(50.0, "metal", 120.0), "hot-hazard"
        )

    def test_same_temperature_passes_for_a_momentary_contact(self):
        self.assertEqual(
            touch_temperature_verdict(50.0, "metal", 0.5), "within-limits"
        )

    def test_cold_surface_is_a_cold_hazard(self):
        self.assertEqual(
            touch_temperature_verdict(-12.0, "metal", 30.0), "cold-hazard"
        )

    def test_insulator_tolerates_more_than_metal(self):
        self.assertEqual(
            touch_temperature_verdict(60.0, "insulator", 30.0), "within-limits"
        )
        self.assertEqual(
            touch_temperature_verdict(60.0, "metal", 30.0), "hot-hazard"
        )

    def test_unknown_material_group_rejected(self):
        with self.assertRaises(ValueError):
            touch_temperature_verdict(30.0, "aerogel-blanket", 30.0)

    def test_every_tabulated_band_is_ordered(self):
        for key, (low, high) in TOUCH_TEMPERATURE_LIMITS_C.items():
            self.assertLess(low, high, key)


class LauncherAssessmentTests(unittest.TestCase):
    def test_nominal_launcher_interface_is_compliant(self):
        record = assess_launcher_interface(launcher())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_starved_air_flow_overheats_the_item(self):
        record = assess_launcher_interface(launcher(mass_flow_kg_s=0.02))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("non-operating" in f for f in record["findings"]))

    def test_damp_supply_raises_a_condensation_finding(self):
        record = assess_launcher_interface(launcher(dew_point_c=13.0))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("dew" in f for f in record["findings"]))

    def test_dew_point_exactly_at_the_margin_is_accepted(self):
        record = assess_launcher_interface(
            launcher(coldest_surface_c=4.0 + CONDENSATION_MARGIN_K)
        )
        self.assertAlmostEqual(
            record["dew_point_clearance_k"], CONDENSATION_MARGIN_K, places=12
        )
        self.assertTrue(record["compliant"])

    def test_tight_envelope_raises_a_clearance_finding(self):
        record = assess_launcher_interface(launcher(static_gap_m=0.05))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("clearance" in f for f in record["findings"]))

    def test_missing_launcher_key_rejected(self):
        bad = launcher()
        del bad["dew_point_c"]
        with self.assertRaises(ValueError):
            assess_launcher_interface(bad)


class GseAssessmentTests(unittest.TestCase):
    def test_nominal_gse_interface_is_compliant(self):
        record = assess_gse_interface(gse())
        self.assertTrue(record["compliant"])

    def test_undersized_equipment_raises_a_finding(self):
        record = assess_gse_interface(gse(capacity_w=1900.0))
        self.assertFalse(record["compliant"])
        self.assertTrue(any("margin" in f for f in record["findings"]))

    def test_required_margin_at_or_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_interface(gse(required_margin_fraction=1.0))

    def test_missing_gse_key_rejected(self):
        bad = gse()
        del bad["capacity_w"]
        with self.assertRaises(ValueError):
            assess_gse_interface(bad)


class CrewSurfaceTests(unittest.TestCase):
    def test_nominal_surfaces_are_compliant(self):
        result = assess_crew_touch_surfaces([crew_surface()])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_hot_surface_reaches_the_findings(self):
        result = assess_crew_touch_surfaces(
            [crew_surface(surface_temperature_c=52.0)]
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("hot-hazard" in f for f in result["findings"]))

    def test_uncrewed_vehicle_has_no_touch_surfaces(self):
        result = assess_crew_touch_surfaces([])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["surfaces"], [])

    def test_surface_missing_a_key_rejected(self):
        bad = crew_surface()
        del bad["material_group"]
        with self.assertRaises(ValueError):
            assess_crew_touch_surfaces([bad])


class ExternalAssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "launcher": launcher(),
            "gse": gse(),
            "crew_surfaces": [crew_surface()],
        }
        spec.update(overrides)
        return spec

    def test_nominal_assessment_is_compliant(self):
        result = assess_external_interfaces(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_findings_aggregate_across_the_three_interfaces(self):
        result = assess_external_interfaces(self._spec(
            launcher=launcher(dew_point_c=13.0),
            gse=gse(capacity_w=1900.0),
            crew_surfaces=[crew_surface(surface_temperature_c=52.0)],
        ))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 3)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["gse"]
        with self.assertRaises(ValueError):
            assess_external_interfaces(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_external_interfaces("launcher")


if __name__ == "__main__":
    unittest.main()
