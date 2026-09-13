#!/usr/bin/env python3
"""Gate 3 contract test for the ECSS-E-ST-20C clause 7.2.2.3.3 lens
material properties logic. Stdlib unittest, offline, deterministic."""

import math
import unittest

from e20_lens_material_properties_logic import (
    FREE_SPACE_RELATIVE_PERMITTIVITY,
    MAX_MODELLED_LOSS_TANGENT,
    MAX_MODELLED_PHASE_ERROR_DEG,
    UNBOUNDED_RETURN_LOSS_DB,
    assess_lens_material,
    categorize_lens_material,
    dielectric_absorption_loss_db,
    face_transmission_loss_db,
    feed_return_loss_db,
    interface_power_reflectance,
    lens_loss_tangent,
    lens_relative_permittivity,
    matched_face_power_reflectance,
    permittivity_tolerance_phase_error_deg,
    phase_error_gain_loss_db,
    quarter_wave_matching_layer,
    refractive_index,
    total_lens_loss_db,
    wavelength_m,
)


def lens_record(**overrides):
    record = {
        "material": "polytetrafluoroethylene",
        "frequency_hz": 30.0e9,
        "ray_path_length_m": 0.05,
        "lens_thickness_m": 0.04,
        "permittivity_tolerance": 0.02,
        "max_phase_error_deg": 20.0,
        "required_feed_return_loss_db": 12.0,
        "allocated_loss_db": 0.80,
    }
    record.update(overrides)
    return record


def ceramic_record(**overrides):
    record = {
        "material": "alumina_ceramic",
        "frequency_hz": 20.0e9,
        "ray_path_length_m": 0.012,
        "lens_thickness_m": 0.010,
        "permittivity_tolerance": 0.05,
        "max_phase_error_deg": 20.0,
        "required_feed_return_loss_db": 12.0,
        "allocated_loss_db": 0.80,
    }
    record.update(overrides)
    return record


class TestMaterialCategorization(unittest.TestCase):
    def test_fluoropolymer_is_a_low_loss_thermoplastic(self):
        self.assertEqual(
            categorize_lens_material("polytetrafluoroethylene"), "low_loss_thermoplastic"
        )

    def test_foam_is_a_dielectric_foam(self):
        self.assertEqual(
            categorize_lens_material("polymethacrylimide_foam"), "dielectric_foam"
        )

    def test_alumina_is_a_ceramic_dielectric(self):
        self.assertEqual(categorize_lens_material("alumina_ceramic"), "ceramic_dielectric")

    def test_plate_lattice_is_an_artificial_dielectric(self):
        self.assertEqual(
            categorize_lens_material("parallel_plate_metal_lens"), "artificial_dielectric"
        )

    def test_uncategorized_lens_material_raises(self):
        with self.assertRaises(ValueError):
            categorize_lens_material("window_glass_offcut")

    def test_permittivity_of_a_known_material(self):
        self.assertAlmostEqual(
            lens_relative_permittivity("polytetrafluoroethylene"), 2.05, places=9
        )

    def test_foam_sits_close_to_free_space(self):
        self.assertLess(
            lens_relative_permittivity("expanded_polystyrene_foam"),
            1.1 * FREE_SPACE_RELATIVE_PERMITTIVITY,
        )

    def test_artificial_lattice_can_sit_below_free_space(self):
        self.assertLess(
            lens_relative_permittivity("parallel_plate_metal_lens"),
            FREE_SPACE_RELATIVE_PERMITTIVITY,
        )

    def test_loss_tangent_of_a_known_material(self):
        self.assertAlmostEqual(
            lens_loss_tangent("cross_linked_polystyrene"), 6.0e-4, places=9
        )

    def test_permittivity_of_an_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            lens_relative_permittivity("window_glass_offcut")

    def test_loss_tangent_of_an_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            lens_loss_tangent("window_glass_offcut")


class TestInterfaceReflection(unittest.TestCase):
    def test_refractive_index_is_the_root_of_permittivity(self):
        self.assertAlmostEqual(refractive_index(4.0), 2.0, places=12)

    def test_non_positive_permittivity_raises(self):
        with self.assertRaises(ValueError):
            refractive_index(0.0)

    def test_identical_media_reflect_nothing(self):
        self.assertAlmostEqual(interface_power_reflectance(2.05, 2.05), 0.0, places=12)

    def test_fluoropolymer_face_reflects_about_three_percent(self):
        reflectance = interface_power_reflectance(1.0, 2.05)
        self.assertAlmostEqual(reflectance, 0.031527, places=6)

    def test_ceramic_face_reflects_far_more_than_foam(self):
        foam = interface_power_reflectance(1.0, 1.05)
        ceramic = interface_power_reflectance(1.0, 9.80)
        self.assertGreater(ceramic, 50.0 * foam)

    def test_reflectance_is_direction_independent(self):
        self.assertAlmostEqual(
            interface_power_reflectance(1.0, 3.78),
            interface_power_reflectance(3.78, 1.0),
            places=12,
        )

    def test_negative_permittivity_in_reflectance_raises(self):
        with self.assertRaises(ValueError):
            interface_power_reflectance(1.0, -2.0)

    def test_two_faces_lose_twice_one_face(self):
        one = face_transmission_loss_db(0.031527, face_count=1)
        two = face_transmission_loss_db(0.031527, face_count=2)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_fluoropolymer_lens_faces_cost_about_a_quarter_decibel(self):
        loss = face_transmission_loss_db(interface_power_reflectance(1.0, 2.05))
        self.assertAlmostEqual(loss, 0.27825, places=5)

    def test_zero_reflectance_costs_no_transmission(self):
        self.assertAlmostEqual(face_transmission_loss_db(0.0), 0.0, places=12)

    def test_total_reflectance_raises(self):
        with self.assertRaises(ValueError):
            face_transmission_loss_db(1.0)

    def test_negative_reflectance_raises(self):
        with self.assertRaises(ValueError):
            face_transmission_loss_db(-0.01)

    def test_zero_face_count_raises(self):
        with self.assertRaises(ValueError):
            face_transmission_loss_db(0.03, face_count=0)


class TestMatchingLayer(unittest.TestCase):
    def test_geometric_mean_layer_cancels_the_face_reflection(self):
        layer = quarter_wave_matching_layer(2.05, 30.0e9)
        reflectance = matched_face_power_reflectance(
            2.05, layer["layer_relative_permittivity"]
        )
        self.assertAlmostEqual(reflectance, 0.0, places=12)

    def test_layer_permittivity_is_the_geometric_mean(self):
        layer = quarter_wave_matching_layer(9.80, 20.0e9)
        self.assertAlmostEqual(
            layer["layer_relative_permittivity"], math.sqrt(9.80), places=9
        )

    def test_layer_thickness_is_a_quarter_wave_inside_the_layer(self):
        layer = quarter_wave_matching_layer(9.80, 20.0e9)
        expected = wavelength_m(20.0e9) / (
            4.0 * math.sqrt(layer["layer_relative_permittivity"])
        )
        self.assertAlmostEqual(layer["layer_thickness_m"], expected, places=12)

    def test_layer_is_thinner_than_a_free_space_quarter_wave(self):
        layer = quarter_wave_matching_layer(9.80, 20.0e9)
        self.assertLess(layer["layer_thickness_m"], wavelength_m(20.0e9) / 4.0)

    def test_wrong_layer_permittivity_leaves_a_residual_reflection(self):
        residual = matched_face_power_reflectance(9.80, 2.05)
        self.assertGreater(residual, 0.0)

    def test_layer_far_off_the_mean_is_worse_than_a_bare_face(self):
        bare = interface_power_reflectance(1.0, 2.05)
        badly_matched = matched_face_power_reflectance(2.05, 9.80)
        self.assertGreater(badly_matched, bare)

    def test_sub_unity_lens_cannot_be_matched_naturally(self):
        with self.assertRaises(ValueError):
            quarter_wave_matching_layer(0.60, 30.0e9)

    def test_non_positive_lens_permittivity_raises(self):
        with self.assertRaises(ValueError):
            quarter_wave_matching_layer(0.0, 30.0e9)

    def test_non_positive_frequency_in_the_layer_design_raises(self):
        with self.assertRaises(ValueError):
            quarter_wave_matching_layer(2.05, 0.0)


class TestAbsorption(unittest.TestCase):
    def test_absorption_matches_the_low_loss_form(self):
        lam = wavelength_m(30.0e9)
        alpha = math.pi * math.sqrt(2.05) * 2.0e-4 / lam
        self.assertAlmostEqual(
            dielectric_absorption_loss_db(2.05, 2.0e-4, 0.05, 30.0e9),
            20.0 * math.log10(math.e) * alpha * 0.05,
            places=12,
        )

    def test_absorption_doubles_with_the_path(self):
        one = dielectric_absorption_loss_db(2.05, 2.0e-4, 0.05, 30.0e9)
        two = dielectric_absorption_loss_db(2.05, 2.0e-4, 0.10, 30.0e9)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_absorption_rises_with_frequency(self):
        low = dielectric_absorption_loss_db(2.05, 2.0e-4, 0.05, 10.0e9)
        high = dielectric_absorption_loss_db(2.05, 2.0e-4, 0.05, 30.0e9)
        self.assertGreater(high, low)

    def test_lossless_material_absorbs_nothing(self):
        self.assertAlmostEqual(
            dielectric_absorption_loss_db(2.05, 0.0, 0.05, 30.0e9), 0.0, places=12
        )

    def test_negative_loss_tangent_raises(self):
        with self.assertRaises(ValueError):
            dielectric_absorption_loss_db(2.05, -1.0e-4, 0.05, 30.0e9)

    def test_loss_tangent_on_the_model_bound_is_accepted(self):
        self.assertGreater(
            dielectric_absorption_loss_db(
                2.05, MAX_MODELLED_LOSS_TANGENT, 0.05, 30.0e9
            ),
            0.0,
        )

    def test_loss_tangent_beyond_the_model_bound_raises(self):
        with self.assertRaises(ValueError):
            dielectric_absorption_loss_db(
                2.05, MAX_MODELLED_LOSS_TANGENT * 2.0, 0.05, 30.0e9
            )

    def test_non_positive_path_length_raises(self):
        with self.assertRaises(ValueError):
            dielectric_absorption_loss_db(2.05, 2.0e-4, 0.0, 30.0e9)


class TestPermittivityTolerance(unittest.TestCase):
    def test_phase_error_matches_the_index_difference(self):
        lam = wavelength_m(30.0e9)
        expected = 360.0 * (math.sqrt(2.07) - math.sqrt(2.05)) * 0.04 / lam
        self.assertAlmostEqual(
            permittivity_tolerance_phase_error_deg(2.05, 0.02, 0.04, 30.0e9),
            expected,
            places=9,
        )

    def test_phase_error_scales_with_thickness(self):
        thin = permittivity_tolerance_phase_error_deg(2.05, 0.02, 0.02, 30.0e9)
        thick = permittivity_tolerance_phase_error_deg(2.05, 0.02, 0.06, 30.0e9)
        self.assertAlmostEqual(thick, 3.0 * thin, places=9)

    def test_tolerance_sign_does_not_change_the_error(self):
        self.assertAlmostEqual(
            permittivity_tolerance_phase_error_deg(2.05, -0.02, 0.04, 30.0e9),
            permittivity_tolerance_phase_error_deg(2.05, 0.02, 0.04, 30.0e9),
            places=12,
        )

    def test_zero_tolerance_gives_no_phase_error(self):
        self.assertAlmostEqual(
            permittivity_tolerance_phase_error_deg(2.05, 0.0, 0.04, 30.0e9),
            0.0,
            places=12,
        )

    def test_non_positive_thickness_raises(self):
        with self.assertRaises(ValueError):
            permittivity_tolerance_phase_error_deg(2.05, 0.02, 0.0, 30.0e9)

    def test_tolerance_swallowing_the_permittivity_raises(self):
        with self.assertRaises(ValueError):
            permittivity_tolerance_phase_error_deg(1.05, 1.20, 0.04, 30.0e9)

    def test_phase_loss_matches_the_square_law(self):
        phase_rad = math.radians(12.0)
        self.assertAlmostEqual(
            phase_error_gain_loss_db(12.0),
            10.0 * math.log10(math.e) * phase_rad * phase_rad,
            places=12,
        )

    def test_phase_loss_quadruples_when_the_error_doubles(self):
        self.assertAlmostEqual(
            phase_error_gain_loss_db(20.0), 4.0 * phase_error_gain_loss_db(10.0), places=9
        )

    def test_no_phase_error_costs_no_gain(self):
        self.assertAlmostEqual(phase_error_gain_loss_db(0.0), 0.0, places=12)

    def test_phase_error_on_the_model_bound_is_accepted(self):
        self.assertGreater(phase_error_gain_loss_db(MAX_MODELLED_PHASE_ERROR_DEG), 0.0)

    def test_phase_error_beyond_the_model_bound_raises(self):
        with self.assertRaises(ValueError):
            phase_error_gain_loss_db(MAX_MODELLED_PHASE_ERROR_DEG + 1.0)

    def test_negative_phase_error_raises(self):
        with self.assertRaises(ValueError):
            phase_error_gain_loss_db(-1.0)


class TestFeedReturnAndTotals(unittest.TestCase):
    def test_return_loss_of_a_bare_fluoropolymer_face(self):
        reflectance = interface_power_reflectance(1.0, 2.05)
        self.assertAlmostEqual(
            feed_return_loss_db(reflectance), -10.0 * math.log10(reflectance), places=12
        )

    def test_ceramic_face_returns_more_to_the_feed(self):
        thermoplastic = feed_return_loss_db(interface_power_reflectance(1.0, 2.05))
        ceramic = feed_return_loss_db(interface_power_reflectance(1.0, 9.80))
        self.assertLess(ceramic, thermoplastic)

    def test_partial_capture_improves_the_return_loss(self):
        full = feed_return_loss_db(0.03, 1.0)
        partial = feed_return_loss_db(0.03, 0.25)
        self.assertAlmostEqual(partial - full, 10.0 * math.log10(4.0), places=9)

    def test_a_perfectly_matched_face_returns_the_model_bound(self):
        self.assertAlmostEqual(
            feed_return_loss_db(0.0), UNBOUNDED_RETURN_LOSS_DB, places=12
        )

    def test_reflectance_above_unity_raises(self):
        with self.assertRaises(ValueError):
            feed_return_loss_db(1.2)

    def test_zero_capture_fraction_raises(self):
        with self.assertRaises(ValueError):
            feed_return_loss_db(0.03, 0.0)

    def test_terms_add_in_decibels(self):
        self.assertAlmostEqual(
            total_lens_loss_db({"face_reflection": 0.28, "absorption": 0.04}),
            0.32,
            places=12,
        )

    def test_empty_term_set_raises(self):
        with self.assertRaises(ValueError):
            total_lens_loss_db({})

    def test_negative_term_raises(self):
        with self.assertRaises(ValueError):
            total_lens_loss_db({"absorption": -0.01})


class TestAssessment(unittest.TestCase):
    def test_compliant_thermoplastic_lens_is_acceptable(self):
        result = assess_lens_material(lens_record())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["lens_material_acceptable"])
        self.assertEqual(result["material_family"], "low_loss_thermoplastic")

    def test_compliant_lens_carries_all_three_loss_terms(self):
        result = assess_lens_material(lens_record())
        self.assertAlmostEqual(
            result["total_loss_db"],
            result["face_transmission_loss_db"]
            + result["absorption_loss_db"]
            + result["phase_error_loss_db"],
            places=12,
        )

    def test_bare_ceramic_face_fails_the_feed_return_requirement(self):
        result = assess_lens_material(ceramic_record())
        self.assertIn("feed_return_loss_below_requirement", result["findings"])
        self.assertFalse(result["lens_material_acceptable"])

    def test_matching_layer_rescues_the_ceramic_feed_return(self):
        result = assess_lens_material(
            ceramic_record(matching_layer_permittivity=math.sqrt(9.80))
        )
        self.assertNotIn("feed_return_loss_below_requirement", result["findings"])
        self.assertAlmostEqual(
            result["feed_return_loss_db"], UNBOUNDED_RETURN_LOSS_DB, places=9
        )

    def test_matching_layer_removes_the_face_transmission_loss(self):
        bare = assess_lens_material(ceramic_record())
        matched = assess_lens_material(
            ceramic_record(matching_layer_permittivity=math.sqrt(9.80))
        )
        self.assertGreater(bare["face_transmission_loss_db"], 2.0)
        self.assertAlmostEqual(matched["face_transmission_loss_db"], 0.0, places=9)

    def test_loss_above_allocation_is_reported(self):
        result = assess_lens_material(lens_record(allocated_loss_db=0.10))
        self.assertIn("lens_loss_above_allocation", result["findings"])

    def test_allocation_exactly_on_the_total_passes(self):
        base = assess_lens_material(lens_record())
        tight = assess_lens_material(
            lens_record(allocated_loss_db=base["total_loss_db"])
        )
        self.assertNotIn("lens_loss_above_allocation", tight["findings"])

    def test_excess_phase_error_is_reported(self):
        result = assess_lens_material(
            lens_record(permittivity_tolerance=0.06, max_phase_error_deg=5.0)
        )
        self.assertIn("lens_aperture_phase_error_above_limit", result["findings"])

    def test_phase_error_exactly_on_the_limit_passes(self):
        base = assess_lens_material(lens_record())
        tight = assess_lens_material(
            lens_record(max_phase_error_deg=base["lens_aperture_phase_error_deg"])
        )
        self.assertNotIn("lens_aperture_phase_error_above_limit", tight["findings"])

    def test_feed_capture_fraction_is_honoured(self):
        full = assess_lens_material(lens_record())
        partial = assess_lens_material(lens_record(feed_capture_fraction=0.25))
        self.assertGreater(partial["feed_return_loss_db"], full["feed_return_loss_db"])

    def test_unknown_material_in_a_record_raises(self):
        with self.assertRaises(ValueError):
            assess_lens_material(lens_record(material="window_glass_offcut"))

    def test_missing_required_key_raises(self):
        record = lens_record()
        del record["ray_path_length_m"]
        with self.assertRaises(ValueError):
            assess_lens_material(record)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            assess_lens_material(["polytetrafluoroethylene"])

    def test_non_positive_frequency_in_a_record_raises(self):
        with self.assertRaises(ValueError):
            assess_lens_material(lens_record(frequency_hz=0.0))


if __name__ == "__main__":
    unittest.main()
