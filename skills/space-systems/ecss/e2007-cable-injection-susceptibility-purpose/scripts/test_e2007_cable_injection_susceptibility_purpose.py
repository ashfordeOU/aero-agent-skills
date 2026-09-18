#!/usr/bin/env python3
"""Gate 3 contract test for e2007-cable-injection-susceptibility-purpose.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_cable_injection_susceptibility_purpose.py
"""

import math
import unittest

from e2007_cable_injection_susceptibility_purpose_logic import (
    AT_LIMIT,
    DRIVE_SHORTFALL,
    MEETS_LIMIT,
    NOT_SUSCEPTIBLE,
    SUSCEPTIBLE_ABOVE_LIMIT,
    SUSCEPTIBLE_AT_OR_BELOW_LIMIT,
    VERDICT_DEMONSTRATED,
    VERDICT_NOT_DEMONSTRATED,
    VERDICT_WITH_LIMITATIONS,
    assess_cable_injection_aim,
    categorize_drive,
    categorize_response,
    coverage_gaps,
    grade_point,
    grid_step_ratio,
    margin_db,
    validate_band,
    validate_injection_point,
    validate_sweep,
    worst_point,
)

BAND = (1.0e5, 1.0e6)
PER_DECADE = 10.0
BUNDLE = "power-harness"
REQUIRED_A = 0.05


def sweep_frequencies(count=11, low=1.0e5, per_decade=PER_DECADE):
    return [low * math.pow(10.0, index / per_decade) for index in range(count)]


def point(frequency, bundle=BUNDLE, required=REQUIRED_A, achieved=0.06, onset=None):
    record = {
        "bundle": bundle,
        "frequency_hz": frequency,
        "required_current_a": required,
        "achieved_current_a": achieved,
    }
    if onset is not None:
        record["deviation_current_a"] = onset
    return record


def good_run(**over):
    return [point(frequency, **over) for frequency in sweep_frequencies()]


def assess(records=None, required=(BUNDLE,)):
    return assess_cable_injection_aim(
        good_run() if records is None else records, BAND, required, PER_DECADE
    )


class TestMarginAndBand(unittest.TestCase):
    def test_equal_currents_carry_no_margin(self):
        self.assertAlmostEqual(margin_db(0.05, 0.05), 0.0, places=9)

    def test_a_tenfold_current_is_twenty_decibels(self):
        self.assertAlmostEqual(margin_db(0.5, 0.05), 20.0, places=9)

    def test_half_the_current_is_a_negative_margin(self):
        self.assertAlmostEqual(margin_db(0.025, 0.05), -20.0 * math.log10(2.0), places=9)

    def test_zero_achieved_current_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_db(0.0, 0.05)

    def test_negative_required_current_is_rejected(self):
        with self.assertRaises(ValueError):
            margin_db(0.05, -0.05)

    def test_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((1.0e6, 1.0e5))

    def test_band_must_be_a_pair(self):
        with self.assertRaises(ValueError):
            validate_band((1.0e5, 1.0e6, 1.0e7))

    def test_zero_band_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((0.0, 1.0e6))


class TestPointValidation(unittest.TestCase):
    def test_good_point_normalizes_its_bundle_name(self):
        normalized = validate_injection_point(point(1.0e5, bundle="Power-Harness"))
        self.assertEqual(normalized["bundle"], BUNDLE)

    def test_missing_frequency_is_rejected(self):
        record = point(1.0e5)
        del record["frequency_hz"]
        with self.assertRaises(ValueError):
            validate_injection_point(record)

    def test_zero_required_current_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(point(1.0e5, required=0.0))

    def test_boolean_achieved_current_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(point(1.0e5, achieved=True))

    def test_an_absent_deviation_reads_as_none(self):
        self.assertIsNone(validate_injection_point(point(1.0e5))["deviation_current_a"])

    def test_a_non_positive_deviation_onset_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(point(1.0e5, onset=-0.01))

    def test_a_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(("power-harness", 1.0e5))


class TestSweepValidation(unittest.TestCase):
    def test_good_sweep_keeps_every_point(self):
        self.assertEqual(len(validate_sweep(good_run())), 11)

    def test_a_single_point_is_not_a_sweep(self):
        with self.assertRaises(ValueError):
            validate_sweep([point(1.0e5)])

    def test_a_repeated_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([point(1.0e5), point(1.0e5)])

    def test_a_descending_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([point(2.0e5), point(1.0e5)])

    def test_two_bundles_in_one_sweep_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([point(1.0e5), point(2.0e5, bundle="signal-harness")])


class TestCoverage(unittest.TestCase):
    def test_ten_points_per_decade_is_the_tenth_root_of_ten(self):
        self.assertAlmostEqual(
            grid_step_ratio(10.0), math.pow(10.0, 0.1), places=12
        )

    def test_fewer_than_one_point_per_decade_is_rejected(self):
        with self.assertRaises(ValueError):
            grid_step_ratio(0.5)

    def test_a_sweep_on_the_grid_leaves_no_gap(self):
        self.assertEqual(coverage_gaps(sweep_frequencies(), BAND, PER_DECADE), [])

    def test_a_dropped_middle_point_is_reported_as_a_gap(self):
        frequencies = sweep_frequencies()
        del frequencies[5]
        gaps = coverage_gaps(frequencies, BAND, PER_DECADE)
        self.assertEqual(len(gaps), 1)

    def test_a_sweep_starting_above_the_band_floor_reports_a_low_end_gap(self):
        gaps = coverage_gaps(sweep_frequencies()[2:], BAND, PER_DECADE)
        self.assertAlmostEqual(gaps[0][0], BAND[0], places=6)

    def test_a_sweep_ending_below_the_band_ceiling_reports_a_high_end_gap(self):
        gaps = coverage_gaps(sweep_frequencies()[:-2], BAND, PER_DECADE)
        self.assertAlmostEqual(gaps[-1][1], BAND[1], places=6)

    def test_non_advancing_frequencies_are_rejected(self):
        with self.assertRaises(ValueError):
            coverage_gaps([2.0e5, 1.0e5], BAND, PER_DECADE)

    def test_an_empty_frequency_list_is_rejected(self):
        with self.assertRaises(ValueError):
            coverage_gaps([], BAND, PER_DECADE)


class TestGrading(unittest.TestCase):
    def test_a_comfortable_drive_meets_the_limit(self):
        self.assertEqual(categorize_drive(0.06, REQUIRED_A), MEETS_LIMIT)

    def test_a_drive_landing_on_the_level_sits_at_the_limit(self):
        self.assertEqual(categorize_drive(REQUIRED_A, REQUIRED_A), AT_LIMIT)

    def test_a_drive_under_the_level_is_a_shortfall(self):
        self.assertEqual(categorize_drive(0.04, REQUIRED_A), DRIVE_SHORTFALL)

    def test_a_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_drive(0.06, REQUIRED_A, -1.0)

    def test_a_point_without_a_deviation_is_not_susceptible(self):
        response, threshold = categorize_response(
            validate_injection_point(point(1.0e5))
        )
        self.assertEqual(response, NOT_SUSCEPTIBLE)
        self.assertIsNone(threshold)

    def test_a_deviation_well_above_the_level_keeps_its_threshold(self):
        response, threshold = categorize_response(
            validate_injection_point(point(1.0e5, onset=0.09))
        )
        self.assertEqual(response, SUSCEPTIBLE_ABOVE_LIMIT)
        self.assertGreater(threshold, 5.0)

    def test_a_deviation_on_the_level_is_at_or_below_it(self):
        response, threshold = categorize_response(
            validate_injection_point(point(1.0e5, onset=REQUIRED_A))
        )
        self.assertEqual(response, SUSCEPTIBLE_AT_OR_BELOW_LIMIT)
        self.assertAlmostEqual(threshold, 0.0, places=9)

    def test_the_governing_margin_takes_the_smaller_of_the_two(self):
        graded = grade_point(validate_injection_point(point(1.0e5, onset=0.055)))
        self.assertAlmostEqual(
            graded["governing_margin_db"], graded["threshold_margin_db"], places=9
        )

    def test_the_governing_margin_is_the_drive_when_nothing_deviated(self):
        graded = grade_point(validate_injection_point(point(1.0e5)))
        self.assertAlmostEqual(
            graded["governing_margin_db"], graded["drive_margin_db"], places=9
        )

    def test_worst_point_takes_the_least_margin(self):
        graded = [
            grade_point(validate_injection_point(point(1.0e5))),
            grade_point(validate_injection_point(point(2.0e5, achieved=0.051))),
        ]
        self.assertAlmostEqual(worst_point(graded)["frequency_hz"], 2.0e5, places=3)

    def test_worst_point_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_point([])


class TestAimAssessment(unittest.TestCase):
    def test_a_clean_run_demonstrates_the_aim(self):
        report = assess()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["limitations"], [])
        self.assertEqual(report["verdict"], VERDICT_DEMONSTRATED)

    def test_the_report_names_a_governing_bundle_and_frequency(self):
        report = assess()
        self.assertEqual(report["governing_bundle"], BUNDLE)
        self.assertIsNotNone(report["governing_frequency_hz"])

    def test_a_drive_shortfall_is_a_finding(self):
        records = good_run()
        records[4]["achieved_current_a"] = 0.03
        report = assess(records)
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)
        self.assertEqual(len(report["findings"]), 1)

    def test_a_point_sitting_on_the_level_is_only_a_limitation(self):
        records = good_run()
        records[4]["achieved_current_a"] = REQUIRED_A
        report = assess(records)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_LIMITATIONS)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_deviation_at_the_required_level_is_a_finding(self):
        records = good_run()
        records[7]["deviation_current_a"] = REQUIRED_A
        report = assess(records)
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)

    def test_a_deviation_above_the_required_level_is_a_limitation(self):
        records = good_run()
        records[7]["deviation_current_a"] = 0.12
        report = assess(records)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_LIMITATIONS)

    def test_a_required_bundle_never_injected_is_a_finding(self):
        report = assess(required=(BUNDLE, "signal-harness"))
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)
        self.assertIn("signal-harness", " ".join(report["findings"]))

    def test_an_unrequired_bundle_is_carried_as_a_limitation(self):
        records = good_run() + [
            point(frequency, bundle="spare-harness")
            for frequency in sweep_frequencies()
        ]
        report = assess(records)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_LIMITATIONS)

    def test_a_coverage_gap_inside_the_band_is_a_finding(self):
        records = good_run()
        del records[5]
        report = assess(records)
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)

    def test_records_that_are_not_a_sequence_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_cable_injection_aim({"bundle": BUNDLE}, BAND, (BUNDLE,))

    def test_required_bundles_as_a_bare_string_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_cable_injection_aim(good_run(), BAND, BUNDLE)

    def test_an_empty_required_bundle_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_cable_injection_aim(good_run(), BAND, ())

    def test_the_assessment_propagates_a_bad_point(self):
        records = good_run()
        records[3]["achieved_current_a"] = 0.0
        with self.assertRaises(ValueError):
            assess(records)


if __name__ == "__main__":
    unittest.main()
