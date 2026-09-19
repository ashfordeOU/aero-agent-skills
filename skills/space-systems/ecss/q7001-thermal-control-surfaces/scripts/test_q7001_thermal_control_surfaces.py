"""Contract tests for the thermal-control-surface contamination logic."""

import math
import unittest

from q7001_thermal_control_surfaces_logic import (
    AREA_TOLERANCE_M2,
    STEFAN_BOLTZMANN,
    TEMPERATURE_TOLERANCE_K,
    absorptance_to_emittance_ratio,
    assess_thermal_surface,
    degraded_absorptance,
    degraded_emittance,
    equilibrium_temperature_k,
    molecular_absorptance_increase,
    obscuration_fraction,
    particulate_absorptance,
    radiator_rejection_w_m2,
    required_radiator_area_m2,
    validate_surface,
)


def surface(**overrides):
    base = {
        "alpha_bol": 0.14,
        "emittance_bol": 0.85,
        "heat_load_w": 200.0,
        "installed_area_m2": 2.0,
        "sink_temperature_k": 4.0,
        "max_allowable_temperature_k": 320.0,
        "solar_flux_w_m2": 0.0,
        "deposition_ng_cm2": 500.0,
        "percent_area_coverage": 0.5,
    }
    base.update(overrides)
    return base


class ObscurationTests(unittest.TestCase):
    def test_percent_becomes_fraction(self):
        self.assertAlmostEqual(obscuration_fraction(0.5), 0.005, places=12)

    def test_zero_coverage_is_zero(self):
        self.assertAlmostEqual(obscuration_fraction(0.0), 0.0)

    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(obscuration_fraction(100.0), 1.0)

    def test_over_one_hundred_percent_rejected(self):
        with self.assertRaises(ValueError):
            obscuration_fraction(120.0)

    def test_negative_coverage_rejected(self):
        with self.assertRaises(ValueError):
            obscuration_fraction(-1.0)

    def test_string_coverage_rejected(self):
        with self.assertRaises(ValueError):
            obscuration_fraction("0.5")


class AbsorptanceModelTests(unittest.TestCase):
    def test_no_film_is_no_rise(self):
        self.assertAlmostEqual(molecular_absorptance_increase(0.0, 0.25, 1000.0), 0.0)

    def test_rise_saturates(self):
        value = molecular_absorptance_increase(1.0e6, 0.25, 1000.0)
        self.assertAlmostEqual(value, 0.25, places=9)

    def test_one_scale_length_is_the_exponential_value(self):
        value = molecular_absorptance_increase(1000.0, 0.25, 1000.0)
        self.assertAlmostEqual(value, 0.25 * (1.0 - math.exp(-1.0)), places=12)

    def test_zero_scale_rejected(self):
        with self.assertRaises(ValueError):
            molecular_absorptance_increase(500.0, 0.25, 0.0)

    def test_saturation_above_one_rejected(self):
        with self.assertRaises(ValueError):
            molecular_absorptance_increase(500.0, 1.4, 1000.0)

    def test_clean_surface_is_unchanged_by_zero_coverage(self):
        self.assertAlmostEqual(particulate_absorptance(0.14, 0.0, 0.95), 0.14)

    def test_full_coverage_takes_the_particle_value(self):
        self.assertAlmostEqual(particulate_absorptance(0.14, 1.0, 0.95), 0.95)

    def test_blend_is_area_weighted(self):
        self.assertAlmostEqual(
            particulate_absorptance(0.2, 0.5, 0.8), 0.5, places=12
        )

    def test_degraded_absorptance_grows_with_deposition(self):
        low = degraded_absorptance(0.14, 100.0, 0.5)
        high = degraded_absorptance(0.14, 2000.0, 0.5)
        self.assertGreater(high, low)

    def test_degraded_absorptance_grows_with_coverage(self):
        clean = degraded_absorptance(0.14, 500.0, 0.0)
        dirty = degraded_absorptance(0.14, 500.0, 5.0)
        self.assertGreater(dirty, clean)

    def test_degraded_absorptance_is_capped_at_unity(self):
        value = degraded_absorptance(0.9, 1.0e7, 50.0, saturation_delta=0.9)
        self.assertAlmostEqual(value, 1.0)


class EmittanceTests(unittest.TestCase):
    def test_clean_surface_keeps_its_emittance(self):
        self.assertAlmostEqual(degraded_emittance(0.85, 0.0), 0.85)

    def test_film_lowers_the_emittance(self):
        self.assertLess(degraded_emittance(0.85, 2000.0), 0.85)

    def test_emittance_drop_saturates(self):
        value = degraded_emittance(0.85, 1.0e7, 0.02, 1000.0)
        self.assertAlmostEqual(value, 0.83, places=9)

    def test_over_deep_degradation_is_refused(self):
        with self.assertRaises(ValueError):
            degraded_emittance(0.01, 1.0e7, 0.5, 1000.0)

    def test_ratio_is_alpha_over_epsilon(self):
        self.assertAlmostEqual(
            absorptance_to_emittance_ratio(0.2, 0.8), 0.25, places=12
        )

    def test_ratio_rejects_a_dead_emitter(self):
        with self.assertRaises(ValueError):
            absorptance_to_emittance_ratio(0.2, 0.0)


class RadiativeTests(unittest.TestCase):
    def test_pure_internal_load_equilibrium(self):
        value = equilibrium_temperature_k(0.1, 1.0, 0.0, STEFAN_BOLTZMANN * 300.0 ** 4, 0.0)
        self.assertAlmostEqual(value, 300.0, places=9)

    def test_sink_sets_the_floor_with_no_load(self):
        self.assertAlmostEqual(
            equilibrium_temperature_k(0.1, 0.9, 0.0, 0.0, 150.0), 150.0, places=9
        )

    def test_solar_load_raises_the_temperature(self):
        cold = equilibrium_temperature_k(0.14, 0.85, 0.0, 100.0, 4.0)
        warm = equilibrium_temperature_k(0.14, 0.85, 1361.0, 100.0, 4.0)
        self.assertGreater(warm, cold)

    def test_higher_emittance_runs_colder(self):
        low = equilibrium_temperature_k(0.14, 0.5, 1361.0, 100.0, 4.0)
        high = equilibrium_temperature_k(0.14, 0.9, 1361.0, 100.0, 4.0)
        self.assertGreater(low, high)

    def test_negative_solar_flux_rejected(self):
        with self.assertRaises(ValueError):
            equilibrium_temperature_k(0.14, 0.85, -10.0, 100.0, 4.0)

    def test_rejection_is_stefan_boltzmann(self):
        value = radiator_rejection_w_m2(1.0, 300.0, 0.0)
        self.assertAlmostEqual(value, STEFAN_BOLTZMANN * 300.0 ** 4, places=12)

    def test_rejection_falls_with_emittance(self):
        self.assertAlmostEqual(
            radiator_rejection_w_m2(0.5, 300.0, 0.0),
            radiator_rejection_w_m2(1.0, 300.0, 0.0) / 2.0,
            places=12,
        )

    def test_sink_at_surface_temperature_rejected(self):
        with self.assertRaises(ValueError):
            radiator_rejection_w_m2(0.85, 300.0, 300.0)

    def test_required_area_is_load_over_rejection(self):
        self.assertAlmostEqual(required_radiator_area_m2(100.0, 50.0), 2.0, places=12)

    def test_zero_rejection_rejected(self):
        with self.assertRaises(ValueError):
            required_radiator_area_m2(100.0, 0.0)


class ValidationTests(unittest.TestCase):
    def test_defaults_are_applied(self):
        record = validate_surface(surface())
        self.assertAlmostEqual(record["scale_ng_cm2"], 1000.0)
        self.assertAlmostEqual(record["particle_absorptance"], 0.95)

    def test_missing_key_rejected(self):
        bad = surface()
        del bad["heat_load_w"]
        with self.assertRaises(ValueError):
            validate_surface(bad)

    def test_absorptance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface(surface(alpha_bol=1.2))

    def test_sink_above_allowable_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface(surface(sink_temperature_k=400.0))

    def test_zero_installed_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface(surface(installed_area_m2=0.0))

    def test_non_mapping_surface_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface(["alpha_bol"])


class AssessmentTests(unittest.TestCase):
    def test_clean_design_is_compliant(self):
        result = assess_thermal_surface(surface())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_contamination_raises_the_ratio(self):
        result = assess_thermal_surface(surface())
        self.assertGreater(result["ratio_eol"], result["ratio_bol"])

    def test_contamination_raises_the_temperature_under_sun(self):
        result = assess_thermal_surface(surface(solar_flux_w_m2=1361.0))
        self.assertGreater(result["temperature_rise_k"], 0.0)

    def test_tight_allowable_temperature_is_flagged(self):
        result = assess_thermal_surface(surface(max_allowable_temperature_k=200.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("equilibrium temperature" in f for f in result["findings"])
        )

    def test_undersized_radiator_is_flagged(self):
        result = assess_thermal_surface(
            surface(installed_area_m2=0.2, max_allowable_temperature_k=250.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("installed" in f for f in result["findings"]))

    def test_surface_that_cannot_close_reports_infinite_area(self):
        result = assess_thermal_surface(
            surface(
                solar_flux_w_m2=1361.0,
                max_allowable_temperature_k=200.0,
                percent_area_coverage=60.0,
            )
        )
        self.assertFalse(math.isfinite(result["required_area_m2"]))
        self.assertTrue(any("no finite area" in f for f in result["findings"]))

    def test_exact_temperature_limit_is_accepted(self):
        probe = assess_thermal_surface(surface())
        limit = probe["temperature_eol_k"]
        result = assess_thermal_surface(surface(max_allowable_temperature_k=limit))
        self.assertAlmostEqual(result["temperature_eol_k"], limit, places=9)
        self.assertLessEqual(
            abs(result["temperature_eol_k"] - limit), TEMPERATURE_TOLERANCE_K
        )
        self.assertTrue(result["compliant"])

    def test_exact_area_boundary_is_accepted(self):
        probe = assess_thermal_surface(surface())
        limit = probe["temperature_eol_k"]
        result = assess_thermal_surface(surface(max_allowable_temperature_k=limit))
        self.assertAlmostEqual(
            result["required_area_m2"], result["installed_area_m2"], places=9
        )
        self.assertLessEqual(
            abs(result["required_area_m2"] - result["installed_area_m2"]),
            max(AREA_TOLERANCE_M2, 1e-9),
        )

    def test_beginning_of_life_is_cooler_than_end_of_life(self):
        result = assess_thermal_surface(surface(solar_flux_w_m2=1361.0))
        self.assertGreater(result["temperature_eol_k"], result["temperature_bol_k"])

    def test_report_carries_both_life_points(self):
        result = assess_thermal_surface(surface())
        for key in ("alpha_bol", "alpha_eol", "emittance_bol", "emittance_eol"):
            self.assertIn(key, result)

    def test_heavier_deposition_needs_more_area(self):
        light = assess_thermal_surface(
            surface(deposition_ng_cm2=10.0, solar_flux_w_m2=1361.0)
        )
        heavy = assess_thermal_surface(
            surface(deposition_ng_cm2=5000.0, solar_flux_w_m2=1361.0)
        )
        self.assertGreater(heavy["required_area_m2"], light["required_area_m2"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermal_surface("alpha_bol")


if __name__ == "__main__":
    unittest.main()
