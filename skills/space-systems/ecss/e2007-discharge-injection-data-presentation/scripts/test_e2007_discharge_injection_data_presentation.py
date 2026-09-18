#!/usr/bin/env python3
"""Contract tests for the clause 5.4.13.5 discharge-injection data package."""

import unittest

from e2007_discharge_injection_data_presentation_logic import (
    DEFAULT_CALIBRATION_VALIDITY_H,
    EUT_STATUSES,
    MANDATORY_GENERATOR_FIELDS,
    amplitude_reversals,
    assess_discharge_injection_data,
    audit_calibration,
    audit_compliance_table,
    audit_test_captures,
    build_required_matrix,
    cell_key,
    coverage,
    level_key,
    status_counts,
    validate_calibration_record,
    validate_compliance_row,
    validate_generator_settings,
    validate_test_capture,
    worst_status,
)

POINTS = ["power-bundle", "signal-bundle"]
LEVELS = [1.0, 2.0, 4.0]
POLARITIES = ["positive", "negative"]


def a_settings(**overrides):
    settings = {
        "charge_voltage_kv": 4.0,
        "storage_capacitance_pf": 150.0,
        "discharge_resistance_ohm": 330.0,
        "pulses_per_polarity": 10,
        "repetition_interval_s": 1.0,
        "polarities": ["positive", "negative"],
    }
    settings.update(overrides)
    return settings


def full_captures():
    captures = []
    index = 0
    for point in POINTS:
        for level in LEVELS:
            for polarity in POLARITIES:
                index += 1
                captures.append(
                    {
                        "point": point,
                        "level_kv": level,
                        "polarity": polarity,
                        "peak_current_a": 3.0 * level,
                        "capture_id": "cap-%03d" % index,
                    }
                )
    return captures


def full_rows(status="no-effect"):
    rows = []
    for point in POINTS:
        for level in LEVELS:
            for polarity in POLARITIES:
                rows.append(
                    {
                        "point": point,
                        "level_kv": level,
                        "polarity": polarity,
                        "eut_status": status,
                    }
                )
    return rows


def a_calibration():
    return [
        {
            "timestamp_h": 10.0,
            "level_kv": 4.0,
            "peak_current_a": 12.0,
            "rise_time_ns": 0.8,
            "duration_ns": 60.0,
            "capture_id": "cal-open",
        },
        {
            "timestamp_h": 18.0,
            "level_kv": 4.0,
            "peak_current_a": 12.5,
            "rise_time_ns": 0.9,
            "duration_ns": 60.0,
            "capture_id": "cal-close",
        },
    ]


def a_package(**overrides):
    package = {
        "injection_points": list(POINTS),
        "level_ladder_kv": list(LEVELS),
        "polarities": list(POLARITIES),
        "generator_settings": a_settings(),
        "calibration_records": a_calibration(),
        "test_captures": full_captures(),
        "compliance_rows": full_rows(),
        "test_start_h": 12.0,
        "test_stop_h": 16.0,
    }
    package.update(overrides)
    return package


class KeyTests(unittest.TestCase):
    def test_level_key_quantizes_to_microvolts(self):
        self.assertEqual(level_key(4.0), 4000000)

    def test_level_key_collapses_equivalent_spellings(self):
        self.assertEqual(level_key(4.0), level_key(4.000000))

    def test_level_key_rejects_zero(self):
        with self.assertRaises(ValueError):
            level_key(0.0)

    def test_cell_key_lowercases_and_trims(self):
        self.assertEqual(cell_key("  Power-Bundle ", 2.0, "Positive"),
                         ("power-bundle", 2000000, "positive"))

    def test_cell_key_rejects_an_unknown_polarity(self):
        with self.assertRaises(ValueError):
            cell_key("power-bundle", 2.0, "bipolar")


class MatrixTests(unittest.TestCase):
    def test_matrix_size_is_the_product(self):
        self.assertEqual(len(build_required_matrix(POINTS, LEVELS, POLARITIES)), 12)

    def test_matrix_is_sorted_and_unique(self):
        matrix = build_required_matrix(POINTS, LEVELS, POLARITIES)
        self.assertEqual(matrix, sorted(set(matrix)))

    def test_repeated_point_rejected(self):
        with self.assertRaises(ValueError):
            build_required_matrix(["a", "A"], LEVELS, POLARITIES)

    def test_repeated_level_rejected(self):
        with self.assertRaises(ValueError):
            build_required_matrix(POINTS, [2.0, 2.0], POLARITIES)

    def test_empty_polarity_list_rejected(self):
        with self.assertRaises(ValueError):
            build_required_matrix(POINTS, LEVELS, [])


class GeneratorSettingsTests(unittest.TestCase):
    def test_complete_settings_report_no_gap(self):
        report = validate_generator_settings(a_settings())
        self.assertTrue(report["complete"])
        self.assertEqual(report["missing"], [])

    def test_every_mandatory_field_is_checked(self):
        for field in MANDATORY_GENERATOR_FIELDS:
            settings = a_settings()
            del settings[field]
            report = validate_generator_settings(settings)
            self.assertIn(field, report["missing"])

    def test_absent_polarities_are_reported_missing(self):
        settings = a_settings()
        del settings["polarities"]
        self.assertIn("polarities", validate_generator_settings(settings)["missing"])

    def test_blank_field_counts_as_missing(self):
        report = validate_generator_settings(a_settings(repetition_interval_s=""))
        self.assertIn("repetition_interval_s", report["missing"])

    def test_negative_capacitance_is_an_input_error(self):
        with self.assertRaises(ValueError):
            validate_generator_settings(a_settings(storage_capacitance_pf=-150.0))

    def test_non_integer_pulse_count_is_an_input_error(self):
        with self.assertRaises(ValueError):
            validate_generator_settings(a_settings(pulses_per_polarity=10.5))


class RecordValidationTests(unittest.TestCase):
    def test_capture_is_normalized_to_a_cell_key(self):
        record = validate_test_capture(full_captures()[0])
        self.assertEqual(record["key"][0], "power-bundle")

    def test_capture_without_a_peak_rejected(self):
        capture = full_captures()[0]
        del capture["peak_current_a"]
        with self.assertRaises(ValueError):
            validate_test_capture(capture)

    def test_capture_with_a_blank_identifier_rejected(self):
        capture = full_captures()[0]
        capture["capture_id"] = "  "
        with self.assertRaises(ValueError):
            validate_test_capture(capture)

    def test_compliance_row_marks_an_allowed_status(self):
        row = validate_compliance_row(full_rows()[0])
        self.assertTrue(row["within_allowed"])

    def test_compliance_row_marks_a_status_outside_the_agreed_set(self):
        row = validate_compliance_row(full_rows("damage")[0])
        self.assertFalse(row["within_allowed"])

    def test_unrecognized_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_compliance_row(full_rows("exploded")[0])

    def test_calibration_record_is_normalized(self):
        record = validate_calibration_record(a_calibration()[0])
        self.assertAlmostEqual(record["peak_current_a"], 12.0, places=9)

    def test_calibration_duration_shorter_than_the_rise_rejected(self):
        record = a_calibration()[0]
        record["duration_ns"] = 0.4
        with self.assertRaises(ValueError):
            validate_calibration_record(record)

    def test_calibration_without_a_timestamp_rejected(self):
        record = a_calibration()[0]
        del record["timestamp_h"]
        with self.assertRaises(ValueError):
            validate_calibration_record(record)


class CoverageTests(unittest.TestCase):
    def test_full_coverage_has_ratio_one(self):
        matrix = build_required_matrix(POINTS, LEVELS, POLARITIES)
        report = coverage(matrix, list(matrix))
        self.assertAlmostEqual(report["ratio"], 1.0, places=9)
        self.assertEqual(report["missing"], [])

    def test_half_coverage_is_reported_as_a_ratio(self):
        matrix = build_required_matrix(POINTS, LEVELS, POLARITIES)
        report = coverage(matrix, matrix[:6])
        self.assertAlmostEqual(report["ratio"], 0.5, places=9)
        self.assertEqual(len(report["missing"]), 6)

    def test_repeated_supply_is_a_duplicate(self):
        matrix = build_required_matrix(POINTS, LEVELS, POLARITIES)
        report = coverage(matrix, list(matrix) + [matrix[0]])
        self.assertEqual(report["duplicates"], [matrix[0]])

    def test_unplanned_supply_is_extra(self):
        matrix = build_required_matrix(POINTS, LEVELS, POLARITIES)
        report = coverage(matrix, list(matrix) + [("other-bundle", 4000000, "positive")])
        self.assertEqual(len(report["extra"]), 1)

    def test_empty_required_matrix_rejected(self):
        with self.assertRaises(ValueError):
            coverage([], [])


class StatusTests(unittest.TestCase):
    def test_counts_cover_every_recognized_status(self):
        rows = [validate_compliance_row(r) for r in full_rows()]
        counts = status_counts(rows)
        self.assertEqual(sorted(counts), sorted(EUT_STATUSES))
        self.assertEqual(counts["no-effect"], 12)

    def test_worst_status_takes_the_most_severe(self):
        rows = [validate_compliance_row(r) for r in full_rows()]
        rows.append(validate_compliance_row(full_rows("degraded")[0]))
        self.assertEqual(worst_status(rows), "degraded")

    def test_worst_status_of_an_empty_table_is_none(self):
        self.assertIsNone(worst_status([]))

    def test_allowed_statuses_can_be_widened(self):
        row = validate_compliance_row(
            full_rows("operator-recoverable")[0],
            0,
            ("no-effect", "self-recovering", "operator-recoverable"),
        )
        self.assertTrue(row["within_allowed"])


class AmplitudeTests(unittest.TestCase):
    def test_rising_peaks_have_no_reversal(self):
        captures = [validate_test_capture(c) for c in full_captures()]
        self.assertEqual(amplitude_reversals(captures), [])

    def test_a_lower_peak_at_a_higher_level_is_a_reversal(self):
        raw = full_captures()
        raw[4]["peak_current_a"] = 1.0
        captures = [validate_test_capture(c) for c in raw]
        reversals = amplitude_reversals(captures)
        self.assertEqual(len(reversals), 1)
        self.assertAlmostEqual(reversals[0]["upper_level_kv"], 4.0, places=9)
        self.assertEqual(reversals[0]["polarity"], "positive")

    def test_equal_peaks_are_not_a_reversal(self):
        raw = full_captures()
        for capture in raw:
            capture["peak_current_a"] = 6.0
        captures = [validate_test_capture(c) for c in raw]
        self.assertEqual(amplitude_reversals(captures), [])


class CalibrationTests(unittest.TestCase):
    def test_a_bracketing_calibration_has_no_finding(self):
        report = audit_calibration(a_calibration(), 12.0, 16.0)
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["within_drift"])

    def test_opening_and_closing_records_are_identified(self):
        report = audit_calibration(a_calibration(), 12.0, 16.0)
        self.assertEqual(report["opening"]["capture_id"], "cal-open")
        self.assertEqual(report["closing"]["capture_id"], "cal-close")

    def test_missing_closing_calibration_is_a_finding(self):
        records = a_calibration()[:1]
        report = audit_calibration(records, 12.0, 16.0)
        self.assertIsNone(report["closing"])
        self.assertEqual(len(report["findings"]), 1)

    def test_calibration_outside_the_validity_window_does_not_count(self):
        records = a_calibration()
        records[0]["timestamp_h"] = -100.0
        report = audit_calibration(records, 12.0, 16.0, 24.0)
        self.assertIsNone(report["opening"])

    def test_drift_exactly_at_the_allowance_is_within_it(self):
        records = a_calibration()
        records[0]["peak_current_a"] = 10.0
        records[1]["peak_current_a"] = 11.0
        report = audit_calibration(records, 12.0, 16.0, 24.0, 0.10)
        self.assertAlmostEqual(report["drift_ratio"], 1.1, places=9)
        self.assertTrue(report["within_drift"])

    def test_drift_beyond_the_allowance_is_a_finding(self):
        records = a_calibration()
        records[1]["peak_current_a"] = 20.0
        report = audit_calibration(records, 12.0, 16.0, 24.0, 0.10)
        self.assertFalse(report["within_drift"])
        self.assertEqual(len(report["findings"]), 1)

    def test_run_stop_before_its_start_rejected(self):
        with self.assertRaises(ValueError):
            audit_calibration(a_calibration(), 16.0, 12.0)

    def test_default_validity_window_is_a_day(self):
        self.assertAlmostEqual(DEFAULT_CALIBRATION_VALIDITY_H, 24.0, places=9)


class PackageAssessmentTests(unittest.TestCase):
    def test_a_complete_package_is_acceptable(self):
        report = assess_discharge_injection_data(a_package())
        self.assertTrue(report["package_acceptable"])
        self.assertEqual(report["findings"], [])

    def test_completeness_ratios_are_reported(self):
        report = assess_discharge_injection_data(a_package())
        self.assertAlmostEqual(report["capture_completeness"], 1.0, places=9)
        self.assertAlmostEqual(report["table_completeness"], 1.0, places=9)

    def test_a_missing_oscilloscope_record_is_a_finding(self):
        report = assess_discharge_injection_data(
            a_package(test_captures=full_captures()[:-1])
        )
        self.assertFalse(report["package_acceptable"])
        self.assertAlmostEqual(report["capture_completeness"], 11.0 / 12.0, places=9)

    def test_a_missing_compliance_row_is_a_finding(self):
        report = assess_discharge_injection_data(a_package(compliance_rows=full_rows()[:-2]))
        self.assertFalse(report["package_acceptable"])

    def test_incomplete_generator_settings_are_a_finding(self):
        settings = a_settings()
        del settings["discharge_resistance_ohm"]
        report = assess_discharge_injection_data(a_package(generator_settings=settings))
        self.assertFalse(report["package_acceptable"])

    def test_a_reused_capture_identifier_is_a_finding(self):
        captures = full_captures()
        captures[1]["capture_id"] = captures[0]["capture_id"]
        report = assess_discharge_injection_data(a_package(test_captures=captures))
        self.assertFalse(report["package_acceptable"])

    def test_a_damaging_status_is_a_finding(self):
        rows = full_rows()
        rows[3]["eut_status"] = "damage"
        report = assess_discharge_injection_data(a_package(compliance_rows=rows))
        self.assertFalse(report["package_acceptable"])
        self.assertEqual(report["compliance_table"]["worst_status"], "damage")

    def test_an_unplanned_capture_is_a_limitation_not_a_finding(self):
        captures = full_captures()
        captures.append(
            {
                "point": "spare-bundle",
                "level_kv": 4.0,
                "polarity": "positive",
                "peak_current_a": 12.0,
                "capture_id": "cap-extra",
            }
        )
        report = assess_discharge_injection_data(a_package(test_captures=captures))
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["limitations"])

    def test_an_amplitude_reversal_is_a_limitation(self):
        captures = full_captures()
        captures[4]["peak_current_a"] = 1.0
        report = assess_discharge_injection_data(a_package(test_captures=captures))
        self.assertEqual(report["findings"], [])
        self.assertTrue(
            any("lower peak current" in note for note in report["limitations"])
        )

    def test_a_missing_package_field_rejected(self):
        package = a_package()
        del package["calibration_records"]
        with self.assertRaises(ValueError):
            assess_discharge_injection_data(package)

    def test_package_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_discharge_injection_data([1, 2, 3])

    def test_a_duplicated_compliance_row_is_a_finding(self):
        rows = full_rows()
        rows.append(dict(rows[0]))
        report = assess_discharge_injection_data(a_package(compliance_rows=rows))
        self.assertFalse(report["package_acceptable"])


if __name__ == "__main__":
    unittest.main()
