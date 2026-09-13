#!/usr/bin/env python3
"""Contract test for the clause 6.5.1 electron-seeding general provisions."""

import unittest

from e2001_electron_seeding_general_provisions_logic import (
    ACCESS_APERTURE,
    ACCESS_BLOCKED,
    ACCESS_DIRECT,
    MAX_SHIELD_ATTENUATION_DB,
    MIN_APERTURE_MM2,
    ROUTE_ARTICLE,
    ROUTE_SUBSTITUTE,
    assess_seeding_provisions,
    assess_substitute_seedability,
    categorize_seed_access,
    evaluate_representativeness,
    relative_deviation,
    seeding_route,
    summarize_campaign,
)


def make_gap(**overrides):
    gap = {
        "line_of_sight": False,
        "aperture_area_mm2": 0.0,
        "shield_attenuation_db": 0.0,
        "gap_height_mm": 0.5,
        "drive_frequency_ghz": 12.0,
        "surface_roughness_um": 0.8,
        "base_material": "aluminium-6082",
        "surface_coating": "silver-plated",
        "gap_geometry": "waveguide-iris",
    }
    gap.update(overrides)
    return gap


def make_substitute(**overrides):
    gap_overrides = overrides.pop("gap", {})
    substitute = {
        "model_type": "breadboard",
        "seeding_effectiveness_verified": True,
        "gap": make_gap(line_of_sight=True, **gap_overrides),
    }
    substitute.update(overrides)
    return substitute


class SeedAccessCategoryTests(unittest.TestCase):
    def test_line_of_sight_gap_is_directly_seedable(self):
        self.assertEqual(categorize_seed_access(make_gap(line_of_sight=True)), ACCESS_DIRECT)

    def test_open_aperture_gap_is_seedable_through_the_aperture(self):
        gap = make_gap(aperture_area_mm2=4.0, shield_attenuation_db=6.0)
        self.assertEqual(categorize_seed_access(gap), ACCESS_APERTURE)

    def test_aperture_below_minimum_area_blocks_the_seed_path(self):
        gap = make_gap(aperture_area_mm2=0.4, shield_attenuation_db=2.0)
        self.assertEqual(categorize_seed_access(gap), ACCESS_BLOCKED)

    def test_excess_shield_attenuation_blocks_the_seed_path(self):
        gap = make_gap(aperture_area_mm2=9.0, shield_attenuation_db=31.0)
        self.assertEqual(categorize_seed_access(gap), ACCESS_BLOCKED)

    def test_fully_enclosed_gap_is_not_seedable(self):
        self.assertEqual(categorize_seed_access(make_gap()), ACCESS_BLOCKED)

    def test_aperture_area_summed_a_hair_under_the_minimum_still_passes(self):
        summed = 3 * 0.3 + 0.1
        self.assertLess(summed, MIN_APERTURE_MM2)
        gap = make_gap(aperture_area_mm2=summed, shield_attenuation_db=3.0)
        self.assertEqual(categorize_seed_access(gap), ACCESS_APERTURE)

    def test_attenuation_exactly_at_the_ceiling_is_accepted(self):
        gap = make_gap(aperture_area_mm2=2.0, shield_attenuation_db=MAX_SHIELD_ATTENUATION_DB)
        self.assertEqual(categorize_seed_access(gap), ACCESS_APERTURE)

    def test_negative_aperture_area_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_access(make_gap(aperture_area_mm2=-1.0))

    def test_negative_attenuation_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_access(make_gap(shield_attenuation_db=-0.5))

    def test_missing_line_of_sight_field_is_rejected(self):
        gap = make_gap()
        del gap["line_of_sight"]
        with self.assertRaises(ValueError):
            categorize_seed_access(gap)

    def test_non_boolean_line_of_sight_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_access(make_gap(line_of_sight="yes"))

    def test_gap_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_access(["line_of_sight"])

    def test_non_finite_aperture_area_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_access(make_gap(aperture_area_mm2=float("nan")))

    def test_boolean_aperture_area_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_access(make_gap(aperture_area_mm2=True))


class SeedingRouteTests(unittest.TestCase):
    def test_direct_access_seeds_the_flight_article(self):
        self.assertEqual(seeding_route(ACCESS_DIRECT), ROUTE_ARTICLE)

    def test_aperture_access_seeds_the_flight_article(self):
        self.assertEqual(seeding_route(ACCESS_APERTURE), ROUTE_ARTICLE)

    def test_blocked_access_forces_a_dedicated_substitute(self):
        self.assertEqual(seeding_route(ACCESS_BLOCKED), ROUTE_SUBSTITUTE)

    def test_route_lookup_is_case_insensitive(self):
        self.assertEqual(seeding_route("Direct-Seedable"), ROUTE_ARTICLE)

    def test_unknown_access_category_is_rejected(self):
        with self.assertRaises(ValueError):
            seeding_route("partly-seedable")

    def test_empty_access_category_is_rejected(self):
        with self.assertRaises(ValueError):
            seeding_route("   ")


class RelativeDeviationTests(unittest.TestCase):
    def test_deviation_above_the_reference(self):
        self.assertAlmostEqual(relative_deviation(0.5, 0.55), 0.1, places=12)

    def test_deviation_below_the_reference(self):
        self.assertAlmostEqual(relative_deviation(10.0, 9.0), 0.1, places=12)

    def test_identical_values_have_no_deviation(self):
        self.assertAlmostEqual(relative_deviation(3.2, 3.2), 0.0, places=12)

    def test_zero_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation(0.0, 1.0)

    def test_negative_candidate_is_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation(1.0, -1.0)

    def test_boolean_input_is_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation(True, 1.0)

    def test_infinite_input_is_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation(1.0, float("inf"))


class RepresentativenessTests(unittest.TestCase):
    def test_identical_substitute_is_representative(self):
        report = evaluate_representativeness(make_gap(), make_gap())
        self.assertTrue(report["representative"])
        self.assertEqual(report["mismatches"], [])

    def test_every_attribute_is_scored(self):
        report = evaluate_representativeness(make_gap(), make_gap())
        self.assertEqual(len(report["attributes"]), 6)

    def test_gap_height_beyond_tolerance_is_a_mismatch(self):
        report = evaluate_representativeness(make_gap(), make_gap(gap_height_mm=0.6))
        self.assertIn("gap_height_mm", report["mismatches"])
        self.assertFalse(report["representative"])

    def test_gap_height_at_the_tolerance_edge_absorbs_representation_error(self):
        raw = (0.51 - 0.5) / 0.5
        self.assertGreater(raw, 0.02)
        report = evaluate_representativeness(make_gap(), make_gap(gap_height_mm=0.51))
        self.assertTrue(report["representative"])

    def test_drive_frequency_mismatch_is_reported(self):
        report = evaluate_representativeness(make_gap(), make_gap(drive_frequency_ghz=18.0))
        self.assertIn("drive_frequency_ghz", report["mismatches"])

    def test_surface_roughness_within_its_wider_tolerance_passes(self):
        report = evaluate_representativeness(make_gap(), make_gap(surface_roughness_um=1.0))
        self.assertTrue(report["representative"])

    def test_base_material_mismatch_is_reported(self):
        report = evaluate_representativeness(make_gap(), make_gap(base_material="copper-c101"))
        self.assertIn("base_material", report["mismatches"])

    def test_surface_coating_mismatch_is_reported(self):
        report = evaluate_representativeness(make_gap(), make_gap(surface_coating="bare"))
        self.assertIn("surface_coating", report["mismatches"])

    def test_gap_geometry_mismatch_is_reported(self):
        report = evaluate_representativeness(make_gap(), make_gap(gap_geometry="coaxial-gap"))
        self.assertIn("gap_geometry", report["mismatches"])

    def test_deviation_value_is_recorded_for_numeric_attributes(self):
        report = evaluate_representativeness(make_gap(), make_gap(drive_frequency_ghz=12.6))
        record = [r for r in report["attributes"] if r["attribute"] == "drive_frequency_ghz"][0]
        self.assertAlmostEqual(record["deviation"], 0.05, places=12)

    def test_unrecognised_gap_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_representativeness(make_gap(gap_geometry="helical-slot"), make_gap())

    def test_looser_tolerance_override_accepts_a_wider_gap(self):
        report = evaluate_representativeness(
            make_gap(), make_gap(gap_height_mm=0.55), {"gap_height_mm": 0.2}
        )
        self.assertTrue(report["representative"])

    def test_tolerance_override_for_unknown_attribute_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_representativeness(make_gap(), make_gap(), {"gap_width_mm": 0.1})

    def test_non_positive_tolerance_override_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_representativeness(make_gap(), make_gap(), {"gap_height_mm": 0.0})

    def test_missing_numeric_attribute_is_rejected(self):
        gap = make_gap()
        del gap["surface_roughness_um"]
        with self.assertRaises(ValueError):
            evaluate_representativeness(make_gap(), gap)

    def test_zero_gap_height_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_representativeness(make_gap(gap_height_mm=0.0), make_gap())

    def test_empty_material_string_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_representativeness(make_gap(), make_gap(base_material="  "))


class SubstituteSeedabilityTests(unittest.TestCase):
    def test_open_and_verified_substitute_raises_no_finding(self):
        report = assess_substitute_seedability(make_substitute())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["access"], ACCESS_DIRECT)

    def test_enclosed_substitute_is_flagged(self):
        substitute = make_substitute()
        substitute["gap"] = make_gap()
        report = assess_substitute_seedability(substitute)
        self.assertIn("substitute-not-seedable", report["findings"])

    def test_unverified_seeding_effectiveness_is_flagged(self):
        report = assess_substitute_seedability(
            make_substitute(seeding_effectiveness_verified=False)
        )
        self.assertIn("substitute-seeding-effectiveness-unverified", report["findings"])

    def test_development_model_is_an_accepted_substitute_type(self):
        report = assess_substitute_seedability(make_substitute(model_type="development-model"))
        self.assertEqual(report["model_type"], "development-model")

    def test_unknown_substitute_model_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_substitute_seedability(make_substitute(model_type="flight-spare"))

    def test_substitute_without_a_gap_is_rejected(self):
        substitute = make_substitute()
        del substitute["gap"]
        with self.assertRaises(ValueError):
            assess_substitute_seedability(substitute)

    def test_non_boolean_effectiveness_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_substitute_seedability(make_substitute(seeding_effectiveness_verified="ok"))


class ProvisionAssessmentTests(unittest.TestCase):
    def test_reachable_article_gap_is_seeded_directly(self):
        result = assess_seeding_provisions(
            {"gap_id": "gap-a", "article_gap": make_gap(line_of_sight=True)}
        )
        self.assertEqual(result["route"], ROUTE_ARTICLE)
        self.assertTrue(result["compliant"])

    def test_substitute_offered_for_a_reachable_gap_is_flagged(self):
        result = assess_seeding_provisions(
            {
                "gap_id": "gap-a",
                "article_gap": make_gap(line_of_sight=True),
                "substitute": make_substitute(),
            }
        )
        self.assertIn("substitute-substitution-unjustified", result["findings"])
        self.assertFalse(result["compliant"])

    def test_enclosed_gap_with_a_representative_substitute_is_compliant(self):
        result = assess_seeding_provisions(
            {"gap_id": "gap-b", "article_gap": make_gap(), "substitute": make_substitute()}
        )
        self.assertEqual(result["route"], ROUTE_SUBSTITUTE)
        self.assertTrue(result["compliant"])
        self.assertTrue(result["representativeness"]["representative"])

    def test_enclosed_gap_without_a_substitute_is_flagged(self):
        result = assess_seeding_provisions({"gap_id": "gap-b", "article_gap": make_gap()})
        self.assertEqual(result["findings"], ["no-seeded-path-to-critical-gap"])

    def test_non_representative_substitute_names_the_failing_attribute(self):
        result = assess_seeding_provisions(
            {
                "gap_id": "gap-c",
                "article_gap": make_gap(),
                "substitute": make_substitute(gap={"base_material": "copper-c101"}),
            }
        )
        self.assertIn("substitute-not-representative:base_material", result["findings"])

    def test_enclosed_substitute_and_mismatch_are_reported_together(self):
        substitute = make_substitute()
        substitute["gap"] = make_gap(gap_height_mm=0.9)
        result = assess_seeding_provisions(
            {"gap_id": "gap-d", "article_gap": make_gap(), "substitute": substitute}
        )
        self.assertIn("substitute-not-seedable", result["findings"])
        self.assertIn("substitute-not-representative:gap_height_mm", result["findings"])

    def test_missing_gap_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_seeding_provisions({"article_gap": make_gap()})

    def test_missing_article_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_seeding_provisions({"gap_id": "gap-a"})


class CampaignSummaryTests(unittest.TestCase):
    def test_campaign_counts_substitute_routes(self):
        summary = summarize_campaign(
            [
                {"gap_id": "gap-a", "article_gap": make_gap(line_of_sight=True)},
                {"gap_id": "gap-b", "article_gap": make_gap(), "substitute": make_substitute()},
            ]
        )
        self.assertEqual(summary["gap_count"], 2)
        self.assertEqual(summary["substitute_count"], 1)
        self.assertTrue(summary["compliant"])

    def test_campaign_collects_findings_with_their_gap_identifier(self):
        summary = summarize_campaign(
            [{"gap_id": "gap-b", "article_gap": make_gap()}]
        )
        self.assertEqual(summary["open_findings"], ["gap-b:no-seeded-path-to-critical-gap"])
        self.assertFalse(summary["compliant"])

    def test_empty_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_campaign([])

    def test_campaign_that_is_not_a_list_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_campaign({"gap_id": "gap-a"})

    def test_duplicate_gap_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_campaign(
                [
                    {"gap_id": "gap-a", "article_gap": make_gap(line_of_sight=True)},
                    {"gap_id": "gap-a", "article_gap": make_gap(line_of_sight=True)},
                ]
            )


if __name__ == "__main__":
    unittest.main()
