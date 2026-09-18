#!/usr/bin/env python3
"""Contract test for the complementary braid-shield branching leaf."""

import math
import unittest

from q2030_comp_branching_logic import (
    assess_breakout,
    braid_angle_rad,
    braid_coverage_from_construction,
    branch_shield_resistance_ohm,
    coverage_meets_trunk,
    evaluate_branch,
    exposed_length_acceptable,
    filling_factor,
    optical_coverage,
)

TRUNK = {
    "carriers": 24,
    "ends_per_carrier": 6,
    "wire_diameter_mm": 0.127,
    "picks_per_mm": 0.40,
    "core_diameter_mm": 5.0,
}

REQUIREMENTS = {
    "minimum_coverage": 0.80,
    "continuity_limit_ohm": 0.010,
    "exposed_length_limit_mm": 25.0,
    "max_branches_per_breakout": 3,
}


def branch_construction(**overrides):
    construction = dict(TRUNK)
    construction["core_diameter_mm"] = 3.0
    construction.update(overrides)
    return construction


def good_branch(**overrides):
    branch = {
        "id": "B-1",
        "construction": branch_construction(),
        "trunk_ohm": 0.0020,
        "junction_ohm": 0.0030,
        "branch_ohm": 0.0015,
        "junction_bonded": True,
        "exposed_length_mm": 12.0,
    }
    branch.update(overrides)
    return branch


def good_breakout(**overrides):
    spec = {
        "trunk_construction": TRUNK,
        "branches": [good_branch(id="B-1"), good_branch(id="B-2")],
        "requirements": REQUIREMENTS,
    }
    spec.update(overrides)
    return spec


class TestBraidAngle(unittest.TestCase):
    def test_angle_is_positive_and_below_a_right_angle(self):
        angle = braid_angle_rad(24, 0.40, 5.0, 0.127)
        self.assertGreater(angle, 0.0)
        self.assertLess(angle, math.pi / 2.0)

    def test_a_smaller_core_lays_the_braid_at_a_shallower_angle(self):
        wide = braid_angle_rad(24, 0.40, 5.0, 0.127)
        narrow = braid_angle_rad(24, 0.40, 3.0, 0.127)
        self.assertLess(narrow, wide)

    def test_more_carriers_lay_the_braid_at_a_shallower_angle(self):
        few = braid_angle_rad(16, 0.40, 5.0, 0.127)
        many = braid_angle_rad(48, 0.40, 5.0, 0.127)
        self.assertLess(many, few)

    def test_zero_carriers_raises(self):
        with self.assertRaises(ValueError):
            braid_angle_rad(0, 0.40, 5.0, 0.127)

    def test_non_integer_carriers_raises(self):
        with self.assertRaises(ValueError):
            braid_angle_rad(24.0, 0.40, 5.0, 0.127)


class TestFillingFactor(unittest.TestCase):
    def test_trunk_construction_fills_the_expected_fraction(self):
        angle = braid_angle_rad(24, 0.40, 5.0, 0.127)
        self.assertAlmostEqual(filling_factor(6, 0.127, 0.40, angle), 0.63229737937, places=9)

    def test_doubling_the_ends_doubles_the_fill(self):
        angle = braid_angle_rad(24, 0.40, 5.0, 0.127)
        self.assertAlmostEqual(
            filling_factor(12, 0.127, 0.40, angle),
            2.0 * filling_factor(6, 0.127, 0.40, angle),
            places=9,
        )

    def test_angle_at_zero_raises(self):
        with self.assertRaises(ValueError):
            filling_factor(6, 0.127, 0.40, 0.0)

    def test_angle_at_a_right_angle_raises(self):
        with self.assertRaises(ValueError):
            filling_factor(6, 0.127, 0.40, math.pi / 2.0)


class TestOpticalCoverage(unittest.TestCase):
    def test_full_fill_gives_full_coverage(self):
        self.assertAlmostEqual(optical_coverage(1.0), 1.0, places=9)

    def test_half_fill_gives_three_quarters_coverage(self):
        self.assertAlmostEqual(optical_coverage(0.5), 0.75, places=9)

    def test_coverage_rises_with_fill(self):
        self.assertLess(optical_coverage(0.4), optical_coverage(0.7))

    def test_fill_above_unity_raises(self):
        with self.assertRaises(ValueError):
            optical_coverage(1.26)

    def test_zero_fill_raises(self):
        with self.assertRaises(ValueError):
            optical_coverage(0.0)


class TestCoverageFromConstruction(unittest.TestCase):
    def test_trunk_coverage_is_computed(self):
        self.assertAlmostEqual(
            braid_coverage_from_construction(TRUNK)["optical_coverage"], 0.86479478278, places=9
        )

    def test_same_braid_over_a_smaller_core_covers_more(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        branch = braid_coverage_from_construction(branch_construction())["optical_coverage"]
        self.assertGreater(branch, trunk)

    def test_thinner_branch_braid_covers_less_than_the_trunk(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        thin = braid_coverage_from_construction(
            branch_construction(ends_per_carrier=3)
        )["optical_coverage"]
        self.assertLess(thin, trunk)

    def test_braid_angle_is_reported_in_degrees_too(self):
        geometry = braid_coverage_from_construction(TRUNK)
        self.assertAlmostEqual(
            geometry["braid_angle_deg"], math.degrees(geometry["braid_angle_rad"]), places=9
        )

    def test_missing_construction_key_raises(self):
        broken = dict(TRUNK)
        del broken["picks_per_mm"]
        with self.assertRaises(ValueError):
            braid_coverage_from_construction(broken)


class TestShieldResistance(unittest.TestCase):
    def test_path_resistance_adds_its_three_segments(self):
        self.assertAlmostEqual(
            branch_shield_resistance_ohm(0.0020, 0.0030, 0.0015), 0.0065, places=12
        )

    def test_a_perfect_junction_contributes_nothing(self):
        self.assertAlmostEqual(
            branch_shield_resistance_ohm(0.0020, 0.0, 0.0015), 0.0035, places=12
        )

    def test_negative_segment_raises(self):
        with self.assertRaises(ValueError):
            branch_shield_resistance_ohm(0.0020, -0.0010, 0.0015)

    def test_non_numeric_segment_raises(self):
        with self.assertRaises(ValueError):
            branch_shield_resistance_ohm("0.002", 0.0030, 0.0015)


class TestCoverageMeetsTrunk(unittest.TestCase):
    def test_branch_above_both_targets_passes(self):
        self.assertTrue(coverage_meets_trunk(0.99, 0.86, 0.80))

    def test_branch_exactly_on_the_trunk_coverage_passes(self):
        self.assertTrue(coverage_meets_trunk(0.86, 0.86, 0.80))

    def test_branch_exactly_on_the_floor_with_a_lower_trunk_passes(self):
        self.assertTrue(coverage_meets_trunk(0.80, 0.70, 0.80))

    def test_branch_below_the_trunk_fails_even_above_the_floor(self):
        self.assertFalse(coverage_meets_trunk(0.83, 0.86, 0.80))

    def test_branch_below_the_floor_fails(self):
        self.assertFalse(coverage_meets_trunk(0.72, 0.70, 0.80))

    def test_coverage_above_unity_raises(self):
        with self.assertRaises(ValueError):
            coverage_meets_trunk(1.4, 0.86, 0.80)


class TestExposedLength(unittest.TestCase):
    def test_short_exposure_is_acceptable(self):
        self.assertTrue(exposed_length_acceptable(12.0, 25.0))

    def test_exposure_exactly_on_the_limit_is_acceptable(self):
        self.assertTrue(exposed_length_acceptable(25.0, 25.0))

    def test_long_exposure_is_not_acceptable(self):
        self.assertFalse(exposed_length_acceptable(40.0, 25.0))

    def test_negative_exposure_raises(self):
        with self.assertRaises(ValueError):
            exposed_length_acceptable(-1.0, 25.0)


class TestEvaluateBranch(unittest.TestCase):
    def test_conforming_branch_has_no_finding(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        self.assertTrue(evaluate_branch(good_branch(), trunk, REQUIREMENTS)["conforming"])

    def test_thin_branch_braid_is_a_finding(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        branch = good_branch(construction=branch_construction(ends_per_carrier=3))
        self.assertFalse(evaluate_branch(branch, trunk, REQUIREMENTS)["conforming"])

    def test_high_junction_resistance_is_a_finding(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        branch = good_branch(junction_ohm=0.050)
        self.assertFalse(evaluate_branch(branch, trunk, REQUIREMENTS)["conforming"])

    def test_unbonded_junction_is_a_finding(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        self.assertFalse(
            evaluate_branch(good_branch(junction_bonded=False), trunk, REQUIREMENTS)["conforming"]
        )

    def test_long_unshielded_takeoff_is_a_finding(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        self.assertFalse(
            evaluate_branch(good_branch(exposed_length_mm=60.0), trunk, REQUIREMENTS)["conforming"]
        )

    def test_resistance_exactly_on_the_limit_is_accepted(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        branch = good_branch(trunk_ohm=0.004, junction_ohm=0.004, branch_ohm=0.002)
        result = evaluate_branch(branch, trunk, REQUIREMENTS)
        self.assertAlmostEqual(result["shield_resistance_ohm"], 0.010, places=12)
        self.assertTrue(result["conforming"])

    def test_missing_branch_key_raises(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        branch = good_branch()
        del branch["junction_ohm"]
        with self.assertRaises(ValueError):
            evaluate_branch(branch, trunk, REQUIREMENTS)

    def test_blank_branch_identifier_raises(self):
        trunk = braid_coverage_from_construction(TRUNK)["optical_coverage"]
        with self.assertRaises(ValueError):
            evaluate_branch(good_branch(id="  "), trunk, REQUIREMENTS)


class TestAssessBreakout(unittest.TestCase):
    def test_clean_breakout_is_compliant(self):
        report = assess_breakout(good_breakout())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["branch_count"], 2)

    def test_worst_branch_coverage_is_reported(self):
        spec = good_breakout(
            branches=[
                good_branch(id="B-1"),
                good_branch(id="B-2", construction=branch_construction(ends_per_carrier=3)),
            ]
        )
        report = assess_breakout(spec)
        self.assertAlmostEqual(report["worst_branch_coverage"], 0.72173418695, places=9)
        self.assertFalse(report["compliant"])

    def test_too_many_branches_at_one_point_is_a_finding(self):
        spec = good_breakout(
            branches=[good_branch(id="B-%d" % i) for i in range(1, 6)]
        )
        self.assertFalse(assess_breakout(spec)["compliant"])

    def test_duplicate_branch_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_breakout(good_breakout(branches=[good_branch(id="B-1"), good_branch(id="B-1")]))

    def test_empty_branch_list_raises(self):
        with self.assertRaises(ValueError):
            assess_breakout(good_breakout(branches=[]))

    def test_missing_trunk_construction_raises(self):
        spec = good_breakout()
        del spec["trunk_construction"]
        with self.assertRaises(ValueError):
            assess_breakout(spec)

    def test_trunk_geometry_is_carried_up(self):
        report = assess_breakout(good_breakout())
        self.assertAlmostEqual(report["trunk"]["optical_coverage"], 0.86479478278, places=9)


if __name__ == "__main__":
    unittest.main()
