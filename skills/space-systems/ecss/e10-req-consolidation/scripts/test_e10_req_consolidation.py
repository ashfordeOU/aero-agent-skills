#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C requirement consolidation.

Exercises scripts/e10_req_consolidation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a requirement
subject shared by two or more products with one agreed value is a
consolidation candidate; a shared subject with disagreeing values is a
flow-down conflict, not a candidate; consolidating a candidate returns a
support-spec-targeted requirement plus the superseded per-product ids;
resolving a conflict without a recorded rationale, or on a subject with no
conflict, raises ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_consolidation_logic as rc  # noqa: E402


REQUIREMENTS = [
    {"id": "REQ-1", "product": "EQUIP-A", "subject": "operating-temp-range", "value": "-20C..+50C"},
    {"id": "REQ-2", "product": "EQUIP-B", "subject": "operating-temp-range", "value": "-20C..+50C"},
    {"id": "REQ-3", "product": "EQUIP-C", "subject": "operating-temp-range", "value": "-20C..+50C"},
    {"id": "REQ-4", "product": "EQUIP-A", "subject": "random-vibe-level", "value": "6.0 Grms"},
    {"id": "REQ-5", "product": "EQUIP-B", "subject": "random-vibe-level", "value": "8.1 Grms"},
    {"id": "REQ-6", "product": "EQUIP-A", "subject": "mass-budget", "value": "12.0 kg"},
]


class SharedSubjectsTest(unittest.TestCase):
    def test_shared_subjects_span_two_or_more_products(self):
        self.assertEqual(
            rc.shared_subjects(REQUIREMENTS),
            ["operating-temp-range", "random-vibe-level"],
        )

    def test_single_product_subject_not_shared(self):
        self.assertNotIn("mass-budget", rc.shared_subjects(REQUIREMENTS))

    def test_min_products_threshold(self):
        self.assertEqual(rc.shared_subjects(REQUIREMENTS, min_products=3), ["operating-temp-range"])


class DetectConflictsTest(unittest.TestCase):
    def test_agreeing_subject_has_no_conflict(self):
        self.assertNotIn("operating-temp-range", rc.detect_conflicts(REQUIREMENTS))

    def test_disagreeing_subject_is_a_conflict(self):
        conflicts = rc.detect_conflicts(REQUIREMENTS)
        self.assertEqual(
            conflicts["random-vibe-level"],
            [("EQUIP-A", "6.0 Grms"), ("EQUIP-B", "8.1 Grms")],
        )

    def test_single_product_subject_has_no_conflict(self):
        self.assertNotIn("mass-budget", rc.detect_conflicts(REQUIREMENTS))


class ConsolidationCandidatesTest(unittest.TestCase):
    def test_agreeing_shared_subject_is_a_candidate(self):
        self.assertEqual(rc.consolidation_candidates(REQUIREMENTS), ["operating-temp-range"])

    def test_conflicted_subject_excluded(self):
        self.assertNotIn("random-vibe-level", rc.consolidation_candidates(REQUIREMENTS))

    def test_single_product_subject_excluded(self):
        self.assertNotIn("mass-budget", rc.consolidation_candidates(REQUIREMENTS))


class ConsolidateTest(unittest.TestCase):
    def test_consolidates_into_support_spec(self):
        consolidated, superseded = rc.consolidate(
            REQUIREMENTS, "operating-temp-range", "SPT-ENV-01"
        )
        self.assertEqual(
            consolidated,
            {"subject": "operating-temp-range", "value": "-20C..+50C", "product": "SPT-ENV-01"},
        )
        self.assertEqual(superseded, ["REQ-1", "REQ-2", "REQ-3"])

    def test_conflicted_subject_rejected(self):
        with self.assertRaises(ValueError):
            rc.consolidate(REQUIREMENTS, "random-vibe-level", "SPT-ENV-01")

    def test_single_product_subject_rejected(self):
        with self.assertRaises(ValueError):
            rc.consolidate(REQUIREMENTS, "mass-budget", "SPT-ENV-01")

    def test_unknown_subject_rejected(self):
        with self.assertRaises(ValueError):
            rc.consolidate(REQUIREMENTS, "not-a-subject", "SPT-ENV-01")


class ResolveConflictTest(unittest.TestCase):
    def test_resolve_lists_deltas_to_the_losing_products(self):
        deltas = rc.resolve_conflict(
            REQUIREMENTS, "random-vibe-level", "8.1 Grms", "higher envelope covers both products"
        )
        self.assertEqual(deltas, [("EQUIP-A", "6.0 Grms")])

    def test_resolve_to_untouched_value_lists_all_products(self):
        deltas = rc.resolve_conflict(
            REQUIREMENTS, "random-vibe-level", "7.0 Grms", "compromise envelope"
        )
        self.assertEqual(deltas, [("EQUIP-A", "6.0 Grms"), ("EQUIP-B", "8.1 Grms")])

    def test_resolve_without_rationale_raises(self):
        with self.assertRaises(ValueError):
            rc.resolve_conflict(REQUIREMENTS, "random-vibe-level", "8.1 Grms", "")

    def test_resolve_subject_without_conflict_raises(self):
        with self.assertRaises(ValueError):
            rc.resolve_conflict(REQUIREMENTS, "operating-temp-range", "-20C..+50C", "n/a")


if __name__ == "__main__":
    unittest.main(verbosity=2)
