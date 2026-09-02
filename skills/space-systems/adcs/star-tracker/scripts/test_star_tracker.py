#!/usr/bin/env python3
"""Gate 3 contract test: star tracker attitude determination logic.

Exercises scripts/star_tracker_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - angular separation
theta = acos(dot(u, v)) in degrees between unit vectors, star
identification of a measured centroid against a star catalog within
the field of view, boresight error in arcseconds, and lost in space
versus tracking mode selection.

Known values: separation between u = (1, 0, 0) and
v = (cos 10 deg, sin 10 deg, 0) is exactly 10.0 degrees; separation
between (1, 0, 0) and (0, 1, 0) is exactly 90.0 degrees. A measured
centroid 0.5 degrees from catalog star 'B' (and 1.5 degrees from star
'A') matches 'B' inside a 10 degree FOV. A centroid at 45 degrees
from every catalog star matches nothing inside a 1 degree FOV.
Boresight (1, 0, 0) against a centroid at 0.01 degrees gives 36.0
arcseconds. Mode: prior attitude with a 0.005 degree match and a
0.05 degree tracking radius is tracking; a 0.5 degree match is lost
in space.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import star_tracker_logic as st  # noqa: E402

CATALOG = [
    ("A", (1.0, 0.0, 0.0)),
    ("B", (math.cos(math.radians(2.0)), math.sin(math.radians(2.0)), 0.0)),
    ("C", (0.0, 0.0, 1.0)),
]


class UnitVectorTest(unittest.TestCase):
    def test_normalizes_to_unit_length(self):
        u = st.unit_vector((3.0, 4.0, 0.0))
        self.assertAlmostEqual(math.sqrt(sum(c * c for c in u)), 1.0, places=12)

    def test_keeps_direction(self):
        u = st.unit_vector((3.0, 4.0, 0.0))
        self.assertAlmostEqual(u[0], 0.6, places=12)
        self.assertAlmostEqual(u[1], 0.8, places=12)

    def test_zero_vector_raises(self):
        with self.assertRaises(ValueError):
            st.unit_vector((0.0, 0.0, 0.0))


class AngularSeparationTest(unittest.TestCase):
    def test_ten_degree_separation(self):
        # v = (cos 10 deg, sin 10 deg, 0): acos(dot) = 10.0 degrees.
        v = (math.cos(math.radians(10.0)), math.sin(math.radians(10.0)), 0.0)
        self.assertAlmostEqual(st.angular_separation((1.0, 0.0, 0.0), v), 10.0, places=9)

    def test_orthogonal_axes_are_90_degrees(self):
        self.assertAlmostEqual(
            st.angular_separation((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)), 90.0, places=9
        )

    def test_identical_vectors_zero(self):
        self.assertAlmostEqual(
            st.angular_separation((0.0, 0.0, 1.0), (0.0, 0.0, 1.0)), 0.0, places=9
        )

    def test_opposite_vectors_180_degrees(self):
        self.assertAlmostEqual(
            st.angular_separation((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)), 180.0, places=9
        )


class IdentifyStarTest(unittest.TestCase):
    def test_nearest_match_inside_fov(self):
        # Measured centroid at 1.5 degrees from the x-axis: 1.5 degrees
        # from star A, 0.5 degrees from star B.
        measured = (
            math.cos(math.radians(1.5)),
            math.sin(math.radians(1.5)),
            0.0,
        )
        star_id, sep = st.identify_star(CATALOG, measured, 10.0)
        self.assertEqual(star_id, "B")
        self.assertAlmostEqual(sep, 0.5, places=9)

    def test_no_match_when_all_stars_outside_fov(self):
        # Centroid at 45 degrees from every catalog star; a 1 degree FOV
        # (half-angle 0.5) contains no match.
        measured = (1.0 / math.sqrt(2.0), 0.0, 1.0 / math.sqrt(2.0))
        star_id, sep = st.identify_star(CATALOG, measured, 1.0)
        self.assertIsNone(star_id)
        self.assertIsNone(sep)

    def test_non_unit_measured_vector_normalized(self):
        # (2, 0, 0) is the same direction as (1, 0, 0): matches star A
        # with zero separation.
        star_id, sep = st.identify_star(CATALOG, (2.0, 0.0, 0.0), 5.0)
        self.assertEqual(star_id, "A")
        self.assertAlmostEqual(sep, 0.0, places=9)

    def test_zero_separation_match_accepted(self):
        star_id, sep = st.identify_star(CATALOG, (0.0, 0.0, 1.0), 2.0)
        self.assertEqual(star_id, "C")
        self.assertAlmostEqual(sep, 0.0, places=9)

    def test_fov_half_angle(self):
        self.assertAlmostEqual(st.fov_half_angle(10.0), 5.0, places=12)


class BoresightErrorTest(unittest.TestCase):
    def test_known_arcsecond_error(self):
        # 0.01 degree separation = 0.01 * 3600 = 36.0 arcseconds.
        measured = (
            math.cos(math.radians(0.01)),
            math.sin(math.radians(0.01)),
            0.0,
        )
        self.assertAlmostEqual(
            st.boresight_error((1.0, 0.0, 0.0), measured), 36.0, places=6
        )

    def test_zero_error_on_alignment(self):
        self.assertAlmostEqual(st.boresight_error((0.0, 0.0, 1.0), (0.0, 0.0, 1.0)), 0.0, places=9)


class ModeSelectionTest(unittest.TestCase):
    def test_tracking_with_prior_within_radius(self):
        self.assertEqual(st.select_mode(True, 0.005, 0.05), "tracking")

    def test_lost_in_space_when_match_exceeds_radius(self):
        self.assertEqual(st.select_mode(True, 0.5, 0.05), "lost-in-space")

    def test_lost_in_space_without_prior(self):
        self.assertEqual(st.select_mode(False, 0.001, 0.05), "lost-in-space")


if __name__ == "__main__":
    unittest.main(verbosity=2)
