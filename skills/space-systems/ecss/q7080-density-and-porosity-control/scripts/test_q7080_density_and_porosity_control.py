#!/usr/bin/env python3
"""Contract test for density and porosity control (offline)."""

import copy
import unittest

from q7080_density_and_porosity_control_logic import (
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_REVIEW,
    archimedes_density,
    assess_density_and_porosity,
    ct_pore_population,
    governing_pore_limit,
    grade_pore_size,
    grade_relative_density,
    method_agreement,
    relative_density,
)

GOOD_CASE = {
    "dry_mass_g": 100.0,
    "suspended_mass_g": 62.5,
    "fluid_density_g_cm3": 1.0,
    "reference_density_g_cm3": 2.672,
    "minimum_relative_density": 0.995,
    "largest_pore_um": 90.0,
    "pore_limit_um": 200.0,
    "wall_thickness_mm": 4.0,
    "max_pore_wall_fraction": 0.10,
    "ct_pore_diameters_um": [30.0, 45.0, 80.0],
    "ct_detection_limit_um": 25.0,
    "max_indications": 5,
    "sectioned_relative_density": 0.9975,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class ArchimedesTests(unittest.TestCase):
    def test_density_from_the_two_weighings(self):
        value = archimedes_density(100.0, 62.5, 1.0)
        self.assertAlmostEqual(value, 100.0 / 37.5, places=9)

    def test_fluid_density_scales_the_result(self):
        value = archimedes_density(100.0, 62.5, 0.997)
        self.assertAlmostEqual(value, 100.0 / 37.5 * 0.997, places=9)

    def test_suspended_mass_at_or_above_the_dry_mass_rejected(self):
        with self.assertRaises(ValueError):
            archimedes_density(100.0, 100.0, 1.0)

    def test_zero_fluid_density_rejected(self):
        with self.assertRaises(ValueError):
            archimedes_density(100.0, 62.5, 0.0)

    def test_non_numeric_mass_rejected(self):
        with self.assertRaises(ValueError):
            archimedes_density("100", 62.5, 1.0)


class RelativeDensityTests(unittest.TestCase):
    def test_fraction_of_the_reference_alloy_density(self):
        self.assertAlmostEqual(relative_density(2.6400, 2.6700), 2.64 / 2.67, places=9)

    def test_small_overshoot_is_measurement_scatter(self):
        self.assertAlmostEqual(relative_density(2.6800, 2.6700), 2.68 / 2.67, places=9)

    def test_large_overshoot_is_an_inconsistent_record(self):
        with self.assertRaises(ValueError):
            relative_density(2.7400, 2.6700)

    def test_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            relative_density(2.6400, 0.0)


class GradeRelativeDensityTests(unittest.TestCase):
    def test_comfortable_density_accepts(self):
        result = grade_relative_density(0.9990, 0.9950)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["porosity_fraction"], 0.0010, places=9)

    def test_density_exactly_on_the_floor_is_a_review_not_a_reject(self):
        result = grade_relative_density(0.9950, 0.9950)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_density_below_the_floor_rejects(self):
        result = grade_relative_density(0.9900, 0.9950)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("porosity" in text for text in result["findings"]))

    def test_thin_margin_is_a_review(self):
        result = grade_relative_density(0.9960, 0.9950)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_floor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            grade_relative_density(0.9990, 1.1)


class GoverningLimitTests(unittest.TestCase):
    def test_thin_wall_sets_the_limit(self):
        result = governing_pore_limit(200.0, 1.0, 0.10)
        self.assertAlmostEqual(result["limit_um"], 100.0, places=9)
        self.assertEqual(result["governed_by"], "wall-fraction")

    def test_thick_wall_leaves_the_drawing_limit(self):
        result = governing_pore_limit(200.0, 4.0, 0.10)
        self.assertAlmostEqual(result["limit_um"], 200.0, places=9)
        self.assertEqual(result["governed_by"], "drawing")

    def test_equal_limits_are_reported_as_the_drawing_limit(self):
        result = governing_pore_limit(200.0, 2.0, 0.10)
        self.assertAlmostEqual(result["limit_um"], 200.0, places=9)
        self.assertEqual(result["governed_by"], "drawing")

    def test_wall_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            governing_pore_limit(200.0, 2.0, 1.5)

    def test_zero_wall_rejected(self):
        with self.assertRaises(ValueError):
            governing_pore_limit(200.0, 0.0, 0.10)


class PoreSizeTests(unittest.TestCase):
    def test_pore_inside_the_limit_accepts(self):
        result = grade_pore_size(90.0, 200.0, 4.0, 0.10)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_pore_exactly_on_the_limit_accepts(self):
        result = grade_pore_size(200.0, 200.0, 4.0, 0.10)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_pore_over_the_wall_fraction_limit_rejects(self):
        result = grade_pore_size(150.0, 200.0, 1.0, 0.10)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("wall-fraction" in text for text in result["findings"]))

    def test_negative_pore_size_rejected(self):
        with self.assertRaises(ValueError):
            grade_pore_size(-10.0, 200.0, 4.0, 0.10)


class CtPopulationTests(unittest.TestCase):
    def test_clean_population_accepts(self):
        result = ct_pore_population([30.0, 45.0, 80.0], 25.0, 100.0, 5)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["resolved_count"], 3)

    def test_pores_below_detection_are_counted_separately(self):
        result = ct_pore_population([10.0, 15.0, 30.0], 25.0, 100.0, 5)
        self.assertEqual(result["resolved_count"], 1)
        self.assertEqual(result["below_detection_count"], 2)

    def test_oversize_indication_rejects(self):
        result = ct_pore_population([30.0, 120.0], 25.0, 100.0, 5)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["oversize_count"], 1)

    def test_indication_exactly_on_the_size_limit_accepts(self):
        result = ct_pore_population([100.0], 25.0, 100.0, 5)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_scan_coarser_than_the_limit_it_grades_rejects(self):
        result = ct_pore_population([], 150.0, 100.0, 5)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("cannot see" in text for text in result["findings"]))

    def test_too_many_resolved_indications_is_a_review(self):
        result = ct_pore_population([30.0] * 7, 25.0, 100.0, 5)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_largest_resolved_is_reported(self):
        result = ct_pore_population([30.0, 45.0, 80.0], 25.0, 100.0, 5)
        self.assertAlmostEqual(result["largest_resolved_um"], 80.0, places=9)

    def test_non_sequence_population_rejected(self):
        with self.assertRaises(ValueError):
            ct_pore_population(30.0, 25.0, 100.0, 5)

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            ct_pore_population([30.0], 25.0, 100.0, -1)


class MethodAgreementTests(unittest.TestCase):
    def test_methods_within_tolerance_accept(self):
        result = method_agreement(0.9980, 0.9965, 0.003)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["difference"], 0.0015, places=9)

    def test_difference_exactly_on_the_tolerance_accepts(self):
        result = method_agreement(0.9980, 0.9950, 0.003)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_methods_apart_is_a_review(self):
        result = method_agreement(0.9980, 0.9900, 0.003)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            method_agreement(0.9980, 0.9965, -0.001)


class AssessDensityAndPorosityTests(unittest.TestCase):
    def test_compliant_part_accepts_with_no_findings(self):
        result = assess_density_and_porosity(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["driving_characteristics"], [])

    def test_measured_density_is_reported(self):
        result = assess_density_and_porosity(_case())
        self.assertAlmostEqual(result["measured_density_g_cm3"], 100.0 / 37.5, places=9)

    def test_low_density_drives_the_verdict(self):
        result = assess_density_and_porosity(_case(reference_density_g_cm3=2.70))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("relative-density", result["driving_characteristics"])

    def test_single_large_pore_rejects_a_dense_part(self):
        result = assess_density_and_porosity(
            _case(largest_pore_um=260.0, ct_pore_diameters_um=[30.0, 260.0])
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("pore-size", result["driving_characteristics"])

    def test_thin_wall_pulls_the_governing_limit_down(self):
        result = assess_density_and_porosity(
            _case(wall_thickness_mm=0.8, largest_pore_um=90.0)
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["pore_size"]["governed_by"], "wall-fraction")

    def test_blind_scan_drives_the_verdict(self):
        result = assess_density_and_porosity(_case(ct_detection_limit_um=250.0))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("pore-population", result["driving_characteristics"])

    def test_method_disagreement_is_reported(self):
        result = assess_density_and_porosity(_case(sectioned_relative_density=0.9700))
        self.assertEqual(result["verdict"], VERDICT_REVIEW)
        self.assertIn("method-agreement", result["driving_characteristics"])

    def test_case_without_a_section_carries_no_agreement_record(self):
        case = _case()
        case["sectioned_relative_density"] = None
        result = assess_density_and_porosity(case)
        self.assertIsNone(result["method_agreement"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_density_and_porosity([2.67])


if __name__ == "__main__":
    unittest.main()
