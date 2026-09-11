"""
Stdlib unittest for e1003_test_programme_logic.py.
Offline, deterministic. Run: python3 test_e1003_test_programme.py
Must print OK.
"""

import unittest

from e1003_test_programme_logic import (
    ModelUnderTest,
    TestItem,
    ProgrammeDocumentSet,
    VerificationInputSet,
    categorize_model,
    validate_test_sequence,
    check_functional_bookend,
    check_programme_documentation,
    check_verification_inputs,
    build_programme_summary,
    REQUIRED_PROGRAMME_DOCUMENTS,
)


def _fm_sequence(model_id: str = "FM-01") -> list:
    """Return a valid 4-item acceptance test sequence."""
    return [
        TestItem("T01", "functional",       model_id, 1),
        TestItem("T02", "vibration-random", model_id, 2),
        TestItem("T03", "thermal-vacuum",   model_id, 3),
        TestItem("T04", "functional",       model_id, 4),
    ]


def _all_docs_present() -> ProgrammeDocumentSet:
    return ProgrammeDocumentSet({d: True for d in REQUIRED_PROGRAMME_DOCUMENTS})


# ---------------------------------------------------------------------------
# Model categorization
# ---------------------------------------------------------------------------

class TestCategorizeModel(unittest.TestCase):

    def test_em_yields_development_level(self):
        level, errors = categorize_model(ModelUnderTest("EM-01", "EM", "Structure"))
        self.assertEqual(errors, [])
        self.assertEqual(level, "development")

    def test_bb_yields_development_level(self):
        level, errors = categorize_model(ModelUnderTest("BB-01", "BB", "AOCS"))
        self.assertEqual(errors, [])
        self.assertEqual(level, "development")

    def test_qm_yields_qualification_level(self):
        level, errors = categorize_model(ModelUnderTest("QM-01", "QM", "Thermal"))
        self.assertEqual(errors, [])
        self.assertEqual(level, "qualification")

    def test_eqm_yields_qualification_level(self):
        level, errors = categorize_model(ModelUnderTest("EQM-01", "EQM", "Power"))
        self.assertEqual(errors, [])
        self.assertEqual(level, "qualification")

    def test_pfm_yields_proto_flight_level(self):
        level, errors = categorize_model(ModelUnderTest("PFM-01", "PFM", "Propulsion"))
        self.assertEqual(errors, [])
        self.assertEqual(level, "proto-flight")

    def test_fm_yields_acceptance_level(self):
        level, errors = categorize_model(ModelUnderTest("FM-01", "FM", "Structure"))
        self.assertEqual(errors, [])
        self.assertEqual(level, "acceptance")

    def test_invalid_type_returns_empty_level_and_error(self):
        level, errors = categorize_model(ModelUnderTest("XX-01", "XX", "Unknown"))
        self.assertEqual(level, "")
        self.assertGreater(len(errors), 0)
        self.assertIn("XX", errors[0])


# ---------------------------------------------------------------------------
# Test sequence validation
# ---------------------------------------------------------------------------

class TestValidateTestSequence(unittest.TestCase):

    def test_valid_fm_sequence_passes(self):
        model = ModelUnderTest("FM-01", "FM", "Structure")
        valid, findings = validate_test_sequence(model, _fm_sequence("FM-01"))
        self.assertTrue(valid)
        self.assertEqual(findings, [])

    def test_empty_sequence_is_rejected(self):
        model = ModelUnderTest("FM-01", "FM", "Structure")
        valid, findings = validate_test_sequence(model, [])
        self.assertFalse(valid)
        self.assertGreater(len(findings), 0)

    def test_duplicate_positions_are_detected(self):
        model = ModelUnderTest("FM-01", "FM", "Structure")
        seq = [
            TestItem("T01", "functional",       "FM-01", 1),
            TestItem("T02", "vibration-random", "FM-01", 1),
        ]
        valid, findings = validate_test_sequence(model, seq)
        self.assertFalse(valid)
        self.assertTrue(any("uplicate" in f for f in findings))

    def test_nonconsecutive_positions_are_detected(self):
        model = ModelUnderTest("FM-01", "FM", "Structure")
        seq = [
            TestItem("T01", "functional",       "FM-01", 1),
            TestItem("T02", "vibration-random", "FM-01", 3),
            TestItem("T03", "functional",       "FM-01", 4),
        ]
        valid, findings = validate_test_sequence(model, seq)
        self.assertFalse(valid)
        self.assertGreater(len(findings), 0)

    def test_wrong_model_id_in_sequence_is_detected(self):
        model = ModelUnderTest("FM-01", "FM", "Structure")
        seq = [
            TestItem("T01", "functional", "FM-99", 1),
            TestItem("T02", "functional", "FM-99", 2),
        ]
        valid, findings = validate_test_sequence(model, seq)
        self.assertFalse(valid)
        self.assertTrue(any("FM-99" in f for f in findings))

    def test_unknown_test_type_is_rejected(self):
        model = ModelUnderTest("FM-01", "FM", "Structure")
        seq = [
            TestItem("T01", "functional",    "FM-01", 1),
            TestItem("T02", "unknown-test",  "FM-01", 2),
            TestItem("T03", "functional",    "FM-01", 3),
        ]
        valid, findings = validate_test_sequence(model, seq)
        self.assertFalse(valid)
        self.assertTrue(any("unknown-test" in f for f in findings))


# ---------------------------------------------------------------------------
# Functional bookend check
# ---------------------------------------------------------------------------

class TestCheckFunctionalBookend(unittest.TestCase):

    def test_valid_bookend_passes(self):
        ok, findings = check_functional_bookend(_fm_sequence("FM-01"))
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_missing_leading_functional_is_detected(self):
        seq = [
            TestItem("T01", "vibration-random", "FM-01", 1),
            TestItem("T02", "thermal-vacuum",   "FM-01", 2),
            TestItem("T03", "functional",       "FM-01", 3),
        ]
        ok, findings = check_functional_bookend(seq)
        self.assertFalse(ok)
        self.assertTrue(any("First" in f for f in findings))

    def test_missing_trailing_functional_is_detected(self):
        seq = [
            TestItem("T01", "functional",       "FM-01", 1),
            TestItem("T02", "vibration-random", "FM-01", 2),
            TestItem("T03", "thermal-vacuum",   "FM-01", 3),
        ]
        ok, findings = check_functional_bookend(seq)
        self.assertFalse(ok)
        self.assertTrue(any("Last" in f for f in findings))

    def test_single_functional_item_satisfies_bookend(self):
        seq = [TestItem("T01", "functional", "FM-01", 1)]
        ok, findings = check_functional_bookend(seq)
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_empty_sequence_fails_bookend(self):
        ok, findings = check_functional_bookend([])
        self.assertFalse(ok)
        self.assertGreater(len(findings), 0)


# ---------------------------------------------------------------------------
# Programme documentation check
# ---------------------------------------------------------------------------

class TestCheckProgrammeDocumentation(unittest.TestCase):

    def test_all_documents_present_passes(self):
        ok, missing = check_programme_documentation(_all_docs_present())
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_missing_documents_are_reported(self):
        docs = ProgrammeDocumentSet({
            "test-plan":                    True,
            "test-procedures":              False,
            "verification-control-document": True,
            "test-reports":                 False,
        })
        ok, missing = check_programme_documentation(docs)
        self.assertFalse(ok)
        self.assertIn("test-procedures", missing)
        self.assertIn("test-reports", missing)

    def test_empty_document_set_reports_all_missing(self):
        ok, missing = check_programme_documentation(ProgrammeDocumentSet({}))
        self.assertFalse(ok)
        self.assertEqual(set(missing), REQUIRED_PROGRAMME_DOCUMENTS)


# ---------------------------------------------------------------------------
# Verification input check
# ---------------------------------------------------------------------------

class TestCheckVerificationInputs(unittest.TestCase):

    def test_complete_inputs_for_thermal_vacuum_passes(self):
        vis = VerificationInputSet(
            "thermal-vacuum",
            ["thermal-model", "thermal-environment", "qualification-levels"],
        )
        ok, missing = check_verification_inputs(vis)
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_partial_inputs_for_thermal_vacuum_are_reported(self):
        vis = VerificationInputSet(
            "thermal-vacuum",
            ["thermal-model"],
        )
        ok, missing = check_verification_inputs(vis)
        self.assertFalse(ok)
        self.assertIn("thermal-environment", missing)
        self.assertIn("qualification-levels", missing)

    def test_complete_inputs_for_vibration_random_passes(self):
        vis = VerificationInputSet(
            "vibration-random",
            ["loads-environment", "qualification-levels"],
        )
        ok, missing = check_verification_inputs(vis)
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_unknown_test_type_returns_error(self):
        vis = VerificationInputSet("nonexistent-test", ["some-input"])
        ok, missing = check_verification_inputs(vis)
        self.assertFalse(ok)
        self.assertTrue(any("nonexistent-test" in m for m in missing))

    def test_complete_inputs_for_functional_passes(self):
        vis = VerificationInputSet(
            "functional",
            ["functional-baseline", "requirement-list"],
        )
        ok, missing = check_verification_inputs(vis)
        self.assertTrue(ok)
        self.assertEqual(missing, [])


# ---------------------------------------------------------------------------
# Programme summary
# ---------------------------------------------------------------------------

class TestBuildProgrammeSummary(unittest.TestCase):

    def test_valid_programme_has_no_findings(self):
        models = [ModelUnderTest("FM-01", "FM", "Structure")]
        sequences = {"FM-01": _fm_sequence("FM-01")}
        summary = build_programme_summary(models, sequences, _all_docs_present())
        self.assertTrue(summary["programme_valid"])
        self.assertEqual(summary["findings"], [])
        self.assertIn("FM-01", summary["models"])
        self.assertEqual(summary["models"]["FM-01"]["test_level"], "acceptance")

    def test_invalid_model_type_produces_finding(self):
        models = [ModelUnderTest("XX-01", "XX", "Unknown")]
        summary = build_programme_summary(models, {}, _all_docs_present())
        self.assertFalse(summary["programme_valid"])
        self.assertGreater(len(summary["findings"]), 0)

    def test_missing_programme_documents_produce_findings(self):
        models = [ModelUnderTest("FM-01", "FM", "Structure")]
        sequences = {"FM-01": _fm_sequence("FM-01")}
        docs = ProgrammeDocumentSet({"test-plan": True})
        summary = build_programme_summary(models, sequences, docs)
        self.assertFalse(summary["programme_valid"])
        self.assertGreater(len(summary["findings"]), 0)
        self.assertFalse(summary["doc_status"]["complete"])

    def test_empty_sequence_produces_finding(self):
        models = [ModelUnderTest("FM-01", "FM", "Structure")]
        sequences = {"FM-01": []}
        summary = build_programme_summary(models, sequences, _all_docs_present())
        self.assertFalse(summary["programme_valid"])
        self.assertGreater(len(summary["findings"]), 0)

    def test_model_absent_from_sequences_produces_finding(self):
        models = [ModelUnderTest("FM-01", "FM", "Structure")]
        summary = build_programme_summary(models, {}, _all_docs_present())
        self.assertFalse(summary["programme_valid"])

    def test_multiple_models_both_valid(self):
        models = [
            ModelUnderTest("QM-01", "QM", "Structure"),
            ModelUnderTest("FM-01", "FM", "Thermal"),
        ]
        qm_seq = [
            TestItem("Q01", "functional",       "QM-01", 1),
            TestItem("Q02", "vibration-sine",   "QM-01", 2),
            TestItem("Q03", "thermal-vacuum",   "QM-01", 3),
            TestItem("Q04", "functional",       "QM-01", 4),
        ]
        sequences = {"QM-01": qm_seq, "FM-01": _fm_sequence("FM-01")}
        summary = build_programme_summary(models, sequences, _all_docs_present())
        self.assertTrue(summary["programme_valid"])
        self.assertEqual(summary["models"]["QM-01"]["test_level"], "qualification")
        self.assertEqual(summary["models"]["FM-01"]["test_level"], "acceptance")


if __name__ == "__main__":
    unittest.main()
