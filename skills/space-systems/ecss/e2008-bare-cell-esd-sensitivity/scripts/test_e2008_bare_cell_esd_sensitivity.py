#!/usr/bin/env python3
"""Contract test for bare-cell ESD-sensitive handling, clause 7.9.2 (offline)."""

import unittest

from e2008_bare_cell_esd_sensitivity_logic import (
    CONTROL_RESISTANCE_BANDS,
    DISCHARGE_MODELS,
    PACKAGING_CATEGORIES,
    REGIME_ACCEPTED,
    REGIME_REJECTED,
    REQUIRED_CONTROLS,
    SENSITIVITY_BANDS,
    STORAGE_ENVELOPE,
    assess_packaging,
    assess_protected_area,
    assess_storage,
    categorize_sensitivity,
    evaluate_handling_regime,
    normalize_discharge_model,
    normalize_packaging_category,
    required_controls,
    residual_charge_voltage,
    validate_capacitance,
    validate_resistance,
    validate_withstand_voltage,
)

BAND_1 = "esd-band-1-most-sensitive"
BAND_3 = "esd-band-3-moderate"
BAND_4 = "esd-band-4-least-sensitive"


def _controls(band=BAND_1, **overrides):
    values = {
        "esd-protected-area-marking": True,
        "grounded-work-surface": 1.0e6,
        "operator-wrist-strap": 1.0e6,
        "grounded-floor-and-footwear": 1.0e6,
        "air-ionizer": True,
    }
    owed = required_controls(band)
    controls = {k: v for k, v in values.items() if k in owed}
    controls.update(overrides)
    return controls


def _storage(**overrides):
    conditions = {
        "relative_humidity_percent": 45.0,
        "temperature_celsius": 22.0,
        "days_stored": 100,
        "declared_shelf_life_days": 365,
    }
    conditions.update(overrides)
    return conditions


def _spec(**overrides):
    spec = {
        "cell_id": "cell-a-001",
        "withstand_voltage_v": 200.0,
        "discharge_model": "human-body-model",
        "cell_capacitance_f": 2.0e-9,
        "residual_charge_c": 1.0e-9,
        "required_margin_factor": 2.0,
        "controls": _controls(BAND_1),
        "packaging_category": "shielding",
        "leaves_protected_area": True,
        "storage": _storage(),
    }
    spec.update(overrides)
    return spec


class SensitivityBandTests(unittest.TestCase):
    def test_every_model_carries_its_own_band_table(self):
        self.assertEqual(set(SENSITIVITY_BANDS), set(DISCHARGE_MODELS))

    def test_the_same_number_lands_in_different_bands_under_two_models(self):
        human = categorize_sensitivity(200.0, "human-body-model")
        device = categorize_sensitivity(200.0, "charged-device-model")
        self.assertEqual(human["band"], BAND_1)
        self.assertEqual(device["band"], "esd-band-2-sensitive")

    def test_a_band_lower_bound_belongs_to_the_band_above_it(self):
        result = categorize_sensitivity(250.0, "human-body-model")
        self.assertEqual(result["band"], "esd-band-2-sensitive")
        self.assertAlmostEqual(result["band_lower_v"], 250.0, places=9)

    def test_the_least_sensitive_band_is_unbounded_above(self):
        result = categorize_sensitivity(50000.0, "human-body-model")
        self.assertEqual(result["band"], BAND_4)
        self.assertFalse(result["sensitive"])

    def test_a_model_cannot_be_defaulted_away(self):
        with self.assertRaises(ValueError):
            categorize_sensitivity(200.0, "")

    def test_unknown_model_rejected(self):
        with self.assertRaises(ValueError):
            normalize_discharge_model("finger-poke-model")

    def test_zero_withstand_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_withstand_voltage(0.0)

    def test_boolean_withstand_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_withstand_voltage(True)


class ControlCatalogueTests(unittest.TestCase):
    def test_more_sensitive_bands_inherit_and_add(self):
        self.assertTrue(
            set(REQUIRED_CONTROLS[BAND_4]).issubset(set(REQUIRED_CONTROLS[BAND_1]))
        )
        self.assertIn("air-ionizer", REQUIRED_CONTROLS[BAND_1])
        self.assertNotIn("air-ionizer", REQUIRED_CONTROLS[BAND_3])

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            required_controls("esd-band-9")

    def test_resistance_bands_have_a_floor_as_well_as_a_ceiling(self):
        for low, high in CONTROL_RESISTANCE_BANDS.values():
            self.assertGreater(low, 0.0)
            self.assertGreater(high, low)


class ProtectedAreaTests(unittest.TestCase):
    def test_a_complete_in_band_control_set_is_accepted(self):
        result = assess_protected_area(BAND_1, _controls(BAND_1))
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["controls"]), 5)

    def test_an_absent_obliged_control_is_a_finding(self):
        controls = _controls(BAND_1)
        del controls["air-ionizer"]
        result = assess_protected_area(BAND_1, controls)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("air-ionizer" in f for f in result["findings"]))

    def test_a_fitted_strap_above_its_ceiling_is_not_a_ground(self):
        result = assess_protected_area(
            BAND_1, _controls(BAND_1, **{"operator-wrist-strap": 1.0e9})
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("ceiling" in f for f in result["findings"]))

    def test_a_strap_below_its_floor_is_a_safety_defect_not_a_better_ground(self):
        result = assess_protected_area(
            BAND_1, _controls(BAND_1, **{"operator-wrist-strap": 10.0})
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("floor" in f for f in result["findings"]))

    def test_a_resistance_control_refuses_a_bare_yes(self):
        with self.assertRaises(ValueError):
            assess_protected_area(
                BAND_1, _controls(BAND_1, **{"operator-wrist-strap": True})
            )

    def test_a_presence_control_refuses_a_resistance(self):
        with self.assertRaises(ValueError):
            assess_protected_area(
                BAND_1, _controls(BAND_1, **{"air-ionizer": 1.0e6})
            )

    def test_an_unowed_control_does_not_pay_for_an_owed_one(self):
        controls = _controls(BAND_3)
        del controls["operator-wrist-strap"]
        controls["air-ionizer"] = True
        result = assess_protected_area(BAND_3, controls)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["unowed_controls"], ("air-ionizer",))

    def test_non_mapping_control_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_protected_area(BAND_1, "everything was grounded")

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_resistance(-5.0)


class PackagingTests(unittest.TestCase):
    def test_shielding_packaging_may_leave_the_protected_area(self):
        self.assertTrue(assess_packaging("shielding", True)["accepted"])

    def test_dissipative_packaging_may_not_leave_the_protected_area(self):
        result = assess_packaging("dissipative", True)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["shields"])

    def test_dissipative_packaging_is_fine_inside_the_area(self):
        self.assertTrue(assess_packaging("dissipative", False)["accepted"])

    def test_insulative_packaging_is_never_a_protection(self):
        self.assertFalse(assess_packaging("insulative", False)["accepted"])

    def test_unknown_packaging_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_packaging_category("brown-paper")

    def test_packaging_catalogue_names_four_categories(self):
        self.assertEqual(len(PACKAGING_CATEGORIES), 4)

    def test_non_boolean_travel_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_packaging("shielding", "sometimes")


class StorageTests(unittest.TestCase):
    def test_a_quiet_envelope_is_accepted(self):
        result = assess_storage(_storage())
        self.assertTrue(result["accepted"])
        self.assertAlmostEqual(
            result["shelf_life_fraction_spent"], 100.0 / 365.0, places=9
        )

    def test_dry_storage_raises_tribocharging(self):
        result = assess_storage(_storage(relative_humidity_percent=12.0))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("tribocharge" in f for f in result["findings"]))

    def test_damp_storage_invites_condensation(self):
        result = assess_storage(_storage(relative_humidity_percent=85.0))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("condensation" in f for f in result["findings"]))

    def test_temperature_outside_the_envelope_is_a_finding(self):
        self.assertFalse(assess_storage(_storage(temperature_celsius=45.0))["accepted"])

    def test_shelf_life_is_consumed_even_with_nothing_observed(self):
        result = assess_storage(_storage(days_stored=500))
        self.assertFalse(result["accepted"])
        self.assertGreater(result["shelf_life_fraction_spent"], 1.0)

    def test_humidity_above_one_hundred_per_cent_rejected(self):
        with self.assertRaises(ValueError):
            assess_storage(_storage(relative_humidity_percent=140.0))

    def test_negative_days_stored_rejected(self):
        with self.assertRaises(ValueError):
            assess_storage(_storage(days_stored=-1))

    def test_zero_shelf_life_rejected(self):
        with self.assertRaises(ValueError):
            assess_storage(_storage(declared_shelf_life_days=0))

    def test_envelope_bounds_are_ordered(self):
        for low, high in STORAGE_ENVELOPE.values():
            self.assertGreater(high, low)


class ResidualChargeTests(unittest.TestCase):
    def test_charge_over_capacitance_gives_the_delivered_voltage(self):
        self.assertAlmostEqual(residual_charge_voltage(1.0e-9, 2.0e-9), 0.5, places=9)

    def test_a_smaller_cell_capacitance_delivers_a_higher_voltage(self):
        low = residual_charge_voltage(1.0e-9, 4.0e-9)
        high = residual_charge_voltage(1.0e-9, 1.0e-9)
        self.assertGreater(high, low)

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            validate_capacitance(0.0)

    def test_negative_charge_rejected(self):
        with self.assertRaises(ValueError):
            residual_charge_voltage(-1.0e-9, 1.0e-9)


class RegimeTests(unittest.TestCase):
    def test_a_sound_regime_is_accepted(self):
        result = evaluate_handling_regime(_spec())
        self.assertEqual(result["verdict"], REGIME_ACCEPTED)
        self.assertEqual(result["sensitivity"]["band"], BAND_1)
        self.assertAlmostEqual(result["allowed_voltage_v"], 100.0, places=9)

    def test_a_complete_control_set_still_fails_on_the_charge_it_leaves(self):
        result = evaluate_handling_regime(_spec(residual_charge_c=1.0e-6))
        self.assertEqual(result["verdict"], REGIME_REJECTED)
        self.assertTrue(any("residual charge" in f for f in result["findings"]))

    def test_reading_the_wrong_model_moves_the_control_obligation(self):
        spec = _spec(
            withstand_voltage_v=1500.0,
            discharge_model="human-body-model",
            controls=_controls(BAND_3),
        )
        result = evaluate_handling_regime(spec)
        self.assertEqual(result["sensitivity"]["band"], BAND_3)
        self.assertTrue(result["protected_area"]["accepted"])

    def test_the_same_cell_under_the_other_model_owes_more_controls(self):
        spec = _spec(
            withstand_voltage_v=100.0,
            discharge_model="charged-device-model",
            controls=_controls(BAND_3),
        )
        result = evaluate_handling_regime(spec)
        self.assertEqual(result["sensitivity"]["band"], BAND_1)
        self.assertFalse(result["protected_area"]["accepted"])

    def test_achieved_margin_is_reported_alongside_the_required_one(self):
        result = evaluate_handling_regime(_spec())
        self.assertAlmostEqual(result["delivered_voltage_v"], 0.5, places=9)
        self.assertAlmostEqual(result["achieved_margin_factor"], 400.0, places=9)

    def test_a_margin_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_handling_regime(_spec(required_margin_factor=0.5))

    def test_packaging_and_storage_findings_reach_the_regime_verdict(self):
        result = evaluate_handling_regime(
            _spec(packaging_category="dissipative", storage=_storage(days_stored=900))
        )
        self.assertEqual(result["verdict"], REGIME_REJECTED)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["storage"]
        with self.assertRaises(ValueError):
            evaluate_handling_regime(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_handling_regime("handled carefully")

    def test_blank_cell_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_handling_regime(_spec(cell_id="   "))


if __name__ == "__main__":
    unittest.main()
