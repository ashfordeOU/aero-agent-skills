#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-emission-purpose.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_emission_purpose.py
"""

import unittest

from e2007_radiated_electric_emission_purpose_logic import (
    CATEGORY_AT_LIMIT,
    CATEGORY_EXCEEDANCE,
    CATEGORY_WITHIN,
    DEFAULT_METHOD_BAND_HZ,
    EMISSION_SOURCES,
    POLARIZATIONS,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_radiated_emission_objective,
    categorize_point,
    governing_emitter,
    grade_scan,
    missing_scan_pairs,
    normalize_emission_source,
    normalize_polarization,
    point_margin_db,
    scan_band_coverage,
    validate_field_scan,
    validate_method_band,
)


def clean_scan():
    return [
        {"frequency_hz": 30.0e6, "level_dbuv_m": 24.0, "limit_dbuv_m": 50.0},
        {"frequency_hz": 200.0e6, "level_dbuv_m": 28.0, "limit_dbuv_m": 54.0},
        {"frequency_hz": 2.0e9, "level_dbuv_m": 33.0, "limit_dbuv_m": 60.0},
        {"frequency_hz": 18.0e9, "level_dbuv_m": 41.0, "limit_dbuv_m": 66.0},
    ]


def full_record():
    return dict(
        (source, dict((plane, clean_scan()) for plane in POLARIZATIONS))
        for source in EMISSION_SOURCES
    )


class TestMethodBand(unittest.TestCase):
    def test_default_band_validates(self):
        low, high = validate_method_band()
        self.assertAlmostEqual(low, DEFAULT_METHOD_BAND_HZ[0], places=9)
        self.assertAlmostEqual(high, DEFAULT_METHOD_BAND_HZ[1], places=9)

    def test_declared_band_is_returned_as_floats(self):
        low, high = validate_method_band((30.0e6, 1.0e9))
        self.assertAlmostEqual(low, 30.0e6, places=9)
        self.assertAlmostEqual(high, 1.0e9, places=9)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((18.0e9, 30.0e6))

    def test_zero_low_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((0.0, 18.0e9))

    def test_collapsed_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((1.0e9, 1.0e9))

    def test_non_pair_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band(1.0e9)


class TestSourceAndPolarization(unittest.TestCase):
    def test_every_recognized_source_normalizes(self):
        for source in EMISSION_SOURCES:
            self.assertEqual(normalize_emission_source(source.upper()), source)

    def test_unrecognized_source_rejected(self):
        with self.assertRaises(ValueError):
            normalize_emission_source("power-input-lead")

    def test_non_string_source_rejected(self):
        with self.assertRaises(ValueError):
            normalize_emission_source(3)

    def test_every_recognized_polarization_normalizes(self):
        for plane in POLARIZATIONS:
            self.assertEqual(normalize_polarization("  %s  " % plane.upper()), plane)

    def test_unrecognized_polarization_rejected(self):
        with self.assertRaises(ValueError):
            normalize_polarization("circular")


class TestScanValidation(unittest.TestCase):
    def test_clean_scan_normalizes(self):
        scan = validate_field_scan(clean_scan())
        self.assertEqual(len(scan), 4)
        self.assertAlmostEqual(scan[0]["level_dbuv_m"], 24.0, places=9)

    def test_empty_scan_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_scan([])

    def test_non_increasing_frequencies_rejected(self):
        points = clean_scan()
        points[2]["frequency_hz"] = points[1]["frequency_hz"]
        with self.assertRaises(ValueError):
            validate_field_scan(points)

    def test_missing_limit_rejected(self):
        points = clean_scan()
        del points[1]["limit_dbuv_m"]
        with self.assertRaises(ValueError):
            validate_field_scan(points)

    def test_boolean_level_rejected(self):
        points = clean_scan()
        points[0]["level_dbuv_m"] = True
        with self.assertRaises(ValueError):
            validate_field_scan(points)

    def test_non_positive_frequency_rejected(self):
        points = clean_scan()
        points[0]["frequency_hz"] = 0.0
        with self.assertRaises(ValueError):
            validate_field_scan(points)


class TestBandCoverage(unittest.TestCase):
    def test_full_scan_covers_the_band(self):
        coverage = scan_band_coverage(clean_scan())
        self.assertTrue(coverage["covers_band"])

    def test_scan_stopping_early_misses_the_upper_edge(self):
        coverage = scan_band_coverage(clean_scan()[:-1])
        self.assertTrue(coverage["reaches_low_edge"])
        self.assertFalse(coverage["reaches_high_edge"])

    def test_scan_starting_late_misses_the_lower_edge(self):
        coverage = scan_band_coverage(clean_scan()[1:])
        self.assertFalse(coverage["reaches_low_edge"])

    def test_edge_slack_absorbs_a_representation_difference(self):
        points = clean_scan()
        points[0]["frequency_hz"] = 30.0e6 * (1.0 + 1e-12)
        coverage = scan_band_coverage(points)
        self.assertTrue(coverage["reaches_low_edge"])

    def test_out_of_range_slack_rejected(self):
        with self.assertRaises(ValueError):
            scan_band_coverage(clean_scan(), rel_tol=1.0)


class TestCategorization(unittest.TestCase):
    def test_comfortable_point_is_within_limit(self):
        self.assertEqual(categorize_point(validate_field_scan(clean_scan())[0]),
                         CATEGORY_WITHIN)

    def test_point_on_the_limit_is_at_limit(self):
        point = {"frequency_hz": 1.0e9, "level_dbuv_m": 55.0, "limit_dbuv_m": 55.0}
        self.assertEqual(categorize_point(point), CATEGORY_AT_LIMIT)

    def test_point_above_the_limit_is_an_exceedance(self):
        point = {"frequency_hz": 1.0e9, "level_dbuv_m": 61.0, "limit_dbuv_m": 55.0}
        self.assertEqual(categorize_point(point), CATEGORY_EXCEEDANCE)

    def test_margin_is_limit_minus_level(self):
        point = {"frequency_hz": 1.0e9, "level_dbuv_m": 42.0, "limit_dbuv_m": 55.0}
        self.assertAlmostEqual(point_margin_db(point), 13.0, places=9)

    def test_negative_tolerance_rejected(self):
        point = {"frequency_hz": 1.0e9, "level_dbuv_m": 55.0, "limit_dbuv_m": 55.0}
        with self.assertRaises(ValueError):
            categorize_point(point, tol_db=-1.0)


class TestScanGrading(unittest.TestCase):
    def test_clean_scan_grades_within_limits(self):
        report = grade_scan(EMISSION_SOURCES[0], POLARIZATIONS[0], clean_scan())
        self.assertTrue(report["within_limits"])
        self.assertEqual(report["counts"][CATEGORY_EXCEEDANCE], 0)

    def test_worst_case_is_the_smallest_margin(self):
        points = clean_scan()
        points[1]["level_dbuv_m"] = 52.0
        report = grade_scan(EMISSION_SOURCES[1], POLARIZATIONS[1], points)
        self.assertAlmostEqual(report["worst_case"]["margin_db"], 2.0, places=9)
        self.assertAlmostEqual(report["worst_case"]["frequency_hz"], 200.0e6, places=9)

    def test_tie_on_margin_breaks_on_the_lower_frequency(self):
        points = clean_scan()
        points[1]["level_dbuv_m"] = 44.0
        points[2]["level_dbuv_m"] = 50.0
        report = grade_scan(EMISSION_SOURCES[0], POLARIZATIONS[0], points)
        self.assertAlmostEqual(report["worst_case"]["frequency_hz"], 200.0e6, places=9)

    def test_grading_carries_the_polarization_through(self):
        report = grade_scan(EMISSION_SOURCES[0], "HORIZONTAL", clean_scan())
        self.assertEqual(report["polarization"], "horizontal")


class TestGoverningEmitter(unittest.TestCase):
    def test_governing_scan_is_the_tightest(self):
        loose = grade_scan(EMISSION_SOURCES[0], POLARIZATIONS[0], clean_scan())
        points = clean_scan()
        points[3]["level_dbuv_m"] = 64.0
        tight = grade_scan(EMISSION_SOURCES[1], POLARIZATIONS[1], points)
        self.assertIs(governing_emitter([loose, tight]), tight)

    def test_empty_report_set_rejected(self):
        with self.assertRaises(ValueError):
            governing_emitter([])


class TestMissingPairs(unittest.TestCase):
    def test_complete_record_has_no_missing_pairs(self):
        self.assertEqual(missing_scan_pairs(full_record()), ())

    def test_single_polarization_record_reports_the_gap(self):
        record = full_record()
        del record["unit-enclosure"]["horizontal"]
        self.assertEqual(
            missing_scan_pairs(record), (("unit-enclosure", "horizontal"),)
        )

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            missing_scan_pairs([("unit-enclosure", [])])


class TestObjective(unittest.TestCase):
    def test_clean_record_demonstrates_the_objective(self):
        report = assess_radiated_emission_objective(full_record())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])

    def test_all_four_scans_are_graded_in_a_stable_order(self):
        report = assess_radiated_emission_objective(full_record())
        self.assertEqual(
            [(r["source"], r["polarization"]) for r in report["scans"]],
            [(s, p) for s in EMISSION_SOURCES for p in POLARIZATIONS],
        )

    def test_missing_cabling_scan_is_refused(self):
        record = full_record()
        del record["interconnecting-cabling"]
        with self.assertRaises(ValueError):
            assess_radiated_emission_objective(record)

    def test_missing_polarization_is_refused(self):
        record = full_record()
        del record["unit-enclosure"]["vertical"]
        with self.assertRaises(ValueError):
            assess_radiated_emission_objective(record)

    def test_empty_record_is_refused(self):
        with self.assertRaises(ValueError):
            assess_radiated_emission_objective({})

    def test_exceedance_blocks_the_objective(self):
        record = full_record()
        record["interconnecting-cabling"]["horizontal"][2]["level_dbuv_m"] = 67.0
        report = assess_radiated_emission_objective(record)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(len(report["findings"]), 1)

    def test_on_limit_point_is_a_limitation_not_a_finding(self):
        record = full_record()
        record["unit-enclosure"]["vertical"][1]["level_dbuv_m"] = 54.0
        report = assess_radiated_emission_objective(record)
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(len(report["limitations"]), 1)

    def test_short_scan_is_a_coverage_finding(self):
        record = full_record()
        record["unit-enclosure"]["horizontal"] = clean_scan()[:-1]
        report = assess_radiated_emission_objective(record)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_waived_span_downgrades_the_coverage_finding(self):
        record = full_record()
        record["unit-enclosure"]["horizontal"] = clean_scan()[:-1]
        report = assess_radiated_emission_objective(record, require_full_band=False)
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(len(report["limitations"]), 1)

    def test_narrower_declared_band_changes_the_coverage_verdict(self):
        record = full_record()
        record["unit-enclosure"]["horizontal"] = clean_scan()[:-1]
        report = assess_radiated_emission_objective(record, band=(30.0e6, 2.0e9))
        self.assertEqual(report["verdict"], VERDICT_MET)

    def test_governing_point_carries_the_smallest_margin(self):
        record = full_record()
        record["interconnecting-cabling"]["vertical"][2]["level_dbuv_m"] = 57.0
        report = assess_radiated_emission_objective(record)
        self.assertEqual(report["governing_source"], "interconnecting-cabling")
        self.assertEqual(report["governing_polarization"], "vertical")
        self.assertAlmostEqual(report["governing_point"]["margin_db"], 3.0, places=9)

    def test_duplicate_source_declaration_rejected(self):
        record = full_record()
        record["UNIT-ENCLOSURE"] = record["unit-enclosure"]
        with self.assertRaises(ValueError):
            assess_radiated_emission_objective(record)

    def test_band_is_echoed_back_on_the_report(self):
        report = assess_radiated_emission_objective(full_record())
        self.assertAlmostEqual(report["band_hz"][0], 30.0e6, places=9)
        self.assertAlmostEqual(report["band_hz"][1], 18.0e9, places=9)


if __name__ == "__main__":
    unittest.main()
