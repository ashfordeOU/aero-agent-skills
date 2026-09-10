#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex C SCR DRD check.

Exercises scripts/e10_scr_drd_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - required SCR content
sections, candidate-concept completeness, trade-criteria coverage,
feasibility classification, recommendation validity, overall
completeness report, and ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_scr_drd_logic as scrdrd  # noqa: E402


FULL_SCR = {
    "candidate_concepts": [
        {"id": "C1", "description": "Deployable-antenna concept."},
        {"id": "C2", "description": "Body-fixed-antenna concept."},
    ],
    "trade_summary": [
        {"concept_id": "C1", "criterion": "technical", "score": 8},
        {"concept_id": "C1", "criterion": "programmatic", "score": 7},
        {"concept_id": "C1", "criterion": "cost", "score": 6},
        {"concept_id": "C1", "criterion": "risk", "score": 7},
        {"concept_id": "C2", "criterion": "technical", "score": 5},
        {"concept_id": "C2", "criterion": "programmatic", "score": 6},
        {"concept_id": "C2", "criterion": "cost", "score": 9},
        {"concept_id": "C2", "criterion": "risk", "score": 5},
    ],
    "feasibility_assessment": [
        {"concept_id": "C1", "verdict": "feasible"},
        {"concept_id": "C2", "verdict": "feasible_with_risk"},
    ],
    "recommended_concept": "C1",
}

CONCEPT_IDS = ["C1", "C2"]


class MissingSectionsTest(unittest.TestCase):
    def test_complete_scr_has_no_missing_sections(self):
        self.assertEqual(scrdrd.missing_sections(FULL_SCR), [])

    def test_absent_section_flagged(self):
        scr = dict(FULL_SCR)
        del scr["trade_summary"]
        self.assertEqual(scrdrd.missing_sections(scr), ["trade_summary"])

    def test_blank_section_flagged(self):
        scr = dict(FULL_SCR)
        scr["candidate_concepts"] = []
        self.assertIn("candidate_concepts", scrdrd.missing_sections(scr))

    def test_order_matches_required_sections(self):
        self.assertEqual(scrdrd.missing_sections({}), list(scrdrd.REQUIRED_SECTIONS))

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            scrdrd.missing_sections(["candidate_concepts"])


class IncompleteConceptsTest(unittest.TestCase):
    def test_complete_concepts_have_no_gaps(self):
        self.assertEqual(
            scrdrd.incomplete_concepts(FULL_SCR["candidate_concepts"]), []
        )

    def test_missing_description_flagged(self):
        concepts = [
            {"id": "C1", "description": "Deployable-antenna concept."},
            {"id": "C2", "description": ""},
        ]
        self.assertEqual(scrdrd.incomplete_concepts(concepts), ["C2"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            scrdrd.incomplete_concepts([{"description": "no id here"}])


class MissingTradeCriteriaTest(unittest.TestCase):
    def test_full_coverage_has_no_gaps(self):
        self.assertEqual(
            scrdrd.missing_trade_criteria(FULL_SCR["trade_summary"], CONCEPT_IDS), {}
        )

    def test_partial_coverage_flagged(self):
        trade_summary = [
            entry
            for entry in FULL_SCR["trade_summary"]
            if not (entry["concept_id"] == "C2" and entry["criterion"] == "risk")
        ]
        gaps = scrdrd.missing_trade_criteria(trade_summary, CONCEPT_IDS)
        self.assertEqual(gaps, {"C2": ["risk"]})

    def test_concept_with_no_entries_flagged_on_all_criteria(self):
        gaps = scrdrd.missing_trade_criteria([], CONCEPT_IDS)
        self.assertEqual(gaps["C1"], list(scrdrd.TRADE_CRITERIA))
        self.assertEqual(gaps["C2"], list(scrdrd.TRADE_CRITERIA))

    def test_unknown_concept_id_raises(self):
        trade_summary = [{"concept_id": "GHOST", "criterion": "technical"}]
        with self.assertRaises(ValueError):
            scrdrd.missing_trade_criteria(trade_summary, CONCEPT_IDS)

    def test_unknown_criterion_raises(self):
        trade_summary = [{"concept_id": "C1", "criterion": "marketing"}]
        with self.assertRaises(ValueError):
            scrdrd.missing_trade_criteria(trade_summary, CONCEPT_IDS)


class ClassifyFeasibilityTest(unittest.TestCase):
    def test_mixed_verdicts_categorized(self):
        result = scrdrd.classify_feasibility(
            FULL_SCR["feasibility_assessment"], CONCEPT_IDS
        )
        self.assertEqual(result, {"not_feasible": [], "invalid": [], "missing": []})

    def test_not_feasible_flagged(self):
        assessment = [
            {"concept_id": "C1", "verdict": "not_feasible"},
            {"concept_id": "C2", "verdict": "feasible"},
        ]
        result = scrdrd.classify_feasibility(assessment, CONCEPT_IDS)
        self.assertEqual(result["not_feasible"], ["C1"])

    def test_invalid_verdict_flagged(self):
        assessment = [
            {"concept_id": "C1", "verdict": "maybe"},
            {"concept_id": "C2", "verdict": "feasible"},
        ]
        result = scrdrd.classify_feasibility(assessment, CONCEPT_IDS)
        self.assertEqual(result["invalid"], ["C1"])

    def test_missing_verdict_key_marks_invalid(self):
        assessment = [
            {"concept_id": "C1"},
            {"concept_id": "C2", "verdict": "feasible"},
        ]
        result = scrdrd.classify_feasibility(assessment, CONCEPT_IDS)
        self.assertEqual(result["invalid"], ["C1"])

    def test_missing_assessment_flagged(self):
        assessment = [{"concept_id": "C1", "verdict": "feasible"}]
        result = scrdrd.classify_feasibility(assessment, CONCEPT_IDS)
        self.assertEqual(result["missing"], ["C2"])

    def test_no_concept_id_raises(self):
        with self.assertRaises(ValueError):
            scrdrd.classify_feasibility([{"verdict": "feasible"}], CONCEPT_IDS)

    def test_unknown_concept_id_raises(self):
        with self.assertRaises(ValueError):
            scrdrd.classify_feasibility(
                [{"concept_id": "GHOST", "verdict": "feasible"}], CONCEPT_IDS
            )


class ValidateRecommendationTest(unittest.TestCase):
    def test_valid_recommendation_has_no_issues(self):
        self.assertEqual(
            scrdrd.validate_recommendation(
                "C1", CONCEPT_IDS, FULL_SCR["feasibility_assessment"]
            ),
            [],
        )

    def test_unknown_concept_flagged(self):
        self.assertEqual(
            scrdrd.validate_recommendation(
                "GHOST", CONCEPT_IDS, FULL_SCR["feasibility_assessment"]
            ),
            ["unknown_concept"],
        )

    def test_no_feasibility_assessment_flagged(self):
        self.assertEqual(
            scrdrd.validate_recommendation("C1", CONCEPT_IDS, []),
            ["no_feasibility_assessment"],
        )

    def test_not_feasible_recommendation_flagged(self):
        assessment = [{"concept_id": "C1", "verdict": "not_feasible"}]
        self.assertEqual(
            scrdrd.validate_recommendation("C1", CONCEPT_IDS, assessment),
            ["not_feasible"],
        )

    def test_empty_recommendation_raises(self):
        with self.assertRaises(ValueError):
            scrdrd.validate_recommendation(
                "", CONCEPT_IDS, FULL_SCR["feasibility_assessment"]
            )


class BuildCompletenessReportTest(unittest.TestCase):
    def test_fully_complete_scr(self):
        report = scrdrd.build_completeness_report(FULL_SCR)
        self.assertTrue(report["complete"])
        self.assertEqual(report["sections_missing"], [])
        self.assertEqual(report["concepts_incomplete"], [])
        self.assertEqual(report["trade_criteria_gaps"], {})
        self.assertEqual(report["recommendation_issues"], [])

    def test_known_textbook_case_multiple_violations(self):
        scr = {
            "candidate_concepts": [
                {"id": "C1", "description": "Deployable-antenna concept."},
                {"id": "C2", "description": ""},
            ],
            "trade_summary": [
                {"concept_id": "C1", "criterion": "technical", "score": 8},
            ],
            "feasibility_assessment": [
                {"concept_id": "C1", "verdict": "not_feasible"},
            ],
            "recommended_concept": "C1",
        }
        report = scrdrd.build_completeness_report(scr)
        self.assertFalse(report["complete"])
        self.assertEqual(report["concepts_incomplete"], ["C2"])
        self.assertIn("C1", report["trade_criteria_gaps"])
        self.assertIn("C2", report["trade_criteria_gaps"])
        self.assertEqual(report["feasibility_issues"]["missing"], ["C2"])
        self.assertEqual(report["recommendation_issues"], ["not_feasible"])

    def test_not_feasible_non_recommended_concept_does_not_block_completeness(self):
        scr = {
            "candidate_concepts": FULL_SCR["candidate_concepts"],
            "trade_summary": FULL_SCR["trade_summary"],
            "feasibility_assessment": [
                {"concept_id": "C1", "verdict": "feasible"},
                {"concept_id": "C2", "verdict": "not_feasible"},
            ],
            "recommended_concept": "C1",
        }
        report = scrdrd.build_completeness_report(scr)
        self.assertTrue(report["complete"])
        self.assertEqual(report["feasibility_issues"]["not_feasible"], ["C2"])


class DrdGateVerdictTest(unittest.TestCase):
    def test_ready_when_complete(self):
        report = scrdrd.build_completeness_report(FULL_SCR)
        self.assertEqual(scrdrd.drd_gate_verdict(report), "ready")

    def test_not_ready_when_incomplete(self):
        report = scrdrd.build_completeness_report({})
        self.assertEqual(scrdrd.drd_gate_verdict(report), "not_ready")

    def test_missing_complete_key_raises(self):
        with self.assertRaises(ValueError):
            scrdrd.drd_gate_verdict({})


if __name__ == "__main__":
    unittest.main(verbosity=2)
