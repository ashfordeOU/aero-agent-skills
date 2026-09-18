#!/usr/bin/env python3
"""Gate 3 contract test for q6005-materials-and-parts-specifications.

Offline, stdlib unittest. Exercises the key normalisation, placeholder
detection, category-driven applicable set, the completeness ratio over that
set alone, the approval state and the procurement issue alignment of
ECSS-Q-ST-60-05C clause 9.3 as paraphrased in the logic module. The ratio
lands exactly on one for a finished document, so that bound is asserted with
assertAlmostEqual rather than a strict inequality that could round either way
between the build host and the CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_materials_and_parts_specifications_logic import (  # noqa: E402
    CATEGORY_CONTENT,
    CORE_CONTENT,
    HOLD,
    RELEASED,
    approval_state,
    assess_specification,
    assess_specification_set,
    completeness_ratio,
    is_defined,
    issue_alignment,
    normalise_key,
    required_content,
    surplus_content,
    undefined_content,
    validate_specification,
)


def full_content(category):
    """A content mapping defining every applicable item for a category."""
    return {item: "defined-%s" % item for item in required_content(category)}


def specification(category="adhesive", **overrides):
    record = {
        "designation": "HYB-MAT-%s-001" % category.upper(),
        "category": category,
        "content": full_content(category),
        "issue": "C",
        "approved_by": "materials engineering",
        "approval_date": "2026-04-17",
        "order_cites_issue": "C",
    }
    record.update(overrides)
    return record


class KeyAndValueTests(unittest.TestCase):
    def test_keys_normalise_across_separators_and_case(self):
        self.assertEqual(normalise_key("Cure_Schedule"), "cure-schedule")
        self.assertEqual(normalise_key(" shelf  life "), "shelf-life")

    def test_blank_key_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_key("   ")

    def test_placeholders_define_nothing(self):
        for placeholder in ("TBD", "to be confirmed", " n/a ", "-", ""):
            self.assertFalse(is_defined(placeholder), placeholder)

    def test_real_text_and_numbers_define_something(self):
        self.assertTrue(is_defined("150 C for 60 min"))
        self.assertTrue(is_defined(0))
        self.assertTrue(is_defined(False))

    def test_empty_collections_define_nothing_but_populated_ones_do(self):
        self.assertFalse(is_defined([]))
        self.assertFalse(is_defined({}))
        self.assertTrue(is_defined(["A", "B"]))


class ApplicableSetTests(unittest.TestCase):
    def test_every_category_carries_the_core_content(self):
        for category in CATEGORY_CONTENT:
            applicable = required_content(category)
            for item in CORE_CONTENT:
                self.assertIn(item, applicable, category)

    def test_category_adds_its_own_content_on_top(self):
        self.assertIn("cure-schedule", required_content("adhesive"))
        self.assertNotIn("cure-schedule", required_content("bonding-wire"))

    def test_unrecognised_category_is_refused(self):
        with self.assertRaises(ValueError):
            required_content("solder-paste")

    def test_category_name_is_normalised_before_lookup(self):
        self.assertEqual(required_content("Bonding_Wire"), required_content("bonding-wire"))


class SpecificationValidationTests(unittest.TestCase):
    def test_missing_required_key_is_refused(self):
        for key in ("designation", "category", "content"):
            record = specification()
            del record[key]
            with self.assertRaises(ValueError):
                validate_specification(record)

    def test_two_keys_normalising_to_one_item_are_refused(self):
        record = specification(content={"cure_schedule": "x", "Cure Schedule": "y"})
        with self.assertRaises(ValueError):
            validate_specification(record)

    def test_content_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_specification(specification(content=["cure-schedule"]))

    def test_issue_is_normalised_to_upper_case(self):
        self.assertEqual(validate_specification(specification(issue="c"))["issue"], "C")

    def test_blank_designation_is_refused(self):
        with self.assertRaises(ValueError):
            validate_specification(specification(designation="  "))


class CompletenessTests(unittest.TestCase):
    def test_a_finished_document_leaves_nothing_undefined(self):
        record = specification()
        self.assertEqual(undefined_content(record), [])
        self.assertAlmostEqual(completeness_ratio(record), 1.0, places=9)

    def test_a_placeholder_value_reads_as_undefined(self):
        content = full_content("adhesive")
        content["pot-life"] = "TBD"
        record = specification(content=content)
        self.assertEqual(undefined_content(record), ["pot-life"])

    def test_an_absent_item_reads_as_undefined(self):
        content = full_content("adhesive")
        del content["outgassing-data"]
        self.assertEqual(undefined_content(specification(content=content)), ["outgassing-data"])

    def test_undefined_items_are_reported_in_applicable_order(self):
        content = full_content("adhesive")
        content["shelf-life"] = ""
        content["item-designation"] = "TBC"
        undefined = undefined_content(specification(content=content))
        self.assertEqual(undefined, ["item-designation", "shelf-life"])

    def test_a_surplus_item_cannot_raise_the_ratio(self):
        content = full_content("adhesive")
        content["pot-life"] = "TBD"
        content["favourite-colour"] = "blue"
        record = specification(content=content)
        applicable = len(required_content("adhesive"))
        self.assertAlmostEqual(
            completeness_ratio(record), (applicable - 1) / float(applicable), places=9
        )
        self.assertEqual(surplus_content(record), ["favourite-colour"])

    def test_an_empty_document_scores_zero(self):
        self.assertAlmostEqual(completeness_ratio(specification(content={})), 0.0, places=9)


class ApprovalTests(unittest.TestCase):
    def test_a_signed_dated_issued_document_is_approved(self):
        state = approval_state(specification())
        self.assertTrue(state["approved"])
        self.assertEqual(state["findings"], [])
        self.assertEqual(state["approval_date"], "2026-04-17")

    def test_a_missing_approver_is_named(self):
        state = approval_state(specification(approved_by=None))
        self.assertFalse(state["approved"])
        self.assertTrue(any("approver" in f for f in state["findings"]))

    def test_a_missing_approval_date_is_named(self):
        state = approval_state(specification(approval_date="TBD"))
        self.assertFalse(state["approved"])
        self.assertTrue(any("approval date" in f for f in state["findings"]))

    def test_a_missing_issue_is_named(self):
        state = approval_state(specification(issue=None))
        self.assertFalse(state["approved"])
        self.assertTrue(any("issue" in f for f in state["findings"]))

    def test_a_malformed_approval_date_is_refused(self):
        with self.assertRaises(ValueError):
            approval_state(specification(approval_date="17/04/2026"))

    def test_a_non_string_approver_is_refused(self):
        with self.assertRaises(ValueError):
            approval_state(specification(approved_by=7))


class IssueAlignmentTests(unittest.TestCase):
    def test_matching_issues_align(self):
        alignment = issue_alignment(specification())
        self.assertTrue(alignment["aligned"])
        self.assertIsNone(alignment["finding"])

    def test_citation_is_matched_case_insensitively(self):
        self.assertTrue(issue_alignment(specification(order_cites_issue="c"))["aligned"])

    def test_an_order_citing_an_earlier_issue_is_reported(self):
        alignment = issue_alignment(specification(order_cites_issue="B"))
        self.assertFalse(alignment["aligned"])
        self.assertIn("issue B", alignment["finding"])

    def test_an_order_citing_nothing_is_reported(self):
        alignment = issue_alignment(specification(order_cites_issue=None))
        self.assertFalse(alignment["aligned"])
        self.assertIn("cites no specification issue", alignment["finding"])

    def test_an_order_citing_an_issue_the_document_lacks_is_reported(self):
        alignment = issue_alignment(specification(issue=None, order_cites_issue="C"))
        self.assertFalse(alignment["aligned"])
        self.assertIn("carries none", alignment["finding"])

    def test_a_non_string_citation_is_refused(self):
        with self.assertRaises(ValueError):
            issue_alignment(specification(order_cites_issue=3))


class SpecificationVerdictTests(unittest.TestCase):
    def test_a_finished_approved_aligned_document_is_released(self):
        verdict = assess_specification(specification())
        self.assertEqual(verdict["status"], RELEASED)
        self.assertEqual(verdict["findings"], [])
        self.assertTrue(verdict["content_complete"])
        self.assertAlmostEqual(verdict["completeness_ratio"], 1.0, places=9)

    def test_one_undefined_item_holds_the_document(self):
        content = full_content("substrate")
        content["metallization-system"] = "TBD"
        verdict = assess_specification(specification("substrate", content=content))
        self.assertEqual(verdict["status"], HOLD)
        self.assertEqual(verdict["undefined_content"], ["metallization-system"])

    def test_an_unapproved_but_complete_document_is_held(self):
        verdict = assess_specification(specification(approved_by=" "))
        self.assertEqual(verdict["status"], HOLD)
        self.assertTrue(verdict["content_complete"])
        self.assertFalse(verdict["approved"])

    def test_a_superseded_citation_holds_an_otherwise_finished_document(self):
        verdict = assess_specification(specification(order_cites_issue="A"))
        self.assertEqual(verdict["status"], HOLD)
        self.assertTrue(verdict["content_complete"])
        self.assertTrue(verdict["approved"])
        self.assertFalse(verdict["issue_aligned"])

    def test_several_failings_are_all_named(self):
        content = full_content("bonding-wire")
        content["spool-identification"] = "TBD"
        verdict = assess_specification(
            specification("bonding-wire", content=content, approved_by=None,
                          order_cites_issue=None)
        )
        self.assertEqual(verdict["status"], HOLD)
        self.assertGreaterEqual(len(verdict["findings"]), 3)

    def test_the_verdict_reports_the_applicable_count(self):
        verdict = assess_specification(specification("preform"))
        self.assertEqual(verdict["applicable_count"], len(required_content("preform")))


class SetRollupTests(unittest.TestCase):
    def test_an_all_released_set_is_ready_to_procure(self):
        result = assess_specification_set(
            [specification("adhesive"), specification("bonding-wire")]
        )
        self.assertTrue(result["ready_to_procure"])
        self.assertEqual(result["specification_count"], 2)
        self.assertAlmostEqual(result["mean_completeness_ratio"], 1.0, places=9)

    def test_one_held_document_holds_the_whole_procurement(self):
        content = full_content("preform")
        content["surface-condition"] = "TBD"
        result = assess_specification_set(
            [specification("adhesive"), specification("preform", content=content)]
        )
        self.assertFalse(result["ready_to_procure"])
        self.assertEqual(result["held"], ["HYB-MAT-PREFORM-001"])
        self.assertEqual(result["released"], ["HYB-MAT-ADHESIVE-001"])

    def test_duplicate_designations_are_refused(self):
        with self.assertRaises(ValueError):
            assess_specification_set([specification("adhesive"), specification("adhesive")])

    def test_an_empty_set_is_refused(self):
        with self.assertRaises(ValueError):
            assess_specification_set([])

    def test_a_mapping_is_not_a_set_of_specifications(self):
        with self.assertRaises(ValueError):
            assess_specification_set(specification())


if __name__ == "__main__":
    unittest.main(verbosity=2)
