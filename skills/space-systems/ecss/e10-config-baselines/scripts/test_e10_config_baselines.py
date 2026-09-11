#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.4.2.2 configuration
baseline establishment.

Exercises scripts/e10_config_baselines_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a baseline type
outside {functional, allocated, product} raises, and each type maps to
its own gating milestone and required artifact set; establishing a
baseline out of sequence (an earlier baseline not yet established), at
an unpassed milestone, or with missing artifacts is flagged, and a
baseline meeting all three checks has no violations; the full-program
review aggregates all three baseline types independently and is
compliant only when every list is empty; the next-establishable helper
never returns a baseline ahead of an earlier, still-unestablished one.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_config_baselines_logic as cb  # noqa: E402


class ValidateBaselineTypeTest(unittest.TestCase):
    def test_functional_is_valid(self):
        self.assertEqual(cb.validate_baseline_type("functional"), "functional")

    def test_allocated_is_valid(self):
        self.assertEqual(cb.validate_baseline_type("allocated"), "allocated")

    def test_product_is_valid(self):
        self.assertEqual(cb.validate_baseline_type("product"), "product")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            cb.validate_baseline_type("interim")


class ValidateMilestoneTest(unittest.TestCase):
    def test_known_milestone_is_valid(self):
        self.assertEqual(cb.validate_milestone("PDR"), "PDR")

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            cb.validate_milestone("MOT")


class RequiredMilestoneTest(unittest.TestCase):
    def test_functional_gated_by_srr(self):
        self.assertEqual(cb.required_milestone("functional"), "SRR")

    def test_allocated_gated_by_pdr(self):
        self.assertEqual(cb.required_milestone("allocated"), "PDR")

    def test_product_gated_by_cdr(self):
        self.assertEqual(cb.required_milestone("product"), "CDR")

    def test_unknown_baseline_raises(self):
        with self.assertRaises(ValueError):
            cb.required_milestone("draft")


class RequiredArtifactsTest(unittest.TestCase):
    def test_functional_artifacts(self):
        self.assertEqual(
            cb.required_artifacts("functional"),
            frozenset({"top_level_requirements_doc", "functional_interface_spec"}),
        )

    def test_product_artifacts(self):
        self.assertEqual(
            cb.required_artifacts("product"),
            frozenset(
                {
                    "build_to_documentation",
                    "as_built_configuration_list",
                    "verification_closeout_record",
                }
            ),
        )

    def test_unknown_baseline_raises(self):
        with self.assertRaises(ValueError):
            cb.required_artifacts("draft")


class PriorBaselineTypesTest(unittest.TestCase):
    def test_functional_has_no_prior(self):
        self.assertEqual(cb.prior_baseline_types("functional"), ())

    def test_allocated_prior_is_functional(self):
        self.assertEqual(cb.prior_baseline_types("allocated"), ("functional",))

    def test_product_prior_is_functional_then_allocated(self):
        self.assertEqual(cb.prior_baseline_types("product"), ("functional", "allocated"))


class SequenceViolationsTest(unittest.TestCase):
    def test_functional_never_out_of_sequence(self):
        self.assertEqual(cb.sequence_violations("functional", set()), [])

    def test_allocated_with_functional_established_ok(self):
        self.assertEqual(cb.sequence_violations("allocated", {"functional"}), [])

    def test_allocated_without_functional_flagged(self):
        violations = cb.sequence_violations("allocated", set())
        self.assertEqual(
            violations,
            [
                {
                    "issue": "out_of_sequence_baseline",
                    "baseline": "allocated",
                    "missing_prior": ["functional"],
                }
            ],
        )

    def test_product_missing_both_priors_flagged(self):
        violations = cb.sequence_violations("product", set())
        self.assertEqual(violations[0]["missing_prior"], ["functional", "allocated"])


class MilestoneViolationsTest(unittest.TestCase):
    def test_milestone_passed_no_violation(self):
        self.assertEqual(cb.milestone_violations("functional", {"SRR"}), [])

    def test_milestone_not_passed_flagged(self):
        violations = cb.milestone_violations("allocated", {"SRR"})
        self.assertEqual(
            violations,
            [
                {
                    "issue": "milestone_not_passed",
                    "baseline": "allocated",
                    "required_milestone": "PDR",
                }
            ],
        )


class ArtifactViolationsTest(unittest.TestCase):
    def test_complete_artifacts_no_violation(self):
        artifacts = {"top_level_requirements_doc", "functional_interface_spec"}
        self.assertEqual(cb.artifact_violations("functional", artifacts), [])

    def test_missing_artifacts_flagged_sorted(self):
        violations = cb.artifact_violations("functional", {"functional_interface_spec"})
        self.assertEqual(
            violations,
            [
                {
                    "issue": "missing_baseline_artifacts",
                    "baseline": "functional",
                    "missing_artifacts": ["top_level_requirements_doc"],
                }
            ],
        )


class EvaluateBaselineTest(unittest.TestCase):
    def test_fully_ready_baseline_has_no_violations(self):
        violations = cb.evaluate_baseline(
            "functional",
            completed_milestones={"SRR"},
            established_baselines=set(),
            available_artifacts={"top_level_requirements_doc", "functional_interface_spec"},
        )
        self.assertEqual(violations, [])
        self.assertTrue(cb.is_baseline_ready(violations))

    def test_all_three_checks_can_fail_together(self):
        violations = cb.evaluate_baseline(
            "product",
            completed_milestones=set(),
            established_baselines=set(),
            available_artifacts=set(),
        )
        issues = {v["issue"] for v in violations}
        self.assertEqual(
            issues,
            {"out_of_sequence_baseline", "milestone_not_passed", "missing_baseline_artifacts"},
        )
        self.assertFalse(cb.is_baseline_ready(violations))

    def test_unknown_baseline_raises(self):
        with self.assertRaises(ValueError):
            cb.evaluate_baseline("draft", set(), set(), set())


class ConfigurationBaselineReviewTest(unittest.TestCase):
    def test_fully_compliant_program(self):
        program = {
            "completed_milestones": ["SRR", "PDR", "CDR"],
            "established_baselines": ["functional", "allocated"],
            "artifacts": {
                "functional": ["top_level_requirements_doc", "functional_interface_spec"],
                "allocated": ["configuration_item_requirements", "interface_control_documents"],
                "product": [
                    "build_to_documentation",
                    "as_built_configuration_list",
                    "verification_closeout_record",
                ],
            },
        }
        review = cb.configuration_baseline_review(program)
        self.assertEqual(review, {"functional": [], "allocated": [], "product": []})
        self.assertTrue(cb.is_baseline_program_compliant(review))

    def test_early_program_flags_later_baselines_only(self):
        program = {
            "completed_milestones": ["SRR"],
            "established_baselines": [],
            "artifacts": {
                "functional": ["top_level_requirements_doc", "functional_interface_spec"],
            },
        }
        review = cb.configuration_baseline_review(program)
        self.assertEqual(review["functional"], [])
        self.assertTrue(review["allocated"])
        self.assertTrue(review["product"])
        self.assertFalse(cb.is_baseline_program_compliant(review))

    def test_unknown_milestone_in_program_raises(self):
        program = {"completed_milestones": ["MOT"], "established_baselines": [], "artifacts": {}}
        with self.assertRaises(ValueError):
            cb.configuration_baseline_review(program)

    def test_unknown_established_baseline_raises(self):
        program = {
            "completed_milestones": [],
            "established_baselines": ["draft"],
            "artifacts": {},
        }
        with self.assertRaises(ValueError):
            cb.configuration_baseline_review(program)


class NextEstablishableBaselineTest(unittest.TestCase):
    def test_nothing_established_srr_passed_returns_functional(self):
        self.assertEqual(
            cb.next_establishable_baseline(set(), {"SRR"}), "functional"
        )

    def test_no_milestones_passed_returns_none(self):
        self.assertIsNone(cb.next_establishable_baseline(set(), set()))

    def test_functional_established_pdr_passed_returns_allocated(self):
        self.assertEqual(
            cb.next_establishable_baseline({"functional"}, {"SRR", "PDR"}), "allocated"
        )

    def test_does_not_skip_ahead_of_unestablished_functional(self):
        # PDR passed but SRR (and thus "functional") never happened --
        # sequence must not let "allocated" jump the queue.
        self.assertIsNone(cb.next_establishable_baseline(set(), {"PDR"}))

    def test_all_established_returns_none(self):
        self.assertIsNone(
            cb.next_establishable_baseline(
                {"functional", "allocated", "product"}, {"SRR", "PDR", "CDR"}
            )
        )

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            cb.next_establishable_baseline(set(), {"MOT"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
