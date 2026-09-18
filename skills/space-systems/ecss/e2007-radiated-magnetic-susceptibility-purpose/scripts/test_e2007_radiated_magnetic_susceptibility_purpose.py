#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-magnetic-susceptibility-purpose.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_magnetic_susceptibility_purpose.py
"""

import math
import unittest

from e2007_radiated_magnetic_susceptibility_purpose_logic import (
    AIM_OBJECTIVES,
    DEFAULT_AIM_BAND_HZ,
    DEFAULT_MAX_STANDOFF_M,
    OBJECTIVE_BAND_SPAN,
    OBJECTIVE_FIELD_LEVEL,
    OBJECTIVE_LOOP_STANDOFF,
    OBJECTIVE_PERFORMANCE_WATCH,
    OBJECTIVE_RADIATING_LOOP,
    VACUUM_PERMEABILITY_H_PER_M,
    VERDICT_SERVED,
    VERDICT_UNSERVED,
    assess_plan_set,
    at_most,
    band_coverage_fraction,
    band_edges_reached,
    field_to_flux_density_t,
    grade_objectives,
    loop_axial_field_a_per_m,
    normalize_source,
    validate_plan,
)


def good_plan(**over):
    record = {
        "id": "rms-1",
        "source": "radiating-loop",
        "sweep_start_hz": 30.0,
        "sweep_stop_hz": 50.0e3,
        "standoff_m": 0.05,
        "required_field_a_per_m": 140.0,
        "performance_monitored": True,
    }
    record.update(over)
    return record


class TestSourceNormalization(unittest.TestCase):
    def test_a_radiating_loop_normalizes(self):
        self.assertEqual(normalize_source(" Radiating-Loop "), "radiating-loop")

    def test_a_helmholtz_pair_normalizes(self):
        self.assertEqual(normalize_source("HELMHOLTZ-PAIR"), "helmholtz-pair")

    def test_a_far_field_antenna_is_not_this_aim(self):
        with self.assertRaises(ValueError):
            normalize_source("biconical-antenna")

    def test_a_non_string_source_rejected(self):
        with self.assertRaises(ValueError):
            normalize_source(1)


class TestLoopField(unittest.TestCase):
    def test_field_at_the_loop_centre_matches_the_closed_form(self):
        # On the plane of the loop the field reduces to turns*current/(2*radius).
        self.assertAlmostEqual(
            loop_axial_field_a_per_m(10, 1.0, 0.05, 0.0), 100.0, places=9
        )

    def test_field_falls_off_with_standoff(self):
        near = loop_axial_field_a_per_m(10, 1.0, 0.05, 0.0)
        far = loop_axial_field_a_per_m(10, 1.0, 0.05, 0.20)
        self.assertLess(far, near)

    def test_field_scales_linearly_with_current(self):
        single = loop_axial_field_a_per_m(10, 1.0, 0.05, 0.03)
        double = loop_axial_field_a_per_m(10, 2.0, 0.05, 0.03)
        self.assertAlmostEqual(double, 2.0 * single, places=9)

    def test_field_scales_linearly_with_turns(self):
        one_turn = loop_axial_field_a_per_m(1, 1.0, 0.05, 0.03)
        ten_turns = loop_axial_field_a_per_m(10, 1.0, 0.05, 0.03)
        self.assertAlmostEqual(ten_turns, 10.0 * one_turn, places=9)

    def test_a_standoff_of_one_radius_leaves_a_known_share(self):
        # At d = r the slant distance is r*sqrt(2), so the field drops to
        # 1/(2*sqrt(2)) of its centre value.
        centre = loop_axial_field_a_per_m(10, 1.0, 0.05, 0.0)
        at_radius = loop_axial_field_a_per_m(10, 1.0, 0.05, 0.05)
        self.assertAlmostEqual(
            at_radius, centre / (2.0 * math.sqrt(2.0)), places=9
        )

    def test_zero_turns_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_field_a_per_m(0, 1.0, 0.05, 0.0)

    def test_a_fractional_turn_count_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_field_a_per_m(2.5, 1.0, 0.05, 0.0)

    def test_a_boolean_turn_count_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_field_a_per_m(True, 1.0, 0.05, 0.0)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_field_a_per_m(10, 0.0, 0.05, 0.0)

    def test_zero_radius_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_field_a_per_m(10, 1.0, 0.0, 0.0)

    def test_a_negative_standoff_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_field_a_per_m(10, 1.0, 0.05, -0.01)


class TestFluxDensity(unittest.TestCase):
    def test_conversion_uses_the_free_space_permeability(self):
        self.assertAlmostEqual(
            field_to_flux_density_t(100.0),
            100.0 * VACUUM_PERMEABILITY_H_PER_M,
            places=15,
        )

    def test_a_zero_field_converts_to_zero(self):
        self.assertAlmostEqual(field_to_flux_density_t(0.0), 0.0, places=15)

    def test_a_negative_field_rejected(self):
        with self.assertRaises(ValueError):
            field_to_flux_density_t(-1.0)


class TestBandEdges(unittest.TestCase):
    def test_a_sweep_spanning_the_band_reaches_both_edges(self):
        edges = band_edges_reached(DEFAULT_AIM_BAND_HZ)
        self.assertTrue(edges["spans_band"])

    def test_a_sweep_starting_late_misses_the_bottom(self):
        edges = band_edges_reached((300.0, 50.0e3))
        self.assertFalse(edges["reaches_bottom"])
        self.assertTrue(edges["reaches_top"])

    def test_a_sweep_stopping_early_misses_the_top(self):
        edges = band_edges_reached((30.0, 5.0e3))
        self.assertTrue(edges["reaches_bottom"])
        self.assertFalse(edges["reaches_top"])

    def test_an_inverted_sweep_rejected(self):
        with self.assertRaises(ValueError):
            band_edges_reached((50.0e3, 30.0))

    def test_a_sweep_that_is_not_a_pair_rejected(self):
        with self.assertRaises(ValueError):
            band_edges_reached((30.0, 300.0, 50.0e3))

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            band_edges_reached((30.0, 50.0e3), (50.0e3, 30.0))


class TestBandCoverage(unittest.TestCase):
    def test_a_sweep_covering_the_band_scores_one(self):
        self.assertAlmostEqual(
            band_coverage_fraction(DEFAULT_AIM_BAND_HZ), 1.0, places=9
        )

    def test_one_decade_of_a_three_decade_band_scores_a_third(self):
        self.assertAlmostEqual(
            band_coverage_fraction((1.0, 10.0), (1.0, 1000.0)), 1.0 / 3.0, places=9
        )

    def test_a_sweep_wholly_outside_the_band_scores_zero(self):
        self.assertAlmostEqual(
            band_coverage_fraction((1.0e6, 2.0e6), DEFAULT_AIM_BAND_HZ), 0.0, places=9
        )

    def test_a_sweep_wider_than_the_band_is_clipped_to_one(self):
        self.assertAlmostEqual(
            band_coverage_fraction((1.0, 1.0e6), DEFAULT_AIM_BAND_HZ), 1.0, places=9
        )

    def test_skipping_the_bottom_decade_costs_a_large_share(self):
        # Judged linearly this sweep looks nearly complete; across decades it
        # is visibly short, which is the whole point of the log domain.
        covered = band_coverage_fraction((300.0, 50.0e3), DEFAULT_AIM_BAND_HZ)
        self.assertGreater(covered, 0.60)
        self.assertLess(covered, 0.75)

    def test_coverage_never_exceeds_one(self):
        for sweep in ((1.0, 1.0e9), (30.0, 50.0e3), (100.0, 40.0e3)):
            self.assertTrue(at_most(band_coverage_fraction(sweep), 1.0))


class TestPlanValidation(unittest.TestCase):
    def test_a_good_plan_normalizes(self):
        record = validate_plan(good_plan())
        self.assertEqual(record["id"], "rms-1")
        self.assertEqual(record["source"], "radiating-loop")

    def test_an_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(good_plan(id="   "))

    def test_a_non_positive_sweep_start_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(good_plan(sweep_start_hz=0.0))

    def test_a_sweep_stop_at_the_start_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(good_plan(sweep_stop_hz=30.0))

    def test_a_negative_standoff_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(good_plan(standoff_m=-0.01))

    def test_a_non_boolean_monitoring_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(good_plan(performance_monitored="yes"))

    def test_a_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(["rms-1"])


class TestObjectiveGrading(unittest.TestCase):
    def test_a_good_plan_serves_every_aim(self):
        report = grade_objectives(good_plan())
        self.assertTrue(report["serves_aim"])
        self.assertEqual(report["unserved"], [])
        self.assertEqual(len(report["served"]), len(AIM_OBJECTIVES))

    def test_a_loop_held_too_far_away_leaves_the_standoff_unserved(self):
        report = grade_objectives(good_plan(standoff_m=0.5))
        self.assertIn(OBJECTIVE_LOOP_STANDOFF, report["unserved"])
        self.assertFalse(report["serves_aim"])

    def test_a_standoff_exactly_at_the_limit_is_served(self):
        report = grade_objectives(good_plan(standoff_m=DEFAULT_MAX_STANDOFF_M))
        self.assertNotIn(OBJECTIVE_LOOP_STANDOFF, report["unserved"])

    def test_a_narrow_sweep_leaves_the_band_span_unserved(self):
        report = grade_objectives(good_plan(sweep_start_hz=1.0e3))
        self.assertIn(OBJECTIVE_BAND_SPAN, report["unserved"])

    def test_a_plan_with_no_field_level_leaves_that_aim_unserved(self):
        report = grade_objectives(good_plan(required_field_a_per_m=0.0))
        self.assertIn(OBJECTIVE_FIELD_LEVEL, report["unserved"])

    def test_an_unwatched_unit_leaves_the_monitoring_aim_unserved(self):
        report = grade_objectives(good_plan(performance_monitored=False))
        self.assertIn(OBJECTIVE_PERFORMANCE_WATCH, report["unserved"])

    def test_the_loop_source_aim_is_served_by_a_helmholtz_pair(self):
        report = grade_objectives(good_plan(source="helmholtz-pair"))
        self.assertNotIn(OBJECTIVE_RADIATING_LOOP, report["unserved"])

    def test_unserved_aims_are_reported_in_the_fixed_order(self):
        report = grade_objectives(
            good_plan(
                standoff_m=0.5,
                required_field_a_per_m=0.0,
                performance_monitored=False,
            )
        )
        ranks = [AIM_OBJECTIVES.index(name) for name in report["unserved"]]
        self.assertEqual(ranks, sorted(ranks))

    def test_a_zero_standoff_limit_rejected(self):
        with self.assertRaises(ValueError):
            grade_objectives(good_plan(), max_standoff_m=0.0)


class TestPlanSet(unittest.TestCase):
    def test_a_set_of_good_plans_serves_the_aim(self):
        report = assess_plan_set([good_plan(), good_plan(id="rms-2")])
        self.assertEqual(report["verdict"], VERDICT_SERVED)
        self.assertEqual(report["plans_missing_the_aim"], [])
        self.assertAlmostEqual(report["mean_coverage_fraction"], 1.0, places=9)

    def test_one_bad_plan_makes_the_set_unserved(self):
        report = assess_plan_set(
            [good_plan(), good_plan(id="rms-2", performance_monitored=False)]
        )
        self.assertEqual(report["verdict"], VERDICT_UNSERVED)
        self.assertEqual(report["plans_missing_the_aim"], ["rms-2"])

    def test_mean_coverage_averages_across_the_set(self):
        report = assess_plan_set(
            [
                good_plan(),
                good_plan(id="rms-2", sweep_start_hz=1.0e3),
            ]
        )
        self.assertLess(report["mean_coverage_fraction"], 1.0)
        self.assertGreater(report["mean_coverage_fraction"], 0.5)

    def test_a_repeated_plan_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_plan_set([good_plan(), good_plan()])

    def test_an_empty_plan_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_plan_set([])

    def test_findings_name_the_plan_and_the_aim(self):
        report = assess_plan_set([good_plan(performance_monitored=False)])
        self.assertEqual(len(report["findings"]), 1)
        self.assertIn("rms-1", report["findings"][0])
        self.assertIn(OBJECTIVE_PERFORMANCE_WATCH, report["findings"][0])


if __name__ == "__main__":
    unittest.main(verbosity=1)
