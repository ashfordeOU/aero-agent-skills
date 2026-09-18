#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radio-frequency-conducted-emission-purpose.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radio_frequency_conducted_emission_purpose.py
"""

import unittest

from e2007_radio_frequency_conducted_emission_purpose_logic import (
    CATEGORY_AT_LIMIT,
    CATEGORY_EXCEEDANCE,
    CATEGORY_WITHIN,
    DEFAULT_METHOD_BAND_HZ,
    LEAD_ROLES,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_conducted_emission_objective,
    categorize_point,
    governing_lead,
    grade_lead_emission,
    normalize_lead_role,
    point_margin_db,
    sweep_band_coverage,
    validate_emission_sweep,
    validate_method_band,
)


def clean_sweep():
    return [
        {"frequency_hz": 2.0e6, "level_dbuv": 40.0, "limit_dbuv": 70.0},
        {"frequency_hz": 10.0e6, "level_dbuv": 38.0, "limit_dbuv": 66.0},
        {"frequency_hz": 50.0e6, "level_dbuv": 34.0, "limit_dbuv": 60.0},
        {"frequency_hz": 100.0e6, "level_dbuv": 30.0, "limit_dbuv": 56.0},
    ]


def lead_pair():
    return {"power-input": clean_sweep(), "power-return": clean_sweep()}


class TestMethodBand(unittest.TestCase):
    def test_default_band_validates(self):
        low, high = validate_method_band()
        self.assertAlmostEqual(low, DEFAULT_METHOD_BAND_HZ[0], places=9)
        self.assertAlmostEqual(high, DEFAULT_METHOD_BAND_HZ[1], places=9)

    def test_declared_band_is_returned_as_floats(self):
        low, high = validate_method_band((1.0e6, 30.0e6))
        self.assertAlmostEqual(low, 1.0e6, places=9)
        self.assertAlmostEqual(high, 30.0e6, places=9)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((100.0e6, 2.0e6))

    def test_zero_low_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((0.0, 100.0e6))

    def test_collapsed_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band((30.0e6, 30.0e6))

    def test_non_pair_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_band(30.0e6)


class TestLeadRoles(unittest.TestCase):
    def test_every_recognized_role_normalizes(self):
        for role in LEAD_ROLES:
            self.assertEqual(normalize_lead_role(role.upper()), role)

    def test_unrecognized_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead_role("antenna-port")

    def test_non_string_role_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead_role(7)


class TestSweepValidation(unittest.TestCase):
    def test_clean_sweep_normalizes(self):
        sweep = validate_emission_sweep(clean_sweep())
        self.assertEqual(len(sweep), 4)
        self.assertAlmostEqual(sweep[0]["level_dbuv"], 40.0, places=9)

    def test_empty_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_emission_sweep([])

    def test_non_list_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_emission_sweep({"frequency_hz": 2.0e6})

    def test_missing_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_emission_sweep([{"frequency_hz": 2.0e6, "level_dbuv": 40.0}])

    def test_boolean_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_emission_sweep(
                [{"frequency_hz": 2.0e6, "level_dbuv": True, "limit_dbuv": 70.0}]
            )

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_emission_sweep(
                [{"frequency_hz": -2.0e6, "level_dbuv": 40.0, "limit_dbuv": 70.0}]
            )

    def test_decreasing_frequency_rejected(self):
        points = clean_sweep()
        points[2]["frequency_hz"] = 5.0e6
        with self.assertRaises(ValueError):
            validate_emission_sweep(points)

    def test_duplicate_frequency_rejected(self):
        points = clean_sweep()
        points[1]["frequency_hz"] = points[0]["frequency_hz"]
        with self.assertRaises(ValueError):
            validate_emission_sweep(points)


class TestBandCoverage(unittest.TestCase):
    def test_full_sweep_covers_the_band(self):
        coverage = sweep_band_coverage(clean_sweep())
        self.assertTrue(coverage["covers_band"])
        self.assertAlmostEqual(coverage["first_hz"], 2.0e6, places=9)

    def test_sweep_starting_high_misses_the_low_edge(self):
        points = clean_sweep()[1:]
        coverage = sweep_band_coverage(points)
        self.assertFalse(coverage["reaches_low_edge"])
        self.assertTrue(coverage["reaches_high_edge"])

    def test_sweep_stopping_early_misses_the_high_edge(self):
        points = clean_sweep()[:-1]
        coverage = sweep_band_coverage(points)
        self.assertTrue(coverage["reaches_low_edge"])
        self.assertFalse(coverage["reaches_high_edge"])

    def test_edge_slack_absorbs_a_near_edge_start(self):
        points = clean_sweep()
        points[0]["frequency_hz"] = 2.01e6
        coverage = sweep_band_coverage(points)
        self.assertTrue(coverage["reaches_low_edge"])

    def test_negative_edge_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            sweep_band_coverage(clean_sweep(), rel_tol=-0.01)


class TestMarginCategorization(unittest.TestCase):
    def test_margin_is_limit_minus_level(self):
        point = {"frequency_hz": 2.0e6, "level_dbuv": 41.5, "limit_dbuv": 70.0}
        self.assertAlmostEqual(point_margin_db(point), 28.5, places=9)

    def test_level_under_the_limit_is_within(self):
        point = {"frequency_hz": 2.0e6, "level_dbuv": 40.0, "limit_dbuv": 70.0}
        self.assertEqual(categorize_point(point), CATEGORY_WITHIN)

    def test_level_on_the_limit_is_at_limit(self):
        point = {"frequency_hz": 2.0e6, "level_dbuv": 70.0, "limit_dbuv": 70.0}
        self.assertAlmostEqual(point_margin_db(point), 0.0, places=9)
        self.assertEqual(categorize_point(point), CATEGORY_AT_LIMIT)

    def test_level_over_the_limit_is_an_exceedance(self):
        point = {"frequency_hz": 2.0e6, "level_dbuv": 74.0, "limit_dbuv": 70.0}
        self.assertEqual(categorize_point(point), CATEGORY_EXCEEDANCE)

    def test_representation_error_at_the_limit_reads_as_at_limit(self):
        # 70.3 - 29.3 - 41.0 is not exactly zero in binary floating point, so
        # a level physically equal to its limit can land either side of it.
        point = {"frequency_hz": 2.0e6, "level_dbuv": 29.3 + 41.0, "limit_dbuv": 70.3}
        self.assertAlmostEqual(point_margin_db(point), 0.0, places=9)
        self.assertEqual(categorize_point(point), CATEGORY_AT_LIMIT)

    def test_negative_tolerance_rejected(self):
        point = {"frequency_hz": 2.0e6, "level_dbuv": 40.0, "limit_dbuv": 70.0}
        with self.assertRaises(ValueError):
            categorize_point(point, tol_db=-1.0)


class TestLeadGrading(unittest.TestCase):
    def test_quiet_lead_is_within_limits(self):
        report = grade_lead_emission("power-input", clean_sweep())
        self.assertTrue(report["within_limits"])
        self.assertEqual(report["counts"][CATEGORY_WITHIN], 4)

    def test_worst_case_is_the_smallest_margin(self):
        points = clean_sweep()
        points[2]["level_dbuv"] = 58.0
        report = grade_lead_emission("power-return", points)
        self.assertAlmostEqual(report["worst_case"]["frequency_hz"], 50.0e6, places=9)
        self.assertAlmostEqual(report["worst_case"]["margin_db"], 2.0, places=9)

    def test_exceedance_clears_the_within_limits_flag(self):
        points = clean_sweep()
        points[0]["level_dbuv"] = 73.0
        report = grade_lead_emission("power-input", points)
        self.assertFalse(report["within_limits"])
        self.assertEqual(report["counts"][CATEGORY_EXCEEDANCE], 1)

    def test_grade_rejects_an_unrecognized_lead(self):
        with self.assertRaises(ValueError):
            grade_lead_emission("chassis-bond", clean_sweep())

    def test_governing_lead_is_the_tighter_lead(self):
        quiet = grade_lead_emission("power-input", clean_sweep())
        noisy_points = clean_sweep()
        noisy_points[1]["level_dbuv"] = 64.0
        noisy = grade_lead_emission("power-return", noisy_points)
        self.assertEqual(governing_lead([quiet, noisy])["lead"], "power-return")

    def test_governing_lead_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            governing_lead([])


class TestObjectiveAssessment(unittest.TestCase):
    def test_clean_pair_meets_the_objective(self):
        report = assess_conducted_emission_objective(lead_pair())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["leads"]), 2)

    def test_missing_return_lead_rejected(self):
        with self.assertRaises(ValueError):
            assess_conducted_emission_objective({"power-input": clean_sweep()})

    def test_duplicate_lead_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_conducted_emission_objective(
                {"power-input": clean_sweep(), "POWER-INPUT ": clean_sweep()}
            )

    def test_empty_lead_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assess_conducted_emission_objective({})

    def test_non_mapping_lead_sweeps_rejected(self):
        with self.assertRaises(ValueError):
            assess_conducted_emission_objective([clean_sweep()])

    def test_exceedance_blocks_the_objective(self):
        sweeps = lead_pair()
        sweeps["power-return"][3]["level_dbuv"] = 62.0
        report = assess_conducted_emission_objective(sweeps)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["governing_lead"], "power-return")
        self.assertTrue(any("limit exceeded" in f for f in report["findings"]))

    def test_level_on_the_limit_is_a_limitation_not_a_finding(self):
        sweeps = lead_pair()
        sweeps["power-input"][1]["level_dbuv"] = 66.0
        report = assess_conducted_emission_objective(sweeps)
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertTrue(any("sits on the limit" in l for l in report["limitations"]))

    def test_short_sweep_is_a_finding_when_full_band_required(self):
        sweeps = lead_pair()
        sweeps["power-input"] = clean_sweep()[:-1]
        report = assess_conducted_emission_objective(sweeps)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertTrue(any("stops short" in f for f in report["findings"]))

    def test_short_sweep_is_a_limitation_when_full_band_waived(self):
        sweeps = lead_pair()
        sweeps["power-input"] = clean_sweep()[:-1]
        report = assess_conducted_emission_objective(sweeps, require_full_band=False)
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertTrue(any("stops short" in l for l in report["limitations"]))

    def test_leads_are_reported_in_a_stable_order(self):
        report = assess_conducted_emission_objective(lead_pair())
        self.assertEqual([r["lead"] for r in report["leads"]], list(LEAD_ROLES))

    def test_narrower_declared_band_changes_the_coverage_verdict(self):
        sweeps = lead_pair()
        sweeps["power-input"] = clean_sweep()[:-1]
        report = assess_conducted_emission_objective(sweeps, band=(2.0e6, 50.0e6))
        self.assertEqual(report["verdict"], VERDICT_MET)

    def test_governing_point_carries_the_smallest_margin(self):
        sweeps = lead_pair()
        sweeps["power-return"][2]["level_dbuv"] = 57.0
        report = assess_conducted_emission_objective(sweeps)
        self.assertEqual(report["governing_lead"], "power-return")
        self.assertAlmostEqual(report["governing_point"]["margin_db"], 3.0, places=9)


if __name__ == "__main__":
    unittest.main()
