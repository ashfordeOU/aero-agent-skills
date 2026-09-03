#!/usr/bin/env python3
"""Gate 3 contract test: GNSS pseudorange single-epoch positioning.

Exercises scripts/gnss_pseudorange_positioning_logic.py (stdlib
unittest, offline, deterministic). Contract anchors (receiver at the
ECEF origin, clock bias 100 m, three axis satellites at 20000 km plus
one diagonal satellite at 10^7*sqrt(2) m per axis whose true range is
sqrt(6)*10^7 = 24494897.42 m; every pseudorange = true range + 100 m):

- geometric_range((0,0,0), sat at 20000 km on z) = 20000000.0
- geometry_matrix rows at the origin for the axis satellites are
  [-1, 0, 0, 1] type unit lines of sight with last column 1
- solve_iterated worked example (4 satellites, exact bias model):
    x = -1.4414913407917115e-13
    y = -1.2789769243681803e-13
    z = -1.2789769243681803e-13
    clock_bias = 99.99999999999983
    residual_rms = 0.0, iterations = 2, converged = True
- redundant 5-satellite constellation (adds sat at
  (-10000 km, -10000 km, 0), range sqrt(2)*10^7 m, +100 m bias):
    clean fix x,y,z ~ 1.36e-09, clock_bias = 100.00000000160125,
    residual_rms = 1.862645149230957e-09
- perturbation: +3 m on the z-axis satellite pseudorange of the
  5-satellite set:
    fix = (0.2830128083384195, 0.2830128083384148,
           -2.497073769324896), clock_bias = 99.91076389567742,
    residual_rms = 0.5960682709777892, shift = 2.5289464038108727 m
- position_error_estimate: pos_1sigma = uere_equiv * pdop, and the
  exact-fit case gives gdop = 1.7216197603949122,
  pdop = 1.6202812472328787 with uere ~ 0
- Invalid inputs (fewer than 4 satellites, iters < 1, missing sat
  keys, non-finite pseudorange, coincident satellite) raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gnss_pseudorange_positioning_logic as gpp  # noqa: E402

EARTH_R = gpp.EARTH_RADIUS_SPHERICAL  # 6378137.0 m
DIAG_COORD = 24494897.42 / math.sqrt(3.0)  # 14142135.61920927 m ~ 14142 km


def axis_constellation():
    """Four satellites: three at 20000 km on the axes, one diagonal.

    Diagonal satellite at (d, d, d) with d = 24494897.42/sqrt(3), so
    its true range from the origin receiver is 24494897.42 m exactly.
    """
    return [
        {"x": 0.0, "y": 0.0, "z": 20000000.0, "pseudorange": 20000100.0},
        {"x": 20000000.0, "y": 0.0, "z": 0.0, "pseudorange": 20000100.0},
        {"x": 0.0, "y": 20000000.0, "z": 0.0, "pseudorange": 20000100.0},
        {"x": DIAG_COORD, "y": DIAG_COORD, "z": DIAG_COORD,
         "pseudorange": 24494897.42 + 100.0},
    ]


def redundant_constellation():
    """Five satellites: the axis set plus a redundant satellite.

    The fifth satellite sits at (-10^7, -10^7, 0) m with true range
    sqrt(2)*10^7 m from the origin receiver and the same +100 m bias.
    """
    sats = axis_constellation()
    sats.append({"x": -10000000.0, "y": -10000000.0, "z": 0.0,
                 "pseudorange": math.sqrt(2.0) * 10000000.0 + 100.0})
    return sats


class GeometricRangeTest(unittest.TestCase):
    def test_range_axis_satellite_from_origin(self):
        sat = {"x": 0.0, "y": 0.0, "z": 20000000.0, "pseudorange": 1.0}
        self.assertAlmostEqual(gpp.geometric_range((0.0, 0.0, 0.0), sat),
                               20000000.0, places=3)

    def test_range_diagonal_satellite_matches_spec(self):
        sat = {"x": DIAG_COORD, "y": DIAG_COORD, "z": DIAG_COORD,
               "pseudorange": 1.0}
        self.assertAlmostEqual(gpp.geometric_range((0.0, 0.0, 0.0), sat),
                               24494897.42, places=1)

    def test_range_offset_receiver(self):
        sat = {"x": 1000.0, "y": 0.0, "z": 0.0, "pseudorange": 1.0}
        self.assertAlmostEqual(gpp.geometric_range((0.0, 0.0, 0.0), sat),
                               1000.0, places=6)

    def test_range_missing_key_raises(self):
        sat = {"x": 1.0, "y": 0.0, "z": 0.0}
        with self.assertRaises(ValueError):
            gpp.geometric_range((0.0, 0.0, 0.0), sat)


class PredictedPseudorangeTest(unittest.TestCase):
    def test_predicted_is_range_plus_bias(self):
        sat = {"x": 0.0, "y": 0.0, "z": 20000000.0, "pseudorange": 1.0}
        self.assertAlmostEqual(
            gpp.predicted_pseudorange((0.0, 0.0, 0.0), sat, 100.0),
            20000100.0, places=3)

    def test_predicted_zero_bias_is_range(self):
        sat = {"x": 1000.0, "y": 0.0, "z": 0.0, "pseudorange": 1.0}
        self.assertAlmostEqual(
            gpp.predicted_pseudorange((0.0, 0.0, 0.0), sat, 0.0),
            1000.0, places=6)

    def test_predicted_non_finite_bias_raises(self):
        sat = {"x": 1000.0, "y": 0.0, "z": 0.0, "pseudorange": 1.0}
        with self.assertRaises(ValueError):
            gpp.predicted_pseudorange((0.0, 0.0, 0.0), sat, float("nan"))


class ResidualTest(unittest.TestCase):
    def test_residual_zero_at_true_state(self):
        sats = axis_constellation()
        for sat in sats:
            self.assertAlmostEqual(
                gpp.residual((0.0, 0.0, 0.0), sat, 100.0), 0.0, places=3)

    def test_residual_is_measured_minus_predicted(self):
        sat = {"x": 1000.0, "y": 0.0, "z": 0.0, "pseudorange": 1100.0}
        # predicted 1000 + 50 = 1050, residual 1100 - 1050 = 50
        self.assertAlmostEqual(gpp.residual((0.0, 0.0, 0.0), sat, 50.0),
                               50.0, places=6)

    def test_residual_positive_when_measurement_large(self):
        sat = {"x": 1000.0, "y": 0.0, "z": 0.0, "pseudorange": 1001.0}
        self.assertGreater(gpp.residual((0.0, 0.0, 0.0), sat, 0.0), 0.0)

    def test_residual_non_finite_pseudorange_raises(self):
        sat = {"x": 1000.0, "y": 0.0, "z": 0.0, "pseudorange": float("inf")}
        with self.assertRaises(ValueError):
            gpp.residual((0.0, 0.0, 0.0), sat, 0.0)


class GeometryMatrixTest(unittest.TestCase):
    def test_axis_rows_have_unit_line_of_sight(self):
        sats = axis_constellation()
        h = gpp.geometry_matrix(sats, (0.0, 0.0, 0.0))
        self.assertEqual(len(h), 4)
        for row in h:
            self.assertEqual(len(row), 4)
            self.assertAlmostEqual(
                math.sqrt(row[0] ** 2 + row[1] ** 2 + row[2] ** 2),
                1.0, places=6)
            self.assertAlmostEqual(row[3], 1.0, places=9)

    def test_z_axis_satellite_row(self):
        sats = axis_constellation()
        h = gpp.geometry_matrix(sats, (0.0, 0.0, 0.0))
        # First satellite sits on +z, so the line of sight points -z.
        self.assertAlmostEqual(h[0][0], 0.0, places=9)
        self.assertAlmostEqual(h[0][1], 0.0, places=9)
        self.assertAlmostEqual(h[0][2], -1.0, places=9)

    def test_diagonal_row_symmetric(self):
        sats = axis_constellation()
        h = gpp.geometry_matrix(sats, (0.0, 0.0, 0.0))
        row = h[3]
        expected = -DIAG_COORD / 24494897.42
        for component in row[:3]:
            self.assertAlmostEqual(component, expected, places=6)

    def test_coincident_satellite_raises(self):
        sat = {"x": 1.0, "y": 2.0, "z": 3.0, "pseudorange": 1.0}
        with self.assertRaises(ValueError):
            gpp.geometry_matrix([sat], (1.0, 2.0, 3.0))

    def test_missing_key_raises(self):
        sat = {"x": 1.0, "y": 2.0, "z": 3.0}
        with self.assertRaises(ValueError):
            gpp.geometry_matrix([sat], (0.0, 0.0, 0.0))


class Solve4x4Test(unittest.TestCase):
    def test_identity_system(self):
        a = [[1.0, 0.0, 0.0, 0.0],
             [0.0, 1.0, 0.0, 0.0],
             [0.0, 0.0, 1.0, 0.0],
             [0.0, 0.0, 0.0, 1.0]]
        x = gpp.solve_4x4(a, [5.0, -3.0, 2.0, 7.0])
        self.assertEqual(x, [5.0, -3.0, 2.0, 7.0])

    def test_diagonal_system(self):
        a = [[2.0, 0.0, 0.0, 0.0],
             [0.0, 4.0, 0.0, 0.0],
             [0.0, 0.0, 5.0, 0.0],
             [0.0, 0.0, 0.0, 10.0]]
        x = gpp.solve_4x4(a, [2.0, 8.0, 25.0, 30.0])
        for got, want in zip(x, [1.0, 2.0, 5.0, 3.0]):
            self.assertAlmostEqual(got, want, places=9)

    def test_known_coupled_system(self):
        a = [[1.0, 1.0, 0.0, 0.0],
             [1.0, -1.0, 0.0, 0.0],
             [0.0, 0.0, 2.0, 1.0],
             [0.0, 0.0, 1.0, -1.0]]
        x = gpp.solve_4x4(a, [3.0, 1.0, 5.0, 1.0])
        for got, want in zip(x, [2.0, 1.0, 2.0, 1.0]):
            self.assertAlmostEqual(got, want, places=9)

    def test_singular_system_raises(self):
        a = [[1.0, 2.0, 3.0, 4.0],
             [2.0, 4.0, 6.0, 8.0],
             [1.0, 1.0, 1.0, 1.0],
             [0.0, 0.0, 0.0, 0.0]]
        with self.assertRaises(ValueError):
            gpp.solve_4x4(a, [1.0, 2.0, 3.0, 4.0])


class SolveIteratedTest(unittest.TestCase):
    def test_worked_example_converges_to_origin(self):
        fix = gpp.solve_iterated(axis_constellation())
        self.assertLess(abs(fix["x"]), 0.5)
        self.assertLess(abs(fix["y"]), 0.5)
        self.assertLess(abs(fix["z"]), 0.5)
        self.assertLess(abs(fix["clock_bias"] - 100.0), 0.5)
        self.assertLess(fix["residual_rms"], 0.5)
        self.assertLessEqual(fix["iterations"], 8)
        self.assertTrue(fix["converged"])

    def test_worked_example_exact_module_outputs(self):
        fix = gpp.solve_iterated(axis_constellation())
        # Anchors recorded from the module run, deterministic.
        self.assertAlmostEqual(fix["x"], -1.4414913407917115e-13, places=6)
        self.assertAlmostEqual(fix["y"], -1.2789769243681803e-13, places=6)
        self.assertAlmostEqual(fix["z"], -1.2789769243681803e-13, places=6)
        self.assertAlmostEqual(fix["clock_bias"], 99.99999999999983,
                               places=6)
        self.assertAlmostEqual(fix["residual_rms"], 0.0, places=9)
        self.assertEqual(fix["iterations"], 2)
        self.assertTrue(fix["converged"])

    def test_result_contains_all_keys(self):
        fix = gpp.solve_iterated(axis_constellation())
        for key in ("x", "y", "z", "clock_bias", "residuals",
                    "residual_rms", "iterations", "converged"):
            self.assertIn(key, fix)
        self.assertEqual(len(fix["residuals"]), 4)

    def test_nonzero_initial_guess_still_converges(self):
        fix = gpp.solve_iterated(axis_constellation(), x0=100.0, y0=-50.0,
                                 z0=25.0, b0=10.0)
        self.assertLess(abs(fix["x"]), 0.5)
        self.assertLess(abs(fix["clock_bias"] - 100.0), 0.5)
        self.assertTrue(fix["converged"])

    def test_perturbation_shifts_fix_with_redundant_set(self):
        sats = redundant_constellation()
        clean = gpp.solve_iterated(sats)
        perturbed = [dict(sats[0], pseudorange=sats[0]["pseudorange"] + 3.0)]
        perturbed.extend(sats[1:])
        fix = gpp.solve_iterated(perturbed)
        # Anchors recorded from the module run, deterministic.
        self.assertAlmostEqual(fix["x"], 0.2830128083384195, places=5)
        self.assertAlmostEqual(fix["y"], 0.2830128083384148, places=5)
        self.assertAlmostEqual(fix["z"], -2.497073769324896, places=5)
        self.assertAlmostEqual(fix["clock_bias"], 99.91076389567742,
                               places=5)
        self.assertGreater(fix["residual_rms"], 0.0)
        shift = math.sqrt((fix["x"] - clean["x"]) ** 2
                          + (fix["y"] - clean["y"]) ** 2
                          + (fix["z"] - clean["z"]) ** 2)
        # A 3 m range error moves the fix by a few metres in 3D.
        self.assertAlmostEqual(shift, 2.5289464038108727, places=4)
        self.assertGreater(shift, 0.5)
        self.assertLess(shift, 10.0)

    def test_redundant_clean_fix_bias_anchor(self):
        fix = gpp.solve_iterated(redundant_constellation())
        self.assertAlmostEqual(fix["clock_bias"], 100.00000000160125,
                               places=5)
        self.assertLess(fix["residual_rms"], 1e-6)
        self.assertTrue(fix["converged"])

    def test_fewer_than_four_satellites_raises(self):
        sats = axis_constellation()[:3]
        with self.assertRaises(ValueError):
            gpp.solve_iterated(sats)

    def test_iters_zero_raises(self):
        with self.assertRaises(ValueError):
            gpp.solve_iterated(axis_constellation(), iters=0)

    def test_iters_one_returns_single_iteration(self):
        fix = gpp.solve_iterated(axis_constellation(), iters=1)
        self.assertEqual(fix["iterations"], 1)
        self.assertIn("converged", fix)

    def test_missing_satellite_key_raises(self):
        sats = axis_constellation()
        del sats[0]["x"]
        with self.assertRaises(ValueError):
            gpp.solve_iterated(sats)

    def test_non_finite_pseudorange_raises(self):
        sats = axis_constellation()
        sats[0]["pseudorange"] = float("nan")
        with self.assertRaises(ValueError):
            gpp.solve_iterated(sats)


class PositionErrorEstimateTest(unittest.TestCase):
    def test_pos_1sigma_is_uere_times_pdop(self):
        sats = redundant_constellation()
        fix = gpp.solve_iterated(sats)
        est = gpp.position_error_estimate(sats, fix)
        self.assertAlmostEqual(est["pos_1sigma"],
                               est["uere_equiv"] * est["pdop"], places=9)

    def test_exact_fit_gives_zero_position_error(self):
        sats = redundant_constellation()
        fix = gpp.solve_iterated(sats)
        est = gpp.position_error_estimate(sats, fix)
        # Anchors recorded from the module run, deterministic.
        self.assertAlmostEqual(est["gdop"], 1.7216197603949122, places=6)
        self.assertAlmostEqual(est["pdop"], 1.6202812472328787, places=6)
        self.assertLess(est["pos_1sigma"], 1e-6)

    def test_perturbed_fit_gives_positive_position_error(self):
        sats = redundant_constellation()
        perturbed = [dict(sats[0], pseudorange=sats[0]["pseudorange"] + 3.0)]
        perturbed.extend(sats[1:])
        fix = gpp.solve_iterated(perturbed)
        est = gpp.position_error_estimate(sats, fix)
        self.assertGreater(est["pos_1sigma"], 0.0)
        self.assertAlmostEqual(est["pos_1sigma"], 0.9657982974559285,
                               places=5)

    def test_dop_positive_definite(self):
        sats = redundant_constellation()
        fix = gpp.solve_iterated(sats)
        est = gpp.position_error_estimate(sats, fix)
        self.assertGreater(est["gdop"], 0.0)
        self.assertGreater(est["pdop"], 0.0)
        self.assertGreater(est["gdop"], est["pdop"])

    def test_fewer_than_four_satellites_raises(self):
        sats = axis_constellation()[:3]
        fix = {"x": 0.0, "y": 0.0, "z": 0.0, "residual_rms": 1.0}
        with self.assertRaises(ValueError):
            gpp.position_error_estimate(sats, fix)


class GeodeticApproxTest(unittest.TestCase):
    def test_origin_is_center_of_sphere(self):
        geo = gpp.to_geodetic_approx(0.0, 0.0, 0.0)
        self.assertAlmostEqual(geo["lat_rad"], 0.0, places=9)
        self.assertAlmostEqual(geo["lon_rad"], 0.0, places=9)
        self.assertAlmostEqual(geo["alt_m"], -EARTH_R, places=3)

    def test_equator_on_x_axis(self):
        geo = gpp.to_geodetic_approx(EARTH_R, 0.0, 0.0)
        self.assertAlmostEqual(geo["lat_rad"], 0.0, places=9)
        self.assertAlmostEqual(geo["lon_rad"], 0.0, places=9)
        self.assertAlmostEqual(geo["alt_m"], 0.0, places=3)

    def test_north_pole(self):
        geo = gpp.to_geodetic_approx(0.0, 0.0, EARTH_R)
        self.assertAlmostEqual(geo["lat_rad"], math.pi / 2.0, places=9)
        self.assertAlmostEqual(geo["alt_m"], 0.0, places=3)

    def test_lon_quarter_turn(self):
        geo = gpp.to_geodetic_approx(0.0, EARTH_R, 0.0)
        self.assertAlmostEqual(geo["lon_rad"], math.pi / 2.0, places=9)

    def test_altitude_above_pole(self):
        geo = gpp.to_geodetic_approx(0.0, 0.0, 20000000.0)
        self.assertAlmostEqual(geo["lat_rad"], math.pi / 2.0, places=9)
        self.assertAlmostEqual(geo["alt_m"], 20000000.0 - EARTH_R, places=3)


if __name__ == "__main__":
    unittest.main()
