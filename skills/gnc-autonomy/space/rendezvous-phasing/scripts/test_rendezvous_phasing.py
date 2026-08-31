#!/usr/bin/env python3
"""Gate 3 contract test: orbital rendezvous phasing.

Exercises scripts/rendezvous_phasing_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 — phasing drift
rate from phase angle and transfer time, delta-v for a phasing orbit
around a circular orbit, closing rate checks, and invalid inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rendezvous_phasing_logic as rp  # noqa: E402

R_LEO = 6.878e6  # m, LEO at 500 km altitude


class DriftRateTest(unittest.TestCase):
    def test_quarter_phase_over_hour(self):
        self.assertAlmostEqual(rp.drift_rate_required(90.0, 3600.0), 0.025)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rp.drift_rate_required(-10.0, 3600.0)
        with self.assertRaises(ValueError):
            rp.drift_rate_required(90.0, 0.0)


class DeltaVTest(unittest.TestCase):
    def test_leo_phasing_dv_band(self):
        dv = rp.delta_v_for_drift(R_LEO, 90.0, 5700.0)
        self.assertTrue(300.0 <= dv <= 700.0, "dv %r m/s" % dv)

    def test_larger_phase_larger_dv(self):
        small = rp.delta_v_for_drift(R_LEO, 45.0, 5700.0)
        large = rp.delta_v_for_drift(R_LEO, 90.0, 5700.0)
        self.assertLess(small, large)

    def test_longer_time_smaller_dv(self):
        short = rp.delta_v_for_drift(R_LEO, 90.0, 5700.0)
        long = rp.delta_v_for_drift(R_LEO, 90.0, 11400.0)
        self.assertGreater(short, long)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rp.delta_v_for_drift(0.0, 90.0, 5700.0)
        with self.assertRaises(ValueError):
            rp.delta_v_for_drift(-1.0, 90.0, 5700.0)
        with self.assertRaises(ValueError):
            rp.delta_v_for_drift(R_LEO, 90.0, -1.0)


class ClosingRateTest(unittest.TestCase):
    def test_within_allowed(self):
        self.assertTrue(rp.closing_rate_ok(5.0, 10.0))
        self.assertTrue(rp.closing_rate_ok(10.0, 10.0))

    def test_exceeding_allowed(self):
        self.assertFalse(rp.closing_rate_ok(12.0, 10.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rp.closing_rate_ok(-1.0, 10.0)
        with self.assertRaises(ValueError):
            rp.closing_rate_ok(5.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
