#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 4.6 retesting rules.

Exercises scripts/e1003_retesting_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a design modification that
touches the qualified envelope forces requalification while one kept
outside it does not; storage outside spec conditions or beyond the
qualified shelf life forces a retest; a re-flown article is either
routed to repair-and-requalify or still needs a fresh acceptance-level
retest, never a bare re-acceptance; a qualification article that
consumed damaging margin or shows damage is disallowed from flight,
and a clean one still needs an acceptance-level retest; and a
retesting review is only complete when every case in scope has a
disposition.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_retesting_logic as retest  # noqa: E402


class EvaluateDesignModificationTest(unittest.TestCase):
    def test_envelope_change_requires_requalification(self):
        self.assertEqual(
            retest.evaluate_design_modification(True), "requalification_required"
        )

    def test_change_outside_envelope_needs_no_retest(self):
        self.assertEqual(
            retest.evaluate_design_modification(False), "no_retest_required"
        )


class EvaluateStorageRetestTest(unittest.TestCase):
    def test_within_shelf_life_and_spec_needs_no_retest(self):
        self.assertEqual(
            retest.evaluate_storage_retest(6.0, 12.0, True), "no_retest_required"
        )

    def test_exceeding_shelf_life_forces_retest(self):
        self.assertEqual(
            retest.evaluate_storage_retest(18.0, 12.0, True), "retest_required"
        )

    def test_out_of_spec_conditions_forces_retest_even_within_shelf_life(self):
        self.assertEqual(
            retest.evaluate_storage_retest(3.0, 12.0, False), "retest_required"
        )

    def test_at_exact_shelf_life_boundary_needs_no_retest(self):
        self.assertEqual(
            retest.evaluate_storage_retest(12.0, 12.0, True), "no_retest_required"
        )


class EvaluateReflownArticleTest(unittest.TestCase):
    def test_damage_found_routes_to_repair_and_requalify(self):
        self.assertEqual(
            retest.evaluate_reflown_article(True), "repair_and_requalify"
        )

    def test_clean_inspection_still_needs_acceptance_retest(self):
        self.assertEqual(
            retest.evaluate_reflown_article(False), "acceptance_retest_required"
        )


class EvaluateQualificationArticleForFlightTest(unittest.TestCase):
    def test_excess_margin_consumption_disallows_flight(self):
        self.assertEqual(
            retest.evaluate_qualification_article_for_flight(True, False),
            "disallowed_for_flight",
        )

    def test_damage_found_disallows_flight(self):
        self.assertEqual(
            retest.evaluate_qualification_article_for_flight(False, True),
            "disallowed_for_flight",
        )

    def test_both_findings_disallows_flight(self):
        self.assertEqual(
            retest.evaluate_qualification_article_for_flight(True, True),
            "disallowed_for_flight",
        )

    def test_clean_article_still_needs_acceptance_retest(self):
        self.assertEqual(
            retest.evaluate_qualification_article_for_flight(False, False),
            "acceptance_retest_required",
        )


class EvaluateRetestingCaseTest(unittest.TestCase):
    def test_design_modification_dispatch(self):
        case = {
            "id": "CASE-001",
            "trigger": "design_modification",
            "affects_qualified_envelope": True,
        }
        self.assertEqual(
            retest.evaluate_retesting_case(case),
            {"id": "CASE-001", "trigger": "design_modification", "status": "requalification_required"},
        )

    def test_storage_after_test_dispatch(self):
        case = {
            "id": "CASE-002",
            "trigger": "storage_after_test",
            "storage_duration_months": 4.0,
            "qualified_shelf_life_months": 12.0,
            "storage_conditions_within_spec": True,
        }
        self.assertEqual(
            retest.evaluate_retesting_case(case),
            {"id": "CASE-002", "trigger": "storage_after_test", "status": "no_retest_required"},
        )

    def test_reflown_article_dispatch(self):
        case = {
            "id": "CASE-003",
            "trigger": "reflown_article",
            "inspection_damage_found": False,
        }
        self.assertEqual(
            retest.evaluate_retesting_case(case),
            {"id": "CASE-003", "trigger": "reflown_article", "status": "acceptance_retest_required"},
        )

    def test_qualification_article_for_flight_dispatch(self):
        case = {
            "id": "CASE-004",
            "trigger": "qualification_article_for_flight",
            "margin_consumed_exceeds_limit": False,
            "damage_found": True,
        }
        self.assertEqual(
            retest.evaluate_retesting_case(case),
            {"id": "CASE-004", "trigger": "qualification_article_for_flight", "status": "disallowed_for_flight"},
        )

    def test_missing_id_raises(self):
        case = {
            "trigger": "design_modification",
            "affects_qualified_envelope": False,
        }
        with self.assertRaises(ValueError):
            retest.evaluate_retesting_case(case)

    def test_unknown_trigger_raises(self):
        case = {"id": "CASE-005", "trigger": "unobtanium_event"}
        with self.assertRaises(ValueError):
            retest.evaluate_retesting_case(case)


class BuildRetestingDispositionsTest(unittest.TestCase):
    CASES = [
        {
            "id": "CASE-001",
            "trigger": "design_modification",
            "affects_qualified_envelope": True,
        },
        {
            "id": "CASE-002",
            "trigger": "reflown_article",
            "inspection_damage_found": False,
        },
    ]

    def test_disposition_order_and_content(self):
        result = retest.build_retesting_dispositions(self.CASES)
        self.assertEqual(
            result,
            [
                {"id": "CASE-001", "trigger": "design_modification", "status": "requalification_required"},
                {"id": "CASE-002", "trigger": "reflown_article", "status": "acceptance_retest_required"},
            ],
        )

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            retest.build_retesting_dispositions(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        retest.build_retesting_dispositions(self.CASES)
        self.assertEqual(self.CASES, before)


class MissingRetestingDispositionsTest(unittest.TestCase):
    def test_detects_gap(self):
        dispositions = [
            {"id": "CASE-001", "trigger": "design_modification", "status": "no_retest_required"}
        ]
        self.assertEqual(
            retest.missing_retesting_dispositions(
                ["CASE-001", "CASE-002", "CASE-003"], dispositions
            ),
            ["CASE-002", "CASE-003"],
        )

    def test_no_gap(self):
        dispositions = [
            {"id": "CASE-001", "trigger": "design_modification", "status": "no_retest_required"}
        ]
        self.assertEqual(
            retest.missing_retesting_dispositions(["CASE-001"], dispositions), []
        )


class CloseOutRetestingReviewTest(unittest.TestCase):
    def test_all_dispositioned_closes_clean(self):
        dispositions = [
            {"id": "CASE-001", "trigger": "design_modification", "status": "requalification_required"},
            {"id": "CASE-002", "trigger": "reflown_article", "status": "acceptance_retest_required"},
        ]
        self.assertEqual(
            retest.close_out_retesting_review(["CASE-001", "CASE-002"], dispositions),
            (True, []),
        )

    def test_missing_case_blocks_closure(self):
        dispositions = [
            {"id": "CASE-001", "trigger": "design_modification", "status": "no_retest_required"}
        ]
        self.assertEqual(
            retest.close_out_retesting_review(["CASE-001", "CASE-002"], dispositions),
            (False, ["CASE-002"]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
