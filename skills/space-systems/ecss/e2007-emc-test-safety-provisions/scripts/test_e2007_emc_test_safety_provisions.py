#!/usr/bin/env python3
"""Contract test for the clause 5.2.5.1 radiation-hazard-provision logic.

Standard library unittest only; offline and deterministic.
Run: python3 test_e2007_emc_test_safety_provisions.py
"""

import math
import unittest

from e2007_emc_test_safety_provisions_logic import (
    ELECTRICAL_HAZARD,
    ELECTRICAL_PROVISIONS,
    KNOWN_PROVISIONS,
    LOW_HAZARD,
    RADIATED_HAZARD,
    RADIATED_PROVISIONS,
    assess_run_safety_provisions,
    categorize_asset,
    evaluate_asset,
    far_field_boundary,
    far_field_power_density,
    minimum_standoff_distance,
    permissible_exposure_limit,
    required_provisions,
)


def radiating_asset(**overrides):
    asset = {
        "id": "amp-chain-1",
        "kind": "radiating-amplifier-chain",
        "drive_watt": 100.0,
        "antenna_gain_linear": 10.0,
        "frequency_hz": 1.0e8,
        "provisions": list(RADIATED_PROVISIONS),
    }
    asset.update(overrides)
    return asset


def high_voltage_asset(**overrides):
    asset = {
        "id": "hv-supply-1",
        "kind": "high-voltage-supply",
        "open_circuit_voltage_v": 1200.0,
        "stored_energy_j": 25.0,
        "provisions": list(ELECTRICAL_PROVISIONS),
    }
    asset.update(overrides)
    return asset


class TestExposureLimits(unittest.TestCase):
    def test_low_band_limit_is_flat(self):
        self.assertAlmostEqual(permissible_exposure_limit(1.0e6), 100.0)

    def test_very_high_frequency_band_is_the_most_restrictive(self):
        self.assertAlmostEqual(permissible_exposure_limit(1.0e8), 10.0)
        self.assertLess(
            permissible_exposure_limit(1.0e8), permissible_exposure_limit(1.0e7)
        )

    def test_microwave_band_scales_with_frequency(self):
        self.assertAlmostEqual(permissible_exposure_limit(9.0e8), 30.0)

    def test_upper_microwave_band_is_flat_again(self):
        self.assertAlmostEqual(permissible_exposure_limit(1.0e10), 50.0)

    def test_frequency_below_the_table_rejected(self):
        with self.assertRaises(ValueError):
            permissible_exposure_limit(1.0e3)

    def test_frequency_above_the_table_rejected(self):
        with self.assertRaises(ValueError):
            permissible_exposure_limit(1.0e12)

    def test_non_numeric_frequency_rejected(self):
        with self.assertRaises(ValueError):
            permissible_exposure_limit("100 MHz")


class TestFieldGeometry(unittest.TestCase):
    def test_power_density_follows_inverse_square(self):
        near = far_field_power_density(100.0, 10.0, 2.0)
        far = far_field_power_density(100.0, 10.0, 4.0)
        self.assertAlmostEqual(near / far, 4.0)

    def test_power_density_known_value(self):
        value = far_field_power_density(100.0, 10.0, 3.0)
        self.assertAlmostEqual(value, 1000.0 / (4.0 * math.pi * 9.0))

    def test_power_density_rejects_zero_distance(self):
        with self.assertRaises(ValueError):
            far_field_power_density(100.0, 10.0, 0.0)

    def test_power_density_rejects_non_positive_drive(self):
        with self.assertRaises(ValueError):
            far_field_power_density(0.0, 10.0, 3.0)

    def test_power_density_rejects_non_positive_gain(self):
        with self.assertRaises(ValueError):
            far_field_power_density(100.0, 0.0, 3.0)

    def test_minimum_standoff_matches_the_limit(self):
        distance = minimum_standoff_distance(100.0, 10.0, 10.0)
        self.assertAlmostEqual(far_field_power_density(100.0, 10.0, distance), 10.0)

    def test_minimum_standoff_grows_with_drive(self):
        self.assertGreater(
            minimum_standoff_distance(400.0, 10.0, 10.0),
            minimum_standoff_distance(100.0, 10.0, 10.0),
        )

    def test_minimum_standoff_rejects_non_positive_limit(self):
        with self.assertRaises(ValueError):
            minimum_standoff_distance(100.0, 10.0, 0.0)

    def test_far_field_boundary_known_value(self):
        boundary = far_field_boundary(1.0, 299792458.0)
        self.assertAlmostEqual(boundary, 2.0)

    def test_far_field_boundary_rejects_zero_aperture(self):
        with self.assertRaises(ValueError):
            far_field_boundary(0.0, 1.0e9)

    def test_far_field_boundary_rejects_zero_frequency(self):
        with self.assertRaises(ValueError):
            far_field_boundary(1.0, 0.0)


class TestHazardCategories(unittest.TestCase):
    def test_high_drive_radiator_is_a_field_hazard(self):
        self.assertEqual(categorize_asset(radiating_asset()), (RADIATED_HAZARD,))

    def test_low_drive_radiator_is_uncategorized(self):
        self.assertEqual(
            categorize_asset(radiating_asset(drive_watt=1.0)), (LOW_HAZARD,)
        )

    def test_drive_exactly_at_the_threshold_enters_the_regime(self):
        self.assertIn(
            RADIATED_HAZARD, categorize_asset(radiating_asset(drive_watt=10.0))
        )

    def test_high_voltage_supply_is_an_electrical_hazard(self):
        self.assertEqual(categorize_asset(high_voltage_asset()), (ELECTRICAL_HAZARD,))

    def test_stored_energy_alone_triggers_the_electrical_regime(self):
        asset = high_voltage_asset(open_circuit_voltage_v=12.0, stored_energy_j=50.0)
        self.assertEqual(categorize_asset(asset), (ELECTRICAL_HAZARD,))

    def test_an_asset_can_carry_both_categories(self):
        asset = radiating_asset(open_circuit_voltage_v=3000.0)
        self.assertEqual(
            sorted(categorize_asset(asset)), sorted((RADIATED_HAZARD, ELECTRICAL_HAZARD))
        )

    def test_receiver_is_not_a_field_hazard_whatever_its_drive_field_says(self):
        asset = {"kind": "measurement-receiver", "drive_watt": 500.0}
        self.assertEqual(categorize_asset(asset), (LOW_HAZARD,))

    def test_unrecognized_asset_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_asset({"kind": "coffee-machine"})

    def test_negative_drive_rejected(self):
        with self.assertRaises(ValueError):
            categorize_asset(radiating_asset(drive_watt=-5.0))

    def test_non_mapping_asset_rejected(self):
        with self.assertRaises(ValueError):
            categorize_asset(["radiating-amplifier-chain"])


class TestRequiredProvisions(unittest.TestCase):
    def test_field_hazard_demands_its_safeguards(self):
        self.assertEqual(
            required_provisions([RADIATED_HAZARD]), frozenset(RADIATED_PROVISIONS)
        )

    def test_electrical_hazard_demands_discharge_tooling(self):
        self.assertIn(
            "discharge-and-ground-tooling", required_provisions([ELECTRICAL_HAZARD])
        )

    def test_both_categories_take_the_union(self):
        combined = required_provisions([RADIATED_HAZARD, ELECTRICAL_HAZARD])
        self.assertEqual(combined, frozenset(KNOWN_PROVISIONS))

    def test_low_hazard_demands_nothing(self):
        self.assertEqual(required_provisions([LOW_HAZARD]), frozenset())

    def test_unrecognized_category_rejected(self):
        with self.assertRaises(ValueError):
            required_provisions(["acoustic-hazard"])

    def test_bare_string_is_not_a_category_collection(self):
        with self.assertRaises(ValueError):
            required_provisions(RADIATED_HAZARD)


class TestAssetEvaluation(unittest.TestCase):
    def test_compliant_radiating_asset_has_no_finding(self):
        result = evaluate_asset(radiating_asset(), 3.0)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["exposure"]["within_limit"])

    def test_operator_too_close_is_flagged_with_a_standoff(self):
        result = evaluate_asset(radiating_asset(), 1.0)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(
            result["findings"][0]["finding"], "operator-position-inside-hazard-zone"
        )
        self.assertAlmostEqual(result["findings"][0]["minimum_standoff_m"], 2.8209479177)

    def test_standing_exactly_at_the_minimum_standoff_is_compliant(self):
        distance = minimum_standoff_distance(100.0, 10.0, 10.0)
        density = far_field_power_density(100.0, 10.0, distance)
        self.assertGreater(density, 10.0)
        result = evaluate_asset(radiating_asset(), distance)
        self.assertTrue(result["exposure"]["within_limit"])
        self.assertEqual(result["findings"], [])

    def test_a_real_exceedance_is_not_absorbed(self):
        distance = minimum_standoff_distance(100.0, 10.0, 10.0) * 0.999
        result = evaluate_asset(radiating_asset(), distance)
        self.assertFalse(result["exposure"]["within_limit"])

    def test_missing_provision_is_reported_per_provision(self):
        asset = radiating_asset(provisions=["warning-indicator"])
        result = evaluate_asset(asset, 3.0)
        self.assertEqual(len(result["findings"]), 3)
        self.assertEqual(
            result["missing_provisions"],
            sorted(set(RADIATED_PROVISIONS) - {"warning-indicator"}),
        )

    def test_operator_inside_the_far_field_boundary_is_flagged(self):
        asset = radiating_asset(aperture_m=3.0)
        result = evaluate_asset(asset, 3.0)
        reasons = [item["finding"] for item in result["findings"]]
        self.assertIn("standoff-inside-far-field-boundary", reasons)

    def test_far_field_boundary_is_not_flagged_when_the_operator_is_beyond_it(self):
        asset = radiating_asset(aperture_m=0.2)
        result = evaluate_asset(asset, 3.0)
        self.assertEqual(result["findings"], [])
        self.assertLess(result["exposure"]["far_field_boundary_m"], 3.0)

    def test_low_hazard_asset_needs_no_provision_and_gets_no_exposure_record(self):
        asset = {"id": "scope-1", "kind": "support-instrument", "provisions": []}
        result = evaluate_asset(asset, 3.0)
        self.assertEqual(result["categories"], [LOW_HAZARD])
        self.assertIsNone(result["exposure"])
        self.assertEqual(result["findings"], [])

    def test_radiating_asset_without_a_frequency_rejected(self):
        asset = radiating_asset()
        del asset["frequency_hz"]
        with self.assertRaises(ValueError):
            evaluate_asset(asset, 3.0)

    def test_unrecognized_provision_token_rejected(self):
        asset = radiating_asset(provisions=["hard-hat"])
        with self.assertRaises(ValueError):
            evaluate_asset(asset, 3.0)

    def test_asset_without_an_id_rejected(self):
        asset = radiating_asset()
        del asset["id"]
        with self.assertRaises(ValueError):
            evaluate_asset(asset, 3.0)

    def test_non_positive_standoff_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_asset(radiating_asset(), 0.0)

    def test_provisions_given_as_a_bare_string_rejected(self):
        asset = radiating_asset(provisions="warning-indicator")
        with self.assertRaises(ValueError):
            evaluate_asset(asset, 3.0)


class TestRunAssessment(unittest.TestCase):
    def test_a_fully_provisioned_bench_permits_the_run(self):
        result = assess_run_safety_provisions(
            [radiating_asset(), high_voltage_asset()], 3.0
        )
        self.assertTrue(result["run_permitted"])
        self.assertEqual(
            sorted(result["hazardous_assets"]), ["amp-chain-1", "hv-supply-1"]
        )

    def test_any_finding_blocks_the_run(self):
        assets = [radiating_asset(), high_voltage_asset(provisions=[])]
        result = assess_run_safety_provisions(assets, 3.0)
        self.assertFalse(result["run_permitted"])
        self.assertEqual(len(result["findings"]), len(ELECTRICAL_PROVISIONS))

    def test_findings_from_several_assets_are_aggregated(self):
        assets = [radiating_asset(provisions=[]), high_voltage_asset(provisions=[])]
        result = assess_run_safety_provisions(assets, 3.0)
        self.assertEqual(
            len(result["findings"]),
            len(RADIATED_PROVISIONS) + len(ELECTRICAL_PROVISIONS),
        )

    def test_low_hazard_assets_stay_off_the_hazardous_list(self):
        assets = [
            radiating_asset(),
            {"id": "scope-1", "kind": "support-instrument", "provisions": []},
        ]
        result = assess_run_safety_provisions(assets, 3.0)
        self.assertEqual(result["hazardous_assets"], ["amp-chain-1"])

    def test_duplicate_asset_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_run_safety_provisions(
                [radiating_asset(), radiating_asset()], 3.0
            )

    def test_empty_bench_rejected(self):
        with self.assertRaises(ValueError):
            assess_run_safety_provisions([], 3.0)


if __name__ == "__main__":
    unittest.main()
