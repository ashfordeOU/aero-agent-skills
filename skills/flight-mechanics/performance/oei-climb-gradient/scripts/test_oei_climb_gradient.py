#!/usr/bin/env python3
"""Gate 3 contract test: one-engine-inoperative climb gradient.

Exercises scripts/oei_climb_gradient_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (OEI thrust
from the engine count; climb gradient from excess thrust over the
drag at weight; gradient percent; rate of climb; FAR-25.121(b)/(d)/(e)
minimum gradients for the engine count; clearance verdict; invalid
inputs raise ValueError.

Anchors:
- oei_thrust(400000, 4) = 300000 N (three of four engines)
- oei_thrust(300000, 2) = 150000 N (one of two engines)
- climb_gradient(120000, 90000, 600000) = 0.05 (excess 30000 N
  over 600000 N weight)
- gradient_percent(0.05) = 5.0
- rate_of_climb(0.05, 80) = 4.0 m/s
- second_segment_minimum: 2.4 / 2.7 / 3.0 percent (FAR-25.121(b))
- approach_climb_minimum: 2.1 / 2.4 / 2.7 percent (FAR-25.121(d))
- landing_climb_minimum() = 3.2 percent (FAR-25.121(e))
- meets_minimum(2.5, 2.4) is True; meets_minimum(2.3, 2.4) is False
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import oei_climb_gradient_logic as ocg  # noqa: E402


class OeiThrustTest(unittest.TestCase):
    def test_anchor_twin(self):
        self.assertAlmostEqual(ocg.oei_thrust(300000, 2), 150000.0)

    def test_anchor_quad(self):
        self.assertAlmostEqual(ocg.oei_thrust(400000, 4), 300000.0)

    def test_multi_failure(self):
        self.assertAlmostEqual(ocg.oei_thrust(400000, 4, failed_engines=2), 200000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocg.oei_thrust(0, 2)
        with self.assertRaises(ValueError):
            ocg.oei_thrust(-1, 2)
        with self.assertRaises(ValueError):
            ocg.oei_thrust(300000, 1)
        with self.assertRaises(ValueError):
            ocg.oei_thrust(300000, 2.5)
        with self.assertRaises(ValueError):
            ocg.oei_thrust(300000, 2, failed_engines=0)
        with self.assertRaises(ValueError):
            ocg.oei_thrust(300000, 2, failed_engines=2)


class ClimbGradientTest(unittest.TestCase):
    def test_anchor_gradient(self):
        self.assertAlmostEqual(ocg.climb_gradient(120000, 90000, 600000), 0.05)

    def test_anchor_percent(self):
        self.assertAlmostEqual(ocg.gradient_percent(0.05), 5.0)

    def test_negative_gradient_allowed(self):
        # Drag above the OEI thrust: no climb, gradient negative.
        self.assertAlmostEqual(ocg.climb_gradient(90000, 120000, 600000), -0.05)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocg.climb_gradient(120000, 90000, 0)
        with self.assertRaises(ValueError):
            ocg.climb_gradient(120000, -1, 600000)
        with self.assertRaises(ValueError):
            ocg.climb_gradient(-1, 90000, 600000)


class RateOfClimbTest(unittest.TestCase):
    def test_anchor_roc(self):
        self.assertAlmostEqual(ocg.rate_of_climb(0.05, 80), 4.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocg.rate_of_climb(0.05, 0)
        with self.assertRaises(ValueError):
            ocg.rate_of_climb(0.05, -10)


class MinimumGradientTest(unittest.TestCase):
    def test_second_segment_minimums(self):
        self.assertAlmostEqual(ocg.second_segment_minimum(2), 2.4)
        self.assertAlmostEqual(ocg.second_segment_minimum(3), 2.7)
        self.assertAlmostEqual(ocg.second_segment_minimum(4), 3.0)

    def test_approach_climb_minimums(self):
        self.assertAlmostEqual(ocg.approach_climb_minimum(2), 2.1)
        self.assertAlmostEqual(ocg.approach_climb_minimum(3), 2.4)
        self.assertAlmostEqual(ocg.approach_climb_minimum(4), 2.7)

    def test_landing_climb_minimum(self):
        self.assertAlmostEqual(ocg.landing_climb_minimum(), 3.2)

    def test_invalid_engine_count_raises(self):
        with self.assertRaises(ValueError):
            ocg.second_segment_minimum(1)
        with self.assertRaises(ValueError):
            ocg.second_segment_minimum(5)
        with self.assertRaises(ValueError):
            ocg.approach_climb_minimum(0)


class ClearanceTest(unittest.TestCase):
    def test_clears_minimum(self):
        self.assertTrue(ocg.meets_minimum(2.5, 2.4))
        self.assertTrue(ocg.meets_minimum(2.4, 2.4))

    def test_fails_minimum(self):
        self.assertFalse(ocg.meets_minimum(2.3, 2.4))


class TwinScenarioTest(unittest.TestCase):
    def test_second_segment_clearance(self):
        # 2 x 130 kN twin, one engine out, drag 70 kN at V2,
        # weight 650 kN: gradient clears the 2.4 percent minimum.
        thrust = ocg.oei_thrust(260000, 2)
        grad = ocg.climb_gradient(thrust, 70000, 650000)
        pct = ocg.gradient_percent(grad)
        self.assertAlmostEqual(thrust, 130000.0)
        self.assertAlmostEqual(pct, 60000.0 / 650000.0 * 100.0)
        self.assertTrue(ocg.meets_minimum(pct, ocg.second_segment_minimum(2)))

    def test_second_segment_failure(self):
        # Same twin with drag 125 kN at V2: gradient below the
        # 2.4 percent minimum, the takeoff does not clear.
        thrust = ocg.oei_thrust(260000, 2)
        grad = ocg.climb_gradient(thrust, 125000, 650000)
        pct = ocg.gradient_percent(grad)
        self.assertAlmostEqual(pct, 5000.0 / 650000.0 * 100.0)
        self.assertFalse(ocg.meets_minimum(pct, ocg.second_segment_minimum(2)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
