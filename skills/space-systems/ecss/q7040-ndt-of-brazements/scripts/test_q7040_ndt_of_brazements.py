#!/usr/bin/env python3
"""Contract test for NDT selection on a brazement (offline)."""

import copy
import unittest

from q7040_ndt_of_brazements_logic import (
    BRAZE_CLASSES,
    JOINT_GEOMETRIES,
    LEAK_TEST,
    RADIOGRAPHY,
    ULTRASONICS,
    VISUAL,
    WITNESS_COUPONS,
    accepted_void_mm,
    method_out_resolves_class,
    ndt_sample_size,
    plan_ndt,
    radiography_admissible,
    resolvable_void_mm,
    select_volumetric_method,
    ultrasonics_admissible,
)

SLEEVE_JOINT = {
    "geometry": "sleeve",
    "access": "two-sided",
    "thickness_mm": 4.0,
    "braze_class": "class-a",
    "hermetic": True,
    "lot_size": 12,
}

LAP_JOINT = {
    "geometry": "lap",
    "access": "single-sided",
    "thickness_mm": 6.0,
    "braze_class": "class-b",
    "hermetic": False,
    "lot_size": 40,
}


def _joint(base, **overrides):
    joint = copy.deepcopy(base)
    joint.update(overrides)
    return joint


class AdmissibilityTests(unittest.TestCase):
    def test_a_butt_joint_with_two_sided_access_admits_radiography(self):
        self.assertTrue(radiography_admissible("butt", "two-sided", 8.0))

    def test_a_lap_joint_never_admits_radiography(self):
        self.assertFalse(radiography_admissible("lap", "two-sided", 8.0))

    def test_single_sided_access_rules_radiography_out(self):
        self.assertFalse(radiography_admissible("butt", "single-sided", 8.0))

    def test_radiography_is_admissible_exactly_at_its_thickness_ceiling(self):
        self.assertTrue(radiography_admissible("butt", "two-sided", 25.0))
        self.assertFalse(radiography_admissible("butt", "two-sided", 26.0))

    def test_a_lap_joint_with_one_coupling_face_admits_ultrasonics(self):
        self.assertTrue(ultrasonics_admissible("lap", "single-sided", 6.0))

    def test_ultrasonics_is_admissible_exactly_at_its_thickness_floor(self):
        self.assertTrue(ultrasonics_admissible("lap", "single-sided", 1.0))
        self.assertFalse(ultrasonics_admissible("lap", "single-sided", 0.4))

    def test_an_unreachable_joint_admits_neither_method(self):
        self.assertFalse(radiography_admissible("butt", "unreachable", 5.0))
        self.assertFalse(ultrasonics_admissible("lap", "unreachable", 5.0))

    def test_an_unknown_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            radiography_admissible("scarf", "two-sided", 5.0)

    def test_a_zero_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            ultrasonics_admissible("lap", "single-sided", 0.0)


class SelectionTests(unittest.TestCase):
    def test_a_lap_plane_goes_to_ultrasonics(self):
        self.assertEqual(
            select_volumetric_method("lap", "two-sided", 6.0)["method"], ULTRASONICS
        )

    def test_a_butt_plane_goes_to_radiography(self):
        self.assertEqual(
            select_volumetric_method("butt", "two-sided", 6.0)["method"], RADIOGRAPHY
        )

    def test_a_sleeve_joint_with_one_sided_access_falls_to_ultrasonics(self):
        self.assertEqual(
            select_volumetric_method("sleeve", "single-sided", 6.0)["method"],
            ULTRASONICS,
        )

    def test_a_joint_with_no_admissible_method_returns_none_with_a_finding(self):
        result = select_volumetric_method("tee", "unreachable", 6.0)
        self.assertIsNone(result["method"])
        self.assertTrue(any("witness coupons" in f for f in result["findings"]))

    def test_a_very_thin_tee_joint_still_reaches_radiography(self):
        self.assertEqual(
            select_volumetric_method("tee", "two-sided", 0.5)["method"], RADIOGRAPHY
        )


class ResolutionTests(unittest.TestCase):
    def test_radiographic_resolution_scales_with_thickness(self):
        self.assertAlmostEqual(
            resolvable_void_mm(RADIOGRAPHY, 20.0), 0.4, places=9
        )

    def test_radiographic_resolution_has_an_absolute_floor(self):
        self.assertAlmostEqual(
            resolvable_void_mm(RADIOGRAPHY, 1.0), 0.10, places=9
        )

    def test_ultrasonic_resolution_has_its_own_floor(self):
        self.assertAlmostEqual(resolvable_void_mm(ULTRASONICS, 5.0), 0.50, places=9)

    def test_the_accepted_void_widens_as_the_class_relaxes(self):
        self.assertGreater(
            accepted_void_mm("class-c", 10.0), accepted_void_mm("class-a", 10.0)
        )

    def test_a_method_exactly_on_the_accepted_void_still_counts_as_covering(self):
        self.assertAlmostEqual(
            resolvable_void_mm(RADIOGRAPHY, 2.0), accepted_void_mm("class-a", 2.0),
            places=9,
        )
        self.assertTrue(method_out_resolves_class(RADIOGRAPHY, "class-a", 2.0))

    def test_a_thick_tight_class_section_is_not_covered(self):
        self.assertFalse(method_out_resolves_class(ULTRASONICS, "class-a", 2.0))

    def test_an_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            resolvable_void_mm("eddy-current-testing", 5.0)


class SampleSizeTests(unittest.TestCase):
    def test_the_top_class_is_inspected_throughout(self):
        self.assertEqual(ndt_sample_size(12, "class-a"), 12)

    def test_a_sampled_class_takes_its_declared_fraction(self):
        self.assertEqual(ndt_sample_size(100, "class-b"), 10)

    def test_the_floor_holds_on_a_small_lot(self):
        self.assertEqual(ndt_sample_size(4, "class-b"), 3)

    def test_the_sample_never_exceeds_the_lot(self):
        for lot in (1, 2, 3, 7, 51, 100):
            for braze_class in BRAZE_CLASSES:
                self.assertLessEqual(ndt_sample_size(lot, braze_class), lot)

    def test_the_sample_is_a_whole_number_of_joints_rounded_up(self):
        self.assertEqual(ndt_sample_size(101, "class-c"), 3)

    def test_a_zero_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            ndt_sample_size(0, "class-a")

    def test_a_non_integer_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            ndt_sample_size(12.5, "class-a")


class PlanTests(unittest.TestCase):
    def test_visual_inspection_is_always_on_the_list(self):
        for geometry in JOINT_GEOMETRIES:
            plan = plan_ndt(_joint(SLEEVE_JOINT, geometry=geometry))
            self.assertIn(VISUAL, plan["methods"])

    def test_a_hermetic_joint_carries_a_leak_test(self):
        self.assertIn(LEAK_TEST, plan_ndt(SLEEVE_JOINT)["methods"])

    def test_a_non_hermetic_joint_carries_no_leak_test(self):
        self.assertNotIn(LEAK_TEST, plan_ndt(LAP_JOINT)["methods"])

    def test_the_lap_joint_plan_uses_ultrasonics(self):
        plan = plan_ndt(LAP_JOINT)
        self.assertEqual(plan["volumetric_method"], ULTRASONICS)
        self.assertIn(ULTRASONICS, plan["methods"])

    def test_an_unreachable_joint_escalates_to_witness_coupons(self):
        plan = plan_ndt(_joint(SLEEVE_JOINT, access="unreachable"))
        self.assertIn(WITNESS_COUPONS, plan["methods"])
        self.assertIsNone(plan["volumetric_method"])

    def test_the_bottom_class_owes_no_volumetric_method_by_default(self):
        plan = plan_ndt(_joint(LAP_JOINT, braze_class="class-c"))
        self.assertFalse(plan["coverage_required"])
        self.assertIsNone(plan["volumetric_method"])

    def test_a_declared_coverage_requirement_overrides_the_class_default(self):
        plan = plan_ndt(
            _joint(LAP_JOINT, braze_class="class-c", coverage_required=True)
        )
        self.assertEqual(plan["volumetric_method"], ULTRASONICS)

    def test_a_method_too_coarse_for_the_class_raises_a_finding(self):
        plan = plan_ndt(
            _joint(LAP_JOINT, braze_class="class-a", thickness_mm=2.0)
        )
        self.assertTrue(any("coarser" in f for f in plan["findings"]))

    def test_the_top_class_plan_reports_full_coverage(self):
        plan = plan_ndt(SLEEVE_JOINT)
        self.assertTrue(plan["full_coverage"])
        self.assertEqual(plan["sample_size"], 12)

    def test_a_sampled_plan_does_not_report_full_coverage(self):
        plan = plan_ndt(LAP_JOINT)
        self.assertFalse(plan["full_coverage"])
        self.assertEqual(plan["sample_size"], 4)

    def test_a_non_mapping_brazement_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_ndt("sleeve joint")

    def test_a_non_boolean_hermetic_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_ndt(_joint(SLEEVE_JOINT, hermetic="yes"))

    def test_an_unknown_class_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_ndt(_joint(SLEEVE_JOINT, braze_class="class-z"))


if __name__ == "__main__":
    unittest.main()
