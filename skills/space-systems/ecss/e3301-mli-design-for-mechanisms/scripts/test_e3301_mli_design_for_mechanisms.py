"""Contract tests for the clause 4.7.4.3 MLI-on-a-mechanism design logic."""

import unittest

from e3301_mli_design_for_mechanisms_logic import (
    STEFAN_BOLTZMANN,
    assess_mli_design,
    blanket_thickness_mm,
    clearance_margin_mm,
    cutout_margin_mm,
    effective_emittance,
    ground_path_resistance_ohm,
    grounding_points_required,
    open_area_fraction,
    parasitic_heat_w,
    required_clearance_mm,
    required_cutout_diameter_mm,
    swept_diameter_mm,
)


def base_spec(**overrides):
    """Return a representative blanket over a rotating deployment hinge."""
    spec = {
        "layer_count": 20,
        "layer_pitch_mm": 0.25,
        "cover_thickness_mm": 0.15,
        "sweep_envelope_mm": 8.0,
        "tolerance_stack_mm": 1.5,
        "billow_allowance_mm": 3.0,
        "available_gap_mm": 25.0,
        "moving_part_diameter_mm": 40.0,
        "radial_excursion_mm": 1.0,
        "radial_clearance_mm": 5.0,
        "cutout_diameter_mm": 60.0,
        "blanket_area_m2": 0.6,
        "cutout_areas_m2": [0.002827],
        "mli_emittance": 0.02,
        "open_emittance": 0.85,
        "hot_temperature_k": 300.0,
        "sink_temperature_k": 4.0,
        "parasitic_budget_w": 8.0,
        "ground_points": 4,
        "max_area_per_point_m2": 0.25,
        "ground_segment_resistances_ohm": [0.3, 0.2, 0.15],
        "max_ground_resistance_ohm": 1.0,
    }
    spec.update(overrides)
    return spec


class ThicknessAndClearanceTests(unittest.TestCase):
    def test_thickness_counts_layers_pitch_and_cover(self):
        self.assertAlmostEqual(blanket_thickness_mm(20, 0.25, 0.15), 5.15, places=12)

    def test_cover_is_optional(self):
        self.assertAlmostEqual(blanket_thickness_mm(20, 0.25), 5.0, places=12)

    def test_zero_layers_rejected(self):
        with self.assertRaises(ValueError):
            blanket_thickness_mm(0, 0.25)

    def test_non_integer_layer_count_rejected(self):
        with self.assertRaises(ValueError):
            blanket_thickness_mm(20.5, 0.25)

    def test_required_clearance_sums_every_contributor(self):
        self.assertAlmostEqual(required_clearance_mm(8.0, 5.15, 1.5, 3.0), 17.65, places=12)

    def test_billow_allowance_is_part_of_the_stack(self):
        without = required_clearance_mm(8.0, 5.15, 1.5, 0.0)
        with_billow = required_clearance_mm(8.0, 5.15, 1.5, 3.0)
        self.assertAlmostEqual(with_billow - without, 3.0, places=12)

    def test_margin_is_available_minus_required(self):
        self.assertAlmostEqual(clearance_margin_mm(25.0, 17.65), 7.35, places=12)

    def test_zero_available_gap_rejected(self):
        with self.assertRaises(ValueError):
            clearance_margin_mm(0.0, 17.65)


class CutoutTests(unittest.TestCase):
    def test_excursion_widens_the_swept_diameter(self):
        self.assertAlmostEqual(swept_diameter_mm(40.0, 1.0), 42.0, places=12)

    def test_no_excursion_leaves_the_part_diameter(self):
        self.assertAlmostEqual(swept_diameter_mm(40.0), 40.0, places=12)

    def test_cutout_adds_clearance_on_both_sides(self):
        self.assertAlmostEqual(required_cutout_diameter_mm(42.0, 5.0), 52.0, places=12)

    def test_cutout_margin_is_diametral(self):
        self.assertAlmostEqual(cutout_margin_mm(60.0, 52.0), 8.0, places=12)

    def test_negative_excursion_rejected(self):
        with self.assertRaises(ValueError):
            swept_diameter_mm(40.0, -1.0)

    def test_zero_radial_clearance_rejected(self):
        with self.assertRaises(ValueError):
            required_cutout_diameter_mm(42.0, 0.0)


class OpticalTests(unittest.TestCase):
    def test_open_fraction_is_the_area_quotient(self):
        self.assertAlmostEqual(open_area_fraction([0.06, 0.06], 0.6), 0.2, places=12)

    def test_cutouts_larger_than_the_blanket_rejected(self):
        with self.assertRaises(ValueError):
            open_area_fraction([0.4, 0.4], 0.6)

    def test_unperforated_blanket_keeps_its_own_emittance(self):
        self.assertAlmostEqual(effective_emittance(0.02, 0.85, 0.0), 0.02, places=12)

    def test_fully_open_area_takes_the_open_emittance(self):
        self.assertAlmostEqual(effective_emittance(0.02, 0.85, 1.0), 0.85, places=12)

    def test_effective_emittance_is_area_weighted(self):
        self.assertAlmostEqual(
            effective_emittance(0.02, 0.85, 0.25), 0.02 * 0.75 + 0.85 * 0.25, places=12
        )

    def test_opening_that_insulates_better_than_the_blanket_rejected(self):
        with self.assertRaises(ValueError):
            effective_emittance(0.85, 0.02, 0.1)

    def test_parasitic_heat_follows_the_quartic_difference(self):
        heat = parasitic_heat_w(0.024, 0.6, 300.0, 4.0)
        expected = STEFAN_BOLTZMANN * 0.024 * 0.6 * (300.0 ** 4 - 4.0 ** 4)
        self.assertAlmostEqual(heat, expected, places=12)

    def test_colder_part_leaks_less(self):
        hot = parasitic_heat_w(0.024, 0.6, 300.0, 4.0)
        cool = parasitic_heat_w(0.024, 0.6, 250.0, 4.0)
        self.assertGreater(hot, cool)


class GroundingTests(unittest.TestCase):
    def test_point_count_rounds_up_to_cover_the_area(self):
        self.assertEqual(grounding_points_required(0.6, 0.25), 3)

    def test_exact_multiple_does_not_gain_a_spurious_point(self):
        self.assertEqual(grounding_points_required(0.5, 0.25), 2)

    def test_zero_area_per_point_rejected(self):
        with self.assertRaises(ValueError):
            grounding_points_required(0.6, 0.0)

    def test_path_resistance_is_the_series_sum(self):
        self.assertAlmostEqual(ground_path_resistance_ohm([0.3, 0.2, 0.15]), 0.65, places=12)

    def test_empty_path_rejected(self):
        with self.assertRaises(ValueError):
            ground_path_resistance_ohm([])

    def test_negative_segment_rejected(self):
        with self.assertRaises(ValueError):
            ground_path_resistance_ohm([0.3, -0.1])


class AssessMliDesignTests(unittest.TestCase):
    def test_representative_blanket_is_compliant(self):
        result = assess_mli_design(base_spec())
        self.assertTrue(result["compliant"], result["findings"])
        self.assertTrue(result["motion_unimpeded"])

    def test_thin_gap_fouls_the_motion(self):
        result = assess_mli_design(base_spec(available_gap_mm=12.0))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["motion_unimpeded"])
        self.assertTrue(any("foul the motion" in f for f in result["findings"]))

    def test_undersized_cutout_edge_enters_the_swept_path(self):
        result = assess_mli_design(base_spec(cutout_diameter_mm=45.0))
        self.assertFalse(result["motion_unimpeded"])
        self.assertTrue(any("swept path" in f for f in result["findings"]))

    def test_large_cutouts_break_the_parasitic_budget(self):
        result = assess_mli_design(base_spec(cutout_areas_m2=[0.15]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("parasitic leak" in f for f in result["findings"]))
        self.assertGreater(result["effective_emittance"], 0.2)

    def test_too_few_ground_points_is_a_finding(self):
        result = assess_mli_design(base_spec(ground_points=2))
        self.assertEqual(result["ground_points_required"], 3)
        self.assertTrue(any("ground points" in f for f in result["findings"]))

    def test_high_ground_resistance_is_a_finding(self):
        result = assess_mli_design(base_spec(max_ground_resistance_ohm=0.5))
        self.assertTrue(any("ohm" in f for f in result["findings"]))

    def test_billow_allowance_moves_the_clearance_requirement(self):
        tight = assess_mli_design(base_spec(billow_allowance_mm=0.0))
        loose = assess_mli_design(base_spec(billow_allowance_mm=3.0))
        self.assertAlmostEqual(
            loose["required_clearance_mm"] - tight["required_clearance_mm"], 3.0, places=12
        )

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["max_ground_resistance_ohm"]
        with self.assertRaises(ValueError):
            assess_mli_design(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_mli_design(["layer_count", 20])


if __name__ == "__main__":
    unittest.main()
