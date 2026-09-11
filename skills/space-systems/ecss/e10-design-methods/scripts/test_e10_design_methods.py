#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.4.1.3 design method,
tool and model selection and validation.

Exercises scripts/e10_design_methods_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a method type
categorizes as exactly model-based or rule-based and an unrecognized
type raises; a model-based method's validation status is
validated_in_domain when it has a validation record and the case
falls within its covered domain, validated_out_of_domain when it has
a record but the case falls outside that domain, and unvalidated
otherwise; a rule-based method's precedent is bounded only when a
documented precedent exists and its conditions cover the case;
confirmation weight is base confidence x the status weight, and a
negative base confidence or unrecognized status raises; a design
output's summed model-based confirmation weight is checked against
its required threshold (an uncaptured threshold with nonzero weight is
itself a finding), and an output with an unbounded rule-based method
but no recorded rationale is flagged; the aggregated review is
compliant only when both categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_design_methods_logic as dm  # noqa: E402


class ClassifyDesignMethodTest(unittest.TestCase):
    def test_analytical_is_model_based(self):
        self.assertEqual(dm.classify_design_method("analytical"), "model_based")

    def test_numerical_simulation_is_model_based(self):
        self.assertEqual(
            dm.classify_design_method("numerical_simulation"), "model_based"
        )

    def test_empirical_correlation_is_rule_based(self):
        self.assertEqual(
            dm.classify_design_method("empirical_correlation"), "rule_based"
        )

    def test_heritage_design_rule_is_rule_based(self):
        self.assertEqual(
            dm.classify_design_method("heritage_design_rule"), "rule_based"
        )

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            dm.classify_design_method("gut_feeling")


class ModelValidationStatusTest(unittest.TestCase):
    def test_validated_in_domain(self):
        self.assertEqual(
            dm.model_validation_status(True, True), "validated_in_domain"
        )

    def test_validated_out_of_domain(self):
        self.assertEqual(
            dm.model_validation_status(True, False), "validated_out_of_domain"
        )

    def test_unvalidated_regardless_of_domain(self):
        self.assertEqual(dm.model_validation_status(False, True), "unvalidated")
        self.assertEqual(dm.model_validation_status(False, False), "unvalidated")


class RulePrecedentBoundedTest(unittest.TestCase):
    def test_documented_and_bounded_is_true(self):
        self.assertTrue(dm.rule_precedent_bounded(True, True))

    def test_documented_but_unbounded_is_false(self):
        self.assertFalse(dm.rule_precedent_bounded(True, False))

    def test_no_precedent_is_false(self):
        self.assertFalse(dm.rule_precedent_bounded(False, True))
        self.assertFalse(dm.rule_precedent_bounded(False, False))


class DesignMethodConfirmationWeightTest(unittest.TestCase):
    def test_validated_in_domain_full_weight(self):
        weight = dm.design_method_confirmation_weight(0.8, "validated_in_domain")
        self.assertAlmostEqual(weight, 0.8)

    def test_validated_out_of_domain_half_weight(self):
        weight = dm.design_method_confirmation_weight(0.8, "validated_out_of_domain")
        self.assertAlmostEqual(weight, 0.4)

    def test_unvalidated_is_zero(self):
        self.assertEqual(
            dm.design_method_confirmation_weight(0.9, "unvalidated"), 0.0
        )

    def test_negative_base_confidence_raises(self):
        with self.assertRaises(ValueError):
            dm.design_method_confirmation_weight(-0.1, "validated_in_domain")

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            dm.design_method_confirmation_weight(0.5, "vibes_based")


class ModelConfirmationViolationsTest(unittest.TestCase):
    def test_meets_required_weight_no_violation(self):
        methods = [{"base_confidence": 1.0, "validation_status": "validated_in_domain"}]
        self.assertEqual(
            dm.model_confirmation_violations("bracket-1", methods, 1.0), []
        )

    def test_below_required_weight_flagged(self):
        methods = [{"base_confidence": 0.5, "validation_status": "validated_out_of_domain"}]
        violations = dm.model_confirmation_violations("bracket-1", methods, 1.0)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "insufficient_design_method_confirmation",
                    "output": "bracket-1",
                    "total_weight": 0.25,
                    "required_weight": 1.0,
                }
            ],
        )

    def test_missing_threshold_with_weight_flagged(self):
        methods = [{"base_confidence": 1.0, "validation_status": "validated_in_domain"}]
        violations = dm.model_confirmation_violations("bracket-1", methods, None)
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0]["issue"], "missing_required_confirmation_weight"
        )

    def test_missing_threshold_with_no_methods_not_flagged(self):
        self.assertEqual(dm.model_confirmation_violations("bracket-1", [], None), [])

    def test_sums_multiple_methods(self):
        methods = [
            {"base_confidence": 0.5, "validation_status": "validated_in_domain"},
            {"base_confidence": 1.0, "validation_status": "validated_out_of_domain"},
        ]
        # 0.5*1.0 + 1.0*0.5 = 1.0, meets a 1.0 threshold.
        self.assertEqual(dm.model_confirmation_violations("bracket-2", methods, 1.0), [])


class RuleBasedTraceabilityViolationsTest(unittest.TestCase):
    def test_no_unbounded_rule_no_violation(self):
        self.assertEqual(
            dm.rule_based_traceability_violations("bracket-1", False, None), []
        )

    def test_unbounded_rule_with_rationale_no_violation(self):
        self.assertEqual(
            dm.rule_based_traceability_violations("bracket-1", True, True), []
        )

    def test_unbounded_rule_without_rationale_flagged(self):
        violations = dm.rule_based_traceability_violations("bracket-1", True, False)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "missing_rationale_for_unbounded_design_rule",
                    "output": "bracket-1",
                }
            ],
        )


class DesignMethodsReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        output = {
            "output_id": "bracket-1",
            "methods": [
                {
                    "method_type": "analytical",
                    "is_validated": True,
                    "within_domain_of_applicability": True,
                    "base_confidence": 1.0,
                },
                {
                    "method_type": "heritage_design_rule",
                    "has_documented_precedent": True,
                    "precedent_conditions_bound_case": True,
                },
            ],
            "required_confirmation_weight": 1.0,
            "rationale_on_record": False,
        }
        review = dm.design_methods_review(output)
        self.assertEqual(review, {"selection": [], "traceability": []})
        self.assertTrue(dm.is_design_methods_compliant(review))

    def test_review_surfaces_each_category_independently(self):
        output = {
            "output_id": "bracket-2",
            "methods": [
                {
                    "method_type": "numerical_simulation",
                    "is_validated": False,
                    "within_domain_of_applicability": False,
                    "base_confidence": 1.0,
                },
                {
                    "method_type": "empirical_correlation",
                    "has_documented_precedent": True,
                    "precedent_conditions_bound_case": False,
                },
            ],
            "required_confirmation_weight": 0.5,
            "rationale_on_record": False,
        }
        review = dm.design_methods_review(output)
        self.assertTrue(review["selection"])
        self.assertTrue(review["traceability"])
        self.assertFalse(dm.is_design_methods_compliant(review))

    def test_review_ignores_bounded_rule_based_method(self):
        output = {
            "output_id": "bracket-3",
            "methods": [
                {
                    "method_type": "heritage_design_rule",
                    "has_documented_precedent": True,
                    "precedent_conditions_bound_case": True,
                },
            ],
            "required_confirmation_weight": None,
            "rationale_on_record": False,
        }
        review = dm.design_methods_review(output)
        self.assertEqual(review["traceability"], [])

    def test_review_raises_on_unknown_method_type(self):
        output = {
            "output_id": "bracket-4",
            "methods": [{"method_type": "crystal_ball"}],
            "required_confirmation_weight": None,
            "rationale_on_record": False,
        }
        with self.assertRaises(ValueError):
            dm.design_methods_review(output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
