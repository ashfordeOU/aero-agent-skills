#!/usr/bin/env python3
"""Gate 3 contract test: DO-160 lightning protection (paraphrase).

Exercises scripts/lightning_protection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - test level
range checks (1-5), waveform set support (A-H), and the pass
verdict over physical damage, upset, and latch-up flags; invalid
inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lightning_protection_logic as lp  # noqa: E402


class TestLevelRangeTest(unittest.TestCase):
    def test_in_range(self):
        self.assertTrue(lp.test_level_in_range(3))

    def test_above_range(self):
        self.assertFalse(lp.test_level_in_range(6))

    def test_below_range(self):
        self.assertFalse(lp.test_level_in_range(0))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            lp.test_level_in_range("3")
        with self.assertRaises(ValueError):
            lp.test_level_in_range(3.5)


class WaveformSupportTest(unittest.TestCase):
    def test_supported_letter(self):
        self.assertTrue(lp.waveform_supported("C"))

    def test_unsupported_letter(self):
        self.assertFalse(lp.waveform_supported("z"))

    def test_empty_string(self):
        self.assertFalse(lp.waveform_supported(""))

    def test_lowercase_letter(self):
        self.assertTrue(lp.waveform_supported("c"))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            lp.waveform_supported(7)


class PassVerdictTest(unittest.TestCase):
    def test_no_faults_passes(self):
        self.assertTrue(lp.pass_verdict(False, False, False))

    def test_physical_damage_fails(self):
        self.assertFalse(lp.pass_verdict(True, False, False))

    def test_upset_fails(self):
        self.assertFalse(lp.pass_verdict(False, True, False))

    def test_latch_up_fails(self):
        self.assertFalse(lp.pass_verdict(False, False, True))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            lp.pass_verdict("yes", False, False)
        with self.assertRaises(ValueError):
            lp.pass_verdict(False, 1, False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
