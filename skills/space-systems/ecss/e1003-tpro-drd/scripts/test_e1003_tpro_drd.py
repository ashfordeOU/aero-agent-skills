#!/usr/bin/env python3
"""Offline deterministic contract tests for e1003_tpro_drd_logic.

Run: python3 test_e1003_tpro_drd.py
Must print OK with no external dependencies.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_tpro_drd_logic import (
    validate_header,
    validate_step,
    validate_procedure,
    validate_data_record,
    validate_pass_fail_criteria,
    validate_tpro,
    is_tpro_compliant,
    VALID_TEST_LEVELS,
)


def _severities(findings):
    return [f["severity"] for f in findings]


def _make_header(**overrides):
    base = {
        "doc_id": "TPRO-001",
        "title": "Thermal Cycling Test Procedure",
        "revision": "A",
        "objective": "Verify the unit survives the required thermal cycles.",
        "test_level": "acceptance",
        "applicable_standard": "ECSS-E-ST-10C",
        "safety_requirements": "No hazardous voltages during chamber access.",
    }
    base.update(overrides)
    return base


def _make_step(step_number, action="Apply power to the unit.",
               expected_result="Output voltage is within specification."):
    return {
        "step_number": step_number,
        "action": action,
        "expected_result": expected_result,
    }


def _make_criterion(**overrides):
    base = {
        "parameter": "output_voltage_V",
        "condition": "within",
        "acceptance_value": "3.3 +/- 0.1",
    }
    base.update(overrides)
    return base


class TestValidateHeader(unittest.TestCase):

    def test_valid_header_returns_no_findings(self):
        findings = validate_header(_make_header())
        self.assertEqual(findings, [])

    def test_missing_doc_id_returns_critical(self):
        hdr = _make_header()
        del hdr["doc_id"]
        findings = validate_header(hdr)
        self.assertIn("CRITICAL", _severities(findings))
        self.assertTrue(any("doc_id" in f["location"] for f in findings))

    def test_empty_title_returns_critical(self):
        findings = validate_header(_make_header(title=""))
        self.assertIn("CRITICAL", _severities(findings))

    def test_whitespace_only_objective_returns_critical(self):
        findings = validate_header(_make_header(objective="   "))
        self.assertIn("CRITICAL", _severities(findings))

    def test_unrecognized_test_level_returns_major(self):
        findings = validate_header(_make_header(test_level="flight_spare"))
        self.assertIn("MAJOR", _severities(findings))

    def test_all_valid_test_levels_accepted(self):
        for level in VALID_TEST_LEVELS:
            findings = validate_header(_make_header(test_level=level))
            level_findings = [f for f in findings if "test_level" in f["location"]]
            self.assertEqual(level_findings, [],
                             msg="Level '%s' should be accepted" % level)

    def test_multiple_missing_fields_all_reported(self):
        findings = validate_header({})
        self.assertGreaterEqual(len(findings), 7)
        self.assertTrue(all(f["severity"] == "CRITICAL" for f in findings))


class TestValidateStep(unittest.TestCase):

    def test_valid_step_returns_no_findings(self):
        findings = validate_step(_make_step(1), step_idx=0)
        self.assertEqual(findings, [])

    def test_missing_action_returns_major(self):
        step = _make_step(1)
        del step["action"]
        findings = validate_step(step, step_idx=0)
        self.assertIn("MAJOR", _severities(findings))

    def test_empty_expected_result_returns_major(self):
        step = _make_step(1, expected_result="")
        findings = validate_step(step, step_idx=0)
        self.assertIn("MAJOR", _severities(findings))

    def test_out_of_sequence_step_number_returns_minor(self):
        step = _make_step(5)
        findings = validate_step(step, step_idx=0)
        self.assertIn("MINOR", _severities(findings))

    def test_valid_step_with_data_records_returns_no_findings(self):
        step = _make_step(1)
        step["data_to_record"] = [
            {"parameter": "temperature_C", "unit": "degC", "acceptance_range": "-20 to +70"},
        ]
        findings = validate_step(step, step_idx=0)
        self.assertEqual(findings, [])

    def test_data_record_missing_unit_returns_major(self):
        step = _make_step(1)
        step["data_to_record"] = [
            {"parameter": "temperature_C", "unit": "", "acceptance_range": "-20 to +70"},
        ]
        findings = validate_step(step, step_idx=0)
        self.assertIn("MAJOR", _severities(findings))


class TestValidateDataRecord(unittest.TestCase):

    def test_complete_record_returns_no_findings(self):
        record = {"parameter": "pressure_Pa", "unit": "Pa", "acceptance_range": "0 to 1e5"}
        findings = validate_data_record(record, step_idx=0, rec_idx=0)
        self.assertEqual(findings, [])

    def test_missing_parameter_returns_major(self):
        record = {"parameter": "", "unit": "Pa", "acceptance_range": "0 to 1e5"}
        findings = validate_data_record(record, step_idx=0, rec_idx=0)
        self.assertIn("MAJOR", _severities(findings))

    def test_missing_acceptance_range_returns_major(self):
        record = {"parameter": "pressure_Pa", "unit": "Pa", "acceptance_range": ""}
        findings = validate_data_record(record, step_idx=0, rec_idx=0)
        self.assertIn("MAJOR", _severities(findings))


class TestValidateProcedure(unittest.TestCase):

    def test_empty_procedure_returns_critical(self):
        findings = validate_procedure([])
        self.assertIn("CRITICAL", _severities(findings))

    def test_single_valid_step_returns_no_findings(self):
        findings = validate_procedure([_make_step(1)])
        self.assertEqual(findings, [])

    def test_multiple_valid_steps_return_no_findings(self):
        steps = [_make_step(i + 1) for i in range(5)]
        findings = validate_procedure(steps)
        self.assertEqual(findings, [])

    def test_second_step_missing_action_returns_major(self):
        step2 = _make_step(2)
        del step2["action"]
        findings = validate_procedure([_make_step(1), step2])
        self.assertIn("MAJOR", _severities(findings))
        self.assertTrue(any("procedure[1]" in f["location"] for f in findings))


class TestValidatePassFailCriteria(unittest.TestCase):

    def test_empty_criteria_returns_critical(self):
        findings = validate_pass_fail_criteria([])
        self.assertIn("CRITICAL", _severities(findings))

    def test_valid_criterion_returns_no_findings(self):
        findings = validate_pass_fail_criteria([_make_criterion()])
        self.assertEqual(findings, [])

    def test_missing_condition_returns_major(self):
        findings = validate_pass_fail_criteria([_make_criterion(condition="")])
        self.assertIn("MAJOR", _severities(findings))

    def test_missing_acceptance_value_returns_major(self):
        findings = validate_pass_fail_criteria([_make_criterion(acceptance_value="")])
        self.assertIn("MAJOR", _severities(findings))


class TestValidateTpro(unittest.TestCase):

    def _valid_tpro(self):
        return {
            "header": _make_header(),
            "procedure": [_make_step(1), _make_step(2)],
            "pass_fail_criteria": [_make_criterion()],
        }

    def test_valid_tpro_returns_no_findings(self):
        findings = validate_tpro(self._valid_tpro())
        self.assertEqual(findings, [])

    def test_tpro_missing_header_field_returns_critical(self):
        doc = self._valid_tpro()
        del doc["header"]["doc_id"]
        findings = validate_tpro(doc)
        self.assertIn("CRITICAL", _severities(findings))

    def test_tpro_empty_procedure_returns_critical(self):
        doc = self._valid_tpro()
        doc["procedure"] = []
        findings = validate_tpro(doc)
        self.assertIn("CRITICAL", _severities(findings))

    def test_tpro_missing_criteria_returns_critical(self):
        doc = self._valid_tpro()
        doc["pass_fail_criteria"] = []
        findings = validate_tpro(doc)
        self.assertIn("CRITICAL", _severities(findings))

    def test_tpro_multiple_errors_all_reported(self):
        doc = {
            "header": {},
            "procedure": [],
            "pass_fail_criteria": [],
        }
        findings = validate_tpro(doc)
        self.assertGreater(len(findings), 3)

    def test_tpro_none_sections_handled_gracefully(self):
        doc = {"header": None, "procedure": None, "pass_fail_criteria": None}
        findings = validate_tpro(doc)
        self.assertTrue(len(findings) > 0)


class TestIsTproCompliant(unittest.TestCase):

    def test_no_findings_is_compliant(self):
        self.assertTrue(is_tpro_compliant([]))

    def test_only_minor_is_compliant(self):
        findings = [{"severity": "MINOR", "location": "x", "issue": "y"}]
        self.assertTrue(is_tpro_compliant(findings))

    def test_major_finding_is_not_compliant(self):
        findings = [{"severity": "MAJOR", "location": "x", "issue": "y"}]
        self.assertFalse(is_tpro_compliant(findings))

    def test_critical_finding_is_not_compliant(self):
        findings = [{"severity": "CRITICAL", "location": "x", "issue": "y"}]
        self.assertFalse(is_tpro_compliant(findings))

    def test_mixed_minor_and_major_is_not_compliant(self):
        findings = [
            {"severity": "MINOR", "location": "a", "issue": "b"},
            {"severity": "MAJOR", "location": "c", "issue": "d"},
        ]
        self.assertFalse(is_tpro_compliant(findings))


if __name__ == "__main__":
    unittest.main()
