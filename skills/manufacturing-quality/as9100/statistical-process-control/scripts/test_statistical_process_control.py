#!/usr/bin/env python3
"""Gate 3 contract test: statistical process control math.

Exercises scripts/statistical_process_control_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 -
X-bar/R chart limits with the A2, D3, D4 constants, the range-derived
process sigma with the d2 constant, the Cp/CPU/CPL/Cpk capability
indices, and the Western Electric out-of-control rules.

All expected values are hand-computed (see each docstring) with the
standard published SPC constants for the subgroup size.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import statistical_process_control_logic as spc  # noqa: E402


class XbarRLimitsTest(unittest.TestCase):
    def test_n5_limits(self):
        # n=5: A2=0.577, D4=2.114, D3=0. With xbar=10, rbar=2:
        # UCLx = 10 + 0.577*2 = 11.154, LCLx = 10 - 1.154 = 8.846,
        # UCLr = 2.114*2 = 4.228, LCLr = 0.
        uclx, lclx, uclr, lclr = spc.xbar_r_limits(10.0, 2.0, 5)
        self.assertAlmostEqual(uclx, 11.154, places=3)
        self.assertAlmostEqual(lclx, 8.846, places=3)
        self.assertAlmostEqual(uclr, 4.228, places=3)
        self.assertEqual(lclr, 0.0)

    def test_n2_limits(self):
        # n=2: A2=1.880, D4=3.267. xbar=50, rbar=1:
        # UCLx = 51.88, LCLx = 48.12, UCLr = 3.267.
        uclx, lclx, uclr, lclr = spc.xbar_r_limits(50.0, 1.0, 2)
        self.assertAlmostEqual(uclx, 51.88, places=2)
        self.assertAlmostEqual(lclx, 48.12, places=2)
        self.assertAlmostEqual(uclr, 3.267, places=3)

    def test_n7_has_nonzero_d3(self):
        # n=7: D3=0.076, so the R chart lower limit is nonzero.
        _, _, uclr, lclr = spc.xbar_r_limits(10.0, 2.0, 7)
        self.assertAlmostEqual(lclr, 0.152, places=3)
        self.assertGreater(uclr, lclr)

    def test_zero_range_limits(self):
        # rbar=0 collapses every limit onto the centerline.
        uclx, lclx, uclr, lclr = spc.xbar_r_limits(10.0, 0.0, 5)
        self.assertEqual(uclx, 10.0)
        self.assertEqual(lclx, 10.0)
        self.assertEqual(uclr, 0.0)
        self.assertEqual(lclr, 0.0)

    def test_unsupported_n_raises(self):
        with self.assertRaises(ValueError):
            spc.xbar_r_limits(10.0, 2.0, 1)
        with self.assertRaises(ValueError):
            spc.xbar_r_limits(10.0, 2.0, 11)
        with self.assertRaises(ValueError):
            spc.xbar_r_limits(10.0, 2.0, 5.0)

    def test_negative_range_raises(self):
        with self.assertRaises(ValueError):
            spc.xbar_r_limits(10.0, -0.1, 5)


class ProcessSigmaTest(unittest.TestCase):
    def test_n5_sigma(self):
        # d2(5)=2.326: sigma = 2.0 / 2.326 = 0.859845.
        self.assertAlmostEqual(spc.process_sigma(2.0, 5), 0.859845, places=5)

    def test_n2_sigma(self):
        # d2(2)=1.128: sigma = 3.0 / 1.128 = 2.659574.
        self.assertAlmostEqual(spc.process_sigma(3.0, 2), 2.659574, places=5)

    def test_zero_range_sigma(self):
        self.assertEqual(spc.process_sigma(0.0, 5), 0.0)

    def test_unsupported_n_raises(self):
        with self.assertRaises(ValueError):
            spc.process_sigma(2.0, 12)

    def test_negative_range_raises(self):
        with self.assertRaises(ValueError):
            spc.process_sigma(-1.0, 5)


class CapabilityIndicesTest(unittest.TestCase):
    def test_centered_process(self):
        # USL=12, LSL=8, xbar=10, sigma=0.859845 (from rbar=2, n=5):
        # Cp = 4 / (6*0.859845) = 0.775337, CPU = CPL = 2 / (3*0.859845)
        # = 0.775337, Cpk = 0.775337.
        cp, cpu, cpl, cpk = spc.capability_indices(12.0, 8.0, 10.0, 0.859845)
        self.assertAlmostEqual(cp, 0.775337, places=5)
        self.assertAlmostEqual(cpu, 0.775337, places=5)
        self.assertAlmostEqual(cpl, 0.775337, places=5)
        self.assertAlmostEqual(cpk, 0.775337, places=5)

    def test_off_center_process(self):
        # USL=12, LSL=8, xbar=10.5, sigma=0.5: Cp = 4/3 = 1.333333,
        # CPU = 1.5/1.5 = 1.0, CPL = 2.5/1.5 = 1.666667, Cpk = 1.0.
        cp, cpu, cpl, cpk = spc.capability_indices(12.0, 8.0, 10.5, 0.5)
        self.assertAlmostEqual(cp, 1.333333, places=5)
        self.assertAlmostEqual(cpu, 1.0, places=5)
        self.assertAlmostEqual(cpl, 1.666667, places=5)
        self.assertAlmostEqual(cpk, 1.0, places=5)

    def test_capable_process(self):
        # USL=22, LSL=18, xbar=20, sigma=0.25: Cp = 4/1.5 = 2.666667,
        # Cpk = 2 / 0.75 = 2.666667 (centered).
        cp, cpu, cpl, cpk = spc.capability_indices(22.0, 18.0, 20.0, 0.25)
        self.assertAlmostEqual(cp, 2.666667, places=5)
        self.assertAlmostEqual(cpk, 2.666667, places=5)

    def test_inverted_limits_raise(self):
        with self.assertRaises(ValueError):
            spc.capability_indices(8.0, 12.0, 10.0, 0.5)

    def test_non_positive_sigma_raises(self):
        with self.assertRaises(ValueError):
            spc.capability_indices(12.0, 8.0, 10.0, 0.0)
        with self.assertRaises(ValueError):
            spc.capability_indices(12.0, 8.0, 10.0, -0.5)


class OutOfControlRulesTest(unittest.TestCase):
    def test_rule1_point_beyond_3_sigma(self):
        # centerline 0, sigma 0.5: 3 sigma = 1.5, so 1.6 is beyond.
        self.assertEqual(spc.out_of_control_rules([0.0, 0.1, 1.6], 0.0, 0.5),
                         ["rule1"])

    def test_rule1_boundary_point_is_in_control(self):
        # Exactly 3 sigma (1.5) is not beyond 3 sigma.
        self.assertEqual(spc.out_of_control_rules([0.0, 1.5], 0.0, 0.5), [])

    def test_rule2_run_of_eight(self):
        # Eight points above the centerline trigger rule 2.
        pts = [0.1] * 8
        self.assertEqual(spc.out_of_control_rules(pts, 0.0, 0.5), ["rule2"])

    def test_rule2_seven_point_run_is_in_control(self):
        self.assertEqual(spc.out_of_control_rules([0.1] * 7, 0.0, 0.5), [])

    def test_rule3_two_of_three_beyond_2_sigma(self):
        # 2 sigma = 1.0; points at 1.1, 0.0, 1.1 put two of three beyond.
        self.assertEqual(
            spc.out_of_control_rules([1.1, 0.0, 1.1], 0.0, 0.5), ["rule3"]
        )

    def test_rule4_four_of_five_beyond_1_sigma(self):
        # 1 sigma = 0.5; four of five at 0.6 are beyond.
        self.assertEqual(
            spc.out_of_control_rules([0.6, 0.6, 0.0, 0.6, 0.6], 0.0, 0.5),
            ["rule4"],
        )

    def test_rule4_three_of_five_is_in_control(self):
        self.assertEqual(
            spc.out_of_control_rules([0.6, 0.6, 0.0, 0.6, 0.0], 0.0, 0.5), []
        )

    def test_in_control_sequence(self):
        # Small alternation stays inside all rule thresholds.
        pts = [0.1, -0.1, 0.1, -0.1, 0.1, -0.1, 0.1, -0.1, 0.1, -0.1]
        self.assertEqual(spc.out_of_control_rules(pts, 0.0, 0.5), [])

    def test_combined_rules(self):
        # A point at 1.6 (rule 1) plus an eight-point run (rule 2).
        pts = [1.6] + [0.1] * 8
        rules = spc.out_of_control_rules(pts, 0.0, 0.5)
        self.assertIn("rule1", rules)
        self.assertIn("rule2", rules)

    def test_insufficient_points_raise(self):
        with self.assertRaises(ValueError):
            spc.out_of_control_rules([0.1], 0.0, 0.5)
        with self.assertRaises(ValueError):
            spc.out_of_control_rules([], 0.0, 0.5)

    def test_non_positive_sigma_raises(self):
        with self.assertRaises(ValueError):
            spc.out_of_control_rules([0.1, 0.2], 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
