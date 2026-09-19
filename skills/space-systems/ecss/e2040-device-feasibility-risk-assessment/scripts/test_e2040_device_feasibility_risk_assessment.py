#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-feasibility-risk-assessment.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_feasibility_risk_assessment.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_feasibility_risk_assessment_logic import (  # noqa: E402
    FEASIBILITY_DRIVERS,
    HIGH,
    LOW,
    MAX_RISK_INDEX,
    UNACCEPTABLE,
    assess_feasibility,
    band_rank,
    normalize_driver,
    normalize_score,
    normalize_verdict,
    readiness_gap,
    residual_scores,
    risk_band,
    risk_exposure,
    risk_index,
    validate_drivers,
    validate_risks,
    within_exposure_limit,
)


def base_case():
    return {
        "drivers": [
            {"driver": "technology", "verdict": "achievable", "rationale": "flight heritage part"},
            {"driver": "resources", "verdict": "achievable"},
            {"driver": "schedule", "verdict": "achievable"},
            {"driver": "cost", "verdict": "achievable"},
            {"driver": "supply chain", "verdict": "achievable"},
        ],
        "risks": [
            {
                "id": "R-1",
                "severity": 3,
                "likelihood": 3,
                "mitigation": {
                    "owner": "device lead",
                    "likelihood_reduction": 1,
                    "summary": "second source qualified early",
                },
            },
            {"id": "R-2", "severity": 2, "likelihood": 2},
        ],
        "technology_readiness": 6,
        "required_readiness": 5,
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_supply_chain_folds_to_supply(self):
        self.assertEqual(normalize_driver("Supply Chain"), "supply")

    def test_budget_folds_to_cost(self):
        self.assertEqual(normalize_driver("budget"), "cost")

    def test_unknown_driver_rejected(self):
        with self.assertRaises(ValueError):
            normalize_driver("weather")

    def test_no_folds_to_unachievable(self):
        self.assertEqual(normalize_verdict("no"), "unachievable")

    def test_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            normalize_verdict("probably")

    def test_five_drivers_are_the_whole_set(self):
        self.assertEqual(len(FEASIBILITY_DRIVERS), 5)


class TestScores(unittest.TestCase):
    def test_catastrophic_folds_to_five(self):
        self.assertEqual(normalize_score("severity", "catastrophic"), 5)

    def test_severity_letter_form_folds(self):
        self.assertEqual(normalize_score("severity", "S4"), 4)

    def test_likelihood_letter_folds(self):
        self.assertEqual(normalize_score("likelihood", "E"), 5)

    def test_score_outside_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            normalize_score("severity", 6)

    def test_boolean_is_not_a_score(self):
        with self.assertRaises(ValueError):
            normalize_score("severity", True)

    def test_index_is_the_product(self):
        self.assertEqual(risk_index(4, 3), 12)

    def test_max_index_is_twenty_five(self):
        self.assertEqual(MAX_RISK_INDEX, 25)


class TestBanding(unittest.TestCase):
    def test_smallest_risk_bands_low(self):
        self.assertEqual(risk_band(1, 1), LOW)

    def test_largest_risk_bands_unacceptable(self):
        self.assertEqual(risk_band(5, 5), UNACCEPTABLE)

    def test_catastrophic_but_unlikely_is_not_low(self):
        self.assertNotEqual(risk_band(5, 1), LOW)

    def test_bands_are_ordered(self):
        self.assertLess(band_rank(LOW), band_rank(HIGH))

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            band_rank("terrifying")


class TestMitigation(unittest.TestCase):
    def test_mitigation_reduces_the_residual(self):
        self.assertEqual(
            residual_scores(4, 4, {"owner": "lead", "likelihood_reduction": 2}), (4, 2)
        )

    def test_reduction_cannot_drop_below_the_scale(self):
        self.assertEqual(
            residual_scores(2, 2, {"owner": "lead", "severity_reduction": 4, "likelihood_reduction": 4}),
            (1, 1),
        )

    def test_no_mitigation_leaves_the_scores_alone(self):
        self.assertEqual(residual_scores(3, 2, None), (3, 2))

    def test_unknown_mitigation_key_rejected(self):
        with self.assertRaises(ValueError):
            residual_scores(3, 3, {"owner": "lead", "cost": 10})

    def test_negative_reduction_rejected(self):
        with self.assertRaises(ValueError):
            residual_scores(3, 3, {"owner": "lead", "severity_reduction": -1})


class TestExposure(unittest.TestCase):
    def setUp(self):
        self.risks = validate_risks(base_case()["risks"])

    def test_exposure_is_the_mean_residual_over_the_maximum(self):
        self.assertAlmostEqual(self.risks[0]["residual_index"] / 25.0, 0.24, places=9)
        self.assertAlmostEqual(risk_exposure(self.risks), (6 + 4) / 50.0, places=9)

    def test_exposure_needs_a_risk(self):
        with self.assertRaises(ValueError):
            risk_exposure([])

    def test_a_limit_met_exactly_is_met(self):
        self.assertTrue(within_exposure_limit(1 / 5, 0.2))

    def test_a_limit_met_by_a_third_landing_is_met(self):
        self.assertTrue(within_exposure_limit(1 / 3, 1 / 3))

    def test_a_limit_exceeded_is_reported(self):
        self.assertFalse(within_exposure_limit(0.5, 0.2))

    def test_a_limit_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            within_exposure_limit(0.2, 1.4)


class TestValidation(unittest.TestCase):
    def test_duplicate_driver_rejected(self):
        entries = base_case()["drivers"]
        entries.append({"driver": "cost", "verdict": "achievable"})
        with self.assertRaises(ValueError):
            validate_drivers(entries)

    def test_unknown_driver_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_drivers([{"driver": "cost", "verdict": "achievable", "owner": "x"}])

    def test_driver_without_a_verdict_rejected(self):
        with self.assertRaises(ValueError):
            validate_drivers([{"driver": "cost"}])

    def test_duplicate_risk_id_rejected(self):
        entries = base_case()["risks"]
        entries.append({"id": "R-2", "severity": 1, "likelihood": 1})
        with self.assertRaises(ValueError):
            validate_risks(entries)

    def test_risk_without_a_likelihood_rejected(self):
        with self.assertRaises(ValueError):
            validate_risks([{"id": "R-1", "severity": 2}])

    def test_non_list_risks_rejected(self):
        with self.assertRaises(ValueError):
            validate_risks({"id": "R-1"})


class TestReadiness(unittest.TestCase):
    def test_a_device_at_the_required_level_has_no_gap(self):
        self.assertEqual(readiness_gap(5, 5), 0)

    def test_a_device_above_the_required_level_has_no_gap(self):
        self.assertEqual(readiness_gap(8, 5), 0)

    def test_a_shortfall_is_counted_in_steps(self):
        self.assertEqual(readiness_gap(3, 6), 3)

    def test_a_level_off_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            readiness_gap(0, 5)


class TestAssessFeasibility(unittest.TestCase):
    def test_a_sound_case_is_feasible(self):
        result = assess_feasibility(base_case())
        self.assertEqual(result["verdict"], "feasible")
        self.assertEqual(result["findings"], [])

    def test_exposure_reaches_the_result(self):
        result = assess_feasibility(base_case())
        self.assertAlmostEqual(result["risk_exposure"], 0.2, places=9)

    def test_an_unachievable_driver_sinks_the_case(self):
        case = base_case()
        case["drivers"][2]["verdict"] = "unachievable"
        result = assess_feasibility(case)
        self.assertEqual(result["verdict"], "not-feasible")
        self.assertIn("driver-unachievable", codes(result))

    def test_a_missing_driver_is_reported(self):
        case = base_case()
        del case["drivers"][4]
        result = assess_feasibility(case)
        self.assertIn("driver-not-assessed", codes(result))
        self.assertFalse(result["feasible"])

    def test_a_qualified_driver_needs_a_named_action(self):
        case = base_case()
        case["drivers"][3]["verdict"] = "achievable-with-action"
        result = assess_feasibility(case)
        self.assertIn("qualified-driver-without-action", codes(result))

    def test_a_qualified_driver_with_an_action_is_carried(self):
        case = base_case()
        case["drivers"][3]["verdict"] = "achievable-with-action"
        case["drivers"][3]["action"] = "re-baseline the device budget at the review"
        result = assess_feasibility(case)
        self.assertEqual(result["verdict"], "feasible-with-actions")

    def test_a_one_step_readiness_gap_needs_a_maturation_action(self):
        case = base_case()
        case["technology_readiness"] = 4
        result = assess_feasibility(case)
        self.assertIn("readiness-gap-without-maturation-action", codes(result))

    def test_a_one_step_readiness_gap_with_an_action_is_carried(self):
        case = base_case()
        case["technology_readiness"] = 4
        case["drivers"][0]["verdict"] = "achievable-with-action"
        case["drivers"][0]["action"] = "breadboard the front end before architecture close"
        result = assess_feasibility(case)
        self.assertEqual(result["verdict"], "feasible-with-actions")
        self.assertEqual(result["readiness_gap"], 1)

    def test_a_two_step_readiness_gap_is_not_recoverable(self):
        case = base_case()
        case["technology_readiness"] = 3
        result = assess_feasibility(case)
        self.assertIn("readiness-gap-not-recoverable", codes(result))
        self.assertEqual(result["verdict"], "not-feasible")

    def test_an_unacceptable_residual_stops_the_case(self):
        case = base_case()
        case["risks"][1] = {"id": "R-2", "severity": 5, "likelihood": 5,
                            "mitigation": {"owner": "lead", "likelihood_reduction": 1}}
        result = assess_feasibility(case)
        self.assertIn("residual-risk-unacceptable", codes(result))
        self.assertEqual(result["verdict"], "not-feasible")

    def test_mitigation_is_applied_before_banding(self):
        case = base_case()
        case["risks"][1] = {
            "id": "R-2",
            "severity": 5,
            "likelihood": 4,
            "mitigation": {"owner": "lead", "severity_reduction": 2, "likelihood_reduction": 2},
        }
        result = assess_feasibility(case)
        self.assertNotIn("residual-risk-unacceptable", codes(result))

    def test_a_mitigation_without_an_owner_is_reported(self):
        case = base_case()
        case["risks"][0]["mitigation"] = {"likelihood_reduction": 1}
        result = assess_feasibility(case)
        self.assertIn("mitigation-without-owner", codes(result))

    def test_a_high_risk_with_no_mitigation_is_reported(self):
        case = base_case()
        case["risks"][1] = {"id": "R-2", "severity": 4, "likelihood": 4}
        result = assess_feasibility(case)
        self.assertIn("high-risk-without-mitigation", codes(result))

    def test_an_exposure_limit_met_exactly_does_not_fail_the_case(self):
        case = base_case()
        case["exposure_limit"] = 10 / 50
        result = assess_feasibility(case)
        self.assertNotIn("exposure-limit-exceeded", codes(result))

    def test_an_exposure_limit_exceeded_is_reported(self):
        case = base_case()
        case["exposure_limit"] = 0.05
        result = assess_feasibility(case)
        self.assertIn("exposure-limit-exceeded", codes(result))

    def test_the_worst_residual_band_reaches_the_result(self):
        result = assess_feasibility(base_case())
        self.assertIn(result["worst_residual_band"], (LOW, "medium"))

    def test_unknown_case_key_rejected(self):
        case = base_case()
        case["owner"] = "someone"
        with self.assertRaises(ValueError):
            assess_feasibility(case)

    def test_missing_risks_rejected(self):
        case = base_case()
        del case["risks"]
        with self.assertRaises(ValueError):
            assess_feasibility(case)

    def test_empty_risk_register_rejected(self):
        case = base_case()
        case["risks"] = []
        with self.assertRaises(ValueError):
            assess_feasibility(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_feasibility([("drivers", [])])


if __name__ == "__main__":
    unittest.main()
