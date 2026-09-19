"""Contract tests for the hardness reading and conversion logic.

The cases read an indentation the way a reviewer does: whether the impression
sits inside the size band the scale is defined over, whether the force and
the indenter were a standard pairing, whether the impression had room around
it, what number it corresponds to, and whether that number may be carried
onto another scale at all.
"""

import unittest

from q7045_hardness_testing_logic import (
    BRINELL_RATIO_BAND,
    DIAGONAL_ASYMMETRY_LIMIT,
    EDGE_FACTOR,
    SCALES,
    SPACING_FACTOR,
    STANDARD_LOAD_INDICES,
    assess_hardness_test,
    brinell_hardness,
    brinell_load_index,
    convert_hardness,
    indentation_spacing_findings,
    rockwell_c_from_depth,
    vickers_hardness,
)

BALL = 10.0
BRINELL_FORCE = 29420.0
INDENT = 4.0
BRINELL_VALUE = 228.83119821082627
VICKERS_FORCE = 294.2
DIAGONAL = 0.5
VICKERS_VALUE = 222.53287999999998


def _brinell_spec(**overrides):
    spec = {
        "scale": "HBW",
        "force_n": BRINELL_FORCE,
        "ball_diameter_mm": BALL,
        "indent_diameter_mm": INDENT,
        "spacing_mm": 20.0,
        "edge_distance_mm": 15.0,
    }
    spec.update(overrides)
    return spec


def _vickers_spec(**overrides):
    spec = {
        "scale": "HV",
        "force_n": VICKERS_FORCE,
        "diagonals_mm": (0.5, 0.5),
        "spacing_mm": 3.0,
        "edge_distance_mm": 2.0,
    }
    spec.update(overrides)
    return spec


class BrinellTests(unittest.TestCase):
    def test_brinell_number_from_the_impression(self):
        value = brinell_hardness(BRINELL_FORCE, BALL, INDENT)
        self.assertAlmostEqual(value / BRINELL_VALUE, 1.0, places=9)

    def test_a_deeper_impression_reads_softer(self):
        shallow = brinell_hardness(BRINELL_FORCE, BALL, 3.0)
        deep = brinell_hardness(BRINELL_FORCE, BALL, 5.0)
        self.assertGreater(shallow, deep)

    def test_impression_wider_than_the_ball_rejected(self):
        with self.assertRaises(ValueError):
            brinell_hardness(BRINELL_FORCE, BALL, 10.0)

    def test_zero_force_rejected(self):
        with self.assertRaises(ValueError):
            brinell_hardness(0.0, BALL, INDENT)

    def test_load_index_pairs_force_with_ball(self):
        index = brinell_load_index(BRINELL_FORCE, BALL)
        self.assertAlmostEqual(index / 30.0, 1.0, places=3)

    def test_standard_load_indices_are_the_five_usual_pairings(self):
        self.assertEqual(len(STANDARD_LOAD_INDICES), 5)

    def test_quartering_the_ball_area_holds_the_index(self):
        full = brinell_load_index(BRINELL_FORCE, BALL)
        half = brinell_load_index(BRINELL_FORCE / 4.0, BALL / 2.0)
        self.assertAlmostEqual(half / full, 1.0, places=9)


class VickersAndRockwellTests(unittest.TestCase):
    def test_vickers_number_from_the_mean_diagonal(self):
        value = vickers_hardness(VICKERS_FORCE, DIAGONAL)
        self.assertAlmostEqual(value / VICKERS_VALUE, 1.0, places=9)

    def test_vickers_scales_with_the_inverse_square_of_the_diagonal(self):
        small = vickers_hardness(VICKERS_FORCE, 0.25)
        large = vickers_hardness(VICKERS_FORCE, 0.5)
        self.assertAlmostEqual(small / large, 4.0, places=9)

    def test_zero_diagonal_rejected(self):
        with self.assertRaises(ValueError):
            vickers_hardness(VICKERS_FORCE, 0.0)

    def test_rockwell_c_from_permanent_depth(self):
        self.assertAlmostEqual(rockwell_c_from_depth(0.12), 40.0, places=9)

    def test_a_deeper_rockwell_indent_reads_softer(self):
        self.assertAlmostEqual(rockwell_c_from_depth(0.16), 20.0, places=9)

    def test_depth_beyond_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            rockwell_c_from_depth(0.25)

    def test_negative_depth_rejected(self):
        with self.assertRaises(ValueError):
            rockwell_c_from_depth(-0.1)


class SpacingTests(unittest.TestCase):
    def test_roomy_impression_is_silent(self):
        self.assertEqual(indentation_spacing_findings(1.0, 5.0, 5.0), [])

    def test_impression_exactly_at_the_spacing_minimum_is_silent(self):
        self.assertEqual(indentation_spacing_findings(1.0, SPACING_FACTOR, 5.0), [])

    def test_impression_exactly_at_the_edge_minimum_is_silent(self):
        self.assertEqual(indentation_spacing_findings(1.0, 5.0, EDGE_FACTOR), [])

    def test_crowded_neighbour_is_reported(self):
        notes = indentation_spacing_findings(1.0, 1.5, 5.0)
        self.assertEqual(len(notes), 1)
        self.assertIn("centre spacing", notes[0])

    def test_edge_and_neighbour_are_both_reported(self):
        self.assertEqual(len(indentation_spacing_findings(1.0, 1.5, 1.0)), 2)

    def test_unmeasured_distances_raise_nothing(self):
        self.assertEqual(indentation_spacing_findings(1.0), [])


class ConversionTests(unittest.TestCase):
    def test_tabulated_level_converts_exactly(self):
        self.assertAlmostEqual(convert_hardness(300.0, "HV", "HBW"), 285.0, places=9)

    def test_conversion_between_the_tabulated_levels_interpolates(self):
        self.assertAlmostEqual(convert_hardness(275.0, "HV", "HBW"), 261.5, places=9)

    def test_conversion_is_reversible_on_a_tabulated_level(self):
        self.assertAlmostEqual(convert_hardness(285.0, "HBW", "HV"), 300.0, places=9)

    def test_same_scale_returns_the_value(self):
        self.assertAlmostEqual(convert_hardness(275.0, "HV", "HV"), 275.0, places=9)

    def test_untabulated_target_level_refuses(self):
        with self.assertRaises(ValueError):
            convert_hardness(200.0, "HV", "HRC")

    def test_bracket_with_an_untabulated_end_refuses(self):
        with self.assertRaises(ValueError):
            convert_hardness(225.0, "HV", "HRC")

    def test_value_above_the_table_refuses(self):
        with self.assertRaises(ValueError):
            convert_hardness(700.0, "HV", "HBW")

    def test_value_below_the_table_refuses(self):
        with self.assertRaises(ValueError):
            convert_hardness(80.0, "HV", "HBW")

    def test_unknown_scale_rejected(self):
        with self.assertRaises(ValueError):
            convert_hardness(300.0, "HV", "HSD")

    def test_three_scales_are_covered(self):
        self.assertEqual(len(SCALES), 3)


class AssessmentTests(unittest.TestCase):
    def test_clean_brinell_reading_is_accepted(self):
        result = assess_hardness_test(_brinell_spec())
        self.assertTrue(result["reading_accepted"])
        self.assertAlmostEqual(result["hardness"] / BRINELL_VALUE, 1.0, places=9)

    def test_diameter_ratio_is_reported(self):
        result = assess_hardness_test(_brinell_spec())
        low, high = BRINELL_RATIO_BAND
        self.assertGreater(result["diameter_ratio"], low)
        self.assertLess(result["diameter_ratio"], high)

    def test_oversize_impression_is_reported(self):
        result = assess_hardness_test(_brinell_spec(indent_diameter_mm=7.0))
        self.assertFalse(result["reading_accepted"])
        self.assertIn("ball ratio", result["findings"][0])

    def test_non_standard_load_pairing_is_reported(self):
        result = assess_hardness_test(_brinell_spec(force_n=18000.0))
        self.assertFalse(result["reading_accepted"])
        self.assertIn("load index", " ".join(result["findings"]))

    def test_crowded_brinell_impression_is_reported(self):
        result = assess_hardness_test(_brinell_spec(spacing_mm=6.0))
        self.assertFalse(result["reading_accepted"])

    def test_clean_vickers_reading_is_accepted(self):
        result = assess_hardness_test(_vickers_spec())
        self.assertTrue(result["reading_accepted"])
        self.assertAlmostEqual(result["hardness"] / VICKERS_VALUE, 1.0, places=9)

    def test_lopsided_vickers_impression_is_reported(self):
        result = assess_hardness_test(_vickers_spec(diagonals_mm=(0.45, 0.55)))
        self.assertFalse(result["reading_accepted"])
        self.assertIn("diagonals differ", result["findings"][0])

    def test_small_diagonal_difference_is_tolerated(self):
        result = assess_hardness_test(_vickers_spec(diagonals_mm=(0.495, 0.505)))
        self.assertLess(result["diagonal_asymmetry"], DIAGONAL_ASYMMETRY_LIMIT)
        self.assertTrue(result["reading_accepted"])

    def test_single_diagonal_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardness_test(_vickers_spec(diagonals_mm=(0.5,)))

    def test_rockwell_reading_is_accepted(self):
        result = assess_hardness_test(
            {"scale": "HRC", "permanent_depth_mm": 0.12}
        )
        self.assertTrue(result["reading_accepted"])
        self.assertAlmostEqual(result["hardness"], 40.0, places=9)

    def test_rockwell_below_the_usable_scale_is_reported(self):
        result = assess_hardness_test(
            {"scale": "HRC", "permanent_depth_mm": 0.17}
        )
        self.assertFalse(result["reading_accepted"])

    def test_reading_carried_onto_the_reporting_scale(self):
        result = assess_hardness_test(_vickers_spec(report_scale="HBW"))
        self.assertIsNotNone(result["converted_hardness"])
        self.assertLess(result["converted_hardness"], result["hardness"])

    def test_refused_conversion_becomes_a_finding(self):
        result = assess_hardness_test(_brinell_spec(report_scale="HRC"))
        self.assertFalse(result["reading_accepted"])
        self.assertIn("conversion refused", " ".join(result["findings"]))

    def test_reading_outside_the_acceptance_band_is_reported(self):
        result = assess_hardness_test(_brinell_spec(acceptance_band=(100.0, 200.0)))
        self.assertFalse(result["reading_accepted"])
        self.assertIn("acceptance band", " ".join(result["findings"]))

    def test_reading_inside_the_acceptance_band_is_accepted(self):
        result = assess_hardness_test(_brinell_spec(acceptance_band=(200.0, 250.0)))
        self.assertTrue(result["reading_accepted"])

    def test_inverted_acceptance_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardness_test(_brinell_spec(acceptance_band=(250.0, 200.0)))

    def test_unknown_scale_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardness_test(_brinell_spec(scale="HSD"))

    def test_missing_measurement_rejected(self):
        spec = _brinell_spec()
        del spec["indent_diameter_mm"]
        with self.assertRaises(ValueError):
            assess_hardness_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardness_test(["HBW"])


if __name__ == "__main__":
    unittest.main()
