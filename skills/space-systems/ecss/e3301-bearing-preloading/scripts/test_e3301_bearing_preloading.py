"""Contract tests for the clause 4.7.3.4.2 bearing-preload logic."""

import math
import unittest

from e3301_bearing_preloading_logic import (
    SEPARATION_FACTORS,
    assess_preload,
    axial_natural_frequency_hz,
    axial_stiffness_n_per_m,
    differential_axial_growth_m,
    effective_preload_path_stiffness,
    preload_after_temperature_n,
    preload_from_frequency_n,
    preload_from_stiffness_n,
    required_preload_n,
    separation_factor,
)


def base_spec(**overrides):
    """Return a representative solidly preloaded duplex pair."""
    spec = {
        "mount_type": "solid",
        "worst_case_axial_load_n": 560.0,
        "safety_factor": 1.25,
        "applied_preload_n": 320.0,
        "stiffness_coefficient": 4.0e6,
        "supported_mass_kg": 3.0,
        "cte_housing_per_k": 12.5e-6,
        "cte_shaft_per_k": 11.0e-6,
        "span_m": 0.05,
        "thermal_cases": [
            {"name": "cold-non-operational", "delta_t_k": -30.0},
            {"name": "hot-operational", "delta_t_k": 25.0},
        ],
        "max_preload_n": 900.0,
    }
    spec.update(overrides)
    return spec


class SeparationFactorTests(unittest.TestCase):
    def test_solid_pair_shares_the_external_load(self):
        self.assertAlmostEqual(separation_factor("solid"), 2.8, places=12)

    def test_flexible_pair_lifts_at_the_preload(self):
        self.assertAlmostEqual(separation_factor("flexible"), 1.0, places=12)

    def test_case_and_padding_tolerated(self):
        self.assertAlmostEqual(separation_factor("  Solid "), 2.8, places=12)

    def test_unknown_arrangement_rejected(self):
        with self.assertRaises(ValueError):
            separation_factor("angular-contact-triplex")

    def test_non_string_arrangement_rejected(self):
        with self.assertRaises(ValueError):
            separation_factor(2.8)

    def test_both_arrangements_are_tabulated(self):
        self.assertEqual(set(SEPARATION_FACTORS), {"solid", "flexible"})


class RequiredPreloadTests(unittest.TestCase):
    def test_solid_mount_needs_less_preload_than_flexible(self):
        solid = required_preload_n(560.0, 1.25, "solid")
        flexible = required_preload_n(560.0, 1.25, "flexible")
        self.assertAlmostEqual(solid * 2.8, flexible, places=9)

    def test_value_follows_the_definition(self):
        self.assertAlmostEqual(required_preload_n(560.0, 1.25, "solid"), 700.0 / 2.8, places=9)

    def test_safety_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            required_preload_n(560.0, 0.9, "solid")

    def test_zero_load_rejected(self):
        with self.assertRaises(ValueError):
            required_preload_n(0.0, 1.25, "solid")


class StiffnessTests(unittest.TestCase):
    def test_one_third_power_law_is_sub_linear(self):
        low = axial_stiffness_n_per_m(100.0, 4.0e6)
        high = axial_stiffness_n_per_m(800.0, 4.0e6)
        self.assertAlmostEqual(high, low * 2.0, places=3)

    def test_stiffness_inverts_back_to_the_preload(self):
        stiffness = axial_stiffness_n_per_m(320.0, 4.0e6)
        self.assertAlmostEqual(preload_from_stiffness_n(stiffness, 4.0e6), 320.0, places=6)

    def test_frequency_round_trips_through_the_preload(self):
        stiffness = axial_stiffness_n_per_m(320.0, 4.0e6)
        freq = axial_natural_frequency_hz(stiffness, 3.0)
        self.assertAlmostEqual(preload_from_frequency_n(freq, 3.0, 4.0e6), 320.0, places=6)

    def test_zero_mass_rejected(self):
        with self.assertRaises(ValueError):
            axial_natural_frequency_hz(1.0e6, 0.0)

    def test_negative_preload_rejected(self):
        with self.assertRaises(ValueError):
            axial_stiffness_n_per_m(-10.0, 4.0e6)


class PreloadPathTests(unittest.TestCase):
    def test_solid_path_is_the_bearing_stack_alone(self):
        self.assertAlmostEqual(
            effective_preload_path_stiffness(2.0e7, "solid"), 2.0e7, places=3
        )

    def test_flexible_path_is_dominated_by_the_spring(self):
        path = effective_preload_path_stiffness(2.0e7, "flexible", spring_rate_n_per_m=5.0e5)
        self.assertAlmostEqual(path, 1.0 / (1.0 / 2.0e7 + 1.0 / 5.0e5), places=3)
        self.assertLess(path, 5.0e5)

    def test_flexible_path_without_a_spring_rate_rejected(self):
        with self.assertRaises(ValueError):
            effective_preload_path_stiffness(2.0e7, "flexible")

    def test_solid_path_with_a_spring_rate_rejected(self):
        with self.assertRaises(ValueError):
            effective_preload_path_stiffness(2.0e7, "solid", spring_rate_n_per_m=5.0e5)


class ThermalShiftTests(unittest.TestCase):
    def test_growth_follows_the_mismatch(self):
        growth = differential_axial_growth_m(23.0e-6, 11.0e-6, 0.12, 25.0)
        self.assertAlmostEqual(growth, 12.0e-6 * 0.12 * 25.0, places=15)

    def test_equal_cte_gives_no_shift(self):
        self.assertAlmostEqual(
            differential_axial_growth_m(16.0e-6, 16.0e-6, 0.12, 80.0), 0.0, places=15
        )

    def test_housing_growth_reduces_a_solid_preload(self):
        growth = differential_axial_growth_m(23.0e-6, 11.0e-6, 0.12, 25.0)
        self.assertLess(preload_after_temperature_n(320.0, 1.0e6, growth), 320.0)

    def test_preload_floors_at_zero_rather_than_going_negative(self):
        self.assertAlmostEqual(preload_after_temperature_n(320.0, 1.0e8, 1.0e-3), 0.0, places=12)

    def test_zero_span_rejected(self):
        with self.assertRaises(ValueError):
            differential_axial_growth_m(23.0e-6, 11.0e-6, 0.0, 25.0)


class AssessPreloadTests(unittest.TestCase):
    def test_representative_solid_pair_is_compliant(self):
        result = assess_preload(base_spec())
        self.assertTrue(result["compliant"], result["findings"])
        self.assertAlmostEqual(result["separation_factor"], 2.8, places=12)

    def test_same_duty_on_a_flexible_mount_needs_more_preload(self):
        result = assess_preload(base_spec(mount_type="flexible", spring_rate_n_per_m=5.0e5))
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["required_preload_n"], 700.0, places=9)

    def test_cold_case_unloading_is_reported(self):
        result = assess_preload(
            base_spec(
                thermal_cases=[{"name": "cold-survival", "delta_t_k": 90.0}],
            )
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no-unload floor" in f for f in result["findings"]))

    def test_ceiling_breach_is_reported(self):
        result = assess_preload(
            base_spec(
                max_preload_n=330.0,
                thermal_cases=[{"name": "cold-operational", "delta_t_k": -40.0}],
            )
        )
        self.assertTrue(any("ceiling" in f for f in result["findings"]))

    def test_lowest_and_highest_cases_are_named(self):
        result = assess_preload(base_spec())
        self.assertEqual(result["lowest_preload_case"]["name"], "hot-operational")
        self.assertEqual(result["highest_preload_case"]["name"], "cold-non-operational")

    def test_matching_frequency_measurement_raises_no_finding(self):
        spec = base_spec()
        stiffness = axial_stiffness_n_per_m(spec["applied_preload_n"], spec["stiffness_coefficient"])
        freq = axial_natural_frequency_hz(stiffness, spec["supported_mass_kg"])
        result = assess_preload(base_spec(measured_frequency_hz=freq))
        self.assertAlmostEqual(result["measured_preload_n"], 320.0, places=6)
        self.assertTrue(result["compliant"], result["findings"])

    def test_low_frequency_measurement_flags_a_short_preload(self):
        spec = base_spec()
        stiffness = axial_stiffness_n_per_m(spec["applied_preload_n"], spec["stiffness_coefficient"])
        freq = axial_natural_frequency_hz(stiffness, spec["supported_mass_kg"])
        result = assess_preload(base_spec(measured_frequency_hz=freq * 0.8))
        self.assertFalse(result["compliant"])
        self.assertLess(result["measured_preload_n"], 320.0)

    def test_measurement_tolerance_of_one_or_more_rejected(self):
        with self.assertRaises(ValueError):
            assess_preload(base_spec(measured_frequency_hz=200.0, measurement_tolerance=1.0))

    def test_empty_thermal_case_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_preload(base_spec(thermal_cases=[]))

    def test_malformed_thermal_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_preload(base_spec(thermal_cases=[{"name": "hot"}]))

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["span_m"]
        with self.assertRaises(ValueError):
            assess_preload(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_preload("solid")

    def test_reported_axial_frequency_matches_the_stiffness(self):
        result = assess_preload(base_spec())
        expected = math.sqrt(result["bearing_stiffness_n_per_m"] / 3.0) / (2.0 * math.pi)
        self.assertAlmostEqual(result["axial_frequency_hz"], expected, places=9)


if __name__ == "__main__":
    unittest.main()
