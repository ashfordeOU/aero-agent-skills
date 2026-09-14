#!/usr/bin/env python3
"""Contract test for the bare cell dimension and mass check (offline)."""

import copy
import unittest

from e2008_bare_cell_dimensions_and_weight_logic import (
    ACCEPT,
    DIMENSION_ABOVE,
    DIMENSION_BELOW,
    DIMENSION_WITHIN,
    REJECT,
    REVIEW,
    areal_density_mg_per_cm2,
    assess_bare_cell_dimensions,
    assess_interconnector_positions,
    evaluate_dimension,
    positional_deviation_mm,
    validate_band,
    validate_cell_specification,
)

SPEC = {
    "length_mm": {"nominal": 80.0, "minus": 0.10, "plus": 0.10},
    "width_mm": {"nominal": 40.0, "minus": 0.10, "plus": 0.10},
    "thickness_um": {"nominal": 150.0, "minus": 10.0, "plus": 10.0},
    "mass_g": {"nominal": 2.50, "minus": 0.10, "plus": 0.10},
    "contacts": [
        {
            "id": "rear-pad-1",
            "width_mm": {"nominal": 6.0, "minus": 0.20, "plus": 0.20},
            "length_mm": {"nominal": 2.0, "minus": 0.10, "plus": 0.10},
        }
    ],
    "interconnector_positions": [
        {"id": "IC-1", "x_mm": 10.0, "y_mm": 20.0},
        {"id": "IC-2", "x_mm": 70.0, "y_mm": 20.0},
    ],
    "position_tolerance_mm": 0.15,
    "review_band_factor": 2.0,
    "areal_density_tolerance": 0.10,
}

CELL = {
    "cell_id": "BARE-CELL-0003",
    "length_mm": 80.02,
    "width_mm": 40.00,
    "thickness_um": 152.0,
    "mass_g": 2.52,
    "contacts": [{"id": "rear-pad-1", "width_mm": 6.02, "length_mm": 2.01}],
    "interconnector_positions": [
        {"id": "IC-1", "x_mm": 10.05, "y_mm": 20.00},
        {"id": "IC-2", "x_mm": 70.00, "y_mm": 20.02},
    ],
}

BARE_SPEC = {
    "length_mm": {"nominal": 80.0, "minus": 0.10, "plus": 0.10},
    "width_mm": {"nominal": 40.0, "minus": 0.10, "plus": 0.10},
    "thickness_um": {"nominal": 150.0, "minus": 10.0, "plus": 10.0},
    "mass_g": {"nominal": 2.50, "minus": 0.10, "plus": 0.10},
}

LENGTH_BAND = {"nominal": 80.0, "minus": 0.10, "plus": 0.10}


def _spec(**overrides):
    spec = copy.deepcopy(SPEC)
    spec.update(overrides)
    return spec


def _cell(**overrides):
    cell = copy.deepcopy(CELL)
    cell.update(overrides)
    return cell


class BandValidationTests(unittest.TestCase):
    def test_a_good_band_is_returned_normalised(self):
        band = validate_band("length_mm", LENGTH_BAND)
        self.assertAlmostEqual(band["nominal"], 80.0, places=9)
        self.assertAlmostEqual(band["plus"], 0.10, places=9)

    def test_a_zero_width_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("length_mm", {"nominal": 80.0, "minus": 0.0, "plus": 0.0})

    def test_a_one_sided_band_is_allowed(self):
        band = validate_band("length_mm", {"nominal": 80.0, "minus": 0.0, "plus": 0.2})
        self.assertAlmostEqual(band["minus"], 0.0, places=9)

    def test_a_minus_tolerance_past_the_nominal_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("mass_g", {"nominal": 2.5, "minus": 3.0, "plus": 0.1})

    def test_a_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("mass_g", {"nominal": 2.5, "minus": -0.1, "plus": 0.1})

    def test_a_non_mapping_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("mass_g", "2.5 +/- 0.1")


class SpecificationTests(unittest.TestCase):
    def test_a_full_specification_validates(self):
        checked = validate_cell_specification(SPEC)
        self.assertIn("length_mm", checked["bands"])
        self.assertIn("rear-pad-1", checked["contacts"])
        self.assertEqual(len(checked["positions"]), 2)

    def test_a_specification_missing_a_band_rejected(self):
        broken = copy.deepcopy(SPEC)
        del broken["thickness_um"]
        with self.assertRaises(ValueError):
            validate_cell_specification(broken)

    def test_a_contact_with_no_bands_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_specification(_spec(contacts=[{"id": "rear-pad-1"}]))

    def test_duplicate_contact_ids_rejected(self):
        duplicated = copy.deepcopy(SPEC["contacts"][0])
        with self.assertRaises(ValueError):
            validate_cell_specification(
                _spec(contacts=[SPEC["contacts"][0], duplicated])
            )

    def test_positions_without_a_tolerance_rejected(self):
        broken = copy.deepcopy(SPEC)
        del broken["position_tolerance_mm"]
        with self.assertRaises(ValueError):
            validate_cell_specification(broken)

    def test_a_review_band_factor_under_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_specification(_spec(review_band_factor=0.5))

    def test_a_specification_with_no_contacts_or_positions_validates(self):
        checked = validate_cell_specification(BARE_SPEC)
        self.assertEqual(checked["contacts"], {})
        self.assertEqual(checked["positions"], {})

    def test_a_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_specification("80x40")


class DimensionTests(unittest.TestCase):
    def test_a_measurement_mid_band_is_within_tolerance(self):
        result = evaluate_dimension("length_mm", 80.00, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_WITHIN)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["deviation"], 0.0, places=9)

    def test_a_measurement_exactly_on_the_upper_limit_is_within_tolerance(self):
        result = evaluate_dimension("length_mm", 80.10, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_WITHIN)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["margin"], 0.0, places=9)

    def test_a_measurement_exactly_on_the_lower_limit_is_within_tolerance(self):
        result = evaluate_dimension("length_mm", 79.90, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_WITHIN)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_measurement_just_over_the_band_goes_to_review(self):
        result = evaluate_dimension("length_mm", 80.15, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_ABOVE)
        self.assertEqual(result["disposition"], REVIEW)

    def test_a_measurement_exactly_on_the_review_limit_stays_in_review(self):
        result = evaluate_dimension("length_mm", 80.20, LENGTH_BAND)
        self.assertEqual(result["disposition"], REVIEW)

    def test_a_measurement_past_the_review_band_rejects(self):
        result = evaluate_dimension("length_mm", 80.50, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_ABOVE)
        self.assertEqual(result["disposition"], REJECT)

    def test_an_undersize_measurement_is_below_the_lower_limit(self):
        result = evaluate_dimension("length_mm", 79.85, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_BELOW)
        self.assertEqual(result["disposition"], REVIEW)

    def test_a_badly_undersize_measurement_rejects(self):
        result = evaluate_dimension("length_mm", 79.40, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_BELOW)
        self.assertEqual(result["disposition"], REJECT)

    def test_a_wider_review_factor_saves_the_same_measurement(self):
        tight = evaluate_dimension("length_mm", 80.25, LENGTH_BAND, 2.0)
        loose = evaluate_dimension("length_mm", 80.25, LENGTH_BAND, 4.0)
        self.assertEqual(tight["disposition"], REJECT)
        self.assertEqual(loose["disposition"], REVIEW)

    def test_a_non_numeric_measurement_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dimension("length_mm", "80.0", LENGTH_BAND)


class PositionTests(unittest.TestCase):
    def test_positional_deviation_is_radial(self):
        self.assertAlmostEqual(
            positional_deviation_mm((13.0, 24.0), (10.0, 20.0)), 5.0, places=9
        )

    def test_a_point_on_nominal_has_no_deviation(self):
        self.assertAlmostEqual(
            positional_deviation_mm((10.0, 20.0), (10.0, 20.0)), 0.0, places=9
        )

    def test_a_position_that_is_not_a_pair_rejected(self):
        with self.assertRaises(ValueError):
            positional_deviation_mm((10.0,), (10.0, 20.0))

    def test_positions_inside_the_tolerance_are_accepted(self):
        checked = validate_cell_specification(SPEC)
        result = assess_interconnector_positions(
            CELL["interconnector_positions"], checked
        )
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["worst_deviation_mm"], 0.05, places=9)

    def test_a_deviation_exactly_on_the_tolerance_is_accepted(self):
        checked = validate_cell_specification(SPEC)
        result = assess_interconnector_positions(
            [
                {"id": "IC-1", "x_mm": 10.15, "y_mm": 20.00},
                {"id": "IC-2", "x_mm": 70.00, "y_mm": 20.00},
            ],
            checked,
        )
        self.assertAlmostEqual(result["worst_deviation_mm"], 0.15, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_deviation_past_the_tolerance_goes_to_review(self):
        checked = validate_cell_specification(SPEC)
        result = assess_interconnector_positions(
            [
                {"id": "IC-1", "x_mm": 10.20, "y_mm": 20.00},
                {"id": "IC-2", "x_mm": 70.00, "y_mm": 20.00},
            ],
            checked,
        )
        self.assertEqual(result["disposition"], REVIEW)

    def test_a_deviation_past_the_review_band_rejects(self):
        checked = validate_cell_specification(SPEC)
        result = assess_interconnector_positions(
            [
                {"id": "IC-1", "x_mm": 10.40, "y_mm": 20.00},
                {"id": "IC-2", "x_mm": 70.00, "y_mm": 20.00},
            ],
            checked,
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_two_axis_offsets_combine_into_one_radial_deviation(self):
        checked = validate_cell_specification(SPEC)
        result = assess_interconnector_positions(
            [
                {"id": "IC-1", "x_mm": 10.12, "y_mm": 20.12},
                {"id": "IC-2", "x_mm": 70.00, "y_mm": 20.00},
            ],
            checked,
        )
        self.assertEqual(result["disposition"], REVIEW)

    def test_an_unmeasured_position_rejected(self):
        checked = validate_cell_specification(SPEC)
        with self.assertRaises(ValueError):
            assess_interconnector_positions(
                [{"id": "IC-1", "x_mm": 10.0, "y_mm": 20.0}], checked
            )

    def test_an_unspecified_measured_position_rejected(self):
        checked = validate_cell_specification(SPEC)
        with self.assertRaises(ValueError):
            assess_interconnector_positions(
                [
                    {"id": "IC-1", "x_mm": 10.0, "y_mm": 20.0},
                    {"id": "IC-2", "x_mm": 70.0, "y_mm": 20.0},
                    {"id": "IC-9", "x_mm": 40.0, "y_mm": 20.0},
                ],
                checked,
            )

    def test_measuring_positions_the_drawing_does_not_declare_rejected(self):
        checked = validate_cell_specification(BARE_SPEC)
        with self.assertRaises(ValueError):
            assess_interconnector_positions(
                [{"id": "IC-1", "x_mm": 10.0, "y_mm": 20.0}], checked
            )


class ArealDensityTests(unittest.TestCase):
    def test_areal_density_is_mass_over_outline_area(self):
        self.assertAlmostEqual(
            areal_density_mg_per_cm2(2.5, 80.0, 40.0), 78.125, places=9
        )

    def test_a_heavier_cell_of_the_same_outline_is_denser(self):
        light = areal_density_mg_per_cm2(2.0, 80.0, 40.0)
        heavy = areal_density_mg_per_cm2(3.0, 80.0, 40.0)
        self.assertGreater(heavy, light)

    def test_zero_mass_rejected(self):
        with self.assertRaises(ValueError):
            areal_density_mg_per_cm2(0.0, 80.0, 40.0)

    def test_zero_outline_rejected(self):
        with self.assertRaises(ValueError):
            areal_density_mg_per_cm2(2.5, 0.0, 40.0)


class CellAssessmentTests(unittest.TestCase):
    def test_a_conforming_cell_is_accepted(self):
        result = assess_bare_cell_dimensions(CELL, SPEC)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["out_of_tolerance_names"], [])
        self.assertTrue(result["areal_density_consistent"])
        self.assertTrue(
            any("conformity evidence" in finding for finding in result["findings"])
        )

    def test_an_oversize_outline_raises_a_nonconformance(self):
        result = assess_bare_cell_dimensions(_cell(length_mm=80.15), SPEC)
        self.assertEqual(result["verdict"], REVIEW)
        self.assertIn("length_mm", result["out_of_tolerance_names"])
        self.assertTrue(result["nonconformance_review_required"])

    def test_a_grossly_thick_cell_rejects(self):
        result = assess_bare_cell_dimensions(_cell(thickness_um=200.0), SPEC)
        self.assertEqual(result["verdict"], REJECT)
        self.assertIn("thickness_um", result["out_of_tolerance_names"])

    def test_an_out_of_band_contact_is_caught(self):
        result = assess_bare_cell_dimensions(
            _cell(contacts=[{"id": "rear-pad-1", "width_mm": 6.30, "length_mm": 2.01}]),
            SPEC,
        )
        self.assertEqual(result["verdict"], REVIEW)
        self.assertIn("rear-pad-1 width_mm", result["out_of_tolerance_names"])

    def test_an_out_of_position_interconnector_pad_is_caught(self):
        result = assess_bare_cell_dimensions(
            _cell(
                interconnector_positions=[
                    {"id": "IC-1", "x_mm": 10.50, "y_mm": 20.00},
                    {"id": "IC-2", "x_mm": 70.00, "y_mm": 20.00},
                ]
            ),
            SPEC,
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertAlmostEqual(result["worst_position_deviation_mm"], 0.50, places=9)

    def test_mass_and_outline_that_disagree_are_flagged(self):
        wide_mass = _spec(mass_g={"nominal": 2.50, "minus": 1.00, "plus": 1.00})
        result = assess_bare_cell_dimensions(_cell(mass_g=3.30), wide_mass)
        self.assertFalse(result["areal_density_consistent"])
        self.assertEqual(result["verdict"], REVIEW)
        self.assertTrue(any("disagree" in finding for finding in result["findings"]))

    def test_the_nominal_areal_density_comes_from_the_drawing(self):
        result = assess_bare_cell_dimensions(CELL, SPEC)
        self.assertAlmostEqual(
            result["nominal_areal_density_mg_per_cm2"], 78.125, places=9
        )

    def test_the_worst_call_across_families_governs_the_verdict(self):
        result = assess_bare_cell_dimensions(
            _cell(length_mm=80.15, thickness_um=200.0), SPEC
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_an_unmeasured_dimension_rejected(self):
        broken = copy.deepcopy(CELL)
        del broken["mass_g"]
        with self.assertRaises(ValueError):
            assess_bare_cell_dimensions(broken, SPEC)

    def test_an_unmeasured_contact_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_dimensions(_cell(contacts=[]), SPEC)

    def test_a_contact_missing_one_feature_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_dimensions(
                _cell(contacts=[{"id": "rear-pad-1", "width_mm": 6.0}]), SPEC
            )

    def test_a_contact_the_drawing_does_not_declare_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_dimensions(
                _cell(
                    contacts=[
                        {"id": "rear-pad-1", "width_mm": 6.0, "length_mm": 2.0},
                        {"id": "rear-pad-9", "width_mm": 6.0, "length_mm": 2.0},
                    ]
                ),
                SPEC,
            )

    def test_cell_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_dimensions(_cell(cell_id="  "), SPEC)

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_dimensions("BARE-CELL-0003", SPEC)


if __name__ == "__main__":
    unittest.main()
