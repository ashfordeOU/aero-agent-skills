"""Contract test for the landing gear retraction sizing module.

Offline, deterministic, stdlib unittest. Run from the repo root:

    python3 skills/vehicle-design/sizing/landing-gear-retraction-sizing/scripts/test_landing_gear_retraction_sizing.py

Covers the reference main gear worked example (moment 15400 N m,
actuator force 66000 N, link lengths 0.6513 / 0.1637 m, stroke
0.4876 m, lock reactions 19250 / 25666.7 N, stowage PASS), the
scaling identities, the law of cosines closed forms, ValueError
rejection of every non-physical input, and determinism.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from landing_gear_retraction_sizing_logic import (  # noqa: E402
    DESIGN_FACTOR_DEFAULT,
    LOCK_FACTOR_DEFAULT,
    actuator_force,
    actuator_stroke,
    link_length,
    lock_reaction,
    retraction_moment,
    retraction_summary,
    stowage_check,
)

# Reference main gear worked example (spec: landing-gear-retraction-sizing).
W = 14000.0        # gear weight N
CG = 1.10          # gear CG arm m ahead of the retract pivot
ARM = 0.35         # actuator attach arm m
A = 0.55           # fixed link a m
B = 0.40           # fixed link b m
DOWN_DEG = 85.0    # down-locked angle
UP_DEG = 8.0       # up-locked angle
DOWN_LOCK_ARM = 0.80
UP_LOCK_ARM = 0.60
WHEEL_D = 0.66
WHEEL_W = 0.22
STRUT = 2.80
BAY_L = 0.70
BAY_W = 0.30
BAY_D = 3.00

MOMENT = 15400.0        # 14000 * 1.10
FORCE = 66000.0         # 1.5 * 15400 / 0.35
DOWN_LINK = 0.6512691250097999
UP_LINK = 0.16365222196386173
STROKE = 0.4876169030459382
DOWN_RXN = 19250.0
UP_RXN = 25666.666666666668


class TestRetractionMoment(unittest.TestCase):
    def test_worked_example_and_keys(self):
        out = retraction_moment(W, CG)
        self.assertAlmostEqual(out["moment_nm"], MOMENT, delta=1e-6)
        self.assertAlmostEqual(out["cg_arm_m"], CG, delta=1e-12)
        self.assertEqual(sorted(out.keys()), ["cg_arm_m", "moment_nm"])

    def test_doubling_weight_doubles_moment(self):
        base = retraction_moment(W, CG)["moment_nm"]
        double = retraction_moment(2.0 * W, CG)["moment_nm"]
        self.assertAlmostEqual(double, 2.0 * base, delta=1e-6)

    def test_zero_weight_raises(self):
        with self.assertRaises(ValueError):
            retraction_moment(0.0, CG)

    def test_nonpositive_cg_arm_raises(self):
        with self.assertRaises(ValueError):
            retraction_moment(W, -1.0)
        with self.assertRaises(ValueError):
            retraction_moment(W, 0.0)


class TestActuatorForce(unittest.TestCase):
    def test_worked_example_and_keys(self):
        out = actuator_force(MOMENT, ARM)
        self.assertAlmostEqual(out["force_n"], FORCE, delta=1e-6)
        self.assertAlmostEqual(out["moment_nm"], MOMENT, delta=1e-9)
        self.assertAlmostEqual(out["actuator_arm_m"], ARM, delta=1e-12)
        self.assertEqual(sorted(out.keys()),
                         ["actuator_arm_m", "force_n", "moment_nm"])
        self.assertEqual(actuator_force(MOMENT, ARM, 1.5)["force_n"],
                         actuator_force(MOMENT, ARM)["force_n"])

    def test_doubling_design_factor_doubles_force(self):
        base = actuator_force(MOMENT, ARM, DESIGN_FACTOR_DEFAULT)
        double = actuator_force(MOMENT, ARM, 2.0 * DESIGN_FACTOR_DEFAULT)
        self.assertAlmostEqual(double["force_n"], 2.0 * base["force_n"],
                               delta=1e-6)

    def test_doubling_arm_halves_force(self):
        half_arm = actuator_force(MOMENT, 0.5 * ARM)
        full_arm = actuator_force(MOMENT, ARM)
        self.assertAlmostEqual(half_arm["force_n"], 2.0 * full_arm["force_n"],
                               delta=1e-6)

    def test_nonpositive_moment_raises(self):
        with self.assertRaises(ValueError):
            actuator_force(0.0, ARM)
        with self.assertRaises(ValueError):
            actuator_force(-MOMENT, ARM)

    def test_nonpositive_arm_raises(self):
        with self.assertRaises(ValueError):
            actuator_force(MOMENT, 0.0)
        with self.assertRaises(ValueError):
            actuator_force(MOMENT, -0.2)

    def test_design_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            actuator_force(MOMENT, ARM, 0.9)
        with self.assertRaises(ValueError):
            actuator_force(MOMENT, ARM, 1.0 - 1e-9)


class TestLinkLength(unittest.TestCase):
    def test_equilateral_60_degrees(self):
        self.assertAlmostEqual(link_length(1.0, 1.0, 60.0), 1.0, delta=1e-10)

    def test_90_degrees_sqrt2(self):
        self.assertAlmostEqual(link_length(1.0, 1.0, 90.0),
                               math.sqrt(2.0), delta=1e-9)

    def test_worked_example_down_85(self):
        self.assertAlmostEqual(link_length(A, B, DOWN_DEG), DOWN_LINK,
                               delta=1e-9)
        # Spec magnitude bound: 0.6513 m.
        self.assertLess(abs(link_length(A, B, DOWN_DEG) - 0.6513), 5e-4)

    def test_worked_example_up_8(self):
        self.assertAlmostEqual(link_length(A, B, UP_DEG), UP_LINK,
                               delta=1e-9)
        # Spec magnitude bound: 0.1637 m.
        self.assertLess(abs(link_length(A, B, UP_DEG) - 0.1637), 5e-4)

    def test_cos_even_identity(self):
        # link_length at theta equals the law-of-cosines value at -theta
        # (cosine is even); the module guards negative angles, so the
        # closed form is evaluated with the mirrored cosine directly.
        theta = 85.0
        closed = math.sqrt(A ** 2 + B ** 2
                           - 2.0 * A * B * math.cos(math.radians(-theta)))
        self.assertAlmostEqual(link_length(A, B, theta), closed, delta=1e-12)
        self.assertEqual(math.cos(math.radians(theta)),
                         math.cos(math.radians(-theta)))

    def test_invalid_links_raise(self):
        with self.assertRaises(ValueError):
            link_length(0.0, B, 45.0)
        with self.assertRaises(ValueError):
            link_length(A, -B, 45.0)

    def test_invalid_angles_raise(self):
        for bad in (0.0, 180.0, -10.0, 200.0):
            with self.assertRaises(ValueError):
                link_length(A, B, bad)


class TestActuatorStroke(unittest.TestCase):
    def test_worked_example_and_keys(self):
        out = actuator_stroke(A, B, DOWN_DEG, UP_DEG)
        self.assertAlmostEqual(out["down_link_m"], DOWN_LINK, delta=1e-9)
        self.assertAlmostEqual(out["up_link_m"], UP_LINK, delta=1e-9)
        self.assertAlmostEqual(out["stroke_m"], STROKE, delta=1e-9)
        self.assertEqual(sorted(out.keys()),
                         ["down_link_m", "stroke_m", "up_link_m"])
        # Spec magnitude bound: about 0.4876 m (488 mm).
        self.assertLess(abs(out["stroke_m"] - 0.4876), 5e-4)

    def test_sign_guard_down_smaller_than_up_raises(self):
        # Down angle 8 deg smaller than up angle 85 deg: the up-lock
        # geometry is longer than the down-lock geometry, so the
        # actuator cannot retract the gear.
        with self.assertRaisesRegex(ValueError, "up-lock not reachable"):
            actuator_stroke(A, B, 8.0, 85.0)

    def test_zero_stroke_raises(self):
        # Identical down and up geometry gives a zero stroke.
        with self.assertRaises(ValueError):
            actuator_stroke(A, B, 45.0, 45.0)

    def test_greater_spread_gives_longer_stroke(self):
        narrow = actuator_stroke(A, B, 90.0, 45.0)["stroke_m"]
        wide = actuator_stroke(A, B, 120.0, 20.0)["stroke_m"]
        self.assertGreater(wide, narrow)


class TestLockReaction(unittest.TestCase):
    def test_down_lock_worked_example(self):
        out = lock_reaction(MOMENT, DOWN_LOCK_ARM)
        self.assertAlmostEqual(out["reaction_n"], DOWN_RXN, delta=1e-6)
        self.assertAlmostEqual(out["lock_arm_m"], DOWN_LOCK_ARM, delta=1e-12)

    def test_up_lock_worked_example(self):
        out = lock_reaction(MOMENT, UP_LOCK_ARM, LOCK_FACTOR_DEFAULT)
        self.assertAlmostEqual(out["reaction_n"], UP_RXN, delta=1e-9)
        # Spec magnitude bound: 25666.7 N.
        self.assertLess(abs(out["reaction_n"] - 25666.7), 0.05)

    def test_inversely_proportional_to_arm(self):
        long_arm = lock_reaction(MOMENT, 2.0 * UP_LOCK_ARM)
        short_arm = lock_reaction(MOMENT, UP_LOCK_ARM)
        self.assertAlmostEqual(long_arm["reaction_n"],
                               0.5 * short_arm["reaction_n"], delta=1e-6)

    def test_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            lock_reaction(0.0, UP_LOCK_ARM)
        with self.assertRaises(ValueError):
            lock_reaction(MOMENT, 0.0)
        with self.assertRaises(ValueError):
            lock_reaction(MOMENT, -0.5)
        with self.assertRaises(ValueError):
            lock_reaction(MOMENT, UP_LOCK_ARM, 0.0)

    def test_dict_keys_exact(self):
        out = lock_reaction(MOMENT, DOWN_LOCK_ARM)
        self.assertEqual(sorted(out.keys()), ["lock_arm_m", "reaction_n"])


class TestStowageCheck(unittest.TestCase):
    def test_nominal_pass(self):
        out = stowage_check(WHEEL_D, WHEEL_W, STRUT, BAY_L, BAY_W, BAY_D)
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["reasons"], [])
        self.assertEqual(sorted(out.keys()), ["reasons", "verdict"])

    def test_oversize_wheel_fails(self):
        out = stowage_check(0.75, WHEEL_W, STRUT, BAY_L, BAY_W, BAY_D)
        self.assertEqual(out["verdict"], "FAIL")
        self.assertEqual(len(out["reasons"]), 1)
        self.assertIn("wheel_diameter", out["reasons"][0])

    def test_oversize_wheel_and_strut_fail_two_reasons(self):
        out = stowage_check(0.75, WHEEL_W, 3.10, BAY_L, BAY_W, BAY_D)
        self.assertEqual(out["verdict"], "FAIL")
        self.assertEqual(len(out["reasons"]), 2)

    def test_oversize_width_fails(self):
        out = stowage_check(WHEEL_D, 0.35, STRUT, BAY_L, BAY_W, BAY_D)
        self.assertEqual(out["verdict"], "FAIL")
        self.assertEqual(len(out["reasons"]), 1)
        self.assertIn("wheel_width", out["reasons"][0])

    def test_nonpositive_dimensions_raise(self):
        with self.assertRaises(ValueError):
            stowage_check(0.0, WHEEL_W, STRUT, BAY_L, BAY_W, BAY_D)
        with self.assertRaises(ValueError):
            stowage_check(WHEEL_D, -WHEEL_W, STRUT, BAY_L, BAY_W, BAY_D)
        with self.assertRaises(ValueError):
            stowage_check(WHEEL_D, WHEEL_W, STRUT, 0.0, BAY_W, BAY_D)
        with self.assertRaises(ValueError):
            stowage_check(WHEEL_D, WHEEL_W, STRUT, BAY_L, BAY_W, -3.0)


class TestRetractionSummary(unittest.TestCase):
    SUMMARY_KEYS = [
        "a_m", "actuator_arm_m", "b_m", "cg_arm_m", "design_factor",
        "down_angle_deg", "down_link_m", "down_lock_arm_m",
        "down_lock_reaction_n", "force_n", "moment_nm", "stroke_m",
        "stowage", "up_angle_deg", "up_link_m", "up_lock_arm_m",
        "up_lock_reaction_n",
    ]

    def _summary(self, design_factor=DESIGN_FACTOR_DEFAULT):
        return retraction_summary(
            W, CG, ARM, A, B, DOWN_DEG, UP_DEG,
            DOWN_LOCK_ARM, UP_LOCK_ARM,
            WHEEL_D, WHEEL_W, STRUT, BAY_L, BAY_W, BAY_D,
            design_factor)

    def test_worked_example_values(self):
        s = self._summary()
        self.assertAlmostEqual(s["moment_nm"], MOMENT, delta=1e-6)
        self.assertAlmostEqual(s["force_n"], FORCE, delta=1e-6)
        self.assertAlmostEqual(s["stroke_m"], STROKE, delta=1e-9)
        self.assertAlmostEqual(s["down_link_m"], DOWN_LINK, delta=1e-9)
        self.assertAlmostEqual(s["up_link_m"], UP_LINK, delta=1e-9)
        self.assertAlmostEqual(s["down_lock_reaction_n"], DOWN_RXN,
                               delta=1e-6)
        self.assertAlmostEqual(s["up_lock_reaction_n"], UP_RXN, delta=1e-9)
        self.assertEqual(s["stowage"]["verdict"], "PASS")
        self.assertEqual(s["stowage"]["reasons"], [])

    def test_summary_keys_exact(self):
        s = self._summary()
        self.assertEqual(sorted(s.keys()), sorted(self.SUMMARY_KEYS))
        self.assertEqual(sorted(s["stowage"].keys()), ["reasons", "verdict"])

    def test_custom_design_factor_flows_through(self):
        s = self._summary(design_factor=2.0)
        self.assertAlmostEqual(s["force_n"], 2.0 * MOMENT / ARM, delta=1e-6)
        self.assertEqual(s["design_factor"], 2.0)

    def test_determinism_identical_inputs(self):
        first = self._summary()
        second = self._summary()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
