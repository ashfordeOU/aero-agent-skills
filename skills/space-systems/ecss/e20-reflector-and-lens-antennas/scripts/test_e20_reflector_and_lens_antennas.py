#!/usr/bin/env python3
"""Gate 3 contract test for e20-reflector-and-lens-antennas (stdlib only)."""

import unittest

import e20_reflector_and_lens_antennas_logic as L


def reflecting_spec(**overrides):
    spec = {
        "id": "main-reflector",
        "family": "metal-reflector",
        "frequency_hz": 20.0e9,
        "incidence_deg": 0.0,
        "conductivity_s_per_m": 3.5e7,
        "rms_roughness_m": 60.0e-6,
        "depolarisation_terms_db": [35.0, 38.0],
    }
    spec.update(overrides)
    return spec


def transmitting_spec(**overrides):
    spec = {
        "id": "radome",
        "family": "radome-wall",
        "frequency_hz": 20.0e9,
        "incidence_deg": 0.0,
        "thickness_m": 0.004,
        "relative_permittivity": 3.0,
        "loss_tangent": 0.005,
        "rms_roughness_m": 60.0e-6,
        "depolarisation_terms_db": [40.0],
    }
    spec.update(overrides)
    return spec


class TestSurfaceCategorization(unittest.TestCase):
    def test_reflecting_families_categorize_as_reflecting(self):
        for family in ("metal-reflector", "mesh-reflector", "grid-polariser",
                       "sub-reflector", "shaped-reflector"):
            self.assertEqual(L.categorize_surface(family), "reflecting")

    def test_transmitting_families_categorize_as_transmitting(self):
        for family in ("dielectric-lens", "radome-wall", "dichroic-panel",
                       "matching-layer", "transmit-window"):
            self.assertEqual(L.categorize_surface(family), "transmitting")

    def test_categorization_is_case_and_whitespace_tolerant(self):
        self.assertEqual(L.categorize_surface("  Metal-Reflector "), "reflecting")

    def test_unknown_family_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_surface("waveguide-horn")

    def test_empty_family_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_surface("   ")

    def test_non_string_family_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_surface(7)


class TestWavelengthAndSurfaceResistance(unittest.TestCase):
    def test_wavelength_at_20_ghz(self):
        self.assertAlmostEqual(L.wavelength_m(20.0e9), 0.0149896229, places=9)

    def test_wavelength_rejects_non_positive_frequency(self):
        with self.assertRaises(ValueError):
            L.wavelength_m(0.0)

    def test_surface_resistance_value(self):
        self.assertAlmostEqual(
            L.surface_resistance_ohm(20.0e9, 3.5e7), 0.0474964165, places=9
        )

    def test_surface_resistance_scales_as_root_frequency(self):
        low = L.surface_resistance_ohm(5.0e9, 3.5e7)
        high = L.surface_resistance_ohm(20.0e9, 3.5e7)
        self.assertAlmostEqual(high / low, 2.0, places=9)

    def test_surface_resistance_rejects_bad_frequency(self):
        with self.assertRaises(ValueError):
            L.surface_resistance_ohm(-1.0, 3.5e7)

    def test_surface_resistance_rejects_bad_conductivity(self):
        with self.assertRaises(ValueError):
            L.surface_resistance_ohm(20.0e9, 0.0)


class TestConductorLoss(unittest.TestCase):
    def test_absorptivity_grows_with_incidence(self):
        normal = L.conductor_absorptivity(20.0e9, 3.5e7, 0.0)
        oblique = L.conductor_absorptivity(20.0e9, 3.5e7, 60.0)
        self.assertGreater(oblique, normal)
        self.assertAlmostEqual(oblique / normal, 2.0, places=9)

    def test_absorptivity_rejects_a_poor_conductor(self):
        with self.assertRaises(ValueError):
            L.conductor_absorptivity(20.0e9, 1.0, 0.0)

    def test_absorptivity_rejects_grazing_incidence(self):
        with self.assertRaises(ValueError):
            L.conductor_absorptivity(20.0e9, 3.5e7, 90.0)

    def test_loss_value_at_normal_incidence(self):
        self.assertAlmostEqual(
            L.conductor_loss_db(20.0e9, 3.5e7, 0.0, 1), 0.00219071, places=8
        )

    def test_loss_scales_linearly_with_bounce_count(self):
        one = L.conductor_loss_db(20.0e9, 3.5e7, 30.0, 1)
        three = L.conductor_loss_db(20.0e9, 3.5e7, 30.0, 3)
        self.assertAlmostEqual(three / one, 3.0, places=9)

    def test_loss_rejects_non_integer_bounces(self):
        with self.assertRaises(ValueError):
            L.conductor_loss_db(20.0e9, 3.5e7, 0.0, 1.5)

    def test_loss_rejects_zero_bounces(self):
        with self.assertRaises(ValueError):
            L.conductor_loss_db(20.0e9, 3.5e7, 0.0, 0)


class TestDielectricLoss(unittest.TestCase):
    def test_refracted_path_equals_thickness_at_normal_incidence(self):
        self.assertAlmostEqual(L.refracted_path_m(0.004, 3.0, 0.0), 0.004, places=12)

    def test_refracted_path_exceeds_thickness_at_oblique_incidence(self):
        self.assertGreater(L.refracted_path_m(0.004, 3.0, 60.0), 0.004)

    def test_refracted_path_rejects_bad_thickness(self):
        with self.assertRaises(ValueError):
            L.refracted_path_m(0.0, 3.0, 0.0)

    def test_refracted_path_rejects_permittivity_below_unity(self):
        with self.assertRaises(ValueError):
            L.refracted_path_m(0.004, 0.5, 0.0)

    def test_dielectric_loss_value(self):
        self.assertAlmostEqual(
            L.dielectric_loss_db(20.0e9, 0.004, 3.0, 0.005, 0.0), 0.06306147, places=8
        )

    def test_dielectric_loss_grows_with_incidence(self):
        normal = L.dielectric_loss_db(20.0e9, 0.004, 3.0, 0.005, 0.0)
        oblique = L.dielectric_loss_db(20.0e9, 0.004, 3.0, 0.005, 45.0)
        self.assertGreater(oblique, normal)

    def test_lossless_wall_has_zero_loss(self):
        self.assertAlmostEqual(
            L.dielectric_loss_db(20.0e9, 0.004, 3.0, 0.0, 0.0), 0.0, places=12
        )

    def test_dielectric_loss_rejects_negative_loss_tangent(self):
        with self.assertRaises(ValueError):
            L.dielectric_loss_db(20.0e9, 0.004, 3.0, -0.001, 0.0)

    def test_dielectric_loss_rejects_loss_tangent_above_unity(self):
        with self.assertRaises(ValueError):
            L.dielectric_loss_db(20.0e9, 0.004, 3.0, 1.5, 0.0)

    def test_dielectric_loss_rejects_bad_frequency(self):
        with self.assertRaises(ValueError):
            L.dielectric_loss_db(0.0, 0.004, 3.0, 0.005, 0.0)


class TestDiffusivity(unittest.TestCase):
    def test_reflecting_specular_and_diffuse_sum_to_unity(self):
        out = L.diffusivity(60.0e-6, L.wavelength_m(20.0e9), "reflecting", 0.0)
        self.assertAlmostEqual(
            out["specular_efficiency"] + out["diffuse_fraction"], 1.0, places=12
        )

    def test_reflecting_diffuse_fraction_value(self):
        out = L.diffusivity(60.0e-6, L.wavelength_m(20.0e9), "reflecting", 0.0)
        self.assertAlmostEqual(out["diffuse_fraction"], 0.00252692, places=8)

    def test_transmitting_scatters_less_than_reflecting_for_equal_roughness(self):
        lam = L.wavelength_m(20.0e9)
        refl = L.diffusivity(60.0e-6, lam, "reflecting", 0.0)
        trans = L.diffusivity(60.0e-6, lam, "transmitting", 0.0, 3.0)
        self.assertLess(trans["diffuse_fraction"], refl["diffuse_fraction"])

    def test_smooth_surface_is_fully_specular(self):
        out = L.diffusivity(0.0, L.wavelength_m(20.0e9), "reflecting", 0.0)
        self.assertAlmostEqual(out["specular_efficiency"], 1.0, places=12)
        self.assertAlmostEqual(out["scatter_loss_db"], 0.0, places=12)

    def test_oblique_incidence_reduces_reflecting_phase_error(self):
        lam = L.wavelength_m(20.0e9)
        normal = L.diffusivity(60.0e-6, lam, "reflecting", 0.0)
        oblique = L.diffusivity(60.0e-6, lam, "reflecting", 60.0)
        self.assertAlmostEqual(
            oblique["phase_error_rad"] / normal["phase_error_rad"], 0.5, places=9
        )

    def test_transmitting_requires_permittivity(self):
        with self.assertRaises(ValueError):
            L.diffusivity(60.0e-6, 0.015, "transmitting", 0.0, None)

    def test_negative_roughness_is_rejected(self):
        with self.assertRaises(ValueError):
            L.diffusivity(-1.0e-6, 0.015, "reflecting", 0.0)

    def test_non_positive_wavelength_is_rejected(self):
        with self.assertRaises(ValueError):
            L.diffusivity(60.0e-6, 0.0, "reflecting", 0.0)

    def test_unknown_surface_class_is_rejected(self):
        with self.assertRaises(ValueError):
            L.diffusivity(60.0e-6, 0.015, "absorbing", 0.0)


class TestDepolarisation(unittest.TestCase):
    def test_two_equal_terms_combine_three_db_worse(self):
        self.assertAlmostEqual(
            L.combine_depolarisation_db([40.0, 40.0]), 36.98970004, places=8
        )

    def test_single_term_is_returned_unchanged(self):
        self.assertAlmostEqual(L.combine_depolarisation_db([33.0]), 33.0, places=10)

    def test_combination_is_dominated_by_the_worst_term(self):
        combined = L.combine_depolarisation_db([25.0, 45.0])
        self.assertLess(combined, 25.0)
        self.assertGreater(combined, 24.9)

    def test_empty_contribution_list_is_rejected(self):
        with self.assertRaises(ValueError):
            L.combine_depolarisation_db([])

    def test_non_positive_contribution_is_rejected(self):
        with self.assertRaises(ValueError):
            L.combine_depolarisation_db([30.0, 0.0])

    def test_cross_polar_power_above_co_polar_power_is_rejected(self):
        with self.assertRaises(ValueError):
            L.combine_depolarisation_db([0.5, 0.5])

    def test_axial_ratio_value(self):
        self.assertAlmostEqual(L.axial_ratio_db(30.0), 0.54952712, places=8)

    def test_axial_ratio_falls_as_discrimination_improves(self):
        self.assertLess(L.axial_ratio_db(40.0), L.axial_ratio_db(30.0))

    def test_axial_ratio_rejects_non_positive_discrimination(self):
        with self.assertRaises(ValueError):
            L.axial_ratio_db(0.0)


class TestEvaluateSurface(unittest.TestCase):
    def test_reflecting_surface_evaluation(self):
        out = L.evaluate_surface(reflecting_spec())
        self.assertEqual(out["surface_class"], "reflecting")
        self.assertAlmostEqual(out["dissipative_loss_db"], 0.00219071, places=8)
        self.assertAlmostEqual(out["total_loss_db"], 0.01317887, places=8)
        self.assertAlmostEqual(
            out["cross_polar_discrimination_db"], 33.23565138, places=8
        )

    def test_transmitting_surface_evaluation(self):
        out = L.evaluate_surface(transmitting_spec())
        self.assertEqual(out["surface_class"], "transmitting")
        self.assertAlmostEqual(out["dissipative_loss_db"], 0.06306147, places=8)
        self.assertGreater(out["total_loss_db"], out["dissipative_loss_db"])

    def test_surface_without_depolarisation_terms_has_no_discrimination(self):
        out = L.evaluate_surface(reflecting_spec(depolarisation_terms_db=[]))
        self.assertIsNone(out["cross_polar_discrimination_db"])
        self.assertIsNone(out["axial_ratio_db"])

    def test_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_surface(["main-reflector"])

    def test_missing_frequency_is_rejected(self):
        spec = reflecting_spec()
        del spec["frequency_hz"]
        with self.assertRaises(ValueError):
            L.evaluate_surface(spec)

    def test_reflecting_surface_without_conductivity_is_rejected(self):
        spec = reflecting_spec()
        del spec["conductivity_s_per_m"]
        with self.assertRaises(ValueError):
            L.evaluate_surface(spec)

    def test_transmitting_surface_without_loss_tangent_is_rejected(self):
        spec = transmitting_spec()
        del spec["loss_tangent"]
        with self.assertRaises(ValueError):
            L.evaluate_surface(spec)


class TestAssessSurface(unittest.TestCase):
    requirement = {
        "max_total_loss_db": 0.5,
        "max_diffuse_fraction": 0.05,
        "min_cross_polar_discrimination_db": 30.0,
    }

    def test_compliant_surface_has_no_findings(self):
        out = L.assess_surface(reflecting_spec(), self.requirement)
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])

    def test_loss_exceedance_is_reported(self):
        req = dict(self.requirement, max_total_loss_db=0.001)
        out = L.assess_surface(reflecting_spec(), req)
        self.assertFalse(out["compliant"])
        self.assertIn("surface-loss", out["findings"][0])

    def test_diffusivity_exceedance_is_reported(self):
        req = dict(self.requirement, max_diffuse_fraction=1.0e-6)
        out = L.assess_surface(reflecting_spec(), req)
        self.assertFalse(out["compliant"])
        self.assertTrue(any("diffuse" in f for f in out["findings"]))

    def test_discrimination_shortfall_is_reported(self):
        req = dict(self.requirement, min_cross_polar_discrimination_db=40.0)
        out = L.assess_surface(reflecting_spec(), req)
        self.assertFalse(out["compliant"])
        self.assertTrue(
            any("cross-polar-discrimination" in f for f in out["findings"])
        )

    def test_absent_loss_limit_is_itself_a_finding(self):
        req = dict(self.requirement)
        del req["max_total_loss_db"]
        out = L.assess_surface(reflecting_spec(), req)
        self.assertFalse(out["compliant"])
        self.assertTrue(any("no surface-loss limit" in f for f in out["findings"]))

    def test_absent_diffusivity_limit_is_itself_a_finding(self):
        req = dict(self.requirement)
        del req["max_diffuse_fraction"]
        out = L.assess_surface(reflecting_spec(), req)
        self.assertTrue(any("no diffusivity limit" in f for f in out["findings"]))

    def test_required_depolarisation_without_terms_is_a_finding(self):
        out = L.assess_surface(
            reflecting_spec(depolarisation_terms_db=[]), self.requirement
        )
        self.assertFalse(out["compliant"])
        self.assertTrue(any("no contributions" in f for f in out["findings"]))

    def test_non_mapping_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            L.assess_surface(reflecting_spec(), None)

    def test_limit_exactly_met_is_compliant(self):
        evaluated = L.evaluate_surface(reflecting_spec())
        req = dict(self.requirement, max_total_loss_db=evaluated["total_loss_db"])
        out = L.assess_surface(reflecting_spec(), req)
        self.assertTrue(out["compliant"])


class TestLimitTolerance(unittest.TestCase):
    def test_tolerance_absorbs_representation_error_on_a_sum(self):
        self.assertTrue(L._le(0.1 + 0.2, 0.3))

    def test_tolerance_absorbs_representation_error_on_a_difference(self):
        self.assertTrue(L._ge(1.0 - 0.9, 0.1))

    def test_tolerance_does_not_widen_a_real_exceedance(self):
        self.assertFalse(L._le(0.3 + 1.0e-6, 0.3))

    def test_tolerance_does_not_widen_a_real_shortfall(self):
        self.assertFalse(L._ge(0.3 - 1.0e-6, 0.3))


class TestRadiatingPath(unittest.TestCase):
    requirement = {
        "max_total_loss_db": 0.5,
        "max_diffuse_fraction": 0.05,
        "min_cross_polar_discrimination_db": 30.0,
    }

    def test_path_rolls_up_every_surface_loss(self):
        specs = [reflecting_spec(), transmitting_spec()]
        reqs = {"main-reflector": self.requirement, "radome": self.requirement}
        out = L.assess_radiating_path(specs, reqs)
        expected = sum(s["total_loss_db"] for s in out["surfaces"])
        self.assertAlmostEqual(out["path_total_loss_db"], expected, places=12)
        self.assertTrue(out["compliant"])

    def test_one_bad_surface_fails_the_path(self):
        specs = [reflecting_spec(), transmitting_spec()]
        reqs = {
            "main-reflector": self.requirement,
            "radome": dict(self.requirement, max_total_loss_db=0.001),
        }
        out = L.assess_radiating_path(specs, reqs)
        self.assertFalse(out["compliant"])
        self.assertEqual(len(out["findings"]), 1)

    def test_empty_path_is_rejected(self):
        with self.assertRaises(ValueError):
            L.assess_radiating_path([], {})

    def test_surface_without_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            L.assess_radiating_path([reflecting_spec()], {"radome": self.requirement})

    def test_surface_without_an_id_is_rejected(self):
        spec = reflecting_spec()
        del spec["id"]
        with self.assertRaises(ValueError):
            L.assess_radiating_path([spec], {"main-reflector": self.requirement})

    def test_non_mapping_requirements_are_rejected(self):
        with self.assertRaises(ValueError):
            L.assess_radiating_path([reflecting_spec()], [])


if __name__ == "__main__":
    unittest.main()
