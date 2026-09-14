#!/usr/bin/env python3
"""Contract test for ESD-sensitive assembly handling and storage (offline)."""

import copy
import math
import unittest

from e2008_sca_electrostatic_sensitivity_handling_logic import (
    CONTROL_BANDS,
    DISCHARGE_MODELS,
    HANDLING_COMPLIANT,
    HANDLING_CONDITIONAL,
    HANDLING_NON_COMPLIANT,
    PACKAGING_RANK,
    SENSITIVITY_BANDS,
    assess_handling_and_storage,
    categorize_sensitivity,
    control_verdict,
    decade_decay_time_s,
    evaluate_controls,
    packaging_adequacy,
    required_controls,
    residual_voltage_v,
    shelf_life_used_fraction,
    storage_envelope_findings,
)

GOOD_READINGS = {
    "operator-ground-path-ohm": 1.2e6,
    "worksurface-to-ground-ohm": 5.0e7,
    "floor-footwear-system-ohm": 4.0e6,
    "tool-to-ground-ohm": 2.0e6,
    "ionizer-offset-volt": -12.0,
    "relative-humidity-percent": 45.0,
}

ENVELOPE = {
    "temperature_c": (10.0, 30.0),
    "relative_humidity_percent": (30.0, 60.0),
}

BASE_SPEC = {
    "withstand_v": 180.0,
    "discharge_model": "human-body",
    "control_readings": dict(GOOD_READINGS),
    "packaging": "shielding",
    "storage_temperature_c": 21.0,
    "storage_relative_humidity_percent": 45.0,
    "storage_envelope": copy.deepcopy(ENVELOPE),
    "days_stored": 120.0,
    "shelf_life_days": 365.0,
}


def _spec(**overrides):
    item = copy.deepcopy(BASE_SPEC)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


class SensitivityCategorizationTests(unittest.TestCase):
    def test_a_low_withstand_voltage_lands_in_the_most_sensitive_band(self):
        result = categorize_sensitivity(180.0, "human-body")
        self.assertEqual(result["band"], "band-0-most-sensitive")
        self.assertEqual(result["rank"], 0)

    def test_a_high_withstand_voltage_lands_in_the_robust_band(self):
        self.assertEqual(categorize_sensitivity(9000.0)["rank"], 3)

    def test_the_same_voltage_categorizes_differently_per_discharge_model(self):
        human = categorize_sensitivity(300.0, "human-body")["rank"]
        device = categorize_sensitivity(300.0, "charged-device")["rank"]
        self.assertEqual(human, 1)
        self.assertEqual(device, 2)

    def test_every_declared_model_categorizes_a_mid_voltage(self):
        for model in DISCHARGE_MODELS:
            self.assertIn(model, SENSITIVITY_BANDS)
            band = categorize_sensitivity(300.0, model)
            self.assertIn(band["rank"], (0, 1, 2, 3))

    def test_a_non_positive_withstand_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_sensitivity(0.0)

    def test_an_unknown_discharge_model_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_sensitivity(500.0, "triboelectric-guess")


class RequiredControlTests(unittest.TestCase):
    def test_the_most_sensitive_band_owes_the_full_control_set(self):
        self.assertEqual(len(required_controls(0)), 6)

    def test_a_robust_band_owes_only_the_base_controls(self):
        self.assertEqual(len(required_controls(3)), 2)

    def test_the_obliged_set_never_shrinks_as_sensitivity_rises(self):
        sizes = [len(required_controls(rank)) for rank in (3, 2, 1, 0)]
        self.assertEqual(sizes, sorted(sizes))

    def test_an_unknown_band_rank_is_rejected(self):
        with self.assertRaises(ValueError):
            required_controls(9)


class ControlVerdictTests(unittest.TestCase):
    def test_an_in_band_ground_path_is_a_control(self):
        self.assertTrue(control_verdict("operator-ground-path-ohm", 1.0e7)["in_band"])

    def test_a_ground_path_below_the_floor_is_reported_as_too_conductive(self):
        verdict = control_verdict("operator-ground-path-ohm", 1.0e4)
        self.assertFalse(verdict["in_band"])
        self.assertEqual(verdict["side"], "below-band")

    def test_a_ground_path_above_the_ceiling_does_not_bleed_charge(self):
        verdict = control_verdict("operator-ground-path-ohm", 1.0e9)
        self.assertEqual(verdict["side"], "above-band")

    def test_a_reading_exactly_on_the_band_edge_is_inside_it(self):
        band = CONTROL_BANDS["worksurface-to-ground-ohm"]
        self.assertTrue(control_verdict("worksurface-to-ground-ohm", band["low"])["in_band"])
        self.assertTrue(control_verdict("worksurface-to-ground-ohm", band["high"])["in_band"])

    def test_an_ionizer_offset_is_graded_on_magnitude_not_sign(self):
        self.assertTrue(control_verdict("ionizer-offset-volt", -30.0)["in_band"])
        self.assertFalse(control_verdict("ionizer-offset-volt", -60.0)["in_band"])

    def test_a_non_positive_resistance_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            control_verdict("worksurface-to-ground-ohm", -5.0)

    def test_an_unknown_control_name_is_rejected(self):
        with self.assertRaises(ValueError):
            control_verdict("vibes-to-ground-ohm", 1.0e6)


class ControlSetTests(unittest.TestCase):
    def test_a_full_in_band_reading_set_covers_the_obliged_controls(self):
        result = evaluate_controls(dict(GOOD_READINGS), 0)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["out_of_band"], [])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_an_obliged_control_with_no_reading_is_named_missing(self):
        readings = dict(GOOD_READINGS)
        del readings["ionizer-offset-volt"]
        result = evaluate_controls(readings, 0)
        self.assertEqual(result["missing"], ["ionizer-offset-volt"])
        self.assertAlmostEqual(result["coverage"], 5.0 / 6.0, places=9)

    def test_a_control_present_but_out_of_band_does_not_count_as_coverage(self):
        readings = dict(GOOD_READINGS)
        readings["tool-to-ground-ohm"] = 1.0e11
        result = evaluate_controls(readings, 0)
        self.assertEqual(result["out_of_band"], ["tool-to-ground-ohm"])
        self.assertAlmostEqual(result["coverage"], 5.0 / 6.0, places=9)

    def test_a_reading_the_band_does_not_oblige_is_kept_out_of_scope(self):
        result = evaluate_controls(dict(GOOD_READINGS), 3)
        self.assertEqual(len(result["required"]), 2)
        self.assertIn("ionizer-offset-volt", result["off_scope"])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_an_unrecognised_reading_name_is_rejected(self):
        readings = dict(GOOD_READINGS)
        readings["lucky-charm-ohm"] = 1.0e6
        with self.assertRaises(ValueError):
            evaluate_controls(readings, 0)


class PackagingTests(unittest.TestCase):
    def test_shielding_packaging_carries_the_most_sensitive_band(self):
        self.assertTrue(packaging_adequacy("shielding", 0)["adequate"])

    def test_dissipative_packaging_does_not_carry_a_sensitive_band(self):
        result = packaging_adequacy("dissipative", 1)
        self.assertFalse(result["adequate"])
        self.assertIn("shielding", result["finding"])

    def test_dissipative_packaging_does_carry_a_moderate_band(self):
        self.assertTrue(packaging_adequacy("dissipative", 2)["adequate"])

    def test_insulative_packaging_carries_nothing(self):
        for rank in sorted(PACKAGING_RANK.values()):
            self.assertFalse(packaging_adequacy("insulative", rank)["adequate"])

    def test_an_unknown_packaging_family_is_rejected(self):
        with self.assertRaises(ValueError):
            packaging_adequacy("bubble-wrap-and-hope", 0)


class ResidualChargeTests(unittest.TestCase):
    def test_residual_voltage_is_the_charge_over_the_capacitance(self):
        self.assertAlmostEqual(residual_voltage_v(1.0, 100.0), 10.0, places=9)

    def test_a_smaller_assembly_capacitance_makes_the_same_charge_worse(self):
        small = abs(residual_voltage_v(1.0, 10.0))
        large = abs(residual_voltage_v(1.0, 1000.0))
        self.assertGreater(small, large * 10.0 - 1e-6)

    def test_a_negative_residual_charge_is_a_voltage_of_the_other_sign(self):
        self.assertAlmostEqual(residual_voltage_v(-2.0, 200.0), -10.0, places=9)

    def test_a_zero_assembly_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            residual_voltage_v(1.0, 0.0)

    def test_decade_decay_time_follows_the_resistance_capacitance_product(self):
        expected = 1.0e9 * 1.0e-10 * math.log(10.0)
        self.assertAlmostEqual(decade_decay_time_s(1.0e9, 100.0), expected, places=9)

    def test_a_non_positive_decay_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            decade_decay_time_s(0.0, 100.0)


class StorageTests(unittest.TestCase):
    def test_a_condition_inside_the_envelope_produces_no_finding(self):
        self.assertEqual(storage_envelope_findings(21.0, 45.0, ENVELOPE), [])

    def test_a_condition_exactly_on_an_envelope_edge_produces_no_finding(self):
        self.assertEqual(storage_envelope_findings(10.0, 60.0, ENVELOPE), [])

    def test_a_dry_store_is_reported_against_the_humidity_floor(self):
        findings = storage_envelope_findings(21.0, 12.0, ENVELOPE)
        self.assertEqual(len(findings), 1)
        self.assertIn("relative_humidity_percent", findings[0])

    def test_a_hot_store_is_reported_against_the_temperature_ceiling(self):
        findings = storage_envelope_findings(48.0, 45.0, ENVELOPE)
        self.assertEqual(len(findings), 1)
        self.assertIn("temperature_c", findings[0])

    def test_an_inverted_envelope_is_rejected(self):
        bad = {"temperature_c": (30.0, 10.0), "relative_humidity_percent": (30.0, 60.0)}
        with self.assertRaises(ValueError):
            storage_envelope_findings(21.0, 45.0, bad)

    def test_shelf_life_used_is_a_share_not_a_flag(self):
        self.assertAlmostEqual(shelf_life_used_fraction(146.0, 365.0), 0.4, places=9)

    def test_a_negative_storage_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_used_fraction(-1.0, 365.0)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_record_set_is_handling_compliant(self):
        result = assess_handling_and_storage(_spec())
        self.assertEqual(result["verdict"], HANDLING_COMPLIANT)
        self.assertEqual(result["findings"], [])

    def test_an_out_of_band_control_blocks_the_handling(self):
        readings = dict(GOOD_READINGS)
        readings["operator-ground-path-ohm"] = 1.0e3
        result = assess_handling_and_storage(_spec(control_readings=readings))
        self.assertEqual(result["verdict"], HANDLING_NON_COMPLIANT)

    def test_packaging_that_only_dissipates_blocks_a_band_zero_assembly(self):
        result = assess_handling_and_storage(_spec(packaging="dissipative"))
        self.assertEqual(result["verdict"], HANDLING_NON_COMPLIANT)
        self.assertTrue(any("shielding" in f for f in result["findings"]))

    def test_a_store_outside_the_envelope_restricts_rather_than_blocks(self):
        result = assess_handling_and_storage(_spec(storage_relative_humidity_percent=18.0))
        self.assertEqual(result["verdict"], HANDLING_CONDITIONAL)

    def test_a_spent_storage_life_restricts_the_assembly(self):
        result = assess_handling_and_storage(_spec(days_stored=400.0))
        self.assertEqual(result["verdict"], HANDLING_CONDITIONAL)
        self.assertGreater(result["shelf_life_used_fraction"], 1.0)

    def test_a_storage_life_exactly_spent_is_not_yet_a_finding(self):
        result = assess_handling_and_storage(_spec(days_stored=365.0))
        self.assertAlmostEqual(result["shelf_life_used_fraction"], 1.0, places=9)
        self.assertEqual(result["verdict"], HANDLING_COMPLIANT)

    def test_residual_charge_over_the_withstand_voltage_blocks_the_handling(self):
        result = assess_handling_and_storage(
            _spec(residual_charge_nc=40.0, assembly_capacitance_pf=100.0)
        )
        self.assertEqual(result["verdict"], HANDLING_NON_COMPLIANT)
        self.assertAlmostEqual(result["residual_voltage_v"], 400.0, places=9)

    def test_residual_charge_under_the_withstand_voltage_leaves_a_margin(self):
        result = assess_handling_and_storage(
            _spec(residual_charge_nc=5.0, assembly_capacitance_pf=100.0)
        )
        self.assertEqual(result["verdict"], HANDLING_COMPLIANT)
        self.assertAlmostEqual(result["withstand_margin_v"], 130.0, places=9)

    def test_residual_charge_needs_the_assembly_capacitance_alongside_it(self):
        with self.assertRaises(ValueError):
            assess_handling_and_storage(_spec(residual_charge_nc=5.0))

    def test_a_missing_spec_key_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_handling_and_storage(_spec(packaging=None))

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_handling_and_storage(["withstand_v", 180.0])


if __name__ == "__main__":
    unittest.main(verbosity=1)
