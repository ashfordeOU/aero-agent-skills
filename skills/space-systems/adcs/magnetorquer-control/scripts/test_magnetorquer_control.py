#!/usr/bin/env python3
"""Gate 3 contract test: magnetorquer control logic.

Exercises scripts/magnetorquer_control_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - required dipole
m = (B x torque) / |B|^2 from a torque demand and the local field,
the B-dot detumbling law m = gain * (omega x B), achievable torque
|m x B|, torque authority m_max * |B|, underdetermined-axis warning,
coil sizing N * I * A, and orbit-averaged authority.

Known values: with B = (1, 0, 0) and torque = (0, 0, 1) the required
dipole is (B x torque) / 1 = (0, -1, 0) and the along-B component is
zero. With torque = (2, 1, 0) the along-B component is (2, 0, 0) and
the dipole is (0, 0, 1), which reproduces only (0, 1, 0). The B-dot
dipole for omega = (0, 0, 1), B = (1, 0, 0), gain = 2 is
2 * (omega x B) = (0, 2, 0); its torque (0, 0, -2) opposes the rate
(dot = -2). |(0, 1, 0) x (1, 0, 0)| = 1.0 and parallel vectors give
zero. Authority for m_max = 4 in B = (3, 0, 0) is 12.0. A torque
(1, 0, 1) against B = (0, 0, 1) has an along-B magnitude of 1.0.
A 100-turn 0.02 m^2 coil at 0.5 A gives dipole 1.0; the current for
dipole 1.0 is 0.5 A. Field samples (1,0,0), (0,2,0), (0,0,3) with
m_max = 2 give orbit-averaged authority 4.0.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import magnetorquer_control_logic as mcl  # noqa: E402


class DipoleFromTorqueTest(unittest.TestCase):
    def test_perpendicular_demand(self):
        # B = (1,0,0), torque = (0,0,1): m = (B x torque) / |B|^2 = (0,-1,0).
        m, along_b = mcl.dipole_from_torque((0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        self.assertAlmostEqual(m[0], 0.0, places=12)
        self.assertAlmostEqual(m[1], -1.0, places=12)
        self.assertAlmostEqual(m[2], 0.0, places=12)
        # along-B component is zero for a perpendicular demand.
        self.assertAlmostEqual(mcl.vec_norm(along_b), 0.0, places=12)

    def test_reproduces_torque(self):
        # m x B must equal the demand when the demand is perpendicular.
        m, _ = mcl.dipole_from_torque((0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        tau = mcl.cross(m, (1.0, 0.0, 0.0))
        self.assertAlmostEqual(tau[0], 0.0, places=12)
        self.assertAlmostEqual(tau[1], 0.0, places=12)
        self.assertAlmostEqual(tau[2], 1.0, places=12)

    def test_partial_along_b_component_returned(self):
        # torque = (2,1,0) with B = (1,0,0): along-B part is (2,0,0),
        # dipole (0,0,1) reproduces only the perpendicular part (0,1,0).
        m, along_b = mcl.dipole_from_torque((2.0, 1.0, 0.0), (1.0, 0.0, 0.0))
        self.assertAlmostEqual(m[0], 0.0, places=12)
        self.assertAlmostEqual(m[1], 0.0, places=12)
        self.assertAlmostEqual(m[2], 1.0, places=12)
        self.assertAlmostEqual(along_b[0], 2.0, places=12)
        self.assertAlmostEqual(along_b[1], 0.0, places=12)
        self.assertAlmostEqual(along_b[2], 0.0, places=12)
        tau = mcl.cross(m, (1.0, 0.0, 0.0))
        self.assertAlmostEqual(tau[1], 1.0, places=12)  # only perp part

    def test_zero_field_raises(self):
        with self.assertRaises(ValueError):
            mcl.dipole_from_torque((0.0, 0.0, 1.0), (0.0, 0.0, 0.0))


class BDotDipoleTest(unittest.TestCase):
    def test_known_dipole(self):
        # gain * (omega x B) = 2 * ((0,0,1) x (1,0,0)) = (0,2,0).
        m = mcl.b_dot_dipole((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), 2.0)
        self.assertAlmostEqual(m[0], 0.0, places=12)
        self.assertAlmostEqual(m[1], 2.0, places=12)
        self.assertAlmostEqual(m[2], 0.0, places=12)

    def test_torque_opposes_rate(self):
        # m x B = (0,2,0) x (1,0,0) = (0,0,-2): dot with rate (0,0,1)
        # is -2, so the law damps the rate.
        m = mcl.b_dot_dipole((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), 2.0)
        tau = mcl.cross(m, (1.0, 0.0, 0.0))
        damping = tau[0] * 0.0 + tau[1] * 0.0 + tau[2] * 1.0
        self.assertAlmostEqual(damping, -2.0, places=12)
        self.assertLess(damping, 0.0)

    def test_zero_rate_gives_zero_dipole(self):
        m = mcl.b_dot_dipole((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 2.0)
        self.assertAlmostEqual(mcl.vec_norm(m), 0.0, places=12)

    def test_zero_field_raises(self):
        with self.assertRaises(ValueError):
            mcl.b_dot_dipole((0.0, 0.0, 1.0), (0.0, 0.0, 0.0), 2.0)


class AchievableTorqueTest(unittest.TestCase):
    def test_known_magnitude(self):
        # |(0,1,0) x (1,0,0)| = |(0,0,-1)| = 1.0.
        self.assertAlmostEqual(
            mcl.achievable_torque((0.0, 1.0, 0.0), (1.0, 0.0, 0.0)), 1.0, places=12
        )

    def test_parallel_dipole_zero_torque(self):
        self.assertAlmostEqual(
            mcl.achievable_torque((2.0, 0.0, 0.0), (1.0, 0.0, 0.0)), 0.0, places=12
        )

    def test_scales_with_field_magnitude(self):
        # |(0,2,0) x (3,0,0)| = |(0,0,-6)| = 6.0.
        self.assertAlmostEqual(
            mcl.achievable_torque((0.0, 2.0, 0.0), (3.0, 0.0, 0.0)), 6.0, places=12
        )


class TorqueAuthorityTest(unittest.TestCase):
    def test_authority_is_mmax_times_field(self):
        self.assertAlmostEqual(
            mcl.torque_authority(4.0, (3.0, 0.0, 0.0)), 12.0, places=12
        )

    def test_zero_field_zero_authority(self):
        self.assertAlmostEqual(
            mcl.torque_authority(4.0, (0.0, 0.0, 0.0)), 0.0, places=12
        )


class UnderdeterminedWarningTest(unittest.TestCase):
    def test_perpendicular_demand_no_warning(self):
        warning, along = mcl.underdetermined_warning((1.0, 2.0, 0.0), (0.0, 0.0, 1.0))
        self.assertFalse(warning)
        self.assertAlmostEqual(along, 0.0, places=12)

    def test_along_b_demand_warns(self):
        # torque = (1,0,1) against B = (0,0,1): along-B magnitude 1.0.
        warning, along = mcl.underdetermined_warning((1.0, 0.0, 1.0), (0.0, 0.0, 1.0))
        self.assertTrue(warning)
        self.assertAlmostEqual(along, 1.0, places=12)

    def test_tolerance_suppresses_small_component(self):
        warning, along = mcl.underdetermined_warning(
            (1.0, 0.0, 0.5), (0.0, 0.0, 1.0), tolerance=1.0
        )
        self.assertFalse(warning)
        self.assertAlmostEqual(along, 0.5, places=12)

    def test_zero_field_raises(self):
        with self.assertRaises(ValueError):
            mcl.underdetermined_warning((1.0, 0.0, 1.0), (0.0, 0.0, 0.0))


class CoilSizingTest(unittest.TestCase):
    def test_dipole_is_turns_times_current_times_area(self):
        self.assertAlmostEqual(mcl.coil_dipole(100.0, 0.5, 0.02), 1.0, places=12)

    def test_current_for_dipole(self):
        self.assertAlmostEqual(
            mcl.coil_current_for_dipole(1.0, 100.0, 0.02), 0.5, places=12
        )

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            mcl.coil_current_for_dipole(1.0, 100.0, 0.0)


class OrbitAverageTest(unittest.TestCase):
    def test_mean_authority_over_samples(self):
        # norms 1, 2, 3; mean 2.0; authority m_max * 2.0 = 4.0.
        samples = [(1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0)]
        self.assertAlmostEqual(
            mcl.orbit_average_authority(samples, 2.0), 4.0, places=12
        )

    def test_empty_samples_raise(self):
        with self.assertRaises(ValueError):
            mcl.orbit_average_authority([], 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
