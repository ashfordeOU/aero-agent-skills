#!/usr/bin/env python3
"""Gate 3 contract test: dilution of precision logic.

Exercises scripts/dop_logic.py (stdlib unittest, offline). Contract:
docs/harness-contract.md gate 3 - build the geometry matrix H with one
row [e, n, u, 1] per satellite unit vector, form A = H^T H, invert it
to G = A^-1, and read the DOP values off the diagonal:
gdop = sqrt(g00+g11+g22+g33), pdop = sqrt(g00+g11+g22),
hdop = sqrt(g00+g11), vdop = sqrt(g22), tdop = sqrt(g33).

Reference case (hand computed): four satellites on the corners of a
regular tetrahedron. Unit vectors (1,1,1), (1,-1,-1), (-1,1,-1),
(-1,-1,1) normalized by sqrt(3). Each component squared sums to 4/3
and every cross term cancels, so A = diag(4/3, 4/3, 4/3, 4) and
G = diag(3/4, 3/4, 3/4, 1/4). Hence gdop = sqrt(10/4) =
1.5811388300841898, pdop = sqrt(9/4) = 1.5, hdop = sqrt(6/4) =
1.224744871391589, vdop = sqrt(3/4) = 0.8660254037844386,
tdop = sqrt(1/4) = 0.5.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dop_logic as dop  # noqa: E402

TETRA = [
    (1.0, 1.0, 1.0),
    (1.0, -1.0, -1.0),
    (-1.0, 1.0, -1.0),
    (-1.0, -1.0, 1.0),
]

GDOP_REF = 1.5811388300841898  # sqrt(2.5)
PDOP_REF = 1.5
HDOP_REF = 1.224744871391589  # sqrt(1.5)
VDOP_REF = 0.8660254037844386  # sqrt(0.75)
TDOP_REF = 0.5


def enu(elev_deg, azim_deg):
    """Unit line-of-sight vector at elevation and azimuth (degrees)."""
    el = math.radians(elev_deg)
    az = math.radians(azim_deg)
    return (
        math.cos(el) * math.sin(az),
        math.cos(el) * math.cos(az),
        math.sin(el),
    )


# Non-singular test geometries. Same-elevation sets are coplanar in
# (e, n, u, 1) space (u and the unit column become dependent), which
# makes the normal matrix singular; every set here varies elevation.
# LOW: low satellites near the horizon, poor geometry (high PDOP),
# all below a 10 deg mask. HIGH: high-elevation satellites, good
# geometry (low PDOP), all above a 30 deg mask.
LOW = [enu(5.0, 0.0), enu(5.0, 90.0), enu(5.0, 180.0), enu(8.0, 270.0)]
HIGH = [enu(45.0, 45.0), enu(45.0, 135.0), enu(45.0, 225.0), enu(60.0, 315.0)]
EIGHT = LOW + HIGH


class TetrahedronDopTest(unittest.TestCase):
    def test_analytic_dops(self):
        # Hand values from A = diag(4/3, 4/3, 4/3, 4), see module docstring.
        d = dop.compute_dops(TETRA)
        self.assertAlmostEqual(d["gdop"], GDOP_REF, places=12)
        self.assertAlmostEqual(d["pdop"], PDOP_REF, places=12)
        self.assertAlmostEqual(d["hdop"], HDOP_REF, places=12)
        self.assertAlmostEqual(d["vdop"], VDOP_REF, places=12)
        self.assertAlmostEqual(d["tdop"], TDOP_REF, places=12)

    def test_dop_relations(self):
        # GDOP dominates PDOP dominates HDOP; squares differ by the
        # diagonal terms exactly.
        d = dop.compute_dops(TETRA)
        self.assertAlmostEqual(d["gdop"] ** 2, d["pdop"] ** 2 + d["tdop"] ** 2, places=12)
        self.assertAlmostEqual(d["pdop"] ** 2, d["hdop"] ** 2 + d["vdop"] ** 2, places=12)

    def test_geometry_and_normal_matrix(self):
        # A = H^T H is exactly diagonal for the tetrahedron.
        h = dop.geometry_matrix(TETRA)
        self.assertEqual(len(h), 4)
        self.assertEqual(len(h[0]), 4)
        a = dop.normal_matrix(h)
        for i in range(4):
            for j in range(4):
                want = {0: 4.0 / 3.0, 1: 4.0 / 3.0, 2: 4.0 / 3.0, 3: 4.0}[i] if i == j else 0.0
                self.assertAlmostEqual(a[i][j], want, places=12)

    def test_invert_4x4_identity(self):
        ident = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
        g = dop.invert_4x4(ident)
        for i in range(4):
            for j in range(4):
                self.assertAlmostEqual(g[i][j], 1.0 if i == j else 0.0, places=12)

    def test_invert_4x4_singular_returns_none(self):
        singular = [[1.0, 0.0, 0.0, 0.0]] * 4
        self.assertIsNone(dop.invert_4x4(singular))

    def test_position_error_from_uere(self):
        # 1-sigma position error = PDOP * UERE; tetrahedron PDOP = 1.5.
        self.assertAlmostEqual(dop.position_error_std(TETRA, 3.0), 4.5, places=12)


class GeometryValidationTest(unittest.TestCase):
    def test_fewer_than_four_raises(self):
        with self.assertRaises(ValueError):
            dop.compute_dops(TETRA[:3])

    def test_zero_length_vector_raises(self):
        with self.assertRaises(ValueError):
            dop.compute_dops(TETRA[:3] + [(0.0, 0.0, 0.0)])

    def test_wrong_arity_raises(self):
        with self.assertRaises(ValueError):
            dop.compute_dops([(1.0, 0.0)] * 4)

    def test_collinear_geometry_is_singular(self):
        # All four satellites at the same line of sight: rank-1 H,
        # the normal matrix is singular and no DOP exists.
        with self.assertRaises(ValueError):
            dop.compute_dops([(0.0, 0.0, 1.0)] * 4)


class ElevationMaskTest(unittest.TestCase):
    def test_elevation_of_constructed_vector(self):
        self.assertAlmostEqual(dop.elevation_deg(enu(30.0, 120.0)), 30.0, places=9)
        self.assertAlmostEqual(dop.elevation_deg((0.0, 0.0, 1.0)), 90.0, places=9)
        self.assertAlmostEqual(dop.elevation_deg((0.0, 1.0, 0.0)), 0.0, places=9)

    def test_mask_filters_low_satellites(self):
        self.assertEqual(len(dop.apply_elevation_mask(EIGHT, 0.0)), 8)
        self.assertEqual(len(dop.apply_elevation_mask(EIGHT, 10.0)), 4)
        self.assertEqual(len(dop.apply_elevation_mask(EIGHT, 30.0)), 4)
        kept = dop.apply_elevation_mask(EIGHT, 10.0)
        for v in kept:
            self.assertGreaterEqual(dop.elevation_deg(v), 10.0)

    def test_mask_raises_out_of_range(self):
        with self.assertRaises(ValueError):
            dop.apply_elevation_mask(EIGHT, 95.0)
        with self.assertRaises(ValueError):
            dop.apply_elevation_mask(EIGHT, -95.0)


class SatelliteSelectionTest(unittest.TestCase):
    def test_single_subset_when_mask_leaves_exactly_k(self):
        # Mask 10 deg leaves exactly the four high satellites; the
        # selection must equal their PDOP, recomputed independently.
        subset, pdop = dop.select_best_subset(EIGHT, 4, mask_deg=10.0)
        self.assertEqual(len(subset), 4)
        self.assertAlmostEqual(pdop, dop.compute_dops(HIGH)["pdop"], places=12)
        for v in subset:
            self.assertGreaterEqual(dop.elevation_deg(v), 10.0)

    def test_selection_improves_on_any_single_subset(self):
        # The exhaustive minimum cannot be worse than any feasible
        # subset; low satellites near the horizon give a poor geometry.
        subset, pdop = dop.select_best_subset(EIGHT, 4)
        self.assertEqual(len(subset), 4)
        self.assertLess(pdop, dop.compute_dops(LOW)["pdop"])
        self.assertLessEqual(pdop, dop.compute_dops(HIGH)["pdop"])

    def test_k_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            dop.select_best_subset(EIGHT, 3)
        with self.assertRaises(ValueError):
            dop.select_best_subset(EIGHT, 9)

    def test_adding_a_zenith_satellite_strictly_improves_pdop(self):
        # Tetrahedron plus a zenith satellite: G gains a rank-1 term,
        # so every diagonal entry drops and PDOP strictly decreases.
        five = TETRA + [(0.0, 0.0, 1.0)]
        d4 = dop.compute_dops(TETRA)
        d5 = dop.compute_dops(five)
        self.assertLess(d5["pdop"], d4["pdop"])
        self.assertLess(d5["gdop"], d4["gdop"])
        # Hand value: G5 = diag(0.75, 0.75, 0.46875, 0.21875), so
        # pdop5 = sqrt(1.96875).
        self.assertAlmostEqual(d5["pdop"], math.sqrt(1.96875), places=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
