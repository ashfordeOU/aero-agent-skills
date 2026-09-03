"""Contract tests for the coverage-path-planning logic module.

Runs offline with stdlib only: python3 scripts/test_coverage_path_planning.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import coverage_path_planning_logic as cpp


class TestGroundSwath(unittest.TestCase):
    def test_swath_anchor_60_deg_fov(self):
        self.assertAlmostEqual(cpp.ground_swath(120.0, 60.0), 138.56,
                               delta=0.01)

    def test_swath_90_deg_fov(self):
        self.assertAlmostEqual(cpp.ground_swath(100.0, 90.0), 200.0,
                               delta=0.01)

    def test_swath_scales_with_altitude(self):
        self.assertAlmostEqual(cpp.ground_swath(240.0, 60.0),
                               2.0 * cpp.ground_swath(120.0, 60.0),
                               delta=0.01)

    def test_swath_zero_altitude_raises(self):
        with self.assertRaises(ValueError):
            cpp.ground_swath(0.0, 60.0)

    def test_swath_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            cpp.ground_swath(-10.0, 60.0)

    def test_swath_zero_fov_raises(self):
        with self.assertRaises(ValueError):
            cpp.ground_swath(120.0, 0.0)

    def test_swath_fov_180_raises(self):
        with self.assertRaises(ValueError):
            cpp.ground_swath(120.0, 180.0)

    def test_swath_narrow_positive_fov_valid(self):
        self.assertGreater(cpp.ground_swath(120.0, 0.5), 0.0)


class TestTrackSpacing(unittest.TestCase):
    def test_spacing_anchor_25_percent_overlap(self):
        sw = cpp.ground_swath(120.0, 60.0)
        self.assertAlmostEqual(cpp.track_spacing(sw, 0.25), 103.92,
                               delta=0.01)

    def test_spacing_zero_overlap_keeps_full_swath(self):
        self.assertAlmostEqual(cpp.track_spacing(138.56, 0.0), 138.56,
                               delta=0.01)

    def test_spacing_max_overlap_boundary_valid(self):
        self.assertAlmostEqual(cpp.track_spacing(100.0, 0.95), 5.0,
                               delta=1e-9)

    def test_spacing_overlap_one_raises(self):
        with self.assertRaises(ValueError):
            cpp.track_spacing(138.56, 1.0)

    def test_spacing_negative_overlap_raises(self):
        with self.assertRaises(ValueError):
            cpp.track_spacing(138.56, -0.1)

    def test_spacing_nonpositive_swath_raises(self):
        with self.assertRaises(ValueError):
            cpp.track_spacing(0.0, 0.25)
        with self.assertRaises(ValueError):
            cpp.track_spacing(-50.0, 0.25)


class TestPassCount(unittest.TestCase):
    def test_pass_count_anchor_over_ceil(self):
        sw = cpp.ground_swath(120.0, 60.0)
        spacing = cpp.track_spacing(sw, 0.25)
        self.assertEqual(cpp.pass_count(800.0, spacing), 8)

    def test_pass_count_exact_divide(self):
        self.assertEqual(cpp.pass_count(800.0, 100.0), 8)

    def test_pass_count_ceil_boundary_nine(self):
        self.assertEqual(cpp.pass_count(800.0, 90.0), 9)

    def test_pass_count_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            cpp.pass_count(0.0, 90.0)
        with self.assertRaises(ValueError):
            cpp.pass_count(800.0, 0.0)
        with self.assertRaises(ValueError):
            cpp.pass_count(800.0, -5.0)


class TestPathLength(unittest.TestCase):
    def test_path_length_anchor_eight_passes(self):
        self.assertAlmostEqual(cpp.path_length(1200.0, 8, 60.0),
                               10919.47, delta=0.1)

    def test_path_length_anchor_turn_total(self):
        straight = 8.0 * 1200.0
        turns = 7.0 * math.pi * 60.0
        self.assertAlmostEqual(straight + turns, 10919.47, delta=0.1)

    def test_path_length_single_pass_no_turns(self):
        self.assertAlmostEqual(cpp.path_length(1200.0, 1, 60.0), 1200.0,
                               delta=1e-9)

    def test_path_length_two_passes_one_turn(self):
        expected = 2.0 * 1200.0 + math.pi * 60.0
        self.assertAlmostEqual(cpp.path_length(1200.0, 2, 60.0), expected,
                               delta=0.1)

    def test_path_length_ceil_boundary_nine_passes(self):
        self.assertAlmostEqual(cpp.path_length(1200.0, 9, 60.0),
                               12307.96, delta=0.5)

    def test_path_length_zero_passes_no_turns(self):
        self.assertAlmostEqual(cpp.path_length(1200.0, 0, 60.0), 0.0,
                               delta=1e-9)

    def test_path_length_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cpp.path_length(-1200.0, 8, 60.0)
        with self.assertRaises(ValueError):
            cpp.path_length(1200.0, -1, 60.0)
        with self.assertRaises(ValueError):
            cpp.path_length(1200.0, 8, 0.0)
        with self.assertRaises(ValueError):
            cpp.path_length(1200.0, 8, -60.0)


class TestSurveyTime(unittest.TestCase):
    def test_survey_time_anchor(self):
        total = cpp.path_length(1200.0, 8, 60.0)
        self.assertAlmostEqual(cpp.survey_time(total, 25.0), 436.78,
                               delta=0.1)

    def test_survey_time_ceil_boundary_case(self):
        total = cpp.path_length(1200.0, 9, 60.0)
        self.assertAlmostEqual(cpp.survey_time(total, 25.0), 492.32,
                               delta=0.5)

    def test_survey_time_speed_scaling(self):
        self.assertAlmostEqual(cpp.survey_time(1000.0, 50.0), 20.0,
                               delta=1e-9)

    def test_survey_time_nonpositive_speed_raises(self):
        with self.assertRaises(ValueError):
            cpp.survey_time(1000.0, 0.0)
        with self.assertRaises(ValueError):
            cpp.survey_time(1000.0, -25.0)


class TestPlanCoverage(unittest.TestCase):
    def test_plan_coverage_dict_keys(self):
        plan = cpp.plan_coverage(1200.0, 800.0, 120.0, 60.0, 0.25,
                                 60.0, 25.0)
        self.assertEqual(
            set(plan.keys()),
            {"swath_width", "track_spacing", "n_passes",
             "straight_length", "turn_length_total", "total_length",
             "cruise_speed", "survey_time_s", "pass_headings"})

    def test_plan_coverage_anchor_values(self):
        plan = cpp.plan_coverage(1200.0, 800.0, 120.0, 60.0, 0.25,
                                 60.0, 25.0)
        self.assertAlmostEqual(plan["swath_width"], 138.56, delta=0.01)
        self.assertAlmostEqual(plan["track_spacing"], 103.92, delta=0.01)
        self.assertEqual(plan["n_passes"], 8)
        self.assertAlmostEqual(plan["straight_length"], 9600.0,
                               delta=0.1)
        self.assertAlmostEqual(plan["turn_length_total"], 1319.47,
                               delta=0.1)
        self.assertAlmostEqual(plan["total_length"], 10919.47, delta=0.1)
        self.assertEqual(plan["cruise_speed"], 25.0)
        self.assertAlmostEqual(plan["survey_time_s"], 436.78, delta=0.1)

    def test_plan_headings_alternate_eight_passes(self):
        plan = cpp.plan_coverage(1200.0, 800.0, 120.0, 60.0, 0.25,
                                 60.0, 25.0)
        expected = [90.0, 270.0] * 4
        self.assertEqual(plan["pass_headings"], expected)

    def test_plan_headings_alternate_nine_passes(self):
        plan = cpp.plan_coverage(1200.0, 800.0, 103.923, 60.0, 0.25,
                                 60.0, 25.0)
        expected = [90.0, 270.0, 90.0, 270.0, 90.0, 270.0, 90.0, 270.0,
                    90.0]
        self.assertEqual(plan["n_passes"], 9)
        self.assertEqual(plan["pass_headings"], expected)
        self.assertAlmostEqual(plan["total_length"], 12307.96, delta=0.5)
        self.assertAlmostEqual(plan["survey_time_s"], 492.32, delta=0.5)

    def test_plan_coverage_propagates_value_errors(self):
        with self.assertRaises(ValueError):
            cpp.plan_coverage(1200.0, 800.0, 0.0, 60.0, 0.25, 60.0, 25.0)
        with self.assertRaises(ValueError):
            cpp.plan_coverage(1200.0, 800.0, 120.0, 180.0, 0.25, 60.0,
                              25.0)
        with self.assertRaises(ValueError):
            cpp.plan_coverage(1200.0, 800.0, 120.0, 60.0, 1.0, 60.0,
                              25.0)
        with self.assertRaises(ValueError):
            cpp.plan_coverage(1200.0, 800.0, 120.0, 60.0, 0.25, 0.0,
                              25.0)
        with self.assertRaises(ValueError):
            cpp.plan_coverage(1200.0, 800.0, 120.0, 60.0, 0.25, 60.0,
                              0.0)

    def test_plan_coverage_n_passes_is_int(self):
        plan = cpp.plan_coverage(1200.0, 800.0, 120.0, 60.0, 0.25,
                                 60.0, 25.0)
        self.assertIsInstance(plan["n_passes"], int)
        self.assertEqual(len(plan["pass_headings"]), plan["n_passes"])


if __name__ == "__main__":
    unittest.main()
