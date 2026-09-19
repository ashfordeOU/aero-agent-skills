#!/usr/bin/env python3
"""Gate 3 contract test for q2007-facility-test-report.

stdlib unittest, offline, deterministic. Run:
    python3 test_q2007_facility_test_report.py
"""

import unittest

from q2007_facility_test_report_logic import (
    REPORT_COMPLETE,
    REPORT_INCOMPLETE,
    calibration_findings,
    compile_facility_test_report,
    condition_log_gaps,
    coverage_fraction,
    missing_sections,
    ordered_samples,
    validate_campaign,
    validate_configuration_items,
)

CAMPAIGN = {"start_s": 0.0, "end_s": 600.0, "max_interval_s": 60.0}


def full_log():
    return [{"time_s": float(t), "value": 20.0} for t in range(0, 601, 60)]


def good_items():
    return [
        {"identifier": "TVAC-3 chamber, plant asset 4471", "configuration": "cold shroud fitted"},
        {"identifier": "fixture DWG-2210 issue C, serial 07", "configuration": "four-point mount"},
    ]


def good_instruments():
    return [
        {"identifier": "thermocouple set TC-11", "calibration_due_s": 900.0},
        {"identifier": "vacuum gauge VG-4", "calibration_due_s": 600.0},
    ]


def good_report(**over):
    record = {
        "facility_identification": "thermal vacuum bay 3",
        "test_configuration": "specimen on cold plate, shroud at minus 170 C",
        "configuration_items": good_items(),
        "condition_log": full_log(),
        "instrument_list": good_instruments(),
    }
    record.update(over)
    return record


class TestCampaignValidation(unittest.TestCase):
    def test_good_campaign_normalizes(self):
        window = validate_campaign(CAMPAIGN)
        self.assertAlmostEqual(window["end_s"], 600.0, places=9)

    def test_end_before_start_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign({"start_s": 600.0, "end_s": 0.0, "max_interval_s": 60.0})

    def test_zero_length_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign({"start_s": 0.0, "end_s": 0.0, "max_interval_s": 60.0})

    def test_zero_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign({"start_s": 0.0, "end_s": 600.0, "max_interval_s": 0.0})


class TestSections(unittest.TestCase):
    def test_full_report_has_no_missing_sections(self):
        self.assertEqual(missing_sections(good_report()), [])

    def test_absent_section_is_reported(self):
        record = good_report()
        del record["instrument_list"]
        self.assertEqual(missing_sections(record), ["instrument_list"])

    def test_empty_section_counts_as_missing(self):
        self.assertEqual(missing_sections(good_report(condition_log=[])), ["condition_log"])

    def test_whitespace_section_counts_as_missing(self):
        self.assertEqual(
            missing_sections(good_report(facility_identification="  ")),
            ["facility_identification"],
        )


class TestConfigurationItems(unittest.TestCase):
    def test_good_items_normalize(self):
        items = validate_configuration_items(good_items())
        self.assertEqual(len(items), 2)

    def test_item_without_an_identifier_is_rejected(self):
        items = good_items()
        items[0]["identifier"] = ""
        with self.assertRaises(ValueError):
            validate_configuration_items(items)

    def test_item_without_a_configuration_reference_is_rejected(self):
        items = good_items()
        del items[1]["configuration"]
        with self.assertRaises(ValueError):
            validate_configuration_items(items)

    def test_duplicate_identifier_is_rejected(self):
        items = good_items()
        items[1]["identifier"] = items[0]["identifier"]
        with self.assertRaises(ValueError):
            validate_configuration_items(items)

    def test_empty_item_list_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_configuration_items([])


class TestConditionLog(unittest.TestCase):
    def test_samples_are_returned_in_time_order(self):
        shuffled = [full_log()[3], full_log()[0], full_log()[7]]
        ordered = ordered_samples(shuffled, CAMPAIGN)
        self.assertEqual([s["time_s"] for s in ordered], [0.0, 180.0, 420.0])

    def test_sample_outside_the_window_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_samples([{"time_s": 900.0, "value": 20.0}], CAMPAIGN)

    def test_a_full_log_has_no_gaps(self):
        self.assertEqual(condition_log_gaps(full_log(), CAMPAIGN), [])

    def test_a_sample_exactly_one_interval_later_is_not_a_gap(self):
        log = [{"time_s": 0.0, "value": 20.0}, {"time_s": 60.0, "value": 20.0}]
        window = {"start_s": 0.0, "end_s": 60.0, "max_interval_s": 60.0}
        self.assertEqual(condition_log_gaps(log, window), [])

    def test_a_late_first_sample_is_a_leading_gap(self):
        log = [s for s in full_log() if s["time_s"] >= 180.0]
        gaps = condition_log_gaps(log, CAMPAIGN)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["to_s"], 180.0, places=9)

    def test_an_early_last_sample_is_a_trailing_gap(self):
        log = [s for s in full_log() if s["time_s"] <= 420.0]
        gaps = condition_log_gaps(log, CAMPAIGN)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["from_s"], 420.0, places=9)

    def test_a_dense_burst_still_leaves_the_rest_uncovered(self):
        log = [{"time_s": float(t), "value": 20.0} for t in range(0, 31, 2)]
        gaps = condition_log_gaps(log, CAMPAIGN)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["from_s"], 30.0, places=9)

    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(coverage_fraction(full_log(), CAMPAIGN), 1.0, places=9)

    def test_a_burst_log_reports_a_small_coverage_fraction(self):
        log = [{"time_s": float(t), "value": 20.0} for t in range(0, 31, 2)]
        self.assertAlmostEqual(coverage_fraction(log, CAMPAIGN), 0.15, places=9)


class TestCalibration(unittest.TestCase):
    def test_certificates_valid_to_the_campaign_end_have_no_findings(self):
        self.assertEqual(calibration_findings(good_instruments(), CAMPAIGN), [])

    def test_a_certificate_lapsing_mid_campaign_is_a_finding(self):
        instruments = good_instruments()
        instruments[0]["calibration_due_s"] = 300.0
        self.assertEqual(len(calibration_findings(instruments, CAMPAIGN)), 1)

    def test_an_unnamed_instrument_is_rejected(self):
        instruments = good_instruments()
        instruments[0]["identifier"] = " "
        with self.assertRaises(ValueError):
            calibration_findings(instruments, CAMPAIGN)

    def test_an_empty_instrument_list_is_rejected(self):
        with self.assertRaises(ValueError):
            calibration_findings([], CAMPAIGN)


class TestFullReport(unittest.TestCase):
    def test_a_complete_record_is_complete(self):
        report = compile_facility_test_report(good_report(), CAMPAIGN)
        self.assertEqual(report["verdict"], REPORT_COMPLETE)
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["coverage_fraction"], 1.0, places=9)

    def test_a_missing_section_is_a_finding(self):
        record = good_report()
        del record["test_configuration"]
        report = compile_facility_test_report(record, CAMPAIGN)
        self.assertEqual(report["verdict"], REPORT_INCOMPLETE)
        self.assertEqual(report["missing_sections"], ["test_configuration"])

    def test_an_uncovered_stretch_is_a_finding(self):
        log = [s for s in full_log() if s["time_s"] <= 300.0]
        report = compile_facility_test_report(good_report(condition_log=log), CAMPAIGN)
        self.assertEqual(report["verdict"], REPORT_INCOMPLETE)
        self.assertEqual(len(report["condition_log_gaps"]), 1)

    def test_a_lapsed_certificate_is_a_finding(self):
        instruments = good_instruments()
        instruments[1]["calibration_due_s"] = 120.0
        report = compile_facility_test_report(
            good_report(instrument_list=instruments), CAMPAIGN
        )
        self.assertEqual(len(report["calibration_findings"]), 1)

    def test_an_empty_condition_log_is_a_missing_section_not_a_crash(self):
        report = compile_facility_test_report(good_report(condition_log=[]), CAMPAIGN)
        self.assertEqual(report["missing_sections"], ["condition_log"])
        self.assertAlmostEqual(report["coverage_fraction"], 0.0, places=9)

    def test_report_propagates_a_duplicate_item_error(self):
        items = good_items()
        items[1]["identifier"] = items[0]["identifier"]
        with self.assertRaises(ValueError):
            compile_facility_test_report(good_report(configuration_items=items), CAMPAIGN)


if __name__ == "__main__":
    unittest.main()
