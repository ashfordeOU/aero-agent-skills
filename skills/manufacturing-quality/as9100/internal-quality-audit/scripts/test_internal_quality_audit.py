"""Contract test for the internal quality audit program logic.

Offline, deterministic, stdlib unittest. Run from the leaf directory:

    python3 scripts/test_internal_quality_audit.py

Covers the spec validation list: ValueError rejections (malformed
date, unknown risk category, empty required_areas, lot_size below 1,
confidence outside [0.5, 0.999], impact_severity outside 1-5), the
month end clamp, independence failures, the finding ladder, closure
verification, determinism, and the worked example from the spec.
"""

import unittest

from internal_quality_audit_logic import (
    BASE_INTERVAL_MONTHS,
    RISK_MULTIPLIERS,
    audit_due_date,
    audit_sample_size,
    auditor_competent,
    auditor_independent,
    classify_finding,
    internal_audit_review,
    verify_closure,
)

WORKED = dict(
    last_audit_date_iso="2026-03-15",
    risk_category="high",
    lot_size=400,
    auditor_name="A. Chen",
    area_owner_name="B. Lopez",
    required_areas=["calibration", "corrective action"],
    qualifications=["calibration", "corrective action", "document control"],
    impact_severity=3,
    containment_required=True,
    systemic=False,
    corrective_action_taken=True,
    root_cause_stated=True,
    effectiveness_check=True,
)


class TestModuleConstants(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(BASE_INTERVAL_MONTHS, 12.0)
        self.assertEqual(RISK_MULTIPLIERS,
                         {"low": 1.5, "medium": 1.0, "high": 0.5})


class TestAuditDueDate(unittest.TestCase):
    def test_risk_based_intervals(self):
        # 12 * 0.5 = 6 months (high), 12 months (medium), 18 (low).
        self.assertEqual(audit_due_date("2026-03-15", "high"),
                         "2026-09-15")
        self.assertEqual(audit_due_date("2026-03-15", "medium"),
                         "2027-03-15")
        self.assertEqual(audit_due_date("2026-03-15", "low"),
                         "2027-09-15")

    def test_month_end_clamp(self):
        # 2026-01-31 + 1 month -> 2026-02-28; leap year -> 2024-02-29.
        self.assertEqual(audit_due_date("2026-01-31", "medium", 1.0),
                         "2026-02-28")
        self.assertEqual(audit_due_date("2024-01-31", "medium", 1.0),
                         "2024-02-29")

    def test_rollover_and_custom_base(self):
        self.assertEqual(audit_due_date("2025-11-30", "medium", 2.0),
                         "2026-01-30")
        # base 4.0 * high 0.5 = 2 calendar months.
        self.assertEqual(audit_due_date("2026-01-15", "high", 4.0),
                         "2026-03-15")

    def test_malformed_date_raises(self):
        for bad in ("15-03-2026", "2026/03/15", "not-a-date", ""):
            with self.assertRaises(ValueError):
                audit_due_date(bad, "medium")

    def test_unknown_risk_category_raises(self):
        for bad in ("extreme", "HIGH", "Medium", ""):
            with self.assertRaises(ValueError):
                audit_due_date("2026-03-15", bad)


class TestAuditorIndependence(unittest.TestCase):
    def test_independent_when_people_differ(self):
        result = auditor_independent("A. Chen", "B. Lopez")
        self.assertTrue(result["independent"])
        self.assertIn("reason", result)

    def test_not_independent_when_same_person(self):
        result = auditor_independent("A. Chen", "A. Chen")
        self.assertFalse(result["independent"])
        # Case insensitive comparison.
        self.assertFalse(
            auditor_independent("a. chen", "A. Chen")["independent"])

    def test_not_independent_on_declared_conflict(self):
        result = auditor_independent("A. Chen", "B. Lopez",
                                     independence_ok=False)
        self.assertFalse(result["independent"])

    def test_result_keys_exact(self):
        self.assertEqual(
            sorted(auditor_independent("A", "B").keys()),
            ["independent", "reason"])


class TestAuditorCompetence(unittest.TestCase):
    def test_competent_when_required_covered(self):
        quals = ["calibration", "corrective action", "document control"]
        self.assertTrue(
            auditor_competent(quals, None,
                              ["calibration", "corrective action"]))
        # Case insensitive substring match.
        self.assertTrue(
            auditor_competent(["Calibration Technician"],
                              None, ["calibration"]))

    def test_not_competent_when_area_missing(self):
        self.assertFalse(
            auditor_competent(["calibration"], None,
                              ["calibration", "welding"]))
        self.assertFalse(auditor_competent([], None, ["calibration"]))

    def test_competent_scope_fallback(self):
        # Two argument call checks the audit scope areas.
        self.assertTrue(auditor_competent(["calibration"], ["calibration"]))
        self.assertFalse(auditor_competent(["calibration"], ["welding"]))

    def test_empty_required_areas_raises(self):
        with self.assertRaises(ValueError):
            auditor_competent(["calibration"], None, [])


class TestAuditSampleSize(unittest.TestCase):
    def test_sqrt_anchor_at_default_confidence(self):
        # ceil(sqrt(400)) = 20 at 0.95; spec magnitude bound 15-25.
        self.assertEqual(audit_sample_size(400), 20)
        self.assertTrue(15 <= audit_sample_size(400) <= 25)

    def test_high_confidence_factor(self):
        # 20 * 1.2 = 24 at 0.99.
        self.assertEqual(audit_sample_size(400, 0.99), 24)

    def test_low_confidence_factor(self):
        # 20 * 0.8 = 16 at 0.90.
        self.assertEqual(audit_sample_size(400, 0.90), 16)

    def test_rounds_up_non_square_lot_and_minimum(self):
        # ceil(sqrt(10)) = 4 at 0.95; sample never below 1.
        self.assertEqual(audit_sample_size(10), 4)
        self.assertEqual(audit_sample_size(1), 1)

    def test_lot_size_below_one_raises(self):
        for bad in (0, -5):
            with self.assertRaises(ValueError):
                audit_sample_size(bad)

    def test_confidence_out_of_range_raises(self):
        for bad in (0.49, 0.4, 1.0, 1.5):
            with self.assertRaises(ValueError):
                audit_sample_size(400, bad)
        # Edges of [0.5, 0.999] are accepted.
        self.assertIsInstance(audit_sample_size(400, 0.5), int)
        self.assertIsInstance(audit_sample_size(400, 0.999), int)


class TestClassifyFinding(unittest.TestCase):
    def test_severity_ladder(self):
        self.assertEqual(classify_finding(5, False, False), "major")
        self.assertEqual(classify_finding(4, False, False), "major")
        self.assertEqual(classify_finding(1, False, False), "ofi")

    def test_minor_default_for_mid_severity(self):
        self.assertEqual(classify_finding(3, False, False), "minor")
        self.assertEqual(classify_finding(2, False, False), "minor")

    def test_systemic_escalates_minor_to_major(self):
        self.assertEqual(classify_finding(2, False, True), "major")
        self.assertEqual(classify_finding(3, False, True), "major")

    def test_containment_required_escalates(self):
        self.assertEqual(classify_finding(1, True, False), "major")
        self.assertEqual(classify_finding(2, True, False), "major")

    def test_severity_out_of_range_raises(self):
        for bad in (0, -1, 6, 7):
            with self.assertRaises(ValueError):
                classify_finding(bad, False, False)


class TestVerifyClosure(unittest.TestCase):
    def test_closure_requires_all_three_elements(self):
        self.assertTrue(verify_closure("yes", "yes", "verified"))
        self.assertFalse(verify_closure("", "cause", "verified"))
        self.assertFalse(verify_closure("action", None, "verified"))
        self.assertFalse(verify_closure("action", "cause", False))
        self.assertFalse(verify_closure(0, "cause", "verified"))


class TestInternalAuditReview(unittest.TestCase):
    def test_worked_example(self):
        result = internal_audit_review(**WORKED)
        self.assertEqual(result["due_date"], "2026-09-15")
        self.assertEqual(result["interval_months"], 6.0)
        self.assertTrue(result["auditor_independent"]["independent"])
        self.assertTrue(result["auditor_competent"])
        self.assertEqual(result["sample_size"], 20)
        self.assertEqual(result["finding_classification"], "major")
        self.assertTrue(result["closure_verified"])
        # Determinism: no RNG, run-to-run identical output.
        self.assertEqual(result, internal_audit_review(**WORKED))

    def test_result_keys_exact(self):
        result = internal_audit_review(**WORKED)
        self.assertEqual(
            sorted(result.keys()),
            ["auditor_competent", "auditor_independent",
             "closure_verified", "due_date", "finding_classification",
             "interval_months", "sample_size"])

    def test_closure_false_propagates(self):
        args = dict(WORKED)
        args.update(corrective_action_taken="",
                    root_cause_stated="n/a",
                    effectiveness_check=False)
        result = internal_audit_review(**args)
        self.assertFalse(result["closure_verified"])
        self.assertEqual(result["finding_classification"], "major")

    def test_errors_propagate_from_chain(self):
        cases = [
            dict(WORKED, last_audit_date_iso="2026/03/15"),
            dict(WORKED, risk_category="extreme"),
            dict(WORKED, lot_size=0),
            dict(WORKED, required_areas=[]),
        ]
        for bad_args in cases:
            with self.assertRaises(ValueError):
                internal_audit_review(**bad_args)


if __name__ == "__main__":
    unittest.main()
