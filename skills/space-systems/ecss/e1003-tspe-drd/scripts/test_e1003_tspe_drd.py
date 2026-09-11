import unittest
from e1003_tspe_drd_logic import (
    validate_test_identification,
    validate_description,
    validate_conditions,
    validate_procedure,
    validate_success_criteria,
    validate_tspe_document,
    generate_drd_compliance_report,
    VALID_TEST_TYPES,
)


def _minimal_valid_doc():
    return {
        "test_id": "TST-001",
        "test_name": "Power Subsystem Functional Test",
        "test_type": "functional",
        "description": (
            "Verify that the power subsystem delivers regulated voltage "
            "within the specified tolerance under nominal load conditions "
            "with the battery at eighty percent state of charge."
        ),
        "conditions": {
            "environment": "Thermal-vacuum chamber at 20 degC, 1e-5 mbar",
            "configuration": "Flight hardware fully integrated; EGSE connected; battery 80% SoC",
            "stimuli": "Nominal power-on command sequence sent via EGSE software",
        },
        "procedure": [
            {"step_number": 1, "action": "Power on EGSE and verify telemetry link."},
            {"step_number": 2, "action": "Send power-on command to the unit under test."},
            {"step_number": 3, "action": "Record bus voltage 30 s after power-on command."},
        ],
        "success_criteria": [
            {"parameter": "bus_voltage", "limit": 28.0, "unit": "V"},
            {"parameter": "bus_voltage_tolerance", "limit": 0.5, "unit": "V"},
        ],
    }


class TestValidateTestIdentification(unittest.TestCase):

    def test_valid_identification_produces_no_findings(self):
        findings = validate_test_identification(_minimal_valid_doc())
        self.assertEqual(findings, [])

    def test_missing_test_id_produces_error(self):
        doc = _minimal_valid_doc()
        del doc["test_id"]
        findings = validate_test_identification(doc)
        self.assertTrue(any(f.severity == "error" for f in findings))

    def test_missing_test_name_produces_error(self):
        doc = _minimal_valid_doc()
        doc["test_name"] = ""
        findings = validate_test_identification(doc)
        self.assertTrue(any(f.severity == "error" for f in findings))

    def test_unrecognized_test_type_produces_error(self):
        doc = _minimal_valid_doc()
        doc["test_type"] = "hypothetical"
        findings = validate_test_identification(doc)
        errors = [f for f in findings if f.severity == "error"]
        self.assertTrue(len(errors) > 0)

    def test_all_valid_test_types_are_accepted(self):
        for t in VALID_TEST_TYPES:
            doc = _minimal_valid_doc()
            doc["test_type"] = t
            errors = [f for f in validate_test_identification(doc) if f.severity == "error"]
            self.assertEqual(errors, [], msg=f"type '{t}' should be accepted")


class TestValidateDescription(unittest.TestCase):

    def test_substantive_description_produces_no_findings(self):
        findings = validate_description(_minimal_valid_doc())
        self.assertEqual(findings, [])

    def test_empty_description_produces_error(self):
        doc = _minimal_valid_doc()
        doc["description"] = ""
        findings = validate_description(doc)
        self.assertTrue(any(f.severity == "error" for f in findings))

    def test_very_short_description_produces_warning(self):
        doc = _minimal_valid_doc()
        doc["description"] = "Too brief."
        findings = validate_description(doc)
        self.assertTrue(any(f.severity == "warning" for f in findings))

    def test_ten_word_description_is_not_a_warning(self):
        doc = _minimal_valid_doc()
        doc["description"] = "Verify the unit operates correctly under all nominal conditions now."
        findings = validate_description(doc)
        warnings = [f for f in findings if f.severity == "warning"]
        self.assertEqual(warnings, [])


class TestValidateConditions(unittest.TestCase):

    def test_complete_conditions_block_produces_no_findings(self):
        doc = _minimal_valid_doc()
        findings = validate_conditions(doc["conditions"])
        self.assertEqual(findings, [])

    def test_missing_environment_produces_error(self):
        findings = validate_conditions({"configuration": "FM", "stimuli": "cmd"})
        messages = " ".join(f.message for f in findings)
        self.assertIn("environment", messages)

    def test_missing_stimuli_produces_error(self):
        findings = validate_conditions({"environment": "vac", "configuration": "FM"})
        messages = " ".join(f.message for f in findings)
        self.assertIn("stimuli", messages)

    def test_missing_configuration_produces_error(self):
        findings = validate_conditions({"environment": "vac", "stimuli": "cmd"})
        messages = " ".join(f.message for f in findings)
        self.assertIn("configuration", messages)

    def test_non_dict_conditions_produces_error(self):
        findings = validate_conditions("not a mapping")
        self.assertTrue(any(f.severity == "error" for f in findings))


class TestValidateProcedure(unittest.TestCase):

    def test_valid_procedure_produces_no_findings(self):
        doc = _minimal_valid_doc()
        findings = validate_procedure(doc["procedure"])
        self.assertEqual(findings, [])

    def test_empty_procedure_list_produces_error(self):
        findings = validate_procedure([])
        self.assertTrue(any(f.severity == "error" for f in findings))

    def test_step_missing_action_produces_error(self):
        steps = [{"step_number": 1}]
        findings = validate_procedure(steps)
        messages = " ".join(f.message for f in findings)
        self.assertIn("action", messages)

    def test_step_missing_step_number_produces_error(self):
        steps = [{"action": "Perform calibration sequence."}]
        findings = validate_procedure(steps)
        messages = " ".join(f.message for f in findings)
        self.assertIn("step_number", messages)

    def test_non_list_procedure_produces_error(self):
        findings = validate_procedure("step one; step two")
        self.assertTrue(any(f.severity == "error" for f in findings))


class TestValidateSuccessCriteria(unittest.TestCase):

    def test_valid_criteria_produce_no_findings(self):
        doc = _minimal_valid_doc()
        findings = validate_success_criteria(doc["success_criteria"])
        self.assertEqual(findings, [])

    def test_empty_criteria_list_produces_error(self):
        findings = validate_success_criteria([])
        self.assertTrue(any(f.severity == "error" for f in findings))

    def test_criterion_missing_unit_produces_error(self):
        criteria = [{"parameter": "voltage", "limit": 28.0}]
        findings = validate_success_criteria(criteria)
        messages = " ".join(f.message for f in findings)
        self.assertIn("unit", messages)

    def test_criterion_missing_limit_produces_error(self):
        criteria = [{"parameter": "voltage", "unit": "V"}]
        findings = validate_success_criteria(criteria)
        messages = " ".join(f.message for f in findings)
        self.assertIn("limit", messages)

    def test_criterion_missing_parameter_produces_error(self):
        criteria = [{"limit": 28.0, "unit": "V"}]
        findings = validate_success_criteria(criteria)
        messages = " ".join(f.message for f in findings)
        self.assertIn("parameter", messages)


class TestValidateTspeDocument(unittest.TestCase):

    def test_fully_valid_document_is_compliant(self):
        result = validate_tspe_document(_minimal_valid_doc())
        self.assertTrue(result.compliant)
        errors = [f for f in result.findings if f.severity == "error"]
        self.assertEqual(errors, [])

    def test_missing_top_level_key_fails_compliance(self):
        doc = _minimal_valid_doc()
        del doc["success_criteria"]
        result = validate_tspe_document(doc)
        self.assertFalse(result.compliant)

    def test_test_id_propagated_into_result(self):
        result = validate_tspe_document(_minimal_valid_doc())
        self.assertEqual(result.test_id, "TST-001")

    def test_unknown_sentinel_when_test_id_absent(self):
        doc = _minimal_valid_doc()
        del doc["test_id"]
        result = validate_tspe_document(doc)
        self.assertEqual(result.test_id, "<unknown>")

    def test_invalid_test_type_fails_compliance(self):
        doc = _minimal_valid_doc()
        doc["test_type"] = "informal"
        result = validate_tspe_document(doc)
        self.assertFalse(result.compliant)


class TestGenerateDrdComplianceReport(unittest.TestCase):

    def test_report_contains_all_required_keys(self):
        report = generate_drd_compliance_report(_minimal_valid_doc())
        for key in ("test_id", "drd_standard", "compliant", "error_count",
                    "warning_count", "errors", "warnings"):
            self.assertIn(key, report)

    def test_compliant_doc_yields_zero_errors(self):
        report = generate_drd_compliance_report(_minimal_valid_doc())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["error_count"], 0)

    def test_standard_citation_references_annex_b(self):
        report = generate_drd_compliance_report(_minimal_valid_doc())
        self.assertIn("ECSS-E-ST-10C", report["drd_standard"])
        self.assertIn("Annex B", report["drd_standard"])

    def test_skeletal_doc_yields_nonzero_error_count(self):
        report = generate_drd_compliance_report({"test_id": "TST-BAD"})
        self.assertFalse(report["compliant"])
        self.assertGreater(report["error_count"], 0)

    def test_error_entries_carry_section_and_message(self):
        report = generate_drd_compliance_report({"test_id": "TST-X"})
        self.assertTrue(len(report["errors"]) > 0)
        for entry in report["errors"]:
            self.assertIn("section", entry)
            self.assertIn("message", entry)


if __name__ == "__main__":
    unittest.main()
