"""Gate 3 contract test for e2006-surface-charging-physical-mechanisms.

Offline, deterministic, stdlib unittest. Exercises the contributor
categorization, the potential-dependent current terms, the Sternglass
yield curve, the current-balance bisection, the regime bands, the
differential-charging assessment and every ValueError path.
"""

import math
import unittest

import e2006_surface_charging_physical_mechanisms_logic as logic


def geo_storm_environment():
    """Hot substorm plasma: a few microamps per square metre of electrons."""
    return {
        "electron_current": 4.0e-6,
        "ion_current": 1.0e-7,
        "electron_temperature_ev": 10000.0,
        "ion_temperature_ev": 10000.0,
    }


def eclipse_surface():
    return {
        "name": "shadow-side-kapton",
        "yield_max": 2.1,
        "energy_max_ev": 150.0,
        "backscatter_fraction": 0.2,
        "sunlit": False,
    }


def sunlit_surface():
    surface = eclipse_surface()
    surface["name"] = "sun-side-kapton"
    surface["sunlit"] = True
    surface["photoemission_current"] = 2.0e-5
    return surface


class ContributorCategorizationTests(unittest.TestCase):

    def test_ambient_electron_collection_is_collected(self):
        self.assertEqual(
            logic.categorize_current_contributor("ambient-electron-collection"),
            "collected")

    def test_photoelectron_emission_is_emitted(self):
        self.assertEqual(
            logic.categorize_current_contributor("photoelectron-emission"),
            "emitted")

    def test_every_registry_entry_categorizes(self):
        for kind in logic.CURRENT_CONTRIBUTORS:
            self.assertIn(logic.categorize_current_contributor(kind),
                          ("collected", "emitted"))

    def test_uncategorized_contributor_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_current_contributor("cosmic-ray-collection")

    def test_non_string_contributor_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_current_contributor(7)

    def test_charge_signs_follow_the_convention(self):
        self.assertAlmostEqual(
            logic.charge_sign("ambient-electron-collection"), -1.0)
        self.assertAlmostEqual(logic.charge_sign("ambient-ion-collection"), 1.0)
        self.assertAlmostEqual(
            logic.charge_sign("secondary-electron-emission"), 1.0)


class SignedCurrentTests(unittest.TestCase):

    def test_electron_collection_is_negative(self):
        self.assertAlmostEqual(
            logic.signed_current_density("ambient-electron-collection", 3.0e-6),
            -3.0e-6)

    def test_negative_magnitude_raises(self):
        with self.assertRaises(ValueError):
            logic.signed_current_density("ambient-ion-collection", -1.0e-9)

    def test_net_current_density_sums_signed_terms(self):
        total = logic.net_current_density([
            {"kind": "ambient-electron-collection", "magnitude": 4.0e-6},
            {"kind": "ambient-ion-collection", "magnitude": 1.0e-7},
            {"kind": "photoelectron-emission", "magnitude": 2.0e-5},
        ])
        self.assertAlmostEqual(total, 1.61e-5, places=9)

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            logic.net_current_density([])

    def test_contributor_missing_magnitude_raises(self):
        with self.assertRaises(ValueError):
            logic.net_current_density(
                [{"kind": "ambient-ion-collection"}])

    def test_contributor_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.net_current_density(["ambient-ion-collection"])


class SecondaryYieldTests(unittest.TestCase):

    def test_yield_at_peak_energy_is_near_the_maximum(self):
        value = logic.secondary_electron_yield(150.0, 2.1, 150.0)
        self.assertAlmostEqual(value, 2.1, places=1)

    def test_yield_is_zero_at_zero_energy(self):
        self.assertAlmostEqual(logic.secondary_electron_yield(0.0, 2.1, 150.0),
                               0.0)

    def test_yield_collapses_for_hot_plasma_electrons(self):
        value = logic.secondary_electron_yield(10000.0, 2.1, 150.0)
        self.assertLess(value, 0.1)
        self.assertGreater(value, 0.0)

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            logic.secondary_electron_yield(-1.0, 2.1, 150.0)

    def test_non_positive_peak_energy_raises(self):
        with self.assertRaises(ValueError):
            logic.secondary_electron_yield(100.0, 2.1, 0.0)


class PotentialDependentCurrentTests(unittest.TestCase):

    def test_negative_surface_retards_electrons(self):
        value = logic.electron_collection_current(4.0e-6, -10000.0, 10000.0)
        self.assertAlmostEqual(value, 4.0e-6 * math.exp(-1.0), places=12)

    def test_positive_surface_attracts_electrons(self):
        value = logic.electron_collection_current(4.0e-6, 5000.0, 10000.0)
        self.assertAlmostEqual(value, 6.0e-6, places=12)

    def test_zero_potential_returns_the_ambient_term(self):
        self.assertAlmostEqual(
            logic.electron_collection_current(4.0e-6, 0.0, 10000.0), 4.0e-6)

    def test_electron_temperature_must_be_positive(self):
        with self.assertRaises(ValueError):
            logic.electron_collection_current(4.0e-6, -100.0, 0.0)

    def test_negative_surface_accelerates_ions(self):
        value = logic.ion_collection_current(1.0e-7, -10000.0, 10000.0)
        self.assertAlmostEqual(value, 2.0e-7, places=14)

    def test_positive_surface_retards_ions(self):
        value = logic.ion_collection_current(1.0e-7, 10000.0, 10000.0)
        self.assertAlmostEqual(value, 1.0e-7 * math.exp(-1.0), places=14)

    def test_emission_survives_a_negative_surface(self):
        self.assertAlmostEqual(
            logic.emission_current(2.0e-5, -50.0, 1.5), 2.0e-5)

    def test_emission_is_suppressed_by_a_positive_barrier(self):
        value = logic.emission_current(2.0e-5, 1.5, 1.5)
        self.assertAlmostEqual(value, 2.0e-5 * math.exp(-1.0), places=12)

    def test_non_positive_escape_energy_raises(self):
        with self.assertRaises(ValueError):
            logic.emission_current(2.0e-5, 10.0, 0.0)


class CurrentBalanceTests(unittest.TestCase):

    def test_eclipse_surface_floats_strongly_negative(self):
        potential = logic.solve_equilibrium_potential(
            geo_storm_environment(), eclipse_surface())
        self.assertLess(potential, -10000.0)
        self.assertGreater(potential, -40000.0)

    def test_eclipse_balance_residual_is_null(self):
        env = geo_storm_environment()
        surface = eclipse_surface()
        potential = logic.solve_equilibrium_potential(env, surface)
        residual = logic.net_current_at_potential(env, surface, potential)
        self.assertAlmostEqual(residual, 0.0, delta=1.0e-12)

    def test_sunlit_surface_floats_slightly_positive(self):
        potential = logic.solve_equilibrium_potential(
            geo_storm_environment(), sunlit_surface())
        self.assertGreater(potential, 0.0)
        self.assertLess(potential, 50.0)

    def test_photoemission_raises_the_floating_potential(self):
        env = geo_storm_environment()
        dark = logic.solve_equilibrium_potential(env, eclipse_surface())
        lit = logic.solve_equilibrium_potential(env, sunlit_surface())
        self.assertGreater(lit, dark)

    def test_balance_is_deterministic(self):
        env = geo_storm_environment()
        first = logic.solve_equilibrium_potential(env, eclipse_surface())
        second = logic.solve_equilibrium_potential(env, eclipse_surface())
        self.assertEqual(first, second)

    def test_no_positive_charging_current_raises(self):
        env = geo_storm_environment()
        env["ion_current"] = 0.0
        with self.assertRaises(ValueError):
            logic.solve_equilibrium_potential(env, eclipse_surface())

    def test_ion_dominated_input_reports_an_unbracketed_root(self):
        env = geo_storm_environment()
        env["ion_current"] = 1.0e-3
        with self.assertRaises(ValueError):
            logic.solve_equilibrium_potential(env, eclipse_surface())

    def test_inverted_bracket_raises(self):
        with self.assertRaises(ValueError):
            logic.solve_equilibrium_potential(
                geo_storm_environment(), eclipse_surface(),
                lower_v=10.0, upper_v=-10.0)

    def test_environment_missing_key_raises(self):
        env = geo_storm_environment()
        del env["ion_temperature_ev"]
        with self.assertRaises(ValueError):
            logic.net_current_at_potential(env, eclipse_surface(), 0.0)

    def test_surface_missing_key_raises(self):
        surface = eclipse_surface()
        del surface["yield_max"]
        with self.assertRaises(ValueError):
            logic.net_current_at_potential(geo_storm_environment(), surface,
                                           0.0)

    def test_backscatter_fraction_above_unity_raises(self):
        surface = eclipse_surface()
        surface["backscatter_fraction"] = 1.4
        with self.assertRaises(ValueError):
            logic.net_current_at_potential(geo_storm_environment(), surface,
                                           0.0)

    def test_environment_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.net_current_at_potential(["hot-plasma"], eclipse_surface(),
                                           0.0)


class RegimeBandTests(unittest.TestCase):

    def test_low_band_below_the_first_edge(self):
        self.assertEqual(logic.categorize_charging_regime(-42.0),
                         "low-negative-surface-charging")

    def test_moderate_band_at_the_exact_edge(self):
        self.assertEqual(logic.categorize_charging_regime(-100.0),
                         "moderate-negative-surface-charging")

    def test_severe_band_at_the_exact_edge(self):
        self.assertEqual(logic.categorize_charging_regime(-1000.0),
                         "severe-negative-surface-charging")

    def test_edge_value_built_from_a_difference_still_lands_severe(self):
        potential = -(0.3 + 0.6 + 999.1)
        self.assertEqual(logic.categorize_charging_regime(potential),
                         "severe-negative-surface-charging")

    def test_positive_polarity_is_reported(self):
        self.assertEqual(logic.categorize_charging_regime(2.5),
                         "low-positive-surface-charging")

    def test_non_finite_potential_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_charging_regime(float("nan"))


class DifferentialChargingTests(unittest.TestCase):

    def test_differential_picks_the_extreme_pair(self):
        result = logic.differential_charging(
            {"array": 3.0, "kapton": -1200.0, "radiator": -50.0})
        self.assertAlmostEqual(result["differential_v"], 1203.0)
        self.assertEqual(result["most_positive"], "array")
        self.assertEqual(result["most_negative"], "kapton")

    def test_single_surface_raises(self):
        with self.assertRaises(ValueError):
            logic.differential_charging({"array": 3.0})

    def test_potentials_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.differential_charging([3.0, -1200.0])

    def test_offset_exactly_at_the_threshold_is_compliant(self):
        result = logic.assess_differential_charging(
            {"array": 0.1 + 0.2, "kapton": -399.7}, 400.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_offset_above_the_threshold_is_reported(self):
        result = logic.assess_differential_charging(
            {"array": 3.0, "kapton": -1200.0}, 400.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_differential_charging({"a": 1.0, "b": -1.0}, 0.0)


class AssessmentTests(unittest.TestCase):

    def test_geo_eclipse_pair_is_not_compliant(self):
        report = logic.assess_surface_charging(
            geo_storm_environment(), [eclipse_surface(), sunlit_surface()],
            400.0)
        self.assertFalse(report["compliant"])
        self.assertEqual(len(report["surfaces"]), 2)
        self.assertTrue(any("severe" in f for f in report["findings"]))

    def test_benign_plasma_pair_is_compliant(self):
        env = {
            "electron_current": 1.0e-6,
            "ion_current": 4.0e-7,
            "electron_temperature_ev": 1.0,
            "ion_temperature_ev": 1.0,
        }
        surfaces = [
            {"name": "grounded-radiator", "yield_max": 1.4,
             "energy_max_ev": 300.0, "sunlit": False},
            {"name": "array-coverglass", "yield_max": 1.4,
             "energy_max_ev": 300.0, "sunlit": True,
             "photoemission_current": 2.0e-6},
        ]
        report = logic.assess_surface_charging(env, surfaces, 400.0)
        self.assertTrue(report["compliant"])
        self.assertIsNotNone(report["differential"])

    def test_duplicate_surface_name_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_surface_charging(
                geo_storm_environment(),
                [eclipse_surface(), eclipse_surface()], 400.0)

    def test_empty_surface_inventory_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_surface_charging(geo_storm_environment(), [], 400.0)

    def test_single_surface_report_has_no_differential(self):
        report = logic.assess_surface_charging(
            geo_storm_environment(), [sunlit_surface()], 400.0)
        self.assertIsNone(report["differential"])
        self.assertTrue(report["compliant"])


if __name__ == "__main__":
    unittest.main()
