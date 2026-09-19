#!/usr/bin/env python3
"""Gate 3 contract test for q6005-hybrid-lot-rejection.

Offline, stdlib unittest. Exercises the stage-verdict validation, the evidence
chain measurement, the earliest-failing-stage rule, the rejection scope, the
admissibility check and the three-way lot status of ECSS-Q-ST-60-05C clause
10.4 as paraphrased in the logic module. Evidence completeness lands exactly
on one for a fully worked lot, so that bound is asserted with
assertAlmostEqual rather than a strict inequality that libm could round either
way between build host and CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_hybrid_lot_rejection_logic import (  # noqa: E402
    MANDATORY_SEQUENCE,
    declare_lot_status,
    evidence_completeness,
    first_failing_stage,
    missing_stages,
    rejection_scope,
    stage_order,
    status_obligations,
    validate_stage_verdicts,
)


def all_pass(**overrides):
    """A fully worked lot with every mandatory stage passing."""
    verdicts = {stage: "pass" for stage in MANDATORY_SEQUENCE}
    verdicts.update(overrides)
    return [{"stage": stage, "verdict": verdicts[stage]} for stage in MANDATORY_SEQUENCE]


def lot(**overrides):
    spec = {"stage_verdicts": all_pass(), "declared_by": "manufacturer-quality"}
    spec.update(overrides)
    return spec


class StageVerdictValidationTests(unittest.TestCase):
    def test_empty_record_set_is_refused(self):
        with self.assertRaises(ValueError):
            validate_stage_verdicts([])

    def test_mapping_is_not_a_sequence_of_records(self):
        with self.assertRaises(ValueError):
            validate_stage_verdicts({"stage": "burn-in", "verdict": "pass"})

    def test_unknown_stage_is_refused(self):
        with self.assertRaises(ValueError):
            validate_stage_verdicts([{"stage": "vibration-survey", "verdict": "pass"}])

    def test_unknown_verdict_is_refused(self):
        with self.assertRaises(ValueError):
            validate_stage_verdicts([{"stage": "burn-in", "verdict": "probably-fine"}])

    def test_duplicate_stage_is_refused_not_resolved(self):
        records = [
            {"stage": "burn-in", "verdict": "pass"},
            {"stage": "burn-in", "verdict": "fail"},
        ]
        with self.assertRaises(ValueError):
            validate_stage_verdicts(records)

    def test_record_without_a_verdict_is_refused(self):
        with self.assertRaises(ValueError):
            validate_stage_verdicts([{"stage": "burn-in"}])

    def test_names_are_matched_case_and_separator_insensitively(self):
        normalised = validate_stage_verdicts([{"stage": "BURN IN", "verdict": "PASS"}])
        self.assertEqual(normalised[0]["stage"], "burn-in")
        self.assertEqual(normalised[0]["verdict"], "pass")

    def test_records_come_back_in_worked_order(self):
        records = [
            {"stage": "external-visual", "verdict": "pass"},
            {"stage": "internal-visual", "verdict": "pass"},
        ]
        order = [item["stage"] for item in validate_stage_verdicts(records)]
        self.assertEqual(order, ["internal-visual", "external-visual"])

    def test_stage_order_rejects_a_stage_outside_the_sequence(self):
        self.assertEqual(stage_order("internal-visual"), 0)
        with self.assertRaises(ValueError):
            stage_order("lid-polishing")


class EvidenceChainTests(unittest.TestCase):
    def test_fully_worked_lot_has_complete_evidence(self):
        # Completeness lands exactly on one; assert the equality, not a side of it.
        self.assertAlmostEqual(evidence_completeness(all_pass()), 1.0, places=9)
        self.assertEqual(missing_stages(all_pass()), [])

    def test_absent_stage_is_not_a_pass(self):
        records = [r for r in all_pass() if r["stage"] != "burn-in"]
        self.assertEqual(missing_stages(records), ["burn-in"])
        self.assertAlmostEqual(evidence_completeness(records), 0.9, places=9)

    def test_not_run_verdict_counts_the_same_as_an_absent_record(self):
        records = all_pass(**{"burn-in": "not-run"})
        self.assertEqual(missing_stages(records), ["burn-in"])
        self.assertAlmostEqual(evidence_completeness(records), 0.9, places=9)

    def test_missing_stages_are_reported_in_worked_order(self):
        records = all_pass(**{"external-visual": "not-run", "internal-visual": "not-run"})
        self.assertEqual(missing_stages(records), ["internal-visual", "external-visual"])


class FailingStageTests(unittest.TestCase):
    def test_clean_lot_has_no_failing_stage(self):
        self.assertIsNone(first_failing_stage(all_pass()))

    def test_earliest_failure_wins_regardless_of_record_order(self):
        records = all_pass(**{"external-visual": "fail", "temperature-cycling": "fail"})
        records.reverse()
        self.assertEqual(first_failing_stage(records), "temperature-cycling")


class RejectionScopeTests(unittest.TestCase):
    def test_all_three_conditions_give_a_sublot_scope(self):
        context = {
            "failures_confined_to_one_sublot": True,
            "sublot_physically_segregated": True,
            "sublot_traceability_intact": True,
        }
        self.assertEqual(rejection_scope(context), "sublot")

    def test_any_condition_absent_makes_the_rejection_lot_wide(self):
        for missing in (
            "failures_confined_to_one_sublot",
            "sublot_physically_segregated",
            "sublot_traceability_intact",
        ):
            context = {
                "failures_confined_to_one_sublot": True,
                "sublot_physically_segregated": True,
                "sublot_traceability_intact": True,
            }
            context[missing] = False
            self.assertEqual(rejection_scope(context), "whole-lot")

    def test_unset_conditions_default_to_a_lot_wide_scope(self):
        self.assertEqual(rejection_scope({}), "whole-lot")

    def test_non_boolean_condition_is_refused(self):
        with self.assertRaises(ValueError):
            rejection_scope({"failures_confined_to_one_sublot": "yes"})


class DeclarationTests(unittest.TestCase):
    def test_fully_worked_passing_lot_is_accepted(self):
        result = declare_lot_status(lot())
        self.assertEqual(result["status"], "accepted")
        self.assertFalse(result["rejected"])
        self.assertTrue(result["evidence_complete"])
        self.assertAlmostEqual(result["evidence_completeness"], 1.0, places=9)
        self.assertEqual(result["scope"], "not-applicable")

    def test_a_failure_rejects_the_lot_and_names_the_stage(self):
        result = declare_lot_status(lot(stage_verdicts=all_pass(**{"burn-in": "fail"})))
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(result["rejected"])
        self.assertEqual(result["first_failing_stage"], "burn-in")
        self.assertEqual(result["scope"], "whole-lot")

    def test_unrun_stage_without_a_failure_is_indeterminate_not_accepted(self):
        records = [r for r in all_pass() if r["stage"] != "lot-acceptance-tests"]
        result = declare_lot_status(lot(stage_verdicts=records))
        self.assertEqual(result["status"], "indeterminate")
        self.assertFalse(result["evidence_complete"])
        self.assertTrue(any("never ran" in f for f in result["findings"]))

    def test_rejection_on_a_broken_chain_is_not_admissible(self):
        records = all_pass(**{"temperature-cycling": "not-run", "burn-in": "fail"})
        result = declare_lot_status(lot(stage_verdicts=records))
        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["admissible"])
        self.assertTrue(any("incomplete chain" in f for f in result["findings"]))

    def test_gap_after_the_failing_stage_does_not_break_admissibility(self):
        records = all_pass(**{"temperature-cycling": "fail", "external-visual": "not-run"})
        result = declare_lot_status(lot(stage_verdicts=records))
        self.assertEqual(result["status"], "rejected")
        self.assertTrue(result["admissible"])

    def test_segregated_traceable_sublot_narrows_the_scope(self):
        spec = lot(
            stage_verdicts=all_pass(**{"final-electrical": "fail"}),
            failures_confined_to_one_sublot=True,
            sublot_physically_segregated=True,
            sublot_traceability_intact=True,
        )
        result = declare_lot_status(spec)
        self.assertEqual(result["scope"], "sublot")
        self.assertTrue(any("segregated sublot" in f for f in result["findings"]))

    def test_rejection_carries_quarantine_and_notification_obligations(self):
        result = declare_lot_status(lot(stage_verdicts=all_pass(**{"seal-fine-leak": "fail"})))
        self.assertIn("quarantine-the-lot", result["obligations"])
        self.assertIn("notify-the-customer", result["obligations"])
        self.assertIn("open-a-failure-analysis", result["obligations"])

    def test_accepted_lot_carries_only_the_release_obligation(self):
        self.assertEqual(
            declare_lot_status(lot())["obligations"],
            ["release-the-lot-with-its-screening-record"],
        )

    def test_status_obligations_refuses_an_unknown_status(self):
        with self.assertRaises(ValueError):
            status_obligations("probably-ok")

    def test_missing_required_key_is_refused(self):
        for key in ("stage_verdicts", "declared_by"):
            spec = lot()
            del spec[key]
            with self.assertRaises(ValueError):
                declare_lot_status(spec)

    def test_blank_declaring_authority_is_refused(self):
        with self.assertRaises(ValueError):
            declare_lot_status(lot(declared_by="   "))


if __name__ == "__main__":
    unittest.main(verbosity=2)
