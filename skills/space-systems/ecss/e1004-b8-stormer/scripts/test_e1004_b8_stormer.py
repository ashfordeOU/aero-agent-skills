#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.8 Størmer vertical
cutoff rigidity.

Exercises scripts/e1004_b8_stormer_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the dipole moment scale
factor is 1.0 at the reference epoch and raises for an epoch driving it
non-positive; the Størmer constant scales linearly with that factor;
the vertical cutoff rigidity follows stormer_constant * cos^4(latitude)
/ radial_distance^2 and raises for an out-of-range latitude or a
non-positive radial distance; a particle penetrates only at or above
the local cutoff and a negative rigidity raises; the orbit-level
unshielded fraction is the equal-time-weighted share of penetrating
samples and raises on an empty orbit; the unshielded-fraction budget
check flags a missing budget with nonzero exposure and an exceeded
budget, and passes within budget; and the worst-case epoch selection
follows the secular decay direction.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_b8_stormer_logic as st  # noqa: E402


class DipoleMomentScaleFactorTest(unittest.TestCase):
    def test_reference_epoch_is_unity(self):
        self.assertAlmostEqual(st.dipole_moment_scale_factor(st.REFERENCE_EPOCH_YEAR), 1.0)

    def test_later_epoch_scales_below_unity(self):
        scale = st.dipole_moment_scale_factor(st.REFERENCE_EPOCH_YEAR + 100)
        self.assertLess(scale, 1.0)

    def test_earlier_epoch_scales_above_unity(self):
        scale = st.dipole_moment_scale_factor(st.REFERENCE_EPOCH_YEAR - 100)
        self.assertGreater(scale, 1.0)

    def test_far_future_epoch_raises(self):
        with self.assertRaises(ValueError):
            st.dipole_moment_scale_factor(st.REFERENCE_EPOCH_YEAR + 100000)


class StormerConstantTest(unittest.TestCase):
    def test_reference_epoch_matches_reference_constant(self):
        self.assertAlmostEqual(
            st.stormer_constant_gv(st.REFERENCE_EPOCH_YEAR), st.STORMER_CONSTANT_REFERENCE_GV
        )

    def test_scales_with_moment_factor(self):
        epoch = st.REFERENCE_EPOCH_YEAR + 50
        expected = st.STORMER_CONSTANT_REFERENCE_GV * st.dipole_moment_scale_factor(epoch)
        self.assertAlmostEqual(st.stormer_constant_gv(epoch), expected)


class VerticalCutoffRigidityTest(unittest.TestCase):
    def test_equator_at_reference_epoch_matches_reference_constant(self):
        cutoff = st.vertical_cutoff_rigidity_gv(0.0, 1.0, st.REFERENCE_EPOCH_YEAR)
        self.assertAlmostEqual(cutoff, st.STORMER_CONSTANT_REFERENCE_GV)

    def test_pole_cutoff_is_zero(self):
        cutoff = st.vertical_cutoff_rigidity_gv(90.0, 1.0, st.REFERENCE_EPOCH_YEAR)
        self.assertAlmostEqual(cutoff, 0.0, places=9)

    def test_cutoff_decreases_with_radial_distance(self):
        near = st.vertical_cutoff_rigidity_gv(30.0, 1.0, st.REFERENCE_EPOCH_YEAR)
        far = st.vertical_cutoff_rigidity_gv(30.0, 2.0, st.REFERENCE_EPOCH_YEAR)
        self.assertGreater(near, far)

    def test_cutoff_decreases_with_latitude_magnitude(self):
        low_lat = st.vertical_cutoff_rigidity_gv(10.0, 1.2, st.REFERENCE_EPOCH_YEAR)
        high_lat = st.vertical_cutoff_rigidity_gv(60.0, 1.2, st.REFERENCE_EPOCH_YEAR)
        self.assertGreater(low_lat, high_lat)

    def test_negative_latitude_symmetric_to_positive(self):
        pos = st.vertical_cutoff_rigidity_gv(45.0, 1.2, st.REFERENCE_EPOCH_YEAR)
        neg = st.vertical_cutoff_rigidity_gv(-45.0, 1.2, st.REFERENCE_EPOCH_YEAR)
        self.assertAlmostEqual(pos, neg)

    def test_later_epoch_lowers_cutoff(self):
        early = st.vertical_cutoff_rigidity_gv(30.0, 1.2, st.REFERENCE_EPOCH_YEAR)
        later = st.vertical_cutoff_rigidity_gv(30.0, 1.2, st.REFERENCE_EPOCH_YEAR + 50)
        self.assertGreater(early, later)

    def test_latitude_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            st.vertical_cutoff_rigidity_gv(91.0, 1.2, st.REFERENCE_EPOCH_YEAR)
        with self.assertRaises(ValueError):
            st.vertical_cutoff_rigidity_gv(-91.0, 1.2, st.REFERENCE_EPOCH_YEAR)

    def test_non_positive_radial_distance_raises(self):
        with self.assertRaises(ValueError):
            st.vertical_cutoff_rigidity_gv(30.0, 0.0, st.REFERENCE_EPOCH_YEAR)
        with self.assertRaises(ValueError):
            st.vertical_cutoff_rigidity_gv(30.0, -1.0, st.REFERENCE_EPOCH_YEAR)


class IsPenetratingTest(unittest.TestCase):
    def test_at_cutoff_penetrates(self):
        self.assertTrue(st.is_penetrating(5.0, 5.0))

    def test_above_cutoff_penetrates(self):
        self.assertTrue(st.is_penetrating(10.0, 5.0))

    def test_below_cutoff_is_shielded(self):
        self.assertFalse(st.is_penetrating(1.0, 5.0))

    def test_negative_particle_rigidity_raises(self):
        with self.assertRaises(ValueError):
            st.is_penetrating(-1.0, 5.0)

    def test_negative_cutoff_rigidity_raises(self):
        with self.assertRaises(ValueError):
            st.is_penetrating(1.0, -5.0)


class OrbitUnshieldedFractionTest(unittest.TestCase):
    def test_all_equatorial_low_threshold_fully_shielded(self):
        points = [{"geomagnetic_latitude_deg": 0.0, "radial_distance_re": 1.1}] * 4
        fraction = st.orbit_unshielded_fraction(points, 1.0, st.REFERENCE_EPOCH_YEAR)
        self.assertAlmostEqual(fraction, 0.0)

    def test_all_polar_any_threshold_fully_unshielded(self):
        points = [{"geomagnetic_latitude_deg": 90.0, "radial_distance_re": 1.1}] * 4
        fraction = st.orbit_unshielded_fraction(points, 0.5, st.REFERENCE_EPOCH_YEAR)
        self.assertAlmostEqual(fraction, 1.0)

    def test_mixed_orbit_fraction(self):
        points = [
            {"geomagnetic_latitude_deg": 0.0, "radial_distance_re": 1.1},
            {"geomagnetic_latitude_deg": 90.0, "radial_distance_re": 1.1},
            {"geomagnetic_latitude_deg": 90.0, "radial_distance_re": 1.1},
            {"geomagnetic_latitude_deg": 90.0, "radial_distance_re": 1.1},
        ]
        fraction = st.orbit_unshielded_fraction(points, 1.0, st.REFERENCE_EPOCH_YEAR)
        self.assertAlmostEqual(fraction, 0.75)

    def test_empty_orbit_raises(self):
        with self.assertRaises(ValueError):
            st.orbit_unshielded_fraction([], 1.0, st.REFERENCE_EPOCH_YEAR)


class GeomagneticShieldingViolationsTest(unittest.TestCase):
    def test_within_budget_no_violation(self):
        points = [{"geomagnetic_latitude_deg": 0.0, "radial_distance_re": 1.1}] * 4
        violations = st.geomagnetic_shielding_violations(
            "case-1", points, 1.0, st.REFERENCE_EPOCH_YEAR, 0.5
        )
        self.assertEqual(violations, [])

    def test_exceeding_budget_flagged(self):
        points = [{"geomagnetic_latitude_deg": 90.0, "radial_distance_re": 1.1}] * 4
        violations = st.geomagnetic_shielding_violations(
            "case-2", points, 0.5, st.REFERENCE_EPOCH_YEAR, 0.1
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "unshielded_fraction_exceeded")
        self.assertEqual(violations[0]["case"], "case-2")

    def test_missing_budget_with_exposure_flagged(self):
        points = [{"geomagnetic_latitude_deg": 90.0, "radial_distance_re": 1.1}] * 4
        violations = st.geomagnetic_shielding_violations(
            "case-3", points, 0.5, st.REFERENCE_EPOCH_YEAR, None
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_unshielded_fraction_budget")

    def test_missing_budget_with_zero_exposure_not_flagged(self):
        points = [{"geomagnetic_latitude_deg": 0.0, "radial_distance_re": 1.1}] * 4
        violations = st.geomagnetic_shielding_violations(
            "case-4", points, 1.0, st.REFERENCE_EPOCH_YEAR, None
        )
        self.assertEqual(violations, [])


class WorstCaseEpochForShieldingTest(unittest.TestCase):
    def test_decaying_moment_picks_end_of_mission(self):
        self.assertLess(st.SECULAR_DECAY_FRACTION_PER_YEAR, 0)
        epoch = st.worst_case_epoch_for_shielding(2025, 2035)
        self.assertEqual(epoch, 2035)

    def test_start_equals_end(self):
        epoch = st.worst_case_epoch_for_shielding(2030, 2030)
        self.assertEqual(epoch, 2030)

    def test_end_before_start_raises(self):
        with self.assertRaises(ValueError):
            st.worst_case_epoch_for_shielding(2035, 2025)


class StormerShieldingReviewTest(unittest.TestCase):
    def test_compliant_case(self):
        case = {
            "case_id": "orbit-1",
            "orbit_points": [{"geomagnetic_latitude_deg": 0.0, "radial_distance_re": 1.1}] * 4,
            "threshold_rigidity_gv": 1.0,
            "epoch_year": st.REFERENCE_EPOCH_YEAR,
            "max_unshielded_fraction": 0.1,
        }
        review = st.stormer_shielding_review(case)
        self.assertEqual(review, [])
        self.assertTrue(st.is_stormer_shielding_compliant(review))

    def test_noncompliant_case(self):
        case = {
            "case_id": "orbit-2",
            "orbit_points": [{"geomagnetic_latitude_deg": 90.0, "radial_distance_re": 1.1}] * 4,
            "threshold_rigidity_gv": 0.5,
            "epoch_year": st.REFERENCE_EPOCH_YEAR,
            "max_unshielded_fraction": 0.1,
        }
        review = st.stormer_shielding_review(case)
        self.assertTrue(review)
        self.assertFalse(st.is_stormer_shielding_compliant(review))

    def test_default_missing_budget(self):
        case = {
            "case_id": "orbit-3",
            "orbit_points": [{"geomagnetic_latitude_deg": 90.0, "radial_distance_re": 1.1}] * 4,
            "threshold_rigidity_gv": 0.5,
            "epoch_year": st.REFERENCE_EPOCH_YEAR,
        }
        review = st.stormer_shielding_review(case)
        self.assertEqual(review[0]["issue"], "missing_unshielded_fraction_budget")


if __name__ == "__main__":
    unittest.main(verbosity=2)
