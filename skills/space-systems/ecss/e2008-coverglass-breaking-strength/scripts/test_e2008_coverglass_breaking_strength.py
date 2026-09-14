#!/usr/bin/env python3
"""Contract test for the coverglass breaking strength leaf (offline)."""

import copy
import math
import unittest

from e2008_coverglass_breaking_strength_logic import (
    BEND_FIXTURES,
    DESIGN_FAILURE_PROBABILITY,
    FOUR_POINT_BEND,
    LOT_ACCEPTED,
    LOT_NOT_ACCEPTED,
    MIN_BROKEN_SAMPLES,
    MIN_WEIBULL_MODULUS,
    RING_ON_RING,
    THREE_POINT_BEND,
    assess_breaking_strength,
    break_stress_mpa,
    design_allowable_mpa,
    fit_weibull,
    four_point_bend_stress_mpa,
    mean_stress_mpa,
    median_rank_probabilities,
    missing_geometry,
    required_geometry,
    ring_on_ring_stress_mpa,
    three_point_bend_stress_mpa,
)

BAR_GEOMETRY = {
    "support_span_mm": 20.0,
    "width_mm": 10.0,
    "thickness_mm": 0.1,
}

# 300 MPa per newton with the bar geometry above, so the loads below map
# onto a tight lot running from 138 MPa to 198 MPa.
TIGHT_LOADS_N = (
    0.46,
    0.49,
    0.51,
    0.53,
    0.55,
    0.57,
    0.58,
    0.60,
    0.62,
    0.64,
    0.645,
    0.66,
)

# Same central tendency, a long weak tail underneath it.
SCATTERED_LOADS_N = (
    0.16,
    0.24,
    0.33,
    0.42,
    0.50,
    0.57,
    0.63,
    0.70,
    0.78,
    0.88,
    0.99,
    1.15,
)

TIGHT_CASE = {
    "bend_fixture": THREE_POINT_BEND,
    "geometry": dict(BAR_GEOMETRY),
    "break_loads_n": TIGHT_LOADS_N,
    "drawing_minimum_strength_mpa": 100.0,
}


def _case(**overrides):
    case = copy.deepcopy(TIGHT_CASE)
    case.update(overrides)
    return case


class FixtureGeometryTests(unittest.TestCase):
    def test_every_handled_fixture_declares_its_geometry(self):
        for fixture in BEND_FIXTURES:
            self.assertGreaterEqual(len(required_geometry(fixture)), 3)

    def test_a_ring_fixture_needs_poissons_ratio_and_a_bar_does_not(self):
        self.assertIn("poisson_ratio", required_geometry(RING_ON_RING))
        self.assertNotIn("poisson_ratio", required_geometry(THREE_POINT_BEND))

    def test_a_four_point_rig_needs_both_spans(self):
        keys = required_geometry(FOUR_POINT_BEND)
        self.assertIn("support_span_mm", keys)
        self.assertIn("load_span_mm", keys)

    def test_an_unhandled_fixture_has_no_geometry(self):
        with self.assertRaises(ValueError):
            required_geometry("pillow-block-crush")

    def test_absent_geometry_is_named_rather_than_defaulted(self):
        absent = missing_geometry(THREE_POINT_BEND, {"support_span_mm": 20.0})
        self.assertEqual(set(absent), {"width_mm", "thickness_mm"})

    def test_geometry_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            missing_geometry(THREE_POINT_BEND, ["support_span_mm"])


class StressConversionTests(unittest.TestCase):
    def test_a_centre_load_converts_by_the_bar_bending_formula(self):
        stress = three_point_bend_stress_mpa(0.5, 20.0, 10.0, 0.1)
        self.assertAlmostEqual(stress, 150.0, places=9)

    def test_stress_grows_as_the_square_of_the_thinning(self):
        thick = three_point_bend_stress_mpa(0.5, 20.0, 10.0, 0.2)
        thin = three_point_bend_stress_mpa(0.5, 20.0, 10.0, 0.1)
        self.assertAlmostEqual(thin / thick, 4.0, places=9)

    def test_a_four_point_rig_uses_the_offset_arm(self):
        stress = four_point_bend_stress_mpa(0.5, 20.0, 10.0, 10.0, 0.1)
        self.assertAlmostEqual(stress, 3.0 * 0.5 * 5.0 / (10.0 * 0.01), places=9)

    def test_a_four_point_load_span_inside_the_support_span_is_required(self):
        with self.assertRaises(ValueError):
            four_point_bend_stress_mpa(0.5, 10.0, 20.0, 10.0, 0.1)

    def test_the_ring_pair_returns_a_positive_equibiaxial_stress(self):
        stress = ring_on_ring_stress_mpa(2.0, 18.0, 6.0, 20.0, 0.15, 0.22)
        self.assertGreater(stress, 0.0)

    def test_a_support_ring_inside_the_load_ring_is_refused(self):
        with self.assertRaises(ValueError):
            ring_on_ring_stress_mpa(2.0, 6.0, 18.0, 20.0, 0.15, 0.22)

    def test_a_specimen_smaller_than_its_support_ring_is_refused(self):
        with self.assertRaises(ValueError):
            ring_on_ring_stress_mpa(2.0, 18.0, 6.0, 12.0, 0.15, 0.22)

    def test_a_negative_break_load_is_refused(self):
        with self.assertRaises(ValueError):
            three_point_bend_stress_mpa(-0.5, 20.0, 10.0, 0.1)

    def test_a_boolean_masquerading_as_a_load_is_refused(self):
        with self.assertRaises(ValueError):
            three_point_bend_stress_mpa(True, 20.0, 10.0, 0.1)

    def test_the_dispatcher_routes_each_fixture_to_its_own_formula(self):
        direct = three_point_bend_stress_mpa(0.5, 20.0, 10.0, 0.1)
        routed = break_stress_mpa(THREE_POINT_BEND, 0.5, BAR_GEOMETRY)
        self.assertAlmostEqual(routed, direct, places=9)

    def test_the_dispatcher_refuses_a_fixture_with_missing_geometry(self):
        with self.assertRaises(ValueError):
            break_stress_mpa(THREE_POINT_BEND, 0.5, {"width_mm": 10.0})


class WeibullFitTests(unittest.TestCase):
    def test_median_ranks_are_centred_inside_the_unit_interval(self):
        ranks = median_rank_probabilities(10)
        self.assertEqual(len(ranks), 10)
        self.assertAlmostEqual(ranks[0], 0.05, places=9)
        self.assertAlmostEqual(ranks[-1], 0.95, places=9)

    def test_a_single_article_cannot_be_ranked(self):
        with self.assertRaises(ValueError):
            median_rank_probabilities(1)

    def test_a_sample_set_below_the_floor_cannot_be_fitted(self):
        short = [150.0 + index for index in range(MIN_BROKEN_SAMPLES - 1)]
        with self.assertRaises(ValueError):
            fit_weibull(short)

    def test_a_set_with_no_spread_carries_no_distribution(self):
        with self.assertRaises(ValueError):
            fit_weibull([150.0] * (MIN_BROKEN_SAMPLES + 2))

    def test_a_tight_lot_fits_a_higher_modulus_than_a_scattered_one(self):
        tight = fit_weibull([300.0 * load for load in TIGHT_LOADS_N])
        scattered = fit_weibull([300.0 * load for load in SCATTERED_LOADS_N])
        self.assertGreater(tight["modulus"], scattered["modulus"])

    def test_the_characteristic_strength_sits_inside_the_sample_range(self):
        fit = fit_weibull([300.0 * load for load in TIGHT_LOADS_N])
        ordered = fit["ordered_stresses_mpa"]
        self.assertGreater(fit["characteristic_strength_mpa"], ordered[0])
        self.assertLess(fit["characteristic_strength_mpa"], ordered[-1] * 1.5)

    def test_the_allowable_falls_below_the_characteristic_strength(self):
        fit = fit_weibull([300.0 * load for load in TIGHT_LOADS_N])
        allowable = design_allowable_mpa(
            fit["modulus"],
            fit["characteristic_strength_mpa"],
            DESIGN_FAILURE_PROBABILITY,
        )
        self.assertLess(allowable, fit["characteristic_strength_mpa"])

    def test_a_certain_failure_probability_is_refused(self):
        with self.assertRaises(ValueError):
            design_allowable_mpa(8.0, 180.0, 1.0)

    def test_a_zero_failure_probability_is_refused(self):
        with self.assertRaises(ValueError):
            design_allowable_mpa(8.0, 180.0, 0.0)

    def test_the_allowable_reaches_the_scale_at_the_characteristic_risk(self):
        risk = 1.0 - math.exp(-1.0)
        allowable = design_allowable_mpa(8.0, 180.0, risk)
        self.assertAlmostEqual(allowable / 180.0, 1.0, places=9)

    def test_the_mean_is_reported_but_is_not_the_fit(self):
        stresses = [300.0 * load for load in TIGHT_LOADS_N]
        self.assertAlmostEqual(
            mean_stress_mpa(stresses), sum(stresses) / len(stresses), places=9
        )

    def test_an_empty_sample_set_has_no_mean(self):
        with self.assertRaises(ValueError):
            mean_stress_mpa([])


class LotAssessmentTests(unittest.TestCase):
    def test_a_tight_lot_over_the_drawing_value_is_accepted(self):
        result = assess_breaking_strength(TIGHT_CASE)
        self.assertEqual(result["verdict"], LOT_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_the_accepted_lot_reports_every_stage_of_its_own_arithmetic(self):
        result = assess_breaking_strength(TIGHT_CASE)
        self.assertEqual(result["sample_count"], len(TIGHT_LOADS_N))
        self.assertGreater(result["weibull_modulus"], MIN_WEIBULL_MODULUS)
        self.assertAlmostEqual(
            result["design_failure_probability"],
            DESIGN_FAILURE_PROBABILITY,
            places=9,
        )
        self.assertAlmostEqual(
            result["weakest_strength_mpa"], 300.0 * min(TIGHT_LOADS_N), places=6
        )

    def test_a_drawing_value_above_the_allowable_is_a_finding(self):
        result = assess_breaking_strength(
            _case(drawing_minimum_strength_mpa=150.0)
        )
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)
        self.assertTrue(any("design allowable" in f for f in result["findings"]))

    def test_a_passing_mean_over_a_failing_allowable_is_flagged(self):
        result = assess_breaking_strength(
            _case(
                break_loads_n=SCATTERED_LOADS_N,
                drawing_minimum_strength_mpa=100.0,
            )
        )
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)
        self.assertTrue(result["mean_hides_weak_tail"])
        self.assertGreater(result["mean_strength_mpa"], 100.0)
        self.assertLess(result["design_allowable_mpa"], 100.0)

    def test_a_tight_accepted_lot_is_not_flagged_as_hiding_a_tail(self):
        result = assess_breaking_strength(TIGHT_CASE)
        self.assertFalse(result["mean_hides_weak_tail"])

    def test_a_weak_individual_article_is_recorded_against_the_lot(self):
        loads = (0.20,) + TIGHT_LOADS_N[1:]
        result = assess_breaking_strength(
            _case(break_loads_n=loads, drawing_minimum_strength_mpa=100.0)
        )
        self.assertEqual(result["verdict"], LOT_NOT_ACCEPTED)
        self.assertTrue(any("weakest article" in f for f in result["findings"]))

    def test_an_unknown_fixture_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_breaking_strength(_case(bend_fixture="thumb-pressure"))

    def test_a_missing_drawing_minimum_stops_the_assessment(self):
        case = _case()
        del case["drawing_minimum_strength_mpa"]
        with self.assertRaises(ValueError):
            assess_breaking_strength(case)

    def test_an_empty_load_record_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_breaking_strength(_case(break_loads_n=[]))

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_breaking_strength(THREE_POINT_BEND)


if __name__ == "__main__":
    unittest.main()
