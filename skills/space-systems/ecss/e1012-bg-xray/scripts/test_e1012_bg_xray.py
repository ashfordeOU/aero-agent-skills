"""
test_e1012_bg_xray.py

Offline deterministic unittest for e1012_bg_xray_logic.py.
Run: python3 test_e1012_bg_xray.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e1012_bg_xray_logic as logic


class TestElementLookup(unittest.TestCase):

    def test_known_element_al_k_alpha(self):
        data = logic.get_element_data("Al")
        self.assertAlmostEqual(data["k_alpha_keV"], 1.487, places=2)

    def test_known_element_fe_k_edge(self):
        data = logic.get_element_data("Fe")
        self.assertAlmostEqual(data["k_edge_keV"], 7.112, places=2)

    def test_known_element_cu_fluorescence_yield(self):
        data = logic.get_element_data("Cu")
        self.assertAlmostEqual(data["fluorescence_yield"], 0.440, places=2)

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            logic.get_element_data("Xx")

    def test_empty_symbol_raises(self):
        with self.assertRaises(ValueError):
            logic.get_element_data("")

    def test_all_elements_have_valid_fluorescence_yield(self):
        for sym in logic.MATERIAL_DB:
            data = logic.get_element_data(sym)
            self.assertGreater(data["fluorescence_yield"], 0.0)
            self.assertLessEqual(data["fluorescence_yield"], 1.0)

    def test_all_elements_k_alpha_below_k_edge(self):
        # K-alpha emission energy is always below the K-shell absorption edge
        for sym in logic.MATERIAL_DB:
            data = logic.get_element_data(sym)
            self.assertLess(data["k_alpha_keV"], data["k_edge_keV"])


class TestExcitationCondition(unittest.TestCase):

    def test_excited_above_edge(self):
        # Fe K-edge 7.112 keV; 10 keV primary exceeds it
        self.assertTrue(logic.is_line_excited("Fe", 10.0))

    def test_not_excited_below_edge(self):
        # Fe K-edge 7.112 keV; 5 keV primary cannot excite K-shell
        self.assertFalse(logic.is_line_excited("Fe", 5.0))

    def test_not_excited_at_exact_edge(self):
        # Strict inequality: energy must be strictly above the edge
        edge = logic.get_element_data("Fe")["k_edge_keV"]
        self.assertFalse(logic.is_line_excited("Fe", edge))

    def test_cross_section_zero_at_edge(self):
        edge = logic.get_element_data("Al")["k_edge_keV"]
        self.assertEqual(logic.photoelectric_cross_section("Al", edge), 0.0)

    def test_cross_section_zero_below_edge(self):
        self.assertEqual(logic.photoelectric_cross_section("Al", 1.0), 0.0)

    def test_cross_section_positive_above_edge(self):
        sigma = logic.photoelectric_cross_section("Al", 2.0)
        self.assertGreater(sigma, 0.0)

    def test_cross_section_decreases_with_increasing_energy(self):
        # E⁻³ dependence: higher primary energy → lower cross-section
        s_low = logic.photoelectric_cross_section("Fe", 8.0)
        s_high = logic.photoelectric_cross_section("Fe", 20.0)
        self.assertGreater(s_low, s_high)

    def test_cross_section_cube_law_ratio(self):
        # σ(2×E_edge) / σ(E_edge+ε) ≈ (1/2)³ = 0.125 approximately
        data = logic.get_element_data("Ti")
        e_edge = data["k_edge_keV"]
        s1 = logic.photoelectric_cross_section("Ti", e_edge * 1.001)
        s2 = logic.photoelectric_cross_section("Ti", e_edge * 2.0)
        ratio = s2 / s1
        # Expect ratio ≈ (1/2)³ / (1.001)³ ≈ 0.124
        self.assertAlmostEqual(ratio, (1.0 / 2.0) ** 3 / (1.001) ** 3, places=2)


class TestFluorescentYield(unittest.TestCase):

    def test_yield_zero_when_not_excited(self):
        # Al K-edge 1.56 keV; primary at 1.0 keV → no excitation
        y = logic.compute_fluorescent_yield(
            "Al", 1.0,
            fluence_phcm2=1e9,
            areal_density_gcm2=0.1,
            detector_solid_angle_sr=0.01,
        )
        self.assertEqual(y, 0.0)

    def test_yield_positive_when_excited(self):
        y = logic.compute_fluorescent_yield(
            "Fe", 10.0,
            fluence_phcm2=1e9,
            areal_density_gcm2=0.5,
            detector_solid_angle_sr=0.1,
        )
        self.assertGreater(y, 0.0)

    def test_zero_fluence_gives_zero_yield(self):
        y = logic.compute_fluorescent_yield(
            "Fe", 10.0,
            fluence_phcm2=0.0,
            areal_density_gcm2=0.5,
            detector_solid_angle_sr=0.1,
        )
        self.assertEqual(y, 0.0)

    def test_zero_solid_angle_gives_zero_yield(self):
        y = logic.compute_fluorescent_yield(
            "Fe", 10.0,
            fluence_phcm2=1e9,
            areal_density_gcm2=0.5,
            detector_solid_angle_sr=0.0,
        )
        self.assertEqual(y, 0.0)

    def test_negative_fluence_raises(self):
        with self.assertRaises(ValueError):
            logic.compute_fluorescent_yield(
                "Fe", 10.0,
                fluence_phcm2=-1.0,
                areal_density_gcm2=0.5,
                detector_solid_angle_sr=0.1,
            )

    def test_negative_areal_density_raises(self):
        with self.assertRaises(ValueError):
            logic.compute_fluorescent_yield(
                "Fe", 10.0,
                fluence_phcm2=1e9,
                areal_density_gcm2=-0.1,
                detector_solid_angle_sr=0.1,
            )

    def test_solid_angle_exceeds_4pi_raises(self):
        with self.assertRaises(ValueError):
            logic.compute_fluorescent_yield(
                "Fe", 10.0,
                fluence_phcm2=1e9,
                areal_density_gcm2=0.5,
                detector_solid_angle_sr=4.0 * math.pi + 0.1,
            )

    def test_invalid_line_name_raises(self):
        with self.assertRaises(ValueError):
            logic.compute_fluorescent_yield(
                "Fe", 10.0,
                fluence_phcm2=1e9,
                areal_density_gcm2=0.5,
                detector_solid_angle_sr=0.1,
                line="l_alpha",
            )

    def test_k_alpha_yield_greater_than_k_beta(self):
        # K-alpha carries ~88% of K-vacancy X-ray emission
        y_alpha = logic.compute_fluorescent_yield(
            "Fe", 10.0, 1e9, 0.5, 0.1, line="k_alpha"
        )
        y_beta = logic.compute_fluorescent_yield(
            "Fe", 10.0, 1e9, 0.5, 0.1, line="k_beta"
        )
        self.assertGreater(y_alpha, y_beta)

    def test_yield_scales_linearly_with_fluence(self):
        base = logic.compute_fluorescent_yield("Ni", 10.0, 1e9, 0.3, 0.05)
        double = logic.compute_fluorescent_yield("Ni", 10.0, 2e9, 0.3, 0.05)
        self.assertAlmostEqual(double, 2.0 * base, places=6)

    def test_yield_scales_linearly_with_areal_density(self):
        base = logic.compute_fluorescent_yield("Cu", 10.0, 1e9, 0.2, 0.05)
        triple = logic.compute_fluorescent_yield("Cu", 10.0, 1e9, 0.6, 0.05)
        self.assertAlmostEqual(triple, 3.0 * base, places=6)


class TestMaterialBackground(unittest.TestCase):

    def test_assess_contributes_true_when_excited(self):
        result = logic.assess_material_background("Cu", 10.0, 1e9, 0.3, 0.05)
        self.assertTrue(result["contributes"])

    def test_assess_contributes_false_when_not_excited(self):
        # Cu K-edge 8.979 keV; 5 keV primary cannot excite Cu K-shell
        result = logic.assess_material_background("Cu", 5.0, 1e9, 0.3, 0.05)
        self.assertFalse(result["contributes"])

    def test_assess_returns_correct_element_key(self):
        result = logic.assess_material_background("Ti", 6.0, 1e9, 0.2, 0.01)
        self.assertEqual(result["element"], "Ti")

    def test_assess_total_equals_alpha_plus_beta(self):
        result = logic.assess_material_background("Fe", 15.0, 1e9, 0.4, 0.1)
        self.assertAlmostEqual(
            result["total_yield"],
            result["k_alpha_yield"] + result["k_beta_yield"],
            places=10,
        )

    def test_assess_k_alpha_energy_matches_database(self):
        result = logic.assess_material_background("Si", 5.0, 1e9, 0.1, 0.01)
        self.assertAlmostEqual(result["k_alpha_keV"], 1.740, places=2)


class TestBackgroundSpectrum(unittest.TestCase):

    def test_spectrum_length_matches_input(self):
        materials = [
            {"element": "Al", "fluence_phcm2": 1e10, "areal_density_gcm2": 0.2},
            {"element": "Fe", "fluence_phcm2": 1e10, "areal_density_gcm2": 0.1},
        ]
        results = logic.compute_background_spectrum(materials, 10.0, 0.05)
        self.assertEqual(len(results), 2)

    def test_spectrum_empty_input_returns_empty(self):
        results = logic.compute_background_spectrum([], 10.0, 0.05)
        self.assertEqual(results, [])

    def test_al_excited_fe_not_at_low_primary_energy(self):
        # At 2 keV: Al edge 1.56 keV is below → Al excited; Fe edge 7.11 keV above → Fe not excited
        materials = [
            {"element": "Al", "fluence_phcm2": 1e10, "areal_density_gcm2": 0.3},
            {"element": "Fe", "fluence_phcm2": 1e10, "areal_density_gcm2": 0.3},
        ]
        results = logic.compute_background_spectrum(materials, 2.0, 0.05)
        al_rec = next(r for r in results if r["element"] == "Al")
        fe_rec = next(r for r in results if r["element"] == "Fe")
        self.assertTrue(al_rec["contributes"])
        self.assertFalse(fe_rec["contributes"])

    def test_all_materials_excited_at_high_primary_energy(self):
        # At 15 keV all listed elements are excited (Cu edge ≈ 9.0 keV < 15 keV)
        materials = [
            {"element": "Al", "fluence_phcm2": 1e10, "areal_density_gcm2": 0.3},
            {"element": "Fe", "fluence_phcm2": 1e10, "areal_density_gcm2": 0.3},
            {"element": "Cu", "fluence_phcm2": 1e10, "areal_density_gcm2": 0.2},
        ]
        results = logic.compute_background_spectrum(materials, 15.0, 0.05)
        for rec in results:
            self.assertTrue(rec["contributes"], msg=f"{rec['element']} should contribute")

    def test_spectrum_order_preserved(self):
        materials = [
            {"element": "Fe", "fluence_phcm2": 1e9, "areal_density_gcm2": 0.1},
            {"element": "Al", "fluence_phcm2": 1e9, "areal_density_gcm2": 0.1},
            {"element": "Ni", "fluence_phcm2": 1e9, "areal_density_gcm2": 0.1},
        ]
        results = logic.compute_background_spectrum(materials, 12.0, 0.1)
        self.assertEqual([r["element"] for r in results], ["Fe", "Al", "Ni"])


class TestDominantLineFlagging(unittest.TestCase):

    def test_high_yield_line_flagged(self):
        materials = [
            {"element": "Fe", "fluence_phcm2": 1e12, "areal_density_gcm2": 1.0},
        ]
        bg = logic.compute_background_spectrum(materials, 10.0, 0.1)
        flagged = logic.flag_dominant_lines(bg, threshold_photons=0.0)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["element"], "Fe")

    def test_line_below_threshold_not_flagged(self):
        materials = [
            {"element": "Fe", "fluence_phcm2": 1e9, "areal_density_gcm2": 0.1},
        ]
        bg = logic.compute_background_spectrum(materials, 10.0, 0.01)
        total = bg[0]["total_yield"]
        flagged = logic.flag_dominant_lines(bg, threshold_photons=total + 1.0)
        self.assertEqual(len(flagged), 0)

    def test_not_excited_material_never_flagged(self):
        # Cu K-edge 8.979 keV; primary at 5 keV → yield = 0 → never dominant
        materials = [
            {"element": "Cu", "fluence_phcm2": 1e15, "areal_density_gcm2": 10.0},
        ]
        bg = logic.compute_background_spectrum(materials, 5.0, 0.1)
        flagged = logic.flag_dominant_lines(bg, threshold_photons=0.0)
        self.assertEqual(len(flagged), 0)

    def test_only_dominant_lines_returned(self):
        # Al: excited at 10 keV (large areal density); Fe: excited at 10 keV (tiny density)
        materials = [
            {"element": "Al", "fluence_phcm2": 1e12, "areal_density_gcm2": 5.0},
            {"element": "Fe", "fluence_phcm2": 1e6, "areal_density_gcm2": 0.0001},
        ]
        bg = logic.compute_background_spectrum(materials, 10.0, 0.1)
        al_total = bg[0]["total_yield"]
        fe_total = bg[1]["total_yield"]
        # Set threshold between Fe and Al totals
        threshold = (al_total + fe_total) / 2.0
        flagged = logic.flag_dominant_lines(bg, threshold_photons=threshold)
        elements_flagged = [r["element"] for r in flagged]
        self.assertIn("Al", elements_flagged)
        self.assertNotIn("Fe", elements_flagged)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            logic.flag_dominant_lines([], threshold_photons=-1.0)

    def test_empty_background_returns_empty(self):
        flagged = logic.flag_dominant_lines([], threshold_photons=100.0)
        self.assertEqual(flagged, [])


if __name__ == "__main__":
    unittest.main()
