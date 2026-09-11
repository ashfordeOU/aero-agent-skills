#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.3.2 environments and
design-and-test factors.

Exercises scripts/e10_env_design_factors_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a mission phase
maps to its applicable environment types and an unrecognized phase or
an empty phase list raises; an environment type maps to exactly one
engineering domain and an unrecognized type raises; a verification
approach is either test-based (qualification test, protoflight test,
acceptance test) or documentation-based (analysis, similarity), and an
unrecognized approach raises; a test-based approach has a numeric
design-and-test factor per domain while a documentation-based approach
raises when a factor is requested; the test level is the limit level
times the applicable factor and a non-numeric limit level raises; the
per-product review flags every applicable environment missing a
captured limit level and only populates test levels for a test-based
approach; the review is compliant only when nothing is missing.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_env_design_factors_logic as edf  # noqa: E402


class EnvironmentDomainTest(unittest.TestCase):
    def test_quasi_static_acceleration_is_mechanical(self):
        self.assertEqual(edf.environment_domain("quasi_static_acceleration"), "mechanical")

    def test_random_vibration_is_mechanical(self):
        self.assertEqual(edf.environment_domain("random_vibration"), "mechanical")

    def test_thermal_cycling_is_thermal(self):
        self.assertEqual(edf.environment_domain("thermal_cycling"), "thermal")

    def test_radiation_total_dose_is_radiation(self):
        self.assertEqual(edf.environment_domain("radiation_total_dose"), "radiation")

    def test_electromagnetic_susceptibility_is_electromagnetic(self):
        self.assertEqual(
            edf.environment_domain("electromagnetic_susceptibility"), "electromagnetic"
        )

    def test_unknown_environment_type_raises(self):
        with self.assertRaises(ValueError):
            edf.environment_domain("mystery_field")


class ApplicableEnvironmentsTest(unittest.TestCase):
    def test_ground_only(self):
        self.assertEqual(
            edf.applicable_environments(["ground"]),
            {"electromagnetic_susceptibility"},
        )

    def test_launch_includes_mechanical_and_emc(self):
        environments = edf.applicable_environments(["launch"])
        self.assertIn("random_vibration", environments)
        self.assertIn("shock", environments)
        self.assertIn("electromagnetic_susceptibility", environments)
        self.assertNotIn("thermal_cycling", environments)

    def test_union_across_multiple_phases(self):
        environments = edf.applicable_environments(["launch", "on_station"])
        self.assertIn("random_vibration", environments)
        self.assertIn("thermal_vacuum", environments)
        self.assertIn("radiation_total_dose", environments)

    def test_empty_phase_list_raises(self):
        with self.assertRaises(ValueError):
            edf.applicable_environments([])

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            edf.applicable_environments(["deep_space_cruise"])


class VerificationRequiresTestTest(unittest.TestCase):
    def test_qualification_test_requires_test(self):
        self.assertTrue(edf.verification_requires_test("qualification_test"))

    def test_protoflight_test_requires_test(self):
        self.assertTrue(edf.verification_requires_test("protoflight_test"))

    def test_acceptance_test_requires_test(self):
        self.assertTrue(edf.verification_requires_test("acceptance_test"))

    def test_analysis_does_not_require_test(self):
        self.assertFalse(edf.verification_requires_test("analysis"))

    def test_similarity_does_not_require_test(self):
        self.assertFalse(edf.verification_requires_test("similarity"))

    def test_unknown_approach_raises(self):
        with self.assertRaises(ValueError):
            edf.verification_requires_test("guesswork")


class DesignTestFactorTest(unittest.TestCase):
    def test_mechanical_qualification_factor(self):
        self.assertAlmostEqual(
            edf.design_test_factor("mechanical", "qualification_test"), 1.25
        )

    def test_thermal_acceptance_factor(self):
        self.assertAlmostEqual(edf.design_test_factor("thermal", "acceptance_test"), 1.0)

    def test_radiation_protoflight_factor(self):
        self.assertAlmostEqual(
            edf.design_test_factor("radiation", "protoflight_test"), 1.5
        )

    def test_analysis_approach_raises(self):
        with self.assertRaises(ValueError):
            edf.design_test_factor("mechanical", "analysis")

    def test_similarity_approach_raises(self):
        with self.assertRaises(ValueError):
            edf.design_test_factor("thermal", "similarity")

    def test_unknown_domain_raises(self):
        with self.assertRaises(ValueError):
            edf.design_test_factor("acoustic_optics", "qualification_test")


class ComputeTestLevelTest(unittest.TestCase):
    def test_mechanical_qualification_level(self):
        level = edf.compute_test_level(10.0, "quasi_static_acceleration", "qualification_test")
        self.assertAlmostEqual(level, 12.5)

    def test_thermal_negative_limit_extends_margin_colder(self):
        level = edf.compute_test_level(-40.0, "thermal_cycling", "qualification_test")
        self.assertAlmostEqual(level, -46.0)

    def test_acceptance_level_equals_limit(self):
        level = edf.compute_test_level(5.0, "shock", "acceptance_test")
        self.assertAlmostEqual(level, 5.0)

    def test_non_numeric_limit_raises(self):
        with self.assertRaises(ValueError):
            edf.compute_test_level("high", "shock", "qualification_test")

    def test_boolean_limit_raises(self):
        with self.assertRaises(ValueError):
            edf.compute_test_level(True, "shock", "qualification_test")

    def test_unknown_environment_type_raises(self):
        with self.assertRaises(ValueError):
            edf.compute_test_level(1.0, "mystery_field", "qualification_test")

    def test_documentation_approach_raises(self):
        with self.assertRaises(ValueError):
            edf.compute_test_level(1.0, "shock", "analysis")


class EnvironmentReviewTest(unittest.TestCase):
    def test_fully_captured_test_based_review(self):
        product = {
            "product_id": "reaction-wheel-1",
            "mission_phases": ["launch"],
            "verification_approach": "qualification_test",
            "limit_levels": {
                "quasi_static_acceleration": 8.0,
                "random_vibration": 12.0,
                "acoustic": 140.0,
                "shock": 1000.0,
                "electromagnetic_susceptibility": 20.0,
            },
        }
        review = edf.environment_review(product)
        self.assertEqual(review["missing_limit_levels"], [])
        self.assertAlmostEqual(review["test_levels"]["shock"], 1250.0)
        self.assertTrue(edf.is_environment_design_compliant(review))

    def test_missing_limit_level_flagged(self):
        product = {
            "product_id": "star-tracker-1",
            "mission_phases": ["ground"],
            "verification_approach": "qualification_test",
            "limit_levels": {},
        }
        review = edf.environment_review(product)
        self.assertEqual(
            review["missing_limit_levels"],
            [
                {
                    "issue": "missing_limit_level",
                    "product": "star-tracker-1",
                    "environment": "electromagnetic_susceptibility",
                }
            ],
        )
        self.assertFalse(edf.is_environment_design_compliant(review))

    def test_analysis_approach_produces_no_test_levels(self):
        product = {
            "product_id": "bus-structure-1",
            "mission_phases": ["on_station"],
            "verification_approach": "analysis",
            "limit_levels": {
                "thermal_cycling": 100.0,
                "thermal_vacuum": 1e-5,
                "radiation_total_dose": 30.0,
                "electromagnetic_susceptibility": 15.0,
            },
        }
        review = edf.environment_review(product)
        self.assertEqual(review["missing_limit_levels"], [])
        self.assertEqual(review["test_levels"], {})
        self.assertTrue(edf.is_environment_design_compliant(review))

    def test_unknown_phase_in_review_raises(self):
        product = {
            "product_id": "payload-1",
            "mission_phases": ["deep_space_cruise"],
            "verification_approach": "protoflight_test",
            "limit_levels": {},
        }
        with self.assertRaises(ValueError):
            edf.environment_review(product)

    def test_unknown_approach_in_review_raises(self):
        product = {
            "product_id": "payload-2",
            "mission_phases": ["launch"],
            "verification_approach": "guesswork",
            "limit_levels": {},
        }
        with self.assertRaises(ValueError):
            edf.environment_review(product)


if __name__ == "__main__":
    unittest.main(verbosity=2)
