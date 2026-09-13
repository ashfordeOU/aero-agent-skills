"""Gate 3 contract test for e2006-space-plasma-introduction.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2006_space_plasma_introduction.py
"""

import math
import unittest

import e2006_space_plasma_introduction_logic as logic

LOW_ORBIT = {
    "name": "low-orbit-ionosphere",
    "electron_density_m3": 1.0e12,
    "electron_temperature_ev": 0.1,
    "characteristic_length_m": 2.0,
}

SUBSTORM = {
    "name": "geostationary-substorm",
    "electron_density_m3": 1.0e6,
    "electron_temperature_ev": 5.0e3,
    "characteristic_length_m": 5.0,
}

OUTER_BELT = {
    "name": "outer-belt-energetic-electrons",
    "electron_density_m3": 1.0e4,
    "electron_temperature_ev": 3.0e5,
    "characteristic_length_m": 5.0,
}


class NormalisationTests(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        env = logic.normalize_environment(
            {"electron_density_m3": 1.0e6, "electron_temperature_ev": 100.0}
        )
        self.assertAlmostEqual(env["characteristic_length_m"], 1.0, places=12)
        self.assertFalse(env["high_voltage_array"])
        self.assertFalse(env["eclipse_exposed"])
        self.assertEqual(env["name"], "unnamed-environment")

    def test_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(["1e6", "100"])

    def test_missing_density_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment({"electron_temperature_ev": 100.0})

    def test_missing_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment({"electron_density_m3": 1.0e6})

    def test_non_positive_density_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(
                {"electron_density_m3": 0.0, "electron_temperature_ev": 100.0}
            )

    def test_negative_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(
                {
                    "electron_density_m3": 1.0e6,
                    "electron_temperature_ev": 100.0,
                    "characteristic_length_m": -2.0,
                }
            )

    def test_boolean_density_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(
                {"electron_density_m3": True, "electron_temperature_ev": 100.0}
            )

    def test_non_finite_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(
                {
                    "electron_density_m3": 1.0e6,
                    "electron_temperature_ev": float("inf"),
                }
            )

    def test_blank_name_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(
                {
                    "name": "   ",
                    "electron_density_m3": 1.0e6,
                    "electron_temperature_ev": 100.0,
                }
            )

    def test_non_boolean_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment(
                {
                    "electron_density_m3": 1.0e6,
                    "electron_temperature_ev": 100.0,
                    "high_voltage_array": "yes",
                }
            )


class DebyeLengthTests(unittest.TestCase):
    def test_low_orbit_screening_is_millimetric(self):
        value = logic.debye_length(1.0e12, 0.1)
        self.assertGreater(value, 1.0e-3)
        self.assertLess(value, 1.0e-2)

    def test_substorm_screening_is_hundreds_of_metres(self):
        value = logic.debye_length(1.0e6, 5.0e3)
        self.assertGreater(value, 1.0e2)
        self.assertLess(value, 1.0e3)

    def test_screening_scales_with_root_temperature(self):
        base = logic.debye_length(1.0e6, 100.0)
        quadrupled = logic.debye_length(1.0e6, 400.0)
        self.assertAlmostEqual(quadrupled / base, 2.0, places=9)

    def test_screening_scales_inversely_with_root_density(self):
        base = logic.debye_length(1.0e6, 100.0)
        denser = logic.debye_length(4.0e6, 100.0)
        self.assertAlmostEqual(base / denser, 2.0, places=9)

    def test_zero_density_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.debye_length(0.0, 100.0)

    def test_negative_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.debye_length(1.0e6, -5.0)


class ThermalFluxTests(unittest.TestCase):
    def test_thermal_speed_scales_with_root_temperature(self):
        base = logic.electron_thermal_speed(100.0)
        quadrupled = logic.electron_thermal_speed(400.0)
        self.assertAlmostEqual(quadrupled / base, 2.0, places=9)

    def test_substorm_flux_is_sub_microamp_per_square_metre(self):
        flux = logic.electron_thermal_flux(1.0e6, 5.0e3)
        self.assertGreater(flux, 1.0e-7)
        self.assertLess(flux, 1.0e-5)

    def test_flux_is_linear_in_density(self):
        base = logic.electron_thermal_flux(1.0e6, 100.0)
        doubled = logic.electron_thermal_flux(2.0e6, 100.0)
        self.assertAlmostEqual(doubled / base, 2.0, places=9)

    def test_flux_rejects_non_positive_density(self):
        with self.assertRaises(ValueError):
            logic.electron_thermal_flux(-1.0e6, 100.0)


class DensityClassTests(unittest.TestCase):
    def test_dense_ionosphere_is_dense(self):
        self.assertEqual(logic.density_class(1.0e12), "dense-plasma")

    def test_magnetospheric_density_is_tenuous(self):
        self.assertEqual(logic.density_class(1.0e6), "tenuous-plasma")

    def test_threshold_density_counts_as_dense(self):
        self.assertEqual(
            logic.density_class(logic.DENSE_PLASMA_DENSITY_M3), "dense-plasma"
        )


class PopulationCategoryTests(unittest.TestCase):
    def test_sub_electronvolt_population_is_cold(self):
        self.assertEqual(logic.categorize_population(0.1), "cold-ionospheric-plasma")

    def test_tens_of_electronvolts_is_warm(self):
        self.assertEqual(
            logic.categorize_population(50.0), "warm-magnetospheric-plasma"
        )

    def test_kiloelectronvolt_population_is_a_substorm_population(self):
        self.assertEqual(logic.categorize_population(5.0e3), "hot-substorm-plasma")

    def test_hundreds_of_kiloelectronvolts_is_energetic(self):
        self.assertEqual(
            logic.categorize_population(3.0e5), "energetic-electron-population"
        )

    def test_band_edge_belongs_to_the_upper_band(self):
        self.assertEqual(
            logic.categorize_population(logic.COLD_BAND_EDGE_EV),
            "warm-magnetospheric-plasma",
        )
        self.assertEqual(
            logic.categorize_population(logic.WARM_BAND_EDGE_EV),
            "hot-substorm-plasma",
        )
        self.assertEqual(
            logic.categorize_population(logic.HOT_BAND_EDGE_EV),
            "energetic-electron-population",
        )

    def test_band_edge_absorbs_representation_error(self):
        drifted = logic.WARM_BAND_EDGE_EV * (1.0 - 1.0e-12)
        self.assertLess(drifted, logic.WARM_BAND_EDGE_EV)
        self.assertEqual(logic.categorize_population(drifted), "hot-substorm-plasma")

    def test_clear_margin_below_an_edge_stays_in_the_lower_band(self):
        self.assertEqual(
            logic.categorize_population(999.0), "warm-magnetospheric-plasma"
        )

    def test_non_positive_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_population(0.0)


class SheathRegimeTests(unittest.TestCase):
    def test_low_orbit_body_sits_in_a_thin_sheath(self):
        screening = logic.debye_length(1.0e12, 0.1)
        self.assertEqual(logic.sheath_regime(screening, 2.0), "thin-sheath")

    def test_substorm_body_sits_in_a_thick_sheath(self):
        screening = logic.debye_length(1.0e6, 5.0e3)
        self.assertEqual(logic.sheath_regime(screening, 5.0), "thick-sheath")

    def test_comparable_scales_are_transitional(self):
        self.assertEqual(logic.sheath_regime(0.5, 1.0), "transitional-sheath")

    def test_thick_boundary_is_inclusive(self):
        self.assertEqual(logic.sheath_regime(2.0, 2.0), "thick-sheath")

    def test_thin_boundary_is_inclusive(self):
        self.assertEqual(logic.sheath_regime(0.01, 1.0), "thin-sheath")

    def test_thick_boundary_absorbs_representation_error(self):
        screening = 0.7 + 0.1
        self.assertLess(screening / 0.8, 1.0)
        self.assertEqual(logic.sheath_regime(screening, 0.8), "thick-sheath")

    def test_ratio_is_screening_over_body(self):
        self.assertAlmostEqual(logic.sheath_ratio(4.0, 2.0), 2.0, places=12)

    def test_zero_body_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.sheath_regime(1.0, 0.0)


class RiskFamilyTests(unittest.TestCase):
    def test_substorm_population_raises_surface_potential_risks(self):
        risks = logic.charging_risk_families("hot-substorm-plasma", "thick-sheath")
        self.assertIn("absolute-frame-potential-excursion", risks)
        self.assertIn("differential-surface-potential", risks)
        self.assertNotIn("internal-charge-deposition", risks)

    def test_energetic_population_raises_internal_deposition_risks(self):
        risks = logic.charging_risk_families(
            "energetic-electron-population", "thick-sheath"
        )
        self.assertIn("internal-charge-deposition", risks)
        self.assertIn("buried-charge-breakdown", risks)
        self.assertNotIn("absolute-frame-potential-excursion", risks)

    def test_high_voltage_array_in_a_thin_sheath_adds_arcing(self):
        risks = logic.charging_risk_families(
            "cold-ionospheric-plasma", "thin-sheath", high_voltage_array=True
        )
        self.assertIn("high-voltage-array-arcing", risks)
        self.assertIn("ram-wake-potential-asymmetry", risks)

    def test_high_voltage_array_in_a_thick_sheath_does_not_add_arcing(self):
        risks = logic.charging_risk_families(
            "hot-substorm-plasma", "thick-sheath", high_voltage_array=True
        )
        self.assertNotIn("high-voltage-array-arcing", risks)

    def test_eclipse_exposure_adds_a_transient_for_hot_populations(self):
        risks = logic.charging_risk_families(
            "hot-substorm-plasma", "thick-sheath", eclipse_exposed=True
        )
        self.assertIn("eclipse-entry-potential-transient", risks)

    def test_eclipse_exposure_adds_nothing_to_a_cold_population(self):
        risks = logic.charging_risk_families(
            "cold-ionospheric-plasma", "thin-sheath", eclipse_exposed=True
        )
        self.assertEqual(risks, ("ram-wake-potential-asymmetry",))

    def test_results_are_sorted_and_deduplicated(self):
        risks = logic.charging_risk_families("hot-substorm-plasma", "thick-sheath")
        self.assertEqual(list(risks), sorted(set(risks)))

    def test_unknown_population_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.charging_risk_families("solar-wind", "thick-sheath")

    def test_unknown_regime_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.charging_risk_families("hot-substorm-plasma", "no-sheath")

    def test_non_boolean_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.charging_risk_families(
                "hot-substorm-plasma", "thick-sheath", high_voltage_array=1
            )


class BuildUpTimeTests(unittest.TestCase):
    def test_timescale_follows_stored_charge_over_collected_current(self):
        seconds = logic.potential_build_up_time(1.0e-9, 10.0, 1.0e-6, 1000.0)
        self.assertAlmostEqual(seconds, 0.1, places=12)

    def test_sign_of_the_target_potential_does_not_matter(self):
        positive = logic.potential_build_up_time(1.0e-9, 10.0, 1.0e-6, 1000.0)
        negative = logic.potential_build_up_time(1.0e-9, 10.0, 1.0e-6, -1000.0)
        self.assertAlmostEqual(positive, negative, places=12)

    def test_weaker_current_takes_proportionally_longer(self):
        fast = logic.potential_build_up_time(1.0e-9, 10.0, 1.0e-6, 1000.0)
        slow = logic.potential_build_up_time(1.0e-9, 10.0, 1.0e-7, 1000.0)
        self.assertAlmostEqual(slow / fast, 10.0, places=9)

    def test_zero_target_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.potential_build_up_time(1.0e-9, 10.0, 1.0e-6, 0.0)

    def test_non_positive_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.potential_build_up_time(0.0, 10.0, 1.0e-6, 1000.0)

    def test_boolean_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.potential_build_up_time(1.0e-9, 10.0, 1.0e-6, True)


class ScreeningTests(unittest.TestCase):
    def test_low_orbit_record_screens_as_cold_and_thin(self):
        result = logic.screen_environment(LOW_ORBIT)
        self.assertEqual(result["population"], "cold-ionospheric-plasma")
        self.assertEqual(result["sheath_regime"], "thin-sheath")
        self.assertEqual(result["density_class"], "dense-plasma")
        self.assertFalse(result["internal_deposition_driver"])

    def test_substorm_record_screens_as_hot_and_thick(self):
        result = logic.screen_environment(SUBSTORM)
        self.assertEqual(result["population"], "hot-substorm-plasma")
        self.assertEqual(result["sheath_regime"], "thick-sheath")
        self.assertIn("differential-surface-potential", result["risk_families"])

    def test_outer_belt_record_flags_internal_deposition(self):
        result = logic.screen_environment(OUTER_BELT)
        self.assertTrue(result["internal_deposition_driver"])
        self.assertIn("internal-charge-deposition", result["risk_families"])

    def test_high_voltage_array_flag_reaches_the_risk_set(self):
        record = dict(LOW_ORBIT)
        record["high_voltage_array"] = True
        result = logic.screen_environment(record)
        self.assertIn("high-voltage-array-arcing", result["risk_families"])

    def test_screening_reports_the_computed_ratio(self):
        result = logic.screen_environment(SUBSTORM)
        expected = result["debye_length_m"] / SUBSTORM["characteristic_length_m"]
        self.assertAlmostEqual(result["sheath_ratio"] / expected, 1.0, places=12)

    def test_screening_rejects_a_bad_record(self):
        with self.assertRaises(ValueError):
            logic.screen_environment({"electron_density_m3": 1.0e6})


class RollUpTests(unittest.TestCase):
    def test_worst_case_is_the_hottest_population(self):
        worst = logic.worst_case_environment([LOW_ORBIT, SUBSTORM, OUTER_BELT])
        self.assertEqual(worst["name"], "outer-belt-energetic-electrons")

    def test_density_breaks_a_temperature_tie(self):
        cooler = dict(SUBSTORM)
        cooler["name"] = "denser-substorm"
        cooler["electron_density_m3"] = 5.0e6
        worst = logic.worst_case_environment([SUBSTORM, cooler])
        self.assertEqual(worst["name"], "denser-substorm")

    def test_empty_record_set_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.worst_case_environment([])

    def test_non_iterable_record_set_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.worst_case_environment(42)

    def test_summary_unions_the_risk_families(self):
        summary = logic.summarize_environments([LOW_ORBIT, SUBSTORM, OUTER_BELT])
        self.assertEqual(summary["count"], 3)
        self.assertIn("ram-wake-potential-asymmetry", summary["risk_families"])
        self.assertIn("absolute-frame-potential-excursion", summary["risk_families"])
        self.assertIn("internal-charge-deposition", summary["risk_families"])
        self.assertTrue(summary["internal_deposition_credible"])

    def test_summary_without_energetic_population_clears_internal_deposition(self):
        summary = logic.summarize_environments([LOW_ORBIT, SUBSTORM])
        self.assertFalse(summary["internal_deposition_credible"])
        self.assertEqual(summary["worst_case"], "geostationary-substorm")

    def test_summary_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            logic.summarize_environments([])


class ConstantsTests(unittest.TestCase):
    def test_physical_constants_are_the_si_values(self):
        self.assertAlmostEqual(logic.EPSILON_0 / 8.8541878128e-12, 1.0, places=12)
        self.assertAlmostEqual(
            logic.ELEMENTARY_CHARGE / 1.602176634e-19, 1.0, places=12
        )
        self.assertTrue(math.isfinite(logic.ELECTRON_MASS))


if __name__ == "__main__":
    unittest.main()
