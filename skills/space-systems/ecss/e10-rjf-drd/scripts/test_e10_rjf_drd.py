#!/usr/bin/env python3
"""Gate 3 behavior contract for e10-rjf-drd (stdlib unittest, offline)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e10_rjf_drd_logic import (  # noqa: E402
    DERIVATION_BASES, MIN_RATIONALE_WORDS, TOP_LEVEL_BASES,
    attribution_violations, basis_violations, is_rjf_complete,
    rationale_is_restatement, rationale_violations, rjf_review, validate_basis,
)


def req(rid="R1", text="The spacecraft shall survive launch loads.",
        rationale="Derived from the launcher user manual load envelope.",
        basis="applicable_standard", parent=None, top=False, author="SE"):
    return {"requirement_id": rid, "text": text, "rationale": rationale,
            "basis": basis, "parent_id": parent, "is_top_level": top,
            "author": author}


class BasisVocabularyTest(unittest.TestCase):
    def test_every_basis_validates(self):
        for b in DERIVATION_BASES:
            self.assertEqual(validate_basis(b), b)

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            validate_basis("because")

    def test_top_level_bases_are_a_subset(self):
        for b in TOP_LEVEL_BASES:
            self.assertIn(b, DERIVATION_BASES)


class RationaleTest(unittest.TestCase):
    def test_identical_text_is_a_restatement(self):
        self.assertTrue(rationale_is_restatement("Mass shall be under 50 kg.",
                                                 "mass shall be under 50 kg"))

    def test_substring_of_the_requirement_is_a_restatement(self):
        self.assertTrue(rationale_is_restatement(
            "The bus shall provide 28 V regulated power to all users.",
            "provide 28 v regulated power"))

    def test_genuine_reason_is_not_a_restatement(self):
        self.assertFalse(rationale_is_restatement(
            "Mass shall be under 50 kg.",
            "The launcher rideshare slot caps dispenser mass at 50 kg."))

    def test_empty_rationale_is_not_counted_as_restatement(self):
        self.assertFalse(rationale_is_restatement("anything", ""))

    def test_absent_rationale_is_reported(self):
        f = rationale_violations(req(rationale=""))
        self.assertEqual(f[0]["issue"], "no_rationale")

    def test_absent_rationale_short_circuits_other_rationale_checks(self):
        self.assertEqual(len(rationale_violations(req(rationale="   "))), 1)

    def test_too_short_rationale_is_reported(self):
        issues = [f["issue"] for f in rationale_violations(req(rationale="launcher"))]
        self.assertIn("rationale_too_short", issues)

    def test_restating_rationale_is_reported(self):
        r = req(text="Mass shall be under 50 kg.",
                rationale="Mass shall be under 50 kg.")
        issues = [f["issue"] for f in rationale_violations(r)]
        self.assertIn("rationale_restates_requirement", issues)

    def test_good_rationale_is_clean(self):
        self.assertEqual(rationale_violations(req()), [])

    def test_minimum_word_count_is_declared(self):
        self.assertGreaterEqual(MIN_RATIONALE_WORDS, 2)


class BasisTest(unittest.TestCase):
    def test_parent_basis_with_parent_is_clean(self):
        self.assertEqual(basis_violations(
            req(basis="parent_requirement", parent="SYS-1")), [])

    def test_parent_basis_without_parent_is_reported(self):
        f = basis_violations(req(basis="parent_requirement"))
        self.assertEqual(f[0]["issue"], "parent_basis_without_parent")

    def test_top_level_derived_from_parent_is_reported(self):
        f = basis_violations(req(basis="parent_requirement", top=True))
        self.assertEqual(f[0]["issue"], "top_level_derived_from_parent")

    def test_top_level_on_mission_need_is_clean(self):
        self.assertEqual(basis_violations(req(basis="mission_need", top=True)), [])

    def test_top_level_on_heritage_is_reported(self):
        f = basis_violations(req(basis="heritage", top=True))
        self.assertEqual(f[0]["issue"], "top_level_basis_not_external")

    def test_parent_recorded_alongside_analysis_basis_is_clean(self):
        self.assertEqual(basis_violations(req(basis="analysis", parent="SYS-1")), [])

    def test_unknown_basis_raises_from_the_check(self):
        with self.assertRaises(ValueError):
            basis_violations(req(basis="vibes"))


class AttributionTest(unittest.TestCase):
    def test_authored_requirement_is_clean(self):
        self.assertEqual(attribution_violations(req()), [])

    def test_unattributed_requirement_is_reported(self):
        self.assertEqual(attribution_violations(req(author=""))[0]["issue"],
                         "no_author")


class ReviewTest(unittest.TestCase):
    def test_clean_file_is_complete(self):
        r = rjf_review([req("R1"), req("R2", basis="analysis", parent="R1")])
        self.assertEqual(r["justified"], ["R1", "R2"])
        self.assertTrue(is_rjf_complete(r))

    def test_flagged_requirement_is_not_justified(self):
        r = rjf_review([req("R1"), req("R2", rationale="")])
        self.assertEqual(r["justified"], ["R1"])
        self.assertFalse(is_rjf_complete(r))

    def test_duplicate_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            rjf_review([req("R1"), req("R1")])

    def test_missing_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            rjf_review([req(rid="")])

    def test_empty_file_is_vacuously_complete(self):
        self.assertTrue(is_rjf_complete(rjf_review([])))

    def test_review_does_not_mutate_input(self):
        import copy
        rs = [req("R1"), req("R2", basis="analysis")]
        before = copy.deepcopy(rs)
        rjf_review(rs)
        self.assertEqual(rs, before)


if __name__ == "__main__":
    unittest.main()
