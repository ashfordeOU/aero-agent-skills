"""Contract tests for the clause 5.6.3.2 test-report grading logic."""

import unittest
from datetime import date

from q20_test_reports_logic import (
    LIMIT_TOLERANCE,
    MANDATORY_APPROVAL_ROLES,
    REQUIRED_SECTIONS,
    approval_findings,
    assess_test_report,
    conclusion_findings,
    data_completeness,
    discrepancy_findings,
    grade_measurement,
    normalise_identifier,
    parse_iso_date,
    results_outcome,
    section_findings,
    validate_report,
)

PARAMETERS = [
    {"id": "insulation-resistance", "unit": "mohm", "minimum": 100.0},
    {"id": "chamber-pressure", "unit": "mbar", "maximum": 1.0e-5},
    {"id": "dwell-duration", "unit": "h", "minimum": 6.0, "maximum": 8.0},
]

GOOD_REPORT = {
    "identification": "tr-tv-001 rev a",
    "article_configuration": "fm-01 as-built list 07",
    "procedure_reference": "tpro-tv-001 rev b",
    "test_conditions": "thermal vacuum, 8 cycles",
    "conclusion": "pass",
    "test_end_date": "2026-04-10",
    "issue_date": "2026-04-18",
    "results": [
        {"parameter": "insulation-resistance", "value": 250.0, "unit": "mohm"},
        {"parameter": "chamber-pressure", "value": 4.0e-6, "unit": "mbar"},
        {"parameter": "dwell-duration", "value": 6.5, "unit": "h"},
    ],
    "observed_anomalies": [],
    "discrepancies": [],
    "approvals": [
        {"role": "test-responsible", "date": "2026-04-14"},
        {"role": "product-assurance", "date": "2026-04-16"},
    ],
}


def report(**overrides):
    """Return a copy of the good report with overrides applied."""
    item = dict(GOOD_REPORT)
    item["results"] = [dict(entry) for entry in GOOD_REPORT["results"]]
    item["approvals"] = [dict(entry) for entry in GOOD_REPORT["approvals"]]
    item.update(overrides)
    return item


class HelperTests(unittest.TestCase):
    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" MOhm ", "unit"), "mohm")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("", "unit")

    def test_iso_date_parsed(self):
        self.assertEqual(parse_iso_date("2026-04-10", "d"), date(2026, 4, 10))

    def test_bad_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-13-01", "d")


class ValidationTests(unittest.TestCase):
    def test_good_report_validates(self):
        record = validate_report(report())
        self.assertEqual(record["issue_date"], date(2026, 4, 18))
        self.assertEqual(len(record["results"]), 3)

    def test_issue_before_test_end_rejected(self):
        with self.assertRaises(ValueError):
            validate_report(report(issue_date="2026-04-01"))

    def test_duplicate_measured_parameter_rejected(self):
        extra = GOOD_REPORT["results"] + [
            {"parameter": "dwell-duration", "value": 7.0, "unit": "h"}
        ]
        with self.assertRaises(ValueError):
            validate_report(report(results=extra))

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_report(
                report(results=[{"parameter": "dwell-duration", "value": "7", "unit": "h"}])
            )

    def test_not_measured_without_justification_rejected(self):
        with self.assertRaises(ValueError):
            validate_report(
                report(results=[{"parameter": "dwell-duration", "not_measured": True}])
            )

    def test_not_measured_with_justification_accepted(self):
        record = validate_report(
            report(
                results=[
                    {
                        "parameter": "dwell-duration",
                        "not_measured": True,
                        "justification": "chamber logger failed, run repeated",
                    }
                ]
            )
        )
        self.assertTrue(record["results"]["dwell-duration"]["not_measured"])

    def test_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            validate_report("tr-tv-001")


class SectionTests(unittest.TestCase):
    def test_required_sections_are_five(self):
        self.assertEqual(len(REQUIRED_SECTIONS), 5)

    def test_complete_report_has_no_section_finding(self):
        self.assertEqual(section_findings(validate_report(report())), [])

    def test_missing_section_is_a_finding(self):
        record = validate_report(report(article_configuration=None))
        self.assertEqual(
            section_findings(record),
            ["report section 'article_configuration' is absent or blank"],
        )

    def test_blank_section_is_a_finding(self):
        record = validate_report(report(test_conditions="   "))
        self.assertEqual(len(section_findings(record)), 1)


class CompletenessTests(unittest.TestCase):
    def test_full_completeness_is_one(self):
        result = data_completeness(validate_report(report()), PARAMETERS)
        self.assertAlmostEqual(result["completeness_ratio"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_missing_parameter_lowers_the_ratio(self):
        thin = [dict(GOOD_REPORT["results"][0])]
        result = data_completeness(validate_report(report(results=thin)), PARAMETERS)
        self.assertAlmostEqual(result["completeness_ratio"], 1.0 / 3.0, places=9)
        self.assertEqual(result["missing"], ["chamber-pressure", "dwell-duration"])

    def test_wrong_unit_is_not_counted_as_recorded(self):
        swapped = [dict(GOOD_REPORT["results"][0], unit="ohm")] + [
            dict(entry) for entry in GOOD_REPORT["results"][1:]
        ]
        result = data_completeness(validate_report(report(results=swapped)), PARAMETERS)
        self.assertEqual(result["wrong_unit"], ["insulation-resistance"])
        self.assertAlmostEqual(result["completeness_ratio"], 2.0 / 3.0, places=9)

    def test_undemanded_result_is_reported(self):
        extra = [dict(e) for e in GOOD_REPORT["results"]] + [
            {"parameter": "ambient-humidity", "value": 40.0, "unit": "pct"}
        ]
        result = data_completeness(validate_report(report(results=extra)), PARAMETERS)
        self.assertEqual(result["extra"], ["ambient-humidity"])

    def test_empty_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            data_completeness(validate_report(report()), [])

    def test_inverted_limit_band_rejected(self):
        with self.assertRaises(ValueError):
            data_completeness(
                validate_report(report()),
                [{"id": "dwell-duration", "unit": "h", "minimum": 9.0, "maximum": 6.0}],
            )


class MeasurementGradingTests(unittest.TestCase):
    def test_value_inside_band_is_within(self):
        self.assertEqual(grade_measurement(7.0, 6.0, 8.0), "within")

    def test_value_under_minimum_is_below(self):
        self.assertEqual(grade_measurement(5.0, 6.0, 8.0), "below")

    def test_value_over_maximum_is_above(self):
        self.assertEqual(grade_measurement(9.0, 6.0, 8.0), "above")

    def test_value_on_the_limit_counts_as_within(self):
        self.assertEqual(grade_measurement(8.0, 6.0, 8.0), "within")

    def test_limit_tolerance_absorbs_representation_error(self):
        self.assertAlmostEqual(LIMIT_TOLERANCE, 1e-9, places=12)
        self.assertEqual(grade_measurement(8.0 + LIMIT_TOLERANCE / 2.0, None, 8.0), "within")

    def test_unlimited_measurement_rejected(self):
        with self.assertRaises(ValueError):
            grade_measurement(7.0)

    def test_non_numeric_measurement_rejected(self):
        with self.assertRaises(ValueError):
            grade_measurement("7.0", 6.0, 8.0)


class OutcomeTests(unittest.TestCase):
    def test_all_within_gives_pass(self):
        outcome = results_outcome(validate_report(report()), PARAMETERS)
        self.assertEqual(outcome["measured_outcome"], "pass")

    def test_one_out_of_limit_gives_fail(self):
        bad = [dict(e) for e in GOOD_REPORT["results"]]
        bad[2]["value"] = 9.0
        outcome = results_outcome(validate_report(report(results=bad)), PARAMETERS)
        self.assertEqual(outcome["measured_outcome"], "fail")
        self.assertEqual(outcome["out_of_limit"], ["dwell-duration"])

    def test_parameter_without_limits_is_marked_unlimited(self):
        outcome = results_outcome(
            validate_report(report()),
            [{"id": "dwell-duration", "unit": "h"}],
        )
        self.assertEqual(outcome["graded"]["dwell-duration"], "unlimited")


class DiscrepancyTests(unittest.TestCase):
    def test_no_anomalies_gives_no_finding(self):
        self.assertEqual(discrepancy_findings(validate_report(report())), [])

    def test_unwritten_anomaly_is_a_finding(self):
        record = validate_report(report(observed_anomalies=["heater-trip"]))
        self.assertIn("no discrepancy entry", discrepancy_findings(record)[0])

    def test_discrepancy_without_reference_is_a_finding(self):
        record = validate_report(
            report(
                observed_anomalies=["heater-trip"],
                discrepancies=[{"anomaly": "heater-trip", "disposition": "use-as-is"}],
            )
        )
        self.assertIn("no nonconformance reference", discrepancy_findings(record)[0])

    def test_discrepancy_without_disposition_is_a_finding(self):
        record = validate_report(
            report(
                observed_anomalies=["heater-trip"],
                discrepancies=[{"anomaly": "heater-trip", "nonconformance_reference": "ncr-441"}],
            )
        )
        self.assertIn("no disposition", discrepancy_findings(record)[0])

    def test_duplicate_discrepancy_rejected(self):
        with self.assertRaises(ValueError):
            validate_report(
                report(
                    discrepancies=[
                        {"anomaly": "heater-trip", "nonconformance_reference": "ncr-441",
                         "disposition": "repair"},
                        {"anomaly": "heater-trip", "nonconformance_reference": "ncr-442",
                         "disposition": "repair"},
                    ]
                )
            )


class ApprovalTests(unittest.TestCase):
    def test_mandatory_roles(self):
        self.assertEqual(MANDATORY_APPROVAL_ROLES, ("test-responsible", "product-assurance"))

    def test_complete_approvals_give_no_finding(self):
        self.assertEqual(approval_findings(validate_report(report())), [])

    def test_missing_role_is_a_finding(self):
        record = validate_report(
            report(approvals=[{"role": "test-responsible", "date": "2026-04-14"}])
        )
        self.assertEqual(approval_findings(record), ["missing product-assurance approval"])

    def test_signature_before_the_test_ended_is_a_finding(self):
        record = validate_report(
            report(
                approvals=[
                    {"role": "test-responsible", "date": "2026-04-01"},
                    {"role": "product-assurance", "date": "2026-04-16"},
                ]
            )
        )
        self.assertIn("predates the end of the test", approval_findings(record)[0])

    def test_signature_after_issue_is_a_finding(self):
        record = validate_report(
            report(
                approvals=[
                    {"role": "test-responsible", "date": "2026-04-14"},
                    {"role": "product-assurance", "date": "2026-04-25"},
                ]
            )
        )
        self.assertIn("after the report issued", approval_findings(record)[0])


class ConclusionTests(unittest.TestCase):
    def test_pass_with_clean_results_is_accepted(self):
        record = validate_report(report())
        outcome = results_outcome(record, PARAMETERS)
        self.assertEqual(conclusion_findings(record, outcome), [])

    def test_pass_with_out_of_limit_value_is_a_finding(self):
        bad = [dict(e) for e in GOOD_REPORT["results"]]
        bad[1]["value"] = 1.0e-3
        record = validate_report(report(results=bad))
        outcome = results_outcome(record, PARAMETERS)
        self.assertIn("concludes pass", conclusion_findings(record, outcome)[0])

    def test_pass_with_open_discrepancy_is_a_finding(self):
        record = validate_report(
            report(
                observed_anomalies=["heater-trip"],
                discrepancies=[{"anomaly": "heater-trip", "nonconformance_reference": "ncr-441"}],
            )
        )
        outcome = results_outcome(record, PARAMETERS)
        self.assertIn("undispositioned", conclusion_findings(record, outcome)[0])

    def test_unrecognised_conclusion_is_a_finding(self):
        record = validate_report(report(conclusion="mostly fine"))
        outcome = results_outcome(record, PARAMETERS)
        self.assertIn("neither pass nor fail", conclusion_findings(record, outcome)[0])


class AssessmentTests(unittest.TestCase):
    def test_clean_report_is_approved(self):
        result = assess_test_report(report(), PARAMETERS)
        self.assertEqual(result["verdict"], "approved")
        self.assertAlmostEqual(result["completeness_ratio"], 1.0, places=9)

    def test_incomplete_report_is_returned(self):
        thin = [dict(GOOD_REPORT["results"][0])]
        result = assess_test_report(report(results=thin), PARAMETERS)
        self.assertEqual(result["verdict"], "returned-for-correction")
        self.assertTrue(result["findings"])

    def test_counts_are_reported_for_evidence(self):
        result = assess_test_report(report(), PARAMETERS)
        self.assertEqual(result["required_count"], 3)
        self.assertEqual(result["recorded_count"], 3)


if __name__ == "__main__":
    unittest.main()
