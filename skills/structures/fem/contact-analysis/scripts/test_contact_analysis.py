#!/usr/bin/env python3
"""Gate 3 contract test: finite element contact analysis logic.

Exercises scripts/contact_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3. Covers the
penalty stiffness estimate, penalty contact force at zero and finite
penetration, Lagrange enforcement tolerance, Coulomb friction stick
and slip states, friction with zero and negative normal force,
penetration control convergence, node-to-surface signed gaps, tie
constraint tolerance, and invalid-input edge cases.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import contact_analysis_logic as contact  # noqa: E402


class ContactStiffnessTest(unittest.TestCase):
    def test_worked_example_value(self):
        k = contact.contact_stiffness_estimate(
            200000.0, 100.0, 10.0, alpha=100.0)
        self.assertAlmostEqual(k, 2.0e8)

    def test_stiffness_scales_with_area_and_modulus(self):
        k1 = contact.contact_stiffness_estimate(200000.0, 100.0, 10.0)
        k2 = contact.contact_stiffness_estimate(200000.0, 200.0, 10.0)
        k3 = contact.contact_stiffness_estimate(100000.0, 100.0, 10.0)
        self.assertAlmostEqual(k2, 2.0 * k1)
        self.assertAlmostEqual(k3, 0.5 * k1)

    def test_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            contact.contact_stiffness_estimate(0.0, 100.0, 10.0)
        with self.assertRaises(ValueError):
            contact.contact_stiffness_estimate(200000.0, -1.0, 10.0)
        with self.assertRaises(ValueError):
            contact.contact_stiffness_estimate(200000.0, 100.0, 0.0)
        with self.assertRaises(ValueError):
            contact.contact_stiffness_estimate(200000.0, 100.0, 10.0,
                                               alpha=0.0)


class PenaltyForceTest(unittest.TestCase):
    def test_zero_penetration_means_no_force(self):
        result = contact.penalty_contact_force(2.0e8, 0.0)
        self.assertFalse(result["in_contact"])
        self.assertEqual(result["penetration"], 0.0)
        self.assertEqual(result["force"], 0.0)

    def test_separation_gives_zero_force(self):
        result = contact.penalty_contact_force(2.0e8, 0.05)
        self.assertFalse(result["in_contact"])
        self.assertEqual(result["force"], 0.0)

    def test_finite_penetration_force_is_k_times_p(self):
        result = contact.penalty_contact_force(2.0e8, -5.0e-4)
        self.assertTrue(result["in_contact"])
        self.assertAlmostEqual(result["penetration"], 5.0e-4)
        self.assertAlmostEqual(result["force"], 2.0e8 * 5.0e-4)

    def test_force_grows_with_stiffness(self):
        low = contact.penalty_contact_force(1.0e8, -1.0e-3)["force"]
        high = contact.penalty_contact_force(1.0e9, -1.0e-3)["force"]
        self.assertLess(low, high)

    def test_negative_stiffness_raises(self):
        with self.assertRaises(ValueError):
            contact.penalty_contact_force(-1.0, -0.1)


class LagrangeCheckTest(unittest.TestCase):
    def test_zero_gap_is_active_and_enforced(self):
        result = contact.lagrange_contact_check(0.0)
        self.assertTrue(result["in_contact"])
        self.assertTrue(result["enforced"])
        self.assertEqual(result["penetration"], 0.0)

    def test_tiny_penetration_within_tolerance_is_enforced(self):
        result = contact.lagrange_contact_check(-1.0e-12)
        self.assertTrue(result["enforced"])

    def test_penetration_beyond_tolerance_not_enforced(self):
        result = contact.lagrange_contact_check(-1.0e-3, tolerance=1e-9)
        self.assertTrue(result["in_contact"])
        self.assertFalse(result["enforced"])
        self.assertAlmostEqual(result["penetration"], 1.0e-3)

    def test_separation_is_inactive(self):
        result = contact.lagrange_contact_check(1.0e-3)
        self.assertFalse(result["in_contact"])
        self.assertEqual(result["penetration"], 0.0)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            contact.lagrange_contact_check(-1.0e-6, tolerance=-1.0)


class FrictionTest(unittest.TestCase):
    def test_low_trial_shear_sticks(self):
        result = contact.friction_force(100000.0, 0.2, 8000.0)
        self.assertEqual(result["state"], "sticking")
        self.assertAlmostEqual(result["friction_force"], 8000.0)
        self.assertAlmostEqual(result["max_friction"], 20000.0)

    def test_trial_at_cap_sticks(self):
        result = contact.friction_force(100000.0, 0.2, 20000.0)
        self.assertEqual(result["state"], "sticking")
        self.assertAlmostEqual(result["friction_force"], 20000.0)

    def test_high_trial_shear_slips_and_saturates(self):
        result = contact.friction_force(100000.0, 0.2, 25000.0)
        self.assertEqual(result["state"], "slipping")
        self.assertAlmostEqual(result["friction_force"], 20000.0)

    def test_slip_direction_preserved_for_negative_trial(self):
        result = contact.friction_force(100000.0, 0.2, -25000.0)
        self.assertEqual(result["state"], "slipping")
        self.assertAlmostEqual(result["friction_force"], -20000.0)

    def test_zero_friction_coefficient_caps_at_zero(self):
        result = contact.friction_force(50000.0, 0.0, 100.0)
        self.assertEqual(result["state"], "slipping")
        self.assertEqual(result["friction_force"], 0.0)
        self.assertEqual(result["max_friction"], 0.0)

    def test_zero_normal_force_carries_no_friction(self):
        result = contact.friction_force(0.0, 0.3, 50.0)
        self.assertEqual(result["max_friction"], 0.0)
        self.assertEqual(result["state"], "slipping")
        self.assertEqual(result["friction_force"], 0.0)

    def test_negative_normal_force_raises(self):
        with self.assertRaises(ValueError):
            contact.friction_force(-100.0, 0.2, 10.0)

    def test_negative_mu_raises(self):
        with self.assertRaises(ValueError):
            contact.friction_force(100.0, -0.2, 10.0)


class PenetrationControlTest(unittest.TestCase):
    def test_converges_on_first_iteration_when_tolerance_met(self):
        result = contact.penetration_control(
            100000.0, 2.0e8, 0.01)
        self.assertTrue(result["converged"])
        self.assertEqual(result["iterations"], 1)
        self.assertAlmostEqual(result["stiffness"], 2.0e8)
        self.assertAlmostEqual(result["penetration"], 5.0e-4)

    def test_raises_stiffness_until_under_tolerance(self):
        result = contact.penetration_control(
            100000.0, 1.0e6, 0.001, factor=10.0, max_iterations=20)
        self.assertTrue(result["converged"])
        self.assertLessEqual(result["penetration"], 0.001)
        self.assertGreater(result["stiffness"], 1.0e6)

    def test_iteration_count_matches_stiffness_growth(self):
        result = contact.penetration_control(
            100000.0, 1.0e6, 0.001, factor=10.0, max_iterations=20)
        self.assertEqual(result["stiffness"], 1.0e6 * (10.0 ** (result["iterations"] - 1)))

    def test_zero_force_converges_immediately(self):
        result = contact.penetration_control(0.0, 2.0e8, 0.01)
        self.assertTrue(result["converged"])
        self.assertEqual(result["iterations"], 1)
        self.assertEqual(result["penetration"], 0.0)

    def test_runs_out_of_iterations_reports_not_converged(self):
        result = contact.penetration_control(
            1.0e12, 1.0, 1.0e-12, factor=2.0, max_iterations=3)
        self.assertFalse(result["converged"])
        self.assertEqual(result["iterations"], 3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            contact.penetration_control(-1.0, 2.0e8, 0.01)
        with self.assertRaises(ValueError):
            contact.penetration_control(100.0, 0.0, 0.01)
        with self.assertRaises(ValueError):
            contact.penetration_control(100.0, 2.0e8, 0.0)
        with self.assertRaises(ValueError):
            contact.penetration_control(100.0, 2.0e8, 0.01, factor=1.0)
        with self.assertRaises(ValueError):
            contact.penetration_control(100.0, 2.0e8, 0.01, max_iterations=0)


class NodeToSurfaceGapTest(unittest.TestCase):
    def test_slave_on_normal_side_is_positive_gap(self):
        gap = contact.node_to_surface_gap((0.0, 0.0), (10.0, 0.0), (5.0, 3.0))
        self.assertAlmostEqual(gap, 3.0)

    def test_slave_penetrating_is_negative_gap(self):
        gap = contact.node_to_surface_gap((0.0, 0.0), (10.0, 0.0), (5.0, -2.0))
        self.assertAlmostEqual(gap, -2.0)

    def test_slave_on_segment_is_zero_gap(self):
        gap = contact.node_to_surface_gap((0.0, 0.0), (10.0, 0.0), (5.0, 0.0))
        self.assertAlmostEqual(gap, 0.0)

    def test_rotated_segment_normal(self):
        # segment along the y axis: left normal points along -x
        gap = contact.node_to_surface_gap((0.0, 0.0), (0.0, 10.0), (-4.0, 5.0))
        self.assertAlmostEqual(gap, 4.0)

    def test_zero_length_segment_raises(self):
        with self.assertRaises(ValueError):
            contact.node_to_surface_gap((1.0, 1.0), (1.0, 1.0), (2.0, 2.0))


class TieConstraintTest(unittest.TestCase):
    def test_within_tolerance_is_tied(self):
        result = contact.tie_constraint_check(1.0e-5, 1.0e-3)
        self.assertTrue(result["tied"])

    def test_beyond_tolerance_not_tied(self):
        result = contact.tie_constraint_check(2.0e-2, 1.0e-3)
        self.assertFalse(result["tied"])

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            contact.tie_constraint_check(0.0, -1.0e-3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
