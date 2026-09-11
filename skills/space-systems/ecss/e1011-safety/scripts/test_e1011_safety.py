import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_safety_logic import (
    CriticalityLevel,
    OperationRecord,
    SafetyFinding,
    REQUIRED_MEASURES,
    parse_criticality,
    check_required_measures,
    check_interface_requirements,
    check_irreversibility_protection,
    assess_operation,
    assess_catalogue,
    is_compliant,
)

_ALL_CRITICAL_MEASURES = [
    "confirmation_step",
    "interlock",
    "reversibility_check",
    "crew_notification",
    "dual_verification",
]

_ALL_HIGH_MEASURES = [
    "confirmation_step",
    "interlock",
    "reversibility_check",
    "crew_notification",
]


def _make_critical(name="op_crit", reversible=False, measures=None,
                   state_cues=True, go_nogo=True):
    return OperationRecord(
        name=name,
        criticality="CRITICAL",
        reversible=reversible,
        measures=list(_ALL_CRITICAL_MEASURES) if measures is None else measures,
        has_state_cues=state_cues,
        has_go_nogo_criteria=go_nogo,
    )


def _make_high(name="op_high", reversible=True, measures=None,
               state_cues=True, go_nogo=True):
    return OperationRecord(
        name=name,
        criticality="HIGH",
        reversible=reversible,
        measures=list(_ALL_HIGH_MEASURES) if measures is None else measures,
        has_state_cues=state_cues,
        has_go_nogo_criteria=go_nogo,
    )


class TestParseCriticality(unittest.TestCase):

    def test_parse_critical(self):
        self.assertEqual(parse_criticality("CRITICAL"), CriticalityLevel.CRITICAL)

    def test_parse_high(self):
        self.assertEqual(parse_criticality("HIGH"), CriticalityLevel.HIGH)

    def test_parse_medium(self):
        self.assertEqual(parse_criticality("MEDIUM"), CriticalityLevel.MEDIUM)

    def test_parse_low(self):
        self.assertEqual(parse_criticality("LOW"), CriticalityLevel.LOW)

    def test_parse_lowercase_accepted(self):
        self.assertEqual(parse_criticality("critical"), CriticalityLevel.CRITICAL)
        self.assertEqual(parse_criticality("high"), CriticalityLevel.HIGH)

    def test_parse_mixed_case_accepted(self):
        self.assertEqual(parse_criticality("Medium"), CriticalityLevel.MEDIUM)

    def test_parse_invalid_label_raises(self):
        with self.assertRaises(ValueError):
            parse_criticality("EXTREME")

    def test_parse_empty_string_raises(self):
        with self.assertRaises(ValueError):
            parse_criticality("")


class TestRequiredMeasuresCheck(unittest.TestCase):

    def test_critical_op_full_set_no_findings(self):
        op = _make_critical()
        self.assertEqual(check_required_measures(op), [])

    def test_critical_op_missing_dual_verification(self):
        measures = [m for m in _ALL_CRITICAL_MEASURES if m != "dual_verification"]
        op = OperationRecord("op_x", "CRITICAL", False, measures, True, True)
        findings = check_required_measures(op)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].finding_type, "MISSING_MEASURE")
        self.assertIn("dual_verification", findings[0].details)
        self.assertEqual(findings[0].operation, "op_x")

    def test_high_op_missing_interlock(self):
        measures = [m for m in _ALL_HIGH_MEASURES if m != "interlock"]
        op = OperationRecord("op_y", "HIGH", True, measures, True, True)
        findings = check_required_measures(op)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].finding_type, "MISSING_MEASURE")
        self.assertIn("interlock", findings[0].details)

    def test_high_op_full_set_no_findings(self):
        op = _make_high()
        self.assertEqual(check_required_measures(op), [])

    def test_medium_op_minimal_set_no_findings(self):
        op = OperationRecord("op_med", "MEDIUM", True,
                             ["confirmation_step", "reversibility_check"], False, False)
        self.assertEqual(check_required_measures(op), [])

    def test_medium_op_missing_reversibility_check(self):
        op = OperationRecord("op_med2", "MEDIUM", True,
                             ["confirmation_step"], False, False)
        findings = check_required_measures(op)
        self.assertEqual(len(findings), 1)
        self.assertIn("reversibility_check", findings[0].details)

    def test_low_op_no_measures_no_findings(self):
        op = OperationRecord("op_low", "LOW", True, [], False, False)
        self.assertEqual(check_required_measures(op), [])

    def test_multiple_missing_measures_all_reported(self):
        op = OperationRecord("op_multi", "CRITICAL", False, [], True, True)
        findings = check_required_measures(op)
        reported_names = {f.details.split("'")[1] for f in findings}
        self.assertEqual(reported_names, set(_ALL_CRITICAL_MEASURES))


class TestInterfaceRequirementsCheck(unittest.TestCase):

    def test_critical_missing_state_cues_flagged(self):
        op = _make_critical(state_cues=False)
        findings = check_interface_requirements(op)
        types = {f.finding_type for f in findings}
        self.assertIn("MISSING_STATE_CUES", types)

    def test_critical_missing_go_nogo_flagged(self):
        op = _make_critical(go_nogo=False)
        findings = check_interface_requirements(op)
        types = {f.finding_type for f in findings}
        self.assertIn("MISSING_GO_NOGO", types)

    def test_high_missing_both_interface_requirements(self):
        op = _make_high(state_cues=False, go_nogo=False)
        findings = check_interface_requirements(op)
        self.assertEqual(len(findings), 2)
        types = {f.finding_type for f in findings}
        self.assertIn("MISSING_STATE_CUES", types)
        self.assertIn("MISSING_GO_NOGO", types)

    def test_critical_all_interface_present_no_findings(self):
        op = _make_critical(state_cues=True, go_nogo=True)
        self.assertEqual(check_interface_requirements(op), [])

    def test_low_op_interface_not_required(self):
        op = OperationRecord("op_low", "LOW", True, [], False, False)
        self.assertEqual(check_interface_requirements(op), [])

    def test_medium_op_interface_not_required(self):
        op = OperationRecord("op_med", "MEDIUM", True, [], False, False)
        self.assertEqual(check_interface_requirements(op), [])


class TestIrreversibilityProtectionCheck(unittest.TestCase):

    def test_irreversible_high_missing_dual_verification_flagged(self):
        # HIGH op + irreversible → must have full CRITICAL set
        measures = [m for m in _ALL_CRITICAL_MEASURES if m != "dual_verification"]
        op = OperationRecord("op_irrev_high", "HIGH", False, measures, True, True)
        findings = check_irreversibility_protection(op)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].finding_type, "IRREVERSIBLE_UNDERPROTECTED")
        self.assertIn("dual_verification", findings[0].details)

    def test_irreversible_critical_full_set_no_finding(self):
        op = _make_critical(reversible=False)  # all 5 measures present
        self.assertEqual(check_irreversibility_protection(op), [])

    def test_reversible_high_no_irreversibility_finding(self):
        op = _make_high(reversible=True)
        self.assertEqual(check_irreversibility_protection(op), [])

    def test_irreversible_low_not_subject_to_check(self):
        op = OperationRecord("op_low_irrev", "LOW", False, [], False, False)
        self.assertEqual(check_irreversibility_protection(op), [])

    def test_irreversible_medium_not_subject_to_check(self):
        op = OperationRecord("op_med_irrev", "MEDIUM", False,
                             ["confirmation_step", "reversibility_check"], False, False)
        self.assertEqual(check_irreversibility_protection(op), [])


class TestAssessOperation(unittest.TestCase):

    def test_fully_compliant_critical_op_no_findings(self):
        op = _make_critical(reversible=False)
        self.assertEqual(assess_operation(op), [])

    def test_non_compliant_op_produces_multiple_finding_types(self):
        # CRITICAL, irreversible, no measures, no interface requirements
        op = OperationRecord("op_bad", "CRITICAL", False, [], False, False)
        findings = assess_operation(op)
        types = {f.finding_type for f in findings}
        self.assertIn("MISSING_MEASURE", types)
        self.assertIn("MISSING_STATE_CUES", types)
        self.assertIn("MISSING_GO_NOGO", types)
        self.assertIn("IRREVERSIBLE_UNDERPROTECTED", types)

    def test_findings_carry_correct_operation_name(self):
        op = OperationRecord("named_op", "HIGH", False, [], False, False)
        findings = assess_operation(op)
        for f in findings:
            self.assertEqual(f.operation, "named_op")


class TestAssessCatalogue(unittest.TestCase):

    def test_catalogue_entry_per_operation(self):
        ops = [_make_critical("op1"), _make_high("op2")]
        result = assess_catalogue(ops)
        self.assertIn("op1", result)
        self.assertIn("op2", result)
        self.assertEqual(len(result), 2)

    def test_compliant_op_has_empty_findings_list(self):
        result = assess_catalogue([_make_critical("op_good", reversible=False)])
        self.assertEqual(result["op_good"], [])

    def test_non_compliant_op_has_findings(self):
        op = OperationRecord("op_nok", "HIGH", False, [], False, False)
        result = assess_catalogue([op])
        self.assertGreater(len(result["op_nok"]), 0)

    def test_empty_catalogue_returns_empty_dict(self):
        self.assertEqual(assess_catalogue([]), {})


class TestIsCompliant(unittest.TestCase):

    def test_is_compliant_with_no_findings(self):
        self.assertTrue(is_compliant([]))

    def test_is_not_compliant_with_one_finding(self):
        f = SafetyFinding("op", "MISSING_MEASURE", "detail")
        self.assertFalse(is_compliant([f]))

    def test_is_not_compliant_with_multiple_findings(self):
        findings = [
            SafetyFinding("op", "MISSING_MEASURE", "d1"),
            SafetyFinding("op", "MISSING_STATE_CUES", "d2"),
        ]
        self.assertFalse(is_compliant(findings))


if __name__ == "__main__":
    unittest.main()
