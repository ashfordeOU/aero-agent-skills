#!/usr/bin/env python3
"""Gate 3 contract test: ECSS software verification planning.

Exercises scripts/software_verification_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - verification
method selection per requirement category, verification depth per
criticality, plan verdict closure, and ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import software_verification_logic as svl  # noqa: E402


class VerifyMethodTest(unittest.TestCase):
    def test_functional_methods(self):
        self.assertEqual(svl.verify_method("functional"), ["test", "review"])

    def test_safety_methods(self):
        self.assertEqual(svl.verify_method("safety"), ["test", "analysis", "review"])

    def test_resource_led_by_analysis(self):
        methods = svl.verify_method("resource")
        self.assertEqual(methods[0], "analysis")
        self.assertIn("test", methods)

    def test_all_six_categories_covered(self):
        expected = {
            "functional", "performance", "interface", "resource", "safety", "data",
        }
        self.assertEqual(set(svl.VERIFICATION_METHODS), expected)

    def test_every_method_list_nonempty(self):
        for category in svl.VERIFICATION_METHODS:
            self.assertTrue(svl.verify_method(category))

    def test_case_insensitive(self):
        self.assertEqual(svl.verify_method("FUNCTIONAL"), ["test", "review"])

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            svl.verify_method("maintainability")
        with self.assertRaises(ValueError):
            svl.verify_method(42)


class VerificationDepthTest(unittest.TestCase):
    def test_catastrophic_full_independent(self):
        verdict = svl.verification_depth("catastrophic")
        self.assertTrue(verdict["independent"])
        self.assertIn("full independent verification", verdict["depth"])
        self.assertIn("formal", verdict["records"])

    def test_critical_independent(self):
        verdict = svl.verification_depth("critical")
        self.assertTrue(verdict["independent"])
        self.assertIn("independent review", verdict["depth"])

    def test_major_not_independent(self):
        verdict = svl.verification_depth("major")
        self.assertFalse(verdict["independent"])
        self.assertIn("analysis", verdict["depth"])

    def test_minor_review_records(self):
        verdict = svl.verification_depth("minor")
        self.assertFalse(verdict["independent"])
        self.assertEqual(verdict["records"], "review records")

    def test_no_effect_inspection(self):
        verdict = svl.verification_depth("no-effect")
        self.assertFalse(verdict["independent"])
        self.assertEqual(verdict["depth"], "inspection")

    def test_all_five_levels_covered(self):
        expected = {"catastrophic", "critical", "major", "minor", "no-effect"}
        self.assertEqual(set(svl.CRITICALITY_DEPTH), expected)

    def test_unknown_criticality_raises(self):
        with self.assertRaises(ValueError):
            svl.verification_depth("negligible")
        with self.assertRaises(ValueError):
            svl.verification_depth("")


class PlanVerdictTest(unittest.TestCase):
    def test_complete_plan_status(self):
        plan = svl.plan_verdict([("functional", "catastrophic"), ("data", "minor")])
        self.assertEqual(plan["status"], "verification-plan-complete")
        self.assertEqual(len(plan["requirements"]), 2)

    def test_independence_flag_per_requirement(self):
        plan = svl.plan_verdict([("functional", "catastrophic"), ("data", "minor")])
        self.assertTrue(plan["requirements"][0]["independent"])
        self.assertFalse(plan["requirements"][1]["independent"])

    def test_methods_preserved_per_requirement(self):
        plan = svl.plan_verdict([("resource", "major")])
        self.assertEqual(plan["requirements"][0]["methods"], ["analysis", "test"])

    def test_known_textbook_pair(self):
        # Safety requirements on catastrophic software: the heaviest
        # ECSS verification plan, all methods plus independent review.
        plan = svl.plan_verdict([("safety", "catastrophic")])
        req = plan["requirements"][0]
        self.assertEqual(req["methods"], ["test", "analysis", "review"])
        self.assertTrue(req["independent"])
        self.assertEqual(plan["status"], "verification-plan-complete")

    def test_empty_plan_raises(self):
        with self.assertRaises(ValueError):
            svl.plan_verdict([])

    def test_malformed_pair_raises(self):
        with self.assertRaises(ValueError):
            svl.plan_verdict([("functional",)])
        with self.assertRaises(ValueError):
            svl.plan_verdict([("functional", "catastrophic", "extra")])

    def test_unknown_entries_raise(self):
        with self.assertRaises(ValueError):
            svl.plan_verdict([("obscure", "major")])
        with self.assertRaises(ValueError):
            svl.plan_verdict([("functional", "severe")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
