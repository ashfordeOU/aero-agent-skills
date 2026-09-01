#!/usr/bin/env python3
"""Gate 3 contract test: Cooper-Harper handling qualities rating.

Exercises scripts/cooper_harper_rating_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the decision
tree returns the correct integer rating for worked evaluation cases
across the rating bands, the band and level helpers classify 1-10,
the boundary cases are pinned (1, 3, 6, 9, 10), and invalid inputs
raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cooper_harper_rating_logic as chr  # noqa: E402


class DecisionTreeTest(unittest.TestCase):
    def test_satisfactory_band_anchors(self):
        # Desired tolerances: none -> 1, negligible -> 2, minor -> 3.
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "desired", "none"), 1)
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "desired", "negligible"), 2)
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "desired", "minor"), 3)

    def test_warrant_improvement_band_anchors(self):
        # Adequate tolerances: minor -> 4, moderate -> 5, considerable -> 6.
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "adequate", "minor"), 4)
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "adequate", "moderate"), 5)
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "adequate", "considerable"),
            6)
        # Extensive compensation tops the 4-6 band at 6.
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "adequate", "extensive"), 6)

    def test_require_improvement_band_anchors(self):
        # Adequate performance not attainable: minimal -> 7,
        # considerable -> 8, extensive/intense -> 9.
        self.assertEqual(
            chr.cooper_harper_rating(True, False, "adequate", "minor"), 7)
        self.assertEqual(
            chr.cooper_harper_rating(True, False, "adequate",
                                     "considerable"), 8)
        self.assertEqual(
            chr.cooper_harper_rating(True, False, "adequate", "extensive"),
            9)
        self.assertEqual(
            chr.cooper_harper_rating(True, False, "desired", "intense"), 9)

    def test_uncontrollable_gives_10(self):
        self.assertEqual(
            chr.cooper_harper_rating(False, True, "desired", "none"), 10)
        self.assertEqual(
            chr.cooper_harper_rating(False, False, "adequate",
                                     "extensive"), 10)

    def test_boundary_cases(self):
        # Pinned contract boundaries: 1, 3, 6, 9, 10.
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "desired", "none"), 1)
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "desired", "minor"), 3)
        self.assertEqual(
            chr.cooper_harper_rating(True, True, "adequate",
                                     "considerable"), 6)
        self.assertEqual(
            chr.cooper_harper_rating(True, False, "adequate", "extensive"),
            9)
        self.assertEqual(
            chr.cooper_harper_rating(False, True, "desired", "none"), 10)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            chr.cooper_harper_rating("yes", True, "desired", "none")
        with self.assertRaises(ValueError):
            chr.cooper_harper_rating(True, 1, "desired", "none")
        with self.assertRaises(ValueError):
            chr.cooper_harper_rating(True, True, "satisfactory", "none")
        with self.assertRaises(ValueError):
            chr.cooper_harper_rating(True, True, "desired", "heavy")
        # Desired tolerances with compensation beyond minor contradict
        # the 1-3 band and must raise.
        with self.assertRaises(ValueError):
            chr.cooper_harper_rating(True, True, "desired", "moderate")
        with self.assertRaises(ValueError):
            chr.cooper_harper_rating(True, True, "desired", "extensive")


class BandClassificationTest(unittest.TestCase):
    def test_rating_band_anchors(self):
        self.assertEqual(chr.rating_band(1),
                         "satisfactory without improvement")
        self.assertEqual(chr.rating_band(3),
                         "satisfactory without improvement")
        self.assertEqual(chr.rating_band(4),
                         "deficiencies warrant improvement")
        self.assertEqual(chr.rating_band(6),
                         "deficiencies warrant improvement")
        self.assertEqual(chr.rating_band(7),
                         "deficiencies require improvement")
        self.assertEqual(chr.rating_band(9),
                         "deficiencies require improvement")
        self.assertEqual(chr.rating_band(10), "uncontrollable")

    def test_level_anchors(self):
        self.assertEqual(chr.handling_qualities_level(1), "Level 1")
        self.assertEqual(chr.handling_qualities_level(3), "Level 1")
        self.assertEqual(chr.handling_qualities_level(4), "Level 2")
        self.assertEqual(chr.handling_qualities_level(6), "Level 2")
        self.assertEqual(chr.handling_qualities_level(7), "Level 3")
        self.assertEqual(chr.handling_qualities_level(9), "Level 3")
        self.assertEqual(chr.handling_qualities_level(10), "uncontrolled")

    def test_invalid_ratings_raise(self):
        with self.assertRaises(ValueError):
            chr.rating_band(0)
        with self.assertRaises(ValueError):
            chr.rating_band(11)
        with self.assertRaises(ValueError):
            chr.rating_band(3.5)
        with self.assertRaises(ValueError):
            chr.handling_qualities_level(0)
        with self.assertRaises(ValueError):
            chr.handling_qualities_level("four")


if __name__ == "__main__":
    unittest.main(verbosity=2)
