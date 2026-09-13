"""Contract test for the ECSS-E-ST-20C 7.2.3.2 radiative-interface leaf.

Offline, deterministic, stdlib unittest only.
"""

import math
import unittest

from e20_antenna_radiative_interfaces_logic import (
    SPEED_OF_LIGHT_M_S,
    assess_radiative_interface,
    assess_surrounding_items,
    assessment_due,
    beam_sector,
    categorize_radiative_interaction,
    far_field_distance_m,
    field_region_at,
    free_space_transmission_loss_db,
    pattern_ripple_db,
    pointing_perturbation_deg,
    port_to_port_isolation_db,
    reactive_near_field_radius_m,
    reradiated_level_dbc,
    wavelength_m,
)


def antenna(**overrides):
    spec = {
        "aperture_diameter_m": 0.3,
        "frequency_hz": 2.2e9,
        "peak_gain_dbi": 15.0,
        "half_power_beamwidth_deg": 30.0,
        "project_phase": "b",
        "allowable_pattern_ripple_db": 0.5,
        "allowable_boresight_perturbation_deg": 0.5,
        "required_port_isolation_db": 40.0,
    }
    spec.update(overrides)
    return spec


def appendage(**overrides):
    item = {
        "id": "solar-array-wing",
        "distance_m": 2.5,
        "angular_offset_deg": 60.0,
        "gain_toward_item_dbi": -5.0,
        "radar_cross_section_m2": 0.6,
        "illuminated": True,
        "is_radiating_port": False,
    }
    item.update(overrides)
    return item


def neighbour_port(**overrides):
    item = {
        "id": "telemetry-patch",
        "distance_m": 2.0,
        "angular_offset_deg": 90.0,
        "gain_toward_item_dbi": -5.0,
        "port_gain_dbi": 0.0,
        "is_radiating_port": True,
    }
    item.update(overrides)
    return item


class FieldZones(unittest.TestCase):
    def test_wavelength_at_s_band(self):
        self.assertAlmostEqual(wavelength_m(2.2e9), SPEED_OF_LIGHT_M_S / 2.2e9, places=12)

    def test_zero_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            wavelength_m(0.0)

    def test_non_numeric_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            wavelength_m("s-band")

    def test_far_field_boundary_of_the_reference_antenna(self):
        lam = wavelength_m(2.2e9)
        self.assertAlmostEqual(far_field_distance_m(0.3, lam), 2.0 * 0.09 / lam, places=9)

    def test_reactive_boundary_sits_inside_the_far_field_boundary(self):
        lam = wavelength_m(2.2e9)
        self.assertLess(
            reactive_near_field_radius_m(0.3, lam), far_field_distance_m(0.3, lam)
        )

    def test_far_field_boundary_rejects_zero_aperture(self):
        with self.assertRaises(ValueError):
            far_field_distance_m(0.0, 0.136)

    def test_a_distant_item_is_in_the_far_field(self):
        self.assertEqual(field_region_at(2.5, 0.3, wavelength_m(2.2e9)), "far-field")

    def test_an_item_just_outside_the_reactive_zone_is_in_the_radiating_near_field(self):
        self.assertEqual(field_region_at(1.0, 0.3, wavelength_m(2.2e9)), "radiating-near-field")

    def test_a_very_close_item_is_in_the_reactive_near_field(self):
        self.assertEqual(field_region_at(0.2, 0.3, wavelength_m(2.2e9)), "reactive-near-field")

    def test_an_item_exactly_on_the_far_field_boundary_counts_as_far_field(self):
        lam = wavelength_m(2.2e9)
        boundary = far_field_distance_m(0.3, lam)
        self.assertEqual(field_region_at(boundary, 0.3, lam), "far-field")

    def test_zero_distance_is_rejected(self):
        with self.assertRaises(ValueError):
            field_region_at(0.0, 0.3, 0.136)


class BeamSectors(unittest.TestCase):
    def test_boresight_is_in_the_main_beam(self):
        self.assertEqual(beam_sector(0.0, 30.0), "main-beam")

    def test_the_half_power_point_is_still_main_beam(self):
        self.assertEqual(beam_sector(15.0, 30.0), "main-beam")

    def test_just_outside_the_half_power_point_is_the_skirt(self):
        self.assertEqual(beam_sector(20.0, 30.0), "main-lobe-skirt")

    def test_beyond_the_first_null_is_the_side_lobe_region(self):
        self.assertEqual(beam_sector(60.0, 30.0), "side-lobe-region")

    def test_offset_beyond_the_sphere_is_rejected(self):
        with self.assertRaises(ValueError):
            beam_sector(200.0, 30.0)

    def test_negative_offset_is_rejected(self):
        with self.assertRaises(ValueError):
            beam_sector(-5.0, 30.0)

    def test_beamwidth_of_a_half_sphere_is_rejected(self):
        with self.assertRaises(ValueError):
            beam_sector(10.0, 180.0)


class InteractionCategorisation(unittest.TestCase):
    def test_a_radiating_neighbour_is_port_to_port_coupling(self):
        self.assertEqual(
            categorize_radiative_interaction("far-field", "side-lobe-region", True, True),
            "port-to-port-coupling",
        )

    def test_a_shadowed_item_has_no_interaction_path(self):
        self.assertEqual(
            categorize_radiative_interaction("far-field", "main-beam", False, False),
            "no-interaction-path",
        )

    def test_an_item_on_boresight_blocks_the_main_beam(self):
        self.assertEqual(
            categorize_radiative_interaction("far-field", "main-beam", False, True),
            "main-beam-blockage",
        )

    def test_a_close_item_couples_in_the_near_field(self):
        self.assertEqual(
            categorize_radiative_interaction(
                "radiating-near-field", "side-lobe-region", False, True
            ),
            "near-field-coupling",
        )

    def test_a_far_skirt_item_scatters_from_the_main_lobe(self):
        self.assertEqual(
            categorize_radiative_interaction("far-field", "main-lobe-skirt", False, True),
            "main-lobe-scattering",
        )

    def test_uncategorized_field_region_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_radiative_interaction("somewhere", "main-beam", False, True)

    def test_uncategorized_beam_sector_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_radiative_interaction("far-field", "back-lobe", False, True)

    def test_non_boolean_port_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_radiative_interaction("far-field", "main-beam", "yes", True)


class CouplingArithmetic(unittest.TestCase):
    def test_free_space_loss_matches_the_spreading_formula(self):
        lam = wavelength_m(2.2e9)
        expected = 20.0 * math.log10(4.0 * math.pi * 2.0 / lam)
        self.assertAlmostEqual(free_space_transmission_loss_db(2.0, lam), expected, places=9)

    def test_doubling_the_distance_costs_six_decibels(self):
        lam = wavelength_m(2.2e9)
        near = free_space_transmission_loss_db(2.0, lam)
        far = free_space_transmission_loss_db(4.0, lam)
        self.assertAlmostEqual(far - near, 6.0206, places=3)

    def test_isolation_is_the_loss_less_both_gains(self):
        lam = wavelength_m(2.2e9)
        loss = free_space_transmission_loss_db(2.0, lam)
        self.assertAlmostEqual(
            port_to_port_isolation_db(-5.0, 0.0, 2.0, lam), loss + 5.0, places=9
        )

    def test_reradiated_level_falls_with_distance(self):
        near = reradiated_level_dbc(-5.0, 15.0, 0.6, 2.5)
        far = reradiated_level_dbc(-5.0, 15.0, 0.6, 5.0)
        self.assertAlmostEqual(near - far, 6.0206, places=3)

    def test_reradiated_level_of_the_reference_appendage(self):
        self.assertAlmostEqual(reradiated_level_dbc(-5.0, 15.0, 0.6, 2.5), -41.16939, places=4)

    def test_gain_toward_item_above_the_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            reradiated_level_dbc(20.0, 15.0, 0.6, 2.5)

    def test_zero_cross_section_is_rejected(self):
        with self.assertRaises(ValueError):
            reradiated_level_dbc(-5.0, 15.0, 0.0, 2.5)


class RippleAndPointing(unittest.TestCase):
    def test_ripple_of_a_twenty_decibel_scatterer(self):
        self.assertAlmostEqual(pattern_ripple_db(-20.0), 1.7430, places=3)

    def test_a_quieter_scatterer_ripples_less(self):
        self.assertLess(pattern_ripple_db(-40.0), pattern_ripple_db(-20.0))

    def test_a_scatterer_at_the_direct_level_is_rejected(self):
        with self.assertRaises(ValueError):
            pattern_ripple_db(0.0)

    def test_an_infinite_level_is_rejected(self):
        with self.assertRaises(ValueError):
            pattern_ripple_db(float("inf"))

    def test_pointing_shift_scales_with_the_beamwidth(self):
        narrow = pointing_perturbation_deg(-30.0, 1.0)
        wide = pointing_perturbation_deg(-30.0, 2.0)
        self.assertAlmostEqual(wide, 2.0 * narrow, places=12)

    def test_pointing_shift_of_the_reference_case(self):
        self.assertAlmostEqual(pointing_perturbation_deg(-40.0, 30.0), 0.15, places=6)

    def test_pointing_shift_rejects_a_zero_beamwidth(self):
        with self.assertRaises(ValueError):
            pointing_perturbation_deg(-40.0, 0.0)


class PhaseGate(unittest.TestCase):
    def test_phase_b_is_due(self):
        self.assertTrue(assessment_due("B"))

    def test_phase_d_is_due(self):
        self.assertTrue(assessment_due("d"))

    def test_phase_a_is_not_yet_due(self):
        self.assertFalse(assessment_due("a"))

    def test_uncategorized_phase_is_rejected(self):
        with self.assertRaises(ValueError):
            assessment_due("phase-zero")

    def test_non_string_phase_is_rejected(self):
        with self.assertRaises(ValueError):
            assessment_due(2)


class InterfaceAssessment(unittest.TestCase):
    def test_a_quiet_side_lobe_appendage_is_compliant(self):
        result = assess_radiative_interface(antenna(), appendage())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["interaction_path"], "side-lobe-scattering")
        self.assertEqual(result["field_region"], "far-field")
        self.assertAlmostEqual(result["pattern_ripple_db"], 0.1518, places=3)

    def test_a_large_close_scatterer_breaks_the_ripple_allowable(self):
        result = assess_radiative_interface(
            antenna(), appendage(distance_m=1.4, radar_cross_section_m2=20.0)
        )
        self.assertIn("pattern-ripple-exceeds-allowable", result["findings"])
        self.assertFalse(result["compliant"])

    def test_ripple_exactly_at_the_allowable_is_compliant(self):
        baseline = assess_radiative_interface(antenna(), appendage())
        tight = assess_radiative_interface(
            antenna(allowable_pattern_ripple_db=baseline["pattern_ripple_db"]),
            appendage(),
        )
        self.assertNotIn("pattern-ripple-exceeds-allowable", tight["findings"])
        self.assertTrue(tight["compliant"])

    def test_boresight_perturbation_exactly_at_the_allowable_is_compliant(self):
        baseline = assess_radiative_interface(antenna(), appendage())
        tight = assess_radiative_interface(
            antenna(
                allowable_boresight_perturbation_deg=baseline["pointing_perturbation_deg"]
            ),
            appendage(),
        )
        self.assertNotIn("boresight-perturbation-exceeds-allowable", tight["findings"])

    def test_a_tight_boresight_allowable_is_flagged(self):
        result = assess_radiative_interface(
            antenna(allowable_boresight_perturbation_deg=0.001), appendage()
        )
        self.assertIn("boresight-perturbation-exceeds-allowable", result["findings"])

    def test_missing_ripple_allowable_is_itself_a_finding(self):
        spec = antenna()
        del spec["allowable_pattern_ripple_db"]
        result = assess_radiative_interface(spec, appendage())
        self.assertIn("no-allowable-pattern-ripple-on-record", result["findings"])

    def test_an_item_on_boresight_is_flagged_as_blockage(self):
        result = assess_radiative_interface(antenna(), appendage(angular_offset_deg=5.0))
        self.assertEqual(result["interaction_path"], "main-beam-blockage")
        self.assertIn("appendage-inside-the-main-beam", result["findings"])

    def test_a_near_field_item_demands_a_full_wave_model(self):
        result = assess_radiative_interface(antenna(), appendage(distance_m=1.0))
        self.assertEqual(result["interaction_path"], "near-field-coupling")
        self.assertIn("near-field-coupling-requires-full-wave-model", result["findings"])
        self.assertIsNone(result["pattern_ripple_db"])

    def test_a_shadowed_item_is_dropped_rather_than_charged(self):
        result = assess_radiative_interface(antenna(), appendage(illuminated=False))
        self.assertEqual(result["interaction_path"], "no-interaction-path")
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["reradiated_level_dbc"])

    def test_a_neighbouring_port_meets_the_isolation_requirement(self):
        result = assess_radiative_interface(antenna(), neighbour_port())
        self.assertEqual(result["interaction_path"], "port-to-port-coupling")
        self.assertTrue(result["compliant"])
        self.assertGreater(result["port_isolation_db"], 40.0)

    def test_two_high_gain_ports_fail_the_isolation_requirement(self):
        result = assess_radiative_interface(
            antenna(),
            neighbour_port(distance_m=1.5, gain_toward_item_dbi=5.0, port_gain_dbi=5.0),
        )
        self.assertIn("port-to-port-isolation-below-required", result["findings"])

    def test_isolation_exactly_at_the_requirement_is_compliant(self):
        baseline = assess_radiative_interface(antenna(), neighbour_port())
        tight = assess_radiative_interface(
            antenna(required_port_isolation_db=baseline["port_isolation_db"]),
            neighbour_port(),
        )
        self.assertNotIn("port-to-port-isolation-below-required", tight["findings"])
        self.assertTrue(tight["compliant"])

    def test_missing_isolation_requirement_is_itself_a_finding(self):
        spec = antenna()
        del spec["required_port_isolation_db"]
        result = assess_radiative_interface(spec, neighbour_port())
        self.assertIn("no-required-port-isolation-on-record", result["findings"])

    def test_a_near_field_neighbouring_port_is_flagged_as_well(self):
        result = assess_radiative_interface(antenna(), neighbour_port(distance_m=0.8))
        self.assertIn("near-field-coupling-requires-full-wave-model", result["findings"])

    def test_an_item_without_an_id_is_rejected(self):
        item = appendage()
        del item["id"]
        with self.assertRaises(ValueError):
            assess_radiative_interface(antenna(), item)

    def test_an_antenna_without_a_peak_gain_is_rejected(self):
        spec = antenna()
        del spec["peak_gain_dbi"]
        with self.assertRaises(ValueError):
            assess_radiative_interface(spec, appendage())

    def test_a_non_mapping_item_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiative_interface(antenna(), "solar-array-wing")


class SurroundingSetAssessment(unittest.TestCase):
    def test_a_clean_configuration_is_compliant(self):
        result = assess_surrounding_items(antenna(), [appendage(), neighbour_port()])
        self.assertTrue(result["assessment_due"])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["non_compliant_items"], [])
        self.assertAlmostEqual(result["worst_pattern_ripple_db"], 0.1518, places=3)
        self.assertIsNotNone(result["minimum_port_isolation_db"])

    def test_one_bad_appendage_sinks_the_configuration(self):
        result = assess_surrounding_items(
            antenna(),
            [appendage(distance_m=1.4, radar_cross_section_m2=20.0), neighbour_port()],
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["non_compliant_items"], ["solar-array-wing"])

    def test_phase_a_defers_the_assessment(self):
        result = assess_surrounding_items(antenna(project_phase="a"), [appendage()])
        self.assertFalse(result["assessment_due"])
        self.assertEqual(result["status"], "deferred-until-phase-b")
        self.assertFalse(result["compliant"])

    def test_duplicate_item_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_surrounding_items(antenna(), [appendage(), appendage()])

    def test_an_empty_item_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surrounding_items(antenna(), [])

    def test_a_non_mapping_antenna_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surrounding_items(["antenna"], [appendage()])


if __name__ == "__main__":
    unittest.main()
