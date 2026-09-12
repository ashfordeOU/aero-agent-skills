"""
Gate-3 contract tests for initial_flaw_size_assumption_logic.

Run with:  python3 test_initial_flaw_size_assumption.py
Expected:  OK  (all tests pass)

Rules:
- stdlib unittest only; no numpy, no pytest, no network.
- Deterministic and offline.
- No use of security-marking category words anywhere.
"""

import sys
import os
import unittest

# Allow running from the scripts/ directory or the leaf root.
sys.path.insert(0, os.path.dirname(__file__))

from initial_flaw_size_assumption_logic import (
    get_ndt_capability,
    select_most_sensitive_method,
    assign_flaw_shape,
    compute_aspect_ratio,
    determine_initial_flaw,
    determine_initial_flaw_from_methods,
    FlawAssumption,
    VALID_NDT_METHODS,
    VALID_GEOMETRIES,
)


class TestGetNdtCapability(unittest.TestCase):

    def test_pt_returns_expected_depth(self):
        cap = get_ndt_capability("PT")
        self.assertAlmostEqual(cap["a_mm"], 0.75)

    def test_mt_returns_expected_half_length(self):
        cap = get_ndt_capability("MT")
        self.assertAlmostEqual(cap["c_mm"], 1.00)

    def test_et_is_most_sensitive_surface_method(self):
        et = get_ndt_capability("ET")
        pt = get_ndt_capability("PT")
        mt = get_ndt_capability("MT")
        self.assertLess(et["a_mm"], pt["a_mm"])
        self.assertLess(et["a_mm"], mt["a_mm"])

    def test_rt_has_no_surface_half_length(self):
        cap = get_ndt_capability("RT")
        self.assertIsNone(cap["c_mm"])

    def test_ut_has_no_surface_half_length(self):
        cap = get_ndt_capability("UT")
        self.assertIsNone(cap["c_mm"])

    def test_uninspected_default_depth_is_standard_value(self):
        cap = get_ndt_capability("UNINSPECTED")
        self.assertAlmostEqual(cap["a_mm"], 1.27)

    def test_unknown_method_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            get_ndt_capability("XRAY_CUSTOM")
        self.assertIn("XRAY_CUSTOM", str(ctx.exception))

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_ndt_capability("")

    def test_valid_methods_list_is_non_empty(self):
        self.assertGreater(len(VALID_NDT_METHODS), 0)
        self.assertIn("PT", VALID_NDT_METHODS)
        self.assertIn("UNINSPECTED", VALID_NDT_METHODS)


class TestSelectMostSensitiveMethod(unittest.TestCase):

    def test_et_governs_over_pt_and_mt(self):
        result = select_most_sensitive_method(["PT", "MT", "ET"])
        self.assertEqual(result, "ET")

    def test_mt_governs_over_pt_alone(self):
        result = select_most_sensitive_method(["PT", "MT"])
        self.assertEqual(result, "MT")

    def test_single_method_returns_itself(self):
        result = select_most_sensitive_method(["PT"])
        self.assertEqual(result, "PT")

    def test_ut_governs_over_rt(self):
        result = select_most_sensitive_method(["RT", "UT"])
        self.assertEqual(result, "UT")

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_most_sensitive_method([])

    def test_invalid_method_in_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_most_sensitive_method(["PT", "UNKNOWN"])


class TestAssignFlawShape(unittest.TestCase):

    def test_surface_geometry_gives_semi_elliptical(self):
        shape = assign_flaw_shape("surface", "PT")
        self.assertEqual(shape, "surface_semi_elliptical")

    def test_corner_geometry_gives_quarter_circle(self):
        shape = assign_flaw_shape("corner", "MT")
        self.assertEqual(shape, "corner_quarter_circle")

    def test_edge_geometry_gives_quarter_circle(self):
        shape = assign_flaw_shape("edge", "ET")
        self.assertEqual(shape, "corner_quarter_circle")

    def test_hole_geometry_gives_quarter_circle(self):
        shape = assign_flaw_shape("hole", "PT")
        self.assertEqual(shape, "corner_quarter_circle")

    def test_through_geometry_gives_through_crack(self):
        shape = assign_flaw_shape("through", "RT")
        self.assertEqual(shape, "through_crack")

    def test_invalid_geometry_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            assign_flaw_shape("embedded", "UT")
        self.assertIn("embedded", str(ctx.exception))

    def test_valid_geometries_list_contains_expected(self):
        self.assertIn("surface", VALID_GEOMETRIES)
        self.assertIn("corner", VALID_GEOMETRIES)
        self.assertIn("through", VALID_GEOMETRIES)


class TestComputeAspectRatio(unittest.TestCase):

    def test_equal_depth_and_half_length_gives_ratio_one(self):
        ratio = compute_aspect_ratio(1.0, 1.0)
        self.assertAlmostEqual(ratio, 1.0)

    def test_shallow_wide_crack_gives_ratio_below_one(self):
        ratio = compute_aspect_ratio(0.75, 1.25)
        self.assertAlmostEqual(ratio, 0.6)

    def test_deep_narrow_crack_gives_ratio_above_one(self):
        ratio = compute_aspect_ratio(2.0, 1.0)
        self.assertAlmostEqual(ratio, 2.0)

    def test_zero_depth_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_aspect_ratio(0.0, 1.0)

    def test_zero_half_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_aspect_ratio(1.0, 0.0)

    def test_negative_values_raise_value_error(self):
        with self.assertRaises(ValueError):
            compute_aspect_ratio(-0.5, 1.0)


class TestDetermineInitialFlaw(unittest.TestCase):

    def test_pt_surface_flaw_has_correct_depth(self):
        flaw = determine_initial_flaw("PT", "surface")
        self.assertAlmostEqual(flaw.depth_mm, 0.75)

    def test_pt_surface_flaw_shape_is_semi_elliptical(self):
        flaw = determine_initial_flaw("PT", "surface")
        self.assertEqual(flaw.shape, "surface_semi_elliptical")

    def test_mt_surface_flaw_aspect_ratio_correct(self):
        flaw = determine_initial_flaw("MT", "surface")
        self.assertAlmostEqual(flaw.aspect_ratio, 0.50)

    def test_et_corner_flaw_is_quarter_circle(self):
        flaw = determine_initial_flaw("ET", "corner")
        self.assertEqual(flaw.shape, "corner_quarter_circle")
        self.assertAlmostEqual(flaw.aspect_ratio, 1.0)

    def test_et_corner_half_length_equals_depth(self):
        flaw = determine_initial_flaw("ET", "corner")
        self.assertAlmostEqual(flaw.half_length_mm, flaw.depth_mm)

    def test_rt_through_flaw_has_no_aspect_ratio(self):
        flaw = determine_initial_flaw("RT", "through")
        self.assertEqual(flaw.shape, "through_crack")
        self.assertIsNone(flaw.aspect_ratio)
        self.assertIsNone(flaw.half_length_mm)

    def test_ut_through_flaw_depth_is_capability_value(self):
        flaw = determine_initial_flaw("UT", "through")
        self.assertAlmostEqual(flaw.depth_mm, 0.50)

    def test_uninspected_returns_standard_default_depth(self):
        flaw = determine_initial_flaw("UNINSPECTED", "surface")
        self.assertAlmostEqual(flaw.depth_mm, 1.27)

    def test_uninspected_half_length_is_standard_default(self):
        flaw = determine_initial_flaw("UNINSPECTED", "surface")
        self.assertAlmostEqual(flaw.half_length_mm, 1.905)

    def test_compliant_when_depth_below_critical(self):
        flaw = determine_initial_flaw("PT", "surface", critical_flaw_size_mm=5.0)
        self.assertTrue(flaw.compliant)

    def test_non_compliant_when_depth_equals_or_exceeds_critical(self):
        flaw = determine_initial_flaw("UNINSPECTED", "surface", critical_flaw_size_mm=1.0)
        self.assertFalse(flaw.compliant)

    def test_critical_size_zero_raises_value_error(self):
        with self.assertRaises(ValueError):
            determine_initial_flaw("PT", "surface", critical_flaw_size_mm=0.0)

    def test_no_critical_size_defaults_to_compliant(self):
        flaw = determine_initial_flaw("PT", "surface")
        self.assertTrue(flaw.compliant)
        self.assertIsNone(flaw.critical_flaw_size_mm)

    def test_invalid_ndt_method_raises_value_error(self):
        with self.assertRaises(ValueError):
            determine_initial_flaw("GAMMA_RAY", "surface")

    def test_invalid_geometry_raises_value_error(self):
        with self.assertRaises(ValueError):
            determine_initial_flaw("PT", "subsurface_embedded")

    def test_notes_contain_method_name(self):
        flaw = determine_initial_flaw("MT", "surface")
        self.assertIn("MT", flaw.notes)

    def test_flaw_assumption_is_dataclass_with_all_fields(self):
        flaw = determine_initial_flaw("ET", "surface", critical_flaw_size_mm=3.0)
        self.assertIsInstance(flaw, FlawAssumption)
        self.assertIsNotNone(flaw.ndt_method)
        self.assertIsNotNone(flaw.depth_mm)
        self.assertIsNotNone(flaw.shape)
        self.assertIsNotNone(flaw.notes)


class TestDetermineInitialFlawFromMethods(unittest.TestCase):

    def test_most_sensitive_method_governs(self):
        flaw = determine_initial_flaw_from_methods(["PT", "MT", "ET"], "surface")
        self.assertEqual(flaw.ndt_method, "ET")

    def test_superseded_methods_appear_in_notes(self):
        flaw = determine_initial_flaw_from_methods(["PT", "MT"], "surface")
        self.assertIn("PT", flaw.notes)

    def test_single_method_list_returns_that_method(self):
        flaw = determine_initial_flaw_from_methods(["UT"], "through")
        self.assertEqual(flaw.ndt_method, "UT")

    def test_compliance_check_propagated_from_multi_method(self):
        flaw = determine_initial_flaw_from_methods(
            ["PT", "ET"], "surface", critical_flaw_size_mm=10.0
        )
        self.assertTrue(flaw.compliant)

    def test_empty_method_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            determine_initial_flaw_from_methods([], "surface")

    def test_invalid_method_in_multi_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            determine_initial_flaw_from_methods(["PT", "LASER_UT"], "surface")


if __name__ == "__main__":
    unittest.main()
