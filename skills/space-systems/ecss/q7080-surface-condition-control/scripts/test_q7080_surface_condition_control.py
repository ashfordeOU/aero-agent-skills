#!/usr/bin/env python3
"""Contract test for surface condition control (offline)."""

import copy
import unittest

from q7080_surface_condition_control_logic import (
    AS_BUILT_CATEGORIES,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_REVIEW,
    adhered_particle_density,
    assess_surface_condition,
    expected_as_built_ra,
    grade_roughness,
    grade_surface,
    sampling_coverage,
)

PROCESS = {
    "vertical_ra_um": 12.0,
    "downskin_threshold_deg": 45.0,
    "downskin_growth_factor": 1.5,
}

WALL = {
    "id": "wall-a",
    "category": "vertical-wall",
    "overhang_angle_deg": 90.0,
    "readings_um": [11.0, 12.4, 10.8],
    "reading_parameter": "Ra",
    "limit_um": 16.0,
    "limit_parameter": "Ra",
    "adhered_particle_count": 4,
    "area_cm2": 20.0,
    "particle_limit_per_cm2": 0.5,
}

SEAL_FACE = {
    "id": "seal-face",
    "category": "machined",
    "readings_um": [1.2, 1.4, 1.1],
    "reading_parameter": "Ra",
    "limit_um": 1.6,
    "limit_parameter": "Ra",
}

GOOD_CASE = {
    "surfaces": [WALL, SEAL_FACE],
    "declared_ids": ["wall-a", "seal-face"],
    "process": PROCESS,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


def _surface(base, **overrides):
    surface = copy.deepcopy(base)
    surface.update(overrides)
    return surface


class ExpectedRoughnessTests(unittest.TestCase):
    def test_vertical_wall_keeps_the_baseline(self):
        self.assertAlmostEqual(expected_as_built_ra(12.0, 90.0, 45.0, 1.5), 12.0,
                               places=9)

    def test_angle_exactly_on_the_threshold_keeps_the_baseline(self):
        self.assertAlmostEqual(expected_as_built_ra(12.0, 45.0, 45.0, 1.5), 12.0,
                               places=9)

    def test_shallow_overhang_grows_the_roughness(self):
        value = expected_as_built_ra(12.0, 20.0, 45.0, 1.5)
        self.assertAlmostEqual(value, 12.0 * (1.0 + 1.5 * 25.0 / 45.0), places=9)

    def test_horizontal_downskin_is_the_worst_case(self):
        value = expected_as_built_ra(12.0, 0.0, 45.0, 1.5)
        self.assertAlmostEqual(value, 30.0, places=9)

    def test_angle_above_ninety_rejected(self):
        with self.assertRaises(ValueError):
            expected_as_built_ra(12.0, 120.0, 45.0, 1.5)

    def test_negative_angle_rejected(self):
        with self.assertRaises(ValueError):
            expected_as_built_ra(12.0, -5.0, 45.0, 1.5)

    def test_zero_baseline_rejected(self):
        with self.assertRaises(ValueError):
            expected_as_built_ra(0.0, 45.0, 45.0, 1.5)


class RoughnessGradingTests(unittest.TestCase):
    def test_every_reading_inside_the_limit_accepts(self):
        result = grade_roughness([11.0, 12.4, 10.8], 16.0, "Ra", "Ra")
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["worst_um"], 12.4, places=9)

    def test_reading_exactly_on_the_limit_accepts(self):
        result = grade_roughness([16.0], 16.0, "Ra", "Ra")
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_one_reading_over_the_limit_rejects_the_surface(self):
        result = grade_roughness([11.0, 19.0, 10.8], 16.0, "Ra", "Ra")
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["over_limit"], 1)

    def test_mean_inside_the_limit_does_not_rescue_a_high_reading(self):
        result = grade_roughness([4.0, 19.0], 16.0, "Ra", "Ra")
        self.assertAlmostEqual(result["mean_um"], 11.5, places=9)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_rz_readings_against_an_ra_limit_rejected(self):
        with self.assertRaises(ValueError):
            grade_roughness([40.0], 16.0, "Rz", "Ra")

    def test_rz_readings_against_an_rz_limit_are_graded(self):
        result = grade_roughness([40.0], 80.0, "Rz", "Rz")
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["parameter"], "Rz")

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            grade_roughness([11.0], 16.0, "Sa", "Sa")

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            grade_roughness([], 16.0, "Ra", "Ra")

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            grade_roughness([-1.0], 16.0, "Ra", "Ra")


class ParticleTests(unittest.TestCase):
    def test_particles_are_graded_per_unit_area(self):
        result = adhered_particle_density(4, 20.0, 0.5)
        self.assertAlmostEqual(result["density_per_cm2"], 0.2, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_same_count_on_a_small_face_rejects(self):
        result = adhered_particle_density(4, 2.0, 0.5)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_density_exactly_on_the_limit_accepts(self):
        result = adhered_particle_density(10, 20.0, 0.5)
        self.assertAlmostEqual(result["density_per_cm2"], 0.5, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_non_integer_count_rejected(self):
        with self.assertRaises(ValueError):
            adhered_particle_density(4.5, 20.0, 0.5)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            adhered_particle_density(4, 0.0, 0.5)


class SurfaceGradingTests(unittest.TestCase):
    def test_compliant_wall_accepts(self):
        record = grade_surface(WALL, PROCESS)
        self.assertEqual(record["verdict"], VERDICT_ACCEPT)
        self.assertEqual(record["findings"], [])

    def test_expected_roughness_is_reported_for_an_as_built_surface(self):
        record = grade_surface(WALL, PROCESS)
        self.assertAlmostEqual(record["expected_as_built_ra_um"], 12.0, places=9)

    def test_machined_surface_carries_no_as_built_expectation(self):
        record = grade_surface(SEAL_FACE, PROCESS)
        self.assertIsNone(record["expected_as_built_ra_um"])
        self.assertIn("machined", (record["category"],))

    def test_unachievable_downskin_limit_is_a_review(self):
        surface = _surface(
            WALL,
            id="duct-underside",
            category="down-skin",
            overhang_angle_deg=20.0,
            readings_um=[13.0, 14.0],
            limit_um=15.0,
            adhered_particle_count=None,
        )
        record = grade_surface(surface, PROCESS)
        self.assertEqual(record["verdict"], VERDICT_REVIEW)
        self.assertTrue(any("finishing operation" in text for text in record["findings"]))

    def test_downskin_over_its_limit_still_rejects(self):
        surface = _surface(
            WALL,
            id="duct-underside",
            category="down-skin",
            overhang_angle_deg=20.0,
            readings_um=[24.0, 26.0],
            limit_um=15.0,
            adhered_particle_count=None,
        )
        record = grade_surface(surface, PROCESS)
        self.assertEqual(record["verdict"], VERDICT_REJECT)

    def test_particle_density_can_drive_a_surface(self):
        surface = _surface(WALL, adhered_particle_count=40)
        record = grade_surface(surface, PROCESS)
        self.assertEqual(record["verdict"], VERDICT_REJECT)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            grade_surface(_surface(WALL, category="etched"), PROCESS)

    def test_non_mapping_surface_rejected(self):
        with self.assertRaises(ValueError):
            grade_surface(["wall-a"], PROCESS)

    def test_as_built_categories_exclude_machined(self):
        self.assertNotIn("machined", AS_BUILT_CATEGORIES)


class CoverageTests(unittest.TestCase):
    def test_every_declared_surface_measured_accepts(self):
        result = sampling_coverage([WALL, SEAL_FACE], ["wall-a", "seal-face"])
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["measured"], 2)

    def test_unmeasured_declared_surface_rejects(self):
        result = sampling_coverage([WALL], ["wall-a", "seal-face"])
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["missing"], ["seal-face"])

    def test_surface_present_with_no_readings_counts_as_unmeasured(self):
        empty = _surface(SEAL_FACE, readings_um=[])
        result = sampling_coverage([WALL, empty], ["wall-a", "seal-face"])
        self.assertEqual(result["missing"], ["seal-face"])

    def test_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            sampling_coverage([WALL], [])


class AssessSurfaceConditionTests(unittest.TestCase):
    def test_compliant_part_accepts_with_no_findings(self):
        result = assess_surface_condition(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["driving_surfaces"], [])

    def test_rough_surface_drives_the_verdict_and_is_named(self):
        rough = _surface(WALL, readings_um=[11.0, 22.0])
        result = assess_surface_condition(_case(surfaces=[rough, SEAL_FACE]))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertEqual(result["driving_surfaces"], ["wall-a"])

    def test_missing_measurement_rejects_the_part(self):
        result = assess_surface_condition(
            _case(surfaces=[WALL], declared_ids=["wall-a", "seal-face"])
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("unverified" in text for text in result["findings"]))

    def test_unachievable_limit_reviews_rather_than_rejects(self):
        duct = _surface(
            WALL,
            id="duct-underside",
            category="down-skin",
            overhang_angle_deg=20.0,
            readings_um=[13.0, 14.0],
            limit_um=15.0,
            adhered_particle_count=None,
        )
        result = assess_surface_condition(
            _case(surfaces=[duct], declared_ids=["duct-underside"])
        )
        self.assertEqual(result["verdict"], VERDICT_REVIEW)
        self.assertEqual(result["driving_surfaces"], ["duct-underside"])

    def test_declared_ids_default_to_the_measured_surfaces(self):
        case = _case()
        del case["declared_ids"]
        result = assess_surface_condition(case)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_empty_surface_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_condition(_case(surfaces=[]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_surface_condition("wall-a")


if __name__ == "__main__":
    unittest.main()
