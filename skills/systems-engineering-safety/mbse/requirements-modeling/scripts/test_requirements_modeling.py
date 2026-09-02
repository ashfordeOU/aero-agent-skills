#!/usr/bin/env python3
"""Gate 3 contract test: SysML requirements modeling.

Exercises scripts/requirements_modeling_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (requirement id
format validation, shall clause atomicity counting, vague term
screening, verifiability verdicts, relationship kind checks, derive
chain checks, verification status roll-up, satisfy and verify link
coverage, and the combined model review verdict; invalid inputs raise
ValueError.

Anchors:
- validate_requirement_id("SYS-001") = True; ("sys-001") = False
- count_shall_clauses("The system shall provide X.") = 1
- find_vague_terms("adequate") = ["adequate"]
- requirement_verifiability single shall, no vague term, method test
  = verifiable True
- rollup_verification_status(["verified", "verified"]) = "verified"
- satisfy_coverage(["SYS-001"], [("SYS-001", "elem")]) = (1.0, [])
- verify_coverage(["SYS-001"], []) = (0.0, ["SYS-001"])
- relationship_kind_valid("derive") = True; ("owns") = False
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requirements_modeling_logic as rqm  # noqa: E402


class RequirementIdTest(unittest.TestCase):
    def test_anchor_valid_sys_id(self):
        self.assertTrue(rqm.validate_requirement_id("SYS-001"))

    def test_anchor_valid_fc_id(self):
        self.assertTrue(rqm.validate_requirement_id("FC-0001"))

    def test_lowercase_rejected(self):
        self.assertFalse(rqm.validate_requirement_id("sys-001"))

    def test_missing_hyphen_rejected(self):
        self.assertFalse(rqm.validate_requirement_id("SYS001"))

    def test_short_digits_rejected(self):
        self.assertFalse(rqm.validate_requirement_id("SYS-01"))

    def test_long_prefix_rejected(self):
        self.assertFalse(rqm.validate_requirement_id("SYSTEM-001"))

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            rqm.validate_requirement_id(123)


class ShallClauseTest(unittest.TestCase):
    def test_anchor_single_shall(self):
        self.assertEqual(rqm.count_shall_clauses("The system shall provide X."), 1)

    def test_two_shall_clauses(self):
        self.assertEqual(
            rqm.count_shall_clauses("The system shall do A and shall do B."), 2
        )

    def test_no_shall_clause(self):
        self.assertEqual(rqm.count_shall_clauses("The system provides X."), 0)

    def test_case_insensitive_shall(self):
        self.assertEqual(rqm.count_shall_clauses("The System SHALL respond."), 1)

    def test_shall_not_substring(self):
        self.assertEqual(rqm.count_shall_clauses("Shallows are avoided."), 0)

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            rqm.count_shall_clauses(None)


class VagueTermTest(unittest.TestCase):
    def test_anchor_adequate(self):
        self.assertEqual(rqm.find_vague_terms("The part shall be adequate."), ["adequate"])

    def test_no_vague_terms(self):
        self.assertEqual(
            rqm.find_vague_terms("The system shall provide 28 VDC at pin 4."), []
        )

    def test_multiple_terms_sorted(self):
        self.assertEqual(
            rqm.find_vague_terms("approximately adequate and suitable"), [
                "adequate",
                "approximately",
                "suitable",
            ]
        )

    def test_case_insensitive_term(self):
        self.assertEqual(rqm.find_vague_terms("Timely response required."), ["timely"])

    def test_multiword_term(self):
        self.assertEqual(
            rqm.find_vague_terms("The result as required by the plan."), ["as required"]
        )

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            rqm.find_vague_terms(42)


class VerifiabilityTest(unittest.TestCase):
    def test_anchor_verifiable(self):
        req = {
            "id": "SYS-001",
            "text": "The system shall provide 28 VDC at pin 4.",
            "method": "test",
        }
        verdict = rqm.requirement_verifiability(req)
        self.assertTrue(verdict["verifiable"])
        self.assertEqual(verdict["reasons"], [])

    def test_vague_term_fails(self):
        req = {
            "id": "SYS-002",
            "text": "The system shall be approximately 28 VDC.",
            "method": "test",
        }
        verdict = rqm.requirement_verifiability(req)
        self.assertFalse(verdict["verifiable"])
        self.assertIn("vague terms: approximately", verdict["reasons"])

    def test_two_shall_clauses_fail(self):
        req = {
            "id": "SYS-003",
            "text": "The system shall do A and shall do B.",
            "method": "analysis",
        }
        verdict = rqm.requirement_verifiability(req)
        self.assertFalse(verdict["verifiable"])
        self.assertIn("shall-clause count 2, expected 1", verdict["reasons"])

    def test_invalid_method_fails(self):
        req = {
            "id": "SYS-004",
            "text": "The system shall open the valve.",
            "method": "review",
        }
        verdict = rqm.requirement_verifiability(req)
        self.assertFalse(verdict["verifiable"])
        self.assertIn("method 'review' not in test, analysis, demonstration, inspection", verdict["reasons"])

    def test_inspection_method_accepted(self):
        req = {
            "id": "SYS-005",
            "text": "The placard shall show the serial number.",
            "method": "inspection",
        }
        self.assertTrue(rqm.requirement_verifiability(req)["verifiable"])

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            rqm.requirement_verifiability({"id": "SYS-001", "text": "x"})


class StatusRollupTest(unittest.TestCase):
    def test_anchor_all_verified(self):
        self.assertEqual(
            rqm.rollup_verification_status(["verified", "verified"]), "verified"
        )

    def test_any_failed_fails_parent(self):
        self.assertEqual(
            rqm.rollup_verification_status(["verified", "failed", "verified"]), "failed"
        )

    def test_in_review_keeps_parent_in_review(self):
        self.assertEqual(
            rqm.rollup_verification_status(["verified", "in-review"]), "in-review"
        )

    def test_all_not_assessed(self):
        self.assertEqual(
            rqm.rollup_verification_status(["not-assessed", "not-assessed"]),
            "not-assessed",
        )

    def test_empty_list_not_assessed(self):
        self.assertEqual(rqm.rollup_verification_status([]), "not-assessed")

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            rqm.rollup_verification_status("verified")


class SatisfyCoverageTest(unittest.TestCase):
    def test_anchor_full_coverage(self):
        frac, missing = rqm.satisfy_coverage(
            ["SYS-001"], [("SYS-001", "elem-a")]
        )
        self.assertEqual(frac, 1.0)
        self.assertEqual(missing, [])

    def test_partial_coverage_gap_list(self):
        frac, missing = rqm.satisfy_coverage(
            ["SYS-001", "SYS-002", "SYS-003"],
            [("SYS-001", "elem-a"), ("SYS-003", "elem-c")],
        )
        self.assertAlmostEqual(frac, 2.0 / 3.0)
        self.assertEqual(missing, ["SYS-002"])

    def test_empty_requirement_list_full(self):
        frac, missing = rqm.satisfy_coverage([], [])
        self.assertEqual(frac, 1.0)
        self.assertEqual(missing, [])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            rqm.satisfy_coverage("SYS-001", [])


class VerifyCoverageTest(unittest.TestCase):
    def test_anchor_zero_coverage(self):
        frac, missing = rqm.verify_coverage(["SYS-001"], [])
        self.assertEqual(frac, 0.0)
        self.assertEqual(missing, ["SYS-001"])

    def test_anchor_full_coverage(self):
        frac, missing = rqm.verify_coverage(
            ["SYS-001"], [("SYS-001", "test-case-7")]
        )
        self.assertEqual(frac, 1.0)
        self.assertEqual(missing, [])

    def test_partial_verify_gap_list(self):
        frac, missing = rqm.verify_coverage(
            ["SYS-001", "SYS-002"],
            [("SYS-002", "analysis-note-3")],
        )
        self.assertAlmostEqual(frac, 0.5)
        self.assertEqual(missing, ["SYS-001"])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            rqm.verify_coverage(["SYS-001"], None)


class DeriveChainTest(unittest.TestCase):
    def test_anchor_valid_chain(self):
        valid, issues = rqm.derive_chain_check([("SYS-001", "SYS-002")])
        self.assertTrue(valid)
        self.assertEqual(issues, [])

    def test_self_derive_flagged(self):
        valid, issues = rqm.derive_chain_check([("SYS-001", "SYS-001")])
        self.assertFalse(valid)
        self.assertIn("self-derive 'SYS-001'", issues)

    def test_invalid_source_flagged(self):
        valid, issues = rqm.derive_chain_check([("bad", "SYS-002")])
        self.assertFalse(valid)
        self.assertIn("invalid source id 'bad'", issues)

    def test_invalid_target_flagged(self):
        valid, issues = rqm.derive_chain_check([("SYS-001", "sys-002")])
        self.assertFalse(valid)
        self.assertIn("invalid target id 'sys-002'", issues)

    def test_issues_deduplicated(self):
        valid, issues = rqm.derive_chain_check([("SYS-001", "SYS-001"), ("SYS-001", "SYS-001")])
        self.assertFalse(valid)
        self.assertEqual(len(issues), 1)

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            rqm.derive_chain_check("SYS-001,SYS-002")


class RelationshipKindTest(unittest.TestCase):
    def test_anchor_derive_valid(self):
        self.assertTrue(rqm.relationship_kind_valid("derive"))

    def test_all_kinds_valid(self):
        for kind in ("derive", "satisfy", "verify", "refine", "trace"):
            self.assertTrue(rqm.relationship_kind_valid(kind))

    def test_unknown_kind_invalid(self):
        self.assertFalse(rqm.relationship_kind_valid("owns"))

    def test_case_sensitive_kind(self):
        self.assertFalse(rqm.relationship_kind_valid("Derive"))


class ModelReviewVerdictTest(unittest.TestCase):
    def test_anchor_ready_verdict(self):
        verdict = rqm.model_review_verdict(
            ["SYS-001"],
            [("SYS-001", "elem-a")],
            [("SYS-001", "test-case-7")],
            ["verified"],
        )
        self.assertEqual(verdict["verdict"], "ready")
        self.assertEqual(verdict["satisfy_fraction"], 1.0)
        self.assertEqual(verdict["verify_fraction"], 1.0)
        self.assertEqual(verdict["rollup"], "verified")
        self.assertEqual(verdict["reasons"], [])

    def test_gaps_verdict_unsatisfied(self):
        verdict = rqm.model_review_verdict(
            ["SYS-001", "SYS-002"],
            [("SYS-001", "elem-a")],
            [("SYS-001", "test-case-7"), ("SYS-002", "test-case-8")],
            ["verified", "verified"],
        )
        self.assertEqual(verdict["verdict"], "gaps")
        self.assertIn("unsatisfied: SYS-002", verdict["reasons"])

    def test_gaps_verdict_unverified(self):
        verdict = rqm.model_review_verdict(
            ["SYS-001"],
            [("SYS-001", "elem-a")],
            [],
            ["verified"],
        )
        self.assertEqual(verdict["verdict"], "gaps")
        self.assertIn("unverified: SYS-001", verdict["reasons"])

    def test_gaps_verdict_rollup_not_verified(self):
        verdict = rqm.model_review_verdict(
            ["SYS-001"],
            [("SYS-001", "elem-a")],
            [("SYS-001", "test-case-7")],
            ["in-review"],
        )
        self.assertEqual(verdict["verdict"], "gaps")
        self.assertIn("roll-up status in-review", verdict["reasons"])


class EndToEndScenarioTest(unittest.TestCase):
    def test_scenario_landing_gear_requirements_tree(self):
        # Landing gear control requirements: parent derived from
        # SYS-001, children SYS-002 (deploy) and SYS-003 (retract).
        # One child has no verify link; the model review must be gaps.
        parent = {
            "id": "SYS-001",
            "text": "The system shall control landing gear deployment and retraction.",
            "method": "test",
        }
        child_a = {
            "id": "SYS-002",
            "text": "The system shall deploy the landing gear on command.",
            "method": "test",
        }
        child_b = {
            "id": "SYS-003",
            "text": "The system shall retract the landing gear on command.",
            "method": "analysis",
        }
        ids = ["SYS-001", "SYS-002", "SYS-003"]
        for req in (parent, child_a, child_b):
            self.assertTrue(rqm.requirement_verifiability(req)["verifiable"])
        valid, issues = rqm.derive_chain_check(
            [("SYS-001", "SYS-002"), ("SYS-001", "SYS-003")]
        )
        self.assertTrue(valid)
        self.assertEqual(issues, [])
        frac, missing = rqm.satisfy_coverage(
            ids,
            [("SYS-001", "lgcu"), ("SYS-002", "lgcu"), ("SYS-003", "lgcu")],
        )
        self.assertEqual(frac, 1.0)
        self.assertEqual(missing, [])
        vfrac, vmissing = rqm.verify_coverage(
            ids, [("SYS-001", "t-1"), ("SYS-002", "t-2")]
        )
        self.assertAlmostEqual(vfrac, 2.0 / 3.0)
        self.assertEqual(vmissing, ["SYS-003"])
        rollup = rqm.rollup_verification_status(["verified", "verified", "in-review"])
        self.assertEqual(rollup, "in-review")
        verdict = rqm.model_review_verdict(
            ids,
            [("SYS-001", "lgcu"), ("SYS-002", "lgcu"), ("SYS-003", "lgcu")],
            [("SYS-001", "t-1"), ("SYS-002", "t-2")],
            ["verified", "verified", "in-review"],
        )
        self.assertEqual(verdict["verdict"], "gaps")
        self.assertIn("unverified: SYS-003", verdict["reasons"])
        self.assertIn("roll-up status in-review", verdict["reasons"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
