"""
Offline deterministic unit tests for e1011_mannequin_logic.
Run: python3 test_e1011_mannequin.py
Expected output: OK
"""
import sys
import os
import unittest

# Allow running from repo root or from within the scripts/ directory.
sys.path.insert(0, os.path.dirname(__file__))

from e1011_mannequin_logic import (
    get_anthropometry,
    check_fit,
    check_reach,
    check_visibility,
    run_mannequin_verification,
    select_bounding_cases,
)


class TestGetAnthropometry(unittest.TestCase):

    def test_male_95th_stature(self):
        data = get_anthropometry("male", 95)
        self.assertEqual(data["stature_mm"], 1880)

    def test_male_95th_functional_reach(self):
        data = get_anthropometry("male", 95)
        self.assertEqual(data["functional_reach_mm"], 820)

    def test_female_5th_stature(self):
        data = get_anthropometry("female", 5)
        self.assertEqual(data["stature_mm"], 1505)

    def test_female_5th_functional_reach(self):
        data = get_anthropometry("female", 5)
        self.assertEqual(data["functional_reach_mm"], 585)

    def test_returns_copy_not_reference(self):
        data = get_anthropometry("male", 50)
        data["stature_mm"] = 9999
        fresh = get_anthropometry("male", 50)
        self.assertEqual(fresh["stature_mm"], 1755)

    def test_invalid_sex_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_anthropometry("unknown", 50)

    def test_invalid_percentile_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_anthropometry("male", 99)

    def test_invalid_percentile_zero_raises(self):
        with self.assertRaises(ValueError):
            get_anthropometry("female", 0)


class TestCheckFit(unittest.TestCase):

    def test_pass_with_ample_clearance(self):
        result = check_fit(2000, 1880, margin_mm=50)
        self.assertTrue(result["pass"])

    def test_margin_value_computed_correctly(self):
        result = check_fit(2000, 1880, margin_mm=50)
        self.assertAlmostEqual(result["margin_mm"], 120.0)

    def test_fail_insufficient_margin(self):
        result = check_fit(1910, 1880, margin_mm=50)
        self.assertFalse(result["pass"])

    def test_pass_at_exact_required_margin(self):
        result = check_fit(1930, 1880, margin_mm=50)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin_mm"], 50.0)

    def test_fail_stature_exceeds_clearance(self):
        result = check_fit(1800, 1880, margin_mm=0)
        self.assertFalse(result["pass"])

    def test_zero_clearance_raises(self):
        with self.assertRaises(ValueError):
            check_fit(0, 1880)

    def test_negative_clearance_raises(self):
        with self.assertRaises(ValueError):
            check_fit(-100, 1880)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            check_fit(2000, 1880, margin_mm=-1)

    def test_required_margin_in_result(self):
        result = check_fit(2000, 1880, margin_mm=75)
        self.assertEqual(result["required_margin_mm"], 75)


class TestCheckReach(unittest.TestCase):

    def test_pass_target_within_reach(self):
        result = check_reach(580, 585)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["shortfall_mm"], 0.0)

    def test_pass_target_exactly_at_reach(self):
        result = check_reach(585, 585)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["shortfall_mm"], 0.0)

    def test_fail_target_beyond_reach(self):
        result = check_reach(700, 640)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["shortfall_mm"], 60.0)

    def test_shortfall_is_zero_on_pass(self):
        result = check_reach(500, 640)
        self.assertTrue(result["pass"])
        self.assertEqual(result["shortfall_mm"], 0.0)

    def test_zero_target_distance_raises(self):
        with self.assertRaises(ValueError):
            check_reach(0, 640)

    def test_negative_target_distance_raises(self):
        with self.assertRaises(ValueError):
            check_reach(-50, 640)

    def test_zero_functional_reach_raises(self):
        with self.assertRaises(ValueError):
            check_reach(500, 0)


class TestCheckVisibility(unittest.TestCase):

    def test_pass_angle_within_cone_no_obstruction(self):
        result = check_visibility(30.0, obstruction_present=False)
        self.assertTrue(result["pass"])
        self.assertTrue(result["within_cone"])

    def test_fail_obstruction_blocks_sightline(self):
        result = check_visibility(30.0, obstruction_present=True)
        self.assertFalse(result["pass"])
        self.assertTrue(result["obstruction"])

    def test_fail_angle_exceeds_cone(self):
        result = check_visibility(60.0, obstruction_present=False)
        self.assertFalse(result["pass"])
        self.assertFalse(result["within_cone"])

    def test_pass_boundary_angle_at_limit(self):
        result = check_visibility(55.0, obstruction_present=False)
        self.assertTrue(result["pass"])
        self.assertTrue(result["within_cone"])

    def test_fail_both_angle_and_obstruction(self):
        result = check_visibility(70.0, obstruction_present=True)
        self.assertFalse(result["pass"])
        self.assertFalse(result["within_cone"])
        self.assertTrue(result["obstruction"])

    def test_result_contains_angle(self):
        result = check_visibility(40.0, obstruction_present=False)
        self.assertAlmostEqual(result["angle_deg"], 40.0)

    def test_result_contains_max_rotation(self):
        result = check_visibility(40.0, obstruction_present=False, max_eye_rotation_deg=45.0)
        self.assertAlmostEqual(result["max_eye_rotation_deg"], 45.0)

    def test_negative_angle_raises(self):
        with self.assertRaises(ValueError):
            check_visibility(-5.0, False)

    def test_zero_max_rotation_raises(self):
        with self.assertRaises(ValueError):
            check_visibility(30.0, False, max_eye_rotation_deg=0)


class TestRunMannequinVerification(unittest.TestCase):

    def test_full_pass_nominal_case(self):
        result = run_mannequin_verification(
            clearance_mm=2000,
            target_distance_mm=600,
            line_of_sight_angle_deg=30.0,
            obstruction_present=False,
            sex="male",
            percentile=95,
        )
        self.assertTrue(result["pass"])
        self.assertTrue(result["fit"]["pass"])
        self.assertTrue(result["reach"]["pass"])
        self.assertTrue(result["visibility"]["pass"])

    def test_fail_on_fit(self):
        result = run_mannequin_verification(
            clearance_mm=1900,
            target_distance_mm=600,
            line_of_sight_angle_deg=30.0,
            obstruction_present=False,
            sex="male",
            percentile=95,
        )
        self.assertFalse(result["pass"])
        self.assertFalse(result["fit"]["pass"])

    def test_fail_on_reach(self):
        result = run_mannequin_verification(
            clearance_mm=2000,
            target_distance_mm=900,
            line_of_sight_angle_deg=30.0,
            obstruction_present=False,
            sex="male",
            percentile=95,
        )
        self.assertFalse(result["pass"])
        self.assertFalse(result["reach"]["pass"])

    def test_fail_on_visibility_obstruction(self):
        result = run_mannequin_verification(
            clearance_mm=2000,
            target_distance_mm=600,
            line_of_sight_angle_deg=20.0,
            obstruction_present=True,
            sex="male",
            percentile=95,
        )
        self.assertFalse(result["pass"])
        self.assertFalse(result["visibility"]["pass"])

    def test_returns_anthropometry_fields(self):
        result = run_mannequin_verification(
            clearance_mm=2000,
            target_distance_mm=550,
            line_of_sight_angle_deg=20.0,
            obstruction_present=False,
            sex="female",
            percentile=5,
        )
        self.assertEqual(result["sex"], "female")
        self.assertEqual(result["percentile"], 5)
        self.assertIn("stature_mm", result)
        self.assertIn("functional_reach_mm", result)
        self.assertEqual(result["stature_mm"], 1505)
        self.assertEqual(result["functional_reach_mm"], 585)

    def test_female_50th_pass(self):
        result = run_mannequin_verification(
            clearance_mm=1900,
            target_distance_mm=600,
            line_of_sight_angle_deg=30.0,
            obstruction_present=False,
            sex="female",
            percentile=50,
        )
        self.assertTrue(result["fit"]["pass"])


class TestSelectBoundingCases(unittest.TestCase):

    def test_fit_only_returns_male_95(self):
        result = select_bounding_cases(["fit"])
        self.assertIn(("male", 95), result)
        self.assertNotIn(("female", 5), result)

    def test_reach_only_returns_female_5(self):
        result = select_bounding_cases(["reach"])
        self.assertIn(("female", 5), result)
        self.assertNotIn(("male", 95), result)

    def test_visibility_returns_both_bounds(self):
        result = select_bounding_cases(["visibility"])
        self.assertIn(("male", 95), result)
        self.assertIn(("female", 5), result)

    def test_all_checks_returns_both_bounds(self):
        result = select_bounding_cases(["fit", "reach", "visibility"])
        self.assertIn(("male", 95), result)
        self.assertIn(("female", 5), result)

    def test_result_has_no_duplicates(self):
        result = select_bounding_cases(["fit", "reach", "visibility"])
        self.assertEqual(len(result), len(set(result)))

    def test_invalid_check_type_raises(self):
        with self.assertRaises(ValueError):
            select_bounding_cases(["bad_check"])

    def test_empty_checks_returns_empty(self):
        result = select_bounding_cases([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
