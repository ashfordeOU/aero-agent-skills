#!/usr/bin/env python3
"""Contract test for non-destructive testing of built parts (offline)."""

import copy
import math
import unittest

from q7080_ndt_of_am_parts_logic import (
    CRITICALITY_CATEGORIES,
    DEFAULT_NDT_POLICY,
    FULL_VOLUMETRIC,
    NDT_METHODS,
    SAMPLED_VOLUMETRIC,
    SURFACE_ONLY,
    assess_ndt_plan,
    ct_detectable_flaw_mm,
    ct_voxel_size_mm,
    method_applicability,
    method_detectability_mm,
    radiographic_detectable_flaw_mm,
    required_coverage,
    ultrasonic_detectable_flaw_mm,
    ultrasonic_wavelength_mm,
    validate_ndt_policy,
)

GOOD_CASE = {
    "criticality": "catastrophic",
    "methods": ["computed-tomography"],
    "critical_flaw_size_mm": 0.6,
    "pixel_pitch_mm": 0.2,
    "source_to_object_mm": 100.0,
    "source_to_detector_mm": 400.0,
    "max_radiographic_path_mm": 60.0,
    "ct_max_path_mm": 90.0,
    "surface_roughness_um": 12.0,
    "has_enclosed_channels": True,
    "sound_velocity_m_s": 5900.0,
    "probe_frequency_mhz": 5.0,
    "section_thickness_mm": 12.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_ndt_policy(DEFAULT_NDT_POLICY), DEFAULT_NDT_POLICY)

    def test_policy_covers_every_criticality_category(self):
        for category in CRITICALITY_CATEGORIES:
            self.assertIn(category, DEFAULT_NDT_POLICY["coverage"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_ndt_policy("default")

    def test_policy_missing_a_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_NDT_POLICY)
        del broken["coverage"]["major"]
        with self.assertRaises(ValueError):
            validate_ndt_policy(broken)

    def test_policy_sample_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_NDT_POLICY)
        broken["sample_fraction"][SAMPLED_VOLUMETRIC] = 1.4
        with self.assertRaises(ValueError):
            validate_ndt_policy(broken)

    def test_policy_sub_voxel_claim_rejected(self):
        broken = copy.deepcopy(DEFAULT_NDT_POLICY)
        broken["voxels_per_flaw"] = 0.5
        with self.assertRaises(ValueError):
            validate_ndt_policy(broken)


class TomographyTests(unittest.TestCase):
    def test_voxel_shrinks_with_magnification(self):
        near = ct_voxel_size_mm(0.2, 100.0, 400.0)
        far = ct_voxel_size_mm(0.2, 200.0, 400.0)
        self.assertAlmostEqual(near, 0.05, places=9)
        self.assertAlmostEqual(far, 0.1, places=9)

    def test_detector_behind_the_source_rejected(self):
        with self.assertRaises(ValueError):
            ct_voxel_size_mm(0.2, 400.0, 100.0)

    def test_zero_pixel_pitch_rejected(self):
        with self.assertRaises(ValueError):
            ct_voxel_size_mm(0.0, 100.0, 400.0)

    def test_detectable_flaw_is_several_voxels(self):
        self.assertAlmostEqual(ct_detectable_flaw_mm(0.05), 0.15, places=9)

    def test_sub_voxel_flaw_claim_rejected(self):
        with self.assertRaises(ValueError):
            ct_detectable_flaw_mm(0.05, voxels_per_flaw=0.4)

    def test_path_beyond_penetration_is_not_applicable(self):
        result = method_applicability(
            "computed-tomography",
            _case(GOOD_CASE, max_radiographic_path_mm=140.0),
        )
        self.assertFalse(result["applicable"])
        self.assertTrue(any("penetrate" in f for f in result["findings"]))

    def test_path_exactly_on_the_penetration_limit_is_applicable(self):
        case = _case(GOOD_CASE, max_radiographic_path_mm=90.0, ct_max_path_mm=90.0)
        self.assertAlmostEqual(
            case["max_radiographic_path_mm"], case["ct_max_path_mm"], places=9
        )
        self.assertTrue(method_applicability("computed-tomography", case)["applicable"])


class UltrasonicTests(unittest.TestCase):
    def test_wavelength_falls_with_frequency(self):
        self.assertAlmostEqual(ultrasonic_wavelength_mm(5900.0, 5.0), 1.18, places=9)
        self.assertLess(
            ultrasonic_wavelength_mm(5900.0, 10.0),
            ultrasonic_wavelength_mm(5900.0, 5.0),
        )

    def test_detectable_flaw_is_half_a_wavelength(self):
        self.assertAlmostEqual(
            ultrasonic_detectable_flaw_mm(5900.0, 5.0), 0.59, places=9
        )

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            ultrasonic_wavelength_mm(5900.0, 0.0)

    def test_rough_as_built_surface_blocks_the_method(self):
        result = method_applicability("ultrasonic", GOOD_CASE)
        self.assertFalse(result["applicable"])
        self.assertTrue(any("roughness" in f for f in result["findings"]))

    def test_enclosed_channels_block_the_method(self):
        case = _case(GOOD_CASE, surface_roughness_um=1.6)
        result = method_applicability("ultrasonic", case)
        self.assertFalse(result["applicable"])
        self.assertTrue(any("channel" in f for f in result["findings"]))

    def test_machined_open_part_is_applicable(self):
        case = _case(GOOD_CASE, surface_roughness_um=1.6, has_enclosed_channels=False)
        self.assertTrue(method_applicability("ultrasonic", case)["applicable"])


class RadiographyTests(unittest.TestCase):
    def test_square_on_flaw_is_uninspectable(self):
        with self.assertRaises(ValueError):
            radiographic_detectable_flaw_mm(12.0, flaw_tilt_deg=90.0)

    def test_detectable_flaw_grows_with_tilt(self):
        square = radiographic_detectable_flaw_mm(12.0, flaw_tilt_deg=0.0)
        tilted = radiographic_detectable_flaw_mm(12.0, flaw_tilt_deg=60.0)
        self.assertAlmostEqual(square, 0.24, places=9)
        self.assertAlmostEqual(tilted, 0.24 / math.cos(math.radians(60.0)), places=9)
        self.assertGreater(tilted, square)

    def test_negative_tilt_rejected(self):
        with self.assertRaises(ValueError):
            radiographic_detectable_flaw_mm(12.0, flaw_tilt_deg=-5.0)

    def test_channels_raise_a_projection_finding_without_blocking(self):
        result = method_applicability("radiographic", GOOD_CASE)
        self.assertTrue(result["applicable"])
        self.assertTrue(any("projection" in f for f in result["findings"]))


class CoverageTests(unittest.TestCase):
    def test_catastrophic_demands_full_volumetric(self):
        coverage = required_coverage("catastrophic")
        self.assertEqual(coverage["coverage"], FULL_VOLUMETRIC)
        self.assertAlmostEqual(coverage["sample_fraction"], 1.0, places=9)

    def test_major_is_sampled(self):
        coverage = required_coverage("major")
        self.assertEqual(coverage["coverage"], SAMPLED_VOLUMETRIC)
        self.assertTrue(coverage["volumetric_required"])

    def test_minor_needs_no_volumetric_method(self):
        coverage = required_coverage("minor")
        self.assertEqual(coverage["coverage"], SURFACE_ONLY)
        self.assertFalse(coverage["volumetric_required"])

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            required_coverage("fairly-important")


class PlanTests(unittest.TestCase):
    def test_capable_tomography_setup_is_compliant(self):
        result = assess_ndt_plan(GOOD_CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "volumetric-coverage-demonstrated")
        self.assertEqual(result["credited_methods"], ["computed-tomography"])

    def test_detectability_ratio_reported(self):
        result = assess_ndt_plan(GOOD_CASE)
        self.assertAlmostEqual(result["best_detectable_flaw_mm"], 0.15, places=9)
        self.assertAlmostEqual(result["detectability_ratio"], 4.0, places=9)

    def test_setup_exactly_on_the_critical_flaw_still_passes(self):
        case = _case(GOOD_CASE, critical_flaw_size_mm=0.15)
        result = assess_ndt_plan(case)
        self.assertAlmostEqual(result["best_detectable_flaw_mm"], 0.15, places=9)
        self.assertTrue(result["compliant"])

    def test_coarse_setup_fails_a_catastrophic_part(self):
        case = _case(GOOD_CASE, critical_flaw_size_mm=0.05)
        result = assess_ndt_plan(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["verdict"], "volumetric-coverage-not-demonstrated")
        self.assertIsNone(result["best_detectable_flaw_mm"])

    def test_inapplicable_method_is_not_credited(self):
        case = _case(GOOD_CASE, methods=["ultrasonic"])
        result = assess_ndt_plan(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["credited_methods"], [])

    def test_minor_part_closes_on_surface_inspection(self):
        case = _case(GOOD_CASE, criticality="minor", methods=["ultrasonic"])
        result = assess_ndt_plan(case)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "surface-inspection-sufficient")

    def test_empty_method_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_ndt_plan(_case(GOOD_CASE, methods=[]))

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            assess_ndt_plan(_case(GOOD_CASE, methods=["dye-penetrant-volumetric"]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_ndt_plan("catastrophic")

    def test_every_method_name_is_evaluable(self):
        case = _case(
            GOOD_CASE,
            methods=list(NDT_METHODS),
            surface_roughness_um=1.6,
            has_enclosed_channels=False,
        )
        result = assess_ndt_plan(case)
        self.assertEqual(len(result["methods"]), len(NDT_METHODS))
        for entry in result["methods"]:
            self.assertIn(entry["method"], NDT_METHODS)

    def test_detectability_is_method_specific(self):
        ct = method_detectability_mm("computed-tomography", GOOD_CASE)
        ut = method_detectability_mm("ultrasonic", GOOD_CASE)
        self.assertNotAlmostEqual(ct, ut, places=6)


if __name__ == "__main__":
    unittest.main()
