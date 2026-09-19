#!/usr/bin/env python3
"""Detector tests for the publish-health check.

Every verdict gets a case that fires and a neighbouring case that does not.
The point of this check is that a broken publish pipe cannot hide behind a
green tree, so the cases that matter most are the ones asserting it goes RED
-- and the one asserting that "could not check" is not "fine".

Run: python3 ops/automation/test_publish_health.py
(unittest writes OK on stderr; capture both streams.)
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "publish_health", _HERE / "publish-health.py")
ph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ph)


class Drift(unittest.TestCase):
    """The band is the unit: minutes of lag is normal, a band is a defect."""

    def test_identical_counts_are_current(self):
        self.assertEqual(ph.decide(3189, 3189)[0], ph.OK)

    def test_small_lag_inside_the_band_is_tolerated(self):
        # A wave lands on dev and publishes an hour later. Not a defect.
        self.assertEqual(ph.decide(3189, 3150)[0], ph.OK)

    def test_exactly_the_tolerance_is_still_tolerated(self):
        self.assertEqual(ph.decide(3189, 3089, tolerance=100)[0], ph.OK)

    def test_one_past_the_tolerance_is_stale(self):
        self.assertEqual(ph.decide(3190, 3089, tolerance=100)[0], ph.STALE)

    def test_the_real_2026_09_19_outage_is_caught(self):
        # The case this check was written for: 18 hours, three aborts,
        # every dev gate green, nothing reported.
        verdict, drift = ph.decide(3189, 2517)
        self.assertEqual(verdict, ph.STALE)
        self.assertEqual(drift, 672)

    def test_public_ahead_of_dev_is_its_own_verdict(self):
        # Not stale -- something else is wrong (out-of-band push, dev reset).
        # Reporting it as "stale" would send someone to the wrong log.
        verdict, drift = ph.decide(3000, 3100)
        self.assertEqual(verdict, ph.AHEAD)
        self.assertEqual(drift, -100)

    def test_a_missing_count_is_refused_not_defaulted(self):
        # Defaulting an unknown to 0 would read as a catastrophic drift, or
        # worse, as agreement. Neither is honest.
        with self.assertRaises(ValueError):
            ph.decide(3189, None)
        with self.assertRaises(ValueError):
            ph.decide(None, 3189)

    def test_tolerance_is_configurable(self):
        self.assertEqual(ph.decide(3189, 3150, tolerance=10)[0], ph.STALE)


class ExitContract(unittest.TestCase):
    """2 is not a pass."""

    def test_unverifiable_is_not_zero(self):
        # gh absent -> exit 2. The whole point: a check that cannot run must
        # not report success.
        real = ph.gh_bin
        try:
            ph.gh_bin = lambda: None
            self.assertEqual(ph.main([]), 2)
        finally:
            ph.gh_bin = real


if __name__ == "__main__":
    unittest.main(verbosity=2)
