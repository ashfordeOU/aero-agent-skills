#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10 Annex G Design Definition File
(DDF) DRD structure check.

Exercises scripts/e10_ddf_drd_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - an unrecognized review
milestone or maturity level raises; the mandatory content-block set
grows monotonically from SRR through PDR and CDR and does not grow
further at AR; a content-block id outside the Annex G catalogue is
flagged as unrecognized; a mandatory block that is missing, or present
below the milestone's minimum maturity, is flagged; the open-points
register's unresolved-item count is checked only at the AR closure
milestone; and the DDF is reported compliant only when every finding
category is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_ddf_drd_logic as ddf  # noqa: E402


class MilestoneIndexTest(unittest.TestCase):
    def test_known_milestones_ordered(self):
        self.assertEqual(ddf.milestone_index("SRR"), 0)
        self.assertEqual(ddf.milestone_index("PDR"), 1)
        self.assertEqual(ddf.milestone_index("CDR"), 2)
        self.assertEqual(ddf.milestone_index("AR"), 3)

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ddf.DDFValidationError):
            ddf.milestone_index("MDR")


class MaturityIndexTest(unittest.TestCase):
    def test_known_maturity_ordered(self):
        self.assertEqual(ddf.maturity_index("draft"), 0)
        self.assertEqual(ddf.maturity_index("consolidated"), 1)
        self.assertEqual(ddf.maturity_index("final"), 2)

    def test_unknown_maturity_raises(self):
        with self.assertRaises(ddf.DDFValidationError):
            ddf.maturity_index("preliminary")


class RequiredBlocksForMilestoneTest(unittest.TestCase):
    def test_srr_requires_five_blocks(self):
        required = ddf.required_blocks_for_milestone("SRR")
        self.assertEqual(
            sorted(required),
            sorted(
                [
                    "introduction",
                    "applicable_and_reference_documents",
                    "terms_definitions_abbreviations",
                    "design_overview",
                    "open_points_register",
                ]
            ),
        )

    def test_pdr_adds_three_blocks(self):
        required = set(ddf.required_blocks_for_milestone("PDR"))
        self.assertTrue(required.issuperset(ddf.required_blocks_for_milestone("SRR")))
        self.assertEqual(len(required), 8)
        for block_id in (
            "design_solution_per_item",
            "budgets_and_margins",
            "interfaces_definition",
        ):
            self.assertIn(block_id, required)

    def test_cdr_adds_two_more_blocks(self):
        required = set(ddf.required_blocks_for_milestone("CDR"))
        self.assertTrue(required.issuperset(ddf.required_blocks_for_milestone("PDR")))
        self.assertEqual(len(required), 10)

    def test_ar_matches_cdr_set(self):
        self.assertEqual(
            set(ddf.required_blocks_for_milestone("AR")),
            set(ddf.required_blocks_for_milestone("CDR")),
        )

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ddf.DDFValidationError):
            ddf.required_blocks_for_milestone("QR")


def _srr_compliant_blocks():
    return {
        block_id: ddf.BlockRecord(present=True, maturity="draft")
        for block_id in ddf.required_blocks_for_milestone("SRR")
    }


class AssessDdfStructureTest(unittest.TestCase):
    def test_fully_compliant_at_srr(self):
        assessment = ddf.assess_ddf_structure("SRR", _srr_compliant_blocks())
        self.assertEqual(assessment.missing_mandatory, [])
        self.assertEqual(assessment.unrecognized_blocks, [])
        self.assertEqual(assessment.insufficient_maturity, [])
        self.assertTrue(assessment.compliant)

    def test_missing_mandatory_block_flagged(self):
        blocks = _srr_compliant_blocks()
        del blocks["design_overview"]
        assessment = ddf.assess_ddf_structure("SRR", blocks)
        self.assertIn("design_overview", assessment.missing_mandatory)
        self.assertFalse(assessment.compliant)

    def test_present_false_counts_as_missing(self):
        blocks = _srr_compliant_blocks()
        blocks["introduction"] = ddf.BlockRecord(present=False)
        assessment = ddf.assess_ddf_structure("SRR", blocks)
        self.assertIn("introduction", assessment.missing_mandatory)

    def test_unrecognized_block_id_flagged(self):
        blocks = _srr_compliant_blocks()
        blocks["schedule_summary"] = ddf.BlockRecord(present=True, maturity="draft")
        assessment = ddf.assess_ddf_structure("SRR", blocks)
        self.assertEqual(assessment.unrecognized_blocks, ["schedule_summary"])
        self.assertFalse(assessment.compliant)

    def test_missing_maturity_on_mandatory_block_flagged(self):
        blocks = _srr_compliant_blocks()
        blocks["introduction"] = ddf.BlockRecord(present=True, maturity=None)
        assessment = ddf.assess_ddf_structure("SRR", blocks)
        self.assertIn("introduction", assessment.insufficient_maturity)
        self.assertFalse(assessment.compliant)

    def test_maturity_below_milestone_minimum_flagged(self):
        blocks = {
            block_id: ddf.BlockRecord(present=True, maturity="draft")
            for block_id in ddf.required_blocks_for_milestone("PDR")
        }
        assessment = ddf.assess_ddf_structure("PDR", blocks)
        # PDR requires "consolidated" minimum; "draft" is one level short.
        self.assertTrue(set(assessment.insufficient_maturity))
        self.assertFalse(assessment.compliant)

    def test_early_inclusion_of_later_block_not_a_finding(self):
        blocks = _srr_compliant_blocks()
        blocks["annexes_supporting_data"] = ddf.BlockRecord(
            present=True, maturity="draft"
        )
        assessment = ddf.assess_ddf_structure("SRR", blocks)
        self.assertTrue(assessment.compliant)

    def test_ar_with_unresolved_open_items_not_compliant(self):
        blocks = {
            block_id: ddf.BlockRecord(present=True, maturity="final")
            for block_id in ddf.required_blocks_for_milestone("AR")
        }
        blocks["open_points_register"] = ddf.BlockRecord(
            present=True, maturity="final", open_item_count=2
        )
        assessment = ddf.assess_ddf_structure("AR", blocks)
        self.assertEqual(assessment.unresolved_open_items_at_closure, 2)
        self.assertFalse(assessment.compliant)

    def test_ar_with_zero_open_items_compliant(self):
        blocks = {
            block_id: ddf.BlockRecord(present=True, maturity="final")
            for block_id in ddf.required_blocks_for_milestone("AR")
        }
        blocks["open_points_register"] = ddf.BlockRecord(
            present=True, maturity="final", open_item_count=0
        )
        assessment = ddf.assess_ddf_structure("AR", blocks)
        self.assertEqual(assessment.unresolved_open_items_at_closure, 0)
        self.assertTrue(assessment.compliant)

    def test_open_items_ignored_before_ar(self):
        blocks = _srr_compliant_blocks()
        blocks["open_points_register"] = ddf.BlockRecord(
            present=True, maturity="draft", open_item_count=7
        )
        assessment = ddf.assess_ddf_structure("SRR", blocks)
        self.assertEqual(assessment.unresolved_open_items_at_closure, 0)
        self.assertTrue(assessment.compliant)

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ddf.DDFValidationError):
            ddf.assess_ddf_structure("QR", {})

    def test_unknown_maturity_value_raises(self):
        blocks = _srr_compliant_blocks()
        blocks["introduction"] = ddf.BlockRecord(present=True, maturity="polished")
        with self.assertRaises(ddf.DDFValidationError):
            ddf.assess_ddf_structure("SRR", blocks)


if __name__ == "__main__":
    unittest.main(verbosity=2)
