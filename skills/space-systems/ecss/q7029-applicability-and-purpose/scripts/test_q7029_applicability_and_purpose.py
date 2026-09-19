"""Contract tests for the offgassing applicability and purpose logic."""

import unittest

from q7029_applicability_and_purpose_logic import (
    ASSEMBLED_ARTICLE_MATERIAL_COUNT,
    MAX_REPORT_AGE_YEARS,
    MIN_LOADING_G_PER_M3,
    REQUIREMENT_AREAS,
    assess_offgassing_applicability,
    cabin_loading_g_per_m3,
    exposure_disposition,
    loading_is_negligible,
    report_reuse_findings,
    requirement_areas,
    test_route,
)


def base_item(**overrides):
    """A bonded stowage insert inside the crew compartment, never tested."""
    item = {
        "location": "crew-compartment",
        "containment": "none",
        "exposed_mass_g": 400.0,
        "free_volume_m3": 40.0,
        "materials": ("polyurethane-foam", "polyester-fabric", "epoxy-adhesive"),
        "processes": ("adhesive-bonding",),
        "database_entry": False,
        "prior_report": None,
    }
    item.update(overrides)
    return item


class ExposureTests(unittest.TestCase):
    def test_an_item_in_the_crew_compartment_is_exposed(self):
        self.assertTrue(exposure_disposition("crew-compartment")["exposed"])

    def test_an_item_outside_the_pressurised_volume_is_not_exposed(self):
        disposition = exposure_disposition("external-surface")
        self.assertFalse(disposition["exposed"])
        self.assertIn("vacuum", disposition["reason"])

    def test_a_hermetic_seal_removes_the_exposure(self):
        self.assertFalse(
            exposure_disposition("crew-compartment", "hermetically-sealed")["exposed"]
        )

    def test_a_closed_box_does_not_remove_the_exposure(self):
        self.assertTrue(exposure_disposition("crew-compartment", "closed-box")["exposed"])

    def test_a_vented_enclosure_does_not_remove_the_exposure(self):
        self.assertTrue(
            exposure_disposition("internal-stowage", "vented-enclosure")["exposed"]
        )

    def test_location_and_containment_ignore_case(self):
        self.assertTrue(exposure_disposition("  Crew-Compartment ", " None ")["exposed"])

    def test_an_unknown_location_rejected(self):
        with self.assertRaises(ValueError):
            exposure_disposition("service-module-radiator")

    def test_an_unknown_containment_rejected(self):
        with self.assertRaises(ValueError):
            exposure_disposition("crew-compartment", "shrink-wrapped")


class LoadingTests(unittest.TestCase):
    def test_loading_is_mass_over_free_volume(self):
        self.assertAlmostEqual(cabin_loading_g_per_m3(400.0, 40.0), 10.0, places=9)

    def test_a_larger_cabin_dilutes_the_same_mass(self):
        self.assertLess(
            cabin_loading_g_per_m3(400.0, 100.0), cabin_loading_g_per_m3(400.0, 40.0)
        )

    def test_zero_free_volume_rejected(self):
        with self.assertRaises(ValueError):
            cabin_loading_g_per_m3(400.0, 0.0)

    def test_zero_exposed_mass_rejected(self):
        with self.assertRaises(ValueError):
            cabin_loading_g_per_m3(0.0, 40.0)

    def test_a_small_loading_is_negligible(self):
        self.assertTrue(loading_is_negligible(MIN_LOADING_G_PER_M3 / 10.0))

    def test_a_loading_exactly_on_the_threshold_is_not_negligible(self):
        self.assertFalse(loading_is_negligible(MIN_LOADING_G_PER_M3))

    def test_a_negative_loading_rejected(self):
        with self.assertRaises(ValueError):
            loading_is_negligible(-1.0)


class RouteTests(unittest.TestCase):
    def test_a_single_untreated_material_goes_to_material_level(self):
        route = test_route({"materials": ("polyimide-film",)})
        self.assertEqual(route["route"], "material-level")

    def test_several_materials_make_it_an_assembled_article(self):
        materials = tuple("m%d" % i for i in range(ASSEMBLED_ARTICLE_MATERIAL_COUNT))
        self.assertEqual(test_route({"materials": materials})["route"], "assembled-article")

    def test_one_fewer_material_stays_at_material_level(self):
        materials = tuple("m%d" % i for i in range(ASSEMBLED_ARTICLE_MATERIAL_COUNT - 1))
        self.assertEqual(test_route({"materials": materials})["route"], "material-level")

    def test_a_build_process_alone_forces_the_assembled_article(self):
        route = test_route({"materials": ("aluminium",), "processes": ("painting",)})
        self.assertEqual(route["route"], "assembled-article")
        self.assertTrue(any("offgas in their own right" in r for r in route["reasons"]))

    def test_an_item_with_nothing_declared_is_material_level(self):
        self.assertEqual(test_route({})["route"], "material-level")

    def test_an_unknown_build_process_rejected(self):
        with self.assertRaises(ValueError):
            test_route({"materials": ("aluminium",), "processes": ("anodising",)})

    def test_a_bare_string_of_materials_rejected(self):
        with self.assertRaises(ValueError):
            test_route({"materials": "polyimide-film"})


class ReuseTests(unittest.TestCase):
    def test_no_prior_report_requires_a_determination(self):
        self.assertTrue(report_reuse_findings(None))

    def test_a_recent_unchanged_report_still_covers_the_item(self):
        self.assertEqual(report_reuse_findings({"age_years": 2.0}), [])

    def test_a_report_exactly_at_the_validity_age_still_covers_the_item(self):
        self.assertEqual(report_reuse_findings({"age_years": MAX_REPORT_AGE_YEARS}), [])

    def test_an_aged_report_no_longer_covers_the_item(self):
        findings = report_reuse_findings({"age_years": MAX_REPORT_AGE_YEARS + 2.0})
        self.assertTrue(any("past the" in f for f in findings))

    def test_a_process_change_ends_the_coverage(self):
        findings = report_reuse_findings(
            {"age_years": 1.0, "changes_since": ("process-change",)}
        )
        self.assertTrue(any("process-change" in f for f in findings))

    def test_an_unknown_change_rejected(self):
        with self.assertRaises(ValueError):
            report_reuse_findings({"age_years": 1.0, "changes_since": ("repainted",)})

    def test_a_report_without_an_age_rejected(self):
        with self.assertRaises(ValueError):
            report_reuse_findings({"changes_since": ()})

    def test_a_negative_report_age_rejected(self):
        with self.assertRaises(ValueError):
            report_reuse_findings({"age_years": -1.0})


class RequirementAreaTests(unittest.TestCase):
    def test_the_requirement_areas_run_in_test_order(self):
        areas = requirement_areas()
        self.assertEqual(areas[0], "specimen-preparation")
        self.assertEqual(areas[-1], "test-report")

    def test_every_requirement_area_is_distinct(self):
        self.assertEqual(len(set(REQUIREMENT_AREAS)), len(REQUIREMENT_AREAS))


class ApplicabilityTests(unittest.TestCase):
    def test_a_bonded_cabin_insert_is_within_scope(self):
        result = assess_offgassing_applicability(base_item())
        self.assertEqual(result["disposition"], "within-scope")
        self.assertTrue(result["determination_required"])

    def test_an_in_scope_item_takes_on_the_requirement_areas(self):
        result = assess_offgassing_applicability(base_item())
        self.assertEqual(result["requirement_areas"], REQUIREMENT_AREAS)

    def test_an_external_item_is_outside_scope_and_takes_no_areas(self):
        result = assess_offgassing_applicability(base_item(location="unpressurised-bay"))
        self.assertEqual(result["disposition"], "outside-scope")
        self.assertEqual(result["requirement_areas"], ())
        self.assertFalse(result["determination_required"])

    def test_a_sealed_item_in_the_cabin_is_outside_scope(self):
        result = assess_offgassing_applicability(
            base_item(containment="hermetically-sealed")
        )
        self.assertEqual(result["disposition"], "outside-scope")

    def test_a_bonded_article_is_tested_as_an_article(self):
        self.assertEqual(assess_offgassing_applicability(base_item())["route"], "assembled-article")

    def test_a_single_bulk_material_is_tested_at_material_level(self):
        result = assess_offgassing_applicability(
            base_item(materials=("polyimide-film",), processes=())
        )
        self.assertEqual(result["route"], "material-level")

    def test_a_negligible_loading_with_a_database_entry_leans_on_the_entry(self):
        result = assess_offgassing_applicability(
            base_item(exposed_mass_g=4.0, free_volume_m3=40.0, database_entry=True)
        )
        self.assertEqual(result["disposition"], "covered-by-database")
        self.assertFalse(result["determination_required"])

    def test_a_negligible_loading_without_a_database_entry_still_needs_a_test(self):
        result = assess_offgassing_applicability(
            base_item(exposed_mass_g=4.0, free_volume_m3=40.0, database_entry=False)
        )
        self.assertEqual(result["disposition"], "within-scope")
        self.assertTrue(any("cannot be relied on" in n for n in result["notes"]))

    def test_a_valid_prior_report_covers_the_item(self):
        result = assess_offgassing_applicability(base_item(prior_report={"age_years": 1.0}))
        self.assertEqual(result["disposition"], "covered-by-prior-report")
        self.assertFalse(result["determination_required"])

    def test_a_process_change_since_the_report_puts_the_item_back_in_scope(self):
        result = assess_offgassing_applicability(
            base_item(prior_report={"age_years": 1.0, "changes_since": ("process-change",)})
        )
        self.assertEqual(result["disposition"], "within-scope")
        self.assertTrue(result["reuse_findings"])

    def test_the_loading_is_reported_whatever_the_disposition(self):
        result = assess_offgassing_applicability(base_item())
        self.assertAlmostEqual(result["loading_g_per_m3"], 10.0, places=9)

    def test_missing_required_item_key_rejected(self):
        item = base_item()
        del item["free_volume_m3"]
        with self.assertRaises(ValueError):
            assess_offgassing_applicability(item)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_offgassing_applicability("crew-compartment")


if __name__ == "__main__":
    unittest.main()
