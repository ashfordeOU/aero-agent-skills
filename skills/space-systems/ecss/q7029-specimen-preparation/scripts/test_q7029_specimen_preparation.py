"""Contract tests for the offgassing test-item preparation logic."""

import unittest

from q7029_specimen_preparation_logic import (
    ASSEMBLED_ARTICLE_REPLICATES,
    MATERIAL_LEVEL_REPLICATES,
    MAX_CHAMBER_FILL_FRACTION,
    MAX_DAYS_SINCE_CURE,
    MIN_CONSERVATISM_FACTOR,
    MIN_SPECIMEN_MASS_G,
    TEST_ROUTES,
    chamber_fill_fraction,
    chamber_loading_g_per_m3,
    cure_findings,
    fill_findings,
    loading_findings,
    plan_offgassing_test_item,
    preparation_findings,
    replicate_count,
    required_specimen_mass_g,
)

GOOD_CURE = {"required_hours": 24.0, "achieved_hours": 24.0, "days_since_cure": 14.0}


def base_request(**overrides):
    """A bonded insert at 10 g/m3 cabin loading, tested in a 2 m3 chamber."""
    request = {
        "route": "assembled-article",
        "cabin_loading_g_per_m3": 10.0,
        "chamber_volume_m3": 2.0,
        "conservatism": 1.0,
        "available_mass_g": 20.0,
        "item_volume_m3": 0.2,
        "preparations": ("packaging-removed", "gloved-handling"),
        "cure": dict(GOOD_CURE),
    }
    request.update(overrides)
    return request


class SizingTests(unittest.TestCase):
    def test_required_mass_reproduces_the_cabin_loading(self):
        self.assertAlmostEqual(required_specimen_mass_g(10.0, 2.0), 20.0, places=9)

    def test_conservatism_scales_the_required_mass(self):
        self.assertAlmostEqual(required_specimen_mass_g(10.0, 2.0, 1.5), 30.0, places=9)

    def test_a_conservatism_of_exactly_one_is_accepted(self):
        self.assertAlmostEqual(
            required_specimen_mass_g(10.0, 2.0, MIN_CONSERVATISM_FACTOR), 20.0, places=9
        )

    def test_a_conservatism_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            required_specimen_mass_g(10.0, 2.0, 0.5)

    def test_zero_chamber_volume_rejected(self):
        with self.assertRaises(ValueError):
            required_specimen_mass_g(10.0, 0.0)

    def test_non_numeric_cabin_loading_rejected(self):
        with self.assertRaises(ValueError):
            required_specimen_mass_g("10", 2.0)

    def test_chamber_loading_is_mass_over_chamber_volume(self):
        self.assertAlmostEqual(chamber_loading_g_per_m3(20.0, 2.0), 10.0, places=9)


class LoadingTests(unittest.TestCase):
    def test_a_matching_loading_is_clean(self):
        self.assertEqual(loading_findings(10.0, 10.0), [])

    def test_a_heavier_loading_is_clean(self):
        self.assertEqual(loading_findings(15.0, 10.0), [])

    def test_a_lighter_loading_is_reported(self):
        findings = loading_findings(4.0, 10.0)
        self.assertTrue(any("understated" in f for f in findings))

    def test_a_zero_cabin_loading_rejected(self):
        with self.assertRaises(ValueError):
            loading_findings(10.0, 0.0)


class FillTests(unittest.TestCase):
    def test_fill_fraction_is_item_over_chamber(self):
        self.assertAlmostEqual(chamber_fill_fraction(0.5, 2.0), 0.25, places=9)

    def test_a_lightly_filled_chamber_is_clean(self):
        self.assertEqual(fill_findings(0.2, 2.0), [])

    def test_a_chamber_filled_exactly_to_the_bound_is_clean(self):
        self.assertEqual(fill_findings(MAX_CHAMBER_FILL_FRACTION * 2.0, 2.0), [])

    def test_a_packed_chamber_is_reported(self):
        findings = fill_findings(1.8, 2.0)
        self.assertTrue(any("no longer well mixed" in f for f in findings))

    def test_zero_item_volume_rejected(self):
        with self.assertRaises(ValueError):
            chamber_fill_fraction(0.0, 2.0)


class PreparationTests(unittest.TestCase):
    def test_as_flown_preparations_are_clean(self):
        self.assertEqual(
            preparation_findings(("packaging-removed", "as-flown-configuration")), []
        )

    def test_a_solvent_wipe_is_reported(self):
        findings = preparation_findings(("solvent-wipe",))
        self.assertTrue(any("removes volatiles" in f for f in findings))

    def test_a_bake_out_is_reported(self):
        self.assertTrue(preparation_findings(("bake-out",)))

    def test_a_nitrogen_purge_is_reported(self):
        self.assertTrue(preparation_findings(("nitrogen-purge",)))

    def test_every_banned_preparation_in_a_list_is_reported(self):
        findings = preparation_findings(("solvent-wipe", "bake-out", "packaging-removed"))
        self.assertEqual(len(findings), 2)

    def test_an_unknown_preparation_rejected(self):
        with self.assertRaises(ValueError):
            preparation_findings(("polished",))

    def test_a_bare_string_is_not_a_preparation_list(self):
        with self.assertRaises(ValueError):
            preparation_findings("solvent-wipe")


class CureTests(unittest.TestCase):
    def test_a_full_recent_cure_is_clean(self):
        self.assertEqual(cure_findings(GOOD_CURE), [])

    def test_a_longer_cure_is_not_a_finding(self):
        self.assertEqual(cure_findings(dict(GOOD_CURE, achieved_hours=48.0)), [])

    def test_a_short_cure_is_reported(self):
        findings = cure_findings(dict(GOOD_CURE, achieved_hours=6.0))
        self.assertTrue(any("incompletely cured" in f for f in findings))

    def test_an_item_exactly_at_the_age_window_is_clean(self):
        self.assertEqual(
            cure_findings(dict(GOOD_CURE, days_since_cure=MAX_DAYS_SINCE_CURE)), []
        )

    def test_an_item_past_the_age_window_is_reported(self):
        findings = cure_findings(dict(GOOD_CURE, days_since_cure=400.0))
        self.assertTrue(any("already released" in f for f in findings))

    def test_a_missing_cure_key_rejected(self):
        cure = dict(GOOD_CURE)
        del cure["days_since_cure"]
        with self.assertRaises(ValueError):
            cure_findings(cure)

    def test_a_negative_cure_age_rejected(self):
        with self.assertRaises(ValueError):
            cure_findings(dict(GOOD_CURE, days_since_cure=-1.0))


class RouteTests(unittest.TestCase):
    def test_a_bulk_material_is_tested_across_replicates(self):
        self.assertEqual(replicate_count("material-level"), MATERIAL_LEVEL_REPLICATES)

    def test_an_assembled_article_is_tested_once(self):
        self.assertEqual(replicate_count("assembled-article"), ASSEMBLED_ARTICLE_REPLICATES)

    def test_the_material_route_takes_more_items_than_the_article_route(self):
        self.assertGreater(
            replicate_count("material-level"), replicate_count("assembled-article")
        )

    def test_an_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            replicate_count("component-level")

    def test_both_routes_are_named(self):
        self.assertEqual(len(TEST_ROUTES), 2)


class PlanTests(unittest.TestCase):
    def test_a_nominal_request_plans_cleanly(self):
        plan = plan_offgassing_test_item(base_request())
        self.assertTrue(plan["ready"])
        self.assertEqual(plan["findings"], [])

    def test_the_plan_reproduces_the_cabin_loading_exactly(self):
        plan = plan_offgassing_test_item(base_request())
        self.assertAlmostEqual(plan["loading_ratio"], 1.0, places=9)
        self.assertAlmostEqual(plan["achieved_loading_g_per_m3"], 10.0, places=9)

    def test_the_required_mass_is_planned_when_none_is_offered(self):
        request = base_request()
        del request["available_mass_g"]
        plan = plan_offgassing_test_item(request)
        self.assertAlmostEqual(plan["planned_mass_g"], plan["required_mass_g"], places=9)

    def test_too_little_material_under_loads_the_chamber(self):
        plan = plan_offgassing_test_item(base_request(available_mass_g=12.0))
        self.assertFalse(plan["ready"])
        self.assertTrue(any("understated" in f for f in plan["findings"]))

    def test_a_tiny_test_item_is_below_the_detection_floor(self):
        plan = plan_offgassing_test_item(
            base_request(cabin_loading_g_per_m3=2.0, chamber_volume_m3=1.0, available_mass_g=2.0)
        )
        self.assertTrue(any("below the %g g" % MIN_SPECIMEN_MASS_G in f for f in plan["findings"]))

    def test_a_packed_chamber_reaches_the_plan(self):
        plan = plan_offgassing_test_item(base_request(item_volume_m3=1.9))
        self.assertFalse(plan["ready"])
        self.assertAlmostEqual(plan["chamber_fill_fraction"], 0.95, places=9)

    def test_a_banned_preparation_reaches_the_plan(self):
        plan = plan_offgassing_test_item(
            base_request(preparations=("packaging-removed", "solvent-wipe"))
        )
        self.assertFalse(plan["ready"])
        self.assertTrue(any("removes volatiles" in f for f in plan["findings"]))

    def test_an_uncured_item_reaches_the_plan(self):
        plan = plan_offgassing_test_item(
            base_request(cure=dict(GOOD_CURE, achieved_hours=1.0))
        )
        self.assertTrue(any("incompletely cured" in f for f in plan["findings"]))

    def test_a_material_route_plans_replicates_and_their_total_mass(self):
        plan = plan_offgassing_test_item(base_request(route="material-level"))
        self.assertEqual(plan["test_items"], MATERIAL_LEVEL_REPLICATES)
        self.assertAlmostEqual(
            plan["total_material_g"], plan["planned_mass_g"] * MATERIAL_LEVEL_REPLICATES,
            places=9,
        )

    def test_conservatism_raises_the_required_mass_in_the_plan(self):
        plan = plan_offgassing_test_item(base_request(conservatism=2.0))
        self.assertAlmostEqual(plan["required_mass_g"], 40.0, places=9)

    def test_a_plan_without_a_declared_item_volume_skips_the_fill_check(self):
        request = base_request()
        del request["item_volume_m3"]
        plan = plan_offgassing_test_item(request)
        self.assertIsNone(plan["chamber_fill_fraction"])
        self.assertTrue(plan["ready"])

    def test_missing_required_request_key_rejected(self):
        request = base_request()
        del request["chamber_volume_m3"]
        with self.assertRaises(ValueError):
            plan_offgassing_test_item(request)

    def test_non_mapping_request_rejected(self):
        with self.assertRaises(ValueError):
            plan_offgassing_test_item("assembled-article")


if __name__ == "__main__":
    unittest.main()
