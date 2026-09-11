#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.9.1 operational procedure
development, format validation, and HFE review.

Exercises scripts/e1011_procedures_logic.py (stdlib unittest, offline).
Contract: a procedure must carry all required fields (procedure_id,
title, purpose, procedure_type, preconditions, steps, expected_outcome)
and each field must be non-empty; the procedure_type must be one of the
accepted operational categories and an unrecognized type raises; each
step must carry a step_id and an action that begins with a recognized
imperative verb and does not exceed HFE_MAX_STEP_WORDS words; an action
containing two imperative verbs joined by 'and' is flagged as a warning
for splitting; more than HFE_MAX_STEPS_WITHOUT_CHECKPOINT consecutive
non-checkpoint steps is an error; duplicate step IDs within a procedure
are an error; and the procedure is approved only when no error-severity
findings remain across all categories.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_procedures_logic as pl  # noqa: E402


def _make_step(step_id, action, is_checkpoint=False):
    return {"step_id": step_id, "action": action, "is_checkpoint": is_checkpoint}


def _make_valid_procedure(steps=None):
    if steps is None:
        steps = [_make_step("1", "Connect the primary power harness to J1.")]
    return {
        "procedure_id": "PROC-001",
        "title": "Primary Power Activation",
        "purpose": "Activate primary power to the spacecraft bus.",
        "procedure_type": "nominal",
        "preconditions": ["GSE power supply set to 28 V", "All personnel clear of HV areas"],
        "steps": steps,
        "expected_outcome": "Bus voltage stable at 28 ± 0.5 V within 30 s.",
    }


class ValidateProcedureFieldsTest(unittest.TestCase):
    def test_complete_procedure_no_field_findings(self):
        result = pl.validate_procedure_fields(_make_valid_procedure())
        self.assertEqual(result, [])

    def test_missing_title_flagged_as_error(self):
        proc = _make_valid_procedure()
        del proc["title"]
        findings = pl.validate_procedure_fields(proc)
        issues = [f["issue"] for f in findings]
        self.assertIn("missing_field", issues)
        fields = [f["field"] for f in findings]
        self.assertIn("title", fields)

    def test_missing_steps_flagged_as_error(self):
        proc = _make_valid_procedure()
        del proc["steps"]
        findings = pl.validate_procedure_fields(proc)
        fields = [f["field"] for f in findings]
        self.assertIn("steps", fields)

    def test_empty_preconditions_flagged_as_error(self):
        proc = _make_valid_procedure()
        proc["preconditions"] = []
        findings = pl.validate_procedure_fields(proc)
        issues = [f["issue"] for f in findings]
        self.assertIn("empty_field", issues)
        fields = [f["field"] for f in findings]
        self.assertIn("preconditions", fields)

    def test_none_expected_outcome_flagged(self):
        proc = _make_valid_procedure()
        proc["expected_outcome"] = None
        findings = pl.validate_procedure_fields(proc)
        fields = [f["field"] for f in findings]
        self.assertIn("expected_outcome", fields)

    def test_all_findings_have_error_severity(self):
        proc = _make_valid_procedure()
        del proc["title"]
        del proc["purpose"]
        findings = pl.validate_procedure_fields(proc)
        for f in findings:
            self.assertEqual(f["severity"], pl.SEVERITY_ERROR)


class ValidateStepTest(unittest.TestCase):
    def test_valid_step_no_findings(self):
        step = _make_step("1", "Connect J1 to the GSE power port.")
        findings = pl.validate_step(step, 0)
        self.assertEqual(findings, [])

    def test_step_missing_action_field_error(self):
        step = {"step_id": "1"}
        findings = pl.validate_step(step, 0)
        issues = [f["issue"] for f in findings]
        self.assertIn("missing_field", issues)

    def test_step_missing_step_id_error(self):
        step = {"action": "Connect the harness."}
        findings = pl.validate_step(step, 0)
        issues = [f["issue"] for f in findings]
        self.assertIn("missing_field", issues)

    def test_step_not_imperative_verb_warning(self):
        step = _make_step("1", "The operator should connect J1.")
        findings = pl.validate_step(step, 0)
        issues = [f["issue"] for f in findings]
        self.assertIn("step_action_not_imperative_verb", issues)
        severities = [f["severity"] for f in findings]
        self.assertIn(pl.SEVERITY_WARNING, severities)

    def test_step_too_many_words_error(self):
        long_action = "Connect " + " ".join(["the"] * 30) + " harness."
        step = _make_step("1", long_action)
        findings = pl.validate_step(step, 0)
        issues = [f["issue"] for f in findings]
        self.assertIn("step_action_exceeds_word_limit", issues)
        error_findings = [f for f in findings if f["issue"] == "step_action_exceeds_word_limit"]
        self.assertEqual(error_findings[0]["severity"], pl.SEVERITY_ERROR)

    def test_step_at_word_limit_no_error(self):
        action = " ".join(["set"] + ["x"] * (pl.HFE_MAX_STEP_WORDS - 1))
        step = _make_step("1", action)
        findings = pl.validate_step(step, 0)
        limit_issues = [f for f in findings if f["issue"] == "step_action_exceeds_word_limit"]
        self.assertEqual(limit_issues, [])

    def test_compound_action_both_verbs_warning(self):
        step = _make_step("1", "Connect J1 to P2 and verify indicator lamp is green.")
        findings = pl.validate_step(step, 0)
        issues = [f["issue"] for f in findings]
        self.assertIn("compound_action_should_split", issues)
        compound_findings = [f for f in findings if f["issue"] == "compound_action_should_split"]
        self.assertEqual(compound_findings[0]["severity"], pl.SEVERITY_WARNING)

    def test_compound_action_second_not_verb_no_warning(self):
        step = _make_step("1", "Connect J1 and the adjacent bracket securely.")
        findings = pl.validate_step(step, 0)
        issues = [f["issue"] for f in findings]
        self.assertNotIn("compound_action_should_split", issues)

    def test_step_not_dict_raises(self):
        with self.assertRaises(ValueError):
            pl.validate_step("not a dict", 0)


class CheckCheckpointSpacingTest(unittest.TestCase):
    def test_spacing_within_limit_no_finding(self):
        steps = [_make_step(str(i), "Connect item %d." % i)
                 for i in range(pl.HFE_MAX_STEPS_WITHOUT_CHECKPOINT)]
        findings = pl.check_checkpoint_spacing(steps)
        self.assertEqual(findings, [])

    def test_spacing_exactly_at_limit_no_finding(self):
        steps = [_make_step(str(i), "Set item %d." % i)
                 for i in range(pl.HFE_MAX_STEPS_WITHOUT_CHECKPOINT)]
        findings = pl.check_checkpoint_spacing(steps)
        self.assertEqual(findings, [])

    def test_spacing_exceeds_limit_one_error(self):
        steps = [_make_step(str(i), "Set item %d." % i)
                 for i in range(pl.HFE_MAX_STEPS_WITHOUT_CHECKPOINT + 1)]
        findings = pl.check_checkpoint_spacing(steps)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "checkpoint_spacing_exceeded")
        self.assertEqual(findings[0]["severity"], pl.SEVERITY_ERROR)

    def test_checkpoint_resets_counter(self):
        steps = (
            [_make_step(str(i), "Set item %d." % i)
             for i in range(pl.HFE_MAX_STEPS_WITHOUT_CHECKPOINT)]
            + [_make_step("cp", "Verify state.", is_checkpoint=True)]
            + [_make_step(str(i + 100), "Set item %d." % i)
               for i in range(pl.HFE_MAX_STEPS_WITHOUT_CHECKPOINT)]
        )
        findings = pl.check_checkpoint_spacing(steps)
        self.assertEqual(findings, [])


class CheckStepIdUniquenessTest(unittest.TestCase):
    def test_unique_step_ids_no_finding(self):
        steps = [_make_step("1", "Connect J1."),
                 _make_step("2", "Set switch S1.")]
        findings = pl.check_step_id_uniqueness(steps)
        self.assertEqual(findings, [])

    def test_duplicate_step_id_flagged_as_error(self):
        steps = [_make_step("1", "Connect J1."),
                 _make_step("1", "Set switch S1.")]
        findings = pl.check_step_id_uniqueness(steps)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "duplicate_step_id")
        self.assertEqual(findings[0]["severity"], pl.SEVERITY_ERROR)
        self.assertEqual(findings[0]["step_id"], "1")


class ValidateProcedureTest(unittest.TestCase):
    def test_valid_procedure_no_findings(self):
        result = pl.validate_procedure(_make_valid_procedure())
        self.assertEqual(result["field_findings"], [])
        self.assertEqual(result["step_findings"], [])
        self.assertEqual(result["hfe_findings"], [])

    def test_valid_procedure_is_approved(self):
        result = pl.validate_procedure(_make_valid_procedure())
        self.assertTrue(pl.is_procedure_approved(result))

    def test_unknown_procedure_type_raises(self):
        proc = _make_valid_procedure()
        proc["procedure_type"] = "orbital_dance"
        with self.assertRaises(ValueError):
            pl.validate_procedure(proc)

    def test_known_procedure_types_accepted(self):
        for pt in pl.PROCEDURE_TYPES:
            proc = _make_valid_procedure()
            proc["procedure_type"] = pt
            result = pl.validate_procedure(proc)
            type_errors = [
                f for f in result["field_findings"]
                if f.get("field") == "procedure_type"
            ]
            self.assertEqual(type_errors, [], msg="procedure_type=%r raised" % pt)

    def test_missing_field_makes_procedure_not_approved(self):
        proc = _make_valid_procedure()
        del proc["title"]
        result = pl.validate_procedure(proc)
        self.assertFalse(pl.is_procedure_approved(result))

    def test_step_error_makes_procedure_not_approved(self):
        long_action = "Connect " + " ".join(["the"] * 30) + " harness."
        steps = [_make_step("1", long_action)]
        result = pl.validate_procedure(_make_valid_procedure(steps=steps))
        self.assertFalse(pl.is_procedure_approved(result))

    def test_warnings_only_procedure_is_approved(self):
        step = _make_step("1", "The operator should connect J1.")
        result = pl.validate_procedure(_make_valid_procedure(steps=[step]))
        error_findings = [
            f for cat in result.values()
            for f in cat
            if f["severity"] == pl.SEVERITY_ERROR
        ]
        self.assertEqual(error_findings, [])
        self.assertTrue(pl.is_procedure_approved(result))

    def test_checkpoint_spacing_error_in_hfe_findings(self):
        steps = [
            _make_step(str(i), "Set item %d." % i)
            for i in range(pl.HFE_MAX_STEPS_WITHOUT_CHECKPOINT + 1)
        ]
        result = pl.validate_procedure(_make_valid_procedure(steps=steps))
        spacing_errors = [
            f for f in result["hfe_findings"]
            if f["issue"] == "checkpoint_spacing_exceeded"
        ]
        self.assertTrue(len(spacing_errors) >= 1)
        self.assertFalse(pl.is_procedure_approved(result))

    def test_duplicate_step_id_error_in_hfe_findings(self):
        steps = [_make_step("1", "Connect J1."), _make_step("1", "Set S1.")]
        result = pl.validate_procedure(_make_valid_procedure(steps=steps))
        dup_errors = [
            f for f in result["hfe_findings"]
            if f["issue"] == "duplicate_step_id"
        ]
        self.assertEqual(len(dup_errors), 1)
        self.assertFalse(pl.is_procedure_approved(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
