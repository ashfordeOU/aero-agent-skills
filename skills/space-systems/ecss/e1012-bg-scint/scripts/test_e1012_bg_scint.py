"""
Gate 3 contract tests for e1012-bg-scint.
Run: python3 test_e1012_bg_scint.py
stdlib unittest only — no external dependencies, fully offline.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bg_scint_logic import (
    MATERIALS,
    PARTICLES,
    assess_background,
    background_rate,
    beta,
    cerenkov_threshold,
    cerenkov_yield_per_cm,
    scintillation_yield_per_cm,
    sin2_cerenkov,
)


# ---------------------------------------------------------------------------
# beta()
# ---------------------------------------------------------------------------

class TestBeta(unittest.TestCase):

    def test_electron_at_zero_kinetic_energy_is_zero(self):
        self.assertAlmostEqual(beta(0.0, "electron"), 0.0)

    def test_ultra_relativistic_electron_approaches_one(self):
        b = beta(1e6, "electron")   # 1 TeV electron
        self.assertGreater(b, 0.9999)
        self.assertLess(b, 1.0)

    def test_proton_at_1000_mev_kinetic(self):
        # E_total = 1938.272 MeV, β = sqrt(1-(938.272/1938.272)²) ≈ 0.875
        b = beta(1000.0, "proton")
        self.assertGreater(b, 0.87)
        self.assertLess(b, 0.89)

    def test_negative_kinetic_energy_raises(self):
        with self.assertRaises(ValueError):
            beta(-0.001, "electron")

    def test_unknown_particle_raises(self):
        with self.assertRaises(ValueError):
            beta(1.0, "neutrino")


# ---------------------------------------------------------------------------
# cerenkov_threshold()
# ---------------------------------------------------------------------------

class TestCerenkovThreshold(unittest.TestCase):

    def test_borosilicate_electron_threshold_is_positive(self):
        t = cerenkov_threshold("borosilicate", "electron")
        self.assertGreater(t, 0.0)

    def test_electron_threshold_in_borosilicate_below_1_mev(self):
        # β_min=1/1.47≈0.680 → γ_min≈1.364 → E_k≈0.186 MeV
        t = cerenkov_threshold("borosilicate", "electron")
        self.assertLess(t, 1.0)

    def test_proton_threshold_much_higher_than_electron(self):
        # Proton is 938/0.511 ≈ 1835× heavier → threshold far higher
        t_e = cerenkov_threshold("borosilicate", "electron")
        t_p = cerenkov_threshold("borosilicate", "proton")
        self.assertGreater(t_p, t_e * 100)

    def test_lower_refractive_index_gives_higher_threshold(self):
        # mgf2 (n=1.38) requires higher β_min than bk7 (n=1.52)
        t_mgf2 = cerenkov_threshold("mgf2", "electron")
        t_bk7  = cerenkov_threshold("bk7",  "electron")
        self.assertGreater(t_mgf2, t_bk7)

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            cerenkov_threshold("unobtanium", "electron")

    def test_unknown_particle_raises(self):
        with self.assertRaises(ValueError):
            cerenkov_threshold("borosilicate", "muon")


# ---------------------------------------------------------------------------
# sin2_cerenkov()
# ---------------------------------------------------------------------------

class TestSin2Cerenkov(unittest.TestCase):

    def test_below_threshold_returns_zero(self):
        # β=0.5, n=1.47 → βn=0.735 < 1 → no emission
        self.assertEqual(sin2_cerenkov(0.5, 1.47), 0.0)

    def test_above_threshold_returns_positive(self):
        # β=0.99, n=1.47 → βn≈1.455 > 1
        self.assertGreater(sin2_cerenkov(0.99, 1.47), 0.0)

    def test_ultra_relativistic_limit(self):
        # β→1 → sin²θ_C → 1 − 1/n²
        n = 1.5
        expected = 1.0 - 1.0 / (n ** 2)
        self.assertAlmostEqual(sin2_cerenkov(0.9999999, n), expected, places=4)


# ---------------------------------------------------------------------------
# cerenkov_yield_per_cm()
# ---------------------------------------------------------------------------

class TestCerenkovYieldPerCm(unittest.TestCase):

    def test_very_low_energy_electron_gives_zero_yield(self):
        # 0.001 MeV << threshold (~0.186 MeV for borosilicate)
        y = cerenkov_yield_per_cm(0.001, "borosilicate", "electron")
        self.assertEqual(y, 0.0)

    def test_high_energy_electron_gives_positive_yield(self):
        y = cerenkov_yield_per_cm(100.0, "borosilicate", "electron")
        self.assertGreater(y, 0.0)

    def test_alpha_yield_four_times_proton_at_same_ultra_relativistic_energy(self):
        # At 1 TeV both particles are fully relativistic → same sin²θ_C
        # yield ratio = z²_alpha / z²_proton = 4/1 = 4
        e = 1e6  # MeV (1 TeV)
        y_p = cerenkov_yield_per_cm(e, "borosilicate", "proton")
        y_a = cerenkov_yield_per_cm(e, "borosilicate", "alpha")
        self.assertAlmostEqual(y_a / y_p, 4.0, places=1)

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            cerenkov_yield_per_cm(100.0, "sapphire", "electron")


# ---------------------------------------------------------------------------
# scintillation_yield_per_cm()
# ---------------------------------------------------------------------------

class TestScintillationYieldPerCm(unittest.TestCase):

    def test_positive_for_all_supported_combinations(self):
        for p in PARTICLES:
            for m in MATERIALS:
                with self.subTest(particle=p, material=m):
                    y = scintillation_yield_per_cm(1.0, m, p)
                    self.assertGreater(y, 0.0)

    def test_alpha_yields_four_times_proton(self):
        # z²_alpha=4, z²_proton=1 → exact factor of 4
        y_p = scintillation_yield_per_cm(1.0, "borosilicate", "proton")
        y_a = scintillation_yield_per_cm(1.0, "borosilicate", "alpha")
        self.assertAlmostEqual(y_a / y_p, 4.0, places=5)

    def test_unknown_particle_raises(self):
        with self.assertRaises(ValueError):
            scintillation_yield_per_cm(1.0, "borosilicate", "pion")


# ---------------------------------------------------------------------------
# background_rate()
# ---------------------------------------------------------------------------

class TestBackgroundRate(unittest.TestCase):

    def _nominal(self, detector="pmt"):
        return background_rate(1e4, 1.0, 0.3, 10.0, "borosilicate", "electron", detector)

    def test_pmt_returns_required_keys(self):
        r = self._nominal("pmt")
        self.assertIn("cerenkov_rate",      r)
        self.assertIn("scintillation_rate", r)
        self.assertIn("total_rate",         r)

    def test_mcp_returns_required_keys(self):
        r = self._nominal("mcp")
        self.assertIn("total_rate", r)

    def test_total_equals_components_sum(self):
        r = self._nominal()
        self.assertAlmostEqual(
            r["total_rate"],
            r["cerenkov_rate"] + r["scintillation_rate"],
        )

    def test_zero_flux_gives_zero_total_rate(self):
        r = background_rate(0.0, 1.0, 0.3, 10.0, "borosilicate", "electron", "pmt")
        self.assertEqual(r["total_rate"], 0.0)

    def test_total_rate_scales_linearly_with_flux(self):
        r1 = background_rate(1e3, 1.0, 0.3, 10.0, "borosilicate", "electron", "pmt")
        r2 = background_rate(2e3, 1.0, 0.3, 10.0, "borosilicate", "electron", "pmt")
        self.assertAlmostEqual(r2["total_rate"] / r1["total_rate"], 2.0, places=5)

    def test_invalid_detector_type_raises(self):
        with self.assertRaises(ValueError):
            background_rate(1e4, 1.0, 0.3, 10.0, "borosilicate", "electron", "ccd")

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            background_rate(-1.0, 1.0, 0.3, 10.0, "borosilicate", "electron", "pmt")

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            background_rate(1e4, 0.0, 0.3, 10.0, "borosilicate", "electron", "pmt")

    def test_zero_path_raises(self):
        with self.assertRaises(ValueError):
            background_rate(1e4, 1.0, 0.0, 10.0, "borosilicate", "electron", "pmt")


# ---------------------------------------------------------------------------
# assess_background()
# ---------------------------------------------------------------------------

class TestAssessBackground(unittest.TestCase):

    def test_rate_below_budget_returns_pass(self):
        result = assess_background(100.0, 1000.0)
        self.assertEqual(result["status"], "pass")

    def test_rate_above_budget_returns_fail(self):
        result = assess_background(1500.0, 1000.0)
        self.assertEqual(result["status"], "fail")

    def test_rate_equal_to_budget_returns_pass(self):
        result = assess_background(1000.0, 1000.0)
        self.assertEqual(result["status"], "pass")

    def test_margin_correct_for_pass_case(self):
        result = assess_background(300.0, 1000.0)
        self.assertAlmostEqual(result["margin"], 700.0)

    def test_margin_negative_for_fail_case(self):
        result = assess_background(1200.0, 1000.0)
        self.assertLess(result["margin"], 0.0)

    def test_ratio_correct(self):
        result = assess_background(250.0, 1000.0)
        self.assertAlmostEqual(result["ratio"], 0.25)

    def test_zero_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_background(100.0, 0.0)

    def test_negative_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_background(100.0, -500.0)


# ---------------------------------------------------------------------------
# End-to-end integration scenario
# ---------------------------------------------------------------------------

class TestEndToEndScenario(unittest.TestCase):
    """Simulate a complete §10.4.6 assessment for a PMT exposed to belt electrons."""

    def test_full_pmt_assessment_workflow(self):
        # Step 1: confirm 1 MeV electrons exceed Cerenkov threshold in borosilicate
        thr = cerenkov_threshold("borosilicate", "electron")
        self.assertLess(thr, 1.0)   # 1 MeV >> threshold

        # Step 2: compute background rate (flux=1e4 cm⁻²s⁻¹, area=2 cm², path=0.3 cm)
        r = background_rate(
            flux=1e4, area_cm2=2.0, path_cm=0.3,
            kinetic_mev=1.0, material="borosilicate",
            particle="electron", detector_type="pmt",
        )
        self.assertGreater(r["cerenkov_rate"],      0.0)
        self.assertGreater(r["scintillation_rate"], 0.0)
        self.assertGreater(r["total_rate"],         0.0)

        # Step 3: assess against a 5000 counts/s budget
        verdict = assess_background(r["total_rate"], budget_hz=5000.0)
        self.assertIn(verdict["status"], {"pass", "fail"})
        self.assertIsInstance(verdict["margin"], float)
        self.assertGreater(verdict["ratio"], 0.0)


if __name__ == "__main__":
    unittest.main()
