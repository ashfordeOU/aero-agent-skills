"""Contract test for the CDL/LHP performance-verification leaf (stdlib unittest)."""

import unittest

from e3102_cdl_lhp_performance_verification_logic import (
    MARGIN_TOLERANCE,
    REGULATION_METHODS,
    STANDARD_GRAVITY,
    adverse_head_pa,
    assess_off_mode_leak,
    assess_performance_verification,
    assess_regulation_method,
    assess_start_up,
    assess_subcooling,
    capillary_pressure_balance,
    minimum_start_load_at_mass,
    require_positive,
    require_real,
    subcooling_k,
    thermal_mass_sensitivity,
)

SERIES = [(0.0, 4.0), (100.0, 6.0), (200.0, 8.0), (300.0, 10.0)]


def good_spec(**overrides):
    spec = {
        "start_up": {
            "demonstrated_power_w": 8.0,
            "minimum_start_load_w": 10.0,
            "attached_mass_j_per_k": 320.0,
            "qualification_mass_j_per_k": 300.0,
        },
        "sensitivity_series": list(SERIES),
        "subcooling": {
            "saturation_temperature_k": 303.15,
            "inlet_temperature_k": 295.15,
            "required_k": 5.0,
        },
        "orientation": {
            "capillary_limit_pa": 9000.0,
            "liquid_drop_pa": 1200.0,
            "vapour_drop_pa": 800.0,
            "groove_drop_pa": 400.0,
            "density_kg_per_m3": 1000.0,
            "elevation_m": 0.1,
        },
        "off_mode": {"measured_leak_w": 1.2, "allowable_leak_w": 2.0},
        "regulation": {
            "method": "active-reservoir-heater",
            "demonstrated_band_k": 25.0,
            "required_band_k": 20.0,
        },
    }
    spec.update(overrides)
    return spec


class TestValidators(unittest.TestCase):
    def test_require_real_rejects_boolean(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_real_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            require_real("x", float("inf"))

    def test_require_positive_rejects_zero(self):
        with self.assertRaises(ValueError):
            require_positive("x", 0.0)

    def test_require_positive_rejects_string(self):
        with self.assertRaises(ValueError):
            require_positive("x", "12")


class TestStartUp(unittest.TestCase):
    def test_start_below_minimum_load_is_compliant(self):
        result = assess_start_up(8.0, 10.0, 320.0, 300.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["power_margin_w"], 2.0, places=9)

    def test_start_exactly_at_minimum_load_is_compliant(self):
        result = assess_start_up(10.0, 10.0, 300.0, 300.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["power_margin_w"], 0.0, places=9)

    def test_start_above_minimum_load_fails(self):
        result = assess_start_up(12.0, 10.0, 320.0, 300.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("minimum start" in f for f in result["findings"]))

    def test_light_evaporator_mass_invalidates_the_demonstration(self):
        result = assess_start_up(8.0, 10.0, 120.0, 300.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("attached mass" in f for f in result["findings"]))

    def test_negative_attached_mass_raises(self):
        with self.assertRaises(ValueError):
            assess_start_up(8.0, 10.0, -1.0, 300.0)


class TestThermalMassSensitivity(unittest.TestCase):
    def test_slope_of_a_linear_series(self):
        result = thermal_mass_sensitivity(SERIES)
        self.assertAlmostEqual(result["slope_w_per_j_per_k"], 0.02, places=9)
        self.assertAlmostEqual(result["intercept_w"], 4.0, places=9)
        self.assertTrue(result["monotonic"])

    def test_falling_series_is_reported_not_fitted_silently(self):
        result = thermal_mass_sensitivity([(0.0, 9.0), (100.0, 5.0)])
        self.assertFalse(result["monotonic"])
        self.assertTrue(result["findings"])

    def test_single_point_series_raises(self):
        with self.assertRaises(ValueError):
            thermal_mass_sensitivity([(0.0, 4.0)])

    def test_repeated_mass_raises(self):
        with self.assertRaises(ValueError):
            thermal_mass_sensitivity([(100.0, 4.0), (100.0, 5.0)])

    def test_malformed_point_raises(self):
        with self.assertRaises(ValueError):
            thermal_mass_sensitivity([(0.0, 4.0), (100.0,)])

    def test_interpolated_load_at_tested_mass(self):
        self.assertAlmostEqual(minimum_start_load_at_mass(SERIES, 150.0), 7.0, places=9)

    def test_interpolation_at_the_upper_bound_equals_the_point(self):
        self.assertAlmostEqual(minimum_start_load_at_mass(SERIES, 300.0), 10.0, places=9)

    def test_extrapolation_beyond_the_tested_span_is_refused(self):
        with self.assertRaises(ValueError):
            minimum_start_load_at_mass(SERIES, 500.0)


class TestSubcooling(unittest.TestCase):
    def test_subcooling_is_saturation_minus_inlet(self):
        self.assertAlmostEqual(subcooling_k(303.15, 295.15), 8.0, places=9)

    def test_subcooling_exactly_at_requirement_is_compliant(self):
        result = assess_subcooling(300.0, 295.0, 5.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_k"], 0.0, places=9)

    def test_insufficient_subcooling_fails(self):
        result = assess_subcooling(300.0, 298.0, 5.0)
        self.assertFalse(result["compliant"])

    def test_superheated_inlet_reports_vapour_ingestion(self):
        result = assess_subcooling(300.0, 302.0, 5.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("vapour ingestion" in f for f in result["findings"]))

    def test_non_positive_temperature_raises(self):
        with self.assertRaises(ValueError):
            assess_subcooling(0.0, 295.0, 5.0)


class TestAdverseOrientation(unittest.TestCase):
    def test_head_uses_standard_gravity_by_default(self):
        self.assertAlmostEqual(
            adverse_head_pa(1000.0, 0.1), 1000.0 * STANDARD_GRAVITY * 0.1, places=9
        )

    def test_favourable_elevation_gives_a_relieving_negative_head(self):
        self.assertLess(adverse_head_pa(1000.0, -0.1), 0.0)

    def test_zero_density_raises(self):
        with self.assertRaises(ValueError):
            adverse_head_pa(0.0, 0.1)

    def test_budget_closes_with_margin(self):
        result = capillary_pressure_balance(9000.0, 1200.0, 800.0, 400.0, 980.665)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["demand_pa"], 3380.665, places=9)

    def test_budget_exactly_balanced_is_compliant(self):
        result = capillary_pressure_balance(2400.0, 1200.0, 800.0, 400.0, 0.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_pa"], 0.0, places=9)
        self.assertAlmostEqual(result["ratio"], 1.0, places=9)

    def test_deprime_when_demand_exceeds_the_capillary_limit(self):
        result = capillary_pressure_balance(2000.0, 1200.0, 800.0, 400.0, 500.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_negative_pressure_drop_raises(self):
        with self.assertRaises(ValueError):
            capillary_pressure_balance(9000.0, -1.0, 800.0, 400.0, 0.0)


class TestOffModeLeak(unittest.TestCase):
    def test_leak_within_allowance(self):
        result = assess_off_mode_leak(1.2, 2.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_w"], 0.8, places=9)

    def test_leak_exactly_at_allowance_is_compliant(self):
        result = assess_off_mode_leak(2.0, 2.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_w"], 0.0, places=9)

    def test_leak_above_allowance_fails(self):
        self.assertFalse(assess_off_mode_leak(2.5, 2.0)["compliant"])

    def test_negative_measured_leak_raises(self):
        with self.assertRaises(ValueError):
            assess_off_mode_leak(-0.1, 2.0)


class TestRegulation(unittest.TestCase):
    def test_every_recognised_method_is_accepted(self):
        for method in REGULATION_METHODS:
            result = assess_regulation_method(method, 25.0, 20.0)
            self.assertTrue(result["compliant"])

    def test_method_name_is_normalised(self):
        result = assess_regulation_method("  Cold-Biased-Reservoir ", 25.0, 20.0)
        self.assertEqual(result["method"], "cold-biased-reservoir")

    def test_unrecognised_method_raises(self):
        with self.assertRaises(ValueError):
            assess_regulation_method("hand-wave-control", 25.0, 20.0)

    def test_empty_method_raises(self):
        with self.assertRaises(ValueError):
            assess_regulation_method("   ", 25.0, 20.0)

    def test_band_exactly_met_is_compliant(self):
        result = assess_regulation_method("active-reservoir-heater", 20.0, 20.0)
        self.assertTrue(result["compliant"])

    def test_short_demonstrated_band_fails(self):
        result = assess_regulation_method("active-reservoir-heater", 12.0, 20.0)
        self.assertFalse(result["compliant"])


class TestWholeAssessment(unittest.TestCase):
    def test_good_campaign_is_compliant(self):
        report = assess_performance_verification(good_spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["failed_checks"], [])

    def test_one_bad_check_names_itself(self):
        spec = good_spec()
        spec["off_mode"] = {"measured_leak_w": 4.0, "allowable_leak_w": 2.0}
        report = assess_performance_verification(spec)
        self.assertFalse(report["compliant"])
        self.assertIn("off_mode_leak", report["failed_checks"])

    def test_adverse_head_is_carried_into_the_budget(self):
        report = assess_performance_verification(good_spec())
        balance = report["checks"]["adverse_orientation"]
        self.assertAlmostEqual(
            balance["adverse_head_pa"], 1000.0 * STANDARD_GRAVITY * 0.1, places=9
        )

    def test_missing_key_raises(self):
        spec = good_spec()
        del spec["regulation"]
        with self.assertRaises(ValueError):
            assess_performance_verification(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_performance_verification(["start_up"])

    def test_tolerance_is_small_enough_to_be_a_representation_allowance(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
