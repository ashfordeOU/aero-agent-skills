"""Contract tests for the clause 5.5.1/5.5.2 qualification-stage logic."""

import unittest

from e3102_qualification_stage_quality_audits_logic import (
    AUDIT_VALIDITY_MONTHS,
    SPECIAL_PROCESSES,
    STAGE_ACTIVITIES,
    assess_qualification_stage,
    audit_age_months,
    audit_status,
    coverage_fraction,
    process_coverage,
    sequence_findings,
    special_processes_required,
    stage_readiness,
    validate_audit,
)

PROCESSES = ["closure-welding", "wick-sintering", "fluid-purity-and-charging"]


def audit(process, month=10, independent=True, major=0, minor=0):
    return {
        "process": process,
        "audit_month": month,
        "independent_auditor": independent,
        "major_findings_open": major,
        "minor_findings_open": minor,
    }


def clean_audits(month=10):
    return [audit(p, month=month) for p in PROCESSES]


class ValidateAuditTests(unittest.TestCase):
    def test_normalises_the_process_name(self):
        self.assertEqual(validate_audit(audit("Closure-Welding"))["process"], "closure-welding")

    def test_minor_findings_default_to_zero(self):
        record = {
            "process": "brazing",
            "audit_month": 4,
            "independent_auditor": True,
            "major_findings_open": 0,
        }
        self.assertEqual(validate_audit(record)["minor_findings_open"], 0)

    def test_missing_key_rejected(self):
        record = audit("brazing")
        del record["audit_month"]
        with self.assertRaises(ValueError):
            validate_audit(record)

    def test_negative_month_rejected(self):
        with self.assertRaises(ValueError):
            validate_audit(audit("brazing", month=-1))

    def test_float_month_rejected(self):
        with self.assertRaises(ValueError):
            validate_audit(audit("brazing", month=4.5))

    def test_non_boolean_independence_rejected(self):
        record = audit("brazing")
        record["independent_auditor"] = "yes"
        with self.assertRaises(ValueError):
            validate_audit(record)

    def test_negative_finding_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_audit(audit("brazing", major=-2))


class AuditStatusTests(unittest.TestCase):
    def test_age_is_the_month_difference(self):
        self.assertEqual(audit_age_months(audit("brazing", month=6), 18), 12)

    def test_reference_before_the_audit_rejected(self):
        with self.assertRaises(ValueError):
            audit_age_months(audit("brazing", month=18), 6)

    def test_fresh_independent_clean_audit_is_covered(self):
        self.assertEqual(audit_status(audit("brazing", month=10), 14)["status"], "covered")

    def test_audit_exactly_at_the_validity_limit_still_counts(self):
        out = audit_status(audit("brazing", month=0), AUDIT_VALIDITY_MONTHS)
        self.assertEqual(out["age_months"], AUDIT_VALIDITY_MONTHS)
        self.assertEqual(out["status"], "covered")

    def test_one_month_past_validity_expires(self):
        out = audit_status(audit("brazing", month=0), AUDIT_VALIDITY_MONTHS + 1)
        self.assertEqual(out["status"], "expired")

    def test_non_independent_auditor_fails(self):
        out = audit_status(audit("brazing", month=10, independent=False), 12)
        self.assertEqual(out["status"], "not-independent")

    def test_open_major_finding_fails(self):
        out = audit_status(audit("brazing", month=10, major=1), 12)
        self.assertEqual(out["status"], "open-major-finding")

    def test_open_minor_finding_does_not_fail(self):
        out = audit_status(audit("brazing", month=10, minor=3), 12)
        self.assertEqual(out["status"], "covered")
        self.assertEqual(out["minor_findings_open"], 3)

    def test_zero_validity_window_rejected(self):
        with self.assertRaises(ValueError):
            audit_status(audit("brazing", month=1), 2, validity_months=0)


class SpecialProcessTests(unittest.TestCase):
    def test_only_special_processes_owe_an_audit(self):
        out = special_processes_required(["closure-welding", "bolt-torquing", "brazing"])
        self.assertEqual(out, ["brazing", "closure-welding"])

    def test_names_are_normalised(self):
        self.assertEqual(special_processes_required(["  Brazing "]), ["brazing"])

    def test_every_listed_process_is_known(self):
        self.assertIn("leak-testing", SPECIAL_PROCESSES)

    def test_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            special_processes_required([])

    def test_non_string_process_rejected(self):
        with self.assertRaises(ValueError):
            special_processes_required([7])


class CoverageTests(unittest.TestCase):
    def test_clean_set_is_fully_covered(self):
        coverage = process_coverage(PROCESSES, clean_audits(), 14)
        self.assertEqual(sorted(coverage), sorted(PROCESSES))
        self.assertAlmostEqual(coverage_fraction(coverage), 1.0, places=12)

    def test_missing_audit_is_reported(self):
        coverage = process_coverage(PROCESSES, clean_audits()[:2], 14)
        self.assertEqual(coverage["fluid-purity-and-charging"]["status"], "missing")
        self.assertAlmostEqual(coverage_fraction(coverage), 2.0 / 3.0, places=12)

    def test_latest_audit_governs(self):
        audits = [audit("closure-welding", month=4), audit("closure-welding", month=12, major=2)]
        coverage = process_coverage(["closure-welding"], audits, 14)
        self.assertEqual(coverage["closure-welding"]["status"], "open-major-finding")

    def test_an_older_clean_audit_does_not_rescue_a_newer_bad_one(self):
        audits = [audit("brazing", month=1), audit("brazing", month=13, independent=False)]
        coverage = process_coverage(["brazing"], audits, 14)
        self.assertEqual(coverage["brazing"]["status"], "not-independent")

    def test_non_special_process_needs_no_audit(self):
        coverage = process_coverage(["closure-welding", "bolt-torquing"], clean_audits(), 14)
        self.assertNotIn("bolt-torquing", coverage)

    def test_no_audits_at_all(self):
        coverage = process_coverage(PROCESSES, None, 14)
        self.assertAlmostEqual(coverage_fraction(coverage), 0.0, places=12)

    def test_empty_coverage_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction({})

    def test_malformed_coverage_entry_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction({"brazing": "covered"})


class SequenceTests(unittest.TestCase):
    def test_house_order_is_clean(self):
        self.assertEqual(sequence_findings(list(STAGE_ACTIVITIES)), [])

    def test_audit_after_model_manufacture_is_a_finding(self):
        order = [
            "qualification-plan-approval",
            "qualification-model-manufacture",
            "supplier-process-quality-audit",
            "qualification-test-campaign",
            "qualification-review",
        ]
        findings = sequence_findings(order)
        self.assertEqual(len(findings), 1)
        self.assertIn("supplier-process-quality-audit", findings[0])

    def test_absent_activity_is_a_finding(self):
        order = [a for a in STAGE_ACTIVITIES if a != "qualification-review"]
        self.assertTrue(any("qualification-review" in f for f in sequence_findings(order)))

    def test_repeated_activity_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings(list(STAGE_ACTIVITIES) + ["qualification-review"])

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings(["paint-the-radiator"])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            sequence_findings([])


class ReadinessTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "planned_sequence": list(STAGE_ACTIVITIES),
            "declared_processes": PROCESSES,
            "audits": clean_audits(),
            "reference_month": 14,
        }
        spec.update(overrides)
        return spec

    def test_clean_stage_is_ready(self):
        out = assess_qualification_stage(self._spec())
        self.assertTrue(out["ready_for_test_campaign"])
        self.assertTrue(out["audits_complete"])
        self.assertEqual(out["blocking_findings"], [])

    def test_missing_audit_blocks(self):
        out = assess_qualification_stage(self._spec(audits=clean_audits()[:1]))
        self.assertFalse(out["ready_for_test_campaign"])
        self.assertEqual(len(out["blocking_findings"]), 2)

    def test_expired_audit_blocks_and_names_the_age(self):
        out = assess_qualification_stage(
            self._spec(reference_month=10 + AUDIT_VALIDITY_MONTHS + 3)
        )
        self.assertFalse(out["ready_for_test_campaign"])
        self.assertTrue(any("months old" in f for f in out["blocking_findings"]))

    def test_minor_findings_are_counted_not_blocking(self):
        audits = [audit(p, minor=2) for p in PROCESSES]
        out = assess_qualification_stage(self._spec(audits=audits))
        self.assertTrue(out["ready_for_test_campaign"])
        self.assertEqual(out["minor_findings_open"], 6)

    def test_sequence_finding_blocks_even_with_clean_audits(self):
        order = [
            "qualification-plan-approval",
            "qualification-model-manufacture",
            "supplier-process-quality-audit",
            "qualification-test-campaign",
            "qualification-review",
        ]
        out = assess_qualification_stage(self._spec(planned_sequence=order))
        self.assertFalse(out["ready_for_test_campaign"])

    def test_shorter_validity_window_is_honoured(self):
        out = assess_qualification_stage(self._spec(validity_months=2))
        self.assertFalse(out["ready_for_test_campaign"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["declared_processes"]
        with self.assertRaises(ValueError):
            assess_qualification_stage(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_stage(["planned_sequence"])

    def test_stage_readiness_requires_a_sequence_list(self):
        coverage = process_coverage(PROCESSES, clean_audits(), 14)
        with self.assertRaises(ValueError):
            stage_readiness(coverage, "no findings")


if __name__ == "__main__":
    unittest.main()
