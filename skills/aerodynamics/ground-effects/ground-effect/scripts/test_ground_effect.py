#!/usr/bin/env python3
"""Gate 3 contract test: ground effect aerodynamics.

Exercises scripts/ground_effect_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - image vortex induced
drag reduction factor sigma = 1 / (1 + 16 * (h / b)^2) with drag
ratio 1 - sigma, effective aspect ratio AR / (1 - sigma), induced
drag in ground effect scaled by the ratio, lift curve slope
a_inf / (1 + a_inf * (1 - sigma) / (pi * AR)) tending to the 2D
slope near the ground, and image vortex offset 2 * h, with
ValueError on non-positive inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ground_effect_logic as ge  # noqa: E402


class GroundEffectFactorTest(unittest.TestCase):
    def test_known_values(self):
        # sigma = 1 / (1 + 16 * (h/b)^2)
        self.assertAlmostEqual(ge.ground_effect_factor(0.25), 0.5, delta=1e-9)
        self.assertAlmostEqual(ge.ground_effect_factor(0.5), 0.2, delta=1e-9)
        self.assertAlmostEqual(ge.ground_effect_factor(1.0), 1.0 / 17.0, delta=1e-9)

    def test_drag_reduction_grows_as_hb_shrinks(self):
        # sigma is the reduction; it must grow as h/b shrinks
        s_small = ge.ground_effect_factor(0.1)
        s_mid = ge.ground_effect_factor(0.5)
        s_large = ge.ground_effect_factor(2.0)
        self.assertGreater(s_small, s_mid)
        self.assertGreater(s_mid, s_large)

    def test_limits(self):
        # near the ground the reduction saturates at 1, far away it vanishes
        self.assertAlmostEqual(ge.ground_effect_factor(1e-9), 1.0, delta=1e-6)
        self.assertAlmostEqual(ge.ground_effect_factor(1e9), 0.0, delta=1e-9)

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            ge.ground_effect_factor(0.0)
        with self.assertRaises(ValueError):
            ge.ground_effect_factor(-0.5)


class InducedDragRatioTest(unittest.TestCase):
    def test_ratio_is_one_minus_sigma(self):
        for hb in (0.1, 0.25, 0.5, 1.0, 3.0):
            self.assertAlmostEqual(
                ge.induced_drag_ratio(hb),
                1.0 - ge.ground_effect_factor(hb),
                delta=1e-12,
            )

    def test_known_values(self):
        # 16 * (h/b)^2 / (1 + 16 * (h/b)^2)
        self.assertAlmostEqual(ge.induced_drag_ratio(0.25), 0.5, delta=1e-9)
        self.assertAlmostEqual(ge.induced_drag_ratio(0.5), 0.8, delta=1e-9)
        self.assertAlmostEqual(ge.induced_drag_ratio(1.0), 16.0 / 17.0, delta=1e-9)

    def test_ratio_monotone_in_hb(self):
        # drag ratio grows as the wing climbs: less reduction higher up
        self.assertLess(ge.induced_drag_ratio(0.1), ge.induced_drag_ratio(0.5))
        self.assertLess(ge.induced_drag_ratio(0.5), ge.induced_drag_ratio(2.0))

    def test_limits(self):
        self.assertAlmostEqual(ge.induced_drag_ratio(1e-9), 0.0, delta=1e-6)
        self.assertAlmostEqual(ge.induced_drag_ratio(1e9), 1.0, delta=1e-9)


class EffectiveAspectRatioTest(unittest.TestCase):
    def test_known_value(self):
        # AR / (1 - sigma) with sigma = 0.2 at h/b = 0.5 -> AR / 0.8
        self.assertAlmostEqual(ge.effective_aspect_ratio(0.5, 8.0), 10.0, delta=1e-9)

    def test_far_from_ground_tends_to_ar(self):
        self.assertAlmostEqual(ge.effective_aspect_ratio(1e6, 8.0), 8.0, delta=1e-6)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ge.effective_aspect_ratio(0.0, 8.0)
        with self.assertRaises(ValueError):
            ge.effective_aspect_ratio(0.5, 0.0)
        with self.assertRaises(ValueError):
            ge.effective_aspect_ratio(0.5, -2.0)


class InducedDragTest(unittest.TestCase):
    def test_ground_drag_below_free_air(self):
        # C_L 0.5, AR 8, q 1000 Pa, S 16 m^2, e 0.85, h/b 0.5
        d_free = 1000.0 * 16.0 * 0.25 / (3.141592653589793 * 0.85 * 8.0)
        d_g = ge.induced_drag(0.5, 0.5, 8.0, 1000.0, 16.0, e=0.85)
        self.assertLess(d_g, d_free)
        self.assertAlmostEqual(d_g, d_free * ge.induced_drag_ratio(0.5), delta=1e-9)

    def test_reduction_scales_with_hb(self):
        d_near = ge.induced_drag(0.1, 0.5, 8.0, 1000.0, 16.0)
        d_far = ge.induced_drag(3.0, 0.5, 8.0, 1000.0, 16.0)
        self.assertLess(d_near, d_far)

    def test_symmetric_negative_cl(self):
        d_pos = ge.induced_drag(0.5, 0.4, 8.0, 1000.0, 16.0)
        d_neg = ge.induced_drag(0.5, -0.4, 8.0, 1000.0, 16.0)
        self.assertAlmostEqual(d_pos, d_neg, delta=1e-12)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ge.induced_drag(0.0, 0.5, 8.0, 1000.0, 16.0)
        with self.assertRaises(ValueError):
            ge.induced_drag(0.5, 0.5, 0.0, 1000.0, 16.0)
        with self.assertRaises(ValueError):
            ge.induced_drag(0.5, 0.5, 8.0, -100.0, 16.0)
        with self.assertRaises(ValueError):
            ge.induced_drag(0.5, 0.5, 8.0, 1000.0, -1.0)
        with self.assertRaises(ValueError):
            ge.induced_drag(0.5, 0.5, 8.0, 1000.0, 16.0, e=0.0)
        with self.assertRaises(ValueError):
            ge.induced_drag(0.5, 0.5, 8.0, 1000.0, 16.0, e=1.5)


class LiftCurveSlopeTest(unittest.TestCase):
    def test_ground_slope_between_free_air_and_2d(self):
        a_free = ge.lift_curve_slope_free(6.0)
        a_g = ge.lift_curve_slope_ground(0.5, 6.0)
        self.assertGreater(a_g, a_free)
        self.assertLess(a_g, 2.0 * 3.141592653589793)

    def test_near_ground_tends_to_2d_slope(self):
        self.assertAlmostEqual(
            ge.lift_curve_slope_ground(1e-6, 6.0),
            2.0 * 3.141592653589793,
            delta=1e-3,
        )

    def test_far_from_ground_matches_free_air(self):
        self.assertAlmostEqual(
            ge.lift_curve_slope_ground(1e6, 6.0),
            ge.lift_curve_slope_free(6.0),
            delta=1e-6,
        )

    def test_lift_increase_factor_above_one_and_monotone(self):
        self.assertGreater(ge.lift_increase_factor(0.25, 6.0), 1.0)
        self.assertGreater(
            ge.lift_increase_factor(0.1, 6.0), ge.lift_increase_factor(0.5, 6.0)
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ge.lift_curve_slope_ground(0.0, 6.0)
        with self.assertRaises(ValueError):
            ge.lift_curve_slope_ground(0.5, -6.0)
        with self.assertRaises(ValueError):
            ge.lift_curve_slope_ground(0.5, 6.0, a_inf=0.0)


class ImageVortexOffsetTest(unittest.TestCase):
    def test_offset_is_twice_height(self):
        self.assertAlmostEqual(ge.image_vortex_offset(3.0), 6.0, delta=1e-12)
        self.assertAlmostEqual(ge.image_vortex_offset(0.25), 0.5, delta=1e-12)

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            ge.image_vortex_offset(0.0)
        with self.assertRaises(ValueError):
            ge.image_vortex_offset(-1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
