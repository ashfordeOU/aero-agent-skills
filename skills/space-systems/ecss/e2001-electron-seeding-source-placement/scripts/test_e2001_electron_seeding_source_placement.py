#!/usr/bin/env python3
"""Gate 3 contract test for e2001-electron-seeding-source-placement.

Offline, deterministic, stdlib unittest only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2001_electron_seeding_source_placement_logic as logic  # noqa: E402

THIN_WALL = [{"thickness_cm": 0.05, "density_g_cm3": 2.7}]
THICK_WALL = [{"thickness_cm": 1.0, "density_g_cm3": 2.7}]


def radioactive_spec(**over):
    spec = {
        "technique": "radioactive-source",
        "aim_point": "iris-gap-3",
        "initiation_site": "iris-gap-3",
        "source_to_gap_distance_cm": 10.0,
        "gap_aperture_area_cm2": 0.5,
        "emission_rate_per_s": 3.7e6,
        "required_rate_per_s": 100.0,
        "obstructions": THIN_WALL,
        "beta_energy_mev": 2.28,
    }
    spec.update(over)
    return spec


def ultraviolet_spec(**over):
    spec = {
        "technique": "ultraviolet-illumination",
        "aim_point": "iris-gap-3",
        "initiation_site": "iris-gap-3",
        "source_to_gap_distance_cm": 10.0,
        "gap_aperture_area_cm2": 0.5,
        "emission_rate_per_s": 1.0e12,
        "required_rate_per_s": 1.0e6,
        "obstructions": [],
        "wavelength_nm": 220.0,
        "target_surface_material": "aluminium",
    }
    spec.update(over)
    return spec


def gun_spec(**over):
    spec = {
        "technique": "electron-gun",
        "aim_point": "iris-gap-3",
        "initiation_site": "iris-gap-3",
        "source_to_gap_distance_cm": 5.0,
        "gap_aperture_area_cm2": 0.8,
        "emission_rate_per_s": 1.0e10,
        "required_rate_per_s": 1.0e5,
        "obstructions": [],
        "aim_offset_mm": 0.2,
        "gap_height_mm": 1.0,
        "landing_energy_ev": 300.0,
    }
    spec.update(over)
    return spec


class BetaRangeAndTransmission(unittest.TestCase):
    def test_range_at_one_mev_matches_the_fit_constant(self):
        self.assertAlmostEqual(logic.beta_range_mg_cm2(1.0), 412.0, places=9)

    def test_range_grows_with_energy(self):
        self.assertGreater(logic.beta_range_mg_cm2(2.28), logic.beta_range_mg_cm2(0.546))

    def test_energy_below_the_fit_window_rejected(self):
        with self.assertRaises(ValueError):
            logic.beta_range_mg_cm2(0.005)

    def test_energy_above_the_fit_window_rejected(self):
        with self.assertRaises(ValueError):
            logic.beta_range_mg_cm2(5.0)

    def test_non_numeric_energy_rejected(self):
        with self.assertRaises(ValueError):
            logic.beta_range_mg_cm2("2.28")

    def test_absorption_coefficient_at_one_mev(self):
        self.assertAlmostEqual(
            logic.beta_absorption_coefficient_cm2_g(1.0), 17.0, places=9
        )

    def test_absorption_coefficient_falls_with_energy(self):
        self.assertLess(
            logic.beta_absorption_coefficient_cm2_g(2.28),
            logic.beta_absorption_coefficient_cm2_g(0.5),
        )

    def test_thin_wall_leaves_the_path_open(self):
        areal = logic.path_areal_density_mg_cm2(THIN_WALL)
        self.assertTrue(logic.beta_reaches_gap(2.28, areal))

    def test_thick_wall_stops_the_beta_flux(self):
        areal = logic.path_areal_density_mg_cm2(THICK_WALL)
        self.assertFalse(logic.beta_reaches_gap(2.28, areal))

    def test_blocked_path_transmits_nothing(self):
        areal = logic.path_areal_density_mg_cm2(THICK_WALL)
        self.assertAlmostEqual(logic.beta_transmission(2.28, areal), 0.0, places=15)

    def test_open_path_transmits_a_partial_fraction(self):
        value = logic.beta_transmission(2.28, 135.0)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)
        self.assertAlmostEqual(value, 0.40783792731886737, places=12)

    def test_transmission_falls_as_material_thickens(self):
        self.assertLess(
            logic.beta_transmission(2.28, 300.0), logic.beta_transmission(2.28, 100.0)
        )

    def test_negative_areal_density_rejected(self):
        with self.assertRaises(ValueError):
            logic.beta_transmission(2.28, -1.0)


class PathAccounting(unittest.TestCase):
    def test_areal_density_is_thickness_times_density(self):
        self.assertAlmostEqual(
            logic.path_areal_density_mg_cm2(THIN_WALL), 135.0, places=9
        )

    def test_empty_path_has_no_areal_density(self):
        self.assertAlmostEqual(logic.path_areal_density_mg_cm2([]), 0.0, places=12)

    def test_two_items_accumulate(self):
        items = [
            {"thickness_cm": 0.05, "density_g_cm3": 2.7},
            {"thickness_cm": 0.02, "density_g_cm3": 8.96},
        ]
        self.assertAlmostEqual(
            logic.path_areal_density_mg_cm2(items), 135.0 + 179.2, places=9
        )

    def test_non_sequence_path_rejected(self):
        with self.assertRaises(ValueError):
            logic.path_areal_density_mg_cm2({"thickness_cm": 0.05})

    def test_non_dict_item_rejected(self):
        with self.assertRaises(ValueError):
            logic.path_areal_density_mg_cm2([0.05])

    def test_item_missing_density_rejected(self):
        with self.assertRaises(ValueError):
            logic.path_areal_density_mg_cm2([{"thickness_cm": 0.05}])

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            logic.path_areal_density_mg_cm2(
                [{"thickness_cm": 0.0, "density_g_cm3": 2.7}]
            )

    def test_negative_density_rejected(self):
        with self.assertRaises(ValueError):
            logic.path_areal_density_mg_cm2(
                [{"thickness_cm": 0.05, "density_g_cm3": -2.7}]
            )

    def test_opaque_item_blocks_the_sight_line(self):
        self.assertTrue(
            logic.sight_line_blocked(
                [{"thickness_cm": 0.05, "density_g_cm3": 2.7, "opaque": True}]
            )
        )

    def test_transparent_items_leave_the_sight_line_open(self):
        self.assertFalse(logic.sight_line_blocked(THIN_WALL))

    def test_sight_line_check_rejects_non_sequence(self):
        with self.assertRaises(ValueError):
            logic.sight_line_blocked("wall")


class PhotoemissionChecks(unittest.TestCase):
    def test_photon_energy_at_two_hundred_nanometre(self):
        self.assertAlmostEqual(logic.photon_energy_ev(200.0), 6.19920992, places=8)

    def test_zero_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            logic.photon_energy_ev(0.0)

    def test_negative_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            logic.photon_energy_ev(-220.0)

    def test_known_material_lookup(self):
        self.assertAlmostEqual(logic.work_function_ev("copper"), 4.65, places=9)

    def test_material_lookup_ignores_case_and_padding(self):
        self.assertAlmostEqual(logic.work_function_ev("  Aluminium "), 4.28, places=9)

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            logic.work_function_ev("unobtainium")

    def test_non_string_material_rejected(self):
        with self.assertRaises(ValueError):
            logic.work_function_ev(4.28)

    def test_short_wavelength_frees_an_electron(self):
        self.assertTrue(logic.photoemission_possible(220.0, "aluminium"))

    def test_long_wavelength_does_not(self):
        self.assertFalse(logic.photoemission_possible(400.0, "gold"))

    def test_margin_sign_agrees_with_the_verdict(self):
        self.assertGreater(logic.photoemission_margin_ev(220.0, "aluminium"), 0.0)
        self.assertLess(logic.photoemission_margin_ev(300.0, "copper"), 0.0)

    def test_photon_exactly_at_the_work_function_yields_nothing(self):
        wavelength = logic.HC_EV_NM / 4.28
        self.assertAlmostEqual(
            logic.photoemission_margin_ev(wavelength, "aluminium"), 0.0, places=12
        )
        self.assertFalse(logic.photoemission_possible(wavelength, "aluminium"))


class CaptureGeometry(unittest.TestCase):
    def test_capture_fraction_formula(self):
        self.assertAlmostEqual(
            logic.solid_angle_capture_fraction(0.5, 10.0), 0.5 / (4.0 * math.pi * 100.0),
            places=15,
        )

    def test_capture_falls_as_the_inverse_square(self):
        near = logic.solid_angle_capture_fraction(0.5, 10.0)
        far = logic.solid_angle_capture_fraction(0.5, 20.0)
        self.assertAlmostEqual(near / far, 4.0, places=9)

    def test_capture_is_clamped_at_unity(self):
        self.assertAlmostEqual(
            logic.solid_angle_capture_fraction(500.0, 0.1), 1.0, places=12
        )

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            logic.solid_angle_capture_fraction(0.5, 0.0)

    def test_negative_distance_rejected(self):
        with self.assertRaises(ValueError):
            logic.solid_angle_capture_fraction(0.5, -10.0)

    def test_zero_aperture_rejected(self):
        with self.assertRaises(ValueError):
            logic.solid_angle_capture_fraction(0.0, 10.0)


class DeliveredRate(unittest.TestCase):
    def test_delivered_rate_is_the_product(self):
        self.assertAlmostEqual(
            logic.delivered_rate_per_s(1.0e6, 0.5, 1.0e-3), 500.0, places=9
        )

    def test_transmission_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            logic.delivered_rate_per_s(1.0e6, 1.2, 1.0e-3)

    def test_negative_transmission_rejected(self):
        with self.assertRaises(ValueError):
            logic.delivered_rate_per_s(1.0e6, -0.1, 1.0e-3)

    def test_capture_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            logic.delivered_rate_per_s(1.0e6, 0.5, 1.4)

    def test_zero_emission_rate_rejected(self):
        with self.assertRaises(ValueError):
            logic.delivered_rate_per_s(0.0, 0.5, 1.0e-3)


class AimPointIdentity(unittest.TestCase):
    def test_matching_names_agree(self):
        self.assertTrue(
            logic.aim_point_matches_initiation_site("Iris-Gap-3", " iris-gap-3 ")
        )

    def test_different_names_disagree(self):
        self.assertFalse(
            logic.aim_point_matches_initiation_site("coax-gap-1", "iris-gap-3")
        )

    def test_empty_aim_point_rejected(self):
        with self.assertRaises(ValueError):
            logic.aim_point_matches_initiation_site("   ", "iris-gap-3")

    def test_non_string_site_rejected(self):
        with self.assertRaises(ValueError):
            logic.aim_point_matches_initiation_site("iris-gap-3", 3)


class GunAiming(unittest.TestCase):
    def test_beam_inside_the_gap_and_window_is_clean(self):
        out = logic.gun_aim_check(0.2, 1.0, 300.0)
        self.assertEqual(out["findings"], [])
        self.assertTrue(out["inside_gap"])

    def test_beam_beyond_the_half_gap_is_flagged(self):
        out = logic.gun_aim_check(0.8, 1.0, 300.0)
        self.assertIn("beam-misses-critical-gap", out["findings"])

    def test_representation_error_at_the_gap_edge_is_absorbed(self):
        # 0.1 + 0.2 lands one ULP above the 0.3 mm half-gap; still inside.
        out = logic.gun_aim_check(0.1 + 0.2, 0.6, 300.0)
        self.assertTrue(out["inside_gap"])

    def test_negative_offset_uses_magnitude(self):
        out = logic.gun_aim_check(-0.2, 1.0, 300.0)
        self.assertAlmostEqual(out["aim_offset_mm"], 0.2, places=12)
        self.assertTrue(out["inside_gap"])

    def test_landing_energy_below_the_window_is_flagged(self):
        out = logic.gun_aim_check(0.2, 1.0, 10.0)
        self.assertIn("landing-energy-outside-yield-window", out["findings"])

    def test_landing_energy_at_the_lower_bound_is_accepted(self):
        out = logic.gun_aim_check(0.2, 1.0, logic.DEFAULT_LANDING_WINDOW_EV[0])
        self.assertEqual(out["findings"], [])

    def test_landing_energy_above_the_window_is_flagged(self):
        out = logic.gun_aim_check(0.2, 1.0, 5000.0)
        self.assertIn("landing-energy-outside-yield-window", out["findings"])

    def test_custom_window_is_honoured(self):
        out = logic.gun_aim_check(0.2, 1.0, 40.0, window_ev=(20.0, 100.0))
        self.assertEqual(out["findings"], [])

    def test_zero_gap_height_rejected(self):
        with self.assertRaises(ValueError):
            logic.gun_aim_check(0.2, 0.0, 300.0)

    def test_zero_landing_energy_rejected(self):
        with self.assertRaises(ValueError):
            logic.gun_aim_check(0.2, 1.0, 0.0)

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            logic.gun_aim_check(0.2, 1.0, 300.0, window_ev=(2000.0, 50.0))

    def test_malformed_window_rejected(self):
        with self.assertRaises(ValueError):
            logic.gun_aim_check(0.2, 1.0, 300.0, window_ev=(50.0,))


class PlacementAssessment(unittest.TestCase):
    def test_radioactive_source_behind_a_thin_wall_is_acceptable(self):
        out = logic.assess_source_placement(radioactive_spec())
        self.assertTrue(out["acceptable"])
        self.assertAlmostEqual(out["delivered_rate_per_s"], 600.4121545466456, places=6)

    def test_thick_wall_blocks_the_source_and_starves_the_gap(self):
        out = logic.assess_source_placement(radioactive_spec(obstructions=THICK_WALL))
        self.assertIn(
            "beta-range-shorter-than-intervening-areal-density", out["findings"]
        )
        self.assertIn("delivered-rate-below-required-rate", out["findings"])
        self.assertFalse(out["acceptable"])

    def test_ultraviolet_illumination_on_aluminium_is_acceptable(self):
        out = logic.assess_source_placement(ultraviolet_spec())
        self.assertTrue(out["acceptable"])
        self.assertGreater(out["detail"]["photoemission_margin_ev"], 1.0)

    def test_opaque_barrier_defeats_the_illumination(self):
        out = logic.assess_source_placement(
            ultraviolet_spec(
                obstructions=[
                    {"thickness_cm": 0.2, "density_g_cm3": 2.7, "opaque": True}
                ]
            )
        )
        self.assertIn("sight-line-obstructed-by-opaque-barrier", out["findings"])
        self.assertAlmostEqual(out["transmission"], 0.0, places=15)

    def test_wavelength_below_the_copper_work_function_is_flagged(self):
        out = logic.assess_source_placement(
            ultraviolet_spec(wavelength_nm=300.0, target_surface_material="copper")
        )
        self.assertIn("photon-energy-below-surface-work-function", out["findings"])

    def test_aimed_electron_gun_is_acceptable(self):
        out = logic.assess_source_placement(gun_spec())
        self.assertTrue(out["acceptable"])
        self.assertTrue(out["detail"]["inside_gap"])

    def test_misaimed_electron_gun_is_flagged(self):
        out = logic.assess_source_placement(gun_spec(aim_offset_mm=0.9))
        self.assertIn("beam-misses-critical-gap", out["findings"])
        self.assertAlmostEqual(out["delivered_rate_per_s"], 0.0, places=12)

    def test_aim_point_away_from_the_initiation_site_is_flagged(self):
        out = logic.assess_source_placement(gun_spec(aim_point="coax-gap-1"))
        self.assertIn("aim-point-not-the-predicted-initiation-gap", out["findings"])

    def test_delivered_rate_one_ulp_under_the_requirement_still_passes(self):
        # capture is exactly 1/4 here, so the delivered rate is exactly 0,3/s
        # while the requirement carries the 0.1 + 0.2 representation error.
        out = logic.assess_source_placement(
            gun_spec(
                gap_aperture_area_cm2=4.0 * math.pi,
                source_to_gap_distance_cm=2.0,
                emission_rate_per_s=1.2,
                required_rate_per_s=0.1 + 0.2,
            )
        )
        self.assertAlmostEqual(out["delivered_rate_per_s"], 0.3, places=15)
        self.assertNotIn("delivered-rate-below-required-rate", out["findings"])
        self.assertTrue(out["acceptable"])

    def test_unknown_technique_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_source_placement(gun_spec(technique="flashlight"))

    def test_missing_common_key_rejected(self):
        spec = gun_spec()
        del spec["required_rate_per_s"]
        with self.assertRaises(ValueError):
            logic.assess_source_placement(spec)

    def test_missing_technique_specific_key_rejected(self):
        spec = radioactive_spec()
        del spec["beta_energy_mev"]
        with self.assertRaises(ValueError):
            logic.assess_source_placement(spec)

    def test_non_dict_spec_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_source_placement("radioactive-source")

    def test_zero_required_rate_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_source_placement(gun_spec(required_rate_per_s=0.0))


if __name__ == "__main__":
    unittest.main()
