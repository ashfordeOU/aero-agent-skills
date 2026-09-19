"""Contract tests for the metallic test-piece geometry and preparation logic."""

import math
import unittest

from q7045_test_piece_requirements_logic import (
    GRIPPED_END_ROUGHNESS_LIMIT_UM,
    MIN_TRANSITION_RADIUS_FRACTION,
    PARALLEL_ROUGHNESS_LIMIT_UM,
    PROPORTIONAL_COEFFICIENT,
    SECTION_TOLERANCE_FRACTION,
    assess_test_piece,
    characteristic_dimension_mm,
    cross_section_area_mm2,
    gauge_length_agrees,
    marking_ok,
    minimum_parallel_length_mm,
    minimum_transition_radius_mm,
    proportional_gauge_length_mm,
    roughness_ok,
    section_tolerance_ok,
)


def round_piece(**overrides):
    """A 10 mm round proportional tensile piece in an aluminium alloy."""
    area = math.pi * 25.0
    gauge = PROPORTIONAL_COEFFICIENT * math.sqrt(area)
    spec = {
        "shape": "round",
        "dimensions": {"diameter_mm": 10.0},
        "gauge_length_mm": gauge,
        "parallel_length_mm": gauge + 8.0,
        "transition_radius_mm": 10.0,
        "gripped_end_length_mm": 40.0,
        "grip_length_mm": 35.0,
        "section_tolerance_mm": 0.02,
        "parallel_roughness_um": 0.4,
        "gripped_end_roughness_um": 1.6,
        "material_family": "aluminium-alloy",
        "final_light_cut": True,
        "marking": {
            "identity": "TP-014",
            "orientation": "L",
            "location": "shoulder",
        },
    }
    spec.update(overrides)
    return spec


class CrossSectionTests(unittest.TestCase):
    def test_round_area_from_the_diameter(self):
        self.assertAlmostEqual(
            cross_section_area_mm2("round", {"diameter_mm": 10.0}),
            math.pi * 25.0,
            places=9,
        )

    def test_rectangular_area_from_thickness_and_width(self):
        area = cross_section_area_mm2(
            "rectangular", {"thickness_mm": 3.0, "width_mm": 12.5}
        )
        self.assertAlmostEqual(area, 37.5, places=9)

    def test_width_narrower_than_thickness_rejected(self):
        with self.assertRaises(ValueError):
            cross_section_area_mm2(
                "rectangular", {"thickness_mm": 12.5, "width_mm": 3.0}
            )

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            cross_section_area_mm2("round", {"diameter_mm": 0.0})

    def test_unknown_shape_rejected(self):
        with self.assertRaises(ValueError):
            cross_section_area_mm2("hexagonal", {"diameter_mm": 10.0})

    def test_non_numeric_dimension_rejected(self):
        with self.assertRaises(ValueError):
            cross_section_area_mm2("round", {"diameter_mm": "10"})

    def test_characteristic_dimension_is_width_for_a_flat(self):
        self.assertAlmostEqual(
            characteristic_dimension_mm(
                "rectangular", {"thickness_mm": 3.0, "width_mm": 12.5}
            ),
            12.5,
            places=9,
        )


class GaugeLengthTests(unittest.TestCase):
    def test_proportional_gauge_length_follows_the_square_root_of_area(self):
        self.assertAlmostEqual(
            proportional_gauge_length_mm(100.0),
            PROPORTIONAL_COEFFICIENT * 10.0,
            places=9,
        )

    def test_a_larger_section_gets_a_longer_gauge_length(self):
        self.assertGreater(
            proportional_gauge_length_mm(400.0), proportional_gauge_length_mm(100.0)
        )

    def test_drawn_length_equal_to_derived_agrees(self):
        derived = proportional_gauge_length_mm(100.0)
        result = gauge_length_agrees(derived, derived)
        self.assertAlmostEqual(result["deviation_fraction"], 0.0, places=9)
        self.assertTrue(result["within"])

    def test_deviation_exactly_at_the_tolerance_is_accepted(self):
        derived = 50.0
        result = gauge_length_agrees(55.0, derived, tolerance=0.10)
        self.assertAlmostEqual(result["deviation_fraction"], 0.10, places=9)
        self.assertTrue(result["within"])

    def test_deviation_well_past_the_tolerance_is_refused(self):
        result = gauge_length_agrees(80.0, 50.0, tolerance=0.10)
        self.assertFalse(result["within"])

    def test_negative_gauge_length_rejected(self):
        with self.assertRaises(ValueError):
            proportional_gauge_length_mm(-1.0)


class GeometryMinimumTests(unittest.TestCase):
    def test_round_parallel_length_adds_half_a_diameter(self):
        minimum = minimum_parallel_length_mm("round", {"diameter_mm": 10.0}, 50.0)
        self.assertAlmostEqual(minimum, 55.0, places=9)

    def test_flat_parallel_length_adds_more_than_a_round_one(self):
        flat = minimum_parallel_length_mm(
            "rectangular", {"thickness_mm": 3.0, "width_mm": 10.0}, 50.0
        )
        rnd = minimum_parallel_length_mm("round", {"diameter_mm": 10.0}, 50.0)
        self.assertGreater(flat, rnd)

    def test_transition_radius_minimum_scales_with_the_section(self):
        self.assertAlmostEqual(
            minimum_transition_radius_mm("round", {"diameter_mm": 10.0}),
            10.0 * MIN_TRANSITION_RADIUS_FRACTION,
            places=9,
        )

    def test_zero_gauge_length_rejected_by_the_parallel_minimum(self):
        with self.assertRaises(ValueError):
            minimum_parallel_length_mm("round", {"diameter_mm": 10.0}, 0.0)


class ToleranceAndFinishTests(unittest.TestCase):
    def test_tolerance_is_graded_relative_to_the_dimension(self):
        wide = section_tolerance_ok(50.0, 0.05)
        small = section_tolerance_ok(3.0, 0.05)
        self.assertTrue(wide["ok"])
        self.assertFalse(small["ok"])

    def test_tolerance_exactly_at_the_relative_limit_is_accepted(self):
        dimension = 10.0
        result = section_tolerance_ok(dimension, dimension * SECTION_TOLERANCE_FRACTION)
        self.assertAlmostEqual(result["relative"], SECTION_TOLERANCE_FRACTION, places=9)
        self.assertTrue(result["ok"])

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            section_tolerance_ok(10.0, -0.01)

    def test_roughness_exactly_at_the_limit_is_accepted(self):
        self.assertTrue(
            roughness_ok(PARALLEL_ROUGHNESS_LIMIT_UM, PARALLEL_ROUGHNESS_LIMIT_UM)
        )

    def test_gripped_ends_carry_a_looser_limit_than_the_parallel_length(self):
        self.assertGreater(GRIPPED_END_ROUGHNESS_LIMIT_UM, PARALLEL_ROUGHNESS_LIMIT_UM)
        self.assertFalse(roughness_ok(1.6, PARALLEL_ROUGHNESS_LIMIT_UM))
        self.assertTrue(roughness_ok(1.6, GRIPPED_END_ROUGHNESS_LIMIT_UM))


class MarkingTests(unittest.TestCase):
    def test_complete_marking_on_a_shoulder_is_accepted(self):
        result = marking_ok(
            {"identity": "TP-1", "orientation": "ST", "location": "shoulder"}
        )
        self.assertTrue(result["ok"])

    def test_missing_orientation_is_a_finding(self):
        result = marking_ok({"identity": "TP-1", "location": "shoulder"})
        self.assertFalse(result["ok"])
        self.assertTrue(any("orientation" in f for f in result["findings"]))

    def test_marking_inside_the_parallel_length_is_a_finding(self):
        result = marking_ok(
            {"identity": "TP-1", "orientation": "L", "location": "parallel-length"}
        )
        self.assertTrue(any("consumes" in f for f in result["findings"]))

    def test_non_mapping_marking_rejected(self):
        with self.assertRaises(ValueError):
            marking_ok("TP-1")


class AssessmentTests(unittest.TestCase):
    def test_a_conforming_round_piece_is_acceptable(self):
        result = assess_test_piece(round_piece())
        self.assertEqual(result["status"], "acceptable")
        self.assertEqual(result["findings"], [])

    def test_short_parallel_length_is_a_geometry_finding(self):
        spec = round_piece()
        spec["parallel_length_mm"] = spec["gauge_length_mm"] + 1.0
        result = assess_test_piece(spec)
        self.assertTrue(any("transition fillet" in f for f in result["findings"]))

    def test_tight_transition_radius_is_a_geometry_finding(self):
        result = assess_test_piece(round_piece(transition_radius_mm=2.0))
        self.assertTrue(any("transition radius" in f for f in result["findings"]))

    def test_copied_gauge_length_from_another_section_is_caught(self):
        result = assess_test_piece(round_piece(gauge_length_mm=25.0))
        self.assertTrue(any("proportional" in f for f in result["findings"]))

    def test_non_proportional_piece_is_allowed_but_flagged_for_reporting(self):
        result = assess_test_piece(round_piece(gauge_length_mm=25.0, proportional=False))
        self.assertTrue(any("non-proportional" in f for f in result["findings"]))

    def test_coarse_parallel_length_finish_is_a_finding(self):
        result = assess_test_piece(round_piece(parallel_roughness_um=1.6))
        self.assertTrue(any("crack starters" in f for f in result["findings"]))

    def test_coarse_gripped_end_finish_alone_does_not_fail_the_parallel_limit(self):
        result = assess_test_piece(round_piece(gripped_end_roughness_um=3.2))
        self.assertEqual(result["findings"], [])

    def test_cold_work_sensitive_family_needs_a_final_light_cut(self):
        result = assess_test_piece(
            round_piece(material_family="titanium-alloy", final_light_cut=False)
        )
        self.assertTrue(any("final light cut" in f for f in result["findings"]))

    def test_gripped_end_shorter_than_the_machine_grip_is_a_finding(self):
        result = assess_test_piece(round_piece(gripped_end_length_mm=20.0))
        self.assertTrue(any("machine grips" in f for f in result["findings"]))

    def test_loose_section_tolerance_on_a_small_piece_is_a_finding(self):
        spec = round_piece(
            dimensions={"diameter_mm": 3.0}, section_tolerance_mm=0.05
        )
        area = math.pi * 2.25
        spec["gauge_length_mm"] = PROPORTIONAL_COEFFICIENT * math.sqrt(area)
        spec["parallel_length_mm"] = spec["gauge_length_mm"] + 3.0
        spec["transition_radius_mm"] = 4.0
        result = assess_test_piece(spec)
        self.assertTrue(any("stress calculation" in f for f in result["findings"]))

    def test_missing_spec_key_rejected(self):
        spec = round_piece()
        del spec["transition_radius_mm"]
        with self.assertRaises(ValueError):
            assess_test_piece(spec)

    def test_non_boolean_final_light_cut_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_piece(round_piece(final_light_cut="yes"))

    def test_derived_gauge_length_travels_with_the_result(self):
        result = assess_test_piece(round_piece())
        self.assertAlmostEqual(
            result["derived_gauge_length_mm"],
            PROPORTIONAL_COEFFICIENT * math.sqrt(math.pi * 25.0),
            places=9,
        )


if __name__ == "__main__":
    unittest.main()
