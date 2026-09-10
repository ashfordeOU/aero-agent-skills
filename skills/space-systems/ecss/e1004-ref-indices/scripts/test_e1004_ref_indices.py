#!/usr/bin/env python3
"""Offline, deterministic unittest for e1004_ref_indices_logic."""

import unittest

from e1004_ref_indices_logic import (
    classify_f107_activity_level,
    get_albedo_ir_reference,
    get_solar_index,
    interpolate_solar_cycle_index,
    is_reference_data_valid,
    reference_data_review,
    source_reference_for_parameter,
    thermal_case_reference,
    validate_index_value,
)


class ClassifyF107ActivityLevelTests(unittest.TestCase):
    def test_low_value_is_minimum(self):
        self.assertEqual(classify_f107_activity_level(70.0), "minimum")

    def test_boundary_value_is_minimum(self):
        self.assertEqual(classify_f107_activity_level(100.0), "minimum")

    def test_just_above_minimum_boundary_is_mean(self):
        self.assertEqual(classify_f107_activity_level(100.1), "mean")

    def test_boundary_value_is_mean(self):
        self.assertEqual(classify_f107_activity_level(180.0), "mean")

    def test_just_above_mean_boundary_is_maximum(self):
        self.assertEqual(classify_f107_activity_level(180.1), "maximum")

    def test_high_value_is_maximum(self):
        self.assertEqual(classify_f107_activity_level(230.0), "maximum")

    def test_below_physical_range_raises(self):
        with self.assertRaises(ValueError):
            classify_f107_activity_level(10.0)

    def test_above_physical_range_raises(self):
        with self.assertRaises(ValueError):
            classify_f107_activity_level(500.0)


class GetSolarIndexTests(unittest.TestCase):
    def test_known_minimum_values(self):
        self.assertEqual(
            get_solar_index("minimum"),
            {"f107_solar_flux_sfu": 70.0, "sunspot_number": 0.0},
        )

    def test_known_maximum_values(self):
        result = get_solar_index("maximum")
        self.assertEqual(result["f107_solar_flux_sfu"], 230.0)
        self.assertEqual(result["sunspot_number"], 180.0)

    def test_returned_dict_is_a_copy(self):
        result = get_solar_index("mean")
        result["f107_solar_flux_sfu"] = -1.0
        self.assertEqual(get_solar_index("mean")["f107_solar_flux_sfu"], 140.0)

    def test_unrecognized_level_raises(self):
        with self.assertRaises(ValueError):
            get_solar_index("extreme")


class GetAlbedoIrReferenceTests(unittest.TestCase):
    def test_known_mean_values(self):
        self.assertEqual(
            get_albedo_ir_reference("mean"),
            {"earth_albedo": 0.30, "earth_ir_flux_w_m2": 237.0},
        )

    def test_unrecognized_level_raises(self):
        with self.assertRaises(ValueError):
            get_albedo_ir_reference("bogus")


class ValidateIndexValueTests(unittest.TestCase):
    def test_in_range_value_has_no_violations(self):
        self.assertEqual(validate_index_value("earth_albedo", 0.3), [])

    def test_low_boundary_is_valid(self):
        self.assertEqual(validate_index_value("f107_solar_flux_sfu", 50.0), [])

    def test_high_boundary_is_valid(self):
        self.assertEqual(validate_index_value("f107_solar_flux_sfu", 300.0), [])

    def test_below_range_is_flagged(self):
        violations = validate_index_value("f107_solar_flux_sfu", 49.9)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "value_out_of_documented_range")

    def test_above_range_is_flagged(self):
        violations = validate_index_value("earth_albedo", 1.5)
        self.assertEqual(len(violations), 1)

    def test_unrecognized_dataset_raises(self):
        with self.assertRaises(ValueError):
            validate_index_value("unknown_dataset", 1.0)


class SourceReferenceForParameterTests(unittest.TestCase):
    def test_known_parameter_returns_citation(self):
        self.assertIn(
            "Annex F", source_reference_for_parameter("f107_solar_flux_sfu")
        )

    def test_unrecognized_parameter_raises(self):
        with self.assertRaises(ValueError):
            source_reference_for_parameter("unobtainium_index")


class InterpolateSolarCycleIndexTests(unittest.TestCase):
    def test_phase_zero_matches_minimum(self):
        self.assertEqual(
            interpolate_solar_cycle_index("f107_solar_flux_sfu", 0.0), 70.0
        )

    def test_phase_half_matches_mean(self):
        self.assertEqual(
            interpolate_solar_cycle_index("f107_solar_flux_sfu", 0.5), 140.0
        )

    def test_phase_one_matches_maximum(self):
        self.assertEqual(
            interpolate_solar_cycle_index("f107_solar_flux_sfu", 1.0), 230.0
        )

    def test_phase_quarter_is_midway_to_mean(self):
        # halfway between minimum (70.0) and mean (140.0)
        self.assertAlmostEqual(
            interpolate_solar_cycle_index("f107_solar_flux_sfu", 0.25), 105.0
        )

    def test_albedo_dataset_interpolates(self):
        self.assertAlmostEqual(
            interpolate_solar_cycle_index("earth_albedo", 1.0), 0.35
        )

    def test_out_of_range_phase_raises(self):
        with self.assertRaises(ValueError):
            interpolate_solar_cycle_index("f107_solar_flux_sfu", 1.5)

    def test_negative_phase_raises(self):
        with self.assertRaises(ValueError):
            interpolate_solar_cycle_index("f107_solar_flux_sfu", -0.1)

    def test_unrecognized_dataset_raises(self):
        with self.assertRaises(ValueError):
            interpolate_solar_cycle_index("unknown_dataset", 0.5)


class ThermalCaseReferenceTests(unittest.TestCase):
    def test_hot_case_uses_maximum_level(self):
        result = thermal_case_reference("hot")
        self.assertEqual(result["f107_solar_flux_sfu"], 230.0)
        self.assertEqual(result["earth_albedo"], 0.35)

    def test_cold_case_uses_minimum_level(self):
        result = thermal_case_reference("cold")
        self.assertEqual(result["f107_solar_flux_sfu"], 70.0)
        self.assertEqual(result["earth_ir_flux_w_m2"], 260.0)

    def test_unrecognized_case_raises(self):
        with self.assertRaises(ValueError):
            thermal_case_reference("mild")


class ReferenceDataReviewTests(unittest.TestCase):
    def test_valid_f107_value_is_categorized_and_valid(self):
        review = reference_data_review(
            {"dataset_id": "f107_solar_flux_sfu", "value": 70.0}
        )
        self.assertEqual(review["activity_level"], "minimum")
        self.assertTrue(is_reference_data_valid(review))

    def test_out_of_range_f107_value_has_no_activity_level(self):
        review = reference_data_review(
            {"dataset_id": "f107_solar_flux_sfu", "value": 5.0}
        )
        self.assertIsNone(review["activity_level"])
        self.assertFalse(is_reference_data_valid(review))

    def test_non_f107_dataset_has_no_activity_level(self):
        review = reference_data_review({"dataset_id": "earth_albedo", "value": 0.3})
        self.assertIsNone(review["activity_level"])
        self.assertTrue(is_reference_data_valid(review))

    def test_unrecognized_dataset_raises(self):
        with self.assertRaises(ValueError):
            reference_data_review({"dataset_id": "unknown", "value": 1.0})


if __name__ == "__main__":
    unittest.main()
