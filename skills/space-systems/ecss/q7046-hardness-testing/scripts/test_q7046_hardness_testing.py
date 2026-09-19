#!/usr/bin/env python3
"""Contract test for fastener hardness acceptance (offline)."""

import copy
import math
import unittest

from q7046_hardness_testing_logic import (
    HB_VALID_CEILING_HV,
    MIN_READINGS,
    PROPERTY_CLASSES,
    SCALE_HB,
    SCALE_HRC,
    SCALE_HV,
    SPREAD_ALLOWANCE_HV,
    SURFACE_CARBON_LOSS,
    SURFACE_CARBON_PICKUP,
    SURFACE_DELTA_LIMIT_HV,
    SURFACE_OK,
    VERDICT_ACCEPT,
    VERDICT_METHOD_INVALID,
    VERDICT_OUT_OF_BAND,
    VERDICT_SURFACE_FAULT,
    VICKERS_CONSTANT,
    assess_hardness,
    evaluate_readings,
    hardness_band,
    hb_to_hv,
    hrc_to_hv,
    hv_to_hb,
    hv_to_hrc,
    method_validity,
    surface_versus_core,
    to_vickers,
    vickers_diagonal_mm,
)

GOOD_CASE = {
    "property_class": "10.9",
    "scale": SCALE_HV,
    "readings": [335.0, 340.0, 345.0, 350.0],
    "section_thickness_mm": 4.0,
    "test_load_kgf": 30.0,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class BandTests(unittest.TestCase):
    def test_every_class_has_a_floor_below_its_ceiling(self):
        for name in PROPERTY_CLASSES:
            band = hardness_band(name)
            self.assertLess(band["floor"], band["ceiling"])

    def test_stronger_class_sits_higher_in_the_band_table(self):
        self.assertGreater(
            hardness_band("12.9")["floor"], hardness_band("10.9")["floor"]
        )

    def test_band_can_be_expressed_on_the_rockwell_scale(self):
        band = hardness_band("10.9", SCALE_HRC)
        self.assertEqual(band["scale"], SCALE_HRC)
        self.assertAlmostEqual(band["floor"], hv_to_hrc(320.0), places=9)

    def test_band_on_brinell_is_below_the_vickers_numbers(self):
        self.assertLess(
            hardness_band("8.8", SCALE_HB)["floor"],
            hardness_band("8.8", SCALE_HV)["floor"],
        )

    def test_unlisted_class_rejected(self):
        with self.assertRaises(ValueError):
            hardness_band("14.9")

    def test_unknown_scale_rejected(self):
        with self.assertRaises(ValueError):
            hardness_band("10.9", "shore-d")


class ConversionTests(unittest.TestCase):
    def test_tabulated_point_converts_to_its_own_pair(self):
        self.assertAlmostEqual(hv_to_hrc(400.0), 40.8, places=9)

    def test_conversion_round_trips_through_the_curve(self):
        self.assertAlmostEqual(hrc_to_hv(hv_to_hrc(345.0)), 345.0, places=6)

    def test_interpolated_point_lies_between_its_neighbours(self):
        value = hv_to_hrc(410.0)
        self.assertGreater(value, hv_to_hrc(400.0))
        self.assertLess(value, hv_to_hrc(420.0))

    def test_reading_below_the_curve_span_refused(self):
        with self.assertRaises(ValueError):
            hv_to_hrc(150.0)

    def test_reading_above_the_curve_span_refused(self):
        with self.assertRaises(ValueError):
            hv_to_hrc(700.0)

    def test_brinell_round_trips_below_the_ceiling(self):
        self.assertAlmostEqual(hb_to_hv(hv_to_hb(300.0)), 300.0, places=9)

    def test_brinell_refused_above_the_ball_flattening_ceiling(self):
        with self.assertRaises(ValueError):
            hv_to_hb(HB_VALID_CEILING_HV + 10.0)

    def test_vickers_reading_passes_through_unchanged(self):
        self.assertAlmostEqual(to_vickers(340.0, SCALE_HV), 340.0, places=9)

    def test_rockwell_reading_is_brought_onto_the_vickers_axis(self):
        self.assertAlmostEqual(
            to_vickers(36.6, SCALE_HRC), hrc_to_hv(36.6), places=9
        )

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            to_vickers(-300.0, SCALE_HV)


class IndentationTests(unittest.TestCase):
    def test_diagonal_follows_the_load_and_hardness_formula(self):
        expected = math.sqrt(VICKERS_CONSTANT * 30.0 / 340.0)
        self.assertAlmostEqual(vickers_diagonal_mm(30.0, 340.0), expected, places=9)

    def test_heavier_load_leaves_a_larger_diagonal(self):
        self.assertGreater(
            vickers_diagonal_mm(30.0, 340.0), vickers_diagonal_mm(10.0, 340.0)
        )

    def test_harder_material_leaves_a_smaller_diagonal(self):
        self.assertLess(
            vickers_diagonal_mm(30.0, 450.0), vickers_diagonal_mm(30.0, 250.0)
        )

    def test_thick_section_at_a_supported_load_is_valid(self):
        self.assertTrue(method_validity(SCALE_HV, 4.0, 30.0, 340.0)["valid"])

    def test_thin_section_under_a_heavy_load_is_invalid(self):
        outcome = method_validity(SCALE_HV, 0.2, 30.0, 340.0)
        self.assertFalse(outcome["valid"])
        self.assertTrue(any("indentation" in f for f in outcome["findings"]))

    def test_section_landing_exactly_on_the_requirement_is_valid(self):
        required = method_validity(SCALE_HV, 4.0, 30.0, 340.0)["required_section_mm"]
        self.assertTrue(method_validity(SCALE_HV, required, 30.0, 340.0)["valid"])

    def test_unsupported_load_for_the_scale_is_invalid(self):
        outcome = method_validity(SCALE_HRC, 4.0, 30.0, 340.0)
        self.assertFalse(outcome["valid"])

    def test_brinell_on_a_hard_fastener_is_invalid(self):
        outcome = method_validity(SCALE_HB, 8.0, 3000.0, 500.0)
        self.assertFalse(outcome["valid"])

    def test_zero_section_thickness_rejected(self):
        with self.assertRaises(ValueError):
            method_validity(SCALE_HV, 0.0, 30.0, 340.0)


class ReadingSetTests(unittest.TestCase):
    def test_a_clean_set_sits_in_band(self):
        result = evaluate_readings([330.0, 340.0, 350.0], "10.9")
        self.assertTrue(result["in_band"])
        self.assertEqual(result["findings"], [])

    def test_reading_on_the_band_floor_is_in_band(self):
        floor = hardness_band("10.9")["floor"]
        result = evaluate_readings([floor, floor + 5.0, floor + 10.0], "10.9")
        self.assertTrue(result["in_band"])
        self.assertAlmostEqual(result["lowest_hv"], floor, places=9)

    def test_reading_on_the_band_ceiling_is_in_band(self):
        ceiling = hardness_band("10.9")["ceiling"]
        result = evaluate_readings([ceiling - 10.0, ceiling - 5.0, ceiling], "10.9")
        self.assertTrue(result["in_band"])
        self.assertAlmostEqual(result["highest_hv"], ceiling, places=9)

    def test_one_soft_reading_takes_the_set_out_of_band(self):
        result = evaluate_readings([300.0, 340.0, 350.0], "10.9")
        self.assertFalse(result["in_band"])

    def test_a_mean_inside_the_band_does_not_rescue_an_outlier(self):
        result = evaluate_readings([300.0, 350.0, 400.0], "10.9")
        self.assertGreater(result["mean_hv"], hardness_band("10.9")["floor"])
        self.assertFalse(result["in_band"])

    def test_wide_spread_is_a_finding_of_its_own(self):
        result = evaluate_readings([325.0, 350.0, 375.0], "10.9")
        self.assertTrue(result["in_band"])
        self.assertTrue(any("spread" in f for f in result["findings"]))

    def test_spread_landing_on_the_allowance_is_not_a_finding(self):
        low = 330.0
        result = evaluate_readings([low, low + 20.0, low + SPREAD_ALLOWANCE_HV], "10.9")
        self.assertAlmostEqual(result["spread_hv"], SPREAD_ALLOWANCE_HV, places=9)
        self.assertEqual(result["findings"], [])

    def test_rockwell_readings_are_judged_against_the_same_band(self):
        result = evaluate_readings([34.4, 36.6, 38.8], "10.9", SCALE_HRC)
        self.assertTrue(result["in_band"])

    def test_too_few_readings_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_readings([340.0] * (MIN_READINGS - 1), "10.9")

    def test_readings_given_as_a_string_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_readings("340, 345, 350", "10.9")


class SurfaceTests(unittest.TestCase):
    def test_matching_surface_and_core_is_clean(self):
        self.assertEqual(surface_versus_core(340.0, 345.0)["state"], SURFACE_OK)

    def test_soft_surface_is_named_carbon_loss(self):
        outcome = surface_versus_core(340.0, 280.0)
        self.assertEqual(outcome["state"], SURFACE_CARBON_LOSS)

    def test_hard_surface_is_named_carbon_pickup(self):
        outcome = surface_versus_core(340.0, 400.0)
        self.assertEqual(outcome["state"], SURFACE_CARBON_PICKUP)

    def test_difference_landing_on_the_allowance_is_clean(self):
        outcome = surface_versus_core(340.0, 340.0 + SURFACE_DELTA_LIMIT_HV)
        self.assertEqual(outcome["state"], SURFACE_OK)
        self.assertAlmostEqual(outcome["delta_hv"], SURFACE_DELTA_LIMIT_HV, places=9)

    def test_zero_core_hardness_rejected(self):
        with self.assertRaises(ValueError):
            surface_versus_core(0.0, 340.0)


class AssessmentTests(unittest.TestCase):
    def test_clean_case_is_accepted(self):
        self.assertEqual(assess_hardness(_case())["verdict"], VERDICT_ACCEPT)

    def test_soft_lot_is_out_of_band(self):
        result = assess_hardness(_case(readings=[280.0, 285.0, 290.0]))
        self.assertEqual(result["verdict"], VERDICT_OUT_OF_BAND)

    def test_invalid_method_outranks_the_band_verdict(self):
        result = assess_hardness(_case(section_thickness_mm=0.1))
        self.assertEqual(result["verdict"], VERDICT_METHOD_INVALID)

    def test_decarburized_surface_over_a_good_core_is_a_surface_fault(self):
        result = assess_hardness(_case(core_hv=340.0, surface_hv=270.0))
        self.assertEqual(result["verdict"], VERDICT_SURFACE_FAULT)
        self.assertEqual(result["surface"]["state"], SURFACE_CARBON_LOSS)

    def test_findings_carry_through_to_the_assessment(self):
        result = assess_hardness(_case(readings=[280.0, 340.0, 350.0]))
        self.assertTrue(result["findings"])

    def test_case_without_method_data_still_judges_the_band(self):
        case = _case()
        del case["section_thickness_mm"]
        del case["test_load_kgf"]
        result = assess_hardness(case)
        self.assertIsNone(result["method"])
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_missing_property_class_rejected(self):
        case = _case()
        del case["property_class"]
        with self.assertRaises(ValueError):
            assess_hardness(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardness("the bolts felt hard enough")


if __name__ == "__main__":
    unittest.main()
