#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.1 general equipment
test requirements.

Exercises scripts/e1003_eq_general_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a test model is entitled to
exactly one campaign (QM->qualification, PFM->protoflight,
FM->acceptance) and a model with no formal campaign (EM) raises; a
test configuration that is not flight-representative and carries no
documented deviation is flagged, and every required interface absent
from the simulated set is flagged; the interface-check bookend rule
requires a pre-interface check on the first sequence step and a post-
interface check on the last; the functional-test rule requires a
before/after functional test on every step; the performance-test rule
requires a performance test on the first and last steps; and the
aggregated review is compliant only when every category is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_general_logic as eq  # noqa: E402


def make_sequence(length, overrides=None):
    """A fully-compliant test sequence of the given length: every step
    has a functional test before/after; the first and last steps also
    carry the interface-check and performance-test bookends. overrides
    patches specific step indices with partial dicts, e.g.
    {0: {"pre_interface_check": False}}."""
    sequence = []
    for index in range(length):
        step = {
            "functional_test_before": True,
            "functional_test_after": True,
            "pre_interface_check": index == 0,
            "post_interface_check": index == length - 1,
            "performance_test": index in (0, length - 1),
        }
        sequence.append(step)
    for index, patch in (overrides or {}).items():
        sequence[index] = dict(sequence[index], **patch)
    return sequence


class RequiredCampaignTest(unittest.TestCase):
    def test_qm_maps_to_qualification(self):
        self.assertEqual(eq.required_campaign("QM"), "qualification")

    def test_pfm_maps_to_protoflight(self):
        self.assertEqual(eq.required_campaign("PFM"), "protoflight")

    def test_fm_maps_to_acceptance(self):
        self.assertEqual(eq.required_campaign("FM"), "acceptance")

    def test_em_raises(self):
        with self.assertRaises(ValueError):
            eq.required_campaign("EM")

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            eq.required_campaign("SPARE")


class ModelApplicabilityViolationsTest(unittest.TestCase):
    def test_matching_campaign_has_no_violation(self):
        self.assertEqual(eq.model_applicability_violations("QM", "qualification"), [])

    def test_mismatched_campaign_flagged(self):
        violations = eq.model_applicability_violations("FM", "qualification")
        self.assertEqual(
            violations,
            [
                {
                    "issue": "campaign_not_applicable_to_model",
                    "model": "FM",
                    "campaign": "qualification",
                    "expected_campaign": "acceptance",
                }
            ],
        )


class ConfigurationViolationsTest(unittest.TestCase):
    REQUIRED_INTERFACES = ["power", "data", "thermal"]

    def test_representative_and_fully_simulated_has_no_violation(self):
        configuration = {
            "representative": True,
            "deviations": [],
            "interfaces_simulated": ["power", "data", "thermal"],
        }
        self.assertEqual(eq.configuration_violations(configuration, self.REQUIRED_INTERFACES), [])

    def test_unrepresentative_without_deviation_flagged(self):
        configuration = {"representative": False, "deviations": [], "interfaces_simulated": []}
        violations = eq.configuration_violations(configuration, [])
        self.assertIn({"issue": "unrepresentative_configuration_undocumented"}, violations)

    def test_unrepresentative_with_deviation_not_flagged(self):
        configuration = {
            "representative": False,
            "deviations": ["harness length shortened for bench access"],
            "interfaces_simulated": ["power", "data", "thermal"],
        }
        violations = eq.configuration_violations(configuration, self.REQUIRED_INTERFACES)
        self.assertNotIn({"issue": "unrepresentative_configuration_undocumented"}, violations)

    def test_missing_interface_simulation_flagged(self):
        configuration = {"representative": True, "deviations": [], "interfaces_simulated": ["power"]}
        violations = eq.configuration_violations(configuration, self.REQUIRED_INTERFACES)
        self.assertIn({"issue": "interface_not_simulated", "interface": "data"}, violations)
        self.assertIn({"issue": "interface_not_simulated", "interface": "thermal"}, violations)

    def test_does_not_mutate_input(self):
        configuration = {
            "representative": True,
            "deviations": [],
            "interfaces_simulated": ["power", "data", "thermal"],
        }
        before = dict(configuration)
        eq.configuration_violations(configuration, self.REQUIRED_INTERFACES)
        self.assertEqual(configuration, before)


class MissingInterfaceChecksTest(unittest.TestCase):
    def test_compliant_sequence_has_no_violation(self):
        self.assertEqual(eq.missing_interface_checks(make_sequence(3)), [])

    def test_missing_pre_check_flagged(self):
        sequence = make_sequence(3, {0: {"pre_interface_check": False}})
        self.assertIn(
            {"issue": "missing_pre_interface_check", "step": 0},
            eq.missing_interface_checks(sequence),
        )

    def test_missing_post_check_flagged(self):
        sequence = make_sequence(3, {2: {"post_interface_check": False}})
        self.assertIn(
            {"issue": "missing_post_interface_check", "step": 2},
            eq.missing_interface_checks(sequence),
        )

    def test_midsequence_check_not_required(self):
        # Clause 5.1 only mandates the bookend checks; a middle step
        # with no interface check recorded is not itself a violation.
        sequence = make_sequence(3)
        sequence[1] = dict(sequence[1], pre_interface_check=False, post_interface_check=False)
        self.assertEqual(eq.missing_interface_checks(sequence), [])

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            eq.missing_interface_checks([])


class FunctionalTestGapsTest(unittest.TestCase):
    def test_compliant_sequence_has_no_gaps(self):
        self.assertEqual(eq.functional_test_gaps(make_sequence(3)), [])

    def test_missing_before_flagged_on_any_step(self):
        sequence = make_sequence(3, {1: {"functional_test_before": False}})
        self.assertIn(
            {"issue": "missing_functional_test_before", "step": 1},
            eq.functional_test_gaps(sequence),
        )

    def test_missing_after_flagged_on_any_step(self):
        sequence = make_sequence(3, {1: {"functional_test_after": False}})
        self.assertIn(
            {"issue": "missing_functional_test_after", "step": 1},
            eq.functional_test_gaps(sequence),
        )

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            eq.functional_test_gaps([])


class MissingPerformanceTestsTest(unittest.TestCase):
    def test_compliant_sequence_has_no_violation(self):
        self.assertEqual(eq.missing_performance_tests(make_sequence(3)), [])

    def test_missing_first_step_flagged(self):
        sequence = make_sequence(3, {0: {"performance_test": False}})
        self.assertIn(
            {"issue": "missing_performance_test", "step": 0},
            eq.missing_performance_tests(sequence),
        )

    def test_missing_last_step_flagged(self):
        sequence = make_sequence(3, {2: {"performance_test": False}})
        self.assertIn(
            {"issue": "missing_performance_test", "step": 2},
            eq.missing_performance_tests(sequence),
        )

    def test_midsequence_performance_test_not_required(self):
        sequence = make_sequence(3)
        self.assertNotIn(
            {"issue": "missing_performance_test", "step": 1},
            eq.missing_performance_tests(sequence),
        )

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            eq.missing_performance_tests([])


class GeneralEquipmentTestReviewTest(unittest.TestCase):
    CONFIGURATION = {
        "representative": True,
        "deviations": [],
        "interfaces_simulated": ["power", "data"],
    }
    REQUIRED_INTERFACES = ["power", "data"]

    def test_fully_compliant_review(self):
        review = eq.general_equipment_test_review(
            "QM", "qualification", self.CONFIGURATION, self.REQUIRED_INTERFACES, make_sequence(3)
        )
        self.assertEqual(
            review,
            {
                "model_applicability": [],
                "configuration": [],
                "interface_checks": [],
                "functional_tests": [],
                "performance_tests": [],
            },
        )
        self.assertTrue(eq.is_general_compliant(review))

    def test_review_surfaces_each_category_independently(self):
        sequence = make_sequence(3, {0: {"pre_interface_check": False, "performance_test": False}})
        review = eq.general_equipment_test_review(
            "FM", "qualification", {"representative": False, "deviations": []}, self.REQUIRED_INTERFACES, sequence
        )
        self.assertTrue(review["model_applicability"])
        self.assertTrue(review["configuration"])
        self.assertTrue(review["interface_checks"])
        self.assertTrue(review["performance_tests"])
        self.assertEqual(review["functional_tests"], [])
        self.assertFalse(eq.is_general_compliant(review))

    def test_review_propagates_empty_sequence_error(self):
        with self.assertRaises(ValueError):
            eq.general_equipment_test_review("QM", "qualification", self.CONFIGURATION, self.REQUIRED_INTERFACES, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
