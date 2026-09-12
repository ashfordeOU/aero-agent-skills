"""
Contract tests for e1012_bg_nuclear_logic.py — ECSS-E-ST-10-12C §10.4.3.

Run: python3 test_e1012_bg_nuclear.py
Expected: OK
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bg_nuclear_logic import (
    nuclear_interaction_length,
    interaction_probability,
    secondary_neutron_yield,
    nuclear_background_rate,
    check_background_budget,
)


class TestNuclearInteractionLength(unittest.TestCase):

    def test_aluminium_returns_known_value(self):
        result = nuclear_interaction_length("aluminium")
        self.assertAlmostEqual(result, 106.4, places=1)

    def test_lookup_is_case_insensitive(self):
        self.assertAlmostEqual(
            nuclear_interaction_length("Aluminium"),
            nuclear_interaction_length("aluminium"),
        )

    def test_polyethylene_is_shorter_than_lead(self):
        self.assertLess(
            nuclear_interaction_length("polyethylene"),
            nuclear_interaction_length("lead"),
        )

    def test_unknown_material_raises_value_error(self):
        with self.assertRaises(ValueError):
            nuclear_interaction_length("unobtainium")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            nuclear_interaction_length("")


class TestInteractionProbability(unittest.TestCase):

    def test_zero_thickness_gives_zero_probability(self):
        p = interaction_probability(0.0, 106.4)
        self.assertAlmostEqual(p, 0.0)

    def test_one_interaction_length_gives_1_minus_1_over_e(self):
        lam = 106.4
        p = interaction_probability(lam, lam)
        expected = 1.0 - math.exp(-1.0)
        self.assertAlmostEqual(p, expected, places=10)

    def test_probability_increases_with_thickness(self):
        lam = 106.4
        p_thin = interaction_probability(10.0, lam)
        p_thick = interaction_probability(50.0, lam)
        self.assertLess(p_thin, p_thick)

    def test_probability_bounded_below_one(self):
        p = interaction_probability(1000.0, 106.4)
        self.assertLess(p, 1.0)
        self.assertGreater(p, 0.0)

    def test_negative_areal_density_raises(self):
        with self.assertRaises(ValueError):
            interaction_probability(-1.0, 106.4)

    def test_zero_interaction_length_raises(self):
        with self.assertRaises(ValueError):
            interaction_probability(10.0, 0.0)


class TestSecondaryNeutronYield(unittest.TestCase):

    def test_below_threshold_gives_zero(self):
        self.assertEqual(secondary_neutron_yield(15.0), 0.0)

    def test_at_threshold_gives_zero(self):
        self.assertAlmostEqual(secondary_neutron_yield(20.0), 0.0, places=10)

    def test_ten_times_threshold_gives_half(self):
        # n_bar = 0.5 * log10(200 / 20) = 0.5 * 1.0 = 0.5
        self.assertAlmostEqual(secondary_neutron_yield(200.0), 0.5, places=10)

    def test_yield_increases_with_energy(self):
        self.assertLess(
            secondary_neutron_yield(100.0),
            secondary_neutron_yield(1000.0),
        )

    def test_non_positive_energy_raises(self):
        with self.assertRaises(ValueError):
            secondary_neutron_yield(0.0)

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            secondary_neutron_yield(-50.0)


class TestNuclearBackgroundRate(unittest.TestCase):

    def test_zero_flux_gives_zero_rate(self):
        result = nuclear_background_rate(
            particle_flux_cm2_s=0.0,
            detector_area_cm2=10.0,
            areal_density_g_cm2=50.0,
            material="aluminium",
            incident_energy_mev=500.0,
        )
        self.assertAlmostEqual(result["background_rate_hz"], 0.0)

    def test_below_threshold_energy_gives_zero_rate(self):
        result = nuclear_background_rate(
            particle_flux_cm2_s=1e4,
            detector_area_cm2=10.0,
            areal_density_g_cm2=50.0,
            material="aluminium",
            incident_energy_mev=10.0,
        )
        self.assertAlmostEqual(result["background_rate_hz"], 0.0)
        self.assertAlmostEqual(result["secondary_yield"], 0.0)

    def test_result_keys_present(self):
        result = nuclear_background_rate(
            particle_flux_cm2_s=1e3,
            detector_area_cm2=5.0,
            areal_density_g_cm2=30.0,
            material="aluminium",
            incident_energy_mev=100.0,
        )
        for key in (
            "interaction_probability",
            "secondary_yield",
            "interactions_per_second",
            "background_rate_hz",
            "flag",
        ):
            self.assertIn(key, result)

    def test_high_areal_density_triggers_flag(self):
        # 200 g/cm² >> 0.1 * 106.4, so interaction_probability >> 0.1
        result = nuclear_background_rate(
            particle_flux_cm2_s=1e3,
            detector_area_cm2=5.0,
            areal_density_g_cm2=200.0,
            material="aluminium",
            incident_energy_mev=500.0,
        )
        self.assertIsNotNone(result["flag"])
        self.assertIn("HIGH_INTERACTION_PROBABILITY", result["flag"])

    def test_thin_slab_below_flag_threshold(self):
        # 1 g/cm² is tiny compared to lambda_I = 106.4 → P ≈ 0.0094 < 0.1
        result = nuclear_background_rate(
            particle_flux_cm2_s=1e3,
            detector_area_cm2=5.0,
            areal_density_g_cm2=1.0,
            material="aluminium",
            incident_energy_mev=500.0,
        )
        self.assertIsNone(result["flag"])

    def test_deposit_fraction_zero_gives_zero_rate(self):
        result = nuclear_background_rate(
            particle_flux_cm2_s=1e4,
            detector_area_cm2=10.0,
            areal_density_g_cm2=50.0,
            material="aluminium",
            incident_energy_mev=500.0,
            secondary_deposit_fraction=0.0,
        )
        self.assertAlmostEqual(result["background_rate_hz"], 0.0)

    def test_rate_scales_linearly_with_flux(self):
        base = nuclear_background_rate(
            particle_flux_cm2_s=1e3,
            detector_area_cm2=10.0,
            areal_density_g_cm2=50.0,
            material="aluminium",
            incident_energy_mev=500.0,
        )
        double = nuclear_background_rate(
            particle_flux_cm2_s=2e3,
            detector_area_cm2=10.0,
            areal_density_g_cm2=50.0,
            material="aluminium",
            incident_energy_mev=500.0,
        )
        self.assertAlmostEqual(
            double["background_rate_hz"],
            2.0 * base["background_rate_hz"],
            places=10,
        )

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            nuclear_background_rate(
                particle_flux_cm2_s=-1.0,
                detector_area_cm2=10.0,
                areal_density_g_cm2=50.0,
                material="aluminium",
                incident_energy_mev=500.0,
            )

    def test_zero_detector_area_raises(self):
        with self.assertRaises(ValueError):
            nuclear_background_rate(
                particle_flux_cm2_s=1e3,
                detector_area_cm2=0.0,
                areal_density_g_cm2=50.0,
                material="aluminium",
                incident_energy_mev=500.0,
            )

    def test_deposit_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            nuclear_background_rate(
                particle_flux_cm2_s=1e3,
                detector_area_cm2=10.0,
                areal_density_g_cm2=50.0,
                material="aluminium",
                incident_energy_mev=500.0,
                secondary_deposit_fraction=1.5,
            )


class TestCheckBackgroundBudget(unittest.TestCase):

    def test_rate_below_budget_is_compliant(self):
        result = check_background_budget(
            background_rate_hz=0.5,
            budget_hz=1.0,
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["ratio"], 0.5, places=10)

    def test_rate_equal_to_budget_is_compliant(self):
        result = check_background_budget(
            background_rate_hz=1.0,
            budget_hz=1.0,
        )
        self.assertTrue(result["compliant"])

    def test_rate_above_budget_is_non_compliant(self):
        result = check_background_budget(
            background_rate_hz=2.0,
            budget_hz=1.0,
        )
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["ratio"], 2.0, places=10)

    def test_margin_db_positive_when_compliant(self):
        result = check_background_budget(0.1, 1.0)
        self.assertGreater(result["margin_db"], 0.0)

    def test_margin_db_negative_when_non_compliant(self):
        result = check_background_budget(10.0, 1.0)
        self.assertLess(result["margin_db"], 0.0)

    def test_zero_rate_gives_infinite_margin(self):
        result = check_background_budget(0.0, 1.0)
        self.assertTrue(math.isinf(result["margin_db"]))
        self.assertTrue(result["compliant"])

    def test_zero_budget_raises(self):
        with self.assertRaises(ValueError):
            check_background_budget(1.0, 0.0)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            check_background_budget(-1.0, 1.0)

    def test_status_message_contains_compliant_keyword(self):
        result = check_background_budget(0.5, 1.0)
        self.assertIn("COMPLIANT", result["status_message"])

    def test_status_message_contains_non_compliant_keyword(self):
        result = check_background_budget(5.0, 1.0)
        self.assertIn("NON_COMPLIANT", result["status_message"])


if __name__ == "__main__":
    unittest.main()
