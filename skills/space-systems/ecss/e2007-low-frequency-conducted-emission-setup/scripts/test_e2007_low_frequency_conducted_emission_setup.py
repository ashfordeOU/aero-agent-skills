#!/usr/bin/env python3
"""Gate 3 contract test for e2007-low-frequency-conducted-emission-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_low_frequency_conducted_emission_setup.py
"""

import unittest

from e2007_low_frequency_conducted_emission_setup_logic import (
    DEFAULT_HARNESS_HEIGHT_MM,
    DEFAULT_MIN_SEPARATION_MM,
    DEFAULT_PROBE_OFFSET_MM,
    MM_TOL,
    RECOGNIZED_LEADS,
    STATUS_CONFORMING,
    STATUS_DEVIATION,
    STATUS_MARGINAL,
    VERDICT_CONFORMING,
    VERDICT_DEVIATIONS,
    assess_setup,
    dimension_window,
    grade_dimension,
    grade_lead_run,
    normalize_lead,
    plane_margins_mm,
    validate_ground_plane,
    validate_lead_run,
    within,
)


def good_plane(**over):
    record = {
        "length_mm": 1200.0,
        "width_mm": 900.0,
        "bond_resistance_mohm": 1.2,
        "unit_bonded": True,
    }
    record.update(over)
    return record


def good_unit(**over):
    record = {"length_mm": 300.0, "width_mm": 200.0}
    record.update(over)
    return record


def good_run(**over):
    record = {
        "lead": "primary-positive",
        "probe_offset_mm": 50.0,
        "harness_height_mm": 50.0,
        "separation_mm": 150.0,
        "stabilisation_network_present": True,
    }
    record.update(over)
    return record


def two_runs():
    return [good_run(), good_run(lead="primary-return")]


class TestLeadNormalization(unittest.TestCase):
    def test_every_recognized_lead_normalizes(self):
        for lead in RECOGNIZED_LEADS:
            self.assertEqual(normalize_lead(lead.upper()), lead)

    def test_unrecognized_lead_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead("antenna-feed")

    def test_non_string_lead_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead(3)


class TestDimensionWindow(unittest.TestCase):
    def test_window_brackets_the_nominal(self):
        low, high = dimension_window(50.0, 5.0)
        self.assertAlmostEqual(low, 45.0)
        self.assertAlmostEqual(high, 55.0)

    def test_zero_nominal_rejected(self):
        with self.assertRaises(ValueError):
            dimension_window(0.0, 5.0)

    def test_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            dimension_window(50.0, 0.0)

    def test_tolerance_wider_than_nominal_rejected(self):
        with self.assertRaises(ValueError):
            dimension_window(50.0, 50.0)

    def test_within_absorbs_float_error_only(self):
        self.assertTrue(within(45.0, 45.0, 55.0))
        self.assertTrue(within(45.0 - MM_TOL / 2.0, 45.0, 55.0))
        self.assertFalse(within(44.0, 45.0, 55.0))


class TestDimensionGrading(unittest.TestCase):
    def test_nominal_value_is_conforming(self):
        graded = grade_dimension(50.0, 50.0, 5.0)
        self.assertEqual(graded["status"], STATUS_CONFORMING)
        self.assertAlmostEqual(graded["deviation_mm"], 0.0)

    def test_value_near_the_edge_is_marginal(self):
        graded = grade_dimension(54.5, 50.0, 5.0)
        self.assertEqual(graded["status"], STATUS_MARGINAL)

    def test_value_on_the_edge_is_still_inside_the_window(self):
        graded = grade_dimension(55.0, 50.0, 5.0)
        self.assertEqual(graded["status"], STATUS_MARGINAL)
        self.assertAlmostEqual(graded["deviation_mm"], 5.0, places=9)

    def test_value_outside_the_window_is_a_deviation(self):
        graded = grade_dimension(60.0, 50.0, 5.0)
        self.assertEqual(graded["status"], STATUS_DEVIATION)

    def test_deviation_sign_follows_the_offset(self):
        graded = grade_dimension(42.0, 50.0, 5.0)
        self.assertAlmostEqual(graded["deviation_mm"], -8.0, places=9)

    def test_marginal_fraction_of_zero_only_flags_the_exact_edge(self):
        graded = grade_dimension(54.5, 50.0, 5.0, marginal_fraction=0.0)
        self.assertEqual(graded["status"], STATUS_CONFORMING)

    def test_marginal_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_dimension(50.0, 50.0, 5.0, marginal_fraction=1.0)

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            grade_dimension("fifty", 50.0, 5.0)


class TestGroundPlane(unittest.TestCase):
    def test_margins_are_half_the_leftover_dimension(self):
        length_margin, width_margin = plane_margins_mm(good_plane(), good_unit())
        self.assertAlmostEqual(length_margin, 450.0)
        self.assertAlmostEqual(width_margin, 350.0)

    def test_unit_larger_than_the_plane_rejected(self):
        with self.assertRaises(ValueError):
            plane_margins_mm(good_plane(), good_unit(length_mm=1500.0))

    def test_zero_plane_dimension_rejected(self):
        with self.assertRaises(ValueError):
            plane_margins_mm(good_plane(width_mm=0.0), good_unit())

    def test_non_mapping_plane_rejected(self):
        with self.assertRaises(ValueError):
            plane_margins_mm("a copper sheet", good_unit())

    def test_good_plane_meets_margin_and_bond(self):
        record = validate_ground_plane(good_plane(), good_unit())
        self.assertTrue(record["margin_met"])
        self.assertTrue(record["bond_met"])
        self.assertAlmostEqual(record["bond_headroom_mohm"], 1.3, places=9)

    def test_tight_plane_fails_the_margin(self):
        record = validate_ground_plane(
            good_plane(length_mm=400.0, width_mm=900.0), good_unit()
        )
        self.assertFalse(record["margin_met"])

    def test_bond_exactly_on_the_limit_is_met(self):
        record = validate_ground_plane(
            good_plane(bond_resistance_mohm=2.5), good_unit()
        )
        self.assertTrue(record["bond_met"])
        self.assertAlmostEqual(record["bond_headroom_mohm"], 0.0, places=9)

    def test_bond_above_the_limit_is_not_met(self):
        record = validate_ground_plane(
            good_plane(bond_resistance_mohm=9.0), good_unit()
        )
        self.assertFalse(record["bond_met"])

    def test_negative_bond_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_ground_plane(good_plane(bond_resistance_mohm=-1.0), good_unit())

    def test_non_boolean_bond_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_ground_plane(good_plane(unit_bonded="yes"), good_unit())

    def test_zero_bond_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_ground_plane(
                good_plane(), good_unit(), max_bond_resistance_mohm=0.0
            )


class TestLeadRunValidation(unittest.TestCase):
    def test_good_run_normalizes(self):
        run = validate_lead_run(good_run())
        self.assertEqual(run["lead"], "primary-positive")
        self.assertAlmostEqual(run["probe_offset_mm"], DEFAULT_PROBE_OFFSET_MM)

    def test_zero_probe_offset_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead_run(good_run(probe_offset_mm=0.0))

    def test_negative_harness_height_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead_run(good_run(harness_height_mm=-10.0))

    def test_negative_separation_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead_run(good_run(separation_mm=-1.0))

    def test_missing_network_flag_rejected(self):
        record = good_run()
        del record["stabilisation_network_present"]
        with self.assertRaises(ValueError):
            validate_lead_run(record)

    def test_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            validate_lead_run(["primary-positive"])


class TestLeadRunGrading(unittest.TestCase):
    def test_nominal_run_conforms(self):
        report = grade_lead_run(good_run())
        self.assertTrue(report["conforming"])
        self.assertEqual(report["deviations"], [])

    def test_probe_too_far_from_the_connector_is_a_deviation(self):
        report = grade_lead_run(good_run(probe_offset_mm=120.0))
        self.assertFalse(report["conforming"])
        self.assertTrue(any("probe offset" in d for d in report["deviations"]))

    def test_harness_lying_on_the_plane_is_a_deviation(self):
        report = grade_lead_run(good_run(harness_height_mm=5.0))
        self.assertTrue(any("harness height" in d for d in report["deviations"]))

    def test_separation_exactly_at_the_minimum_is_met(self):
        report = grade_lead_run(
            good_run(separation_mm=DEFAULT_MIN_SEPARATION_MM)
        )
        self.assertTrue(report["separation_met"])

    def test_separation_below_the_minimum_is_a_deviation(self):
        report = grade_lead_run(good_run(separation_mm=20.0))
        self.assertFalse(report["separation_met"])
        self.assertTrue(any("separation" in d for d in report["deviations"]))

    def test_missing_stabilisation_network_is_a_deviation(self):
        report = grade_lead_run(good_run(stabilisation_network_present=False))
        self.assertTrue(
            any("stabilisation network" in d for d in report["deviations"])
        )

    def test_edge_of_window_is_carried_as_a_marginal(self):
        report = grade_lead_run(good_run(harness_height_mm=54.6))
        self.assertTrue(report["conforming"])
        self.assertEqual(len(report["marginals"]), 1)

    def test_negative_minimum_separation_rejected(self):
        with self.assertRaises(ValueError):
            grade_lead_run(good_run(), min_separation_mm=-5.0)

    def test_custom_nominal_height_moves_the_window(self):
        report = grade_lead_run(
            good_run(harness_height_mm=100.0), harness_height_mm=100.0
        )
        self.assertTrue(report["conforming"])
        self.assertAlmostEqual(
            report["harness_height"]["window_mm"][0], 95.0, places=9
        )


class TestAssessment(unittest.TestCase):
    def test_clean_bench_conforms(self):
        report = assess_setup(good_plane(), good_unit(), two_runs())
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["leads"]), 2)

    def test_unbonded_unit_is_a_finding(self):
        report = assess_setup(
            good_plane(unit_bonded=False), good_unit(), two_runs()
        )
        self.assertEqual(report["verdict"], VERDICT_DEVIATIONS)
        self.assertTrue(any("not bonded" in f for f in report["findings"]))

    def test_short_plane_overhang_is_a_finding(self):
        report = assess_setup(
            good_plane(length_mm=350.0), good_unit(), two_runs()
        )
        self.assertTrue(any("plane overhang" in f for f in report["findings"]))

    def test_high_bond_resistance_is_a_finding(self):
        report = assess_setup(
            good_plane(bond_resistance_mohm=12.0), good_unit(), two_runs()
        )
        self.assertTrue(any("bond resistance" in f for f in report["findings"]))

    def test_one_bad_lead_fails_the_whole_bench(self):
        runs = two_runs()
        runs[1]["probe_offset_mm"] = 400.0
        report = assess_setup(good_plane(), good_unit(), runs)
        self.assertEqual(report["verdict"], VERDICT_DEVIATIONS)

    def test_leads_are_reported_in_a_stable_order(self):
        runs = [good_run(lead="primary-return"), good_run()]
        report = assess_setup(good_plane(), good_unit(), runs)
        self.assertEqual(
            [r["lead"] for r in report["leads"]],
            ["primary-positive", "primary-return"],
        )

    def test_duplicate_lead_rejected(self):
        with self.assertRaises(ValueError):
            assess_setup(good_plane(), good_unit(), [good_run(), good_run()])

    def test_empty_lead_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_setup(good_plane(), good_unit(), [])

    def test_non_list_lead_runs_rejected(self):
        with self.assertRaises(ValueError):
            assess_setup(good_plane(), good_unit(), good_run())

    def test_marginal_height_does_not_fail_the_bench(self):
        runs = two_runs()
        runs[0]["harness_height_mm"] = 45.4
        report = assess_setup(good_plane(), good_unit(), runs)
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(len(report["limitations"]), 1)

    def test_default_offset_and_height_are_the_same_nominal(self):
        self.assertAlmostEqual(
            DEFAULT_PROBE_OFFSET_MM, DEFAULT_HARNESS_HEIGHT_MM, places=9
        )

    def test_ground_plane_record_is_returned(self):
        report = assess_setup(good_plane(), good_unit(), two_runs())
        self.assertAlmostEqual(report["ground_plane"]["length_margin_mm"], 450.0)


if __name__ == "__main__":
    unittest.main()
