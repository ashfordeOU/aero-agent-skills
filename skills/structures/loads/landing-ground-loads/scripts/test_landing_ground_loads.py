"""Contract test for landing-ground-loads (structures/loads).

Offline, deterministic, stdlib only. Run with:
    python3 scripts/test_landing_ground_loads.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from landing_ground_loads_logic import (  # noqa: E402
    G0,
    N_LEVEL_DEFAULT,
    braked_roll,
    landing_loads_summary,
    level_landing_reactions,
    one_wheel_reaction,
    static_reactions,
    tail_down_reaction,
    weight_force,
)

# Worked example: 60 000 kg transport, W = 588 399 N, a = 8 m, b = 2 m,
# limit load factor 2.5, braking friction 0.8, lateral offset 0.1 m,
# track 5.0 m.
MASS_KG = 60000.0
WEIGHT = weight_force(MASS_KG)
A = 8.0
B = 2.0
LF = N_LEVEL_DEFAULT
FRICTION = 0.8
OFFSET = 0.1
TRACK = 5.0

REL = 1e-6


def assert_rel(test, value, target, tol=REL):
    test.assertTrue(math.isclose(value, target, rel_tol=tol, abs_tol=0.0),
                    "%r != %r within rel tol %g" % (value, target, tol))


class TestWeightForce(unittest.TestCase):

    def test_weight_force_exact(self):
        assert_rel(self, WEIGHT, 588399.0, tol=1e-12)
        self.assertEqual(weight_force(1.0), G0)

    def test_weight_force_nonpositive_valueerror(self):
        for bad in (0.0, -1.0, -60000.0):
            with self.assertRaises(ValueError):
                weight_force(bad)


class TestStaticReactions(unittest.TestCase):

    def test_static_anchors(self):
        out = static_reactions(WEIGHT, A, B)
        assert_rel(self, out["nose_N"], 117679.8)
        assert_rel(self, out["main_N"], 470719.2)

    def test_static_exact_wb_over_wheelbase_identity(self):
        # R_nose = W * b / (a + b) exactly, R_main = W * a / (a + b).
        out = static_reactions(WEIGHT, A, B)
        assert_rel(self, out["nose_N"], WEIGHT * B / (A + B), tol=1e-9)
        assert_rel(self, out["main_N"], WEIGHT * A / (A + B), tol=1e-9)

    def test_static_sum_round_trip_identity(self):
        out = static_reactions(WEIGHT, A, B)
        assert_rel(self, out["nose_N"] + out["main_N"], WEIGHT, tol=1e-9)

    def test_static_balanced_geometry(self):
        # CG midway over the wheelbase splits the load equally.
        out = static_reactions(WEIGHT, 5.0, 5.0)
        assert_rel(self, out["nose_N"], WEIGHT / 2)
        assert_rel(self, out["main_N"], WEIGHT / 2)

    def test_static_nonphysical_valueerror(self):
        for bad in (0.0, -100.0):
            with self.assertRaises(ValueError):
                static_reactions(bad, A, B)
        for bad_a, bad_b in ((0.0, B), (-8.0, B), (A, 0.0), (A, -2.0)):
            with self.assertRaises(ValueError):
                static_reactions(WEIGHT, bad_a, bad_b)


class TestLevelLanding(unittest.TestCase):

    def test_level_anchors_within_bound(self):
        out = level_landing_reactions(WEIGHT, A, B)
        assert_rel(self, out["main_N"], 1176798.0)
        self.assertTrue(1.10e6 <= out["main_N"] <= 1.25e6,
                        "level main outside 1.10e6-1.25e6 N bound")
        assert_rel(self, out["nose_N"], 294199.5)

    def test_level_total_anchor(self):
        out = level_landing_reactions(WEIGHT, A, B)
        assert_rel(self, out["total_N"], WEIGHT * N_LEVEL_DEFAULT, tol=1e-9)
        assert_rel(self, out["nose_N"] + out["main_N"], out["total_N"],
                   tol=1e-9)

    def test_level_scaling_of_static(self):
        lv = level_landing_reactions(WEIGHT, A, B, load_factor=2.0)
        st = static_reactions(WEIGHT, A, B)
        assert_rel(self, lv["nose_N"], 2.0 * st["nose_N"], tol=1e-9)
        assert_rel(self, lv["main_N"], 2.0 * st["main_N"], tol=1e-9)

    def test_level_load_factor_nonpositive_valueerror(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                level_landing_reactions(WEIGHT, A, B, load_factor=bad)


class TestBrakedRoll(unittest.TestCase):

    def test_brake_force_anchor(self):
        assert_rel(self, braked_roll(WEIGHT, A, B, FRICTION)["brake_force_N"],
                   376575.36)

    def test_brake_deceleration_identity(self):
        # decel_g = friction * a / (a + b) = 0.8 * 0.8 = 0.64 exactly.
        out = braked_roll(WEIGHT, A, B, FRICTION)
        assert_rel(self, out["deceleration_g"],
                   FRICTION * A / (A + B), tol=1e-9)
        assert_rel(self, out["deceleration_g"], 0.64, tol=1e-9)

    def test_braked_roll_default_load_factor_is_one(self):
        out = braked_roll(WEIGHT, A, B, FRICTION)
        st = static_reactions(WEIGHT, A, B)
        assert_rel(self, out["main_reaction_N"], st["main_N"], tol=1e-9)

    def test_braked_roll_at_limit_load_factor(self):
        out = braked_roll(WEIGHT, A, B, FRICTION, load_factor=2.5)
        assert_rel(self, out["main_reaction_N"], 1176798.0)
        assert_rel(self, out["brake_force_N"], 941438.4)
        assert_rel(self, out["deceleration_g"], 1.6)

    def test_braked_roll_friction_bounds(self):
        zero = braked_roll(WEIGHT, A, B, 0.0)
        self.assertEqual(zero["brake_force_N"], 0.0)
        self.assertEqual(zero["deceleration_g"], 0.0)
        unit = braked_roll(WEIGHT, A, B, 1.0)
        assert_rel(self, unit["deceleration_g"], A / (A + B), tol=1e-9)
        assert_rel(self, unit["brake_force_N"], unit["main_reaction_N"],
                   tol=1e-9)

    def test_braked_roll_nonphysical_valueerror(self):
        for bad in (-0.1, 1.01, 2.0):
            with self.assertRaises(ValueError):
                braked_roll(WEIGHT, A, B, bad)
        for bad_lf in (0.0, -0.5):
            with self.assertRaises(ValueError):
                braked_roll(WEIGHT, A, B, FRICTION, load_factor=bad_lf)


class TestTailDown(unittest.TestCase):

    def test_tail_down_exact(self):
        out = tail_down_reaction(WEIGHT)
        assert_rel(self, out, WEIGHT * N_LEVEL_DEFAULT, tol=1e-9)
        assert_rel(self, out, 1470997.5)

    def test_tail_down_custom_load_factor(self):
        assert_rel(self, tail_down_reaction(WEIGHT, load_factor=1.0), WEIGHT,
                   tol=1e-9)

    def test_tail_down_nonpositive_valueerror(self):
        for bad_w in (0.0, -10.0):
            with self.assertRaises(ValueError):
                tail_down_reaction(bad_w)
        for bad_lf in (0.0, -2.5):
            with self.assertRaises(ValueError):
                tail_down_reaction(WEIGHT, load_factor=bad_lf)


class TestOneWheel(unittest.TestCase):

    def test_one_wheel_anchor_within_bound(self):
        out = one_wheel_reaction(WEIGHT, LF, OFFSET, TRACK)
        assert_rel(self, out, 764918.7)
        self.assertTrue(0.72e6 <= out <= 0.81e6,
                        "one wheel outside 0.72e6-0.81e6 N bound")

    def test_one_wheel_offset_zero_identity(self):
        # lateral_offset 0 gives weight * load_factor * 0.5 exactly.
        out = one_wheel_reaction(WEIGHT, LF, 0.0, TRACK)
        assert_rel(self, out, WEIGHT * LF * 0.5, tol=1e-9)

    def test_one_wheel_symmetric_level_landing(self):
        # At zero lateral offset each main gear carries half the total
        # level landing reaction.
        out = one_wheel_reaction(WEIGHT, LF, 0.0, TRACK)
        assert_rel(self, 2.0 * out, WEIGHT * LF, tol=1e-9)

    def test_one_wheel_offset_at_track_half_boundary(self):
        # offset == track / 2 is the valid limit (full load on one side).
        out = one_wheel_reaction(WEIGHT, LF, TRACK / 2, TRACK)
        assert_rel(self, out, WEIGHT * LF, tol=1e-9)

    def test_one_wheel_nonphysical_valueerror(self):
        for bad_track in (0.0, -5.0):
            with self.assertRaises(ValueError):
                one_wheel_reaction(WEIGHT, LF, OFFSET, bad_track)
        with self.assertRaises(ValueError):
            one_wheel_reaction(WEIGHT, LF, -0.01, TRACK)
        with self.assertRaises(ValueError):
            one_wheel_reaction(WEIGHT, LF, TRACK / 2 + 1e-9, TRACK)
        for bad_lf in (0.0, -1.0):
            with self.assertRaises(ValueError):
                one_wheel_reaction(WEIGHT, bad_lf, OFFSET, TRACK)


class TestSummary(unittest.TestCase):

    def test_summary_matches_component_functions(self):
        s = landing_loads_summary(WEIGHT, A, B)
        st = static_reactions(WEIGHT, A, B)
        lv = level_landing_reactions(WEIGHT, A, B)
        assert_rel(self, s["static_nose_N"], st["nose_N"], tol=1e-9)
        assert_rel(self, s["static_main_N"], st["main_N"], tol=1e-9)
        assert_rel(self, s["level_nose_N"], lv["nose_N"], tol=1e-9)
        assert_rel(self, s["level_main_N"], lv["main_N"], tol=1e-9)

    def test_summary_braked_roll_values(self):
        s = landing_loads_summary(WEIGHT, A, B)
        assert_rel(self, s["brake_force_N"], 376575.36)
        assert_rel(self, s["deceleration_g"], 0.64, tol=1e-9)

    def test_summary_critical_main_is_tail_down(self):
        s = landing_loads_summary(WEIGHT, A, B)
        assert_rel(self, s["tail_down_main_N"], 1470997.5, tol=1e-9)
        assert_rel(self, s["critical_main_N"], s["tail_down_main_N"],
                   tol=1e-9)
        self.assertGreaterEqual(s["critical_main_N"], s["level_main_N"])
        self.assertGreaterEqual(s["critical_main_N"], s["one_wheel_main_N"])

    def test_summary_critical_nose_is_level_nose(self):
        s = landing_loads_summary(WEIGHT, A, B)
        assert_rel(self, s["critical_nose_N"], s["level_nose_N"], tol=1e-9)
        self.assertGreaterEqual(s["critical_nose_N"], s["static_nose_N"])

    def test_summary_one_wheel_with_offset(self):
        s = landing_loads_summary(WEIGHT, A, B, lateral_offset=OFFSET,
                                  track=TRACK)
        assert_rel(self, s["one_wheel_main_N"], 764918.7)
        assert_rel(self, s["critical_main_N"], s["tail_down_main_N"],
                   tol=1e-9)

    def test_summary_propagates_valueerror(self):
        with self.assertRaises(ValueError):
            landing_loads_summary(0.0, A, B)
        with self.assertRaises(ValueError):
            landing_loads_summary(WEIGHT, A, B, load_factor=0.0)
        with self.assertRaises(ValueError):
            landing_loads_summary(WEIGHT, A, B, friction=1.5)

    def test_determinism(self):
        first = landing_loads_summary(WEIGHT, A, B)
        second = landing_loads_summary(WEIGHT, A, B)
        self.assertEqual(first, second)
        self.assertEqual(braked_roll(WEIGHT, A, B, FRICTION),
                         braked_roll(WEIGHT, A, B, FRICTION))


if __name__ == "__main__":
    unittest.main()
