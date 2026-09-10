#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.5 model philosophy.

Exercises scripts/e1002_models_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - philosophy selection gives
margin preservation precedence over schedule/cost pressure; the model
list must be non-empty with every entry carrying a recognised,
non-duplicate designation and at least one verification stage;
representativeness requires matching configurations; protoflight
severity must hold full qualification amplitude while allowing
reduced duration; and any design change after a prior test on a
requirement triggers re-verification.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1002_models_logic import (
    check_representativeness,
    needs_reverification,
    protoflight_severity_ok,
    select_philosophy,
    validate_model_list,
)


class TestSelectPhilosophy(unittest.TestCase):
    def test_margin_preservation_forces_prototype_even_under_pressure(self):
        self.assertEqual(
            select_philosophy(
                margin_preservation_required=True,
                schedule_constrained=True,
                cost_constrained=True,
            ),
            "prototype",
        )

    def test_schedule_pressure_alone_selects_protoflight(self):
        self.assertEqual(
            select_philosophy(
                margin_preservation_required=False,
                schedule_constrained=True,
                cost_constrained=False,
            ),
            "protoflight",
        )

    def test_cost_pressure_alone_selects_protoflight(self):
        self.assertEqual(
            select_philosophy(
                margin_preservation_required=False,
                schedule_constrained=False,
                cost_constrained=True,
            ),
            "protoflight",
        )

    def test_no_drivers_defaults_to_prototype(self):
        self.assertEqual(
            select_philosophy(
                margin_preservation_required=False,
                schedule_constrained=False,
                cost_constrained=False,
            ),
            "prototype",
        )


class TestValidateModelList(unittest.TestCase):
    def test_empty_list_is_flagged(self):
        issues = validate_model_list([])
        self.assertTrue(any("empty" in issue for issue in issues))

    def test_complete_list_has_no_issues(self):
        models = [
            {
                "designation": "QM",
                "purpose": "absorb qualification-level environmental tests",
                "configuration": "qual-baseline",
                "stages": ["qualification"],
            },
            {
                "designation": "FM",
                "purpose": "flight article, acceptance-tested only",
                "configuration": "flight-baseline",
                "stages": ["acceptance", "pre-launch"],
            },
        ]
        self.assertEqual(validate_model_list(models), [])

    def test_missing_field_is_flagged(self):
        models = [
            {
                "designation": "PFM",
                "purpose": "combined qual/flight article",
                "configuration": "flight-baseline",
                # 'stages' missing
            }
        ]
        issues = validate_model_list(models)
        self.assertTrue(any("missing required field" in issue for issue in issues))

    def test_unrecognised_designation_is_flagged(self):
        models = [
            {
                "designation": "MOCKUP",
                "purpose": "layout check",
                "configuration": "mockup-baseline",
                "stages": ["design"],
            }
        ]
        issues = validate_model_list(models)
        self.assertTrue(any("unrecognised designation" in issue for issue in issues))

    def test_duplicate_designation_is_flagged(self):
        models = [
            {
                "designation": "FM",
                "purpose": "flight article",
                "configuration": "flight-baseline",
                "stages": ["acceptance"],
            },
            {
                "designation": "FM",
                "purpose": "second flight article",
                "configuration": "flight-baseline",
                "stages": ["acceptance"],
            },
        ]
        issues = validate_model_list(models)
        self.assertTrue(any("duplicate designation" in issue for issue in issues))

    def test_empty_stages_is_flagged(self):
        models = [
            {
                "designation": "EM",
                "purpose": "functional breadboard",
                "configuration": "eng-baseline",
                "stages": [],
            }
        ]
        issues = validate_model_list(models)
        self.assertTrue(any("at least one verification stage" in issue for issue in issues))


class TestCheckRepresentativeness(unittest.TestCase):
    def test_matching_configuration_is_representative(self):
        self.assertTrue(check_representativeness("flight-baseline", "flight-baseline"))

    def test_mismatched_configuration_is_not_representative(self):
        self.assertFalse(check_representativeness("qual-baseline", "flight-baseline"))


class TestProtoflightSeverityOk(unittest.TestCase):
    def test_full_amplitude_reduced_duration_is_ok(self):
        ok, reasons = protoflight_severity_ok(
            applied_amplitude=1.25,
            qualification_amplitude=1.25,
            applied_duration=30,
            qualification_duration=60,
        )
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_reduced_amplitude_is_rejected(self):
        ok, reasons = protoflight_severity_ok(
            applied_amplitude=1.0,
            qualification_amplitude=1.25,
            applied_duration=30,
            qualification_duration=60,
        )
        self.assertFalse(ok)
        self.assertTrue(any("amplitude" in reason for reason in reasons))

    def test_excess_duration_is_rejected(self):
        ok, reasons = protoflight_severity_ok(
            applied_amplitude=1.25,
            qualification_amplitude=1.25,
            applied_duration=90,
            qualification_duration=60,
        )
        self.assertFalse(ok)
        self.assertTrue(any("duration" in reason for reason in reasons))


class TestNeedsReverification(unittest.TestCase):
    def test_change_after_prior_test_triggers_reverification(self):
        self.assertTrue(needs_reverification(tested_before_change=True, design_changed_after_test=True))

    def test_no_prior_test_does_not_trigger(self):
        self.assertFalse(needs_reverification(tested_before_change=False, design_changed_after_test=True))

    def test_no_change_does_not_trigger(self):
        self.assertFalse(needs_reverification(tested_before_change=True, design_changed_after_test=False))


if __name__ == "__main__":
    unittest.main()
