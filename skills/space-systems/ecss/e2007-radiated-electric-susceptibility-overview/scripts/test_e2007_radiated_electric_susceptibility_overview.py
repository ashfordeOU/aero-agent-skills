#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-susceptibility-overview.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_susceptibility_overview.py
"""

import unittest

from e2007_radiated_electric_susceptibility_overview_logic import (
    CATEGORY_ABOVE,
    CATEGORY_AT_LEVEL,
    CATEGORY_UNDER,
    DEFAULT_METHOD_BAND_HZ,
    OBJECT_CABLING,
    OBJECT_ENCLOSURE,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_radiated_electric_susceptibility_overview,
    categorize_field_point,
    degradation_frequencies_hz,
    field_margin_db,
    governing_point,
    normalize_exposure_object,
    susceptibility_threshold_hz,
    sweep_band_coverage,
    validate_exposure_sweep,
    validate_method_band,
)

BAND = (1.0e7, 1.0e9)

# 20 log10(2) and 20 log10(1/2), written out rather than recomputed from the
# module under test.
SIX_DB = 6.020599913279624


def points(**over):
    rows = [
        {
            "frequency_hz": 1.0e7,
            "field_applied_v_m": 20.0,
            "field_required_v_m": 20.0,
            "degradation_observed": False,
        },
        {
            "frequency_hz": 1.0e8,
            "field_applied_v_m": 20.0,
            "field_required_v_m": 20.0,
            "degradation_observed": False,
        },
        {
            "frequency_hz": 1.0e9,
            "field_applied_v_m": 20.0,
            "field_required_v_m": 20.0,
            "degradation_observed": False,
        },
    ]
    for index, changes in over.items():
        rows[int(index[1:])].update(changes)
    return rows


def records(enclosure=None, cabling=None):
    out = []
    if enclosure is not None:
        out.append({"object": OBJECT_ENCLOSURE, "points": enclosure})
    if cabling is not None:
        out.append({"object": OBJECT_CABLING, "points": cabling})
    return out


def both():
    return records(points(), points())


class TestMethodBand(unittest.TestCase):
    def test_the_default_band_validates(self):
        low, high = validate_method_band(DEFAULT_METHOD_BAND_HZ)
        self.assertLess(low, high)

    def test_an_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((1.0e9, 1.0e7))

    def test_a_band_that_is_not_a_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((1.0e7,))

    def test_a_non_positive_lower_edge_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((0.0, 1.0e9))


class TestFieldMargin(unittest.TestCase):
    def test_an_applied_field_on_the_requirement_has_no_margin(self):
        self.assertAlmostEqual(field_margin_db(20.0, 20.0), 0.0, places=9)

    def test_twice_the_required_field_is_six_decibels_over(self):
        self.assertAlmostEqual(field_margin_db(40.0, 20.0), SIX_DB, places=9)

    def test_half_the_required_field_is_six_decibels_under(self):
        self.assertAlmostEqual(field_margin_db(10.0, 20.0), -SIX_DB, places=9)

    def test_a_zero_applied_field_is_rejected(self):
        with self.assertRaises(ValueError):
            field_margin_db(0.0, 20.0)

    def test_a_negative_required_field_is_rejected(self):
        with self.assertRaises(ValueError):
            field_margin_db(20.0, -20.0)


class TestCategories(unittest.TestCase):
    def test_a_margin_of_zero_is_at_the_required_level(self):
        self.assertEqual(categorize_field_point(0.0), CATEGORY_AT_LEVEL)

    def test_a_negative_margin_is_below_the_required_level(self):
        self.assertEqual(categorize_field_point(-SIX_DB), CATEGORY_UNDER)

    def test_a_positive_margin_is_above_the_required_level(self):
        self.assertEqual(categorize_field_point(SIX_DB), CATEGORY_ABOVE)

    def test_an_unrecognized_exposure_object_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_exposure_object("test-chamber")

    def test_an_exposure_object_is_case_normalized(self):
        self.assertEqual(normalize_exposure_object("Unit-Enclosure"), OBJECT_ENCLOSURE)


class TestSweepValidation(unittest.TestCase):
    def test_a_good_sweep_normalizes_with_a_category_per_point(self):
        sweep = validate_exposure_sweep(points())
        self.assertEqual(len(sweep), 3)
        self.assertEqual(sweep[0]["category"], CATEGORY_AT_LEVEL)

    def test_a_sweep_whose_frequencies_do_not_increase_is_rejected(self):
        rows = points(p2={"frequency_hz": 1.0e6})
        with self.assertRaises(ValueError):
            validate_exposure_sweep(rows)

    def test_an_empty_sweep_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_sweep([])

    def test_a_point_without_a_monitored_response_is_rejected(self):
        rows = points()
        del rows[1]["degradation_observed"]
        with self.assertRaises(ValueError):
            validate_exposure_sweep(rows)

    def test_a_non_boolean_monitored_response_is_rejected(self):
        rows = points(p1={"degradation_observed": "none"})
        with self.assertRaises(ValueError):
            validate_exposure_sweep(rows)

    def test_a_zero_applied_field_in_a_sweep_is_rejected(self):
        rows = points(p0={"field_applied_v_m": 0.0})
        with self.assertRaises(ValueError):
            validate_exposure_sweep(rows)


class TestBandCoverage(unittest.TestCase):
    def test_a_sweep_spanning_the_band_has_no_shortfall(self):
        coverage = sweep_band_coverage(validate_exposure_sweep(points()), BAND)
        self.assertEqual(coverage["shortfalls"], [])

    def test_a_sweep_starting_inside_the_band_is_short_at_the_low_edge(self):
        rows = points(p0={"frequency_hz": 2.0e7})
        coverage = sweep_band_coverage(validate_exposure_sweep(rows), BAND)
        self.assertFalse(coverage["reaches_low_edge"])
        self.assertEqual(len(coverage["shortfalls"]), 1)

    def test_a_sweep_stopping_inside_the_band_is_short_at_the_high_edge(self):
        rows = points(p2={"frequency_hz": 5.0e8})
        coverage = sweep_band_coverage(validate_exposure_sweep(rows), BAND)
        self.assertFalse(coverage["reaches_high_edge"])

    def test_an_edge_within_the_named_slack_still_counts_as_reached(self):
        rows = points(p0={"frequency_hz": 1.005e7})
        coverage = sweep_band_coverage(validate_exposure_sweep(rows), BAND)
        self.assertTrue(coverage["reaches_low_edge"])

    def test_a_negative_slack_is_rejected(self):
        with self.assertRaises(ValueError):
            sweep_band_coverage(validate_exposure_sweep(points()), BAND, -0.01)


class TestDegradation(unittest.TestCase):
    def test_a_clean_run_has_no_susceptibility_threshold(self):
        sweep = validate_exposure_sweep(points())
        self.assertIsNone(susceptibility_threshold_hz(sweep))

    def test_the_threshold_is_the_lowest_frequency_that_degraded(self):
        rows = points(
            p1={"degradation_observed": True}, p2={"degradation_observed": True}
        )
        sweep = validate_exposure_sweep(rows)
        self.assertAlmostEqual(susceptibility_threshold_hz(sweep), 1.0e8, places=9)

    def test_every_degraded_frequency_is_listed(self):
        rows = points(
            p0={"degradation_observed": True}, p2={"degradation_observed": True}
        )
        sweep = validate_exposure_sweep(rows)
        self.assertEqual(len(degradation_frequencies_hz(sweep)), 2)


class TestGoverningPoint(unittest.TestCase):
    def test_the_governing_point_is_the_least_field_margin(self):
        rows = points(p1={"field_applied_v_m": 10.0})
        worst = governing_point(validate_exposure_sweep(rows))
        self.assertAlmostEqual(worst["frequency_hz"], 1.0e8, places=9)

    def test_an_exact_tie_is_broken_on_the_lower_frequency(self):
        worst = governing_point(validate_exposure_sweep(points()))
        self.assertAlmostEqual(worst["frequency_hz"], 1.0e7, places=9)

    def test_an_empty_sweep_has_no_governing_point(self):
        with self.assertRaises(ValueError):
            governing_point([])


class TestFullAssessment(unittest.TestCase):
    def test_both_objects_swept_at_level_demonstrate_the_aim(self):
        report = assess_radiated_electric_susceptibility_overview(both(), BAND)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_MET)

    def test_a_run_that_never_exposes_the_cabling_does_not_demonstrate_the_aim(self):
        report = assess_radiated_electric_susceptibility_overview(
            records(enclosure=points()), BAND
        )
        self.assertEqual(report["objects_absent"], [OBJECT_CABLING])
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_a_field_under_the_requirement_is_a_finding(self):
        report = assess_radiated_electric_susceptibility_overview(
            records(points(p1={"field_applied_v_m": 10.0}), points()), BAND
        )
        self.assertEqual(report["summaries"][OBJECT_ENCLOSURE]["under_level_count"], 1)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_a_degradation_is_a_finding_with_its_threshold(self):
        report = assess_radiated_electric_susceptibility_overview(
            records(points(), points(p2={"degradation_observed": True})), BAND
        )
        summary = report["summaries"][OBJECT_CABLING]
        self.assertAlmostEqual(summary["susceptibility_threshold_hz"], 1.0e9, places=9)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)

    def test_an_overtest_is_a_limitation_not_a_finding(self):
        report = assess_radiated_electric_susceptibility_overview(
            records(points(p0={"field_applied_v_m": 40.0}), points()), BAND
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("overtest" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], VERDICT_MET)

    def test_a_band_shortfall_is_a_finding(self):
        report = assess_radiated_electric_susceptibility_overview(
            records(points(), points(p2={"frequency_hz": 5.0e8})), BAND
        )
        self.assertTrue(any("upper edge" in f for f in report["findings"]))

    def test_an_object_declared_twice_is_rejected(self):
        twice = [
            {"object": OBJECT_ENCLOSURE, "points": points()},
            {"object": OBJECT_ENCLOSURE, "points": points()},
        ]
        with self.assertRaises(ValueError):
            assess_radiated_electric_susceptibility_overview(twice, BAND)

    def test_the_governing_object_is_the_one_with_the_least_margin(self):
        report = assess_radiated_electric_susceptibility_overview(
            records(points(), points(p1={"field_applied_v_m": 10.0})), BAND
        )
        self.assertEqual(report["governing_object"], OBJECT_CABLING)

    def test_an_empty_record_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_radiated_electric_susceptibility_overview([], BAND)

    def test_the_report_carries_the_band_it_graded_against(self):
        report = assess_radiated_electric_susceptibility_overview(both(), BAND)
        self.assertAlmostEqual(report["method_band_hz"][0], BAND[0], places=9)
        self.assertAlmostEqual(report["method_band_hz"][1], BAND[1], places=9)


if __name__ == "__main__":
    unittest.main()
