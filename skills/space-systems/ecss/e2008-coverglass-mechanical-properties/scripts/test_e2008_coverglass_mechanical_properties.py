#!/usr/bin/env python3
"""Contract test for the coverglass dimensional and mass record (offline)."""

import copy
import unittest

from e2008_coverglass_mechanical_properties_logic import (
    ACCEPT,
    DIMENSION_ABOVE,
    DIMENSION_BELOW,
    DIMENSION_WITHIN,
    REJECT,
    REVIEW,
    areal_density_mg_per_cm2,
    assess_coverglass_configuration,
    assess_coverglass_test_matrix,
    bulk_density_g_per_cm3,
    evaluate_dimension,
    mass_contribution_g,
    outline_area_cm2,
    validate_band,
    validate_coverglass_specification,
)

THIN = {
    "id": "CMG-100",
    "length_mm": {"nominal": 40.0, "minus": 0.10, "plus": 0.10},
    "width_mm": {"nominal": 20.0, "minus": 0.10, "plus": 0.10},
    "thickness_um": {"nominal": 100.0, "minus": 5.0, "plus": 5.0},
    "mass_mg": {"nominal": 204.0, "minus": 5.0, "plus": 5.0},
    "population": 24,
}

THICK = {
    "id": "CMG-150",
    "length_mm": {"nominal": 40.0, "minus": 0.10, "plus": 0.10},
    "width_mm": {"nominal": 20.0, "minus": 0.10, "plus": 0.10},
    "thickness_um": {"nominal": 150.0, "minus": 5.0, "plus": 5.0},
    "mass_mg": {"nominal": 306.0, "minus": 8.0, "plus": 8.0},
    "population": 12,
}

SPEC = {
    "configurations": [THIN, THICK],
    "material_density_g_per_cm3": 2.55,
    "review_band_factor": 2.0,
    "bulk_density_tolerance": 0.08,
}

THIN_RECORD = {
    "configuration_id": "CMG-100",
    "sample_id": "CG-0001",
    "length_mm": 40.02,
    "width_mm": 20.00,
    "thickness_um": 101.0,
    "mass_mg": 205.0,
}

THICK_RECORD = {
    "configuration_id": "CMG-150",
    "sample_id": "CG-0002",
    "length_mm": 40.00,
    "width_mm": 20.00,
    "thickness_um": 150.0,
    "mass_mg": 306.0,
}

LENGTH_BAND = {"nominal": 40.0, "minus": 0.10, "plus": 0.10}


def _spec(**overrides):
    spec = copy.deepcopy(SPEC)
    spec.update(overrides)
    return spec


def _thin(**overrides):
    record = copy.deepcopy(THIN_RECORD)
    record.update(overrides)
    return record


def _wide_mass_spec():
    """Same matrix with a mass band too wide to catch a density error."""
    thin = copy.deepcopy(THIN)
    thin["mass_mg"] = {"nominal": 204.0, "minus": 100.0, "plus": 100.0}
    return _spec(configurations=[thin, copy.deepcopy(THICK)])


class BandValidationTests(unittest.TestCase):
    def test_a_good_band_is_returned_normalised(self):
        band = validate_band("length_mm", LENGTH_BAND)
        self.assertAlmostEqual(band["nominal"], 40.0, places=9)
        self.assertAlmostEqual(band["plus"], 0.10, places=9)

    def test_a_zero_width_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("length_mm", {"nominal": 40.0, "minus": 0.0, "plus": 0.0})

    def test_a_one_sided_band_is_allowed(self):
        band = validate_band("thickness_um", {"nominal": 100.0, "minus": 0.0, "plus": 8.0})
        self.assertAlmostEqual(band["minus"], 0.0, places=9)

    def test_a_minus_tolerance_past_the_nominal_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("mass_mg", {"nominal": 204.0, "minus": 300.0, "plus": 5.0})

    def test_a_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("mass_mg", {"nominal": 204.0, "minus": -5.0, "plus": 5.0})

    def test_a_non_mapping_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("mass_mg", "204 +/- 5")


class SpecificationTests(unittest.TestCase):
    def test_a_full_matrix_specification_validates(self):
        checked = validate_coverglass_specification(SPEC)
        self.assertEqual(checked["order"], ("CMG-100", "CMG-150"))
        self.assertIn("thickness_um", checked["configurations"]["CMG-100"]["bands"])
        self.assertAlmostEqual(checked["material_density_g_per_cm3"], 2.55, places=9)

    def test_a_matrix_with_no_configurations_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverglass_specification(_spec(configurations=[]))

    def test_a_configuration_missing_a_band_rejected(self):
        broken = copy.deepcopy(THIN)
        del broken["mass_mg"]
        with self.assertRaises(ValueError):
            validate_coverglass_specification(_spec(configurations=[broken]))

    def test_duplicate_configuration_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverglass_specification(
                _spec(configurations=[copy.deepcopy(THIN), copy.deepcopy(THIN)])
            )

    def test_a_configuration_without_an_id_rejected(self):
        anonymous = copy.deepcopy(THIN)
        anonymous["id"] = "   "
        with self.assertRaises(ValueError):
            validate_coverglass_specification(_spec(configurations=[anonymous]))

    def test_a_missing_material_density_rejected(self):
        broken = _spec()
        del broken["material_density_g_per_cm3"]
        with self.assertRaises(ValueError):
            validate_coverglass_specification(broken)

    def test_a_review_band_factor_under_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverglass_specification(_spec(review_band_factor=0.5))

    def test_a_density_tolerance_of_one_or_more_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverglass_specification(_spec(bulk_density_tolerance=1.0))

    def test_a_fractional_population_rejected(self):
        odd = copy.deepcopy(THIN)
        odd["population"] = 2.5
        with self.assertRaises(ValueError):
            validate_coverglass_specification(_spec(configurations=[odd]))

    def test_a_population_below_one_rejected(self):
        empty = copy.deepcopy(THIN)
        empty["population"] = 0
        with self.assertRaises(ValueError):
            validate_coverglass_specification(_spec(configurations=[empty]))

    def test_a_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverglass_specification("40x20x0.1")


class DimensionTests(unittest.TestCase):
    def test_a_measurement_mid_band_is_within_tolerance(self):
        result = evaluate_dimension("length_mm", 40.00, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_WITHIN)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["deviation"], 0.0, places=9)

    def test_a_measurement_exactly_on_the_upper_limit_is_within_tolerance(self):
        result = evaluate_dimension("length_mm", 40.10, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_WITHIN)
        self.assertAlmostEqual(result["margin"], 0.0, places=9)

    def test_a_measurement_exactly_on_the_lower_limit_is_within_tolerance(self):
        result = evaluate_dimension("length_mm", 39.90, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_WITHIN)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_measurement_just_over_the_band_goes_to_review(self):
        result = evaluate_dimension("length_mm", 40.15, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_ABOVE)
        self.assertEqual(result["disposition"], REVIEW)

    def test_a_measurement_exactly_on_the_review_limit_stays_in_review(self):
        result = evaluate_dimension("length_mm", 40.20, LENGTH_BAND)
        self.assertEqual(result["disposition"], REVIEW)

    def test_a_measurement_past_the_review_band_rejects(self):
        result = evaluate_dimension("length_mm", 40.60, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_ABOVE)
        self.assertEqual(result["disposition"], REJECT)

    def test_an_undersize_measurement_is_below_the_lower_limit(self):
        result = evaluate_dimension("length_mm", 39.85, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_BELOW)
        self.assertEqual(result["disposition"], REVIEW)

    def test_a_badly_undersize_measurement_rejects(self):
        result = evaluate_dimension("length_mm", 39.40, LENGTH_BAND)
        self.assertEqual(result["state"], DIMENSION_BELOW)
        self.assertEqual(result["disposition"], REJECT)

    def test_a_wider_review_factor_saves_the_same_measurement(self):
        tight = evaluate_dimension("length_mm", 40.25, LENGTH_BAND, 2.0)
        loose = evaluate_dimension("length_mm", 40.25, LENGTH_BAND, 4.0)
        self.assertEqual(tight["disposition"], REJECT)
        self.assertEqual(loose["disposition"], REVIEW)

    def test_a_non_numeric_measurement_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dimension("length_mm", "40.0", LENGTH_BAND)


class DerivedQuantityTests(unittest.TestCase):
    def test_outline_area_is_the_plan_area_in_square_centimetres(self):
        self.assertAlmostEqual(outline_area_cm2(40.0, 20.0), 8.0, places=9)

    def test_areal_density_is_mass_over_outline_area(self):
        self.assertAlmostEqual(
            areal_density_mg_per_cm2(204.0, 40.0, 20.0), 25.5, places=9
        )

    def test_bulk_density_recovers_the_glass_material_density(self):
        self.assertAlmostEqual(
            bulk_density_g_per_cm3(204.0, 40.0, 20.0, 100.0), 2.55, places=9
        )

    def test_a_thicker_piece_of_the_same_mass_reads_less_dense(self):
        thin = bulk_density_g_per_cm3(204.0, 40.0, 20.0, 100.0)
        thick = bulk_density_g_per_cm3(204.0, 40.0, 20.0, 150.0)
        self.assertLess(thick, thin)

    def test_doubling_the_thickness_doubles_the_areal_density_at_fixed_density(self):
        thin = areal_density_mg_per_cm2(204.0, 40.0, 20.0)
        thick = areal_density_mg_per_cm2(408.0, 40.0, 20.0)
        self.assertAlmostEqual(thick, 2.0 * thin, places=9)

    def test_zero_mass_rejected(self):
        with self.assertRaises(ValueError):
            areal_density_mg_per_cm2(0.0, 40.0, 20.0)

    def test_zero_outline_rejected(self):
        with self.assertRaises(ValueError):
            outline_area_cm2(0.0, 20.0)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            bulk_density_g_per_cm3(204.0, 40.0, 20.0, 0.0)

    def test_mass_contribution_scales_with_the_population(self):
        self.assertAlmostEqual(mass_contribution_g(205.0, 24), 4.92, places=9)

    def test_a_fractional_population_has_no_mass_contribution(self):
        with self.assertRaises(ValueError):
            mass_contribution_g(205.0, 2.5)


class ConfigurationRecordTests(unittest.TestCase):
    def test_a_conforming_record_is_accepted(self):
        result = assess_coverglass_configuration(THIN_RECORD, SPEC)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["out_of_tolerance_names"], [])
        self.assertTrue(result["bulk_density_consistent"])
        self.assertTrue(
            any("clause 8.7.4 evidence" in finding for finding in result["findings"])
        )

    def test_the_record_carries_the_areal_density_the_budget_consumes(self):
        result = assess_coverglass_configuration(THICK_RECORD, SPEC)
        self.assertAlmostEqual(
            result["areal_density_mg_per_cm2"], 38.25, places=9
        )

    def test_the_record_carries_the_configuration_mass_contribution(self):
        result = assess_coverglass_configuration(THICK_RECORD, SPEC)
        self.assertEqual(result["population"], 12)
        self.assertAlmostEqual(result["mass_contribution_g"], 3.672, places=9)

    def test_an_oversize_outline_raises_a_nonconformance(self):
        result = assess_coverglass_configuration(_thin(length_mm=40.15), SPEC)
        self.assertEqual(result["verdict"], REVIEW)
        self.assertIn("length_mm", result["out_of_tolerance_names"])
        self.assertTrue(result["nonconformance_review_required"])

    def test_a_thickness_just_over_the_band_goes_to_review(self):
        result = assess_coverglass_configuration(_thin(thickness_um=107.0), SPEC)
        self.assertEqual(result["verdict"], REVIEW)
        self.assertIn("thickness_um", result["out_of_tolerance_names"])

    def test_a_grossly_thick_piece_rejects(self):
        result = assess_coverglass_configuration(_thin(thickness_um=130.0), SPEC)
        self.assertEqual(result["verdict"], REJECT)
        self.assertIn("thickness_um", result["out_of_tolerance_names"])

    def test_mass_and_geometry_that_disagree_are_flagged(self):
        result = assess_coverglass_configuration(
            _thin(mass_mg=260.0), _wide_mass_spec()
        )
        self.assertFalse(result["bulk_density_consistent"])
        self.assertEqual(result["verdict"], REVIEW)
        self.assertTrue(any("disagree" in finding for finding in result["findings"]))

    def test_a_density_error_exactly_on_the_allowance_stays_consistent(self):
        spec = _wide_mass_spec()
        spec["bulk_density_tolerance"] = 0.25
        mass = 204.0 * 1.25
        result = assess_coverglass_configuration(
            _thin(thickness_um=100.0, length_mm=40.0, width_mm=20.0, mass_mg=mass),
            spec,
        )
        self.assertAlmostEqual(result["bulk_density_error_fraction"], 0.25, places=9)
        self.assertTrue(result["bulk_density_consistent"])

    def test_an_unrecorded_property_rejected(self):
        broken = copy.deepcopy(THIN_RECORD)
        del broken["mass_mg"]
        with self.assertRaises(ValueError):
            assess_coverglass_configuration(broken, SPEC)

    def test_a_record_for_an_undeclared_configuration_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_configuration(_thin(configuration_id="CMG-500"), SPEC)

    def test_a_record_without_a_sample_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_configuration(_thin(sample_id="  "), SPEC)

    def test_a_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_configuration("CG-0001", SPEC)


class TestMatrixTests(unittest.TestCase):
    def test_a_complete_matrix_is_accepted(self):
        result = assess_coverglass_test_matrix([THIN_RECORD, THICK_RECORD], SPEC)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["configurations_recorded"], ("CMG-100", "CMG-150"))
        self.assertEqual(result["rejected_samples"], [])

    def test_the_matrix_sums_the_mass_every_configuration_contributes(self):
        result = assess_coverglass_test_matrix([THIN_RECORD, THICK_RECORD], SPEC)
        self.assertAlmostEqual(
            result["matrix_mass_contribution_g"], 8.592, places=9
        )

    def test_a_configuration_under_test_with_no_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_test_matrix([THIN_RECORD], SPEC)

    def test_two_records_sharing_one_sample_identifier_rejected(self):
        clash = copy.deepcopy(THICK_RECORD)
        clash["sample_id"] = THIN_RECORD["sample_id"]
        with self.assertRaises(ValueError):
            assess_coverglass_test_matrix([THIN_RECORD, clash], SPEC)

    def test_the_worst_record_governs_the_matrix_verdict(self):
        result = assess_coverglass_test_matrix(
            [_thin(thickness_um=130.0), THICK_RECORD], SPEC
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["rejected_samples"], ["CG-0001"])

    def test_a_review_record_is_named_without_rejecting_the_matrix(self):
        result = assess_coverglass_test_matrix(
            [_thin(length_mm=40.15), THICK_RECORD], SPEC
        )
        self.assertEqual(result["verdict"], REVIEW)
        self.assertEqual(result["review_samples"], ["CG-0001"])

    def test_the_matrix_names_every_density_inconsistent_sample(self):
        result = assess_coverglass_test_matrix(
            [_thin(mass_mg=260.0), THICK_RECORD], _wide_mass_spec()
        )
        self.assertEqual(result["density_inconsistent_samples"], ["CG-0001"])

    def test_a_non_list_of_records_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_test_matrix(THIN_RECORD, SPEC)


if __name__ == "__main__":
    unittest.main()
