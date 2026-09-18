#!/usr/bin/env python3
"""Gate 3 contract test for q6005-hermetically-encapsulated-chip-procurement.

Offline, deterministic, stdlib unittest. Exercises the clause 8.4 logic:
declaration testing of each mandatory provision, the cavity-volume band
schedule for the fine-leak reject limit, the exact-boundary comparison,
the gross-leak precedence rule, the moisture ceiling and the combined
procurement assessment.
"""

import unittest

from q6005_hermetically_encapsulated_chip_procurement_logic import (
    DEFAULT_MOISTURE_LIMIT_PPMV,
    MANDATORY_PROVISIONS,
    assess_hermetic_procurement,
    check_provision_coverage,
    evaluate_fine_leak,
    evaluate_moisture,
    fine_leak_reject_limit,
    format_procurement_report,
    is_declared,
    validate_seal_evidence,
)


def spec(**kw):
    entry = {
        "seal_method": "seam-welded lid",
        "cavity_volume_cc": 0.05,
        "gross_leak_method": "fluorocarbon immersion",
        "fine_leak_method": "tracer-gas fixed method",
        "internal_moisture_limit_ppmv": 5000.0,
        "lot_date_code_traceability": "wafer lot and seal date code",
        "screening_level": "level-2 screening",
        "storage_and_handling": "dry nitrogen cabinet",
    }
    entry.update(kw)
    return entry


def evidence(**kw):
    entry = {
        "gross_leak_passed": True,
        "fine_leak_rate": 2e-8,
        "moisture_ppmv": 1200.0,
    }
    entry.update(kw)
    return entry


class TestDeclarationTesting(unittest.TestCase):
    def test_real_string_is_declared(self):
        self.assertTrue(is_declared("seam-welded lid"))

    def test_none_is_not_declared(self):
        self.assertFalse(is_declared(None))

    def test_placeholder_token_is_not_declared(self):
        self.assertFalse(is_declared("TBD"))
        self.assertFalse(is_declared("  n/a "))

    def test_zero_is_a_declaration_not_an_absence(self):
        self.assertTrue(is_declared(0))

    def test_empty_collection_is_not_declared(self):
        self.assertFalse(is_declared([]))


class TestProvisionCoverage(unittest.TestCase):
    def test_complete_specification_has_no_missing_provision(self):
        coverage = check_provision_coverage(spec())
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["missing"], [])
        self.assertEqual(len(coverage["declared"]), len(MANDATORY_PROVISIONS))

    def test_blank_provision_is_reported_missing(self):
        coverage = check_provision_coverage(spec(screening_level="   "))
        self.assertFalse(coverage["complete"])
        self.assertIn("screening_level", coverage["missing"])

    def test_absent_provision_is_reported_missing(self):
        incomplete = spec()
        del incomplete["storage_and_handling"]
        coverage = check_provision_coverage(incomplete)
        self.assertIn("storage_and_handling", coverage["missing"])

    def test_additional_provisions_are_listed_separately(self):
        coverage = check_provision_coverage(spec(marking_scheme="laser mark"))
        self.assertEqual(coverage["additional"], ["marking_scheme"])
        self.assertTrue(coverage["complete"])

    def test_non_mapping_specification_raises(self):
        with self.assertRaises(ValueError):
            check_provision_coverage(["seal_method"])

    def test_empty_required_list_raises(self):
        with self.assertRaises(ValueError):
            check_provision_coverage(spec(), required=[])


class TestFineLeakBands(unittest.TestCase):
    def test_small_cavity_gets_the_tightest_limit(self):
        self.assertAlmostEqual(fine_leak_reject_limit(0.005) / 5e-8, 1.0, places=9)

    def test_band_boundary_stays_in_the_lower_band(self):
        self.assertAlmostEqual(fine_leak_reject_limit(0.01) / 5e-8, 1.0, places=9)
        self.assertAlmostEqual(fine_leak_reject_limit(0.02) / 1e-7, 1.0, places=9)

    def test_large_cavity_gets_the_loosest_limit(self):
        self.assertAlmostEqual(fine_leak_reject_limit(5.0) / 1e-6, 1.0, places=9)

    def test_limit_never_tightens_as_volume_grows(self):
        limits = [fine_leak_reject_limit(v) for v in (0.005, 0.05, 1.0)]
        self.assertEqual(limits, sorted(limits))

    def test_zero_volume_raises(self):
        with self.assertRaises(ValueError):
            fine_leak_reject_limit(0.0)

    def test_non_numeric_volume_raises(self):
        with self.assertRaises(ValueError):
            fine_leak_reject_limit("small")


class TestFineLeakEvaluation(unittest.TestCase):
    def test_reading_exactly_on_the_limit_is_within(self):
        result = evaluate_fine_leak(5e-8, 0.005)
        self.assertTrue(result["within_limit"])
        self.assertAlmostEqual(result["measured_rate"] / result["limit"], 1.0, places=9)

    def test_reading_clearly_over_the_limit_fails(self):
        result = evaluate_fine_leak(9e-7, 0.005)
        self.assertFalse(result["within_limit"])

    def test_reading_clearly_under_the_limit_passes(self):
        result = evaluate_fine_leak(1e-9, 0.005)
        self.assertTrue(result["within_limit"])
        self.assertGreater(result["margin"], 0.0)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            evaluate_fine_leak(-1e-9, 0.005)


class TestMoistureCeiling(unittest.TestCase):
    def test_reading_on_the_ceiling_is_within(self):
        result = evaluate_moisture(5000.0, 5000.0)
        self.assertTrue(result["within_limit"])

    def test_reading_over_the_ceiling_fails(self):
        result = evaluate_moisture(7200.0, 5000.0)
        self.assertFalse(result["within_limit"])

    def test_default_ceiling_is_used_when_none_given(self):
        result = evaluate_moisture(100.0)
        self.assertAlmostEqual(result["limit_ppmv"], DEFAULT_MOISTURE_LIMIT_PPMV, places=9)

    def test_negative_moisture_raises(self):
        with self.assertRaises(ValueError):
            evaluate_moisture(-5.0)

    def test_non_positive_ceiling_raises(self):
        with self.assertRaises(ValueError):
            evaluate_moisture(100.0, 0.0)


class TestSealEvidenceNormalization(unittest.TestCase):
    def test_valid_evidence_normalizes(self):
        item = validate_seal_evidence(evidence())
        self.assertTrue(item["gross_leak_passed"])
        self.assertAlmostEqual(item["fine_leak_rate"] / 2e-8, 1.0, places=9)

    def test_non_boolean_gross_leak_outcome_raises(self):
        with self.assertRaises(ValueError):
            validate_seal_evidence(evidence(gross_leak_passed="pass"))

    def test_missing_fine_leak_rate_raises(self):
        with self.assertRaises(ValueError):
            validate_seal_evidence(evidence(fine_leak_rate=None))

    def test_non_mapping_evidence_raises(self):
        with self.assertRaises(ValueError):
            validate_seal_evidence(("pass", 2e-8))


class TestProcurementAssessment(unittest.TestCase):
    def test_complete_conforming_procurement_is_cleared(self):
        report = assess_hermetic_procurement(spec(), evidence())
        self.assertTrue(report["cleared"])
        self.assertEqual(report["findings"], [])

    def test_missing_provision_blocks_clearance(self):
        report = assess_hermetic_procurement(spec(screening_level=None), evidence())
        self.assertFalse(report["cleared"])
        self.assertTrue(any("screening_level" in f for f in report["findings"]))

    def test_failed_gross_leak_voids_a_healthy_fine_leak_reading(self):
        report = assess_hermetic_procurement(
            spec(), evidence(gross_leak_passed=False, fine_leak_rate=1e-12)
        )
        self.assertFalse(report["cleared"])
        self.assertTrue(any("cannot be credited" in f for f in report["findings"]))

    def test_excess_fine_leak_is_a_finding(self):
        report = assess_hermetic_procurement(spec(), evidence(fine_leak_rate=5e-6))
        self.assertFalse(report["cleared"])
        self.assertTrue(any("exceeds the" in f for f in report["findings"]))

    def test_undeclared_cavity_volume_blocks_the_leak_grading(self):
        report = assess_hermetic_procurement(spec(cavity_volume_cc=None), evidence())
        self.assertFalse(report["cleared"])
        self.assertIsNone(report["fine_leak"])

    def test_unreported_moisture_is_a_finding_not_a_zero(self):
        report = assess_hermetic_procurement(spec(), evidence(moisture_ppmv=None))
        self.assertFalse(report["cleared"])
        self.assertTrue(any("moisture content was not reported" in f for f in report["findings"]))

    def test_excess_moisture_is_a_finding(self):
        report = assess_hermetic_procurement(spec(), evidence(moisture_ppmv=8000.0))
        self.assertFalse(report["cleared"])
        self.assertFalse(report["moisture"]["within_limit"])


class TestReportRendering(unittest.TestCase):
    def test_report_is_deterministic(self):
        first = format_procurement_report(assess_hermetic_procurement(spec(), evidence()))
        second = format_procurement_report(assess_hermetic_procurement(spec(), evidence()))
        self.assertEqual(first, second)
        self.assertIn("CLEARED", first)

    def test_report_text_lists_findings(self):
        text = format_procurement_report(
            assess_hermetic_procurement(spec(seal_method=""), evidence())
        )
        self.assertIn("NOT CLEARED", text)
        self.assertIn("FINDING:", text)


if __name__ == "__main__":
    unittest.main()
