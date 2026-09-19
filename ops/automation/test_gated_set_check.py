#!/usr/bin/env python3
"""Detector tests for gated-set-check.

The check passed every run and had never been shown to fail, which is the
same thing as not knowing whether it works. It reads the gated-standards
count out of standards-map.yaml and refuses a document that states a
different one.

Each case here plants a claim the check must reject, beside a neighbouring
claim it must leave alone. The negative cases carry as much weight as the
positives: a scanner that flags everything is as useless as one that flags
nothing.

Run: python3 ops/automation/test_gated_set_check.py
(unittest writes OK on stderr; capture both streams.)
"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "gated_set_check", _HERE / "gated_set_check.py")
gsc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gsc)

GATED, TOTAL = 18, 30          # the canonical pair this tree carries


def scan(text):
    """Run the real scanner over one throwaway document."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "doc.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return gsc.scan_claims(p, GATED, TOTAL)


class StaleGatedCounts(unittest.TestCase):

    def test_the_correct_pair_is_accepted(self):
        self.assertEqual(scan("It covers 30 standards, 18 gated standards."),
                         [])

    # R1: "<N> gated standards"
    def test_a_wrong_gated_count_is_rejected(self):
        # The defect this gate exists for: a document left saying 9 after the
        # gated set grew to 18.
        self.assertTrue(scan("The library carries 9 gated standards."))

    def test_the_spelled_out_form_is_caught_too(self):
        # A stale count written as a word is still a stale count.
        self.assertTrue(scan("The library carries nine gated standards."))

    # R2: "covers|maps|spans <N> standards"
    def test_a_wrong_map_total_is_rejected(self):
        self.assertTrue(scan("The map covers 27 standards."))

    # R3: "all <N> of the gated standards"
    def test_the_all_of_the_form_is_caught(self):
        self.assertTrue(scan("Summaries exist for all 9 of the gated standards."))

    def test_an_unrelated_number_is_left_alone(self):
        # 18 and 30 are ordinary numbers. The check must key on the CLAIM
        # shape, not the digits, or every document becomes a finding.
        self.assertEqual(scan("The rotor turns at 30 rpm across 18 blades."),
                         [])

    def test_a_standards_count_that_is_not_a_coverage_claim_is_left_alone(self):
        # "27 standards were reviewed" is not a claim about what the map
        # covers, so it is none of this check's business.
        self.assertEqual(scan("27 standards were reviewed in the audit."), [])

    def test_a_clean_document_produces_nothing(self):
        self.assertEqual(scan("No counts are stated in this paragraph."), [])


class Contract(unittest.TestCase):

    def test_scan_returns_a_list_not_a_bool(self):
        # The caller counts findings; a bool would collapse "three problems"
        # into "a problem" and the operator would fix one and move on.
        self.assertIsInstance(scan("It carries 9 gated standards."), list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
