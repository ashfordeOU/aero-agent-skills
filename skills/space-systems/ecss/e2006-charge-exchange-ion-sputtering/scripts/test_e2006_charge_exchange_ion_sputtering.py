#!/usr/bin/env python3
"""Gate 3 contract test for e2006-charge-exchange-ion-sputtering.

Offline, deterministic, stdlib unittest. Exercises the material table,
near-threshold sputter yield, exposure categorization, ion number flux,
erosion rate, erosion depth, allowance and coating checks and the
aggregation of the clause 11.2.4 logic, including every ValueError path
and the at-the-limit boundary cases.
"""

import unittest

from e2006_charge_exchange_ion_sputtering_logic import (
    BACKFLOW_EXPOSURE,
    DIRECT_BEAM_EXPOSURE,
    ELEMENTARY_CHARGE_C,
    NO_EXPOSURE,
    assess_erosion_campaign,
    assess_surface_erosion,
    categorize_ion_exposure,
    check_coating_reserve,
    check_erosion_allowance,
    erosion_depth_um,
    erosion_rate_m_per_s,
    ion_number_flux,
    material_properties,
    sputter_yield,
)


def exposed_surface(**overrides):
    """Build a surface record that satisfies every clause 11.2.4 check."""
    surface = {
        "id": "RADIATOR-PANEL-1",
        "material": "aluminium-alloy",
        "ion_energy_ev": 100.0,
        "current_density_a_m2": 2.0e-5,
        "charge_state": 1,
        "exposure_time_s": 1.5768e8,
        "surface_angle_deg": 55.0,
        "plume_half_angle_deg": 20.0,
        "allowable_depth_um": 0.5,
        "coating_thickness_um": 2.0,
        "redeposition_assessed": True,
    }
    surface.update(overrides)
    return surface


class MaterialTableTests(unittest.TestCase):
    def test_known_material_returns_fit_constants(self):
        properties = material_properties("aluminium-alloy")
        self.assertAlmostEqual(properties["threshold_ev"], 20.0)
        self.assertAlmostEqual(properties["yield_coefficient"], 0.012)
        self.assertEqual(properties["material"], "aluminium-alloy")

    def test_case_and_separators_are_normalized(self):
        properties = material_properties(" Silver_Coating ")
        self.assertEqual(properties["material"], "silver-coating")

    def test_returned_mapping_is_a_copy(self):
        properties = material_properties("quartz-osr")
        properties["threshold_ev"] = 1.0
        self.assertAlmostEqual(material_properties("quartz-osr")["threshold_ev"], 30.0)

    def test_unknown_material_is_rejected(self):
        with self.assertRaises(ValueError):
            material_properties("beryllium-mirror")

    def test_empty_material_is_rejected(self):
        with self.assertRaises(ValueError):
            material_properties("   ")

    def test_non_string_material_is_rejected(self):
        with self.assertRaises(ValueError):
            material_properties(42)


class SputterYieldTests(unittest.TestCase):
    def test_yield_at_one_hundred_electronvolts(self):
        self.assertAlmostEqual(
            sputter_yield("aluminium-alloy", 100.0), 0.36669, places=4
        )

    def test_energy_below_threshold_does_not_sputter(self):
        self.assertAlmostEqual(sputter_yield("aluminium-alloy", 12.0), 0.0)

    def test_energy_exactly_at_threshold_does_not_sputter(self):
        self.assertAlmostEqual(sputter_yield("aluminium-alloy", 20.0), 0.0)

    def test_threshold_representation_error_is_absorbed(self):
        # A few ULPs above the 15 eV threshold of the blanket material is
        # still the threshold, not an eroding impact.
        energy = 15.0 * (1.0 + 2.0 ** -50)
        self.assertGreater(energy, 15.0)
        self.assertAlmostEqual(sputter_yield("polyimide-blanket", energy), 0.0)

    def test_yield_increases_with_energy(self):
        low = sputter_yield("aluminium-alloy", 60.0)
        high = sputter_yield("aluminium-alloy", 200.0)
        self.assertGreater(high, low)

    def test_yield_saturates_at_the_tabulated_maximum(self):
        self.assertAlmostEqual(sputter_yield("silver-coating", 1.0e5), 4.0)

    def test_negative_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            sputter_yield("aluminium-alloy", -5.0)

    def test_non_numeric_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            sputter_yield("aluminium-alloy", "100")

    def test_unknown_material_is_rejected_by_the_yield(self):
        with self.assertRaises(ValueError):
            sputter_yield("beryllium-mirror", 100.0)


class ExposureCategorizationTests(unittest.TestCase):
    def test_surface_inside_the_cone_takes_direct_impingement(self):
        self.assertEqual(categorize_ion_exposure(8.0, 20.0), DIRECT_BEAM_EXPOSURE)

    def test_surface_at_the_cone_edge_within_representation_is_direct(self):
        self.assertGreater(0.1 + 0.2, 0.3)
        self.assertEqual(
            categorize_ion_exposure(0.1 + 0.2, 0.3), DIRECT_BEAM_EXPOSURE
        )

    def test_surface_outside_the_cone_sees_backflow(self):
        self.assertEqual(categorize_ion_exposure(70.0, 20.0), BACKFLOW_EXPOSURE)

    def test_shadowed_surface_sees_no_ions(self):
        self.assertEqual(categorize_ion_exposure(70.0, 20.0, False), NO_EXPOSURE)

    def test_negative_surface_angle_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_ion_exposure(-1.0, 20.0)

    def test_zero_half_angle_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_ion_exposure(10.0, 0.0)

    def test_non_boolean_line_of_sight_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_ion_exposure(10.0, 20.0, 1)


class IonFluxTests(unittest.TestCase):
    def test_one_elementary_charge_per_second_is_one_ion(self):
        self.assertAlmostEqual(ion_number_flux(ELEMENTARY_CHARGE_C, 1), 1.0)

    def test_doubly_charged_ions_halve_the_number_flux(self):
        single = ion_number_flux(2.0e-5, 1)
        double = ion_number_flux(2.0e-5, 2)
        self.assertAlmostEqual(double * 2.0, single, places=6)

    def test_zero_current_density_gives_no_flux(self):
        self.assertAlmostEqual(ion_number_flux(0.0, 1), 0.0)

    def test_zero_charge_state_is_rejected(self):
        with self.assertRaises(ValueError):
            ion_number_flux(2.0e-5, 0)

    def test_non_integer_charge_state_is_rejected(self):
        with self.assertRaises(ValueError):
            ion_number_flux(2.0e-5, 1.5)

    def test_boolean_charge_state_is_rejected(self):
        with self.assertRaises(ValueError):
            ion_number_flux(2.0e-5, True)

    def test_negative_current_density_is_rejected(self):
        with self.assertRaises(ValueError):
            ion_number_flux(-2.0e-5, 1)


class ErosionRateTests(unittest.TestCase):
    def test_rate_from_flux_yield_and_number_density(self):
        self.assertAlmostEqual(
            erosion_rate_m_per_s(1.0e18, 0.5, 1.0e28) * 1.0e11, 5.0, places=9
        )

    def test_rate_scales_linearly_with_yield(self):
        low = erosion_rate_m_per_s(1.0e18, 0.5, 1.0e28)
        high = erosion_rate_m_per_s(1.0e18, 1.0, 1.0e28)
        self.assertAlmostEqual(high, 2.0 * low, places=18)

    def test_zero_yield_erodes_nothing(self):
        self.assertAlmostEqual(erosion_rate_m_per_s(1.0e18, 0.0, 1.0e28), 0.0)

    def test_zero_number_density_is_rejected(self):
        with self.assertRaises(ValueError):
            erosion_rate_m_per_s(1.0e18, 0.5, 0.0)

    def test_negative_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            erosion_rate_m_per_s(-1.0e18, 0.5, 1.0e28)


class ErosionDepthTests(unittest.TestCase):
    def test_depth_in_micrometres(self):
        self.assertAlmostEqual(erosion_depth_um(5.0e-11, 1.0e6), 50.0, places=9)

    def test_depth_scales_with_exposure_time(self):
        short = erosion_depth_um(5.0e-11, 1.0e6)
        long_run = erosion_depth_um(5.0e-11, 3.0e6)
        self.assertAlmostEqual(long_run, 3.0 * short, places=9)

    def test_zero_exposure_time_is_rejected(self):
        with self.assertRaises(ValueError):
            erosion_depth_um(5.0e-11, 0.0)

    def test_negative_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            erosion_depth_um(-5.0e-11, 1.0e6)


class ErosionAllowanceTests(unittest.TestCase):
    def test_margin_and_utilisation_are_reported(self):
        check = check_erosion_allowance(0.2, 0.5)
        self.assertAlmostEqual(check["margin_um"], 0.3)
        self.assertAlmostEqual(check["utilisation"], 0.4)
        self.assertTrue(check["compliant"])

    def test_depth_exactly_at_the_allowance_passes(self):
        check = check_erosion_allowance(0.5, 0.5)
        self.assertTrue(check["compliant"])
        self.assertAlmostEqual(check["margin_um"], 0.0)

    def test_representation_error_at_the_allowance_is_absorbed(self):
        depth = 0.1 + 0.2
        self.assertGreater(depth, 0.3)
        check = check_erosion_allowance(depth, 0.3)
        self.assertTrue(check["compliant"])

    def test_depth_above_the_allowance_fails(self):
        check = check_erosion_allowance(0.9, 0.5)
        self.assertFalse(check["compliant"])
        self.assertLess(check["margin_um"], 0.0)

    def test_non_positive_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            check_erosion_allowance(0.2, 0.0)


class CoatingReserveTests(unittest.TestCase):
    def test_coating_survives_with_reserve(self):
        check = check_coating_reserve(0.4, 2.0)
        self.assertTrue(check["coating_intact"])
        self.assertAlmostEqual(check["remaining_um"], 1.6)

    def test_erosion_exactly_at_the_coating_thickness_is_intact(self):
        check = check_coating_reserve(2.0, 2.0)
        self.assertTrue(check["coating_intact"])

    def test_erosion_through_the_coating_is_reported(self):
        check = check_coating_reserve(2.4, 2.0)
        self.assertFalse(check["coating_intact"])
        self.assertLess(check["remaining_um"], 0.0)

    def test_zero_coating_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            check_coating_reserve(0.4, 0.0)


class SurfaceErosionTests(unittest.TestCase):
    def test_compliant_surface_has_no_findings(self):
        result = assess_surface_erosion(exposed_surface())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["exposure"], BACKFLOW_EXPOSURE)

    def test_depth_matches_the_hand_computed_value(self):
        result = assess_surface_erosion(exposed_surface())
        self.assertAlmostEqual(result["erosion_depth_um"], 0.1197, places=4)
        self.assertAlmostEqual(
            result["sputter_yield_atoms_per_ion"], 0.36669, places=4
        )

    def test_exceeding_the_agreed_limit_is_flagged(self):
        result = assess_surface_erosion(exposed_surface(allowable_depth_um=0.05))
        self.assertIn("erosion-depth-exceeds-agreed-limit", result["findings"])
        self.assertFalse(result["compliant"])

    def test_missing_agreed_limit_is_flagged(self):
        result = assess_surface_erosion(exposed_surface(allowable_depth_um=None))
        self.assertIn("agreed-erosion-limit-not-recorded", result["findings"])
        self.assertIsNone(result["allowance_check"])

    def test_surface_inside_the_beam_cone_is_flagged(self):
        result = assess_surface_erosion(exposed_surface(surface_angle_deg=5.0))
        self.assertIn("surface-inside-direct-beam-cone", result["findings"])
        self.assertEqual(result["exposure"], DIRECT_BEAM_EXPOSURE)

    def test_shadowed_surface_erodes_nothing(self):
        result = assess_surface_erosion(exposed_surface(line_of_sight=False))
        self.assertEqual(result["exposure"], NO_EXPOSURE)
        self.assertAlmostEqual(result["erosion_depth_um"], 0.0)
        self.assertTrue(result["compliant"])

    def test_energy_below_threshold_is_recorded_as_an_observation(self):
        result = assess_surface_erosion(exposed_surface(ion_energy_ev=12.0))
        self.assertIn("ion-energy-below-sputter-threshold", result["observations"])
        self.assertAlmostEqual(result["erosion_depth_um"], 0.0)
        self.assertTrue(result["compliant"])

    def test_coating_breach_is_flagged(self):
        result = assess_surface_erosion(
            exposed_surface(coating_thickness_um=0.05, allowable_depth_um=1.0)
        )
        self.assertIn("erosion-breaches-coating-thickness", result["findings"])

    def test_unassessed_redeposition_is_an_observation_only(self):
        surface = exposed_surface()
        del surface["redeposition_assessed"]
        result = assess_surface_erosion(surface)
        self.assertTrue(result["compliant"])
        self.assertIn(
            "sputtered-material-redeposition-not-assessed", result["observations"]
        )

    def test_doubly_charged_ions_lower_the_depth(self):
        single = assess_surface_erosion(exposed_surface())
        double = assess_surface_erosion(exposed_surface(charge_state=2))
        self.assertAlmostEqual(
            double["erosion_depth_um"] * 2.0, single["erosion_depth_um"], places=9
        )

    def test_missing_required_key_is_rejected(self):
        surface = exposed_surface()
        del surface["exposure_time_s"]
        with self.assertRaises(ValueError):
            assess_surface_erosion(surface)

    def test_non_mapping_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_erosion(["RADIATOR-PANEL-1"])

    def test_blank_surface_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_erosion(exposed_surface(id=" "))

    def test_unknown_material_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_erosion(exposed_surface(material="beryllium-mirror"))


class CampaignTests(unittest.TestCase):
    def test_all_compliant_campaign_is_compliant(self):
        summary = assess_erosion_campaign(
            [exposed_surface(), exposed_surface(id="THRUSTER-BOOM-SHIELD")]
        )
        self.assertTrue(summary["compliant"])
        self.assertEqual(summary["compliant_count"], 2)
        self.assertEqual(summary["noncompliant_ids"], [])

    def test_worst_surface_is_named(self):
        summary = assess_erosion_campaign(
            [
                exposed_surface(),
                exposed_surface(
                    id="SILVER-OSR", material="silver-coating", ion_energy_ev=300.0
                ),
            ]
        )
        self.assertEqual(summary["worst_surface_id"], "SILVER-OSR")
        self.assertIn("SILVER-OSR", summary["noncompliant_ids"])
        self.assertIn(
            "erosion-depth-exceeds-agreed-limit",
            summary["findings_by_surface"]["SILVER-OSR"],
        )

    def test_empty_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_erosion_campaign([])

    def test_non_list_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_erosion_campaign(exposed_surface())

    def test_duplicate_surface_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_erosion_campaign([exposed_surface(), exposed_surface()])


if __name__ == "__main__":
    unittest.main()
