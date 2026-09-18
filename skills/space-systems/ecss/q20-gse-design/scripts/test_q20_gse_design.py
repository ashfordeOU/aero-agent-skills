"""Contract tests for the clause 5.8.1 GSE design assurance logic."""

import unittest

from q20_gse_design_logic import (
    CRITICALITIES,
    TEST_ONLY_CRITICALITIES,
    VERIFICATION_METHODS,
    assess_gse_design_assurance,
    closure_coverage,
    method_adequacy_findings,
    normalize_token,
    review_verdict,
    upward_trace_findings,
    validate_requirement,
    validate_requirement_set,
    validate_verification_records,
    verification_findings,
)

SOURCES = ["sys-req-100", "sys-req-200", "sys-req-300"]

REQUIREMENTS = [
    {"id": "gse-req-1", "criticality": "standard", "planned_method": "inspection", "parent_id": "sys-req-100"},
    {"id": "gse-req-2", "criticality": "safety-critical", "planned_method": "test", "parent_id": "sys-req-200"},
    {"id": "gse-req-3", "criticality": "flight-hardware-interfacing", "planned_method": "test", "parent_id": "sys-req-300"},
]

RECORDS = [
    {"id": "vr-1", "requirement_id": "gse-req-1", "method": "inspection", "result": "passed"},
    {"id": "vr-2", "requirement_id": "gse-req-2", "method": "test", "result": "passed"},
    {"id": "vr-3", "requirement_id": "gse-req-3", "method": "test", "result": "passed"},
]


def _spec(**overrides):
    spec = {
        "requirements": [dict(r) for r in REQUIREMENTS],
        "source_ids": list(SOURCES),
        "verification_records": [dict(r) for r in RECORDS],
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_identifier_case_folded(self):
        self.assertEqual(normalize_token("GSE_Req 1"), "gse-req-1")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("  ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(3.5)


class ValidateRequirementTests(unittest.TestCase):
    def test_valid_record_normalized(self):
        requirement = validate_requirement(REQUIREMENTS[1])
        self.assertEqual(requirement["criticality"], "safety-critical")
        self.assertEqual(requirement["planned_method"], "test")

    def test_absent_parent_is_allowed_here_and_caught_in_tracing(self):
        requirement = validate_requirement(
            {"id": "gse-req-9", "criticality": "standard", "planned_method": "test"}
        )
        self.assertIsNone(requirement["parent_id"])

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "r", "criticality": "urgent", "planned_method": "test"})

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "r", "criticality": "standard", "planned_method": "demo"})

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "r", "criticality": "standard"})

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement_set(
                [
                    {"id": "gse-req-1", "criticality": "standard", "planned_method": "test"},
                    {"id": "GSE REQ 1", "criticality": "standard", "planned_method": "test"},
                ]
            )

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement_set([])

    def test_method_and_criticality_vocabularies_are_disjoint(self):
        self.assertEqual(set(VERIFICATION_METHODS) & set(CRITICALITIES), set())


class ValidateRecordTests(unittest.TestCase):
    def test_records_normalized(self):
        records = validate_verification_records(RECORDS)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["result"], "passed")

    def test_none_is_an_empty_set(self):
        self.assertEqual(validate_verification_records(None), [])

    def test_unknown_result_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_records(
                [{"id": "vr-x", "requirement_id": "gse-req-1", "method": "test", "result": "maybe"}]
            )

    def test_duplicate_record_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_records([dict(RECORDS[0]), dict(RECORDS[0])])

    def test_missing_requirement_link_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_records([{"id": "vr-y", "method": "test", "result": "passed"}])


class UpwardTraceTests(unittest.TestCase):
    def test_fully_traced_set_is_clean(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        self.assertEqual(upward_trace_findings(requirements, SOURCES), [])

    def test_orphan_requirement_is_named(self):
        requirements = validate_requirement_set(
            REQUIREMENTS + [{"id": "gse-req-4", "criticality": "standard", "planned_method": "test"}]
        )
        findings = upward_trace_findings(requirements, SOURCES)
        self.assertEqual(len(findings), 1)
        self.assertIn("names no source requirement", findings[0])

    def test_parent_outside_the_source_set_is_named(self):
        requirements = validate_requirement_set(
            [
                {
                    "id": "gse-req-5",
                    "criticality": "standard",
                    "planned_method": "test",
                    "parent_id": "sys-req-999",
                }
            ]
        )
        findings = upward_trace_findings(requirements, SOURCES)
        self.assertIn("not in the source set", findings[0])

    def test_non_sequence_sources_rejected(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        with self.assertRaises(ValueError):
            upward_trace_findings(requirements, "sys-req-100")


class VerificationFindingTests(unittest.TestCase):
    def test_complete_verification_is_clean(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        records = validate_verification_records(RECORDS)
        self.assertEqual(verification_findings(requirements, records), [])

    def test_unverified_requirement_is_named(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        records = validate_verification_records(RECORDS[:2])
        findings = verification_findings(requirements, records)
        self.assertTrue(any("has no verification record" in f for f in findings))

    def test_method_substitution_is_named(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        swapped = [dict(r) for r in RECORDS]
        swapped[1]["method"] = "analysis"
        records = validate_verification_records(swapped)
        findings = verification_findings(requirements, records)
        self.assertTrue(any("planned test but record" in f for f in findings))

    def test_failed_record_is_named(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        failed = [dict(r) for r in RECORDS]
        failed[0]["result"] = "failed"
        records = validate_verification_records(failed)
        self.assertTrue(any("failed" in f for f in verification_findings(requirements, records)))

    def test_open_record_is_named_separately(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        pending = [dict(r) for r in RECORDS]
        pending[2]["result"] = "open"
        records = validate_verification_records(pending)
        self.assertTrue(any("still open" in f for f in verification_findings(requirements, records)))

    def test_record_for_an_unknown_requirement_is_named(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        records = validate_verification_records(
            RECORDS + [{"id": "vr-9", "requirement_id": "gse-req-77", "method": "test", "result": "passed"}]
        )
        findings = verification_findings(requirements, records)
        self.assertTrue(any("not a GSE requirement" in f for f in findings))


class MethodAdequacyTests(unittest.TestCase):
    def test_test_planned_critical_requirements_are_clean(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        self.assertEqual(method_adequacy_findings(requirements), [])

    def test_safety_critical_on_review_of_design_is_a_finding(self):
        requirements = validate_requirement_set(
            [
                {
                    "id": "gse-req-6",
                    "criticality": "safety-critical",
                    "planned_method": "review-of-design",
                    "parent_id": "sys-req-100",
                }
            ]
        )
        findings = method_adequacy_findings(requirements)
        self.assertEqual(len(findings), 1)
        self.assertIn("closed by test", findings[0])

    def test_standard_requirement_may_use_a_paper_method(self):
        requirements = validate_requirement_set(
            [
                {
                    "id": "gse-req-7",
                    "criticality": "standard",
                    "planned_method": "analysis",
                    "parent_id": "sys-req-100",
                }
            ]
        )
        self.assertEqual(method_adequacy_findings(requirements), [])

    def test_both_critical_categories_are_covered(self):
        self.assertEqual(len(TEST_ONLY_CRITICALITIES), 2)


class CoverageTests(unittest.TestCase):
    def test_full_closure_is_unity(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        records = validate_verification_records(RECORDS)
        self.assertAlmostEqual(closure_coverage(requirements, records), 1.0, places=9)

    def test_one_open_requirement_drops_the_coverage(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        records = validate_verification_records(RECORDS[:2])
        self.assertAlmostEqual(closure_coverage(requirements, records), 2.0 / 3.0, places=9)

    def test_a_later_failure_removes_an_earlier_pass(self):
        requirements = validate_requirement_set(REQUIREMENTS)
        records = validate_verification_records(
            RECORDS + [{"id": "vr-4", "requirement_id": "gse-req-1", "method": "inspection", "result": "failed"}]
        )
        self.assertAlmostEqual(closure_coverage(requirements, records), 2.0 / 3.0, places=9)

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            closure_coverage([], [])


class VerdictTests(unittest.TestCase):
    def test_clean_review_is_approved(self):
        self.assertEqual(review_verdict([], []), "approved")

    def test_actions_only_is_approved_with_actions(self):
        self.assertEqual(review_verdict([], ["record open"]), "approved-with-actions")

    def test_blocking_is_not_approved(self):
        self.assertEqual(review_verdict(["untraced"], ["record open"]), "not-approved")

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            review_verdict("untraced", [])


class AssessGseDesignTests(unittest.TestCase):
    def test_clean_design_is_approved(self):
        result = assess_gse_design_assurance(_spec())
        self.assertEqual(result["verdict"], "approved")
        self.assertTrue(result["design_usable"])
        self.assertAlmostEqual(result["closure_coverage"], 1.0, places=9)

    def test_open_record_yields_actions_not_rejection(self):
        spec = _spec()
        spec["verification_records"][0]["result"] = "open"
        spec["required_coverage"] = 0.5
        result = assess_gse_design_assurance(spec)
        self.assertEqual(result["verdict"], "approved-with-actions")
        self.assertTrue(result["design_usable"])

    def test_untraced_requirement_is_not_approved(self):
        spec = _spec()
        spec["requirements"].append(
            {"id": "gse-req-8", "criticality": "standard", "planned_method": "test"}
        )
        spec["verification_records"].append(
            {"id": "vr-8", "requirement_id": "gse-req-8", "method": "test", "result": "passed"}
        )
        result = assess_gse_design_assurance(spec)
        self.assertEqual(result["verdict"], "not-approved")

    def test_paper_closed_safety_requirement_is_not_approved(self):
        spec = _spec()
        spec["requirements"][1]["planned_method"] = "analysis"
        spec["verification_records"][1]["method"] = "analysis"
        result = assess_gse_design_assurance(spec)
        self.assertEqual(result["verdict"], "not-approved")

    def test_coverage_shortfall_is_blocking(self):
        spec = _spec(verification_records=RECORDS[:1])
        result = assess_gse_design_assurance(spec)
        self.assertEqual(result["verdict"], "not-approved")
        self.assertAlmostEqual(result["closure_coverage"], 1.0 / 3.0, places=9)

    def test_required_coverage_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_design_assurance(_spec(required_coverage=1.4))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["source_ids"]
        with self.assertRaises(ValueError):
            assess_gse_design_assurance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_design_assurance(["requirements"])


if __name__ == "__main__":
    unittest.main()
