#!/usr/bin/env python3
"""Gate 3 contract test: conceptual payload-range diagram.

Exercises scripts/payload_range_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - Breguet range factor and
range, range for a payload and fuel mass under a reserve policy, the
max-payload and max-fuel corner points, the ferry range, and the
payload at a design range; invalid inputs raise ValueError.

Reference case: OEW 50,000 kg, max payload 20,000 kg, MTOW 100,000
kg, fuel capacity 40,000 kg, reserve fraction 0.1, range factor
1e7 m. Point A (max payload): fuel 30,000 kg (MTOW-limited), range
3,147,107.45 m. Point B (max fuel): payload 10,000 kg, range
4,462,871.03 m. Point C (ferry): 5,108,256.24 m.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import payload_range_logic as pr  # noqa: E402

OEW = 50000.0
MAX_PAYLOAD = 20000.0
MTOW = 100000.0
FUEL_CAP = 40000.0
RF = 0.1
K = 1e7


class RangeFactorTest(unittest.TestCase):
    def test_range_factor_numeric(self):
        k = pr.range_factor(250.0, 1.5e-5, 18.0)
        self.assertAlmostEqual(k, 30591486.38933785, places=2)

    def test_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            pr.range_factor(0.0, 1.5e-5, 18.0)
        with self.assertRaises(ValueError):
            pr.range_factor(250.0, 0.0, 18.0)
        with self.assertRaises(ValueError):
            pr.range_factor(250.0, 1.5e-5, -18.0)


class BreguetRangeTest(unittest.TestCase):
    def test_breguet_numeric(self):
        self.assertAlmostEqual(
            pr.breguet_range(1e7, 100000.0, 80000.0), 2231435.5131420977,
            places=2)

    def test_ratio_requires_w0_gt_w1(self):
        with self.assertRaises(ValueError):
            pr.breguet_range(1e7, 100000.0, 100000.0)
        with self.assertRaises(ValueError):
            pr.breguet_range(1e7, 100000.0, 120000.0)
        with self.assertRaises(ValueError):
            pr.breguet_range(1e7, 100000.0, 0.0)

    def test_nonpositive_factor_raises(self):
        with self.assertRaises(ValueError):
            pr.breguet_range(0.0, 100000.0, 80000.0)


class RangeForFuelTest(unittest.TestCase):
    def test_range_with_reserve_numeric(self):
        self.assertAlmostEqual(
            pr.range_for_fuel(OEW, MAX_PAYLOAD, 30000.0, RF, K),
            3147107.4483970017, places=2)

    def test_zero_fuel_gives_zero_range(self):
        self.assertEqual(pr.range_for_fuel(OEW, MAX_PAYLOAD, 0.0, RF, K),
                         0.0)

    def test_invalid_reserve_fraction_raises(self):
        with self.assertRaises(ValueError):
            pr.range_for_fuel(OEW, MAX_PAYLOAD, 30000.0, 1.0, K)
        with self.assertRaises(ValueError):
            pr.range_for_fuel(OEW, MAX_PAYLOAD, 30000.0, -0.1, K)

    def test_negative_fuel_raises(self):
        with self.assertRaises(ValueError):
            pr.range_for_fuel(OEW, MAX_PAYLOAD, -1.0, RF, K)


class MaxPayloadPointTest(unittest.TestCase):
    def test_point_a_numeric(self):
        a = pr.max_payload_point(OEW, MAX_PAYLOAD, MTOW, FUEL_CAP, RF, K)
        self.assertAlmostEqual(a["payload"], MAX_PAYLOAD, places=2)
        self.assertAlmostEqual(a["fuel"], 30000.0, places=2)
        self.assertAlmostEqual(a["range"], 3147107.4483970017, places=2)
        self.assertTrue(a["mtow_limited"])

    def test_capacity_binding_case(self):
        a = pr.max_payload_point(OEW, MAX_PAYLOAD, MTOW, 20000.0, RF, K)
        self.assertAlmostEqual(a["fuel"], 20000.0, places=2)
        self.assertAlmostEqual(a["range"], 2231435.5131420977, places=2)
        self.assertFalse(a["mtow_limited"])

    def test_mtow_too_small_raises(self):
        with self.assertRaises(ValueError):
            pr.max_payload_point(OEW, MAX_PAYLOAD, 60000.0, FUEL_CAP, RF, K)


class MaxFuelPointTest(unittest.TestCase):
    def test_point_b_numeric(self):
        b = pr.max_fuel_point(OEW, MAX_PAYLOAD, MTOW, FUEL_CAP, RF, K)
        self.assertAlmostEqual(b["payload"], 10000.0, places=2)
        self.assertAlmostEqual(b["fuel"], FUEL_CAP, places=2)
        self.assertAlmostEqual(b["range"], 4462871.0262841955, places=2)

    def test_full_fuel_exceeds_mtow_raises(self):
        with self.assertRaises(ValueError):
            pr.max_fuel_point(OEW, MAX_PAYLOAD, 80000.0, FUEL_CAP, RF, K)


class FerryRangeTest(unittest.TestCase):
    def test_ferry_numeric(self):
        self.assertAlmostEqual(
            pr.ferry_range(OEW, MTOW, FUEL_CAP, RF, K),
            5108256.237659907, places=2)

    def test_full_fuel_exceeds_mtow_raises(self):
        with self.assertRaises(ValueError):
            pr.ferry_range(OEW, 80000.0, FUEL_CAP, RF, K)

    def test_zero_capacity_gives_zero_range(self):
        self.assertEqual(pr.ferry_range(OEW, MTOW, 0.0, RF, K), 0.0)


class PayloadAtDesignRangeTest(unittest.TestCase):
    def test_descending_segment_numeric(self):
        self.assertAlmostEqual(
            pr.payload_at_design_range(OEW, MAX_PAYLOAD, MTOW, FUEL_CAP,
                                       RF, K, 4000000.0),
            13368.894003959926, places=2)

    def test_inside_max_payload_segment_returns_max_payload(self):
        self.assertEqual(
            pr.payload_at_design_range(OEW, MAX_PAYLOAD, MTOW, FUEL_CAP,
                                       RF, K, 2000000.0),
            MAX_PAYLOAD)
        self.assertEqual(
            pr.payload_at_design_range(OEW, MAX_PAYLOAD, MTOW, FUEL_CAP,
                                       RF, K, 0.0),
            MAX_PAYLOAD)

    def test_beyond_ferry_range_raises(self):
        with self.assertRaises(ValueError):
            pr.payload_at_design_range(OEW, MAX_PAYLOAD, MTOW, FUEL_CAP,
                                       RF, K, 5500000.0)

    def test_negative_design_range_raises(self):
        with self.assertRaises(ValueError):
            pr.payload_at_design_range(OEW, MAX_PAYLOAD, MTOW, FUEL_CAP,
                                       RF, K, -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
