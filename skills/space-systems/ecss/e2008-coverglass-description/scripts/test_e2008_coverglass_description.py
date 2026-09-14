#!/usr/bin/env python3
"""Contract test for the coverglass description check (offline)."""

import copy
import unittest

from e2008_coverglass_description_logic import (
    COATINGS,
    DEFAULT_DESCRIPTION_POLICY,
    DESCRIPTION_COMPLETE,
    DESCRIPTION_INCOMPLETE,
    DESCRIPTION_NON_PHYSICAL,
    DESCRIPTION_QUERIED,
    REQUIRED_FIELDS,
    SUBSTRATE_LIBRARY,
    SUBSTRATE_NOT_ADMISSIBLE,
    areal_mass_kg_m2,
    describe_coverglass,
    normalise_coatings,
    piece_mass_kg,
    shielding_areal_density_g_cm2,
    single_surface_reflectance,
    substrate_properties,
    transmittance_admissibility,
    uncoated_transmittance_ceiling,
    validate_description_policy,
)

SILICA_CASE = {
    "substrate": "fused-silica",
    "thickness_m": 100.0e-6,
    "average_transmittance": 0.92,
    "coatings": [],
    "length_m": 40.0e-3,
    "width_m": 60.0e-3,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_description_policy(DEFAULT_DESCRIPTION_POLICY),
            DEFAULT_DESCRIPTION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_description_policy(0.92)

    def test_inverted_thickness_band_rejected(self):
        broken = copy.deepcopy(DEFAULT_DESCRIPTION_POLICY)
        broken["max_thickness_m"] = 10.0e-6
        with self.assertRaises(ValueError):
            validate_description_policy(broken)

    def test_transmittance_floor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_DESCRIPTION_POLICY)
        broken["min_average_transmittance"] = 1.4
        with self.assertRaises(ValueError):
            validate_description_policy(broken)


class SubstrateTests(unittest.TestCase):
    def test_fused_silica_is_admissible(self):
        self.assertTrue(substrate_properties("fused-silica")["admissible"])

    def test_polymer_film_is_not_admissible(self):
        self.assertFalse(substrate_properties("polymer-film")["admissible"])

    def test_every_library_entry_carries_an_index_and_a_density(self):
        for name in SUBSTRATE_LIBRARY:
            properties = substrate_properties(name)
            self.assertGreater(properties["refractive_index"], 1.0)
            self.assertGreater(properties["density_kg_m3"], 0.0)

    def test_lookup_returns_a_copy(self):
        properties = substrate_properties("fused-silica")
        properties["density_kg_m3"] = 1.0
        self.assertNotEqual(SUBSTRATE_LIBRARY["fused-silica"]["density_kg_m3"], 1.0)

    def test_unknown_substrate_rejected(self):
        with self.assertRaises(ValueError):
            substrate_properties("perspex")


class CoatingStackTests(unittest.TestCase):
    def test_stack_is_deduplicated_and_ordered(self):
        self.assertEqual(
            normalise_coatings(
                ["uv-reflective-coating", "antireflective-coating", "uv-reflective-coating"]
            ),
            ("antireflective-coating", "uv-reflective-coating"),
        )

    def test_empty_stack_is_allowed(self):
        self.assertEqual(normalise_coatings(()), ())

    def test_unknown_coating_rejected(self):
        with self.assertRaises(ValueError):
            normalise_coatings(["anti-scratch-wax"])

    def test_bare_string_stack_rejected(self):
        with self.assertRaises(ValueError):
            normalise_coatings("antireflective-coating")


class OpticsTests(unittest.TestCase):
    def test_index_one_reflects_nothing(self):
        self.assertAlmostEqual(single_surface_reflectance(1.0), 0.0, places=12)

    def test_fused_silica_reflects_about_three_and_a_half_percent(self):
        self.assertAlmostEqual(single_surface_reflectance(1.4585), 0.034781, places=6)

    def test_index_one_passes_everything(self):
        self.assertAlmostEqual(uncoated_transmittance_ceiling(1.0), 1.0, places=12)

    def test_fused_silica_ceiling_is_about_ninety_three_percent(self):
        self.assertAlmostEqual(
            uncoated_transmittance_ceiling(1.4585), 0.932777, places=6
        )

    def test_a_higher_index_lowers_the_ceiling(self):
        silica = uncoated_transmittance_ceiling(1.4585)
        sapphire = uncoated_transmittance_ceiling(1.7682)
        self.assertLess(sapphire, silica)

    def test_ceiling_never_exceeds_unity(self):
        for name in SUBSTRATE_LIBRARY:
            index = SUBSTRATE_LIBRARY[name]["refractive_index"]
            self.assertLessEqual(uncoated_transmittance_ceiling(index), 1.0)

    def test_index_below_one_rejected(self):
        with self.assertRaises(ValueError):
            uncoated_transmittance_ceiling(0.8)

    def test_non_numeric_index_rejected(self):
        with self.assertRaises(ValueError):
            single_surface_reflectance("1.46")


class MassTests(unittest.TestCase):
    def test_areal_mass_is_density_times_thickness(self):
        self.assertAlmostEqual(areal_mass_kg_m2(2200.0, 100.0e-6), 0.22, places=12)

    def test_shielding_density_converts_to_grams_per_square_centimetre(self):
        self.assertAlmostEqual(
            shielding_areal_density_g_cm2(0.22), 0.022, places=12
        )

    def test_a_thicker_glass_shields_more(self):
        thin = areal_mass_kg_m2(2200.0, 100.0e-6)
        thick = areal_mass_kg_m2(2200.0, 300.0e-6)
        self.assertGreater(thick, thin)

    def test_piece_mass_uses_the_declared_footprint(self):
        self.assertAlmostEqual(
            piece_mass_kg(0.22, 40.0e-3, 60.0e-3), 0.22 * 0.0024, places=12
        )

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            areal_mass_kg_m2(2200.0, 0.0)

    def test_negative_footprint_rejected(self):
        with self.assertRaises(ValueError):
            piece_mass_kg(0.22, -40.0e-3, 60.0e-3)


class TransmittanceTests(unittest.TestCase):
    def test_a_modest_uncoated_claim_is_physical(self):
        result = transmittance_admissibility("fused-silica", 0.92)
        self.assertTrue(result["physical"])
        self.assertEqual(result["limit_kind"], "uncoated-fresnel-ceiling")
        self.assertEqual(result["findings"], [])

    def test_an_uncoated_claim_above_the_fresnel_ceiling_is_caught(self):
        result = transmittance_admissibility("fused-silica", 0.97)
        self.assertFalse(result["physical"])
        self.assertTrue(any("uncoated" in f for f in result["findings"]))

    def test_an_antireflective_coating_lifts_the_limit(self):
        result = transmittance_admissibility(
            "fused-silica", 0.97, ["antireflective-coating"]
        )
        self.assertTrue(result["physical"])
        self.assertEqual(result["limit_kind"], "coated-ceiling")

    def test_a_claim_exactly_on_the_fresnel_ceiling_is_physical(self):
        ceiling = uncoated_transmittance_ceiling(
            SUBSTRATE_LIBRARY["fused-silica"]["refractive_index"]
        )
        result = transmittance_admissibility("fused-silica", ceiling)
        self.assertTrue(result["physical"])
        self.assertAlmostEqual(result["applied_limit"], ceiling, places=9)

    def test_even_a_coated_claim_has_a_ceiling(self):
        result = transmittance_admissibility(
            "fused-silica", 0.999, ["antireflective-coating"]
        )
        self.assertFalse(result["physical"])

    def test_a_claim_below_the_policy_floor_is_flagged(self):
        result = transmittance_admissibility("fused-silica", 0.85)
        self.assertTrue(result["physical"])
        self.assertTrue(result["below_floor"])

    def test_a_claim_exactly_on_the_policy_floor_is_not_flagged(self):
        floor = DEFAULT_DESCRIPTION_POLICY["min_average_transmittance"]
        result = transmittance_admissibility("fused-silica", floor)
        self.assertFalse(result["below_floor"])

    def test_sapphire_tolerates_less_than_silica(self):
        silica = transmittance_admissibility("fused-silica", 0.925)
        sapphire = transmittance_admissibility("sapphire", 0.925)
        self.assertTrue(silica["physical"])
        self.assertFalse(sapphire["physical"])

    def test_zero_transmittance_rejected(self):
        with self.assertRaises(ValueError):
            transmittance_admissibility("fused-silica", 0.0)

    def test_transmittance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            transmittance_admissibility("fused-silica", 1.4)


class DescriptionTests(unittest.TestCase):
    def test_a_sound_description_is_complete(self):
        result = describe_coverglass(SILICA_CASE)
        self.assertEqual(result["verdict"], DESCRIPTION_COMPLETE)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["areal_mass_kg_m2"], 0.22, places=12)
        self.assertAlmostEqual(
            result["shielding_areal_density_g_cm2"], 0.022, places=12
        )

    def test_piece_mass_is_reported_when_the_footprint_is_given(self):
        result = describe_coverglass(SILICA_CASE)
        self.assertAlmostEqual(result["piece_mass_kg"], 0.22 * 0.0024, places=12)

    def test_piece_mass_is_absent_without_a_footprint(self):
        case = _case(SILICA_CASE)
        del case["length_m"]
        self.assertIsNone(describe_coverglass(case)["piece_mass_kg"])

    def test_every_required_field_is_enforced(self):
        for field in REQUIRED_FIELDS:
            case = _case(SILICA_CASE)
            del case[field]
            result = describe_coverglass(case)
            self.assertEqual(result["verdict"], DESCRIPTION_INCOMPLETE, field)
            self.assertIn(field, result["missing_fields"])

    def test_a_polymer_substrate_is_not_admissible(self):
        result = describe_coverglass(_case(SILICA_CASE, substrate="polymer-film"))
        self.assertEqual(result["verdict"], SUBSTRATE_NOT_ADMISSIBLE)
        self.assertIsNone(result["areal_mass_kg_m2"])

    def test_an_impossible_optical_claim_is_non_physical(self):
        result = describe_coverglass(
            _case(SILICA_CASE, average_transmittance=0.97)
        )
        self.assertEqual(result["verdict"], DESCRIPTION_NON_PHYSICAL)

    def test_the_same_claim_passes_once_the_coating_is_declared(self):
        result = describe_coverglass(
            _case(
                SILICA_CASE,
                average_transmittance=0.97,
                coatings=["antireflective-coating"],
            )
        )
        self.assertEqual(result["verdict"], DESCRIPTION_COMPLETE)

    def test_a_thickness_outside_the_band_is_queried_not_rejected(self):
        result = describe_coverglass(_case(SILICA_CASE, thickness_m=20.0e-6))
        self.assertEqual(result["verdict"], DESCRIPTION_QUERIED)
        self.assertTrue(any("below" in f for f in result["findings"]))

    def test_a_thick_glass_is_queried_too(self):
        result = describe_coverglass(_case(SILICA_CASE, thickness_m=800.0e-6))
        self.assertEqual(result["verdict"], DESCRIPTION_QUERIED)

    def test_a_thickness_exactly_on_the_band_edge_is_complete(self):
        low = DEFAULT_DESCRIPTION_POLICY["min_thickness_m"]
        high = DEFAULT_DESCRIPTION_POLICY["max_thickness_m"]
        self.assertEqual(
            describe_coverglass(_case(SILICA_CASE, thickness_m=low))["verdict"],
            DESCRIPTION_COMPLETE,
        )
        self.assertEqual(
            describe_coverglass(_case(SILICA_CASE, thickness_m=high))["verdict"],
            DESCRIPTION_COMPLETE,
        )

    def test_a_declared_density_overrides_the_library(self):
        result = describe_coverglass(_case(SILICA_CASE, density_kg_m3=2500.0))
        self.assertAlmostEqual(result["areal_mass_kg_m2"], 0.25, places=12)

    def test_the_coating_stack_is_reported_normalised(self):
        result = describe_coverglass(
            _case(
                SILICA_CASE,
                coatings=["conductive-coating", "antireflective-coating"],
                average_transmittance=0.96,
            )
        )
        self.assertEqual(
            result["coatings"], ("antireflective-coating", "conductive-coating")
        )

    def test_every_admissible_substrate_can_be_described(self):
        for name in SUBSTRATE_LIBRARY:
            if not SUBSTRATE_LIBRARY[name]["admissible"]:
                continue
            ceiling = uncoated_transmittance_ceiling(
                SUBSTRATE_LIBRARY[name]["refractive_index"]
            )
            result = describe_coverglass(
                _case(
                    SILICA_CASE,
                    substrate=name,
                    average_transmittance=ceiling * 0.99,
                )
            )
            self.assertIn(
                result["verdict"], (DESCRIPTION_COMPLETE, DESCRIPTION_QUERIED), name
            )

    def test_every_coating_is_accepted_in_a_description(self):
        for coating in COATINGS:
            result = describe_coverglass(_case(SILICA_CASE, coatings=[coating]))
            self.assertNotEqual(result["verdict"], DESCRIPTION_INCOMPLETE)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            describe_coverglass("fused-silica")

    def test_negative_thickness_rejected(self):
        with self.assertRaises(ValueError):
            describe_coverglass(_case(SILICA_CASE, thickness_m=-100.0e-6))

    def test_unknown_substrate_in_a_case_rejected(self):
        with self.assertRaises(ValueError):
            describe_coverglass(_case(SILICA_CASE, substrate="cling-film"))


if __name__ == "__main__":
    unittest.main()
