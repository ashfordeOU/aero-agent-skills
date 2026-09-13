#!/usr/bin/env python3
"""Gate 3 contract test for e20-antenna-requirement-verification.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e20_antenna_requirement_verification.py
"""

import unittest

import e20_antenna_requirement_verification_logic as logic


def requirement(**overrides):
    """A compliant baseline requirement, overridable field by field."""
    base = {
        "id": "ANT-REQ-001",
        "category": "radiation-pattern",
        "method": "test",
        "planned_gate": "QR",
        "status": "closed",
        "record": "AVR-0142",
    }
    base.update(overrides)
    return base


class TestMethodNormalization(unittest.TestCase):
    def test_canonical_method_passes_through(self):
        self.assertEqual(logic.normalize_method("analysis"), "analysis")

    def test_method_letter_code_expands(self):
        self.assertEqual(logic.normalize_method("R"), "review-of-design")

    def test_method_is_case_and_space_insensitive(self):
        self.assertEqual(logic.normalize_method("  Review Of Design "), "review-of-design")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_method("hand-waving")

    def test_empty_method_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_method("   ")

    def test_non_string_method_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_method(7)


class TestGateNormalization(unittest.TestCase):
    def test_gate_uppercases(self):
        self.assertEqual(logic.normalize_gate("cdr"), "CDR")

    def test_gate_index_is_ordered(self):
        self.assertLess(logic.gate_index("PDR"), logic.gate_index("CDR"))
        self.assertLess(logic.gate_index("CDR"), logic.gate_index("QR"))
        self.assertLess(logic.gate_index("QR"), logic.gate_index("AR"))

    def test_unknown_gate_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_gate("SRR")

    def test_non_string_gate_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_gate(None)


class TestCategoryAndStatus(unittest.TestCase):
    def test_radiation_pattern_admits_measurement_and_analysis(self):
        self.assertEqual(
            logic.admissible_methods("radiation-pattern"), frozenset({"test", "analysis"})
        )

    def test_materials_category_admits_similarity(self):
        self.assertIn("similarity", logic.admissible_methods("materials-and-finish"))

    def test_failure_rate_category_excludes_inspection(self):
        self.assertNotIn("inspection", logic.admissible_methods("failure-rate-allocation"))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            logic.admissible_methods("paint-colour")

    def test_latest_allowed_gate_for_failure_rate_is_critical_design(self):
        self.assertEqual(logic.latest_allowed_gate("failure-rate-allocation"), "CDR")

    def test_earliest_feasible_gate_ordering(self):
        self.assertEqual(logic.earliest_feasible_gate("review-of-design"), "PDR")
        self.assertEqual(logic.earliest_feasible_gate("analysis"), "CDR")
        self.assertEqual(logic.earliest_feasible_gate("test"), "QR")

    def test_status_normalizes(self):
        self.assertEqual(logic.normalize_status(" Waived "), "waived")

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_status("nearly-done")


class TestRecordIdentifier(unittest.TestCase):
    def test_well_formed_record_accepted(self):
        self.assertTrue(logic.is_well_formed_record("AVR-0142"))

    def test_record_with_trailing_space_accepted(self):
        self.assertTrue(logic.is_well_formed_record(" ANT-17 "))

    def test_lowercase_record_rejected(self):
        self.assertFalse(logic.is_well_formed_record("avr-0142"))

    def test_record_without_digits_rejected(self):
        self.assertFalse(logic.is_well_formed_record("AVR-XX"))

    def test_non_string_record_rejected(self):
        self.assertFalse(logic.is_well_formed_record(142))


class TestRequirementEvaluation(unittest.TestCase):
    def test_compliant_requirement_has_no_findings(self):
        result = logic.evaluate_requirement(requirement())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_inadmissible_method_is_flagged(self):
        result = logic.evaluate_requirement(
            requirement(category="failure-rate-allocation", method="inspection")
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any(f.startswith("method-not-admissible") for f in result["findings"])
        )

    def test_measurement_closure_before_hardware_gate_is_flagged(self):
        result = logic.evaluate_requirement(
            requirement(method="test", planned_gate="PDR")
        )
        self.assertTrue(
            any(
                f.startswith("gate-earlier-than-method-can-close")
                for f in result["findings"]
            )
        )

    def test_closure_after_category_deadline_is_flagged(self):
        result = logic.evaluate_requirement(
            requirement(
                category="failure-rate-allocation",
                method="analysis",
                planned_gate="AR",
                record="AVR-0900",
            )
        )
        self.assertTrue(
            any(
                f.startswith("gate-later-than-category-allows")
                for f in result["findings"]
            )
        )

    def test_design_argument_may_close_at_preliminary_gate(self):
        result = logic.evaluate_requirement(
            requirement(
                category="materials-and-finish",
                method="review-of-design",
                planned_gate="PDR",
                record="AVR-0007",
            )
        )
        self.assertTrue(result["compliant"])

    def test_closed_without_record_is_flagged(self):
        result = logic.evaluate_requirement(requirement(record=None))
        self.assertTrue(
            any(f.startswith("missing-verification-record") for f in result["findings"])
        )

    def test_closed_with_blank_record_is_flagged(self):
        result = logic.evaluate_requirement(requirement(record="   "))
        self.assertTrue(
            any(f.startswith("missing-verification-record") for f in result["findings"])
        )

    def test_closed_with_malformed_record_is_flagged(self):
        result = logic.evaluate_requirement(requirement(record="see the folder"))
        self.assertTrue(
            any(f.startswith("malformed-verification-record") for f in result["findings"])
        )

    def test_waiver_with_reference_and_rationale_passes(self):
        result = logic.evaluate_requirement(
            requirement(
                status="waived",
                record=None,
                waiver_reference="WVR-0031",
                rationale="covered by the recurring qualification of the heritage feed",
            )
        )
        self.assertTrue(result["compliant"])

    def test_waiver_without_reference_is_flagged(self):
        result = logic.evaluate_requirement(
            requirement(status="waived", record=None, rationale="heritage feed")
        )
        self.assertTrue(
            any(f.startswith("waiver-without-reference") for f in result["findings"])
        )

    def test_waiver_without_rationale_is_flagged(self):
        result = logic.evaluate_requirement(
            requirement(status="waived", record=None, waiver_reference="WVR-0031")
        )
        self.assertTrue(
            any(f.startswith("waiver-without-rationale") for f in result["findings"])
        )

    def test_open_requirement_before_its_gate_is_not_flagged(self):
        result = logic.evaluate_requirement(
            requirement(status="open", record=None, planned_gate="QR"), at_gate="CDR"
        )
        self.assertTrue(result["compliant"])

    def test_open_requirement_at_its_gate_is_flagged(self):
        result = logic.evaluate_requirement(
            requirement(status="open", record=None, planned_gate="QR"), at_gate="QR"
        )
        self.assertTrue(
            any(f.startswith("open-past-planned-gate") for f in result["findings"])
        )

    def test_open_requirement_without_assessment_gate_is_silent(self):
        result = logic.evaluate_requirement(
            requirement(status="open", record=None, planned_gate="QR")
        )
        self.assertEqual(result["findings"], [])

    def test_requirement_without_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_requirement(requirement(id="  "))

    def test_non_mapping_requirement_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_requirement(["ANT-REQ-001"])

    def test_unknown_category_in_requirement_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_requirement(requirement(category="mystery"))

    def test_two_findings_accumulate_on_one_requirement(self):
        result = logic.evaluate_requirement(
            requirement(
                category="failure-rate-allocation", method="inspection", planned_gate="PDR"
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 2)


class TestCoverage(unittest.TestCase):
    def test_coverage_counts_closed_and_waived(self):
        results = [
            {"status": "closed", "findings": [], "id": "a"},
            {"status": "waived", "findings": [], "id": "b"},
            {"status": "open", "findings": [], "id": "c"},
            {"status": "open", "findings": [], "id": "d"},
        ]
        self.assertAlmostEqual(logic.verification_coverage(results), 0.5, places=12)

    def test_empty_result_set_raises(self):
        with self.assertRaises(ValueError):
            logic.verification_coverage([])

    def test_threshold_met_exactly_is_accepted(self):
        self.assertTrue(logic.meets_coverage_threshold(0.75, 0.75))

    def test_threshold_met_within_representation_error_is_accepted(self):
        coverage = 2 / 3
        threshold = 1 - 1 / 3
        self.assertLess(coverage, threshold)  # one unit in the last place short
        self.assertTrue(logic.meets_coverage_threshold(coverage, threshold))

    def test_real_shortfall_is_still_rejected(self):
        self.assertFalse(logic.meets_coverage_threshold(0.66, 2 / 3))

    def test_threshold_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.meets_coverage_threshold(0.5, 1.4)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            logic.meets_coverage_threshold(0.5, -0.1)

    def test_non_numeric_coverage_raises(self):
        with self.assertRaises(ValueError):
            logic.meets_coverage_threshold("most of it", 0.5)

    def test_boolean_threshold_raises(self):
        with self.assertRaises(ValueError):
            logic.meets_coverage_threshold(0.5, True)


class TestAssessment(unittest.TestCase):
    def test_clean_set_is_compliant(self):
        report = logic.assess_antenna_requirement_verification(
            [
                requirement(id="ANT-REQ-001"),
                requirement(
                    id="ANT-REQ-002",
                    category="guided-wave-interface",
                    method="inspection",
                    record="ANT-0021",
                ),
            ]
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["finding_total"], 0)
        self.assertAlmostEqual(report["coverage"], 1.0, places=12)

    def test_open_requirement_fails_full_coverage_threshold(self):
        report = logic.assess_antenna_requirement_verification(
            [
                requirement(id="ANT-REQ-001"),
                requirement(id="ANT-REQ-002", status="open", record=None),
            ]
        )
        self.assertFalse(report["coverage_met"])
        self.assertFalse(report["compliant"])
        self.assertEqual(report["open_ids"], ["ANT-REQ-002"])

    def test_relaxed_threshold_accepts_partial_coverage(self):
        report = logic.assess_antenna_requirement_verification(
            [
                requirement(id="ANT-REQ-001"),
                requirement(id="ANT-REQ-002", status="open", record=None),
            ],
            coverage_threshold=0.5,
        )
        self.assertTrue(report["coverage_met"])
        self.assertTrue(report["compliant"])

    def test_finding_counts_group_by_code(self):
        report = logic.assess_antenna_requirement_verification(
            [
                requirement(id="ANT-REQ-001", record=None),
                requirement(id="ANT-REQ-002", record=None),
            ]
        )
        self.assertEqual(report["finding_counts"]["missing-verification-record"], 2)
        self.assertEqual(report["finding_total"], 2)

    def test_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_antenna_requirement_verification(
                [requirement(id="ANT-REQ-001"), requirement(id="ANT-REQ-001")]
            )

    def test_empty_requirement_list_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_antenna_requirement_verification([])

    def test_non_list_requirement_set_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_antenna_requirement_verification({"id": "ANT-REQ-001"})

    def test_assessment_gate_propagates_to_each_requirement(self):
        report = logic.assess_antenna_requirement_verification(
            [requirement(id="ANT-REQ-001", status="open", record=None, planned_gate="CDR")],
            coverage_threshold=0.0,
            at_gate="QR",
        )
        self.assertEqual(report["finding_counts"]["open-past-planned-gate"], 1)
        self.assertFalse(report["compliant"])

    def test_report_carries_normalized_fields(self):
        report = logic.assess_antenna_requirement_verification(
            [requirement(id="ANT-REQ-009", method="T", planned_gate="qr")]
        )
        result = report["results"][0]
        self.assertEqual(result["method"], "test")
        self.assertEqual(result["planned_gate"], "QR")
        self.assertEqual(result["category"], "radiation-pattern")


if __name__ == "__main__":
    unittest.main()
