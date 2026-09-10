#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 9.2.4 + Annex B.8
geomagnetic shielding (Stormer cutoffs, trajectory tracing).

Exercises scripts/e1004_stormer_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the vertical cutoff
rigidity falls off as cos(latitude)^4 and as 1/r^2, is highest at the
geomagnetic equator and lowest at the poles; a particle is allowed to
reach a point only when its rigidity is at or above that point's local
cutoff; the orbit shielding profile's fraction_exposed is consistent
with the per-point allowed flags; attenuated_flux zeroes out
sub-cutoff particles and passes through at/above-cutoff particles
unchanged; select_shielding_method escalates to trajectory_tracing
whenever penumbra resolution or off-vertical arrival directions
matter.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_stormer_logic as st  # noqa: E402


class VerticalCutoffRigidityTest(unittest.TestCase):
    def test_equator_higher_than_midlatitude_at_same_radius(self):
        equator = st.vertical_cutoff_rigidity(0.0, 1.1)
        midlat = st.vertical_cutoff_rigidity(45.0, 1.1)
        self.assertGreater(equator, midlat)

    def test_pole_cutoff_is_zero(self):
        self.assertAlmostEqual(st.vertical_cutoff_rigidity(90.0, 1.1), 0.0, places=9)

    def test_larger_radius_lowers_cutoff(self):
        near = st.vertical_cutoff_rigidity(30.0, 1.1)
        far = st.vertical_cutoff_rigidity(30.0, 2.2)
        self.assertGreater(near, far)

    def test_known_value_at_equator_r1(self):
        self.assertAlmostEqual(st.vertical_cutoff_rigidity(0.0, 1.0), 59.6, places=6)

    def test_latitude_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            st.vertical_cutoff_rigidity(91.0, 1.1)
        with self.assertRaises(ValueError):
            st.vertical_cutoff_rigidity(-91.0, 1.1)

    def test_non_positive_radius_raises(self):
        with self.assertRaises(ValueError):
            st.vertical_cutoff_rigidity(30.0, 0.0)
        with self.assertRaises(ValueError):
            st.vertical_cutoff_rigidity(30.0, -1.0)


class IsAccessAllowedTest(unittest.TestCase):
    def test_rigidity_above_cutoff_allowed(self):
        self.assertTrue(st.is_access_allowed(10.0, 5.0))

    def test_rigidity_at_cutoff_allowed(self):
        self.assertTrue(st.is_access_allowed(5.0, 5.0))

    def test_rigidity_below_cutoff_blocked(self):
        self.assertFalse(st.is_access_allowed(2.0, 5.0))

    def test_negative_particle_rigidity_raises(self):
        with self.assertRaises(ValueError):
            st.is_access_allowed(-1.0, 5.0)

    def test_negative_cutoff_rigidity_raises(self):
        with self.assertRaises(ValueError):
            st.is_access_allowed(5.0, -1.0)


class EvaluateOrbitPointTest(unittest.TestCase):
    def test_high_latitude_low_rigidity_still_allowed(self):
        result = st.evaluate_orbit_point(80.0, 1.1, particle_rigidity_gv=0.5)
        self.assertTrue(result["allowed"])

    def test_low_latitude_low_rigidity_blocked(self):
        result = st.evaluate_orbit_point(0.0, 1.1, particle_rigidity_gv=0.5)
        self.assertFalse(result["allowed"])
        self.assertGreater(result["cutoff_rigidity_gv"], 0.5)


class OrbitShieldingProfileTest(unittest.TestCase):
    def test_polar_orbit_fully_exposed_for_low_rigidity_particle(self):
        # A near-90-degree-inclination LEO track samples latitudes across
        # the full range; a very low-rigidity particle should still be
        # blocked near the equator but allowed near the poles.
        track = [(-90.0, 1.1), (-45.0, 1.1), (0.0, 1.1), (45.0, 1.1), (90.0, 1.1)]
        profile = st.orbit_shielding_profile(track, particle_rigidity_gv=1.0)
        self.assertEqual(len(profile["points"]), 5)
        self.assertLess(profile["fraction_exposed"], 1.0)
        self.assertGreater(profile["fraction_exposed"], 0.0)

    def test_high_rigidity_particle_fully_exposed(self):
        track = [(-90.0, 1.1), (-45.0, 1.1), (0.0, 1.1), (45.0, 1.1), (90.0, 1.1)]
        profile = st.orbit_shielding_profile(track, particle_rigidity_gv=1000.0)
        self.assertEqual(profile["fraction_exposed"], 1.0)

    def test_zero_rigidity_particle_only_exposed_at_poles(self):
        track = [(-90.0, 1.1), (0.0, 1.1), (90.0, 1.1)]
        profile = st.orbit_shielding_profile(track, particle_rigidity_gv=0.0)
        self.assertAlmostEqual(profile["fraction_exposed"], 2.0 / 3.0, places=9)

    def test_min_max_cutoff_bounds(self):
        track = [(0.0, 1.1), (90.0, 1.1)]
        profile = st.orbit_shielding_profile(track, particle_rigidity_gv=1.0)
        self.assertAlmostEqual(profile["min_cutoff_rigidity_gv"], 0.0, places=9)
        self.assertGreater(profile["max_cutoff_rigidity_gv"], 0.0)

    def test_empty_track_raises(self):
        with self.assertRaises(ValueError):
            st.orbit_shielding_profile([], particle_rigidity_gv=1.0)


class AttenuatedFluxTest(unittest.TestCase):
    def test_allowed_particle_flux_unchanged(self):
        self.assertEqual(st.attenuated_flux(100.0, 10.0, 5.0), 100.0)

    def test_blocked_particle_flux_zeroed(self):
        self.assertEqual(st.attenuated_flux(100.0, 2.0, 5.0), 0.0)

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            st.attenuated_flux(-1.0, 10.0, 5.0)


class SelectShieldingMethodTest(unittest.TestCase):
    def test_default_is_vertical_cutoff(self):
        self.assertEqual(st.select_shielding_method(False, False), "vertical_stormer_cutoff")

    def test_penumbra_resolution_escalates(self):
        self.assertEqual(st.select_shielding_method(True, False), "trajectory_tracing")

    def test_off_vertical_directions_escalates(self):
        self.assertEqual(st.select_shielding_method(False, True), "trajectory_tracing")

    def test_both_reasons_escalates(self):
        self.assertEqual(st.select_shielding_method(True, True), "trajectory_tracing")


class VerifyShieldingAssessmentTest(unittest.TestCase):
    def setUp(self):
        self.track = [(-90.0, 1.1), (-45.0, 1.1), (0.0, 1.1), (45.0, 1.1), (90.0, 1.1)]
        self.profile = st.orbit_shielding_profile(self.track, particle_rigidity_gv=1.0)

    def test_consistent_profile_passes(self):
        verdict = st.verify_shielding_assessment("vertical_stormer_cutoff", self.profile, 1.0)
        self.assertTrue(verdict["fraction_consistent"])
        self.assertTrue(verdict["passed"])
        self.assertFalse(verdict["fully_shielded"])
        self.assertFalse(verdict["fully_exposed"])

    def test_fully_shielded_flag(self):
        blocked_profile = st.orbit_shielding_profile(
            [(0.0, 1.1), (10.0, 1.1)], particle_rigidity_gv=0.001
        )
        verdict = st.verify_shielding_assessment(
            "vertical_stormer_cutoff", blocked_profile, 0.001
        )
        self.assertTrue(verdict["fully_shielded"])

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            st.verify_shielding_assessment("magic", self.profile, 1.0)

    def test_non_positive_particle_rigidity_raises(self):
        with self.assertRaises(ValueError):
            st.verify_shielding_assessment("vertical_stormer_cutoff", self.profile, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
