#!/usr/bin/env python3
"""Gate 3 contract test: DO-330 tool qualification.

Exercises scripts/tool_qualification_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - tool criteria
1-5 map to TQL-1..TQL-5, lower TQL ranks are stricter and satisfy
higher-numbered requirements, the governing criterion is the maximum
applicable one, TOR artifacts completeness is checked, and invalid
inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tool_qualification_logic as tql  # noqa: E402


class CriterionMappingTest(unittest.TestCase):
    def test_criteria_map_to_tqls(self):
        for criterion in range(1, 6):
            with self.subTest(criterion=criterion):
                self.assertEqual(
                    tql.tql_for_criterion(criterion),
                    "TQL-%d" % criterion,
                )

    def test_out_of_range_criterion_raises(self):
        for bad in (0, 6, -1, 3.5, "3", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    tql.tql_for_criterion(bad)


class RankTest(unittest.TestCase):
    def test_rank_parses(self):
        for n in range(1, 6):
            with self.subTest(n=n):
                self.assertEqual(tql.tql_rank("TQL-%d" % n), n)

    def test_malformed_tql_raises(self):
        for bad in ("TQL-0", "TQL-6", "tql-1", "TQL", "TQL-", "", 3, None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    tql.tql_rank(bad)


class MeetsRequirementTest(unittest.TestCase):
    def test_stricter_meets_looser(self):
        self.assertTrue(tql.tql_meets_requirement("TQL-1", "TQL-4"))
        self.assertTrue(tql.tql_meets_requirement("TQL-2", "TQL-2"))
        self.assertTrue(tql.tql_meets_requirement("TQL-5", "TQL-5"))

    def test_looser_does_not_meet_stricter(self):
        self.assertFalse(tql.tql_meets_requirement("TQL-4", "TQL-1"))
        self.assertFalse(tql.tql_meets_requirement("TQL-3", "TQL-2"))


class ArtifactsTest(unittest.TestCase):
    def test_complete_artifact_set(self):
        complete, missing = tql.tor_artifacts_complete(
            {"tor", "qualification_plan", "tool_accomplishment_summary"}
        )
        self.assertTrue(complete)
        self.assertEqual(missing, [])

    def test_incomplete_artifact_set(self):
        complete, missing = tql.tor_artifacts_complete(
            {"qualification_plan", "tool_accomplishment_summary"}
        )
        self.assertFalse(complete)
        self.assertEqual(missing, ["tor"])

    def test_empty_artifact_set(self):
        complete, missing = tql.tor_artifacts_complete(set())
        self.assertFalse(complete)
        self.assertEqual(
            sorted(missing),
            ["qualification_plan", "tool_accomplishment_summary", "tor"],
        )


class GoverningCriterionTest(unittest.TestCase):
    def test_highest_criterion_governs(self):
        self.assertEqual(tql.tool_category_from_criteria([1, 3, 5]), 5)
        self.assertEqual(tql.tool_category_from_criteria([4]), 4)
        self.assertEqual(tql.tool_category_from_criteria([1, 1]), 1)

    def test_empty_criteria_raises(self):
        with self.assertRaises(ValueError):
            tql.tool_category_from_criteria([])

    def test_invalid_criterion_raises(self):
        for bad in ([3, 7], ["3"], [None], "abc"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    tql.tool_category_from_criteria(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
