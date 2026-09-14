#!/usr/bin/env python3
"""Contract test for the blocking diode production process document.

Walks the clause workflow step by step: whether the submission is a
document in force at all, whether the diode in front of the reviewer
belongs inside its scope, the steps the diode is genuinely built by
against the steps declared, the drift of each declared step away from the
baseline qualification ran on, the share of critical steps still standing
as qualified, the date arithmetic that catches a document issued after
the lot it covers, and the single document verdict. This is the gate 3
review evidence for the leaf.
"""

import copy
import unittest

from e2008_blocking_diode_production_control_logic import (
    PC_ACCEPTED,
    PC_INCOMPLETE,
    PC_NOT_IN_FORCE,
    PC_RANK,
    QUALIFICATION_CRITICAL,
    assess_blocking_diode_production_control,
    baseline_drift,
    construction_scope,
    document_precedes_lot,
    document_standing,
    standing_share,
    step_coverage,
)

ALL_STEPS = [
    "junction-formation",
    "surface-passivation",
    "die-attach",
    "package-seal",
    "lead-attach",
    "lead-finish",
    "screening-burn-in",
    "electrical-test",
    "marking",
    "packing",
]


def _steps(names=None, **overrides):
    rows = []
    for name in ALL_STEPS if names is None else names:
        row = {
            "step": name,
            "baseline_revision": "C",
            "current_revision": "C",
            "change_category": "unchanged",
            "controlling_document": "PD-%s" % name,
        }
        if name in overrides:
            row.update(overrides[name])
        rows.append(row)
    return rows


SOUND_CASE = {
    "document_id": "PD-BLOCK-DIODE-07",
    "document_form": "issued-and-in-force",
    "construction": "planar-blocking-diode",
    "qualification_granted": True,
    "document_issue_date": "2026-01-12",
    "lot_build_date": "2026-04-06",
    "steps_used": list(ALL_STEPS),
    "declared_steps": _steps(),
}


def _case(**overrides):
    record = copy.deepcopy(SOUND_CASE)
    record.update(overrides)
    return record


class DocumentStandingTests(unittest.TestCase):
    def test_an_issued_document_is_in_force(self):
        result = document_standing("issued-and-in-force")
        self.assertTrue(result["in_force"])
        self.assertEqual(result["findings"], [])

    def test_a_draft_is_written_but_not_in_force(self):
        result = document_standing("written-draft")
        self.assertTrue(result["written"])
        self.assertFalse(result["in_force"])
        self.assertTrue(result["findings"])

    def test_slides_are_not_a_written_document(self):
        result = document_standing("presentation-pack")
        self.assertFalse(result["written"])
        self.assertFalse(result["in_force"])

    def test_an_unknown_document_form_is_refused(self):
        with self.assertRaises(ValueError):
            document_standing("emailed-summary")


class ConstructionScopeTests(unittest.TestCase):
    def test_a_qualified_planar_part_is_in_scope(self):
        result = construction_scope("planar-blocking-diode", True)
        self.assertTrue(result["in_scope"])
        self.assertEqual(result["findings"], [])

    def test_a_qualified_mesa_part_is_also_in_scope(self):
        result = construction_scope("mesa-blocking-diode", True)
        self.assertTrue(result["discrete"])
        self.assertTrue(result["in_scope"])

    def test_an_integrated_diode_is_controlled_through_its_assembly(self):
        result = construction_scope("integrated-blocking-diode", True)
        self.assertFalse(result["in_scope"])
        self.assertTrue(result["findings"])

    def test_an_unqualified_discrete_part_has_no_qualified_build(self):
        result = construction_scope("planar-blocking-diode", False)
        self.assertTrue(result["discrete"])
        self.assertFalse(result["in_scope"])

    def test_a_non_boolean_qualification_flag_is_refused(self):
        with self.assertRaises(ValueError):
            construction_scope("planar-blocking-diode", "yes")


class StepCoverageTests(unittest.TestCase):
    def test_full_declaration_covers_every_step_used(self):
        result = step_coverage(ALL_STEPS, ALL_STEPS)
        self.assertEqual(result["undeclared"], [])
        self.assertEqual(result["declared_not_used"], [])
        self.assertAlmostEqual(result["coverage_share"], 1.0, places=9)

    def test_a_step_used_and_never_declared_is_named(self):
        declared = [s for s in ALL_STEPS if s != "surface-passivation"]
        result = step_coverage(declared, ALL_STEPS)
        self.assertEqual(result["undeclared"], ["surface-passivation"])
        self.assertIn("surface-passivation", result["missing_critical"])

    def test_a_declared_step_the_diode_is_not_built_by_is_named(self):
        used = [s for s in ALL_STEPS if s != "lead-finish"]
        result = step_coverage(ALL_STEPS, used)
        self.assertEqual(result["declared_not_used"], ["lead-finish"])

    def test_a_marking_gap_is_not_a_critical_gap(self):
        declared = [s for s in ALL_STEPS if s != "marking"]
        result = step_coverage(declared, ALL_STEPS)
        self.assertEqual(result["undeclared"], ["marking"])
        self.assertEqual(result["missing_critical"], [])

    def test_a_step_declared_twice_is_refused(self):
        with self.assertRaises(ValueError):
            step_coverage(ALL_STEPS + ["die-attach"], ALL_STEPS)

    def test_an_empty_used_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            step_coverage(ALL_STEPS, [])


class BaselineDriftTests(unittest.TestCase):
    def test_an_unmoved_build_stands_wholly_as_qualified(self):
        result = baseline_drift(_steps())
        self.assertEqual(result["drifted"], [])
        self.assertEqual(result["unnotified"], [])
        self.assertEqual(len(result["standing"]), len(ALL_STEPS))

    def test_a_major_change_with_requalification_still_stands(self):
        rows = _steps(
            **{
                "die-attach": {
                    "current_revision": "D",
                    "change_category": "major-change",
                    "requalification_reference": "RQ-2026-02",
                }
            }
        )
        result = baseline_drift(rows)
        self.assertEqual(result["drifted"], [])
        self.assertIn("die-attach", result["standing"])

    def test_a_major_change_without_requalification_has_drifted(self):
        rows = _steps(
            **{
                "package-seal": {
                    "current_revision": "E",
                    "change_category": "major-change",
                }
            }
        )
        result = baseline_drift(rows)
        self.assertEqual(result["drifted"], ["package-seal"])
        self.assertNotIn("package-seal", result["standing"])

    def test_a_minor_change_without_a_notice_is_unnotified(self):
        rows = _steps(
            **{
                "marking": {
                    "current_revision": "C1",
                    "change_category": "minor-change",
                }
            }
        )
        result = baseline_drift(rows)
        self.assertEqual(result["unnotified"], ["marking"])

    def test_a_minor_change_with_a_notice_still_stands(self):
        rows = _steps(
            **{
                "marking": {
                    "current_revision": "C1",
                    "change_category": "minor-change",
                    "change_notice": "CN-114",
                }
            }
        )
        result = baseline_drift(rows)
        self.assertEqual(result["unnotified"], [])
        self.assertIn("marking", result["standing"])

    def test_a_step_with_no_controlling_document_is_uncontrolled(self):
        rows = _steps(**{"lead-attach": {"controlling_document": "  "}})
        result = baseline_drift(rows)
        self.assertEqual(result["uncontrolled"], ["lead-attach"])

    def test_a_category_contradicting_the_revisions_is_refused(self):
        rows = _steps(**{"die-attach": {"change_category": "major-change"}})
        with self.assertRaises(ValueError):
            baseline_drift(rows)

    def test_a_step_listed_twice_is_refused(self):
        rows = _steps() + _steps(["die-attach"])
        with self.assertRaises(ValueError):
            baseline_drift(rows)

    def test_an_empty_entry_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            baseline_drift([])


class StandingShareTests(unittest.TestCase):
    def test_every_critical_step_standing_gives_a_full_share(self):
        result = standing_share(list(QUALIFICATION_CRITICAL))
        self.assertEqual(result["short"], [])
        self.assertAlmostEqual(result["standing_share"], 1.0, places=9)

    def test_one_critical_step_adrift_is_named_and_counted(self):
        held = [s for s in QUALIFICATION_CRITICAL if s != "package-seal"]
        result = standing_share(held)
        self.assertEqual(result["short"], ["package-seal"])
        self.assertAlmostEqual(
            result["standing_share"],
            (len(QUALIFICATION_CRITICAL) - 1) / len(QUALIFICATION_CRITICAL),
            places=9,
        )

    def test_an_empty_critical_policy_is_refused(self):
        with self.assertRaises(ValueError):
            standing_share(list(QUALIFICATION_CRITICAL), critical=())


class ChronologyTests(unittest.TestCase):
    def test_a_document_issued_before_the_lot_is_ordered(self):
        result = document_precedes_lot("2026-01-12", "2026-04-06")
        self.assertTrue(result["ordered"])
        self.assertEqual(result["days_ahead"], 84)

    def test_a_document_issued_after_the_lot_is_a_record(self):
        result = document_precedes_lot("2026-04-20", "2026-04-06")
        self.assertFalse(result["ordered"])
        self.assertEqual(result["days_ahead"], -14)
        self.assertTrue(result["findings"])

    def test_same_day_issue_is_ordered(self):
        result = document_precedes_lot("2026-04-06", "2026-04-06")
        self.assertTrue(result["ordered"])
        self.assertEqual(result["days_ahead"], 0)

    def test_a_malformed_date_is_refused(self):
        with self.assertRaises(ValueError):
            document_precedes_lot("April 2026", "2026-04-06")


class RolledUpAssessmentTests(unittest.TestCase):
    def test_a_sound_document_controls_the_qualified_build(self):
        result = assess_blocking_diode_production_control(_case())
        self.assertEqual(result["verdict"], PC_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["standing_floor_met"])

    def test_a_draft_is_not_a_document_in_force(self):
        result = assess_blocking_diode_production_control(
            _case(document_form="written-draft")
        )
        self.assertEqual(result["verdict"], PC_NOT_IN_FORCE)

    def test_an_integrated_diode_falls_outside_the_document(self):
        result = assess_blocking_diode_production_control(
            _case(construction="integrated-blocking-diode")
        )
        self.assertEqual(result["verdict"], PC_NOT_IN_FORCE)

    def test_an_undeclared_critical_step_leaves_the_document_incomplete(self):
        rows = _steps([s for s in ALL_STEPS if s != "junction-formation"])
        result = assess_blocking_diode_production_control(
            _case(declared_steps=rows)
        )
        self.assertEqual(result["verdict"], PC_INCOMPLETE)
        self.assertTrue(
            any("junction-formation" in f for f in result["findings"])
        )

    def test_an_uncarried_major_change_leaves_the_document_incomplete(self):
        rows = _steps(
            **{
                "screening-burn-in": {
                    "current_revision": "F",
                    "change_category": "major-change",
                }
            }
        )
        result = assess_blocking_diode_production_control(
            _case(declared_steps=rows)
        )
        self.assertEqual(result["verdict"], PC_INCOMPLETE)
        self.assertFalse(result["standing_floor_met"])

    def test_a_backwards_issue_date_leaves_the_document_incomplete(self):
        result = assess_blocking_diode_production_control(
            _case(document_issue_date="2026-05-01")
        )
        self.assertEqual(result["verdict"], PC_INCOMPLETE)
        self.assertFalse(result["chronology"]["ordered"])

    def test_a_major_change_carried_by_requalification_closes_the_document(self):
        rows = _steps(
            **{
                "screening-burn-in": {
                    "current_revision": "F",
                    "change_category": "major-change",
                    "requalification_reference": "RQ-2026-09",
                }
            }
        )
        result = assess_blocking_diode_production_control(
            _case(declared_steps=rows)
        )
        self.assertEqual(result["verdict"], PC_ACCEPTED)

    def test_the_verdict_rank_orders_the_three_outcomes(self):
        self.assertLess(PC_RANK[PC_NOT_IN_FORCE], PC_RANK[PC_INCOMPLETE])
        self.assertLess(PC_RANK[PC_INCOMPLETE], PC_RANK[PC_ACCEPTED])

    def test_an_empty_declared_step_list_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_production_control(_case(declared_steps=[]))

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_production_control(
                "the production route was written up"
            )

    def test_a_non_numeric_floor_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_production_control(
                _case(policy={"min_standing_share": "all of them"})
            )


if __name__ == "__main__":
    unittest.main()
