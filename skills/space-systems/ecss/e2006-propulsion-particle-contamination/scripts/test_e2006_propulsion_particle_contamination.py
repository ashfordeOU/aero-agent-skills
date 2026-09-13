#!/usr/bin/env python3
"""Gate 3 contract test for e2006-propulsion-particle-contamination.

Offline, deterministic, stdlib unittest. Exercises species categorization,
transport-path resolution, plume and backflow flux, accumulation, film
thickness, allowance comparison and aggregation for the clause 11.2.3
logic, including every ValueError path and the at-the-limit boundaries.
"""

import math
import unittest

from e2006_propulsion_particle_contamination_logic import (
    CHARGE_EXCHANGE_PATH,
    CHARGED_FAMILY,
    DIRECT_PATH,
    NEUTRAL_FAMILY,
    NEUTRAL_SCATTER_PATH,
    NO_TRANSPORT_PATH,
    accumulate_deposition,
    assess_deposition_campaign,
    assess_surface_deposition,
    categorize_efflux_species,
    check_deposition_allowance,
    deposition_thickness_nm,
    plume_transport_path,
    surface_particle_flux,
)


def neutral_source(**overrides):
    source = {
        "species": "unionized-propellant",
        "source_rate_kg_s": 1.0e-7,
        "distance_m": 2.0,
        "incidence_deg": 30.0,
        "plume_half_angle_deg": 20.0,
        "surface_angle_deg": 45.0,
        "backflow_fraction": 0.02,
        "sticking_coefficient": 0.5,
        "firing_duration_s": 3.6e6,
        "film_density_kg_m3": 1400.0,
    }
    source.update(overrides)
    return source


def charged_source(**overrides):
    source = {
        "species": "charge-exchange-ion",
        "source_rate_kg_s": 2.0e-8,
        "distance_m": 2.0,
        "incidence_deg": 30.0,
        "plume_half_angle_deg": 20.0,
        "surface_angle_deg": 45.0,
        "backflow_fraction": 0.05,
        "sticking_coefficient": 1.0,
        "firing_duration_s": 3.6e6,
        "film_density_kg_m3": 4500.0,
    }
    source.update(overrides)
    return source


def compliant_surface(**overrides):
    surface = {
        "id": "OSR-PANEL-A",
        "allowable_thickness_nm": 100.0,
        "sources": [neutral_source(), charged_source()],
    }
    surface.update(overrides)
    return surface


class SpeciesCategorizationTests(unittest.TestCase):
    def test_unionized_propellant_is_neutral(self):
        self.assertEqual(
            categorize_efflux_species("unionized-propellant"), NEUTRAL_FAMILY
        )

    def test_beam_ion_is_charged(self):
        self.assertEqual(categorize_efflux_species("beam-ion"), CHARGED_FAMILY)

    def test_sputtered_neutral_and_sputtered_ion_differ(self):
        self.assertEqual(categorize_efflux_species("sputtered-neutral"), NEUTRAL_FAMILY)
        self.assertEqual(categorize_efflux_species("sputtered-ion"), CHARGED_FAMILY)

    def test_case_and_separators_are_normalized(self):
        self.assertEqual(
            categorize_efflux_species(" Charge_Exchange Ion "), CHARGED_FAMILY
        )

    def test_unknown_species_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_efflux_species("micrometeoroid-fragment")

    def test_empty_species_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_efflux_species("  ")

    def test_non_string_species_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_efflux_species(None)


class TransportPathTests(unittest.TestCase):
    def test_surface_inside_the_cone_takes_direct_impingement(self):
        transport = plume_transport_path("beam-ion", 10.0, 20.0)
        self.assertEqual(transport["path"], DIRECT_PATH)
        self.assertTrue(transport["inside_cone"])

    def test_surface_at_the_cone_edge_within_representation_is_direct(self):
        # 0.1 + 0.2 lands a few ULPs above 0.3, yet the surface sits on the
        # cone edge and is physically inside it.
        transport = plume_transport_path("beam-ion", 0.1 + 0.2, 0.3)
        self.assertGreater(0.1 + 0.2, 0.3)
        self.assertEqual(transport["path"], DIRECT_PATH)

    def test_charged_species_outside_the_cone_takes_charge_exchange(self):
        transport = plume_transport_path("charge-exchange-ion", 60.0, 20.0)
        self.assertEqual(transport["path"], CHARGE_EXCHANGE_PATH)

    def test_neutral_species_outside_the_cone_takes_scatter_backflow(self):
        transport = plume_transport_path("cathode-neutral-flow", 60.0, 20.0)
        self.assertEqual(transport["path"], NEUTRAL_SCATTER_PATH)

    def test_blocked_line_of_sight_gives_no_transport_path(self):
        transport = plume_transport_path("beam-ion", 10.0, 20.0, False)
        self.assertEqual(transport["path"], NO_TRANSPORT_PATH)
        self.assertFalse(transport["inside_cone"])

    def test_negative_surface_angle_is_rejected(self):
        with self.assertRaises(ValueError):
            plume_transport_path("beam-ion", -5.0, 20.0)

    def test_half_angle_above_ninety_degrees_is_rejected(self):
        with self.assertRaises(ValueError):
            plume_transport_path("beam-ion", 10.0, 120.0)

    def test_zero_half_angle_is_rejected(self):
        with self.assertRaises(ValueError):
            plume_transport_path("beam-ion", 10.0, 0.0)

    def test_non_boolean_line_of_sight_is_rejected(self):
        with self.assertRaises(ValueError):
            plume_transport_path("beam-ion", 10.0, 20.0, "yes")


class SurfaceFluxTests(unittest.TestCase):
    def test_direct_flux_matches_the_cone_solid_angle_result(self):
        # A 60 deg half angle subtends pi steradians, so a 1 m normal
        # surface sees rate / pi.
        flux = surface_particle_flux(1.0e-6, 1.0, 0.0, DIRECT_PATH, 60.0)
        self.assertAlmostEqual(flux * 1.0e6, 1.0 / math.pi, places=9)

    def test_narrower_cone_concentrates_the_flux(self):
        wide = surface_particle_flux(1.0e-6, 1.0, 0.0, DIRECT_PATH, 60.0)
        narrow = surface_particle_flux(1.0e-6, 1.0, 0.0, DIRECT_PATH, 15.0)
        self.assertGreater(narrow, wide)

    def test_flux_falls_with_the_inverse_square_of_distance(self):
        near = surface_particle_flux(1.0e-6, 1.0, 0.0, DIRECT_PATH, 30.0)
        far = surface_particle_flux(1.0e-6, 2.0, 0.0, DIRECT_PATH, 30.0)
        self.assertAlmostEqual(far * 4.0, near, places=12)

    def test_incidence_cosine_reduces_the_flux(self):
        normal = surface_particle_flux(1.0e-6, 1.0, 0.0, DIRECT_PATH, 30.0)
        oblique = surface_particle_flux(1.0e-6, 1.0, 60.0, DIRECT_PATH, 30.0)
        self.assertAlmostEqual(oblique * 2.0, normal, places=12)

    def test_grazing_incidence_deposits_nothing(self):
        flux = surface_particle_flux(1.0e-6, 1.0, 90.0, DIRECT_PATH, 30.0)
        self.assertAlmostEqual(flux, 0.0, places=18)

    def test_backflow_flux_spreads_over_the_full_sphere(self):
        flux = surface_particle_flux(
            1.0e-6, 2.0, 60.0, CHARGE_EXCHANGE_PATH, 20.0, 0.1
        )
        self.assertAlmostEqual(flux * 1.0e10, 9.947183943, places=6)

    def test_no_transport_path_returns_zero_flux(self):
        flux = surface_particle_flux(1.0e-6, 2.0, 0.0, NO_TRANSPORT_PATH, 20.0, 0.1)
        self.assertAlmostEqual(flux, 0.0, places=18)

    def test_unknown_path_is_rejected(self):
        with self.assertRaises(ValueError):
            surface_particle_flux(1.0e-6, 2.0, 0.0, "sputter-transport", 20.0)

    def test_zero_distance_is_rejected(self):
        with self.assertRaises(ValueError):
            surface_particle_flux(1.0e-6, 0.0, 0.0, DIRECT_PATH, 20.0)

    def test_backflow_fraction_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            surface_particle_flux(
                1.0e-6, 2.0, 0.0, NEUTRAL_SCATTER_PATH, 20.0, 1.4
            )

    def test_incidence_beyond_ninety_degrees_is_rejected(self):
        with self.assertRaises(ValueError):
            surface_particle_flux(1.0e-6, 2.0, 120.0, DIRECT_PATH, 20.0)

    def test_non_positive_source_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            surface_particle_flux(0.0, 2.0, 0.0, DIRECT_PATH, 20.0)


class AccumulationTests(unittest.TestCase):
    def test_deposited_mass_scales_with_duration(self):
        short = accumulate_deposition(1.0e-11, 1.0e3, 1.0)
        long_run = accumulate_deposition(1.0e-11, 2.0e3, 1.0)
        self.assertAlmostEqual(long_run, 2.0 * short, places=18)

    def test_sticking_coefficient_scales_the_deposit(self):
        full = accumulate_deposition(1.0e-11, 1.0e3, 1.0)
        half = accumulate_deposition(1.0e-11, 1.0e3, 0.5)
        self.assertAlmostEqual(half * 2.0, full, places=18)

    def test_zero_flux_deposits_nothing(self):
        self.assertAlmostEqual(accumulate_deposition(0.0, 1.0e3, 1.0), 0.0, places=18)

    def test_zero_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_deposition(1.0e-11, 0.0, 1.0)

    def test_sticking_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_deposition(1.0e-11, 1.0e3, 1.2)

    def test_negative_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_deposition(-1.0e-11, 1.0e3, 1.0)


class ThicknessTests(unittest.TestCase):
    def test_areal_mass_converts_to_nanometres(self):
        self.assertAlmostEqual(deposition_thickness_nm(6.3e-5, 1400.0), 45.0, places=9)

    def test_denser_film_is_thinner(self):
        light = deposition_thickness_nm(6.3e-5, 1400.0)
        heavy = deposition_thickness_nm(6.3e-5, 4200.0)
        self.assertAlmostEqual(heavy * 3.0, light, places=9)

    def test_zero_density_is_rejected(self):
        with self.assertRaises(ValueError):
            deposition_thickness_nm(6.3e-5, 0.0)

    def test_negative_areal_mass_is_rejected(self):
        with self.assertRaises(ValueError):
            deposition_thickness_nm(-1.0e-6, 1400.0)


class AllowanceTests(unittest.TestCase):
    def test_margin_and_utilisation_are_reported(self):
        check = check_deposition_allowance(40.0, 100.0)
        self.assertAlmostEqual(check["margin_nm"], 60.0)
        self.assertAlmostEqual(check["utilisation"], 0.4)
        self.assertTrue(check["compliant"])

    def test_thickness_exactly_at_the_limit_passes(self):
        check = check_deposition_allowance(100.0, 100.0)
        self.assertTrue(check["compliant"])
        self.assertAlmostEqual(check["margin_nm"], 0.0)

    def test_representation_error_at_the_limit_is_absorbed(self):
        thickness = 0.1 + 0.2
        self.assertGreater(thickness, 0.3)
        check = check_deposition_allowance(thickness, 0.3)
        self.assertTrue(check["compliant"])

    def test_thickness_above_the_limit_fails(self):
        check = check_deposition_allowance(140.0, 100.0)
        self.assertFalse(check["compliant"])
        self.assertLess(check["margin_nm"], 0.0)

    def test_non_positive_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            check_deposition_allowance(40.0, 0.0)


class SurfaceAssessmentTests(unittest.TestCase):
    def test_compliant_surface_has_no_findings(self):
        result = assess_surface_deposition(compliant_surface())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(
            result["total_thickness_nm"],
            result["neutral_thickness_nm"] + result["charged_thickness_nm"],
            places=9,
        )

    def test_total_thickness_matches_the_hand_computed_value(self):
        result = assess_surface_deposition(compliant_surface())
        self.assertAlmostEqual(result["neutral_thickness_nm"], 44.30, places=1)
        self.assertAlmostEqual(result["charged_thickness_nm"], 13.78, places=1)

    def test_exceeding_the_agreed_limit_is_flagged(self):
        result = assess_surface_deposition(
            compliant_surface(allowable_thickness_nm=25.0)
        )
        self.assertIn("plume-deposition-exceeds-agreed-limit", result["findings"])
        self.assertFalse(result["compliant"])

    def test_missing_agreed_limit_is_flagged(self):
        result = assess_surface_deposition(
            compliant_surface(allowable_thickness_nm=None)
        )
        self.assertIn("agreed-deposition-limit-not-recorded", result["findings"])
        self.assertIsNone(result["allowance_check"])

    def test_missing_backflow_fraction_is_flagged(self):
        surface = compliant_surface(
            sources=[neutral_source(backflow_fraction=None), charged_source()]
        )
        result = assess_surface_deposition(surface)
        self.assertIn("backflow-fraction-not-recorded", result["findings"])
        self.assertAlmostEqual(result["neutral_thickness_nm"], 0.0, places=12)

    def test_missing_sticking_coefficient_is_an_observation_only(self):
        surface = compliant_surface(
            allowable_thickness_nm=200.0,
            sources=[neutral_source(sticking_coefficient=None), charged_source()],
        )
        result = assess_surface_deposition(surface)
        self.assertTrue(result["compliant"])
        self.assertIn(
            "sticking-coefficient-defaulted-to-unity", result["observations"]
        )

    def test_shadowed_source_deposits_nothing(self):
        surface = compliant_surface(
            sources=[neutral_source(line_of_sight=False), charged_source()]
        )
        result = assess_surface_deposition(surface)
        self.assertAlmostEqual(result["neutral_thickness_nm"], 0.0, places=12)
        self.assertTrue(result["compliant"])

    def test_absent_charged_source_is_flagged(self):
        surface = compliant_surface(sources=[neutral_source()])
        result = assess_surface_deposition(surface)
        self.assertIn("charged-efflux-source-not-declared", result["findings"])

    def test_absent_neutral_source_is_flagged(self):
        surface = compliant_surface(sources=[charged_source()])
        result = assess_surface_deposition(surface)
        self.assertIn("neutral-efflux-source-not-declared", result["findings"])

    def test_source_missing_a_required_key_is_rejected(self):
        source = neutral_source()
        del source["film_density_kg_m3"]
        with self.assertRaises(ValueError):
            assess_surface_deposition(compliant_surface(sources=[source]))

    def test_empty_source_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_deposition(compliant_surface(sources=[]))

    def test_sources_not_a_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_deposition(compliant_surface(sources=neutral_source()))

    def test_non_mapping_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_deposition(["OSR-PANEL-A"])

    def test_blank_surface_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_deposition(compliant_surface(id="   "))


class CampaignTests(unittest.TestCase):
    def test_all_compliant_campaign_is_compliant(self):
        summary = assess_deposition_campaign(
            [compliant_surface(), compliant_surface(id="STAR-TRACKER-BAFFLE")]
        )
        self.assertTrue(summary["compliant"])
        self.assertEqual(summary["compliant_count"], 2)

    def test_worst_surface_is_named(self):
        summary = assess_deposition_campaign(
            [
                compliant_surface(),
                compliant_surface(
                    id="OSR-PANEL-B",
                    sources=[neutral_source(distance_m=1.0), charged_source()],
                ),
            ]
        )
        self.assertEqual(summary["worst_surface_id"], "OSR-PANEL-B")
        self.assertIn("OSR-PANEL-B", summary["noncompliant_ids"])

    def test_empty_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_deposition_campaign([])

    def test_non_list_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_deposition_campaign(compliant_surface())

    def test_duplicate_surface_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_deposition_campaign([compliant_surface(), compliant_surface()])


if __name__ == "__main__":
    unittest.main()
