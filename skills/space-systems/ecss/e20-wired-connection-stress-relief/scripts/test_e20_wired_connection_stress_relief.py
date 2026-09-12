#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 4.2.5 wired connection
strain relief.

Exercises the sibling logic module (stdlib unittest, offline).
Contract: a relief provision is categorized as exactly restraining or
non-restraining and an unrecognized provision raises; the quasi-static
inertial load is mass x acceleration x g0 x safety factor, with a
negative mass or acceleration and a safety factor below unity raising;
the conductor allowable is area x stress and the termination allowable
is that allowable scaled by the termination's strength fraction, with
a non-positive area or stress and an unrecognized termination raising;
the load margin inverts the allowable over the applied load and is
infinite at zero load; the maximum unsupported span round-trips back
to the allowable through the load expression; a connection carrying
more than a de-minimis load with no restraint is reported, and a
soldered termination in that state is reported a second time; relief
geometry below the minimum bend radius is reported; and a review is
compliant only when every finding group is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_wired_connection_stress_relief_logic as sr  # noqa: E402


def make_connection(**overrides):
    """A compliant baseline connection record; overrides replace fields."""
    connection = {
        "connection_id": "W12-J3",
        "relief_provision": "clamp_saddle",
        "termination_type": "crimp_contact",
        "conductor_area_mm2": 0.38,
        "allowable_stress_mpa": 160.0,
        "unsupported_span_m": 0.15,
        "mass_per_metre_kg_m": 0.012,
        "design_acceleration_g": 25.0,
        "safety_factor": 1.5,
        "required_margin": 0.25,
        "bend_radius_mm": 30.0,
        "bundle_outer_diameter_mm": 8.0,
        "min_bend_ratio": 3.0,
    }
    connection.update(overrides)
    return connection


class CategorizeReliefProvisionTest(unittest.TestCase):
    def test_clamp_saddle_is_restraining(self):
        self.assertEqual(
            sr.categorize_relief_provision("clamp_saddle"), "restraining"
        )

    def test_backshell_relief_is_restraining(self):
        self.assertEqual(
            sr.categorize_relief_provision("connector_backshell_relief"),
            "restraining",
        )

    def test_potted_transition_is_restraining(self):
        self.assertEqual(
            sr.categorize_relief_provision("potted_transition"), "restraining"
        )

    def test_none_is_non_restraining(self):
        self.assertEqual(
            sr.categorize_relief_provision("none"), "non_restraining"
        )

    def test_sleeving_only_is_non_restraining(self):
        self.assertEqual(
            sr.categorize_relief_provision("sleeving_only"), "non_restraining"
        )

    def test_unknown_provision_raises(self):
        with self.assertRaises(ValueError):
            sr.categorize_relief_provision("a_bit_of_tape")


class SegmentInertialLoadTest(unittest.TestCase):
    def test_nominal_segment_load(self):
        self.assertAlmostEqual(
            sr.segment_inertial_load_n(0.0018, 25.0, 1.5), 0.661948875
        )

    def test_load_scales_linearly_with_mass(self):
        single = sr.segment_inertial_load_n(0.002, 20.0, 1.25)
        double = sr.segment_inertial_load_n(0.004, 20.0, 1.25)
        self.assertAlmostEqual(double, 2.0 * single)

    def test_zero_mass_gives_zero_load(self):
        self.assertAlmostEqual(sr.segment_inertial_load_n(0.0, 25.0, 1.5), 0.0)

    def test_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            sr.segment_inertial_load_n(-0.001, 25.0, 1.5)

    def test_negative_acceleration_raises(self):
        with self.assertRaises(ValueError):
            sr.segment_inertial_load_n(0.001, -25.0, 1.5)

    def test_safety_factor_below_unity_raises(self):
        with self.assertRaises(ValueError):
            sr.segment_inertial_load_n(0.001, 25.0, 0.9)


class AllowableLoadTest(unittest.TestCase):
    def test_conductor_allowable_is_area_times_stress(self):
        self.assertAlmostEqual(
            sr.conductor_allowable_load_n(0.38, 160.0), 60.8
        )

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            sr.conductor_allowable_load_n(0.0, 160.0)

    def test_negative_stress_raises(self):
        with self.assertRaises(ValueError):
            sr.conductor_allowable_load_n(0.38, -160.0)

    def test_crimp_termination_keeps_most_of_the_conductor(self):
        self.assertAlmostEqual(
            sr.termination_allowable_load_n("crimp_contact", 60.8), 51.68
        )

    def test_solder_cup_is_markedly_weaker_than_a_crimp(self):
        crimp = sr.termination_allowable_load_n("crimp_contact", 60.8)
        solder = sr.termination_allowable_load_n("solder_cup", 60.8)
        self.assertLess(solder, 0.5 * crimp)

    def test_unknown_termination_raises(self):
        with self.assertRaises(ValueError):
            sr.termination_allowable_load_n("twisted_and_hoped", 60.8)

    def test_negative_conductor_allowable_raises(self):
        with self.assertRaises(ValueError):
            sr.termination_allowable_load_n("crimp_contact", -1.0)


class LoadMarginTest(unittest.TestCase):
    def test_allowable_twice_the_load_gives_unit_margin(self):
        self.assertAlmostEqual(sr.load_margin(20.0, 10.0), 1.0)

    def test_allowable_equal_to_load_gives_zero_margin(self):
        self.assertAlmostEqual(sr.load_margin(10.0, 10.0), 0.0)

    def test_overloaded_connection_gives_negative_margin(self):
        self.assertAlmostEqual(sr.load_margin(5.0, 10.0), -0.5)

    def test_zero_applied_load_is_infinite_margin(self):
        self.assertTrue(math.isinf(sr.load_margin(10.0, 0.0)))

    def test_negative_applied_load_raises(self):
        with self.assertRaises(ValueError):
            sr.load_margin(10.0, -1.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            sr.load_margin(-10.0, 1.0)


class MaxUnsupportedSpanTest(unittest.TestCase):
    def test_span_round_trips_to_the_allowable(self):
        span = sr.max_unsupported_span_m(51.68, 0.012, 25.0, 1.5)
        self.assertAlmostEqual(
            sr.segment_inertial_load_n(span * 0.012, 25.0, 1.5), 51.68
        )

    def test_heavier_harness_shortens_the_span(self):
        light = sr.max_unsupported_span_m(51.68, 0.012, 25.0, 1.5)
        heavy = sr.max_unsupported_span_m(51.68, 0.048, 25.0, 1.5)
        self.assertAlmostEqual(heavy, light / 4.0)

    def test_zero_mass_per_metre_raises(self):
        with self.assertRaises(ValueError):
            sr.max_unsupported_span_m(51.68, 0.0, 25.0, 1.5)

    def test_zero_acceleration_raises(self):
        with self.assertRaises(ValueError):
            sr.max_unsupported_span_m(51.68, 0.012, 0.0, 1.5)

    def test_safety_factor_below_unity_raises(self):
        with self.assertRaises(ValueError):
            sr.max_unsupported_span_m(51.68, 0.012, 25.0, 0.5)


class BendRadiusFindingsTest(unittest.TestCase):
    def test_generous_radius_is_clean(self):
        self.assertEqual(sr.bend_radius_findings("W1", 30.0, 8.0, 3.0), [])

    def test_radius_exactly_at_the_minimum_is_clean(self):
        self.assertEqual(sr.bend_radius_findings("W1", 24.0, 8.0, 3.0), [])

    def test_tight_radius_is_flagged_with_the_requirement(self):
        findings = sr.bend_radius_findings("W2", 12.0, 8.0, 3.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "relief_forces_bend_below_minimum_radius"
        )
        self.assertAlmostEqual(findings[0]["required_radius_mm"], 24.0)

    def test_zero_outer_diameter_raises(self):
        with self.assertRaises(ValueError):
            sr.bend_radius_findings("W1", 30.0, 0.0, 3.0)

    def test_negative_radius_raises(self):
        with self.assertRaises(ValueError):
            sr.bend_radius_findings("W1", -1.0, 8.0, 3.0)

    def test_zero_ratio_raises(self):
        with self.assertRaises(ValueError):
            sr.bend_radius_findings("W1", 30.0, 8.0, 0.0)


class LoadPathFindingsTest(unittest.TestCase):
    def test_restrained_connection_is_clean(self):
        self.assertEqual(
            sr.load_path_findings("W1", "clamp_saddle", "solder_cup", 5.0), []
        )

    def test_de_minimis_load_without_restraint_is_clean(self):
        self.assertEqual(
            sr.load_path_findings("W1", "none", "crimp_contact", 0.01), []
        )

    def test_unrestrained_crimped_connection_is_flagged_once(self):
        findings = sr.load_path_findings("W3", "none", "crimp_contact", 5.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "wire_carries_load_without_strain_relief"
        )

    def test_unrestrained_soldered_connection_is_flagged_twice(self):
        findings = sr.load_path_findings("W4", "sleeving_only", "solder_lug", 5.0)
        self.assertEqual(len(findings), 2)
        self.assertEqual(
            findings[1]["issue"], "soldered_joint_in_primary_load_path"
        )

    def test_negative_applied_load_raises(self):
        with self.assertRaises(ValueError):
            sr.load_path_findings("W1", "none", "crimp_contact", -1.0)

    def test_unknown_termination_raises(self):
        with self.assertRaises(ValueError):
            sr.load_path_findings("W1", "none", "glued_on", 5.0)


class StrengthFindingsTest(unittest.TestCase):
    def test_ample_capability_is_clean(self):
        self.assertEqual(
            sr.strength_findings("W1", 0.66, 60.8, 51.68, 0.25), []
        )

    def test_termination_alone_can_fail(self):
        findings = sr.strength_findings("W5", 40.0, 60.8, 30.0, 0.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "termination_pull_out_capability_exceeded"
        )

    def test_both_conductor_and_termination_can_fail(self):
        findings = sr.strength_findings("W6", 80.0, 60.8, 51.68, 0.0)
        self.assertEqual(len(findings), 2)
        self.assertAlmostEqual(findings[0]["margin"], 60.8 / 80.0 - 1.0)

    def test_required_margin_can_turn_a_positive_margin_into_a_finding(self):
        self.assertEqual(sr.strength_findings("W7", 30.0, 60.8, 51.68, 0.5), [])
        findings = sr.strength_findings("W7", 30.0, 60.8, 51.68, 1.0)
        self.assertEqual(len(findings), 1)

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            sr.strength_findings("W1", 1.0, 60.8, 51.68, -0.1)


class ReviewConnectionTest(unittest.TestCase):
    def test_compliant_connection(self):
        review = sr.review_connection(make_connection())
        self.assertTrue(sr.is_connection_compliant(review))
        self.assertAlmostEqual(review["applied_load_n"], 0.661948875)
        self.assertAlmostEqual(review["conductor_allowable_n"], 60.8)
        self.assertAlmostEqual(review["termination_allowable_n"], 51.68)

    def test_unrestrained_soldered_connection_fails_the_load_path(self):
        review = sr.review_connection(
            make_connection(relief_provision="none", termination_type="solder_cup")
        )
        self.assertFalse(sr.is_connection_compliant(review))
        self.assertEqual(len(review["load_path"]), 2)

    def test_overlong_heavy_span_fails_strength_and_span(self):
        review = sr.review_connection(
            make_connection(
                conductor_area_mm2=0.02,
                termination_type="solder_lug",
                unsupported_span_m=2.0,
                mass_per_metre_kg_m=0.05,
                design_acceleration_g=40.0,
            )
        )
        self.assertFalse(sr.is_connection_compliant(review))
        self.assertEqual(len(review["strength"]), 2)
        self.assertEqual(len(review["span"]), 1)
        self.assertLess(review["permissible_span_m"], 2.0)

    def test_tight_bend_radius_fails_an_otherwise_clean_connection(self):
        review = sr.review_connection(make_connection(bend_radius_mm=10.0))
        self.assertFalse(sr.is_connection_compliant(review))
        self.assertEqual(len(review["bend_radius"]), 1)

    def test_bend_radius_is_skipped_when_not_recorded(self):
        connection = make_connection()
        del connection["bend_radius_mm"]
        review = sr.review_connection(connection)
        self.assertEqual(review["bend_radius"], [])
        self.assertTrue(sr.is_connection_compliant(review))

    def test_missing_required_key_raises(self):
        connection = make_connection()
        del connection["safety_factor"]
        with self.assertRaises(ValueError):
            sr.review_connection(connection)

    def test_negative_span_raises(self):
        with self.assertRaises(ValueError):
            sr.review_connection(make_connection(unsupported_span_m=-0.1))

    def test_zero_mass_per_metre_raises(self):
        with self.assertRaises(ValueError):
            sr.review_connection(make_connection(mass_per_metre_kg_m=0.0))


if __name__ == "__main__":
    unittest.main()
