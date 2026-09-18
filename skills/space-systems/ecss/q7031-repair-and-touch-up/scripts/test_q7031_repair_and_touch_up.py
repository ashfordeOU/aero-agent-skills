"""Contract tests for the paint repair and touch-up logic.

The cases take one local defect through the four budgets a touch-up has to sit
inside: how deep the defect reaches and therefore what has to be rebuilt, how
much of the painted area the repairs have consumed, how many local
re-applications the area has left, and what the extra film does to local
thickness, to the blend and to the mass budget.
"""

import unittest

from q7031_repair_and_touch_up_logic import (
    DEFAULT_REAPPLICATION_LIMIT,
    DEPTH_SCHEMES,
    REPAIR_DEPTHS,
    added_mass_g,
    assess_repair_history,
    assess_touch_up_request,
    blend_margin_sufficient,
    categorize_repair_depth,
    projected_local_thickness_um,
    reapplications_remaining,
    repair_scheme_for_depth,
    touch_up_area_fraction,
    within_area_limit,
)


def _request(**overrides):
    request = {
        "name": "bracket-face-01",
        "depth": "topcoat-only",
        "painted_area_m2": 2.0,
        "repair_area_cm2": 40.0,
        "prior_repair_areas_cm2": [],
        "area_fraction_limit": 0.05,
        "prior_applications": 0,
        "reapplication_limit": 2,
        "existing_thickness_um": 55.0,
        "removed_thickness_um": 10.0,
        "added_thickness_um": 20.0,
        "maximum_thickness_um": 80.0,
        "blend_margin_mm": 15.0,
        "minimum_blend_margin_mm": 10.0,
        "hours_since_last_coat": 6.0,
        "minimum_recoat_interval_h": 4.0,
        "paint_density_g_cm3": 1.4,
        "mass_allowance_g": 5.0,
    }
    request.update(overrides)
    return request


class DepthTests(unittest.TestCase):
    def test_every_catalogued_depth_normalizes(self):
        for depth in REPAIR_DEPTHS:
            self.assertEqual(categorize_repair_depth(depth.upper()), depth)

    def test_a_topcoat_defect_rebuilds_only_the_topcoat(self):
        self.assertEqual(repair_scheme_for_depth("topcoat-only"), DEPTH_SCHEMES["topcoat-only"])

    def test_a_defect_to_the_substrate_owes_surface_preparation(self):
        self.assertIn("surface-preparation", repair_scheme_for_depth("to-substrate"))

    def test_substrate_damage_is_not_a_coating_repair(self):
        with self.assertRaises(ValueError):
            repair_scheme_for_depth("substrate-damaged")

    def test_an_unknown_depth_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_repair_depth("slightly-scuffed")


class AreaBudgetTests(unittest.TestCase):
    def test_fraction_is_repaired_area_over_painted_area(self):
        self.assertAlmostEqual(touch_up_area_fraction([100.0], 1.0), 0.01, places=9)

    def test_prior_repairs_are_carried_into_the_fraction(self):
        self.assertAlmostEqual(touch_up_area_fraction([100.0, 100.0], 1.0), 0.02, places=9)

    def test_a_fraction_exactly_on_the_limit_is_inside_it(self):
        fraction = touch_up_area_fraction([500.0], 1.0)
        self.assertAlmostEqual(fraction, 0.05, places=9)
        self.assertTrue(within_area_limit(fraction, 0.05))

    def test_a_clearly_larger_fraction_is_outside_the_limit(self):
        self.assertFalse(within_area_limit(0.20, 0.05))

    def test_zero_painted_area_is_refused(self):
        with self.assertRaises(ValueError):
            touch_up_area_fraction([10.0], 0.0)

    def test_a_non_positive_repair_area_is_refused(self):
        with self.assertRaises(ValueError):
            touch_up_area_fraction([0.0], 1.0)

    def test_a_limit_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            within_area_limit(0.01, 1.5)


class ReapplicationTests(unittest.TestCase):
    def test_a_fresh_area_has_the_whole_budget(self):
        self.assertEqual(reapplications_remaining(0), DEFAULT_REAPPLICATION_LIMIT)

    def test_each_prior_application_spends_one(self):
        self.assertEqual(reapplications_remaining(1, 2), 1)

    def test_an_exhausted_budget_reports_zero_not_a_negative(self):
        self.assertEqual(reapplications_remaining(5, 2), 0)

    def test_a_boolean_count_is_refused(self):
        with self.assertRaises(ValueError):
            reapplications_remaining(True)

    def test_a_negative_count_is_refused(self):
        with self.assertRaises(ValueError):
            reapplications_remaining(-1)


class ThicknessAndMassTests(unittest.TestCase):
    def test_abrasion_is_taken_off_before_the_new_film_goes_on(self):
        self.assertAlmostEqual(projected_local_thickness_um(55.0, 20.0, 10.0), 65.0, places=9)

    def test_with_no_abrasion_the_new_film_simply_adds(self):
        self.assertAlmostEqual(projected_local_thickness_um(55.0, 20.0), 75.0, places=9)

    def test_removing_more_film_than_the_area_carries_is_refused(self):
        with self.assertRaises(ValueError):
            projected_local_thickness_um(20.0, 20.0, 30.0)

    def test_a_non_positive_added_film_is_refused(self):
        with self.assertRaises(ValueError):
            projected_local_thickness_um(55.0, 0.0)

    def test_added_mass_follows_area_times_film_times_density(self):
        self.assertAlmostEqual(added_mass_g(100.0, 50.0, 1.4), 0.7, places=9)

    def test_a_non_positive_density_is_refused(self):
        with self.assertRaises(ValueError):
            added_mass_g(100.0, 50.0, 0.0)

    def test_a_blend_margin_on_the_floor_is_sufficient(self):
        self.assertTrue(blend_margin_sufficient(10.0, 10.0))

    def test_a_clearly_short_blend_margin_is_insufficient(self):
        self.assertFalse(blend_margin_sufficient(2.0, 10.0))

    def test_a_negative_blend_margin_is_refused(self):
        with self.assertRaises(ValueError):
            blend_margin_sufficient(-1.0)


class RequestDispositionTests(unittest.TestCase):
    def test_a_request_inside_every_budget_is_permitted(self):
        result = assess_touch_up_request(_request())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["disposition"], "touch-up-permitted")
        self.assertTrue(result["permitted"])

    def test_an_exhausted_reapplication_budget_forces_a_strip(self):
        result = assess_touch_up_request(_request(prior_applications=2))
        self.assertIn("reapplication-limit-reached", result["findings"])
        self.assertEqual(result["disposition"], "strip-and-repaint-required")

    def test_too_much_repaired_area_forces_a_strip(self):
        result = assess_touch_up_request(
            _request(repair_area_cm2=40.0, prior_repair_areas_cm2=[1200.0])
        )
        self.assertIn("repaired-area-fraction-exceeded", result["findings"])
        self.assertEqual(result["disposition"], "strip-and-repaint-required")

    def test_a_projection_above_the_ceiling_forces_a_strip(self):
        result = assess_touch_up_request(
            _request(existing_thickness_um=75.0, removed_thickness_um=0.0, added_thickness_um=30.0)
        )
        self.assertIn("local-thickness-above-maximum", result["findings"])

    def test_a_narrow_blend_is_corrective_action_not_a_strip(self):
        result = assess_touch_up_request(_request(blend_margin_mm=3.0))
        self.assertIn("blend-margin-too-narrow", result["findings"])
        self.assertEqual(result["disposition"], "corrective-action-required")

    def test_an_unmet_recoat_interval_is_raised(self):
        result = assess_touch_up_request(_request(hours_since_last_coat=1.0))
        self.assertIn("recoat-interval-not-met", result["findings"])

    def test_an_exceeded_mass_allowance_is_raised(self):
        result = assess_touch_up_request(_request(mass_allowance_g=0.01))
        self.assertIn("repair-mass-allowance-exceeded", result["findings"])

    def test_substrate_damage_is_refused_rather_than_repaired(self):
        result = assess_touch_up_request(_request(depth="substrate-damaged"))
        self.assertEqual(result["disposition"], "refused")
        self.assertEqual(result["findings"], ["substrate-damage-not-a-coating-repair"])

    def test_a_request_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            assess_touch_up_request(_request(name="   "))

    def test_a_non_mapping_request_is_refused(self):
        with self.assertRaises(ValueError):
            assess_touch_up_request(["bracket-face-01"])


class HistoryTests(unittest.TestCase):
    def test_a_history_of_permitted_repairs_is_accepted(self):
        history = assess_repair_history([_request(), _request(name="bracket-face-02")])
        self.assertTrue(history["history_accepted"])
        self.assertEqual(history["strip_required"], [])

    def test_total_added_mass_is_summed_across_the_history(self):
        history = assess_repair_history([_request(), _request(name="bracket-face-02")])
        self.assertAlmostEqual(history["total_added_mass_g"], 0.224, places=9)

    def test_one_exhausted_area_shows_up_as_a_strip(self):
        history = assess_repair_history([
            _request(),
            _request(name="bracket-face-02", prior_applications=2),
        ])
        self.assertEqual(history["strip_required"], ["bracket-face-02"])
        self.assertFalse(history["history_accepted"])

    def test_a_refused_request_is_reported_separately(self):
        history = assess_repair_history([_request(name="rib-01", depth="substrate-damaged")])
        self.assertEqual(history["refused"], ["rib-01"])

    def test_duplicate_request_names_are_refused(self):
        with self.assertRaises(ValueError):
            assess_repair_history([_request(), _request()])

    def test_an_empty_history_is_refused(self):
        with self.assertRaises(ValueError):
            assess_repair_history([])


if __name__ == "__main__":
    unittest.main()
