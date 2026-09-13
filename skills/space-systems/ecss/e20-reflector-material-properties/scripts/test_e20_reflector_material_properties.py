#!/usr/bin/env python3
"""Gate 3 contract test for the ECSS-E-ST-20C clause 7.2.2.3.2
reflector material properties logic. Stdlib unittest, offline,
deterministic."""

import math
import unittest

from e20_reflector_material_properties_logic import (
    BARE_COMPOSITE_OHMIC_LOSS_LIMIT_DB,
    FREE_SPACE_WAVE_IMPEDANCE_OHM,
    MIN_METALLISATION_SKIN_DEPTHS,
    RUZE_MAX_RMS_WAVELENGTHS,
    assess_reflector_material,
    categorize_reflector_material,
    conductor_surface_resistance_ohm,
    material_conductivity_s_per_m,
    material_expansion_per_k,
    mesh_leakage_loss_db,
    mesh_normalised_reactance,
    ohmic_reflection_loss_db,
    required_metallisation_thickness_m,
    ruze_gain_loss_db,
    skin_depth_m,
    thermoelastic_surface_rms_m,
    total_reflector_loss_db,
    wavelength_m,
)


def metallised_record(**overrides):
    record = {
        "material": "cfrp_with_vapour_deposited_aluminium",
        "lowest_frequency_hz": 10.0e9,
        "highest_frequency_hz": 12.0e9,
        "incidence_angle_deg": 0.0,
        "metallisation_thickness_m": 6.0e-6,
        "temperature_excursion_k": 100.0,
        "characteristic_length_m": 1.5,
        "distortion_factor": 0.30,
        "allocated_loss_db": 0.05,
    }
    record.update(overrides)
    return record


def mesh_record(**overrides):
    record = {
        "material": "gold_plated_molybdenum_mesh",
        "lowest_frequency_hz": 2.0e9,
        "highest_frequency_hz": 2.3e9,
        "incidence_angle_deg": 30.0,
        "cell_size_m": 1.2e-3,
        "wire_radius_m": 3.0e-5,
        "temperature_excursion_k": 150.0,
        "characteristic_length_m": 6.0,
        "distortion_factor": 0.30,
        "allocated_loss_db": 0.50,
    }
    record.update(overrides)
    return record


class TestMaterialCategorization(unittest.TestCase):
    def test_aluminium_sheet_is_a_metallic_sheet(self):
        self.assertEqual(
            categorize_reflector_material("aluminium_alloy_sheet"), "metallic_sheet"
        )

    def test_coated_laminate_is_a_metallised_composite(self):
        self.assertEqual(
            categorize_reflector_material("cfrp_with_vapour_deposited_aluminium"),
            "metallised_composite",
        )

    def test_coated_film_is_a_metallised_membrane(self):
        self.assertEqual(
            categorize_reflector_material(
                "polyimide_membrane_with_vapour_deposited_aluminium"
            ),
            "metallised_membrane",
        )

    def test_uncoated_laminate_is_a_bare_composite(self):
        self.assertEqual(
            categorize_reflector_material("bare_carbon_fibre_laminate"), "bare_composite"
        )

    def test_woven_grid_is_a_knitted_metal_mesh(self):
        self.assertEqual(
            categorize_reflector_material("silver_plated_tungsten_mesh"),
            "knitted_metal_mesh",
        )

    def test_uncategorized_material_raises(self):
        with self.assertRaises(ValueError):
            categorize_reflector_material("anodised_plywood")

    def test_conductivity_of_a_known_material(self):
        self.assertAlmostEqual(
            material_conductivity_s_per_m("copper_clad_sheet"), 5.8e7, places=3
        )

    def test_conductivity_of_an_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            material_conductivity_s_per_m("anodised_plywood")

    def test_laminate_expansion_is_far_below_aluminium(self):
        self.assertLess(
            material_expansion_per_k("cfrp_with_vapour_deposited_aluminium"),
            material_expansion_per_k("aluminium_alloy_sheet") / 10.0,
        )

    def test_expansion_of_an_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            material_expansion_per_k("anodised_plywood")


class TestSkinDepthAndMetallisation(unittest.TestCase):
    def test_skin_depth_of_aluminium_at_twelve_gigahertz(self):
        self.assertAlmostEqual(skin_depth_m(2.2e7, 12.0e9) * 1e6, 0.97953, places=5)

    def test_skin_depth_falls_as_the_square_root_of_frequency(self):
        low = skin_depth_m(2.2e7, 1.0e9)
        high = skin_depth_m(2.2e7, 4.0e9)
        self.assertAlmostEqual(high, low / 2.0, places=12)

    def test_better_conductor_has_a_shallower_skin_depth(self):
        self.assertLess(skin_depth_m(5.8e7, 10.0e9), skin_depth_m(2.2e7, 10.0e9))

    def test_magnetic_material_has_a_shallower_skin_depth(self):
        self.assertLess(
            skin_depth_m(1.0e7, 10.0e9, relative_permeability=100.0),
            skin_depth_m(1.0e7, 10.0e9),
        )

    def test_non_positive_conductivity_raises(self):
        with self.assertRaises(ValueError):
            skin_depth_m(0.0, 10.0e9)

    def test_non_positive_frequency_in_skin_depth_raises(self):
        with self.assertRaises(ValueError):
            skin_depth_m(2.2e7, 0.0)

    def test_non_positive_permeability_raises(self):
        with self.assertRaises(ValueError):
            skin_depth_m(2.2e7, 10.0e9, relative_permeability=0.0)

    def test_required_thickness_is_five_skin_depths(self):
        self.assertAlmostEqual(
            required_metallisation_thickness_m(3.5e7, 10.0e9),
            MIN_METALLISATION_SKIN_DEPTHS * skin_depth_m(3.5e7, 10.0e9),
            places=12,
        )

    def test_required_thickness_is_largest_at_the_band_bottom(self):
        self.assertGreater(
            required_metallisation_thickness_m(3.5e7, 4.0e9),
            required_metallisation_thickness_m(3.5e7, 12.0e9),
        )

    def test_non_positive_skin_depth_count_raises(self):
        with self.assertRaises(ValueError):
            required_metallisation_thickness_m(3.5e7, 10.0e9, skin_depths=0.0)


class TestOhmicReflection(unittest.TestCase):
    def test_surface_resistance_matches_the_skin_depth_definition(self):
        expected = 1.0 / (2.2e7 * skin_depth_m(2.2e7, 12.0e9))
        self.assertAlmostEqual(
            conductor_surface_resistance_ohm(2.2e7, 12.0e9), expected, places=12
        )

    def test_aluminium_surface_resistance_is_tens_of_milliohms(self):
        self.assertAlmostEqual(
            conductor_surface_resistance_ohm(2.2e7, 12.0e9), 0.046404, places=6
        )

    def test_aluminium_reflection_loss_is_a_few_thousandths_of_a_decibel(self):
        loss = ohmic_reflection_loss_db(conductor_surface_resistance_ohm(2.2e7, 12.0e9))
        self.assertGreater(loss, 0.0)
        self.assertLess(loss, 0.01)

    def test_poorer_conductor_loses_more(self):
        good = ohmic_reflection_loss_db(conductor_surface_resistance_ohm(5.8e7, 12.0e9))
        poor = ohmic_reflection_loss_db(conductor_surface_resistance_ohm(1.0e4, 12.0e9))
        self.assertGreater(poor, good * 10.0)

    def test_oblique_incidence_reduces_the_perpendicular_absorption(self):
        normal = ohmic_reflection_loss_db(0.05, 0.0)
        oblique = ohmic_reflection_loss_db(0.05, 60.0)
        self.assertLess(oblique, normal)

    def test_reflection_loss_matches_the_closed_form(self):
        absorbed = 4.0 * 0.05 / FREE_SPACE_WAVE_IMPEDANCE_OHM
        self.assertAlmostEqual(
            ohmic_reflection_loss_db(0.05), -10.0 * math.log10(1.0 - absorbed), places=12
        )

    def test_non_positive_surface_resistance_raises(self):
        with self.assertRaises(ValueError):
            ohmic_reflection_loss_db(0.0)

    def test_grazing_incidence_raises(self):
        with self.assertRaises(ValueError):
            ohmic_reflection_loss_db(0.05, 90.0)

    def test_negative_incidence_angle_raises(self):
        with self.assertRaises(ValueError):
            ohmic_reflection_loss_db(0.05, -10.0)

    def test_surface_outside_the_good_conductor_model_raises(self):
        with self.assertRaises(ValueError):
            ohmic_reflection_loss_db(conductor_surface_resistance_ohm(1.0, 12.0e9))


class TestMeshLeakage(unittest.TestCase):
    def test_fine_mesh_leaks_only_hundredths_of_a_decibel(self):
        loss = mesh_leakage_loss_db(1.2e-3, 3.0e-5, 2.3e9)
        self.assertGreater(loss, 0.0)
        self.assertLess(loss, 0.05)

    def test_leakage_matches_the_inductive_grid_form(self):
        x = mesh_normalised_reactance(1.2e-3, 3.0e-5, 2.3e9)
        self.assertAlmostEqual(
            mesh_leakage_loss_db(1.2e-3, 3.0e-5, 2.3e9),
            10.0 * math.log10(1.0 + 4.0 * x * x),
            places=12,
        )

    def test_leakage_rises_with_frequency(self):
        low = mesh_leakage_loss_db(1.2e-3, 3.0e-5, 2.0e9)
        high = mesh_leakage_loss_db(1.2e-3, 3.0e-5, 8.0e9)
        self.assertGreater(high, low)

    def test_coarser_weave_leaks_more(self):
        fine = mesh_leakage_loss_db(0.8e-3, 3.0e-5, 2.3e9)
        coarse = mesh_leakage_loss_db(2.0e-3, 3.0e-5, 2.3e9)
        self.assertGreater(coarse, fine)

    def test_thicker_wire_leaks_more_at_the_same_opening(self):
        thin = mesh_leakage_loss_db(1.2e-3, 1.0e-5, 2.3e9)
        thick = mesh_leakage_loss_db(1.2e-3, 5.0e-5, 2.3e9)
        self.assertGreater(thin, thick)

    def test_non_positive_cell_size_raises(self):
        with self.assertRaises(ValueError):
            mesh_leakage_loss_db(0.0, 3.0e-5, 2.3e9)

    def test_non_positive_wire_radius_raises(self):
        with self.assertRaises(ValueError):
            mesh_leakage_loss_db(1.2e-3, 0.0, 2.3e9)

    def test_wire_too_thick_for_the_grid_model_raises(self):
        with self.assertRaises(ValueError):
            mesh_leakage_loss_db(1.0e-3, 2.0e-4, 2.3e9)

    def test_cell_in_the_grating_regime_raises(self):
        with self.assertRaises(ValueError):
            mesh_leakage_loss_db(2.0e-2, 3.0e-5, 12.0e9)


class TestSurfaceErrorLoss(unittest.TestCase):
    def test_surface_error_scales_with_the_excursion(self):
        one = thermoelastic_surface_rms_m(5.0e-6, 100.0, 6.0, 0.3)
        two = thermoelastic_surface_rms_m(5.0e-6, 200.0, 6.0, 0.3)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_surface_error_uses_the_magnitude_of_a_cold_excursion(self):
        self.assertAlmostEqual(
            thermoelastic_surface_rms_m(5.0e-6, -120.0, 6.0, 0.3),
            thermoelastic_surface_rms_m(5.0e-6, 120.0, 6.0, 0.3),
            places=12,
        )

    def test_low_expansion_laminate_distorts_less(self):
        laminate = thermoelastic_surface_rms_m(1.0e-6, 100.0, 1.5, 0.3)
        metal = thermoelastic_surface_rms_m(23.0e-6, 100.0, 1.5, 0.3)
        self.assertLess(laminate, metal)

    def test_negative_expansion_raises(self):
        with self.assertRaises(ValueError):
            thermoelastic_surface_rms_m(-1.0e-6, 100.0, 1.5, 0.3)

    def test_non_positive_length_raises(self):
        with self.assertRaises(ValueError):
            thermoelastic_surface_rms_m(1.0e-6, 100.0, 0.0, 0.3)

    def test_distortion_factor_above_unity_raises(self):
        with self.assertRaises(ValueError):
            thermoelastic_surface_rms_m(1.0e-6, 100.0, 1.5, 1.4)

    def test_ruze_loss_matches_the_closed_form(self):
        lam = wavelength_m(12.0e9)
        phase = 4.0 * math.pi * 1.0e-4 / lam
        self.assertAlmostEqual(
            ruze_gain_loss_db(1.0e-4, 12.0e9),
            10.0 * math.log10(math.e) * phase * phase,
            places=12,
        )

    def test_ruze_loss_quadruples_when_the_error_doubles(self):
        one = ruze_gain_loss_db(1.0e-4, 12.0e9)
        two = ruze_gain_loss_db(2.0e-4, 12.0e9)
        self.assertAlmostEqual(two, 4.0 * one, places=9)

    def test_perfect_surface_costs_no_gain(self):
        self.assertAlmostEqual(ruze_gain_loss_db(0.0, 12.0e9), 0.0, places=12)

    def test_same_surface_costs_more_at_a_higher_frequency(self):
        self.assertGreater(
            ruze_gain_loss_db(1.0e-4, 12.0e9), ruze_gain_loss_db(1.0e-4, 4.0e9)
        )

    def test_error_exactly_on_the_small_error_bound_is_accepted(self):
        bound = RUZE_MAX_RMS_WAVELENGTHS * wavelength_m(12.0e9)
        self.assertGreater(ruze_gain_loss_db(bound, 12.0e9), 0.0)

    def test_error_beyond_the_small_error_bound_raises(self):
        bound = RUZE_MAX_RMS_WAVELENGTHS * wavelength_m(12.0e9)
        with self.assertRaises(ValueError):
            ruze_gain_loss_db(bound * 1.5, 12.0e9)

    def test_negative_surface_error_raises(self):
        with self.assertRaises(ValueError):
            ruze_gain_loss_db(-1.0e-6, 12.0e9)


class TestLossSummation(unittest.TestCase):
    def test_terms_add_in_decibels(self):
        self.assertAlmostEqual(
            total_reflector_loss_db({"ohmic": 0.01, "surface_error": 0.04}),
            0.05,
            places=12,
        )

    def test_empty_term_set_raises(self):
        with self.assertRaises(ValueError):
            total_reflector_loss_db({})

    def test_negative_term_raises(self):
        with self.assertRaises(ValueError):
            total_reflector_loss_db({"ohmic": -0.01})


class TestAssessment(unittest.TestCase):
    def test_compliant_metallised_laminate_is_acceptable(self):
        result = assess_reflector_material(metallised_record())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["reflecting_surface_acceptable"])
        self.assertEqual(result["material_family"], "metallised_composite")

    def test_metallised_laminate_carries_no_mesh_leakage(self):
        result = assess_reflector_material(metallised_record())
        self.assertAlmostEqual(result["mesh_leakage_loss_db"], 0.0, places=12)

    def test_thin_metallisation_is_reported(self):
        result = assess_reflector_material(
            metallised_record(metallisation_thickness_m=1.0e-6)
        )
        self.assertIn("metallisation_thinner_than_required", result["findings"])
        self.assertFalse(result["reflecting_surface_acceptable"])

    def test_metallisation_exactly_on_the_requirement_passes(self):
        required = required_metallisation_thickness_m(3.5e7, 10.0e9)
        result = assess_reflector_material(
            metallised_record(metallisation_thickness_m=required)
        )
        self.assertNotIn("metallisation_thinner_than_required", result["findings"])

    def test_missing_metallisation_thickness_raises(self):
        record = metallised_record()
        del record["metallisation_thickness_m"]
        with self.assertRaises(ValueError):
            assess_reflector_material(record)

    def test_non_positive_metallisation_thickness_raises(self):
        with self.assertRaises(ValueError):
            assess_reflector_material(metallised_record(metallisation_thickness_m=0.0))

    def test_loss_above_allocation_is_reported(self):
        result = assess_reflector_material(metallised_record(allocated_loss_db=0.001))
        self.assertIn("reflector_loss_above_allocation", result["findings"])

    def test_allocation_exactly_on_the_total_passes(self):
        base = assess_reflector_material(metallised_record())
        tight = assess_reflector_material(
            metallised_record(allocated_loss_db=base["total_loss_db"])
        )
        self.assertNotIn("reflector_loss_above_allocation", tight["findings"])

    def test_compliant_mesh_reflector_is_acceptable(self):
        result = assess_reflector_material(mesh_record())
        self.assertEqual(result["findings"], [])
        self.assertGreater(result["mesh_leakage_loss_db"], 0.0)

    def test_mesh_record_without_cell_geometry_raises(self):
        record = mesh_record()
        del record["cell_size_m"]
        with self.assertRaises(ValueError):
            assess_reflector_material(record)

    def test_bare_laminate_reflection_loss_is_reported(self):
        result = assess_reflector_material(
            {
                "material": "bare_carbon_fibre_laminate",
                "lowest_frequency_hz": 10.0e9,
                "highest_frequency_hz": 12.0e9,
                "incidence_angle_deg": 0.0,
                "temperature_excursion_k": 80.0,
                "characteristic_length_m": 1.2,
                "distortion_factor": 0.30,
                "allocated_loss_db": 1.0,
            }
        )
        self.assertIn(
            "unmetallised_composite_reflection_loss_significant", result["findings"]
        )
        self.assertGreater(result["ohmic_loss_db"], BARE_COMPOSITE_OHMIC_LOSS_LIMIT_DB)

    def test_inverted_band_edges_raise(self):
        with self.assertRaises(ValueError):
            assess_reflector_material(
                metallised_record(lowest_frequency_hz=14.0e9, highest_frequency_hz=12.0e9)
            )

    def test_unknown_material_in_a_record_raises(self):
        with self.assertRaises(ValueError):
            assess_reflector_material(metallised_record(material="anodised_plywood"))

    def test_missing_required_key_raises(self):
        record = metallised_record()
        del record["allocated_loss_db"]
        with self.assertRaises(ValueError):
            assess_reflector_material(record)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            assess_reflector_material(["aluminium_alloy_sheet"])


if __name__ == "__main__":
    unittest.main()
