#!/usr/bin/env python3
"""Gate 3 contract test: ARP4761A common cause analysis.

Exercises scripts/common_cause_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - zonal safety
analysis item scoring and verdicts, common cause analysis set
completeness (ZSA/PRA/CMA), and invalid-input handling.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common_cause_analysis_logic as cca  # noqa: E402


class ZsaItemTest(unittest.TestCase):
    def test_all_pass_low_risk(self):
        items = [("fire", True), ("fluid", True), ("birds", True)]
        score, verdict = cca.zsa_zone_check(items)
        self.assertAlmostEqual(score, 0.0)
        self.assertEqual(verdict, "ok")

    def test_failures_raise_score(self):
        items = [("fire", True), ("fluid", False), ("birds", False)]
        score, verdict = cca.zsa_zone_check(items)
        self.assertGreater(score, 0.0)
        self.assertEqual(verdict, "action")

    def test_empty_zone_raises(self):
        with self.assertRaises(ValueError):
            cca.zsa_zone_check([])


class CcaCompletenessTest(unittest.TestCase):
    def test_full_set_complete(self):
        self.assertTrue(cca.cca_complete(["zsa", "pra", "cma"]))

    def test_partial_set_incomplete(self):
        self.assertFalse(cca.cca_complete(["zsa", "pra"]))

    def test_unknown_analysis_raises(self):
        with self.assertRaises(ValueError):
            cca.cca_complete(["zsa", "tea"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
