#!/usr/bin/env python3
"""Contract test for the reflectance cut-on purpose assessment (offline)."""

import copy
import unittest

from e2008_reflectance_cut_on_purpose_logic import (
    COMMON_OBJECTIVE,
    CUT_ON_CHARACTERISATION_NOT_REQUIRED,
    CUT_ON_CHARACTERISED,
    CUT_ON_MEASUREMENT_INADEQUATE,
    CUT_ON_NOT_MEASURED,
    CUT_ON_PLACEMENT_SHORTFALL,
    EDGE_ABOVE_REQUIRED,
    EDGE_BELOW_REQUIRED,
    EDGE_ON_TARGET,
    RECOGNISED_DRIVERS,
    absorbed_fraction_in_band,
    assess_cut_on_purpose,
    assess_scan_bracket,
    band_coverage_fraction,
    band_edge_direction,
    band_edge_offset_nm,
    band_is_high_reflectance,
    group_band_drivers,
    validate_cut_on_purpose_policy,
)

MEASUREMENT = {
    "cut_on_nm": 348.0,
    "band_end_nm": 1250.0,
    "scan_start_nm": 300.0,
    "scan_end_nm": 1400.0,
    "plateau_wavelength_nm": 500.0,
}

CASE = {
    "coating_id": "OSR-CG-2",
    "drivers": [
        "coverglass-uv-reflector-band",
        "cell-photo-response-band-protection",
    ],
    "plateau_reflectance": 0.92,
    "required_band_start_nm": 350.0,
    "required_band_end_nm": 1200.0,
    "required_edge_nm": 350.0,
    "measurement": copy.deepcopy(MEASUREMENT),
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


def _measured(**overrides):
    measurement = copy.deepcopy(MEASUREMENT)
    measurement.update(overrides)
    return _case(measurement=measurement)


class PolicyTests(unittest.TestCase):
    def test_an_absent_policy_falls_back_to_the_declared_default(self):
        policy = validate_cut_on_purpose_policy(None)
        self.assertAlmostEqual(policy["min_plateau_reflectance"], 0.60, places=9)
        self.assertAlmostEqual(policy["band_edge_tolerance_nm"], 10.0, places=9)
        self.assertAlmostEqual(policy["min_scan_margin_nm"], 20.0, places=9)

    def test_a_plateau_threshold_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_purpose_policy({"min_plateau_reflectance": 1.4})

    def test_a_zero_plateau_threshold_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_purpose_policy({"min_plateau_reflectance": 0.0})

    def test_a_zero_edge_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_purpose_policy({"band_edge_tolerance_nm": 0.0})

    def test_a_negative_scan_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_purpose_policy({"min_scan_margin_nm": -5.0})

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_on_purpose_policy("default")


class DriverTests(unittest.TestCase):
    def test_every_recognised_driver_maps_to_a_quantity(self):
        grouped = group_band_drivers(list(RECOGNISED_DRIVERS))
        self.assertEqual(len(grouped["drivers"]), len(RECOGNISED_DRIVERS))
        self.assertEqual(len(set(grouped["objectives"])), len(RECOGNISED_DRIVERS) + 1)

    def test_the_shared_objective_is_appended_when_any_driver_is_present(self):
        grouped = group_band_drivers(["coverglass-uv-reflector-band"])
        self.assertIn(COMMON_OBJECTIVE, grouped["objectives"])

    def test_no_drivers_yields_no_objectives_at_all(self):
        grouped = group_band_drivers([])
        self.assertEqual(grouped["drivers"], [])
        self.assertEqual(grouped["objectives"], ())

    def test_a_driver_maps_to_the_budget_it_feeds(self):
        grouped = group_band_drivers(["optical-solar-reflector-thermal-budget"])
        self.assertEqual(
            grouped["drivers"][0]["objective"], "reflector-absorptance-budget"
        )

    def test_an_unrecognised_driver_rejected(self):
        with self.assertRaises(ValueError):
            group_band_drivers(["looks-nice-on-the-panel"])

    def test_a_driver_declared_twice_rejected(self):
        with self.assertRaises(ValueError):
            group_band_drivers(
                ["coverglass-uv-reflector-band", "coverglass-uv-reflector-band"]
            )

    def test_a_bare_string_of_drivers_rejected(self):
        with self.assertRaises(ValueError):
            group_band_drivers("coverglass-uv-reflector-band")

    def test_an_empty_driver_name_rejected(self):
        with self.assertRaises(ValueError):
            group_band_drivers(["  "])


class BandQuantityTests(unittest.TestCase):
    def test_a_tall_plateau_is_a_high_reflectance_band(self):
        self.assertTrue(band_is_high_reflectance(0.92))

    def test_a_plateau_exactly_on_the_threshold_still_counts(self):
        self.assertTrue(band_is_high_reflectance(0.60))

    def test_a_low_plateau_is_not_a_band(self):
        self.assertFalse(band_is_high_reflectance(0.35))

    def test_a_plateau_above_one_rejected(self):
        with self.assertRaises(ValueError):
            band_is_high_reflectance(1.2)

    def test_the_absorbed_fraction_is_what_the_band_does_not_reject(self):
        self.assertAlmostEqual(absorbed_fraction_in_band(0.92), 0.08, places=9)

    def test_a_perfect_reflector_absorbs_nothing_in_band(self):
        self.assertAlmostEqual(absorbed_fraction_in_band(1.0), 0.0, places=9)

    def test_a_negative_plateau_rejected(self):
        with self.assertRaises(ValueError):
            absorbed_fraction_in_band(-0.1)


class EdgePlacementTests(unittest.TestCase):
    def test_the_offset_is_signed_from_the_required_edge(self):
        self.assertAlmostEqual(band_edge_offset_nm(348.0, 350.0), -2.0, places=9)
        self.assertAlmostEqual(band_edge_offset_nm(375.0, 350.0), 25.0, places=9)

    def test_an_offset_inside_the_tolerance_is_on_target(self):
        self.assertEqual(band_edge_direction(-2.0, 10.0), EDGE_ON_TARGET)

    def test_an_offset_exactly_on_the_tolerance_is_on_target(self):
        self.assertEqual(band_edge_direction(10.0, 10.0), EDGE_ON_TARGET)

    def test_an_edge_short_of_the_requirement_costs_array_current(self):
        self.assertEqual(band_edge_direction(-25.0, 10.0), EDGE_BELOW_REQUIRED)

    def test_an_edge_past_the_requirement_costs_thermal_margin(self):
        self.assertEqual(band_edge_direction(25.0, 10.0), EDGE_ABOVE_REQUIRED)

    def test_a_zero_edge_tolerance_rejected_by_the_direction_call(self):
        with self.assertRaises(ValueError):
            band_edge_direction(5.0, 0.0)

    def test_a_band_spanning_the_requirement_covers_all_of_it(self):
        self.assertAlmostEqual(
            band_coverage_fraction(348.0, 1250.0, 350.0, 1200.0), 1.0, places=9
        )

    def test_a_band_starting_late_covers_only_part_of_the_requirement(self):
        self.assertAlmostEqual(
            band_coverage_fraction(400.0, 1250.0, 350.0, 1200.0),
            800.0 / 850.0,
            places=9,
        )

    def test_a_band_entirely_outside_the_requirement_covers_none_of_it(self):
        self.assertAlmostEqual(
            band_coverage_fraction(1300.0, 1500.0, 350.0, 1200.0), 0.0, places=9
        )

    def test_a_band_end_below_its_cut_on_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage_fraction(1250.0, 348.0, 350.0, 1200.0)

    def test_a_required_band_that_does_not_advance_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage_fraction(348.0, 1250.0, 1200.0, 350.0)


class ScanBracketTests(unittest.TestCase):
    def test_a_scan_reaching_both_sides_is_adequate(self):
        bracket = assess_scan_bracket(MEASUREMENT)
        self.assertTrue(bracket["adequate"])
        self.assertAlmostEqual(bracket["below_edge_margin_nm"], 48.0, places=9)

    def test_a_scan_margin_exactly_on_the_requirement_is_adequate(self):
        measurement = dict(MEASUREMENT, scan_start_nm=328.0)
        bracket = assess_scan_bracket(measurement)
        self.assertAlmostEqual(bracket["below_edge_margin_nm"], 20.0, places=9)
        self.assertTrue(bracket["adequate"])

    def test_a_scan_starting_inside_the_edge_is_not_adequate(self):
        bracket = assess_scan_bracket(dict(MEASUREMENT, scan_start_nm=340.0))
        self.assertFalse(bracket["adequate"])
        self.assertTrue(any("rising into the edge" in f for f in bracket["shortfalls"]))

    def test_a_scan_stopping_before_the_plateau_is_not_adequate(self):
        bracket = assess_scan_bracket(dict(MEASUREMENT, scan_end_nm=400.0))
        self.assertFalse(bracket["adequate"])
        self.assertTrue(any("before the band plateau" in f for f in bracket["shortfalls"]))

    def test_a_plateau_below_the_cut_on_is_not_a_rising_edge(self):
        bracket = assess_scan_bracket(dict(MEASUREMENT, plateau_wavelength_nm=300.0))
        self.assertFalse(bracket["adequate"])
        self.assertTrue(any("not a rising edge" in f for f in bracket["shortfalls"]))

    def test_a_scan_that_does_not_advance_rejected(self):
        with self.assertRaises(ValueError):
            assess_scan_bracket(dict(MEASUREMENT, scan_end_nm=250.0))

    def test_a_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_scan_bracket("348 nm")


class PurposeAssessmentTests(unittest.TestCase):
    def test_a_placed_edge_on_a_real_band_is_characterised(self):
        result = assess_cut_on_purpose(CASE)
        self.assertEqual(result["verdict"], CUT_ON_CHARACTERISED)
        self.assertEqual(result["band_edge_direction"], EDGE_ON_TARGET)
        self.assertAlmostEqual(result["band_edge_offset_nm"], -2.0, places=9)
        self.assertAlmostEqual(result["band_edge_margin_nm"], 8.0, places=9)

    def test_the_objectives_the_cut_on_feeds_are_reported(self):
        result = assess_cut_on_purpose(CASE)
        self.assertIn("uv-rejection-band-edge-placement", result["objectives"])
        self.assertIn("in-band-reflection-power-loss", result["objectives"])
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_the_coverage_of_the_required_rejection_band_is_reported(self):
        result = assess_cut_on_purpose(CASE)
        self.assertAlmostEqual(result["band_coverage_fraction"], 1.0, places=9)

    def test_the_in_band_thermal_load_is_reported_whatever_the_verdict(self):
        result = assess_cut_on_purpose(CASE)
        self.assertAlmostEqual(result["absorbed_fraction_in_band"], 0.08, places=9)

    def test_an_edge_exactly_on_the_tolerance_is_still_characterised(self):
        result = assess_cut_on_purpose(_measured(cut_on_nm=360.0))
        self.assertEqual(result["verdict"], CUT_ON_CHARACTERISED)
        self.assertAlmostEqual(result["band_edge_margin_nm"], 0.0, places=9)

    def test_an_edge_short_of_the_requirement_is_a_placement_shortfall(self):
        result = assess_cut_on_purpose(_measured(cut_on_nm=330.0))
        self.assertEqual(result["verdict"], CUT_ON_PLACEMENT_SHORTFALL)
        self.assertEqual(result["band_edge_direction"], EDGE_BELOW_REQUIRED)
        self.assertTrue(any("array current" in f for f in result["findings"]))

    def test_an_edge_past_the_requirement_is_a_different_shortfall(self):
        result = assess_cut_on_purpose(_measured(cut_on_nm=375.0))
        self.assertEqual(result["verdict"], CUT_ON_PLACEMENT_SHORTFALL)
        self.assertEqual(result["band_edge_direction"], EDGE_ABOVE_REQUIRED)
        self.assertTrue(any("thermal margin" in f for f in result["findings"]))

    def test_a_late_edge_lowers_the_coverage_of_the_required_band(self):
        result = assess_cut_on_purpose(_measured(cut_on_nm=400.0))
        self.assertAlmostEqual(
            result["band_coverage_fraction"], 800.0 / 850.0, places=9
        )

    def test_a_coating_with_no_declared_driver_needs_no_cut_on(self):
        result = assess_cut_on_purpose(_case(drivers=[]))
        self.assertEqual(result["verdict"], CUT_ON_CHARACTERISATION_NOT_REQUIRED)
        self.assertTrue(any("no budget to serve" in f for f in result["findings"]))

    def test_a_plateau_too_low_to_be_a_band_needs_no_cut_on(self):
        result = assess_cut_on_purpose(_case(plateau_reflectance=0.35))
        self.assertEqual(result["verdict"], CUT_ON_CHARACTERISATION_NOT_REQUIRED)
        self.assertFalse(result["band_is_high_reflectance"])

    def test_a_wanted_but_unmeasured_cut_on_is_named_not_defaulted(self):
        result = assess_cut_on_purpose(_case(measurement=None))
        self.assertEqual(result["verdict"], CUT_ON_NOT_MEASURED)
        self.assertIsNone(result["cut_on_nm"])
        self.assertTrue(any("says nothing about where" in f for f in result["findings"]))

    def test_a_scan_that_cannot_place_the_edge_is_inadequate_not_a_shortfall(self):
        result = assess_cut_on_purpose(_measured(scan_start_nm=344.0))
        self.assertEqual(result["verdict"], CUT_ON_MEASUREMENT_INADEQUATE)
        self.assertIsNone(result["band_edge_offset_nm"])

    def test_an_inadequate_scan_is_reported_before_the_edge_is_judged(self):
        result = assess_cut_on_purpose(
            _measured(cut_on_nm=330.0, scan_start_nm=325.0)
        )
        self.assertEqual(result["verdict"], CUT_ON_MEASUREMENT_INADEQUATE)
        self.assertIsNone(result["band_edge_direction"])

    def test_the_required_edge_defaults_to_the_start_of_the_required_band(self):
        case = _case()
        del case["required_edge_nm"]
        result = assess_cut_on_purpose(case)
        self.assertAlmostEqual(result["required_edge_nm"], 350.0, places=9)

    def test_a_tighter_tolerance_turns_the_same_edge_into_a_shortfall(self):
        result = assess_cut_on_purpose(CASE, {"band_edge_tolerance_nm": 1.0})
        self.assertEqual(result["verdict"], CUT_ON_PLACEMENT_SHORTFALL)

    def test_a_case_without_a_coating_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_on_purpose(_case(coating_id="  "))

    def test_a_required_band_that_does_not_advance_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_on_purpose(
                _case(required_band_start_nm=1200.0, required_band_end_nm=350.0)
            )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_on_purpose("OSR-CG-2")


if __name__ == "__main__":
    unittest.main()
