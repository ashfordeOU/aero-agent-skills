#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-09C §5.4.7 coordinate system
parameterisation.

Exercises scripts/e1009_parameterisation_logic.py (stdlib unittest,
offline). Contract: geometry categorization accepts cartesian, spherical,
and cylindrical and rejects unknown strings; the right-hand rule passes
a standard xyz triad and rejects a left-hand triad and a degenerate
zero-length axis; spherical range validation catches negative r, theta
outside [0, pi], and phi outside [0, 2*pi); cylindrical range
validation catches negative rho and phi outside [0, 2*pi); cartesian
range validation catches non-finite coordinates; origin violation
detection flags missing and non-numeric components; orientation-
convention checking flags an absent or empty convention string; the
aggregate review correctly combines all violation lists; and
is_parameterisation_valid returns true only when all lists are empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1009_parameterisation_logic as pm  # noqa: E402


class CategorizeCSGeometryTest(unittest.TestCase):
    def test_cartesian_accepted(self):
        self.assertEqual(pm.categorize_cs_geometry("cartesian"), "cartesian")

    def test_spherical_accepted(self):
        self.assertEqual(pm.categorize_cs_geometry("spherical"), "spherical")

    def test_cylindrical_accepted(self):
        self.assertEqual(pm.categorize_cs_geometry("cylindrical"), "cylindrical")

    def test_unknown_geometry_raises(self):
        with self.assertRaises(ValueError):
            pm.categorize_cs_geometry("polar_2d")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            pm.categorize_cs_geometry("")


class RightHandRuleTest(unittest.TestCase):
    def test_standard_xyz_triad_passes(self):
        self.assertTrue(
            pm.check_right_hand_rule([1, 0, 0], [0, 1, 0], [0, 0, 1])
        )

    def test_left_hand_triad_fails(self):
        # x cross y = (0,0,1) but z is (0,0,-1) — left-hand
        self.assertFalse(
            pm.check_right_hand_rule([1, 0, 0], [0, 1, 0], [0, 0, -1])
        )

    def test_permuted_right_hand_triad_passes(self):
        # y cross z = x  →  (0,1,0) × (0,0,1) = (1,0,0)
        self.assertTrue(
            pm.check_right_hand_rule([0, 1, 0], [0, 0, 1], [1, 0, 0])
        )

    def test_degenerate_zero_z_axis_fails(self):
        self.assertFalse(
            pm.check_right_hand_rule([1, 0, 0], [0, 1, 0], [0, 0, 0])
        )

    def test_degenerate_zero_x_axis_fails(self):
        self.assertFalse(
            pm.check_right_hand_rule([0, 0, 0], [0, 1, 0], [0, 0, 1])
        )


class SphericalRangeTest(unittest.TestCase):
    def test_valid_spherical_no_issues(self):
        self.assertEqual(pm.validate_spherical_ranges(1.0, math.pi / 2, math.pi), [])

    def test_zero_r_is_valid(self):
        self.assertEqual(pm.validate_spherical_ranges(0.0, 0.0, 0.0), [])

    def test_negative_r_flagged(self):
        issues = pm.validate_spherical_ranges(-1.0, 0.0, 0.0)
        self.assertTrue(any("r" in i for i in issues))

    def test_theta_above_pi_flagged(self):
        issues = pm.validate_spherical_ranges(1.0, math.pi + 0.01, 0.0)
        self.assertTrue(any("theta" in i for i in issues))

    def test_theta_at_pi_is_valid(self):
        self.assertEqual(
            pm.validate_spherical_ranges(1.0, math.pi, math.pi), []
        )

    def test_phi_negative_flagged(self):
        issues = pm.validate_spherical_ranges(1.0, 0.0, -0.1)
        self.assertTrue(any("phi" in i for i in issues))

    def test_phi_at_2pi_flagged(self):
        issues = pm.validate_spherical_ranges(1.0, 0.0, 2 * math.pi)
        self.assertTrue(any("phi" in i for i in issues))

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            pm.validate_spherical_ranges("not_a_number", 0.0, 0.0)


class CylindricalRangeTest(unittest.TestCase):
    def test_valid_cylindrical_no_issues(self):
        self.assertEqual(pm.validate_cylindrical_ranges(2.0, math.pi, 0.0), [])

    def test_negative_rho_flagged(self):
        issues = pm.validate_cylindrical_ranges(-0.5, 0.0, 0.0)
        self.assertTrue(any("rho" in i for i in issues))

    def test_phi_at_2pi_flagged(self):
        issues = pm.validate_cylindrical_ranges(1.0, 2 * math.pi, 0.0)
        self.assertTrue(any("phi" in i for i in issues))

    def test_z_unconstrained_negative_valid(self):
        self.assertEqual(pm.validate_cylindrical_ranges(1.0, 0.0, -1e9), [])

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            pm.validate_cylindrical_ranges(None, 0.0, 0.0)


class CartesianRangeTest(unittest.TestCase):
    def test_finite_coords_no_issues(self):
        self.assertEqual(pm.validate_cartesian_ranges(1.0, -2.5, 0.0), [])

    def test_inf_x_flagged(self):
        issues = pm.validate_cartesian_ranges(float("inf"), 0.0, 0.0)
        self.assertTrue(any("x" in i for i in issues))

    def test_nan_y_flagged(self):
        issues = pm.validate_cartesian_ranges(0.0, float("nan"), 0.0)
        self.assertTrue(any("y" in i for i in issues))


class OriginViolationsTest(unittest.TestCase):
    def test_complete_numeric_origin_no_violation(self):
        self.assertEqual(
            pm.origin_violations("cs-1", {"x": 0.0, "y": 1.0, "z": -2.0}), []
        )

    def test_missing_y_component_flagged(self):
        violations = pm.origin_violations("cs-1", {"x": 0.0, "z": 0.0})
        self.assertTrue(
            any(v["issue"] == "origin_component_missing" and v["component"] == "y"
                for v in violations)
        )

    def test_non_numeric_component_flagged(self):
        violations = pm.origin_violations("cs-1", {"x": "bad", "y": 0.0, "z": 0.0})
        self.assertTrue(
            any(v["issue"] == "origin_component_non_numeric" for v in violations)
        )

    def test_non_dict_origin_flagged(self):
        violations = pm.origin_violations("cs-1", None)
        self.assertTrue(any(v["issue"] == "origin_not_a_dict" for v in violations))

    def test_non_finite_component_flagged(self):
        violations = pm.origin_violations("cs-1", {"x": float("inf"), "y": 0.0, "z": 0.0})
        self.assertTrue(
            any(v["issue"] == "origin_component_non_finite" for v in violations)
        )


class OrientationConventionTest(unittest.TestCase):
    def test_documented_convention_no_violation(self):
        self.assertEqual(
            pm.orientation_convention_violations("cs-1", "ECI"), []
        )

    def test_none_convention_flagged(self):
        violations = pm.orientation_convention_violations("cs-1", None)
        self.assertEqual(
            violations,
            [{"issue": "orientation_convention_undocumented", "cs_id": "cs-1"}],
        )

    def test_empty_string_convention_flagged(self):
        violations = pm.orientation_convention_violations("cs-1", "")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "orientation_convention_undocumented")


class ParameteriseReviewTest(unittest.TestCase):
    def _valid_cartesian(self, cs_id="frame-1"):
        return {
            "cs_id": cs_id,
            "geometry": "cartesian",
            "origin": {"x": 0.0, "y": 0.0, "z": 0.0},
            "orientation_convention": "body-fixed",
            "x_axis": [1.0, 0.0, 0.0],
            "y_axis": [0.0, 1.0, 0.0],
            "z_axis": [0.0, 0.0, 1.0],
        }

    def test_fully_valid_cartesian_review(self):
        review = pm.parameterise_review(self._valid_cartesian())
        self.assertEqual(review, {"origin": [], "axes": [], "convention": []})
        self.assertTrue(pm.is_parameterisation_valid(review))

    def test_unknown_geometry_raises(self):
        bad = self._valid_cartesian()
        bad["geometry"] = "toroidal"
        with self.assertRaises(ValueError):
            pm.parameterise_review(bad)

    def test_missing_convention_flagged_in_review(self):
        cs = self._valid_cartesian()
        cs["orientation_convention"] = None
        review = pm.parameterise_review(cs)
        self.assertTrue(len(review["convention"]) == 1)
        self.assertFalse(pm.is_parameterisation_valid(review))

    def test_left_hand_axes_flagged_in_review(self):
        cs = self._valid_cartesian()
        cs["z_axis"] = [0.0, 0.0, -1.0]  # left-hand
        review = pm.parameterise_review(cs)
        self.assertTrue(len(review["axes"]) == 1)
        self.assertEqual(review["axes"][0]["issue"], "axes_not_right_hand_triad")
        self.assertFalse(pm.is_parameterisation_valid(review))

    def test_missing_origin_component_flagged_in_review(self):
        cs = self._valid_cartesian()
        cs["origin"] = {"x": 0.0}  # missing y and z
        review = pm.parameterise_review(cs)
        self.assertEqual(len(review["origin"]), 2)
        self.assertFalse(pm.is_parameterisation_valid(review))

    def test_spherical_geometry_no_axes_check(self):
        cs = {
            "cs_id": "sph-1",
            "geometry": "spherical",
            "origin": {"x": 0.0, "y": 0.0, "z": 0.0},
            "orientation_convention": "ECI",
        }
        review = pm.parameterise_review(cs)
        self.assertEqual(review["axes"], [])
        self.assertTrue(pm.is_parameterisation_valid(review))

    def test_is_parameterisation_valid_false_on_multiple_violations(self):
        cs = self._valid_cartesian()
        cs["orientation_convention"] = None
        cs["origin"] = {}  # all components missing
        review = pm.parameterise_review(cs)
        self.assertFalse(pm.is_parameterisation_valid(review))
        self.assertEqual(len(review["origin"]), 3)
        self.assertEqual(len(review["convention"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
