"""
Gate-3 contract tests for e1012-bg-calc radiation background calculation logic.
Run: python3 test_e1012_bg_calc.py
Expected output: OK
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bg_calc_logic import (
    compute_energy_deposition,
    build_energy_deposition_spectrum,
    compute_nuclear_interaction_rate,
    attenuate_flux,
    check_dose_budget,
    AVOGADRO,
    MEV_PER_G_PER_GY,
)


class TestComputeEnergyDeposition(unittest.TestCase):

    def test_proton_basic_dose_value(self):
        result = compute_energy_deposition(
            particle_type="proton",
            flux=1e4,
            let=0.15,
            areal_density=0.1,
            exposure_s=1.0,
        )
        expected_fluence = 1e4
        self.assertAlmostEqual(result["total_fluence_cm2"], expected_fluence, places=6)
        expected_energy = 0.15 * 0.1 * 1e4
        self.assertAlmostEqual(result["energy_dep_MeV_per_cm2"], expected_energy, places=6)
        expected_dose = expected_energy / (MEV_PER_G_PER_GY * 0.1)
        self.assertAlmostEqual(result["dose_Gy"], expected_dose, places=10)

    def test_electron_exposure_scaling(self):
        result_1s = compute_energy_deposition("electron", 500.0, 0.20, 0.5, 1.0)
        result_2s = compute_energy_deposition("electron", 500.0, 0.20, 0.5, 2.0)
        self.assertAlmostEqual(result_2s["dose_Gy"], 2.0 * result_1s["dose_Gy"], places=10)

    def test_alpha_particle_returns_correct_keys(self):
        result = compute_energy_deposition("alpha", 1e3, 1.5, 0.2, 60.0)
        for key in ("particle_type", "total_fluence_cm2",
                    "energy_dep_MeV_per_cm2", "dose_Gy"):
            self.assertIn(key, result)
        self.assertEqual(result["particle_type"], "alpha")

    def test_invalid_particle_raises(self):
        with self.assertRaises(ValueError):
            compute_energy_deposition("muon", 1e4, 0.15, 0.1, 1.0)

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            compute_energy_deposition("proton", -1.0, 0.15, 0.1, 1.0)

    def test_zero_let_raises(self):
        with self.assertRaises(ValueError):
            compute_energy_deposition("neutron", 1e4, 0.0, 0.1, 1.0)

    def test_zero_exposure_raises(self):
        with self.assertRaises(ValueError):
            compute_energy_deposition("photon", 1e4, 0.02, 0.1, 0.0)


class TestBuildEnergyDepositionSpectrum(unittest.TestCase):

    def _simple_spectrum(self):
        return [(1.0, 1e3), (10.0, 2e3), (100.0, 5e2)]

    def test_total_dose_is_sum_of_bins(self):
        result = build_energy_deposition_spectrum(
            "proton", self._simple_spectrum(), 0.1, 1.0
        )
        bin_sum = sum(b["dose_bin_Gy"] for b in result["bins"])
        self.assertAlmostEqual(result["total_dose_Gy"], bin_sum, places=12)

    def test_correct_number_of_bins(self):
        spectrum = [(float(e), 1e3) for e in range(1, 6)]
        result = build_energy_deposition_spectrum("electron", spectrum, 0.2, 10.0)
        self.assertEqual(len(result["bins"]), 5)

    def test_custom_let_fn_applied(self):
        spectrum = [(10.0, 1e4), (20.0, 1e4)]
        let_fn = lambda e: 0.5
        result = build_energy_deposition_spectrum(
            "proton", spectrum, 0.1, 1.0, let_fn=let_fn
        )
        for b in result["bins"]:
            self.assertGreater(b["dose_bin_Gy"], 0.0)

    def test_empty_spectrum_raises(self):
        with self.assertRaises(ValueError):
            build_energy_deposition_spectrum("proton", [], 0.1, 1.0)

    def test_non_ascending_energy_raises(self):
        with self.assertRaises(ValueError):
            build_energy_deposition_spectrum(
                "proton", [(10.0, 1e3), (5.0, 1e3)], 0.1, 1.0
            )

    def test_negative_diff_flux_raises(self):
        with self.assertRaises(ValueError):
            build_energy_deposition_spectrum(
                "proton", [(1.0, -1.0), (2.0, 1e3)], 0.1, 1.0
            )


class TestComputeNuclearInteractionRate(unittest.TestCase):

    def test_silicon_proton_rate_order_of_magnitude(self):
        # Silicon: A = 28 g/mol, rho = 2.33 g/cm³
        result = compute_nuclear_interaction_rate(
            particle_type="proton",
            flux=1e5,
            cross_section_cm2=4.0e-25,
            material_density=2.33,
            thickness_cm=0.05,
            atomic_mass_g_mol=28.085,
        )
        n_expected = (2.33 * AVOGADRO) / 28.085
        self.assertAlmostEqual(result["n_atoms_per_cm3"], n_expected, delta=1e15)
        self.assertGreater(result["rate_per_cm3_per_s"], 0.0)
        self.assertGreater(result["rate_per_cm2_per_s"], 0.0)
        # Volumetric × thickness = areal
        self.assertAlmostEqual(
            result["rate_per_cm2_per_s"],
            result["rate_per_cm3_per_s"] * 0.05,
            places=10,
        )

    def test_rate_scales_linearly_with_flux(self):
        kwargs = dict(
            particle_type="neutron",
            cross_section_cm2=6.0e-25,
            material_density=2.33,
            thickness_cm=0.1,
            atomic_mass_g_mol=28.085,
        )
        r1 = compute_nuclear_interaction_rate(flux=1e4, **kwargs)
        r2 = compute_nuclear_interaction_rate(flux=2e4, **kwargs)
        self.assertAlmostEqual(r2["rate_per_cm2_per_s"],
                               2.0 * r1["rate_per_cm2_per_s"], places=10)

    def test_invalid_cross_section_raises(self):
        with self.assertRaises(ValueError):
            compute_nuclear_interaction_rate(
                "proton", 1e4, 0.0, 2.33, 0.1, 28.085
            )

    def test_invalid_particle_raises(self):
        with self.assertRaises(ValueError):
            compute_nuclear_interaction_rate(
                "pion", 1e4, 4.0e-25, 2.33, 0.1, 28.085
            )


class TestAttenuateFlux(unittest.TestCase):

    def test_zero_shield_passes_full_flux(self):
        result = attenuate_flux("proton", 1e6, 10.0, 0.0)
        self.assertAlmostEqual(result["attenuation_factor"], 1.0, places=12)
        self.assertAlmostEqual(result["transmitted_flux"], 1e6, places=6)

    def test_one_mfp_attenuates_by_1_over_e(self):
        mfp = 5.0
        result = attenuate_flux("proton", 1e6, mfp, mfp)
        self.assertAlmostEqual(result["attenuation_factor"], math.exp(-1.0), places=10)

    def test_transmitted_less_than_incident_for_nonzero_shield(self):
        result = attenuate_flux("photon", 5e5, 8.0, 2.0)
        self.assertLess(result["transmitted_flux"], 5e5)

    def test_negative_shield_thickness_raises(self):
        with self.assertRaises(ValueError):
            attenuate_flux("neutron", 1e4, 10.0, -1.0)

    def test_invalid_mfp_raises(self):
        with self.assertRaises(ValueError):
            attenuate_flux("electron", 1e4, 0.0, 5.0)

    def test_result_keys_present(self):
        result = attenuate_flux("alpha", 2e4, 3.0, 1.0)
        for key in ("particle_type", "incident_flux", "shield_thickness_cm",
                    "attenuation_factor", "transmitted_flux"):
            self.assertIn(key, result)


class TestCheckDoseBudget(unittest.TestCase):

    def test_passes_when_below_budget(self):
        result = check_dose_budget(0.5, 1.0)
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["margin_Gy"], 0.5, places=10)

    def test_fails_when_over_budget(self):
        result = check_dose_budget(1.5, 1.0)
        self.assertFalse(result["passes"])
        self.assertAlmostEqual(result["margin_Gy"], -0.5, places=10)

    def test_passes_exactly_at_budget(self):
        result = check_dose_budget(1.0, 1.0)
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["margin_Gy"], 0.0, places=12)

    def test_zero_computed_dose_is_valid(self):
        result = check_dose_budget(0.0, 0.1)
        self.assertTrue(result["passes"])

    def test_zero_allowable_budget_raises(self):
        with self.assertRaises(ValueError):
            check_dose_budget(0.5, 0.0)

    def test_negative_computed_dose_raises(self):
        with self.assertRaises(ValueError):
            check_dose_budget(-0.1, 1.0)


if __name__ == "__main__":
    unittest.main()
