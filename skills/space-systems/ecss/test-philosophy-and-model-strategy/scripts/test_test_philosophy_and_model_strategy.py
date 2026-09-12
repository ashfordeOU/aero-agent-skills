#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clauses 4.6.3.1-4.6.3.6 structural
model philosophy and test campaign.

Exercises scripts/test_philosophy_and_model_strategy_logic.py (stdlib
unittest, offline). Contract: each model type is assigned to exactly one
article category (development, qualification, or flight) and an
unrecognized type raises; each model type has a fixed set of required test
phases; flight intent is correctly derived per model type; the
qualification strategy is selected deterministically from unit count, risk
level, and schedule constraint; test level validity is enforced per phase
(qualification test at or above minimum, acceptance test strictly below
qualification, development test unconstrained); PFM qualification test
duration must be reduced relative to QM but not below a minimum fraction;
similarity holds only when the reference is qualified and all design,
material, process, and environment criteria match; and the full campaign
validator surfaces missing phases, wrong-phase records, and invalid levels.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_philosophy_and_model_strategy_logic as tp  # noqa: E402


class CategorizModelTest(unittest.TestCase):
    def test_ptm_is_development_article(self):
        self.assertEqual(tp.categorize_model("PTM"), "development_article")

    def test_stm_is_development_article(self):
        self.assertEqual(tp.categorize_model("STM"), "development_article")

    def test_qm_is_qualification_article(self):
        self.assertEqual(tp.categorize_model("QM"), "qualification_article")

    def test_fm_is_flight_article(self):
        self.assertEqual(tp.categorize_model("FM"), "flight_article")

    def test_pfm_is_flight_article(self):
        self.assertEqual(tp.categorize_model("PFM"), "flight_article")

    def test_unknown_model_type_raises(self):
        with self.assertRaises(ValueError):
            tp.categorize_model("XRT")


class RequiredTestPhasesTest(unittest.TestCase):
    def test_ptm_requires_development_test_only(self):
        self.assertEqual(
            tp.required_test_phases("PTM"), frozenset({"development_test"})
        )

    def test_stm_requires_development_test_only(self):
        self.assertEqual(
            tp.required_test_phases("STM"), frozenset({"development_test"})
        )

    def test_qm_requires_qualification_test_only(self):
        self.assertEqual(
            tp.required_test_phases("QM"), frozenset({"qualification_test"})
        )

    def test_fm_requires_acceptance_test_only(self):
        self.assertEqual(
            tp.required_test_phases("FM"), frozenset({"acceptance_test"})
        )

    def test_pfm_requires_qualification_and_acceptance(self):
        self.assertEqual(
            tp.required_test_phases("PFM"),
            frozenset({"qualification_test", "acceptance_test"}),
        )

    def test_unknown_model_type_raises(self):
        with self.assertRaises(ValueError):
            tp.required_test_phases("ABC")


class IsFlightIntendedTest(unittest.TestCase):
    def test_ptm_not_flight_intended(self):
        self.assertFalse(tp.is_flight_intended("PTM"))

    def test_stm_not_flight_intended(self):
        self.assertFalse(tp.is_flight_intended("STM"))

    def test_qm_not_flight_intended(self):
        self.assertFalse(tp.is_flight_intended("QM"))

    def test_fm_is_flight_intended(self):
        self.assertTrue(tp.is_flight_intended("FM"))

    def test_pfm_is_flight_intended(self):
        self.assertTrue(tp.is_flight_intended("PFM"))

    def test_unknown_model_type_raises(self):
        with self.assertRaises(ValueError):
            tp.is_flight_intended("ZZZ")


class SelectQualificationStrategyTest(unittest.TestCase):
    def test_multiple_units_selects_qm_plus_fm(self):
        self.assertEqual(
            tp.select_qualification_strategy(3, "low", False), "qm_plus_fm"
        )

    def test_multiple_units_high_risk_still_qm_plus_fm(self):
        self.assertEqual(
            tp.select_qualification_strategy(2, "high", False), "qm_plus_fm"
        )

    def test_single_high_risk_no_schedule_selects_ptm_plus_fm(self):
        self.assertEqual(
            tp.select_qualification_strategy(1, "high", False), "ptm_plus_fm"
        )

    def test_single_low_risk_no_schedule_selects_proto_flight(self):
        self.assertEqual(
            tp.select_qualification_strategy(1, "low", False), "proto_flight"
        )

    def test_single_medium_risk_no_schedule_selects_proto_flight(self):
        self.assertEqual(
            tp.select_qualification_strategy(1, "medium", False), "proto_flight"
        )

    def test_single_high_risk_schedule_constraint_selects_proto_flight(self):
        self.assertEqual(
            tp.select_qualification_strategy(1, "high", True), "proto_flight"
        )

    def test_zero_units_raises(self):
        with self.assertRaises(ValueError):
            tp.select_qualification_strategy(0, "low", False)

    def test_unknown_risk_level_raises(self):
        with self.assertRaises(ValueError):
            tp.select_qualification_strategy(1, "critical", False)


class CheckTestLevelTest(unittest.TestCase):
    def test_qt_level_at_minimum_passes(self):
        self.assertEqual(
            tp.check_test_level("qualification_test", 10.0, 10.0), []
        )

    def test_qt_level_above_minimum_passes(self):
        self.assertEqual(
            tp.check_test_level("qualification_test", 12.0, 10.0), []
        )

    def test_qt_level_below_minimum_fails(self):
        violations = tp.check_test_level("qualification_test", 8.0, 10.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "qualification_level_not_met")

    def test_at_level_below_qt_passes(self):
        self.assertEqual(
            tp.check_test_level("acceptance_test", 7.5, 10.0), []
        )

    def test_at_level_equal_to_qt_fails(self):
        violations = tp.check_test_level("acceptance_test", 10.0, 10.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"], "acceptance_level_at_or_above_qualification"
        )

    def test_at_level_above_qt_fails(self):
        violations = tp.check_test_level("acceptance_test", 11.0, 10.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"], "acceptance_level_at_or_above_qualification"
        )

    def test_development_test_unconstrained_high_level(self):
        self.assertEqual(
            tp.check_test_level("development_test", 999.0, 0.1), []
        )

    def test_negative_test_level_raises(self):
        with self.assertRaises(ValueError):
            tp.check_test_level("qualification_test", -1.0, 10.0)

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            tp.check_test_level("random_shaking", 10.0, 10.0)


class CheckPfmDurationTest(unittest.TestCase):
    def test_valid_pfm_duration_half_qm(self):
        self.assertEqual(tp.check_pfm_duration(60.0, 120.0), [])

    def test_pfm_duration_equal_to_qm_fails(self):
        findings = tp.check_pfm_duration(120.0, 120.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "pfm_duration_not_reduced")

    def test_pfm_duration_greater_than_qm_fails(self):
        findings = tp.check_pfm_duration(150.0, 120.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "pfm_duration_not_reduced")

    def test_pfm_duration_below_minimum_fraction_fails(self):
        # 0.25 * 120 = 30; 10 < 30
        findings = tp.check_pfm_duration(10.0, 120.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "pfm_duration_below_minimum_fraction")

    def test_pfm_duration_exactly_at_minimum_fraction_passes(self):
        # 0.25 * 120 = 30; 30 >= 30 and 30 < 120
        self.assertEqual(tp.check_pfm_duration(30.0, 120.0), [])

    def test_nonpositive_pfm_duration_raises(self):
        with self.assertRaises(ValueError):
            tp.check_pfm_duration(0.0, 120.0)

    def test_nonpositive_qm_duration_raises(self):
        with self.assertRaises(ValueError):
            tp.check_pfm_duration(60.0, 0.0)


class CheckSimilarityTest(unittest.TestCase):
    def _base_reference(self):
        return {
            "item_id": "bracket-A",
            "is_qualified": True,
            "design_version": "v1.0",
            "qualification_environment": {
                "random_grms": 15.0,
                "sine_g": 20.0,
                "shock_srs_g": 1000.0,
            },
            "material_spec": "AL-7075-T73",
            "manufacturing_process": "CNC-milled",
        }

    def _base_candidate(self):
        return {
            "item_id": "bracket-B",
            "design_version": "v1.0",
            "target_environment": {
                "random_grms": 12.0,
                "sine_g": 18.0,
                "shock_srs_g": 800.0,
            },
            "material_spec": "AL-7075-T73",
            "manufacturing_process": "CNC-milled",
        }

    def test_identical_items_are_similar(self):
        result = tp.check_similarity(self._base_reference(), self._base_candidate())
        self.assertTrue(result["is_similar"])
        self.assertEqual(result["findings"], [])

    def test_reference_not_qualified_fails(self):
        ref = self._base_reference()
        ref["is_qualified"] = False
        result = tp.check_similarity(ref, self._base_candidate())
        self.assertFalse(result["is_similar"])
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("reference_not_qualified", issues)

    def test_design_version_differs_fails(self):
        cand = self._base_candidate()
        cand["design_version"] = "v2.0"
        result = tp.check_similarity(self._base_reference(), cand)
        self.assertFalse(result["is_similar"])
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("design_version_differs", issues)

    def test_material_spec_differs_fails(self):
        cand = self._base_candidate()
        cand["material_spec"] = "AL-6061-T6"
        result = tp.check_similarity(self._base_reference(), cand)
        self.assertFalse(result["is_similar"])
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("material_spec_differs", issues)

    def test_manufacturing_process_differs_fails(self):
        cand = self._base_candidate()
        cand["manufacturing_process"] = "casting"
        result = tp.check_similarity(self._base_reference(), cand)
        self.assertFalse(result["is_similar"])
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("manufacturing_process_differs", issues)

    def test_environment_more_severe_fails(self):
        cand = self._base_candidate()
        cand["target_environment"]["random_grms"] = 20.0  # exceeds ref 15.0
        result = tp.check_similarity(self._base_reference(), cand)
        self.assertFalse(result["is_similar"])
        env_issues = [
            f for f in result["findings"] if f["issue"] == "environment_more_severe"
        ]
        self.assertTrue(any(f["field"] == "random_grms" for f in env_issues))

    def test_multiple_criteria_failing_all_reported(self):
        ref = self._base_reference()
        ref["is_qualified"] = False
        cand = self._base_candidate()
        cand["design_version"] = "v3.0"
        result = tp.check_similarity(ref, cand)
        self.assertFalse(result["is_similar"])
        self.assertGreaterEqual(len(result["findings"]), 2)


class ValidateTestCampaignTest(unittest.TestCase):
    def test_fm_with_valid_acceptance_test_is_valid(self):
        records = [{"phase": "acceptance_test", "test_level": 8.0, "reference_level": 10.0}]
        result = tp.validate_test_campaign("FM", records)
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_qm_with_valid_qualification_test_is_valid(self):
        records = [{"phase": "qualification_test", "test_level": 10.0, "reference_level": 10.0}]
        result = tp.validate_test_campaign("QM", records)
        self.assertTrue(result["valid"])

    def test_pfm_with_both_phases_valid(self):
        records = [
            {"phase": "qualification_test", "test_level": 10.0, "reference_level": 10.0},
            {"phase": "acceptance_test", "test_level": 7.0, "reference_level": 10.0},
        ]
        result = tp.validate_test_campaign("PFM", records)
        self.assertTrue(result["valid"])

    def test_fm_missing_acceptance_test_is_invalid(self):
        result = tp.validate_test_campaign("FM", [])
        self.assertFalse(result["valid"])
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("required_phase_not_performed", issues)

    def test_fm_with_qualification_test_is_invalid(self):
        records = [
            {"phase": "acceptance_test", "test_level": 7.0, "reference_level": 10.0},
            {"phase": "qualification_test", "test_level": 10.0, "reference_level": 10.0},
        ]
        result = tp.validate_test_campaign("FM", records)
        self.assertFalse(result["valid"])
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("phase_not_required_for_model_type", issues)

    def test_fm_acceptance_level_too_high_is_invalid(self):
        records = [{"phase": "acceptance_test", "test_level": 12.0, "reference_level": 10.0}]
        result = tp.validate_test_campaign("FM", records)
        self.assertFalse(result["valid"])
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("acceptance_level_at_or_above_qualification", issues)

    def test_unrecognized_model_type_is_invalid(self):
        result = tp.validate_test_campaign("UNK", [])
        self.assertFalse(result["valid"])
        self.assertEqual(result["findings"][0]["issue"], "unrecognized_model_type")

    def test_ptm_with_development_test_is_valid(self):
        records = [{"phase": "development_test", "test_level": 50.0, "reference_level": 0.0}]
        result = tp.validate_test_campaign("PTM", records)
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
