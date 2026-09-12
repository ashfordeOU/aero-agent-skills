#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 4.3.1 electrical design
verification provisions.

Exercises scripts/e20_electrical_design_verification_provisions_logic.py
(stdlib unittest, offline). Contract: docs/harness-contract.md gate 3 --
a verification method normalizes to one of the four recognized names and
anything else raises; the acceptable-method set is enforced per
requirement characteristic; preferred-method selection follows hardware
availability, destructiveness and whether the requirement is
quantitative; the earliest closure milestone follows the evidence a
method needs, with a test slipping from QR to AR when no qualification
model exists; a provision is flagged for an unacceptable method, an
over-optimistic milestone or a missing evidence artefact; coverage is
computed both ways and a duplicated or empty requirement set raises; and
the matrix is compliant only when both finding lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electrical_design_verification_provisions_logic as vp  # noqa: E402


class NormalizeMethodTest(unittest.TestCase):
    def test_canonical_method_passes_through(self):
        self.assertEqual(vp.normalize_method("analysis"), "analysis")

    def test_hyphen_and_case_are_normalized(self):
        self.assertEqual(vp.normalize_method("Review-Of-Design"), "review_of_design")

    def test_surrounding_space_is_stripped(self):
        self.assertEqual(vp.normalize_method("  inspection "), "inspection")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            vp.normalize_method("gut_feel")

    def test_non_string_method_raises(self):
        with self.assertRaises(ValueError):
            vp.normalize_method(7)


class MilestoneIndexTest(unittest.TestCase):
    def test_sequence_is_chronological(self):
        self.assertLess(vp.milestone_index("pdr"), vp.milestone_index("cdr"))
        self.assertLess(vp.milestone_index("cdr"), vp.milestone_index("qr"))
        self.assertLess(vp.milestone_index("qr"), vp.milestone_index("ar"))

    def test_case_is_normalized(self):
        self.assertEqual(vp.milestone_index("CDR"), vp.milestone_index("cdr"))

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            vp.milestone_index("frr")

    def test_non_string_milestone_raises(self):
        with self.assertRaises(ValueError):
            vp.milestone_index(None)


class MethodAcceptabilityTest(unittest.TestCase):
    def test_workmanship_accepts_inspection_only(self):
        self.assertTrue(vp.method_is_acceptable("workmanship", "inspection"))
        self.assertFalse(vp.method_is_acceptable("workmanship", "test"))
        self.assertFalse(vp.method_is_acceptable("workmanship", "analysis"))

    def test_part_selection_rejects_test(self):
        self.assertTrue(vp.method_is_acceptable("part_selection", "review_of_design"))
        self.assertFalse(vp.method_is_acceptable("part_selection", "test"))

    def test_performance_margin_rejects_design_argument(self):
        self.assertTrue(vp.method_is_acceptable("performance_margin", "test"))
        self.assertFalse(
            vp.method_is_acceptable("performance_margin", "review_of_design")
        )

    def test_unknown_characteristic_raises(self):
        with self.assertRaises(ValueError):
            vp.method_is_acceptable("vibe_check", "test")


class SelectVerificationMethodTest(unittest.TestCase):
    def test_workmanship_selects_inspection(self):
        self.assertEqual(
            vp.select_verification_method("workmanship", False, True, False),
            "inspection",
        )

    def test_part_selection_selects_design_argument(self):
        self.assertEqual(
            vp.select_verification_method("part_selection", False, True, False),
            "review_of_design",
        )

    def test_hardware_available_and_non_destructive_selects_test(self):
        self.assertEqual(
            vp.select_verification_method("performance_margin", True, True, False),
            "test",
        )

    def test_destructive_demonstration_falls_back_to_analysis(self):
        self.assertEqual(
            vp.select_verification_method("performance_margin", True, True, True),
            "analysis",
        )

    def test_no_hardware_and_qualitative_selects_design_argument(self):
        self.assertEqual(
            vp.select_verification_method("functional_behaviour", False, False, False),
            "review_of_design",
        )

    def test_no_hardware_and_emc_still_selects_analysis(self):
        self.assertEqual(
            vp.select_verification_method(
                "electromagnetic_compatibility", False, False, False
            ),
            "analysis",
        )

    def test_selected_method_is_always_acceptable(self):
        for characteristic in sorted(vp.REQUIREMENT_CHARACTERISTICS):
            for quantitative in (True, False):
                for hardware in (True, False):
                    for destructive in (True, False):
                        method = vp.select_verification_method(
                            characteristic, quantitative, hardware, destructive
                        )
                        self.assertTrue(
                            vp.method_is_acceptable(characteristic, method),
                            "%s -> %s" % (characteristic, method),
                        )

    def test_unknown_characteristic_raises(self):
        with self.assertRaises(ValueError):
            vp.select_verification_method("vibe_check", True, True, False)


class EarliestClosureMilestoneTest(unittest.TestCase):
    def test_design_argument_closes_at_pdr(self):
        self.assertEqual(vp.earliest_closure_milestone("review_of_design", False), "pdr")

    def test_analysis_closes_at_cdr(self):
        self.assertEqual(vp.earliest_closure_milestone("analysis", True), "cdr")

    def test_inspection_needs_hardware_at_qr(self):
        self.assertEqual(vp.earliest_closure_milestone("inspection", True), "qr")

    def test_test_with_qualification_model_closes_at_qr(self):
        self.assertEqual(vp.earliest_closure_milestone("test", True), "qr")

    def test_test_without_qualification_model_slips_to_ar(self):
        self.assertEqual(vp.earliest_closure_milestone("test", False), "ar")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            vp.earliest_closure_milestone("simulation_vibes", True)


def _requirement(requirement_id="EE-001", characteristic="performance_margin"):
    return {"requirement_id": requirement_id, "characteristic": characteristic}


def _provision(**overrides):
    provision = {
        "requirement_id": "EE-001",
        "method": "test",
        "milestone": "qr",
        "evidence_artefact": "EE-001 qualification report",
        "qualification_model_available": True,
    }
    provision.update(overrides)
    return provision


class ProvisionFindingsTest(unittest.TestCase):
    def test_well_formed_provision_has_no_finding(self):
        self.assertEqual(vp.provision_findings(_requirement(), _provision()), [])

    def test_unacceptable_method_is_flagged(self):
        findings = vp.provision_findings(
            _requirement(characteristic="workmanship"),
            _provision(method="test"),
        )
        issues = [finding["issue"] for finding in findings]
        self.assertIn("method_not_acceptable_for_characteristic", issues)

    def test_optimistic_milestone_is_flagged(self):
        findings = vp.provision_findings(
            _requirement(), _provision(milestone="cdr")
        )
        issues = [finding["issue"] for finding in findings]
        self.assertIn("milestone_earlier_than_method_can_close", issues)

    def test_missing_qualification_model_pushes_closure_to_ar(self):
        findings = vp.provision_findings(
            _requirement(),
            _provision(milestone="qr", qualification_model_available=False),
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["earliest_milestone"], "ar")

    def test_missing_evidence_artefact_is_flagged(self):
        findings = vp.provision_findings(
            _requirement(), _provision(evidence_artefact="")
        )
        issues = [finding["issue"] for finding in findings]
        self.assertIn("missing_evidence_artefact", issues)

    def test_several_defects_are_reported_together(self):
        findings = vp.provision_findings(
            _requirement(characteristic="workmanship"),
            _provision(method="test", milestone="pdr", evidence_artefact=None),
        )
        self.assertEqual(len(findings), 3)

    def test_provision_is_not_mutated(self):
        provision = _provision(milestone="QR")
        vp.provision_findings(_requirement(), provision)
        self.assertEqual(provision["milestone"], "QR")

    def test_unknown_method_in_provision_raises(self):
        with self.assertRaises(ValueError):
            vp.provision_findings(_requirement(), _provision(method="hand_waving"))

    def test_unknown_milestone_in_provision_raises(self):
        with self.assertRaises(ValueError):
            vp.provision_findings(_requirement(), _provision(milestone="lrr"))


class CoverageFindingsTest(unittest.TestCase):
    def test_full_coverage_has_no_finding(self):
        self.assertEqual(
            vp.coverage_findings([_requirement()], [_provision()]), []
        )

    def test_uncovered_requirement_is_flagged(self):
        findings = vp.coverage_findings([_requirement()], [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "requirement_without_verification_provision"
        )

    def test_orphan_provision_is_flagged(self):
        findings = vp.coverage_findings(
            [_requirement()], [_provision(), _provision(requirement_id="EE-999")]
        )
        issues = [finding["issue"] for finding in findings]
        self.assertEqual(issues, ["orphan_verification_provision"])

    def test_duplicate_requirement_identifier_raises(self):
        with self.assertRaises(ValueError):
            vp.coverage_findings([_requirement(), _requirement()], [_provision()])

    def test_empty_requirement_set_raises(self):
        with self.assertRaises(ValueError):
            vp.coverage_findings([], [])


class VerificationProvisionReviewTest(unittest.TestCase):
    def test_clean_matrix_is_compliant(self):
        review = vp.verification_provision_review([_requirement()], [_provision()])
        self.assertEqual(review["provision"], [])
        self.assertEqual(review["coverage"], [])
        self.assertTrue(vp.is_verification_plan_compliant(review))

    def test_uncovered_requirement_breaks_compliance(self):
        review = vp.verification_provision_review(
            [_requirement(), _requirement("EE-002", "workmanship")], [_provision()]
        )
        self.assertFalse(vp.is_verification_plan_compliant(review))
        self.assertEqual(len(review["coverage"]), 1)

    def test_orphan_provision_is_not_method_checked(self):
        review = vp.verification_provision_review(
            [_requirement()],
            [_provision(), _provision(requirement_id="EE-404", method="test",
                                      milestone="srr")],
        )
        self.assertEqual(review["provision"], [])
        self.assertEqual(len(review["coverage"]), 1)
        self.assertFalse(vp.is_verification_plan_compliant(review))

    def test_bad_method_breaks_compliance_with_full_coverage(self):
        review = vp.verification_provision_review(
            [_requirement("EE-003", "part_selection")],
            [_provision(requirement_id="EE-003", method="test", milestone="ar")],
        )
        self.assertEqual(review["coverage"], [])
        self.assertEqual(len(review["provision"]), 1)
        self.assertFalse(vp.is_verification_plan_compliant(review))


if __name__ == "__main__":
    unittest.main()
