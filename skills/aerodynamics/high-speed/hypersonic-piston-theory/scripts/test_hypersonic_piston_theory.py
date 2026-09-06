#!/usr/bin/env python3
"""Gate 3 contract test: hypersonic-piston-theory (Lighthill piston theory).

Exercises scripts/hypersonic_piston_theory_logic.py (stdlib unittest,
offline, deterministic). Contract: the piston-theory pressure ratio
p/p_inf = (1 + ((gamma - 1)/2) * (v/a_inf))^(2 gamma/(gamma - 1)) from
the local piston velocity ratio, its linearized limit 1 + gamma*v/a_inf,
the piston velocity ratio M*sin(theta) of a steady inclined surface, the
per-side surface-pressure coefficient Cp = 2/(gamma M^2)*(p/p_inf - 1)
with the linearized limit 2*sin(theta)/M, and the unsteady composition
of a moving surface whose normal wall motion adds to the geometric
piston velocity. The methods exercise the numbered steps of the
SKILL.md workflow: the operating-point read, the piston-velocity-ratio
traverse, the piston-theory pressure ratio evaluation, the linearized
limit pass, the compression-expansion split, the per-side coefficient
step, and the unsteady surface composition at each phase of the wall
motion. Worked anchors (spec, real prep outputs): law table
1.948717100000 at v/a 0.5, cutoff zero at -5.0, surface A (M 6, theta
5 deg) compression 2.006315343379 vs expansion 0.461491957246, surface
B (M 8, theta 10 deg) 5.563247915155 vs 0.102434506727, unsteady
inward 2.274841372010 and retreat 1.765429818550. Non-physical inputs
(gamma <= 1, mach <= 1, theta outside [0, 90), ratio below the cutoff,
bad side or direction) raise ValueError. Deterministic, no RNG.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hypersonic_piston_theory_logic as hpt  # noqa: E402


class PistonLawTest(unittest.TestCase):
    def test_neutral_ratio_is_one(self):
        # Step 3 of the SKILL.md workflow, the piston-theory pressure
        # ratio evaluation: a zero piston velocity ratio (aligned
        # surface) returns p/p_inf = 1.0 exactly.
        self.assertAlmostEqual(hpt.piston_pressure_ratio(0.0), 1.0, delta=1e-12)

    def test_compression_side_law_anchors(self):
        # Step 3 of the SKILL.md workflow: the compression side of the
        # law table at gamma 1.4, every value above 1.
        anchors = {0.05: 1.072135352107, 0.2: 1.315931779236,
                   0.5: 1.948717100000, 0.8: 2.826219734467,
                   1.5: 6.274851700000}
        for v_a, expected in anchors.items():
            self.assertAlmostEqual(hpt.piston_pressure_ratio(v_a),
                                   expected, delta=1e-5)

    def test_expansion_side_law_anchors(self):
        # Step 3 of the SKILL.md workflow: the expansion side of the law
        # table at gamma 1.4, every value between 0 and 1.
        anchors = {-0.05: 0.932065347907, -0.2: 0.751447478108,
                   -0.5: 0.478296900000, -0.8: 0.295090346557,
                   -1.5: 0.082354300000}
        for v_a, expected in anchors.items():
            self.assertAlmostEqual(hpt.piston_pressure_ratio(v_a),
                                   expected, delta=1e-5)

    def test_law_strictly_increasing_across_sides(self):
        # Step 3 of the SKILL.md workflow: the law is strictly
        # increasing in the piston velocity ratio across both sides.
        ratios = [hpt.piston_pressure_ratio(v)
                  for v in (-1.5, -1.0, -0.5, -0.2, -0.05, 0.0,
                            0.05, 0.2, 0.5, 1.0, 1.5)]
        for lower, upper in zip(ratios, ratios[1:]):
            self.assertGreater(upper, lower)

    def test_expansion_cutoff_is_exact_vacuum(self):
        # Step 3 of the SKILL.md workflow: at the expansion cutoff
        # v/a = -2/(gamma - 1) = -5.0 the base is exactly zero and the
        # law returns p/p_inf = 0.0, the vacuum state.
        self.assertAlmostEqual(hpt.piston_pressure_ratio(-5.0), 0.0,
                               delta=1e-12)

    def test_below_cutoff_raises_value_error(self):
        # Step 3 of the SKILL.md workflow: a piston velocity ratio below
        # the expansion cutoff is fully expanded and raises ValueError.
        with self.assertRaises(ValueError):
            hpt.piston_pressure_ratio(-5.5)

    def test_gamma_at_or_below_one_raises_everywhere(self):
        # Step 1 of the SKILL.md workflow, the operating-point read:
        # gamma must exceed 1 in the law, the linearized limit and both
        # surface functions.
        for fn in (hpt.piston_pressure_ratio, hpt.linear_pressure_ratio):
            with self.assertRaises(ValueError):
                fn(0.5, gamma=1.0)
            with self.assertRaises(ValueError):
                fn(0.5, gamma=0.9)
        for fn in (hpt.surface_pressure_ratio,
                   hpt.surface_pressure_coefficient):
            with self.assertRaises(ValueError):
                fn(6.0, 5.0, "compression", gamma=1.0)


class LinearLimitTest(unittest.TestCase):
    def test_linear_ratio_matches_analytic_form(self):
        # Step 4 of the SKILL.md workflow, the linearized limit pass:
        # p_lin/p_inf = 1 + gamma*(v/a_inf) at every sample.
        for v_a in (-0.3, -0.02, 0.0, 0.02, 0.4):
            self.assertAlmostEqual(hpt.linear_pressure_ratio(v_a),
                                   1.0 + 1.4 * v_a, delta=1e-12)

    def test_linearized_relative_error_at_small_ratios(self):
        # Step 4 of the SKILL.md workflow: at v/a = +-0.02 the
        # linearized ratio sits within a relative error of about 3.4e-4
        # of the exact law, the small-piston-velocity regime.
        exact_p = hpt.piston_pressure_ratio(0.02)
        rel_p = (exact_p - hpt.linear_pressure_ratio(0.02)) / exact_p
        self.assertAlmostEqual(rel_p, 0.000328927745, delta=1e-5)
        exact_m = hpt.piston_pressure_ratio(-0.02)
        rel_m = (exact_m - hpt.linear_pressure_ratio(-0.02)) / exact_m
        self.assertAlmostEqual(rel_m, 0.000343265810, delta=1e-5)

    def test_exact_law_diverges_from_linear_at_large_ratio(self):
        # Step 4 of the SKILL.md workflow: at v/a = 0.5 the residual
        # between the exact law and its tangent is 0.248717100000, so
        # the nonlinear law is required away from the small-ratio regime.
        residual = (hpt.piston_pressure_ratio(0.5)
                    - hpt.linear_pressure_ratio(0.5))
        self.assertAlmostEqual(residual, 0.248717100000, delta=1e-5)


class SteadySurfaceTest(unittest.TestCase):
    def test_piston_velocity_ratio_surface_a(self):
        # Step 2 of the SKILL.md workflow, the piston-velocity-ratio
        # traverse: surface A (M 6, theta 5 deg) carries
        # v/a = M*sin(theta) = 0.522934456486.
        self.assertAlmostEqual(hpt.piston_velocity_ratio(6.0, 5.0),
                               0.522934456486, delta=1e-9)

    def test_piston_velocity_ratio_surface_b(self):
        # Step 2 of the SKILL.md workflow: surface B (M 8, theta 10 deg)
        # carries v/a = 1.389185421335, an order-one piston ratio.
        self.assertAlmostEqual(hpt.piston_velocity_ratio(8.0, 10.0),
                               1.389185421335, delta=1e-9)

    def test_surface_a_compression_side(self):
        # Step 5 of the SKILL.md workflow, the compression-expansion
        # split: surface A compression p/p_inf = 2.006315343379 with
        # Cp = 0.039933148547 (step 6, the per-side coefficient step).
        self.assertAlmostEqual(
            hpt.surface_pressure_ratio(6.0, 5.0, "compression"),
            2.006315343379, delta=1e-5)
        self.assertAlmostEqual(
            hpt.surface_pressure_coefficient(6.0, 5.0, "compression"),
            0.039933148547, delta=1e-5)

    def test_surface_a_expansion_side(self):
        # Step 5 of the SKILL.md workflow: surface A expansion
        # p/p_inf = 0.461491957246 with Cp = -0.021369366776.
        self.assertAlmostEqual(
            hpt.surface_pressure_ratio(6.0, 5.0, "expansion"),
            0.461491957246, delta=1e-5)
        self.assertAlmostEqual(
            hpt.surface_pressure_coefficient(6.0, 5.0, "expansion"),
            -0.021369366776, delta=1e-5)

    def test_surface_b_compression_side(self):
        # Step 5 of the SKILL.md workflow: surface B compression
        # p/p_inf = 5.563247915155 with Cp = 0.101858212392.
        self.assertAlmostEqual(
            hpt.surface_pressure_ratio(8.0, 10.0, "compression"),
            5.563247915155, delta=1e-5)
        self.assertAlmostEqual(
            hpt.surface_pressure_coefficient(8.0, 10.0, "compression"),
            0.101858212392, delta=1e-5)

    def test_surface_b_expansion_side(self):
        # Step 5 of the SKILL.md workflow: surface B expansion
        # p/p_inf = 0.102434506727 with Cp = -0.020034944046, a
        # compression-to-expansion ratio near 54.3.
        self.assertAlmostEqual(
            hpt.surface_pressure_ratio(8.0, 10.0, "expansion"),
            0.102434506727, delta=1e-5)
        self.assertAlmostEqual(
            hpt.surface_pressure_coefficient(8.0, 10.0, "expansion"),
            -0.020034944046, delta=1e-5)

    def test_compression_side_exceeds_expansion_side(self):
        # Step 5 of the SKILL.md workflow: the compression side always
        # exceeds the expansion side of the same surface.
        for mach, theta in ((6.0, 5.0), (8.0, 10.0)):
            p_c = hpt.surface_pressure_ratio(mach, theta, "compression")
            p_e = hpt.surface_pressure_ratio(mach, theta, "expansion")
            self.assertGreater(p_c, 1.0)
            self.assertLess(p_e, 1.0)
            self.assertGreater(p_c, p_e)

    def test_pressure_product_not_reciprocal(self):
        # Step 5 of the SKILL.md workflow: at M 8, theta 10 deg the
        # product p_c * p_e = 0.569868555988, not 1, because the
        # exponent-7 law is not antisymmetric under a sign flip.
        p_c = hpt.surface_pressure_ratio(8.0, 10.0, "compression")
        p_e = hpt.surface_pressure_ratio(8.0, 10.0, "expansion")
        self.assertAlmostEqual(p_c * p_e, 0.569868555988, delta=1e-5)
        self.assertNotAlmostEqual(p_c * p_e, 1.0, delta=1e-3)

    def test_linear_cp_anchors(self):
        # Step 6 of the SKILL.md workflow, the per-side coefficient
        # step: the linearized limit Cp = 2*sin(theta)/M is 0.029051914249
        # at surface A and 0.043412044417 at surface B.
        self.assertAlmostEqual(hpt.linear_cp(6.0, 5.0), 0.029051914249,
                               delta=1e-9)
        self.assertAlmostEqual(hpt.linear_cp(8.0, 10.0), 0.043412044417,
                               delta=1e-9)

    def test_cp_rebuilt_from_linear_ratio_equals_linear_cp(self):
        # Step 6 of the SKILL.md workflow: the Cp rebuilt from the
        # linearized pressure ratio equals linear_cp to float zero, the
        # linearization identity (anchor residual 0.000000000000).
        for mach, theta in ((6.0, 5.0), (8.0, 10.0)):
            v_a = hpt.piston_velocity_ratio(mach, theta)
            p_lin = hpt.linear_pressure_ratio(v_a)
            cp_rebuilt = 2.0 / (1.4 * mach * mach) * (p_lin - 1.0)
            self.assertAlmostEqual(cp_rebuilt, hpt.linear_cp(mach, theta),
                                   delta=1e-9)

    def test_linear_cp_is_gamma_independent(self):
        # Step 6 of the SKILL.md workflow: gamma cancels in the
        # linearized coefficient, so the rebuilt Cp at any gamma equals
        # linear_cp 2*sin(theta)/M.
        for gamma in (1.3, 1.4, 1.67):
            v_a = hpt.piston_velocity_ratio(6.0, 5.0)
            p_lin = hpt.linear_pressure_ratio(v_a, gamma=gamma)
            cp_rebuilt = 2.0 / (gamma * 36.0) * (p_lin - 1.0)
            self.assertAlmostEqual(cp_rebuilt, hpt.linear_cp(6.0, 5.0),
                                   delta=1e-12)

    def test_exact_compression_cp_exceeds_linear_limit(self):
        # Step 6 of the SKILL.md workflow: the exact compression Cp sits
        # above the linearized coefficient at both steady surfaces, so
        # the linear limit underestimates the load.
        self.assertGreater(
            hpt.surface_pressure_coefficient(6.0, 5.0, "compression"),
            hpt.linear_cp(6.0, 5.0))
        self.assertGreater(
            hpt.surface_pressure_coefficient(8.0, 10.0, "compression"),
            hpt.linear_cp(8.0, 10.0))

    def test_aligned_surface_neutral_loading(self):
        # Steps 2 and 6 of the SKILL.md workflow: an aligned surface
        # (theta 0) sees no compression, p/p_inf = 1.000000000000 and
        # Cp = 0.000000000000 on both sides at any Mach.
        for side in ("compression", "expansion"):
            self.assertAlmostEqual(
                hpt.surface_pressure_ratio(8.0, 0.0, side), 1.0, delta=1e-12)
            self.assertAlmostEqual(
                hpt.surface_pressure_coefficient(8.0, 0.0, side), 0.0,
                delta=1e-12)


class GammaHonoredTest(unittest.TestCase):
    def test_gamma_13_piston_law_anchor(self):
        # Step 3 of the SKILL.md workflow: the exponent and the cutoff
        # follow gamma; at gamma 1.3 the ratio at v/a 0.5 is
        # 1.871572650534.
        self.assertAlmostEqual(hpt.piston_pressure_ratio(0.5, gamma=1.3),
                               1.871572650534, delta=1e-5)

    def test_gamma_13_surface_compression_anchor(self):
        # Step 5 of the SKILL.md workflow: surface B at gamma 1.3 gives
        # compression p/p_inf = 5.157316326010.
        self.assertAlmostEqual(
            hpt.surface_pressure_ratio(8.0, 10.0, "compression", gamma=1.3),
            5.157316326010, delta=1e-5)


class UnsteadySurfaceTest(unittest.TestCase):
    def test_inward_and_retreat_piston_ratios(self):
        # Step 7 of the SKILL.md workflow, the unsteady surface
        # composition: a wall velocity ratio 0.10 at M 6, theta 5 deg
        # moves the piston ratio to 0.622934456486 inward and
        # 0.422934456486 retreat around the steady 0.522934456486.
        steady = hpt.piston_velocity_ratio(6.0, 5.0)
        self.assertAlmostEqual(steady, 0.522934456486, delta=1e-9)
        self.assertAlmostEqual(
            hpt.unsteady_piston_ratio(6.0, 5.0, 0.10, 1),
            0.622934456486, delta=1e-9)
        self.assertAlmostEqual(
            hpt.unsteady_piston_ratio(6.0, 5.0, 0.10, -1),
            0.422934456486, delta=1e-9)

    def test_inward_and_retreat_pressure_ratios(self):
        # Step 7 of the SKILL.md workflow: the instantaneous pressures
        # follow from the composed ratios, 2.274841372010 inward and
        # 1.765429818550 retreat around the steady 2.006315343379.
        self.assertAlmostEqual(
            hpt.unsteady_pressure_ratio(6.0, 5.0, 0.10, 1),
            2.274841372010, delta=1e-5)
        self.assertAlmostEqual(
            hpt.unsteady_pressure_ratio(6.0, 5.0, 0.10, -1),
            1.765429818550, delta=1e-5)

    def test_inward_and_retreat_coefficients_and_swing(self):
        # Step 7 of the SKILL.md workflow: the instantaneous pressure
        # coefficients 0.050588943334 (inward) and 0.030374199149
        # (retreat) around the steady 0.039933148547, and the motion
        # swings the surface pressure by 0.253904031159 of the steady
        # ratio at the peak phase of the quarter-wave load cycle.
        def cp_of(p_ratio):
            return 2.0 / (1.4 * 36.0) * (p_ratio - 1.0)
        p_steady = hpt.surface_pressure_ratio(6.0, 5.0, "compression")
        p_in = hpt.unsteady_pressure_ratio(6.0, 5.0, 0.10, 1)
        p_ret = hpt.unsteady_pressure_ratio(6.0, 5.0, 0.10, -1)
        self.assertAlmostEqual(cp_of(p_steady), 0.039933148547, delta=1e-5)
        self.assertAlmostEqual(cp_of(p_in), 0.050588943334, delta=1e-5)
        self.assertAlmostEqual(cp_of(p_ret), 0.030374199149, delta=1e-5)
        self.assertAlmostEqual((p_in - p_ret) / p_steady,
                               0.253904031159, delta=1e-5)

    def test_zero_wall_motion_matches_steady_state(self):
        # Step 7 of the SKILL.md workflow: a stationary wall (wall
        # velocity ratio 0) recovers the steady compression state at
        # any phase of the composition.
        for direction in (1, -1):
            self.assertAlmostEqual(
                hpt.unsteady_pressure_ratio(6.0, 5.0, 0.0, direction),
                hpt.surface_pressure_ratio(6.0, 5.0, "compression"),
                delta=1e-12)

    def test_wall_motion_sign_taken_as_magnitude(self):
        # Step 7 of the SKILL.md workflow: the wall velocity enters as
        # abs(wall_v_a), so a negative signed amplitude with direction
        # +1 compresses exactly like the positive amplitude.
        self.assertEqual(
            hpt.unsteady_piston_ratio(6.0, 5.0, -0.10, 1),
            hpt.unsteady_piston_ratio(6.0, 5.0, 0.10, 1))

    def test_bad_direction_raises_value_error(self):
        # Step 7 of the SKILL.md workflow: only direction +1 (into the
        # gas) and -1 (retreat) are allowed.
        for direction in (0, -2, 2):
            with self.assertRaises(ValueError):
                hpt.unsteady_piston_ratio(6.0, 5.0, 0.10, direction)
            with self.assertRaises(ValueError):
                hpt.unsteady_pressure_ratio(6.0, 5.0, 0.10, direction)


class InputValidationTest(unittest.TestCase):
    def test_mach_at_or_below_one_raises(self):
        # Step 1 of the SKILL.md workflow: the guard requires Mach above
        # 1 in every surface and velocity-ratio function.
        with self.assertRaises(ValueError):
            hpt.surface_pressure_ratio(1.0, 5.0, "compression")
        with self.assertRaises(ValueError):
            hpt.surface_pressure_coefficient(1.0, 5.0, "compression")
        with self.assertRaises(ValueError):
            hpt.piston_velocity_ratio(0.8, 5.0)
        with self.assertRaises(ValueError):
            hpt.linear_cp(1.0, 5.0)

    def test_theta_out_of_range_and_bad_side_raise(self):
        # Step 1 of the SKILL.md workflow: theta must lie in [0, 90)
        # degrees and the side name must be one of the two allowed.
        for theta in (90.0, 95.0, -5.0):
            with self.assertRaises(ValueError):
                hpt.surface_pressure_coefficient(8.0, theta, "compression")
            with self.assertRaises(ValueError):
                hpt.piston_velocity_ratio(6.0, theta)
        for side in ("shock", "windward", "suction"):
            with self.assertRaises(ValueError):
                hpt.surface_pressure_ratio(8.0, 10.0, side)
            with self.assertRaises(ValueError):
                hpt.surface_pressure_coefficient(8.0, 10.0, side)

    def test_expansion_side_below_cutoff_raises(self):
        # Step 5 of the SKILL.md workflow: a steep enough expansion side
        # (M*sin(theta) past the cutoff) is fully expanded and raises
        # through the same guard as the raw law.
        with self.assertRaises(ValueError):
            hpt.surface_pressure_ratio(8.0, 45.0, "expansion")


class DeterminismTest(unittest.TestCase):
    def test_two_identical_runs_return_identical_bits(self):
        # Step 8 of the SKILL.md workflow, the deterministic contract
        # check: identical inputs give identical bits across runs and
        # the logic imports only the stdlib math module, no RNG.
        calls = [(hpt.piston_pressure_ratio, (0.5,)),
                 (hpt.surface_pressure_ratio, (8.0, 10.0, "compression")),
                 (hpt.unsteady_pressure_ratio, (6.0, 5.0, 0.10, -1))]
        first = [fn(*args) for fn, args in calls]
        second = [fn(*args) for fn, args in calls]
        self.assertEqual(first, second)
        logic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "hypersonic_piston_theory_logic.py")
        with open(logic_path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("import math", src)
        self.assertNotIn("import random", src)
        self.assertNotIn("numpy", src)


if __name__ == "__main__":
    unittest.main()
