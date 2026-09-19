"""Contract test for the radiation analysis report deliverable leaf."""

import unittest

from q6015_radiation_analysis_report_deliverable_logic import (
    FINDING_ENTRY_NO_MARGIN,
    FINDING_ENTRY_WITHOUT_SECTION,
    FINDING_EVIDENCE_AFTER_REPORT,
    FINDING_NO_EVIDENCE,
    FINDING_PLACEHOLDER_EVIDENCE,
    FINDING_SECTION_MISSING,
    FINDING_SHORTFALL_NO_DECISION,
    REQUIRED_SECTIONS,
    assess_radiation_analysis_report,
    entry_findings,
    is_placeholder_reference,
    margin_meets_requirement,
    missing_required_sections,
    validate_entry,
    validate_evidence,
    validate_report,
    worst_margin_ratio,
)

REPORT_DATE = "2026-06-30"


def evidence(**kw):
    record = {
        "reference": "RAD-TR-201",
        "test_date": "2026-03-04",
        "facility": "proton beam line",
    }
    record.update(kw)
    return record


def entry(part_id="U1", effect="total-ionising-dose", **kw):
    record = {
        "part_id": part_id,
        "effect": effect,
        "margin": 3.0,
        "margin_requirement": 2.0,
        "evidence": evidence(),
    }
    record.update(kw)
    return record


def report(**kw):
    record = {
        "report_date": REPORT_DATE,
        "sections": list(REQUIRED_SECTIONS),
        "entries": [
            entry("U1", "total-ionising-dose"),
            entry("U1", "single-event"),
            entry("U2", "displacement-damage"),
        ],
    }
    record.update(kw)
    return record


class TestPlaceholders(unittest.TestCase):
    def test_tbd_is_a_placeholder(self):
        self.assertTrue(is_placeholder_reference("TBD"))

    def test_dash_is_a_placeholder(self):
        self.assertTrue(is_placeholder_reference(" - "))

    def test_none_is_a_placeholder(self):
        self.assertTrue(is_placeholder_reference(None))

    def test_a_real_reference_is_not(self):
        self.assertFalse(is_placeholder_reference("RAD-TR-201"))

    def test_non_string_reference_raises(self):
        with self.assertRaises(ValueError):
            is_placeholder_reference(42)


class TestEntryValidation(unittest.TestCase):
    def test_valid_entry_normalizes_with_a_label(self):
        record = validate_entry(entry())
        self.assertEqual(record["label"], "U1/total-ionising-dose")

    def test_unknown_effect_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry("U1", "sunburn"))

    def test_unknown_mitigation_decision_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry("U1", mitigation_decision="hope"))

    def test_non_positive_requirement_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry("U1", margin_requirement=0.0))

    def test_malformed_test_date_raises(self):
        with self.assertRaises(ValueError):
            validate_entry(entry("U1", evidence=evidence(test_date="4 March 2026")))

    def test_blank_facility_raises(self):
        with self.assertRaises(ValueError):
            validate_evidence({"reference": "R", "facility": "  "}, "U1/x")

    def test_absent_evidence_normalizes_to_none(self):
        self.assertIsNone(validate_evidence(None, "U1/x"))


class TestReportValidation(unittest.TestCase):
    def test_valid_report_normalizes(self):
        normalized = validate_report(report())
        self.assertEqual(len(normalized["entries"]), 3)

    def test_unknown_section_raises(self):
        with self.assertRaises(ValueError):
            validate_report(report(sections=["executive-poetry"]))

    def test_duplicate_section_raises(self):
        with self.assertRaises(ValueError):
            validate_report(
                report(sections=list(REQUIRED_SECTIONS) + ["mitigation-decisions"])
            )

    def test_duplicate_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_report(
                report(entries=[entry("U1"), entry("U1")])
            )

    def test_empty_entries_raises(self):
        with self.assertRaises(ValueError):
            validate_report(report(entries=[]))

    def test_missing_report_date_raises(self):
        record = report()
        del record["report_date"]
        with self.assertRaises(ValueError):
            validate_report(record)


class TestSectionCoverage(unittest.TestCase):
    def test_full_report_is_missing_no_sections(self):
        self.assertEqual(missing_required_sections(report()), [])

    def test_dropped_section_is_reported(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "radiation-test-evidence"]
        self.assertEqual(
            missing_required_sections(report(sections=sections)),
            ["radiation-test-evidence"],
        )

    def test_optional_section_is_accepted(self):
        sections = list(REQUIRED_SECTIONS) + ["open-actions"]
        self.assertEqual(missing_required_sections(report(sections=sections)), [])


class TestEntryFindings(unittest.TestCase):
    def test_a_complete_entry_has_no_findings(self):
        self.assertEqual(
            entry_findings(entry(), REQUIRED_SECTIONS, REPORT_DATE), []
        )

    def test_entry_without_a_margin_is_a_finding(self):
        findings = entry_findings(
            entry("U1", margin=None), REQUIRED_SECTIONS, REPORT_DATE
        )
        self.assertIn(
            "%s:U1/total-ionising-dose" % FINDING_ENTRY_NO_MARGIN, findings
        )

    def test_margin_exactly_at_requirement_needs_no_decision(self):
        findings = entry_findings(
            entry("U1", margin=2.0), REQUIRED_SECTIONS, REPORT_DATE
        )
        self.assertEqual(findings, [])

    def test_shortfall_without_a_decision_is_a_finding(self):
        findings = entry_findings(
            entry("U1", margin=1.1), REQUIRED_SECTIONS, REPORT_DATE
        )
        self.assertIn(
            "%s:U1/total-ionising-dose" % FINDING_SHORTFALL_NO_DECISION, findings
        )

    def test_shortfall_with_a_decision_is_accepted(self):
        findings = entry_findings(
            entry("U1", margin=1.1, mitigation_decision="shielding-added"),
            REQUIRED_SECTIONS,
            REPORT_DATE,
        )
        self.assertEqual(findings, [])

    def test_missing_evidence_reference_is_a_finding(self):
        findings = entry_findings(
            entry("U1", evidence=None), REQUIRED_SECTIONS, REPORT_DATE
        )
        self.assertIn("%s:U1/total-ionising-dose" % FINDING_NO_EVIDENCE, findings)

    def test_placeholder_evidence_reference_is_its_own_finding(self):
        findings = entry_findings(
            entry("U1", evidence=evidence(reference="TBD")),
            REQUIRED_SECTIONS,
            REPORT_DATE,
        )
        self.assertIn(
            "%s:U1/total-ionising-dose" % FINDING_PLACEHOLDER_EVIDENCE, findings
        )

    def test_evidence_without_a_date_is_a_finding(self):
        findings = entry_findings(
            entry("U1", evidence={"reference": "RAD-TR-201"}),
            REQUIRED_SECTIONS,
            REPORT_DATE,
        )
        self.assertIn("%s:U1/total-ionising-dose" % FINDING_NO_EVIDENCE, findings)

    def test_evidence_dated_after_the_report_is_a_finding(self):
        findings = entry_findings(
            entry("U1", evidence=evidence(test_date="2026-08-01")),
            REQUIRED_SECTIONS,
            REPORT_DATE,
        )
        self.assertIn(
            "%s:U1/total-ionising-dose" % FINDING_EVIDENCE_AFTER_REPORT, findings
        )

    def test_entry_whose_section_is_absent_is_a_finding(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "single-event-analysis"]
        findings = entry_findings(
            entry("U1", "single-event"), sections, REPORT_DATE
        )
        self.assertIn(
            "%s:U1/single-event" % FINDING_ENTRY_WITHOUT_SECTION, findings
        )

    def test_non_sequence_sections_raises(self):
        with self.assertRaises(ValueError):
            entry_findings(entry(), 7, REPORT_DATE)


class TestMarginHelpers(unittest.TestCase):
    def test_margin_at_requirement_is_met(self):
        self.assertTrue(margin_meets_requirement(2.0, 2.0))

    def test_margin_under_requirement_is_not_met(self):
        self.assertFalse(margin_meets_requirement(1.5, 2.0))

    def test_worst_ratio_is_the_lowest_graded_entry(self):
        ratio = worst_margin_ratio([entry("U1"), entry("U2", margin=1.0)])
        self.assertAlmostEqual(ratio, 0.5, places=9)

    def test_worst_ratio_is_none_when_nothing_is_graded(self):
        self.assertIsNone(worst_margin_ratio([entry("U1", margin=None)]))


class TestAssessment(unittest.TestCase):
    def test_a_complete_report_is_compliant(self):
        result = assess_radiation_analysis_report(report())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["section_completeness_ratio"], 1.0, places=9)
        self.assertAlmostEqual(result["entry_completeness_ratio"], 1.0, places=9)

    def test_a_missing_section_appears_as_a_finding(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "mitigation-decisions"]
        result = assess_radiation_analysis_report(report(sections=sections))
        self.assertIn(
            "%s:mitigation-decisions" % FINDING_SECTION_MISSING, result["findings"]
        )
        self.assertFalse(result["compliant"])

    def test_incomplete_entries_are_listed(self):
        entries = [entry("U1"), entry("U2", margin=1.0)]
        result = assess_radiation_analysis_report(report(entries=entries))
        self.assertEqual(
            result["incomplete_entry_labels"], ["U2/total-ionising-dose"]
        )

    def test_entry_completeness_ratio_counts_clean_entries(self):
        entries = [entry("U1"), entry("U2", margin=1.0)]
        result = assess_radiation_analysis_report(report(entries=entries))
        self.assertAlmostEqual(result["entry_completeness_ratio"], 0.5, places=9)

    def test_worst_margin_ratio_is_reported(self):
        entries = [entry("U1"), entry("U2", margin=1.0)]
        result = assess_radiation_analysis_report(report(entries=entries))
        self.assertAlmostEqual(result["worst_margin_ratio"], 0.5, places=9)

    def test_placeholder_evidence_fails_the_report(self):
        entries = [entry("U1", evidence=evidence(reference="to-be-determined"))]
        result = assess_radiation_analysis_report(report(entries=entries))
        self.assertFalse(result["compliant"])

    def test_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            assess_radiation_analysis_report(["sections"])


if __name__ == "__main__":
    unittest.main()
